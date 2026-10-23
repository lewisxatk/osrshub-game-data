import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import report_hub_readiness_matrix as matrix


class HubReadinessMatrixTests(unittest.TestCase):
    def fixture(self):
        return {
            "items.json": [
                {"id": 1, "name": "Known item", "wiki_url": "https://example.invalid/item"},
                {"id": 2, "name": "Missing join", "wiki_url": None},
            ],
            "equipment-stats.json": [
                {"id": 1, "name": "Known item", "slot": "weapon", "bonuses": {"melee_strength": 1}},
                {"id": 2, "name": "Missing join", "slot": "weapon", "bonuses": {}},
            ],
            "weapons.json": [
                {"id": 1, "name": "Weapon", "attack_speed": 4, "weapon_type": "sword", "stances": ["accurate"]},
                {"id": 2, "name": "Unknown weapon", "attack_speed": None, "weapon_type": None, "stances": []},
            ],
            "item-requirements.json": [
                {"item_id": 1, "requirements": [], "requirements_status": "known_empty", "source_url": "https://example.invalid/req"}
            ],
            "item-combat-profiles.json": [
                {"id": 1, "name": "Known item", "bonuses": {}, "source_urls": ["https://example.invalid/item"]}
            ],
            "monsters-combat.json": [
                {"id": 5, "name": "Test monster", "combat_level": 100, "hitpoints": 100, "defence_level": None}
            ],
            "quests.json": [
                {"id": 10, "name": "Test quest", "field_status": {"requirements": "unknown", "skill_requirements": "known"}}
            ],
            "quest-relationships.json": [],
            "item-relationships.json": [{"item_id": 1, "relationships": []}],
        }

    def test_reports_join_gaps_without_inventing_facts(self):
        data = self.fixture()
        result = matrix.build_readiness_report(lambda filename: data[filename])
        self.assertEqual(result["status"], "review_required")
        self.assertEqual(result["cross_domain_joins"]["equipment_missing_profile_ids"], [2])
        self.assertEqual(result["cross_domain_joins"]["equipment_missing_requirement_ids"], [2])
        self.assertEqual(result["cross_domain_joins"]["quest_missing_relationship_ids"], [10])
        self.assertIn("Missing values are unknown, not zero.", result["guardrails"])
        gaps = {gap["key"]: gap for gap in result["gaps"]}
        self.assertEqual(gaps["weapon_mechanics"]["affected_records"], 1)
        self.assertEqual(gaps["monster_core_combat"]["affected_records"], 1)
        self.assertEqual(gaps["quest_requirement_facts"]["affected_records"], 1)

    def test_duplicate_and_invalid_ids_are_counted(self):
        data = self.fixture()
        data["items.json"].append({"id": 1, "name": "Duplicate"})
        data["items.json"].append({"id": "bad", "name": "Invalid"})
        result = matrix.build_readiness_report(lambda filename: data[filename])
        self.assertGreaterEqual(result["integrity_issue_count"], 2)
        self.assertEqual(result["dataset_summaries"]["items"]["duplicate_ids"], [1])
        self.assertEqual(result["dataset_summaries"]["items"]["invalid_id_count"], 1)

    def test_missing_dataset_is_a_failure_not_an_empty_dataset(self):
        data = self.fixture()
        def loader(filename):
            if filename == "quests.json":
                raise ValueError("missing source dataset")
            return data[filename]
        result = matrix.build_readiness_report(loader)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("missing source dataset" in error for error in result["errors"]))
        self.assertNotIn("quests", result["dataset_summaries"])

    def test_empty_values_are_not_claimed_as_known(self):
        data = self.fixture()
        data["quests.json"] = [{"id": 11, "name": "Unknown", "field_status": None}]
        result = matrix.build_readiness_report(lambda filename: data[filename])
        self.assertEqual(result["gaps"][[g["key"] for g in result["gaps"]].index("quest_requirement_facts")]["affected_records"], 1)

    def test_complete_empty_input_is_structurally_passed(self):
        data = {contract["file"]: [] for contract in matrix.CONTRACTS.values()}
        result = matrix.build_readiness_report(lambda filename: data[filename])
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["gap_count"], 8)


if __name__ == "__main__":
    unittest.main()
