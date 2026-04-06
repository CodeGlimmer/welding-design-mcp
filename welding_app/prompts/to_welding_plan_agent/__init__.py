"""焊接计划智能体提示词工厂"""

from pathlib import Path


def get_system_prompt() -> str:
    """获取焊接计划智能体的系统提示词"""
    prompt_path = Path(__file__).parent / "system_prompt.md"
    return prompt_path.read_text(encoding="utf-8")