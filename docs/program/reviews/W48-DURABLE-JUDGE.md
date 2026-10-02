# W48-DURABLE-JUDGE — adversarial review of durable effects

## 1. Subject and verdict

- **Subject:** `00100e8129ab0d144d66f7bac4899c069879b3cb`.
- **Implementation base:** `e3fedd0fdf2f2eda18e55c22867201f5663717a6`.
- **Frozen surface:** API 17 paths / 20 operations / 61 schemas; error catalog 22;
  migration head `0014_durable_analysis_effects`.
- **Audit rows under judgment:** `A-01` and `A-02`; `A-03` remains outside the repair.
- **Date:** 2026-10-02.

**Verdict: REJECT W48 integration.** `A-01` is not closed because a valid current authority can
checkpoint another run's provider effect (`DJ-01`). `A-02` is narrowed at the canonical publish
boundary but not closed: process loss after temporary-object verification and before the database
callback leaves analysis bytes with no enumerable breadcrumb (`DJ-02`). The manual live-capture
entry point is also internally contradictory and now refuses every invocation it documents
(`DJ-03`). The first two findings violate the task's explicit integration contract and are release
blockers.

This review was run adversarially in a separate clean worktree and isolated PostgreSQL/MinIO
namespace, but it was performed by the same coding agent that continued the programme work. It is
therefore **not organisationally independent sign-off**. The required independent reviewer must
still examine the repaired candidate; this report does not conceal or substitute for that role.

No public credential, provider call, public-host write, deployment, tag or remote ref was touched.

## 2. Environment and method

The review ran in `/root/projects/PDF-Analysis/.local/worktrees/w48-durable-judge` on branch
`agent/w48-durable-judge`. The disposable service namespace was:

- Compose project `w48-durable-judge`;
- PostgreSQL port 55463, database `audit_w48_durable_judge`;
- MinIO API port 59070, console port 59071, bucket `audit-w48-durable-judge`.

The schema was migrated to `0014_durable_analysis_effects`. The committed durability,
reconciliation and no-guard suites established a green baseline before the attacks. Temporary
attack tests were added only long enough to run the exact seams and then deleted; the temporary
object created by `DJ-02` was point-deleted in `finally`, and the provider mutation transaction was
rolled back. No attack instrument or disposable object remains in the final diff.

Initial focused attempts made before the isolated services were running produced setup errors.
They are not counted as product failures. The same suite completed green after the owned services
and migration were ready.

## 3. Transaction-order trace

### Provider effect

1. `execute_run()` advances the Run, creates Job/Attempt/Lease authority, and commits it before an
   external effect (`runs/executor.py:663-684`).
2. `_DurableCallJournal.prepare()` inserts `provider_call_effect(prepared)` and commits before
   `adapter.complete()` (`runs/executor.py:247-259`).
3. A response advances the effect to `response_received` and commits before downstream parsing;
   an exception after dispatch records and commits `outcome_unknown` (`runs/executor.py:261-293`).
4. Completion inserts immutable `model_call`, advances the effect to `completed`, and commits
   (`jobs/repository.py:331-371`, `runs/executor.py:276-281`).

This order gives a possibly paid call a durable pre-dispatch identity and preserves an ambiguous
outcome. `DJ-01` attacks the identity binding of steps 3 and 4, not their commit order.

### Analysis-object effect

1. `DurablePublicationStore.put_blob()` uploads a temporary object and verifies it
   (`storage/durable_publication.py:73-81`).
2. The `before_publish` callback records verified blob metadata plus an attempt-scoped publication
   intent and commits (`runs/executor.py:306-315`).
3. The store publishes the canonical object (`storage/durable_publication.py:82-85`).
4. Stage persistence binds the publication and marks the blob available in the fenced result
   transaction (`runs/executor.py:326-343`). Reconciliation can later point-inspect committed
   unbound or missing canonical objects without listing the bucket.

This correctly closes the old interval between canonical publication and DB intent. `DJ-02`
attacks the earlier external upload in step 1, before any database row exists.

## 4. Release-blocking findings

### DJ-01 — a current authority can checkpoint another run's provider effect

**Class:** release-blocking authority cross-wire; `A-01` not closed.

