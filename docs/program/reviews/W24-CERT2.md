# `W24-CERT2` — `PA-01` re-certified at `16d3503`

**Session** `W24-CERT2`. **Base** `16d3503` (`origin/dev` on arrival). **Branch**
`agent/w24-cert2`. **Worktree** `/root/w24cert2`. **Lane** `gate-w24a`.

This file is opened before the first measurement, per the dispatch, and filled as each
verdict is produced. Nothing below is written before the command that produced it has run.

## 0. Status

All ten criteria driven. **Eight hold, two of them with a named exception; two cannot be
established; none was found to fail.** The record is
`artifacts/checkpoints/PA-01/certification-16d3503.json`.

## 1. The criteria, quoted from the file

`docs/program/ALPHA_ROADMAP.md` §5, lines 307–331, quoted rather than paraphrased. The
preamble matters as much as the ten items, because it is where *"on the server"* and *"from
a clean clone"* are said:

> Executed **on the server**, from a clean clone, by an independent session, and recorded in
> `artifacts/checkpoints/PA-01/report.json` with the commit, the image digests and the
> migration head:
>
> 1. `deploy.sh` brings the stack up from a clean clone on a machine that has never run it,
>    and the schema the running app serves conforms to the frozen
>    `contracts/api/v1/openapi.json` — the same check the gate runs, re-run against the
>    deployed process rather than against a build artifact;
> 2. the browser reaches the app over TLS, and a request carrying no token is refused with
>    `authentication_required` **from the application**, not by the proxy — shown for an
>    operation of each kind, so the dependency is proved to be in front of all twelve rather
>    than in front of the one that was tried;
> 3. a project is created and a real AR PDF is uploaded through the browser, producing an
>    immutable version and a verified private object;
> 4. a live `text_analysis` run completes, with its provider mode and cost visible, and the
>    UI distinguishes running, published, partial and failed — criterion 4's UI clause,
>    which the `e6eae1e` certification explicitly did not establish;
> 5. a finding opens at its exact quotation beside the page it came from;
> 6. an accept, a reject and a later comment are recorded, and the history shows all three;
> 7. the CSV downloads through the browser with its seventeen columns, its BOM and its CRLF
>    intact, and resolves back to the same version and run;
> 8. the server is rebooted and every canonical row, object and decision survives;
> 9. each of the five refusals answers with its own typed code **through HTTP**, and a
>    provider outage fails the run rather than publishing it;
> 10. `reset.sh` dumps, wipes and re-initialises; the app comes back empty and working; the
>     dump restores the wiped state.

**The frozen inputs, checked rather than inherited.** `contracts/api/v1/openapi.json` —
12 paths, 15 operations, 46 schemas, read out of the document itself.
`contracts/domain/v1/error-codes.json` — 21 codes, `frozen: false`,
`status: draft_candidate`. Both as the dispatch states them.

## 2. Base gate

