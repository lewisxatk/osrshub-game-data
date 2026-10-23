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
python scripts/evaluate_ranged_loadout.py --selected examples/ranged-loadout-selected.example.json --costs examples/ranged-loadout-costs.example.json --inputs examples/ranged-loadout-inputs.example.json --budget 1000000
python scripts/normalize_player_profile.py --input examples/player-profile.json
python scripts/evaluate_combat_loadout.py --selected examples/combat-loadout-selected.example.json --costs examples/combat-loadout-costs.example.json --inputs examples/combat-loadout-inputs.example.json --budget 1000000 --style slash
python scripts/audit_combat_loadout_evaluation.py
python scripts/audit_item_combat_profiles.py
python scripts/build_item_requirements.py
python scripts/evaluate_item_eligibility.py --profile examples/player-profile.json
python scripts/plan_equipment_upgrades.py --profile examples/player-profile.json --costs examples/item-costs.example.json --budget 100000000 --objective melee_strength
python scripts/report_combat_categories.py
python scripts/normalize_monster_combat.py
python scripts/build_item_relationships.py
python scripts/download_quest_catalog.py
python scripts/download_quest_requirement_evidence.py
python scripts/extract_quest_skill_requirement_candidates.py
python scripts/import_quests.py
python scripts/build_quest_relationships.py
python scripts/audit_quest_fact_quality.py
python scripts/report_quest_readiness.py
python scripts/report_quest_gap_queue.py
python scripts/report_normalized_combat_provenance.py
python scripts/check_combat_reference.py
python scripts/audit_combat_inputs.py --profile examples/player-profile.json --costs examples/item-costs.example.json --inputs examples/weapon-baseline-input.json --budget 100000000
python scripts/report_coverage.py
python scripts/audit_normalized_data.py
python scripts/validate_schemas.py
python scripts/report_combat_readiness.py
python -m unittest discover -s tests -v
```

## Compare loadout upgrade deltas

Compare a current loadout with a candidate upgrade using the same caller-supplied combat inputs. The report separates slot-by-slot item changes, caller-supplied GP cost changes, attack/strength bonus deltas, and the scoped baseline DPS delta.

```bash
python scripts/compare_loadout_upgrade_delta.py \
  --baseline examples/loadout-upgrade-delta-baseline.example.json \
  --candidate examples/loadout-upgrade-delta-candidate.example.json \
  --costs examples/loadout-upgrade-delta-costs.example.json \
  --inputs examples/combat-loadout-inputs.example.json \
  --budget 100000000 --style slash \
  --output reports/loadout-upgrade-delta.json
