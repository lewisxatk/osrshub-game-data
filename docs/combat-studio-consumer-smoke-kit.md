# Combat Studio consumer smoke kit

Run against the generated bundle:

```bash
python scripts/build_combat_studio_v1_bundle_manifest.py
python scripts/smoke_test_combat_studio_bundle.py --dist-dir dist --output reports/combat-studio-consumer-smoke.json
python -m unittest discover -s tests -p 'test_combat_studio_consumer_smoke.py' -v
```

The smoke kit checks that each required artifact can be read, contains records, and exposes the declared identity field. It is deliberately a preflight, not proof that the frontend's actual data adapter works.

## Integration handoff

The website repository is separate: `lewisxatk/osrsflipit`. Its current package scripts include `npm test` and `npm run build`. Before wiring data into the app, inspect its existing architecture and tests, agree on an explicit adapter and preserve the existing trading, live GE, Cloudflare and Discord flows. Test against a copied fixture bundle first; do not replace production data or embed generated megabytes in the main UI component.

## Acceptance stages

1. Database CI and bundle manifest pass.
2. This structural smoke test passes.
3. Website adapter unit tests pass on fixtures.
4. Website build and existing regression tests pass.
5. A real consumer integration test verifies one item, one weapon, one monster and one quest case, including unknown/missing values.
6. Only then is the data import accepted for V1.
