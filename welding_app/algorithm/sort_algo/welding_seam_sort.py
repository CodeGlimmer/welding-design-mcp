from dataclasses import dataclass
import enum

from .solder_joint_sort import sort_solder_joints


def sort_welding_seam(
    welding_seams: dict[
        int,
        tuple[tuple[float, float, float], tuple[float, float, float]]
    ]
) -> list[int]:
    '''焊缝排序算法
    
    基本参照焊点排序算法，使用焊缝的中点坐标代替焊缝，按照最小热集中的优化指标，使用遗传算法进行优化

    Args:
        welding_seams: 焊缝，使用直线模型，记录起点与终点坐标
    
    Returns:
        best_sort: 最佳焊缝排序
    '''

    # 建立从焊缝到中点的映射关系
    welding_seam_middle_point = dict()
    for key in welding_seams:
        point_pair = welding_seams[key]
        welding_seam_middle_point[key] = (
            (point_pair[0][0] + point_pair[1][0]) / 2,
            (point_pair[0][1] + point_pair[1][1]) / 2,
            (point_pair[0][2] + point_pair[1][2]) / 2,
        )
    
    # 调用焊点排序算法
    best_sort, _, _ = sort_solder_joints(welding_seam_middle_point)
    return list(best_sort)


def sort_by_axis(solder_joints: list[tuple[float, float, float]], axis: int) -> list[int]:
    # 建立映射表
    position_to_idx_map = dict()
    for idx, position in enumerate(solder_joints):
        position_to_idx_map[position] = idx
        idx += 1
    # 排序，返回排序后的idx
    sorted_solder_joints = sorted(solder_joints, key=lambda pos: pos[axis])
    sorted_idx = []
    for joints in solder_joints:
        sorted_idx.append(position_to_idx_map[joints])
    return sorted_idx

def design_single_welding_seam_sort(
    solder_joints: list[tuple[float, float, float]]
) -> list[tuple[int, int]]:
    '''根据固定点将焊缝分为多段进行焊接，同时给出每段的焊接顺序'''

    if len(solder_joints) == 2:
        # 如果只有两个焊点，就无所谓顺序
        return [(0, 1)]

    # step1: 选择一个变化的坐标轴(变化率最大，即坐标差最大)
    delta_x = abs(solder_joints[0][0] - solder_joints[1][0])
    delta_y = abs(solder_joints[0][1] - solder_joints[1][1])
    delta_z = abs(solder_joints[0][2] - solder_joints[1][2])
    axis = 0
    if delta_x >= delta_y and delta_x >= delta_z:
        axis = 0
    elif delta_y >= delta_x and delta_y >= delta_z:
        axis = 1
    else: 
        axis = 2
    
    # step2: 在给定的坐标轴上对坐标的数值进行排序
    sorted_idx = sort_by_axis(solder_joints, axis)

    # step3: 划分
    devides = []
    for idx in range(len(solder_joints) - 1):
        devides.append((sorted_idx[idx+1], sorted_idx[idx]))
    
    return devides
