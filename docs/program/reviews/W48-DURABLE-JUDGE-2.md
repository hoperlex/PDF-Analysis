# W48-DURABLE-JUDGE-2 — independent re-judgment of durable external effects

## 1. Subject and verdict

- **Subject:** `411c6d0a4fcc44a2b522dbb11f7ed726ef87fe12`.
- **Branch/worktree:** `agent/w48-durable-judge-2` at
  `/root/projects/PDF-Analysis/.local/worktrees/w48-durable-judge-2`.
- **Frozen surface:** domain revision 8; API 17 paths / 20 operations / 61 schemas;
  migration head `0014_durable_analysis_effects`.
- **Date:** 2026-10-05.

**Verdict: REJECT / release-blocking.** The repaired candidate closes the three original
`W48-DURABLE-JUDGE` defects (`DJ-01` to `DJ-03`) at their tested boundaries: provider writes are
authority-scoped, temporary upload has a pre-effect database breadcrumb, and the standalone
analysis runner is truthfully replay-only. The database also enforces the final-call composite
foreign key, initial state transition and occupied-`0014` downgrade refusal.

It is nevertheless not safe to merge:

- `DJ-R3` is upheld: an unbound artifact owned by an Attempt that is still `running` is reported
  without attempt state or age, and `reject_unpublished()` can change that live blob from
  `verifying` to `rejected` while the Attempt remains `running`;
- `DJ-R4` is upheld: startup reconciliation terminates the Run/Attempt but never settles its
  provider effect, so the same `prepared` effect is returned on every later startup;
- `DJ-R5` is upheld: the paid norms re-recognition path calls the provider before any durable
  call intent or page ledger record, so process loss can spend again on the same page.

`DJ-R2`, the regression-test portion of `DJ-R6`, `DJ-R7` and `DJ-R8` are additionally
must-fix-before-merge governance/test obligations. `DJ-R1` is falsified as a current blocker by
the completed `W48-RULE-01` dependency: `R-53` now records the exceptional migration authority.

| disposition | items | consequence |
|---|---|---|
| release-blocking | `DJ-R3`, `DJ-R4`, `DJ-R5` | bounded implementation repair and committed regressions before merge |
| must-fix-before-merge | `DJ-R2`, `DJ-R6` (tests), `DJ-R7`, `DJ-R8` | truthful addendum/path accounting, behavioural guards and a full gate on the eventual merged candidate |
| falsified/closed dependency | `DJ-R1` | no repair grant; preserve `R-53` and its in-place-migration warning |
| register only | none | no finding is deferred merely because the clean battery passed |

No source, test, contract, migration, ref, tag, deployment, credential or public service was
changed by this judge.

## 2. Independence and review order

The black-box pass was completed before reading `W48-CLOSE.md`, either author completion report,
or `docs/program/reviews/W48-DURABLE-JUDGE.md`. Before cross-examination the judge had read only
`AGENTS.md`, the executor prompt and its own dispatched task, then production code and executable
tests. The pre-cross-examination evidence was:

1. exact subject/ancestry and clean branch;
2. isolated foundation and focused durability suites;
3. independent provider/S3 process-loss probes;
4. direct database refusals;
5. occupied downgrade refusal, fresh migration lifecycle and the full canonical backend battery.

Only after that pass was fixed did the judge read the prior findings and author reports and
measure every `DJ-R` item below.

## 3. Environment

The disposable lane used only its assigned namespace and ports:

- Compose project `gate-w48dj2`;
- PostgreSQL `127.0.0.1:56450`;
- MinIO API `127.0.0.1:60050`, console `60051`;
- API port `56451` and Next port `56453` were reserved but no API/Next process was started.

`make foundation` established PostgreSQL 17.11, the private S3 bucket, head
`0014_durable_analysis_effects`, the storage round-trip and 35 foundation tests. Local `.env`,
runtime projection and real-corpus link were ignored operator state. No credential, execution
token, provider body, cookie, bucket key or upload handle is recorded here.

