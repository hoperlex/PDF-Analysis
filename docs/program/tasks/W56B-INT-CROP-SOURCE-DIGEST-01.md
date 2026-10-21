# Task W56B-INT-CROP-SOURCE-DIGEST-01 — bind saved IMAGE crops to their Version source

task_id: W56B-INT-CROP-SOURCE-DIGEST-01

## Outcome

The unserved saved IMAGE-crop reader returns a cohort only when its checked
portal `blocks_sha256` equals the SHA-256 of the one structured-companion
entry in the Run Version's immutable manifest. It fences that Version after
the Blob reads as well as the Run, StageResult and Attempt.

## Depends on

- `W55B-INGEST-01` — completed immutable portal bundle manifest entries.
- `W56B-INT-RUN-CROP-READ-01` — completed current-Attempt crop reader.
- `W56B-INT-PORTAL-MANIFEST-DIGEST-01` — completed source-digest binding
  pattern for the separate OCR reader.

## Frozen inputs

- base commit: `417123c729599cfa075d3461038c8dd15b86d4a3`
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

- premise: the saved crop reader verifies derived Blob bytes and their
  StageResult references, but accepts the portal's inner source digest without
  comparing it to the immutable Version manifest. The completed OCR reader
  already makes that comparison for the same portal source.

### P-01 — exact-base source lineage gap

- captured_at: 2026-10-16
- command: `rg -n 'def load_saved_image_crops|check_saved_crop_bytes|DocumentRepository|blocks_sha256|MANIFEST_ROLE_STRUCTURED_COMPANION' src/auditmanager/runs/geometry_crop_input.py src/auditmanager/analysis/geometry/crop_cohort.py src/auditmanager/runs/recognised_region_input.py src/auditmanager/documents/models.py`
- captured_output:
  ```text
  src/auditmanager/documents/models.py:36:    "MANIFEST_ROLE_STRUCTURED_COMPANION",
  src/auditmanager/documents/models.py:118:MANIFEST_ROLE_STRUCTURED_COMPANION: Final[str] = _declared_source_role(
  src/auditmanager/runs/recognised_region_input.py:38:    MANIFEST_ROLE_STRUCTURED_COMPANION,
  src/auditmanager/runs/recognised_region_input.py:39:    DocumentRepository,
  src/auditmanager/runs/recognised_region_input.py:134:        if entry.role == MANIFEST_ROLE_STRUCTURED_COMPANION
  src/auditmanager/runs/recognised_region_input.py:199:    documents: DocumentRepository | None = None,
  src/auditmanager/runs/recognised_region_input.py:204:    document_repo = documents or DocumentRepository()
  src/auditmanager/runs/recognised_region_input.py:228:    markdown_sha256, blocks_sha256 = _manifest_source_digests(version)
  src/auditmanager/runs/recognised_region_input.py:249:        or portal.get("blocks_sha256") != blocks_sha256
  src/auditmanager/analysis/geometry/crop_cohort.py:30:    "artifact_role", "artifact_version", "version_uid", "blocks_sha256", "pages", "blocks",
  src/auditmanager/analysis/geometry/crop_cohort.py:75:    blocks_sha256: str
  src/auditmanager/analysis/geometry/crop_cohort.py:254:    digest = portal["blocks_sha256"]
  src/auditmanager/runs/geometry_crop_input.py:25:    check_saved_crop_bytes,
  src/auditmanager/runs/geometry_crop_input.py:132:def load_saved_image_crops(
  src/auditmanager/runs/geometry_crop_input.py:157:        checked = check_saved_crop_bytes(
  ```
- interpretation: the listed code has no Version lookup in the crop reader;
  the adversarial fake-port regression must prove the observable gap.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none
- integration grant: direct integrator message on 2026-10-16 for the exact
  four paths below; local commit and handoff only.

## Allowed paths

- `src/auditmanager/runs/geometry_crop_input.py`
- `tests/integration/runs/test_geometry_crop_input.py`
- `docs/program/tasks/W56B-INT-CROP-SOURCE-DIGEST-01.md`
- `docs/program/W56B-INT-CROP-SOURCE-DIGEST-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, geometry producer and pure verifier,
OCR reader, `analysis/public.py`, `runs/repository.py`, jobs/storage/documents
adapters, stage registry, provider/rate adapters, composition root, API/UI,
root dependencies/locks, global styles, `CURRENT_STATE.md`, remote refs/tags.

## Non-goals

No original portal Blob reread, source repair, model/vision/citation/budget
choice, provider effect, served route, persisted finding, contract/migration,
real DB/S3 acceptance, corpus publication, deployment or full beta gate.

## Deliverables

One fail-closed Version-manifest check in the existing crop reader, focused
fake-port regressions and a paired handoff report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_geometry_crop_input.py tests/integration/analysis/geometry/test_saved_crop_custody.py tests/integration/runs/test_recognised_region_input.py` — pass;
- Python compilation, direct task governance, frozen SHA-256 readback,
  `git diff --check` and exact allowed-path proof — pass;
- no Docker/PostgreSQL/S3/proxy/full gate.

## Integration contract

The caller supplies the same transaction, Attempt authority, BlobStore and
explicit positive aggregate byte ceiling. Before any Blob read, the reader
fetches the exact Run Version and requires matching Version/project identity
and exactly one well-formed structured-companion manifest entry. After its
existing checked cohort is built, its source digest must equal that immutable
entry. The second fence repeats Attempt, Run, Version and StageResult checks.
The returned bytes remain a read-only candidate, not authority for an effect.

## Failure/idempotency/security cases

Missing, duplicate, wrong-role, wrong-media, invalid-SHA or nonpositive-size
source manifest entries refuse before Blob reads. A self-consistent changed
StageResult reference plus changed Blob with a foreign inner source digest
refuses. Changed Version at the second read refuses. Stable inputs return the
same value; errors reveal no Blob key or source payload.

## Rollback / feature flag

Revert this narrow unserved reader/test change before wiring. No runtime flag
or data rollback is needed.

## Handoff

- changed files/checks/limitations: paired report;
- contracts: none;
- next: integrate only as an unserved W56b custody improvement until the
  separate policy/effect owner authorizes activation.
