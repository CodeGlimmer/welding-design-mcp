import sqlite3
from pathlib import Path
from typing import Annotated

from langchain.tools import tool
from pydantic import Field

from .types import GetScenarioFileContentOutput


@tool
def get_scenario_file_content(
    id: Annotated[str, Field(description="模型ID")],
) -> GetScenarioFileContentOutput:
    """获取场景文件内容"""
    # 检查数据库中是否保存场景
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
                "select file_position from local_file where id = ?", (id,)
            )
            file_position = res.fetchone()[0]
    finally:
        connect.close()
    if not file_position:
        # id 不存在
        return GetScenarioFileContentOutput(id=id, id_exists=False)
    # 测试文件是否存在
    file_path = Path(file_position)
    if not file_path.exists():
        return GetScenarioFileContentOutput(
            id=id,
            id_exists=True,
            file_exists=False,
        )
    # 检测文件类型
    file_type = file_path.suffix[1:]
    # 读取文件内容
    match file_type:
        case "txt" | "json":
            content = file_path.read_text()
        case "robx":
            # TODO: 完成robx解析函数
            content = ""
        case _:
            content = "文件类型不支持"

    return GetScenarioFileContentOutput(
        id=id,
        id_exsits=True,
        file_exists=True,
        content=content,
    )
