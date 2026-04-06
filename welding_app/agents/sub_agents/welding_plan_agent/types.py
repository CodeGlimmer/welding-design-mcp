from typing import Annotated
import sqlite3
from pathlib import Path

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
