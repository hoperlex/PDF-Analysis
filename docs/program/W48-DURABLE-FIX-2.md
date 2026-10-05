# W48-DURABLE-FIX-2 — durable-effects settlement repair

## Result

**DONE for the executor repair slot.** The release-blocking findings upheld by
`W48-DURABLE-JUDGE-2` are closed at their judged boundaries:

- `DJ-R3`: W48 analysis publications remain Attempt-attributed, report their Attempt state and
  age, and cannot be rejected while live, fresh, or backed by temporary/canonical bytes;
- `DJ-R4`: terminal execution owners settle non-repeatable provider effects through a bounded,
  resumable sweep instead of returning the same transitional row forever;
- `DJ-R5`: the standalone norms command refuses live paid execution before transport
  construction until it owns a durable per-call journal;
- `DJ-R6`: direct cross-run provenance, invalid initial state, and occupied-downgrade attacks
  are committed behavioural database tests;
- `DJ-R2`/`DJ-R8`: the source report contains an explicit scope-compliance addendum and no
  task-file edit is treated as retroactive authorization.

`DJ-R7` remains the final integrator's merged-candidate gate obligation. This executor also ran
a complete gate on its clean implementation commit and repeats it after the report commit, but
does not claim that either run substitutes for the later merged-candidate gate.

No remote ref, tag, deployment, paid provider, public host, bucket listing, or broad process
operation was performed.

## Repair shape

### Live and legacy analysis publications (`DJ-R3`)

`Reconciler.report()` no longer duplicates a current W48 publication under generic orphan or
unpublished categories. A prepared `analysis_artifact_publication` remains in
`unbound_analysis_artifacts`, with its producing Attempt state, creation timestamp, staleness,
and exact point-inspection facts. A blob with no publication row is separately named
`legacy_unattributed_blobs`: it is visible and remains content-adoptable, but absence of W48
Attempt authority is not presented as permission to reject it.

`reject_unpublished()` now locks the publication authority and requires all of these facts:

1. at least one prepared W48 publication row owns the blob;
2. every producing Attempt is terminal;
3. every publication meets the explicit age threshold;
4. neither the canonical object nor any exact temporary object is present.

Failure of any condition returns the existing typed `state_transition_not_allowed` domain error
without changing the content-derived blob identity. The ordinary action neither lists nor
deletes storage.

### Bounded provider-effect settlement (`DJ-R4`)

Reconciliation first terminates stale execution owners, then selects at most 100 eligible
effects by `(prepared_at, model_call_id)` under `FOR UPDATE ... SKIP LOCKED`. Eligibility requires
terminal Run, Job, and Attempt states plus the explicit age threshold. Each selected `prepared`
or `response_received` row advances once to terminal `abandoned`; a later pass does not return it
as unresolved or settle it again. A caller may choose a smaller positive batch size, and tests
prove continuation across two passes.

Migration `0014_durable_analysis_effects` was changed because no existing state could truthfully
settle both crash shapes without losing evidence or inventing success. `completed` requires an
immutable final `model_call`; `outcome_unknown` requires the absence of response facts, so moving
a `response_received` row there would discard a committed checksum and token/latency facts; and
leaving either row transitional is the defect in `DJ-R4`. The new internal terminal
`abandoned` state preserves either the complete response-fact tuple or its complete absence,
requires an error code, and is excluded from the unsettled partial index. Its transition trigger
allows only `prepared`/`response_received -> abandoned`.

This is an in-place repair to the authorized migration head, not a new revision. Under `R-53`, a
disposable database that previously applied different `0014` bytes must be recreated. The task
lane was freshly migrated before verification.

### Paid norms path (`DJ-R5`)

Dry-run discovery remains available. Non-dry-run execution raises typed `RunRefused` with
`durable_call_journal_required` before provider transport construction and before any ledger
write. The module prose no longer claims that a post-response page ledger makes a paid run
non-repeating. Building a separate durable corpus-call aggregate is deliberately outside this
minimum repair.

### Behavioural schema guards (`DJ-R6`)

Fresh-database tests now execute the attacks rather than comparing only catalog text:

- a completed effect owned by Run A cannot name a real `model_call` owned by Run B; PostgreSQL
  returns `23503` at `fk_provider_effect_final_call_belongs_to_run`;
- direct initial `job.state = running` and `attempt.state = running` inserts return `AM001`;
- downgrade of populated `0014` fails with the evidence counts, while the migration head and
  data remain intact.

The fresh-schema inventory was deliberately resealed for the reviewed constraint, partial-index,
and transition-function changes. No unrelated catalog family changed.

## Changed files

### Migration and runtime

- `db/migrations/versions/20261002_0014_durable_analysis_effects.py`
- `src/auditmanager/ingest/reconciliation.py`
- `src/auditmanager/jobs/__init__.py`
- `src/auditmanager/jobs/repository.py`
- `src/auditmanager/norms/__main__.py`
- `src/auditmanager/runs/reconciliation.py`

### Behavioural tests

- `tests/integration/db/test_durable_analysis_effects.py`
- `tests/integration/db/test_schema_invariant_inventory.py`
- `tests/integration/ingest/test_reconciliation.py`
- `tests/integration/ingest/test_reconciliation_rules_with_no_guard.py`
- `tests/integration/norms/test_rerecognition.py`
- `tests/integration/runs/test_durable_effect_boundaries.py`

### Programme records

