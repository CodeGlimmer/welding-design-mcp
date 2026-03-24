from langchain.agents import create_agent
from langchain_core.messages.human import HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.memory import InMemorySaver


def create_main_agent():
    model = ChatDeepSeek(
        model="deepseek-chat",
        temperature=0.1,
    )
    agent = create_agent(
        model=model,
        tools=[],
        checkpointer=InMemorySaver(),
    )
    return agent


def main():
    agent = create_main_agent()
    res = agent.invoke(
        input={"messages": [HumanMessage(content="你好")]},
        config={"configurable": {"thread_id": "1"}},
    )
    print(res)


if __name__ == "__main__":
    main()
