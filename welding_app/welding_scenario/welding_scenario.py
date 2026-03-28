from pydantic import BaseModel, Field

from .solder_joint import SolderJoint, SolderJointModel
from .weld_seam import WeldSeam, WeldSeamModel


class WeldingScenarioModel(BaseModel):
    solder_joints: list[SolderJointModel] = Field(default_factory=list)
    weld_seams: list[WeldSeamModel] = Field(default_factory=list)

    @classmethod
    def from_welding_scenario(cls, scenario: set) -> "WeldingScenarioModel":
        solder_joints = []
        weld_seams = []
        for item in scenario:
            if isinstance(item, SolderJoint):
                solder_joints.append(SolderJointModel.from_SolderJoint(item))
            elif isinstance(item, WeldSeam):
                weld_seams.append(WeldSeamModel.from_WeldSeam(item))
        return cls(solder_joints=solder_joints, weld_seams=weld_seams)

    def to_welding_scenario(self) -> set:
        result: set[SolderJoint | WeldSeam] = set()
        for sj in self.solder_joints:
            result.add(sj.to_SolderJoint())
        for ws in self.weld_seams:
            result.add(ws.to_WeldSeam())
        return result
