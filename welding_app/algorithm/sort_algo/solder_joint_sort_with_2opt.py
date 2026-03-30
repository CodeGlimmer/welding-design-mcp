"""焊点焊接顺序排序算法 - 带2-opt局部搜索优化

- 基于遗传算法 + 2-opt局部搜索的混合优化
- 2-opt对遗传算法产生的精英个体进行局部优化
- 预计算距离矩阵加速计算
"""

from typing import Optional, Tuple

import numpy as np
from numpy.typing import NDArray


def caculate_fitness_by_heat(
    sorted_points: list[int] | np.ndarray,
    points: dict[int, tuple[float, float, float]],
) -> float:
    """计算焊接顺序的热集中度

    热集中度 = 相邻两个焊点距离的倒数之和
    热集中度越小越好（距离越大，热量累积越少）
    """
    epsilon = 1e-6
    heat_concentration = 0.0
    for i in range(len(sorted_points) - 1):
        p1 = points[sorted_points[i]]
        p2 = points[sorted_points[i + 1]]
        dist = (
            (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2
        ) ** 0.5
        heat_concentration += 1.0 / (dist + epsilon)

    return heat_concentration


def calculate_population_diversity(population: NDArray) -> float:
    """计算种群多样性（平均汉明距离）- 向量化版本"""
    population_size, n = population.shape
    if population_size <= 1:
        return 0.0

    expanded1 = population[:, np.newaxis, :]
    expanded2 = population[np.newaxis, :, :]
    hamming_matrix = np.sum(expanded1 != expanded2, axis=2) / n
    upper_tri = np.triu(hamming_matrix, k=1)
    pair_count = population_size * (population_size - 1) / 2
    avg_hamming = np.sum(upper_tri) / pair_count

    return float(avg_hamming)


def build_distance_matrix(
    points: dict[int, tuple[float, float, float]],
) -> Tuple[dict[int, int], np.ndarray]:
    """构建距离矩阵

    Returns:
        id_to_idx: 焊点ID到矩阵索引的映射
        dist_matrix: 距离矩阵 (n x n)
    """
    point_ids = list(points.keys())
    id_to_idx = {pid: i for i, pid in enumerate(point_ids)}

    coords = np.array([points[pid] for pid in point_ids])
    dist_matrix = np.sqrt(
        np.sum((coords[:, np.newaxis, :] - coords[np.newaxis, :, :]) ** 2, axis=2)
    )

    return id_to_idx, dist_matrix


def two_opt_improve(
    individual: np.ndarray,
    dist_matrix: np.ndarray,
    id_to_idx: dict[int, int],
    max_iterations: int = 100,
) -> Tuple[np.ndarray, float | NDArray[np.float64], int]:
    """2-opt局部搜索优化 - 最大化相邻点距离（最小化热量）

    2-opt通过交换边来优化：选择两条边 (i, i+1) 和 (j, j+1)，
    如果新的边长度之和更大（热量更分散），则接受交换。

    Args:
        individual: 当前解（焊点ID序列）
        dist_matrix: 预计算的距离矩阵
        id_to_idx: 焊点ID到索引的映射
        max_iterations: 最大迭代次数

    Returns:
        improved_individual: 优化后的解
        improvement: 热量改善量（负值表示改善）
        swaps: 执行交换的次数
    """
    n = len(individual)
    current = individual.copy()
    epsilon = 1e-6

    # 计算当前热量
    def calc_heat(path):
        heat = 0.0
        for i in range(len(path) - 1):
            d = dist_matrix[path[i], path[i + 1]]
            heat += 1.0 / (d + epsilon)
        return heat

    swaps = 0

    for _ in range(max_iterations):
        improved = False

        for i in range(n - 3):
            for j in range(i + 2, n - 1):
                if j == n - 1 and i == 0:
                    continue

                # 当前边: (i, i+1) 和 (j, j+1)
                # 交换后边: (i, j) 和 (i+1, j+1)

                d_i_i1 = dist_matrix[current[i], current[i + 1]]
                d_j_j1 = dist_matrix[current[j], current[j + 1]]
                d_i_j = dist_matrix[current[i], current[j]]
                d_i1_j1 = dist_matrix[current[i + 1], current[j + 1]]

                # 当前热量贡献 vs 交换后热量贡献
                old_heat = 1.0 / (d_i_i1 + epsilon) + 1.0 / (d_j_j1 + epsilon)
                new_heat = 1.0 / (d_i_j + epsilon) + 1.0 / (d_i1_j1 + epsilon)

                # 如果交换后热量减少（变好），则接受
                if new_heat < old_heat:
                    current[i + 1 : j + 1] = current[i + 1 : j + 1][::-1]
                    swaps += 1
                    improved = True

        if not improved:
            break

    new_heat = calc_heat(current)
    return current, new_heat, swaps


def two_opt_fast(
    individual: np.ndarray,
    dist_matrix: np.ndarray,
    id_to_idx: dict[int, int],
) -> Tuple[np.ndarray, bool]:
    """快速2-opt优化（只遍历一次，不重复优化直到收敛）

    Args:
        individual: 当前解
        dist_matrix: 距离矩阵
        id_to_idx: ID到索引映射

    Returns:
        improved_individual: 优化后的解
        improved: 是否进行了改进
    """
    n = len(individual)
    current = individual.copy()
    improved = False

    for i in range(n - 2):
        for j in range(i + 2, n):
            if j == n - 1 and i == 0:
                continue

            idx_i = id_to_idx[current[i]]
            idx_i1 = id_to_idx[current[i + 1]]
            idx_j = id_to_idx[current[j]]
            idx_j1 = id_to_idx[current[j + 1]] if j + 1 < n else id_to_idx[current[0]]

            old_dist = dist_matrix[idx_i, idx_i1] + dist_matrix[idx_j, idx_j1]
            new_dist = dist_matrix[idx_i, idx_j] + dist_matrix[idx_i1, idx_j1]

            if new_dist < old_dist:
                current[i + 1 : j + 1] = current[i + 1 : j + 1][::-1]
                improved = True

    return current, improved


def greedy_initialize(
    points: dict[int, tuple[float, float, float]],
    num_individuals: int,
    dist_matrix: np.ndarray,
    id_to_idx: dict[int, int],
) -> list[NDArray]:
    """贪心初始化 - 使用预计算的距离矩阵"""
    n = len(points)
    point_ids = list(points.keys())
    individuals = []

    # 1. 纯贪心解（从不同起点出发）
    for start_idx in range(min(num_individuals // 2, n)):
        start_point = point_ids[start_idx]
        visited = {start_point}
        order = [start_point]

        current_pos = start_idx
        for _ in range(n - 1):
            unvisited_mask = np.array([pid not in visited for pid in point_ids])
            unvisited_dists = dist_matrix[current_pos].copy()
            unvisited_dists[~unvisited_mask] = np.inf

            nearest_pos = int(np.argmin(unvisited_dists))
            nearest = point_ids[nearest_pos]

            visited.add(nearest)
            order.append(nearest)
            current_pos = nearest_pos

        individuals.append(np.array(order))

    # 2. 贪心 + 随机扰动
    for _ in range(num_individuals - len(individuals)):
        start_pos = np.random.randint(n)
        start_point = point_ids[start_pos]
        visited = {start_point}
        order = [start_point]
        current_pos = start_pos

        for _ in range(n - 1):
            unvisited_mask = np.array([pid not in visited for pid in point_ids])
            unvisited_dists = dist_matrix[current_pos].copy()
            unvisited_dists[~unvisited_mask] = np.inf

            min_dist = np.min(unvisited_dists)
            candidates_mask = unvisited_dists <= min_dist * 1.5
            candidate_positions = np.where(candidates_mask)[0]

            chosen_pos = int(np.random.choice(candidate_positions))
            chosen = point_ids[chosen_pos]

            visited.add(chosen)
            order.append(chosen)
            current_pos = chosen_pos

        individuals.append(np.array(order))

    return individuals


def sort_solder_joints(
    points: dict[int, tuple[float, float, float]],
    population_size: int = 200,
    num_generations: int = 500,
    base_mutation_rate: float = 0.15,
    diversity_threshold: float = 0.15,
    mutation_boost_factor: float = 5.0,
    tournament_size: int = 5,
    random_seed: Optional[int] = 42,
    patience: int = 50,
    elite_count: int = 5,
    use_2opt: bool = True,
) -> Tuple[NDArray, float, NDArray]:
    """焊点焊接顺序排序（遗传算法 + 2-opt局部搜索）

    改进点：
    - 贪心初始化：生成优质初始解
    - PMX交叉：更好的交叉算子
    - 逆转变异：更适合TSP类问题
    - 2-opt局部搜索：对精英个体进行局部优化

    Args:
        points: 焊点坐标字典
        population_size: 种群大小
        num_generations: 迭代代数
        base_mutation_rate: 基础突变率
        diversity_threshold: 多样性阈值
        mutation_boost_factor: 收敛时突变率放大倍数
        tournament_size: 锦标赛大小
        random_seed: 随机种子
        patience: 早停耐心值
        elite_count: 精英保留数量
        use_2opt: 是否使用2-opt局部搜索

    Returns:
        Tuple[NDArray, float, NDArray]: 最优顺序、最优适应度、适应度历史
    """
    if random_seed is not None:
        np.random.seed(random_seed)

    n = len(points)

    # 预计算距离矩阵
    id_to_idx, dist_matrix = build_distance_matrix(points)

    # 贪心初始化 + 随机初始化混合
    greedy_individuals = greedy_initialize(
        points, population_size // 3, dist_matrix, id_to_idx
    )
    random_individuals = [
        np.random.permutation(n)
        for _ in range(population_size - len(greedy_individuals))
    ]
    population = np.array(greedy_individuals + random_individuals)

    # 评估初始种群
    fitness = evaluate_fitness(population, points)

    # 初始化全局最优
    global_best_individual: Optional[NDArray] = None
    global_best_fitness: float = np.inf
    no_improvement_count = 0

    # 记录每代最优适应度
    best_fitness_history: list[float] = []

    for gen in range(num_generations):
        # 更新全局最优
        current_best_idx = np.argmin(fitness)
        current_best_fitness = fitness[current_best_idx]
        current_best_individual = population[current_best_idx]

        if current_best_fitness < global_best_fitness:
            global_best_fitness = current_best_fitness
            global_best_individual = current_best_individual.copy()
            no_improvement_count = 0
        else:
            no_improvement_count += 1

        # 记录当前代最优适应度
        best_fitness_history.append(global_best_fitness)

        # 计算当前种群多样性
        current_diversity = calculate_population_diversity(population)

        # 自适应计算突变率
        decay_mutation_rate = base_mutation_rate * (1 - gen / num_generations) ** 0.5

        if current_diversity < diversity_threshold:
            adaptive_mutation_rate = decay_mutation_rate * mutation_boost_factor
        else:
            adaptive_mutation_rate = decay_mutation_rate

        adaptive_mutation_rate = np.clip(adaptive_mutation_rate, 0.01, 0.6)

        # 早停判断
        if no_improvement_count >= patience:
            print(
                f"Early termination at generation {gen + 1} "
                f"(no improvement for {patience} consecutive generations)"
            )
            break

        # 自然选择
        parents = natural_selection(
            population, fitness, population_size, tournament_size
        )

        # PMX交叉
        offspring = pmx_crossover(parents, population_size - elite_count)

        # 逆转变异
        offspring = inversion_mutation(offspring, adaptive_mutation_rate)

        # 选择精英个体并应用2-opt局部搜索
        elite = select_best(population, fitness, elite_count)
        if use_2opt:
            for i in range(len(elite)):
                elite[i], _, _ = two_opt_improve(elite[i], dist_matrix, id_to_idx)

        # 精英保留
        offspring = np.vstack([offspring, elite])

        population = offspring
        fitness = evaluate_fitness(population, points)

        # 打印进度
        if (gen + 1) % 20 == 0:
            print(
                f"Generation {gen + 1} | Best Heat: {global_best_fitness:.6f} | "
                f"Diversity: {current_diversity:.3f} | Mutation: {adaptive_mutation_rate:.3f}"
            )

    # 最终精修：对全局最优解应用2-opt局部搜索
    if use_2opt and global_best_individual is not None:
        global_best_individual, _, _ = two_opt_improve(
            global_best_individual, dist_matrix, id_to_idx, max_iterations=200
        )
        global_best_fitness = caculate_fitness_by_heat(global_best_individual, points)
        best_fitness_history[-1] = global_best_fitness

    return (
        global_best_individual,  # type: ignore
        global_best_fitness,
        np.array(best_fitness_history),
    )


def evaluate_fitness(
    population: NDArray, points: dict[int, tuple[float, float, float]]
) -> NDArray:
    """评估种群中每个个体的适应度"""
    fitnesses = [caculate_fitness_by_heat(ind, points) for ind in population]
    return np.array(fitnesses)


def natural_selection(
    population: NDArray, fitnesses: NDArray, num_parents: int, tournament_size: int = 5
) -> NDArray:
    """自然选择，采用锦标赛策略"""
    parents = []
    pop_size = len(population)
    for _ in range(num_parents):
        tournament = np.random.choice(pop_size, tournament_size, replace=False)
        winner = tournament[np.argmin(fitnesses[tournament])]
        parents.append(population[winner])
    return np.array(parents)


def pmx_crossover(parents: NDArray, offspring_size: int) -> NDArray:
    """PMX（部分映射）交叉"""
    offspring = []
    n = parents.shape[1]

    for _ in range(offspring_size):
        parent1_pos, parent2_pos = np.random.choice(len(parents), 2, replace=False)
        parent1, parent2 = parents[parent1_pos], parents[parent2_pos]

        cross_start = np.random.randint(0, n - 1)
        cross_end = np.random.randint(cross_start + 1, n)

        child = np.full(n, -1, dtype=int)
        child[cross_start:cross_end] = parent1[cross_start:cross_end]

        mapping = {}
        for i in range(cross_start, cross_end):
            mapping[parent1[i]] = parent2[i]

        segment_genes = set(child[cross_start:cross_end])
        pos_in_parent1 = {gene: i for i, gene in enumerate(parent1)}

        for i in range(n):
            if cross_start <= i < cross_end:
                continue

            gene = parent2[i]

            while gene in segment_genes:
                pos = pos_in_parent1.get(gene)
                if pos is not None and cross_start <= pos < cross_end:
                    gene = parent2[pos]
                else:
                    break

            child[i] = gene
            segment_genes.add(gene)

        offspring.append(child)

    return np.array(offspring)


def inversion_mutation(offspring: NDArray, mutation_rate: float) -> NDArray:
    """逆转变异"""
    for i in range(len(offspring)):
        if np.random.rand() < mutation_rate:
            n = len(offspring[i])
            pos1 = np.random.randint(0, n - 1)
            pos2 = np.random.randint(pos1 + 1, n)
            offspring[i, pos1:pos2] = offspring[i, pos1:pos2][::-1]

    return offspring


def select_best(population: NDArray, fitnesses: NDArray, num_parents: int) -> NDArray:
    """选择热集中度最低的个体"""
    sorted_indices = np.argsort(fitnesses)
    return population[sorted_indices[:num_parents]]


def main():
    """测试函数"""
    points = {
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

    best_order, best_fitness, fitness_history = sort_solder_joints(
        points,
        population_size=200,
        num_generations=1000,
        base_mutation_rate=0.15,
        tournament_size=5,
        random_seed=50,
        patience=100,
        elite_count=3,
        use_2opt=True,
    )

    print("\n=== Final Result ===")
    print(f"Best welding order: {best_order}")
    print(f"Best heat concentration: {best_fitness:.6f}")
    print(f"Initial heat: {fitness_history[0]:.6f}")
    improvement = (fitness_history[0] - best_fitness) / fitness_history[0] * 100
    print(f"Heat reduction: {improvement:.2f}%")


if __name__ == "__main__":
    main()