The first full battery exposed two worktree-provisioning failures, not product failures:

```text
FAILED test_release_command_cannot_turn_skips_recorded_mode_or_outage_into_pass
  FAIL: checkout contains untracked files
FAILED test_every_relevance_anchor_resolves_to_the_exact_real_corpus
  real corpus required; this test never substitutes a tiny fixture
2 failed, 2711 passed, 5 skipped, 297 subtests passed
```

The judge replaced its untracked `.venv` symlink with an ignored directory projection and linked
the read-only real corpus under ignored `.local/`. The exact two failures then passed `2/2`.
The unchanged subject's complete backend battery was rerun once and passed:

```text
2713 passed, 5 skipped, 4 warnings, 297 subtests passed in 689.74s
exit 0
```

Both modes are retained as evidence; the provisioning-only first result is not silently presented
as a subject pass.

## 4. Black-box command and probe ledger

| command / instrument | exit and measured result |
|---|---|
| `git rev-parse HEAD`; `git branch --show-current`; `git merge-base --is-ancestor agent/w48-stage-a 411c6d0...` | `0`; exact subject, correct judge branch and ancestry |
| `make foundation` | `0`; check-services/check-db/check-storage sentinels, head `0014`, `35 passed` |
| `.venv/bin/pytest -q tests/integration/runs/test_durable_effect_boundaries.py` | `0`; `11 passed` |
| temporary independent process-loss and SQL probe module | `0`; `4 passed` |
| occupied `alembic downgrade 0013_norm_embeddings` | Alembic `1` as required; refusal named populated evidence counts; wrapper recorded `occupied_downgrade_exit=1` |
| `make check-db` after the refused downgrade | `0`; current and expected head both `0014_durable_analysis_effects` |
| `.venv/bin/pytest -vv tests/integration/db/test_durable_analysis_effects.py` | `0`; `7 passed`, each on fresh disposable databases, including empty downgrade/upgrade |
| canonical backend battery from `Makefile.run_battery` | first `1` for the two provisioning conditions above; after exact two-test `2 passed`, clean rerun `0`: `2713 passed, 5 skipped, 297 subtests` |
| cross-examination live-reject and repeated-settlement probes | `0`; `2 passed`, where pass means the probe observed both defects exactly |
| direct final-call composite-FK probe | `0`; `1 passed`, observing SQLSTATE `23503` and constraint `fk_provider_effect_final_call_belongs_to_run` |

### Provider completion before response-checkpoint commit

A session subclass raised a `BaseException` after `adapter.complete()` returned and after the
transaction had staged `response_received`, but before that transaction committed. A fresh
session observed:

```text
adapter calls                         1
provider_call_effect.state           prepared
provider_call_effect.response_sha256 NULL
model_call rows for the run           0
```

Startup reconciliation then moved the Run to `failed` and named the stable model-call identity
in `unresolved_provider_effects`. This is the correct conservative answer: the possibly paid
call is not repeated and its response is not invented.

### Blob publication before stage-result commit

A `BaseException` at `source_preparation:artifact_published` bypassed Python exception cleanup.
A fresh transaction and exact S3 point inspection observed:

```text
analysis_artifact_publication.state  prepared
blob.state                            verifying
canonical object present             true
temporary object present             false
```

`Reconciler.report()` named the blob both as an orphan object and as an unbound analysis artifact
with its exact Run/stage attribution. This upholds the repaired pre-upload/publication ordering.

### Direct database refusals

Three direct SQL attacks reached the database rather than a Python guard:

1. a `provider_call_effect` with Run A and Job/Attempt B was refused with SQLSTATE `23503` at
   `fk_provider_effect_job_belongs_to_run`;
2. a `job` inserted directly as `running` was refused with SQLSTATE `AM001` and
   `state_transition_not_allowed`;
