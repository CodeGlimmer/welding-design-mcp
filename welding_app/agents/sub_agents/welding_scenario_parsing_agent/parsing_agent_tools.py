import sqlite3
import uuid
from pathlib import Path
from typing import Annotated, Literal, Optional, cast

from langchain.tools import tool
from pydantic import Field

from welding_app.welding_scenario.materials import WeldingMaterialBIW
from welding_app.welding_scenario.solder_joint import (
    GeometryPointModel,
    SolderJoint,
    SolderJointModel,
)
from welding_app.welding_scenario.weld_seam import (
    GeometryStraightLineModel,
    WeldSeam,
    WeldSeamModel,
)
from welding_app.welding_scenario.welding_scenario import WeldingScenarioModel

from .command import Action, Command, Commands
from .extract_path_info_from_robx import extract_path_json
from .types import GetScenarioFileContentOutput, SaveScenarioOutput


source_file_id: str = ""


@tool
def get_scenario_file_content(
    id: Annotated[str, Field(description="模型ID")],
) -> GetScenarioFileContentOutput:
    """获取场景文件内容"""
    global source_file_id

    connect = sqlite3.connect(
        Path(__file__).parent.parent.parent.parent
        / "databases"
        / "welding_scenarios.db"
    )
    file_position = ""
    content = ""
    file_type = "txt"
    try:
        with connect:
            cursor = connect.cursor()
            res = cursor.execute(
                "select file_position from local_file where id = ?", (id,)
            )
            file_position = res.fetchone()[0]
    finally:
        connect.close()
    if not file_position:
        return GetScenarioFileContentOutput(id=id, id_exists=False, file_exsits=False)

    file_path = Path(file_position)
    if not file_path.exists():
        return GetScenarioFileContentOutput(
            id=id,
            id_exists=True,
            file_exsits=False,
        )

    file_type = file_path.suffix[1:]
    match file_type:
        case "txt" | "json":
            content = file_path.read_text()
        case "robx":
            content = extract_path_json(str(file_path))
            if not content:
                content = "场景文件解析失败"
        case _:
            content = "文件类型不支持"

    source_file_id = id

    return GetScenarioFileContentOutput(
        id=id,
        id_exists=True,
        file_exsits=True,
        content=content,
        file_type=cast(Optional[Literal["txt", "json", "robx"]], file_type),
    )


