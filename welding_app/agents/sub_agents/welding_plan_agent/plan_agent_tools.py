import sqlite3
from copy import deepcopy
from pathlib import Path

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

from .types import GenerateWeldingPlanInputModel, QueryWeldingInformationInputModel

# ============ Helper Functions ============


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

    # 获取json-str格式的场景
    connect = sqlite3.connect(
        Path(__file__).parent.parent.parent.parent.parent
        / "welding_app"
        / "data"
        / "welding_scenarios.db"
    )
    res = None
    try:
        with connect:
            cursor = connect.cursor()
            res = cursor.execute(
                "select data from welding_scenarios where id = ?",
                (scenario_id,),
            )
            res = res.fetchone()
            res = res[0]
    finally:
        connect.close()

    # 获取场景model
    scenario_model = WeldingScenarioModel.model_validate_json(res)
    if not scenario_model.weld_seams:
        # 不存在焊缝，纯焊点集合排序
        if not scenario_model.solder_joints:
            # 焊点集合为空
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
        # 只存在焊点集合，建立映射表
        points = dict()
        for idx, point in enumerate(scenario_model.solder_joints):
            points[idx] = (point.position.x, point.position.y, point.position.z)
        best_order, best_fitness, best_history = sort_solder_joints(points)
        best_joint_sort = []
        for idx in best_order:
            best_joint_sort.append(scenario_model.solder_joints[idx])
        return WeldingSequenceSortModel(
            sequence_plan=SolderJointsSortModel(
                best_fitness=best_fitness,
                solder_joint_sort=best_joint_sort,
                best_fitness_history=list(best_history),
            )
        )

    # 考虑有焊缝的情况
    # step1: 提取焊缝中的焊点，组成新的焊点集合
    seams = scenario_model.weld_seams
    idx = len(scenario_model.solder_joints)  # 新的idx从此出开始
    solder_joints = deepcopy(scenario_model.solder_joints)
    map_dict = dict()  # 映射表，方便从下标映射到焊点
    for i, point in enumerate(solder_joints):
        map_dict[i] = (
            point.position.x,
            point.position.y,
            point.position.z,
        )
    for weld_seam in seams:
        for solder_joint in weld_seam.solder_joints:
            map_dict[idx] = (
                solder_joint.position.x,
                solder_joint.position.y,
                solder_joint.position.z,
            )
            solder_joints.append(solder_joint)  # 将焊缝中的焊点加入原本的焊点集合
            idx += 1

    # step2: 按照无焊缝的情况规划顺序, 得到纯焊点的规划顺序
    best_order, best_fitness, best_history = sort_solder_joints(map_dict)
    best_joint_sort = []
    for idx in best_order:
        best_joint_sort.append(scenario_model.solder_joints[idx])

    # step3: 对焊缝进行排序
    idx_to_pos_map = dict()
    for idx, welding_seam in enumerate(scenario_model.weld_seams):
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
        # 不存在line，则应该在焊点中获取首尾两点作为边界
        solder_joints = welding_seam.solder_joints
        # 选择变化的坐标轴, 随机两点，最大变化坐标轴
        axis = 0
        point1 = solder_joints[0].position
        point2 = solder_joints[-1].position
        delta_x = abs(point1.x - point2.x)
        delta_y = abs(point1.y - point2.y)
        delta_z = abs(point1.z - point2.z)
        if delta_x >= delta_y and delta_x >= delta_z:
            axis = 0
        elif delta_y >= delta_x and delta_y >= delta_z:
            axis = 1
        else:
            axis = 2

        sorted_joints = sorted(solder_joints, key=_get_sort_key(axis))
        start_joint, end_joint = sorted_joints[0], sorted_joints[-1]
        idx_to_pos_map[idx] = (
            (start_joint.position.x, start_joint.position.y, start_joint.position.z),
            (end_joint.position.x, end_joint.position.y, end_joint.position.z),
        )
    sorted_welding_seam_plan = sort_welding_seam(idx_to_pos_map)

    # step4: 对每段焊缝作出划分，给出每段焊缝的焊接顺序
    welding_seam_devides = []
    for welding_seam in scenario_model.weld_seams:
        solder_joints_on_seam = []
        for solder_joint_on_seam in welding_seam.solder_joints:
            solder_joints_on_seam.append(
                (
                    solder_joint_on_seam.position.x,
                    solder_joint_on_seam.position.y,
                    solder_joint_on_seam.position.z,
                )
            )
        sorted_devides = design_single_welding_seam_sort(solder_joints_on_seam)
        welding_seam_devides.append(sorted_devides)

    # step5: 综合统计给出顺序
    welding_seam_list: list[WeldSeamSortModel] = []
    for seam_idx in sorted_welding_seam_plan:
        sorted_devide = welding_seam_devides[seam_idx]  # 排序后的idx
        sorted_weld_joint_on_seam = []
        for pair in sorted_devide:
            sorted_weld_joint_on_seam.append(
                (
                    scenario_model.weld_seams[seam_idx].solder_joints[pair[0]],
                    scenario_model.weld_seams[seam_idx].solder_joints[pair[1]],
                )
            )
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
