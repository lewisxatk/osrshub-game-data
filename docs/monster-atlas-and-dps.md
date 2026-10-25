undefined

## Expanded atlas tools

The milestone also emits a full fact-card catalogue, a field-presence triage report,
a DPS sensitivity curve at 50%, 75%, 90%, 100%, 110%, 125% and 150% of supplied
DPS, and a name/numeric-filter search interface.

\`\`\`bash
python scripts/build_monster_fact_catalog.py
python scripts/report_monster_readiness.py
python scripts/analyze_monster_dps_sensitivity.py
python scripts/search_monster_database.py --query dragon --min-level 100
python scripts/audit_monster_source_provenance.py
\`\`\`

The source provenance audit compares shared numeric aliases in the raw community and
original snapshots. It reports equal, conflicting, and one-sided fields without
choosing a winner or changing normalized data. The readiness report is a data-cleanup
priority score, not a claim that a monster is ready for accurate DPS simulation.
