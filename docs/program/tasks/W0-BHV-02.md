# Task W0-BHV-02 — selected golden journeys and edge-case matrix

## Outcome

Create a reviewable golden plan containing exactly five stable, synthetic or
anonymized journeys derived from the accepted legacy inventory. Each journey must
separate observed legacy behavior from the intended greenfield target and define
machine-readable structural expectations for later characterization tests.

## Ownership

- implementation owner: planned agent `/root/w0_golden_journeys`
- program integrator: primary agent `/root`
- independent reviewer: assigned by the integrator; must not author reviewed files
- product/domain approval authority: repository owner/user

## Depends on

- Completed `W0-BHV-01`, accepted at
  `667fb00fe3e45d1ce0bce7860725c1654b4cdeba`.
- Completed `W0-DEP-01`, accepted at
  `ab1cfdab0ec5c413b188a44ff82a99586ecd7994`.
- Completed `W0-EVD-01`, accepted at
  `134436502b7ee40ca9abb061e0080741a863ffda`.
- Completed `W0-QA-02`, accepted at
  `6c82004b35f49463c8e7fc8602fbced2f374167e`.

## Frozen inputs

- base commit: `6c82004b35f49463c8e7fc8602fbced2f374167e`
- accepted inventory semantics at `667fb00fe3e45d1ce0bce7860725c1654b4cdeba`;
  normalized immutable locators at `134436502b7ee40ca9abb061e0080741a863ffda`
- immutable legacy oracle: `32b9d903792b30506048a1d42b0e6b2d07aee403`
- domain/API/analysis/event/comparison contracts: advisory drafts at the base commit;
  read-only and not ratified
- migration head: none
- validator/dependency gate: accepted `W0-QA-02` and `W0-DEP-01` commits above

## Allowed paths

- `fixtures/golden/**`

No other path is writable.

## Forbidden hotspots

- `docs/behavior/legacy_capability_inventory.md` and `docs/PRODUCT_SYNOPSIS.md`
- `docs/architecture/**`, `contracts/**`, `tests/**`
- root dependencies/locks, migrations, composition root, global styles
- `docs/program/CURRENT_STATE.md`, checkpoint registry/evidence and stage plans
- every legacy repository file/ref/worktree entry

## Non-goals

- No production or legacy runtime execution.
- No customer/production PDF, payload, model response, credential or `.env` content.
- No contract freeze or resolution of owner decisions.
- No claim that live LLM text is byte-stable.
- No fabricated graphic comparison, Run identity or append-only legacy behavior.

## Deliverables

1. Update `fixtures/golden/README.md` with the selected-set convention.
2. Add `SELECTION.md`, `EDGE_CASE_MATRIX.md`, `selection.schema.json`,
   `journey-manifest.schema.json` and `selection.json`.
3. `selection.json` contains a `journeys` array with exactly the ordered IDs below,
   an exact `manifest_path` of `fixtures/golden/<journey_id>/manifest.json`, and the
   exact non-empty `inventory_candidates` mapping in the table below.
   Add exactly these five `GJ-*` directories and that manifest filename in each:
   - `GJ-01`: ingest/version plus malformed, duplicate, conflict, isolation and path
     cases;
   - `GJ-02`: interruption/resume/retry/skip, text/block-stage invalidation,
     provider timeout, missing norm, successful Excel export and ZIP-without-Excel
     failure;
   - `GJ-03`: finding rerun/carryover, provider failure/no-overwrite provenance and
     expert decision correction/revocation;
   - `GJ-04`: comparison links/reuse/stale invalidation/recompute, raw-vs-AI
     evidence and repair snapshot/audit/undo;
   - `GJ-05`: worker reconnect/outbox ACK, lost/new/stale worker state, crash
     recovery/hash replay/result publication plus route-flag/auth behavior.
4. Each manifest requires `journey_id`, `comparison_mode`, `provenance`,
   `input_manifest`, `expected_outputs` and `failure_cases`. `provenance` requires
   `legacy_source_commit`, `method`, `data_classification` and a non-empty
   `evidence` array; each evidence item has a `source_ref` beginning with the full
   immutable legacy SHA followed by `:`.
5. Every expectation is tagged `legacy_observed`, `greenfield_target` or
   `pending_owner_decision`. A target divergence is never represented as parity.
6. Provider replay material, if any, is minimal, synthetic and explicitly reviewed.

### Inventory-candidate to selected-journey mapping

The inventory IDs and selected IDs are different namespaces. `inventory_candidates`
is the normative, lossless fan-in map; no inventory candidate may be omitted or
mapped more than once.

| Selected journey | Inventory candidates |
|---|---|
| `GJ-01` | `GJ-01` |
| `GJ-02` | `GJ-02`, `GJ-07` |
| `GJ-03` | `GJ-03`, `GJ-04` |
| `GJ-04` | `GJ-05`, `GJ-06` |
| `GJ-05` | `GJ-08`, `GJ-09`, `GJ-10`, `GJ-11` |

