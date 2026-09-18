# `W17-VIEW` — what a published run tells a user about itself

**Session `W17-VIEW`, wave 17. HEAD on arrival: `ebf06ad`** (`origin/dev`,
*"feat: the mutation copy carries the tests, and a migration is mutable at last"*).
Worktree `/root/w17view`, branch `agent/w17-view`. Logs in `/root/w17view-logs/`.
Instance `gate-w17a`. Elapsed **20 min 27 s** wall-clock (04:32:41 → 04:53:08 +05:00),
measured as `date +%s` on arrival against `date +%s` at the close, not estimated. Of that,
the gate is **3 min 24 s** of battery plus foundation, frontend and whitespace.

**Gate: `make gate` → exit status `0`**, read from `$?` and never through a pipe.

## Summary

`W15RUN-4` and `W15RUN-5` were **two defects, not one**, and neither lived only where the
dispatch said.

1. **`W17VIEW-1` — four declared fields with no producer.** The omission is in **two**
   readers, not one. `runs/repository.py::_SELECT_STAGE_RESULTS` never selected the
   `started_at`/`finished_at` columns *its own upsert has written since the first
   migration*, so `StageResultRow` had nowhere to carry them and the columns were
   write-only. `bootstrap/adapters.py::_run_status_view` then also never set
   `published_finding_count` or `diagnostic_observation_count`.
2. **`W17VIEW-2` — `now()` is `transaction_timestamp()`.** Unrelated to the above, and in
   SQL rather than in the assembler. `RunAdapter.start_run` creates *and executes* a run
   inside one `self._write(...)`, so `created_at` (a `DEFAULT now()`), every `updated_at`
   and `terminal_at` were three copies of the instant the transaction opened.

Both are repaired, both are guarded by tests shown able to fail, and **no contract change
was needed**: all four fields were already declared by the frozen document.

**The response baseline had pinned the second defect as the expectation.** Records 03–07
carried `"created_at": "{{ts_5}}"` *and* `"terminal_at": "{{ts_5}}"` — one token, because
substitution is by exact value and the two values really were identical to the microsecond.
That is the single most interesting thing this session found, and §5 is about it.

**No frontend handoff is needed.** §6.

## 1. Where the omission actually lives, measured

The dispatch named `_run_status_view` because that is where `W15-RUN` looked. Measured
before changing anything:

```
$ grep -rn "RunStatusView(\|StageStateView(" src/ | grep -v "class "
src/auditmanager/bootstrap/adapters.py:279:    return RunStatusView(
src/auditmanager/bootstrap/adapters.py:293:            StageStateView(
```

So `_run_status_view` **is** the only assembler — that much of the brief holds, and
`adapters.py:266` is the correct line. But the assembler could not have set the stage
timings even if it had tried:

```
$ grep -n "class StageResultRow" -A 8 src/auditmanager/runs/repository.py
173:class StageResultRow:
176-    stage_id: str
177-    stage_version: str
178-    status: str
179-    artifacts: tuple[Mapping[str, Any], ...]
180-    metrics: Mapping[str, Any]
181-    error: Mapping[str, Any] | None          <- and nothing else
```

```
_UPSERT_STAGE_RESULT  ... started_at, finished_at ) VALUES ( ..., :started_at, :finished_at )
_SELECT_STAGE_RESULTS "SELECT stage_id, stage_version, status, artifacts, metrics, error "
```

**The writer writes two columns the reader does not read.** That is the whole of the first
half of `W17VIEW-1`, and it is one file below where the dispatch pointed.

The counts had a producer waiting the whole time: `findings.published_finding_count` and
`findings.diagnostics` already exist and are already exported; `findings/queries.py` keeps
them deliberately apart by name *"so nothing can obtain diagnostics and published findings
from one call and confuse the two counts"*. The repair uses both, separately.

## 2. The envelope, before and after — over a real socket

Not the in-process router. `uvicorn` bound to `127.0.0.1:31790` over this lane's real
PostgreSQL and MinIO, driven by `curl`. Full transcript in
`/root/w17view-logs/envelope-{before,after}.txt`; the script is
`/root/w17view-logs/drive.sh`.

### Before (`ebf06ad`) — `GET /runs/{id}`, 200, bytes as received

