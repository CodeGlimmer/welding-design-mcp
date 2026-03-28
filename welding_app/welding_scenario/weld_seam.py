from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from typing import Annotated, Literal, Optional, Union

import numpy as np
from pydantic import BaseModel, Field

from .solder_joint import (
    GeometryPoint,
    GeometryPointModel,
    SolderJoint,
    SolderJointModel,
)


class GeometryLine(ABC):
    @property
    @abstractmethod
    def start_point(self) -> GeometryPoint:
        """线的起点"""
        pass

    @property
    @abstractmethod
    def end_point(self) -> GeometryPoint:
        """线的终点"""
        pass

    @property
    @abstractmethod
    def is_closed(self) -> bool:
        """线是否闭合"""
        pass

    @abstractmethod
    def trave_on_line(self, num: int) -> Iterable[GeometryPoint]:
        """返回一个遍历该线的迭代器，迭代方法默认从start到end

        Args:
            num (int): 遍历的点数
        """
        pass

    @property
    @abstractmethod
    def length(self) -> float:
        """线的长度"""
        pass


class StraightLineIterator:
    def __init__(
        self, start_point: GeometryPoint, end_point: GeometryPoint, points_num: int
    ):
        if points_num < 2:
            raise ValueError("points_num 需要满足大于等于2的条件")
        self._start_point = start_point
        self._end_point = end_point
        self._points_num = points_num

    def __iter__(self) -> Iterator[GeometryPoint]:
        start_x, start_y, start_z = self._start_point.position
        end_x, end_y, end_z = self._end_point.position
        x = np.linspace(start_x, end_x, self._points_num)
        y = np.linspace(start_y, end_y, self._points_num)
        z = np.linspace(start_z, end_z, self._points_num)
        for i in range(self._points_num):
            yield GeometryPoint(x[i], y[i], z[i])


class GeometryStraightLine(GeometryLine):
    def __init__(
        self, start_point: GeometryPoint, end_point: GeometryPoint, id: Optional[str]
    ):
        self._start_point = start_point
        self._end_point = end_point
        self._id = id

    @property
    def start_point(self) -> GeometryPoint:
        return self._start_point

    @property
    def end_point(self) -> GeometryPoint:
        return self._end_point

    @property
    def is_closed(self) -> bool:
        return False

    @property
    def length(self) -> float:
        """线的长度"""
        return self._end_point.distance_to(self._start_point)

    def trave_on_line(self, num: int) -> Iterable[GeometryPoint]:
        return StraightLineIterator(self._start_point, self._end_point, num)

    @classmethod
    def from_points(
        cls,
        points: list[GeometryPoint],
        id: Optional[str] = None,
    ) -> "GeometryStraightLine":
        """从点列表创建直线，使用第一个和最后一个点"""
        if len(points) < 2:
            raise ValueError("至少需要两个点来创建直线")
        return cls(
            start_point=points[0],
            end_point=points[-1],
            id=id,
        )

    def distance_to_line(self, point: GeometryPoint) -> float:
        """计算点到直线的距离

        Args:
            point: 要计算距离的点

        Returns:
            float: 点到直线的距离
        """
        # 获取点的坐标
        x, y, z = point.position

        # 获取直线起点和终点的坐标
        start_x, start_y, start_z = self._start_point.position
        end_x, end_y, end_z = self._end_point.position

        # 计算向量
        # 直线方向向量
        line_vec = np.array([end_x - start_x, end_y - start_y, end_z - start_z])

        # 点到直线起点的向量
        point_to_start_vec = np.array([x - start_x, y - start_y, z - start_z])

        # 计算点到直线的距离
        # 距离 = |(point_to_start_vec) × line_vec| / |line_vec|
        # 其中 × 表示叉积

        # 计算叉积
        cross_product = np.cross(point_to_start_vec, line_vec)

        # 计算叉积的模（长度）
        cross_norm = np.linalg.norm(cross_product)

        # 计算直线方向向量的模
        line_norm = np.linalg.norm(line_vec)

        # 避免除以零（如果直线长度为0，则起点和终点重合）
        if line_norm < 1e-10:
            # 如果直线长度为0，则距离就是点到起点的距离
            distance = np.linalg.norm(point_to_start_vec)
        else:
            # 计算点到直线的距离
            distance = cross_norm / line_norm

        return distance  # type: ignore

    def check_point_on_line(self, point: GeometryPoint, tol: float) -> bool:
        """检查点是否在直线上（考虑容忍度）

        Args:
            point: 要检查的点
            tol: 容忍度，点到直线的最大允许距离

        Returns:
            bool: 如果点到直线的距离小于等于容忍度，返回True，否则返回False
        """
        # 计算点到直线的距离
        distance = self.distance_to_line(point)

        # 检查距离是否在容忍度范围内
        return distance <= tol

    def check_point_on_segment(self, point: GeometryPoint, tol: float) -> bool:
        """检查点是否在线段上（考虑容忍度）

        不仅检查点到直线的距离，还检查点是否在线段范围内

        Args:
            point: 要检查的点
            tol: 容忍度，点到直线的最大允许距离

        Returns:
            bool: 如果点到直线的距离小于等于容忍度且点在线段范围内，返回True，否则返回False
        """
        # 首先检查点到直线的距离
        if not self.check_point_on_line(point, tol):
            return False

        # 获取点的坐标
        x, y, z = point.position

        # 获取直线起点和终点的坐标
        start_x, start_y, start_z = self._start_point.position
        end_x, end_y, end_z = self._end_point.position

        # 计算向量
        line_vec = np.array([end_x - start_x, end_y - start_y, end_z - start_z])
        point_to_start_vec = np.array([x - start_x, y - start_y, z - start_z])

        # 计算点在线段上的投影参数 t
        # t = (point_to_start_vec · line_vec) / (line_vec · line_vec)
        line_norm_squared = np.dot(line_vec, line_vec)

        # 避免除以零
        if line_norm_squared < 1e-20:
            # 如果线段长度为0，检查点是否与起点/终点重合
            return np.linalg.norm(point_to_start_vec) <= tol  # type: ignore

        t = np.dot(point_to_start_vec, line_vec) / line_norm_squared

        # 检查t是否在[0, 1]范围内（考虑容忍度）
        # 添加一个小缓冲，因为点可能稍微超出线段端点但在容忍度范围内
        buffer = tol / (np.sqrt(line_norm_squared) + 1e-10)
        return -buffer <= t <= 1 + buffer


