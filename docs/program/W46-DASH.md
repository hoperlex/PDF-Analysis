# W46-DASH — working log

**task_id:** `W46-DASH` · wave 46, sub-stage A · lane `gate-w46b` · worktree
`/root/w46dash` · branch `agent/w46-dash`

**Process note, stated rather than hidden.** The dispatch's deliverable #2 asks this file
to be opened *before the first measurement*. It was not: exploration (reading the brief,
the owner rulings, `OPERATING_CONSTRAINTS.md`, the route tree, the contract, and several
early `npx vitest` runs against the pre-existing suite to learn the two instruments' cache
harness before writing any code) came first, and this file was opened once the design was
settled and the first code was about to be written. Nothing in that exploration edited the
tree — the first tracked change is the dashboard itself — so the ordering slip cost no
evidence, but it is still not what the deliverable asked for, and is recorded here rather
than left for a reader to assume was followed.

## Provisioning (2026-09-25)

```
npm --prefix web ci        -> added 184 packages
web/node_modules/.bin/tsc --noEmit --incremental false   -> clean, 0 errors
```

Backend provisioning (`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`,
`.venv/bin/python -c "import boto3"`) is run as part of `make gate` below; this task's
`allowed_paths` are frontend-only (`web/src/**` except the generated client, `web/tests/**`),
so no Python source changes.

## Premises re-measured before building

1. **Contract surface.** `python3 -c "..."` over `contracts/api/v1/openapi.json` at
   `8180ccc` (this task's base) → **16 paths / 19 operations / 53 schemas**, matching
   `alpha-w45`. `W46-SEAL`'s reseal has not merged into this worktree as of writing —
   confirmed by re-running the same count immediately before the final gate, below.
2. **The three "reachable today" panels, checked against the live contract rather than
   trusted from the brief:**
   - `Project.document_count` — present, **optional** (not in the schema's `required`
     list). `entities/project/model/project.ts` already draws the absent/zero line
     (`projectDocumentCount`); this task reuses it rather than re-deciding it.
   - `listDecisions` (`GET /decisions`) — present, `category`/`verdict` query filters
     confirmed in the operation's parameters. Its own description: *"a client could
     otherwise reach only by walking every run and every finding"* — i.e. it is the one
     operation this dashboard may lean on instead of walking.
   - `listRuns` — present, but **its path is `/versions/{version_uid}/runs`, not a
     deployment-wide listing.** The dispatch brief's table and `R-44`'s own table both
     call this panel "exists today" without flagging that scoping. **This is a false-by-
     omission premise, reported rather than silently worked around**: there is no
     operation that lists every run of a deployment, so "run activity and spend" cannot
     be one request. See D1 below for how this was handled.
3. **The per-section panel's data source.** `D-56` / `entities/project/model/section.ts`:
   the contract has no section field anywhere today, independent of whether `W46-SEAL`'s
   migration has landed in `/root/w46seal` — this worktree does not have it, and
   `web/src/shared/api/generated/**` is that stream's own hotspot. **Confirmed: the
   per-section panel cannot be driven against real data in this worktree at all**, not
   even for the one analysed section (AR) — there is no operation on this contract that
   returns a per-section count for anything.
4. **The screen/instrument-coverage mechanism.** Read `web/tests/unit/screens/route-screens.ts`
   in full before writing any component: `SEEDS` is the single point both
   `rendered-language.guard.test.ts` and `contrast.test.ts` derive their screen set from
   (`derivedScreens()`), so a new route needs exactly one entry there — confirmed by
   grepping both files' imports rather than assumed from the dispatch prose.

## D1 — the four panels, what each is driven against

| panel | driven against real data? | source |
|---|---|---|
| documents per project | **yes** | `listProjects` → `Project.document_count`, one page |
| findings by verdict | **yes** | `listDecisions`, unfiltered, one page, deduped by `finding_uid` |
| run activity and spend | **yes, bounded** | a walk: one page of projects → one page of each project's documents (`listDocuments`, which already carries each document's current version) → one page of each version's runs (`listRuns`) |
| per-section breakdown | **no** | structure only (`PROJECT_SECTIONS`, the fourteen `D-56` measured); no operation on this contract returns a count |

