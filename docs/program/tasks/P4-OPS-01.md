# Task P4-OPS-01 — build the PC-02 measurement tooling and the pre-session preflight

> **Status: specified; not dispatchable.** Planned for P04, after `PC-01` acceptance.

## Outcome

Accepted, reproducible tooling that can extract every provider call, run failure and
agent-navigation event — latency, token usage, measured or estimated cost, failure class
and live/recorded mode — plus a preflight that proves the telemetry it needs exists
**before** any expert session is booked, and a pre-session snapshot of the state the study
starts from. No runtime instrumentation is added.

This task deliberately does **not** produce the validation-period ledger. That ledger
covers the sessions, so it cannot exist until the sessions have run; `P4-INT-01` produces
it after `P4-BHV-01` by running this task's accepted tooling unmodified. Running the
extraction here would either report an empty period or, worse, be re-run later by a second
writer over the same path.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until each
is accepted and integrated:

  - `P3-INT-01` — `PC-01` accepted
  - `P1-NAV-01` — navigation layer accepted, the source of agent search/rework telemetry

## Frozen inputs

- ADR-0011 and Bible P-15: a published run records provider, model, params,
  request/response checksums, token usage, latency, status and measured or estimated cost
- Bible P-16: cost per run and cost per accepted finding are the reported units
- ADR-0019 rollout item 4: field validation measures agent search/rework failures before
  any richer graph or semantic search is considered
- the PC-01 persistence schema at the accepted `PC-01` commit, read only
- owner decision `OD-03` for the cost ceiling, the payer and the halt behavior

## Allowed paths

- `tools/validation/ledger_report.py`
- `artifacts/validation/PC-02/preflight/**` — the gap register and the pre-session
  snapshot. This is **not** the validation-period ledger: it records the state the study
  starts from, is written once before the first session, and is read-only thereafter
- `docs/navigation/incidents/p4-ops-01.jsonl` — created only if this task actually records an
  incident; never a shared append target
- `docs/program/tasks/P4-OPS-01.md`
- `docs/navigation/entries/p4-ops-01.json`

## Forbidden hotspots

- `src/**`, `db/migrations/**`, `contracts/**`, `infra/**`, `web/**`, `scripts/**`
- `tools/validation/corpus_check.py`, owned by `P4-QA-01`
- `artifacts/validation/PC-02/ledger/**` — the final validation-period ledger, written
  only by `P4-INT-01` after the sessions, so the period has exactly one writer
- `artifacts/validation/PC-02/sessions/**`, owned by `P4-BHV-01`
- `docs/navigation/INDEX.md`, root locks, `Makefile`, migration head

## Non-goals

- No new runtime instrumentation, migration, column or event. This is the constraint
  that enforces "P04 changes no foundational architecture".
- No cost optimization, provider change or added retry to observe fewer failures.

## Deliverables

- `ledger_report.py`, read-only over PostgreSQL and the PC-01 run records, emitting
  per-call latency, tokens, cost and provider status; per-run duration, stage outcomes,
  terminal state and live/recorded mode; and a failure ledger grouped by eight
  **observation classes** — provider unavailable, provider timeout, malformed provider
  response, ungrounded item rejected, unsupported input, checksum failure, application or
  process crash, and other. These are reporting buckets defined by this task, not codes from
  the domain error catalog, and the tool records the catalog code separately in whatever
  output it is writing — the preflight snapshot here, the validation-period ledger when
  `P4-INT-01` runs it
- the **complete tool interface** every later consumer invokes, since all of them are
  forbidden from editing it: `--self-check`; `--dry-run`; `--snapshot <dir>` writing the
  pre-session baseline; `--validate-sessions <dir>` asserting a session dataset is complete
  before anything aggregates it, used by `P4-BHV-01` per session and by `P4-INT-01` before
  the report; and `--period <sessions> --baseline <preflight> --out <ledger>`, which extracts
  the closed validation period, differences the baseline and writes the validation-period
  ledger `P4-INT-01` owns. Every mode is gated below: an interface a consumer needs but this
  task never exercised would force reopening an accepted task on the PC-02 critical path
- cost roll-up **capability** in the tooling: per run, per published finding and per
  accepted finding, plus cumulative spend against the `OD-03` ceiling. It is exercised here
  against the pre-session state and against the recorded-response fixture run; the numbers
  that enter PC-02 are produced by `P4-INT-01` from the same tool after the sessions
- the **pre-session snapshot** under `artifacts/validation/PC-02/preflight/`: the PC-01
  commit the study will run against, the tool version, the run and call counts already
  present before the study, and the spend already incurred. It is the baseline the final
  ledger is differenced against, so a later reader can tell study activity from
  pre-existing activity. It is never presented as validation-period data
