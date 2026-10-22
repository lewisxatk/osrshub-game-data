import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from explain_game_fact import build_fact_card, find_record, load_rows

class ExplainGameFactTests(unittest.TestCase):
    def test_fact_card_preserves_record_and_provenance(self):
        row = {"id": 4151, "name": "Abyssal whip", "attack_speed": 4, "source_urls": ["https://example.invalid/source"], "bonus": None}
        card = build_fact_card("item-combat-profiles", row)
        self.assertEqual(card["status"], "found")
        self.assertEqual(card["record"], row)
        self.assertIn("bonus", card["unknown_fields"])
        self.assertTrue(card["provenance"]["has_source_url"])
        self.assertIn("not independently verified", " ".join(card["guardrails"]))

    def test_missing_record_is_unknown_not_absence_claim(self):
        card = build_fact_card("weapons", None)
        self.assertEqual(card["status"], "not_found")
        self.assertIn("unknown", card["guardrails"][0])

    def test_search_is_case_insensitive_and_id_is_exact(self):
        rows = [{"id": 1, "name": "Dragon scimitar"}, {"id": 2, "name": "Rune sword"}]
        self.assertEqual(find_record(rows, search="DRAGON")["id"], 1)
        self.assertEqual(find_record(rows, record_id=2)["name"], "Rune sword")
        self.assertIsNone(find_record(rows, record_id=99))

    def test_dataset_load_rejects_wrong_shape_and_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "weapons.json").write_text('{"not":"array"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_rows("weapons", root)
            with self.assertRaises(ValueError):
                load_rows("quests", root)

    def test_search_requires_nonempty_query(self):
        with self.assertRaises(ValueError):
            find_record([{"id": 1}], search="  ")

if __name__ == "__main__":
    unittest.main()
