# W46-DASH — four panels, and the structure of what has no numbers yet

**task_id:** `W46-DASH` · **wave:** 46, sub-stage A · **lane:** `gate-w46b`
**worktree:** `/root/w46dash` · **branch:** `agent/w46-dash`

`R-44`: **all four panels, in wave 46, without waiting for the deploy.** `R-25` already fixed how
a panel behaves when the data is not there: **real numbers for what exists, the structure shown
without numbers, and an honest caption saying why.**

## D1 — the four panels

| panel | source |
|---|---|
| documents per project | `Project.document_count` — **exists today** |
| findings by verdict | `listDecisions` with `category` and `verdict` — **exists today** |
| run activity and spend | `listRuns`; `RunStatus` carries `cost_micros`, `cost_basis`, `model_call_count` |
| **per-section breakdown** | **`W46-SEAL`'s new aggregate read** — the only panel that needed `R-40` |

**You consume `W46-SEAL`'s operation; you do not build a second source.** It is live in
`/root/w46seal` and its generated client arrives at merge. **Until it does, build against the
contract's declared shape, not against a guess** — and say in your report which parts you could
not drive because the operation was not merged yet.

## D2 — what a panel does when it has nothing

`R-25`'s rule, and `D-46`'s vocabulary makes it sayable now: **absent, empty and not-yet-produced
are three different answers.** A project with no runs, a section with no documents and a verdict
nobody recorded must not render identically. Wave 45 set the precedent on `/blocks`:
`NotApplicableState` against `EmptyState`, so **a reviewer reads a state rather than counting a
list.**

**No invented numbers.** `R-23`'s addendum: an empty panel is more honest than a plausible one.
**A zero that nothing computed is an invented number too.**

## D3 — the thirteen sections have no data and the screen says so

`R-25` ordered them by how textual they are — **ПОС, ТХ, ПБ first** — and the reason is measured:
the AR vertical is **5 175 lines** plus a content-hashed prompt bundle plus 16 fixtures, and a
section whose answers live in drawings reuses none of it. **Only AR is analysed today.**

So the per-section panel shows **structure for fourteen and numbers for one**. `R-39` lets the
screen say why, **in the words of the subject**: *«по этому разделу анализ ещё не делается»* is
allowed and useful. **The prohibition that stays: no operation ids, no field names, no
transport.**

## D4 — the instruments reach you by themselves now

Wave 44 derived the screen set from the route tree, and wave 45 proved it on a new screen. **The
language guard will render your dashboard and the contrast census will measure it without you
adding anything to a list**, and `R-33`'s 3:1 border floor applies to every border you draw.

**If you find yourself editing `SEEDS` or `UNREACHABLE_IN_ONE_PASS` to make something pass, that
is a finding to report, not a step to take.** Wave 45 added seven entries to that list with a
named reason each; a judge checked every one individually, and that is what will happen to yours.

**And the bar wraps now** (`D-93`): wave 43 put a horizontal scrollbar on every screen by adding
four links, and nothing in the gate could see it. **A dashboard is the widest thing this product
has.** Drive it at 780 px.

## allowed_paths

```
web/src/**  EXCEPT web/src/shared/api/generated/**
web/tests/**
docs/program/W46-DASH.md
```

## forbidden_hotspots

`contracts/**` · `web/openapi/**` · `web/FRONTEND_LOCK.json` · `web/src/shared/api/generated/**`
— **all `W46-SEAL`'s**, live in `/root/w46seal` · `src/auditmanager/**` · `db/migrations/**` ·
`tests/**` (the Python tree) · `infra/**` · `docs/program/DEBT_REGISTER.md` ·
`docs/program/dispatch/**` · `Makefile` · `package.json` · any container not named `gate-w46b*` ·
**the owner's stand is read-only.**

**`tests/e2e/pc01/journey/manifest.json` is the integrator's** (`D-89`). You add an address, so
**you will need a row in it — report what it should say; do not write it.**

## Deliverables

1. The dashboard, committed step by step.
2. `docs/program/W46-DASH.md`, opened **before** the first measurement.
3. Every new guard shown failing, with the mutation quoted.
4. **Rendered evidence of both palettes at 780 px**, and a plain statement of which panels you
   could drive against real data and which you could not.
5. The journey manifest row, written out for the integrator to apply.
6. Anything outside the grant: reported, not repaired.

## Verification

Lane `gate-w46b` — PostgreSQL `127.0.0.1:56380`, S3 `59980`/`59981`. Provision as usual. **Run
the whole frontend suite**, not the tests you were thinking of. `make gate > /root/w46b-gate.log
2>&1`, verdict from the **`GATE OK` line**. `alpha-w45`: **2493 / 35 / 1110 in 78**.

## Discipline

Commit each step. Do not tag, push or merge.
