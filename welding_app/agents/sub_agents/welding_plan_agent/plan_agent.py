from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain_deepseek import ChatDeepSeek

from welding_app.error.error_message import handle_tool_error

from .plan_agent_tools import (
    design_welding_plan_toolkit,
    generate_welding_plan,
    get_welding_scenario,
    query_welding_infomation,
)
from .prompt import system_prompt, todo_list_prompt


def create_plan_agent():

    model = ChatDeepSeek(model="deepseek-chat", temperature=0.1, top_p=0.2)

    plan_agent = create_agent(
        model=model,
        system_prompt=system_prompt(),
        tools=[generate_welding_plan, query_welding_infomation, get_welding_scenario]
        + design_welding_plan_toolkit(),
        middleware=[
            handle_tool_error,
            TodoListMiddleware(
                system_prompt=todo_list_prompt(),  # TODO: 补全使用todolist的提示词, 重点是如何使用以加强模型能力
            ),  # type: ignore
        ],
    )
    return plan_agent


if __name__ == "__main__":
    import mlflow
    from langchain.messages import HumanMessage

    mlflow.set_tracking_uri("http://127.0.0.1:5000")
    mlflow.set_experiment("plan_agent v2")
    mlflow.autolog()

    agent = create_plan_agent()
    while True:
        human_input = input("Human: ")
        if human_input in {"q", "quit", "exit"}:
            break
        result = agent.invoke(
            {"messages": [HumanMessage(content=human_input)]},
            {"configurable": {"thread_id": 1}},
        )
        print("AI: ", result["messages"][-1].content)
