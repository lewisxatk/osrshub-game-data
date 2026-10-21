"""Tests for the generated game-data query interface."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import query_game_data as query


class QueryGameDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)
        (self.directory / "equipment-stats.json").write_text(json.dumps([
            {"id": 4151, "name": "Abyssal whip", "bonuses": {"attack_slash": 82}},
            {"id": 11802, "name": "Armadyl godsword", "bonuses": {"attack_slash": 132}},
        ]), encoding="utf-8")
        (self.directory / "quest-relationships.json").write_text(json.dumps([
            {"quest_key": "dragon_slayer", "name": "Dragon Slayer", "prerequisites": [],
             "dependents": [{"quest_key": "legends_quest", "name": "Legends' Quest"}],
             "unresolved_requirements": [], "skill_requirements": [], "source_url": "https://example.com"}
        ]), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_search_is_case_insensitive(self):
        result = query.run_query("equipment-stats", query="WHIP", dist_dir=self.directory)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["match_count"], 1)
        self.assertEqual(result["results"][0]["id"], 4151)

    def test_exact_id_and_nested_field_search(self):
        result = query.run_query("equipment-stats", record_id=4151, field="bonuses.attack_slash",
                                 query="82", dist_dir=self.directory)
        self.assertEqual(result["match_count"], 1)
        self.assertEqual(result["results"][0]["name"], "Abyssal whip")

    def test_relationship_search_finds_dependents(self):
        result = query.run_query("quest-relationships", query="Legends", dist_dir=self.directory)
        self.assertEqual(result["match_count"], 1)
        self.assertEqual(result["results"][0]["name"], "Dragon Slayer")

    def test_missing_dataset_is_unknown_not_empty_success(self):
        result = query.run_query("quests", query="dragon", dist_dir=self.directory)
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("not present", result["warning"])

    def test_bad_dataset_shape_fails(self):
        (self.directory / "weapons.json").write_text('{"not":"an array"}', encoding="utf-8")
        result = query.run_query("weapons", query="whip", dist_dir=self.directory)
        self.assertEqual(result["status"], "failed")

    def test_unknown_dataset_is_rejected(self):
        result = query.run_query("not-a-dataset", query="x", dist_dir=self.directory)
        self.assertEqual(result["status"], "failed")
        self.assertIn("supported_datasets", result)


if __name__ == "__main__":
    unittest.main()