class GeometryStraightLineModel(BaseModel):
    type_flag: Literal["GeometryStraightLine"] = "GeometryStraightLine"
    start_point: GeometryPointModel
    end_point: GeometryPointModel
    id: str

    @classmethod
    def from_GeometryStraightLine(
        cls, line: GeometryStraightLine
    ) -> "GeometryStraightLineModel":
        return cls(
            start_point=GeometryPointModel.from_GeometryPoint(line.start_point),
            end_point=GeometryPointModel.from_GeometryPoint(line.end_point),
            id=line._id if line._id else "",
        )

    def to_GeometryStraightLine(self) -> GeometryStraightLine:
        start_point = self.start_point.to_GeometryPoint()
        end_point = self.end_point.to_GeometryPoint()
        return GeometryStraightLine(
            start_point=start_point,
            end_point=end_point,
            id=self.id,
        )


class WeldSeam:
    # TODO: 完成焊缝建模
    def __init__(
        self,
        line: GeometryLine,
        solder_joints: Optional[set[SolderJoint]] = None,  # 焊缝上的控制点，用于定位
        id: str | None = None,
        name: str | None = None,
    ):
        """焊缝类，包含几何的线与定位的焊点集合"""
        self._line = line
        self._solder_joints = solder_joints
        self._name = name
        self._id = id

    def __repr__(self) -> str:
        """返回WeldSeam的字符串表示"""
        return f"WeldSeam(id={self._id}, name={self._name}, length={self.get_seam_length()}, solder_joints={self.get_solder_joints_num()})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WeldSeam):
            return False

        # 主要比较ID，如果ID相同则认为是同一个焊缝
        return self._id == other._id

    def __hash__(self) -> int:
        # 主要使用ID的哈希值
        return hash(self._id) if self._id is not None else hash(id(self))

    def get_solder_joints_num(self) -> int:
        """获取焊缝上的焊点数量"""
        return len(self._solder_joints) if self._solder_joints else 0

    def get_seam_length(self) -> float:
        """获取焊缝长度"""
        return self._line.length


class WeldSeamModel(BaseModel):
    id: Optional[str]
    name: Optional[str]
    line: Annotated[
        # NOTE: 如果添加新的线型，在此处添加，并移除None
        Union[GeometryStraightLineModel, None], Field(discriminator="type_flag")
    ]
    solder_joints: list[SolderJointModel]

    @classmethod
    def from_WeldSeam(cls, seam: WeldSeam) -> "WeldSeamModel":
        # 转换几何线
        line_model = None
        if isinstance(seam._line, GeometryStraightLine):
            line_model = GeometryStraightLineModel.from_GeometryStraightLine(seam._line)

        # 转换焊点集合
        solder_joint_models = []
        if seam._solder_joints:
            for solder_joint in seam._solder_joints:
                solder_joint_models.append(
                    SolderJointModel.from_SolderJoint(solder_joint)
                )

        return cls(
            id=seam._id,
            name=seam._name,
            line=line_model,
            solder_joints=solder_joint_models,
        )

    def to_WeldSeam(self) -> WeldSeam:
        # 转换几何线
        if self.line and isinstance(self.line, GeometryStraightLineModel):
            geometry_line = self.line.to_GeometryStraightLine()
        else:
            # 从焊点列表生成默认线段
            if not self.solder_joints:
                raise ValueError("焊缝既没有几何线又没有焊点，无法创建")

            # 将 SolderJointModel 转换为 GeometryPoint
            points = []
            for sj_model in self.solder_joints:
                points.append(sj_model.position.to_GeometryPoint())

            geometry_line = GeometryStraightLine.from_points(points)

        # 转换焊点集合
        solder_joint_objects = set()
        for solder_joint_model in self.solder_joints:
            solder_joint_objects.add(solder_joint_model.to_SolderJoint())

        return WeldSeam(
            line=geometry_line,
            solder_joints=solder_joint_objects,
            id=self.id,
            name=self.name,
        )