3. a completed effect owned by Run A but naming a real immutable `model_call` from Run B was
   refused with SQLSTATE `23503` at
   `fk_provider_effect_final_call_belongs_to_run`.

The schema implementation is sound at those tested boundaries. `DJ-R6` survives because these
behavioural attacks are not committed regressions, not because the constraints failed today.

## 5. Cross-examination of every `DJ-R` item

### DJ-R1 — falsified as a current blocker

Fresh measurement on the completed dependency tree:

```text
rg -c '^### `R-53`' docs/program/OWNER_RULINGS_2026-09-17.md
1

rg -n 'R-53|0014_durable_analysis_effects' docs/program/dispatch/W48-PLAN.md
374:- **Section 9:** under `R-53`, `W48-DURABLE-01` owns the one migration
375:  `0014_durable_analysis_effects`; no other migration or contract slot opens.
```

`W48-RULE-01` is recorded at integration commit `32fd8f4...` and its report is `DONE`. The old
statement that no ruling records the migration grant is no longer true. The warning remains
material: a database that saw the earlier in-place `0014` shape must be recreated, not upgraded.

### DJ-R2 — upheld and generalized

`src/auditmanager/analysis/text/__init__.py` is present in the implementation delta but absent
from the exact `allowed_paths` dispatched at `03c04a1`:

```text
git diff --name-only 03c04a1..00100e8 | rg '^src/auditmanager/analysis/text/__init__.py$'
src/auditmanager/analysis/text/__init__.py

git show 03c04a1:docs/program/tasks/W48-DURABLE-01.md \
  | sed -n '/^## Allowed paths$/,/^## Forbidden hotspots$/p' \
  | rg 'src/auditmanager/analysis/text/__init__.py'
exit 1
```

The author report nevertheless states that all tracked changes were confined to the declared
grant. The full dispatched-path audit in section 6 finds 20 product/prose/test paths outside the
union of the two author grants. This is a truthful-handoff defect. It does not by itself show
those bytes are technically wrong; it requires an explicit integrator addendum/acceptance, not a
retroactive task edit.

### DJ-R3 — upheld, release-blocking

The report query selects every prepared analysis publication and every `temporary`/`verifying`
blob. It selects no Attempt state and applies no age threshold. A fresh process-loss probe left
the source-preparation artifact live and observed:

```text
before operator action: blob=verifying, attempt=running
report: exact blob in orphan_objects and Run in unbound_analysis_artifacts
after reject_unpublished(blob_id): blob=rejected, attempt=running
```

`reject_unpublished()` checks only that the blob is not already `available`; it does not prove the
owning Attempt is terminal, stale or absent, and it does not refuse a canonical object that point
inspection just found. This can burn a content-derived identity while its producer is still
running. Repair must bind report/action eligibility to terminal authority plus an explicit age or
operator policy; merely changing display classification is insufficient.

### DJ-R4 — upheld, release-blocking

A new call intent was committed and the process exited at `provider_intent_committed`, before
dispatch. The first startup reconciliation moved its Run/Job/Attempt to
`failed`/`failed`/`lost`. A second startup found no Run to terminate, but both reports contained
the same model-call identity, and the database still read:

```text
audit_run.state              failed
attempt.state                lost
provider_call_effect.state   prepared
```

`JobRepository.unresolved_provider_effects()` is an unbounded `state <> 'completed'` query and
no reconciliation path advances an effect to a settled outcome. Historical unresolved rows are
therefore replayed forever. Repair needs an explicit durable settlement vocabulary and a bounded
sweep; erasing or silently treating an unknown provider outcome as completed would be incorrect.

### DJ-R5 — upheld, release-blocking

The only production provider call sites remain:

```text
src/auditmanager/analysis/text/stage.py:286: response = adapter.complete(request)
src/auditmanager/norms/__main__.py:147: response = self._adapter.complete(...)
```

