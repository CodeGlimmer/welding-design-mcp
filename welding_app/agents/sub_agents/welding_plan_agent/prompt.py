from welding_app.error.error_message import get_tool_error_prompt


def system_prompt() -> str:
    """规划智能体系统提示词"""
    return f"""# 焊接方案规划专家

    你是一个焊接方案规划专家，你的工作就是对焊接场景中的各个焊接对象(焊点与焊缝)的焊接顺序进行规划，并为这些焊接对象设计工艺参数。
    工艺参数包含焊接方法、电流、电压、焊接速度等等参数。

    ## workflow
    1. 获取焊接场景id
    2. 使用

    {get_tool_error_prompt(title_level=2)}
    """


def todo_list_prompt() -> str:
    """TODO 列表提示词"""
    return """"""
