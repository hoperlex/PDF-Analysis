# Task W56B-INT-RECOGNISED-REGION-DB-S3-ACCEPT-01 — persisted OCR region read

task_id: W56B-INT-RECOGNISED-REGION-DB-S3-ACCEPT-01

## Outcome

An addressable integration test proves that the unserved W56b OCR-region
reader obtains a marked quote and region from a real PostgreSQL Run, current
Attempt, immutable Version manifest, two saved successful StageResults and
two verified S3 Blobs. The same persisted input refuses a noncurrent Attempt.
No provider call or finding publication is performed by this test.

## Depends on

- `W55B-RECOGNISED-01` — completed portal markdown preparation.
- `W55B-GEOMETRY-01` — completed portal geometry stage and saved Blobs.
- `W56B-INT-RUN-RECOGNISED-REGION-READ-01` — completed unserved two-fence reader.
- `W56B-INT-PORTAL-MANIFEST-DIGEST-01` — completed source digest binding.

## Frozen inputs

- base commit: `ef802c112cd2b61de5ee9aa701739b04eb2d7f36`
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- domain identifiers SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- code-first plan SHA-256: `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- migration head: `0023_norm_citations`, SHA-256 `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- fixture: `fixtures/synthetic/ar/bundles/image_only_with_block.zip` SHA-256
  `6f4568de2ccf34e03cec4078f2bd8ed21144fc68027f9c30cce9b72b01bdad3b`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the current fake-port W56b reader suite does not prove persisted
  Run/Attempt/StageResult and real S3 custody. The committed textless bundle
  and recorded executor provide a testable boundary after geometry binding,
  before the next deterministic stage or model dispatch.

### P-01 — textless source and deterministic stages

- captured_at: 2026-10-16
- command: `sed -n '248,259p' tests/integration/qa_w55b/test_p2_run_to_portal_blocks.py`
- captured_output:
  ```text
      version = _uploaded(expert, committed("image_only_with_block.zip"), "textless page")
      stored = rows(
          engine,
          "SELECT textless_pages, recognised_character_count FROM document_version WHERE version_uid = :v",
          v=version,
      )
      textless, recognised_count = list(stored[0][0]), stored[0][1]
      assert textless == [1, 2]
      run = _ran(expert, version)
      stages = {s["stage_id"]: s["status"] for s in run["stages"]}
      assert stages.get("source_preparation") == "succeeded", run
      assert stages.get("page_geometry_extraction") == "succeeded", run
  ```
- interpretation: this existing synthetic source has a real two-stage OCR
  path and a Version with two textless pages.

### P-02 — saved reader boundary

- captured_at: 2026-10-16
- command: `rg -n 'def load_saved_recognised_region|require_current|stage_results|open_stream' src/auditmanager/runs/recognised_region_input.py`
- captured_output:
  ```text
  155:        chunks = store.open_stream(
  188:def load_saved_recognised_region(
  206:    job_repo.require_current(session, authority)
  230:    rows = run_repo.stage_results(session, authority.run_id)
  267:    job_repo.require_current(session, authority)
  272:    later_rows = run_repo.stage_results(session, authority.run_id)
  ```
- interpretation: the test must enter while the production Run is still
  `running` and the Attempt current; a terminal-run-only test cannot reach
  this service.

### P-03 — code-first boundary

- captured_at: 2026-10-16
- command: `sed -n '140,142p' docs/program/dispatch/CODE-FIRST-TO-BETA.md`
- captured_output:
  ```text
  - W56b требует ещё не утверждённых границ vision, region и бюджета. До
    решения можно реализовать нейтральные storage/evidence primitives и
    recorded harness, но не закреплять выдуманный модельный контракт.
  ```
- interpretation: this is test-only evidence custody with no provider,
  citation, vision or cost policy.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none
- integration grant: direct integrator message on 2026-10-16 for exactly
  three paths; local commit and handoff only, no push.

## Allowed paths

- `tests/integration/runs/test_recognised_region_db_s3_accept.py`
- `docs/program/tasks/W56B-INT-RECOGNISED-REGION-DB-S3-ACCEPT-01.md`
- `docs/program/W56B-INT-RECOGNISED-REGION-DB-S3-ACCEPT-01.md`

## Forbidden hotspots

Runtime modules, `contracts/**`, `db/migrations/**`, W54/W57/W58 paths,
other tests or fixtures, jobs/storage/documents adapters, provider/rate
adapters, composition root, API/UI, root dependency/lock files, global
styles, `CURRENT_STATE.md`, remote refs and tags.

## Non-goals

No served OCR route, model/proxy use, citation assertion, finding write,
product policy, deployment, corpus publication, full gate or beta verdict.
This test does not measure real S3 outage/retry or cross-process lease expiry.

## Deliverables

One real-service test using the existing PostgreSQL/S3 fixtures, this task
and a paired result report. No runtime change.

## Required tests

- Before the gate slot is released: direct task governance, Python
  compilation, frozen SHA-256 readback and whitespace only.
- After the integrator releases the slot: one targeted real PostgreSQL/S3
  test file; fail rather than skip if service prerequisites are absent.
- Exact three-path and clean-tree technical handoff. No full gate.

## Integration contract

Seed the committed scanned bundle through public Blob and Document ports.
Start a recorded AR v2 Run through its public command. The production
executor writes and binds source preparation and geometry under its real
current Attempt. A test-local publication-store spy at the next stage's
entry point, after its `stage_started` commit, calls the unserved reader
before model dispatch and checks the OCR quote,
textless page, region, source digests and saved references, then stops the
executor with a test sentinel. The same persisted Run must refuse a forged
Attempt. The harness rolls back database rows; content-addressed synthetic
S3 objects may remain. No provider effect, result publication or terminal
Run is asserted.

## Failure/idempotency/security cases

The test fails if the services, migrations or bucket are unavailable, or
if stages do not save the expected refs. A forged Attempt token refuses
without yielding a candidate. The test uses committed synthetic bytes and
records no secret, Blob key or payload in its report.

## Rollback / feature flag

Remove the test and paired documents. No runtime flag, data migration or
production rollback is needed.

## Handoff

- changed files: exactly the three allowed paths;
- contracts: none;
- checks and limitations: paired report;
- forbidden hotspots untouched.
