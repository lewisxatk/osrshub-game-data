"""Tests for safe OSRS Wiki quest-catalogue retrieval and reporting."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import download_quest_catalog as catalog


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = json.dumps(payload).encode("utf-8")
        self.status = status
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return self.payload


class QuestCatalogTests(unittest.TestCase):
    def test_follows_continuation_and_deduplicates_page_ids(self):
        responses = [
            {"query": {"categorymembers": [
                {"pageid": 2, "title": "Cook's Assistant"},
                {"pageid": 1, "title": "Doric's Quest"}]},
             "continue": {"cmcontinue": "next", "continue": "-||"}},
            {"query": {"categorymembers": [
                {"pageid": 2, "title": "Cook's Assistant"},
                {"pageid": 3, "title": "Dragon Slayer"}]}},
        ]
        def opener(request, timeout=45):
            return FakeResponse(responses.pop(0))
        rows, calls = catalog.fetch_category_members(opener=opener, sleep=lambda _: None)
        self.assertEqual(calls, 2)
        self.assertEqual([row["id"] for row in rows], [2, 1, 3])
        self.assertEqual(len({row["id"] for row in rows}), 3)
        self.assertTrue(all(row["source_kind"] == "category_catalog_only" for row in rows))
        self.assertTrue(all(row["url"].startswith("https://oldschool.runescape.wiki/w/") for row in rows))

    def test_api_error_is_not_silently_accepted(self):
        with self.assertRaises(ValueError):
            catalog.fetch_category_members(
                opener=lambda request, timeout=45: FakeResponse({"error": {"code": "bad"}}),
                sleep=lambda _: None,
            )

    def test_empty_category_is_not_successful_report(self):
        report = catalog.build_report([], 1, b"[]")
        self.assertEqual(report["status"], "empty")
        self.assertIn("quest prerequisites", report["not_provided"])
        self.assertIn("must not be used", report["account_safety_note"])

    def test_report_marks_catalog_scope_and_hash(self):
        report = catalog.build_report([{"id": 1, "name": "Example"}], 1, b"payload")
        self.assertEqual(report["record_count"], 1)
        self.assertEqual(report["sha256"], __import__("hashlib").sha256(b"payload").hexdigest())
        self.assertIn("only", report["scope"])


if __name__ == "__main__":
    unittest.main()
