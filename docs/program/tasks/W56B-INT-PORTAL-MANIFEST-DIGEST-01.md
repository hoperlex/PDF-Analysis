# Task W56B-INT-PORTAL-MANIFEST-DIGEST-01 — bind OCR region to version source digests

task_id: W56B-INT-PORTAL-MANIFEST-DIGEST-01

## Outcome

The unserved saved OCR region reader refuses unless the recognised artifact's
`results_sha256` equals the exact Version manifest markdown SHA-256 and the
portal geometry artifact's `blocks_sha256` equals the exact Version manifest
structured-companion SHA-256. The reader does not invent a source identity or
read an unbounded third Blob.

## Depends on

- `W55B-INGEST-01` — completed immutable portal bundle manifest entries.
- `W56B-INT-RUN-RECOGNISED-REGION-READ-01` — completed fenced reader of
  canonical recognised and portal geometry artifacts.

## Frozen inputs

- base commit: `3a7c558a862d975f5305f6c54b15c6dfa5e9dca6`
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- domain identifiers SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- code-first plan SHA-256: `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- migration head: `0023_norm_citations`, SHA-256 `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: both deterministic producers record the SHA-256 of the exact
  original portal member bytes, while the completed W56b reader verifies the
  derived artifact Blobs but does not compare these inner digests to the
  immutable Version manifest.

### P-01 — producer digests and manifest roles at exact base

- captured_at: 2026-10-16
- command: `rg -n 'results_sha256=|blocks_sha256=|MANIFEST_ROLE_MARKDOWN|MANIFEST_ROLE_STRUCTURED_COMPANION' src/auditmanager/analysis/recognised/artifact.py src/auditmanager/analysis/geometry/portal.py src/auditmanager/documents/models.py`
- captured_output:
  ```text
  src/auditmanager/analysis/recognised/artifact.py:85:        results_sha256=hashlib.sha256(markdown).hexdigest(),
  src/auditmanager/analysis/geometry/portal.py:215:        blocks_sha256=hashlib.sha256(raw).hexdigest(), pages=pages, blocks=blocks
  src/auditmanager/documents/models.py:118:MANIFEST_ROLE_STRUCTURED_COMPANION: Final[str] = _declared_source_role(
  src/auditmanager/documents/models.py:121:MANIFEST_ROLE_MARKDOWN: Final[str] = _declared_source_role("source.markdown", "text/markdown")
  ```
- interpretation: the two existing inner digests can be checked against
  version-owned source entries without defining a new artifact or policy.

### P-02 — adopted W56b boundary

- captured_at: 2026-10-16
- command: `sed -n '140,143p' docs/program/dispatch/CODE-FIRST-TO-BETA.md`
- captured_output:
  ```text
- W56b требует ещё не утверждённых границ vision, region и бюджета. До
  решения можно реализовать нейтральные storage/evidence primitives и
  recorded harness, но не закреплять выдуманный модельный контракт.
- Выделенного `W56B-PLAN.md` и task-планов W58–W63 на `origin/dev` пока
  ```
- interpretation: immutable source-digest binding is neutral evidence
  custody, with no model, vision, citation or spend decision.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none
- task owner: this isolated W56b lane; no shared contract/hotspot owner.

## Allowed paths

- `src/auditmanager/runs/recognised_region_input.py`
- `tests/integration/runs/test_recognised_region_input.py`
- `docs/program/tasks/W56B-INT-PORTAL-MANIFEST-DIGEST-01.md`
- `docs/program/W56B-INT-PORTAL-MANIFEST-DIGEST-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, W54/W57/W58 paths, producer and pure
binder modules, `analysis/public.py`, `runs/repository.py`, jobs/storage/
documents adapters, stage registry, provider/rate adapters, composition
root, API/UI, root dependency/lock files, global styles, `CURRENT_STATE.md`,
remote refs and tags.

## Non-goals

No reread of original portal member Blobs, source repair, contract or
migration, stage registration, model/vision/citation/budget choice, provider
effect, persisted finding, served route, real DB/S3 acceptance or full gate.

## Deliverables

Fail-closed exact manifest-digest binding in the existing W56b reader,
focused fake-port tests and a paired report.

## Required tests

- focused saved OCR region and pure OCR candidate tests — pass;
- Python compilation, direct task governance, frozen SHA-256 readback,
  whitespace and exact four-path proof — pass;
- no Docker/PostgreSQL/S3/proxy/full gate.

## Integration contract

The reader requires exactly one markdown and one structured-companion entry
in the same Version manifest before Blob reads. Their media type, digest and
positive size must be valid. After reading the two bounded, saved derived
artifact Blobs, it compares their inner source digests to those Version
entries before yielding any OCR region candidate. The existing second
Attempt/Run/Version/StageResult fence remains in force. Matching digests
prove content identity with the immutable manifest, not availability of the
original member Blobs; a later real DB/S3 acceptance may read those too.

## Failure/idempotency/security cases

Missing, duplicate, malformed or wrong-media manifest entries refuse before
Blob reads. An otherwise valid saved artifact with an inner digest from a
different portal source refuses without a candidate. Changed manifest on
the second Version read refuses. Stable inputs return equal values with no
write, no path/key disclosure and no fallback.

## Rollback / feature flag

Revert this narrow reader/test change before wiring; no data rollback or
runtime flag is needed because this reader remains unserved.

## Handoff

- changed files/checks/limitations: paired report;
- contracts: none;
- next: W56b policy and persisted acceptance remain separate.
