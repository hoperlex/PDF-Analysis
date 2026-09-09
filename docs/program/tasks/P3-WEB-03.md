# Task P3-WEB-03 — append-only expert decision UI with visible history

> **Status: specified; not dispatchable.** Planned for P03; authored in parallel and
> integrated before `P3-WEB-02` is accepted.

## Outcome

An expert records accept or reject with a comment and appends a later comment; every event
is a new decision identity visible in a chronological ledger, and no earlier value is
overwritten or hidden.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until it is
accepted and integrated:

  - `P3-API-01` — generated client and transport seam accepted, with the decision append
    and list operations present and PD-01 semantics implemented server-side
  - owner decision `OD-12`, the decision author identity this ledger displays

## Frozen inputs

- API contract: the decision append and decision history operations at the `P3-API-01`
  snapshot
- domain contract: `ExpertDecision` as a non-state-machine append-only aggregate and the
  `finding_current_verdict` projection; owner decision PD-01 of 2026-09-01
- golden assertions `GJ-03-EO-09` and `GJ-03-EO-10`
- migration head: not consumed
- base commit: the accepted `P3-API-01` integration commit

## Allowed paths

- `web/src/widgets/decision-panel/**`, `web/src/widgets/decision-history/**`
- `web/src/features/record-verdict/**`, `web/src/features/append-comment/**`,
- `web/src/entities/expert-decision/**`
- `web/tests/unit/decisions/**`
- `docs/navigation/entries/p3-web-03.json`
- `docs/program/tasks/P3-WEB-03.md`

## Forbidden hotspots

- `web/src/app/**`, `web/src/_app/**`, the global stylesheet, `web/src/shared/**` and every
  web manifest
- the review, project and export slices
- `src/**`, `contracts/**`, `tests/e2e/**`

## Non-goals

- No edit or delete affordance for any decision, no bulk accept or reject, no
  keyboard-driven triage queue, no AI recommendation surface.
- No decision carryover across runs and no local persistence of an unsent verdict beyond
  the open form.

## Deliverables

- a decision panel showing the current projection value from the closed enumeration, with
  `pending` explicit and `needs_manual_review` rendered as a first-class value even though
  PC-01 has no producer for it
- two append actions — record verdict and append comment — each producing a new event, the
  comment action carrying the unchanged verdict so history stays complete. Revocation is
  deferred with `P2-FND-01`: the ledger stays append-only, so adding it later needs no
  schema or UI rework
- a chronological ledger listing decision identity, event kind, verdict, comment, author
  label and recorded timestamp, oldest first, with superseded values still readable
- provenance labels that distinguish expert events from any future recommendation event;
  the model is never shown as the author of a verdict

## Required tests

- Command: `npm --prefix web run test:unit -- decisions`
  Expected: exit `0`. The suite asserts that after a second decision the first remains
  rendered with its original value and identity; that the ledger grows rather than changes;
  and that the UI exposes no mutation path other than the two append actions.
- Command: `npm --prefix web run test:unit -- --grep "overwrite probe"` against a fixture
  ledger returned in reverse order with a duplicated decision identity
  Expected: non-zero; the history-integrity guard can fail.
- Command: `rg -n "PATCH|PUT|DELETE" web/src/features/record-verdict web/src/features/append-comment`
  Expected: no match.
- Command: `npm --prefix web run lint && npm --prefix web run build`
  Expected: exit `0`.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

The decision panel takes the finding and run identities plus a disabled flag and returns
no state to its parent; the review page never reads or caches a verdict independently. The
verdict shown in the finding list is the same projection value, refetched after any append.

## Failure/idempotency/security cases

- Every append carries a per-intent idempotency key; a retried submit returns the same
  decision identity and appends nothing.
- `idempotency_key_reuse` after an edited comment is an explicit conflict; the UI never
  quietly mints a fresh key.
- `conflict` or `not_found` on a finding renders explicitly and leaves the ledger untouched.
- The author label comes from the configured local reviewer identity, never from a free
  text field that the CSV would later present as authority.

## Rollback / feature flag

Revert the slice. Appended decisions remain in the server ledger and stay valid; no client
rollback deletes history.

## Estimate

Effort P50 0.75 person-day, P80 1.5 person-days. It narrowed when revocation was deferred
with `P2-FND-01`. Basis: two append actions and a chronological ledger. Calibration pending.

## Handoff

- changed files and containment proof, with commands and results
- the event kinds actually emitted and their payloads
- known limits: one local reviewer, no carryover
