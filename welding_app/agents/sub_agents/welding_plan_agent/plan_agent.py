from pathlib import Path

from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek


def create_plan_agent():

    model = ChatDeepSeek(model="deepseek-chat", temperature=0.1)

    system_prompt_path = (
        Path(__file__).parent.parent.parent.parent
        / "prompts"
        / "to_welding_plan_agent"
        / "system_prompt.md"
    )

    plan_agent = create_agent(
        model=model, system_prompt=system_prompt_path.read_text(), tools=[]
    )
    return plan_agent
