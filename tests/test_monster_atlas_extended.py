import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from build_monster_fact_catalog import build_catalog
from report_monster_readiness import report
from analyze_monster_dps_sensitivity import analyze
from search_monster_database import search
from audit_monster_source_provenance import audit

class MonsterAtlasExtendedTests(unittest.TestCase):
 def setUp(self):
  self.rows=[{"id":1,"name":"Alpha goblin","combat_level":2,"hitpoints":5,"attack_level":1,"strength_level":1,"defence_level":1,"attack_speed":4,"max_hit":1,"sources":["a"]},
             {"id":2,"name":"Beta dragon","combat_level":200,"hitpoints":300,"sources":["b"]},
             {"id":3,"name":"Unknown","combat_level":None,"hitpoints":None,"sources":[]}]
 def test_fact_catalog_preserves_records(self):
  c=build_catalog(self.rows);self.assertEqual(c["record_count"],3);self.assertEqual(c["fact_cards"][0]["record"]["id"],1)
 def test_fact_catalog_does_not_claim_verification(self):
  c=build_catalog(self.rows);self.assertIn("not_independently_verified",c["fact_cards"][0]["verification_status"])
 def test_fact_catalog_reports_null_as_unknown(self):
  c=build_catalog(self.rows);unknown=next(x for x in c["fact_cards"] if x["id"]==3);self.assertIn("hitpoints",unknown["unknown_fields"])
 def test_readiness_counts_missing_fields(self):
  r=report(self.rows);self.assertEqual(r["record_count"],3);self.assertEqual(r["field_missing_counts"]["hitpoints"],1)
 def test_readiness_does_not_call_score_accuracy(self):
  self.assertIn("not an accuracy",report(self.rows)["definition"])
 def test_search_casefolds_names(self):
  r=search(self.rows,"DRAGON");self.assertEqual(r["match_count"],1);self.assertEqual(r["results"][0]["id"],2)
 def test_search_filters_by_combat_level(self):
  r=search(self.rows,min_level=100);self.assertEqual([x["id"] for x in r["results"]],[2])
 def test_search_filters_by_hitpoints(self):
  r=search(self.rows,min_hp=100);self.assertEqual([x["id"] for x in r["results"]],[2])
 def test_search_excludes_unknown_numeric_values_from_numeric_filters(self):
  self.assertEqual(search(self.rows,min_hp=1)["match_count"],2)
 def test_search_rejects_extreme_limit(self):
  with self.assertRaises(ValueError):search(self.rows,limit=501)
 def test_dps_sensitivity_monotonic(self):
  r=analyze([{"scenario_id":"a","target_hitpoints":100,"player_dps":10}],[])
  curve=r["results"][0]["sensitivity"]
  self.assertEqual(len(curve),7)
  self.assertGreater(curve[0]["time_to_kill_seconds"],curve[-1]["time_to_kill_seconds"])
 def test_dps_sensitivity_uses_db_hp(self):
  r=analyze([{"scenario_id":"a","monster_id":2,"player_dps":10}],self.rows)
  self.assertEqual(r["results"][0]["hitpoints"],300)
 def test_dps_sensitivity_unknown_id_is_not_estimated(self):
  r=analyze([{"scenario_id":"a","monster_id":99,"target_hitpoints":100,"player_dps":10}],self.rows)
  self.assertEqual(r["results"][0]["status"],"unknown_monster_id")
 def test_dps_sensitivity_invalid_dps_fails(self):
  with self.assertRaises(ValueError):analyze([{"scenario_id":"a","target_hitpoints":100,"player_dps":0}],[])
 def test_provenance_reports_differences_without_winner(self):
  r=audit({"a":[{"id":1,"name":"A","hitpoints":10}],"b":[{"id":1,"name":"A","hitpoints":12}]})
  self.assertEqual(r["conflict_count"],1);self.assertEqual(r["conflicts"][0]["left_value"],10);self.assertEqual(r["conflicts"][0]["right_value"],12)
 def test_provenance_equal_fields_are_not_conflicts(self):
  r=audit({"a":[{"id":1,"hitpoints":10}],"b":[{"id":1,"hitpoints":10}]})
  self.assertEqual(r["conflict_count"],0);self.assertEqual(r["field_summary"]["hitpoints"]["equal"],1)
 def test_provenance_missing_values_are_separate(self):
  r=audit({"a":[{"id":1,"hitpoints":10}],"b":[{"id":1}]})
  self.assertEqual(r["field_summary"]["hitpoints"]["one_missing"],1)
 def test_provenance_does_not_join_non_numeric_ids(self):
  r=audit({"a":[{"id":"x","hitpoints":10}],"b":[{"id":"x","hitpoints":12}]})
  self.assertEqual(r["overlapping_numeric_id_count"],0)
 def test_duplicate_ids_use_first_record_and_are_guarded(self):
  r=audit({"a":[{"id":1,"hitpoints":10},{"id":1,"hitpoints":20}],"b":[{"id":1,"hitpoints":10}]})
  self.assertEqual(r["field_summary"]["hitpoints"]["equal"],1)
  self.assertIn("duplicate IDs", " ".join(r["guardrails"]))
if __name__=="__main__":unittest.main()
