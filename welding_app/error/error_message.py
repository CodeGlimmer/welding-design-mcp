from typing import Annotated, Optional
from enum import Enum

from pydantic import BaseModel, Field


class ToolErrorCode(Enum):
    ENOENT = "文件不存在"
    EACCES = "权限拒绝"
    INVALID_INPUT = "输入格式错误"
    TIMEOUT = "工具超时"
    SIZE_LIMIT = "大小超出限制"
    UNKNOWN = "未知错误"


class ToolExceptionModel(BaseModel):
    """工具异常信息"""

    code: Annotated[
        ToolErrorCode,
        Field(
            description='工具错误码，大致对异常类型进行分类'
        )
    ]
    details: Annotated[
        Optional[str],
        Field(
            description='错误的一些细节，你不能从中获取一些完整的错误原因，但是这里会提供一些细节，或者发现，据此你可以合理的推断更底层的错误'
        )
    ]
    input_args: Annotated[
        Optional[dict],
        Field(
            description='你使用该工具的输入参数'
        )
    ]
    content: Annotated[str, Field(description='工具报错的主要信息，你因该重点看这里')]
    tool_name: Annotated[str, Field(description='发生报错的工具名')]
    retryable: Annotated[bool, Field(description='是否可以重新尝试运行，一些错误比如网络异常等是可以多次尝试的，另外的报错比如文件不存在是不可以多次尝试的。某些tool多次调用都发生报错，及时可以重试也不建议')]


class ToolException(Exception):
    """工具执行异常"""

    def __init__(
        self,
        message: str,
        code: ToolErrorCode,
        details: str | None,
        input_args: dict | None,
        content: str,
        tool_name: str,
        retryable: bool,
    ):
        super().__init__(message)
        self.code = code
        self.details = details
        self.input_args = input_args
        self.content = content
        self.tool_name = tool_name
        self.retryable = retryable
        self.expose_to_agent: list[str] = []

    def to_model(self):
        return ToolExceptionModel(
            code=self.code,
            details=self.details,
            input_args=self.input_args,
            content=self.content,
            tool_name=self.tool_name,
            retryable=self.retryable,
        )

def get_tool_error_prompt():
    return f"""# 工具错误
    当工具运行过程中发生报错时，工具不会按照预定义的output schema返回结果，而是会按照一下格式返回错误信息：

    error-schema:
    {ToolExceptionModel.model_json_schema()}
    """