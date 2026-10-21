"""Tests for numeric range and provenance auditing."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from audit_numeric_provenance import audit_numeric_ranges

def fixture():
 return {
  "items.json":[{"id":1,"name":"Item"}],
  "equipment-stats.json":[{"id":1,"name":"Item","bonuses":{"attack_stab":10,"melee_strength":"20"},"sources":["wiki"]}],
  "weapons.json":[{"id":1,"name":"Item","attack_speed":4,"sources":["wiki"]}],
  "monsters-combat.json":[{"id":1,"name":"Monster","combat_level":10,"hitpoints":20,"attack_level":10,"strength_level":10,"defence_level":10,"max_hit":5}],
  "item-combat-profiles.json":[{"id":1,"source_urls":["https://oldschool.runescape.wiki/w/Item"]}]
 }
class NumericProvenanceTests(unittest.TestCase):
 def test_valid_records_pass(self):
  self.assertEqual(audit_numeric_ranges(fixture())["status"],"passed")
 def test_negative_monster_stat_fails(self):
  data=fixture(); data["monsters-combat.json"][0]["hitpoints"]=-1
  report=audit_numeric_ranges(data)
  self.assertEqual(report["status"],"failed")
  self.assertTrue(any(x["field"]=="hitpoints" for x in report["errors"]))
 def test_bad_attack_speed_fails(self):
  data=fixture(); data["weapons.json"][0]["attack_speed"]=0
  self.assertEqual(audit_numeric_ranges(data)["status"],"failed")
 def test_missing_provenance_is_warning_not_false_fact(self):
  data=fixture(); data["weapons.json"][0].pop("sources")
  report=audit_numeric_ranges(data)
  self.assertEqual(report["status"],"review_required")
  self.assertTrue(any(x["issue"]=="missing_source_provenance" for x in report["warnings"]))
 def test_bad_source_url_fails(self):
  data=fixture(); data["item-combat-profiles.json"][0]["source_urls"]=["file:///private/item"]
  report=audit_numeric_ranges(data)
  self.assertEqual(report["status"],"failed")
if __name__=="__main__": unittest.main()
