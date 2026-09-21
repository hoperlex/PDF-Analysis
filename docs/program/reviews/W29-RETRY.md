# W29-RETRY — a missing file is not an outage

**Session** `W29-RETRY` · base `origin/dev` = `714da53` · branch `agent/w29-retry` ·
worktree `/root/w29retry` · lane `gate-w29a` (PostgreSQL 56040, MinIO 59640/59641,
database `audit_w29a`, bucket `auditmanager-gate-w29a`). No image built. `df -h /` on
arrival **12 GB**, on exit **9.5 GB** — the mutation copy took most of the difference and
was deleted. Started 2026-09-21 16:11:33 +05:00, handed back 16:31 — **20 minutes**, wall-clock, of which the gate is 5:40 and provisioning ~3.

`W28-LIVE` measured a run on a document with no recording: **16.1 s**, of which **10.0 s**
is the retry ladder, terminal `failed`. Ten of those sixteen seconds were spent waiting for
a file to appear on a local disk.

## 1. The question, and the answer

`dependency_unavailable` is `retryable: true` in the frozen catalog, and
`src/auditmanager/runs/retry.py` is right to ladder it: for a provider that is
unreachable, a second attempt can answer differently. **The policy is not the defect and
it is not touched by this branch.** The defect is what the adapter says about itself.

`RecordedAdapter.complete` read a file out of a local directory. When the file was not
there it reported `dependency_unavailable` — a *transport* condition — for a *local,
deterministic* one, and so bought three attempts and both pinned backoffs waiting for a
file to appear on a disk it had already looked at. `W28-LIVE` measured the cost through a
browser: **10.0 s of a 16.1 s run**, three runs of three, and a terminal that told the
operator to retry a run that cannot succeed.

**That is the `W23-PARTIAL` shape.** There, `proxy.py` wrote a call-status word into a
stop-reason field and a test asserting the string pinned it. Here the adapter wrote a
transport code into a stop-reason field, and
`test_missing_recording_is_dependency_unavailable_and_never_a_live_call` pinned it — the
defect was in the test's *name*.

## 2. Where the repair belongs, and why not in the policy

The task allowed `src/auditmanager/runs/**` on proof that the policy is where this
belongs. **It is not, and the proof is the policy's own construction.**

`RetryPolicy` decides by one question: `error.code in self.retryable_errors`, and
`__post_init__` refuses to construct over any code the frozen catalog does not mark
retryable. The module docstring states why that is structural rather than a comment:
*"A policy that retries `analysis_failed` is therefore not expressible, and making it
expressible means editing a frozen contract."* The code **is** the classification. There
is no second axis, and adding one — a "deterministic" flag, an adapter allow-list, a
`isinstance` on the raising module — would put the decision back in the executor as a
literal, which is exactly the arrangement `P4_CLOSURE.md` §6 and this module were built to
prevent. The only honest way to tell the policy this failure cannot change is to report a
code that says so.

**No new code was needed, and no contract was touched.** `analysis_input_invalid` is an
existing catalog member, `retryable: false`, and its declared `safe_detail_keys` are
exactly `stage_id` and `reason` — the two the adapter already fills for the other three
ways a recording fails. No 22nd-code ruling is required and none is requested.

The choice is not a judgement call imported from outside: **this adapter already owned the
vocabulary.** A recording that is filed under a key it does not declare, one at an
unsupported version and one that is malformed all report `analysis_input_invalid` with a
`recording_*` reason. All four are one fact — *the corpus this adapter was given does not
answer this request* — and absence was the only one dressed as an outage.

`live.py`'s `ImportError` on the pinned SDK is the same shape and the same argument: the
two construction refusals either side of it in the same constructor, a missing credential
and a version mismatch, already report `analysis_input_invalid` with a reason. Only the
absent SDK reported a retryable outage for a deployment that cannot change while the
process runs.

## 3. The sweep

Not a grep for one string. The retryable set is **computed from the catalog** and every
form each code can appear in is searched; the whole output is below, with no `head` and no
`tail`, because `W20-CODE` piped a correct sweep through `head -20` and read the
truncation as the answer.

```sh
CODES=$(python3 -c "
import json
d=json.load(open('contracts/domain/v1/error-codes.json'))
print(' '.join(k for k,v in d['codes'].items() if v['retryable']))")
# -> idempotency_key_in_progress dependency_unavailable staged_upload_lost
grep -rnE "IDEMPOTENCY_KEY_IN_PROGRESS|DEPENDENCY_UNAVAILABLE|STAGED_UPLOAD_LOST|\
\"(idempotency_key_in_progress|dependency_unavailable|staged_upload_lost)\"|\
'(idempotency_key_in_progress|dependency_unavailable|staged_upload_lost)'" src/ --include='*.py'
```

