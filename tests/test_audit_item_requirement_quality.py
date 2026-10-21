"""Tests for conservative item-requirement coverage and provenance audit."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from audit_item_requirement_quality import audit_requirements
class RequirementQualityTests(unittest.TestCase):
    def setUp(self):
        self.items=[{"id":1,"name":"A"},{"id":2,"name":"B"},{"id":3,"name":"C"}]
        self.requirements=[{"item_id":1,"requirements":[{"skill":"Attack","level":60}],"sources":["OSRS Wiki"],"source_url":"https://oldschool.runescape.wiki/w/A"}]
    def test_missing_requirement_record_is_unknown_and_reported(self):
        result=audit_requirements(self.items,self.requirements)
        self.assertEqual(result["items_without_requirement_record"],2)
        self.assertEqual(result["status"],"incomplete")
        self.assertTrue(any("absence does not mean no requirement" in x for x in result["warnings"]))
    def test_duplicate_requirement_records_and_orphans_reported(self):
        rows=self.requirements+[dict(self.requirements[0]),{"item_id":999,"requirements":[],"sources":[],"source_url":None}]
        result=audit_requirements(self.items,rows)
        self.assertEqual(result["duplicate_requirement_item_ids"],[1])
        self.assertEqual(result["orphan_requirement_item_ids"],[999])
    def test_malformed_requirement_entry_is_reported(self):
        rows=[{"item_id":1,"requirements":[{"skill":"Attack","level":True}],"sources":[],"source_url":None}]
        result=audit_requirements(self.items,rows)
        self.assertEqual(result["requirement_entry_count"],0)
        self.assertTrue(result["malformed_entries"])
    def test_duplicate_item_ids_fail(self):
        result=audit_requirements([{"id":1},{"id":1}],[])
        self.assertEqual(result["status"],"failed")
        self.assertFalse(result["item_ids_unique"])
    def test_invalid_root_types_raise(self):
        with self.assertRaises(ValueError): audit_requirements({},[])
        with self.assertRaises(ValueError): audit_requirements([],{})
    def test_complete_fixture_still_requires_review(self):
        items=[{"id":1}]
        rows=[{"item_id":1,"requirements":[],"sources":["Wiki"],"source_url":"https://example.org/item"}]
        self.assertEqual(audit_requirements(items,rows)["status"],"review_required")
if __name__=="__main__":unittest.main()