```json
{"run_id": "run_01M2RVPNNSXYB6WWS90M9FKSJR", ..., "state": "published",
 "stages": [{"stage_id": "document_context_build", "status": "succeeded", "stage_version": "1.0.0"},
            {"stage_id": "page_geometry_extraction", "status": "succeeded", "stage_version": "1.0.0"},
            {"stage_id": "source_preparation", "status": "succeeded", "stage_version": "1.0.0"},
            {"stage_id": "text_analysis", "status": "succeeded", "stage_version": "1.0.0"}],
 "created_at": "2026-09-17T23:37:19.797308Z",
 "degradation_set": [],
 "terminal_at": "2026-09-17T23:37:19.797308Z"}
```

No `started_at`, no `finished_at`, no `published_finding_count`, no
`diagnostic_observation_count`, and `created_at == terminal_at` **to the microsecond**.
`W15-RUN`'s browser reading reproduced exactly, on a fresh lane, at a different HEAD.

What the rows underneath held at that same moment:

```
$ psql -c "SELECT stage_id, started_at, finished_at FROM stage_result WHERE run_id=..."
source_preparation       | 23:37:19.808917 | 23:37:19.904324    (0.095 s)
page_geometry_extraction | 23:37:19.906589 | 23:37:20.008553    (0.102 s)
document_context_build   | 23:37:20.010079 | 23:37:20.025055    (0.015 s)
text_analysis            | 23:37:20.026068 | 23:37:20.047389    (0.021 s)

$ psql -c "SELECT created_at, updated_at, terminal_at FROM audit_run WHERE run_id=..."
23:37:19.797308 | 23:37:19.797308 | 23:37:19.797308
```

The run genuinely finished at `…20.047389` and reported `…19.797308`. Every layer below the
response had the answer, exactly as the dispatch said.

### After (`aae0209`) — same operation, same lane, same socket

```json
{"run_id": "run_01M2RVSMC0WYJYK7WAVCVJCSXT", ..., "state": "published",
 "stages": [{"stage_id": "document_context_build", "status": "succeeded", "stage_version": "1.0.0",
             "started_at": "2026-09-17T23:38:56.981337Z", "finished_at": "2026-09-17T23:38:56.996658Z"},
            {"stage_id": "page_geometry_extraction", "status": "succeeded", "stage_version": "1.0.0",
             "started_at": "2026-09-17T23:38:56.890712Z", "finished_at": "2026-09-17T23:38:56.980023Z"},
            {"stage_id": "source_preparation", "status": "succeeded", "stage_version": "1.0.0",
             "started_at": "2026-09-17T23:38:56.776064Z", "finished_at": "2026-09-17T23:38:56.888857Z"},
            {"stage_id": "text_analysis", "status": "succeeded", "stage_version": "1.0.0",
             "started_at": "2026-09-17T23:38:56.997622Z", "finished_at": "2026-09-17T23:38:57.015389Z"}],
 "created_at": "2026-09-17T23:38:56.766030Z",
 "degradation_set": [],
 "published_finding_count": 3,
 "diagnostic_observation_count": 0,
 "terminal_at": "2026-09-17T23:38:57.026767Z"}
```

`created_at → terminal_at` is **260.7 ms**, and the span contains all four stage spans.
`POST /runs` (202) carries the identical body — the frozen document renders both operations
with the same `RunStatus`, and the repair is in the shared view, so the 202 a client
actually receives is as rich as the 200 it polls for.

## 3. One defect or two? Two, and here is the evidence

They appear together and are unrelated. The dispatch was right to warn against assuming.

**`W17VIEW-1` is a missing read.** Two SELECT/constructor omissions. Nothing to do with
clocks: the stage timings that were missing are computed in **Python**, by the executor
(`runs/executor.py:330`), and were always correct in the rows — which is *itself* the proof
that the two defects are different. If one mechanism had produced both, the stage rows would
have carried the collapsed value too. They did not: they carried four distinct, real spans
while the run row carried one instant three times.

**`W17VIEW-2` is a PostgreSQL semantic.** Confirmed directly rather than argued:

```
$ psql -c "SELECT now()=transaction_timestamp() AS now_is_txn_start, now()<>clock_timestamp();"
t|t
```

`_ADVANCE` and `_TERMINATE` both used `now()`. `audit_run.created_at` and `updated_at` are
`DEFAULT now()`. A run is created and executed in one transaction, so all three names
resolved to one value however long the run took.

**The repair is `statement_timestamp()`**, not `clock_timestamp()`. `statement_timestamp()`
advances between statements of one transaction — which is what was wanted — *and is constant
within* a statement, so `_TERMINATE` stamps `terminal_at` and `updated_at` with one identical
value rather than two `clock_timestamp()` readings a microsecond apart.

**`created_at`'s `DEFAULT now()` is left alone, deliberately.** The INSERT is the first
statement of the transaction, so the transaction timestamp *is* when the run was created —
measured at 11 ms before the first stage started. It is the values that must move on *later*
statements that were wrong. Changing the column default would have been a migration for no
defect.

