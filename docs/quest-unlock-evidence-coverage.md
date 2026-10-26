# Quest and item unlock evidence coverage

This report summarizes the current generated quest catalogue, item-to-quest unlock evidence, and quest prerequisite relationship graph. It is designed to expose missing evidence rather than manufacture facts.

Run:

```bash
python scripts/report_quest_unlock_coverage.py --output reports/quest-unlock-coverage.json
python -m unittest discover -s tests -p 'test_quest_unlock_coverage.py' -v
```

The report tracks quest requirement/reward knowledge states, source URL presence, duplicate quest keys, item unlock records with missing/orphan item IDs, and unresolved prerequisite edges.

**Interpretation:** `known_empty` means a source-backed workflow explicitly records no requirements; missing records, blanks, dashes, and `unknown` do not mean no requirement. Exact reward-text-to-item matches are evidence of reward wording only, not proof of permanent unlock or account eligibility. Source URL presence does not independently verify a claim.

The report is a coverage/review queue, not a factual validator or a complete quest graph.
