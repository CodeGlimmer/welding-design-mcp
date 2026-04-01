from langchain.tools import tool
from langchain_core.messages import HumanMessage
from sqlalchemy import desc

from .scenario_operations import get_latest_parsed_scenario
from .sub_agents.welding_scenario_parsing_agent.parsing_agent import (
    create_parsing_agent,
)
from .sub_agents.welding_scenario_parsing_agent.types import ParsingAgentOutput
from .sub_agents.welding_scenario_parsing_checker.checker_agent import (
    create_checker_agent,
)
from .types import TaskExcutionResult, TaskState, WeldingTask


@tool(
    args_schema=WeldingTask,
    description=f"""将焊接任务对象传入该工具，下面会执行该任务

    Returns:
        返回的对象为TaskExcutionResult:
            <json-schema>
                {TaskExcutionResult.model_json_schema()}
            <json-schema>""",
)
def execute_welding_task(
    scenario_id: str, content: str, requirements: list[dict], addtional_info: str | None
):
    """将焊接任务对象传入该工具，下面会执行该任务"""

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

    # 获取最终的解析场景id
    # TODO: 完善成真正的业务逻辑
    print("场景id：")
    print(pasing_agent_res["structured_response"].parsed_model_id)

    # 获取解析后的场景model
    scenario_model = get_latest_parsed_scenario(scenario_id)
    if not scenario_model:
        return TaskExcutionResult(
            error=True,
            state=TaskState.DESIGN,
            error_reason="设计阶段为能找到解析提取的焊接场景model",
            reply=None,
            solution_id=None,
        )
