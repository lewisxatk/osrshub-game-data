# Monster Atlas and DPS Envelope

This milestone adds a database-backed monster atlas, a random factual field picker,
combat-level-band coverage, identity integrity checks, explicit monster/drop ID
link auditing, and an arithmetic DPS envelope.

## Outputs

| Report | Purpose |
| --- | --- |
| \`reports/monster-atlas.json\` | Snapshot counts, per-field presence, combat-level bands, highest-HP rows, and one random existing fact |
| \`reports/monster-random-fact.json\` | A standalone, source-attributed fact selected from a populated monster field |
| \`reports/monster-coverage-matrix.json\` | Coverage by combat-level band with separate denominators |
| \`reports/monster-identity-audit.json\` | Duplicate IDs/names, missing identity fields, invalid numeric fields |
| \`reports/monster-drop-link-audit.json\` | Explicit numeric joins between monster IDs and drop records |
| \`reports/monster-dps-envelope.json\` | Constant-DPS time-to-kill estimates for caller-supplied scenarios |

## Run locally

\`\`\`bash
python scripts/normalize_monster_combat.py
python scripts/build_monster_atlas.py --seed 42
python scripts/audit_monster_coverage_matrix.py
python scripts/audit_monster_identity.py
python scripts/audit_monster_drop_links.py
python scripts/analyze_monster_dps_envelope.py
\`\`\`

Omit \`--seed\` to select a fresh random fact each run. Use a fixed seed for a
repeatable report. The selected value is copied from the generated monster data;
the report does not claim that the source value was independently verified.

## DPS envelope contract

Each scenario must provide a finite positive \`player_dps\`. When \`monster_id\` is
provided, the analyzer uses that monster's positive \`hitpoints\` from the generated
database and refuses to substitute caller-provided HP if the ID is unknown. Without
a monster ID, a positive \`target_hitpoints\` is treated as an explicit scenario
input, useful for synthetic regression fixtures.

The estimate is \`target_hitpoints / player_dps\`. Ticks are estimated using the
explicit 0.6-second tick assumption. Theoretical kills/hour excludes travel,
respawn, movement, downtime, supplies, healing, phases, immunities, defence
changes, and loot collection. It is not an OSRS boss simulator, kill-rate promise,
or source-verified DPS calculation.

## Interpretation guardrails

- Field presence measures coverage, not factual accuracy.
- A zero value is retained as a value; null and invalid numbers count as missing.
- Names are not automatically merged, and source keys are not treated as NPC IDs.
- Unresolved drop links are not reported as orphaned links.
- No missing monster stats, attack styles, weaknesses, drop rates, or player DPS are inferred.
- These are generated CI artifacts. They are not committed as a fake snapshot and do not alter the live website, Cloudflare, GE feed, or Discord integration.
