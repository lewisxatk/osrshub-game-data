"""Tests for combat readiness summaries."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import report_combat_readiness as readiness


class CombatReadinessTests(unittest.TestCase):
    def test_zero_is_present_and_null_is_missing(self):
        result = readiness.field_summary(
            [{"attack_speed": 0}, {"attack_speed": None}],
            ("attack_speed",),
        )
        self.assertEqual(result["attack_speed"]["present"], 1)
        self.assertEqual(result["attack_speed"]["missing"], 1)
        self.assertEqual(result["attack_speed"]["coverage_percent"], 50.0)

    def test_empty_dataset_is_safe(self):
        result = readiness.field_summary([], ("hitpoints",))
        self.assertEqual(result["hitpoints"]["present"], 0)
        self.assertEqual(result["hitpoints"]["coverage_percent"], 0.0)

    def test_nested_empty_objects_are_missing(self):
        result = readiness.field_summary(
            [{"bonuses": {}}, {"bonuses": {"prayer": 0}}],
            ("bonuses",),
        )
        self.assertEqual(result["bonuses"]["present"], 1)

    def test_non_array_dataset_is_rejected(self):
        with self.assertRaises(ValueError):
            readiness.validate_array({"id": 1})


if __name__ == "__main__":
    unittest.main()
