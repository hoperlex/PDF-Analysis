# Task P2-FND-01 — evidence gate, finding publication and the append-only decision ledger

> **Status: specified; not dispatchable.** Planned for P02.

## Outcome

Only observations whose exact quotation exists at its declared anchor become published
findings, and an expert verdict is an append-only event whose current value is a
rebuildable projection.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until the
first two are accepted and integrated; its gate tests run against synthetic observation
payloads until the third is:

  - `P2-DOM-01` — the P02 migration head and the append-only ledger constraints
  - `P2-ENG-01` — the text layer and block index the gate resolves anchors against
  - `P2-AI-01` — supplies the real text-observations artifact

## Frozen inputs

- domain contract: the expert decision as a non-state-machine append-only aggregate, the
  current-verdict projection and its four values, and owner decision PD-01
- ADR-0010 on finding versus observation identity, and ADR-0012
- the audit run transition from `validating` to a terminal state, and the
  `partial_result_not_publishable` error code
- migration head: the P02 head, read only
- base commit: the accepted `P2-ENG-01` integration commit

## Allowed paths

- `src/auditmanager/findings/**`, `src/auditmanager/decisions/**`
- `tests/integration/findings/**`, `tests/integration/decisions/**`
- `docs/program/tasks/P2-FND-01.md`
- `docs/navigation/entries/p2-fnd-01.json`

## Forbidden hotspots

- `db/migrations/**`, root locks, the composition root and the `Makefile`
- `src/auditmanager/{documents,ingest,storage,jobs,analysis,api}/**`, `contracts/**`,
  `fixtures/**`

## Non-goals

- No cross-run finding matching, decision carryover, knowledge projection or AI re-review.
- No CSV rendering or export, which belong to P03, and no UI.
- No repair of an ungrounded item and no model-assisted verdict.

## Deliverables

- a grounding gate executed in the run's `validating` phase requiring, for every evidence
  item, that the exact quotation is present at its declared page and character span in the
  text layer, and inside the declared block's span in the block index, compared exactly
  after one declared and tested normalization and nothing else
- rejection of an ungrounded item from the finding list, retained only as diagnostic
  evidence attached to the run and never counted as a finding
- publication giving each surviving observation a fresh finding identity and an immutable
  observation identity bound to the run, with category, finding text, recommendation,
  evidence rows and stage, profile, prompt and model-call provenance including the mode
- terminal selection: all required stages `succeeded` and the gate passed gives `published`;
  a `partial` text analysis gives a `partial` run with the missing set recorded; any
  required stage `failed` gives a `failed` run with nothing published
- append-only decision events for accept, reject, comment and revoke, each a new identity
  referencing the finding and the reviewed observation, with the current verdict rebuildable
  from the event stream alone and revocation moving it to `pending` without restoring a
  superseded verdict

## Required tests

- Command: `make foundation`
  Expected: exit `0`.
- Command: `.venv/bin/pytest tests/integration/findings`
  Expected: exit `0`. The suite asserts that a recorded run over the baseline fixture
  publishes findings for both seeded contradictions and the placeholder with pages matching
  the expected-issues manifest; that a control statement is not flagged; that an observation
  whose quotation is absent, and one whose quotation exists on a different page, are both
  rejected from the finding list, retained as diagnostics, and reduce the published count;
  that a `partial` text analysis terminates the run `partial` and never `published`; and that
  an operation requiring a complete run over a `partial` run returns
  `partial_result_not_publishable`.
- Command: `.venv/bin/pytest tests/integration/decisions`
  Expected: exit `0`. The suite asserts that accept, then comment, then reject appends three
  events and updates no row; that the projection equals the last valid event; that revoke
  moves the projection to `pending` without restoring the earlier verdict; that the
  projection rebuilt from the ledger equals the stored projection; that a decision on an
  unknown finding returns `not_found`; and that a direct UPDATE or DELETE on the ledger is
  refused by the database.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

`P2-JOB-01` calls the gate during `validating` and receives the terminal selection and the
published set; it never selects the terminal itself. The API exposes findings, evidence and
the current verdict; P03 renders them and owns the CSV.

## Failure/idempotency/security cases

- `GJ-03-EO-09`, `GJ-03-EO-10` and `GJ-03-FC-06`: correction and revocation each create a
  new decision identity with history preserved, the verdict enumeration is closed, and
  `pending` is explicit.
- Model output never becomes a verdict; the gate is deterministic and takes no model input.
- Replaying the same decision command under one idempotency key appends exactly one event.

## Rollback / feature flag

Not applicable. The gate is unconditional and no flag lets an ungrounded item publish.

## Estimate

P50 2.5 days, P80 4.5 days.

## Handoff

- the normalization rule and why it is the only one
- grounded versus diagnostic counts on the fixture, with the command that produced them
- the projection rebuild command and the decision event vocabulary
