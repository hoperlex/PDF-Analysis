# Task P3-API-01 — generated OpenAPI client and typed transport seam

> **Status: specified; not dispatchable.** Planned for P03. Sole writer of the generated
> API client and of all HTTP in `web/`.

## Outcome

A deterministically regenerated TypeScript client plus one transport wrapper is the only
place in `web/` where HTTP exists; it injects idempotency keys, decodes the domain error
envelope into the closed `error_code` union, and consumer contract tests fail when the
P02 API drifts from the PC-01 seam.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until each
is accepted and integrated:

  - `P3-WEB-00` — frontend toolchain and seam document accepted
  - `P2-API-01` — the OpenAPI document frozen at a named commit containing the PC-01 seam

## Frozen inputs

- API contract: the P02 OpenAPI document at its accepted freeze commit, snapshotted here
  and never edited
- domain contract: `error-codes.json`, `identifiers.json`, `state-machines.json`, read only
- analysis/comparison/event contract: none consumed
- migration head: not consumed
- base commit: the accepted `P3-WEB-00` integration commit

## Allowed paths

- `web/src/shared/api/**`
- `web/openapi/**`
- `web/scripts/generate-api-client.mjs`
- `web/tests/contract/**`
- `docs/navigation/entries/p3-api-01.json`
- `docs/navigation/incidents/p3-api-01.jsonl` — created only if this task actually records an
  incident; never a shared append target
- `docs/program/tasks/P3-API-01.md`

## Forbidden hotspots

- `contracts/**` and the upstream OpenAPI source; `src/**`
- `web/package.json` and every web manifest or config, owned by `P3-WEB-00`
- every `_pages`, `widgets`, `features` and `entities` slice

## Non-goals

- No hand-edit of generated output and no bespoke domain types layered over the schema.
- No retry or backoff policy beyond the frozen polling helper, and no caching layer
  beyond the query client supplied by `_app`.

## Deliverables

- generator config plus generated client under `web/src/shared/api/generated/**` carrying
  a do-not-edit header
- a transport wrapper reading the base URL from config, setting `Idempotency-Key` on every
  write, passing the correlation id through, and decoding the envelope into exactly
  `validation_failed`, `not_found`, `conflict`, `state_transition_not_allowed`,
  `idempotency_key_reuse`, `idempotency_key_in_progress`, `idempotency_key_stale`,
  `dependency_unavailable`, `analysis_failed`, `partial_result_not_publishable` and
  `internal_error`
- a run-state union taken from the contract, with `published` and never `succeeded`, and a
  verdict union `pending`, `accepted`, `rejected`, `needs_manual_review`
- one polling helper honoring the frozen interval and backoff and stopping on any terminal
  state
- consumer contract tests pinning the seam operations, the finding and observation field
  sets, the decision-ledger field set and the CSV column list

## Required tests

- Command: `npm --prefix web run api:generate && git diff --exit-code web/src/shared/api/generated`
  Expected: exit `0`; regeneration is deterministic.
- Command: `npm --prefix web run test:contract`
  Expected: exit `0`; every seam operation and required field present.
- Command: `npm --prefix web run test:contract -- --grep "drift probe"` against a mutated
  snapshot in which `published` is renamed
  Expected: non-zero, naming the missing state; proves the contract guard can fail.
- Command: `rg -n "fetch\(|axios|XMLHttpRequest" web/src --glob '!web/src/shared/api/**'`
  Expected: no match.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

Slices import only the public API of `shared/api`; they never see a raw response, never
construct a URL and never hand-write an error string. A P02 API change that breaks the
seam fails `test:contract` before any UI task is blamed.

## Failure/idempotency/security cases

- An unknown `error_code` surfaces as an explicit unrecognized-error state, never as
  success and never as a generic retry.
- `idempotency_key_in_progress` resolves by polling the same key; the client never mints a
  new one.
- `idempotency_key_reuse` is a terminal user-visible conflict, never a silent resubmit.
- Object keys, bucket names and the S3 endpoint never appear in typed models; a contract
  test rejects any schema property matching `bucket`, `object_key` or `s3_key`.

## Rollback / feature flag

Revert the client commit and regenerate from the previous snapshot. No server state is
involved.

## Estimate

Effort P50 0.5 person-day, P80 1.5 person-days. Basis: generation config plus one transport wrapper and consumer contract tests. Calibration pending.

## Handoff

- navigation incident status, one of `recorded`, `none_observed` or
  `practice_not_exercised`; `recorded` requires the incident file above, and the other
  two assert that no incident occurred or that the practice was not followed
- generated client version, the snapshot commit of the P02 OpenAPI and the generator pin
- commands/results including the drift probe
- seam operations actually exercised versus declared
