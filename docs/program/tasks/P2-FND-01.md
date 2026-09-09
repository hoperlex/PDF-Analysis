# Task P2-FND-01 — evidence gate, finding publication and the append-only decision ledger

> **Status: specified; not dispatchable.** Planned for P02.

## Outcome

Only observations whose exact quotation exists at its declared anchor become published
findings, and an expert verdict is an append-only event whose current value is a
rebuildable projection.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until **all
three** are accepted and integrated. There is no synthetic-observation escape: the gate is
authored and tested against the real `analysis.text_observations` artifact, because
`P2-RUN-01` will depend on its terminal selection and a gate proved only against invented
payloads would prove nothing about the run it terminates:

  - `P2-DOM-01` — the P02 migration head and the append-only ledger constraints
  - `P2-ENG-01` — the text layer and block index the gate resolves anchors against
  - `P2-AI-01` — the real text-observations artifact the gate judges

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
- `docs/navigation/incidents/p2-fnd-01.jsonl` — created only if this task actually records an
  incident; never a shared append target
- `docs/program/tasks/P2-FND-01.md`
- `docs/navigation/entries/p2-fnd-01.json`

## Forbidden hotspots

- `db/migrations/**`, root locks, the composition root and the `Makefile`
- `src/auditmanager/{documents,ingest,storage,runs,exports,analysis,api}/**`, `contracts/**`,
  `fixtures/**`

## Non-goals

- No cross-run finding matching, decision carryover, knowledge projection or AI re-review.
- No CSV rendering or export: that use case belongs to `P2-EXP-01`, which reads this
  module's public queries. No UI.
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
- append-only decision events for the PC-01 journey — accept, reject and comment — each a
  new identity referencing the finding and the reviewed observation, with the current
  verdict rebuildable from the event stream alone. The ledger is append-only by
  construction, so the PD-01 revocation semantics remain implementable later without a
  schema change; PC-01 emits no revocation event and the UI offers none, because the journey
  under test is accept, reject and comment

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
  events and updates no row; that the projection equals the last valid event; that the
  projection rebuilt from the ledger equals the stored projection; that a decision on an
  unknown finding returns `not_found`; and that a direct UPDATE or DELETE on the ledger is
  refused by the database.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

`P2-RUN-01` calls this gate during `validating` and records the terminal it returns; the
executor never selects a terminal itself. This ordering is deliberate: the gate is built
before the runner so the runner is never authored against a stub that fakes `published`.
`P2-API-01` exposes findings, evidence and the current verdict, and `P2-EXP-01` reads them
for the CSV.

## Failure/idempotency/security cases

- `GJ-03-EO-09` and `GJ-03-EO-10`: every decision event creates a new identity with history
  preserved, the verdict enumeration is closed and `pending` is explicit. `GJ-03-FC-06`
  concerns revocation and is deferred with it.
- Model output never becomes a verdict; the gate is deterministic and takes no model input.
- Replaying the same decision command under one idempotency key appends exactly one event.

## Rollback / feature flag

Not applicable. The gate is unconditional and no flag lets an ungrounded item publish.

## Estimate

Effort P50 2.5 person-days, P80 4.5 person-days. Basis: one deterministic gate plus the append-only ledger and its projection. Calibration pending.

## Handoff

- navigation incident status, one of `recorded`, `none_observed` or
  `practice_not_exercised`; `recorded` requires the incident file above, and the other
  two assert that no incident occurred or that the practice was not followed
- the normalization rule and why it is the only one
- grounded versus diagnostic counts on the fixture, with the command that produced them
- the projection rebuild command and the decision event vocabulary
