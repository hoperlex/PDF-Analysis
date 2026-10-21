# Task W57B-INT-REFERENCE-LIST-BOUNDS-01 — bound explicit slug listing

task_id: W57B-INT-REFERENCE-LIST-BOUNDS-01

## Outcome

The unserved Run reference chain rejects a malformed or impossibly large
explicit unparsed-slug tuple before either saved Blob read. After the
verified catalogue read, it also rejects a tuple longer than the snapshot's
declared document count before extraction. These are evidence-derived bounds,
not a reviewed-slug policy or a new count ceiling.

## Depends on

- `W57B-INT-RUN-REFERENCE-CHAIN-01` — completed read-only composed chain.
- `W57B-INT-CATALOGUE-CUSTODY-READ-01` — completed bounded catalogue reader.
- `W57B-INT-CATALOGUE-QUERY-PREP-01` — completed canonical JSON validator.
- `CFB-INT-DEV-PUBLISH-65` — completed exact development base.

## Frozen inputs

- base commit: `8c39b9e0dfd63da7d32d1a848e609ae2dd437a01`
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- W57 plan SHA-256: `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`;
- code-first plan SHA-256: `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- migration head `0023_norm_citations`, SHA-256 `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- chain SHA-256: `2915c524cacefaa81555d115458bd8fec3ad9ef7228e8027a16c556acd8be6a8`;
- catalogue reader SHA-256: `4600cd274615f233c889f473d69c00209f49b0dfbf0dd6647fa330bfa6728c57`;
- canonical catalogue validator SHA-256: `1684cbc9cf3eb24ab51f4edbcc3bc16f51cce9dee2abb1fade2a18206fd69780`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: the listing is checked against the verified snapshot's
  complete document count; no maintained enumerator changes.

## Captured premise evidence

- premise: the chain only checks tuple type before it reads both Blobs, while
  the pure validator traverses each slug afterwards and the catalogue reader
  already has a 10 MB byte cap.

### P-01 — delayed listing validation on exact base

- captured_at: 2026-10-16
- command: `rg -n 'listed_unparsed_slugs|load_saved_reference_text|load_verified_catalogue|_MAX_BYTES|max_catalogue_bytes' src/auditmanager/runs/reference_pipeline.py src/auditmanager/norms/references/catalogue_input.py src/auditmanager/norms/references/catalogue_query.py`
- captured_output:
  ```text
  src/auditmanager/norms/references/catalogue_query.py:43:_MAX_BYTES = 10_000_000
  src/auditmanager/norms/references/catalogue_query.py:70:    if not isinstance(blob, bytes) or not blob or len(blob) > _MAX_BYTES:
  src/auditmanager/norms/references/catalogue_query.py:93:    listed_unparsed_slugs: tuple[str, ...],
  src/auditmanager/norms/references/catalogue_query.py:110:    if not isinstance(listed_unparsed_slugs, tuple):
  src/auditmanager/norms/references/catalogue_query.py:113:    for slug in listed_unparsed_slugs:
  src/auditmanager/norms/references/catalogue_query.py:118:    if not isinstance(blob, bytes) or not blob or len(blob) > _MAX_BYTES:
  src/auditmanager/norms/references/catalogue_input.py:119:def load_verified_catalogue(
  src/auditmanager/norms/references/catalogue_input.py:121:    max_catalogue_bytes: int = 10_000_000, jobs: JobRepository | None = None,
  src/auditmanager/norms/references/catalogue_input.py:128:    if (type(max_catalogue_bytes) is not int
  src/auditmanager/norms/references/catalogue_input.py:129:            or not 1 <= max_catalogue_bytes <= 10_000_000):
  src/auditmanager/norms/references/catalogue_input.py:141:        or type(size) is not int or not 1 <= size <= max_catalogue_bytes
  src/auditmanager/norms/references/catalogue_input.py:176:    "CatalogueInputRefused", "VerifiedCatalogueInput", "load_verified_catalogue",
  src/auditmanager/runs/reference_pipeline.py:18:    load_verified_catalogue,
  src/auditmanager/runs/reference_pipeline.py:22:from auditmanager.runs.reference_text_input import load_saved_reference_text
  src/auditmanager/runs/reference_pipeline.py:80:    listed_unparsed_slugs: tuple[str, ...],
  src/auditmanager/runs/reference_pipeline.py:82:    max_catalogue_bytes: int,
  src/auditmanager/runs/reference_pipeline.py:100:    if not isinstance(listed_unparsed_slugs, tuple):
  src/auditmanager/runs/reference_pipeline.py:107:    saved = load_saved_reference_text(
  src/auditmanager/runs/reference_pipeline.py:115:    catalogue = load_verified_catalogue(
  src/auditmanager/runs/reference_pipeline.py:117:        max_catalogue_bytes=max_catalogue_bytes, jobs=job_repo,
  src/auditmanager/runs/reference_pipeline.py:134:        listed_unparsed_slugs=listed_unparsed_slugs,
  ```
