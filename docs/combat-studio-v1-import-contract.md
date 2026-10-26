# Combat Studio V1 import contract

Run:

```bash
python scripts/build_combat_studio_v1_import_contract.py --output reports/combat-studio-v1-import-contract.json
python -m unittest discover -s tests -p 'test_combat_studio_v1_import_contract.py' -v
```

The report checks nine required generated datasets for file presence, JSON array/object shape, identity-field availability, duplicate identifiers, empty datasets, and SHA-256 fingerprints. It emits one of three statuses:

- `blocked`: a required artifact is missing or malformed.
- `review_required`: files parse but at least one dataset is empty or has identity issues.
- `ready_for_consumer_smoke_test`: all required artifacts are structurally present and identity-clean.

The last status is intentionally not named production-ready. It does not verify every OSRS fact, combat formulas, unlock semantics, frontend field mappings, or a real consumer import. The consuming Combat Studio must run its own integration test before V1 is declared complete.
