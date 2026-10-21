"""Tests for normalized equipment and weapon field provenance."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import report_normalized_combat_provenance as provenance


class NormalizedCombatProvenanceTests(unittest.TestCase):
    def test_nested_source_field_is_resolved(self):
        raw = {"equipment": {"attack_slash": 82}}
        self.assertEqual(provenance.get_path(raw, ("equipment", "attack_slash")), 82)

    def test_missing_nested_field_returns_none(self):
        self.assertIsNone(provenance.get_path({"weapon": None}, ("weapon", "attack_speed")))

    def test_source_index_handles_list_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "raw.json"
            path.write_text('[{"id": 4151, "equipment": {"attack_slash": 82}}]', encoding="utf-8")
            indexed, errors = provenance.build_source_index([("community_items", path)])
        self.assertEqual(errors, [])
        self.assertEqual(indexed[4151][0][0], "community_items")

    def test_missing_raw_source_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            indexed, errors = provenance.build_source_index([("community_items", Path(tmp) / "missing.json")])
        self.assertEqual(indexed, {})
        self.assertEqual(len(errors), 1)


if __name__ == "__main__":
    unittest.main()
