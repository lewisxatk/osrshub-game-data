"""Tests for safe, bounded queries over core and extended generated datasets."""
import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from query_game_data import run_query, search_rows, DATASETS


class QueryGameDataTests(unittest.TestCase):
    def test_search_nested_fields_and_casefold(self):
        rows = [{"id": 1, "name": "Dragon scimitar", "bonuses": {"attack_slash": 8}}, {"id": 2, "name": "Rune sword", "bonuses": {"attack_slash": 45}}]
        self.assertEqual(search_rows(rows, "dragon")[0]["id"], 1)
        self.assertEqual(search_rows(rows, "45", field="bonuses.attack_slash")[0]["id"], 2)

    def test_id_filter_accepts_extended_identity_fields(self):
        rows = [{"npc_id": 123, "source_key": "123"}, {"id": 1234}]
        self.assertEqual(search_rows(rows, record_id=123)[0]["npc_id"], 123)

    def test_exact_source_key_filter(self):
        rows = [{"source_key": "Grand Tree Groceries", "shop_name": "Grand Tree Groceries"}, {"source_key": "other"}]
        self.assertEqual(search_rows(rows, key="grand tree groceries"), [rows[0]])

    def test_extended_domains_are_registered(self):
        for name in ("npc-drops", "drop-subtables", "shops-by-shop", "prayers", "npcs-summary", "slayer-tasks"):
            self.assertIn(name, DATASETS)

    def test_missing_dataset_is_unavailable_not_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_query("quests", "dragon", dist_dir=Path(tmp))
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["record_count"])

    def test_malformed_json_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "weapons.json").write_text("{bad", encoding="utf-8")
            result = run_query("weapons", "whip", dist_dir=Path(tmp))
        self.assertEqual(result["status"], "failed")

    def test_invalid_limits_and_empty_queries_rejected(self):
        with self.assertRaises(ValueError):
            search_rows([], limit=0)
        self.assertEqual(run_query("weapons", limit=0)["status"], "failed")
        self.assertEqual(run_query("weapons")["status"], "failed")

    def test_missing_nested_field_does_not_match(self):
        self.assertEqual(search_rows([{"id": 1, "name": "whip"}], "whip", field="bonuses.attack_slash"), [])


if __name__ == "__main__":
    unittest.main()
