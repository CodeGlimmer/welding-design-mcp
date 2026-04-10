import sqlite3
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from langchain.messages import HumanMessage
from langchain.tools import tool

from welding_app.agents.sub_agents.rag_agent.rag_agent import create_rag_agent
from welding_app.algorithm.sort_algo.solder_joint_sort import sort_solder_joints
from welding_app.algorithm.sort_algo.welding_seam_sort import (
    design_single_welding_seam_sort,
    sort_welding_seam,
)
from welding_app.error.error_message import ToolErrorCode, ToolException
from welding_app.welding_scenario.weld_seam import WeldSeamModel
from welding_app.welding_scenario.weld_sequence_plan import (
    SolderJointMixedWeldSeamSortModel,
    SolderJointsSortModel,
    WeldingSequenceSortModel,
    WeldSeamSortModel,
    WeldSeamsSortModel,
)
from welding_app.welding_scenario.welding_scenario import WeldingScenarioModel

from .types import (
    GenerateWeldingPlanInputModel,
    GetWeldingScenarioInputModel,
    QueryWeldingInformationInputModel,
)


def _determine_sort_axis(point1, point2) -> int:
    """根据两点确定排序坐标轴：返回变化量最大的轴 (0=x, 1=y, 2=z)"""
    delta_x = abs(point1.x - point2.x)
    delta_y = abs(point1.y - point2.y)
    delta_z = abs(point1.z - point2.z)
    if delta_x >= delta_y and delta_x >= delta_z:
        return 0
    elif delta_y >= delta_x and delta_y >= delta_z:
        return 1
    return 2


def _get_sort_key(axis: int):
    """根据坐标轴获取排序函数"""
    match axis:
        case 0:
            return lambda joint: joint.position.x
        case 1:
            return lambda joint: joint.position.y
        case 2:
            return lambda joint: joint.position.z
        case _:
            return lambda joint: joint.position.x


def _build_seam_position_map(weld_seams: list[WeldSeamModel]) -> dict[int, tuple]:
    """构建焊缝位置映射：idx -> (起点坐标, 终点坐标)"""
    idx_to_pos_map = {}
    for idx, welding_seam in enumerate(weld_seams):
        if welding_seam.line:
            idx_to_pos_map[idx] = (
                (
                    welding_seam.line.start_point.x,
                    welding_seam.line.start_point.y,
                    welding_seam.line.start_point.z,
                ),
                (
                    welding_seam.line.end_point.x,
                    welding_seam.line.end_point.y,
                    welding_seam.line.end_point.z,
                ),
            )
            continue

        # 无line时，根据首尾焊点确定边界
        solder_joints = welding_seam.solder_joints
        point1, point2 = solder_joints[0].position, solder_joints[-1].position
        axis = _determine_sort_axis(point1, point2)
        sorted_joints = sorted(solder_joints, key=_get_sort_key(axis))
        start_joint, end_joint = sorted_joints[0], sorted_joints[-1]
        idx_to_pos_map[idx] = (
            (start_joint.position.x, start_joint.position.y, start_joint.position.z),
            (end_joint.position.x, end_joint.position.y, end_joint.position.z),
        )
    return idx_to_pos_map


def _divide_seam_welding_order(weld_seams: list[WeldSeamModel]) -> list:
    """对每段焊缝进行焊接顺序划分"""
    welding_seam_devides = []
    for welding_seam in weld_seams:
        solder_joints_on_seam = [
            (j.position.x, j.position.y, j.position.z)
            for j in welding_seam.solder_joints
        ]
        sorted_devides = design_single_welding_seam_sort(solder_joints_on_seam)
        welding_seam_devides.append(sorted_devides)
    return welding_seam_devides