`make gate FOUNDATION_PYTHON=/usr/bin/python3.12` on the committed, clean tree at
`2126598` (this review's opening commit; `16d3503` plus this file), lane `gate-w24a`,
`POSTGRES_PORT=55940`, `S3_API_PORT=59540`/`59541`, `POSTGRES_DB=audit_w24a`, bucket
`auditmanager-gate-w24a`. Exit code from `$?` after a redirect, never through `| tail`.

```
foundation  35 passed in 28.97s
battery     1909 passed, 5 skipped, 1 warning, 168 subtests passed in 236.63s
frontend    Test Files 48 passed (48)   Tests 706 passed (706)
GATE OK: battery, foundation, frontend and whitespace all pass
GATE_EXIT=0
```

**Identical to the dispatch's figures in every number.** Provisioning was
`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` (exit 0) and `npm --prefix web ci`
(exit 0, 184 packages); without the second the gate exits 2 at the frontend.

## 3. The stack driven

**Not `31500`, and the probe the dispatch asked for was run first.**

```
$ ./infra/deploy/verify-deployed.sh --env-file <the alpha env> --repo /root/w24cert2
  src/                141 files, identical      contracts/     34 files, identical
  db/                   9 files, identical      fixtures/recorded/  7 files, identical
  docs/program/P02_LOCK.json  1 file, identical infra/deploy/serve.py 1 file, identical
  web/                218 files, identical
verify-deployed.sh: the deployed stack IS this tree (2126598).
VERIFY_EXIT=0
```

**The dispatch's claim about `31500` is true at this tip, and it is verified rather than
inherited.** It is still not the stack anything below was driven on, because criteria 8 and
10 restart and wipe what they measure and `31500` is shared programme state.

What was driven instead is **this session's own alpha instance**, `auditmanager-w24cert2` on
`127.0.0.1:31540`, brought up by `infra/deploy/deploy.sh` out of `/root/w24clone` — a fresh
`git clone` checked out at `16d3503`, with no `.venv`, no `web/node_modules` and no
`alpha.env`. `verify-deployed.sh` says the running images **are** that clone. Every criterion
below went through that stack's **nginx**, which is the `T-2` single origin `W21-CERT` could
not put in its own path.

### 3a. The clean-clone drive, criterion 1's first clause

Two refusals before any `docker` call, both from a clone that has exactly what a clone has:

```
$ ./infra/deploy/deploy.sh                                   # no environment at all
deploy.sh: REFUSED: the deployment environment /root/w24clone/infra/deploy/env/alpha.env
           is missing or unreadable.
EXIT=3
$ cp infra/deploy/env/alpha.env.example infra/deploy/env/alpha.env && chmod 600 …
$ ./infra/deploy/deploy.sh                                   # the example, unedited
deploy.sh: REFUSED: POSTGRES_PASSWORD is still the value shipped in alpha.env.example.
EXIT=3
```

Then with an environment this session wrote, **outside the clone**:

```
11:06:18 +05  →  11:07:37 +05      79 s,  0 of the build's steps CACHED
  postgres running/healthy   s3 running/healthy   api running/healthy
  web running/healthy        proxy running/none
  check-db: head expected 0005_truncated_call_status / current 0005_truncated_call_status
  200 on http://127.0.0.1:31540/api/v1/openapi.json
  frozen ops : 15    served ops : 15    differences: 0
DEPLOY_EXIT=0
```

### 3b. `D-36`, re-measured by running it twice

| | run 1 | run 2 |
|---|---|---|
| build steps `CACHED` | 0 of 24 | **24 of 24** |
| `postgres` / `s3` / `proxy` container id | `7d57a161fa23` / `e20b53260332` / `a235ae82b485` | **unchanged** |
| `api` container id | `01af503a3fc5` | `1cf4b89a38b4` |
| `web` container id | `0e6bac92d29f` | `b5d53bdb7d5f` |
| both named volumes created | `2026-09-20T11:07:17+05:00` | **unchanged** |

`D-36` stands, measured on this tree by a session that did not write the row: no layer
rebuilds, no data is touched, and `api` and `web` are recreated anyway.

### 3c. What running it a third time cost, and it is worth recording

The third `deploy.sh` run **exited 5**, and the cause was the host rather than the tree: the
two image builds had taken `/` from 8.9 GB free to **0 bytes, 100 %**, at 06:10:27Z. MinIO
refused the bucket policy write on its minimum-free-drive threshold, so `s3-init` exited 1,
so `api` never started, so nginx could not resolve the `api` upstream.

**This session's own gate lane paid for it**: `gate-w24a-postgres-1` died in WAL redo with
*"Check free disk space"* and stayed down for sixteen minutes. `docker builder prune -af`
returned 8.2 GB and `make up` brought the lane back healthy. **No other lane lost a service**
— all three alpha stacks and both other lanes stayed up and `31500` kept answering 200 — but
that is luck and not design, and a clean-clone deploy on this host needs about **8 GB of
build-cache headroom** it does not have. That is a fact about the `R-1` host too.

## 4. The ten verdicts

| | criterion | verdict | what produced it |
|---|---|---|---|
| 1 | deploy from a clean clone; served schema conforms | **cannot be established** | the drive in §3a; and `openapi_conformance.surface()/differences()` over the frozen document and the served one — **0 differences**, planted `operationId` → 1 |
| 2 | TLS; no token refused **by the application** | **cannot be established** | one `listen 8080;`; and 15/15 operations → `401 authentication_required` with **no** credential *and* with a **wrong** bearer |
| 3 | project, upload, immutable version, private object | **holds** | a real browser; `403` on anonymous LIST **and** GET against the bucket itself |
| 4 | live run, cost visible, four states distinguished | **holds** *(exception removed)* | three journeys: `published`, **`partial`**, `failed` — five distinct badge states in all |
| 5 | a finding opens at its exact quotation beside its page | **holds** *(exception removed)* | the caption, and `pdfminer` page by page |
| 6 | accept, reject, a later comment, history shows all three | **holds** | three clicks, three `201`s, the History list |
| 7 | CSV through the browser, resolving back | **holds** | 3924 bytes, BOM, 6 CRLF / 0 bare LF, 17 columns, 5 rows over 3 findings |
| 8 | the server is rebooted and everything survives | **holds, named exception** | a 60-line census, all five containers restarted by id, `diff` exits 0 |
| 9 | five typed refusals through HTTP; an outage fails the run | **holds** | five distinct `constraint`s, all `422`; `failed / dependency_unavailable` |
| 10 | `reset.sh` dumps, wipes, re-initialises; the dump restores | **holds, named exception** | the full cycle, and a re-upload of the same bytes answering **201** |

### Criterion 1 — the reason changed, the verdict did not

`ALPHA_ROADMAP.md:313` asks for two things. The second — *"the schema the running app serves
conforms to the frozen `contracts/api/v1/openapi.json`"* — **holds**, driven twice: by
`deploy.sh`'s own twelfth guard (`frozen ops 15 / served ops 15 / differences 0`), and
independently by this session against `http://127.0.0.1:31540/api/v1/openapi.json` with the
gate's own comparison engine, with the comparison shown able to fail.

The first — *"brings the stack up from a clean clone **on a machine that has never run
it**"* — is where it stops. The clone had never run it; the instance had never existed; the
two images had never been built; **the machine has.** `W23-DEPLOY` ran this script on this
host yesterday, three alpha stacks live here, and fetch/switch/rollback are not in the script
and cannot be, because all three are claims about a server carrying a *previous version*.
`R-1`'s host — a name, a certificate, who holds root — does not exist; `ALPHA_ROADMAP.md` §9
still lists it as owed.

**`W21-CERT`'s sentence for this row was *"there is nothing to run"*. That is no longer true.
The row's reason is now *"there is nothing left to run it on"*, and it is the owner's.**

### Criterion 2 — the second clause, wider than the criterion asks

15 of 15 declared operations answer `401` with `error_code: authentication_required`, to a
request with **no** credential and to one with a **wrong** bearer. The criterion says
*"twelve"*; the frozen document declares **12 paths and 15 operations** over them, and this
drove all fifteen.

**Proved to come from the application**, which is the clause's actual claim, by asking the
`api` container with nginx entirely out of the path:

```
http://127.0.0.1:8000/projects   401  {"contract_version": "1.0.0-draft.1",
                                        "error_code": "authentication_required", …}
http://127.0.0.1:8001/healthz    200  {"status": "ok"}        <- T-3, no credential
```

TLS is still absent and still for `R-1`'s reason. **"Cannot be established" is not a synonym
for "holds": a reader told criterion 2 passed would conclude the alpha speaks HTTPS.**

### Criterion 4 — `partial`, in a browser, on the deployed path

`W21-CERT` named an exception: `partial` was not inducible. `W23-PARTIAL` proved that was a
**defect** — `proxy.py` mapped OpenAI's `finish_reason: "length"` onto a *call-status* word,
so `ModelResponse.truncated` never saw it and a cut-short analysis published as a complete
one — repaired it, and could not open a browser because `web/` was not its to touch. So the
UI clause was an inference from a unit test. **It is now an observation.**

```
[data-run-state]   queued 160 ms  →  running 317 ms  →  PARTIAL 2334 ms
run_01M2YQGB7529ZCKX2FXJ517DDV   partial   live   degradation_set ["text_analysis"]
  text_analysis partial / partial_result_not_publishable, the other three succeeded
  published_finding_count 1   cost_micros 41200   basis measured
model_call, read from the database:  truncated | live | (no error_code) | 16000 | measured
```

The provider was a local stub of the proxy's **own documented contract**, running as its own
container **on the stack's network**, answering `finish_reason: "length"`. Nothing about the
application was stubbed, and the stub's log carries the application's real call —
`Authorization` present, `X-Idempotency-Key 728e6342…`, `model anthropic/claude-opus-5`,
`max_tokens 16000`, which is `prompt.py`'s `MAX_OUTPUT_TOKENS` literal.

The live half of the criterion is `run_01M2YQ489FF8H5R9JP971E5XFW` through the operated proxy:
`published`, `provider_mode live`, 3 findings, `cost_micros 37225`, `cost_basis measured`,
`model_call_count 1`, and the screen printing all of it.

**`D-35` is not decided here.** Whether the criterion requires `partial` from inside a
*user's* journey is the owner's one yes/no. Nothing in the product journey still chooses a
model, a prompt or an output ceiling.

### Criterion 5 — the caption, and an extractor the application does not use

```
1.3. Степень огнестойкости здания — II.
page 2, characters 707–746 of the whole document, not of page 2
```

and after clicking the second declared page, `data-active-page` 6, the same document blob at
`#page=6`, and `page 6, characters 2618–2658 of the whole document, not of page 6`.
`W21CERT-2` is closed — that caption used to read `page 2, chars 707–746`.

`pdfminer.high_level.extract_text`, page by page: page 2 is 557 characters and carries the
first quotation at page-local `201..240`; page 6 is 484 and carries the second at `180..220`.
Both `True`. Control: neither is on page 1.

### Criterion 8 — a census, not a screen

Sixty lines through PostgreSQL and MinIO rather than through the application: every base
table's row count, every run, every version with state/digest/size/pages, every decision
event with verdict and comment, the blob rows, and every object with its full user metadata.
Then **all five containers restarted by container id**, and the census retaken. `diff` exits
**0**. The proxy answered 200 afterwards with no reload, because a restart keeps the network
aliases a *recreate* replaces.

Every screen then loads cold in its own fresh browser process — `projects`, `project`,
`version`, `run`, `review` — 200 each, with 1/1/2/1/5 `/bff/v1` calls, all 200. The run still
reads `published · live · Took 11.0 s`; the review still shows `rejected`.

**The exception is unchanged and is not the software's:** this is a container restart, not a
host reboot, and the host carries three alpha stacks and other lanes' services.

*Separately, by accident:* a run whose `api` process was **replaced mid-flight** came back
`failed / analysis_failed` with no `stage_result` rows — `W20-EXEC`'s startup reconciler
closed it rather than stranding it in `running`. No run on this instance was left
non-terminal.

### Criterion 10 — the cycle, and a smaller exception in the safe direction

Four guards, each `exit 3` read from `$?` after a redirect: no destructive flag; a foreign
database (this lane's own gate database typed against the alpha configuration — `T-5`'s
stale-environment case exactly); a foreign bucket; `--dryrun`.

```
--dry-run                 exit 0   total: 104 rows in 17 tables, 23 objects listed exactly
--yes-destroy-everything  exit 0   dump verified: database.dump readable, 23/23 objects
                                   schema dropped, 5 migrations re-run, bucket re-initialised private
  same api process:  GET /projects -> {items: []} ; wiped content -> 404
                     POST /projects -> 201 ; upload -> 201, 58978 bytes, same digest
--restore <the relative path the script prints>   exit 0   restored 23 objects
  census before the wipe  ==  census after the restore     diff exits 0
  content -> 200, 58978 bytes, sha256 6d53674f…bd31f
  RE-UPLOAD OF THOSE SAME BYTES -> 201, not 409
```

**`W21CERT-1` is closed.** Every per-table figure in the rehearsal matches `count(*)`
exactly, including on the freshly-written database that used to make `n_live_tup` print
`(0 rows)` over live data.

**`W24CERT2-2` replaces it, and is much smaller.** `finding_current_verdict` is a **VIEW**
over `expert_decision_event`, and it is listed under *"tables that would be dropped with
schema public"* with `(4 rows)` beside it. So `total: 104 rows in 17 tables` is 100 rows in
16 base tables plus a 4-row projection of rows already counted. `information_schema` says so:
16 `BASE TABLE`, 1 `VIEW`. The direction is the safe one — it **over**-reports, the opposite
of `W21CERT-1` — and the wipe is unaffected, but the total is the number an operator is asked
to believe before a destructive act under `R-4`.

## 5. Diff against `certification-0f9989a.json`

### Verdicts that changed

| criterion | from | to | the measurement that moved it |
|---|---|---|---|
| **4** | holds *with a named exception*: `partial` not inducible | **holds** | the badge going `queued → running → partial` at 2334 ms on the deployed stack, with `model_call.status = truncated`, `output_tokens 16000`, `error_code` NULL |
| **5** | holds *with a named exception* `W21CERT-2` | **holds** | the rendered caption now naming its own coordinate system, confirmed by `pdfminer` at page-local `201..240` and `180..220` |
| **10** | holds *with* `W21CERT-1` (rehearsal **under**-reports) | holds *with* `W24CERT2-2` (rehearsal **over**-reports by a view) | per-table figures now exact against `count(*)`; the new row found by summing them against `information_schema` |

### Verdicts that did not change, but whose reason did

| criterion | verdict both times | what moved |
|---|---|---|
| **1** | cannot be established | from *"`deploy.sh` does not exist"* to *"it exists, it was run from a clean clone at this commit, it exits 0 in 79 s, and `verify-deployed.sh` certifies the result as that clone — what is missing is a machine that has never run it and a previous version to roll back to"* |
| **2** | cannot be established | nothing moved in the verdict; the second clause is now additionally proved to come **from the application**, with nginx out of the path |
| **8** | holds, named exception | same exception; what is new is that the restart was of a stack `deploy.sh` built, through the `T-2` proxy |

### What `W21-CERT` could not drive and this session could

* the **`T-2` single origin and the 300 s proxy read timeout** — `W21-CERT`'s dispatch
  forbade building images, so it served the application itself with `serve.py` and
  `next start` and could certify neither;
* **`partial`**, its own named exception on criterion 4;
* the **caption repair** on criterion 5, which did not exist then;
* an **exact wipe rehearsal** on criterion 10, which did not exist then.

### What is unchanged, and is the whole reason `PA-01` is not certifiable

Criteria 1 and 2 both stop at `R-1`'s host: a name, a certificate, who holds root, and a
machine with no history of this stack on it. §9 of the roadmap still lists those as owed by
the owner, not by any session.

## 6. Proposed register rows

**Proposed, not written.** `DEBT_REGISTER.md` is the integrator's file and a forbidden
hotspot for this task.

### `W24CERT2-1` — when `up` fails, the script's own diagnosis points at the wrong file

Measured at `16d3503`, `/root/w24cert2-logs/deploy-run3-proxy.log`. `s3-init` exited 1 (the
host was out of disk), so `api` never started. `deploy.sh` printed

```
deploy.sh: `compose up -d` exited 1; the guards below decide.
-- reloading the proxy --
nginx: [emerg] host not found in upstream "api" …
reload-proxy.sh: the proxy configuration is not valid.
  Nothing was reloaded and the old workers are still serving. Fix proxy/nginx.conf;
```

and exited **5**. `nginx.conf` was not the problem and needed no fixing; the `services-healthy`
guard, which would have named `s3-init` and `api`, is **after** the reload and never ran. The
script refused rather than reporting success, which is the important half — but *"the guards
below decide"* is not what happened, and the operator is sent to edit a file that is fine.

*Check:* stop any one service of a running instance, then run
`infra/deploy/deploy.sh --env-file <env>` and read `$?` and the last ten lines.

### `W24CERT2-2` — the wipe rehearsal's total counts a view

Measured at `16d3503`, `/root/w24cert2-logs/reset-dryrun.log`. `total: 104 rows in 17 tables`
over a database holding 100 rows in 16 base tables; the seventeenth name,
`finding_current_verdict`, is a `VIEW` over `expert_decision_event` whose 4 rows are a
projection of rows already counted. Over-reporting, so safe; but this is the screen `R-4`
asks an operator to believe.

*Check:*
```
infra/deploy/reset.sh --env-file <env> --database <db> --bucket <bucket> --dry-run | tail -3
psql -qtA -c "select table_type, count(*) from information_schema.tables
              where table_schema='public' group by 1"
```

### Not a defect, recorded so the next session does not re-find it

* every page load produces one console `404` — `/favicon.ico` and `/apple-touch-icon.png` are
  not served. Cosmetic, and it is the only non-2xx anything in 33 `/bff/v1` calls;
* a provider whose packets are **dropped** rather than refused does not fail fast: the
  adapter waits its full `_TIMEOUT_SECONDS = 200`. That is the documented timeout doing its
  job, but it is why the first truncation attempt looked like a hang.

## 7. False premises in the dispatch

**None material**, which is worth saying plainly after twenty-two were found this week. Every
figure the dispatch carried was checked and held: the base gate to the number, `12 paths / 15
operations / 46 schemas`, `21` error codes with `frozen: false` and `status:
draft_candidate`, `deploy.sh`'s existence and its clean-clone proof, `verify-deployed.sh`
exiting 0 on `31500`, and both `W22` repairs. The instruction to quote the criteria from the
file is the reason criterion 1's second clause here is about the **API** schema and not the
database schema.

**One thing it understates.** Driving `partial` needs the stub reachable *from the api
container*, and on this host a container cannot reach a listener on the host gateway — the
packets are dropped, not refused, so the first attempt did not fail fast, it hung for 200 s.
The stub has to run on the stack's own network. (`D-37`'s lesson applied: the script was
`docker cp`'d in rather than bind-mounted.)

## 8. Limits, spend and elapsed

**Limits.** No host reboot (criterion 8's exception, and other lanes' stacks are the reason).
No TLS and no machine that has never run this (criteria 1 and 2, `R-1`). `partial` was not
provoked from inside a *user's* journey and that question is deliberately left where it
belongs, in `D-35`. No real client documents: the fixtures are synthetic, as `R-4` requires
until the pilot.

**Spend.** One paid provider call, on the certified journey: `cost_micros 37225` =
**USD 0.037225**, `cost_basis measured`, against `OD-03`'s USD 1.00 ceiling. Every other run
reached either nothing or a local stub.

**Nothing was repaired.** `src/`, `web/`, `contracts/`, `infra/`, `tests/`, the `Makefile`,
`DEBT_REGISTER.md` and `CURRENT_STATE.md` are untouched; this branch contains exactly two
files, this one and `artifacts/checkpoints/PA-01/certification-16d3503.json`. No tag and no
checkpoint was created.