The Run-stage site has the durable journal. The norms site does not. The outer command calls
`rerecognise(page, recogniser)` at line 278 and only writes the page ledger at lines 282-284,
after one or possibly two paid calls return. Its restart skip set is derived only from pages
already present in that ledger. A process exit after provider acceptance and before `_write_ledger`
therefore causes the same page to be paid for again on restart, contradicting the module's
"never re-spends" claim. No committed norms test mentions `provider_call_effect`, a call journal
or this kill boundary. The path must either gain a durable pre-call journal or refuse live mode
with a typed operator-visible result until such authority exists.

### DJ-R6 — narrowed but upheld as a test gap

The independent direct attacks falsify a current schema failure: the final-call composite FK,
initial transition trigger and populated downgrade guard all work. The committed tests do not
hold those behaviours down:

- `test_final_model_call_is_composite_bound_to_the_effect_run` compares
  `pg_get_constraintdef` text;
- the durable schema suite contains no direct invalid Job/Attempt initial INSERT;
- the only `0014` downgrade test downgrades an empty database.

Repository search found no committed assertion for the occupied refusal message and no direct
INSERT naming `fk_provider_effect_final_call_belongs_to_run`. The minimum repair is behavioural
regression coverage; the migration needs no change unless those tests expose a different defect.

### DJ-R7 — upheld as a release procedure obligation

The subject premise is correct: `411c6d0` is a report-only tip after the implementation commit
whose recorded gate was for `0e88589`; no gate is tied to `411c6d0`. This judge independently ran
foundation and the complete backend battery, but did not run frontend lint/typecheck/tests and
does not call that a `make gate`. The eventual merged candidate still requires one literal
`GATE OK`; neither the author record nor this judge report substitutes for it.

### DJ-R8 — upheld

The task files changed after dispatch:

```text
git log 03c04a1..afc6fcb -- docs/program/tasks/W48-DURABLE-01.md  # 7 commits
git log fd9881c..0e88589 -- docs/program/tasks/W48-DURABLE-REPAIR.md  # 3 commits
```

Every one of those commits widened ownership after dispatch. The repair task happened to grant
its own task-file path, but the executor prompt still forbids widening a task in-lane. Allowed
paths are therefore evaluated only from `git show 03c04a1:...` and `git show fd9881c:...`.

## 6. Dispatched allowed-path audit

Command and tree:

```text
git diff --name-only e3fedd0fdf2f2eda18e55c22867201f5663717a6..411c6d0a4fcc44a2b522dbb11f7ed726ef87fe12
54 paths
```

Matching those 54 paths against the union of the two exact dispatched grants leaves 23 unmatched
paths. Two are the separately dispatched prior-judge artifacts
(`docs/program/reviews/W48-DURABLE-JUDGE.md` and
`docs/program/tasks/W48-DURABLE-JUDGE.md`) and are not charged to either author slot. Of the
remaining 21, one is the in-lane-edited original task file itself and these 20 are product,
programme-prose or test paths outside both dispatched grants:

```text
docs/manual-tests/PC-01_prototype.md
docs/program/CONTRACT_PIN_REGISTRY.md
docs/program/CURRENT_STATE.md
docs/program/P02_SEAMS.md
docs/program/PROTOTYPE_EXECUTION_PLAN.md
docs/program/PROTOTYPE_PROFILE.md
src/auditmanager/analysis/text/__init__.py
src/auditmanager/runs/__init__.py
src/auditmanager/runs/repository.py
src/auditmanager/shared/identity/ids.py
src/auditmanager/storage/README.md
src/auditmanager/storage/port.py
src/auditmanager/storage/s3.py
tests/contract/api_v1/test_doc_prose_facts.py
tests/contract/domain_p02/test_identifier_catalog.py
tests/contract/domain_p02/test_seam_register.py
tests/integration/composition/test_the_run_leaves_the_request_thread.py
tests/integration/foundation/test_real_providers.py
tests/integration/shared_kernel/test_topology_guard.py
tests/integration/storage/test_publication.py
```

