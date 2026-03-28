import json
import sqlite3
from pathlib import Path
from typing import Literal, Optional, cast

from langchain.tools import tool
from pydantic import Field

from welding_app.agents.sub_agents.welding_scenario_parsing_agent.extract_path_info_from_robx import (
    extract_path_json,
)

from .types import ParsedScenarioOutput, ScenarioFileContentOutput


@tool(args_schema=ScenarioFileContentOutput)
def get_scenario_file_content(
    id: str,
) -> ScenarioFileContentOutput:
    """获取原始场景文件内容"""
    connect = sqlite3.connect(
        Path(__file__).parent.parent.parent.parent
        / "databases"
        / "welding_scenarios.db"
    )
    file_position = ""
    content = ""
    file_type = "txt"
    try:
        with connect:
            cursor = connect.cursor()
            res = cursor.execute(
                "SELECT file_position FROM local_file WHERE id = ?", (id,)
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


@tool(args_schema=ParsedScenarioOutput)
def get_latest_parsed_scenario(
    source_file_id: str,
) -> ParsedScenarioOutput:
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
