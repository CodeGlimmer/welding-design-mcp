import sqlite3
from pathlib import Path

from welding_app.welding_scenario.welding_scenario import WeldingScenarioModel


def get_latest_parsed_scenario(scenario_file_id: str) -> WeldingScenarioModel | None:
    """获取最新的解析后的焊接场景的model"""
    connect = sqlite3.connect(
        Path(__file__).parent.parent.parent / "databases" / "welding_scenarios.db"
    )
    data = None
    row = None
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
                (scenario_file_id,),
            )
            row = res.fetchone()
    finally:
        connect.close()
    if not row:
        return None
    data = row[0]
    return WeldingScenarioModel.model_validate_json(data)