**`updated_at` is not in the contract.** `W15RUN-5` names three timestamps; only two are
API-visible. `RunStatus` declares `created_at` and `terminal_at` and no `updated_at`, so the
third was only ever observable in the database. It was collapsed by the same mechanism and is
repaired by the same `_ADVANCE` change.

### Same class, elsewhere, not repaired

`grep -rn "now()" src/ --include=*.py` finds four more `updated_at = now()` writes —
`ingest/commands.py:86,90`, `storage/blob_repository.py:62`,
`documents/repository.py:97`. Each has the same transaction-timestamp property. **I did not
change them**: none is on a surface where the collapse is observable to a client, none is in
a tree I proved this omission lives in, and a blind sweep would be a change without a defect
behind it. Naming them here so the next session does not rediscover the mechanism from
scratch.

## 4. Which test reddened when each repair was reverted

Via `make mutation-copy MUT=/root/w17view-mut` (src-only form:
`.venv/bin/pytest <suite> -o pythonpath=/root/w17view-mut/src`). **The probe worked exactly
as documented** — nothing to report against it. Baselined green on the unmutated copy first:
7 passed.

| probe | mutation, in the copy | what reddened |
|---|---|---|
| **A** | `_SELECT_STAGE_RESULTS` → `NULL AS started_at, NULL AS finished_at` | `test_every_stage_reports_when_it_started_and_when_it_finished`, `test_the_stage_timings_are_per_stage_and_not_one_repeated_instant`, `test_the_reported_span_contains_the_work_the_stages_report` — **3 failed, 4 passed** |
| **B** | the two `*_count=` lines deleted from `_run_status_view` | `test_a_published_run_reports_how_many_findings_it_published`, `test_a_published_run_reports_its_diagnostic_observation_count` — **2 failed, 5 passed** |
| **C** | `statement_timestamp()` → `now()` in `_ADVANCE` and `_TERMINATE` | `test_a_run_that_did_work_reports_a_duration_greater_than_zero`, `test_the_reported_span_contains_the_work_the_stages_report` — **2 failed, 5 passed** |

The two defects' test classes are separable: probe **C** reddens only
`TestTheRunDoesNotBeginAndEndAtTheSameInstant`, probe **B** only
`TestTheFourDeclaredFieldsHaveAProducer`. `test_the_reported_span_contains_the_work_the_stages_report`
appears twice on purpose — it ties the two aggregates together, and cannot hold if either
side is missing.

Two more, on the characterization guards added in §5, planted into the copy's records:

| probe | mutation | what reddened |
|---|---|---|
| **D** | record 06's `terminal_at` set back to its `created_at` | `test_the_five_run_status_records_no_longer_pin_one_instant_for_the_whole_run` |
| **E** | an unnamed `exception` block added to record 08 | `test_exactly_the_named_records_are_marked_as_permitted_exceptions` |

The mutation copy was restored after each probe and the worktree confirmed clean
(`git status --porcelain` empty) before the gate.

## 5. The characterization records — five were affected, and one had frozen the defect

**The dispatch's path is slightly off**: there are 5 entries under
`tests/characterization/w13_baseline/`; the **33 records** are one level down, in
`records/`. Of those 33, **five** exercise the operations changed — every case that renders
a `RunStatus` body:

```
03-startRun.success   04-startRun.replay   05-startRun.replay_with_normalised_property
06-getRunStatus.success   07-getRunStatus.correlation_supplied
```

So a `permitted_change` **did** happen, and record 31's form is followed exactly: each of
the five now carries an `exception` block naming `D-19`, citing `aae0209` and its subject,
dated, with a `permitted_change` describing the whole of the move and the standard
`everything_else` clause.

### What the baseline had been protecting

Record 06, as committed at `ebf06ad`:

```
"created_at": "{{ts_5}}",  ...  "terminal_at": "{{ts_5}}"
```

**One token for two fields.** Substitution in this corpus is by exact value, so two fields
earn one token exactly when their values are identical — and they were, to the microsecond,
in all five records. `W15RUN-5` was legible in this directory for five waves before a
browser found it. A safety net that reproduces a defect byte for byte is protecting it.

A re-capture alone would have erased that evidence with nobody having to say it had been
there, so it is asserted rather than left to a diff:
`test_the_five_run_status_records_no_longer_pin_one_instant_for_the_whole_run` reads the five
records back and requires `created_at != terminal_at` and both stage timing fields present.
Shown able to fail (probe **D**).

