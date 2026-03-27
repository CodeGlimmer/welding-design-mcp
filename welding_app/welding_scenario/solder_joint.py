from typing import Optional, cast

from pydantic import BaseModel, Field

from .materials import WeldingMaterialBIW


class GeometryPoint:
    def __init__(self, x: float, y: float, z: float, id: Optional[str] = None):
        """点模型对象

        Args:
            x (float): 点的x坐标
            y (float): 点的y坐标
            z (float): 点的z坐标
            id (Optional[str]): 点的唯一标识，默认为None, 如果该点没有记录的价值比如一些插值点，那么就不必添加id
        """
        self._x = x
        self._y = y
        self._z = z
        self._id = id

    @property
    def id(self) -> str | None:
        return self._id

    @property
    def position(self) -> tuple[float, float, float]:
        return (self._x, self._y, self._z)

    def distance_to(self, other: "GeometryPoint") -> float:
        dx = self._x - other._x
        dy = self._y - other._y
        dz = self._z - other._z
        return (dx**2 + dy**2 + dz**2) ** 0.5


class GeometryPointModel(BaseModel):
    x: float = Field(..., description="点的x坐标")
    y: float = Field(..., description="点的y坐标")
    z: float = Field(..., description="点的z坐标")
    id: Optional[str] = Field(None, description="点的唯一标识")

    @classmethod
    def from_GeometryPoint(cls, point: GeometryPoint) -> "GeometryPointModel":
        return cls(x=point._x, y=point._y, z=point._z, id=point._id)

    def to_GeometryPoint(self) -> GeometryPoint:
        return GeometryPoint(self.x, self.y, self.z, self.id)


class SolderJoint(GeometryPoint):
    """焊点对象模型"""

    # TODO: 补充关于焊点的相关内容，以借此实现焊接参数的选择
    def __init__(
        self,
        x: float,
        y: float,
        z: float,
        id: str,  # 焊点是必须记录的，所有不可以为空
        base_material: list[WeldingMaterialBIW] | None = None,  # 母材
        name: str | None = None,  # 焊点名称
        surface_normal: tuple[float, float, float] | None = None,  # 表面法线
        connected_parts: list[str] | None = None,  # 连接的部件
        thicknss_combination: list[float] | None = None,  # 厚度组合
    ):
        super().__init__(x, y, z, id)
        self._base_material = base_material
        self._name = name
        self._surface_normal = surface_normal
        self._connected_parts = connected_parts
        self._thicknss_combination = thicknss_combination


class SolderJointModel(BaseModel):
    position: GeometryPointModel
    base_material: Optional[list[WeldingMaterialBIW]] = None
    name: Optional[str] = None
    surface_normal: Optional[tuple[float, float, float]] = None
    connected_parts: Optional[list[str]] = None
    thicknss_combination: Optional[list[float]] = None

    @classmethod
    def from_SolderJoint(cls, joint: SolderJoint) -> "SolderJointModel":
        return cls(
            position=GeometryPointModel.from_GeometryPoint(joint),
            base_material=joint._base_material,
            name=joint._name,
            surface_normal=joint._surface_normal,
            connected_parts=joint._connected_parts,
            thicknss_combination=joint._thicknss_combination,
        )

    def to_SolderJoint(self) -> SolderJoint:
        return SolderJoint(
            x=self.position.x,
            y=self.position.y,
            z=self.position.z,
            id=cast(str, self.position.id),
            base_material=self.base_material,
            name=self.name,
            surface_normal=self.surface_normal,
            connected_parts=self.connected_parts,
            thicknss_combination=self.thicknss_combination,
        )
