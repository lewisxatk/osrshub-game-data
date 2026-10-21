# OSRS Hub Game Data

A standalone, reproducible data pipeline for structured Old School RuneScape (OSRS) game data. This repository is separate from the OSRS Hub website and its Cloudflare Worker/D1 systems.

## Goals

- Import source snapshots with URL, retrieval time, and SHA-256 provenance.
- Merge item and monster records by numeric ID while retaining source attribution.
- Report field disagreements separately from volatile timestamps and presentation-image fields.
- Validate generated JSON, IDs, source attribution and combat-field coverage.
- Grow into equipment, weapon mechanics, NPCs, quests, spells, prayers, recipes and verified combat rules.

Imported community data is evidence, not a guarantee of correctness or completeness. Structural validation does not prove game mechanics are accurate. Live Grand Exchange prices remain out of scope.

## Requirements

- Python 3.10 or newer
- Internet access for source downloads
- jsonschema (install with `python -m pip install -r requirements-ci.txt`)

## Quick start

Run from the repository root:

```bash
python scripts/download_sources.py
python scripts/audit_source_integrity.py
python scripts/build_dataset.py
python scripts/report_field_provenance.py
python scripts/report_item_identity.py
python scripts/validate_dataset.py
python scripts/audit_equipment.py
python scripts/normalize_combat_data.py
python scripts/build_item_combat_profiles.py
python scripts/audit_item_combat_profiles.py
python scripts/build_item_requirements.py
python scripts/evaluate_item_eligibility.py --profile examples/player-profile.json
python scripts/plan_equipment_upgrades.py --profile examples/player-profile.json --costs examples/item-costs.example.json --budget 100000000 --objective melee_strength
python scripts/report_combat_categories.py
python scripts/normalize_monster_combat.py
python scripts/build_item_relationships.py
python scripts/download_quest_catalog.py
python scripts/import_quests.py
python scripts/build_quest_relationships.py
python scripts/report_quest_readiness.py
python scripts/report_normalized_combat_provenance.py
python scripts/check_combat_reference.py
python scripts/audit_combat_inputs.py --profile examples/player-profile.json --costs examples/item-costs.example.json --inputs examples/weapon-baseline-input.json --budget 100000000
python scripts/report_coverage.py
python scripts/audit_normalized_data.py
python scripts/validate_schemas.py
python scripts/report_combat_readiness.py
python -m unittest discover -s tests -v
```

## Search the generated data

```bash
python scripts/query_game_data.py --dataset weapons --search whip
python scripts/query_game_data.py --dataset equipment-stats --id 4151
python scripts/query_game_data.py --dataset item-combat-profiles --id 4151
python scripts/query_game_data.py --dataset quest-relationships --search dragon
```

The query interface searches only records present in generated datasets. Missing records and fields are unknown, not proof that an item is usable or a quest is unnecessary.

## Budget-aware equipment shortlist

```bash
python scripts/plan_equipment_upgrades.py --profile examples/player-profile.json --costs examples/item-costs.example.json --budget 100000000 --objective melee_strength
```

Provide a JSON object mapping item IDs to GP costs with `--costs`. The checked-in cost file is illustrative only, not live or authoritative pricing. Supported objectives include attack bonuses, melee/ranged strength, magic damage, defensive bonuses and prayer. The tool ranks items within individual equipment slots, filters known skill failures, honours manual exclusions and shows unknown requirements.

**This is a candidate shortlist, not a complete gear optimiser.** The follow-on loadout search chooses one candidate per slot under a total budget by maximising the sum of the selected stat. It is still not a DPS optimiser: candidates may have unknown quest/unlock restrictions, and a higher summed stat does not necessarily mean higher DPS.\n\n## Baseline weapon comparison\n\nThe weapon comparison combines the normalized weapon-speed and equipment-bonus records with the scoped formula primitives. Supply effective attack/strength/defence inputs and a GP cost per item. It ranks only weapons whose known skill requirements are met, flags unknown restrictions, and reports the calculation inputs. It is **not** a boss-specific calculator and does not account for special attacks, prayers, potions, target-specific mechanics or unverified unlocks.

## Item requirement completeness audit

```bash
python scripts/audit_item_requirement_quality.py
```

This reports how many equipment records have a normalized skill-requirement record, malformed or duplicate records, orphan IDs, and source provenance coverage. It deliberately labels incomplete coverage: missing records do not prove an item has no requirements, and a skill requirement record is not a complete unlock/quest eligibility result.

## Combat input audit

```bash
python scripts/audit_combat_inputs.py --profile examples/player-profile.json --costs examples/item-costs.example.json --inputs examples/weapon-baseline-input.json --budget 100000000
```

This checks profile skill ranges, exclusions, cost-map shape, required effective combat inputs and provenance warnings before a baseline comparison. It validates structure and plausible ranges only; it cannot establish that the upstream game facts or effective-level calculations are correct. Warnings about missing source URLs or dates are retained in the JSON report rather than silently treated as verified.

## Scoped combat arithmetic

```bash
python scripts/combat_math.py --input examples/combat-baseline-input.json
```

The current formula primitives calculate attack and defence rolls, roll-comparison hit chance, max hit from a precomputed effective strength level and strength bonus, average damage, expected damage per attack and simple DPS using attack speed in ticks (600 ms per tick).

**This is not a complete Combat Lab calculator.** Effective levels and bonuses must be supplied; this code does not derive them from player settings or equipment. Prayers, potions, special attacks, weapon-specific effects, damage caps, NPC phases, immunities and other exceptions must be added as separately sourced, tested rules before boss-specific DPS recommendations are reliable.

## Data sources

- OSRSBox database: https://github.com/osrsbox/osrsbox-db
- RSPSApp community extension: https://github.com/RSPSApp/osrsreboxed-db
- OSRS Wiki: https://oldschool.runescape.wiki/

Coverage reports describe field presence, not independent factual verification.

## Safety boundaries

- This repository does not deploy the website or modify Cloudflare, Workers, D1 or Discord.
- It does not contain live GE prices.
- It does not claim source coverage or combat formulas are complete.

## Next milestones

1. Build a maintained source-backed adapter for quest prerequisites, skill levels, rewards and unlocks; the Wiki title catalogue is not a quest-fact dataset.
2. Verify equipment and monster combat fields against trusted sources and expand regression fixtures.
3. Add source-backed effective-level and equipment effect rules, then model prayers, potions, target-specific defence, damage caps and special attacks.
4. Connect formula primitives to validated player/equipment/monster records and add loadout search under budget and exclusions.
5. Publish versioned datasets and integrate with the website only under a separate approved plan.


## Joined item combat profiles

After the item, equipment, weapon and skill-requirement datasets have been generated, run:

```bash
python scripts/build_item_combat_profiles.py
python scripts/query_game_data.py --dataset equipment-stats --id 4151
```

The pipeline writes `dist/item-combat-profiles.json` and `reports/item-combat-profile-summary.json`. Each profile joins source-backed item identity, equipment bonuses, weapon speed/type/stances, normalized skill requirements and provenance URLs where available. Missing fields remain `null`; absent requirement records are explicitly distinguished from an empty list. This is a joined factual data profile, not a DPS result: the profile does not infer missing unlocks or calculate boss damage.


The joined profiles can be audited with `python scripts/audit_item_combat_profiles.py`. The audit flags malformed IDs, invalid attack speeds, duplicate skill requirements, missing source URLs and incomplete stat coverage. Warnings mean records need review; the audit never fills missing bonuses with zero and never treats absent requirements as proof of no requirements. Query the joined dataset with `--dataset item-combat-profiles`.
