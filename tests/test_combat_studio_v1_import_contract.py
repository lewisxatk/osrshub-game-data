import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from build_combat_studio_v1_import_contract import build_report,CONTRACT
class ImportContractTests(unittest.TestCase):
 def fill(self,d):
  for name,spec in CONTRACT.items():
   key=spec["identity"]; (d/name).write_text(json.dumps([{key:1,"name":"sample"}]),encoding="utf-8")
 def test_all_valid_datasets_are_ready_for_consumer_smoke_test(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);self.fill(d);r=build_report(d);self.assertEqual(r["status"],"ready_for_consumer_smoke_test");self.assertEqual(r["ready_dataset_count"],len(CONTRACT))
 def test_missing_dataset_blocks_contract(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);self.fill(d);(d/"weapons.json").unlink();r=build_report(d);self.assertEqual(r["status"],"blocked");self.assertEqual(r["blocking_issues"][0]["dataset"],"weapons.json")
 def test_duplicate_ids_are_review_warning_not_silent_pass(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);self.fill(d);(d/"items.json").write_text(json.dumps([{"id":1},{"id":1}]),encoding="utf-8");r=build_report(d);self.assertEqual(r["status"],"review_required");self.assertEqual(r["datasets"]["items.json"]["duplicate_identity_count"],1)
 def test_missing_identity_is_reported(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);self.fill(d);(d/"items.json").write_text(json.dumps([{"name":"no id"}]),encoding="utf-8");r=build_report(d);self.assertEqual(r["datasets"]["items.json"]["missing_identity_count"],1)
 def test_empty_dataset_requires_review(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);self.fill(d);(d/"quests.json").write_text("[]",encoding="utf-8");r=build_report(d);self.assertEqual(r["datasets"]["quests.json"]["state"],"review_required")
 def test_invalid_json_blocks(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);self.fill(d);(d/"items.json").write_text("{bad",encoding="utf-8");r=build_report(d);self.assertEqual(r["status"],"blocked");self.assertEqual(r["datasets"]["items.json"]["state"],"invalid_json")
 def test_boolean_identity_not_accepted(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);self.fill(d);(d/"items.json").write_text(json.dumps([{"id":True}]),encoding="utf-8");r=build_report(d);self.assertEqual(r["datasets"]["items.json"]["missing_identity_count"],1)
if __name__=="__main__":unittest.main()
