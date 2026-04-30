import sqlite3
from enum import Enum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

from welding_app.welding_scenario.process_parameters import ProcessParamsUnion
from welding_app.welding_scenario.solder_joint import SolderJointModel


class GenerateWeldingPlanInputModel(BaseModel):
    """tool generate_welding_plan input schema"""

    scenario_id: Annotated[
        str,
        Field(
            description="场景id，根据此id，tool可以寻找到场景对象，进一步对场景对象中的焊点进行排序"
        ),
    ]

    @field_validator("scenario_id")
    @classmethod
    def check_id_exists(cls, scenario_id: str):
        """检查id是否存在"""
        connect = sqlite3.connect(
            Path(__file__).parent.parent.parent.parent.parent
            / "welding_app"
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
                res = res.fetchone()
                if not res:
                    raise ValueError("不存在符合该id的场景")
        finally:
            connect.close()
        return scenario_id


class QueryWeldingInformationInputModel(BaseModel):
    """tool query_welding_information input schema"""

    query: Annotated[
        str,
        Field(
            description="""查询内容,一个语义清晰，目的完整的句子

            <examples>
            <example>帮我查找电流与材料之间的关系</example>
            <example>焊接材料是铝，如何设置焊接电流</example>
            </examples>
            """
        ),
    ]


class GetWeldingScenarioInputModel(BaseModel):
    """tool get_welding_scenario input schema"""

    scenario_id: Annotated[
        str,
        Field(description="传入场景id，本工具会返回焊接场景对象"),
    ]

    @field_validator("scenario_id")
    @classmethod
    def check_id_exists(cls, scenario_id: str):
        """检查id是否存在"""
        connect = sqlite3.connect(
            Path(__file__).parent.parent.parent.parent.parent
            / "welding_app"
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
                res = res.fetchone()
                if not res:
                    raise ValueError("不存在符合该id的场景")
        finally:
            connect.close()
        return scenario_id


class WeldingSortTaskSummaryModel(BaseModel):
    """用于给 agent 做排序决策的轻量焊接任务摘要。"""

    task_id: Annotated[
        str,
        Field(
            description=(
                "线性焊接任务ID。agent 调整焊接顺序时只需要返回这些 task_id，"
                "不要返回完整焊接对象。"
            )
        ),
    ]
    task_type: Annotated[
        Literal["solder_joint", "sub_seam"],
        Field(description="任务类型：焊点或子焊缝段"),
    ]
    name: Annotated[str | None, Field(description="焊点名称或子焊缝任务名称")] = None
    parent_seam_id: Annotated[
        str | None, Field(description="子焊缝所属焊缝ID；焊点任务为空")
    ] = None
    position: Annotated[
        list[float] | None, Field(description="焊点坐标；子焊缝任务为空")
    ] = None
    start_position: Annotated[
        list[float] | None, Field(description="子焊缝起点坐标；焊点任务为空")
    ] = None
    end_position: Annotated[
        list[float] | None, Field(description="子焊缝终点坐标；焊点任务为空")
    ] = None
    base_material: Annotated[
        list[str] | None, Field(description="焊点或子焊缝起点材料信息")
    ] = None
    connected_parts: Annotated[
        list[str] | None, Field(description="焊点或子焊缝起点连接部件")
    ] = None


class WeldingSortPlanSummaryModel(BaseModel):
    """generate_welding_plan 返回给 agent 的轻量排序摘要。"""

    scenario_id: Annotated[str, Field(description="焊接场景ID")]
    initial_order_task_ids: Annotated[
        list[str], Field(description="算法生成的初始线性焊接任务顺序")
    ]
    tasks: Annotated[
        list[WeldingSortTaskSummaryModel],
        Field(description="用于排序决策的轻量任务清单"),
    ]
    instruction: Annotated[
        str,
        Field(
            description=(
                "下一步操作提示：agent 应将最终顺序的 task_id 列表传给 "
                "set_welding_task_order，而不是传完整排序模型。"
            )
        ),
    ]


class SetWeldingTaskOrderInputModel(BaseModel):
    """tool set_welding_task_order input schema"""

    ordered_task_ids: Annotated[
        list[str],
        Field(
            description=(
                "最终焊接任务顺序。必须只包含 generate_welding_plan 返回的 task_id，"
                "且不能重复、不能遗漏。"
            )
        ),
    ]
    welding_scenario_id: Annotated[
        str,
        Field(
            description="焊接方案对应的场景ID，必须与 generate_welding_plan 使用的场景一致"
        ),
    ]

    @field_validator("welding_scenario_id")
    @classmethod
    def check_id_exists(cls, scenario_id: str):
        """检查id是否存在"""
        connect = sqlite3.connect(
            Path(__file__).parent.parent.parent.parent.parent
            / "welding_app"
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
                res = res.fetchone()
                if not res:
                    raise ValueError("不存在符合该id的场景")
        finally:
            connect.close()
        return scenario_id


class CurrentState(Enum):
    START = "起始对象"
    END = "结束对象"
    MIDDLE = "中间对象"
    NONE = "无效对象"


class ShowCurrentWeldingObjectOutputModel(BaseModel):
    """tool show_current_welding_object output schema"""

    state: Annotated[
        CurrentState,
        Field(
            description="当前对象的状态，如果注意到当前对象是边界上的对象且仍然执行了超出边界的操作，那么当前对象不会改变"
        ),
    ]
    current_object: Annotated[
        SolderJointModel | tuple[SolderJointModel, SolderJointModel],
        Field(
            description="""当前对象
            可能是一个 solder joint 或者一个 solder joint 对
            - 如果是一个solder_joint则就是单纯的焊点，不存在parent_object
            - 如果是一个solder_joint对, 那么就是方向从第一个焊点到第二个焊点的短焊缝，会存在一个parent_object，也就是整体焊缝
            即使是一个焊缝，它的焊接也是分段的，这里的solder_joint对就是一个焊缝中的子分段"""
        ),
    ]
    parent_object_id: Annotated[
        str | None,
        Field(
            description="如果当前对象是焊点，则不存在该项；否则该项表示整体焊缝的id，通过id，你可以从整体的焊接场景中定位到这条焊缝"
        ),
    ]


class SetWeldingParamsInputModel(BaseModel):
    """根据焊接工艺对象的类型，设置焊接工艺参数"""

    process_params: ProcessParamsUnion


class SaveWeldingPlanInputModel(BaseModel):
    """保存焊接方案"""

    plan_name: Annotated[str, Field(description="名称焊接方案的名称，要求简短易识别")]
    scenario_id: Annotated[str, Field(description="焊接方案对应的场景ID")]

    @field_validator("scenario_id")
    @classmethod
    def check_id_exists(cls, scenario_id: str):
        """检查id是否存在"""
        connect = sqlite3.connect(
            Path(__file__).parent.parent.parent.parent.parent
            / "welding_app"
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
                res = res.fetchone()
                if not res:
                    raise ValueError("不存在符合该id的场景")
        finally:
            connect.close()
        return scenario_id


class SaveWeldingPlanOutputModel(BaseModel):
    """保存焊接方案的输出"""

    plan_id: Annotated[str, Field(description="保存成功后返回的焊接方案id")]


class WeldingPlanResult(BaseModel):
    """run_welding_plan_design 的返回值，包含焊接方案设计的最终结果"""

    plan_id: Annotated[
        str,
        Field(description="保存到数据库后获得的焊接方案唯一标识"),
    ]
    report: Annotated[
        str,
        Field(description="完整的设计报告，包含焊接顺序规划、工艺参数设计、参数选择依据等内容"),
    ]