def _build_solder_joints_map(scenario_model: WeldingScenarioModel) -> tuple[dict, list]:
    """提取焊缝中的焊点，与原有焊点合并成新的映射表"""
    seams = scenario_model.weld_seams
    solder_joints = deepcopy(scenario_model.solder_joints)
    map_dict = {}

    # 原有焊点建立映射
    for i, point in enumerate(solder_joints):
        map_dict[i] = (point.position.x, point.position.y, point.position.z)

    # 焊缝中的焊点加入映射
    next_idx = len(solder_joints)
    for weld_seam in seams:
        for solder_joint in weld_seam.solder_joints:
            map_dict[next_idx] = (
                solder_joint.position.x,
                solder_joint.position.y,
                solder_joint.position.z,
            )
            solder_joints.append(solder_joint)
            next_idx += 1

    return map_dict, solder_joints


def _fetch_scenario_from_db(scenario_id: str) -> str:
    """从数据库获取场景JSON数据"""
    connect = sqlite3.connect(
        Path(__file__).parent.parent.parent.parent.parent
        / "welding_app"
        / "data"
        / "welding_scenarios.db"
    )
    try:
        with connect:
            cursor = connect.cursor()
            res = cursor.execute(
                "select data from welding_scenarios where id = ?",
                (scenario_id,),
            )
            return res.fetchone()[0]
    finally:
        connect.close()


@tool(
    args_schema=GenerateWeldingPlanInputModel,
    description=f"""根据场景id获取场景对象，从而对场景中的焊点，焊缝的焊接顺序作出规划

        Returns:
            WeldingSequenceSortModel:
                <json-schema>
                    {WeldingSequenceSortModel.model_json_schema()}
                <json-schema>

        Error: 可能抛出异常""",
)
def generate_welding_plan(scenario_id: str) -> WeldingSequenceSortModel:
    """根据场景id获取场景对象，从而对场景中的焊点，焊缝的焊接顺序作出规划"""

    # 从数据库获取场景
    scenario_model = WeldingScenarioModel.model_validate_json(
        _fetch_scenario_from_db(scenario_id)
    )

    if not scenario_model.weld_seams:
        # 场景为空
        if not scenario_model.solder_joints:
            raise ToolException(
                message="场景为空，无法生成工艺规划",
                content="场景为空，无法为空场景生成工艺规划",
                code=ToolErrorCode.SCENARIO_NOT_FOUND,
                details="场景中既不存在焊缝，也不存在焊点",
                input_args=GenerateWeldingPlanInputModel(
                    scenario_id=scenario_id
                ).model_dump(),
                retryable=False,
                tool_name="generate_welding_plan",
            )

        # 只存在焊点集合：直接排序
        points = {
            idx: (p.position.x, p.position.y, p.position.z)
            for idx, p in enumerate(scenario_model.solder_joints)
        }
        best_order, best_fitness, best_history = sort_solder_joints(points)
        return WeldingSequenceSortModel(
            sequence_plan=SolderJointsSortModel(
                best_fitness=best_fitness,
                solder_joint_sort=[scenario_model.solder_joints[i] for i in best_order],
                best_fitness_history=list(best_history),
            )
        )

    # 存在焊缝的情况
    # step1+2: 合并焊点映射表，规划纯焊点顺序
    map_dict, _ = _build_solder_joints_map(scenario_model)
    best_order, best_fitness, best_history = sort_solder_joints(map_dict)
    best_joint_sort = [
        scenario_model.solder_joints[i]
        for i in best_order
        if i < len(scenario_model.solder_joints)
    ]

    # step3: 对焊缝排序
    idx_to_pos_map = _build_seam_position_map(scenario_model.weld_seams)
    sorted_welding_seam_plan = sort_welding_seam(idx_to_pos_map)

    # step4: 对每段焊缝划分焊接顺序
    welding_seam_devides = _divide_seam_welding_order(scenario_model.weld_seams)

    # step5: 综合统计，组装最终结果
    welding_seam_list: list[WeldSeamSortModel] = []
    for seam_idx in sorted_welding_seam_plan:
        sorted_devide = welding_seam_devides[seam_idx]
        sorted_weld_joint_on_seam = [
            (
                scenario_model.weld_seams[seam_idx].solder_joints[pair[0]],
                scenario_model.weld_seams[seam_idx].solder_joints[pair[1]],
            )
            for pair in sorted_devide
        ]
        welding_seam_list.append(
            WeldSeamSortModel(sub_seam_sort=sorted_weld_joint_on_seam)
        )

    return WeldingSequenceSortModel(
        sequence_plan=SolderJointMixedWeldSeamSortModel(
            solder_joints_sort=SolderJointsSortModel(
                best_fitness=best_fitness,
                solder_joint_sort=best_joint_sort,
                best_fitness_history=list(best_history),
            ),
            weld_seam_sort=WeldSeamsSortModel(welding_seam_sort=welding_seam_list),
        )
    )


