from langchain.tools import tool

from .sub_agents.welding_scenario_parsing_agent.parsing_agent import (
    create_parsing_agent,
)
from .types import WeldingTask


@tool(args_schema=WeldingTask)
def execute_welding_task(
    senario_id: str, requirements: list[dict], addtional_info: str | None
):
    """将焊接任务对象传入该工具，下面会执行该任务"""

    # 场景构建智能体与场景构建检测智能体协同工作，当双方都认为工作完成则进入设计阶段
    parsing_agent = create_parsing_agent()

    result = parsing_agent.invoke(input={"messages": []})