`JobRepository.require_current()` verifies that the supplied authority is itself current
(`jobs/repository.py:218-229`). The three following provider transitions, however, identify their
target solely by `model_call_id` and prior state:

- response: `jobs/repository.py:79-86`;
- ambiguous outcome: `jobs/repository.py:88-94`;
- completion: `jobs/repository.py:96-102`.

None binds the update to the validated `run_id`, `job_id` and `attempt_id`. The migration's
composite foreign keys prove that an effect's stored run/job/attempt tuple is internally
consistent (`20261002_0014_durable_analysis_effects.py:302-306`); they do not prove that the
runtime authority supplied to an update owns that effect.

The attack created two current run/job/attempt authorities A and B, prepared an effect under A,
and invoked `record_provider_unknown()` with authority B and A's `model_call_id`. The call
succeeded and a separate read observed A's effect in `outcome_unknown`. The required refusal
assertion failed with:

```text
foreign current authority advanced another run's effect; state=outcome_unknown
```

The same predicate defect exists in response and completion. Completion is worse in shape:
`model_call.run_id` is populated from the supplied authority while the effect row is selected by
the separately supplied model-call ID. The foreign key on `final_model_call_id` checks only the
model-call ID (`20261002_0014_durable_analysis_effects.py:251`) and does not bind its run to the
effect's run.

**Consequence.** Possession of any valid current Attempt authority inside the worker process is
sufficient to mutate another current Attempt's provider journal when a foreign model-call ID is
misrouted. The journal can then misstate which authority acknowledged or completed a paid
external effect.

**Repair boundary.** Every provider transition must atomically bind the target effect to the
exact validated `(run_id, job_id, attempt_id)` tuple, with committed cross-authority tests for
response, unknown and completion. Completion must also prevent `model_call`/effect run
cross-wiring at a database-enforced boundary. This report grants no implementation path.

### DJ-02 — process loss after temporary verification leaves unindexed bytes

**Class:** release-blocking unrecorded external effect; `A-02` not closed.

`put_blob()` uploads before entering a durable database breadcrumb and calls the DB callback only
after verification (`storage/durable_publication.py:73-82`). Cleanup catches `Exception` at lines
87-93. A real process loss cannot be repaired by that handler; an uncatchable termination at the
seam after verification leaves the temporary object behind.

The attack wrapped the local S3 store so that `stage_temporary()` completed and
`verify_temporary()` returned a valid `VerifiedBlob`, then raised a `BaseException`-derived
process-exit signal before `before_publish()`. From a new transaction and by exact point lookup:

- the temporary handle still addressed the uploaded bytes;
- canonical `inspect(blob_id)` correctly reported no canonical object;
- `blob` contained zero rows for the object;
- `analysis_artifact_publication` contained zero rows for the object;
- `Reconciler.report()` did not enumerate the blob ID.

The temporary object was explicitly discarded by the probe after recording those assertions.
The required assertion that every possibly external effect is enumerable without bucket listing
failed.

**Consequence.** Analysis artifact content can persist in object storage outside retention and
reconciliation ownership. The implementation has made canonical orphan publication auditable,
but it still performs an earlier external S3 write without a durable breadcrumb. Catching broader
exceptions cannot close a real kill window.

**Repair boundary.** Establish a stable, durable and point-addressable upload intent before the
temporary S3 write, or otherwise make every staged object recoverably enumerable without bucket
listing. Add a committed kill/fresh-transaction test at the pre-intent verification seam. This
report grants no implementation path.

## 5. Additional regression

### DJ-03 — the documented manual live-capture command is unreachable

**Class:** operator-path regression and false documentation; blocks truthful W48 closure but does
not weaken the live runtime's fail-closed property.

The module documentation says this runner is the deliberate live-call path and that `--capture`
writes the recording (`analysis/text/__main__.py:1-23`). Its invocation of `run_text_analysis()`
does not supply `call_journal` (`analysis/text/__main__.py:90-95`). The stage now refuses every
live adapter lacking that journal before `adapter.complete()` (`analysis/text/stage.py:265-278`).

