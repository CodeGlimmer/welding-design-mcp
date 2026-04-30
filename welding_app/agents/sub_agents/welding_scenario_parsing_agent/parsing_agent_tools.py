import sqlite3
import uuid
from pathlib import Path
from typing import Annotated, Literal, Optional, cast

from langchain.tools import tool
from pydantic import BaseModel, Field

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


# ============== Input/Output Schemas ==============


class GetScenarioFileContentInput(BaseModel):
    """tool get_scenario_file_content input schema"""

    id: Annotated[str, Field(description="场景文件ID，用于查询对应的场景文件")]


class ShowScenarioOutput(BaseModel):
    """tool show_scenario output schema"""

    total_items: Annotated[int, Field(description="场景中总的项目数量（焊点+焊缝）")]
    solder_joints: Annotated[
        list[dict], Field(description="焊点列表，包含每个焊点的详细信息")
    ]
    weld_seams: Annotated[
        list[dict], Field(description="焊缝列表，包含每个焊缝的详细信息")
    ]


class ClearScenarioInput(BaseModel):
    """tool clear_scenario input schema（无输入参数）"""

    pass


class ClearScenarioOutput(BaseModel):
    """tool clear_scenario output schema"""

    message: Annotated[str, Field(description="操作结果消息")]


class UndoInput(BaseModel):
    """tool undo input schema（无输入参数）"""

    pass


class UndoOutput(BaseModel):
    """tool undo output schema"""

    message: Annotated[str, Field(description="操作结果消息")]


class SaveScenarioInput(BaseModel):
    """tool save_scenario input schema（无输入参数）"""

    pass


class SolderJointBatchItemInput(BaseModel):
    """批量添加焊点的单个焊点数据"""

    position: GeometryPointModel
    base_material: Optional[list[WeldingMaterialBIW]] = None
    name: Optional[str] = None
    surface_normal: Optional[tuple[float, float, float]] = None
    connected_parts: Optional[list[str]] = None
    thicknss_combination: Optional[list[float]] = None


class AddSolderJointsInput(BaseModel):
    """tool add_solder_joints input schema"""

    solder_joints: Annotated[
        list[SolderJointBatchItemInput],
        Field(description="焊点列表，每个焊点包含位置、材料、名称等属性"),
    ]


class AddSolderJointInput(BaseModel):
    """tool add_solder_joint input schema"""

    position: Annotated[GeometryPointModel, Field(description="焊点位置坐标")]
    base_material: Annotated[
        Optional[list[WeldingMaterialBIW]], Field(description="母材材质列表")
    ] = None
    name: Annotated[Optional[str], Field(description="焊点名称")] = None
    surface_normal: Annotated[
        Optional[tuple[float, float, float]],
        Field(description="焊接表面法线向量 (x, y, z)"),
    ] = None
    connected_parts: Annotated[
        Optional[list[str]], Field(description="焊接连接的部件名称列表")
    ] = None
    thicknss_combination: Annotated[
        Optional[list[float]], Field(description="板厚组合列表")
    ] = None


class AddWeldSeamInput(BaseModel):
    """tool add_weld_seam input schema"""

    line: Annotated[
        GeometryStraightLineModel, Field(description="焊缝的几何线段，定义起点和终点")
    ]
    solder_joints: Annotated[
        list[SolderJointModel],
        Field(description="焊缝上的控制点列表，作为焊缝的定位参考"),
    ]
    id: Annotated[Optional[str], Field(description="焊缝的唯一标识符")] = None
    name: Annotated[Optional[str], Field(description="焊缝的自定义名称")] = None


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _point_key(point: GeometryPointModel) -> tuple[float, float, float]:
    return (round(point.x, 9), round(point.y, 9), round(point.z, 9))


def _ensure_point_id(
    point: GeometryPointModel,
    point_id_by_position: dict[tuple[float, float, float], str] | None = None,
) -> None:
    if point_id_by_position is None:
        if not point.id:
            point.id = _new_uuid()
        return

    key = _point_key(point)
    if point.id:
        existing_id = point_id_by_position.setdefault(key, point.id)
        point.id = existing_id
        return

    point.id = point_id_by_position.setdefault(key, _new_uuid())


def _ensure_solder_joint_model_id(
    solder_joint: SolderJointModel,
    point_id_by_position: dict[tuple[float, float, float], str] | None = None,
) -> None:
    _ensure_point_id(solder_joint.position, point_id_by_position)


def _ensure_line_model_ids(
    line: GeometryStraightLineModel,
    point_id_by_position: dict[tuple[float, float, float], str] | None = None,
) -> None:
    if not line.id:
        line.id = _new_uuid()
    _ensure_point_id(line.start_point, point_id_by_position)
    _ensure_point_id(line.end_point, point_id_by_position)


def _ensure_weld_seam_model_ids(
    weld_seam: WeldSeamModel,
    point_id_by_position: dict[tuple[float, float, float], str],
) -> None:
    if not weld_seam.id:
        weld_seam.id = _new_uuid()
    if weld_seam.line:
        _ensure_line_model_ids(weld_seam.line, point_id_by_position)
    for solder_joint in weld_seam.solder_joints:
        _ensure_solder_joint_model_id(solder_joint, point_id_by_position)


