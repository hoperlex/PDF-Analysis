# Task P4-BHV-01 — run the moderated expert validation sessions

> **Status: specified; not dispatchable.** Planned for P04, after the corpus and ledger
> tasks are accepted.

## Outcome

A complete, schema-valid labelled dataset in which every published finding across the
corpus carries an expert label, a moderator-verified evidence check and a time
measurement, produced by at least three experts, at least two of them independent of the
build team.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until each
is accepted and integrated:

  - `P4-QA-01` — corpus and protocol accepted
  - `P4-OPS-01` — ledger accepted, or its `BLOCKED` precondition explicitly cleared by
    the owner
  - owner decisions `OD-01` cost ceiling, `OD-02` expert recruitment and time budget,
    `OD-04` reviewer independence

## Frozen inputs

- the `P4-QA-01` corpus manifest, protocol and recording schema at their accepted commit;
  the protocol is not edited mid-study and a change voids the sessions run before it
- the PC-01 build at the accepted `PC-01` commit, frozen for the whole study: no prompt,
  threshold or UI change between the first and last session
- `P4-OPS-01` ledger tooling
- migration head: not touched

## Allowed paths

- `artifacts/validation/PC-02/sessions/**`
- `docs/program/tasks/P4-BHV-01.md`

## Forbidden hotspots

- `src/**`, `web/**`, `fixtures/**`, `contracts/**`, `scripts/**`, `tools/**`, `db/**`
- `docs/program/validation/**` and `artifacts/validation/PC-02/ledger/**`
- the PC-01 build itself: a mid-study fix is a new study

## Non-goals

- No fix of any defect observed during a session; defects are logged and left.
- No aggregation, interpretation or threshold judgment — that is `P4-INT-01`.
- No claim about real production documents.

## Deliverables

- one schema-valid session record per expert per document holding: the per-finding label
  `useful`, `incorrect` or `unclear` as a mandatory single choice with its follow-up; the
  moderator's independent check that the quotation is verbatim at the declared anchor;
  seconds on finding; and navigation-friction incidents
- per-document record: run identity, document version, live/recorded mode, run duration,
  stage outcomes, published and ungrounded-rejected counts, terminal state, false
  negatives against the seeded manifest, expert total review time and a "would you use
  this on this document" answer
- post-session forced choices: top-three missing capability; audit depth versus document
  comparison with reasoning; and the retry/fencing/remote question answered against the
  moderator's failure ledger rather than from memory
- at least two documents independently reviewed by two experts
- a defect log of observed, unfixed defects, and the disposal attestation if `OD-03`
  applied
- expert accept/reject/comment decisions recorded in the product, exercising the
  append-only path

## Required tests

- Command: `.venv/bin/python tools/validation/ledger_report.py --validate-sessions
  artifacts/validation/PC-02/sessions`
  Expected: exit `0`; every record validates and no published finding lacks a label.
- Command: `git diff --check`
  Expected: exit `0`.
- Manual check: the build commit recorded in every session record is identical.
  Expected: exactly one commit across all sessions.
- Manual check: consent and no-production-data reminder delivered, and every document's
  provenance is `synthetic` or an `OD-03`-approved `anonymized`. Expected: pass.

## Integration contract

`P4-INT-01` receives a dataset in which the objective evidence-location metric, checked
by the moderator, is separable from the subjective usefulness label, so a low usefulness
rate cannot be mistaken for an evidence defect.

## Failure/idempotency/security cases

- A session interrupted mid-document is recorded as partial and its document re-run with
  another expert or dropped; a partial record is never completed from memory.
- Spend crossing the `OD-01` ceiling halts sessions immediately; completed sessions stay
  valid.
- A build change mid-study voids every earlier session; the study restarts from the new
  commit.
- Quotations from anonymized documents are stored as page, offset and hash, never as
  text; anonymized bytes are destroyed at study end with a two-person attestation.
- Expert identity is pseudonymous in committed evidence and the mapping is not committed.

## Rollback / feature flag

Not applicable: evidence capture only. Evidence is never edited after the fact;
corrections are appended as erratum entries.

## Estimate

P50 5–8 days elapsed, P80 12–15 days. Basis: scheduling latency of three to five external
experts, not effort — roughly two to three 90-minute blocks per expert plus moderator
write-up. This is the most sensitive row in the plan and is governed by `OD-02`; with
named experts and committed slots the P80 falls to 8–9 days. Calibration pending.

## Handoff

- session counts by expert and document, and the coverage matrix
- defect log
- spend against the ceiling
- documents that could not be reviewed and why
