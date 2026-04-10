import sqlite3
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class GenerateWeldingPlanInputModel(BaseModel):
    """tool generate_welding_plan input schema"""

    scenario_id: Annotated[
        str,
        Field(
            description="场景id，根据此id，tool可以寻找到场景对象，进一步对场景对象中的焊点进行排序"
        ),
    ]

    @field_validator("scenario_id")
    @classmethod
    def check_id_exists(cls, scenario_id: str):
        """检查id是否存在"""
        connect = sqlite3.connect(
            Path(__file__).parent.parent.parent.parent.parent
            / "welding_app"
            / "data"
            / "welding_scenarios.db"
        )
        try:
            with connect:
                cursor = connect.cursor()
                res = cursor.execute(
                    "select data from welding_scenarios where id = ?",
                    (scenario_id,),
                )
                res = res.fetchone()
                if not res:
                    raise ValueError("不存在符合该id的场景")
        finally:
            connect.close()
        return scenario_id


class QueryWeldingInformationInputModel(BaseModel):
    """tool query_welding_information input schema"""

    query: Annotated[
        str,
        Field(
            description="""查询内容,一个语义清晰，目的完整的句子

            <examples>
            <example>帮我查找电流与材料之间的关系</example>
            <example>焊接材料是铝，如何设置焊接电流</example>
            </examples>
            """
        ),
    ]


class GetWeldingScenarioInputModel(BaseModel):
    """tool get_welding_scenario input schema"""

    scenario_id: Annotated[
        str,
        Field(description="传入场景id，本工具会返回焊接场景对象"),
    ]

    @field_validator("scenario_id")
    @classmethod
    def check_id_exists(cls, scenario_id: str):
        """检查id是否存在"""
        connect = sqlite3.connect(
            Path(__file__).parent.parent.parent.parent.parent
            / "welding_app"
            / "data"
            / "welding_scenarios.db"
        )
        try:
            with connect:
                cursor = connect.cursor()
                res = cursor.execute(
                    "select data from welding_scenarios where id = ?",
                    (scenario_id,),
                )
                res = res.fetchone()
                if not res:
                    raise ValueError("不存在符合该id的场景")
        finally:
            connect.close()
        return scenario_id
