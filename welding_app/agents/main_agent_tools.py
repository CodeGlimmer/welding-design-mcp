from langchain.tools import tool

from .welding_task import WeldingTask


@tool(args_schema=WeldingTask)
def execute_welding_task(
    senario_id: str, requirements: list[dict], addtional_info: str | None
):
    """将焊接任务对象传入该工具，下面会执行该任务"""
    # TODO: 任务执行工具