- interpretation: invalid or huge supplied listings are currently processed
  only after bounded external reads; this does not show a served exploit.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none
- integration grant: direct integrator assignment on 2026-10-16; local source
  commit and handoff only.

## Allowed paths

- `src/auditmanager/runs/reference_pipeline.py`
- `tests/integration/runs/test_reference_pipeline.py`
- `docs/program/tasks/W57B-INT-REFERENCE-LIST-BOUNDS-01.md`
- `docs/program/W57B-INT-REFERENCE-LIST-BOUNDS-01.md`

## Forbidden hotspots

`contracts/**`, migrations, W56a evaluation/tools, W59 comparison, W56b
crops, W54 corpus, existing catalogue reader/validator internals, API/routes,
provider, findings/observation publication, root dependencies/locks,
composition root/global styles, `CURRENT_STATE.md`, remote refs/tags.

## Non-goals

No reviewed-slug source/policy, default candidate list, report truncation,
new fixed reference count, served stage/route, provider/effect, schema,
qualified corpus, real DB/S3 acceptance, publication or beta acceptance.

## Deliverables

One derived preflight bound in the chain, focused offline regression, paired
task/result record and local source commit/handoff.

## Required tests

- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_reference_pipeline.py tests/integration/norms/references/test_catalogue_query.py tests/integration/norms/references/test_reference_pipeline.py` — pass;
- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/architecture/test_alr05_boundaries.py tests/contract/program/test_wave_governance.py` — pass;
- compile owned Python, frozen-hash readback, `git diff --check`, exact
  four-path and `scripts/task_handoff.py` proof — pass;
- no Docker/provider/full gate under R-135.

## Integration contract

The caller supplies the existing explicit byte cap and reviewed tuple. As
canonical JSON contains each listed slug at least once, the tuple's count
and cumulative UTF-8 payload bytes cannot exceed the already supplied
catalogue byte cap. The chain validates that necessary bound and each slug's
basic NFC/nonempty/unique shape before any reader is called. Once the
verified snapshot facts arrive, the tuple cannot be larger than its document
count. The canonical catalogue validator still proves that each name is
actually present, unparsed and pinned; no local candidate list is trusted.

## Failure/idempotency/security cases

Invalid cap, non-tuple, empty/non-NFC/duplicate/surrogate slug or an
impossibly large listing refuse before any Blob read. Excess count versus
the verified snapshot refuses before PDF extraction. Stable valid inputs
produce the same report; no writes or new effect authority arise.

## Rollback / feature flag

Revert the four paths before activation. This is unserved read-only code,
so no flag or data rollback applies.

## Handoff

- changed files/checks/limitations: paired report;
- contracts: none;
- next: integrate only as an unserved preflight guard; future served callers
  still need an independently reviewed slug tuple and W57b seal.
