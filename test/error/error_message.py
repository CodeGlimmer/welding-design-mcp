from enum import Enum

from pydantic import BaseModel


class ToolErrorCode(Enum):
    ENOENT = "文件不存在"
    EACCES = "权限拒绝"
    INVALID_INPUT = "输入格式错误"
    TIMEOUT = "工具超时"
    SIZE_LIMIT = "大小超出限制"
    UNKNOWN = "未知错误"


class ToolExceptionModel(BaseModel):
    """此model应该被content包含，并在ToolMessage中附上tool_call_id信息"""

    code: ToolErrorCode
    details: str | None
    input_args: dict | None
    content: str
    tool_name: str
    retryable: bool


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

    def to_model(self):
        return ToolExceptionModel(
            code=self.code,
            details=self.details,
            input_args=self.input_args,
            content=self.content,
            tool_name=self.tool_name,
            retryable=self.retryable,
        )
