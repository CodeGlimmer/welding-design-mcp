from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.memory import InMemorySaver

from welding_app.prompts.to_welding_scenario_parsing_agent import (
    get_system_prompt,
)

from .parsing_agent_tools import (
    generate_scenario_builder_toolkit,
    get_scenario_file_content,
)
from .types import ParsingAgentOutput


def create_parsing_agent():
    """配置解析场景文件的智能体"""
    model = ChatDeepSeek(model="deepseek-chat", temperature=0.1)

    agent = create_agent(
        model=model,
        tools=generate_scenario_builder_toolkit() + [get_scenario_file_content],
        system_prompt=get_system_prompt(),
        response_format=ToolStrategy(ParsingAgentOutput),
        checkpointer=InMemorySaver(),
    )

    return agent