**Why "run activity and spend" is a walk rather than one request**, since the brief
implied a single existing operation: `listRuns` has no global form (premise 2 above).
`R-44`'s own argument — `R-24` was ruled *for* a listing operation and *against* a
client-side walk specifically to stop a client walking every run — applies here too, and
the honest resolution is the one the ruling itself points at: **the walk this wave builds
is exactly the three page-walks `W46-SEAL`'s later aggregate read deletes**, bounded to one
page at each of three levels (projects, documents-per-project, runs-per-version) and
disclosed rather than presented as exhaustive — see `useRunActivityWalk`'s own header in
`web/src/widgets/dashboard/api/use-run-activity-walk.ts`. A deployment with more than a
page of projects, or a project with more than a page of documents, is under-counted;
`moreProjects`/`moreDocuments`/`moreRuns` say so on screen rather than silently.

**Why the per-section panel is structure-only rather than showing a number for AR.** The
dispatch's own D3 section reads *"the per-section panel shows structure for fourteen
sections and numbers for one"* — that is the **post-merge** end state, once `W46-SEAL`'s
aggregate read exists and is called. Before merge there is no operation that returns a
count for any section, AR included: the contract carries no section field at all (premise
3). Inventing a number for AR from a different source (e.g. counting today's total
findings and asserting they are "AR's", since AR is the only analysed section) would be
exactly the second-source invention D1's own instruction forbids ("you do not build a
second source") — the dispatch itself says which panel needed the reseal, and this is that
one. `web/src/widgets/dashboard/ui/sections-panel.tsx` says why in the words of the
subject, no operation id, field name or transport named.

## D2 — absent, empty, not-yet-produced

Each panel reaches its own honest states independently, so the four together do not all
read the same:

- documents/verdicts panels: `LoadingState` → `ErrorState` (classified per the existing
  `classifyProjectListFailure` / a local `listDecisions` classifier) → `EmptyState` (the
  request succeeded and there is genuinely nothing) → real numbers.
- run-activity panel: the same shape, plus a **second** empty case distinguished from the
  first — "no projects at all" vs "projects exist, the walk completed, zero runs were
  found" — added as a new render-matrix cache state, `runs-empty`, in
  `web/tests/guards/rendered-language.guard.test.ts` (see below; this branch had no
  existing state that reached it and the guard caught that itself).
- per-section panel: permanently `NotApplicableState`. Never `EmptyState` — the question
  was not asked and answered empty, it cannot be asked at all on this contract yet, which
  is the distinction `/blocks`' `NotApplicableState`/`EmptyState` split set the precedent
  for (`R-25`'s citation).

No invented numbers: `Project.document_count`'s absence is kept absent
(`summarizeDocumentTotals`, `web/tests/unit/widgets/dashboard.test.ts`), and a run that
made no provider call is counted apart from a run that spent zero
(`RunStatus.cost_micros`'s own contract description; `summarizeRunActivity` reuses
`entities/audit-run`'s existing `runCost` classifier rather than re-deciding the line).

## D4 — the instruments, and one gap they found

Adding the route required exactly one edit to reach both static instruments: one `SEEDS`
entry in `route-screens.ts` (`address: '/dashboard'`, a `make`, not an `optOut` — a route
with real content, so this is the ordinary "new screen arrives" path the file's own header
describes, not a case of editing `SEEDS`/`UNREACHABLE_IN_ONE_PASS` to make something pass).
Both `rendered-language.guard.test.ts` and `contrast.test.ts` picked the address up from
that one entry, with zero further edits needed for the contrast side.

The language guard's **branch-coverage matrix did find a real gap**, on the first run: the
run-activity panel's "projects exist, walk succeeded, zero runs" branch had no cache state
among the existing sixteen that produced it (every state either empties `KEYS.projects` too
or seeds exactly one run). Per the file's own instruction — *"seed a state that reaches it,
or add it to `UNREACHABLE_IN_ONE_PASS`"* — a state was added (`runs-empty`, and its builder
`runsEmptyClient`) rather than excused, because the branch is genuinely reachable by a real
client (a project whose current version has never been run). This is reported here as the
finding it is, not folded silently into the diff: the gap existed because this dashboard
introduced the first widget that needs "some listings loaded, one specific listing empty"
as a distinct shape from the existing "everything loaded" / "everything empty" pair.

## The gate, run in full (2026-09-25)

```
make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12   -> bootstrap OK
.venv/bin/python -c "import boto3"                     -> boto3 OK 1.43.90
npm --prefix web ci                                     -> added 184 packages
make gate > /root/w46b-gate.log 2>&1
```

**Foundation: 35 passed**, matching baseline. **Frontend: 79 files, 1120 tests, all
passed** (`alpha-w45` baseline 78/1110; +1 file, +10 tests is exactly
`tests/unit/widgets/dashboard.test.ts`). **Battery: 2491 passed / 5 skipped / 4 warnings /
169 subtests, 2 failed.** There is no `GATE OK` line in `/root/w46b-gate.log`, and this
document does not claim one. The two failures, read rather than assumed:

1. **`tests/contract/api_v1/test_doc_prose_facts.py::test_the_scanned_docs_state_the_tagged_tip_this_tree_has`**
   — *"prose says a wave closed as a tag that is not the tagged tip: `docs/program/CURRENT_STATE.md`:
   'closed as `alpha-w44`' names alpha-w44, tip is alpha-w45."* **Pre-existing and outside
   this task's grant.** `docs/program/CURRENT_STATE.md` is not in `allowed_paths` (only
   `docs/program/W46-DASH.md` is), this task's diff never touches it, and the sentence this
   test flags was already there at the base commit `8180ccc` — `CURRENT_STATE.md` itself
   said *"Wave 44 is closed as `alpha-w44`"* under "Where the programme was, 2026-09-24"
   when it was read at the start of this task, unchanged since. Reported, not repaired.
