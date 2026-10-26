import sys,tempfile,json,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from build_combat_studio_readiness_matrix import build_report
FILES=["items.json","equipment-stats.json","weapons.json","item-combat-profiles.json","item-requirements.json","monsters-combat.json","quests.json","quest-relationships.json","item-relationships.json"]
class ReadinessTests(unittest.TestCase):
 def write(self,d,f,v):(d/f).write_text(json.dumps(v),encoding="utf-8")
 def test_missing_data_not_assessed(self):
  with tempfile.TemporaryDirectory() as t:
   r=build_report(Path(t));self.assertEqual(r["available_dataset_count"],0);self.assertTrue(all(e["state"]=="not_assessed" for e in r["relationships"]))
 def test_duplicate_and_missing_ids(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);self.write(d,"items.json",[{"id":1,"name":"A"},{"id":1,"name":"B"},{"name":"C"}])
   r=build_report(d);self.assertEqual(r["datasets"]["items"]["duplicate_id_count"],1);self.assertEqual(r["datasets"]["items"]["missing_id_count"],1)
 def test_same_name_does_not_create_link(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);self.write(d,"items.json",[{"id":1,"name":"same"}]);self.write(d,"equipment-stats.json",[{"id":2,"name":"same"}])
   for f in FILES:
    if f not in ("items.json","equipment-stats.json"):self.write(d,f,[])
   r=build_report(d);e=next(x for x in r["relationships"] if x["relationship"]=="equipment")
   self.assertEqual(e["linked_count"],0);self.assertEqual(e["unlinked_source_count"],1);self.assertEqual(e["orphan_target_count"],1)
 def test_empty_data_safe(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t)
   for f in FILES:self.write(d,f,[])
   r=build_report(d);self.assertEqual(r["datasets"]["items"]["field_coverage_percent"],0.0);self.assertEqual(r["relationships"][0]["coverage_percent"],0.0)
 def test_blank_field_is_not_populated(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t)
   for f in FILES:self.write(d,f,[])
   self.write(d,"items.json",[{"id":1,"name":" "}])
   self.assertEqual(build_report(d)["datasets"]["items"]["field_coverage_percent"],0.0)
 def test_invalid_json_reported(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);(d/"items.json").write_text("{bad",encoding="utf-8")
   self.assertEqual(build_report(d)["datasets"]["items"]["state"],"invalid_json")
if __name__=="__main__":unittest.main()
