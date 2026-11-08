import tempfile
import unittest
from pathlib import Path

from scripts.import_combat_engine_snapshot import audit_catalogues, write_json


class CombatEngineSnapshotTests(unittest.TestCase):
    def test_preserves_distinction_between_elemental_weakness_and_defence(self):
        monsters = [
            {"id": 1, "name": "Elemental test", "weakness": {"element": "water", "severity": 50},
             "attributes": ["dragon"], "defensive": {"stab": 0, "crush": 70}},
            {"id": 2, "name": "Unknown test", "weakness": None,
             "attributes": [], "defensive": {"magic": 12}},
        ]
        report = audit_catalogues(monsters, [])
        self.assertEqual(report["monster_catalogue"]["records_with_verified_elemental_weakness_field"], 1)
        self.assertEqual(report["monster_catalogue"]["records_without_verified_elemental_weakness"], 1)
        self.assertEqual(report["monster_catalogue"]["weakness_elements"], {"water": 1})
        self.assertEqual(report["monster_catalogue"]["defensive_field_record_counts"]["stab"], 1)
        self.assertEqual(report["monster_catalogue"]["defensive_field_record_counts"]["magic"], 1)

    def test_keeps_variants_as_separate_records_and_counts_engine_flags(self):
        monsters = [
            {"id": 5, "name": "Boss", "version": "Normal", "weakness": None},
            {"id": 5, "name": "Boss", "version": "Awakened", "weakness": None},
        ]
        equipment = [
            {"id": 100, "name": "Craw's bow", "slot": "weapon", "version": "Charged", "isTwoHanded": True},
            {"id": 101, "name": "Craw's bow", "slot": "weapon", "version": "Uncharged", "isTwoHanded": True},
            {"id": 102, "name": "Elite void top", "slot": "body", "version": "Normal", "isTwoHanded": False},
        ]
        report = audit_catalogues(monsters, equipment)
        self.assertEqual(report["monster_catalogue"]["records"], 2)
        self.assertEqual(report["equipment_catalogue"]["records"], 3)
        self.assertEqual(report["equipment_catalogue"]["two_handed_records"], 2)
        self.assertEqual(report["equipment_catalogue"]["slot_record_counts"]["weapon"], 2)
        self.assertFalse(report["safety"]["records_deduplicated"])
        self.assertFalse(report["safety"]["missing_facts_invented"])

    def test_json_writer_writes_complete_objects(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reports" / "catalog.json"
            write_json(path, {"ok": True})
            self.assertIn('"ok": true', path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
