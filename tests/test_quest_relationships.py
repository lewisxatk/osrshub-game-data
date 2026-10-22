"""Tests for quest graph semantics and malformed inputs."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from build_quest_relationships import build_graph,find_cycles
def quest(key,name,requirements=None): return {"key":key,"name":name,"requirements":requirements or [],"skill_requirements":[],"source_url":None}
class QuestRelationshipTests(unittest.TestCase):
    def test_prerequisite_and_dependent_edges(self):
        rows,report=build_graph([quest("a","Cook's Assistant"),quest("b","Recipe for Disaster",["cook's assistant"])])
        child=next(r for r in rows if r["quest_key"]=="b"); parent=next(r for r in rows if r["quest_key"]=="a")
        self.assertEqual(child["prerequisites"],[{"quest_key":"a","name":"Cook's Assistant","completion_state":"completed"}])
        self.assertEqual(parent["dependents"],[{"quest_key":"b","name":"Recipe for Disaster"}]); self.assertEqual(report["resolved_prerequisite_edges"],1)
    def test_started_prefix(self):
        rows,report=build_graph([quest("a","Restless Ghost"),quest("b","Example Quest",["Started: Restless Ghost"])])
        self.assertEqual(next(r for r in rows if r["quest_key"]=="b")["prerequisites"][0]["completion_state"],"started"); self.assertEqual(report["unresolved_requirement_count"],0)
    def test_unresolved_and_ambiguous(self):
        _,report=build_graph([quest("a","Quest A",["Missing quest","Shared"]),quest("b","Shared"),quest("c","shared")])
        self.assertEqual({r["reason"] for r in report["unresolved_requirements"]},{"not_found","ambiguous_name"})
    def test_malformed_requirement_visible(self):
        rows,report=build_graph([{"key":"a","name":"Quest A","requirements":"Quest B"},quest("b","Quest B")])
        self.assertEqual(rows[0]["unresolved_requirements"],["'Quest B'"]); self.assertEqual(report["unresolved_requirements"][0]["reason"],"malformed_requirement_list")
    def test_invalid_entries_reported(self):
        rows,report=build_graph([{"key":"a","name":"Quest A","requirements":[None," "]}])
        self.assertEqual(rows[0]["unresolved_requirements"],[" ","None"]); self.assertEqual(report["unresolved_requirement_count"],2)
    def test_duplicate_keys_rejected(self):
        with self.assertRaisesRegex(ValueError,"duplicate quest key"): build_graph([quest("same","Quest A"),quest("same","Quest B")])
    def test_cycle_detection(self):
        _,report=build_graph([quest("a","Quest A",["Quest B"]),quest("b","Quest B",["Quest A"])])
        self.assertEqual(report["cycle_count"],1); self.assertEqual(report["status"],"failed")
    def test_long_chain_is_iterative(self):
        graph={str(i):{"prerequisites":[{"quest_key":str(i-1)}] if i else []} for i in range(1500)}
        self.assertEqual(find_cycles(graph),[])
    def test_raw_evidence_links_are_candidates_not_verified_edges(self):
        q1=quest("a","Biohazard")
        q1["requirement_evidence"]={"requirement_links":[{"title":"Plague City","url":"https://oldschool.runescape.wiki/w/Plague_City"}]}
        q2=quest("b","Plague City")
        rows,report=build_graph([q1,q2])
        bio=next(r for r in rows if r["quest_key"]=="a")
        self.assertEqual(bio["prerequisites"],[])
        self.assertEqual(bio["requirement_candidates"][0]["match_status"],"unique_unverified_candidate")
        self.assertEqual(bio["requirement_candidates"][0]["candidate_quest_keys"],["b"])

    def test_empty_graph(self):
        rows,report=build_graph([]); self.assertEqual(rows,[]); self.assertEqual(report["status"],"passed")
if __name__=="__main__": unittest.main()
