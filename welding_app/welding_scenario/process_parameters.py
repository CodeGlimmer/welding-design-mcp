from typing import Annotated, Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, Field

from .materials import WeldingProcessType


class WeldingEquipmentModel(BaseModel):
    """焊接设备模型（可选扩展）"""

    equipment_id: str = Field(..., description="设备唯一标识")
    model_name: Optional[str] = Field(None, description="设备型号")
    brand: Optional[str] = Field(None, description="品牌")
    specifications: Dict[str, Any] = Field(
        default_factory=dict, description="硬件详细规格"
    )


class BaseProcessParams(BaseModel):
    """工艺参数基类"""

    process_type: WeldingProcessType = Field(..., description="工艺类型")
    equipment: Optional[WeldingEquipmentModel] = Field(
        None, description="绑定的焊接设备"
    )
    extra_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="扩展属性，用于存储不同厂家或特殊需求的非标参数",
    )


class SpotWeldingParams(BaseProcessParams):
    """点焊工艺参数"""

    type_flag: Literal["spot_welding"] = Field(..., description="工艺类型标识")
    process_type: WeldingProcessType = WeldingProcessType.SPOT_WELDING
    current_ka: Annotated[
        float,
        Field(
            default=8.0,
            description="焊接电流，单位：千安 (kA)，常见范围 2-15 kA（视材料厚度而定）",
        ),
    ]
    pressure_kn: Annotated[
        float,
        Field(
            default=3.0,
            description="电极压力，单位：千牛 (kN)，常见范围 1-6 kN",
        ),
    ]
    weld_time_ms: Annotated[
        int,
        Field(
            default=200,
            description="焊接时间（通电时间），单位：毫秒 (ms)，常见范围 100-500 ms",
        ),
    ]
    pre_pressure_time_ms: Annotated[
        Optional[int],
        Field(
            default=100,
            description="预压时间（电极接触工件到通电前的时间），单位：毫秒 (ms)",
        ),
    ]
    hold_time_ms: Annotated[
        Optional[int],
        Field(
            default=150,
            description="维持时间（断电后电极保持压力的时间），单位：毫秒 (ms)",
        ),
    ]


class ContinuousWeldingParams(BaseProcessParams):
    """连续焊工艺参数（适用于弧焊、激光焊）"""

    type_flag: Literal["continuous_welding"] = Field(..., description="工艺类型标识")
    voltage_v: Annotated[
        float,
        Field(
            default=22.0,
            description="焊接电压，单位：伏特 (V)，常见范围 18-32 V",
        ),
    ]
    current_a: Annotated[
        float,
        Field(
            default=180.0,
            description="焊接电流，单位：安培 (A)，常见范围 80-300 A",
        ),
    ]
    speed_mms: Annotated[
        float,
        Field(
            default=5.0,
            description="焊接速度，单位：毫米/秒 (mm/s)，常见范围 2-15 mm/s",
        ),
    ]
    wire_feed_speed_mmin: Annotated[
        Optional[float],
        Field(
            default=6.0,
            description="送丝速度，单位：米/分钟 (m/min)，常见范围 3-12 m/min",
        ),
    ]
    gas_flow_lmin: Annotated[
        Optional[float],
        Field(
            default=15.0,
            description="保护气流量，单位：升/分钟 (L/min)，常见范围 10-25 L/min",
        ),
    ]


# 使用 Union 组合多态参数
ProcessParamsUnion = Annotated[
    Union[SpotWeldingParams, ContinuousWeldingParams],
    Field(discriminator="type_flag"),
]


class ProcessAssignmentModel(BaseModel):
    """工艺分配记录：将工艺参数映射到具体的几何实体"""

    entity_id: str = Field(..., description="对应的 SolderJoint 或 WeldSeam 的 ID")
    params: ProcessParamsUnion = Field(..., description="具体的工艺参数内容")
