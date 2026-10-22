#!/usr/bin/env python3
"""Build a conservative account quest progression report from known facts only."""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"

def canon(value):
    return " ".join(value.casefold().split()) if isinstance(value, str) else ""

def build_report(quests, relationships, profile):
    errors, warnings = [], []
    if not isinstance(quests, list):
        errors.append("Quest dataset must be an array"); quests = []
    if not isinstance(relationships, list):
        errors.append("Quest relationship dataset must be an array"); relationships = []
    if not isinstance(profile, dict):
        errors.append("Normalized player profile must be an object"); profile = {}
    if profile.get("import_status") == "invalid" or profile.get("errors"):
        errors.append("Player profile contains validation errors")
    completed = {canon(x) for x in profile.get("completed_quests", []) if isinstance(x, str)}
    skills = profile.get("skills", {}) if isinstance(profile.get("skills"), dict) else {}
    skill_lookup = {canon(k): v for k, v in skills.items()}
    rel_by_key = {r.get("quest_key"): r for r in relationships if isinstance(r, dict) and isinstance(r.get("quest_key"), str)}
    quest_by_name = {}
    for q in quests:
        if isinstance(q, dict) and isinstance(q.get("name"), str):
            quest_by_name.setdefault(canon(q["name"]), []).append(q)
    rows = []
    for q in sorted((x for x in quests if isinstance(x, dict) and isinstance(x.get("name"), str)), key=lambda x: (canon(x["name"]), str(x.get("key", "")))):
        name = q["name"]
        key = q.get("key")
        states = q.get("field_status") if isinstance(q.get("field_status"), dict) else {}
        requirement_state = states.get("requirements", "unknown")
        skill_state = states.get("skill_requirements", "unknown")
        relation = rel_by_key.get(key, {})
        blockers, unknowns = [], []
        if canon(name) in completed:
            status = "completed"
        else:
            if requirement_state != "known":
                unknowns.append("Quest prerequisite facts are not marked as known")
            elif isinstance(q.get("requirements"), list):
                for requirement in q["requirements"]:
                    text = requirement if isinstance(requirement, str) else ""
                    required_name = text.split(":", 1)[1].strip() if text.casefold().startswith("started:") else text.strip()
                    if not required_name:
                        unknowns.append("Malformed prerequisite fact"); continue
                    if canon(required_name) not in completed:
                        blockers.append({"type": "quest", "name": required_name, "required_state": "started" if text.casefold().startswith("started:") else "completed", "reason": "not listed as completed in this profile"})
            else:
                unknowns.append("Known prerequisite field is not a list")
            if skill_state != "known":
                unknowns.append("Skill requirement facts are not marked as known")
            elif isinstance(q.get("skill_requirements"), list):
                for requirement in q["skill_requirements"]:
                    if not isinstance(requirement, dict) or not isinstance(requirement.get("skill"), str) or isinstance(requirement.get("level"), bool) or not isinstance(requirement.get("level"), int):
                        unknowns.append("Malformed skill requirement fact"); continue
                    actual = skill_lookup.get(canon(requirement["skill"]))
                    if actual is None:
                        unknowns.append(f"Account level for {requirement['skill']} is unknown")
                    elif actual < requirement["level"]:
                        blockers.append({"type": "skill", "name": requirement["skill"], "required_level": requirement["level"], "account_level": actual})
            else:
                unknowns.append("Known skill requirement field is not a list")
            if relation.get("unresolved_requirements"):
                unknowns.append("Relationship graph has unresolved prerequisite references")
            status = "blocked" if blockers else "unknown" if unknowns else "ready"
        rows.append({"quest_key": key, "quest_name": name, "status": status, "blockers": blockers, "unknowns": sorted(set(unknowns)), "requirement_fact_status": requirement_state, "skill_requirement_fact_status": skill_state, "source_url": q.get("source_url")})
    counts = {status: sum(row["status"] == status for row in rows) for status in ("completed", "ready", "blocked", "unknown")}
    if not quests: warnings.append("No structured quest facts are available; the title catalogue alone cannot establish readiness")
    if profile.get("import_status") != "validated": warnings.append("Account profile is partial or not fully provenance-validated")
    if counts["unknown"]: warnings.append(f"{counts['unknown']} quests have insufficient facts to determine readiness")
    if any(row["status"] == "blocked" for row in rows): warnings.append("Blocked means a known requirement is not met; it does not imply all other requirements are known")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if errors else "review_required" if counts["unknown"] or warnings else "passed",
        "account_label": profile.get("label", "Imported account"),
        "quest_count": len(rows),
        "counts": counts,
        "ready_quest_names": [r["quest_name"] for r in rows if r["status"] == "ready"],
        "quests": rows,
        "errors": errors,
        "warnings": warnings,
        "interpretation": "Ready means every requirement field used by this report is explicitly marked known and all listed requirements are met. Unknown facts are never treated as no requirements; completed quests are based only on the supplied profile."
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="reports/normalized-player-profile.json")
    parser.add_argument("--output", default="reports/account-quest-progression.json")
    args = parser.parse_args()
    def load(path, fallback):
        try: return json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError): return fallback
    result = build_report(load(DIST / "quests.json", []), load(DIST / "quest-relationships.json", []), load(args.profile, {}))
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "failed" else 0

if __name__ == "__main__":
    raise SystemExit(main())
