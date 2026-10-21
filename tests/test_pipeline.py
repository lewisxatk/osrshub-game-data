"""Unit tests for dataset normalization and conflict reporting."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_dataset
import normalize_combat_data


class PipelineTests(unittest.TestCase):
    def test_numeric_id_variants(self):
        self.assertEqual(build_dataset.numeric_id({"id": "4151"}), 4151)
        self.assertEqual(build_dataset.numeric_id({"item_id": 11802}), 11802)
        self.assertIsNone(build_dataset.numeric_id({"id": "not-an-id"}))

    def test_name_variants(self):
        self.assertEqual(build_dataset.name_of({"name": "Whip"}), "Whip")
        self.assertEqual(build_dataset.name_of({"item_name": "Rune platebody"}), "Rune platebody")
        self.assertEqual(build_dataset.name_of({}), "")

    def test_volatile_conflict_fields_are_ignored(self):
        self.assertTrue(build_dataset._is_ignored_conflict_field("last_updated"))
        self.assertTrue(build_dataset._is_ignored_conflict_field("icon_large"))
        self.assertFalse(build_dataset._is_ignored_conflict_field("attack_speed"))

    def test_large_conflict_values_are_summarized(self):
        summary = build_dataset._value_summary("x" * 1000)
        self.assertIsInstance(summary, dict)
        self.assertTrue(summary["truncated"])
        self.assertEqual(summary["characters"], 1002)

    def test_merge_keeps_source_attribution_without_raw_record_duplication(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory)
            (raw / "community_items.json").write_text(json.dumps([{
                "id": 4151, "name": "Abyssal whip", "attack_speed": 4,
                "last_updated": "2025-01-01", "icon": "first",
            }]), encoding="utf-8")
            (raw / "original_items.json").write_text(json.dumps([{
                "id": 4151, "name": "Abyssal whip", "attack_speed": 5,
                "last_updated": "2026-01-01", "icon": "second",
            }]), encoding="utf-8")
            with patch.object(build_dataset, "RAW", raw):
                records, conflicts, missing, ignored = build_dataset.merge_category("items")
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["sources"], ["community_items", "original_items"])
            self.assertNotIn("source_records", records[0])
            self.assertEqual(len(conflicts), 1)
            self.assertEqual(conflicts[0]["field"], "attack_speed")
            self.assertEqual(missing, [])
            self.assertEqual(ignored, {"icon": 1, "last_updated": 1})

    def test_equipment_normalizer_preserves_bonus_fields(self):
        row = {"id": 4151, "name": "Abyssal whip", "sources": ["osrsbox"],
               "wiki_url": "https://oldschool.runescape.wiki/w/Abyssal_whip",
               "equipment": {"attack_slash": 82, "melee_strength": 82, "slot": "weapon",
                             "requirements": {"attack": 70}}}
        result = normalize_combat_data.normalize_equipment(row)
        self.assertEqual(result["bonuses"]["attack_slash"], 82)
        self.assertEqual(result["slot"], "weapon")
        self.assertEqual(result["requirements"]["attack"], 70)

    def test_weapon_normalizer_keeps_stances_and_speed(self):
        row = {"id": 4151, "name": "Abyssal whip", "sources": ["osrsbox"],
               "weapon": {"attack_speed": 4, "weapon_type": "whip",
                          "stances": [{"combat_style": "lash", "attack_type": "slash",
                                       "attack_style": "controlled", "experience": "shared",
                                       "boosts": "+1 attack, strength and defence"}]}}
        result = normalize_combat_data.normalize_weapon(row)
        self.assertEqual(result["attack_speed"], 4)
        self.assertEqual(result["stances"][0]["attack_type"], "slash")
        self.assertIsNone(normalize_combat_data.normalize_weapon({"id": 1, "weapon": None}))


if __name__ == "__main__":
    unittest.main()
