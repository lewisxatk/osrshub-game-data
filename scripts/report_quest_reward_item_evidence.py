#!/usr/bin/env python3
"""Link quest reward text to item records only on exact normalized name matches.

This is evidence extraction, not a claim that a quest unlocks or makes an item usable.
No network requests, fuzzy matching, reward inference, or external game facts are used.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"


def canon(value):
    return " ".join(value.casefold().split()) if isinstance(value, str) else ""


def build_report(quests, items):
    if not isinstance(quests, list) or any(not isinstance(row, dict) for row in quests):
        raise ValueError("Quest dataset must be an array of objects")
    if not isinstance(items, list) or any(not isinstance(row, dict) for row in items):
        raise ValueError("Item dataset must be an array of objects")

    items_by_name = {}
    duplicate_item_names = set()
    for item in items:
        name = item.get("name")
        item_id = item.get("id")
        if not isinstance(name, str) or isinstance(item_id, bool) or not isinstance(item_id, int):
            continue
        key = canon(name)
        if key in items_by_name and items_by_name[key].get("item_id") != item_id:
            duplicate_item_names.add(key)
        else:
            items_by_name[key] = {"item_id": item_id, "item_name": name, "source_urls": item.get("sources", [])}

    matches = []
    unmatched = []
    unknown_reward_quests = []
    for quest in sorted(quests, key=lambda row: (canon(row.get("name")), str(row.get("key", "")))):
        name = quest.get("name")
        if not isinstance(name, str):
            continue
        states = quest.get("field_status") if isinstance(quest.get("field_status"), dict) else {}
        if states.get("rewards") != "known" or not isinstance(quest.get("rewards"), list):
            unknown_reward_quests.append({"quest_key": quest.get("key"), "quest_name": name, "reason": "Reward field is not explicitly marked known"})
            continue
        for reward in quest["rewards"]:
            if not isinstance(reward, str) or not reward.strip():
                continue
            reward_text = " ".join(reward.split())
            key = canon(reward_text)
            item = items_by_name.get(key)
            if item and key not in duplicate_item_names:
                matches.append({
                    "quest_key": quest.get("key"),
                    "quest_name": name,
                    "reward_text": reward_text,
                    "item_id": item["item_id"],
                    "item_name": item["item_name"],
                    "quest_source_url": (quest.get("field_sources") if isinstance(quest.get("field_sources"), dict) else {}).get("rewards") or quest.get("source_url"),
                    "item_source_urls": item["source_urls"] if isinstance(item["source_urls"], list) else [],
                    "match_method": "exact_case_insensitive_normalized_name",
                    "evidence_status": "source_reward_text_exactly_matches_item_name",
                    "interpretation": "The structured quest record lists reward text exactly matching this item name. This does not establish an equipment requirement, permanent unlock, or usability condition."
                })
            else:
                unmatched.append({
                    "quest_key": quest.get("key"),
                    "quest_name": name,
                    "reward_text": reward_text,
                    "reason": "No unique exact item-name match in generated items dataset" if key not in duplicate_item_names else "Item name is duplicated; ambiguous match withheld"
                })

    matches.sort(key=lambda row: (canon(row["quest_name"]), row["item_id"], canon(row["reward_text"])))
    unmatched.sort(key=lambda row: (canon(row["quest_name"]), canon(row["reward_text"])))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "review_required" if unmatched or unknown_reward_quests or not quests or not items else "passed",
        "quest_dataset_record_count": len(quests),
        "item_dataset_record_count": len(items),
        "exact_reward_item_match_count": len(matches),
        "unmatched_reward_text_count": len(unmatched),
        "quests_with_unknown_reward_fields": len(unknown_reward_quests),
        "matches": matches,
        "unmatched_reward_text": unmatched,
        "unknown_reward_quests": unknown_reward_quests,
        "guardrails": [
            "Generated datasets only; this report performs no network requests.",
            "Only an exact normalized reward-text to item-name match is accepted; ambiguous and fuzzy matches are withheld.",
            "A match is not proof that the item is usable, equipable, permanently unlocked, or only obtainable from this quest.",
            "Missing reward facts remain unknown, not empty; source URLs are provenance pointers, not live verification."
        ]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quests", default="dist/quests.json")
    parser.add_argument("--items", default="dist/items.json")
    parser.add_argument("--output", default="reports/quest-reward-item-evidence.json")
    args = parser.parse_args()

    try:
        quests = json.loads(Path(args.quests).read_text(encoding="utf-8"))
        items = json.loads(Path(args.items).read_text(encoding="utf-8"))
        report = build_report(quests, items)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "failed",
            "quest_dataset_record_count": 0,
            "item_dataset_record_count": 0,
            "exact_reward_item_match_count": 0,
            "unmatched_reward_text_count": 0,
            "quests_with_unknown_reward_fields": 0,
            "matches": [],
            "unmatched_reward_text": [],
            "unknown_reward_quests": [],
            "guardrails": ["No facts were inferred because required generated datasets could not be read."],
            "errors": [str(exc)]
        }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