2. **`tests/e2e/test_pc01_journey_conformance.py::test_the_journey_walks_every_screen_the_application_offers`**
   — *"1 screen(s) exist that the PC-01 journey does not walk: `['/dashboard']`."* **Caused
   by this task, and structurally unclosable from this worktree.** `/dashboard` is the new
   route; `tests/e2e/pc01/journey/manifest.json` needs a row for it, and that file is
   explicitly the integrator's by `D-89` — the dispatch says so and it is not in
   `allowed_paths` (nor is it in `forbidden_hotspots`'s list verbatim, but the dispatch's
   own sentence, *"you will need a row in it — report what it should say; do not write
   it,"* makes the ownership unambiguous). **This lane's gate cannot reach `GATE OK` on its
   own by design** until the integrator applies the row below. The proposed row is written
   out under "Journey manifest row" for the integrator to apply.

Both failures are named, neither is silently worked around, and neither required editing
inside `web/src/**`/`web/tests/**` to close: the first belongs to a document this task does
not own, the second belongs to a file this task is explicitly told not to write.

## Journey manifest row, for the integrator to apply

`tests/e2e/pc01/journey/manifest.json`'s `routes` array, in the same shape the existing
no-parameter, no-write entries use (`blocks`, `optimisation`, `logs`, `workers`,
`knowledge-base`):

```json
{
  "name": "dashboard",
  "path": "/dashboard",
  "page_module": "web/src/app/dashboard/page.tsx",
  "$comment": [
    "Four panels, R-44. Three are driven against real data on mount: listProjects,",
    "listDecisions and the run-activity walk's own listProjects call (the same request,",
    "deduplicated by React Query) all fire unconditionally when the screen loads.",
    "expects_api below is only those three, because a live browser only observes a",
    "call that actually fires: the run-activity walk's nested listDocuments/listRuns",
    "calls are conditional on the seeded fixture actually holding a project with a",
    "document, and are NOT declared here for that reason -- see the caveat below.",
    "The per-section panel calls nothing: no operation on this contract returns a",
    "per-section count yet (D1; awaits W46-SEAL's merge)."
  ],
  "expects_api": [
    { "method": "GET", "path": "/projects", "operationId": "listProjects" },
    { "method": "GET", "path": "/decisions", "operationId": "listDecisions" }
  ],
  "follow": null
}
```

**One honest caveat this session could not resolve itself, because driving the live
journey is outside this task's lane.** If the fixture data `journey.mjs` runs against
holds at least one project with at least one document, the run-activity walk will also
issue `GET /projects/{project_uid}/documents` (`listDocuments`) and, for that document's
current version, `GET /versions/{version_uid}/runs` (`listRuns`) — both real operations,
both already in the contract. Whether to declare them in `expects_api` depends on whether
the seeded journey fixture actually has a project to walk into, which this session did not
drive live to check. The integrator should run the journey once against the deployed
fixture and add those two lines if the calls are observed; declaring an operation that
never fires would make the manifest's own conformance check assert something false in the
other direction.

## Panels driven against real data, restated plainly for the handoff

- **Documents per project** — real data.
- **Findings by verdict** — real data.
- **Run activity and spend** — real data, bounded to one page per level, disclosed.
- **Per-section breakdown** — structure only; no operation on this contract returns the
  numbers. This is the one panel `W46-SEAL`'s merge changes.
