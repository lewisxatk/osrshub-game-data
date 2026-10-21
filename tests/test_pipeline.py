"""Smoke tests for helper behavior; run with python -m unittest discover -s tests."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_dataset
class PipelineTests(unittest.TestCase):
    def test_numeric_id_variants(self):
        self.assertEqual(build_dataset.numeric_id({"id":"4151"}), 4151)
        self.assertEqual(build_dataset.numeric_id({"item_id": 11802}), 11802)
        self.assertIsNone(build_dataset.numeric_id({"id":"not-an-id"}))
    def test_name_variants(self):
        self.assertEqual(build_dataset.name_of({"name":"Whip"}), "Whip")
        self.assertEqual(build_dataset.name_of({"item_name":"Rune platebody"}), "Rune platebody")
        self.assertEqual(build_dataset.name_of({}), "")
if __name__ == "__main__": unittest.main()
