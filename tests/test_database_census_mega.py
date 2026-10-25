import json, sys, tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from build_database_census import build_census, inspect_file
from audit_database_record_quality import audit_rows, audit_directory
from report_source_snapshot_freshness import build_freshness, walk_metadata
from build_domain_coverage_matrix import build_matrix
from report_database_release_gates import build_gates

class DatabaseCensusMegaTests(unittest.TestCase):
 def test_census_counts_files_and_rows_without_claiming_global_unique_entities(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/"items.json").write_text('[{"id":1},{"id":2}]');(p/"equipment-stats.json").write_text('[{"id":1}]')
   r=build_census(p)
   self.assertEqual(r["totals"]["dataset_file_count"],2);self.assertEqual(r["totals"]["record_rows_across_files"],3)
   self.assertIn("not a global unique-entity count",r["definition"])
 def test_census_reports_duplicate_ids(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"items.json";p.write_text('[{"id":1},{"id":1}]')
   self.assertEqual(inspect_file(p)["duplicate_identity_count"],1)
 def test_census_handles_invalid_json(self):
  with tempfile.TemporaryDirectory() as d:
   (Path(d)/"broken.json").write_text('{bad')
   r=build_census(Path(d));self.assertEqual(r["status"],"failed");self.assertEqual(r["totals"]["invalid_json_file_count"],1)
 def test_census_counts_zero_as_present_and_null_as_missing(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"items.json";p.write_text('[{"id":0,"name":null},{"id":1,"name":"A"}]')
   r=inspect_file(p);self.assertEqual(r["fields"]["id"]["present_records"],2);self.assertEqual(r["fields"]["name"]["missing_records"],1)
 def test_census_rejects_boolean_identity_as_valid(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"items.json";p.write_text('[{"id":true}]')
   self.assertEqual(inspect_file(p)["invalid_identity_count"],1)
 def test_quality_duplicate_and_numeric_detection(self):
  r=audit_rows([{"id":1,"name":"A","hitpoints":-1},{"id":1,"name":" ","attack_speed":True}],"items.json")
  self.assertEqual(r["duplicate_identity_count"],1);self.assertEqual(r["invalid_numeric_value_count"],2);self.assertEqual(r["blank_name_count"],1)
 def test_quality_accepts_zero_stats(self):
  r=audit_rows([{"id":0,"name":"Fixture","hitpoints":0}],"items.json")
  self.assertEqual(r["invalid_numeric_value_count"],0);self.assertEqual(r["missing_identity_count"],0)
 def test_quality_does_not_modify_input(self):
  rows=[{"id":1,"name":"A"}];before=json.dumps(rows);audit_rows(rows,"items.json");self.assertEqual(json.dumps(rows),before)
 def test_quality_handles_empty_array(self):
  r=audit_rows([],"items.json");self.assertEqual(r["record_count"],0);self.assertEqual(r["issue_count"],0)
 def test_manifest_metadata_walk(self):
  m={"sources":[{"url":"https://example.org/a","retrieved_at":"2026-10-24T12:00:00Z","sha256":"abc"}]}
  r=walk_metadata(m);self.assertEqual(len(r),1);self.assertEqual(r[0]["url"],"https://example.org/a")
 def test_freshness_marks_missing_manifest_review_not_fresh(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/"a.json").write_text('[{"id":1}]')
   r=build_freshness(p,p/"manifest.json",datetime(2026,10,25,tzinfo=timezone.utc))
   self.assertEqual(r["status"],"review_required");self.assertEqual(r["raw_snapshot_file_count"],1)
 def test_freshness_reports_hash_and_row_count(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/"manifest.json").write_text('{"sources":[{"url":"https://x.test","retrieved_at":"2026-10-24T00:00:00Z","sha256":"abc"}]}')
   (p/"a.json").write_text('[{"id":1},{"id":2}]')
   r=build_freshness(p,p/"manifest.json",datetime(2026,10,25,tzinfo=timezone.utc))
   self.assertEqual(r["raw_snapshot_record_rows"],2);self.assertEqual(r["metadata_entries_without_parseable_timestamp"],0)
 def test_matrix_groups_domains(self):
  c={"datasets":[{"file":"items.json","domain":"items","record_count":2,"unique_identity_count":2,"byte_size":10,"field_count":2}]}
  q={"datasets":[{"file":"items.json","issue_count":1,"duplicate_identity_count":1,"missing_identity_count":0}]}
  r=build_matrix(c,q);self.assertEqual(r["domains"]["items"]["dataset_count"],1);self.assertEqual(r["domains"]["items"]["quality_issue_count"],1)
 def test_release_gates_make_missing_core_dataset_blocking(self):
  c={"datasets":[],"totals":{"invalid_json_file_count":0}};q={"datasets":[],"issue_count":0}
  f={"status":"passed","metadata_entries_without_parseable_timestamp":0};m={"dataset_count":1}
  r=build_gates(c,q,f,m);self.assertEqual(r["status"],"blocked");self.assertEqual(r["release_decision"],"do_not_promote")
 def test_release_gates_report_unknown_quest_data_as_review(self):
  c={"datasets":[{"file":n,"record_count":0,"unique_identity_count":0} for n in ["items.json","equipment-stats.json","weapons.json","item-requirements.json","item-combat-profiles.json","monsters-combat.json","quests.json","quest-relationships.json","item-relationships.json","npc-drops.json","prayers.json"]],"totals":{"invalid_json_file_count":0}}
  q={"datasets":[],"issue_count":0};f={"status":"passed","metadata_entries_without_parseable_timestamp":0};m={"dataset_count":1}
  r=build_gates(c,q,f,m);self.assertEqual(r["status"],"review_required");self.assertTrue(any("Empty core datasets" in g["detail"] for g in r["gates"]))
 def test_release_gate_does_not_claim_fact_accuracy(self):
  c={"datasets":[],"totals":{}};q={};f={};m={}
  r=build_gates(c,q,f,m);self.assertIn("not an OSRS fact-accuracy certificate"," ".join(r["guardrails"]))
if __name__=="__main__":unittest.main()
