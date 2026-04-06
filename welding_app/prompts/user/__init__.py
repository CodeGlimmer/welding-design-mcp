"""用户提示词工厂"""

from pathlib import Path


def get_to_user_prompt() -> str:
    """获取面向用户的提示词"""
    prompt_path = Path(__file__).parent / "to_user.txt"
    return prompt_path.read_text(encoding="utf-8")