- `docs/program/W48-DURABLE-01.md` — `DJ-R2`/`DJ-R8` scope-compliance addendum only
- `docs/program/W48-DURABLE-FIX-2.md`

## Verification evidence

The isolated lane was `gate-w48df2`: PostgreSQL `56460`, S3 `60060/60061`, reserved API
`56461`, and reserved Next `56463`. A real `.venv` directory and read-only corpus link were
ignored operator state.

```text
make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12       PASS
npm --prefix web ci                                        PASS (184 packages)
make foundation                                            PASS; 35 passed, fresh 0014
focused repair/judge set after final code                  PASS; 68 passed
git diff --check                                           PASS
```

The first expanded task-owned run produced `539 passed` and two failures. They were retained as
diagnostic evidence rather than called a pass: the schema inventory still named the pre-repair
`0014` digests, and this fresh worktree did not yet have the required read-only real-corpus link.
After reviewing and resealing exactly the three changed catalog families and attaching the local
corpus, the exact failed scope passed `5/5`. The later focused set passed `68/68`.

The clean implementation commit was
`a8ba8d2e8f720c6f2ec07db317668d871eed2fc8`. Its literal canonical command completed:

```text
make gate
foundation:      35 passed
backend battery: 2720 passed, 5 skipped, 4 warnings, 297 subtests passed
frontend:        lint PASS; typecheck PASS; 82 files / 1176 tests passed
whitespace:      PASS
GATE OK: battery, foundation, frontend lint/typecheck/tests and whitespace all pass
```

The warnings were one upstream Starlette deprecation and three pre-existing SQLAlchemy rollback
warnings. No test was failed or deselected beyond the gate's five recorded skips. This report
commit is followed by the same full gate on the final clean task tip; that exact final-tip result
is part of the executor handoff because a commit cannot contain a report of its own future test.

## Judge probes

The required attacks were run against production code in the disposable lane:

1. A `BaseException` immediately after the live provider returned, before the response
   checkpoint, left one `prepared` intent with no response hash and no `model_call`. Startup
   settlement advanced it to `abandoned`; the adapter call count remained exactly one.
2. Artifact process loss after exact temporary verification left a running Attempt and prepared
   publication. The report kept it W48-attributed and ineligible; explicit rejection was refused
   without changing either state. A separate terminal/stale/no-bytes case became eligible and
   settled once.
3. Direct cross-run final-call provenance and invalid initial Job/Attempt inserts were refused
   by PostgreSQL with the expected SQLSTATE/constraint evidence.
4. Occupied `0014 -> 0013` downgrade was refused, then the same database still reported head
   `0014` and retained its Job row.
5. Fresh migration/foundation and the full clean-tree gate passed as recorded above.

## Mutation evidence

`make mutation-copy` first proved that the external source copy was actually imported. The
unmutated R3/R4/R5 selection passed `4/4`. One safeguard was then weakened at a time:

| mutation | expected red result |
|---|---|
| remove current W48 blob IDs from the classification exclusion | R3 live-artifact test: `1 failed` |
| remove the provider-effect settlement call from startup reconciliation | R4 crash-boundary tests: `2 failed` |
| replace the norms live refusal with success | R5 pre-transport refusal test: `1 failed` |

A separate `FULL=1` copy made the migration bytes private. Its occupied-downgrade baseline passed
`1/1`; disabling the populated-evidence condition made the downgrade succeed and the behavioural
test failed `1/1`. No tracked task-worktree file was mutated.

## Contracts, risks, and limitations

No frozen domain/API/error contract, generated client, public route, dependency lock, frontend,
composition root, or earlier migration changed. The API remains 17 paths / 20 operations / 61
schemas. The only vocabulary change is the internal `provider_call_effect.state = abandoned`
settlement state in the owned migration and repository report.

Deliberate limits remain:

1. an ambiguous live provider outcome is never automatically retried, but provider-side
   exactly-once cannot be proven without a provider idempotency guarantee;
2. `abandoned` records conservative local settlement, not provider failure or success;
3. legacy blobs remain visible and adoptable but cannot be rejected through an action that lacks
   Attempt authority;
4. canonical or temporary bytes require a separate recovery decision; this repair does not
   delete them;
5. paid norms live mode is unavailable until a future task owns its durable call aggregate;
6. no public API exposes the internal settlement details.

Rollback is an empty-table downgrade plus code revert only before durable evidence exists. Once
any owned execution/effect row exists, use forward repair or restore; the guarded migration will
not discard it.

## Integration instruction and scope proof

Integrate both commits from `agent/w48-durable-fix-2` after reviewing the in-place `0014`
semantics. Preserve the source-report addendum. Do not restore the old orphan classification,
unbounded unresolved query, or paid norms command. The final W48 integrator still owns `DJ-R7`:
run literal `make gate` on the exact merged candidate before any ref publication. This task has
no merge, push, tag, deployment, or `origin/main` authority.

Relative to base `411c6d0a4fcc44a2b522dbb11f7ed726ef87fe12`, every tracked path is one of the
14 files enumerated under **Changed files** and is covered by the pre-dispatched
`W48-DURABLE-FIX-2` grant. In particular, `tests/integration/ingest/**` was explicitly added by
the integrator before repair began. No task file, immutable judge report, contract, earlier
migration, root dependency/lock file, composition root, frontend/global style, workflow,
credential, deployment state, or remote ref changed.