def generate_scenario_builder_toolkit():
    """生成场景构建工具包
    ToolKit:
        clear_scenario: 初始化场景
        add_solder_joint: 添加一个焊点
        add_weld_seam: 添加一个焊缝
        undo: 撤回
        show_scenario: 将场景转换成basemodel, 供agent整体把握
        save_scenario: 保存当前场景到数据库
    """
    global source_file_id

    welding_scenario: set = set()
    welding_scenario_history = Commands(welding_scenario)

    @tool
    def clear_scenario() -> str:
        """清空当前场景, 这是你创建一个新场景时必须首先做的事"""
        nonlocal welding_scenario
        nonlocal welding_scenario_history
        welding_scenario = set()
        welding_scenario_history = Commands(welding_scenario)
        return "场景已清空"

    @tool(args_schema=SolderJointModel)
    def add_solder_joint(
        position: GeometryPointModel,
        base_material: Optional[list[WeldingMaterialBIW]] = None,
        name: Optional[str] = None,
        surface_normal: Optional[tuple[float, float, float]] = None,
        connected_parts: Optional[list[str]] = None,
        thicknss_combination: Optional[list[float]] = None,
    ):
        """添加一个焊点
        Args:
            position: 焊点位置
            base_material: 基础材料
            name: 焊点名称
            surface_normal: 表面法线
            connected_parts: 连接的部件
            thicknss_combination: 厚度组合
        """
        nonlocal welding_scenario, welding_scenario_history

        if not welding_scenario:
            welding_scenario = set()

        solder_joint: SolderJoint = SolderJointModel(
            position=position,
            base_material=base_material,
            name=name,
            surface_normal=surface_normal,
            connected_parts=connected_parts,
            thicknss_combination=thicknss_combination,
        ).to_SolderJoint()

        welding_scenario.add(solder_joint)

        welding_scenario_history.add_command(
            Command(
                action=Action.ADD_SOLDER_JOINT,
                action_item=solder_joint,
            )
        )

        return "焊点已添加"

    @tool(args_schema=WeldSeamModel)
    def add_weld_seam(
        line: GeometryStraightLineModel,
        solder_joints: list[SolderJointModel],
        id: Optional[str] = None,
        name: Optional[str] = None,
    ):
        """添加一个焊缝
        Args:
            line: 焊缝的几何线
            solder_joints: 焊缝上的焊点集合
            id: 焊缝的唯一标识
            name: 焊缝名称
        """
        nonlocal welding_scenario, welding_scenario_history

        if not welding_scenario:
            welding_scenario = set()

        weld_seam_model = WeldSeamModel(
            id=id,
            name=name,
            line=line,
            solder_joints=solder_joints,
        )

        weld_seam = weld_seam_model.to_WeldSeam()

        welding_scenario.add(weld_seam)

        welding_scenario_history.add_command(
            Command(
                action=Action.ADD_WELDING_SEAM,
                action_item=weld_seam,
            )
        )

        return "焊缝已添加"

    @tool
    def undo() -> str:
        """撤回上一步操作"""
        nonlocal welding_scenario, welding_scenario_history

        if not welding_scenario_history._commands:
            return "没有可撤回的操作"

        welding_scenario_history.undo()
        return "已撤回上一步操作"

    @tool
    def show_scenario() -> dict:
        """显示当前场景的完整信息，返回完整的JSON数据供agent整体把握"""
        nonlocal welding_scenario

        scenario_info = {
            "total_items": len(welding_scenario),
            "solder_joints": [],
            "weld_seams": [],
        }

        for item in welding_scenario:
            if isinstance(item, SolderJoint):
                solder_joint_model = SolderJointModel.from_SolderJoint(item)
                full_model_dict = solder_joint_model.model_dump()
                if full_model_dict.get("base_material"):
                    full_model_dict["base_material"] = [
                        material.value for material in full_model_dict["base_material"]
                    ]

                scenario_info["solder_joints"].append(
                    {
                        "id": item.id,
                        "position": item.position,
                        "name": item._name,
                        "base_material": (
                            [material.value for material in item._base_material]
                            if item._base_material
                            else None
                        ),
                        "surface_normal": item._surface_normal,
                        "connected_parts": item._connected_parts,
                        "thicknss_combination": item._thicknss_combination,
                        "full_model": full_model_dict,
                    }
                )
            elif isinstance(item, WeldSeam):
                weld_seam_model = WeldSeamModel.from_WeldSeam(item)
                full_model_dict = weld_seam_model.model_dump()
                if full_model_dict.get("solder_joints"):
                    for solder_joint in full_model_dict["solder_joints"]:
                        if solder_joint.get("base_material"):
                            solder_joint["base_material"] = [
                                material.value
                                for material in solder_joint["base_material"]
                            ]

                scenario_info["weld_seams"].append(
                    {
                        "id": item._id,
                        "name": item._name,
                        "length": item.get_seam_length(),
                        "solder_joints_count": item.get_solder_joints_num(),
                        "full_model": full_model_dict,
                    }
                )

        return scenario_info

    @tool
    def save_scenario() -> SaveScenarioOutput:
        """保存当前场景到数据库，返回场景ID"""
        nonlocal welding_scenario

        scenario_model = WeldingScenarioModel.from_welding_scenario(welding_scenario)
        scenario_id = str(uuid.uuid4())

        db_path = (
            Path(__file__).parent.parent.parent.parent
            / "databases"
            / "welding_scenarios.db"
        )

        conn = sqlite3.connect(db_path)
        try:
            with conn:
                conn.execute(
                    "INSERT INTO welding_scenarios (id, source_file_id, data) VALUES (?, ?, ?)",
                    (scenario_id, source_file_id, scenario_model.model_dump_json()),
                )
        finally:
            conn.close()

        return SaveScenarioOutput(
            scenario_id=scenario_id,
            source_file_id=source_file_id,
            solder_joints_count=len(scenario_model.solder_joints),
            weld_seams_count=len(scenario_model.weld_seams),
        )

    return [
        clear_scenario,
        add_solder_joint,
        add_weld_seam,
        undo,
        show_scenario,
        save_scenario,
    ]
