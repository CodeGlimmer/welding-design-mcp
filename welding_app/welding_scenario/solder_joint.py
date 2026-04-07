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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GeometryPoint):
            return False
        # 比较位置和ID
        return (
            self._x == other._x
            and self._y == other._y
            and self._z == other._z
            and self._id == other._id
        )

    def __hash__(self) -> int:
        # 使用位置和ID的哈希值
        position_hash = hash((self._x, self._y, self._z))
        id_hash = hash(self._id) if self._id is not None else 0
        return hash((position_hash, id_hash))


class GeometryPointModel(BaseModel):
    x: float = Field(..., description="点的x坐标")
    y: float = Field(..., description="点的y坐标")
    z: float = Field(..., description="点的z坐标")
    id: Optional[str] = Field(None, description="点的唯一标识")

    def __hash__(self) -> int:
        """为GeometryPointModel添加哈希支持"""
        # 使用坐标和ID的哈希值
        coord_hash = hash((self.x, self.y, self.z))
        id_hash = hash(self.id) if self.id is not None else 0
        return hash((coord_hash, id_hash))

    @classmethod
    def from_GeometryPoint(cls, point: GeometryPoint) -> "GeometryPointModel":
        return cls(x=point._x, y=point._y, z=point._z, id=point._id)

    def to_GeometryPoint(self) -> GeometryPoint:
        return GeometryPoint(self.x, self.y, self.z, self.id)


class SolderJoint(GeometryPoint):
    """焊点对象模型"""

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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SolderJoint):
            return False

        # 首先检查父类的相等性（位置和ID）
        if not super().__eq__(other):
            return False

        # 检查其他属性的相等性
        return (
            self._base_material == other._base_material
            and self._name == other._name
            and self._surface_normal == other._surface_normal
            and self._connected_parts == other._connected_parts
            and self._thicknss_combination == other._thicknss_combination
        )

    def __hash__(self) -> int:
        # 获取父类的哈希值
        parent_hash = super().__hash__()

        # 计算其他属性的哈希值
        base_material_hash = (
            tuple(material.value for material in self._base_material)
            if self._base_material
            else None
        )
        # 处理surface_normal字段，确保它是元组
        surface_normal_hash = None
        if self._surface_normal:
            # 如果surface_normal是列表，转换为元组
            if isinstance(self._surface_normal, list):
                surface_normal_hash = tuple(self._surface_normal)
            else:
                surface_normal_hash = self._surface_normal

        connected_parts_hash = (
            tuple(self._connected_parts) if self._connected_parts else None
        )
        thicknss_combination_hash = (
            tuple(self._thicknss_combination) if self._thicknss_combination else None
        )

        other_hash = hash(
            (
                base_material_hash,
                self._name,
                surface_normal_hash,
                connected_parts_hash,
                thicknss_combination_hash,
            )
        )

        return hash((parent_hash, other_hash))


class SolderJointModel(BaseModel):
    position: GeometryPointModel
    base_material: Optional[list[WeldingMaterialBIW]] = None
    name: Optional[str] = None
    surface_normal: Optional[tuple[float, float, float]] = None
    connected_parts: Optional[list[str]] = None
    thicknss_combination: Optional[list[float]] = None

    def __hash__(self) -> int:
        """为SolderJointModel添加哈希支持，使其可以用于集合"""
        # 安全地计算哈希值，处理各种可能的数据类型
        try:
            # 使用position的哈希值
            base_hash = hash(self.position) if self.position else 0

            # 安全地处理base_material
            base_material_hash = None
            if self.base_material:
                try:
                    # 处理枚举或字符串
                    material_values = []
                    for material in self.base_material:
                        if hasattr(material, "value"):
                            material_values.append(material.value)
                        else:
                            material_values.append(str(material))
                    base_material_hash = tuple(material_values)
                except Exception:
                    base_material_hash = None

            # 安全地处理surface_normal
            surface_normal_hash = None
            if self.surface_normal:
                try:
                    if isinstance(self.surface_normal, (list, tuple)):
                        # 列表或元组，转换为浮点数元组
                        surface_normal_hash = tuple(
                            float(x) for x in self.surface_normal[:3]
                        )
                    elif isinstance(self.surface_normal, dict):
                        # 字典，尝试提取数值
                        x = float(
                            self.surface_normal.get(
                                "x", self.surface_normal.get("0", 0.0)
                            )
                        )
                        y = float(
                            self.surface_normal.get(
                                "y", self.surface_normal.get("1", 0.0)
                            )
                        )
                        z = float(
                            self.surface_normal.get(
                                "z", self.surface_normal.get("2", 0.0)
                            )
                        )
                        surface_normal_hash = (x, y, z)
                    else:
                        # 其他类型，尝试转换为字符串然后哈希
                        surface_normal_hash = hash(str(self.surface_normal))
                except Exception:
                    surface_normal_hash = None

            # 安全地处理其他字段
            connected_parts_hash = None
            if self.connected_parts:
                try:
                    connected_parts_hash = tuple(
                        str(part) for part in self.connected_parts
                    )
                except Exception:
                    connected_parts_hash = None

            thicknss_combination_hash = None
            if self.thicknss_combination:
                try:
                    thicknss_combination_hash = tuple(
                        float(t) for t in self.thicknss_combination
                    )
                except Exception:
                    thicknss_combination_hash = None

            # 安全地处理name
            name_hash = hash(self.name) if self.name is not None else 0

            # 计算最终哈希值
            other_hash = hash(
                (
                    base_material_hash,
                    name_hash,
                    surface_normal_hash,
                    connected_parts_hash,
                    thicknss_combination_hash,
                )
            )

            return hash((base_hash, other_hash))

        except Exception:
            # 如果哈希计算失败，返回一个固定的哈希值
            # 这虽然会影响集合的去重功能，但至少不会崩溃
            return hash(("SolderJointModel", id(self)))

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
