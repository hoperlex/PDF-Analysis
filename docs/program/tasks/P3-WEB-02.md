# Task P3-WEB-02 — finding list and page-beside-quotation evidence review

> **Status: specified; not dispatchable.** Planned for P03; authored in parallel and
> accepted only after the decision and export slices are integrated.

## Outcome

Clicking a finding opens the declared PDF page beside the exact extracted quotation for
every observation of that finding, with no S3 object key, bucket name or presigned URL
anywhere in the browser.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until each
is accepted and integrated, and it may not be accepted until the last two are:

  - `P3-API-01` — generated client and transport seam accepted
  - `P3-WEB-01` — project, upload and run-progress slice accepted
  - `P3-WEB-03` and `P3-WEB-04` — the decision and export widgets this page mounts;
    authoring proceeds against their props frozen in `web/docs/PC01_UI_SEAM.md`

## Frozen inputs

- API contract: the version-content and run-findings operations at the `P3-API-01` snapshot
- domain contract: observation immutability, and the categories `internal_contradiction`
  and `explicit_placeholder`
- golden assertion `GJ-03-EO-01`
- migration head: not consumed
- base commit: the accepted `P3-WEB-01` integration commit, plus the widget props frozen in
  `web/docs/PC01_UI_SEAM.md`

## Allowed paths

- `web/src/_pages/review/**`
- `web/src/widgets/finding-list/**`, `web/src/widgets/evidence-viewer/**`
- `web/src/features/open-evidence/**`
- `web/src/entities/finding/**`, `web/src/entities/finding-observation/**`
- `web/tests/unit/review/**`
- `docs/navigation/entries/p3-web-02.json`
- `docs/program/tasks/P3-WEB-02.md`

## Forbidden hotspots

- `web/src/app/**`, `web/src/_app/**`, the global stylesheet, `web/src/shared/**` and every
  web manifest
- the decision and export slices it mounts
- `src/**`, `contracts/**`, `tests/e2e/**`

## Non-goals

- No bounding-box overlay, highlight rectangle, text-layer selection sync or thumbnail
  strip.
- No cross-run finding matching and no client-side re-extraction or normalization of the
  quotation.

## Deliverables

- a review page composing the finding list, the evidence viewer and the two externally
  owned panels through their frozen props
- a finding list grouped by category, rendering the current verdict from the closed
  enumeration
- an evidence viewer as a bounded client island rendering exactly the declared page of the
  version, fed by the streamed content route, with page navigation limited to the
  observation's declared pages
- a quotation panel rendering the server-supplied string unmodified beside its observation
  identity, page number and anchor
- every observation of a multi-observation finding rendered; a finding with zero
  observations is impossible under the P02 evidence gate and renders as an explicit
  data-integrity error rather than an empty pane
- diagnostic and ungrounded items are never rendered as findings

## Required tests

- Command: `npm --prefix web run test:unit -- review`
  Expected: exit `0`. The suite asserts that the rendered quotation is byte-identical to
  the API string, that the viewer requests only the version-content route, and that the
  declared page index is the page opened.
- Command: `npm --prefix web run test:unit -- --grep "key leakage"` against a fixture
  response carrying an `s3://` value in an unexpected field
  Expected: non-zero; the leakage guard can fail.
- Command: `rg -n "presign|X-Amz|s3\.|minio" web/src/_pages/review web/src/widgets web/src/features web/src/entities`
  Expected: no match.
- Command: `npm --prefix web run lint && npm --prefix web run build`
  Expected: exit `0`.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

The review page is the single mount point for the decision and export panels; it passes
the finding, run and version identities plus the current observation, and owns no decision
or export state.

## Failure/idempotency/security cases

- A content-route failure renders an explicit viewer error with retry; it never renders a
  blank page as if the PDF had no content.
- `not_found` on a version renders an explicit missing-evidence state, never a silent empty
  list.
- The viewer never receives, stores or logs an internal key; page bytes are fetched per
  view and not persisted client-side.

## Rollback / feature flag

Revert the slice; the review route falls back to its placeholder. Decisions already
recorded server-side are unaffected.

## Estimate

P50 2 days, P80 4 days.

## Handoff

- changed files and containment proof, with commands and results
- the PDF rendering library and pin actually used, and the measured first-page render time
  on the acceptance fixture with the command that measured it
- known limits: no overlay, page-level navigation only
