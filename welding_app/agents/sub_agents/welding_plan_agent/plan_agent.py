from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek

from welding_app.error.error_message import handle_tool_error
from welding_app.prompts.to_welding_plan_agent import get_system_prompt


def create_plan_agent():

    model = ChatDeepSeek(model="deepseek-chat", temperature=0.1)

    plan_agent = create_agent(
        model=model,
        system_prompt=get_system_prompt(),
        tools=[],
        middleware=[handle_tool_error],
    )
    return plan_agent
