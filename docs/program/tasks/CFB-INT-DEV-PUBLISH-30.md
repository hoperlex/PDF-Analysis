# Task CFB-INT-DEV-PUBLISH-30 — integrate unserved AR v3 proposal input

task_id: CFB-INT-DEV-PUBLISH-30

## Outcome

A clean fast-forward `origin/dev` candidate carries a pure strict AR v3
response schema/parser. Normative model proposals require 1–5 labelled
quotes and both values; seven legacy nonnormative categories forbid them.
No proposal becomes a verified citation or expert decision.

## Depends on

- `CFB-INT-DEV-PUBLISH-29` — complete at
  `55977fd93414e70ef0deb210f2b7e0511abc7375`;
- `W57A-INT-V3-RESPONSE-PREP-01` — complete at
  `14219bd29ab61cc22a6bf7f563396d9e3d63ef28`.

## Frozen inputs

- integration base and directly read `origin/dev`:
  `55977fd93414e70ef0deb210f2b7e0511abc7375`;
- directly read `origin/main`: `23fd729dbb06c642be0588017f6b195305e2e53e`;
- source parent `f468d20eaf46dba82908615b04f20090541b21df`,
  source commit `14219bd29ab61cc22a6bf7f563396d9e3d63ef28`, exact
  eight-path diff, 40 focused v3/v2 tests;
- API 48 paths / 55 operations / 131 schemas, SHA-256
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
  stage SHA-256
  `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
  domain IDs SHA-256
  `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`,
  error catalogue SHA-256
  `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`,
  migration head `0023_norm_citations`;
- R-135 defers complete beta gate; W55b release gate is separate.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `src/auditmanager/analysis/profiles/ar_v3/response_schema.py`
- enumerator_owner: `W57A-INT-V3-RESPONSE-PREP-01`
- totality_query: `PYTHONPATH=src .venv/bin/python -m pytest -q tests/integration/analysis/test_ar_v3_response_schema.py`

The completed source task owns the exact twelve-category enum and the
test-only v2 pin correction. This integration cherry-picks its bytes
without editing those paths.

## Captured premise evidence

- premise: source is pure and unserved; no registered AR v3 profile ID or
  CITE writer exists, so the typed refusing reader remains the safe route.

### P-01 — source path scope

- captured_at: 2026-10-16
- command: `git show --format= --name-only 14219bd29ab61cc22a6bf7f563396d9e3d63ef28`
- captured_output:
  ```text
  docs/program/W57A-INT-V3-RESPONSE-PREP-01.md
  docs/program/tasks/W57A-INT-V3-RESPONSE-PREP-01.md
  src/auditmanager/analysis/profiles/ar_v3/__init__.py
  src/auditmanager/analysis/profiles/ar_v3/response.py
  src/auditmanager/analysis/profiles/ar_v3/response_schema.py
  tests/integration/analysis/test_ar_v2_response_schema.py
  tests/integration/analysis/test_ar_v3_response_parser.py
  tests/integration/analysis/test_ar_v3_response_schema.py
  ```
- interpretation: accept exact source patch only; the v2 production parser
  and registered runtime are unchanged.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W57A-INT-V3-RESPONSE-PREP-01.md`;
- `docs/program/tasks/W57A-INT-V3-RESPONSE-PREP-01.md`;
- `src/auditmanager/analysis/profiles/ar_v3/__init__.py`;
- `src/auditmanager/analysis/profiles/ar_v3/response.py`;
- `src/auditmanager/analysis/profiles/ar_v3/response_schema.py`;
- `tests/integration/analysis/test_ar_v2_response_schema.py`;
- `tests/integration/analysis/test_ar_v3_response_parser.py`;
- `tests/integration/analysis/test_ar_v3_response_schema.py`;
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-30.md`;
- `docs/program/CFB-INT-DEV-PUBLISH-30.md`;
- `docs/program/CURRENT_STATE.md`;
- ignored `.venv` link to the existing Python environment for focused tests.

## Forbidden hotspots

All other paths, especially `contracts/**`, migrations, root dependencies
and locks, composition root, existing v1/v2 production profile/executor,
API routes, global styles, production DB/S3, `origin/main`, tags and
deployment workflow.

## Non-goals

No registered v3 profile identity, reviewed map or CAP material,
qualified retrieval set, grounded citation, CITE writer, served report
reader, provider call, corpus publication, W55b deployment or beta
acceptance.

## Deliverables

Exact eight-path source payload, bounded state update, this task/report
and direct published-dev SHA readback.

## Required tests

- source/integrated v3/v2 schema/parser suites and programme governance;
- direct task governance, exact patch/path and frozen contract checks,
  whitespace, clean-tree, fresh remote fast-forward and readback;
- complete W56–W63 beta gate deferred by R-135; W55b gate separate.

## Integration contract

Cherry-pick exact source commit after dev29. Parser output remains
untrusted model proposals; future profile/CITE owner must register a
content-bound v3 identity, ground all citations and write canonical/member
partitions with stage result atomically. The served reader remains typed
503 until it can distinguish v3 from v1/v2 and certify a zero partition.
A moved ref or changed source stops publication; never force-push.

## Failure/idempotency/security cases

Malformed/unknown/duplicate/null/out-of-range properties refuse;
truncation salvages only complete initial elements. Pure parsing has no
external effect, and no model text becomes a canonical expert verdict.

## Rollback / feature flag

No served behavior is wired. Revert the eight source paths and these three
integration documents through a reviewed forward commit if abandoned.

## Handoff

- source files: exact eight W57a task paths;
- integration files: this task, report and bounded state update;
- contracts: none; v3 profile/CITE publisher/reader remain open;
- forbidden hotspots and `origin/main` remain untouched.
