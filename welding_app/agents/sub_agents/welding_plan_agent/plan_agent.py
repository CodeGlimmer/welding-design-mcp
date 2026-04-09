from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain_deepseek import ChatDeepSeek

from welding_app.error.error_message import handle_tool_error
from welding_app.prompts.to_welding_plan_agent import get_system_prompt

from .plan_agent_tools import generate_welding_plan, query_welding_infomation


def create_plan_agent():

    model = ChatDeepSeek(model="deepseek-chat", temperature=0.1)

    plan_agent = create_agent(
        model=model,
        system_prompt=get_system_prompt(),
        tools=[generate_welding_plan, query_welding_infomation],
        middleware=[
            handle_tool_error,
            TodoListMiddleware(
                system_prompt="",  # TODO: 补全使用todolist的提示词, 重点是如何使用以加强模型能力
            ),  # type: ignore
        ],
    )
    return plan_agent
