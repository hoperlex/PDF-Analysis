# W46-JUDGE-X — the contract, the instruments and the integrator's own changes

**Judge:** `W46-JUDGE-X` · **lane:** `gate-w46j` (PostgreSQL `127.0.0.1:56390`, S3
`59990`/`59991`, API `56391`, Next `56393`) · **worktree:** `/root/w46j` · **branch:**
`agent/w46-judge-x` · **tree judged:** `d5c9be5`, the merged tip of wave 46 (sub-stage A judged
at `2ffca8c`, then `W46-SPEND` merged at `9a295aa`, `W46-WIRE` at `1c38c52`, and the
integrator's join repair `d5c9be5`).

Brief: `docs/program/dispatch/W46-JUDGES-XY.md`, section `W46-JUDGE-X`. Opened before the first
measurement and committed section by section; a section marked *pending* has not been measured
yet.

## X1 — the whole gate on the merged tip — **`GATE OK`**

```
cd /root/w46j && make gate > /root/w46x-gate.log 2>&1      # literally
grep -n 'GATE' /root/w46x-gate.log
229:GATE OK: battery, foundation, frontend and whitespace all pass
```

Run on `f35e7cd` (= `d5c9be5` plus this file only, which sits in `docs/program/reviews/`,
outside every prose guard's named scope: `test_wave_reports_are_never_scanned`), tree clean,
11:57:13Z–12:09:09Z. Before starting: `free -g` showed 4 GB available, and no other
`make gate` had a cwd under `/root/w46*`. Another project's node test suite ran on the host
during the battery (load 20 at its peak); nothing was OOM-killed and the log is complete.
The verdict is the log line above, not the exit status (which was `0`).

| layer | `W46-JUDGE-A` on `130200d` | this run on `d5c9be5` |
|---|---|---|
| foundation | 35 passed | **35 passed** (log line 60) |
| battery | 7 failed, 2493 passed, 5 skipped, 4 warnings, 169 subtests | **2504 passed, 5 skipped, 4 warnings, 169 subtests** (line 121) |
| frontend | 1 file failed; 2 failed, 1118 passed (1120) in 79 files — run by hand, because the battery stopped the gate first | **79 files, 1118 passed (1118)** (lines 224–225), run by the gate itself |
| whitespace | `git diff --check` exit 0 | passed (the recipe reached `GATE OK`) |

**Every difference, by count.** Accounted by name in X6 below (node-id set algebra), and
predicted before the run from the commits alone:

- **battery 2500 nodes → 2504.** `8ad692f` repaired six battery reds by editing inside
  existing tests (no node added or removed), so `2ffca8c` still had 2500 nodes (`W46-SPEND`'s
  own baseline: 1 failed + 2499 passed). `W46-SPEND` removed one node
  (`test_every_operation_can_report_not_found_or_validation`), added two in the same file
  (`test_every_operation_that_takes_input_can_report_a_client_fault`,
  `test_the_input_less_operation_set_is_exactly_the_pinned_one`) and three in a new file
  (`test_dashboard_summary_over_a_fresh_deployment.py`): 2500 − 1 + 2 + 3 = **2504**.
  `W46-WIRE` and `d5c9be5` touch no Python test. The seven reds of `130200d` are all gone:
  six by `8ad692f`, the seventh (#5) by `W46-SPEND`'s restated rule.
- **frontend 1120 → 1118.** `8ad692f` added `getDashboardSummary` to `SEAM_OPERATIONS`,
  which is iterated into one `it()` per row (`seam-operations.contract.test.ts:95-96`):
  **+1 → 1121 at `2ffca8c`**. That is the one test `W46-WIRE.md`'s *"Frontend baseline"*
  section could not place: the integrator's derived `1120` missed that the row is a test
  of its own; `W46-WIRE`'s reconstructed `1121` was right. `W46-WIRE` then replaced the three
  deleted aggregators' cases in `dashboard.test.ts` (10 → 7): **−3 → 1118**. No test file was
  added or deleted: 79 → 79.
- **the two frontend reds of `130200d`** (`seam-operations`, #8–#9) were repaired by
  `8ad692f`'s row; the second one cleared because its 19 was derived from the list.

## X2 — `F-1` re-driven — **repaired on the wire; one layer still invents zeros, for rows**

**The instrument.** `audit_w46j_judge` and `audit_w46j_judge2` dropped; `CREATE DATABASE
audit_w46x_judge` in `gate-w46j-postgres-1`; `alembic upgrade head` → `0011_document_section`,
`model_call` 0 rows, `project` 0 rows, one account (`admin`). The API from
`infra/deploy/serve.py` on `127.0.0.1:56391`, `recorded` mode, a fresh token
(*"wired, provider_mode=recorded, operations=20"*), PID 2588443, confirmed a descendant of this
session with `pstree -sp` and `readlink /proc/2588443/cwd` = `/root/w46j`. A scratch driver
(not committed) signs in as `admin` through `POST /auth/token` and prints raw status and body.

| state | `run_activity` keys | `spend` | bytes `spend` in the body? |
|---|---|---|---|
| fresh deployment, nothing in it | `['by_state']` | **absent** | **no** |
| + one project, no documents (`document_count: 0` row present) | `['by_state']` | absent | no |
| + one unclassified document (`<none>: 1`) | `['by_state']` | absent | no |
| + one run, `published` in 2.1 s | `['by_state', 'spend']` | `{"model_call_count": 1, "cost_micros": 34400, "cost_basis": "estimated"}` | yes |

`getRunStatus` for that run answers `model_call_count 1, cost_micros 34400, cost_basis
estimated` — the aggregate and the per-run reading agree to the micro. `findings_by_verdict`
moved to `pending: 3`. Without a credential `GET /dashboard` is `401`.

**Absent, not `null`, not zero — and valid.** I validated the four real bodies against the
frozen `DashboardSummary` with the suite's own Draft 2020-12 checker
(`.venv/bootstrap/bin/python tests/contract/api_v1/schema_validation_check.py`): **all four
valid**, and two controls built from the first body are invalid as they must be
(`spend: null` → *"None is not of type 'object'"*; `spend` without `cost_basis` → *"'cost_basis'
is a required property"*). Against the **pre-reseal** contract (`git show
2ffca8c:contracts/api/v1/openapi.json`) the three bodies without `spend` are **invalid**
(*"'spend' is a required property"*) and the fourth is valid: the reseal was load-bearing,
not cosmetic. **Nothing in the battery does this for `/dashboard`**:
`tests/integration/api/test_schema_conformance.py` validates real bodies for five other
schemas and has no `DashboardSummary` case, so the wire-to-contract agreement for this
operation was, until this measurement, asserted rather than observed.

**Layer by layer, for `spend`:** record (`DashboardSummaryRecord.run_spend: … | None`, `None`
exactly when `calls == 0`, `dashboard/repository.py`) → view (`DashboardSummaryView.run_spend:
… | None`) → adapter (`None` carried, `bootstrap/adapters.py`) → serializer
(`_run_activity_body` omits the key; the router returns `json_response(… dashboard_summary_body
…)`, not a Pydantic re-serialisation that could emit `null`) → generated type
(`types.gen.ts:484` `spend?: RunActivitySpend`, no default) → screen
(`run-activity-panel.tsx:86-95` renders *«Ни один прогон ещё не обращался к провайдеру…»* when
`undefined`). `grep -rn 'spend' web/src` finds no other reader. **No layer turns absent `spend`
back into zeros.** `F-1` is repaired, and `W46-SPEND` did the right thing in every layer.

### X2-a — the same collapse, one layer up: the dashboard fills rows the server did not send

`summarizeVerdictBreakdown` (`web/src/widgets/dashboard/model/verdict-breakdown.ts:15-26`) and
`summarizeSectionBreakdown` (`section-breakdown.ts:29-50`) seed every member at `0` and then
overwrite from the wire, and both headers say so as a virtue: *"a row a future response
happens to omit reads as its true zero"*. It is not a true zero. The server's `_filled`
defaults an absent `GROUP BY` group to `0`, which **is** computed (the database counted the
whole table); the client defaulting an absent **wire row** to `0` is a number nobody computed —
`R-23`'s addendum, and `AGENTS.md` §4's silent fallback. Both also drop a member they do not
know (`if (known !== undefined)`, `if (row.verdict in byVerdict)`) without a signal.

Reproduced in the disposable tree `/root/w46x-tree-tip` (never in the worktree), a scratch
vitest file rendering `Dashboard` from a hand-built summary through the repository's own
`renderWith` harness:

```text
findings_by_verdict: [], section_breakdown: [], documents_by_project: one project, 7 documents
  -> "Документов: 7 на 1 проекте" … "Находок: 0" … "не решено 0 принято 0 отклонено 0
     нужен ручной разбор 0" … fourteen sections ": 0" … "Без раздела: 0"
     — 19 zeros the body did not contain, beside a total of 7 they cannot add up to, under a
     caption that says the unclassified row comes «не из пропуска в подсчёте».
a verdict 'escalated' (count 9) and a section 'ZZ' (count 5), 5 documents
  -> "Находок: 0", every section 0, "Без раздела: 0"; no 9 and no ZZ anywhere on the screen.
```

**Cost, stated plainly.** Not reachable against today's server: `F-5a`'s new guard keeps the
server from dropping rows (X4), and every body I drove carried all fourteen sections, the
unclassified row and all four verdicts. It is reachable by a server regression that guard does
not cover, or by version skew between the API and web images after a reseal that adds a member.
What makes it a finding rather than a style point: it is `F-1`'s exact shape — absence rendered
as a measured zero — **designed in on purpose**, and it is invisible to `W46-WIRE`'s render
test, whose promise is *"nothing on screen is a number the fixture did not send"* but whose one
fixture always sends every row. The honest client either renders a missing row as absent or
refuses the body; which one is a small decision, and it is not mine. **Low–medium.**

### X2-b — four sentences the merge made false about the generated type

The streams coded against each other's future, correctly, and wrote that down. After the merge,
`types.gen.ts:484` says `spend?: RunActivitySpend`, and these still say it is required *today*:

```text
web/src/widgets/dashboard/ui/run-activity-panel.tsx:8   "…RunActivity.spend is still typed required today…"
web/src/widgets/dashboard/ui/run-activity-panel.tsx:64  "…whether the generated field is required (today) or optional…"
web/tests/unit/widgets/dashboard.test.ts:61             "…generated client still types `spend` required…"
web/tests/guards/rendered-language.guard.test.ts:644    "…today's generated client still types it required."
```

`grep -rn "still typed\|still types\|required (today)\|today's generated" web/src web/tests`
reproduces them. Comments, not screen text, so **low**; recorded because it is `F-3`'s shape —
a merge made a sentence false and nothing reddened — inside the join this stage exists to
repair. `d5c9be5` repaired the two sentences a guard could read and none of these four.

## X3 — the reseal: five documents or four? — **four kinds in one commit, and the fifth legitimately empty; but nothing checks the sixth**

### One commit

`git show --stat 069f656` carries `contracts/api/v1/openapi.json`, `web/openapi/openapi.json`,
the four files under `web/src/shared/api/generated/` and `web/FRONTEND_LOCK.json` — the
contract, the mirror, the client, the lock. **The fifth element, *every moved pin*, is empty,
and legitimately so**: the contract diff is one word (`"spend"` leaves `RunActivity.required`,
3 lines), no path, operation, schema or error code moves, and the gate is green with every
`D-102`/`D-105` pin where `W46-SPEND.md` §2's table says it is (surface `17/20/61` at
`test_doc_prose_facts.py:316`, `FROZEN_*` counts, `PATH_COUNT`/`OPERATION_COUNT`/`SCHEMA_COUNT`,
the catalog `22`). `git merge-tree` shows the merge `9a295aa` carried the commit unchanged (X6).

### The digests, recomputed by me

`hashlib.sha256` over the merged tree, every 64-hex value in the lock: **8 of 8 match**
(`lockfile_sha256` `98691bc8…`, `openapi.sha256` = `snapshot_sha256` `f688b409…`,
`script_sha256` `787c744d…`, `client.gen.ts` `6f1ca0d5…`, `index.ts` `986aaa02…`,
`operations.gen.ts` `58341631…`, `types.gen.ts` `df105211…`). `cmp` contract vs mirror:
byte-identical. `npm --prefix web run api:verify` → *"generate-api-client --check: OK - 20
operations, contract sha256 f688b409a080b3f6664d6e0dc6e0881f9b14638f57b8d4f240a037ea8775bf54"*,
so the committed client is a fresh generation, not a hand edit hashed afterwards; the worktree
was clean before and after.

**Surface:** 17 paths / 20 operations / 61 schemas from the document, equal to the lock's
`paths`/`operations`/`component_schemas`. **Error codes:** 22 in `ErrorCode`'s enum and 22 in
`contracts/domain/v1/error-codes.json` `codes`; `git diff --stat 2ffca8c d5c9be5 --
contracts/domain` is empty. **Head:** `0011_document_section`, the last revision in
`db/migrations/versions/`, and the one `alembic upgrade head` reached on my fresh database.

### Is the lock's `commit_note` true now? — **The sentence the judge found false is now true; three small ones are not**

- **The corrected sentence is true.** It now says the two further pin files moved *in*
  `d7ac848`, and `git show --stat d7ac848` lists `test_openapi_conformance.py` and
  `test_served_document_and_health_plane.py` beside the five documents. Corrected in place,
  as asked.
- **`W46-SPEND`'s own paragraph is true where it can be measured:** one word off one property
  of one schema; 17/20/61 and 22; the implementation one commit earlier (`f50e656` is
  `069f656`'s parent on the stream's first-parent line); the spelling
  `Field(default=None, json_schema_extra=optional_property)` is the module's for every optional
  property; the digests are as recomputed above; contract = mirror.
- **Not true: *"for the reason every reseal note below gives: a commit cannot name itself"*.**
  Of the eight notes below it, five (`W18-SEAL`, `W25-SEAL`, `W34-CONTRACT`, `W38-KB`,
  `W39-REVOKE`) do not contain that reason. Low.
- **Stretched: *"This mirrors RunStatus"*.** `RunStatus.cost_micros` says in the contract
  *"Absent when the run made no provider call at all, which is a different fact from a cost of
  zero."* `RunActivity.spend` has **no description at all**, and `RunActivitySpend`'s says only
  *"`cost_basis` is `measured` only when every contributing `model_call` row reported a measured
  cost"*. The reseal moved `required` and wrote nothing into the contract about what absence
  means, so the generated type (`spend?: RunActivitySpend`, no doc comment) cannot tell a
  client author either. The behaviour mirrors `RunStatus`; the contract does not. Low, and it
  would cost a second reseal to fix, so it is the owner's call whether it waits.
- **`dispatch_named_commit: "f50e656"`** — per `W25-SEAL.md:112` the field records the commit a
  dispatch named when it differs from the content commit. `W46-SPEND`'s dispatch named only its
  base, `2ffca8c`. The field has simply copied `content_commit` since `W45-BLOCKS` (`830fd76`,
  `d7ac848`, `069f656`), so this is a convention that drifted, not this stream's error.

### The sixth document nobody lists: the model the served document is generated from

`D-102`'s discipline lists the five documents a reseal moves. It does not list
`src/auditmanager/api/schemas/models.py`, from which FastAPI generates the document the
application **serves**. That moved one commit earlier, in `f50e656`. I measured the served
document against the frozen one with the programme's own engine
(`tests/contract/api_v1/openapi_conformance.py`, `differences(surface(frozen), surface(served))`,
`served = create_documentation_app().openapi()`):

```text
f50e656   1 semantic difference: schemas.RunActivity.required: contract ["by_state", "spend"],
          generated ["by_state"]
069f656   0 differences
d5c9be5   0 differences
```

So the tree at `f50e656` served a document that disagreed with its frozen contract — expected,
mid-reseal. The question is **what would have noticed**. `tests/contract/api_v1/
test_openapi_conformance.py` at `f50e656`: **86 passed**. That file tests the comparison
*engine* against planted differences and a miniature app (its Part 5 header: *"Until
[stage 2] lands there is no `app.openapi()` for the twelve operations to compare"*); `grep -rn
'differences(' tests` finds no call on the real application anywhere. `ALPHA_ROADMAP.md:306`
specifies the gate as *"`app.openapi()` against the frozen document"* and
`test_served_document_and_health_plane.py:3-9` says *"the served document is the one the gate
compares"*. To learn whether any test in the canonical battery compares them, I re-created the
disagreement at the tip — `RunActivity.spend` made required again **in the Pydantic model only**
(the engine then reports exactly one difference, `schemas.RunActivity.required`) — and ran the
whole canonical battery on the clone:

```text
cd /root/w46x-clone     # d5c9be5 + that one-line mutation of api/schemas/models.py; lane .env loaded
.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q tests --ignore=tests/checkpoint \
  --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py \
  --ignore=tests/contract/test_validate_bootstrap.py          # run_battery's command
2504 passed, 5 skipped, 4 warnings, 169 subtests passed in 512.21s     (12:31:45Z–12:40:37Z)
```

**Identical to X1's unmutated battery.** The frontend suite and the foundation read files the
mutation does not touch, so `make gate` would print `GATE OK` over an application whose served
document disagrees with its frozen contract. Reverted; the clone's `git status` was clean.

**Why it is this way, from the record.** `W13-CONF` built the engine before the application
existed and handed the last step over in writing (`docs/program/reviews/W13-CONF.md` §11):
*"The wiring is one file and is deliberately not written. When `W13-API` lands, the remaining
step is a new `tests/contract/api_v1/test_openapi_conformance_live.py` holding
`differences(surface(json.loads(CONTRACT_PATH.read_text())), surface(app.openapi()))` and
asserting it empty."* `git log --all -- tests/contract/api_v1/test_openapi_conformance_live.py`
is empty: **that file was never written, on any branch.** `W13_CLOSURE.md` reports *"0
differences between the frozen document and `app.openapi()`"* once, at wave 13; since then
the programme has described the gate as existing (`test_served_document_and_health_plane.py:3`,
*"the served document is the one the gate compares"*) while the gate has had nothing to compare
it with.

**Cost.** The product's own client is generated from the frozen document, so the screens do
not read the served one. But FastAPI **validates requests** from the same Pydantic models it
generates the served document from: a request model that drifts from the contract (a field made
required that the contract calls optional, a bound tightened) refuses requests the contract and
the generated client consider valid. Integration tests catch that only for the fields they
happen to send; this comparison is the one check that sees every field. The lock's
`commit_note` records nine reseals since wave 13 (`W18-SEAL` to `W46-SPEND`), and every one
went through a gate that could not have seen this. **Medium**, and the cheapest repair in this report: `W13-CONF` already wrote it
down, a single test over an engine that is already guarded by 86 planted-difference tests. It
is not `W46-SPEND`'s: `f50e656` → `069f656` is exactly how a reseal is meant to proceed; the
stream simply inherited a gate that could not have noticed a mistake in between.

## X4 — the three guards `W46-SPEND` claims, mutated by me — **each catches what it was shown; each misses one I invented**

**The instrument.** A disposable `git clone` of this worktree at `d5c9be5`
(`/root/w46x-clone`, tags fetched so `test_doc_prose_facts.py` can read `alpha-w45` from git,
the worktree's `.venv` and `web/node_modules` linked and excluded, the lane's `.env` loaded the
way `load_env` loads it). I tried `make mutation-copy MUT=/root/w46x-mut FULL=1` first — it
built cleanly (*"MUTATION-COPY OK"*) — and set it aside because the copy has no `.git`, so the
tagged-tip tests would redden for reasons unrelated to any mutation. Every mutation below is a
scratch script applied to the clone and reverted with `git checkout --`; `git status
--porcelain` in the clone printed `0` after each. Every scope was baselined unmutated first.

### `F-2` — the restated rule (`test_openapi_document.py`)

Baseline: **46 passed**; the whole canonical contract scope (`tests/contract` with
`run_battery`'s three ignores) **367 passed**.

| mutation of `contracts/api/v1/openapi.json` | result |
|---|---|
| direction 1 — `422` added to `getDashboardSummary` (the stream's) | **red**: *"getDashboardSummary takes no caller input but declares ['422'] -- a response no request can produce"* |
| direction 2 — `404`/`409`/`422` stripped from `listDecisions` (the stream used `issueToken`; I took another operation) | **red**: *"listDecisions takes caller input and declares no client-fault response"* |
| **invented** — a required **cookie** parameter added to `getDashboardSummary` (`{"in": "cookie", "name": "am_scope", "required": true, "schema": {"type": "string", "minLength": 1}}`), no client-fault response | **46 passed**, and the whole contract scope **367 passed**. `test_the_input_less_operation_set_is_exactly_the_pinned_one` still calls it input-less. |
| **invented, the honest repair of the above** — the same cookie **plus** a `422` | **red**: *"takes no caller input but declares ['422']"* — the rule refuses the correct declaration |

`_takes_caller_input` (`test_openapi_document.py:297-330`) counts `path`, `query`, a header
other than `X-Correlation-Id`, and a body. **OpenAPI 3.1 has a fourth parameter location,
`cookie`**, and the docstring's own list omits it. So an operation that gains a malformable
cookie is still classified input-less: the rule accepts it with no client fault and refuses it
with one — wrong in both directions, for exactly the case the derivation exists for (*"so an
operation that later gains a parameter is pulled back under the rule without anyone
remembering to"*). The literal pin does not help, because it is computed with the same
function. **Low** today (the surface declares no cookie parameter, and the BFF's `am_session`
cookie never reaches the API), and a one-word repair. The stream's two directions are real, and
it reported honestly that its first version missed path-item parameters.

### `F-5c` — the historical-section control (`test_doc_prose_facts.py`)

Baseline: **21 passed**.

| mutation of `docs/program/CURRENT_STATE.md` | result |
|---|---|
| `W46-JUDGE-A`'s — `### A note on how the historical record is kept` directly under the live heading | **red**: *"the live section survives truncation but makes no claim this guard can read -- the non-vacuity half of the control (F-5c) is failing"* |
| control for mine — a stale sentence, *"The migration head is \`0010_run_terminal_detail\`."*, after the live section's surface-triple paragraph | **red**: `test_the_scanned_docs_state_the_migration_head_this_tree_has` — *"'migration head is \`0010_run' names head 0010, tree has 0011_document_section"* |
| **invented** — the same stale sentence, preceded by a fenced shell block whose comment reads `# the historical record below is kept verbatim; do not edit it` | **21 passed**. The stale head is hidden. |

Two things fail together. `_HISTORICAL_HEADING` is `^#+.*historical record.*$` under
`MULTILINE`, so **any line that begins with `#` and mentions the historical record matches — a
shell comment in a code fence is a "heading"**. And non-vacuity is *"at least one claim survives"*: a boundary placed **after**
the first claim leaves one claim standing and blinds the scan to everything below it. The
stream's comment in the test says the opposite — *"a too-early heading truncates all of them
together, not just one, so this stays exactly as strong a guard"* (`test_doc_prose_facts.py`,
in the `F-5c` block) — which holds only when the premature boundary precedes every claim.
**Low–medium**: the section that closes wave 46 will carry several claims (tagged tip, surface,
head) and very likely a command block; a shell comment mentioning the record is a natural thing
to write there. The stream did report the premise gap (`TAGGED_TIP_CLAIM` has no match in
today's live section) instead of editing a file it did not own, which was right.

### `F-5a` — the fresh-deployment guard (`test_dashboard_summary_over_a_fresh_deployment.py`)

Baseline: the new file **3 passed**; `W46-JUDGE-A`'s scope plus the new file
(`tests/integration/api tests/integration/composition
tests/contract/domain_p02/test_project_section_catalog.py`) **612 passed** (= 609 + 3).

| mutation of `src/auditmanager/dashboard/repository.py` | the new file | the 612-scope |
|---|---|---|
| `W46-JUDGE-A`'s — `_filled` drops zero members; the unclassified row only when non-zero | **red** (*"assert 0 == (14 + 1)"*) | — |
| the stream's — the `calls == 0 → None` branch removed | **red**, two tests (*"spend must be absent, not a zero labelled measured (F-1)"*) | — |
| **invented** — `_filled` returns `(member, 0)` for every member and the unclassified row is `0`: every verdict, state and section count is **never read from the database** | **3 passed** | **612 passed** (combined with the next) |
| **invented** — `basis="measured"` unconditionally | **3 passed** | **612 passed** (combined) |

**The guard proves absent-is-not-empty and nothing about present-is-counted.** Its three states
are all zeros except `spend`, and its one `model_call` row is `measured`, so a repository that
invents a zero for every panel, or labels estimated spend as measured, is indistinguishable
from the real one to every test that exists. Against the real code the numbers are right — X2
drove `pending: 3`, `published: 1`, `<none>: 1` and `estimated` — so this is a missing guard,
not a live defect. It is `R-23`'s addendum (*a zero that nothing computed is an invented number
too*) aimed at the only test that observes a row, and the second invented mutation is `F-1`'s
own subject (a basis the data did not earn). **Medium**: the dashboard is a page of counts, and
the only guard on its counts cannot fail on a count. Repair: one state with a `KM` document, a
finding and an `estimated` call, asserting the non-zero numbers.

**What the stream did right, checked:** both of its quoted failures reproduce exactly as quoted;
the fresh database is really created, migrated and dropped (the lane's postgres held no
`w46_spend_fresh_*` database afterwards); and the guard drives the shipped `DashboardAdapter`
through the real ASGI app rather than a stand-in.

## X5 — the integrator's own changes — **three sentences false, one debt check that cannot fail**

### `8ad692f`'s prose, sentence by sentence, against the tree

| file:line | sentence | true of `d5c9be5`? | measured by |
|---|---|---|---|
| `web/src/app/bff/v1/[...path]/route.ts:22-23` | *"Those figures are **twenty operations across seventeen paths**, which is what the frozen document declares after the `W45-BLOCKS` reseal that added `getVersionBlocks`."* | **False.** The numbers were moved and the clause that dates them was not. After `W45-BLOCKS`'s reseal the document declared 16 paths / 19 operations (`830fd76` and `alpha-w45`: 16/19); 17/20 is `W46-SEAL`'s reseal (`d7ac848`: 17/20, the first to contain `getDashboardSummary`). The next line's history (*"said fifteen and twelve once and sixteen and thirteen after that"*) also stops one reseal short. | `git show <c>:contracts/api/v1/openapi.json` counted for `830fd76`, `alpha-w45`, `d7ac848` |
| `docs/program/P02_SEAMS.md:600-601` | *"…and twenty after `W46-SEAL` added `getDashboardSummary` under `R-44` on 2026-09-28."* | **False date.** `W46-SEAL`'s reseal `d7ac848` is dated 2026-09-25 18:43 and was merged at `57e519b` on 2026-09-25 19:11; the lock's own note says *"Resealed 2026-09-25 by W46-SEAL"*. 2026-09-28 is the date of `8ad692f`, the repair that wrote the sentence. The rest of the paragraph (*"Twenty operations, sealed"*, `:591`) and the table row (`getDashboardSummary` → `GET /dashboard`) are true. | `git show -s --format=%ci d7ac848 57e519b` |
| `docs/program/ALPHA_ROADMAP.md:34-37` | *"**Corrected a fourth time 2026-09-28.** … This block has now been wrong three times in three days"* | **False now.** The sentence was written for the third correction (`git show 8ad692f^:docs/program/ALPHA_ROADMAP.md`: *"Corrected a third time 2026-09-25 … three times in three days"*); the fourth correction changed the heading and the numbers and kept the tally. Four corrections, 2026-09-22 to 2026-09-28. The triple on `:35`, *17 paths / 20 operations / 61 schemas*, is true and is read by `test_doc_prose_facts.py`. | `git show 8ad692f -- docs/program/ALPHA_ROADMAP.md` |
| `infra/deploy/README.md:26`, `:150` | *"the twenty operations under uvicorn"*, *":8000 the twenty operations, mounted by the proxy at /api/v1"* | True. The served API logs *"operations=20"*. (`Dockerfile.api:1`, which the `:26` row describes, still says *"the fifteen operations"*: that is `D-99`, registered, in a file extension the guard does not read.) | X2's stack |
| `infra/deploy/README.md:102-103` | *"An application with no token configured answers `authentication_required` to every one of the twenty operations"* | **Unobservable as written, and off by one where it can be observed.** `create_asgi_app` without `AUDITMANAGER_API_TOKEN` refuses to construct (`ConfigurationError … refuses to start`), as the README's own next paragraph says. The one way to reach the seam without a key — application built with a token, seam assembled from an environ without one — answers **`401` to 19 operations and `200` to `issueToken`**, which is open by design (`security: []`). The sentence counts the open exchange among the refused. It said *"nineteen"* before, with the same imprecision; `8ad692f` moved the number. **Low.** | scratch in-process probe, all 20 operations driven once |
| `infra/deploy/serve.py:4` | *"`create_asgi_app` (the twenty operations)"* | True (*"operations=20"*). | X2's stack |
| `web/src/shared/api/authorization.ts:24` | *"The `authorization` category of the catalog, as the twenty operations can return it."* | True as a union: 19 operations declare `401` and `403`, `issueToken` declares `401`. | the contract, tabulated |

Two more of the integrator's own sentences, found while measuring: the describe block *"the
nineteen seam operations"* that `8ad692f` added the twentieth row to (X6), and
`CURRENT_STATE.md`'s live section (also `8ad692f`), which still says *"Both streams — `W46-SEAL`
and `W46-DASH` — are in the tree; its closing judge found the merged tree **red** and the
integrator is repairing it"*. Its load-bearing claims — merged, not gated, not a release,
17/20/61, catalog 22 — are true; the sub-stage it describes is over. Low, and the wave's close
rewrites it anyway.

**Cost.** None of the three false sentences is on a screen or in a guard's path. Each is the
same defect: **a count was corrected and the words around it were not**, which is `D-104`'s
thesis (*every prose guard here checks a number*) happening inside the repair of a
number-guard's red. `route.ts:23` is the costliest, because it is the file the programme calls
*"the fifth stale count"* and whose paragraph exists to be read.

### `D-106`–`D-109`: each row's check command, run literally

| row | command | the row says it prints | it printed | can it print anything else? |
|---|---|---|---|---|
| `D-106` | `curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer …" '<api>/projects?bogus=1&limit=1'` | `200` | **`200`** (my API, `:56391`). Also `GET /dashboard?project_uid=…` byte-identical to plain, `GET /decisions?project_uid=…` `200` | yes: a surface that refuses unknown parameters prints `422` |
| `D-107` | `grep -rn 'section' web/src/features/upload-document web/src/widgets/upload-panel --include=*.tsx \| grep -v 'className\|<section\|</section' \| wc -l` | `0` | **`0`** | **Not for the two direct implementations.** In the disposable tree: (1) the upload command sending `section: 'KM'` (`use-upload-document.ts` is `.ts`, outside `--include=*.tsx`) → **`0`**; (2) a `<select className="am-input" name="section">` in the form (removed by `grep -v className`) → **`0`**. Both files restored byte-identical to `d5c9be5`. A check that prints `0` whether or not the product can set a section does not measure the debt it names. |
| `D-108` | `grep -c 'e2e:pc01' Makefile` | `0` | **`0`** | yes: a target invoking `npm --prefix web run e2e:pc01` prints `1` |
| `D-109` | `grep -rn 'контракт\|операци' web/src --include=*.tsx \| grep -v shared/api/generated` | (nothing stated) | **one line**: `web/src/_pages/logs/ui/logs-page.tsx:31` (*«…операции, которая отдала бы их приложению, в договоре нет…»*) | It under-reads the debt by an order of magnitude. `grep -rniE 'контракт\|операци\|договор' web/src --include=*.ts --include=*.tsx \| grep -v shared/api/generated` → **24 lines**, 23 of them in `.ts` model files that produce on-screen failure text (*«Клиент получил нечто, что не смог разобрать как отказ по контракту.»* ×5, *«…вне контракта этого клиента»* ×6, `catalog-message.ts` ×5, …) and one capitalised (*«Операция ничего не создала…»*), which the case-sensitive pattern misses. The row's own claim — *"`W46-WIRE` removes both words from the dashboard"* — is **true**: no match under `web/src/widgets/dashboard` or `web/src/_pages/dashboard` either way. |

**`D-107` is the one that matters**: the memory rule this programme keeps — *every guard needs a
test proving it can fail* — applies to a register row's check, because the next person reads
*"prints 0 today"* as *"the product still cannot set a section"*. Reproduce with the two
mutations above in any disposable copy.

### `d5c9be5`, the join repair

Two comments in `section-breakdown.ts`: *"fourteen codes"* → *"fourteen section codes"*. Both
sentences are true of the file (`PROJECT_SECTIONS` seeds fourteen members; the unclassified
count is kept beside them), and X6 shows the commit changed nothing else. Its message says the
guard's noun set *"belongs with `D-98`"*; `D-98`'s row names *declarations, models, copies,
places* and was not amended, so that observation lives only in a commit message. Low.

## X6 — did the merge lose a test? — **No. Nothing was lost, byte or node.**

**The instrument.** Five trees extracted with `git archive` into `/root/w46x-tree-{a130,base,
spend,wire,tip}` (`130200d`, `fbea618` = the streams' common base, `bb985ce` = `W46-SPEND`'s
tip = `9a295aa^2`, `c26340f` = `W46-WIRE`'s tip = `1c38c52^2`, `d5c9be5`), each with the
worktree's `.venv` and `web/node_modules` linked in. Removed at the end.

### Bytes

- **Every file each stream changed, stream tip against merged tip**
  (`git rev-parse <tip>:<path>` vs `git rev-parse d5c9be5:<path>`): `W46-SPEND` 16 of 16
  identical; `W46-WIRE` 30 of 31 identical. The one difference is
  `web/src/widgets/dashboard/model/section-breakdown.ts`, which is `d5c9be5`'s own two-comment
  edit (*"fourteen codes"* → *"fourteen section codes"*) — the whole of that commit.
- **Every file in the merged tree (1354), traced to its origin**: for each path, the tip's blob
  must equal the stream's blob where exactly one stream changed it, and the base's where none
  did. Three paths are not a stream's: `docs/program/dispatch/PORT_REGISTRY.md` and
  `docs/program/dispatch/W46-JUDGES-XY.md` (the dispatch commits `36e5dcf`, `f2f1aa2`) and
  `section-breakdown.ts` (`d5c9be5`). No path was changed by both streams.
- **No evil merge.** `git merge-tree --write-tree <m>^1 <m>^2` reproduces the recorded tree of
  both merges exactly: `9a295aa` → `656d09f8…` = recorded; `1c38c52` → `4438382b…` = recorded.

### Node ids

`pytest --collect-only` with the canonical ignores in each tree (the foundation suite refuses
`--collect-only` by design, `tests/integration/foundation/conftest.py:581`; that directory is
byte-identical from `130200d` to `d5c9be5`, so its 35 nodes cannot differ), and
`vitest list --json` for the frontend. With `B` the base, `S`/`W` the stream tips and `T` the
merged tip, the check is `T == (B − (B−S) − (B−W)) ∪ (S−B) ∪ (W−B)`:

| suite | `130200d` | `fbea618` | `W46-SPEND` | `W46-WIRE` | `d5c9be5` | `T == expected` |
|---|---|---|---|---|---|---|
| pytest (without foundation) | 2470 | 2470 | 2474 | 2470 | 2474 | **true**, nothing missing, nothing unexpected |
| vitest | 1120 | 1121 | 1121 | 1118 | 1118 | **true**, nothing missing, nothing unexpected |

- **pytest.** `W46-SPEND` removed `test_every_operation_can_report_not_found_or_validation` and
  added the five named in X1. `W46-WIRE` changed no node.
- **vitest.** `130200d → fbea618` added one: `the nineteen seam operations > getDashboardSummary
  is GET /dashboard` (`8ad692f`). `W46-WIRE` removed 13 and added 10, and **three of those
  pairs are renames, which a count would have hidden**:
  `declares exactly the four roots` → `…five roots`; `invalidates the history, the detail, the
  run finding list and the journal` → `…and the dashboard`; and
  `says that a document's section is stored nowhere and checked nowhere` →
  `says that a document's section is stored and checked when an upload names one, and the
  product's form does not offer that field`. Each rename is the stream's stated intent (the
  fifth query-key namespace; `F-3`'s false sentence rewritten), and the renamed test asserts the
  new behaviour rather than dropping the old assertion. The other ten removals are the three
  deleted aggregators' cases in `dashboard.test.ts`, replaced by seven render cases (`F-5b`).

### One thing the set algebra surfaced — the integrator's own

**`web/tests/contract/seam-operations.contract.test.ts:90` names its block
`'the nineteen seam operations'`, and the file header (`:6`) says *"the nineteen operations at
their frozen methods and paths"*.** `8ad692f` added the twentieth row to `SEAM_OPERATIONS`
inside that block and left both. `vitest list` now prints a test called
`the nineteen seam operations > getDashboardSummary is GET /dashboard`. The surface-prose guard
reads `web/src`, not `web/tests`, so nothing reddens. Low; it is the same sentence-kind the
wave repaired six of elsewhere.

```
grep -n 'nineteen' web/tests/contract/seam-operations.contract.test.ts   # -> lines 6 and 90
```

## Off the trail

The trail I was handed: the gate, `F-1`'s layers, the reseal's documents and digests, the
three named guards, the integrator's named prose and four debt rows, and a merge-loss check.
Where I went that none of it points, and what came back:

| where | why the trail does not lead there | what came back |
|---|---|---|
| **the served document against the frozen one** (`create_documentation_app().openapi()` through the programme's own conformance engine, at `f50e656`, `069f656`, `d5c9be5`, then a Pydantic-only drift run through the whole battery) | X3 asks whether the five documents moved together; nothing asks whether the application still **conforms** to them — the whole meaning of *contract-first* | **Nothing in the gate compares them.** The engine sees the drift at `f50e656` (1 difference); the whole canonical battery with the same drift re-created at the tip: **2504 passed**, identical to X1. The live test `W13-CONF` handed over as *"one file … deliberately not written"* was never written on any branch (X3) |
| **a real `/dashboard` body validated against the frozen schema** (Draft 2020-12, the suite's own checker) | X2 asks whether layers turn absence into zeros, not whether the wire is what the contract says | **Valid in all four states**; invalid against the pre-reseal contract. And `test_schema_conformance.py` has **no `DashboardSummary` case**, so nothing in the battery does this for the new operation (X2) |
| **the dashboard's own client-side merges** (`verdict-breakdown.ts`, `section-breakdown.ts`) | X2 names record, view, serializer and generated type; the screen's model is one layer further | **X2-a**: rows the server did not send render as `0`; unknown members vanish |
| **who invalidates `['dashboard','summary']`** (`grep -rn 'queryKeys.dashboard' web/src`) | the brief never mentions the cache | **`createProject` does not.** `d4f7b0e` says *"invalidate the dashboard summary at every mutation that changes it"* and wires upload, start-run, a run's terminal reading and decisions. X2 measured that creating a project changes the answer (`documents_by_project` `[]` → one row; the run panel's *«Проектов пока нет»* depends on it). `useCreateProject` invalidates `['projects']` only, which does not reach `['dashboard', …]` (`query-keys.ts:51`, a separate namespace), and the app's queries are `staleTime: 30_000` with `refetchOnWindowFocus: false` (`_app/query-client.ts:34-35`). So for 30 s after a dashboard read, a new project is missing from it. **Low**; static reproduction — I did not drive it in a browser |
| **`infra/deploy/**` beyond the two files `8ad692f` edited** | X5 names `README.md` and `serve.py` | **Nothing new.** `Dockerfile.api:1`, `deploy.sh:215,837`, `alpha.env.example:56,117`, `compose.server.yml:217`, `nginx.conf:7,78` still say *fifteen*/*twelve* — `D-99`'s registered eight, in extensions the guard does not read. The README's `:26` row now says *twenty* about a Dockerfile whose first line says *fifteen*; `D-99` covers it |
| **the lane's databases after the fresh-deployment guard ran** (my own runs of it, four times, plus the gate) | the stream's report says the fixture creates, migrates and drops | **Nothing left behind**: `pg_database` in `gate-w46j-postgres-1` held only `audit_w46j`, my `audit_w46x_judge`, and the three system databases |

## Findings, most severe first

*pending*

## What I could not answer, and why

- **The stale dashboard after `createProject`, in a browser.** Reproduced statically (the
  invalidation sites, the key namespaces, `staleTime: 30_000`, and X2's measured change in the
  answer); I started no Next server, because the screen and the journey are `W46-JUDGE-Y`'s,
  and one measurement per lane kept me to the API.
- **Each invented `F-5a` mutation alone across the 612-scope.** I ran the two together once
  (612 passed) and each alone against the new file (3 passed each). They change disjoint
  fields — counts and `cost_basis` — so neither can mask a test that would catch the other; I
  did not spend two more five-minute runs to show that separately.
- **The cookie mutation (`F-2`) beyond the contract scope.** 367/367 in `tests/contract`; I did
  not run the whole battery with it. Whether an integration test would see a cookie parameter
  on the frozen document depends on the served-vs-frozen question in X3, which I did run in
  full for a different drift.
- **Whether `W46-SPEND`'s *"five more passing nodes"* arithmetic in its §6 is exactly right in
  words.** The numbers agree with mine (X1: 2500 → 2504 nodes, 2499 → 2504 passing); its
  sentence attributes the five to *"three … one net-new … and S4 adding no new test"*, which
  sums to four unless the red-turned-replaced node is counted, which the sentence does not say.
  A stream report's wording is `W46-JUDGE-Y`'s subject (Y6), so I leave it there.
- **Anything about the deployed stand** (`127.0.0.1:31500`). Not touched, read or otherwise;
  `infra/deploy/verify-deployed.sh` inspects a running container, and no container outside
  `gate-w46j*` is mine to touch.
