from typing import Annotated, Literal, Optional

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


class GetScenarioFileContentOutput(BaseModel):
    """场景文件内容查询输出类型

    层次结构介绍：
        id_exists: 如果场景文件ID存在，则返回True，否则返回False, 那么剩下的信息都没有看的价值
        file_exists: 如果场景文件存在，则返回True，否则返回False，说明这条id虽然存在但是无效
    """

    id: Annotated[str, Field(description="场景文件ID")] = ""
    id_exists: Annotated[bool, Field(description="场景文件ID是否存在")] = False
    file_exsits: Annotated[bool, Field(description="场景文件是否存在")]
    file_type: Annotated[
        Optional[Literal["txt", "json", "robx"]],
        Field(
            description="场景文件类型，可选值为txt、json、robx，如果文件类型不支持，则返回空字符串"
        ),
    ] = None
    content: Annotated[
        str,
        Field(
            description="场景文件内容，多数情况下表现为json格式，也有txt格式的情况，如果文件类型不支持，则返回提示：'文件类型不支持',如果robx文件解析失败则会返回'场景文件解析失败'的提示"
        ),
    ] = ""


class SaveScenarioOutput(BaseModel):
    scenario_id: Annotated[str, Field(description="场景UUID")]
    source_file_id: Annotated[str, Field(description="源文件ID")]
    solder_joints_count: Annotated[int, Field(description="焊点数量")]
    weld_seams_count: Annotated[int, Field(description="焊缝数量")]
