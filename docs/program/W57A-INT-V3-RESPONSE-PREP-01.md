# W57A-INT-V3-RESPONSE-PREP-01 — unserved v3 proposal input

**Base:** exact published development candidate
`f468d20eaf46dba82908615b04f20090541b21df`.
**Status:** isolated, pure source candidate. No PostgreSQL, S3, Docker,
provider call, remote publication or stand operation was run.

## Result

The new AR v3 proposal schema and parser accept the seven unchanged AR v2
categories plus the five 0023 normative categories. A normative proposal has
exactly 1–5 labelled `{label, quote}` claims and required/stated values; a
nonnormative proposal must omit all three normative properties. The parser
rejects unknown keys, duplicate JSON keys, invalid labels, empty/out-of-range
values and incomplete trailing normative proposals. It preserves a provider's
explicit truncation signal and salvages only complete initial elements.
The maximum proposed evidence quote is 2,000 characters, matching the existing
finding-evidence writer bound. These objects remain untrusted model proposals:
they have no Run, finding, citation state, raw offsets or expert verdict.

The legacy v2 schema test contained a stale equality check against the entire
now twelve-category API enum. Its test-only assertion now checks the original
seven-category prefix; the v2 parser, schema and registration files were not
changed. A separate v3 test checks totality against the sealed twelve-category
API enum.

## Reader block and dependency order

The served `getRunNormVerification` remains a typed 503. A safe reader cannot
yet distinguish a v3 Run from v1/v2: dev28 has no registered AR v3 profile ID,
and 0023 checks only the format of `audit_run.analysis_profile_id`. A verified
set, succeeded `norm_verification` StageResult and non-NULL partition alone do
not prove a Run used a registered v3 profile. The 0023 partition column is
nullable to preserve legacy rows; an empty citation SELECT cannot certify
zero. W57 §A3.5 requires v1/v2 → `not_found`, and v3 failed stages → a typed
partial report. Opening the route before profile identity and CITE publisher
exist would violate those rules.

The next serial dependencies are: registered, content-bound v3 profile and
stage plan after reviewed map/CAP inputs; CITE integration that grounds every
proposal and writes canonical/member partitions plus stage result in one
transaction; then a persisted reader checking profile, stage, Run snapshot,
verified set, each stored count and raw citation binding. No qualified corpus
or v3 runtime is claimed here.

## Evidence

- New v3 schema/parser tests plus affected v2 schema/parser tests:
  **40 passed** (`PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python
  -m pytest -q tests/integration/analysis/test_ar_v3_response_schema.py
  tests/integration/analysis/test_ar_v3_response_parser.py
  tests/integration/analysis/test_ar_v2_response_schema.py
  tests/integration/analysis/test_ar_v2_response_parser.py`).
- Before correcting the test-only pin, the same v2 pair returned **1 failed,
  17 passed**; the failure was `test_v2_response_enums_match_the_sealed_api`
  comparing seven v2 values to twelve API values.
- Python compilation, `git diff --check`, and direct task governance:
  **passed**, governance findings `[]`.
- `ruff` is not installed in the shared Python environment (`No module named
  ruff`); no lint result is claimed.
- All frozen API/stage/domain/migration SHA-256 values match the task file.
  PostgreSQL/S3 tests and a complete gate were intentionally not started while
  the W55b host gate held those resources.

## Changed paths and integration instruction

Exactly eight paths: task and this report; new
`src/auditmanager/analysis/profiles/ar_v3/{__init__,response_schema,response}.py`;
new `tests/integration/analysis/{test_ar_v3_response_schema,
test_ar_v3_response_parser}.py`; and the test-only correction in
`tests/integration/analysis/test_ar_v2_response_schema.py`.

Cherry-pick the clean source commit after dev28, and keep the v3 module
unserved until the later profile and CITE tasks own the corresponding
runtime/DB slots. No contract, migration, composition root, API router,
existing v1/v2 production file, root dependency, lockfile, UI, global style,
`CURRENT_STATE.md`, remote ref or tag was changed. Rollback is the bounded
source commit; it has no active behavior to switch off.
