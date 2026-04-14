from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .process_parameters import ProcessAssignmentModel
from .weld_sequence_plan import WeldingSequenceSortModel
from .welding_scenario import WeldingScenarioModel


class WeldingPlanModel(BaseModel):
    """焊接方案完整对象模型"""

    model_config = ConfigDict(
        validate_assignment=True, populate_by_name=True
    )  # 允许动态修改，并同步提供检查

    plan_id: str = Field(..., description="方案唯一标识")
    name: Optional[str] = Field(None, description="方案名称")

    # 1. 静态环境：包含所有焊点、焊缝几何信息
    scenario: WeldingScenarioModel = Field(..., description="焊接场景上下文")

    # 2. 动态顺序：定义焊接的先后执行逻辑
    sequence: WeldingSequenceSortModel = Field(..., description="焊接顺序规划结果")

    # 3. 工艺映射：定义每个实体具体的焊接参数
    process_assignments: List[ProcessAssignmentModel] = Field(
        default_factory=list, description="工艺参数分配表"
    )

    @model_validator(mode="after")
    def validate_entity_ids_exist(self) -> "WeldingPlanModel":
        """
        逻辑校验：确保工艺分配表中的 entity_id 在场景中真实存在
        """
        # 提取场景中所有焊点和焊缝的 ID
        existing_ids = {
            sj.position.id for sj in self.scenario.solder_joints if sj.position.id
        }
        existing_ids.update({ws.id for ws in self.scenario.weld_seams if ws.id})

        for assignment in self.process_assignments:
            if assignment.entity_id not in existing_ids:
                raise ValueError(
                    f"工艺参数指向了不存在的实体 ID: {assignment.entity_id}"
                )
        return self

    def get_params_by_entity_id(
        self, entity_id: str
    ) -> Optional[ProcessAssignmentModel]:
        """工具方法：根据实体ID快速获取对应的工艺参数"""
        for assignment in self.process_assignments:
            if assignment.entity_id == entity_id:
                return assignment
        return None