**18 hits at the base `714da53`, 16 after this branch.** Every one, classified:

| site | what it is | can it change between attempts? |
|---|---|---|
| `shared/errors/codes.py:27,31,33` | the closed enum's three retryable members | declaration, not a raise |
| `api/schemas/models.py:234,238,240` | the transport schema's mirror of the same three | declaration, not a raise |
| `runs/retry.py:81` | `RETRYABLE_STAGE_ERRORS`, the policy's narrower set | declaration, not a raise |
| `api/routers/handlers.py:167` | inbound HTTP **503 → code** at the edge | a mapping of a status already received, not a cause |
| `storage/errors.py:189` | `StorageUnavailableError.code` | carrier; raised only at `storage/s3.py:430,435,441,442`, all from a botocore `ClientError` ≥500 or a transport error against a **remote** store — **yes, can change** |
| `storage/errors.py:302` | `StagedUploadLostError.code` | carrier; the staged object is gone from a **remote** store and re-sending is the declared remedy — **yes** |
| `shared/db/errors.py:32` | `DatabaseUnavailableError.catalog_error_code` | carrier; raised at `shared/db/engine.py:77` and `migrations.py:88` on a refused **connection** — **yes** |
| `ingest/commands.py:321` | `idempotency_key_in_progress` | a command with the same key is **still executing**; it finishes — **yes** |
| `analysis/text/proxy.py:121` | `URLError`, the proxy could not be reached | **yes** |
| `analysis/text/proxy.py:282` | proxy answered 429/503, saturated | **yes** |
| `analysis/text/proxy.py:287` | proxy answered 504, deadline | **yes** |
| `analysis/text/live.py:106` | any SDK failure on `messages.create` | **yes** |
| **`analysis/text/recorded.py:100`** | **a recording file absent from a local directory** | **NO — repaired** |
| **`analysis/text/live.py:51`** | **`import anthropic` raised `ImportError`** | **NO — repaired** |

A second axis, in case a local-miss site reached a retryable code by a route the first
sweep could not see — every handler in `src/` that catches a filesystem exception:

```sh
grep -rn "OSError\|FileNotFoundError\|IOError" src/ --include='*.py'
```

**13 hits.** Seven are `storage/s3.py`, where `OSError` is a socket failure against a
remote store. `analysis/text/lock.py:89` (the P02 lock document unreadable) reports
`internal_error`, non-retryable. `analysis/stages/extraction.py:138,189` and
`ingest/envelope.py:203` report `analysis_input_invalid` / a validation code,
non-retryable. `recorded.py:95` was the only one that reached a retryable code, and it is
the site repaired here.

**The class is two members, both repaired, and the sweep is closed.**

## 4. Shown to fail

`make mutation-copy MUT=/root/w29retry-mut`, baselined green first — 189 passed over
`tests/integration/analysis_text` and `tests/integration/runs` against the **unmutated**
copy, with `auditmanager.__file__` asserted to resolve under it. No tracked file was
edited. The copy was deleted afterwards.

**Mutation 1 — the repair reverted in `recorded.py`** (back to `DEPENDENCY_UNAVAILABLE`
with `dependency=DEPENDENCY_NAME`): **5 red.**

```
FAILED tests/.../test_provider_modes.py::test_missing_recording_is_not_a_transport_failure_and_never_a_live_call
FAILED tests/.../test_provider_modes.py::test_every_way_the_corpus_fails_to_answer_takes_the_same_non_retryable_code
FAILED tests/.../test_provider_modes.py::test_missing_recording_envelope_leaks_no_path_or_payload
FAILED tests/.../test_partial_and_status.py::test_a_corpus_that_cannot_answer_is_failed_and_never_partial
FAILED tests/integration/runs/test_exhausted_budget_run_row.py::test_the_recorded_adapter_over_an_empty_directory_is_asked_exactly_once
```

The last one is the outcome itself, and it fails on the behaviour rather than on a string:

```
E  AssertionError: the empty-recordings adapter was asked 3 times. Re-asking a local
   directory for a file that is not in it cannot answer differently, and the budget of 3
   is for a provider that may come back
E  assert 3 == 1
```

**Mutation 2 — the repair reverted in `live.py`**: exactly **1 red**,
`test_every_construction_refusal_is_one_no_second_attempt_could_answer`, on
`provider_sdk_not_importable reports dependency_unavailable, which the catalog marks
retryable`.

**Mutation 3 — the ladder broken instead of the code**
(`RetryPolicy.has_budget_for` → `attempt <= 1`, so nothing is ever retried): **8 red**,
all in `test_retry_policy.py`, `test_retry_policy_refusals.py` and the scripted-provider
half of `test_exhausted_budget_run_row.py`. **My new route test stayed green, and that is
correct and worth stating plainly**: it asserts one attempt and no wait, which a broken
ladder also produces. It cannot on its own tell "this code is not retryable" from "no code
is retried any more". The scripted `_NeverReachable` test beside it is what carries that
distinction, which is why the fixtures were repaired rather than deleted.
`test_terminal_reason_names_the_cause.py` also stayed green under mutation 3, which is
right: its claim is the run row's reason, and that holds whether the reason was reached in
one attempt or three.

