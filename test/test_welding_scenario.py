import unittest
import sqlite3
import tempfile
import shutil
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from welding_app.welding_scenario.solder_joint import (
    GeometryPointModel,
    SolderJointModel,
)
from welding_app.welding_scenario.weld_seam import (
    GeometryStraightLineModel,
    WeldSeamModel,
)
from welding_app.welding_scenario.welding_scenario import WeldingScenarioModel


class TestWeldingScenarioModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = Path(tempfile.mkdtemp())
        cls.db_path = cls.test_dir / "test_welding_scenarios.db"
        cls.source_file_id = "test_source_file_001"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_welding_scenario_model_to_json(self):
        point1 = GeometryPointModel(x=0.0, y=0.0, z=0.0, id="point1")
        point2 = GeometryPointModel(x=10.0, y=0.0, z=0.0, id="point2")

        solder_joint = SolderJointModel(
            position=point1,
            name="焊点1",
        )

        line = GeometryStraightLineModel(
            start_point=point1,
            end_point=point2,
            id="line1",
        )

        weld_seam = WeldSeamModel(
            id="seam1",
            name="焊缝1",
            line=line,
            solder_joints=[solder_joint],
        )

        scenario = WeldingScenarioModel(
            solder_joints=[solder_joint],
            weld_seams=[weld_seam],
        )

        json_str = scenario.model_dump_json()
        self.assertIsInstance(json_str, str)
        self.assertIn("solder_joints", json_str)
        self.assertIn("weld_seams", json_str)

    def test_welding_scenario_to_welding_scenario(self):
        point = GeometryPointModel(x=1.0, y=2.0, z=3.0, id="p1")
        solder_joint = SolderJointModel(position=point, name="test")

        scenario = WeldingScenarioModel(
            solder_joints=[solder_joint],
            weld_seams=[],
        )

        result = scenario.to_welding_scenario()
        self.assertIsInstance(result, set)
        self.assertEqual(len(result), 1)

    def test_database_insertion(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS welding_scenarios "
            "(id TEXT PRIMARY KEY, source_file_id TEXT NOT NULL, data TEXT NOT NULL)"
        )

        point = GeometryPointModel(x=0.0, y=0.0, z=0.0, id="point1")
        solder_joint = SolderJointModel(position=point, name="焊点1")

        scenario = WeldingScenarioModel(
            solder_joints=[solder_joint],
            weld_seams=[],
        )

        import uuid

        scenario_id = str(uuid.uuid4())

        conn.execute(
            "INSERT INTO welding_scenarios (id, source_file_id, data) VALUES (?, ?, ?)",
            (scenario_id, self.source_file_id, scenario.model_dump_json()),
        )
        conn.commit()
        conn.close()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT id, source_file_id, data FROM welding_scenarios WHERE id = ?",
            (scenario_id,),
        )
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], scenario_id)
        self.assertEqual(row[1], self.source_file_id)
        self.assertIn("solder_joints", row[2])


if __name__ == "__main__":
    unittest.main()
