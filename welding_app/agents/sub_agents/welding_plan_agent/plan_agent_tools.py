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
    WeldingSequenceSortModel
)

@tool
def generate_welding_plan(
    scenario_id: Annotated[
        str,
        Field(
            description="场景id，根据此id，tool可以寻找到场景对象，进一步对场景对象中的焊点进行排序"
        ),
    ],
) -> WeldingSequenceSortModel | str:
    """根据场景id获取场景对象，从而对场景中的焊点，焊缝的焊接顺序作出规划"""

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
            if not res:
                return "未找到场景"
            res = res[0]
    finally:
        connect.close()

    # 获取场景model
    scenario_model = WeldingScenarioModel.model_validate_json(res)
    if not scenario_model.weld_seams:
        # 不存在焊缝，纯焊点集合排序
        if not scenario_model.solder_joints:
            # 焊点集合为空
            return "场景为空，无法生成焊接工艺方案"
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
                best_fitness_history=list(best_history)
            )
        )

    # 考虑有焊缝的情况
    # step1: 提取焊缝中的焊点，组成新的焊点集合
    seams = scenario_model.weld_seams
    idx = len(scenario_model.solder_joints) # 新的idx从此出开始
    solder_joints = deepcopy(scenario_model.solder_joints)
    map_dict = dict() # 映射表，方便从下标映射到焊点
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
                solder_joint.position.z
            )
            solder_joints.append(solder_joint)
            idx += 1
    best_order, best_fitness, best_history = sort_solder_joints(map_dict)

    