## 5. What the tests were really asserting

Three fixtures induced "an unreachable provider" with a `RecordedAdapter` over an empty
directory. That is a missing local file, not an outage, and once the adapter stopped
calling it one the fixtures would have gone on claiming coverage they no longer had. They
are repaired, not deleted:

* `test_terminal_reason_names_the_cause.py` — the whole suite's fixture is now a scripted
  `_NeverReachable`, so the run row's transport reason keeps a run that really spends the
  ladder;
* `test_exhausted_budget_run_row.py` — the route test is **inverted**: it used to assert
  that the empty directory exhausts the budget, and now asserts one attempt, no wait, and
  `attempt_budget_exhausted: False`. The file's own docstring records that its premise was
  true and was the defect;
* `test_partial_and_status.py` — the unavailable-provider case takes a real unreachable
  provider, and a second test keeps the corpus-miss case, because `partial` is a strict
  subset of pages and none is not a subset either way;
* `test_explicit_failures.py` (`p02_journey`) — the claim never depended on the code. It
  injects no `sleep`, so it really waited out `(2.0, 8.0)` on every battery run; it does
  not any more.

New guards: the four-ways-the-corpus-fails test, which enumerates the adapter's own
`recording_*` vocabulary so a fifth member on a retryable code fails there, and the three
live construction refusals, with the absent-SDK branch reached through
`builtins.__import__` because the SDK is installed in every lane.

**No timing is proved by sleeping.** Every assertion uses the `sleep` callable
`execute_run` already takes, and `waits == []` is an assertion about the ladder, not about
the clock.

## 6. Characterization records — measured, and nothing moved

36 records under `tests/characterization/w13_baseline/records/`. Two independent methods,
because a record stores its body as a JSON **string** and a structural walk for
`error_code` finds nothing at all — the right answer for the wrong reason.

```sh
grep -rl "dependency_unavailable" tests/characterization/w13_baseline/records/ | wc -l   # -> 0
```

and a parse that goes **through** the string:

```py
json.loads(record["response"]["body"]["text"])["error_code"]
```

which reads 36 records and finds `validation_failed` ×11, `not_found` ×3,
`dependency_credential_refused` ×1, `idempotency_key_reuse` ×1 and no envelope body at all
in the other 20. **Zero carry `dependency_unavailable`; zero carry `analysis_input_invalid`.
No record moved, and no `permitted_change` is written for a change that did not happen.**

## 7. The gate

`make gate FOUNDATION_PYTHON=/usr/bin/python3.12` on `ffdd905`, lane `gate-w29a`, output
redirected to a file and the status taken from `$?` on the next line — never through a
pipe:

```
battery    2001 passed, 5 skipped, 1 warning, 169 subtests passed in 273.70s
foundation 35 passed in 29.66s
frontend   Test Files 49 passed (49)   Tests 715 passed (715)
GATE OK: battery, foundation, frontend and whitespace all pass
GATE_EXIT=0
```

Against the brief's base — battery **1998 / 5 / 169**, foundation **35**, frontend **715
in 49 files** — the battery is **+3** and nothing else moved. The three are the three new
tests: the four-ways-the-corpus-fails guard, the corpus-miss half of the partial test, and
the live-construction-refusals guard. Every other change is a rename or a fixture swap,
which moves no count. **I did not re-measure the base myself**: one lane takes one
measurement at a time, the brief pins the figures, and the frontend and foundation halves
of this run reproduce them exactly, which is the check that the lane is the one those
figures came from.

Provisioning, before any of it: `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`
exited 0 **and** `.venv/bin/python -c "import boto3"` printed `1.43.90`, because an exit
code alone has been wrong here before; then `npm --prefix web ci`, exit 0, 136 entries in
`web/node_modules`.

## 8. What a user sees change, and the one thing I could not touch

A run in `recorded` mode against a document with no recording ends `failed` either way.
Two things about it change:

* it now takes **~6.1 s instead of 16.1 s**, because the 10.0 s ladder is gone —
  `W28-LIVE`'s figure, minus `BACKOFF_SECONDS` summed;
* the run screen prints `Terminal reason: analysis_input_invalid` instead of
  `dependency_unavailable`. The screen renders `terminal_reason` **verbatim** as a
  `<code>` element (`web/src/widgets/run-progress/ui/run-progress.tsx:133`), so no
  frontend mapping breaks and **no `web/**` change is needed** — but the string a person
  reads is different, and `W29-SAY` is working on that screen. **That is the merge
  ordering fact for the integrator.** `analysis_input_invalid` is already a first-class
  kind in `web/src/entities/audit-run/model/run-failure.ts`, kept deliberately distinct
  from `validation_failed`, so the code is one the frontend already knows.

