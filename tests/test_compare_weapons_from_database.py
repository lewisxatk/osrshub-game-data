"""Tests for database-only weapon comparison."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.compare_weapons_from_database import compare_from_database, compare_profiles


class DatabaseWeaponComparisonTests(unittest.TestCase):
    def profile(self, item_id, name, bonuses, **overrides):
        row = {
            "id": item_id, "name": name, "slot": "weapon", "bonuses": bonuses,
            "attack_speed": 4, "weapon_type": "sword", "skill_requirements": [],
            "weapon_record_present": True, "data_status": "joined_fields_present",
        }
        row.update(overrides)
        return row

    def test_delta_is_right_minus_left(self):
        result = compare_profiles(
            self.profile(1, "Left", {"attack_slash": 10, "melee_strength": 8}),
            self.profile(2, "Right", {"attack_slash": 14, "melee_strength": 6}),
        )
        self.assertEqual(result["bonus_differences"]["attack_slash"]["delta_right_minus_left"], 4)
        self.assertEqual(result["bonus_differences"]["melee_strength"]["delta_right_minus_left"], -2)

    def test_missing_bonus_does_not_become_zero(self):
        result = compare_profiles(
            self.profile(1, "Left", {"attack_slash": None}),
            self.profile(2, "Right", {"attack_slash": 5}),
        )
        field = result["bonus_differences"]["attack_slash"]
        self.assertIsNone(field["delta_right_minus_left"])
        self.assertEqual(field["delta_status"], "unknown_input")

    def test_non_finite_bonus_has_no_delta(self):
        result = compare_profiles(
            self.profile(1, "Left", {"attack_slash": "NaN"}),
            self.profile(2, "Right", {"attack_slash": 5}),
        )
        self.assertIsNone(result["bonus_differences"]["attack_slash"]["delta_right_minus_left"])

    def test_comparison_reads_local_dataset_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "item-combat-profiles.json"
            path.write_text(json.dumps([
                self.profile(4587, "Dragon scimitar", {"attack_slash": 67}),
                self.profile(4151, "Abyssal whip", {"attack_slash": 82}),
            ]), encoding="utf-8")
            result = compare_from_database(4587, 4151, Path(tmp))
        self.assertEqual(result["status"], "compared")
        self.assertEqual(result["dataset"], "item-combat-profiles.json")
        self.assertIn("No network requests", " ".join(result["comparison"]["guardrails"]))

    def test_missing_item_fails_instead_of_searching_online(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "item-combat-profiles.json"
            path.write_text(json.dumps([self.profile(1, "Test", {})]), encoding="utf-8")
            with self.assertRaises(LookupError):
                compare_from_database(1, 999, Path(tmp))

    def test_duplicate_item_ids_fail_closed(self):
        row = self.profile(1, "Test", {})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "item-combat-profiles.json"
            path.write_text(json.dumps([row, row]), encoding="utf-8")
            with self.assertRaises(ValueError):
                compare_from_database(1, 2, Path(tmp))


if __name__ == "__main__":
    unittest.main()
