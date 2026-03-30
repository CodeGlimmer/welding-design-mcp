from enum import Enum
from re import A
from typing import Annotated, Optional

from pydantic import BaseModel, Field


class Importance(Enum):
    """焊接要求的重要性"""

    NO_LEVEL = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class WeldingRequirement(BaseModel):
    content: Annotated[
        str,
        Field(
            description="""此项用于描述具体的需求
        <examples>
        <example>焊接接头应符合ISO标准</example>
        <example>保证热集中度足够低</example>
        </examples>"""
        ),
    ]
    importance: Annotated[
        Importance,
        Field(
            description="""此项用于描述焊接要求的重要性
            一共有四级
            NO_LEVEL: 无优先级
            LOW: 低优先级
            MEDIUM: 中等优先级
            HIGH: 高优先级"""
        ),
    ]
    target_object: Annotated[
        Optional[str],
        Field(description="""此项用于描述具体的需求对象, 如果没有具体的对象则为None"""),
    ]
    additional_info: Annotated[
        Optional[str],
        Field(description="""此项用于描述额外的信息, 如果没有则为None"""),
    ]


class WeldingTask(BaseModel):
    scenario_id: Annotated[
        str,
        Field(
            description="""此项用于描述场景的ID, 用于关联具体的场景""",
        ),
    ]
    content: Annotated[
        str,
        Field(
            description="""此项用于描述具体的需求内容, 尽可能详细，并且站在整体任务的角度""",
        ),
    ]
    requirements: Annotated[
        list[WeldingRequirement],
        Field(
            description="""此项用于描述具体的需求, 是一个列表, 每个元素都是一个WeldingRequirement对象""",
        ),
    ]
    addtional_info: Annotated[
        Optional[str],
        Field(description="""此项用于描述额外的信息, 如果没有则为None"""),
    ]


class TaskState(Enum):
    PARSING = 0
    DESIGN = 1
    SIMULATION = 2
    FINAL = 3


class TaskExcutionResult(BaseModel):
    """任务执行结果"""

    error: Annotated[
        bool,
        Field(
            description="""此项用于描述任务执行是否出错, 如果出错则为True, 否则为False"""
        ),
    ]
    state: Annotated[
        TaskState,
        Field(description="""此项用于描述任务的执行状态, 是一个TaskState枚举值"""),
    ]
    error_reason: Annotated[
        Optional[str],
        Field(description="""此项用于描述任务执行出错的原因, 如果没有出错则为None"""),
    ]
    solution_id: Annotated[
        Optional[str],
        Field(
            description="""此项用于描述任务执行成功后的解决方案ID, 如果没有则为None"""
        ),
    ]
    reply: Annotated[
        Optional[str],
        Field(description="""此项用于描述任务执行成功后的回复, 如果没有则为None"""),
    ]


if __name__ == "__main__":
    print(WeldingTask.model_json_schema())