### The boundary I did *not* stop at, and why — the integrator should check this

Following record 31's form exactly is **not sufficient**, and the dispatch could not have
known this. `test_exactly_one_record_is_marked_as_the_permitted_exception` asserts

```python
assert list(exceptions) == ["31-streamDocumentVersionContent.storage_credential_refused"]
```

so marking a second case *fails the countability guard*. There is no way to record a second
permitted change without changing that test. I changed it:

- it becomes `test_exactly_the_named_records_are_marked_as_permitted_exceptions`, driven by
  a **literal** `PERMITTED_EXCEPTIONS` map of case → debt (six entries), never derived from
  the records it checks;
- it now additionally requires every marked record to carry a `permitted_change` and a
  `decided_by`, which the one-case version did not;
- the README paragraph changed **in the same commit**, which is the precedent this corpus
  already set for `test_the_baseline_records_the_authenticated_era` when `W13-API` made the
  journey authenticate.

**The count changed; the rule did not.** But I want this looked at, because it is the guard
the README calls *"the assertion that makes the exception countable"* and *"a safety net
with an unnamed exception is one somebody talks their way past at the end of a long wave"*.
The D-7 exception carries an **owner ruling** (`R-3`); mine carries only `D-19` and this
wave's dispatch. I judged that acceptable because **this is a repair inside a declared
contract, not a contract change** (§7), which is a different kind of act from the one `R-3`
authorised — but the judgement is mine and it is the one thing in this session I would most
like overruled if it is wrong. The alternative was to leave the gate red.

### The re-capture was checked for vacuity

`capture.py` rewrites all 33 files, and the README is explicit that re-running it against a
changed implementation is the one thing that can make this directory worthless. Measured:

```
$ git diff --stat -- tests/characterization/w13_baseline/records/
 5 files changed, 110 insertions(+), 20 deletions(-)
```

**28 of 33 came back byte-identical**; exactly the five above moved. A repair that had
disturbed a sixth would have shown here.

### A defect the re-capture itself surfaced

The first re-capture wrote records containing

```
"finished_at": "2026-09-17T23:44:21.167423Z"
```

— an **absolute wall-clock literal**, in a record that must reproduce byte for byte. It
would have gone red on the very next run. `TIMESTAMP_FIELDS` in `journey.py` names
tokenisable timestamp fields one at a time and listed `started_at` but not `finished_at`,
because before `aae0209` no response carried one. That is the mechanism working as designed
— a new timestamp property on the surface *has* to be added deliberately — and `finished_at`
is now the entry it was waiting for. Caught because the diff was read rather than the suite
merely re-run.

## 6. The contract, and the frontend — no boundary reached on either

**Nothing I added is undeclared, so this is not a contract change.** Evidence:

```
$ python -c "import json; s=json.load(open('contracts/api/v1/openapi.json'))['components']['schemas']; ..."
RunStatus declares:  ['published_finding_count', 'diagnostic_observation_count', 'created_at', 'terminal_at']
StageState declares: ['started_at', 'finished_at']
additionalProperties: False False
```

All four names were already in the frozen document, already carried by `RunStatusView` /
`StageStateView`, and already serialised by `run_status_body` / `stage_state_body` behind an
`is not None` guard. `additionalProperties: false` is satisfied because every added name is
one the document declares. **Populating a declared field is not a reseal**, and no reseal is
requested. `git diff --stat ee44b24..HEAD -- contracts/ web/ infra/ Makefile db/` is empty.

**No frontend handoff is needed** — checked rather than assumed, and this is the happy
answer. `web/` already consumes every field:

```
web/src/entities/audit-run/model/run-presentation.ts:137  status.published_finding_count ?? null
web/src/entities/audit-run/model/run-presentation.ts:198  startedAt: stage?.started_at ?? null
web/src/widgets/run-progress/ui/run-progress.tsx:71       findingCount === null ? <em>not reported</em> : ...
```

The `?? null` and the `<em>not reported</em>` are the browser rendering *absence*. The API
was the only thing missing. A user sees the repair with no change under `web/**`, which
stays `W16-WEB`'s.

**One thing the frontend still cannot show.** `run-progress.tsx:182` renders `terminal_at`
as an instant; nothing anywhere computes `terminal_at - created_at`. Before this session that
would have been a zero, so the absence cost nothing. Now the duration is real and nobody
displays it. **That is a `W16-WEB` handoff, and I am reporting it rather than reaching for
it** — it is a display of data the API now provides, not a repair this wave owes.

## 7. What is false, or stale, in the dispatch

