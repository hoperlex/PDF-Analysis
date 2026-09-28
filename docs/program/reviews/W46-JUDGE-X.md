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

## X2 — `F-1` re-driven

*pending*

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
