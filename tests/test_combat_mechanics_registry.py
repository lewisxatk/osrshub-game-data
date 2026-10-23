"""Guardrails for source-backed combat mechanic verification."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_combat_mechanics_registry import validate_registry


class CombatMechanicsRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ROOT / "schemas" / "combat-mechanics-registry.schema.json").read_text())
        cls.registry = json.loads((ROOT / "data" / "combat-mechanics-registry.json").read_text())

    def test_checked_in_registry_is_valid_scaffold(self):
        self.assertEqual(validate_registry(self.registry, self.schema), [])
        self.assertEqual(self.registry["registry_status"], "research_scaffold")

    def test_verified_mechanic_requires_source_and_fixture(self):
        registry = json.loads(json.dumps(self.registry))
        row = registry["mechanics"][0]
        row["verification_status"] = "verified"
        self.assertTrue(any("source reference" in error for error in validate_registry(registry, self.schema)))
        row["source_references"] = [{"url":"https://example.org/rule","title":"Fixture source","accessed_at":"2026-10-23","claim":"Illustrative test only"}]
        self.assertTrue(any("regression fixture" in error for error in validate_registry(registry, self.schema)))

    def test_unsupported_mechanic_cannot_be_scoped_implemented(self):
        registry = json.loads(json.dumps(self.registry))
        row = next(item for item in registry["mechanics"] if item["mechanic_id"] == "prayers")
        row["implementation_status"] = "implemented_scoped"
        self.assertTrue(any("cannot be marked unsupported" in error for error in validate_registry(registry, self.schema)))

    def test_duplicate_ids_are_rejected(self):
        registry = json.loads(json.dumps(self.registry))
        registry["mechanics"].append(json.loads(json.dumps(registry["mechanics"][0])))
        self.assertTrue(any("duplicate mechanic_id" in error for error in validate_registry(registry, self.schema)))


if __name__ == "__main__":
    unittest.main()
