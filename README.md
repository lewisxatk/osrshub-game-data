# OSRS Hub Game Data

A standalone, reproducible data pipeline for structured Old School RuneScape (OSRS) game data. This repository is intentionally separate from the OSRS Hub website and its Cloudflare Worker/D1 systems.

## Goals

- Import source snapshots with URL, retrieval time, and SHA-256 provenance.
- Merge item and monster records by numeric ID while retaining compact source attribution.
- Report meaningful field disagreements separately from noisy timestamps and presentation-image fields.
- Validate generated JSON, IDs, duplicate IDs, source attribution, expected item examples, and basic combat-field coverage.
- Grow incrementally into equipment, weapon mechanics, NPCs, quests, spells, prayers, recipes, and verified combat rules.

Imported community data is evidence, not a guarantee of correctness or completeness. A passing structural validation does not prove game mechanics are accurate. Live Grand Exchange prices are out of scope; the existing OSRS Hub market feed remains separate.

## Requirements

- Python 3.10 or newer
- Internet access for source downloads
- `jsonschema` for schema validation (`python -m pip install -r requirements-ci.txt`)

## Quick start

From the repository root:

```bash
python scripts/download_sources.py
python scripts/audit_source_integrity.py
python scripts/build_dataset.py
python scripts/report_field_provenance.py
python scripts/validate_dataset.py
python scripts/audit_equipment.py
python scripts/normalize_combat_data.py
python scripts/normalize_monster_combat.py
python scripts/report_coverage.py
python scripts/audit_normalized_data.py
python scripts/validate_schemas.py
python -m unittest discover -s tests -v
```

On Windows, run these commands in Command Prompt or PowerShell.

## Outputs

- `sources/raw/`: downloaded upstream snapshots and `manifest.json`
- `dist/items.json`: compact merged item records
- `dist/equipment.json`: broad equipment candidates with available source metadata
- `dist/equipment-stats.json`: compact equipment slots, bonuses, requirements, source names, and Wiki links
- `dist/weapons.json`: compact weapon attack speeds, weapon types, stances, source names, and Wiki links
- `dist/monsters-combat.json`: normalized monster combat fields where available, with unknown values left null
- `dist/monsters.json`: compact merged monster records
- `dist/manifest.json`: generated counts, source precedence, and input SHA-256 hashes
- `reports/source-conflicts.json`: meaningful field disagreements, skipped source records, and counts of ignored volatile-field differences
- `reports/source-conflict-priorities.json`: conflicts ranked by field and category, with capped examples for targeted human review
- `reports/source-integrity.json`: downloaded snapshot SHA-256, byte-count, JSON-parse, and top-level-type checks against the retrieval manifest
- `reports/field-provenance.json`: per-field source presence and bounded examples of upstream disagreements for item and monster fields
- `reports/combat-reference-checks.json`: pass/fail results for the small, explicitly sourced combat regression fixture set
- `reports/pipeline-health.json`: consolidated statuses for validation, coverage, normalized-data audit, schema checks, combat readiness, and source-conflict review; incomplete inputs are marked explicitly
- `reports/validation.json`: structural checks and coverage counts
- `reports/coverage.json`: field-presence percentages across source and normalized item, equipment, weapon, and monster datasets
- `reports/normalized-data-audit.json`: duplicate/invalid ID checks, missing metadata counts, weapon-speed and stance gaps, and per-field monster combat coverage
- `reports/combat-readiness.json`: core-field coverage and readiness indicators for equipment, weapons, and monster combat datasets; presence is not a claim of factual accuracy
- `reports/equipment-audit.json`: examples and counts of missing equipment bonuses, slots, requirements, source URLs, weapon types, attack speeds, and stances
- `reports/combat-data-summary.json`: counts of normalized equipment and weapon records
- `reports/monster-combat-coverage.json`: per-field coverage percentages and examples of missing monster fields
- `reports/schema-validation.json`: JSON Schema validation results for compact items, monster combat, equipment stats, and weapon records

To compare two prior/current generated JSON arrays by record ID, run `python scripts/report_dataset_changes.py old-items.json new-items.json --output reports/item-changes.json`. The report lists added/removed IDs and changed fields; it does not judge whether a changed value is more accurate.\n\nCombat reference cases live in `tests/fixtures/combat-reference.json`. Keep this set small and reviewable; every case must include a source URL and review date. Update expected values only after checking the cited reference and the upstream mapping.\n\nGenerated data files are build outputs. Do not manually edit them; fix the pipeline or source mapping and rebuild. Raw snapshots are retained separately during the workflow and are available in the downloadable Actions artifact when included by the workflow.

## Conflict handling and provenance

The first source listed for each category in `scripts/build_dataset.py` has precedence for conflicting field values. Each merged record lists its source names. Exact raw snapshots are kept in `sources/raw/`; the download manifest records source URLs, retrieval metadata, and SHA-256 hashes. Large raw source records are no longer duplicated inside each merged record, and long conflict values are truncated in the report.

Timestamp and presentation-image differences are counted but omitted from the meaningful conflict list. Review meaningful conflicts before using disputed fields for game-mechanic calculations.

## Data sources

- OSRSBox database: https://github.com/osrsbox/osrsbox-db
- RSPSApp community extension: https://github.com/RSPSApp/osrsreboxed-db

Upstream field shapes can change; inspect reports and validate outputs after every refresh. The normalized-data audit distinguishes structural errors from metadata gaps: structural defects fail the step, while missing values remain warnings so unknown game mechanics are never guessed. Coverage and audit reports describe data shape and presence, not independent factual verification.

## Safety boundaries

- This repository does not deploy the website.
- It does not connect to Cloudflare, Workers, or D1.
- It does not modify Discord integration.
- It does not contain live GE price data.
- It does not claim that source coverage or combat formulas are complete.

## Next expansion

1. Use `coverage.json` and `equipment-audit.json` to prioritize missing equipment bonuses, weapon attack speeds, and stances.
2. Add source adapters and schemas for quests, spells, prayers, recipes, NPCs, and drop tables.
3. Keep item, monster combat, equipment stats, and weapon datasets validated against versioned JSON Schemas in CI.
4. Add regression fixtures for known OSRS examples, checked against trusted references.
5. Build combat formulas as separately tested code, with citations and test fixtures for verified mechanics.
