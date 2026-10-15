# Task W57B-INT-CATALOGUE-QUERY-PREP-01 — pinned catalogue byte adapter

task_id: W57B-INT-CATALOGUE-QUERY-PREP-01

## Outcome

A pure W57b adapter turns the exact canonical W57a catalogue artifact into
`PinnedCatalogue` only when its bytes, digest, pinned snapshot facts, document
count, stored designation tokens and reviewed unparsed listing agree. It
refuses incomplete or inconsistent input before reference resolution.

## Depends on

- `W57A-INT-SET-ARTIFACT-PREP-01` — completed catalogue artifact builder.
- `W57B-INT-REFERENCE-RESOLUTION-PREP-01` — completed pure reference resolver.
- `W57B-INT-CATALOGUE-SLUG-AUDIT-01` — completed local unparsed-slug audit; its candidate is not a reviewed list.

## Frozen inputs

- base commit `9e3ec73e3be2ba3326380ca2c8e77bda6ad1bb7d`;
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`, §§A3.2, B3.1–B3.3;
- W54 plan SHA-256 `b1b4acbf7ce02c4ef8b14533dedc8d7c9e64404b2f4cc0cc5c6342c9d7fdaf71`;
- W57a `norm-catalogue-prep-v1` canonical JSON shape and W57b `PinnedCatalogue` shape;
- migration head `0022_findings_v2`; planned verified-set table is migration `0023`, not present.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the frozen schema has the snapshot and generated designation tokens, but no verified retrieval-set row or catalogue custody role that could justify a database-backed verified read.

### P-01 — exact base and absent verified-set table

- captured_at: 2026-10-15
- command: `git rev-parse HEAD && (rg -l 'CREATE TABLE norm_retrieval_set|CREATE TABLE norm_catalogue' db/migrations/versions || true)`
- captured_output:
  ```text
  9e3ec73e3be2ba3326380ca2c8e77bda6ad1bb7d
  ```
- interpretation: no current migration creates the verified-set/catalogue table; this lane can validate supplied artifact bytes but cannot authenticate their DB origin.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/references/catalogue_query.py`
- `tests/integration/norms/references/test_catalogue_query.py`
- `docs/program/tasks/W57B-INT-CATALOGUE-QUERY-PREP-01.md`
- `docs/program/W57B-INT-CATALOGUE-QUERY-PREP-01.md`

## Forbidden hotspots

Existing source files, contracts, migrations, custody roles, provider lock,
runtime/API/composition root, corpus source and manifest, reviewed map,
promotion DB, root dependencies, global styles, `CURRENT_STATE.md`, tags,
`origin/dev` and `origin/main`.

## Non-goals

No SQL against a fictitious verified-set table, custody authentication,
proof that a DB query returned every snapshot document, reviewed exception
list, corpus promotion, runtime activation, provider call or beta acceptance.

## Deliverables

Additive byte adapter, focused fail-closed tests and task report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/references/test_catalogue_query.py tests/integration/norms/references/test_reference_resolution.py` — pass;
- compilation, task governance, whitespace and exact owned-path proof — pass;
- no full `make gate` under R-135.

## Integration contract

After migration `0023`, the runtime owner reads the run-pinned verified set,
the confirmed `norm_catalogue` custody binding and exact blob bytes; it
independently supplies the set's catalogue SHA-256 and snapshot row's identity,
content key, digest and document count. This adapter checks only those supplied
facts and returns `PinnedCatalogue` for the pure resolver. The runtime owner
must prove set verification, binding confirmation and DB snapshot totality.
The local 57-slug candidate is not an approved `listed_unparsed_slugs` input.

## Failure/idempotency/security cases

Wrong digest, malformed/noncanonical bytes, wrong snapshot facts, missing or
duplicate rows, token mismatch, unordered rows and unreviewed unparsed slugs
are refused. Equal inputs produce equal output. No norm text or credentials
enter Git.

## Rollback / feature flag

Revert the additive adapter before runtime wiring; no data rollback or flag.
