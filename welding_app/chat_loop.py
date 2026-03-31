import mlflow
from langchain_core.messages import HumanMessage

from welding_app.agents.main_agent import create_main_agent

mlflow.set_tracking_uri("http://127.0.0.1:5000")
mlflow.set_experiment("version 0")
mlflow.autolog()


def main():
    agent = create_main_agent()
    while True:
        human_input = input("Human: ")
        if human_input in {"q", "quit", "exit"}:
            break
        result = agent.invoke(
            {"messages": [HumanMessage(content=human_input)]},
            {"configurable": {"thread_id": 1}},
        )
        print("AI: ", result["messages"][-1].content)


if __name__ == "__main__":
    main()
