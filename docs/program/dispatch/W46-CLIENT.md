# W46-CLIENT — the screen stops inventing what the server stopped sending

**task_id:** `W46-CLIENT` · **wave:** 46, sub-stage C · **lane:** `gate-w46b`
**worktree:** `/root/w46dash` · **branch:** `agent/w46-client`, based on the dispatch commit
**depends_on:** `W46-WIRE`, `W46-JUDGE-X`, `W46-JUDGE-Y`

Read `docs/program/dispatch/W46-STAGE-C.md` first. Then read both judges' reports with
`git show agent/w46-judge-x:docs/program/reviews/W46-JUDGE-X.md` and
`git show agent/w46-judge-y:docs/program/reviews/W46-JUDGE-Y.md`: sections 2, 5 and 6 of Y's,
and findings X-3, X-6 and X-9 of X's. Their findings are your premises. Where this brief and a
report disagree, the report was measured, so say which one is wrong and why.

## C1 — an omitted row is a fault, never a zero (X-3, Y5-a)

`section-breakdown.ts:37-40`, `verdict-breakdown.ts:15-24` and `run-activity-panel.tsx:76,79`
fill every member the response omits with `0` and call it *"its true zero"*. They also silently
drop any value they do not know. Under judge A's server mutation, the API sent
`section_breakdown: []`, `findings_by_verdict: []` and `by_state: []`, and the screen rendered
nineteen zeros identical to an honest answer (Y, section 5). That is `F-1` moved from the server
to the browser.

**The rule:** the contract promises every member of each closed vocabulary. A response that
omits one, or carries one the vocabulary does not have, is broken. The panel says so with the
failure shape `dashboard-failure.ts` already has, and **shows no numbers.** Only a zero the
server sent may render as a zero. `R-39` still applies: no field names, no ids, no transport,
and no *контракт* or *операция*.

## C2 — each number in its place (Y5 M5/M6, the screen half of X-2)

The render guard proves that no number is invented. It does not prove that any number is in
its place:
- Every section showing its neighbour's count passes the whole suite (79 / 1118), and so does
  *принято* swapped with *отклонено*.
- The one per-section check, `dashboard.test.ts:207-208`, is `toContain('4')` anywhere on the page.

Assert per row, keyed by the markup's own data attributes, for the section, verdict and
run-state panels. **Show both of Y's mutations failing**, then one of your own.

## C3 — every mutation that moves a number refreshes it (X-6, Y6-a)

`features/create-project` (`use-create-project.ts:31-34`) does not invalidate
`queryKeys.dashboard.summary()`. With `staleTime: 30_000`, a return to `/dashboard` after
creating the first project still says *«Проектов пока нет.»* That makes the sentence at
`query-keys.ts:165` false. Fix the hook. Then add a test that maps **every** mutation hook under
`web/src/features/**` to whether it invalidates the dashboard key, so a mutation added later that
forgets fails. **Show it failing** with `create-project`'s line removed.

## C4 — the sentences about which section is analysed (Y2-a, Y2-b, X-9)

- **Y2-a.** The server accepts a document stored as `KM` and analyses it with the same profile
  (Y, section 2: published, three findings). Yet `/dashboard` says *«…АР — единственный
  анализируемый раздел: 0»* beside *КМ: 1* (`sections-panel.tsx:51`), and the project screen
  calls it *правило приёма* (`project-sections.tsx:105-108`, `:120`). **What is true:** the
  analysis is built for the text of АР documents, and a document the server stores under another
  section is analysed by the same profile. Make every sentence say that and nothing more. Whether
  intake should refuse, or a run skip, is **not** yours (`D-110`).
- **Y2-b.** The verdict caption explains *«ожидает решения»* (`verdicts-panel.tsx:52`), a label
  that appears nowhere; the row it qualifies reads *«не решено»*. Make them one word.
- **X-9.** Comments that still say `spend` is *typed required today*: after the reseal it is
  optional (`types.gen.ts:484`). Find all of them; X counted four.

## C5 — the journey, driven again

This stage changes a screen, so drive `npm --prefix web run e2e:pc01 -- --origin <your Next>
--phase all --out <dir>` against API `127.0.0.1:56381` and Next `127.0.0.1:56383`, and quote the
summary. **Record your own gate in your report.** `W46-WIRE.md` recorded none, and Y found the
log overwritten (Y6-b).

## allowed_paths

```
web/src/**  EXCEPT web/src/shared/api/generated/**
web/tests/**
tests/e2e/pc01/journey/manifest.json · tests/e2e/test_pc01_journey_conformance.py
docs/program/W46-CLIENT.md
```

## forbidden_hotspots

`contracts/**`, `web/openapi/**`, `web/FRONTEND_LOCK.json` and `web/src/shared/api/generated/**`
belong to `W46-GUARD`, live in `/root/w46seal`. Also forbidden: `src/**` · `db/**` · the rest of
`tests/**` · `infra/**` · `web/docs/**` · `docs/program/CURRENT_STATE.md` ·
`docs/program/DEBT_REGISTER.md` · `docs/program/dispatch/**` · `Makefile` · `package.json` · any
container not named `gate-w46b*`. **The owner's stand is read-only.**

## Verification

The worktree is provisioned. Baseline: `d5c9be5` gated `GATE OK` under `W46-JUDGE-X`, with
frontend 1118 in 79 files. `ce25e14` changed one frontend test file's comment. During
development run `npm --prefix web test` and `npm --prefix web run typecheck`. At the end run
**one** `make gate > /root/w46c-gate.log 2>&1`, and take the verdict from the `GATE OK` line.
Before starting it, check `free -g`, and confirm that no `make gate` whose cwd is under `/root/w46*`
is running. **Exit status 137 is the OOM killer, not a result.**

## Discipline

Open `docs/program/W46-CLIENT.md` before your first measurement. **Commit after each step:** a
restart kills you, and only committed work survives it. Show every new guard failing under a
quoted mutation, then revert. **Kill only by PID**, and only processes confirmed to be your own
descendants (`pstree -p`, `readlink /proc/<pid>/cwd`); never use `pkill -f` or `killall`. When
you finish, stop your API and Next by PID. Do not tag, push or merge, and do not keep working
after you hand back.
