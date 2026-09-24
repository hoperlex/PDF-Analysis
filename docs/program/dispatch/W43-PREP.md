# W43-PREP — four screens prepared, and the note that is the real deliverable

**task_id:** `W43-PREP` · **wave:** 43, stage A · **lane:** `gate-w43b`
**worktree:** `/root/w43prep` · **branch:** `agent/w43-prep`

`R-23`'s same-day addendum, ruled by the owner and landed in
`OWNER_RULINGS_2026-09-17.md` §3.11: **blocks, optimisation, logs and workers** are wanted, each
is wired up as its vertical lands, and **the front-end preparation may be done now.** Read
`docs/program/dispatch/W43-PLAN.md` first.

## The rule these four make general

> **The front end carries the structure before the back end does, with honest stubs.**
> A section that does not exist yet looks like a finished section saying it is unavailable —
> not missing, and not pretending to work.

It has already run on the fourteen project sections: thirteen stubs, one working, and the screen
saying plainly that sections are navigation. `web/src/widgets/project-sections/ui/project-sections.tsx:115`
is the worked example, and `web/src/shared/ui/route-placeholder.tsx` is the component —
`screen`, `route`, `promise`.

## P1 — four places in the navigation

An address each, reachable, in the frame. **You own `web/src/_app/app-frame.tsx` this wave**;
`W43-COMPARE` does not, and may ask you through the integrator for a link.

The frame currently carries two `am-app__nav` links (knowledge base, password). Six will not fit
the way two do — **that is a layout decision and it is yours**, but it is a decision, so argue it
in the report rather than letting it happen.

## P2 — a promise, not a "not implemented"

`RoutePlaceholder`'s `promise` prop takes **one sentence about what will be here**. Not
*«раздел не реализован»*. The default sentence in the component is the generic one; four screens
sharing it would be four screens saying nothing.

**And a promise must be one the programme has actually made.** Workers are excluded outright by
`PROTOTYPE_PROFILE.md` §7 — promising them is promising something nobody decided to build. Say
what is true about each.

## P3 — the data shape on paper, and this is the deliverable a stream skips

**For each of the four, write down what the screen would show and check every field against the
contract.** Where the field exists, name it. Where it does not, **that is a future reseal and
seeing it now is the whole point** — `R-11` reverted a wave over a reseal found at the end.

What is already measured and must be verified rather than copied from here:

- **Blocks** — page-level block markup and a vector graph per block. The corpus has
  `coords_norm = [0,0,1,1]` on **all 28 249** blocks and `polygon_points` empty. There is no
  geometry to draw. **Check this against the corpus yourself** (`.local/`, invisible to git —
  `corpus/MANIFEST.json` orients).
- **Optimisation** — tuning models and stages, including per section. We have **one** visible
  analysis stage against legacy's seventeen.
- **Logs** — an execution journal. It exists on the server; **there is no contract operation to
  read it.** Confirm against `contracts/api/v1/openapi.json`'s 18 operations.
- **Workers** — distributed executors. One sequential in-process executor; `PROTOTYPE_PROFILE.md`
  §7 excludes the job/attempt framework.

**A false note here is worse than no note**, because the next wave budgets against it. The judge
will check each claim against the contract and the corpus independently.

## P4 — no invented numbers

The addendum's fourth rule, verbatim: *«Ни одной выдуманной цифры. Пустой экран честнее
правдоподобного.»* No counts, no placeholder totals, no sample rows that look like data.

## allowed_paths

```
web/src/app/{blocks,optimisation,logs,workers}/**   (new; names are yours to choose and to argue)
web/src/_pages/**                                    (new directories only)
web/src/_app/app-frame.tsx
web/src/shared/ui/route-placeholder.tsx
web/tests/**
docs/program/W43-PREP.md
```

## forbidden_hotspots

`web/src/_pages/stage-comparison/**`, `web/src/widgets/stage-comparison/**` and
`web/src/app/projects/**` — **`W43-COMPARE` owns those**, live in `/root/w43comp` ·
`contracts/**` · `src/auditmanager/**` · `db/**` · `infra/**` · `web/FRONTEND_LOCK.json` ·
`web/src/shared/api/generated/**` · `docs/program/DEBT_REGISTER.md` ·
`docs/program/dispatch/**` · `Makefile` · any container not named `gate-w43b*`.

## Deliverables

1. Four screens, committed step by step.
2. `docs/program/W43-PREP.md`, opened **before** the first measurement, carrying **P3's four
   notes with the command that checked each one**.
3. Every guard shown to fail, with the mutation quoted.
4. The same honest statement `W43-COMPARE` owes: **which instrument reached your screens without
   being told to.** Five new screens are the first real test of wave 41's coverage repair and
   wave 42's contrast floor, and the judge is measuring exactly that.
5. Anything outside the grant: reported, not repaired.

## Verification

Same as the sibling brief, in lane `gate-w43b` (`56270`, `59870/59871`), log
`/root/w43b-gate.log`. **Run the whole frontend suite**, not the tests you were thinking of.

## Discipline

Commit each step. Do not tag, push or merge.
