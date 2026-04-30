from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek

from welding_app.agents.runtime_config import agent_config
from welding_app.error.error_message import handle_tool_error

from .prompt import system_prompt
from .rag_agent_tools import retriever


def create_rag_agent():
    """工具型知识库检索agent，不会保留长期记忆"""
    model = ChatDeepSeek(
        model="deepseek-v4-flash",
        temperature=0.1,
        extra_body={"thinking": {"type": "enabled"}},
    )
    rag_agent = create_agent(
        model=model,
        tools=[retriever],
        system_prompt=system_prompt(),
        middleware=[handle_tool_error],
    )
    return rag_agent


if __name__ == "__main__":
    import mlflow

    mlflow.set_tracking_uri("http://127.0.0.1:5000")
    mlflow.set_experiment("rag version 3")
    mlflow.autolog()
    rag_agent = create_rag_agent()
    result = rag_agent.invoke(
        {
            "messages": [
                {"role": "user", "content": "蛋炒饭怎么做？"},
            ]
        },
        agent_config(),  # type: ignore
    )
    print(result["messages"][-1])