def _ensure_scenario_model_ids(
    scenario_model: WeldingScenarioModel,
) -> WeldingScenarioModel:
    point_id_by_position: dict[tuple[float, float, float], str] = {}

    for solder_joint in scenario_model.solder_joints:
        _ensure_solder_joint_model_id(solder_joint, point_id_by_position)

    for weld_seam in scenario_model.weld_seams:
        _ensure_weld_seam_model_ids(weld_seam, point_id_by_position)

    return scenario_model


# ============== Tools ==============


@tool(
    args_schema=GetScenarioFileContentInput,
    description=f"""根据场景文件ID获取场景文件内容

    根据提供的ID从数据库查询对应的场景文件，并读取文件内容。
    支持txt、json、robx等文件类型。

    Returns:
        GetScenarioFileContentOutput:
            <json-schema>
                {GetScenarioFileContentOutput.model_json_schema()}
            <json-schema>

    Note: 无论是否发生错误，均通过统一schema返回。错误情况通过返回对象中的id_exists、file_exsits等字段标识。""",
)
def get_scenario_file_content(id: str) -> GetScenarioFileContentOutput:
    """根据场景文件ID获取场景文件内容"""
    global source_file_id

    connect = sqlite3.connect(
        Path(__file__).parent.parent.parent.parent / "databases" / "welding_scenario.db"
    )
    file_position = ""
    content = ""
    file_type = "txt"
    try:
        with connect:
            cursor = connect.cursor()
            res = cursor.execute(
                "select file_position from local_file where welding_scenario_id = ?",
                (id,),
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
        add_solder_joints: 批量添加多个焊点
        add_weld_seam: 添加一个焊缝
        undo: 撤回
        show_scenario: 将场景转换成basemodel, 供agent整体把握
        save_scenario: 保存当前场景到数据库
    """
    global source_file_id

    welding_scenario: set = set()
    welding_scenario_history = Commands(welding_scenario)

    @tool(
        args_schema=ClearScenarioInput,
        description=f"""清空当前场景

        这是你创建一个新场景时必须首先做的事，用于初始化一个空场景。

        Returns:
            ClearScenarioOutput:
                <json-schema>
                    {ClearScenarioOutput.model_json_schema()}
                <json-schema>

        Note: 无论是否发生错误，均通过统一schema返回。""",
    )
    def clear_scenario() -> ClearScenarioOutput:
        """清空当前场景"""
        nonlocal welding_scenario
        nonlocal welding_scenario_history
        welding_scenario = set()
        welding_scenario_history = Commands(welding_scenario)
        return ClearScenarioOutput(message="场景已清空")

    @tool(
        args_schema=AddSolderJointInput,
        description="""添加一个焊点到当前场景

        Args:
            position: 焊点位置
            base_material: 基础材料
            name: 焊点名称
            surface_normal: 表面法线
            connected_parts: 连接的部件
            thicknss_combination: 厚度组合

        Returns:
            str: "焊点已添加"

        Note: 无论是否发生错误，均通过统一schema返回。""",
    )
    def add_solder_joint(
        position: GeometryPointModel,
        base_material: Optional[list[WeldingMaterialBIW]] = None,
        name: Optional[str] = None,
        surface_normal: Optional[tuple[float, float, float]] = None,
        connected_parts: Optional[list[str]] = None,
        thicknss_combination: Optional[list[float]] = None,
    ) -> str:
        """添加一个焊点"""
        nonlocal welding_scenario, welding_scenario_history

        _ensure_point_id(position)
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

    @tool(
        args_schema=AddSolderJointsInput,
        description="""批量添加多个焊点到当前场景

        当从场景文件中解析出多个焊点信息后，可以一次性调用此工具添加所有焊点。
        比单独多次调用 add_solder_joint 更高效。
        所有焊点会被作为一个批次添加，调用一次 undo 即可撤回全部。

        Returns:
            str: "已批量添加 X 个焊点"

        Note: 无论是否发生错误，均通过统一schema返回。

        Input:
            solder_joints: 焊点列表，每个焊点包含以下参数：
                - position: 焊点的三维坐标位置 (x, y, z) 和 id。
                - base_material: 母材材质列表。
                - name: 焊点名称。
                - surface_normal: 焊接表面法线向量 (x, y, z)。
                - connected_parts: 焊接连接的部件名称列表。
                - thicknss_combination: 板厚组合列表。
        """,
    )
    def add_solder_joints(
        solder_joints: list[SolderJointBatchItemInput],
    ) -> str:
        """批量添加多个焊点到当前场景"""
        nonlocal welding_scenario, welding_scenario_history

        added_joints = []
        for item in solder_joints:
            _ensure_point_id(item.position)
            solder_joint = SolderJointModel(
                position=item.position,
                base_material=item.base_material,
                name=item.name,
                surface_normal=item.surface_normal,
                connected_parts=item.connected_parts,
                thicknss_combination=item.thicknss_combination,
            ).to_SolderJoint()

            welding_scenario.add(solder_joint)
            added_joints.append(solder_joint)

        welding_scenario_history.add_command(
            Command(
                action=Action.ADD_SOLDER_JOINT,
                action_item=added_joints,
            )
        )

        return f"已批量添加 {len(added_joints)} 个焊点"

    @tool(
        args_schema=AddWeldSeamInput,
        description="""添加一条焊缝到当前场景

        当从场景文件中解析出焊缝信息后，调用此工具将焊缝添加到内存中的场景。
        焊缝包含几何线段和焊点集合。

        Returns:
            str: "焊缝已添加"

        Note: 无论是否发生错误，均通过统一schema返回。

        Input:
            line: 焊缝的几何线段，定义焊缝的起点和终点。
                - start_point: 焊缝起点坐标 (x, y, z)。
                - end_point: 焊缝终点坐标 (x, y, z)。
                - id: 线段的唯一标识符。
                如果无法从文件中获取精确的线段信息，此参数可传 None，
                系统会根据 solder_joints 的位置自动生成一条默认线段。
            solder_joints: 焊缝上的控制点列表。
                这些焊点会作为焊缝的定位参考点。
                注意：这些焊点会同时被添加到场景中，无需单独调用 add_solder_joint。
                当 line=None 时，系统会根据这些点的位置生成默认线段。
            id: 焊缝的唯一标识符，用于在场景中区分不同焊缝。
            name: 焊缝的自定义名称，方便识别，如 "左侧车门焊缝"。
        """,
    )
    def add_weld_seam(
        line: GeometryStraightLineModel,
        solder_joints: list[SolderJointModel],
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> str:
        """添加一条焊缝到当前场景"""
        nonlocal welding_scenario, welding_scenario_history

        if not id:
            id = _new_uuid()
        point_id_by_position: dict[tuple[float, float, float], str] = {}
        _ensure_line_model_ids(line, point_id_by_position)
        for solder_joint in solder_joints:
            _ensure_solder_joint_model_id(solder_joint, point_id_by_position)

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

    @tool(
        args_schema=UndoInput,
        description=f"""撤回上一步操作

        撤回最近一次添加焊点或焊缝的操作。

        Returns:
            UndoOutput:
                <json-schema>
                    {UndoOutput.model_json_schema()}
                <json-schema>

        Note: 无论是否发生错误，均通过统一schema返回。""",
    )
    def undo() -> UndoOutput:
        """撤回上一步操作"""
        nonlocal welding_scenario, welding_scenario_history

        if not welding_scenario_history._commands:
            return UndoOutput(message="没有可撤回的操作")

        welding_scenario_history.undo()
        return UndoOutput(message="已撤回上一步操作")

    @tool(
        args_schema=ClearScenarioInput,
        description=f"""显示当前场景的完整信息

        返回完整的JSON数据供agent整体把握当前场景状态。
        包含焊点和焊缝的详细信息。

        Returns:
            ShowScenarioOutput:
                <json-schema>
                    {ShowScenarioOutput.model_json_schema()}
                <json-schema>

        Note: 无论是否发生错误，均通过统一schema返回。""",
    )
    def show_scenario() -> ShowScenarioOutput:
        """显示当前场景的完整信息"""
        nonlocal welding_scenario

        solder_joints_list = []
        weld_seams_list = []

        for item in welding_scenario:
            if isinstance(item, SolderJoint):
                solder_joint_model = SolderJointModel.from_SolderJoint(item)
                full_model_dict = solder_joint_model.model_dump()
                if full_model_dict.get("base_material"):
                    full_model_dict["base_material"] = [
                        material.value for material in full_model_dict["base_material"]
                    ]

                solder_joints_list.append(
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

                weld_seams_list.append(
                    {
                        "id": item._id,
                        "name": item._name,
                        "length": item.get_seam_length(),
                        "solder_joints_count": item.get_solder_joints_num(),
                        "full_model": full_model_dict,
                    }
                )

        return ShowScenarioOutput(
            total_items=len(welding_scenario),
            solder_joints=solder_joints_list,
            weld_seams=weld_seams_list,
        )

    @tool(
        args_schema=SaveScenarioInput,
        description=f"""保存当前场景到数据库

        将内存中的焊接场景持久化到数据库，返回场景ID。

        Returns:
            SaveScenarioOutput:
                <json-schema>
                    {SaveScenarioOutput.model_json_schema()}
                <json-schema>

        Note: 无论是否发生错误，均通过统一schema返回。""",
    )
    def save_scenario() -> SaveScenarioOutput:
        """保存当前场景到数据库"""
        nonlocal welding_scenario

        scenario_model = _ensure_scenario_model_ids(
            WeldingScenarioModel.from_welding_scenario(welding_scenario)
        )
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
        add_solder_joints,
        add_weld_seam,
        undo,
        show_scenario,
        save_scenario,
    ]
