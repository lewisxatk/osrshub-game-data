"""Tests for the normalized Combat Studio join contract audit."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_combat_join_contract import audit_datasets


def fixture():
    return {
        "items.json": [{"id": 1, "name": "Example"}],
        "equipment-stats.json": [{"id": 1, "name": "Example", "slot": "weapon", "bonuses": {}, "requirements": {}, "sources": ["fixture"], "source_url": "https://example.test/item"}],
        "weapons.json": [{"id": 1, "name": "Example", "attack_speed": 4, "weapon_type": "whip", "stances": [{"name": "Accurate"}], "sources": ["fixture"], "source_url": "https://example.test/item"}],
        "item-requirements.json": [{"item_id": 1, "requirements": [], "source_url": "https://example.test/item"}],
        "item-combat-profiles.json": [{"id": 1, "name": "Example", "bonuses": {"attack_slash": 0}, "equipment_record_present": True, "weapon_record_present": True, "skill_requirement_record_present": True, "source_urls": ["https://example.test/item"]}],
        "monsters-combat.json": [{"id": 2, "name": "Example monster", "combat_level": 0, "hitpoints": 1, "defence_level": 1}],
    }


class CombatJoinContractTests(unittest.TestCase):
    def test_valid_join_contract_passes(self):
        result = audit_datasets(fixture())
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_zero_is_valid_known_numeric_value(self):
        data = fixture()
        data["monsters-combat.json"][0]["combat_level"] = 0
        result = audit_datasets(data)
        self.assertFalse(any(e.get("field") == "combat_level" for e in result["errors"]))

    def test_orphan_equipment_id_is_an_error(self):
        data = fixture()
        data["equipment-stats.json"][0]["id"] = 99
        result = audit_datasets(data)
        self.assertTrue(any(e.get("issue") == "orphan_item_reference" and e.get("item_id") == 99 for e in result["errors"]))

    def test_profile_join_flags_must_match_exact_id_joins(self):
        data = fixture()
        data["item-combat-profiles.json"][0]["weapon_record_present"] = False
        result = audit_datasets(data)
        self.assertTrue(any(e.get("issue") == "join_flag_mismatch" for e in result["errors"]))

    def test_missing_combat_values_are_warnings_not_fabricated_zeroes(self):
        data = fixture()
        data["monsters-combat.json"][0]["hitpoints"] = None
        result = audit_datasets(data)
        self.assertNotEqual(result["status"], "failed")
        self.assertIn(2, result["coverage_gaps"]["monsters_without_core_combat_fields"])

    def test_stance_without_name_is_valid_when_source_style_is_present(self):
        data = fixture()
        data["weapons.json"][0]["stances"] = [{"combat_style": "melee"}]
        result = audit_datasets(data)
        self.assertFalse(any(e.get("issue") == "stance_metadata_missing" for e in result["errors"]))

    def test_stance_with_no_identifying_metadata_is_rejected(self):
        data = fixture()
        data["weapons.json"][0]["stances"] = [{}]
        result = audit_datasets(data)
        self.assertTrue(any(e.get("issue") == "stance_metadata_missing" for e in result["errors"]))


if __name__ == "__main__":
    unittest.main()
