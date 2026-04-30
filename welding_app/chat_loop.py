# import mlflow
from langchain_core.messages import HumanMessage

from welding_app.agents.main_agent import create_main_agent
from welding_app.agents.runtime_config import agent_config

# mlflow.set_tracking_uri("http://127.0.0.1:5000")
# mlflow.set_experiment("version 4")
# mlflow.autolog()


def main():
    agent = create_main_agent()
    while True:
        human_input = input("Human: ")
        if human_input in {"q", "quit", "exit"}:
            break
        result = agent.invoke(
            {"messages": [HumanMessage(content=human_input)]},
            agent_config(thread_id=1),
        )
        print("AI: ", result["messages"][-1].content)


if __name__ == "__main__":
    main()
