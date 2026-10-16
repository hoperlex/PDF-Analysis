# Task W57B-INT-XLSX-RUN-SOURCE-PREFLIGHT-01 — bind exportable run to XLSX page source

task_id: W57B-INT-XLSX-RUN-SOURCE-PREFLIGHT-01

## Outcome

One SELECT-only preflight reads an exact run's state and version, applies the
CSV export's frozen terminal policy, and obtains verified XLSX page labels for
that same version. A refused run performs no Blob read. The result is an
immutable source fact, not permission to download a workbook.

## Depends on

- `W57B-INT-XLSX-PACKAGE-PREP-01` — completed caller-authorized package seam.
- `W57B-INT-XLSX-SOURCE-LABELS-01` — completed version-bound page-label reader.

## Frozen inputs

- base commit and `origin/dev`: `445efc5db8556ef5a5e13fa680f9f49eb9783954`.
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`, §B3.5–B3.6.
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`.
- domain state-machine SHA-256 `f7a333c1f35bbe4ba57733e12898cd31497d87bcae4286bca467c79b6df0a673`.
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
  error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
  analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
  provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`.
- migration head `0022_findings_v2`; no head movement.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the exact base has a package and version-bound labels, but no
  run-state/version preflight or exposed XLSX operation.

### P-01 — exact base and additive paths

- captured_at: 2026-10-16
- command: `git rev-parse HEAD`
- captured_output:
  ```text
  445efc5db8556ef5a5e13fa680f9f49eb9783954
  ```
- interpretation: all new paths below are based on the published dev tree.

### P-02 — no preflight task or implementation at the base

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only HEAD src/auditmanager/exports/xlsx/preflight.py tests/integration/exports/test_xlsx_preflight.py docs/program/tasks/W57B-INT-XLSX-RUN-SOURCE-PREFLIGHT-01.md docs/program/W57B-INT-XLSX-RUN-SOURCE-PREFLIGHT-01.md`
- captured_output: empty (exit 0).
- interpretation: this task can be additive without sharing a writer hotspot.

### P-03 — existing entrypoints and sealed-route gap

- captured_at: 2026-10-16
- command: `rg -n '^def (assert_exportable|read_verified_page_labels|prepare_xlsx_package|run_header)' src/auditmanager/exports/policy.py src/auditmanager/exports/xlsx/source_labels.py src/auditmanager/exports/xlsx/package.py src/auditmanager/exports/query.py`
- captured_output:
  ```text
  src/auditmanager/exports/xlsx/package.py:86:def prepare_xlsx_package(
  src/auditmanager/exports/policy.py:75:def assert_exportable(state: str, *, run_id: str) -> None:
  src/auditmanager/exports/query.py:150:def run_header(session: Session, run_id: str) -> RunHeader | None:
  src/auditmanager/exports/xlsx/source_labels.py:115:def read_verified_page_labels(
  ```
- interpretation: the preflight can reuse export policy and source binding;
  the existing CSV header lacks `version_uid`, so one narrow SELECT is needed.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/exports/xlsx/preflight.py`
- `tests/integration/exports/test_xlsx_preflight.py`
- `docs/program/tasks/W57B-INT-XLSX-RUN-SOURCE-PREFLIGHT-01.md`
- `docs/program/W57B-INT-XLSX-RUN-SOURCE-PREFLIGHT-01.md`

## Forbidden hotspots

Existing XLSX query, projection, writer, package and source-label modules;
CSV query, policy, service and serializer; API security, routes and ports;
bootstrap/composition root; `contracts/**`, migrations, root dependencies and
locks, global styles, corpus, `CURRENT_STATE.md`, tags and remote refs.

## Non-goals

No role grant, `ExportAuthorization`, citation mapping, fabricated empty
citations, attribution, filename, HTTP route, live database/S3 call,
spreadsheet probe, full gate, release or beta acceptance.

## Deliverables

Additive typed preflight, focused fake-session and Blob-reader tests, task
report, and exact changed-path proof.

## Required tests

- `nice -n 19 ionice -c3 ../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/exports/test_xlsx_preflight.py tests/integration/exports/test_xlsx_source_labels.py tests/integration/exports/test_xlsx_package.py` — pass;
- compile the two new Python files; direct task governance and `git diff --check` — pass;
- compare changed paths to this allowlist — exact match;
- no `make gate` under R-135.

## Integration contract

`read_xlsx_run_source_preflight(session, run_id, read_blob=...)` receives the
caller's consistent read transaction and Blob reader. It parses the opaque run
ID, SELECTs only `run_id`, `state` and `version_uid` from `audit_run`, refuses
missing/mismatched rows, applies `exports.policy.assert_exportable`, and then
calls `read_verified_page_labels` with that exact version. It returns the run
ID, version ID, state and `VerifiedPageLabels` together. This result can supply
`ExportSources.page_labels` and `page_label_source_ref` only after the future
sealed caller verifies the same run, principal, citations and attribution.
It does not build an authorization decision.

## Failure/idempotency/security cases

Invalid run ID or Blob reader refuses before SQL; absent run gets CSV's
`not_found` shape. Non-publishing state gets CSV's
`state_transition_not_allowed` before any version/Blob source query. A wrong
run identity, malformed version ID, missing source, changed Blob or page without
a label refuses. No SQL write, transaction commit, or fallback. Repeated
immutable inputs return equal values.

## Rollback / feature flag

Remove the four additive files before runtime wiring. No data rollback or
feature flag is needed because no call site activates the preflight.

## Handoff

- changed files/checks/limits: see report;
- contracts: none;
- next: W57a and W57b seal owners add persisted normative citations and the
  `exportRunXlsx` contract/role, then the XLSX API owner verifies those sources,
  the guarded subject and state in one read and runs the independent workbook
  application probe.
