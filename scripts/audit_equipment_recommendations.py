#!/usr/bin/env python3
"""Audit equipment shortlist/loadout outputs for misleading or unsafe recommendations.

This checks internal consistency only. It cannot establish factual requirements,
quest unlocks, item variants, live prices, or actual combat performance.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
SAFE_CANDIDATE = "candidate_with_unknown_restrictions"

def audit(shortlist, loadout):
    errors, warnings, checks = [], [], []
    if not isinstance(shortlist, dict) or not isinstance(shortlist.get("results_by_slot"), dict):
        raise ValueError("shortlist must contain results_by_slot object")
    seen_slot_ids = {}
    candidate_ids = set()
    for slot, rows in shortlist["results_by_slot"].items():
        if not isinstance(rows, list):
            errors.append({"code":"malformed_slot_rows","slot":slot,"message":"Slot candidates must be an array"})
            continue
        local_ids = set()
        for index, row in enumerate(rows):
            where = f"{slot}[{index}]"
            if not isinstance(row, dict):
                errors.append({"code":"malformed_candidate","slot":slot,"index":index,"message":"Candidate must be an object"})
                continue
            item_id = row.get("item_id")
            status = row.get("status")
            if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 0:
                errors.append({"code":"invalid_item_id","slot":slot,"index":index,"message":"Candidate item_id must be a non-negative integer"})
            else:
                candidate_ids.add(item_id)
                if item_id in local_ids:
                    errors.append({"code":"duplicate_item_in_slot","slot":slot,"item_id":item_id,"message":"Duplicate item ID appears more than once in one slot"})
                local_ids.add(item_id)
            cost, value = row.get("cost"), row.get("objective_value")
            if status == SAFE_CANDIDATE:
                if isinstance(cost, bool) or not isinstance(cost, int) or cost < 0:
                    errors.append({"code":"selectable_without_cost","slot":slot,"item_id":item_id,"message":"Selectable-status candidate lacks a valid non-negative integer cost"})
                if isinstance(value, bool) or not isinstance(value, (int,float)):
                    errors.append({"code":"selectable_without_objective","slot":slot,"item_id":item_id,"message":"Selectable-status candidate lacks a numeric objective value"})
                if not isinstance(row.get("reasons"), list):
                    warnings.append({"code":"missing_reasons","slot":slot,"item_id":item_id,"message":"Candidate has no reasons array"})
                reasons = row.get("reasons", [])
                if not any(isinstance(reason, str) and ("unknown" in reason.casefold() or "not verified" in reason.casefold() or "not verified" in reason.casefold()) for reason in reasons):
                    warnings.append({"code":"restriction_caveat_not_obvious","slot":slot,"item_id":item_id,"message":"Candidate status is uncertain but its reasons do not clearly call out unresolved restrictions"})
            elif status in ("eligible", "confirmed_usable", "fully_eligible", "best_in_slot"):
                errors.append({"code":"unsupported_certainty_status","slot":slot,"item_id":item_id,"message":f"Status {status!r} overstates what this pipeline verifies"})
            if status == "candidate_with_unknown_restrictions" and (isinstance(cost, bool) or not isinstance(cost, int) or cost < 0):
                errors.append({"code":"unknown_cost_promoted","slot":slot,"item_id":item_id,"message":"Unknown or invalid cost must not be represented as a selectable candidate"})
        seen_slot_ids[slot] = len(local_ids)
    selected = []
    if loadout is not None:
        if not isinstance(loadout, dict) or not isinstance(loadout.get("selected_items"), list):
            raise ValueError("loadout must contain selected_items array")
        budget = loadout.get("budget_gp")
        total = loadout.get("total_cost_gp")
        if isinstance(budget, bool) or not isinstance(budget, int) or budget < 0:
            errors.append({"code":"invalid_loadout_budget","message":"Loadout budget must be a non-negative integer"})
        if isinstance(total, bool) or not isinstance(total, int) or total < 0:
            errors.append({"code":"invalid_loadout_total","message":"Loadout total cost must be a non-negative integer"})
        elif isinstance(budget, int) and not isinstance(budget, bool) and total > budget:
            errors.append({"code":"budget_overrun","message":"Reported loadout total exceeds budget"})
        selected_slots, selected_ids, computed_total = set(), set(), 0
        for index, row in enumerate(loadout["selected_items"]):
            if not isinstance(row, dict):
                errors.append({"code":"malformed_selected_item","index":index,"message":"Selected item must be an object"})
                continue
            item_id, slot, cost = row.get("item_id"), row.get("slot"), row.get("cost")
            if row.get("eligibility_status") != SAFE_CANDIDATE:
                errors.append({"code":"unsafe_selected_status","index":index,"item_id":item_id,"message":"Loadout includes a candidate not marked candidate_with_unknown_restrictions"})
            if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 0:
                errors.append({"code":"invalid_selected_id","index":index,"message":"Selected item ID must be a non-negative integer"})
            elif item_id in selected_ids:
                errors.append({"code":"duplicate_selected_item","item_id":item_id,"message":"Same item ID selected more than once"})
            selected_ids.add(item_id)
            if not isinstance(slot, str) or not slot.strip():
                errors.append({"code":"missing_selected_slot","index":index,"message":"Selected item must identify its slot"})
            elif slot.casefold().strip() in selected_slots:
                errors.append({"code":"duplicate_selected_slot","slot":slot,"message":"More than one item selected for the same slot"})
            else:
                selected_slots.add(slot.casefold().strip())
            if isinstance(cost, bool) or not isinstance(cost, int) or cost < 0:
                errors.append({"code":"invalid_selected_cost","index":index,"message":"Selected item cost must be a non-negative integer"})
            else:
                computed_total += cost
            selected.append({"item_id":item_id,"slot":slot,"cost":cost})
            if isinstance(item_id, int) and not isinstance(item_id, bool) and item_id not in candidate_ids:
                warnings.append({"code":"selected_item_not_in_shortlist","item_id":item_id,"message":"Selected item does not appear in supplied shortlist"})
        if isinstance(total, int) and not isinstance(total, bool) and computed_total != total:
            errors.append({"code":"total_cost_mismatch","message":f"Selected item costs sum to {computed_total}, but report says {total}"})
        if loadout.get("status") not in ("stat_loadout_candidate", "search_truncated"):
            warnings.append({"code":"unexpected_loadout_status","message":"Loadout status is unfamiliar; review before consumption"})
    checks = [
        "No recommendation status is treated as proof of factual requirements or unlocks.",
        "No loadout is considered a verified DPS or best-in-slot result.",
        "Costs are checked for consistency only and are not live market prices."
    ]
    return {
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "status":"failed" if errors else ("review_required" if warnings else "passed"),
        "shortlist_slots_checked":len(shortlist["results_by_slot"]),
        "shortlist_unique_item_ids":len(candidate_ids),
        "selected_items_checked":len(selected),
        "error_count":len(errors),"warning_count":len(warnings),
        "errors":errors,"warnings":warnings,"checks":checks,
        "limitations":["Structural consistency is not proof of OSRS factual correctness.","Missing requirement or quest data remains unknown, not proof that no restriction exists."]
    }

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shortlist",default=str(REPORTS/"equipment-shortlist.json"))
    parser.add_argument("--loadout",default=str(REPORTS/"equipment-loadout-candidate.json"))
    parser.add_argument("--output",default=str(REPORTS/"equipment-recommendation-audit.json"))
    args=parser.parse_args()
    try:
        result=audit(read_json(args.shortlist),read_json(args.loadout))
    except (OSError,json.JSONDecodeError,ValueError) as exc:
        print(json.dumps({"status":"failed","error":str(exc)},indent=2)); return 1
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
    return 1 if result["status"]=="failed" else 0

if __name__=="__main__":
    raise SystemExit(main())
