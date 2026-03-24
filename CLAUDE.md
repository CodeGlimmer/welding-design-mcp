# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

welding_design_mcp 是一个基于 FastMCP 的 Model Context Protocol 服务器，用于焊接设计领域。

## Environment

- Python: 3.13
- 包管理: uv
- 虚拟环境: .venv/

## Common Commands

```bash
# 安装依赖
uv sync

# 激活虚拟环境
source .venv/Scripts/activate

# 运行项目
python -m welding_app
```

## Project Structure

```
welding_app/
├── agents/         # AI 代理模块
├── databases/     # 数据库相关
├── models/         # 数据模型
├── prompts/       # 提示词模板
├── resources/     # 资源文件
├── server_tools/  # 服务器工具
├── servers/       # 服务器实现
├── utils/         # 工具函数
└── welding_scenario/  # 焊接场景模块
```

## Key Dependencies

- fastmcp>=3.1.1 - MCP服务器框架
- langchain>=1.2.13 - LLM应用框架
- langgraph>=1.1.3 - Agent工作流
- langchain-deepseek>=1.0.1 - DeepSeek模型集成
- duckduckgo-search>=8.1.1 - 搜索功能
