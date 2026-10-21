"""Tests for monster combat field normalization and source aliases."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import normalize_monster_combat as normalizer


class MonsterCombatNormalizationTests(unittest.TestCase):
    def test_first_valid_alias_wins_and_returns_alias(self):
        value, source_field = normalizer.first_numeric_value(
            {"combat_level": "bad", "combat": "126", "level": 99},
            normalizer.ALIASES["combat_level"],
        )
        self.assertEqual(value, 126)
        self.assertEqual(source_field, "combat")

    def test_invalid_community_value_can_fall_back_to_original_alias(self):
        community_value, community_field = normalizer.first_numeric_value(
            {"attackSpeed": "unknown"}, normalizer.ALIASES["attack_speed"]
        )
        original_value, original_field = normalizer.first_numeric_value(
            {"attack_speed": 4}, normalizer.ALIASES["attack_speed"]
        )
        self.assertIsNone(community_value)
        self.assertIsNone(community_field)
        self.assertEqual(original_value, 4)
        self.assertEqual(original_field, "attack_speed")

    def test_boolean_and_negative_values_are_not_numeric_combat_facts(self):
        self.assertIsNone(normalizer.numeric_value(True))
        self.assertIsNone(normalizer.numeric_value(-1))
        self.assertEqual(normalizer.numeric_value("0"), 0)

    def test_fractional_values_are_preserved_for_audit_not_silently_rounded(self):
        self.assertEqual(normalizer.numeric_value("1.5"), 1.5)


if __name__ == "__main__":
    unittest.main()