```

This is the first comparison layer toward account-specific upgrade advice: it shows what changed and how the repository's current scoped arithmetic responds, without pretending that the model already covers a particular boss. Both sides must fit the supplied budget. The same effective levels and target-defence inputs are used for both sides. Unknown restrictions remain warnings; caller-provided prices are not live GE prices. Prayers, potions, special attacks, boss phases, immunities, and other unimplemented mechanics are not inferred. CI generates and schema-validates an illustrative report and tests budget, duplicate-slot, and upgrade-delta behavior.


## Expanded OSRS source domains

The pipeline now downloads and retains separate source snapshots for more than just items and monsters. It imports additional generated datasets for prayers, NPC drop tables and shared drop subtables, shop stock and shopkeepers, Slayer-master task lists, NPC interactions and dialogue, NPC summaries, object summaries, and model summaries.

Run the source download and import with:

    python scripts/download_sources.py
    python scripts/import_extended_sources.py
python scripts/report_extended_domain_readiness.py

The importer preserves upstream record fields and nested payloads, retains source keys, and attaches the upstream snapshot URL to each generated record. It deliberately does not guess joins between NPCs, items, drops, shops, or objects. Run `python scripts/report_extended_domain_readiness.py` after importing to inventory nested field paths and per-domain coverage across all 11 extended datasets. It flags duplicate source keys and missing provenance URLs, and emits a schema-validated report at `reports/extended-domain-readiness.json`. These extra domains expand the data available to the website, but do not yet mean every OSRS domain or every field is complete. Source availability and structural validation are not proof of game-fact accuracy. The snapshots are kept separately so source changes and field-level disagreements can be audited instead of silently blended.

## Unified OSRS Hub readiness matrix

Run `python scripts/report_hub_readiness_matrix.py --output reports/hub-readiness-matrix.json` to produce a cross-domain structural readiness report. It summarizes field presence and invalid/duplicate IDs, reports missing joins and orphan records separately, and ranks actionable data gaps. Duplicate detection uses a linear-time frequency count so the report remains practical as item datasets grow.

This report is a structural diagnostic, not a factual accuracy score. Missing records remain distinct from known-empty records, and the report does not infer OSRS requirements, combat values, or relationships.

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

**This is a candidate shortlist, not a complete gear optimiser.** The follow-on loadout search chooses one candidate per slot under a total budget by maximising the sum of the selected stat. It also prevents the same item ID from being selected in multiple equipment slots in one loadout. It is still not a DPS optimiser: candidates may have unknown quest/unlock restrictions, and a higher summed stat does not necessarily mean higher DPS.\n\n## Baseline weapon comparison\n\nThe weapon comparison combines the normalized weapon-speed and equipment-bonus records with the scoped formula primitives. Supply effective attack/strength/defence inputs and a GP cost per item. It ranks only weapons whose known skill requirements are met, flags unknown restrictions, and reports the calculation inputs. It is **not** a boss-specific calculator and does not account for special attacks, prayers, potions, target-specific mechanics or unverified unlocks.

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


## Evaluate a caller-selected melee loadout

Once generated profiles exist, a supplied item-ID list, GP cost map, effective combat inputs and target defence inputs can be evaluated:

```bash
python scripts/evaluate_combat_loadout.py --selected examples/combat-loadout-selected.example.json --costs examples/combat-loadout-costs.example.json --inputs examples/combat-loadout-inputs.example.json --budget 1000000 --style slash
```

This evaluator aggregates known melee attack and strength bonuses, enforces the supplied total budget and one-item-per-slot rule, finds the selected weapon's attack speed, and calculates scoped baseline hit chance/max hit/DPS with explicit limitations. Example costs and combat inputs are illustrative and must be replaced with verified values. It evaluates a selected loadout; it does not yet search every combination, calculate ranged or magic DPS, or model boss-specific mechanics.


The generated evaluation is also checked by `scripts/audit_combat_loadout_evaluation.py`, which verifies item cost totals, remaining-budget arithmetic, aggregate bonus totals, slot uniqueness and the presence of a non-negative baseline DPS result. These consistency checks catch report wiring errors but do not certify source facts or boss-specific accuracy.

## Account profile normalization

Run `python scripts/normalize_player_profile.py --input examples/player-profile.json` to normalize known skill names, validate 1–99 levels, de-duplicate quest/exclusion lists and report missing skills. Partial profiles stay partial; missing skills and quests are never inferred. Account provenance and checked dates are retained when supplied.

## Ranged loadout baseline

The ranged evaluator aggregates supplied ranged attack/ranged-strength bonuses, enforces the GP budget and one-weapon rule, and produces a scoped baseline hit-chance/max-hit/DPS report. It does not model ammunition effects, boosts, prayers, special attacks or boss mechanics, and is not a Vorkath optimiser.

## Compare loadout estimates

Use `python scripts/compare_loadout_reports.py --current reports/current.json --candidate reports/candidate.json` to calculate baseline DPS and cost changes, percentage improvement and additional GP per DPS. The report flags attack-style and weapon-speed mismatches but cannot prove inputs match; compare only reports with compatible assumptions.


## Database coverage scorecard

Run `python scripts/report_database_scorecard.py` after generating the datasets. It writes `reports/database-scorecard.json`, with per-dataset record counts, field-presence percentages, selected combat-profile readiness indicators, and a reproducible coverage index. The index is calculated from an explicitly configured list of field-presence opportunities; it is a progress-tracking metric, **not** a claim that the same percentage of all OSRS knowledge is complete or factually verified. An empty quest dataset scores zero presence rather than being treated as complete. The report is included in schema validation and the CI artifact.


## Database integrity audit

Run `python scripts/audit_database_integrity.py` after generating all datasets. It checks duplicate IDs, orphaned item/equipment/weapon/requirement joins, item-profile presence flags, and quest prerequisite references. It writes `reports/database-integrity.json`. Missing profiles and an empty quest catalogue are reported as coverage warnings; unknown prerequisites are never treated as absent.

## Coverage index interpretation

The database scorecard's `coverage_index_percent` is the arithmetic mean of the configured dataset coverage percentages. Each dataset has equal weight, including an empty dataset at 0%, so an empty quest catalogue is visible in the headline. This is a transparent progress index for the currently configured fields, not a universal percentage of all OSRS data or factual accuracy.


## Actionable database gap queue

Run `python scripts/report_database_gaps.py` after generating the datasets. It writes `reports/database-gap-queue.json`, prioritizing gaps in item requirement records, item relationships, combat-profile provenance, weapon attack speeds, monster core stats and quest coverage. Missing data remains unknown; this report never fills facts with guesses and never interprets missing quest relationships as proof that no prerequisites exist. CI generates and schema-validates the report.


## Numeric range and provenance audit

Run `python scripts/audit_numeric_provenance.py` after normalized datasets have been built. It checks IDs, weapon attack-speed tick values, numeric equipment bonuses, monster combat fields and retained HTTP(S) source URLs. It writes `reports/numeric-provenance-audit.json`. Broad outlier thresholds produce review warnings rather than silently changing data. Missing provenance is a warning, while malformed IDs, invalid numeric fields and invalid source URLs fail the audit. Passing means the selected structural/range checks passed—not that every game fact is independently verified.


## Expanded item relationship graph and audit

The item relationship builder now links each item by exact numeric ID to any available equipment-stat record, weapon record, normalized skill-requirement record, and joined item-combat profile. The generated graph retains the target dataset name and record ID; it does not infer missing records, quest unlocks, recipes, or drop sources.

Run:

```bash
python scripts/build_item_relationships.py
python scripts/audit_item_relationships.py
```

The graph audit verifies relationship types, target datasets, target existence, same-item joins, duplicate links, expected link coverage, and item-name consistency. It writes `reports/item-relationship-audit.json`; CI also validates that report against its JSON Schema. A passing result confirms structural join consistency only, not independent factual verification of OSRS data. The item checker and existing database-integrity audit remain in the pipeline.


## Database-only weapon checker and comparison

These commands read only the generated `dist/item-combat-profiles.json` dataset. They do not request external websites; retained source URLs are provenance fields, not live lookups.

```bash
python scripts/check_weapon_from_database.py --id 4587
python scripts/report_weapon_coverage.py
python scripts/compare_weapons_from_database.py --left 4587 --right 4151 --output reports/weapon-database-comparison.json
```

The weapon coverage report describes field presence and flags malformed or duplicate profile IDs. The comparison report shows stored bonus values side by side and computes a numeric delta only when both database records contain finite numeric values. Missing values remain unknown; no damage, eligibility, or DPS conclusion is inferred by this comparison. Both reports are checked against JSON Schemas in CI.


## Database-only loadout compatibility audit

Run `python scripts/audit_loadout_compatibility.py --selected examples/loadout-compatibility-selected.example.json --profile examples/player-profile.json` after joined item combat profiles have been generated. It checks selected item IDs against `dist/item-combat-profiles.json`, validates requested equipment slots, flags duplicate slots/items, evaluates only known skill requirements, respects manual exclusions, and can optionally audit caller-supplied GP costs and budgets. It never performs network lookups. Missing quest/unlock restrictions, requirements, skill levels, source URLs or prices remain unknown; a passing report means only that the selected known checks passed, not that the loadout is fully eligible or optimised for DPS.

### Quest data scope and trust model

The quest pipeline downloads the current OSRS Wiki quest title catalogue and extracts raw requirement-cell text and links from the [quest requirements table](https://oldschool.runescape.wiki/w/Quests/Requirements_by_quest). The extracted evidence is stored in `sources/raw/quest-requirement-evidence.json` and summarized in `reports/quest-requirement-evidence-coverage.json`.

**Raw evidence is not a verified prerequisite graph.** Links that match catalogue titles are emitted as unverified candidates; they are not promoted into prerequisite edges until the source facts are structurally reviewed. Skill levels, boostability, required-to-start versus required-to-complete, quest-point thresholds, rewards, and membership restrictions remain unknown unless supplied in structured source facts. A dash in a source table is retained as source text, not treated as proof that a quest has no requirements.

`reports/quest-fact-quality.json` separates known, unknown and known-empty fields. `reports/quest-gap-queue.json` ranks records needing source review. These reports measure evidence coverage and work priority, not factual accuracy. The full pipeline validates the extracted evidence schema and runs regression tests against known graph cases.


## Quest skill requirement candidates

The quest pipeline now scans the Wiki's raw quest-requirement text for conservative patterns such as `35 Crafting` and emits a separate candidate report at `reports/quest-skill-requirement-candidates.json`. Every match retains the quest key, source URL, catalogue-match status and explicit interpretation limits. Candidates are **not** promoted into normalized quest facts: this text alone may not establish whether a level is needed to start or complete a quest, whether boosts apply, or whether a no-match means no requirement. The candidate report is schema-validated in CI and covered by regression tests.


## Quest skill candidate quality audit

Run `python scripts/audit_quest_skill_candidates.py` after downloading quest requirement evidence and extracting skill-level candidates. The report `reports/quest-skill-candidate-audit.json` counts candidate matches by skill, highlights unmatched catalogue titles and repeated quest/skill matches for manual review, and shows how many evidence rows produced no skill-level text candidate. The Sailing skill is included in the conservative text matcher. A missing match is not evidence that a quest has no skill requirement, and this audit never promotes candidates into verified planner facts. CI tests the audit and validates its report schema.

## Account quest progression report

Run the account profile normalizer first, then build a conservative per-account quest progression report:

```bash
python scripts/normalize_player_profile.py --input examples/player-profile.json
python scripts/report_account_quest_progression.py --profile reports/normalized-player-profile.json
```

The report writes `reports/account-quest-progression.json` and labels each structured quest as completed, ready, blocked by a known unmet requirement, or unknown because the profile or facts are incomplete. A quest is only marked ready when prerequisite and skill requirement fields are explicitly marked known and all supplied requirements pass. Started-state prerequisites remain unknown because the current profile format tracks completed quests only. Raw wiki links and unverified candidates are never promoted to verified prerequisites by this report. CI tests the planner and validates its output schema.



## Cross-domain Combat Lab readiness audit

Run `python scripts/report_combat_lab_readiness.py` after generating the normalized datasets. The report `reports/combat-lab-readiness.json` measures item/equipment/weapon/monster/quest coverage, cross-domain joins, requirement-record gaps, missing weapon mechanics, unresolved quest facts, and source provenance. It emits prioritized follow-up work for an account-aware, budget-constrained, boss-aware Combat Lab.

This is a coverage and data-quality audit, not a DPS calculator or proof that source values are accurate. Missing facts remain unknown; a successful pipeline means checks passed, not that every item, quest restriction or combat mechanic is complete. CI runs regression tests and validates the report schema.


## Quest reward to item evidence (database-only)

Run this after the normalized item and quest datasets have been generated:

```bash
python scripts/report_quest_reward_item_evidence.py --output reports/quest-reward-item-evidence.json
```

The report joins structured quest reward text to `dist/items.json` using only exact, case-insensitive normalized name matches. It records both item IDs and the source pointers already present in the generated data. Fuzzy matches and duplicate item names are withheld; quests whose reward fields are not explicitly marked known are listed separately as unknown. This is intentionally conservative: an exact reward-text match does **not** prove the item is equippable, permanently unlocked, or usable only after that quest. CI runs regression tests and validates the report schema.


## Combat Studio join contract audit

After normalized items, equipment, weapons, requirements, item combat profiles, and monster combat records are generated, run:

```bash
python scripts/audit_combat_join_contract.py
```

The audit checks exact numeric-ID joins, duplicate or invalid identifiers, profile join flags, weapon stance names, numeric combat-field validity, and coverage gaps across the core Combat Studio datasets. Structural contradictions fail validation; missing facts are reported as gaps and are never converted into zeroes or treated as proof that an item has no requirements. The audit validates structural readiness only, not source accuracy, formula correctness, or boss-specific DPS.

Weapon stance names are retained when supplied by the source, along with combat-style, attack-style, and attack-type fields; the audit accepts meaningful source stance metadata without inventing a label when the source has none.


## Unified OSRS Hub readiness matrix

Run `python scripts/report_hub_readiness_matrix.py` after the source import, normalization, joined-profile and relationship steps. It writes `reports/hub-readiness-matrix.json`, a single operational view of nine core datasets: item identity, equipment, weapons, normalized requirements, joined combat profiles, monster combat facts, quests, quest relationships and item relationships.

The matrix reports record counts, field-presence percentages, malformed/duplicate IDs, exact-ID join gaps, and a severity-ranked work queue. It makes gaps actionable without pretending that missing data is a game fact. In particular, missing requirements are not interpreted as no requirements; unknown quest facts are not interpreted as no prerequisites; and coverage percentages do not measure factual accuracy. The report is generated during CI, schema-validated, and included with the workflow's JSON artifacts.

The matrix is a prioritization tool, not a release certificate: `review_required` means structural gaps remain visible, while `failed` means a required dataset could not be read. A zero-gap structural report still does not independently prove that the source facts or combat formulas are correct.
