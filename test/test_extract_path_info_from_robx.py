import unittest
import tempfile
import shutil
from pathlib import Path
import zipfile

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from welding_app.agents.sub_agents.welding_scenario_parsing_agent.extract_path_info_from_robx import (
    extract_path_json,
)


class TestExtractPathJson(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = Path(tempfile.mkdtemp())
        cls.real_robx_path = "/Users/tanghuijia/Desktop/点焊.robx"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_nonexistent_file(self):
        result = extract_path_json("/path/does/not/exist.robx")
        self.assertEqual(result, "")

    def test_real_file(self):
        result = extract_path_json(self.real_robx_path)
        if Path(self.real_robx_path).exists():
            self.assertIsInstance(result, str)
        else:
            self.assertEqual(result, "")

    def test_invalid_zip(self):
        invalid_path = self.test_dir / "invalid.zip"
        invalid_path.write_bytes(b"not a zip file")
        result = extract_path_json(str(invalid_path))
        self.assertEqual(result, "")

    def test_valid_zip_without_path_json(self):
        zip_path = self.test_dir / "no_path_json.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("data/Other.json", '{"key": "value"}')
        result = extract_path_json(str(zip_path))
        self.assertEqual(result, "")

    def test_valid_zip_with_path_json(self):
        zip_path = self.test_dir / "valid.zip"
        test_content = '{"paths": [{"id": 1}], "version": "1.0"}'
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("data/Path.json", test_content)
        result = extract_path_json(str(zip_path))
        self.assertEqual(result, test_content)


if __name__ == "__main__":
    unittest.main()
