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

## X3 — the reseal: five documents or four?

*pending*

## X4 — the three guards `W46-SPEND` claims, mutated by me

*pending*

## X5 — the integrator's own changes

*pending*

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

*pending*

## Findings, most severe first

*pending*

## What I could not answer, and why

*pending*
