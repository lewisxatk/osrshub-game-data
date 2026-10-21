"""Tests for actionable database gap reporting."""
import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from report_database_gaps import build_gap_report

def fixture():
 return {
  "items.json":[{"id":1,"name":"Sword","equipable_by_player":True},{"id":2,"name":"Bone","equipable_by_player":False}],
  "equipment-stats.json":[{"id":1,"name":"Sword","requirements":{"attack":40}}],
  "weapons.json":[{"id":1,"name":"Sword","attack_speed":4}],
  "item-requirements.json":[],
  "item-combat-profiles.json":[{"id":1,"equipment_record_present":True,"source_urls":["https://example.test"]}],
  "monsters-combat.json":[{"id":1,"combat_level":10,"hitpoints":10,"attack_level":10,"strength_level":10,"defence_level":10}],
  "quests.json":[],"quest-relationships.json":[],
  "item-relationships.json":[{"item_id":1,"relationships":[]}]}

class DatabaseGapTests(unittest.TestCase):
 def test_empty_quest_data_is_explicit_critical_gap(self):
  report=build_gap_report(lambda name:fixture()[name])
  gap=next(g for g in report["gaps"] if g["key"]=="quest_catalogue_empty")
  self.assertEqual(gap["priority"],"critical")
  self.assertEqual(gap["affected_records"],1)
 def test_missing_requirement_is_not_called_no_requirement(self):
  report=build_gap_report(lambda name:fixture()[name])
  gap=next(g for g in report["gaps"] if g["key"]=="equipment_requirement_record_missing")
  self.assertEqual(gap["affected_records"],1)
  self.assertIn("must not be treated as no requirements",gap["impact"])
 def test_valid_speed_has_no_speed_gap(self):
  report=build_gap_report(lambda name:fixture()[name])
  gap=next(g for g in report["gaps"] if g["key"]=="weapon_attack_speed_invalid_or_missing")
  self.assertEqual(gap["affected_records"],0)

if __name__=="__main__": unittest.main()
