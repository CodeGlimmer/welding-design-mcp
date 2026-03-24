from typing import Optional


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


class SolderJoint(GeometryPoint):
    """焊点对象模型"""

    # TODO: 补充关于焊点的相关内容，以借此实现焊接参数的选择
    def __init__(
        self,
        x: float,
        y: float,
        z: float,
        id: str,  # 焊点是必须记录的，所有不可以为空
        parent_id: str,
    ):
        super().__init__(x, y, z, id)
