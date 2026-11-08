#!/usr/bin/env python3
"""Import immutable OSRS Hub combat-engine catalogues without inventing facts.

The combat engine is the primary executable source for equipment and NPC combat
records. This importer preserves every record/variant and separately reports
which fields are present or unknown. It never synthesizes missing weaknesses,
attributes, immunities, requirements, or defensive values.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ENGINE_REPOSITORY = "lewisxatk/osrshub-combat-engine"
ENGINE_COMMIT = "bd565dc0d869a4771deac393bfe188e4fdcc1c3e"
SOURCES = {
    "monsters": "cdn/json/monsters.json",
    "equipment": "cdn/json/equipment.json",
}


def fetch_source(path: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    url = f"https://raw.githubusercontent.com/{ENGINE_REPOSITORY}/{ENGINE_COMMIT}/{path}"
    request = urllib.request.Request(url, headers={"User-Agent": "OSRS-Hub-Game-Data/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read()
    value = json.loads(payload)
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise ValueError(f"{path} must contain a JSON array of objects")
    return value, {
        "repository": ENGINE_REPOSITORY,
        "commit": ENGINE_COMMIT,
        "path": path,
        "url": url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "record_count": len(value),
    }


def audit_catalogues(monsters: list[dict[str, Any]], equipment: list[dict[str, Any]]) -> dict[str, Any]:
    monster_attributes: Counter[str] = Counter()
    weakness_elements: Counter[str] = Counter()
    weakness_known = 0
    defence_fields = ("stab", "slash", "crush", "magic", "light", "standard", "heavy", "flat_armour")
    defence_presence: Counter[str] = Counter()
    monster_identity_missing = 0
    for row in monsters:
        if row.get("id") is None or not row.get("name"):
            monster_identity_missing += 1
        for attribute in row.get("attributes") or []:
            monster_attributes[str(attribute)] += 1
        weakness = row.get("weakness")
        if isinstance(weakness, dict) and weakness.get("element") not in (None, "", "none"):
            weakness_known += 1
            weakness_elements[str(weakness["element"])] += 1
        defensive = row.get("defensive")
        if isinstance(defensive, dict):
            for field in defence_fields:
                if isinstance(defensive.get(field), (int, float)):
                    defence_presence[field] += 1

    slots: Counter[str] = Counter()
    equipment_identity_missing = 0
    two_handed_records = 0
    equipment_versions: Counter[str] = Counter()
    for row in equipment:
        if row.get("id") is None or not row.get("name") or not row.get("slot"):
            equipment_identity_missing += 1
        slots[str(row.get("slot") or "unknown")] += 1
        if row.get("isTwoHanded") is True:
            two_handed_records += 1
        equipment_versions[str(row.get("version") or "(base)")] += 1

    return {
        "schema_version": "1.0.0",
        "source_of_truth": "canonical OSRS Hub combat-engine JSON snapshots",
        "engine_repository": ENGINE_REPOSITORY,
        "engine_commit": ENGINE_COMMIT,
        "monster_catalogue": {
            "records": len(monsters),
            "records_without_id_or_name": monster_identity_missing,
            "records_with_verified_elemental_weakness_field": weakness_known,
            "records_without_verified_elemental_weakness": len(monsters) - weakness_known,
            "weakness_elements": dict(sorted(weakness_elements.items())),
            "attribute_record_counts": dict(sorted(monster_attributes.items())),
            "defensive_field_record_counts": dict(sorted(defence_presence.items())),
            "important_semantics": {
                "weakness": "Elemental spell weakness only; null/absent means unknown or no recorded elemental weakness, not a style weakness.",
                "defensive": "Per-style defence values; compare these separately from elemental weakness.",
                "attributes": "Engine attributes activate specialised weapon/effect rules. Preserve exact values and NPC variants.",
                "identity": "Preserve each array record and its record_index; numeric NPC IDs and display names are not unique across all variants."
            }
        },
        "equipment_catalogue": {
            "records": len(equipment),
            "records_without_id_name_or_slot": equipment_identity_missing,
            "two_handed_records": two_handed_records,
            "slot_record_counts": dict(sorted(slots.items())),
            "version_record_counts": dict(sorted(equipment_versions.items())),
            "important_semantics": {
                "version": "Operational state and variants matter (for example Charged versus Uncharged). Never collapse versions by display name alone.",
                "isTwoHanded": "Canonical two-handed flag; do not infer solely from item-name patterns.",
                "bonuses_offensive_defensive": "Canonical engine inputs. Set effects and special effects are calculated by the engine, not inferred from isolated item stats.",
                "market_price": "Not supplied by this catalogue. Join a fresh price source by item ID; absent price is unknown, not zero GP."
            }
        },
        "safety": {
            "missing_facts_invented": False,
            "records_deduplicated": False,
            "source_fields_overwritten": False
        }
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(output_dir: Path = ROOT / "dist", report_dir: Path = ROOT / "reports") -> dict[str, Any]:
    snapshots: dict[str, list[dict[str, Any]]] = {}
    provenance: list[dict[str, Any]] = []
    for name, path in SOURCES.items():
        snapshots[name], source = fetch_source(path)
        provenance.append(source)

    # Preserve each canonical record and its stable position in the upstream
    # array. This disambiguates same-ID/name NPC variants and equipment versions.
    monster_rows = [{**row, "record_index": index} for index, row in enumerate(snapshots["monsters"])]
    equipment_rows = [{**row, "catalogue_index": index} for index, row in enumerate(snapshots["equipment"])]
    write_json(output_dir / "combat-engine-monsters.json", monster_rows)
    write_json(output_dir / "combat-engine-equipment.json", equipment_rows)
    report = audit_catalogues(monster_rows, equipment_rows)
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    report["source_snapshots"] = provenance
    write_json(report_dir / "combat-engine-catalog-audit.json", report)
    write_json(output_dir / "combat-engine-catalog-manifest.json", {
        "schema_version": "1.0.0",
        "engine_repository": ENGINE_REPOSITORY,
        "engine_commit": ENGINE_COMMIT,
        "source_snapshots": provenance,
        "outputs": [
            {"path": "combat-engine-monsters.json", "records": len(monster_rows)},
            {"path": "combat-engine-equipment.json", "records": len(equipment_rows)}
        ]
    })
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--report-dir", type=Path, default=ROOT / "reports")
    args = parser.parse_args()
    report = run(args.output_dir, args.report_dir)
    print(json.dumps({
        "engine_commit": report["engine_commit"],
        "monster_records": report["monster_catalogue"]["records"],
        "equipment_records": report["equipment_catalogue"]["records"],
        "monsters_with_elemental_weakness": report["monster_catalogue"]["records_with_verified_elemental_weakness_field"],
        "monsters_without_verified_elemental_weakness": report["monster_catalogue"]["records_without_verified_elemental_weakness"]
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
