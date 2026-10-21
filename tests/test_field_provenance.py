"""Tests for field-level source provenance and conflict reporting."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import report_field_provenance as provenance


class FieldProvenanceTests(unittest.TestCase):
    def test_reports_field_coverage_and_source_disagreements(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "community_items.json").write_text(json.dumps([
                {"id": 4151, "name": "Abyssal whip", "weapon": {"attack_speed": 4}}
            ]), encoding="utf-8")
            (root / "original_items.json").write_text(json.dumps([
                {"id": 4151, "name": "Abyssal whip", "weapon": {"attack_speed": 5}}
            ]), encoding="utf-8")
            report = provenance.audit_category(
                "items", ("community_items", "original_items"),
                {"weapon": ("weapon",)}, raw_dir=root
            )
            self.assertEqual(report["unique_record_count"], 1)
            self.assertEqual(report["fields"]["weapon"]["records_with_value"], 1)
            self.assertEqual(report["conflict_count"], 1)
            self.assertEqual(report["conflicts"][0]["field"], "weapon")

    def test_aliases_are_reported_for_monster_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "community_monsters.json").write_text('[{"id":1,"combat":100}]', encoding="utf-8")
            (root / "original_monsters.json").write_text('[{"id":1,"combat_level":100}]', encoding="utf-8")
            report = provenance.audit_category(
                "monsters", ("community_monsters", "original_monsters"),
                {"combat_level": ("combat_level", "combat")}, raw_dir=root
            )
            self.assertEqual(report["fields"]["combat_level"]["records_with_value"], 1)
            self.assertEqual(report["conflict_count"], 0)

    def test_missing_source_is_reported_as_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = provenance.audit_category(
                "items", ("community_items", "original_items"),
                {"weapon": ("weapon",)}, raw_dir=Path(tmp)
            )
            self.assertEqual(report["status"], "failed")
            self.assertEqual(len(report["errors"]), 2)

    def test_object_map_input_and_bad_rows_are_handled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "community_items.json").write_text('{"4151":{"name":"Whip","weapon":{}}}', encoding="utf-8")
            (root / "original_items.json").write_text('[null, {"id":"bad"}]', encoding="utf-8")
            report = provenance.audit_category(
                "items", ("community_items", "original_items"),
                {"weapon": ("weapon",)}, raw_dir=root
            )
            self.assertEqual(report["unique_record_count"], 1)
            self.assertEqual(report["fields"]["weapon"]["records_with_value"], 1)


if __name__ == "__main__":
    unittest.main()
