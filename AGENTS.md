# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

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

# 行为准则

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
