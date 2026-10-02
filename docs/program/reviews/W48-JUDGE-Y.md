# W48-JUDGE-Y — architecture and durable-evidence audit of Stage B

## 1. Subject and verdict

- **Subject:** `14caf886e78883ed771d81fbf463c98af727c938`, the same clean four-lane
  Stage-B merge reviewed by Judge X.
- **Frozen base:** `fad3c28748ef52bc9b5f711191ff0130483e0055`.
- **Frozen surface:** API 17 paths / 20 operations / 61 schemas; error catalog 22;
  migration head `0013_norm_embeddings`.
- **Date:** 2026-10-02.

**Verdict: REJECT W48 closure.** Stage B correctly leaves the audited `A-01` and `A-02`
data-integrity defects in place, and they remain release blockers: a paid provider response can
exist before any durable call/attempt identity, and artifact bytes can exist in object storage
before any committed metadata or reconciliation authority. `A-03` remains a measured minimum of
sixteen cross-context deep imports and needs an owner decision before mechanical repair.

This review also found one new Stage-B false green (`Y-01`): the executable governance rules are
never applied to repository task files. A new `W49-*` task omitting all four mandatory sections
left the complete governance test green.

The D-74 narrow existence seam is complete and correctly wired. The WEB screen-wide consumers
share the new renderer, with five named focused exceptions. Contracts, migrations, locks,
composition inputs and the `make gate`/manual-acceptance separation remain frozen.

## 2. Environment and method

The review ran report-only in
`/root/projects/PDF-Analysis/.local/worktrees/w48-judge-y` at the exact subject. Static traces
cover all named implementations and callers, provider/artifact ordering, frozen paths and test
command dependencies. A deliberately invalid untracked `W49` task was added for one governance
mutation, the complete test was run, and the file was removed immediately. The final checkout
contains only this report.

The worktree has no private runtime environment of its own. A DB-backed D-74 rerun against the
root checkout's configured port found no PostgreSQL listener and errored all eight cases in setup;
it is retained as an unavailable measurement, not called a product failure. The completed
`W48-PORTS` lane had already run the same file plus the port-totality suite on its isolated
disposable lane: 20 passed.

## 3. Findings

### Y-01 — mandatory governance is executable only for fixture strings, not dispatched tasks

**Class:** Stage-B false green; governance coverage.

`tests/contract/program/test_wave_governance.py` defines `governance_findings(markdown)` and
checks the template, one embedded valid task, four embedded invalid variants, prose agreement,
six immutable W46 files, the addendum and D-52. It never enumerates or reads
`docs/program/tasks/*.md`.

The judge added an untracked `docs/program/tasks/W49-JUDGE-Y-BROKEN.md` containing only a title
and one sentence — no Enumerator ownership, Captured premise evidence, Historical evidence or
Publication authority section — then ran:

```sh
/root/projects/PDF-Analysis/.venv/bin/python -m pytest \
  tests/contract/program/test_wave_governance.py -q
```

Result: exit `0`, `10 passed in 0.11s`. The invalid file was removed and the checkout restored.

**Consequence.** The task template and prose can state a hard dispatch rule while every future
task silently bypasses it. Authors must opt into calling the parser themselves; the gate does not
hold the maintained task universe.

**Repair boundary.** The suite needs one explicit, owned enumerator over newly dispatched task
files and must call `governance_findings()` for each member. Legacy documents need a declared
baseline or start boundary rather than exemptions discovered ad hoc. The mutation above must go
red and name the file plus all absent sections.

### A-01 upheld — external provider effect precedes durable attempt provenance

`src/auditmanager/analysis/text/stage.py:225-240` calls `adapter.complete(request)` at line 226
and allocates `ModelCallId` only after a response at line 240. The executor writes returned
model-call rows only at `src/auditmanager/runs/executor.py:437-445`. The carrier commits the
`running` row before stages, then commits every stage/call/terminal row together only after
execution at `src/auditmanager/runs/carrier.py:253-270`.

