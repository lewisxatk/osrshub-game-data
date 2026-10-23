# Item-to-quest unlock evidence audit

The Combat Studio planner consumes item-to-quest unlock records to avoid recommending gear that an account cannot use. This audit checks the evidence contract before those records are trusted as inputs.

## Run

```bash
python scripts/audit_item_quest_unlocks.py \
  --input examples/combat-studio-dps-unlocks.example.json \
  --output reports/item-quest-unlock-audit.json
```

The report tracks record count, explicit knowledge states (`known`, `known_empty`, and `unknown`), HTTPS source-pointer coverage, duplicate item IDs, contradictory states, and missing evidence.

- `known` requires at least one named quest.
- `known_empty` requires an explicitly empty quest list; it must not be used merely because no unlock record was found.
- `unknown` must not contain asserted quest requirements.
- Duplicate item IDs and contradictory states fail the audit.
- Missing or invalid source pointers and unknown states require review.
- Reserved `example.test` source URLs are treated as illustrative fixtures, never production evidence.

The audit is intentionally conservative. It does not infer quest unlocks or independently verify source claims. A passing structural audit means the records satisfy the contract, not that every item requirement is factually correct. The checked-in fixture is illustrative and should produce `review_required`, not a production-ready claim.
