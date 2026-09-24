# W44-SEE — derive the subject from the tree, and repair what that makes visible

**task_id:** `W44-SEE` · **wave:** 44, sub-stage A · **lane:** `gate-w44b`
**worktree:** `/root/w44see` · **branch:** `agent/w44-see`

Read `docs/program/dispatch/W44-PLAN.md` first. Your rows are `D-88`, `D-82`, `D-95`, `D-90` and
`D-94`, all measured in `docs/program/DEBT_REGISTER.md`.

## S1 — `D-88`: the screen set is a literal, so a new screen is invisible

Wave 41 made `rendered-language.guard.test.ts` derive **which contract members** must be rendered
from the contract. **It left which screens are rendered a hand-written array** — line 795,
`const SCREENS = [...]` — and `web/tests/unit/styles/screens.ts` is a hand-written import list.

Wave 43 measured the cost. `W43-JUDGE-A` put English prose on four new screens, four different
sentences, and **the whole frontend suite stayed green: 73 files, 1047 tests, 0 failed.** The
nav labels *are* covered, because `AppFrame` is in `SCREENS` — so the guard sees a word in the
panel and not one word on the page that panel opens.

**And the contrast census is two defects, not one:**

1. a screen carrying its own `*.module.css` is seen by `import.meta.glob`, and the census then
   says something **false** — *"no screen in `screens.ts` renders an element they match"* — when
   the screen renders them and `screens.ts` does not render the screen;
2. a screen built from the global `am-*` classes is **invisible in both directions**, and silence
   reads as coverage.

**The repair three independent sessions converged on: derive the screen set from the route tree
under `web/src/app`, the way `tests/e2e/test_pc01_journey_conformance.py` already does with
`rglob("page.tsx")`.** A screen that exists is a screen the instruments render.

**The hard part is not the glob, it is what a derived screen needs to be rendered**: props,
identifiers, cache states. Say how you solved it, and **say what a screen must do to opt out** —
because there will be one, and an opt-out that is a silent `catch` is the defect returning in a
new costume. Wave 41's own words, which your predecessor wrote and which still hold: **coverage
is derived from the contract; the seeds are not. The question is derived; a human answers it.**

**The falsification is the deliverable.** Wave 43's probe, verbatim: English prose on a screen,
and a border at 1.08:1 on a really-rendered element. Both must redden **and name the screen**.

## S2 — `D-82`: three English strings no instrument can render

`LoadingState` renders `the new project`, `the upload` and `the run request` to a reviewer. They
live in branches selected by `useState` and a settled `useMutation`. **The previous wave refused
to change them**, on the grounds that the edit is trivial and unverifiable — which was right, and
this register's rule is that a string is removed because a guard says it is gone from a rendered
screen, never because a diff looked convincing.

**If `S1` makes those branches reachable, repair them and show the guard catching a regression.
If it does not, say so and leave them.** The row asks for an instrument, not an edit.

## S3 — `D-95`: a guard that fails on Latin is blind to Cyrillic that is merely wrong

`web/src/shared/lib/listing-failure.ts:108` substitutes `PARENT_GENITIVE.version = 'версии'` — a
feminine noun — into sentences written for masculine `проекта` / `документа`, so a reviewer reads:

> Такого версии не существует. · На сервере нет этого версии, поэтому перечислять здесь нечего.

**Repair the sentence and the class.** The same substitution mechanism is in `upload-failure.ts`,
`run-failure.ts` and `catalog-message.ts`. Given the templates and the nouns, agreement is
checkable — and the renderer that walks every screen already exists; it looks for the wrong thing.

## S4 — `D-90` and `D-94`: live conditions nothing asserts

- `StageComparisonPage` re-checks `looksLikeProjectUid`; delete the check and 1085 tests stay
  green. **The naive mutation dies at `tsc` for an unused import** — a red that is about the
  import and says nothing about the condition (`§12`).
- `routes.comparison()` is asserted by nothing: point it at `/compare` and the suite is green.
- The only navigational road to the comparison screen is a `<p>` in
  `version-detail-page.tsx`; delete it and the suite is green.

**The last two are the integrator's own changes, and putting them inside your grant is the point
of `D-94`:** work that falls between all grants falls between all guards. `W43-PREP` had a case
asserting *"the frame links to all four addresses"* and a judge's mutation died against it; the
comparison link had no such case because it landed outside every grant.

## allowed_paths

```
web/tests/**
web/src/shared/lib/**
web/src/**        — ONLY where an instrument you repaired newly catches a real defect
docs/program/W44-SEE.md
```

## forbidden_hotspots

`tests/e2e/**` — **`W44-JOURNEY` owns it**, live in `/root/w44jrn` · `contracts/**` ·
`src/auditmanager/**` · `db/**` · `infra/**` · `web/FRONTEND_LOCK.json` ·
`web/src/shared/api/generated/**` · `docs/program/DEBT_REGISTER.md` ·
`docs/program/dispatch/**` · `Makefile` · `package.json` · `package-lock.json` · any container
not named `gate-w44b*`.

## Deliverables

1. The repairs, committed step by step.
2. `docs/program/W44-SEE.md`, opened **before** the first measurement.
3. **Wave 43's probe, driven and red**, quoted with the screen each instrument names.
4. Every new assertion shown failing.
5. **A plain count**: how many screens the derived set renders, against the fourteen addresses
   `web/src/app` offers. If it is not fourteen, say which are missing and why.
6. Anything outside the grant: reported, not repaired.

## Verification

Lane `gate-w44b` — PostgreSQL `127.0.0.1:56300`, S3 `59900`/`59901`. Provision as usual. **Run
the whole frontend suite**, not the tests you were thinking of. `make gate > /root/w44b-gate.log
2>&1`, verdict from the **`GATE OK` line**. Wave 43: battery **2442**, foundation **35**,
frontend **1085 in 75 files**.

## Discipline

Commit each step. Do not tag, push or merge.
