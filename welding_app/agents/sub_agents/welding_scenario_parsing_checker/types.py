from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field


class CheckerOutput(BaseModel):
    approved: Annotated[
        bool,
        Field(description="Whether the parsed scenario passes verification"),
    ]
    diff_report: Annotated[
        str,
        Field(
            description="Markdown format diff report listing missing and incorrect items"
        ),
    ]


class ScenarioFileContentOutput(BaseModel):
    id: Annotated[str, Field(description="场景文件ID")] = ""
    id_exists: Annotated[bool, Field(description="场景文件ID是否存在")] = False
    file_exists: Annotated[bool, Field(description="文件是否存在")] = False
    file_type: Annotated[
        Optional[Literal["txt", "json", "robx"]],
        Field(description="文件类型"),
    ] = None
    content: Annotated[str, Field(description="文件内容")] = ""


class ParsedScenarioOutput(BaseModel):
    exists: Annotated[bool, Field(description="解析结果是否存在")] = False
    data: Annotated[Optional[dict], Field(description="解析后的场景数据")] = None
