# Task P4-OPS-01 — assemble the PC-02 measurement ledger from persisted telemetry

> **Status: specified; not dispatchable.** Planned for P04, after `PC-01` acceptance.

## Outcome

Every provider call, run failure and agent-navigation event of the validation period is
extractable into one reproducible ledger — latency, token usage, measured or estimated
cost, failure class and live/recorded mode — without adding any runtime instrumentation.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until each
is accepted and integrated:

  - `P3-INT-01` — `PC-01` accepted
  - `P1-NAV-01` — navigation layer accepted, the source of agent search/rework telemetry

## Frozen inputs

- ADR-0011 and Bible P-15: a published run records provider, model, params,
  request/response checksums, token usage, latency, status and measured or estimated cost
- Bible P-16: cost per run and cost per accepted finding are the reported units
- ADR-0019 rollout item 4: field validation measures agent search/rework failures before
  any richer graph or semantic search is considered
- the PC-01 persistence schema at the accepted `PC-01` commit, read only
- owner decision `OD-03` for the cost ceiling, the payer and the halt behavior

## Allowed paths

- `tools/validation/ledger_report.py`
- `artifacts/validation/PC-02/ledger/**`
- `docs/program/tasks/P4-OPS-01.md`
- `docs/navigation/entries/p4-ops-01.json`

## Forbidden hotspots

- `src/**`, `db/migrations/**`, `contracts/**`, `infra/**`, `web/**`, `scripts/**`
- `tools/validation/corpus_check.py`, owned by `P4-QA-01`
- `docs/navigation/INDEX.md`, root locks, `Makefile`, migration head

## Non-goals

- No new runtime instrumentation, migration, column or event. This is the constraint
  that enforces "P04 changes no foundational architecture".
- No cost optimization, provider change or added retry to observe fewer failures.

## Deliverables

- `ledger_report.py`, read-only over PostgreSQL and the PC-01 run records, emitting
  per-call latency, tokens, cost and provider status; per-run duration, stage outcomes,
  terminal state and live/recorded mode; and a failure ledger grouped by the classes
  `provider_unavailable`, `provider_timeout`, `provider_malformed`,
  `ungrounded_item_rejected`, `unsupported_input`, `checksum`, `app_or_process_crash`
  and `other`
- cost roll-up: per run, per published finding and per accepted finding, plus cumulative
  spend against the `OD-03` ceiling
- navigation ledger read from the per-task `docs/navigation/incidents/<task-id>.jsonl`
  files whose schema and directory contract `P1-NAV-01` creates: per P02/P03 task, the
  agent search and rework incidents those tasks actually recorded, plus orphan and
  stale-entry counts from the navigation validator. If no task wrote a file, the metric is
  reported **absent**, never as zero — an empty set means the practice was not followed,
  not that navigation was frictionless
- a gap register naming every `PROTOTYPE_PROFILE.md` §9 metric as `persisted`,
  `derivable` or `absent`, with what persisting it would take — raised as a P02 defect
  for owner decision and not fixed here

## Required tests

- Command: `.venv/bin/python tools/validation/ledger_report.py --self-check`
  Expected: exit `0`; reproduces the known call count, latency-field presence and mode of
  the PC-01 recorded-response fixture run.
- Command: `.venv/bin/python tools/validation/ledger_report.py --dry-run`
  Expected: exit `0` and zero write operations, asserted against the statement log rather
  than against the absence of an error.
- Command: `git diff --check`
  Expected: exit `0`.
- Manual check: every §9 metric appears in the gap register with a classification.
  Expected: no metric unclassified.
- Dispatch precondition: if per-call latency or token/cost is `absent`, this task halts
  with `BLOCKED` and its gap register. It does not instrument the runtime, and
  `P4-BHV-01` does not start until the owner rules under `OD-23`.

## Integration contract

`P4-BHV-01` receives a moderator-side failure ledger against which the retry question is
checked rather than asked cold. `P4-INT-01` receives the latency, cost and failure
evidence for the PC-02 observations and for `P5-ARC-01`.

## Failure/idempotency/security cases

- The report is read-only; a second run over the same tree and database state produces
  the same ledger.
- Spend crossing the `OD-03` ceiling halts sessions, and the ledger records the halt.
- No secret, connection string, bucket name or object key enters
  `artifacts/validation/PC-02/**`; blobs are referenced by `blob_id`.
- Absent telemetry is reported as absent; an estimated cost is labelled estimated and is
  never presented as measured.

## Rollback / feature flag

Not applicable: read-only reporting on new paths only.

## Estimate

Effort P50 1.5 person-days, P80 3.0 person-days. Basis: one read-only extraction over an
existing schema plus a documentary gap register; excludes remediation if the dispatch
precondition fires. Calibration pending.

## Handoff

- changed files, ledger outputs and the `--self-check` result
- gap register and any `BLOCKED` precondition
- observed spend against the `OD-03` ceiling
