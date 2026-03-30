import numpy as np


def caculate_fitness_by_heat(
    sorted_points: list[int] | np.ndarray, points: dict[int, tuple[float, float, float]]
) -> float:
    """计算焊接顺序的热集中度适应度, 越小越好"""
    epsilon = 1e-6  # 避免除0错误
    fitness = 0.0
    for i in range(len(sorted_points) - 1):
        fitness += 1 / (
            (
                (points[sorted_points[i]][0] - points[sorted_points[i + 1]][0]) ** 2
                + (points[sorted_points[i]][1] - points[sorted_points[i + 1]][1]) ** 2
                + (points[sorted_points[i]][2] - points[sorted_points[i + 1]][2]) ** 2
            )
            ** 0.5
            + epsilon
        )
    return fitness


# TODO: 完成该适应度函数的设计
# def caculate_fitness_by_symmetry(
#     sorted_points: list[int], points: dict[int, tuple[float, float, float]]
# ) -> float:
#     """计算焊接顺序的对称性适应度, 越小越好"""
#     pass
