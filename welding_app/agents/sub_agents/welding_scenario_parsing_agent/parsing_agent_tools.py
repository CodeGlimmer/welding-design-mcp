import sqlite3
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

from .command import Action, Command, Commands
from .types import GetScenarioFileContentOutput


@tool
def get_scenario_file_content(
    id: Annotated[str, Field(description="模型ID")],
) -> GetScenarioFileContentOutput:
    """获取场景文件内容"""
    # 检查数据库中是否保存场景
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
        # id 不存在
        return GetScenarioFileContentOutput(id=id, id_exists=False, file_exsits=False)
    # 测试文件是否存在
    file_path = Path(file_position)
    if not file_path.exists():
        return GetScenarioFileContentOutput(
            id=id,
            id_exists=True,
            file_exsits=False,
        )
    # 检测文件类型
    file_type = file_path.suffix[1:]
    # 读取文件内容
    match file_type:
        case "txt" | "json":
            content = file_path.read_text()
        case "robx":
            # TODO: 完成robx解析函数
            content = ""
        case _:
            content = "文件类型不支持"

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
        show_scenatio: 将场景转换成basemodel, 供agent整体把握
    """

    welding_scenario = set()
    welding_scenario_history = Commands(welding_scenario)

    @tool
    def clear_scenario() -> str:
        """清空当前场景, 这是你创建一个新场景时必须首先做的事 x"""
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

        # 使用WeldSeamModel创建焊缝对象
        weld_seam_model = WeldSeamModel(
            id=id,
            name=name,
            line=line,
            solder_joints=solder_joints,
        )

        # 转换为WeldSeam对象
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

        from welding_app.welding_scenario.solder_joint import SolderJointModel
        from welding_app.welding_scenario.weld_seam import WeldSeamModel

        scenario_info = {
            "total_items": len(welding_scenario),
            "solder_joints": [],
            "weld_seams": [],
        }

        for item in welding_scenario:
            if isinstance(item, SolderJoint):
                # 使用SolderJointModel获取完整的焊点信息
                solder_joint_model = SolderJointModel.from_SolderJoint(item)
                # 转换枚举为字符串以确保JSON可序列化
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
                # 使用WeldSeamModel获取完整的焊缝信息
                weld_seam_model = WeldSeamModel.from_WeldSeam(item)
                # 转换焊缝中的焊点枚举为字符串
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

    return [
        clear_scenario,
        add_solder_joint,
        add_weld_seam,
        undo,
        show_scenario,
    ]
