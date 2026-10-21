#!/usr/bin/env python3
"""Download the OSRS Wiki quest-category catalogue with pagination and provenance.

This is a title catalogue only. It deliberately does not infer quest prerequisites,
skill requirements, rewards, or account unlock eligibility from category membership.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "raw"
REPORTS = ROOT / "reports"
API_URL = "https://oldschool.runescape.wiki/api.php"
CATEGORY = "Category:Quests"
USER_AGENT = "OSRSHub-Game-Data/0.1 (quest catalogue; contact: repository maintainer)"


def api_url(params):
    return API_URL + "?" + urllib.parse.urlencode(params)


def fetch_category_members(opener=None, sleep=time.sleep):
    """Fetch every page member, following MediaWiki continuation tokens."""
    opener = opener or urllib.request.urlopen
    continuation = {}
    by_page_id = {}
    request_count = 0
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": CATEGORY,
            "cmtype": "page",
            "cmnamespace": 0,
            "cmlimit": "max",
            "format": "json",
            "formatversion": "2",
            **continuation,
        }
        request = urllib.request.Request(
            api_url(params),
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        with opener(request, timeout=45) as response:
            payload = response.read()
            status = getattr(response, "status", 200)
        if status != 200:
            raise RuntimeError(f"Wiki API returned HTTP {status}")
        data = json.loads(payload)
        if not isinstance(data, dict) or "error" in data:
            raise ValueError(f"Unexpected Wiki API response: {data.get('error', 'not an object') if isinstance(data, dict) else 'not an object'}")
        members = data.get("query", {}).get("categorymembers")
        if not isinstance(members, list):
            raise ValueError("Wiki API response did not contain query.categorymembers")
        for member in members:
            if not isinstance(member, dict):
                continue
            page_id, title = member.get("pageid"), member.get("title")
            if isinstance(page_id, int) and isinstance(title, str) and title.strip():
                by_page_id[page_id] = title.strip()
        request_count += 1
        next_token = data.get("continue")
        if not isinstance(next_token, dict):
            break
        continuation = next_token
        sleep(0.1)
    records = [
        {
            "id": page_id,
            "name": title,
            "url": "https://oldschool.runescape.wiki/w/" + urllib.parse.quote(title.replace(" ", "_"), safe="()_'!,"),
            "source_kind": "category_catalog_only",
        }
        for page_id, title in sorted(by_page_id.items(), key=lambda pair: (pair[1].casefold(), pair[0]))
    ]
    return records, request_count


def build_report(records, request_count, payload):
    names = [row["name"].casefold() for row in records]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if records else "empty",
        "source_url": api_url({
            "action": "query", "list": "categorymembers", "cmtitle": CATEGORY,
            "cmtype": "page", "cmnamespace": 0, "cmlimit": "max", "format": "json",
        }),
        "category": CATEGORY,
        "record_count": len(records),
        "duplicate_casefolded_title_count": len(names) - len(set(names)),
        "api_request_count": request_count,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "scope": "Catalogue of pages in the Wiki quest category only.",
        "not_provided": [
            "verified quest prerequisites",
            "skill-level requirements",
            "quest rewards",
            "membership status",
            "quest completion or account unlock eligibility",
        ],
        "account_safety_note": "This catalogue must not be used to infer quest completion, item access, prerequisites, skill requirements, or rewards. Those facts need separate source-backed extraction and validation.",
    }


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    try:
        records, request_count = fetch_category_members()
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        print(f"Quest catalogue download failed: {exc}", file=sys.stderr)
        return 1
    payload = (json.dumps(records, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    (RAW / "quest-catalog.json").write_bytes(payload)
    report = build_report(records, request_count, payload)
    (REPORTS / "quest-catalog-coverage.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if records else 1


if __name__ == "__main__":
    raise SystemExit(main())
