import json
import sqlite3
from pathlib import Path
from typing import Annotated, Literal, Optional, cast

from langchain.tools import tool
from pydantic import BaseModel, Field

from welding_app.agents.sub_agents.welding_scenario_parsing_agent.extract_path_info_from_robx import (
    extract_path_json,
)

from .types import ParsedScenarioOutput, ScenarioFileContentOutput


# ============== Input Schemas ==============

class GetScenarioFileContentInput(BaseModel):
    """tool get_scenario_file_content input schema"""
    id: Annotated[str, Field(description="场景文件ID，用于查询对应的场景文件")]


class GetLatestParsedScenarioInput(BaseModel):
    """tool get_latest_parsed_scenario input schema"""
    source_file_id: Annotated[str, Field(description="原始文件ID，用于查询对应的解析结果")]


# ============== Tools ==============

@tool(
    args_schema=GetScenarioFileContentInput,
    description=f"""获取原始场景文件内容

    根据提供的ID从数据库查询对应的场景文件，并读取文件内容。
    支持txt、json、robx等文件类型。

    Returns:
        ScenarioFileContentOutput:
            <json-schema>
                {ScenarioFileContentOutput.model_json_schema()}
            <json-schema>

    Note: 无论是否发生错误，均通过统一schema返回。错误情况通过返回对象中的id_exists、file_exists等字段标识。""",
)
def get_scenario_file_content(id: str) -> ScenarioFileContentOutput:
    """获取原始场景文件内容"""
    connect = sqlite3.connect(
        Path(__file__).parent.parent.parent.parent / "databases" / "welding_scenario.db"
    )
    file_position = ""
    content = ""
    file_type = "txt"
    try:
        with connect:
            cursor = connect.cursor()
            res = cursor.execute(
                "SELECT file_position FROM local_file WHERE welding_scenario_id = ?",
                (id,),
            )
            row = res.fetchone()
            if row:
                file_position = row[0]
    finally:
        connect.close()

    if not file_position:
        return ScenarioFileContentOutput(
            id=id,
            id_exists=False,
            file_exists=False,
        )

    file_path = Path(file_position)
    if not file_path.exists():
        return ScenarioFileContentOutput(
            id=id,
            id_exists=True,
            file_exists=False,
        )

    file_type = file_path.suffix[1:]
    match file_type:
        case "txt" | "json":
            content = file_path.read_text()
        case "robx":
            content = extract_path_json(str(file_path))
            if not content:
                content = "场景文件解析失败"
        case _:
            content = "文件类型不支持"

    return ScenarioFileContentOutput(
        id=id,
        id_exists=True,
        file_exists=True,
        content=content,
        file_type=cast(Optional[Literal["txt", "json", "robx"]], file_type),
    )


@tool(
    args_schema=GetLatestParsedScenarioInput,
    description=f"""根据原始文件ID获取最新解析的场景数据

    从解析后的场景数据库中，查找与源文件ID关联的最新解析结果。

    Returns:
        ParsedScenarioOutput:
            <json-schema>
                {ParsedScenarioOutput.model_json_schema()}
            <json-schema>

    Note: 无论是否发生错误，均通过统一schema返回。如果没有找到对应的解析结果会返回exists=False。""",
)
def get_latest_parsed_scenario(source_file_id: str) -> ParsedScenarioOutput:
    """根据原始文件ID获取最新解析的场景数据"""
    connect = sqlite3.connect(
        Path(__file__).parent.parent.parent.parent
        / "databases"
        / "welding_scenarios.db"
    )
    try:
        with connect:
            cursor = connect.cursor()
            res = cursor.execute(
                """
                SELECT data FROM welding_scenarios
                WHERE source_file_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (source_file_id,),
            )
            row = res.fetchone()
            if not row:
                return ParsedScenarioOutput(exists=False, data=None)

            return ParsedScenarioOutput(exists=True, data=json.loads(row[0]))
    finally:
        connect.close()