- navigation ledger read from the per-task `docs/navigation/incidents/<lowercase-task-id>.jsonl`
  files whose schema and directory contract `P1-NAV-01` creates, cross-read against the
  navigation incident status in the task handoffs. **Scope: the P02 and P03 tasks that are
  already complete when this task runs** — twenty-one of them, every task accepted up to
  and including `P3-INT-01`. It aggregates no P04 task, because `P4-BHV-01` and `P4-INT-01`
  have not run and this task cannot report on its own wave; `P4-INT-01` aggregates P04 and
  `P5-INT-01` aggregates P05. The rule for reporting is explicit, because an absent file is
  ambiguous: **zero** is reported only when every in-scope task returned `recorded` or
  `none_observed`; if any in-scope task returned `practice_not_exercised`, or gave no
  status at all, the metric is **absent** and the report names the tasks that did not
  report. An empty directory is never itself evidence that navigation was frictionless
- a gap register naming every `PROTOTYPE_PROFILE.md` §9 metric as `persisted`,
  `derivable` or `absent`, with what persisting it would take — raised as a P02 defect
  for owner decision and not fixed here

## Required tests

- Command: `.venv/bin/python tools/validation/ledger_report.py --self-check`
  Expected: exit `0`; reproduces the known call count, latency-field presence and mode of
  the PC-01 recorded-response fixture run.
- Command: `.venv/bin/python tools/validation/ledger_report.py --dry-run`
  Expected: exit `0` and zero write operations, asserted against the statement log rather
  than against the absence of an error.
- Command: `git diff --check`
  Expected: exit `0`.
- Command: `.venv/bin/python tools/validation/ledger_report.py --snapshot artifacts/validation/PC-02/preflight/`
  Expected: exit `0`; writes the pre-session snapshot under `preflight/` and nothing under
  `ledger/`, asserted against the write log rather than against the absence of an error.
- Command: `.venv/bin/python tools/validation/ledger_report.py --validate-sessions <fixture>`
  Expected: exit `0` on a complete fixture dataset and non-zero on one whose session record
  is missing a mandatory field, so the mode is proven able to fail.
- Command: `.venv/bin/python tools/validation/ledger_report.py --period <fixture-sessions>
  --baseline <fixture-preflight> --out <tmpdir>`
  Expected: exit `0`; writes a ledger under `<tmpdir>`, reads the baseline without modifying
  it, and separates period activity from baseline activity. Exercised here against fixtures
  so `P4-INT-01` invokes an interface this task has already proven.
- Manual check: every §9 metric appears in the gap register with a classification.
  Expected: no metric unclassified.
- Manual check: the navigation aggregation covers exactly the completed P02/P03 tasks and
  names any that did not report.
  Expected: no P04 or P05 task aggregated here.
- Dispatch precondition: if per-call latency or token/cost is `absent`, this task halts
  with `BLOCKED` and its gap register. It does not instrument the runtime, and
  `P4-BHV-01` does not start until the owner rules under `OD-23`.

## Integration contract

`P4-BHV-01` receives **accepted tooling** and the accepted preflight: the gap register
tells it which metrics exist, and it runs the tool session by session to keep a
moderator-side failure ledger against which the retry question is checked rather than asked
cold. Those per-session outputs live under `artifacts/validation/PC-02/sessions/**`, which
`P4-BHV-01` owns.

`P4-INT-01` receives the same tooling, unmodified and already accepted, plus the
pre-session snapshot to difference against. It is the sole writer of
`artifacts/validation/PC-02/ledger/**`: after the last session it runs the tool over the
completed validation period, commits that ledger, and only then builds the PC-02 report
from it. This task never writes that path, so the validation-period ledger has exactly one
writer and cannot be produced twice from two different trees.

## Failure/idempotency/security cases

- The extraction is read-only over the runtime; a second run over the same tree and
  database state produces the same output.
- The pre-session snapshot is written once and is read-only afterwards. It is labelled as
  pre-session everywhere it appears, so it can never be mistaken for, or merged into, the
  validation-period ledger `P4-INT-01` produces.
- Spend crossing the `OD-03` ceiling halts sessions; the tooling surfaces the halt and the
  validation-period ledger `P4-INT-01` later produces records it.
- No secret, connection string, bucket name or object key enters
  `artifacts/validation/PC-02/**`; blobs are referenced by `blob_id`.
- Absent telemetry is reported as absent; an estimated cost is labelled estimated and is
  never presented as measured.

## Rollback / feature flag

Not applicable: read-only reporting on new paths only.

## Estimate

Effort P50 1.5 person-days, P80 3.0 person-days. Unchanged: the same read-only extraction
over an existing schema plus a documentary gap register and a snapshot written by the tool
it already builds. Moving the validation-period extraction to `P4-INT-01` reassigns the
run, not the build, and `P4-INT-01`'s own basis already covers aggregation. Excludes
remediation if the dispatch precondition fires. Calibration pending.

## Handoff

- navigation incident status, one of `recorded`, `none_observed` or
  `practice_not_exercised`; `recorded` requires the incident file above, and the other
  two assert that no incident occurred or that the practice was not followed
- changed files, the tool version, the `--self-check` result and the pre-session snapshot
  path and contents
- gap register and any `BLOCKED` precondition
- the exact list of completed P02/P03 tasks aggregated for the navigation metric, and the
  metric's value or its `absent` status with the non-reporting tasks named
- explicit confirmation that no file was written under `artifacts/validation/PC-02/ledger/`
- observed spend against the `OD-03` ceiling
