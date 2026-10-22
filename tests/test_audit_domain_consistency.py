"""Regression tests for cross-domain generated-data integrity checks."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_domain_consistency import REQUIRED, audit_datasets


def fixtures():
    return {
        "items.json": [{"id": 1, "name": "Test blade"}],
        "equipment-stats.json": [{"id": 1, "slot": "weapon", "bonuses": {"attack_slash": 5}}],
        "weapons.json": [{"id": 1, "attack_speed": 4, "weapon_type": "sword"}],
        "item-requirements.json": [{"item_id": 1, "requirements": [{"skill": "Attack", "level": 1}]}],
        "item-relationships.json": [{"item_id": 1, "relationships": [
            {"type": "has_equipment_stats", "record_id": 1},
            {"type": "has_weapon_data", "record_id": 1},
            {"type": "has_skill_requirements", "record_id": 1},
            {"type": "has_combat_profile", "record_id": 1},
        ]}],
        "item-combat-profiles.json": [{
            "id": 1, "name": "Test blade", "slot": "weapon", "attack_speed": 4,
            "bonuses": {"attack_slash": 5, "melee_strength": 2},
            "skill_requirements": [{"skill": "Attack", "level": 1}],
            "equipment_record_present": True, "weapon_record_present": True,
            "skill_requirement_record_present": True,
        }],
        "monsters-combat.json": [{"id": 10, "name": "Test monster"}],
        "quests.json": [{"id": 100, "name": "Quest A"}, {"id": 101, "name": "Quest B"}],
        "quest-relationships.json": [
            {"quest_key": "a", "name": "Quest A", "prerequisites": [], "dependents": [{"quest_key": "b", "name": "Quest B"}]},
            {"quest_key": "b", "name": "Quest B", "prerequisites": [{"quest_key": "a", "name": "Quest A", "completion_state": "completed"}], "dependents": []},
        ],
    }


class DomainConsistencyTests(unittest.TestCase):
    def test_consistent_cross_domain_fixture_passes(self):
        report = audit_datasets(fixtures())
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["counts"]["error_count"], 0)
        self.assertEqual(report["counts"]["quest_prerequisite_edges"], 1)

    def test_missing_required_dataset_is_rejected(self):
        data = fixtures()
        del data["weapons.json"]
        with self.assertRaisesRegex(ValueError, "weapons.json"):
            audit_datasets(data)

    def test_duplicate_item_profile_id_is_detected(self):
        data = fixtures()
        data["item-combat-profiles.json"].append(dict(data["item-combat-profiles.json"][0]))
        report = audit_datasets(data)
        self.assertTrue(any(e["issue"] == "duplicate_id" for e in report["errors"]))

    def test_orphan_equipment_join_is_detected(self):
        data = fixtures()
        data["equipment-stats.json"][0]["id"] = 999
        report = audit_datasets(data)
        self.assertTrue(any(e["issue"] == "orphan_item_join" for e in report["errors"]))

    def test_presence_flag_mismatch_is_detected(self):
        data = fixtures()
        data["item-combat-profiles.json"][0]["weapon_record_present"] = False
        report = audit_datasets(data)
        self.assertTrue(any(e["issue"] == "presence_flag_join_mismatch" for e in report["errors"]))

    def test_invalid_attack_speed_is_detected(self):
        data = fixtures()
        data["item-combat-profiles.json"][0]["attack_speed"] = 0
        report = audit_datasets(data)
        self.assertTrue(any(e["issue"] == "invalid_attack_speed" for e in report["errors"]))

    def test_non_numeric_bonus_is_detected(self):
        data = fixtures()
        data["item-combat-profiles.json"][0]["bonuses"]["attack_slash"] = "unknown"
        report = audit_datasets(data)
        self.assertTrue(any(e["issue"] == "non_finite_or_non_numeric_bonus" for e in report["errors"]))

    def test_duplicate_skill_requirement_is_detected(self):
        data = fixtures()
        data["item-combat-profiles.json"][0]["skill_requirements"].append({"skill": " attack ", "level": 1})
        report = audit_datasets(data)
        self.assertTrue(any(e["issue"] == "duplicate_skill_requirement" for e in report["errors"]))

    def test_dangling_quest_prerequisite_is_detected(self):
        data = fixtures()
        data["quest-relationships.json"][1]["prerequisites"][0]["quest_key"] = "missing"
        report = audit_datasets(data)
        self.assertTrue(any(e["issue"] == "dangling_prerequisite_key" for e in report["errors"]))

    def test_quest_prerequisite_cycle_is_detected(self):
        data = fixtures()
        # A -> B already exists; adding B -> A's prerequisite creates a cycle.
        data["quest-relationships.json"][0]["prerequisites"] = [
            {"quest_key": "b", "name": "Quest B", "completion_state": "completed"}
        ]
        data["quest-relationships.json"][1]["dependents"] = [
            {"quest_key": "a", "name": "Quest A"}
        ]
        report = audit_datasets(data)
        self.assertTrue(any(e["issue"] == "prerequisite_cycle" for e in report["errors"]))

    def test_missing_reverse_quest_edge_is_detected(self):
        data = fixtures()
        data["quest-relationships.json"][0]["dependents"] = []
        report = audit_datasets(data)
        self.assertTrue(any(e["issue"] == "missing_reverse_dependent_edge" for e in report["errors"]))

    def test_invalid_relationship_target_is_detected(self):
        data = fixtures()
        data["item-relationships.json"][0]["relationships"][0]["record_id"] = 999
        report = audit_datasets(data)
        self.assertTrue(any(e["issue"] == "orphan_relationship_target" for e in report["errors"]))

    def test_duplicate_item_relationship_owner_row_is_detected(self):
        data = fixtures()
        data["item-relationships.json"].append(dict(data["item-relationships.json"][0]))
        report = audit_datasets(data)
        self.assertTrue(any(e["issue"] == "duplicate_item_relationship_row" for e in report["errors"]))


    def test_coverage_report_counts_known_gaps_without_failing_audit(self):
        data = fixtures()
        data["equipment-stats.json"] = []
        data["weapons.json"] = []
        data["item-requirements.json"] = []
        data["item-relationships.json"][0]["relationships"] = [
            {"type": "has_combat_profile", "record_id": 1}
        ]
        profile = data["item-combat-profiles.json"][0]
        profile["equipment_record_present"] = False
        profile["weapon_record_present"] = False
        profile["skill_requirement_record_present"] = False
        report = audit_datasets(data)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["coverage"]["items_without_equipment_stats"], 1)
        self.assertEqual(report["coverage"]["items_without_weapon_data"], 1)
        self.assertEqual(report["coverage"]["items_without_skill_requirements_record"], 1)
        self.assertEqual(report["coverage"]["items_with_combat_profile"], 1)

    def test_coverage_counts_quest_nodes_with_and_without_prerequisites(self):
        report = audit_datasets(fixtures())
        self.assertEqual(report["coverage"]["quest_nodes_with_prerequisites"], 1)
        self.assertEqual(report["coverage"]["quest_nodes_without_prerequisites"], 1)

    def test_empty_quest_facts_are_a_warning_not_a_passed_fact(self):
        data = fixtures()
        data["quests.json"] = []
        report = audit_datasets(data)
        self.assertEqual(report["status"], "review_required")
        self.assertTrue(any(w["issue"] == "empty_quest_catalogue" for w in report["warnings"]))


if __name__ == "__main__":
    unittest.main()