This is not covered by another durable authority. `src/auditmanager/runs/retry.py:13-19` says an
attempt is an in-process loop counter, and `runs/scope.py` pins Job, Attempt, lease, heartbeat,
execution token and outbox as absent.

**Consequence.** Kill after provider acceptance but before `_record_model_calls`/commit leaves a
`running` run whose eventual reconciliation has no call id, token/cost, request checksum or
response provenance. A repeat has no durable attempt identity proving it is not purchasing the
same effect again.

This is a release blocker under the repository's no-dual-write/no-in-memory-job rules. Static
ordering proves the interval; a repair additionally needs a kill-after-acceptance test on owned
disposable infrastructure.

### A-02 upheld — object publication precedes recoverable DB authority

`src/auditmanager/analysis/ports/artifacts.py:60-86` calls `blob_store.put_blob`. Deterministic
stages publish inside `run_stage`; only after the function returns does
`src/auditmanager/runs/executor.py:657-665` persist a `stage_result`. Text observations repeat the
ordering at executor lines 462-475. The carrier's final commit is line 270.

Analysis publication does not create a `BlobMetadataRepository` row, outbox event or named orphan
reconciler. The repository's blob metadata/reconciliation use belongs to ingest, not this path.

**Consequence.** Kill or rollback after `put_blob` and before commit leaves an object consuming
storage with no canonical DB reference and no enumerator that can classify or remove it. Content
addressing protects bytes, not reachability.

This remains a release blocker. Repair needs named metadata/outbox/reconciliation ownership and
fault injection at every publication boundary in a disposable bucket; the alpha bucket must not
be used as a test fixture.

### A-03 upheld — architecture debt remains, not newly enlarged by Stage B

The Stage-A AST walk's minimum sixteen ALR-05 violations still exists. Representative sites are
`runs/executor.py` importing analysis internals, analysis modules importing `storage.models`,
ingest importing `storage.blob_repository`, decisions importing `findings.queries`, and
`api/composition.py` importing bootstrap internals.

No Stage-B runtime lane added a new backend cross-context import. The frozen architecture rule
currently labels all sixteen as errors, while `api/composition.py` describes an intentional seam
for which the rule has no waiver. Integration must choose the public-module/ownership shape before
mechanical edits. This is architecture debt, not grounds to reinterpret `A-01`/`A-02` as closed.

## 4. Traces and measured-clean results

### D-74 narrow existence seam

The complete implementation/caller matrix is present:

| role | run | finding |
|---|---|---|
| semantic port | `RunPort.run_exists` | `FindingPort.finding_exists` |
| production adapter | `RunAdapter.run_exists` | `FindingAdapter.finding_exists` |
| API test adapter | `_Runs.run_exists` | `_Findings.finding_exists` |
| caller | findings router line 79 | decisions router line 128 |

`tests/integration/api/test_existence_is_not_a_full_read.py` asserts that run existence touches
neither `stage_result` nor `model_call`, and finding existence touches neither
`expert_decision_event` nor `finding_evidence`; full-read controls prove the SQL recorder sees
those tables. The lane's final DB-backed result was 20 passed with the port-totality suite.

D-74 was already implemented by `8877d5de`; `W48-PORTS` truthfully changes only its report. The
canonical debt register remains for the integration closeout owner.

### Shared screen harness census

All five screen-wide consumers use `renderScreen` from `web/tests/unit/screens/harness.ts`:

- gender-agreement guard;
- prepared-sections guard;
- rendered-language guard;
- screen-set guard;
- style screen matrix.

Direct `AppRouterContext` use remains in five focused tests: cold-load, forms-and-pages,
project-sections, run-cache-shape and stage-comparison. They intentionally build narrow router or
cache conditions rather than duplicating the screen-wide provider stack. No production React
component performs direct SQL, S3 or filesystem access.

### Frozen bytes and command separation

The Stage-B diff from `fad3c28748ef52bc9b5f711191ff0130483e0055` to the subject is empty for
contracts, DB migrations, root dependency/lock files, bootstrap/composition inputs and frontend
dependency/lock files. API/error counts and migration head therefore remain frozen.

