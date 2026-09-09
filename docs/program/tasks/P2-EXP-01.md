# Task P2-EXP-01 — synchronous server-side CSV export

> **Status: specified; not dispatchable.** Planned for P02. It exists because the CSV a
> reviewer downloads must be produced by something the plan actually owns.

## Outcome

One synchronous, deterministic export use case reads canonical data from PostgreSQL and
returns a UTF-8 CSV whose every row resolves to the exact project, document version, run,
finding and observation, with no export aggregate, no polling and no export identity.

## Depends on

- none complete at plan time

Planned predecessors and dispatch conditions — this task is not dispatchable until each is
accepted and integrated:

  - `P2-FND-01` — findings, observations, evidence and the current-verdict projection
  - `P2-RUN-01` — the run row whose state and provider mode the CSV records
  - owner decision `OD-11` for the CSV byte details — encoding and byte-order mark,
    delimiter, line ending and quoting — and for whether a `partial` run may be exported

## Frozen inputs

- domain contract: the project, document, version, run, finding, observation and decision
  identifiers, and the `partial_result_not_publishable` error code
- API contract: none; `P2-API-01` exposes this use case
- migration head: the P02 head, read only; this task creates no table
- base commit: the accepted `P2-RUN-01` integration commit

## Allowed paths

- `src/auditmanager/exports/**`
- `tests/integration/exports/**`
- `docs/navigation/incidents/p2-exp-01.jsonl` — created only if this task actually records an
  incident; never a shared append target
- `docs/program/tasks/P2-EXP-01.md` status/handoff
- `docs/navigation/entries/p2-exp-01.json`

## Forbidden hotspots

- `db/migrations/**` — this task adds no table and no column
- root locks, the composition root, the `Makefile`, `contracts/**`, `fixtures/**`
- `src/auditmanager/{documents,ingest,storage,analysis,findings,decisions,runs,api}/**`
- `web/**` and every P03 path

## Non-goals

- **No export aggregate, table, row or identity; no `export_id` and no `exported_at`.**
  The export is computed on request from canonical data and is not itself canonical data.
- No polling, no asynchronous job, no separate export-idempotency command: a synchronous
  read needs none, because it creates nothing.
- No XLSX, PDF, filtered or column-selected export, and no scheduled or emailed delivery.

## Deliverables

- an export use case taking a run identity and returning a UTF-8 CSV byte stream plus its
  content type, reading only through the owning modules' public queries
- the frozen column contract, in order: `project_uid`, `document_uid`, `version_uid`,
  `run_id`, `run_state`, `provider_mode`, `finding_uid`, `finding_observation_id`,
  `category`, `finding_text`, `recommendation_text`, `evidence_page`, `evidence_quote`,
  `current_verdict`, `latest_comment`, `latest_decision_id`, `decision_recorded_at`
- deterministic row order fixed by a documented sort key, so two exports of an unchanged
  run are byte-identical
- the `OD-11` terminal policy, implemented literally: a `partial` run **is** exported, with
  its degraded state carried explicitly in the `run_state` column rather than as a silent
  empty file; a non-terminal run is **refused explicitly** with a typed error; and a repeat
  request returns byte-identical bytes and creates nothing

## Required tests

- Command: `make foundation`
  Expected: exit `0`.
- Command: `.venv/bin/pytest tests/integration/exports`
  Expected: exit `0`. The suite asserts that every row of a published run resolves to the
  exact project, version, run, finding and observation; that the header equals the frozen
  column list in order; that the bytes are UTF-8 under the `OD-11` encoding decision; that
  two exports of an unchanged run are byte-identical; that a `partial` run exports with its
  degraded state visible; that a non-terminal run is refused explicitly; and that no cell
  contains a bucket name, an object key, an absolute path or a credential.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

`P2-API-01` exposes `GET /runs/{run_id}/export.csv` and calls this use case; it adds no
export logic of its own. `P3-WEB-04` only downloads the response and verifies it. Because
nothing is persisted, there is no export state for any consumer to reconcile.

## Failure/idempotency/security cases

- Repeating the request returns the same bytes and creates nothing, which is what makes a
  separate idempotency command unnecessary.
- A run that is not terminal is refused with a typed error rather than exported empty.
- No internal object key, bucket, filesystem path or credential reaches a cell or a header.

## Rollback / feature flag

Not applicable: a pure read. Revert the module; no data changes.

## Estimate

Effort P50 0.75 person-day, P80 1.5 person-days. Basis: one synchronous read and its deterministic serializer. Calibration pending.

## Handoff

- navigation incident status, one of `recorded`, `none_observed` or
  `practice_not_exercised`; `recorded` requires the incident file above, and the other
  two assert that no incident occurred or that the practice was not followed
- the exact column list produced and the documented sort key
- the encoding decision actually implemented under `OD-11`
- the refusal behavior for non-terminal and `partial` runs
