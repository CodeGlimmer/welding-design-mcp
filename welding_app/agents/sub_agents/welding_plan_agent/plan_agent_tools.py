import json
import sqlite3
import uuid
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
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
from welding_app.welding_scenario.process_parameters import (
    ProcessParamsUnion,
)
from welding_app.welding_scenario.weld_seam import WeldSeamModel
from welding_app.welding_scenario.weld_sequence_plan import (
    SolderJointMixedWeldSeamSortModel,
    SolderJointsSortModel,
    WeldingSequenceNavigator,
    WeldingSequenceSortModel,
    WeldSeamSortModel,
    WeldSeamsSortModel,
)
from welding_app.welding_scenario.welding_plan import (
    ProcessAssignmentModel,
    WeldingPlanModel,
)
from welding_app.welding_scenario.welding_scenario import WeldingScenarioModel

from .types import (
    CurrentState,
    GenerateWeldingPlanInputModel,
    GetWeldingScenarioInputModel,
    QueryWeldingInformationInputModel,
    SaveWeldingPlanInputModel,
    SaveWeldingPlanOutputModel,
    SetWeldingParamsInputModel,
    SetWeldingSortPlanInputModel,
    ShowCurrentWeldingObjectOutputModel,
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
        Path(__file__).parent.parent.parent.parent
        / "databases"
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
        seam_model = scenario_model.weld_seams[seam_idx]
        sorted_devide = welding_seam_devides[seam_idx]
        sorted_weld_joint_on_seam = [
            (
                seam_model.solder_joints[pair[0]],
                seam_model.solder_joints[pair[1]],
            )
            for pair in sorted_devide
        ]
        if not seam_model.id:
            raise ToolException(
                message=f"焊缝索引 {seam_idx} 缺少 ID",
                content="焊缝缺少 ID 无法继续生成工艺规划",
                code=ToolErrorCode.INVALID_INPUT,
                details=None,
                input_args=GenerateWeldingPlanInputModel(
                    scenario_id=scenario_id
                ).model_dump(),
                retryable=False,
                tool_name="generate_welding_plan",
            )
        welding_seam_list.append(
            WeldSeamSortModel(
                seam_id=seam_model.id, sub_seam_sort=sorted_weld_joint_on_seam
            )
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
            code=ToolErrorCode.INVALID_INPUT,
            details=None,
            input_args=GetWeldingScenarioInputModel(
                scenario_id=scenario_id
            ).model_dump(),
            tool_name="get_welding_scenario",
            retryable=False,
        )


class ScenarioType(Enum):
    SolderJoints = 0
    SolderJointMixedWeldSeam = 1


@dataclass
class CurrentWeldingPlanContainer:
    welding_scenario: WeldingScenarioModel | None = None  # 当前焊接场景
    welding_sort_plan: WeldingSequenceSortModel | None = None  # 当前焊接方案顺序
    scenario_type: ScenarioType = ScenarioType.SolderJoints  # 场景类型
    welding_plan: WeldingPlanModel | None = None  # 焊接方案: 生成的目标
    nav: WeldingSequenceNavigator | None = None


def design_welding_plan_toolkit():
    """焊接工艺参数设计工具集

    Tools:
        导航工具
        set_welding_sort_plan: 设计焊接方案的顺序, 初始化参数设计
        next_welding_obj: 获取下一个焊接对象
        previous_welding_obj: 获取上一个焊接对象
        show_current_welding_obj: 显示当前焊接对象

        参数设计工具
        set_welding_params: 设置焊接参数

        保存工具
        save_welding_plan: 保存焊接方案

    Hooks:
        check_velocity: 检查速度
        check_sort_plan: 检查焊接方案顺序
    """

    _welding_plan = CurrentWeldingPlanContainer()

    @tool(
        args_schema=SetWeldingSortPlanInputModel,
        description="""传入完成排序的焊接方案
        系统会将当前被设计的焊接方案指向已经完成排序的焊接方案

        Returns:
            str: 返回“焊接工艺顺序已经设定，可以开始设计工艺参数”的提示
        """,
    )
    def set_welding_sort_plan(
        sort_plan: WeldingSequenceSortModel, welding_scenario_id: str
    ) -> str:
        """传入焊接工艺方案的顺序，即generate_welding_plan与agent审核后的结果"""
        _welding_plan.welding_sort_plan = sort_plan
        _welding_plan.nav = WeldingSequenceNavigator(sort_plan)

        # 设置焊接类型
        if sort_plan.sequence_plan.type_flag == "SolderJointsSortModel":
            _welding_plan.scenario_type = ScenarioType.SolderJoints
        else:
            _welding_plan.scenario_type = ScenarioType.SolderJointMixedWeldSeam

        # 绑定具体的焊接场景
        _welding_plan.welding_scenario = WeldingScenarioModel.model_validate_json(
            _fetch_scenario_from_db(welding_scenario_id)
        )

        # 初始化焊接工艺方案
        _welding_plan.welding_plan = WeldingPlanModel(
            plan_id=uuid.uuid4().hex,
            name=None,
            scenario=_welding_plan.welding_scenario,
            sequence=_welding_plan.welding_sort_plan,
        )

        return "焊接工艺顺序已经设定，可以开始设计工艺参数"

    @tool(
        description=f"""显示当前正在设计的焊接对象

        Returns:
            ShowCurrentWeldingObjectOutputModel:
                <json-schema>
                    {ShowCurrentWeldingObjectOutputModel.model_json_schema()}
                </json-schema>""",
    )
    def show_current_welding_obj() -> ShowCurrentWeldingObjectOutputModel:
        """展示当前的焊接对象（焊点，焊缝），提供参数信息，agent借此推断使用怎样的参数组合"""
        if not _welding_plan.nav:
            raise ToolException(
                message="当前没有正在设计的焊接对象",
                code=ToolErrorCode.RESOURCE_NOT_FOUND,
                details="可能为正确调用set_welding_sort_plan",
                input_args=None,
                content="当前没有正在设计的对象",
                tool_name="show_current_welding_obj",
                retryable=False,
            )
        current_obj = _welding_plan.nav.current()
        if not current_obj:
            raise ToolException(
                message="当前没有正在设计的焊接对象",
                code=ToolErrorCode.RESOURCE_NOT_FOUND,
                details="整体的焊接顺序方案没问题，但是为找到当前被设计的对象",
                input_args=None,
                content="当前没有正在设计的对象",
                tool_name="show_current_welding_obj",
                retryable=False,
            )
        # 对象有效
        state = None
        idx = _welding_plan.nav._current_index
        if idx == 0:
            state = CurrentState.START
        elif idx == _welding_plan.nav.total_count() - 1:
            state = CurrentState.END
        else:
            state = CurrentState.MIDDLE
        if current_obj.task_type == "solder_joint":
            # 类型为单纯的焊点
            return ShowCurrentWeldingObjectOutputModel(
                state=state,
                current_object=current_obj.solder_joint,  # type: ignore
                parent_object_id=None,
            )
        return ShowCurrentWeldingObjectOutputModel(
            state=state,
            current_object=current_obj.sub_seam,  # type: ignore
            parent_object_id=current_obj.seam_id,
        )

    @tool(description="切换到下一个焊接对象，同时提供提示，本工具不会产生报错")
    def next_welding_obj() -> str:
        """切换到下一个焊接对象"""
        if not _welding_plan.nav:
            return "没有可切换的对象"
        if _welding_plan.nav.is_end():
            return "已经是最后一个对象，无法切换"
        _welding_plan.nav.next()
        return "切换到下一个焊接对象成功"

    @tool(description="切换到上一个对象, 并给出提示，本工具不会报错")
    def prev_welding_obj() -> str:
        """切换到上一个焊接对象"""
        if not _welding_plan.nav:
            return "没有可切换的对象"
        if _welding_plan.nav._current_index == 0:
            return "已经是第一个对象，无法切换"
        _welding_plan.nav.prev()
        return "切换到上一个焊接对象成功"

    @tool(
        args_schema=SetWeldingParamsInputModel,
        description="""设置焊接工艺参数
        根据焊接对象的类型，本工具提供了为两种焊接工艺提供工艺参数的方法
        Returns: 返回设置成功的提示
        Error: 本工具可能失败""",
    )
    def set_welding_params(process_params: ProcessParamsUnion) -> str:
        process_type = process_params.type_flag
        if process_type == "spot_welding":
            # 设置点焊的工艺参数
            try:
                process = ProcessAssignmentModel(
                    entity_id=_welding_plan.nav.current().solder_joint.position.id,  # type: ignore
                    params=process_params,
                )
            except Exception as e:
                raise ToolException(
                    message=str(e),
                    code=ToolErrorCode.UNKNOWN,
                    details="此处的错误原因较为复杂，请检查对象类型与工艺类型是否匹配，或者别的原因",
                    input_args=SetWeldingParamsInputModel(
                        process_params=process_params
                    ).model_dump(),
                    content="处理错误，原因较为复杂，请仔细检查分析",
                    tool_name="set_welding_params",
                    retryable=False,
                )
            if not _welding_plan.welding_plan:
                raise ToolException(
                    message="没有设置焊接方案，无法设置焊接参数",
                    code=ToolErrorCode.UNKNOWN,
                    details="可能初始化时有问题",
                    input_args=None,
                    content="不存在焊接方案",
                    tool_name="set_welding_params",
                    retryable=False,
                )
            # 如果列表中不存在该项，则创建此项，否则应该覆盖
            for i, p in enumerate(_welding_plan.welding_plan.process_assignments):
                if p.entity_id == process.entity_id:
                    _welding_plan.welding_plan.process_assignments[i] = process
                    break
            else:
                _welding_plan.welding_plan.process_assignments.append(process)
            return "焊点焊接参数已经设置成功"
        # 子焊缝工艺参数设置
        elif process_type == "continuous_welding":
            # 设置子焊缝的工艺参数
            try:
                current_task = _welding_plan.nav.current()  # type: ignore
                if not current_task or current_task.task_type != "sub_seam":
                    raise ValueError("当前任务不是子焊缝，无法设置连续焊参数")

                process = ProcessAssignmentModel(
                    entity_id=current_task.param_entity_id,
                    params=process_params,
                )
            except Exception as e:
                raise ToolException(
                    message=str(e),
                    code=ToolErrorCode.UNKNOWN,
                    details="子焊缝参数设置错误，请检查当前任务类型",
                    input_args=SetWeldingParamsInputModel(
                        process_params=process_params
                    ).model_dump(),
                    content="子焊缝参数设置失败",
                    tool_name="set_welding_params",
                    retryable=False,
                )
            if not _welding_plan.welding_plan:
                raise ToolException(
                    message="没有设置焊接方案，无法设置焊接参数",
                    code=ToolErrorCode.UNKNOWN,
                    details="可能初始化时有问题",
                    input_args=None,
                    content="不存在焊接方案",
                    tool_name="set_welding_params",
                    retryable=False,
                )
            # 如果列表中不存在该项，则创建此项，否则应该覆盖
            for i, p in enumerate(_welding_plan.welding_plan.process_assignments):
                if p.entity_id == process.entity_id:
                    _welding_plan.welding_plan.process_assignments[i] = process
                    break
            else:
                _welding_plan.welding_plan.process_assignments.append(process)
            return "子焊缝焊接参数已经设置成功"
        else:
            raise ToolException(
                message=f"不支持的工艺类型: {process_type}",
                code=ToolErrorCode.UNKNOWN,
                details="只支持 spot_welding 和 continuous_welding 类型",
                input_args=SetWeldingParamsInputModel(
                    process_params=process_params
                ).model_dump(),
                content="工艺类型不支持",
                tool_name="set_welding_params",
                retryable=False,
            )

    @tool(
        args_schema=SaveWeldingPlanInputModel,
        description=f"""# 保存焊接方案

        保存当前设计的焊接方案到数据库。需要传入方案名称和对应的场景ID。

        Args:
            plan_name: 焊接方案的名称，要求简短易识别
            scenario_id: 焊接方案对应的场景ID，必须与之前使用的场景ID保持一致

        Returns:
            SaveWeldingPlanOutputModel:
                <json-schema>
                    {SaveWeldingPlanOutputModel.model_json_schema()}
                </json-schema>

        Error: 不会发生报错
        """,
    )
    def save_welding_plan(
        plan_name: str, scenario_id: str
    ) -> SaveWeldingPlanOutputModel:
        """保存焊接方案"""
        # 检查是否有可保存的焊接方案
        if not _welding_plan.welding_plan:
            raise ToolException(
                message="没有可保存的焊接方案",
                content="当前没有正在设计的焊接方案，请先设计焊接方案",
                code=ToolErrorCode.RESOURCE_NOT_FOUND,
                details="可能未调用 set_welding_sort_plan 或 generate_welding_plan",
                input_args=SaveWeldingPlanInputModel(
                    plan_name=plan_name, scenario_id=scenario_id
                ).model_dump(),
                tool_name="save_welding_plan",
                retryable=False,
            )

        # 检查焊接方案是否完整
        if not _welding_plan.welding_plan.scenario:
            raise ToolException(
                message="焊接方案不完整，缺少场景信息",
                content="焊接方案缺少场景信息，无法保存",
                code=ToolErrorCode.INVALID_INPUT,
                details="焊接方案的 scenario 字段为空",
                input_args=SaveWeldingPlanInputModel(
                    plan_name=plan_name, scenario_id=scenario_id
                ).model_dump(),
                tool_name="save_welding_plan",
                retryable=False,
            )

        if not _welding_plan.welding_plan.sequence:
            raise ToolException(
                message="焊接方案不完整，缺少顺序信息",
                content="焊接方案缺少顺序信息，无法保存",
                code=ToolErrorCode.INVALID_INPUT,
                details="焊接方案的 sequence 字段为空",
                input_args=SaveWeldingPlanInputModel(
                    plan_name=plan_name, scenario_id=scenario_id
                ).model_dump(),
                tool_name="save_welding_plan",
                retryable=False,
            )

        try:
            # 设置方案名称
            _welding_plan.welding_plan.name = plan_name

            # 如果 plan_id 不存在，生成新的
            if not _welding_plan.welding_plan.plan_id:
                _welding_plan.welding_plan.plan_id = uuid.uuid4().hex

            # 使用传入的场景ID，而不是从焊点中提取
            # 场景ID是在调用 set_welding_sort_plan 时传入的 welding_scenario_id
            # 现在通过参数直接传入，确保一致性

            # 序列化数据
            full_data_json = _welding_plan.welding_plan.model_dump_json()
            scenario_json = _welding_plan.welding_plan.scenario.model_dump_json()
            sequence_json = _welding_plan.welding_plan.sequence.model_dump_json()

            # 序列化工艺分配表 - 使用 model_dump_json 确保一致性
            process_assignments_list = [
                assignment.model_dump(mode='json')
                for assignment in _welding_plan.welding_plan.process_assignments
            ]
            process_assignments_json = json.dumps(process_assignments_list)

            # 构建数据库路径 - 修正路径
            db_path = (
                Path(__file__).parent.parent.parent.parent  # 回到 welding_app 目录
                / "databases"
                / "welding_plan.db"
            )

            # 确保数据库目录存在
            db_path.parent.mkdir(parents=True, exist_ok=True)

            # 连接数据库并保存
            conn = sqlite3.connect(db_path)
            try:
                cursor = conn.cursor()

                # 创建表（如果不存在）
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS welding_plans (
                        plan_id TEXT PRIMARY KEY,
                        name TEXT,
                        scenario_id TEXT,
                        full_data_json TEXT NOT NULL,
                        scenario_json TEXT NOT NULL,
                        sequence_json TEXT NOT NULL,
                        process_assignments_json TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # 插入数据
                cursor.execute(
                    """
                    INSERT INTO welding_plans
                    (plan_id, name, scenario_id, full_data_json, scenario_json, sequence_json, process_assignments_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        _welding_plan.welding_plan.plan_id,
                        plan_name,
                        scenario_id,
                        full_data_json,
                        scenario_json,
                        sequence_json,
                        process_assignments_json,
                    ),
                )

                conn.commit()

                # 返回结果
                return SaveWeldingPlanOutputModel(
                    plan_id=_welding_plan.welding_plan.plan_id
                )

            except sqlite3.Error as e:
                conn.rollback()
                raise ToolException(
                    message=f"数据库操作失败: {str(e)}",
                    content="保存焊接方案到数据库时发生错误",
                    code=ToolErrorCode.DB_WRITE_FAILED,
                    details=f"SQLite错误: {str(e)}",
                    input_args=SaveWeldingPlanInputModel(
                        plan_name=plan_name, scenario_id=scenario_id
                    ).model_dump(),
                    tool_name="save_welding_plan",
                    retryable=True,
                )
            finally:
                conn.close()

        except Exception as e:
            if isinstance(e, ToolException):
                raise e
            raise ToolException(
                message=f"保存焊接方案失败: {str(e)}",
                content="保存焊接方案时发生未知错误",
                code=ToolErrorCode.UNKNOWN,
                details=f"异常类型: {type(e).__name__}, 详细信息: {str(e)}",
                input_args=SaveWeldingPlanInputModel(
                    plan_name=plan_name, scenario_id=scenario_id
                ).model_dump(),
                tool_name="save_welding_plan",
                retryable=False,
            )

    return [
        set_welding_sort_plan,
        show_current_welding_obj,
        next_welding_obj,
        prev_welding_obj,
        set_welding_params,
        save_welding_plan,  # 添加到返回列表中
    ]
