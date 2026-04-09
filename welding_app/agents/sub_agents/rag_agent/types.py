from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class RetrieverInput(BaseModel):
    """焊接知识检索输入"""

    query: Annotated[str, Field(description="将被检索的关键词或者语句")]
    res_len: Annotated[
        int,
        Field(description="检索结果的最大长度, 必要时可以减少检索的长度增加检索的次数"),
    ]

    @field_validator("res_len")
    @classmethod
    def res_len_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("res_len must be positive")
        return v


class RetrieverOutput(BaseModel):
    """焊接知识检索输出"""

    results: Annotated[
        list[str],
        Field(description="检索到的结果列表"),
    ]
