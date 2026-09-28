# W46-WIRE — four panels on the one read `R-44` ruled for, and the sentences the merge made false

**task_id:** `W46-WIRE` · **wave:** 46, sub-stage B · **lane:** `gate-w46b`
**worktree:** `/root/w46dash` · **branch:** `agent/w46-wire`, based on `2ffca8c`
**depends_on:** `W46-SEAL`, `W46-DASH`, `W46-JUDGE-A`, all merged at `2ffca8c`

Read `docs/program/reviews/W46-JUDGE-A.md` sections 4–6 before anything else. Its findings are
your premises. Where this brief and the report disagree, the report was measured and this brief
was written from it, so say which one is wrong and why.

## W1 — `F-3b`: the dashboard reads `getDashboardSummary`, and nothing else

`R-44` ruled for **one aggregate read serving all four panels instead of three client-side
walks.** On `2ffca8c` the read is sealed and generated, and **nothing in `web/src` outside
`shared/api/generated` calls it.** The panels walk lists instead:
`documents-panel.tsx:27` uses `useProjectList`, `verdicts-panel.tsx:76` uses
`useDecisionJournal`, and `run-activity-panel.tsx:39` uses `useRunActivityWalk`. Replace all
three walks with one read. Delete `widgets/dashboard/api/use-run-activity-walk.ts` and any
aggregator in `widgets/dashboard/model/` that loses its last caller. **The entity hooks stay:**
other screens use them.

What each panel shows, and the traps the judge measured:

- **Run activity and spend.** `W46-SPEND`, running in parallel, makes `run_activity.spend`
  **optional**: absent when the deployment has no provider calls, and present with all three
  fields otherwise. Today's generated client still types it as required. **Code to the new
  shape now:** read it into a local value typed `… | undefined`, so the code typechecks
  against both clients. Absence renders as an honest sentence that no provider call has been
  made. **Never `0` with *измерено*.** The walk's current sentence talks about *inspected
  runs*, which will no longer be true, so reword it.
- **Sections.** The server now counts documents per section: fourteen sections plus an
  unclassified bucket, zeros included. These are computed numbers, so the panel shows them.
  **Show the unclassified row, always.** The product's upload form offers a PDF and a title
  and no section, so every document uploaded through the product is unclassified. Fourteen
  true zeros without that row read as *"no documents"*. Adding a section picker is **not**
  yours (`D-107`).
- **Findings by verdict.** The aggregate counts a finding nobody has judged as `pending`,
  which is what the `Verdict` enum says `pending` means. The panel's caption currently
  excludes never-judged findings. **The panel's meaning changes, so the caption changes with
  it.** Keep all four rows the aggregate sends, including `needs_manual_review`.
  **Integrator's ruling:** a computed zero is a fact. `/knowledge-base` hides that verdict in a
  *filter*, because a filter that can only return an empty page misleads; a count of zero does
  not.
- **Documents by project.** As sent. A project with no documents is a row at `0`.

## W2 — `F-3`: the sentences the merge made false

A document's section **is stored** (migration `0011`) and **is checked** (the upload refuses
`""`, `ar` and `ZZ` with `422`). Before the merge, the sentences below were true. They are false
now:

- the dashboard's section caption and its subtitle (*«Три читают то, что уже отдаёт контракт;
  …»*). After W1 the subtitle is doubly false;
- `web/src/widgets/project-sections/ui/project-sections.tsx:92-93` and `:104-107`;
- `web/tests/unit/screens/project-sections.test.ts:119-124`, **which pins the false sentence.**
  Rewrite it to pin a true one; do not just delete it;
