# Task P3-WEB-01 — project, upload and run-progress slice

> **Status: specified; not dispatchable.** Planned for P03.

## Outcome

A local expert creates a project, uploads one AR PDF, starts one run and watches polled
progress that names the contract run state and the persisted provider mode, with
unsupported input, failure and partial outcomes shown explicitly and never as success.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until it is
accepted and integrated:

  - `P3-API-01` — generated client and transport seam accepted

## Frozen inputs

- API contract: the project, upload, version, run-start and run-status operations at the
  `P3-API-01` snapshot
- domain contract: the `audit_run` machine transitions and terminals; the 25 MiB and
  30-page input envelope
- analysis/comparison/event contract: stage identity only, for the per-stage rows
- migration head: not consumed
- base commit: the accepted `P3-API-01` integration commit, plus `web/docs/PC01_UI_SEAM.md`

## Allowed paths

- `web/src/_pages/projects/**`, `web/src/_pages/run/**`
- `web/src/widgets/project-list/**`, `web/src/widgets/upload-panel/**`,
  `web/src/widgets/run-progress/**`
- `web/src/features/create-project/**`, `web/src/features/upload-document/**`,
  `web/src/features/start-run/**`
- `web/src/entities/project/**`, `web/src/entities/document-version/**`,
  `web/src/entities/audit-run/**`
- `web/tests/unit/projects/**`, `web/tests/unit/run/**`
- `docs/navigation/entries/p3-web-01.json`
- `docs/program/tasks/P3-WEB-01.md`

## Forbidden hotspots

- `web/src/app/**`, `web/src/_app/**`, the global stylesheet, `web/src/shared/**` and every
  web manifest
- the review, decision and export slices
- `src/**`, `contracts/**`, `tests/e2e/**`

## Non-goals

- No cancel action, re-run carryover, multi-file or ZIP upload, drag-and-drop resumable
  upload, WebSocket or SSE progress.
- No client-side PDF validation beyond a size and extension pre-check.

## Deliverables

- project create and list with a client-generated idempotency key stable across retries of
  one user intent
- single-PDF upload rendering explicit unsupported-input results for encrypted,
  image-only, oversize, over-page-count and non-PDF rejections, each showing the server
  reason rather than a generic failure
- an immutable version panel showing the version identity, page count, size and SHA-256,
  and no bucket or object key
- run start plus a polling detail view rendering the literal contract states `created`,
  `queued`, `running`, `validating`, `published`, `partial`, `failed` and `cancelled`,
  with per-stage rows for `source_preparation`, `page_geometry_extraction`,
  `document_context_build` and `text_analysis`
- a provider-mode badge of `live`, `recorded` or `unknown`, read from run provenance and
  carried into the review entry point
- `partial` renders the recorded missing or degraded set; `failed` renders the
  `error_code`; a reconciled interrupted run renders its reason and never keeps animating

## Required tests

- Command: `npm --prefix web run test:unit -- projects run`
  Expected: exit `0`. The suite asserts that an unsupported-input response renders the
  server reason and starts no run; that a `partial` run never renders success wording;
  that a run lacking provider provenance renders `unknown` rather than `live`; and that
  polling stops on every terminal state.
- Command: `npm --prefix web run test:unit -- --grep "vocabulary"` against a fixture whose
  state is `succeeded`
  Expected: non-zero; an unknown state is rejected rather than rendered.
- Command: `npm --prefix web run lint && npm --prefix web run build`
  Expected: exit `0`.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

The review slice may rely on the route parameters, on the run entity's public selector for
state and provider mode, and on the guarantee that no other slice polls the run endpoint.

## Failure/idempotency/security cases

- Repeating create, upload or start under the same idempotency key renders the existing
  aggregate and never a second project, version or run.
- `idempotency_key_in_progress` shows an in-flight state and keeps polling the same key.
- `dependency_unavailable` at start is explicit, with no offer to fall back to recorded
  mode.
- No filename, path or object key is used as identity; display ordinals are labels only.

## Rollback / feature flag

Revert the slice; the routes fall back to the `P3-WEB-00` placeholders. No server state
changes.

## Estimate

P50 1.5 days, P80 3 days.

## Handoff

- changed files and containment proof, with commands and results
- the exact states and error codes rendered, and any contract state left unrendered
- known limits: no cancel and no re-run
