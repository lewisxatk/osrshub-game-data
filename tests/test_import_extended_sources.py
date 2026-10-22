"""Tests for lossless import of extended OSRS source domains."""
import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from import_extended_sources import preserve_rows, build_datasets, SOURCES

class ExtendedSourceImportTests(unittest.TestCase):
    def test_keyed_records_keep_original_fields_and_key(self):
        rows = preserve_rows({"1": {"id": 1, "name": "Thick Skin", "bonuses": {"defence": 5}}}, "id", "records", "https://example.test/prayers.json")
        self.assertEqual(rows[0]["id"], 1)
        self.assertEqual(rows[0]["name"], "Thick Skin")
        self.assertEqual(rows[0]["bonuses"], {"defence": 5})
        self.assertEqual(rows[0]["source_key"], "1")
        self.assertEqual(rows[0]["source_snapshot_url"], "https://example.test/prayers.json")

    def test_keyed_values_are_preserved_without_interpreting_drop_data(self):
        value = {"main_table": [{"item_id": 100, "rarity": 32}], "notes": "source payload"}
        rows = preserve_rows({"123": value}, "npc_id", "keyed_value", "https://example.test/drops.json")
        self.assertEqual(rows[0]["npc_id"], 123)
        self.assertEqual(rows[0]["source_value"], value)

    def test_non_numeric_keys_remain_strings(self):
        rows = preserve_rows({"Grand Tree Groceries": {"items": [{"id": 1}]}}, "shop_name", "records", "https://example.test/shops.json")
        self.assertEqual(rows[0]["shop_name"], "Grand Tree Groceries")
        self.assertEqual(rows[0]["items"], [{"id": 1}])

    def test_all_configured_sources_are_required_and_nonempty(self):
        with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as dist:
            for source_file, (_, identity, mode) in SOURCES.items():
                Path(raw, source_file).write_text(json.dumps({"1": {"id": 1, "name": "fixture"}}), encoding="utf-8")
            report = build_datasets(Path(raw), Path(dist))
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["dataset_count"], len(SOURCES))
            self.assertTrue(all(Path(dist, name).exists() for name in (spec[0] for spec in SOURCES.values())))

    def test_empty_source_is_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as dist:
            for source_file in SOURCES:
                Path(raw, source_file).write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                build_datasets(Path(raw), Path(dist))

if __name__ == "__main__":
    unittest.main()
