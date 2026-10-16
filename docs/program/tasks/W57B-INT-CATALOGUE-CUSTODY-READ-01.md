# Task W57B-INT-CATALOGUE-CUSTODY-READ-01 — unserved catalogue custody reader

task_id: W57B-INT-CATALOGUE-CUSTODY-READ-01

## Outcome

An authorized caller can obtain exact, bounded catalogue Blob bytes and an
independent `CatalogueExpectation` from one current Run's verified retrieval
set and pinned snapshot. The reader refuses absent, duplicate, inconsistent or
changed custody and stale Attempt authority before returning bytes.

## Depends on

- `W57A-SEAL-01A` — completed migration 0023 storage/custody seal.
- `W57A-SEAL-01B` — completed frozen contract reseal.
- `W57A-INT-SET-CUSTODY-READ-PREP-01` — completed public-port Attempt/Blob read pattern.
- `W57B-INT-CATALOGUE-QUERY-PREP-01` — completed canonical catalogue byte validator.
- `W57B-INT-REFERENCE-PIPELINE-PREP-01` — completed pure reference pipeline.
- `CFB-INT-DEV-PUBLISH-55` — completed base at `63fa3a40ef54a645dcc57ed99cfd1099b0574774`.

## Frozen inputs

- base commit: `63fa3a40ef54a645dcc57ed99cfd1099b0574774`
- API v1 SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256 `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- domain identifiers SHA-256 `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- errors SHA-256 `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations`, SHA-256 `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- catalogue query `1684cbc9cf3eb24ab51f4edbcc3bc16f51cce9dee2abb1fade2a18206fd69780`;
- W57 plan §§A3.3–A3.5, B3.1–B3.6; R-76, R-80, R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: snapshot `norm_document` count is checked against `norms_snapshot.document_count` before returning the independently pinned expectation.

## Captured premise evidence

- premise: `load_pinned_catalogue` requires bytes through a confirmed custody
  binding and independently pinned facts, while dev55 has no such catalogue
  reader and migration 0023 supplies the verified set and two custody roles.

### P-01 — exact base, requirement and absent reader

- captured_at: 2026-10-16
- command: `git rev-parse HEAD; rg -n 'The caller must fetch|independently pinned catalogue facts|load_pinned_catalogue|norm_catalogue' src/auditmanager/norms/references/catalogue_query.py src/auditmanager/norms/references/pipeline.py db/migrations/versions/20261016_0023_norm_citations.py | head -18; git ls-tree -r --name-only HEAD src/auditmanager/norms/references/catalogue_input.py tests/integration/norms/references/test_catalogue_input.py`
- captured_output:
  ```text
  63fa3a40ef54a645dcc57ed99cfd1099b0574774
  db/migrations/versions/20261016_0023_norm_citations.py:36:    "(role = 'norm_catalogue' AND target_kind = 'norm_retrieval_set' "
  db/migrations/versions/20261016_0023_norm_citations.py:255:                       WHERE b.role = 'norm_catalogue'
  db/migrations/versions/20261016_0023_norm_citations.py:494:            "WHERE role IN ('norm_retrieval_set','norm_catalogue'))"
  src/auditmanager/norms/references/pipeline.py:3:The caller supplies independently pinned catalogue facts. This function cannot
  src/auditmanager/norms/references/pipeline.py:13:    load_pinned_catalogue,
  src/auditmanager/norms/references/pipeline.py:52:    catalogue = load_pinned_catalogue(
  src/auditmanager/norms/references/catalogue_query.py:89:def load_pinned_catalogue(
  src/auditmanager/norms/references/catalogue_query.py:97:    The caller must fetch `blob` through a confirmed catalogue custody binding
  src/auditmanager/norms/references/catalogue_query.py:172:__all__ = ["CatalogueExpectation", "load_pinned_catalogue"]
  ```
- interpretation: an additive, unserved reader can close the source-custody
  seam without changing the pure validator, pipeline, schema or route.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/references/catalogue_input.py`
- `tests/integration/norms/references/test_catalogue_input.py`
- `docs/program/tasks/W57B-INT-CATALOGUE-CUSTODY-READ-01.md`
- `docs/program/W57B-INT-CATALOGUE-CUSTODY-READ-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, root dependencies/locks, composition root,
API/routes/public facades, `pipeline.py`, `catalogue_query.py`, findings,
W54/W56/W58 paths, production DB/S3/corpus, `CURRENT_STATE.md`, global styles,
remote refs, checkpoints and tags.

## Non-goals

No served caller, API or 0024 seal; no proof of qualified W54 corpus, reviewed
unparsed-slug listing, reference-resolution result or B3.5 acceptance; no
provider/model call, canonical expert decision, real DB/S3 suite or beta gate.

## Deliverables

One read-only public-port reader, focused offline tests, this task and a result
report. The existing pure catalogue validator remains the content gate.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/references/test_catalogue_input.py tests/integration/norms/references/test_catalogue_query.py`;
- Python compilation, task governance, `git diff --check`, exact allowed-path
  proof and frozen SHA-256 comparison;
- no PostgreSQL, S3, Docker, LibreOffice or full `make gate` while W56 real
  diagnostics occupy the host.

## Integration contract

The future caller owns authorization and a consistent, short transaction,
passing its `AttemptAuthority`, `Session` and `BlobStore`. This reader checks
the current Attempt, running/validating Run and its verified set, exact two
confirmed custody bindings and available Blob metadata, snapshot facts and
document totality, then reads the bounded object, hashes it independently and
rechecks Attempt and SQL pin. The caller passes `.data` and `.expectation` to
`load_pinned_catalogue` with a separately reviewed unparsed-slug tuple, and
rechecks publication authority later. The reader writes nothing.

## Failure/idempotency/security cases

Missing/duplicate custody, terminal Run, invalid digest/size, changed pin,
stale Attempt, lost/corrupt/oversized object refuse without fallback. The Blob
stream is closed on all read outcomes. Equal pinned inputs give equal bytes.
No source PDF content, token, credential or provider response enters Git.

## Rollback / feature flag

Additive unserved module; revert its scoped commit before activation. No data
rollback or runtime flag applies.
