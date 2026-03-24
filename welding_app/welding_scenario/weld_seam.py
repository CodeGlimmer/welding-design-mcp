from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from enum import Enum
from typing import Optional

import numpy as np

from .solder_joint import GeometryPoint, SolderJoint


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

    def trave_on_line(self, num: int) -> Iterable[GeometryPoint]:
        return StraightLineIterator(self._start_point, self._end_point, num)

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


class Direction(Enum):
    START_TO_END = 0
    END_TO_START = 1


class WeldSeam:
    # TODO: 完成焊缝建模
    def __init__(
        self,
        line: GeometryLine,
        solder_joints: Optional[set[SolderJoint]] = None,
    ):
        """焊缝类，包含几何的线与定位的焊点集合"""
        self._line = line
        self._solder_joints = solder_joints
