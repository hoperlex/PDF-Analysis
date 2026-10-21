# Task W57A-INT-CITE-TXN-PREP-01 — unserved normative citation transaction writer

task_id: W57A-INT-CITE-TXN-PREP-01

## Outcome

One unserved SQL adapter writes a previously grounded normative finding, its
project evidence and its 1–5 canonical norm citations in the caller's single
PostgreSQL transaction. It refuses an obsolete Attempt, mismatched Run pin,
unconfirmed set custody, mismatched set bytes or citation outside the exact
selected set before any INSERT. Offline tests exercise these refusals.

## Depends on

- `W57A-SEAL-01A` — complete at `c71048f788e5d0bee39a312217dfd4c0912e5bc1`.
- `W57A-SEAL-01B` — complete at `c08182cab78bed70afbc777019d43de6c0bd2e18`.
- `W57A-INT-CITE-GROUNDING-CORE-01` — complete in `CFB-INT-DEV-PUBLISH-31`.
- `CFB-INT-DEV-PUBLISH-32` — complete at `5fa9473c54a5fb009ec8c0a6a45327a3a7f1dc15`.

## Frozen inputs

- base commit: `5fa9473c54a5fb009ec8c0a6a45327a3a7f1dc15`;
- API v1 SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- analysis stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- domain identifiers SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head: `0023_norm_citations`, SHA-256 `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- `W57-PLAN.md` §A3.4–A3.6; R-76, R-80 and R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: 0023 has an immutable citation row with a deferred count/quote check,
  but no CITE transaction writer; v3's pure grounding candidate lacks Run or
  Blob custody authority.

### P-01 — exact base and persisted citation certificate

- captured_at: 2026-10-16
- command: `git rev-parse HEAD; rg -n 'CREATE TABLE finding_observation_norm_citation|CREATE CONSTRAINT TRIGGER trg_finding_observation_partition|CREATE CONSTRAINT TRIGGER trg_norm_citation_partition' db/migrations/versions/20261016_0023_norm_citations.py`
- captured_output:
  ```text
  5fa9473c54a5fb009ec8c0a6a45327a3a7f1dc15
  355:        CREATE TABLE finding_observation_norm_citation (
  468:        CREATE CONSTRAINT TRIGGER trg_finding_observation_partition
  471:        CREATE CONSTRAINT TRIGGER trg_norm_citation_partition
  ```
- interpretation: 0023 certifies the relation on commit; the adapter must
  write the count and rows together and cannot call a returned value committed.

### P-02 — no existing CITE writer

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only HEAD src/auditmanager/findings`
- captured_output:
  ```text
  src/auditmanager/findings/README.md
  src/auditmanager/findings/__init__.py
  src/auditmanager/findings/artifacts.py
  src/auditmanager/findings/grounding.py
  src/auditmanager/findings/merge_publication_plan.py
  src/auditmanager/findings/public.py
  src/auditmanager/findings/publication.py
  src/auditmanager/findings/queries.py
  src/auditmanager/findings/recorded_saved_plan.py
  src/auditmanager/findings/terminal.py
  src/auditmanager/findings/v2_publication.py
  src/auditmanager/findings/v2_recorded.py
  ```
- interpretation: the existing publisher writes v1/v2 observations without
  0023 citation-count columns; this slice owns a new, unserved adapter only.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W57A-INT-CITE-TXN-PREP-01.md`
- `docs/program/W57A-INT-CITE-TXN-PREP-01.md`
- `src/auditmanager/findings/citation_publication.py`
- `tests/integration/findings/test_w57a_citation_publication_offline.py`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependencies and locks;
- `src/auditmanager/bootstrap/**`, `src/auditmanager/api/**`,
  `src/auditmanager/analysis/public.py`, v1/v2 publisher and routes;
- `CURRENT_STATE.md`, UI/global styles, stand services, remote refs and tags.

## Non-goals

No v3 runtime profile, source-Blob read port, active CITE stage, PDF gate
activation, failed-citation diagnostic writer, certified zero, report reader,
provider call, qualified corpus, served route or beta acceptance.

## Deliverables

One explicit transaction adapter and focused offline regression probes. The
caller maps the pure v3 candidate to this module's narrow DTO only after
separate grounding and obtains set bytes from the custody-checked Blob.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/findings/test_w57a_citation_publication_offline.py tests/integration/analysis/test_ar_v3_citation_grounding.py tests/integration/norms/test_citation_prep.py`;
- `python3 -m py_compile src/auditmanager/findings/citation_publication.py tests/integration/findings/test_w57a_citation_publication_offline.py`;
- `git diff --check`; direct task governance findings `[]`;
- no PostgreSQL, S3, Docker or full suite while the W55b gate holds the host.

## Integration contract

The adapter checks the current Run/Job/Attempt under row locks, the exact
execution token and completed model-call effect, verified pinned set and
confirmed available set Blob, a succeeded CITE StageResult from the same
Attempt's time window, and SHA-256/size of supplied set bytes. Selected prompt
labels, full rebinding text, raw citation spans and rebound state must match
those bytes. The caller owns its outer transaction: 0023 deferred checks run
at commit, and an error requires rollback. No direct external write occurs.

## Failure/idempotency/security cases

Missing or stale authority, corrupt/mismatched set bytes, foreign label,
wrong document, offset or rebound state refuse before writes. Repeat invocation
does not silently reuse a finding identity; the caller's final publication gate
must prevent duplicate Run/Attempt publication. Execution tokens are equality
values only and never emitted in a result or log.

## Rollback / feature flag

Unserved source only. Revert the bounded commit before activation if rejected;
no runtime feature flag is needed.

## Handoff

- changed files: the four exact allowed paths;
- commands/results: `W57A-INT-CITE-TXN-PREP-01.md`;
- known limits: real DB commit, custody read and v3 route remain to be proved;
- integration notes: cherry-pick after dev32 and keep unserved.
