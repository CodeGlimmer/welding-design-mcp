from typing import Annotated, Any, Dict, Optional, Union

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

    process_type: WeldingProcessType = WeldingProcessType.SPOT_WELDING
    current_ka: float = Field(..., description="焊接电流 (kA)")
    pressure_kn: float = Field(..., description="电极压力 (kN)")
    weld_time_ms: int = Field(..., description="焊接时间 (ms)")
    pre_pressure_time_ms: Optional[int] = Field(None, description="预压时间")
    hold_time_ms: Optional[int] = Field(None, description="维持时间")


class ContinuousWeldingParams(BaseProcessParams):
    """连续焊工艺参数（适用于弧焊、激光焊）"""

    voltage_v: float = Field(..., description="焊接电压 (V)")
    current_a: float = Field(..., description="焊接电流 (A)")
    speed_mms: float = Field(..., description="焊接速度 (mm/s)")
    wire_feed_speed_mmin: Optional[float] = Field(None, description="送丝速度 (m/min)")
    gas_flow_lmin: Optional[float] = Field(None, description="保护气流量 (L/min)")


# 使用 Union 组合多态参数
ProcessParamsUnion = Annotated[
    Union[SpotWeldingParams, ContinuousWeldingParams],
    Field(discriminator="process_type"),
]


class ProcessAssignmentModel(BaseModel):
    """工艺分配记录：将工艺参数映射到具体的几何实体"""

    entity_id: str = Field(..., description="对应的 SolderJoint 或 WeldSeam 的 ID")
    params: ProcessParamsUnion = Field(..., description="具体的工艺参数内容")
