"""主智能体提示词工厂"""

from pathlib import Path


def get_summarization_prompt() -> str:
    """获取摘要提示词"""
    prompt_path = Path(__file__).parent / "summarization.md"
    return prompt_path.read_text(encoding="utf-8")


def get_task_prompt() -> str:
    """获取任务提示词"""
    prompt_path = Path(__file__).parent / "task.md"
    return prompt_path.read_text(encoding="utf-8")