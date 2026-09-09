# Task P3-WEB-04 — CSV export request, download and column verification

> **Status: specified; not dispatchable.** Planned for P03; authored in parallel and
> integrated before `P3-WEB-02` is accepted.

## Outcome

The reviewer downloads the UTF-8 CSV the server produces for the exact run, sees rows that
resolve back to the same project, version, run, finding and observation, and sees an
explicitly degraded label whenever the run is `partial`.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until it is
accepted and integrated:

  - `P3-API-01` — generated client and transport seam accepted, with
    `GET /runs/{run_id}/export.csv` present
  - `P2-EXP-01` — the server-side export use case that actually produces the CSV this task
    verifies

## Frozen inputs

- API contract: `GET /runs/{run_id}/export.csv` at the `P3-API-01` snapshot
- domain contract: the project, document, version, run, finding, observation and decision
  identifiers, and the `state_transition_not_allowed` error code, which is what a
  non-terminal export request returns. No export identifier is used, because PC-01 creates
  no export resource, and no partial-specific refusal exists under `OD-11`
- golden assertions `GJ-02-EO-08` and `GJ-02-EO-10`
- migration head: not consumed
- base commit: the accepted `P3-API-01` integration commit

## Allowed paths

- `web/src/widgets/export-panel/**`, `web/src/features/export-run/**`,
  `web/src/entities/export/**`
- `web/tests/unit/export/**`, `web/tests/csv/**`
- `web/scripts/verify-csv.mjs`
- `docs/navigation/entries/p3-web-04.json`
- `docs/navigation/incidents/p3-web-04.jsonl` — created only if this task actually records an
  incident; never a shared append target
- `docs/program/tasks/P3-WEB-04.md`

## Forbidden hotspots

- `web/src/app/**`, `web/src/_app/**`, the global stylesheet, `web/src/shared/**` and every
  web manifest
- the review, project and decision slices
- `src/**`, `contracts/**`, `tests/e2e/**`

## Non-goals

- No XLSX or PDF report, no column-selection UI, no filtered or partial-selection export,
  no scheduled or emailed export.
- No client-side CSV generation from cached data, and no export polling or export identity:
  the endpoint is synchronous and creates nothing.

## Deliverables

- an export panel that triggers the download and re-downloads it, with no polling state
- the consumer-side check of the frozen column contract owned by `P2-EXP-01`, in order:
  `project_uid`, `document_uid`, `version_uid`, `run_id`, `run_state`, `provider_mode`,
  `finding_uid`, `finding_observation_id`, `category`, `finding_text`,
  `recommendation_text`, `evidence_page`, `evidence_quote`, `current_verdict`,
  `latest_comment`, `latest_decision_id`, `decision_recorded_at`
- degraded rendering: a `partial` run's download is labelled degraded from the `run_state`
  column and the run read model; a non-terminal run offers no download and states why
- `web/scripts/verify-csv.mjs`, a deterministic checker asserting encoding, column order,
  row count against the fixture and identity resolution of every row

## Required tests

- Command: `npm --prefix web run test:unit -- export`
  Expected: exit `0`.
- Command: `npm --prefix web run csv:verify -- web/tests/csv/fixtures/pc01-published.csv`
  Expected: exit `0`; the header equals the frozen column list in order, the encoding is
  UTF-8 and every identifier matches its contract pattern. The fixture is a recorded
  response of the `P2-EXP-01` endpoint, not a hand-written file.
- Command: `npm --prefix web run csv:verify -- web/tests/csv/fixtures/pc01-missing-column.csv`
  Expected: non-zero, naming the missing column; the verification guard can fail.
- Command: `npm --prefix web run test:unit -- --grep "degraded"`
  Expected: exit `0`; a `partial` run never renders success wording and a `failed` run
  offers no download.
- Command: `npm --prefix web run lint && npm --prefix web run build`
  Expected: exit `0`.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

The export panel takes the run identity, run state and provider mode and owns all export
state. The column contract under `web/tests/contract` is the consumer-side authority the
P02 export implementation is tested against; renaming a column is a seam change requiring
both owners.

## Failure/idempotency/security cases

- Repeating the request returns the same bytes and creates nothing, so no idempotency key
  is needed for a read that has no side effect.
- A `partial` run downloads normally — its terminal declares `publishes_result: true` —
  and the UI shows its degraded state from the `run_state` column rather than presenting it
  as a complete result. A run whose terminal does not publish a result offers no download:
  the `failed` case, consistent with the run-detail rule above, and a non-terminal run.
  Both render `state_transition_not_allowed` with its reason; no case ever yields a silent
  empty CSV.
- No internal key, bucket, absolute filesystem path or credential appears in any column or
  in the download URL; the verifier rejects a row containing an `s3://` prefix, the
  configured endpoint host or an absolute path.
- The downloaded file name derives from opaque identities, never from the uploaded
  filename as identity.

## Rollback / feature flag

Revert the slice. Nothing was persisted server-side, so there is no export to retrieve or
orphan; the endpoint recomputes the CSV on the next request.

## Estimate

Effort P50 0.5 person-day, P80 1.0 person-day. It narrowed when server-side CSV generation
moved to its real owner, `P2-EXP-01`. Basis: a download trigger and a deterministic CSV verifier. Calibration pending.

## Handoff

- navigation incident status, one of `recorded`, `none_observed` or
  `practice_not_exercised`; `recorded` requires the incident file above, and the other
  two assert that no incident occurred or that the practice was not followed
- changed files and containment proof, with commands and results
- the verification result against the `P2-EXP-01` column contract, and any divergence
  reported to that owner rather than patched here
- known limits: one CSV form, no filtering
