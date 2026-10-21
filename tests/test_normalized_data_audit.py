"""Tests for normalized combat data auditing."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_normalized_data as audit


class NormalizedDataAuditTests(unittest.TestCase):
    def test_duplicate_ids_are_structural_errors(self):
        result = audit.audit_records("weapons", [
            {"id": 4151, "name": "A", "sources": ["fixture"]},
            {"id": 4151, "name": "B", "sources": ["fixture"]},
        ])
        self.assertTrue(any("duplicate IDs" in error for error in result["errors"]))

    def test_boolean_is_not_accepted_as_numeric_id(self):
        result = audit.audit_records("equipment-stats", [
            {"id": True, "name": "Bad", "sources": ["fixture"]}
        ])
        self.assertEqual(result["missing_id_count"], 1)
        self.assertTrue(result["errors"])

    def test_weapon_audit_flags_missing_speed_and_stances(self):
        result = audit.audit_records("weapons", [
            {"id": 1, "name": "Fixture weapon", "sources": ["fixture"],
             "attack_speed": None, "weapon_type": "sword", "stances": [], "source_url": "https://example.com"}
        ])
        self.assertEqual(result["missing_attack_speed_count"], 1)
        self.assertEqual(result["missing_stances_count"], 1)
        self.assertTrue(result["warnings"])

    def test_zero_bonus_is_not_treated_as_missing(self):
        bonuses = {field: 0 for field in audit.BONUS_FIELDS}
        result = audit.audit_records("equipment-stats", [
            {"id": 1, "name": "Fixture armour", "sources": ["fixture"], "slot": "body",
             "bonuses": bonuses, "requirements": {"defence": 1}, "source_url": "https://example.com"}
        ])
        self.assertEqual(result["missing_bonus_object_count"], 0)
        self.assertEqual(result["partial_bonus_field_count"], 0)

    def test_invalid_bonus_and_requirement_values_are_reported(self):
        bonuses = {field: 0 for field in audit.BONUS_FIELDS}
        bonuses["attack_stab"] = "unknown"
        result = audit.audit_records("equipment-stats", [
            {"id": 1, "name": "Fixture", "sources": ["fixture"], "slot": "weapon",
             "bonuses": bonuses, "requirements": {"attack": -1}, "source_url": "https://example.com"}
        ])
        self.assertEqual(result["invalid_bonus_value_count"], 1)
        self.assertEqual(result["invalid_requirement_level_count"], 1)

    def test_malformed_stance_and_negative_monster_value_are_reported(self):
        weapon = audit.audit_records("weapons", [
            {"id": 1, "name": "Fixture", "sources": ["fixture"], "attack_speed": 4,
             "weapon_type": "sword", "stances": [{"bad": True}], "source_url": "https://example.com"}
        ])
        self.assertEqual(weapon["malformed_stances_count"], 1)
        monster = audit.audit_records("monsters-combat", [
            {"id": 2, "name": "Fixture NPC", "sources": ["fixture"], "hitpoints": -5}
        ])
        self.assertEqual(monster["invalid_numeric_value_count_by_field"]["hitpoints"], 1)

    def test_monster_coverage_keeps_unknown_values_missing(self):
        result = audit.audit_records("monsters-combat", [
            {"id": 1, "name": "Fixture NPC", "sources": ["fixture"], "combat_level": 10}
        ])
        self.assertEqual(result["field_coverage"]["combat_level"]["coverage_percent"], 100.0)
        self.assertEqual(result["field_coverage"]["hitpoints"]["records_with_value"], 0)
        self.assertTrue(result["warnings"])

    def test_non_array_input_fails_clearly(self):
        result = audit.audit_records("weapons", {"id": 1})
        self.assertTrue(result["errors"])


if __name__ == "__main__":
    unittest.main()