`Makefile` defines `alpha-acceptance` separately. `gate: foundation` has no dependency on it, and
`make -n gate` contains no `alpha-acceptance`, Playwright journey, `curl` or external URL. The
printed recipe ends in the literal gate sentinel only after battery, foundation, frontend and
whitespace. Therefore `make gate` remains secret/network-free by dependency graph; live
acceptance cannot be claimed from it.

## 5. Command/result ledger

| command / instrument | exit and result |
|---|---|
| `git rev-parse HEAD` | exact subject `14caf886e78883ed771d81fbf463c98af727c938` |
| invalid actual `W49-*` task + governance suite | `0`; 10 passed — `Y-01` false green |
| frozen-path `git diff --name-only` | empty |
| `rg` of `run_exists` / `finding_exists` | all ports, production/test adapters and two callers accounted |
| D-74 DB-backed rerun in judge worktree | `1`; 8 setup errors because configured PostgreSQL port had no listener; not product evidence |
| accepted `W48-PORTS` isolated-lane command | `0`; 20 passed, one deprecation warning |
| screen harness/direct-context census | five screen-wide shared consumers; five named focused exceptions |
| `make -n gate` live/network query | no matches; acceptance target absent from gate recipe |
| provider/artifact ordering trace | `A-01` and `A-02` unchanged and still reachable |

## 6. Untested questions

1. Kill after provider acceptance and kill after each object publication against owned disposable
   provider/S3/PostgreSQL services.
2. Real public-host authentication, revocation, direct-API denial and exact-SHA acceptance; no
   credential/deployment authority was granted.
3. A final architecture shape for the sixteen ALR-05 violations, especially the composition seam.
4. Online dependency, licence and container vulnerability scans.
5. Current alpha MinIO inventory and orphan count; static absence of a reconciler cannot measure
   already stranded objects.

## 7. Integration, rollback and final diff

Cross-examine `Y-01` with Judge X before any repair. A bounded guard repair can own only the
governance test/enumerator surface. `A-01` and `A-02` require explicit durable-execution/storage
ownership and may require a contract or migration task; they must not be smuggled into a guard
fix. `A-03` requires the owner/integrator architecture ruling described above.

Rollback is deletion/revert of this report. No contract, migration, dependency/lock, runtime,
test, composition root, global style, deployment state, ref or tag changed.

At report commit time the subject diff must contain exactly:

```text
docs/program/reviews/W48-JUDGE-Y.md
```

## 8. Cross-examination

Judge Y read `W48-JUDGE-X` at report commit `05031d2` and inspected both retained synthetic
evidence sets plus the named source branches. The following rulings are final:

- **`X-01` upheld and release-blocking for the acceptance instrument.** The generated JSON is
  internally contradictory exactly as reported: `providerLive.outcome` is `BLOCKED`, both process
  exits are zero and the root verdict is `PASS`. The verifier's verdict expression requires a
  non-zero journey exit before dependency outage can block. No other finding is added for the
  outage. This is a real reachable classification branch, not malformed evidence.
- **`X-02` upheld.** The shell condition is a suffix match only. X's fake response is sufficient
  because the preflight parses the attacker URL verbatim and calls it PASS. The later full journey
  does not repair a false positive emitted by the documented standalone preflight mode.
- The refusal mutation, unreachable-origin result and focused WEB checks are consistent with the
  source and do not falsify either finding. In particular, the existing dependency fixture exits
  non-zero and therefore cannot cover X's `partial`/exit-zero branch.
- X correctly refuses to convert absent public credentials into positive live evidence. This
  matches Y's command-separation trace: `make gate` cannot satisfy the external acceptance
  prerequisite.

One scope correction guides repair: same-origin redirect comparison must normalise default ports
and reject user-info/host ambiguity; a hand-written string-prefix test would create another false
green. The implementation can use a small standard-library URL parser/probe without changing an
API contract or dependency lock.

Cross-verdict: neither `X-01` nor `X-02` is falsified. Together with `Y-01` they warrant one
bounded guard/acceptance repair. `A-01` and `A-02` remain independently blocking after that repair.