**One forbidden-hotspot file is invalidated by this repair and I did not touch it.**
`tests/e2e/pc01/journey/fixtures/w28-live/w28-recorded.manifest.json`, line 210, is a
browser-journey expectation from `W28-LIVE`:

```json
"expects_rendered": [ ..., "Terminal reason: dependency_unavailable", ... ]
```

That manifest drives the recorded-mode journey this branch changes, so re-driving it would
fail on that one line, which must become `"Terminal reason: analysis_input_invalid"`.
`tests/e2e/**` is a forbidden hotspot for this session and `make gate` does not run it, so
it is reported rather than edited. **It is a one-line owner edit.**

The other e2e case that greps as if it were affected is **not**:
`tests/e2e/pc01/test_acceptance.py::test_c10_an_unavailable_provider_fails_the_run_explicitly`
asserts `terminal_reason == "dependency_unavailable"`, and it induces the failure in
**proxy** mode against `http://127.0.0.1:1` with nothing listening — a real transport
failure through `proxy.py`, untouched by this branch. Measured by reading the fixture, not
assumed from the string.

## 9. Risks and known limitations

1. **The route test alone cannot tell a non-retryable code from a broken ladder** —
   mutation 3 above. It is paired with the scripted-provider test for that reason; if
   someone deletes the scripted half, the pair stops being a pair.
2. **`live.py`'s absent-SDK branch is not reachable in a real lane**, because the SDK is
   installed. Its guard defeats `builtins.__import__`, which is a test of the branch, not
   of a deployment that has ever existed here.
3. **The `_translate` fallback in `storage/s3.py:442`** returns `StorageUnavailableError`
   — retryable — for *any* botocore `ClientError` that is not a known bucket-missing or
   denied code and carries no ≥500 status. That is wider than the evidence supports and
   could dress a deterministic remote refusal as an outage. It is **not** this class (the
   condition is remote, and an S3 error is not laddered by `RetryPolicy`, which only runs
   over the model stage), so it is reported and not repaired, and it is not a debt row I
   own.
4. Nothing here is behind a flag. The change is a code value on one failure path; a
   rollback is `git revert` of the one `src/` commit, which would also redden the five
   guards in §4.

## 10. Forbidden hotspots — the proof

```
$ git diff --stat origin/dev...HEAD
```

touches **only** `src/auditmanager/analysis/text/{recorded,live}.py`, **seven** files under
`tests/integration/` (one of them a `conftest.py`), and `docs/program/reviews/W29-RETRY.md`
— 10 files, +369 / -67. No `contracts/**`, no
`web/**`, no `infra/**`, no `Makefile`, no `tests/e2e/**`, no `artifacts/**`, no
`DEBT_REGISTER.md`, no `CURRENT_STATE.md`, no migration, no lockfile. No tag and no
checkpoint was created. `.env` is git-ignored and is this lane's only untracked addition.

## 11. Instruction to the integrator

1. Merge `agent/w29-retry` (base `714da53`).
2. **Sequence against `W29-SAY`**: the terminal reason a person reads on the run screen
   changes from `dependency_unavailable` to `analysis_input_invalid` for a recorded run
   with no recording. No `web/**` file needs editing for it, but a `W29-SAY` change that
   writes an explanatory sentence per code will want this one.
3. **One line is owed in a forbidden hotspot**, §8:
   `tests/e2e/pc01/journey/fixtures/w28-live/w28-recorded.manifest.json:210`.
4. No contract changed; no catalog addition; no frontend reseal (`D-18`, `R-13`) is
   triggered.

## 12. Three documents this repair makes stale, none of them mine to edit

Found by `grep -rln "no recorded model response\|missing recording" docs/`, judged by
reading each rather than by the match:

* `docs/program/tasks/P2-AI-01.md:71` and `:85` — a **completed task file** whose
  acceptance text still states the old behaviour as a requirement: *"a missing recording
  is `dependency_unavailable` and never a live call"*. The second clause is still true and
  still enforced by the socket guard. The first is now wrong. This is a superseded
  specification rather than a historical observation, so it is worth a line from whoever
  owns `docs/program/tasks/**`; outside my `allowed_paths`.
* `docs/program/W5_CLOSURE.md:48` — a closure record of what `W5-ADV` found at the time.
  Historical and correct as history: the route it describes really was the exhausted-budget
  route. Left alone deliberately.
* `docs/program/reviews/W28-LIVE.md` — the measurement this session answers. Its finding 3
  is now fixed, not wrong. Left alone.