- the module header of `web/src/entities/project/model/section.ts` (*"the contract has no
  section field anywhere"*).

What is true now: the section is stored and checked **when an upload supplies one**, and the
product's form does not supply one. The intake rule, *only АР is analysed*, is unchanged.

**`R-39`:** give reasons in the words of the subject. No operation ids, no field names, no
transport. **Also avoid *контракт* and *операция*.** The owner has not drawn that line
(`D-109`), and leaving both words out satisfies either reading.

## W3 — `F-5b`: every number on the dashboard comes from the read

The judge appended `': 0'` to every section row, and the whole frontend suite stayed green.
Add a render test driven by a fixture summary. It asserts that every count the four panels
render equals the fixture, and that nothing else renders as a number. **Show it failing** under
three mutations:

- a number that is not in the fixture;
- the unclassified row dropped;
- absent `spend` rendered as `0`.

## W4 — `F-4`: the journey, driven live

`tests/e2e/pc01/journey/manifest.json` is **in your grant for this stage** (`D-89`: one owner,
and this stage it is you). Two rows:

- **`dashboard`** (line 411): declare what the wired screen actually calls. The present comment
  reasons from the walks, which no longer exist, so rewrite it too.
- **`blocks`** (line 355): it declares `expects_api: []`, but `blocks-page.tsx` has called
  `useProjectList` since `c4165b9` (`W45-BLOCKS`). **That red is older than this wave.** Declare
  the call.

`optional_api` (`journey.mjs:390-395`) is for calls that fire only when data exists. Use it only
for a call that really is conditional, and say which call and why.

**Drive it:** `npm --prefix web run e2e:pc01 -- --origin <your Next> --phase all --out <dir>`,
against your lane's own API and Next. Use API `127.0.0.1:56381` and Next `127.0.0.1:56383`.
**Quote the summary lines.** The deliverable is zero undeclared calls on every route. `make gate`
does not run this (`D-108`).

**If a required sentence moves, update `test_control_a_reworded_panel_is_detected`** in
`tests/e2e/test_pc01_journey_conformance.py` with the manifest. It is the proof the guard can
still go red.

## W5 — two small measurements

- `/projects` is requested twice on a cold load. Measure it after W1. If the dashboard causes
  it, fix it; otherwise report where it comes from.
- Drive `/dashboard` at 780 px in both palettes with real data (a project, a document with a
  section, a published run), and say what you drove and what you could not.

## allowed_paths

```
web/src/**  EXCEPT web/src/shared/api/generated/**
web/tests/**
tests/e2e/pc01/journey/manifest.json · tests/e2e/test_pc01_journey_conformance.py
docs/program/W46-WIRE.md
```

## forbidden_hotspots

`contracts/**`, `web/openapi/**`, `web/FRONTEND_LOCK.json` and `web/src/shared/api/generated/**`
belong to `W46-SPEND`, live in `/root/w46seal`. Also forbidden: `src/**` · `db/**` · the rest of
`tests/**` · `infra/**` · `docs/program/CURRENT_STATE.md` · `docs/program/DEBT_REGISTER.md` ·
`docs/program/dispatch/**` · `Makefile` · `package.json` · any container not named `gate-w46b*`.
**The owner's stand is read-only.**

If `SEEDS` or `UNREACHABLE_IN_ONE_PASS` needs an edit to make something pass, report it as a
finding. Do not make the edit.

## Deliverables

1. The dashboard on one read, committed step by step.
2. `docs/program/W46-WIRE.md`, opened **before** the first measurement.
3. Every new guard shown failing, with the mutation quoted.
4. The live journey's summary lines, quoted.
5. Anything outside the grant, reported and not repaired.

## Verification

Lane `gate-w46b`: PostgreSQL `127.0.0.1:56380`, S3 `59980`/`59981`. The worktree is already
provisioned. **Run the whole frontend suite**, not only the tests you had in mind, plus
`npm --prefix web run typecheck`.

**Baseline: take your own on `2ffca8c` first.** One battery red is expected and is not yours:
`test_every_operation_can_report_not_found_or_validation`, which `W46-SPEND` repairs. If you see
any other red, report it.

`make gate > /root/w46b-gate.log 2>&1`. Take the verdict from the **`GATE OK` line in the log**.
The harness has reported `exit code 0` over a failed gate six times. Rendered copy is checked by
the Python journey-conformance test, which `npm test` cannot see. **Run the canonical battery
literally.**

## Discipline

**Commit after each step.** A session restart kills you, and only committed work survives it.
Do not tag, push or merge.