Running the documented shape with a synthetic invalid key and a disposable capture directory
exited `1`, returned `analysis_input_invalid` with reason `durable_call_journal_required`, made no
model call and created no capture path. No network dispatch occurred.

**Consequence.** The safety guard is correctly fail-closed, but the sole documented manual capture
workflow cannot do what its help text promises. Either the operator path needs a deliberately
owned durable authority/journal, or the obsolete live-capture claim and interface must be removed
under an explicit product decision.

## 6. Controls that held

- The focused durability baseline passed all 30 tests after isolated services were ready.
- Populated downgrade to `0013_norm_embeddings` was refused and the database remained at `0014`.
- The executor commits Run plus Job/Attempt/Lease before provider or analysis publication work.
- Provider intent commits before dispatch; an ambiguous transport failure is journalled and is
  not automatically retried.
- Canonical artifact intent commits before canonical publication; reconciliation detects both
  unbound publication and missing bound canonical object by database identity and point lookup.
- Token generation, constant-time comparison and non-disclosure assertions passed. The disposable
  token values are intentionally absent from this report.
- The only production `adapter.complete()` calls found were the journal-gated text stage and the
  separate norms repair CLI. The latter is outside AuditRun/W48-DURABLE and remains within the
  already-declared `A-03` boundary; it is not counted as a repaired or new bypass.
- Analysis `put_blob()` production callers execute through the durable decorator in the Run
  executor. No alternate canonical analysis-publication caller was found.

## 7. Command/result ledger

| command / instrument | exit and result |
|---|---|
| `git rev-parse 00100e8129ab0d144d66f7bac4899c069879b3cb` | `0`; exact subject resolved |
| wave-governance pytest | `0`; 13 passed |
| `make up`, `make check-services`, `make migrate` in the isolated namespace | `0`; PostgreSQL and MinIO ready, head `0014` |
| durable boundaries + durable DB + both ingest reconciliation files | `0`; 30 passed in 17.72s |
| temporary populated-downgrade probe | `0`; 1 passed in 1.96s; downgrade refused, head retained |
| temporary cross-authority and pre-intent object probes | `1`; 2 intended refusal/enumerability assertions failed in 0.59s — `DJ-01`, `DJ-02` |
| manual live-capture command with a synthetic invalid key | `1`; fail-closed before dispatch, no capture — `DJ-03` |
| production `adapter.complete()` and analysis `put_blob()` caller searches | completed; no undisclosed AuditRun bypass found |

The implementation candidate itself previously completed the canonical full `make gate` on a
clean tree: foundation 35 passed; backend 2705 passed, 5 skipped, 297 subtests; frontend 82 files
and 1176 tests; literal `GATE OK`. The adversarial findings demonstrate gaps in that suite. A
second full gate on this report-only judge branch would not falsify them and is not used to turn
the verdict green.

## 8. Untested questions

1. A real subprocess `SIGKILL` at the verification seam. `DJ-02` uses a `BaseException`-derived
   termination at the exact boundary to model skipped Python cleanup; it does not claim kernel-
   level process testing.
2. A paid live-provider call. The provider attack is a database authority test and intentionally
   performs no network request.
3. Public-host acceptance, restart and deployment behaviour for the exact candidate SHA.
4. Whole-bucket inventory. It is deliberately excluded by the reconciliation contract; the test
   used exact temporary and canonical point lookups.
5. Organisationally independent review of the eventual repaired candidate.

## 9. Integration, rollback and final diff

`W48-DURABLE-01` must not enter `W48-INT-CLOSE` in its current form. The next legal step is a new
bounded repair task owning the repository predicates/database invariant for `DJ-01`, the
pre-upload breadcrumb boundary for `DJ-02`, the manual runner decision for `DJ-03`, and the exact
regression tests. The repaired SHA then requires a genuinely independent durable-effects judge
and the normal integration gate.

No contract bytes, migration, dependency/lock file, composition root, application source, test,
workflow, deployment state, tag or remote ref changed in this judge slot. Rollback is deletion or
revert of the task/report commits. At report commit time the delta from the reviewed subject must
contain exactly:

```text
docs/program/reviews/W48-DURABLE-JUDGE.md
docs/program/tasks/W48-DURABLE-JUDGE.md
```
