"""Tests for the traceable quest import adapter."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import import_quests as quests


class QuestImportTests(unittest.TestCase):
    def test_normalizes_name_requirements_and_skill_levels(self):
        row, error = quests.normalize_record({
            "id": "Cook's Assistant", "name": " Cook's Assistant ",
            "requirements": ["Start", "Start", ""],
            "skill_requirements": {"Cooking": "10", "Bad": "unknown", "Firemaking": -1},
            "rewards": ["Quest points"], "members": False,
            "url": "https://oldschool.runescape.wiki/w/Cook%27s_Assistant"
        })
        self.assertIsNone(error)
        self.assertEqual(row["name"], "Cook's Assistant")
        self.assertEqual(row["requirements"], ["Start"])
        self.assertEqual(row["skill_requirements"], [{"skill": "Cooking", "level": 10}])
        self.assertFalse(row["members"])
        self.assertTrue(row["source_url"].startswith("https://"))
        self.assertEqual(row["field_status"]["requirements"], "known")
        self.assertEqual(row["field_status"]["skill_requirements"], "known")
        self.assertEqual(row["field_status"]["members"], "known")

    def test_missing_values_remain_unknown(self):
        row, error = quests.normalize_record({"name": "Example Quest"})
        self.assertIsNone(error)
        self.assertIsNone(row["members"])
        self.assertIsNone(row["difficulty"])
        self.assertEqual(row["requirements"], [])
        self.assertEqual(row["field_status"]["requirements"], "unknown")
        self.assertEqual(row["field_status"]["rewards"], "unknown")
        self.assertIsNone(row["source_url"])

    def test_source_summary_reports_catalogue_fallback_truthfully(self):
        from pathlib import Path
        rows = [{"name": "Quest A"}, {"name": "Quest B"}]
        summary = quests.source_summary(quests.CATALOG_PATH, rows)
        self.assertEqual(summary["source_record_count"], 2)
        self.assertEqual(summary["source_kind"], "title_catalogue_only")
        self.assertTrue(summary["catalogue_fallback_used"])

    def test_rejects_record_without_name(self):
        row, error = quests.normalize_record({"id": 123, "rewards": ["Something"]})
        self.assertIsNone(row)
        self.assertIn("missing quest name", error)

    def test_http_url_is_not_treated_as_trusted_source_url(self):
        row, error = quests.normalize_record({"name": "Example", "url": "http://example.com"})
        self.assertIsNone(error)
        self.assertIsNone(row["source_url"])

    def test_keyed_source_objects_keep_the_key_as_identity(self):
        import tempfile, json
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "quests.json"
            path.write_text(json.dumps({"dragon-slayer": {"name": "Dragon Slayer"}}), encoding="utf-8")
            rows = quests.load_source(path)
        self.assertEqual(rows[0]["id"], "dragon-slayer")


if __name__ == "__main__":
    unittest.main()
