"""Tests for explicit item-to-equipment/weapon relationships."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_item_relationships as builder


class ItemRelationshipTests(unittest.TestCase):
    def test_builds_equipment_and_weapon_links_by_id(self):
        items = [{"id": 4151, "name": "Abyssal whip", "sources": ["community_items"]}]
        equipment = [{"id": 4151, "slot": "weapon"}]
        weapons = [{"id": 4151, "weapon_type": "whip", "attack_speed": 4}]
        rows, summary = builder.build_relationships(items, equipment, weapons)
        self.assertEqual(rows[0]["item_id"], 4151)
        self.assertEqual([x["type"] for x in rows[0]["relationships"]], ["has_equipment_stats", "has_weapon_data"])
        self.assertEqual(summary["items_with_both"], 1)

    def test_does_not_infer_missing_relationships(self):
        rows, summary = builder.build_relationships(
            [{"id": 1, "name": "Unknown item"}], [], []
        )
        self.assertEqual(rows, [])
        self.assertEqual(summary["items_with_equipment_stats"], 0)
        self.assertEqual(summary["items_with_weapon_data"], 0)

    def test_duplicate_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate IDs"):
            builder.build_relationships(
                [{"id": 1, "name": "One"}, {"id": 1, "name": "Duplicate"}], [], []
            )

    def test_orphaned_normalized_records_are_counted(self):
        _, summary = builder.build_relationships(
            [{"id": 1, "name": "One"}],
            [{"id": 2, "slot": "head"}],
            [{"id": 3, "attack_speed": 4}],
        )
        self.assertEqual(summary["equipment_records_without_item"], 1)
        self.assertEqual(summary["weapon_records_without_item"], 1)


if __name__ == "__main__":
    unittest.main()
