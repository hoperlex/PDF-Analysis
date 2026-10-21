# Task W56A-PROBE-TOOL-PREP-01 — bounded model identity probe tool

## Outcome

A one-call operator tool evaluates the selected and default model signals
without printing a gateway URL, credential or response text. Its offline tests
cover the previously failed identity/rate example. It makes no paid call and
does not claim either gateway has passed.

## Depends on

- `W56A-INT-SEAL-01` — complete on `origin/dev`;
- `W56A-INT-MATCHER-CORE-01` — complete at `6de331c1`.

## Frozen inputs

- base: `origin/dev=6de331c150f6573e320093bb4b2751f3bda016a2`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- `P02_LOCK.json` SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd` (read-only);
- migration head `0022_findings_v2`; `R-29`, `R-133`–`R-136` and
  `W56-PLAN.md` §A3.5; no configured gateway name is yet verified.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the locked primary rate and the current development base are
  available while the two-gateway identity check remains blocked.

### P-01 — base and lock bytes

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && sha256sum docs/program/P02_LOCK.json`
- captured_output:
  ```text
  6de331c150f6573e320093bb4b2751f3bda016a2
  6de331c150f6573e320093bb4b2751f3bda016a2
  2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd  docs/program/P02_LOCK.json
  ```
- interpretation: the development base and lock are unchanged; no live
  identity or gateway access follows from this output.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/W56A-PROBE-01.md` (failed, read-only)
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `tools/provider/__init__.py` (new);
- `tools/provider/identity_probe.py` (new);
- `tests/contract/provider/test_identity_probe.py` (new);
- this task and `docs/program/W56A-PROBE-TOOL-PREP-01.md` (new).

## Forbidden hotspots

- `P02_LOCK.json`, `contracts/**`, migration head, root dependency/lock
  files, composition root, global styles, runtime adapter/UI, deployment
  configuration, credentials, `CURRENT_STATE.md`, `VERSION`, refs and tags;
- historical `W56A-PROBE-01` and stopped `W56A-FREEZE-01` records.

## Non-goals

- No gateway call, spend, model pin, provider activation, recording, full
  local gate, manual acceptance, beta verdict or `origin/main` publication.

## Deliverables

- operator-run tool using the existing provider environment file in memory;
  a maximum of 16 output tokens and one request per invocation;
- selected-model identity and cost comparison at 20% relative or $0.00002
  absolute tolerance; default/stub must report a distinct concrete model;
- bounded response body read, no automatic retry, sanitized failure codes
  and metadata for ledger/report use;
- offline tests with matching, wrong-model, wrong-rate, absent/nonfinite
  usage, default echo, stub configuration and request-shape cases;
- report with changed paths, checks, limitation and next integration step.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m
  tools.provider.identity_probe --help` —
  returns the documented invocation without network;
- `/root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider
  tests/contract/provider/test_identity_probe.py` — green;
- `/root/projects/PDF-Analysis/.venv/bin/python -m compileall -q
  tools/provider tests/contract/provider`;
- `git diff --check` and exact changed-path proof. No full local gate.

## Integration contract

`W56A-MODEL-PIN-01` may use this tool only after a sanctioned authenticated
route to each distinct gateway and a fresh ledger projection. A tool PASS is
one call's evidence; it does not alone prove gateway distinction or the
four-call result. The operator must compare the two configured names and
pin only after both explicit/default pairs pass. The cheaper tier is not
verified. This task gives no `P02_LOCK.json` ownership.

## Failure/idempotency/security cases

- Invalid config, HTTP status, body, model, usage or rate returns a refusal;
  no fallback model and no retry. A timeout may have been charged.
- The tool accepts a host-owned file path but outputs no path, endpoint,
  token, prompt or answer. It does not write credentials or responses.
- Every invocation gets fresh request and idempotency IDs; repetitions are
  new spend and need a ledger entry before execution.

## Rollback / feature flag

Revert the new tool/test/report/task files. No runtime feature flag, schema
or data rollback is involved; the tool is never invoked by the application.

## Handoff

- changed files: the five Allowed paths;
- checks/results and limits: `docs/program/W56A-PROBE-TOOL-PREP-01.md`;
- integrator: publish to `origin/dev` only through a separate integration
  task, then refresh `W56A-MODEL-PIN-01`'s base and dependency.
