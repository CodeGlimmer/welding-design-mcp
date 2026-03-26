from typing import Annotated

from pydantic import BaseModel, Field


class ParsingAgentOutput(BaseModel):
    error: Annotated[
        str,
        Field(
            description="如果发生报错，请说明错误原因，否则为空字符串，如果原因不明则直接填写‘原因不明’"
        ),
    ] = ""
    parsed_model_id: Annotated[
        str, Field(description="解析成功后返回的模型ID，否则为空字符串")
    ] = ""
