import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from explore_item_knowledge import resolve_relationships

class ExploreItemKnowledgeTests(unittest.TestCase):
    def fixture(self, root):
        payloads = {
            "item-relationships.json": [{"item_id": 4151, "item_name": "Abyssal whip", "sources": ["test"], "relationships": [
                {"type": "has_combat_profile", "dataset": "item-combat-profiles.json", "record_id": 4151, "data_status": "joined_fields_present"},
                {"type": "has_weapon_record", "dataset": "weapons.json", "record_id": 4151}
            ]}],
            "item-combat-profiles.json": [{"id": 4151, "name": "Abyssal whip", "slot": "weapon", "attack_speed": 4, "weapon_type": "whip", "bonuses": {"attack_slash": 82}, "skill_requirements": [{"skill": "attack", "level": 70}], "source_urls": ["https://example.invalid/whip"], "data_status": "joined_fields_present"}],
            "weapons.json": [{"id": 4151, "name": "Abyssal whip", "attack_speed": 4, "weapon_type": "whip", "stances": [], "source_url": "https://example.invalid/whip"}]
        }
        for name, data in payloads.items():
            (root / name).write_text(json.dumps(data), encoding="utf-8")

    def test_resolves_exact_ids_and_preserves_unknown_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            result = resolve_relationships(4151, root)
        self.assertEqual(result["status"], "found")
        self.assertEqual(result["resolved_relationship_count"], 2)
        profile = next(x for x in result["relationships"] if x["target_dataset"] == "item-combat-profiles.json")
        self.assertEqual(profile["record_facts"]["attack_speed"], 4)
        self.assertIn("stances", next(x for x in result["relationships"] if x["target_dataset"] == "weapons.json")["unknown_fields"])

    def test_missing_graph_node_is_not_found_not_empty_fact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "item-relationships.json").write_text("[]", encoding="utf-8")
            result = resolve_relationships(99, root)
        self.assertEqual(result["status"], "not_found")
        self.assertIn("unknown", result["guardrails"][0])

    def test_missing_target_is_reported_without_guessing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "item-relationships.json").write_text(json.dumps([{"item_id": 1, "item_name": "X", "relationships": [{"type": "has_weapon_record", "dataset": "weapons.json", "record_id": 99}]}]), encoding="utf-8")
            (root / "weapons.json").write_text("[]", encoding="utf-8")
            result = resolve_relationships(1, root)
        self.assertEqual(result["unresolved_relationships"][0]["reason"], "Target record not present in generated dataset")

if __name__ == "__main__":
    unittest.main()
