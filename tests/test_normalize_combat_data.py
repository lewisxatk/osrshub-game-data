"""Tests for compact equipment and weapon normalization."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import normalize_combat_data as normalizer


class NormalizeCombatDataTests(unittest.TestCase):
    def test_positive_integer_attack_speed_is_preserved(self):
        result = normalizer.normalize_weapon({"id": 1, "name": "Example", "weapon": {"attack_speed": 4}})
        self.assertEqual(result["attack_speed"], 4)

    def test_zero_and_negative_attack_speed_become_unknown(self):
        for speed in (0, -1):
            with self.subTest(speed=speed):
                result = normalizer.normalize_weapon({"id": 1, "weapon": {"attack_speed": speed}})
                self.assertIsNone(result["attack_speed"])

    def test_boolean_and_fractional_attack_speed_become_unknown(self):
        for speed in (True, 2.5, "4"):
            with self.subTest(speed=speed):
                result = normalizer.normalize_weapon({"id": 1, "weapon": {"attack_speed": speed}})
                self.assertIsNone(result["attack_speed"])

    def test_missing_stances_are_normalized_to_empty_list(self):
        result = normalizer.normalize_weapon({"id": 1, "weapon": {"attack_speed": 4, "stances": None}})
        self.assertEqual(result["stances"], [])

    def test_weapon_stance_name_is_preserved_for_site_selection(self):
        result = normalizer.normalize_weapon({
            "id": 1, "weapon": {"stances": [{"name": "Accurate", "combat_style": "melee"}]}
        })
        self.assertEqual(result["stances"][0]["name"], "Accurate")

    def test_non_equipment_record_is_ignored(self):
        self.assertIsNone(normalizer.normalize_equipment({"id": 1, "equipment": None}))


if __name__ == "__main__":
    unittest.main()