Several were necessary consequences of moving the migration head or changing a public port, but
necessity is not ownership. The integrator must acknowledge the exact inherited bytes and record
the scope correction; author reports must not retain the claim that dispatched grants were obeyed.

## 7. Minimum repair grant justified by this verdict

This report grants no repair itself. The smallest follow-on task should consider:

- `src/auditmanager/ingest/reconciliation.py` and focused ingest/run tests for `DJ-R3`;
- `src/auditmanager/jobs/**`, `src/auditmanager/runs/**`, the owned `0014` migration only if a
  settled effect state requires it, and focused run/DB tests for `DJ-R4`;
- `src/auditmanager/norms/__main__.py` plus focused norms tests for `DJ-R5`;
- `tests/integration/db/test_durable_analysis_effects.py` (or another explicitly named focused
  DB test) for the three `DJ-R6` behavioural refusals;
- `docs/program/W48-DURABLE-01.md` for a scope-compliance addendum covering `DJ-R2`/`DJ-R8`.

No contract byte, generated client, API router, dependency lock, global style, deployment path,
remote ref or tag is justified by these findings. The integrator owns the final merged gate.

## 8. Required attacks, restoration and security

No production source mutation was required. The adversarial injections were process exits,
foreign tuple inserts, invalid initial state, cross-run final provenance, occupied downgrade,
live rejection and repeated startup reconciliation. The expected safety assertions that went red
in cross-examination were:

```text
expected: reject_unpublished refuses a blob owned by a running Attempt
actual:   (blob.state, attempt.state) == (rejected, running)

expected: a terminal Run's provider effect leaves the next startup's unresolved set
actual:   second startup still returns the same prepared model_call_id
```

Every temporary pytest source file was deleted after execution. The local runtime/corpus
projections are ignored. The lane contains only disposable data and is torn down after report
verification. No broad process kill, bucket list, production object deletion, credentialed live
provider call or public-host action occurred.

## 9. Contracts, risks, open questions and integration instruction

### Contracts

No external or internal contract was created or changed by this judge. The subject still presents
API 17/20/61 and migration head `0014_durable_analysis_effects`.

### Known limits

1. Process loss was modeled with `BaseException` at the exact seams, not OS-level `SIGKILL`.
2. No paid provider, public host, API server, Next server, deployment or browser acceptance was
   exercised.
3. The full backend battery and foundation passed; this task did not run the frontend and does
   not claim a complete `make gate`.
4. The real migration from an earlier in-place shape of revision `0014` was not attempted; `R-53`
   requires recreation of such disposable databases.

### Open questions

1. Which explicit provider-effect terminal states distinguish operator-resolved, abandoned and
   retry-prohibited unknown outcomes without inventing provider success?
2. What terminal-Attempt and age criteria authorize `reject_unpublished`, and should a present
   canonical object always require a separate operator action?
3. Should norms re-recognition receive its own durable call aggregate, or remain live-refused
   until the later corpus execution model owns one?
4. Which integration record accepts each of the 20 out-of-dispatch paths, rather than
   retroactively widening either frozen task file?

### Integrator instruction

Do not merge this report into the subject before consuming the verdict. Dispatch one bounded
repair for the upheld items, commit the behavioural regressions, re-run focused fault probes, and
then run one complete `make gate` on the exact merged candidate. This judge grants no publication
or deployment authority.

## 10. Changed files and final allowed-path proof

- Changed tracked files: `docs/program/reviews/W48-DURABLE-JUDGE-2.md` only.
- New/changed contracts: none.
- Rollback: revert the report commit if the judging procedure is invalid.
- Forbidden hotspots: untouched; the subject-to-judge delta is report-only.

Final proof command after committing this report:

```text
git diff --name-only 411c6d0a4fcc44a2b522dbb11f7ed726ef87fe12..HEAD
docs/program/reviews/W48-DURABLE-JUDGE-2.md
```