@tool(
    args_schema=QueryWeldingInformationInputModel,
    description="""从知识库检索焊接基础知识

    Returns:
        str: 知识库中查询到的焊接知识
    """,
)
def query_welding_infomation(query: str) -> str:
    """调用rag智能体，从知识库中查询焊接的相关知识"""
    try:
        rag_agent = create_rag_agent()
    except Exception as e:
        raise ToolException(
            message=str(e),
            code=ToolErrorCode.UNKNOWN,
            details=None,
            input_args=QueryWeldingInformationInputModel(query=query).model_dump(),
            content="rag agent初始化失败",
            tool_name="query_welding_infomation",
            retryable=False,
        )
    try:
        result = rag_agent.invoke({"messages": [HumanMessage(content=query)]})
    except Exception as e:
        raise ToolException(
            message=str(e),
            code=ToolErrorCode.UNKNOWN,
            details=None,
            input_args=QueryWeldingInformationInputModel(query=query).model_dump(),
            content="rag agent调用失败",
            tool_name="query_welding_infomation",
            retryable=False,
        )
    return result["messages"][-1].content


@tool(
    args_schema=GetWeldingScenarioInputModel,
    description=f"""获取焊接场景

    Returns:
        WeldingScenarioModel:
            <json-schema>
                {WeldingScenarioModel.model_json_schema()}
            </json-schema>

    Error: 可能尝试异常
    """,
)
def get_welding_scenario(scenario_id: str) -> WeldingScenarioModel:
    """获取焊接场景"""
    try:
        return WeldingScenarioModel.model_validate_json(
            _fetch_scenario_from_db(scenario_id=scenario_id)
        )
    except Exception as e:
        raise ToolException(
            message=str(e),
            content="场景在数据库中存储的schema不符合标准",
            code=ToolErrorCode.NVALID_INPUT,
            details=None,
            input_args=GetWeldingScenarioInputModel(
                scenario_id=scenario_id
            ).model_dump(),
            tool_name="get_welding_scenario",
            retryable=False,
        )


@dataclass
class CurrentWeldingPlanContainer:
    welding_sort_plan: WeldingSequenceSortModel | None
    scenario_type: Literal["solder_joints", "solder_joint_mixed_weld_seam"] = (
        "solder_joints"
    )


def design_welding_plan_toolkit():
    """焊接工艺参数设计工具集

    Tools:
        导航工具
        set_welding_sort_plan: 设计焊接方案的顺序
        next_welding_obj: 获取下一个焊接对象
        previous_welding_obj: 获取上一个焊接对象
        show_current_welding_obj: 显示当前焊接对象

        参数设计工具
        set_welding_params: 设置焊接参数

    Hooks:
        check_velocity: 检查速度
        check_sort_plan: 检查焊接方案顺序
    """

    _welding_sort_plan = None

    @tool(
        description="""传入完成排序的焊接方案
        系统会将当前被设计的焊接方案指向已经完成排序的焊接方案
        """
    )
    def set_welding_sort_plan(sort_plan: WeldingSequenceSortModel):
        """传入焊接工艺方案的顺序，即generate_welding_plan与agent审核后的结果"""
        nonlocal _welding_sort_plan
        _welding_sort_plan = sort_plan
