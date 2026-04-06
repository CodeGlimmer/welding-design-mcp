from pathlib import Path

from langchain.agents import create_agent
from langchain.messages import ToolMessage
from langchain_deepseek import ChatDeepSeek
from langchain.agents.middleware import wrap_tool_call

from welding_app.error.error_message import ToolException


@wrap_tool_call
def handle_tool_error(request, handler):
    """处理工具调用错误"""
    try:
        return handler(request)
    except ToolException as e:
        return ToolMessage(content=e.to_model().model_dump_json(), tool_call_id=request.tool_call["id"])


def create_plan_agent():

    model = ChatDeepSeek(model="deepseek-chat", temperature=0.1)

    system_prompt_path = (
        Path(__file__).parent.parent.parent.parent
        / "prompts"
        / "to_welding_plan_agent"
        / "system_prompt.md"
    )

    plan_agent = create_agent(
        model=model,
        system_prompt=system_prompt_path.read_text(),
        tools=[],
        middleware=[handle_tool_error],
    )
    return plan_agent
