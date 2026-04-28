import sqlite3
from pathlib import Path

from langchain.tools import tool
from langchain_core.messages import HumanMessage

from .scenario_operations import get_latest_parsed_scenario
from .sub_agents.welding_plan_agent.plan_agent import run_welding_plan_design
from .sub_agents.welding_scenario_parsing_agent.parsing_agent import (
    create_parsing_agent,
)
from .sub_agents.welding_scenario_parsing_agent.types import ParsingAgentOutput
from .sub_agents.welding_scenario_parsing_checker.checker_agent import (
    create_checker_agent,
)
from .types import TaskExcutionResult, TaskState, WeldingRequirement, WeldingTask


def _fetch_saved_welding_plan_json(plan_id: str) -> str | None:
    db_path = Path(__file__).parent.parent / "databases" / "welding_plan.db"
    if not db_path.exists():
        return None

    connect = sqlite3.connect(db_path)
    try:
        with connect:
            cursor = connect.cursor()
            try:
                row = cursor.execute(
                    "SELECT full_data_json FROM welding_plans WHERE plan_id = ?",
                    (plan_id,),
                ).fetchone()
            except sqlite3.Error:
                return None
    finally:
        connect.close()

    if not row:
        return None
    return row[0]


def _format_success_reply(
    plan_id: str,
    parsed_scenario_id: str,
    report: str,
    welding_plan_json: str | None,
) -> str:
    plan_content = welding_plan_json or "未能从数据库读取到完整焊接方案 JSON，请通过方案 ID 查询。"
    return f"""焊接方案设计完成。

方案 ID: {plan_id}
解析后场景 ID: {parsed_scenario_id}

设计报告:
{report}

焊接方案 JSON:
```json
{plan_content}
```"""


@tool(
    args_schema=WeldingTask,
    description=f"""执行焊接任务

    将焊接任务对象传入该工具，启动场景解析和检测的协同工作流程。
    场景构建智能体与场景构建检测智能体会协同工作，当双方都认为工作完成后进入设计阶段。

    Returns:
        TaskExcutionResult:
            <json-schema>
                {TaskExcutionResult.model_json_schema()}
            <json-schema>

    Note: 无论是否发生错误，均通过统一schema返回。错误情况通过返回对象中的error字段标识。""",
)
def execute_welding_task(
    scenario_id: str,
    content: str,
    requirements: list[WeldingRequirement],
    addtional_info: str | None,
) -> TaskExcutionResult:  # type: ignore
    """执行焊接任务"""

    # 场景构建智能体与场景构建检测智能体协同工作，当双方都认为工作完成则进入设计阶段
    parsing_agent = create_parsing_agent()
    parsing_checker = create_checker_agent()

    conversation_limit = 3
    conversation_time = 0

    init_message = HumanMessage(
        content=f"场景id是'{scenario_id}', 请你按照要求对场景进行解析"
    )
    pasing_agent_res = parsing_agent.invoke(
        input={"messages": [init_message]}, config={"configurable": {"thread_id": 1}}
    )
    while conversation_time < conversation_limit:
        parsing_agent_output: ParsingAgentOutput = pasing_agent_res[
            "structured_response"
        ]
        if parsing_agent_output.error:
            return TaskExcutionResult(
                error=True,
                state=TaskState.PARSING,
                error_reason=parsing_agent_output.error,
                solution_id=None,
                reply=None,
            )
        # 调用checker进行检查
        checker_res = parsing_checker.invoke(
            input={
                "messages": [
                    HumanMessage(
                        content=f"请检查以下解析结果是否正确，场景文件id为{scenario_id}"
                    )
                ]
            },
            config={"configurable": {"thread_id": 1}},
        )
        if checker_res["structured_response"].approved:
            break

        pasing_agent_res = parsing_agent.invoke(
            input={
                "messages": [
                    HumanMessage(
                        content=f"""你的反对者对比了原来的文件(id为{scenario_id})与你的解析结果，给出了对比报告:
                        {checker_res["structured_response"].diff_report}
                        请根据对比报告修改你的解析结果。
                    """
                    )
                ]
            },
            config={"configurable": {"thread_id": 1}},
        )
        conversation_time += 1

    final_parsing_output: ParsingAgentOutput = pasing_agent_res["structured_response"]
    if final_parsing_output.error:
        return TaskExcutionResult(
            error=True,
            state=TaskState.PARSING,
            error_reason=final_parsing_output.error,
            solution_id=None,
            reply=None,
        )

    parsed_scenario_id = final_parsing_output.parsed_model_id
    if not parsed_scenario_id:
        return TaskExcutionResult(
            error=True,
            state=TaskState.PARSING,
            error_reason="场景解析已结束，但未返回 parsed_model_id，无法进入设计阶段",
            reply=None,
            solution_id=None,
        )

    # 获取解析后的场景model，验证场景是否就绪
    if not get_latest_parsed_scenario(scenario_id):
        return TaskExcutionResult(
            error=True,
            state=TaskState.DESIGN,
            error_reason="设计阶段未能找到解析提取的焊接场景model",
            reply=None,
            solution_id=None,
        )

    design_result = run_welding_plan_design(
        scenario_id=parsed_scenario_id,
        content=content,
        requirements=requirements,
        additional_info=addtional_info,
    )

    if not design_result.plan_id:
        return TaskExcutionResult(
            error=True,
            state=TaskState.DESIGN,
            error_reason="焊接方案设计完成但未能获取到 plan_id，详见 report",
            reply=design_result.report,
            solution_id=None,
        )

    welding_plan_json = _fetch_saved_welding_plan_json(design_result.plan_id)

    return TaskExcutionResult(
        error=False,
        state=TaskState.DESIGN,
        error_reason=None,
        solution_id=design_result.plan_id,
        reply=_format_success_reply(
            plan_id=design_result.plan_id,
            parsed_scenario_id=parsed_scenario_id,
            report=design_result.report,
            welding_plan_json=welding_plan_json,
        ),
    )
