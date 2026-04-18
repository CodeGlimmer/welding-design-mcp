"""焊点焊接顺序排序算法

- 依据遗传算法对焊点集合进行排序，对热集中度进行优化
- 支持自适应突变率（根据种群多样性动态调整）
- 返回迭代过程中最优适应度用于绘图
- 改进：贪心初始化、PMX交叉、逆转变异、更大种群
- v2：加强边界条件与异常处理
"""

from typing import Optional, Tuple

import numpy as np
from numpy.typing import NDArray

# ---------------------------------------------------------------------------
# 参数校验辅助函数
# ---------------------------------------------------------------------------


def _validate_points(points: dict) -> None:
    """校验焊点字典格式。

    Raises:
        TypeError:  points 不是 dict，或坐标不是长度为 3 的可迭代对象
        ValueError: 坐标中包含非有限数值（NaN / inf）
    """
    if not isinstance(points, dict):
        raise TypeError(f"points 必须是 dict，当前类型: {type(points).__name__}")

    for key, val in points.items():
        try:
            coords = tuple(val)
        except TypeError:
            raise TypeError(f"焊点 {key!r} 的坐标必须是可迭代对象，当前值: {val!r}")

        if len(coords) != 3:
            raise ValueError(
                f"焊点 {key!r} 的坐标长度必须为 3，当前长度: {len(coords)}"
            )

        for idx, c in enumerate(coords):
            if not np.isfinite(c):
                raise ValueError(f"焊点 {key!r} 的第 {idx} 个坐标包含非有限值: {c}")


def _validate_positive_int(value: int, name: str) -> None:
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} 必须是正整数，当前值: {value!r}")


def _validate_rate(value: float, name: str) -> None:
    if not (0.0 <= value <= 1.0):
        raise ValueError(f"{name} 必须在 [0, 1] 范围内，当前值: {value!r}")


# ---------------------------------------------------------------------------
# 核心计算函数
# ---------------------------------------------------------------------------


