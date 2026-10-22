"""Tests for the explicit item relationship graph audit."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_item_relationships import audit_relationships


def fixture():
    return {
        "items.json": [{"id": 4151, "name": "Abyssal whip", "sources": ["fixture"]}],
        "item-relationships.json": [{
            "item_id": 4151, "item_name": "Abyssal whip", "sources": ["fixture"],
            "relationships": [
                {"type": "has_equipment_stats", "dataset": "equipment-stats.json", "record_id": 4151, "slot": "weapon"},
                {"type": "has_weapon_data", "dataset": "weapons.json", "record_id": 4151, "weapon_type": "whip", "attack_speed": 4},
                {"type": "has_skill_requirements", "dataset": "item-requirements.json", "record_id": 4151, "requirement_count": 1},
                {"type": "has_combat_profile", "dataset": "item-combat-profiles.json", "record_id": 4151, "data_status": "joined_fields_present"},
            ],
        }],
        "equipment-stats.json": [{"id": 4151}],
        "weapons.json": [{"id": 4151}],
        "item-requirements.json": [{"item_id": 4151}],
        "item-combat-profiles.json": [{"id": 4151}],
    }


class ItemRelationshipAuditTests(unittest.TestCase):
    def test_complete_graph_passes(self):
        report = audit_relationships(fixture())
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["counts"]["expected_links"], 4)
        self.assertEqual(report["counts"]["missing_links"], 0)

    def test_missing_explicit_link_fails(self):
        data = fixture()
        data["item-relationships.json"][0]["relationships"].pop()
        report = audit_relationships(data)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any(x["issue"] == "missing_relationship" for x in report["errors"]))

    def test_wrong_dataset_target_fails(self):
        data = fixture()
        data["item-relationships.json"][0]["relationships"][0]["dataset"] = "weapons.json"
        report = audit_relationships(data)
        self.assertTrue(any(x["issue"] == "relationship_dataset_mismatch" for x in report["errors"]))

    def test_cross_item_join_fails(self):
        data = fixture()
        data["equipment-stats.json"].append({"id": 9000})
        data["item-relationships.json"][0]["relationships"][0]["record_id"] = 9000
        report = audit_relationships(data)
        self.assertTrue(any(x["issue"] == "cross_item_join_mismatch" for x in report["errors"]))

    def test_unknown_relationship_type_fails(self):
        data = fixture()
        data["item-relationships.json"][0]["relationships"][0]["type"] = "guessed_drop"
        report = audit_relationships(data)
        self.assertTrue(any(x["issue"] == "unknown_relationship_type" for x in report["errors"]))


if __name__ == "__main__":
    unittest.main()
