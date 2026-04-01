# Welding Design MCP

基于 FastMCP 的 Model Context Protocol 服务器，专注于焊接工艺设计领域。

## 功能特性

### 核心能力

- **MCP 服务器** - 提供标准化的 MCP 协议接口，支持 SSE 传输
- **焊接场景解析** - 支持解析 txt、json、robx 格式的焊接场景文件
- **多 Agent 协作** - 主 Agent、解析 Agent、检查 Agent 三者协同工作
- **焊接顺序优化** - 提供遗传算法 + 2-opt 局部搜索的焊点排序优化

### 支持的文件格式

| 格式 | 说明 |
|------|------|
| `.txt` | 文本描述文件，用户提供尽可能丰富的文本信息 |
| `.json` | 结构化 JSON，定义焊点和焊缝 |
| `.robx` | ABB RobotStudio 导出格式，可提取焊接路径点 |

## 快速开始

### 环境要求

- Python: 3.13+
- uv (包管理工具)

### 安装

```bash
# 安装依赖
uv sync

# 激活虚拟环境
source .venv/bin/activate
```

### 启动 MCP 服务器

```bash
# 使用 npm 脚本
npm run mcp

# 或直接运行
uv run python -m welding_app.servers.mcp_server
```

服务器将在 `http://0.0.0.0:8000` 启动，使用 SSE 传输协议。

### MCP Inspector 调试

```bash
npm run inspect
```

## 项目结构

```
welding_design_mcp/
├── welding_app/
│   ├── agents/                    # AI Agent 模块
│   │   ├── main_agent.py         # 主 Agent（任务构建与审计）
│   │   ├── main_agent_tools.py   # 主 Agent 工具
│   │   ├── types.py              # 任务类型定义
│   │   └── sub_agents/
│   │       ├── welding_scenario_parsing_agent/   # 场景解析 Agent
│   │       ├── welding_scenario_parsing_checker/ # 场景解析检查 Agent
│   │       └── welding_plan_agent/              # 焊接计划 Agent（开发中）
│   │
│   ├── algorithm/                 # 算法模块
│   │   └── sort_algo/            # 焊接顺序排序算法
│   │       ├── solder_joint_sort.py            # 基础遗传算法
│   │       └── solder_joint_sort_with_2opt.py  # GA + 2-opt 混合算法
│   │
│   ├── database/                  # 数据库
│   └── welding_scenario/          # 焊接场景模型
│       ├── welding_scenario.py    # 场景模型
│       ├── solder_joint.py        # 焊点模型
│       ├── weld_seam.py           # 焊缝模型
│       └── materials.py           # 材料枚举
│
├── servers/                       # 服务器实现
│   ├── mcp_server.py              # MCP 主服务器
│   └── file_transfer.py           # 文件传输服务
│
├── server_tools/                  # 服务器工具
│   ├── main_agent/                # 主 Agent 工具注册
│   └── file_transfer/             # 文件传输工具注册
│
├── prompts/                       # Agent 提示词模板
│   ├── to_main_agent/             # 主 Agent 提示词
│   ├── to_welding_scenario_parsing_agent/
│   └── to_welding_scenario_parsing_checker/
│
└── pyproject.toml
```

## 核心概念

### 焊接场景 (Welding Scenario)

焊接场景是本系统的核心数据模型，包含：

- **焊点 (Solder Joint)** - 3D 坐标、材料、表面法线、连接部件等信息
- **焊缝 (Weld Seam)** - 几何线段及其控制点（焊点）

### 焊接任务 (Welding Task)

```python
WeldingTask:
  scenario_id: str           # 关联的场景 ID
  content: str               # 任务描述
  requirements: list[        # 需求列表
    {
      content: str,          # 需求内容
      importance: int,       # 优先级 (0-3)
      target_object: str,    # 目标对象
      additional_info: str   # 额外信息
    }
  ]
  addtional_info: str        # 额外任务信息
```

### 任务状态机

```
PARSING (解析) → DESIGN (设计) → SIMULATION (仿真) → FINAL (完成)
```

### 多 Agent 工作流

```
外部 Agent
    ↓
主 Agent (构建 WeldingTask)
    ↓
解析 Agent (解析场景文件)
    ↓
检查 Agent (验证解析结果)
    ↓
焊接计划 Agent (生成焊接顺序) [开发中]
```

## 焊接顺序优化算法

### 算法说明

系统提供两种焊点排序算法，均基于遗传算法 (GA)：

#### 1. 基础遗传算法 (`solder_joint_sort.py`)

- 贪心初始化
- PMX 交叉
- 逆转变异
- 自适应突变率

#### 2. GA + 2-opt 混合算法 (`solder_joint_sort_with_2opt.py`)

在基础算法上增加：
- 2-opt 局部搜索优化
- 预计算距离矩阵
- 更多迭代次数和早停耐心值

### 优化目标

**热集中度最小化**：

$$H = \sum_{i=1}^{n-1} \frac{1}{d_{i,i+1} + \epsilon}$$

其中 $d_{i,i+1}$ 是相邻焊点间的欧氏距离。

### 使用示例

```python
from welding_app.algorithm.sort_algo.solder_joint_sort import sort_solder_joints

points = {
    0: (0.0, 0.0, 0.0),
    1: (10.0, 0.0, 0.0),
    2: (20.0, 0.0, 0.0),
}

best_order, best_fitness, history = sort_solder_joints(
    points,
    population_size=200,
    num_generations=500,
    random_seed=42,
)
```

## MCP 工具

### 文件上传

```python
upload_welding_scenario(
    file_local_location: str,   # 文件本地路径
    file_description: str       # 文件描述
) -> UploadWeldingScenarioResult
```

### 文件查询

```python
get_uploaded_file_info(
    id: str | None  # 传入 ID 查询单个，不传则查询全部
) -> FilesInfo
```

### 主 Agent 对话

```python
chat_with_main_agent(
    message: str,    # 对话内容
    thread_id: int   # 线程 ID
) -> MainAgentResponse
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 必需 |

## 技术栈

- **MCP 框架**: FastMCP >= 3.1.1
- **LLM 框架**: LangChain >= 1.2.13
- **Agent 框架**: LangGraph >= 1.1.3
- **LLM 提供商**: DeepSeek (deepseek-chat)
- **搜索**: DuckDuckGo Search >= 8.1.1

## 开发

### 运行测试

```bash
# 待补充
npm run test
```

### 代码规范

```bash
# 待补充
```

## License

ISC