def caculate_fitness_by_heat(
    sorted_points: list[int] | np.ndarray,
    points: dict[int, tuple[float, float, float]],
) -> float:
    """计算焊接顺序的热集中度。

    热集中度 = 相邻两个焊点距离的倒数之和，越小越好。

    边界处理：
    - 空序列或单焊点 → 返回 0.0（无相邻对，热集中度为零）
    - 两焊点完全重合 → 距离趋近于 0，用 epsilon 防止除零

    Args:
        sorted_points: 排序后的焊点索引列表
        points: 焊点坐标字典

    Returns:
        热集中度值，越小越好
    """
    if len(sorted_points) <= 1:
        return 0.0

    epsilon = 1e-6
    heat_concentration = 0.0

    for i in range(len(sorted_points) - 1):
        pid1, pid2 = sorted_points[i], sorted_points[i + 1]

        if pid1 not in points:
            raise KeyError(f"焊点索引 {pid1!r} 不存在于 points 字典中")
        if pid2 not in points:
            raise KeyError(f"焊点索引 {pid2!r} 不存在于 points 字典中")

        p1, p2 = points[pid1], points[pid2]
        dist = (
            (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2
        ) ** 0.5
        heat_concentration += 1.0 / (dist + epsilon)

    return heat_concentration


def calculate_population_diversity(population: NDArray) -> float:
    """计算种群多样性（平均汉明距离）——向量化版本。

    边界处理：
    - 空种群 → 返回 0.0
    - 单个体 → 返回 0.0（无法比较）
    - 单基因位 → 汉明距离归一化为 0 或 1

    Args:
        population: 形状 (N, n) 的整数数组

    Returns:
        平均汉明距离，取值 [0, 1]
    """
    if population.ndim != 2:
        raise ValueError(f"population 必须是二维数组，当前维度: {population.ndim}")

    population_size, n = population.shape

    if population_size <= 1 or n == 0:
        return 0.0

    expanded1 = population[:, np.newaxis, :]  # (N, 1, n)
    expanded2 = population[np.newaxis, :, :]  # (1, N, n)

    hamming_matrix = np.sum(expanded1 != expanded2, axis=2) / n  # (N, N)

    upper_tri = np.triu(hamming_matrix, k=1)
    pair_count = population_size * (population_size - 1) / 2
    avg_hamming = np.sum(upper_tri) / pair_count

    return float(avg_hamming)


def greedy_initialize(
    points: dict[int, tuple[float, float, float]],
    num_individuals: int,
) -> list[NDArray]:
    """贪心初始化：从随机起点出发，每次选最近未访问焊点生成个体。

    边界处理：
    - n == 0 → 返回空列表
    - n == 1 → 每个个体直接是唯一焊点的数组
    - num_individuals == 0 → 返回空列表
    - num_individuals 超过可用起点数时，剩余个体用随机扰动补齐

    Args:
        points: 焊点坐标字典
        num_individuals: 要生成的个体数量

    Returns:
        生成的个体列表，每个元素是长度 n 的 NDArray
    """
    n = len(points)
    if n == 0 or num_individuals == 0:
        return []

    point_ids = list(points.keys())

    # 单焊点特殊处理
    if n == 1:
        return [np.array(point_ids) for _ in range(num_individuals)]

    # 预计算距离矩阵
    coords = np.array([points[pid] for pid in point_ids], dtype=float)  # (n, 3)
    dist_matrix = np.sqrt(
        np.sum((coords[:, np.newaxis, :] - coords[np.newaxis, :, :]) ** 2, axis=2)
    )

    individuals: list[NDArray] = []

    # 1. 纯贪心解（从不同起点出发）
    greedy_count = min(num_individuals // 2, n)
    for start_idx in range(greedy_count):
        visited_mask = np.zeros(n, dtype=bool)
        order_indices: list[int] = [start_idx]
        visited_mask[start_idx] = True

        current = start_idx
        for _ in range(n - 1):
            row = dist_matrix[current].copy()
            row[visited_mask] = np.inf
            nearest = int(np.argmin(row))
            order_indices.append(nearest)
            visited_mask[nearest] = True
            current = nearest

        individuals.append(np.array([point_ids[i] for i in order_indices]))

    # 2. 贪心 + 随机扰动（补齐剩余数量）
    while len(individuals) < num_individuals:
        start = np.random.randint(n)
        visited_mask = np.zeros(n, dtype=bool)
        order_indices = [start]
        visited_mask[start] = True

        current = start
        for _ in range(n - 1):
            row = dist_matrix[current].copy()
            row[visited_mask] = np.inf
            min_dist = np.min(row)

            # 候选：距离在最短距离 1.5 倍以内
            candidates = np.where(row <= min_dist * 1.5)[0]
            chosen = int(np.random.choice(candidates))

            order_indices.append(chosen)
            visited_mask[chosen] = True
            current = chosen

        individuals.append(np.array([point_ids[i] for i in order_indices]))

    return individuals


def sort_solder_joints(
    points: dict[int, tuple[float, float, float]],
    population_size: int = 200,
    num_generations: int = 300,
    base_mutation_rate: float = 0.15,
    diversity_threshold: float = 0.15,
    mutation_boost_factor: float = 5.0,
    tournament_size: int = 5,
    random_seed: Optional[int] = 42,
    patience: int = 20,
    elite_count: int = 2,
) -> Tuple[NDArray, float, NDArray]:
    """焊点焊接顺序排序（改进的遗传算法）。

    边界处理：
    - 空 points → 返回空数组、0.0、空历史
    - 单焊点 → 直接返回该焊点，热集中度 0.0
    - 两焊点 → 两种排列直接枚举，无需演化
    - population_size / elite_count 等参数做合法性校验
    - tournament_size 超过种群时自动收紧

    Args:
        points: 焊点坐标字典 {焊点ID: (x, y, z)}
        population_size: 种群大小（≥ 2）
        num_generations: 迭代代数（≥ 1）
        base_mutation_rate: 基础突变率，[0, 1]
        diversity_threshold: 多样性阈值，[0, 1]
        mutation_boost_factor: 收敛时突变率放大倍数（> 0）
        tournament_size: 锦标赛大小（≥ 2）
        random_seed: 随机种子（None 表示不固定）
        patience: 早停耐心值（≥ 1）
        elite_count: 精英保留数量（≥ 1，且 < population_size）

    Returns:
        Tuple[NDArray, float, NDArray]:
            - global_best: 全局最优焊接顺序（焊点 ID 数组）
            - global_best_fitness: 全局最优热集中度
            - best_fitness_history: 每代最优热集中度的历史记录
    """
    # ------------------------------------------------------------------
    # 参数校验
    # ------------------------------------------------------------------
    _validate_points(points)
    _validate_positive_int(population_size, "population_size")
    _validate_positive_int(num_generations, "num_generations")
    _validate_rate(base_mutation_rate, "base_mutation_rate")
    _validate_rate(diversity_threshold, "diversity_threshold")
    _validate_positive_int(patience, "patience")
    _validate_positive_int(elite_count, "elite_count")
    _validate_positive_int(tournament_size, "tournament_size")

    if mutation_boost_factor <= 0:
        raise ValueError(
            f"mutation_boost_factor 必须大于 0，当前值: {mutation_boost_factor!r}"
        )
    if elite_count >= population_size:
        raise ValueError(
            f"elite_count ({elite_count}) 必须小于 population_size ({population_size})"
        )

    # ------------------------------------------------------------------
    # 特殊规模快速返回
    # ------------------------------------------------------------------
    n = len(points)
    point_ids = list(points.keys())

    if n == 0:
        print("警告: points 为空，无焊点可排序，返回空结果。")
        return np.array([], dtype=int), 0.0, np.array([])

    if n == 1:
        print("警告: 仅有 1 个焊点，无需排序。")
        best = np.array(point_ids)
        return best, 0.0, np.array([0.0])

    if n == 2:
        print("警告: 仅有 2 个焊点，直接枚举最优顺序。")
        order_a = np.array(point_ids)
        order_b = np.array(point_ids[::-1])
        fitness_a = caculate_fitness_by_heat(order_a, points)
        fitness_b = caculate_fitness_by_heat(order_b, points)
        if fitness_a <= fitness_b:
            return order_a, fitness_a, np.array([fitness_a])
        else:
            return order_b, fitness_b, np.array([fitness_b])

    # ------------------------------------------------------------------
    # 参数自动修正（tournament_size 不能超过种群大小）
    # ------------------------------------------------------------------
    if tournament_size > population_size:
        print(
            f"警告: tournament_size ({tournament_size}) > population_size "
            f"({population_size})，自动收紧为 {population_size}。"
        )
        tournament_size = population_size

    if random_seed is not None:
        np.random.seed(random_seed)

    # ------------------------------------------------------------------
    # 种群初始化（贪心 + 随机混合）
    # ------------------------------------------------------------------
    greedy_individuals = greedy_initialize(points, population_size // 3)
    random_count = population_size - len(greedy_individuals)
    random_individuals = [np.random.permutation(n) for _ in range(random_count)]

    # greedy_initialize 返回的是 point_id 数组；
    # 遗传算子内部统一使用"位置索引 0..n-1"，最后再映射回 point_id。
    # 将贪心个体从 point_id 转换为位置索引：
    id_to_pos = {pid: pos for pos, pid in enumerate(point_ids)}
    greedy_as_pos = [
        np.array([id_to_pos[pid] for pid in ind]) for ind in greedy_individuals
    ]

    population: NDArray = np.array(greedy_as_pos + random_individuals)

    # 评估适应度的包装：内部 population 存位置索引，需映射回 point_id
    def _fitness_from_pos(pop: NDArray) -> NDArray:
        fitnesses = []
        for ind in pop:
            pid_order = [point_ids[i] for i in ind]
            fitnesses.append(caculate_fitness_by_heat(pid_order, points))
        return np.array(fitnesses)

    fitness = _fitness_from_pos(population)

    # ------------------------------------------------------------------
    # 演化主循环
    # ------------------------------------------------------------------
    global_best_individual: Optional[NDArray] = None
    global_best_fitness: float = np.inf
    no_improvement_count = 0
    best_fitness_history: list[float] = []

    for gen in range(num_generations):
        current_best_idx = int(np.argmin(fitness))
        current_best_fitness = float(fitness[current_best_idx])

        if current_best_fitness < global_best_fitness:
            global_best_fitness = current_best_fitness
            global_best_individual = population[current_best_idx].copy()
            no_improvement_count = 0
        else:
            no_improvement_count += 1

        best_fitness_history.append(global_best_fitness)

        # 早停
        if no_improvement_count >= patience:
            print(f"早停: 第 {gen + 1} 代（连续 {patience} 代无改善）")
            break

        # 自适应突变率
        current_diversity = calculate_population_diversity(population)
        decay_rate = base_mutation_rate * (1 - gen / num_generations) ** 0.5
        if current_diversity < diversity_threshold:
            adaptive_rate = decay_rate * mutation_boost_factor
        else:
            adaptive_rate = decay_rate
        adaptive_rate = float(np.clip(adaptive_rate, 0.01, 0.6))

        # 选择 → 交叉 → 变异 → 精英保留
        parents = natural_selection(
            population, fitness, population_size, tournament_size
        )
        offspring = pmx_crossover(parents, population_size - elite_count)
        offspring = inversion_mutation(offspring, adaptive_rate)
        elite = select_best(population, fitness, elite_count)
        population = np.vstack([offspring, elite])
        fitness = _fitness_from_pos(population)

        if (gen + 1) % 20 == 0:
            print(
                f"第 {gen + 1} 代 | 最优热集中度: {global_best_fitness:.6f} | "
                f"多样性: {current_diversity:.3f} | 突变率: {adaptive_rate:.3f}"
            )

    # 将位置索引映射回 point_id
    if global_best_individual is None:
        # 理论上不会到达这里，但做防御处理
        global_best_individual = population[int(np.argmin(fitness))].copy()
        global_best_fitness = float(np.min(fitness))

    best_order_ids = np.array([point_ids[i] for i in global_best_individual])  # type: ignore

    return best_order_ids, global_best_fitness, np.array(best_fitness_history)


# ---------------------------------------------------------------------------
# 遗传算子
# ---------------------------------------------------------------------------


def init_population(n: int, population_size: int) -> NDArray:
    """初始化随机种群。

    Args:
        n: 焊点数量
        population_size: 种群大小

    Returns:
        形状 (population_size, n) 的整数数组
    """
    if n <= 0:
        raise ValueError(f"n 必须是正整数，当前值: {n!r}")
    _validate_positive_int(population_size, "population_size")
    return np.array([np.random.permutation(n) for _ in range(population_size)])


def evaluate_fitness(
    population: NDArray,
    points: dict[int, tuple[float, float, float]],
) -> NDArray:
    """评估种群中每个个体的适应度。

    Args:
        population: 形状 (N, n) 的位置索引数组
        points: 焊点坐标字典

    Returns:
        形状 (N,) 的适应度数组
    """
    if population.ndim != 2:
        raise ValueError(f"population 必须是二维数组，当前维度: {population.ndim}")
    point_ids = list(points.keys())
    fitnesses = []
    for individual in population:
        pid_order = [point_ids[i] for i in individual]
        fitnesses.append(caculate_fitness_by_heat(pid_order, points))
    return np.array(fitnesses)


def natural_selection(
    population: NDArray,
    fitnesses: NDArray,
    num_parents: int,
    tournament_size: int = 5,
) -> NDArray:
    """锦标赛选择。

    边界处理：
    - tournament_size 超过种群时自动收紧，避免 replace=False 报错
    - num_parents 为 0 时返回空数组

    Args:
        population: 种群
        fitnesses: 热集中度（越小越好）
        num_parents: 选择的父代数量
        tournament_size: 锦标赛大小

    Returns:
        选择后的父代种群，形状 (num_parents, n)
    """
    pop_size = len(population)
    if pop_size == 0:
        raise ValueError("种群为空，无法进行选择")
    if num_parents == 0:
        return np.empty((0, population.shape[1]), dtype=population.dtype)

    # 自动收紧 tournament_size
    actual_tournament = min(tournament_size, pop_size)

    parents = []
    for _ in range(num_parents):
        tournament = np.random.choice(pop_size, actual_tournament, replace=False)
        winner = tournament[int(np.argmin(fitnesses[tournament]))]
        parents.append(population[winner])
    return np.array(parents)


def pmx_crossover(parents: NDArray, offspring_size: int) -> NDArray:
    """PMX（部分映射）交叉。

    边界处理：
    - offspring_size == 0 → 返回形状 (0, n) 的空数组
    - parents 少于 2 个时，直接复制 parents[0]（无法交叉）
    - n <= 1 时无法选两个不同的交叉点，直接复制父代

    Args:
        parents: 形状 (P, n) 的父代数组
        offspring_size: 子代数量

    Returns:
        形状 (offspring_size, n) 的子代数组
    """
    if parents.ndim != 2:
        raise ValueError(f"parents 必须是二维数组，当前维度: {parents.ndim}")
    n = parents.shape[1]

    if offspring_size == 0:
        return np.empty((0, n), dtype=parents.dtype)

    num_parents = len(parents)

    # n <= 1：基因序列太短，无法交叉，直接随机复制父代
    if n <= 1 or num_parents < 2:
        indices = np.random.randint(0, max(num_parents, 1), size=offspring_size)
        return (
            parents[indices].copy()
            if num_parents > 0
            else np.zeros((offspring_size, n), dtype=int)
        )

    offspring = []
    for _ in range(offspring_size):
        p1_pos, p2_pos = np.random.choice(num_parents, 2, replace=False)
        parent1, parent2 = parents[p1_pos], parents[p2_pos]

        cross_start = np.random.randint(0, n - 1)
        cross_end = np.random.randint(cross_start + 1, n)

        child = np.full(n, -1, dtype=int)
        child[cross_start:cross_end] = parent1[cross_start:cross_end]

        mapping: dict[int, int] = {}
        for i in range(cross_start, cross_end):
            mapping[parent1[i]] = parent2[i]

        segment_genes = set(child[cross_start:cross_end])
        pos_in_parent1 = {gene: i for i, gene in enumerate(parent1)}

        for i in range(n):
            if cross_start <= i < cross_end:
                continue
            gene = int(parent2[i])
            # 跟随映射链直到脱离 segment
            seen: set[int] = set()
            while gene in segment_genes:
                if gene in seen:
                    # 出现环，理论上不应发生，但做防御
                    break
                seen.add(gene)
                pos = pos_in_parent1.get(gene)
                if pos is not None and cross_start <= pos < cross_end:
                    gene = int(parent2[pos])
                else:
                    break
            child[i] = gene
            segment_genes.add(gene)

        offspring.append(child)

    return np.array(offspring)


def inversion_mutation(offspring: NDArray, mutation_rate: float) -> NDArray:
    """逆转变异：随机选择一段基因并反转。

    边界处理：
    - n <= 1：无可逆转片段，直接跳过
    - mutation_rate 超出 [0, 1] 时 clip 到合法范围

    Args:
        offspring: 形状 (M, n) 的子代数组
        mutation_rate: 变异概率

    Returns:
        变异后的子代数组（in-place 修改后返回）
    """
    mutation_rate = float(np.clip(mutation_rate, 0.0, 1.0))

    for i in range(len(offspring)):
        n = len(offspring[i])
        if n <= 1:
            continue  # 单基因无法逆转
        if np.random.rand() < mutation_rate:
            pos1 = np.random.randint(0, n - 1)
            pos2 = np.random.randint(pos1 + 1, n)
            offspring[i, pos1:pos2] = offspring[i, pos1:pos2][::-1]

    return offspring


def select_best(population: NDArray, fitnesses: NDArray, num_parents: int) -> NDArray:
    """选择热集中度最低的若干个体。

    边界处理：
    - num_parents 超过种群大小时，返回全部个体（不报错）

    Args:
        population: 种群
        fitnesses: 适应度数组
        num_parents: 要选择的数量

    Returns:
        选出的精英个体数组
    """
    actual = min(num_parents, len(population))
    if actual <= 0:
        return np.empty((0, population.shape[1]), dtype=population.dtype)
    sorted_indices = np.argsort(fitnesses)
    return population[sorted_indices[:actual]]


def generate_next_gen(offspring: NDArray, best_parent: NDArray) -> NDArray:
    """将变异后的种群与最佳父代拼接（工具函数）。"""
    return np.vstack((offspring, best_parent))


# ---------------------------------------------------------------------------
# 测试入口
# ---------------------------------------------------------------------------


def main():
    """包含正常用例与边界用例的测试函数。"""

    points_normal = {
        0: (-450.0, 100.0, 0.0),
        1: (-450.0, 300.0, 0.0),
        2: (-450.0, 500.0, 0.0),
        3: (-300.0, 150.0, 0.0),
        4: (-300.0, 350.0, 0.0),
        5: (-300.0, 550.0, 0.0),
        6: (-300.0, 750.0, 0.0),
        7: (-150.0, 200.0, 0.0),
        8: (-150.0, 400.0, 0.0),
        9: (-150.0, 600.0, 0.0),
        10: (-600.0, 400.0, 0.0),
        11: (450.0, 100.0, 0.0),
        12: (450.0, 300.0, 0.0),
        13: (450.0, 500.0, 0.0),
        14: (300.0, 150.0, 0.0),
        15: (300.0, 350.0, 0.0),
        16: (300.0, 550.0, 0.0),
        17: (300.0, 750.0, 0.0),
        18: (150.0, 200.0, 0.0),
        19: (150.0, 400.0, 0.0),
        20: (150.0, 600.0, 0.0),
        21: (600.0, 400.0, 0.0),
    }

    # ---- 边界用例 ----
    print("=" * 60)
    print("边界用例 1: 空 points")
    print("=" * 60)
    best, fitness, history = sort_solder_joints({})
    print(f"结果: order={best}, fitness={fitness}, history={history}\n")

    print("=" * 60)
    print("边界用例 2: 单焊点")
    print("=" * 60)
    best, fitness, history = sort_solder_joints({0: (1.0, 2.0, 3.0)})
    print(f"结果: order={best}, fitness={fitness}, history={history}\n")

    print("=" * 60)
    print("边界用例 3: 两个焊点")
    print("=" * 60)
    best, fitness, history = sort_solder_joints(
        {0: (0.0, 0.0, 0.0), 1: (100.0, 0.0, 0.0)}
    )
    print(f"结果: order={best}, fitness={fitness:.6f}, history={history}\n")

    print("=" * 60)
    print("边界用例 4: 两焊点完全重合")
    print("=" * 60)
    best, fitness, history = sort_solder_joints(
        {0: (5.0, 5.0, 5.0), 1: (5.0, 5.0, 5.0)}
    )
    print(f"结果: order={best}, fitness={fitness:.6f}（epsilon 防除零）\n")

    print("=" * 60)
    print("边界用例 5: tournament_size > population_size（自动收紧）")
    print("=" * 60)
    best, fitness, history = sort_solder_joints(
        points_normal,
        population_size=10,
        tournament_size=50,
        num_generations=5,
        patience=5,
    )
    print(f"结果: fitness={fitness:.6f}\n")

    print("=" * 60)
    print("边界用例 6: 非法参数（应抛出异常）")
    print("=" * 60)
    for bad_kwargs, label in [
        ({"population_size": 0}, "population_size=0"),
        ({"elite_count": 200}, "elite_count >= population_size"),
        ({"base_mutation_rate": 1.5}, "base_mutation_rate=1.5"),
        ({"mutation_boost_factor": -1}, "mutation_boost_factor=-1"),
    ]:
        try:
            sort_solder_joints({0: (0.0, 0.0, 0.0), 1: (1.0, 0.0, 0.0)}, **bad_kwargs)
            print(f"  {label}: ❌ 未捕获到异常（预期应抛出）")
        except (ValueError, TypeError) as e:
            print(f"  {label}: ✅ 正确抛出 {type(e).__name__}: {e}")

    # ---- 正常用例 ----
    print("\n" + "=" * 60)
    print("正常用例: 22 个焊点")
    print("=" * 60)
    best_order, best_fitness, fitness_history = sort_solder_joints(
        points_normal,
        population_size=200,
        num_generations=1000,
        base_mutation_rate=0.15,
        tournament_size=3,
        random_seed=99,
        patience=200,
        elite_count=2,
    )

    print("\n=== 最终结果 ===")
    print(f"最优焊接顺序: {best_order}")
    print(f"最优热集中度: {best_fitness:.6f}")
    print(f"初始热集中度: {fitness_history[0]:.6f}")
    improvement = (fitness_history[0] - best_fitness) / fitness_history[0] * 100
    print(f"热集中度降低: {improvement:.2f}%")


if __name__ == "__main__":
    main()
