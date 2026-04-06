import sqlite3
from pathlib import Path
from typing import Annotated
from copy import deepcopy

from langchain.tools import tool
from pydantic import Field

from welding_app.welding_scenario.welding_scenario import WeldingScenarioModel
from welding_app.algorithm.sort_algo.solder_joint_sort import sort_solder_joints
from welding_app.welding_scenario.weld_sequence_plan import (
    SolderJointsSortModel,
    WeldSeamSortModel,
    WeldSeamsSortModel,
    SolderJointMixedWeldSeamSortModel,
    WeldingSequenceSortModel,
)
from welding_app.error.error_message import ToolException, ToolErrorCode

from .types import GenerateWeldingPlanInputModel


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
        # 建立映射表
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
            solder_joints.append(solder_joint)
            idx += 1

    # step2: 按照无焊缝的情况规划顺序, 得到纯焊点的规划顺序
    best_order, best_fitness, best_history = sort_solder_joints(map_dict)
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

    
