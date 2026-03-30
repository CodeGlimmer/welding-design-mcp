"""焊点焊接顺序排序算法

- 依据遗传算法对焊点集合进行排序，对热集中度进行优化
- 支持自适应突变率（根据种群多样性动态调整）
- 返回迭代过程中最优适应度用于绘图
- 改进：贪心初始化、PMX交叉、逆转变异、更大种群
"""

from typing import Optional, Tuple

import numpy as np
from numpy.typing import NDArray


def caculate_fitness_by_heat(
    sorted_points: list[int] | np.ndarray, points: dict[int, tuple[float, float, float]]
) -> float:
    """计算焊接顺序的热集中度

    热集中度 = 相邻两个焊点距离的倒数之和
    热集中度越小越好（距离越大，热量累积越少）

    Args:
        sorted_points: 排序后的焊点索引列表
        points: 焊点坐标字典

    Returns:
        float: 热集中度值，越小越好
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

    # 向量化计算：利用广播一次性计算所有个体对的汉明距离
    # population[:, np.newaxis, :] shape: (N, 1, n)
    # population[np.newaxis, :, :] shape: (1, N, n)
    expanded1 = population[:, np.newaxis, :]  # (N, 1, n)
    expanded2 = population[np.newaxis, :, :]  # (1, N, n)

    # 计算汉明距离矩阵: (N, N)，每对个体一次计算
    hamming_matrix = np.sum(expanded1 != expanded2, axis=2) / n

    # 只取上三角（不含对角线），计算平均值
    upper_tri = np.triu(hamming_matrix, k=1)
    pair_count = population_size * (population_size - 1) / 2
    avg_hamming = np.sum(upper_tri) / pair_count

    return float(avg_hamming)


def greedy_initialize(
    points: dict[int, tuple[float, float, float]], num_individuals: int
) -> list[NDArray]:
    """贪心初始化：使用贪心策略生成多个不同的个体

    从随机起点出发，每次选择最近的未访问焊点，生成多个贪心解
    同时加入一些随机扰动来增加多样性

    Args:
        points: 焊点坐标字典
        num_individuals: 要生成的个体数量

    Returns:
        list[NDArray]: 生成的个体列表
    """
    n = len(points)
    point_ids = list(points.keys())
    individuals = []

    # 预计算所有点对之间的距离矩阵，避免重复计算
    coords = np.array([points[pid] for pid in point_ids])  # (n, 3)
    dist_matrix = np.sqrt(
        np.sum((coords[:, np.newaxis, :] - coords[np.newaxis, :, :]) ** 2, axis=2)
    )

    # 1. 纯贪心解（从不同起点出发）
    for start_idx in range(min(num_individuals // 2, n)):
        start_point = point_ids[start_idx]
        start_pos = point_ids.index(start_point)
        visited = {start_point}
        order = [start_point]

        current_pos = start_pos
        for _ in range(n - 1):
            # 找到最近的未访问焊点（使用预计算的距离矩阵）
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
        # 从贪心解开始
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
            # 放宽选择条件：选择距离在最短距离1.5倍以内的候选者
            candidates_mask = unvisited_dists <= min_dist * 1.5
            candidate_positions = np.where(candidates_mask)[0]

            # 随机选择候选者
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
    num_generations: int = 300,
    base_mutation_rate: float = 0.15,
    diversity_threshold: float = 0.15,
    mutation_boost_factor: float = 5.0,
    tournament_size: int = 5,
    random_seed: Optional[int] = 42,
    patience: int = 20,
    elite_count: int = 2,
) -> Tuple[NDArray, float, NDArray]:
    """焊点焊接顺序排序（改进的遗传算法）

    改进点：
    - 贪心初始化：生成优质初始解
    - PMX交叉：更好的交叉算子
    - 逆转变异：更适合TSP类问题
    - 更大的锦标赛：更强的选择压力
    - 多精英保留：保留多个最优个体

    Args:
        points: 焊点坐标字典 {焊点ID: (x, y, z)}
        population_size: 种群大小
        num_generations: 迭代代数
        base_mutation_rate: 基础突变率
        diversity_threshold: 多样性阈值
        mutation_boost_factor: 收敛时突变率放大倍数
        tournament_size: 锦标赛大小
        random_seed: 随机种子
        patience: 早停耐心值
        elite_count: 精英保留数量

    Returns:
        Tuple[NDArray, float, NDArray]:
            - global_best: 全局最优焊接顺序
            - global_best_fitness: 全局最优热集中度
            - best_fitness_history: 每代最优热集中度的历史记录
    """
    if random_seed is not None:
        np.random.seed(random_seed)

    n = len(points)

    # 贪心初始化 + 随机初始化混合
    greedy_individuals = greedy_initialize(points, population_size // 3)
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

        # 收敛判断：多样性低于阈值时，大幅增加突变率
        if current_diversity < diversity_threshold:
            adaptive_mutation_rate = decay_mutation_rate * mutation_boost_factor
        else:
            adaptive_mutation_rate = decay_mutation_rate

        # 限制突变率范围
        adaptive_mutation_rate = np.clip(adaptive_mutation_rate, 0.01, 0.6)

        # 早停判断
        if no_improvement_count >= patience:
            print(
                f"Early termination at generation {gen + 1} "
                f"(no improvement for {patience} consecutive generations)"
            )
            break

        # 自然选择（更大的锦标赛）
        parents = natural_selection(
            population, fitness, population_size, tournament_size
        )

        # PMX交叉
        offspring = pmx_crossover(parents, population_size - elite_count)

        # 逆转变异（更适合TSP问题）
        offspring = inversion_mutation(offspring, adaptive_mutation_rate)

        # 精英保留（保留多个最优个体）
        elite = select_best(population, fitness, elite_count)
        offspring = np.vstack([offspring, elite])

        population = offspring
        fitness = evaluate_fitness(population, points)

        # 打印进度
        if (gen + 1) % 20 == 0:
            print(
                f"Generation {gen + 1} | Best Heat: {global_best_fitness:.6f} | "
                f"Diversity: {current_diversity:.3f} | Mutation: {adaptive_mutation_rate:.3f}"
            )

    return (
        global_best_individual,  # type: ignore
        global_best_fitness,
        np.array(best_fitness_history),
    )


def init_population(n: int, population_size: int) -> NDArray:
    """初始化种群（随机）"""
    population = [np.random.permutation(n) for _ in range(population_size)]
    return np.array(population)


def evaluate_fitness(
    population: NDArray, points: dict[int, tuple[float, float, float]]
) -> NDArray:
    """评估种群中每个个体的适应度"""
    fitnesses: list[float] = []
    for individual in population:
        fitness = caculate_fitness_by_heat(individual, points)
        fitnesses.append(fitness)
    return np.array(fitnesses)


def natural_selection(
    population: NDArray, fitnesses: NDArray, num_parents: int, tournament_size: int = 5
) -> NDArray:
    """自然选择，采用锦标赛策略

    Args:
        population: 种群
        fitnesses: 热集中度（越小越好）
        num_parents: 选择的父代数量
        tournament_size: 锦标赛大小

    Returns:
        选择后的父代种群
    """
    parents = []
    pop_size = len(population)
    for _ in range(num_parents):
        tournament = np.random.choice(pop_size, tournament_size, replace=False)
        winner = tournament[np.argmin(fitnesses[tournament])]
        parents.append(population[winner])
    return np.array(parents)


def pmx_crossover(parents: NDArray, offspring_size: int) -> NDArray:
    """PMX（部分映射）交叉 - 正确实现"""
    offspring = []
    n = parents.shape[1]

    for _ in range(offspring_size):
        parent1_pos, parent2_pos = np.random.choice(len(parents), 2, replace=False)
        parent1, parent2 = parents[parent1_pos], parents[parent2_pos]

        # 随机选择两个交叉点
        cross_start = np.random.randint(0, n - 1)
        cross_end = np.random.randint(cross_start + 1, n)

        # 创建子代并初始化为-1
        child = np.full(n, -1, dtype=int)

        # 从parent1复制中间段
        child[cross_start:cross_end] = parent1[cross_start:cross_end]

        # 建立映射：parent1中的基因 -> parent2中对应位置的基因
        mapping = {}
        for i in range(cross_start, cross_end):
            mapping[parent1[i]] = parent2[i]

        # segment中已有的基因
        segment_genes = set(child[cross_start:cross_end])

        # 建立位置到基因的反向映射：parent2中的基因 -> 在parent1中的位置
        pos_in_parent1 = {gene: i for i, gene in enumerate(parent1)}

        # 填充剩余位置
        for i in range(n):
            if cross_start <= i < cross_end:
                continue

            gene = parent2[i]

            # 如果gene已在segment中，需要跟随映射链
            while gene in segment_genes:
                # 用映射找到parent2中的基因在parent1中的位置
                pos = pos_in_parent1.get(gene)
                if pos is not None and cross_start <= pos < cross_end:
                    # 跟随映射到parent2中对应位置的基因
                    gene = parent2[pos]
                else:
                    # 映射链断裂，基因不在segment中，可以直接使用
                    break

            child[i] = gene
            segment_genes.add(gene)  # 标记为已使用

        offspring.append(child)

    return np.array(offspring)


def inversion_mutation(offspring: NDArray, mutation_rate: float) -> NDArray:
    """逆转变异：随机选择一段基因 reversed

    这种变异方式更适合TSP问题，因为它保持了相对顺序
    """
    for i in range(len(offspring)):
        if np.random.rand() < mutation_rate:
            n = len(offspring[i])
            # 随机选择两个断点
            pos1 = np.random.randint(0, n - 1)
            pos2 = np.random.randint(pos1 + 1, n)

            # 逆转中间段
            offspring[i, pos1:pos2] = offspring[i, pos1:pos2][::-1]

    return offspring


def select_best(population: NDArray, fitnesses: NDArray, num_parents: int) -> NDArray:
    """选择热集中度最低的个体"""
    sorted_indices = np.argsort(fitnesses)
    return population[sorted_indices[:num_parents]]


def generate_next_gen(offspring: NDArray, best_parent: NDArray) -> NDArray:
    """将变异后的种群与最佳父代拼接"""
    return np.vstack((offspring, best_parent))


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
        tournament_size=3,
        random_seed=99,
        patience=200,
        elite_count=2,
    )

    print("\n=== Final Result ===")
    print(f"Best welding order: {best_order}")
    print(f"Best heat concentration: {best_fitness:.6f}")
    print(f"Initial heat: {fitness_history[0]:.6f}")
    improvement = (fitness_history[0] - best_fitness) / fitness_history[0] * 100
    print(f"Heat reduction: {improvement:.2f}%")


if __name__ == "__main__":
    main()