Graphic/vector comparison absence is an additive `PD-04` target-scope annotation,
not a twelfth inventory candidate and not part of the fan-in map.

## Required tests

- Command: `python3 -c "import json; from pathlib import Path; [json.loads(p.read_text()) for p in Path('fixtures/golden').rglob('*.json')]"`.
  Expected: exit `0`; every JSON file parses.
- Command: `.venv/bootstrap/bin/python -c "import json; from pathlib import Path; from jsonschema import Draft202012Validator as V; root=Path('fixtures/golden'); selection=json.loads((root/'selection.json').read_text()); selection_schema=json.loads((root/'selection.schema.json').read_text()); manifest_schema=json.loads((root/'journey-manifest.schema.json').read_text()); V.check_schema(selection_schema); V.check_schema(manifest_schema); V(selection_schema).validate(selection); [V(manifest_schema).validate(json.loads((root/x['journey_id']/'manifest.json').read_text())) for x in selection['journeys']]"`.
  Expected: exit `0`; schemas and every selected manifest validate. A missing key,
  extra journey or invalid enum exits non-zero and never prints `PASS`.
- Command: `python3 -c "import json,re; from pathlib import Path; root=Path('fixtures/golden'); ids=['GJ-01','GJ-02','GJ-03','GJ-04','GJ-05']; mapping={'GJ-01':['GJ-01'],'GJ-02':['GJ-02','GJ-07'],'GJ-03':['GJ-03','GJ-04'],'GJ-04':['GJ-05','GJ-06'],'GJ-05':['GJ-08','GJ-09','GJ-10','GJ-11']}; inventory_ids=[f'GJ-{n:02d}' for n in range(1,12)]; sha='32b9d903792b30506048a1d42b0e6b2d07aee403'; selection=json.loads((root/'selection.json').read_text()); rows=selection['journeys']; assert [x['journey_id'] for x in rows]==ids; assert {x['journey_id']:x['inventory_candidates'] for x in rows}==mapping; flattened=[candidate for x in rows for candidate in x['inventory_candidates']]; assert sorted(flattened)==inventory_ids and len(flattened)==len(set(flattened))==11; assert [x['manifest_path'] for x in rows]==[f'fixtures/golden/{x}/manifest.json' for x in ids]; assert sorted(p.name for p in root.glob('GJ-*') if p.is_dir())==ids; manifests=[json.loads((root/x/'manifest.json').read_text()) for x in ids]; assert [m['journey_id'] for m in manifests]==ids; assert all(m['comparison_mode'] in {'exact','semantic','replay'} for m in manifests); assert all(m['provenance']['legacy_source_commit']==sha and m['provenance']['method'] and m['provenance']['data_classification'] in {'synthetic','anonymized'} and m['provenance']['evidence'] and all(e['source_ref'].startswith(sha+':') for e in m['provenance']['evidence']) for m in manifests); assert all(all(e['provenance_class'] in {'legacy_observed','greenfield_target','pending_owner_decision'} for e in m['expected_outputs']) for m in manifests); text_suffixes={'.json','.md','.txt','.yaml','.yml'}; raw='\n'.join(p.read_text() for p in root.rglob('*') if p.is_file() and p.suffix.lower() in text_suffixes); assert not re.search(r'(?i)\b(TODO|TBD|placeholder)\b|refs/heads/|legacy_source_commit\s*[:=]\s*[\"\x27]?(main|dev)\b',raw)"`.
  Expected: exit `0`; exact ordered IDs/directories, immutable provenance,
  classification and expectation tags match. Omission, substitution, placeholder,
  moving ref or wrong SHA exits non-zero.
- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`.
  Expected: exit `0` with standalone `PASS`.
- Command: `git diff --check -- fixtures/golden`.
  Expected: exit `0` and no output.
- Independent reviewer samples every journey against the accepted inventory and at
  least one immutable legacy evidence object.

## Integration contract

Downstream QA may rely on stable journey IDs, synthetic inputs, structural expected
outputs, failure matrix and comparison mode. Only `legacy_observed` items are parity
oracle evidence. `greenfield_target` and `pending_owner_decision` remain explicitly
non-legacy and cannot silently freeze product semantics.

## Failure / idempotency / security

- Secret-shaped, customer or production data: stop, do not copy, report exclusion.
- Missing/contradictory evidence: mark pending/contradicted; do not infer.
- Re-running selection updates the same stable journey files and recomputes declared
  checksums; it must not duplicate IDs/directories.
- Malformed fixtures and provider failures must have explicit expected states; no
  silent fallback may turn them into success.

## Rollback / feature flag

Fixture/documentation-only task; no feature flag applies. Roll back only the task's
`fixtures/golden/**` commit. No schema, migration, runtime or external state exists.

## Handoff

- changed files and journey count/IDs
- commands/results and reviewer samples
- new/changed contracts: `none`
- all pending owner decisions and sensitive-data exclusions
- integration notes for `W0-QA-01`
- allowed-path diff and confirmation that legacy/frozen hotspots were not changed
