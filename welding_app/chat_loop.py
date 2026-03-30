from langchain_core.messages import HumanMessage

from welding_app.agents.main_agent import create_main_agent


def main():
    agent = create_main_agent()
    while True:
        human_input = input("Human: ")
        result = agent.invoke(
            {"messages": [HumanMessage(content=human_input)]},
            {"configurable": {"thread_id": 1}},
        )
        print("AI: ", result["messages"][-1].content)


if __name__ == "__main__":
    main()
