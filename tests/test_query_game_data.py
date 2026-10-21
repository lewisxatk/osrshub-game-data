"""Tests for safe, bounded queries over generated datasets."""
import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from query_game_data import run_query, search_rows

class QueryGameDataTests(unittest.TestCase):
    def test_search_nested_fields_and_casefold(self):
        rows=[{"id":1,"name":"Dragon scimitar","bonuses":{"attack_slash":8}},{"id":2,"name":"Rune sword","bonuses":{"attack_slash":45}}]
        self.assertEqual(search_rows(rows,"dragon")[0]["id"],1)
        self.assertEqual(search_rows(rows,"45",field="bonuses.attack_slash")[0]["id"],2)
    def test_id_filter(self):
        rows=[{"id":1},{"id":2}]
        self.assertEqual([r["id"] for r in search_rows(rows,record_id=2)],[2])
    def test_missing_dataset_is_unavailable_not_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=run_query("quests","dragon",dist_dir=Path(tmp))
        self.assertEqual(result["status"],"unavailable")
        self.assertIsNone(result["record_count"])
    def test_malformed_json_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp,"weapons.json").write_text("{bad",encoding="utf-8")
            result=run_query("weapons","whip",dist_dir=Path(tmp))
        self.assertEqual(result["status"],"failed")
    def test_invalid_limits_and_empty_queries_rejected(self):
        with self.assertRaises(ValueError): search_rows([],limit=0)
        self.assertEqual(run_query("weapons",limit=0)["status"],"failed")
        self.assertEqual(run_query("weapons")["status"],"failed")
    def test_missing_nested_field_does_not_match(self):
        self.assertEqual(search_rows([{"id":1,"name":"whip"}],"whip",field="bonuses.attack_slash"),[])
if __name__=="__main__": unittest.main()
