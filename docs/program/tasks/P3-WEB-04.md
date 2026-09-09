# Task P3-WEB-04 — CSV export request, download and column verification

> **Status: specified; not dispatchable.** Planned for P03; authored in parallel and
> integrated before `P3-WEB-02` is accepted.

## Outcome

The reviewer requests one export for the exact run, downloads a UTF-8 CSV whose rows
resolve back to the same project, version, run, finding, observation and current verdict,
and sees an explicitly degraded label whenever the run is `partial` or a declared member
is missing.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until it is
accepted and integrated:

  - `P3-API-01` — generated client and transport seam accepted, with the export
    operations present

## Frozen inputs

- API contract: the export request and export content operations at the `P3-API-01`
  snapshot
- domain contract: the project, document, version, run, finding, observation, decision and
  export identifiers, and the `partial_result_not_publishable` error code
- golden assertions `GJ-02-EO-08` and `GJ-02-EO-10`
- migration head: not consumed
- base commit: the accepted `P3-API-01` integration commit

## Allowed paths

- `web/src/widgets/export-panel/**`, `web/src/features/export-run/**`,
  `web/src/entities/export/**`
- `web/tests/unit/export/**`, `web/tests/csv/**`
- `web/scripts/verify-csv.mjs`
- `docs/navigation/entries/p3-web-04.json`
- `docs/program/tasks/P3-WEB-04.md`

## Forbidden hotspots

- `web/src/app/**`, `web/src/_app/**`, the global stylesheet, `web/src/shared/**` and every
  web manifest
- the review, project and decision slices
- `src/**`, `contracts/**`, `tests/e2e/**`

## Non-goals

- No XLSX or PDF report, no column-selection UI, no filtered or partial-selection export,
  no scheduled or emailed export.
- No client-side CSV generation from cached data.

## Deliverables

- an export panel that requests, polls, downloads and re-downloads the same export
- the frozen column contract, in order: project, document, version and run identities,
  `run_state`, `provider_mode`, finding and observation identities, `category`,
  `finding_text`, `recommendation_text`, `evidence_page`, `evidence_quote`,
  `current_verdict`, `latest_comment`, the latest decision identity,
  `decision_recorded_at`, the export identity and `exported_at`
- degraded rendering: a `partial` run's export is labelled degraded and carries the
  omission reason; a non-terminal, `failed` or `cancelled` run offers no download and
  states why
- `web/scripts/verify-csv.mjs`, a deterministic checker asserting encoding, column order,
  row count against the fixture and identity resolution of every row

## Required tests

- Command: `npm --prefix web run test:unit -- export`
  Expected: exit `0`.
- Command: `npm --prefix web run csv:verify -- web/tests/csv/fixtures/pc01-published.csv`
  Expected: exit `0`; the header equals the frozen column list, the encoding is UTF-8 and
  every identifier matches its contract pattern.
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

- Repeating the export request under one idempotency key returns the same export and
  creates no second one.
- `partial_result_not_publishable` renders as an explicit refusal with its reason, never
  as an empty CSV.
- No internal key, bucket, absolute filesystem path or credential appears in any column or
  in the download URL; the verifier rejects a row containing an `s3://` prefix, the
  configured endpoint host or an absolute path.
- The downloaded file name derives from opaque identities, never from the uploaded
  filename as identity.

## Rollback / feature flag

Revert the slice; exports already produced remain retrievable server-side by their export
identity.

## Estimate

P50 0.75 day, P80 1.5 days.

## Handoff

- changed files and containment proof, with commands and results
- the exact column list produced and any column the P02 export omitted
- known limits: one CSV form, no filtering
