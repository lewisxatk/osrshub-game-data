# Integrated Database Release Gate

## Purpose

The release gate consolidates the database census, integrity, record quality, source freshness, domain coverage, cross-domain readiness, quest evidence, monster identity/drop links, and Combat Studio readiness reports into one conservative summary.

## Run

```bash
python scripts/build_integrated_release_gate.py --output reports/database-integrated-release-gate.json
python -m unittest tests.test_integrated_release_gate -v
```

## Status meanings

- `passed`: every configured component report exists and reports an accepted non-review status.
- `review_required`: at least one report requires interpretation or emits warnings. This is not equivalent to verified data.
- `failed`: a required report is missing, malformed, or reports a blocking failure.

The CI step only fails the workflow for a blocking `failed` status. `review_required` remains visible as a non-blocking research queue because incomplete source evidence is expected while the database is being expanded.

## Guardrails

- Missing report files are blocking; they are not silently replaced with empty objects.
- The report only summarizes the current reports' statuses and a small set of counts. It does not recompute or certify their underlying facts.
- Summed record counts across overlapping datasets must not be called a global unique entity count.
- A passing status does not prove source freshness, complete OSRS coverage, or accurate combat mechanics.
- Quest requirements and unlock relationships stay unverified unless their evidence pipeline explicitly marks them verified.

## Output

`reports/database-integrated-release-gate.json` gives per-component state, missing/invalid reports, warnings, and guardrails in a schema-validated JSON document.
