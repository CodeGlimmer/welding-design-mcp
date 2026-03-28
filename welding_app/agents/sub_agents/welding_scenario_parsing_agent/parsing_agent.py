from pathlib import Path

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_deepseek import ChatDeepSeek

from .parsing_agent_tools import (
    generate_scenario_builder_toolkit,
    get_scenario_file_content,
)
from .types import ParsingAgentOutput


def create_parsing_agent():
    """配置解析场景文件的智能体"""
    model = ChatDeepSeek(model="deepseek-chat", temperature=0.1)
    system_prompt_path = (
        Path(__file__).parent.parent.parent.parent
        / "prompts"
        / "to_welding_scenario_parsing_agent"
        / "system_prompt.md"
    )

    agent = create_agent(
        model=model,
        tools=generate_scenario_builder_toolkit() + [get_scenario_file_content],
        system_prompt=system_prompt_path.read_text(),
        response_format=ToolStrategy(ParsingAgentOutput),
    )

    return agent
