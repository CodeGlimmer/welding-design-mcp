from pathlib import Path

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_deepseek import ChatDeepSeek

from .checker_tools import get_latest_parsed_scenario, get_scenario_file_content
from .types import CheckerOutput


def create_checker_agent():
    """配置检查场景解析结果的智能体"""
    model = ChatDeepSeek(model="deepseek-chat", temperature=0.1)
    system_prompt_path = (
        Path(__file__).parent.parent.parent.parent
        / "prompts"
        / "to_welding_scenario_parsing_checker"
        / "system_prompt.md"
    )

    agent = create_agent(
        model=model,
        tools=[get_scenario_file_content, get_latest_parsed_scenario],
        system_prompt=system_prompt_path.read_text(),
        response_format=ToolStrategy(CheckerOutput),
    )

    return agent
