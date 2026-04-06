from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages.human import HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.memory import InMemorySaver

from welding_app.prompts.to_main_agent import (
    get_summarization_prompt,
    get_task_prompt,
)

from .main_agent_tools import execute_welding_task


def create_main_agent():
    """创建于外部agent对话的主agent"""

    # 初始化deepseek model
    model = ChatDeepSeek(
        model="deepseek-chat",
        temperature=0.1,
    )

    agent = create_agent(
        model=model,
        tools=[execute_welding_task],
        checkpointer=InMemorySaver(),
        system_prompt=get_task_prompt(),
        middleware=[
            SummarizationMiddleware(
                model=model,
                trigger=("tokens", 24000),
                keep=("messages", 35),
                summary_prompt=get_summarization_prompt(),
            ),
        ],
    )
    return agent


def main():
    agent = create_main_agent()
    res = agent.invoke(
        input={"messages": [HumanMessage(content="你好")]},
        config={"configurable": {"thread_id": "1"}},
    )
    print(res["messages"][-1].content)


if __name__ == "__main__":
    main()
