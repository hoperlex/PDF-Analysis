# W46-JUDGE-A — the merged tip `130200d`, sub-stage A of wave 46

**Judge:** `W46-JUDGE-A` (relaunch; the first run died on a host restart before it committed
anything) · **lane:** `gate-w46j` (PostgreSQL `127.0.0.1:56390`, S3 `59990`/`59991`) ·
**worktree:** `/root/w46j` · **branch:** `agent/w46-judge` · **tree judged:** `130200d`.

This file is committed as it is written. A section marked *in progress* is not a conclusion.

## 0. Provisioning

```
make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12   -> bootstrap OK
.venv/bin/python -c "import boto3"                     -> boto3 ok
npm --prefix web ci                                    -> added 184 packages
```

## 1. Does the merged tree gate? — **No.**

```
cd /root/w46j && make gate > /root/w46j-gate.log 2>&1      # the canonical command, literally
grep -c 'GATE OK' /root/w46j-gate.log                        -> 0
```

Run on `5f21ae4` (= `130200d` plus this file only; `docs/program/reviews/` is outside every
prose guard's named scope), 06:28:01Z–06:43:44Z. The log ends:

```
7 failed, 2493 passed, 5 skipped, 4 warnings, 169 subtests passed in 863.10s (0:14:23)
GATE: the canonical battery failed with pytest exit status 1.
make: *** [Makefile:1026: gate] Error 1
```

Foundation **35 passed**. The harness reported my wrapper's `exit code 0` for this run; the
wrapper's own `$?` file says `2` and the log has no `GATE OK` line. §4.6 fired a sixth time.
Host load average was 32–95 on 8 cores during the run, so every red below was read for
contention before being believed: none of the seven builds, deploys or times anything, and
each asserts a literal count or set against `openapi.json`.

**The battery stops the gate, so the gate never ran the frontend.** I ran the two commands
`run_frontend` would have run, separately, after the battery finished:

```
npm --prefix web run typecheck    -> exit 0
npm --prefix web test             -> Test Files 1 failed | 78 passed (79)
                                     Tests      2 failed | 1118 passed (1120)
git diff --check                  -> exit 0
```

### The nine reds, by whose grant they sit in

| # | test | what it says | whose |
|---|---|---|---|
| 1 | `tests/contract/api_v1/test_doc_prose_facts.py::test_the_scanned_docs_state_the_contract_surface_this_tree_has` | `CURRENT_STATE.md` and `ALPHA_ROADMAP.md` say 16/19/53 | integrator (docs) — **predicted by `W46-SEAL` §7** |
| 2 | `tests/contract/api_v1/test_surface_counts_in_prose.py::test_the_api_prose_states_the_surface_this_document_declares` | "nineteen operations" ×6 in `infra/deploy/README.md`, `serve.py`, `bff/v1/[...path]/route.ts`, `authorization.ts`; "sixteen paths" in `route.ts` | integrator (`infra/**`, and `web/src` after merge) — **predicted by `W46-SEAL` §7** |
| 3 | `tests/contract/domain_p02/test_openapi_document.py::test_the_surface_is_exactly_the_declared_capabilities` | extra `getDashboardSummary` in the operation set | **`W46-SEAL`'s own grant (`tests/**`), not reported** |
| 4 | `tests/contract/domain_p02/test_openapi_document.py::test_every_operation_requires_the_bearer_scheme` | the same pinned set, a second copy | **`W46-SEAL`'s own grant, not reported** |
| 5 | `tests/contract/domain_p02/test_openapi_document.py::test_every_operation_can_report_not_found_or_validation` | `getDashboardSummary declares no client-fault response` — `{200,401,403,500,503} & {404,409,422}` is empty | **a rule, not a pin** — see finding F-2 |
| 6 | `tests/contract/domain_p02/test_seam_register.py::test_the_api_operation_table_matches_the_frozen_document` | `docs/program/P02_SEAMS.md`'s operation table lacks `('getDashboardSummary', 'GET /dashboard')` | integrator (docs), **not reported by anyone** |
| 7 | `tests/e2e/pc01/test_acceptance.py::test_c1_the_application_composes_from_the_environment_and_answers` | `assert len(client.app.router.routes) == 19` → 20 | integrator (`tests/e2e/**`), **not reported by anyone** |
| 8 | `web/tests/contract/seam-operations.contract.test.ts` › *are exactly the operations the client exposes* | `SEAM_OPERATIONS` has no `getDashboardSummary` | `web/tests` — predicted by `W46-SEAL` §7 |
| 9 | same file › *includes both authorization codes…* | `expected … to have a length of 19 but got 20` | same file; `W46-SEAL` §7 named the file but said both reds were in the first `describe` — one is in `the error catalog` |

**Five of the nine (#3–#7) were in nobody's report.** #3–#5 sit in
`W46-SEAL`'s own `allowed_paths` and in **the very file `D-105` names as a pin site**
(`test_openapi_document.py:493`, the error-code count, one assertion over from #3). They
reproduce at `W46-SEAL`'s own tip by construction —
`git diff --stat ce47316 130200d -- tests/contract/domain_p02 contracts/` is empty — so
they were red on the branch that made them, which means the branch never ran the canonical
battery: `W46-SEAL.md` §4.1 says the two extra pins were found by "running the actual
canonical battery (not a chosen scope)", and its §8 lists only named suites and defers the
`make gate` result to "the final report handed to the integrator" — the one that never
arrived. **A battery run from that tree would have printed #3–#5.**

## 2. `web/FRONTEND_LOCK.json` — recomputed or carried? — **Recomputed.**

Every 64-hex value in the file, recomputed with `hashlib.sha256` over the merged tree:

| field | file | result |
|---|---|---|
| `toolchain.lockfile_sha256` | `web/package-lock.json` | match `98691bc8…` |
| `openapi.sha256` | `contracts/api/v1/openapi.json` | match `20980cb3…` |
| `openapi.snapshot_sha256` | `web/openapi/openapi.json` | match `20980cb3…` |
| `generator.script_sha256` | `web/scripts/generate-api-client.mjs` | match `787c744d…` |
| `generated.files.client.gen.ts` | generated | match `f9bcfd18…` |
| `generated.files.index.ts` | generated | match `b2596c2e…` |
| `generated.files.operations.gen.ts` | generated | match `63e88502…` |
| `generated.files.types.gen.ts` | generated | match `a7dc6f23…` |

`openapi.paths/operations/component_schemas` = 17/20/61 = the document. The two unchanged
digests are **legitimately carried**: `git diff --stat alpha-w45 130200d -- web/package-lock.json
web/scripts/generate-api-client.mjs web/package.json` is empty. A matching digest only proves the
lock agrees with the files, so I also asked whether **the files agree with the generator**:
`npm --prefix web run api:verify` → `generate-api-client --check: OK - 20 operations, contract
sha256 20980cb3…` — the committed client is byte-identical to a fresh generation, and the
mirror to the contract. Not a hand-edited client with its hash taken afterwards.

Two things that are not digests:

- `openapi.content_commit` is `d55012a`, whose `openapi.json` hashes to `00b16114…` (the
  **pre**-reseal contract). That is a documented convention — the `commit_note` says a commit
  cannot name itself and "THE AUTHORITY IS THE DIGEST" — and it has held since `alpha-w42`
  (`667a49c`, `a49d047` behave the same way). `frontend-lock.guard.test.ts:103` checks only
  that it is hex. Not a finding; recorded so nobody mistakes it for one.
- **The `commit_note` states something false about git.** It says the two further pin files
  "moved in this reseal's own git history, **before** this commit". `git show --stat d7ac848`
  shows `test_openapi_conformance.py` and `test_served_document_and_health_plane.py` **in**
  that commit, which is what `W46-SEAL.md` §1 also says. Low severity; a lock file is read by
  the next resealer.

## 3. `getDashboardSummary`, driven

**The instrument.** A fresh database in my lane's own container
(`CREATE DATABASE audit_w46j_judge`, `alembic upgrade head` → `0011_document_section`), the API
from `infra/deploy/serve.py` on `127.0.0.1:56391` in `recorded` mode, and a driver that signs in
as the seeded `admin` and prints raw status and body (a scratch script, not committed; every
call below is an ordinary `GET /dashboard` with a bearer). The gate's own database was not
used: it holds hundreds of rows no step here created, and "absent" cannot be observed on it.

### What it answers, state by state

| state of the deployment | `documents_by_project` | `section_breakdown` | `findings_by_verdict` | `run_activity.spend` |
|---|---|---|---|---|
| **no projects at all** | `[]` | 14 × `0` + unclassified `0` | 4 × `0` | `{"model_call_count":0,"cost_micros":0,"cost_basis":"measured"}` |
| **one project, no documents, no runs** | `[{…,"document_count":0}]` | 14 × `0` + unclassified `0` | 4 × `0` | `{0, 0, "measured"}` |
| + a project holding one `KM` and one unclassified document | `[{…,2},{…,0}]` | `KM: 1`, unclassified `1`, 13 × `0` | 4 × `0` | `{0, 0, "measured"}` |
| + one published run (recorded) | unchanged | unchanged | `pending: 3` | `{1, 34400, "estimated"}` |
| + a second published run | unchanged | unchanged | `pending: 6` | `{2, 68800, "estimated"}` |

Without a credential: `401 authentication_required`. The upload refuses `section=""`, `ar` and
`ZZ` with `422 validation_failed {"constraint":"enum","field":"section"}` — **no silent
"unclassified" fallback for a malformed section, which is the right answer.** The section counts
are what was stored (`SELECT section, count(*) FROM document` → `KM|1`, `NULL|1`), and
`getDocumentVersion` returns `"section": "KM"` for the one and omits the key for the other.

**Absent, empty, not-yet-produced — which of the three the operation can tell apart.**

- *A section with no documents* is `{"document_count":0,"section":"PB"}`: present, not omitted.
  **Correct.**
- *A deployment with no projects* versus *a project with no runs*: distinguishable only through
  `documents_by_project` (`[]` versus one row). `run_activity` has no per-project dimension, by
  design, so "this project has no runs" is not a question this operation answers. Consistent
  with its own argument; not held against it.
- *Not yet produced* — "no provider call has ever been made, so there is no cost" — is **not**
  distinguishable from "calls were made and cost exactly zero, measured". That is F-1.

### F-1 — the spend panel reports a measurement that never happened (needs a reseal)

With **zero** `model_call` rows in the whole deployment the operation answers
`"cost_basis": "measured", "cost_micros": 0`. The repository computes
`basis="measured" if int(unmeasured) == 0 else "estimated"` (`dashboard/repository.py`), and
`unmeasured` is trivially `0` over an empty table. The sealed schema cannot say anything else:
`RunActivitySpend.required = ["model_call_count", "cost_micros", "cost_basis"]`, and
`DashboardSummary.run_activity.spend` is required.

**This is the collapse the per-run rule forbids in writing.** `RunRepository.cost()`
(`src/auditmanager/runs/repository.py:408-416`): *"`None` and `RunCost(0, 0, "measured")` are
different facts and are kept different all the way to the wire … Reporting the first as `0`
would be the same class of invention as `D-3`'s defaulted provenance."* The aggregate's own
docstring claims *"the same conservative rule `runs.repository.RunCost` applies to one run,
lifted to every `model_call` row"* — it lifts the basis rule and drops the `calls == 0 → None`
branch that precedes it.

And the client-side walk this operation exists to replace **gets it right**:
`summarizeRunActivity` sets `costBasis` to `null` *"when no run in scope reported a cost at all —
there is nothing to grade"*, and the panel then says *«Ни один осмотренный прогон не сообщил
стоимости.»* **Wiring the aggregate in as `R-44` intends would regress the screen** from an honest
absence onto a zero labelled *измерено*.

`R-23`'s addendum: *a zero that nothing computed is an invented number too.* This one is a zero
**labelled as measured**. It only occurs on a deployment that has never run anything — which is
precisely the pilot's first day. **The repair is a contract change** — `spend` optional (absent
when `model_call_count` would be `0`), mirroring `RunStatus`, whose cost fields are absent for a
run that made no call — and therefore a reseal. **This is the real reason to reseal once more,
if the integrator is choosing one.**

Reproduce: fresh DB migrated to head, sign in, `GET /dashboard`, read `run_activity.spend`.

### F-2 — what it refuses, and the rule that refuses it

#### F-2a — it refuses scope by ignoring it, not by refusing it

It declares no parameter, and the application ignores undeclared query parameters:

```text
GET /dashboard?project_uid=prj_01ARZ3NDEKTSV4RRFFQ69G5FAV   200  byte-identical to plain
GET /dashboard?cursor=abc&limit=1                            200  byte-identical to plain
GET /dashboard?section=KM                                    200  byte-identical to plain
GET /dashboard?verdict=accepted                              200  byte-identical to plain
POST | PUT | DELETE | PATCH /dashboard                       404  not_found
GET /dashboard/KM                                            404  not_found
GET /dashboard  with  X-Correlation-Id: !!!not a valid id!!! 200  (id replaced, not refused)
```

**It does not become a second authority**: no input changes the answer, and I found no way to
steer it. `W46-SEAL`'s argument holds on the wire, and I say so plainly — the operation was built
to refuse the generic-query shape and it does. The residue: a caller that asks for one project's
dashboard gets the whole deployment's, `200`, with no signal that the scope was dropped — the
mildest form of `AGENTS.md` §4's *silent fallback*. **It is surface-wide, not new**:
`GET /projects?bogus=1&limit=1` and `GET /decisions?project_uid=…` also answer `200`. Low
severity, recorded so that nobody reads "takes no parameter" as "refuses a scoped request".

#### F-2b — gate red #5: is the rule right, or the operation?

`tests/contract/domain_p02/test_openapi_document.py::test_every_operation_can_report_not_found_or_validation`:

```python
codes = set(operation["responses"])
assert codes & {"404", "422", "409"}, f"{name} declares no client-fault response"
assert "500" in codes, f"{name} cannot report an internal fault"
```

**My ruling: the rule is wrong for this operation, and the operation is right.** The reasoning,
measured rather than argued:

1. **The rule encoded an incidental fact as a law.** It arrived in `9924d32` (2026-09-10, *"pin
   the seams to the frozen contracts"*) with no statement of intent. Tabulating all twenty
   operations from `openapi.json` — caller input meaning a path parameter, a query parameter, a
   header other than `X-Correlation-Id`, or a request body:

   | caller input | operations | declares 404/409/422 |
   |---|---|---|
   | yes | 19 (every one before this wave) | 19 of 19 |
   | **none** | **`getDashboardSummary` only** | 0 of 1 |

   So until this wave *"every operation can report a client fault"* and *"every operation takes
   caller input"* were the same set, and the test could not tell which one it was guarding. It
   is `OPERATING_CONSTRAINTS.md` §12's shape: **a rule that shared an assumption with its
   subject.** The first operation without input is the first time the difference is visible.

2. **Declaring a client fault here would make the contract lie.** No `404`: it addresses no
   identity. No `409`: it writes nothing. No `422`: it has no input to be malformed — measured
   above, not assumed; even the one header it accepts is replaced rather than refused. A `422`
   added to satisfy the rule would be a declared response **no request can produce**, and the
   generated client would carry a branch nothing can reach. That is the "make a guard pass"
   repair the integrator asked me to name if it is one: **it is.**

3. **The one honest way to give it a real `422`** is to make it refuse undeclared query
   parameters — which would also close F-2a. I do **not** recommend it for this operation alone:
   all nineteen others ignore unknown parameters, so a single refusing operation makes the surface
   inconsistent. Whether the surface should refuse unknown parameters is a surface-wide contract
   decision (twenty operations, every client), and it belongs to the owner, not to this red.

**Recommended repair — a test change, no reseal for #5:**

- Restate the rule as *"every operation that takes caller input can report a client fault"*,
  with **input derived from the document** (path, query, non-correlation header, body) rather
  than from a name list — so an operation that later gains a parameter is pulled back under the
  rule without anyone remembering to.
- Make the exemption **two-sided**: an operation with no caller input must declare **none** of
  `404/409/422`. That keeps the exemption from becoming a hiding place — a `422` added to
  `getDashboardSummary` later, with nothing that can produce it, would redden.
- Keep the non-vacuity pin as a literal, the programme's accepted pattern: *the input-less set is
  exactly `{"getDashboardSummary"}`* — so a second input-less operation is a decision someone
  makes, not a drift. **That literal is a pin in `D-105`'s family and moves on a reseal**; it
  should be written into whatever list makes that family enumerable.
- `500` stays required for every operation, unchanged.

**If the integrator is resealing anyway, the reason is F-1, not #5.** The two can travel
together; #5's repair does not need the reseal and should not be dressed as one.

### What is not guarded — a mutation that survives

`W46-SEAL.md` §3 says absent-is-not-empty is *"enforced in every panel and shown failing twice"*.
The two guards it shows failing are the section **vocabulary** (three spellings agree) and the
**page-shape** exemption (no `items`/`page`, four top-level keys present). **Neither observes a
row.**

In a disposable clone at `130200d` (`/root/w46j-probe`, same `.venv`, same lane), baselined
**609 passed** unmutated, I changed `dashboard/repository.py` so that `_filled` drops every
member whose count is zero and the unclassified bucket is appended only when non-zero — absent
rendered as *missing*, the exact defect the operation's description promises it does not have:

```text
-    return [(member, counted.get(member, 0)) for member in vocabulary]
+    return [(member, counted[member]) for member in vocabulary if member in counted]
     … and the unclassified append wrapped in `if section_rows.get(None, 0):`

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q \
  -p no:cacheprovider tests/integration/api tests/integration/composition \
  tests/contract/domain_p02/test_project_section_catalog.py
unmutated: 609 passed          mutated: 609 passed
```

The only other test files that mention the operation at all
(`grep -rlE 'dashboard|Dashboard|section_breakdown|findings_by_verdict|run_activity|documents_by_project' tests --include=*.py`
→ nine files) are `test_doc_prose_facts.py` and `test_openapi_conformance.py`, which read
`openapi.json` and cannot see a response row, plus the composition/authorization/surface files
that check registration. **The property the operation was built for has no guard that can fail.**
Reverted; the clone's `git status` was clean afterwards.

## 4. `/dashboard` at 780 px, both palettes; the `SEEDS` and cache-state edits

**The instrument.** `npm --prefix web run build` (exit 0), `next start` on `127.0.0.1:56393`
forwarding to the API of section 3, signed in through the real `/login` screen with the
repository's own `session.mjs`, each reading in a **cold** browser from `cdp.mjs`
(`withColdBrowser`), the palette chosen by writing `am-theme` into `localStorage` the way the
toggle does, the width read with the repository's own `width.mjs` `MEASUREMENT`. A second stack
(`audit_w46j_judge2`, API `:56394`, web `:56396`) holds the *no projects* and *projects but no
runs* states, so the absent branches were driven on real responses, not on seeded caches.
Screenshots and `results.json` are in my session scratch directory, which does not survive a
restart; everything load-bearing is quoted here.

### Width — the property holds; the literal "`scrollWidth === 780`" does not reproduce, and need not

| palette | viewport | `data-theme`, body background | `scrollWidth` / `clientWidth` / `innerWidth` | boxes past the right edge | console / page errors |
|---|---|---|---|---|---|
| light | **780** | `light`, `rgb(245, 246, 248)` | 765 / 765 / 780 | 0 | 0 / 0 |
| dark | **780** | `dark`, `rgb(13, 18, 25)` | 765 / 765 / 780 | 0 | 0 / 0 |
| light, dark | 781 (one past the breakpoint: two columns) | as above | 766 / 766 / 781 | 0 | 0 / 0 |
| light, dark | 1024 | as above | 1024 / 1024 / 1024 | 0 | 0 / 0 |
| light, dark | 360 | as above | 345 / 345 / 360 | 0 | 0 / 0 |
| light, dark | 780, **no projects** (stack 2) | as above | **780** / 780 / 780 | 0 | 0 / 0 |

**No horizontal overflow at any width, in either palette, on real data.** The merge commit's
figure `scrollWidth === 780` reproduces only on a page **shorter than the viewport**: with real
data the page scrolls vertically, the classic scrollbar takes 15 px, and `scrollWidth` is 765.
The committed instrument asserts `scrollWidth <= innerWidth`, which is the right property; the
literal was a property of how much data the page had, not of the layout. Worth knowing before
anybody writes `=== 780` into a guard.

At 780 the navigation wraps onto a second line in both palettes and pushes nothing past the edge:
`D-93`'s wrap holds with the seventh link.

### Which panels are driven against real data — re-taken

| panel | what the browser actually requested (`/bff/v1/…`, all `200`) | rendered |
|---|---|---|
| documents per project | `GET /projects?limit=50` | real: *Документов: 2 на 2 проектах*, a project at *документов 0* |
| findings by verdict | `GET /decisions?limit=50` | *Решений пока нет.* — true: six findings, no decision recorded |
| run activity and spend | `GET /projects` → `GET /projects/{uid}/documents` ×2 → `GET /versions/{uid}/runs` ×2 | real: *Прогонов: 1 … 0.034400 … оценено* |
| per-section breakdown | **nothing** | structure only (section 5) |

**Three of four, confirmed.** Two details that disagree with what was written down:
`GET /projects?limit=50` is issued **twice** in a cold load (the stream's proposed manifest
comment said React Query would deduplicate it), and **`getDashboardSummary` is requested by
nothing** — see F-3 in section 5.

**The absent branches, on real responses.** Stack 2, empty: documents *«Проектов пока нет.»*,
verdicts *«Решений пока нет.»*, runs *«Проектов пока нет. Прогонов показывать нечего…»*. Then one
project with one never-run document: runs *«Прогонов пока нет. Среди осмотренных проектов и
версий ни один прогон ещё не запускался.»* — **the branch `runs-empty` was added for, reached by a
real client.** Absent (no project) and empty (a project, no runs) render differently on the
screen. **Correct.**

In that same state `GET /dashboard` answers `"spend": {"model_call_count": 0, "cost_micros": 0,
"cost_basis": "measured"}` — the screen says *no runs yet* while the aggregate that is meant to
replace it says *measured, zero*. F-1, seen from the other side.

### The two instrument edits, ruled one by one

`UNREACHABLE_IN_ONE_PASS` holds **13 entries at `alpha-w45` and 13 at `130200d`** — the stream
excused nothing. `SEEDS` gained one entry; `CACHE_STATES` gained one. Each was tested by
removing it in the disposable clone at `130200d`:

1. **`SEEDS` `/dashboard` — correct: an instrument demanded it.** Removed →
   `screen-set.guard.test.ts` red, twice:
   `expected [ '/dashboard' ] to deeply equal []` (*"web/src/app serves these addresses and
   `SEEDS` … answers for none of them"*) and `expected 14 to be 15`. It is a `make`, not an
   `optOut`, with `discipline: {}` like every other parameterless route (`/blocks`,
   `/knowledge-base`). This is the "new screen arrives" path the file's header describes, and
   the only one available: the guard names the address until it is seeded. **Not an edit to make
   something pass.**
2. **`CACHE_STATES` `runs-empty` — correct: the matrix found a real hole.** Removed →
   `rendered-language.guard.test.ts` red, naming exactly one unreached branch:
   `"Прогонов пока нет."  (web/src/widgets/dashboard/ui/run-activity-panel.tsx)`. That branch is
   reachable by a real client — driven above on stack 2 — so the file's own rule (*seed a state
   that reaches it, or excuse it with a reason*) points at seeding, and the stream seeded. The
   edit is **additive**: every derived screen is rendered in one more state, so coverage widened
   rather than narrowed. The stream reported it as a finding rather than folding it in
   (`W46-DASH.md` §D4), which is what `D4` asked for.

**Both instruments reach the dashboard**: the contrast census and the language guard are among
the 78 of 79 frontend files that pass on `130200d`; the one failing file is
`seam-operations.contract.test.ts` (section 1, #8–#9).

### F-4 — the journey row applied for `/dashboard` is red under the journey's own default phase

The integrator applied the row with `expects_api` naming `listProjects` and `listDecisions` only,
and a comment reasoning that the walk's `listDocuments`/`listRuns` fire *"only once real project
data exists"*, so declaring them *"would assert nothing while looking like an assertion"*.

**The journey's own write half creates that data before its read half runs.** Against my stack:

```text
E2E_PC01_LOGIN=admin E2E_PC01_PASSWORD=password \
  npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:56393 --phase all --out <dir>
write steps checked: 3/3        routes checked: 16/16        exit 1
  - dashboard: made 6 API call(s) no route in the manifest declares:
      GET /bff/v1/projects/prj_…/documents (×3) | GET /bff/v1/versions/ver_…/runs (×3)
  - blocks: made 1 API call(s) no route in the manifest declares: GET /bff/v1/projects
```

So under `--phase all` — the default — the dashboard route **cannot** pass. And the manifest
already has the mechanism for a call that fires conditionally: **`optional_api`**, matched by
shape with identifiers collapsed to `{id}` (`journey.mjs:390-395`), written for the review
screen's calls that depend on data. The row wants `listDocuments` and `listRuns` there. Nothing
in `make gate` runs the live journey (`test_pc01_journey_conformance.py` compares the manifest to
the route tree statically), so this was invisible to every green in this wave.

The `blocks` red is **pre-existing and not this wave's**: `useProjectList` entered
`blocks-page.tsx` in `c4165b9` (`W45-BLOCKS`), and the manifest's `blocks` row has declared
`expects_api: []` since then, at `alpha-w45` too. The last recorded live journey run I can find
in `docs/program` is `W43-JUDGE-B`. Found only because I ran the instrument rather than reading
the row — see section 6.

## 5. Can the per-section panel be made to show an invented number?

**Through data: no, and for a reason that is not a guard.** `SectionsPanel` takes no props and
calls no hook; it renders `PROJECT_SECTIONS` and a caption. With a `KM` document stored
(`GET /versions/ver_01M3KC7S853F2DZED8WC7K5KM0` → `"section": "KM"`) and nine findings in the
database, the panel rendered fourteen names and no number in both palettes at 780. **Nothing a
deployment holds can put a digit on it.** The dashboard's promise holds on `130200d`.

**Through code: yes, and nothing notices.** In the disposable clone at `130200d`:

```text
- {section.code === ANALYSED_SECTION_CODE ? ' — единственный анализируемый раздел' : ''}
+ {section.code === ANALYSED_SECTION_CODE ? ' — единственный анализируемый раздел' : ''}{': 0'}

npm test (web/, the whole suite)
unmutated: Test Files 1 failed | 78 passed (79)   Tests 2 failed | 1118 passed (1120)
mutated:   Test Files 1 failed | 78 passed (79)   Tests 2 failed | 1118 passed (1120)
           (the same two seam-operations reds, section 1 #8–#9; nothing new)
```

Fourteen invented zeros — the exact thing `R-23`'s addendum names — pass the frontend battery,
the language guard and the contrast census. `dashboard.test.ts` guards the three **aggregators**
(and I credit it: each of its cases names its mutation, and the absent-versus-zero ones are the
right cases); **no case renders the section panel and asserts the absence of a number.** The
dispatch's deliverable 3 asks for every new guard shown failing; this property has no guard to
show. Reverted.

### F-3 — on the merged tree the panel's reason is false, and so is the project screen's

The caption, rendered today on `/dashboard`:

> *«Раздел документа нигде в системе не хранится и не проверяется, поэтому находки нельзя
> посчитать по разделам.»*

**Both halves became false at `57e519b`**, the merge that landed `W46-SEAL`: the section **is
stored** (`document.section`, migration `0011`; the `KM` upload above round-trips) and **is
checked** (the column's `CHECK` constraint, and the API refuses `section=""`, `ar` and `ZZ` with
`422 validation_failed {"constraint":"enum","field":"section"}`, driven in section 3). When
`W46-DASH` wrote it, in a worktree without the reseal, it was true — the stream's report says so,
honestly, in D1. **The merge made it false and nothing reddened**, because no instrument reads
screen prose against the schema.

**The same sentence stands on a screen this wave never touched.** `/projects/{uid}`, rendered at
780 over the very project holding the `KM` document:

> *«Разделы — это навигация. Раздел документа нигде не хранится и не проверяется…»* and
> *«…принадлежность документа разделу не проверяется и нигде не сохраняется.»*
> (`web/src/widgets/project-sections/ui/project-sections.tsx:93` and `:105-107`)

and **a test pins it**: `web/tests/unit/screens/project-sections.test.ts:119-124`,
*"says that a document's section is stored nowhere and checked nowhere"*, asserts
`'не проверяется'` and `'нигде не сохраняется'`. That test now freezes a false statement in
place — the shape the programme calls *characterization can freeze a defect*. The module header
of `web/src/entities/project/model/section.ts` makes the same claim in prose (*"the contract has
no section field anywhere"*) and is where a future reader will look first.

This is the `OPERATING_CONSTRAINTS.md` §4.7 shape without the security edge: **a backend change
altered what a thing *is*, and the sentences telling a reviewer what it is were in another
stream's tree.** It took the merge to create the contradiction and nobody read across it.

### F-3b — the aggregate read is merged and nothing calls it

```text
grep -rn 'getDashboardSummary\|DashboardSummary' web/src --include=*.ts --include=*.tsx \
  | grep -v 'shared/api/generated' | wc -l          -> 0
```

`R-44`'s decision was **one aggregate read serving all four panels instead of three client-side
walks**. On `130200d` the aggregate exists with **no consumer**, and the three walks it was ruled
to prevent are the live path — including the run-activity walk, which under-counts past one page
at three levels and says so. `W46-DASH` could not have consumed it: the generated client was
`W46-SEAL`'s hotspot and arrived only at merge, and the stream reported exactly that. **The gap is
at the join, not in either stream.** The merge commit says the per-section panel *"never leaves
that state, because only AR is analysed"* — but *analysed* and *counted* are different things:
`section_breakdown` counts **documents**, server-side, per section, and a `KM: 1` there is a
computed number, not an invented one. `docs/program/dispatch/W47-PLAN.md` contains no line about
the dashboard, `R-44` or `getDashboardSummary`, so nothing currently schedules the wiring.

**Two cautions for whoever wires it**, both measured:

- **F-1 first.** Wired as sealed, the spend line would move from the walk's honest *«Ни один
  осмотренный прогон не сообщил стоимости.»* to *0 · измерено* on a deployment that has never run.
- **The product cannot set a section.** The upload form on `/projects/{uid}` offers a PDF and a
  display title, nothing else (rendered at 780), so every document uploaded through the product
  is unclassified. A wired panel that drops the unclassified row would show fourteen true zeros
  that read as *"no documents"* — correct numbers, false picture. The aggregate always sends that
  row; the screen must show it.

### A judgement call on `R-39`, stated as one

`R-39` permits a reason *in the words of the subject* and keeps the ban on *operation ids, field
names, transport*. The dashboard's subtitle says *«Три читают то, что уже отдаёт контракт; …
операции, которая считала бы находки по разделу, в этом контракте пока нет»*, and the verdict
panel's caption says *«…операция читает журнал решений, а не список всех находок»*. No id and no
field name — but *контракт* and *операция* are the author's vocabulary, which is what `D-91`'s
*«не отдаёт ни одна операция договора»* was and what `R-39` moved away from. **Low; the owner's
line, not mine.** Noted because a reviewer reading the dashboard is told about contracts.

### The verdict panel with a real decision

Not part of the question, but it is the one live state the merge commit did not describe: after
one `accept` recorded through the API (`201`), the panel renders *«Находок с решением: 1»*,
*принято 1 · отклонено 0 · не решено 0 · нужен ручной разбор 0*, in both palettes. Every number
is computed from the ledger. The **`нужен ручной разбор 0`** row is for a verdict the code itself
says has **no PC-01 producer** (`verdicts-panel.tsx:51`), while `/knowledge-base` deliberately
refuses to offer that verdict because *"a filter that can only ever return an empty page teaches a
reviewer that the knowledge base is empty"* (`knowledge-base-page.tsx:42-46`). Two screens, one
product, opposite rulings on the same unreachable value. Low. Meanwhile the aggregate, for the
same database, answers `pending: 8, accepted: 1` — it counts never-judged findings as pending,
which the panel's caption explicitly excludes. **When the panel is wired to the aggregate its
meaning changes**, and the caption must change with it.

## 6. Off the trail — *in progress*