1. **`docs/program/reviews/W15-RUN.md` does not exist on `origin/dev`.** Step 1 says to read
   it first. It is on `planning/prototype-roadmap` and `agent/w15-run` only, and a session
   that provisions from `origin/dev` as instructed in step 0 cannot open it. Read via
   `git show planning/prototype-roadmap:...`.
2. **`DEBT_REGISTER.md` on `origin/dev` has no `D-19`.** Same cause: the dev copy's rows stop
   before it, and D-19/D-20/D-21 exist only on the planning branch. `grep -rn "D-19" docs/`
   in a fresh worktree returns only two unrelated `OD-19` hits, which is a good way to be
   sent down the wrong path.
3. **"the 33 records under `tests/characterization/w13_baseline/`"** — that directory holds
   5 entries; the 33 records are in `records/` beneath it.
4. **"`_run_status_view` … simply does not populate them"** is half the defect. Two of the
   four fields could not have been populated there at all until `repository.py` read them.
   The dispatch's own instruction to measure first is what caught it.
5. **The `permitted_change` instruction is incomplete**, not false: following record 31's
   form exactly also requires changing the countability test and the README, which the
   dispatch does not mention and which is the most consequential thing I did. §5.
6. **`adapters.py:266` is correct** — the line the dispatcher flagged as unverified. So is
   `tests/integration/foundation/conftest.py:542` (`checkout_is_unchanged`).
7. **`make mutation-copy MUT=…` works exactly as described**, including the tests-only form.
   Nothing to report against it.
8. **Disk was fine**: `9.9 GB` available at 92% on arrival, above the ~5 GB line; `8.8 GB` at
   93% after the gate. Nothing in this session was a disk symptom.

## 8. The gate

```
$ make gate > /root/w17view-logs/gate.log 2>&1; echo "GATE_EXIT=$?"
GATE_EXIT=0
```

Read from `$?` on the `make` invocation itself — never through `| tail`, which returns
`tail`'s status.

```
1742 passed, 5 skipped, 1 warning, 168 subtests passed in 204.29s (0:03:24)
Test Files  39 passed (39)    Tests  498 passed (498)          [frontend]
GATE OK: battery, foundation, frontend and whitespace all pass
```

Run on a clean tree (`git status --porcelain` empty) with the lane cleared first: the
`uvicorn` from §2 was killed and no `pytest` was running, because `W16-ERR` voided its own
gate today by leaving one on its own database.

## 9. Commits

| | |
|---|---|
| `ee44b24` | `docs(w17-view)`: the review, opened before the first edit |
| `aae0209` | `fix(runs)`: both repairs, with the before/after measured over a socket |
| `7ae4386` | `test(runs)`: the guards, one class per defect |
| `ccee81f` | `test(baseline)`: the five records moved, with the citation and the README |

No tag, no push to `main`, no merge. Branch `agent/w17-view`, worktree `/root/w17view`.

## 10. Reproducing this

```
git worktree add /root/w17view -b agent/w17-view origin/dev
cd /root/w17view && cp .env.example .env     # instance gate-w17a, ports 55790/59390/59391
npm --prefix web ci && make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12
make up && make migrate

# the envelope, over a real socket rather than the in-process router
set -a && . ./.env && set +a
PYTHONPATH=$PWD/src AUDITMANAGER_PROVIDER_MODE=recorded AUDITMANAGER_API_TOKEN=w17-view-local-token \
  ./.venv/bin/python -m uvicorn --factory auditmanager.api.app:create_asgi_app --port 31790 &
/root/w17view-logs/drive.sh          # POST /projects, POST .../documents, POST /runs, GET /runs/{id}

# the fail-probes
make mutation-copy MUT=/root/w17view-mut
./.venv/bin/pytest tests/integration/composition/test_a_published_run_reports_itself.py \
  -o pythonpath=/root/w17view-mut/src          # then mutate /root/w17view-mut/src and re-run
```

`drive.sh` lives outside the worktree for `W12-WEB`'s reason; its output is quoted in §2
in full, so a reader checks the evidence here rather than only in a log.

## 11. Left running

`gate-w17a` — PostgreSQL on **55790**, MinIO on **59390/59391**, database `audit_w17a`,
bucket `auditmanager-gate-w17a`. Holds both journeys from §2: the `before` run
`run_01M2RVPNNSXYB6WWS90M9FKSJR` with its collapsed timestamps, and the `after` run
`run_01M2RVSMC0WYJYK7WAVCVJCSXT` with its real 260.7 ms span. Left up so both can be
re-measured. The `uvicorn` process is **not** left running.
