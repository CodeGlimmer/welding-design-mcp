import uuid

from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain.messages import HumanMessage
from langchain_deepseek import ChatDeepSeek

from welding_app.agents.types import WeldingRequirement
from welding_app.error.error_message import handle_tool_error

from .plan_agent_tools import (
    design_welding_plan_toolkit,
    generate_welding_plan as generate_welding_plan_tool,
    get_welding_scenario,
    query_welding_infomation,
)
from .prompt import system_prompt, todo_list_prompt
from .types import WeldingPlanResult


class WeldingPlanStructuredOutputError(RuntimeError):
    """方案 Agent 未返回 WeldingPlanResult 结构化结果。"""


def create_plan_agent(response_format: type | ToolStrategy | None = None):

    model = ChatDeepSeek(model="deepseek-chat", temperature=0.1, top_p=0.2)

    plan_agent = create_agent(
        model=model,
        system_prompt=system_prompt(),
        tools=[generate_welding_plan_tool, query_welding_infomation, get_welding_scenario]
        + design_welding_plan_toolkit(),
        middleware=[
            handle_tool_error,
            TodoListMiddleware(
                system_prompt=todo_list_prompt(),
            ),  # type: ignore
        ],
        response_format=response_format,
    )
    return plan_agent


def _format_requirements(requirements: list[WeldingRequirement]) -> str:
    """将约束要求列表格式化为智能体可读的文本"""
    if not requirements:
        return "无特殊约束要求"

    importance_label = {0: "无", 1: "低", 2: "中", 3: "高"}

    lines = []
    for i, req in enumerate(requirements, 1):
        lines.append(f"{i}. [{importance_label[req.importance.value]}优先级] {req.content}")
        if req.target_object:
            lines.append(f"   - 目标对象: {req.target_object}")
        if req.additional_info:
            lines.append(f"   - 补充说明: {req.additional_info}")
    return "\n".join(lines)


def run_welding_plan_design(
    scenario_id: str,
    content: str,
    requirements: list[WeldingRequirement],
    additional_info: str | None = None,
) -> WeldingPlanResult:
    """执行完整的焊接方案设计流程

    调用 plan agent，完成焊接顺序规划、工艺参数设计、方案保存的全流程。
    会被 main_agent_tools.py 中的 execute_welding_task 在设计阶段调用。

    Args:
        scenario_id: 已完成解析的场景ID
        content: 任务内容描述，定义焊接方案的整体目标和场景
        requirements: 约束要求列表
        additional_info: 额外信息，包含补充说明或上下文

    Returns:
        WeldingPlanResult: 包含 plan_id 和完整设计报告
    """

    requirements_text = _format_requirements(requirements)

    task_prompt = f"""# 焊接方案设计任务

## 场景ID
{scenario_id}

## 任务内容
{content}

## 约束要求
{requirements_text}

## 额外信息
{additional_info or "无"}

---
请按照你的工作流程完成焊接方案的设计。"""

    agent = create_plan_agent(response_format=ToolStrategy(WeldingPlanResult))
    result = agent.invoke(
        {"messages": [HumanMessage(content=task_prompt)]},
        {
            "configurable": {"thread_id": str(uuid.uuid4())},
            "recursion_limit": 100,
        },
    )

    structured_response = result.get("structured_response")
    if structured_response is None:
        raise WeldingPlanStructuredOutputError(
            f"方案 Agent 未返回 structured_response。result keys: {', '.join(result.keys())}"
        )

    return structured_response


if __name__ == "__main__":
    pass
    # import mlflow
    # from langchain.messages import HumanMessage

    # mlflow.set_tracking_uri("http://127.0.0.1:5000")
    # mlflow.set_experiment("plan_agent v2")
    # mlflow.autolog()

    # agent = create_plan_agent()
    # while True:
    #     human_input = input("Human: ")
    #     if human_input in {"q", "quit", "exit"}:
    #         break
    #     result = agent.invoke(
    #         {"messages": [HumanMessage(content=human_input)]},
    #         {"configurable": {"thread_id": 1}},
    #     )
    #     print("AI: ", result["messages"][-1].content)
