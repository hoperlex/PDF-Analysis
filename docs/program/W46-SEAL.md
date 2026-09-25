# W46-SEAL — the section field, its migration, and one aggregate read

**task_id:** `W46-SEAL` · **wave:** 46, sub-stage A · **lane:** `gate-w46a` · **base:** `8180ccc`
**worktree:** `/root/w46seal` · **branch:** `agent/w46-seal`

Opened after the first exploration but before the first *measurement* (before `make
migrate`, before the first `pytest` invocation) — later than the brief's own instruction
asks for, and that gap is itself reported in section 4 rather than concealed: it took real
reading of the codebase (`documents/repository.py`, `decisions/journal.py`,
`runs/repository.py`, `bootstrap/composition.py`) to know what S1 and S2 would even touch,
and that reading is not free. What follows was written as it was found.

## 1. What landed, commit by commit

1. `ab553f7` — S1: `db/migrations/versions/20260925_0011_document_section.py` (nullable,
   CHECK-bound to fourteen codes), the field threaded through
   `documents/models.py`, `documents/repository.py`, `api/schemas/documents.py`,
   `api/routers/documents.py`, `api/routers/ports.py`, `bootstrap/adapters.py`,
   `ingest/service.py`, plus the two Pydantic contract properties
   (`UploadDocumentRequest.section`, `DocumentVersion.section`) and the `ProjectSection`
   enum in `api/schemas/models.py`.
2. `d55012a` — S2: `DashboardPort`/`DashboardRepository`/`DashboardAdapter`, the
   `getDashboardSummary` router, composition wiring, and the router-only guards that had
   to move because the live application now has twenty routes regardless of what the
   frozen contract says.
3. `d7ac848` — the reseal, one commit, five documents: `contracts/api/v1/openapi.json`,
   `web/openapi/openapi.json`, the four generated client files, `web/FRONTEND_LOCK.json`
   with all six digests recomputed by hand, and the pin at
   `tests/contract/api_v1/test_doc_prose_facts.py`. Plus two more pin locations found red
   and moved in the same commit — see section 4.
4. `4706bbc` — `tests/contract/domain_p02/test_project_section_catalog.py`, a new guard
   checking the fourteen-section vocabulary across its three independent spellings
   (migration CHECK, frozen enum, `dashboard.repository`'s own tuple).

Migration head: `0010_run_terminal_detail` → `0011_document_section`. Verified to apply
and roll back against `gate-w46a` (`make migrate`, then `alembic downgrade -1`, then
`upgrade head` again — all three clean).

Contract surface: **16 / 19 / 53 → 17 / 20 / 61** — one path, one operation, eight schemas
(`ProjectSection` plus the seven `getDashboardSummary` response shapes). No error code
added (catalog stays at twenty-two, untouched, as instructed).

## 2. Argument one: where the section field lives

**On the document. Not the version, not the project.**

Three candidates, and the other two lose on structural grounds rather than convenience:

- **The project.** A project does not *have* a section — it has documents in as many as
  fourteen of them. A single-valued field on `project` cannot represent that; it would
  have to become a set, which is a different, larger feature (`D-56`'s own "sections as
  navigation and stubs" half, explicitly out of this reseal's scope and squarely
  `web/src`'s, i.e. `W46-DASH`'s).
- **The version.** `document_version` is immutable and append-only — a new upload of the
  same document is a new version, never an edit (`trg_document_version_immutable`). A
  section is a classification of *what the document is* (an AR, a KM, …), which does not
  change when a corrected PDF is republished. Putting it on the version would mean either
  repeating the same value on every version of a document (a fact stored N times with N
  chances to disagree) or asking "which version's section is authoritative", a question
  `R-40` never raised and this reseal does not need to answer.
- **The document.** `document` is the one row that persists across republication and is
  already where `display_title` lives, for exactly this reason — a presentation fact
  about the *document*, not about one revision of its bytes. `section` joins it in the
  same table, the same nullability shape, and the same "set once, read many times" life
  cycle.

**Nullable, not required — and this is the part the brief left more open than "where it
lives" and the part I want to argue as hard.** The obvious alternative is `NOT NULL`,
forcing every upload to name a section. Three things rule it out:

1. **No backfill exists and none is invented.** The column starts empty; there is no
   legacy import in this alpha to backfill from, so `NOT NULL` would mean every existing
   caller breaks the moment this migration lands, with nothing to fill the gap but a
   guess — and `AGENTS.md` §4 forbids a fabricated classification precisely because a
   guess in an append-only, expert-facing fact is indistinguishable later from something
   a person actually decided.
2. **`tests/e2e/**` is not mine to edit, and a required field would force it to change.**
   The frozen `uploadDocument` operation is exercised by real multipart bodies all over
   this tree — 18 files, ~55 call sites at the `IngestService.upload_single_pdf` layer
   alone, several more at the HTTP layer. A `NOT NULL` contract property would mean every
   one of those either breaks or needs a `section=` added, and `tests/e2e/**` is an
   explicit forbidden hotspot for this stream. Making the field optional — the same
   declared shape `display_title` already uses
   (`Field(default=None, json_schema_extra=optional_property)`) — means every existing
   caller keeps working unchanged, verified: `tests/integration/ingest`,
   `tests/integration/p02_journey` and `tests/integration/runs` are 248/248 green with no
   edits beyond the two direct `DocumentRepository.create_document` call sites, which I
   touched only to demonstrate the argument rather than because they were forced to move.
3. **This *is* "absent is not empty", applied one layer earlier than the aggregate.** The
   brief's own examples are about read results (a project with no runs, a section with no
   documents). I extended the same discipline to the field itself: a document nobody has
   classified yet is a real, common, legitimate state — not a defect to be defaulted away
   — and the aggregate read's `section_breakdown` has an explicit, always-present,
   never-omitted row for exactly that state (`section` absent from the JSON body,
   `document_count` real). Had the field been required, there would be nothing for that
   row to mean.

## 3. Argument two: what the aggregate read refuses

`getDashboardSummary`, `GET /dashboard`. **It takes no parameter at all** — not
`project_uid`, not a date range, not a category or verdict filter, not `cursor`/`limit`.
That is the whole of what it refuses to become: a second, generic query surface over data
three narrower, already-existing operations answer more precisely. `listProjects` answers
"documents in *this* project"; `listDecisions` answers "decisions matching *this*
category/verdict"; `listRuns` answers "runs of *this* version". A parameterised dashboard
endpoint would be a fourth way to ask overlapping questions, and the next reader would not
know which one is authoritative. `AGENTS.md` §4's ban on a generic query endpoint without
proven semantics is written for exactly this shape.

What it *does* answer is fixed and named: **the operational shape of the whole deployment,
right now** — four panels, each a server-side aggregate (`GROUP BY`), never a client-side
walk over a paginated listing:

| panel | source |
|---|---|
| `documents_by_project` | reuses `DocumentRepository.list_projects` verbatim — not a second definition of the count `Project.document_count` already publishes |
| `findings_by_verdict` | `GROUP BY` over `finding_current_verdict`, the same rebuildable projection `decisions.journal` already reads |
| `run_activity` (`by_state` + `spend`) | `GROUP BY audit_run.state`; `spend` is the same conservative measured/estimated rule `runs.repository.RunCost` applies to one run, lifted to every `model_call` row across every run |
| `section_breakdown` | `GROUP BY document.section`, the new field |

Consequence of "one read serving four panels" that is worth stating plainly: three of the
four panels did **not** need this reseal (R-44's own table, read from the tree before the
ruling). Building them as one operation anyway is the integrator's decision under `R-29`
and `R-24`'s own precedent — a listing operation was ruled *for*, and a client-side walk
*against*, deliberately and against the cheaper recommendation at the time. Founding a new
dashboard on three walks over the very kind of operation `R-24` exists to make
unnecessary would be an odd inheritance, and three walks built now are three walks a real
aggregate read later deletes. The marginal cost of doing it as one read is smallest
exactly now, while the reseal is already open for the fourth panel.

**Absent is not empty, enforced in every panel and shown failing twice (section 5):**
`findings_by_verdict` lists all four `Verdict` members, `run_activity.by_state` lists all
eight `RunState` members, and `section_breakdown` lists all fourteen frozen sections —
every one present at `count: 0` rather than omitted — plus a fifteenth row for documents
nobody has classified, present unconditionally (even at `document_count: 0`), because
omitting it at zero would silently say "no unclassified documents exist as a concept"
rather than "there happen to be none right now".

## 4. Premises checked, and the false ones

Per the brief: every premise verified, false ones reported as a deliverable rather than
silently worked around.

### 4.1 FALSE — "a reseal is FIVE documents… and three more pins move on their own triggers"

Both halves undercount. Running the actual canonical battery (not a chosen scope) found
**two more pin locations neither `D-102` nor `D-105` names**, both moved in the reseal
commit `d7ac848`:

- `tests/contract/api_v1/test_openapi_conformance.py`: `FROZEN_OPERATION_COUNT`,
  `FROZEN_OPERATIONS`, `FROZEN_SCHEMA_COUNT`, `FROZEN_SCHEMA_NAMES`. The file's own header
  calls these "not derived from the document" — i.e. a reseal's to move by hand, exactly
  `D-102`'s shape. Found still at 19/53 while the live contract already read 20/61 (I had
  already applied the contract edit before running this suite), and two of the file's own
  test names had gone stale a wave earlier —
  `test_declares_exactly_eighteen_operations` was asserting `== 19`, and
  `test_declares_exactly_the_fifty_one_schemas` was asserting `== 53` — the identical
  "the guard's own name is the stale count" shape `D-102` is about, one file over from the
  one `D-102` found it in.
- `tests/integration/api/test_served_document_and_health_plane.py`: `PATH_COUNT`,
  `OPERATION_COUNT`, `SCHEMA_COUNT` — the same shape again, a third file.

So the count of independently-moving pins this wave actually touched is **at least
seven**: five reseal documents + migration-head literal + these two, and the true count of
locations that move *on a surface-size change specifically* (excluding the migration-head
one, which moves on a different trigger) is five documents plus three test-fixture
locations. Recorded here rather than only in commit messages because `D-105`'s own
closing line — "wave 48's audit gets it" — is exactly the situation this finding
continues: the pin set is not fully enumerated anywhere, and every session that reseals
without re-running the whole battery will find a subset of it by luck.

### 4.2 FALSE (in a narrow, useful way) — "the pin at `test_doc_prose_facts.py:290`"

Confirmed as a *fact about the past*, false as a *fact about now*, before I ever touched
the file: at dispatch, the assertion `SurfaceTriple(paths=16, operations=19, schemas=53)`
sat at roughly line 305, not 290 — `D-102`'s own writeup grew the docstring around it by
fifteen-odd lines after the brief's line number was presumably taken. It is at line 316
now. The *pin itself* — same variable, same file, same purpose — was exactly where the
brief said to look for it in spirit; only the literal line number had drifted, which is
`W12`'s and `D-27`'s own lesson (a query that shares an assumption with its subject, here
"line numbers don't move", cannot see itself being wrong) applied to a brief's citation
rather than to code.

### 4.3 TRUE, and worth confirming rather than assuming — R-40's batching

The brief's frozen inputs say the batch is what `D-56` measured; `R-40`'s ruling itself
(read in full before starting) corrects that to **exclude** `D-46` (already closed under
`R-29`/`W42-SEAL`) and to flag the log-read operation's premise as false (`audit_event` is
never written by `src/`). Neither correction changed what S1/S2 asked me to build — my
scope was always exactly "the field + its aggregation" — but I verified both against the
tree before starting rather than trusting the ruling's own citation, per `OPERATING_CONSTRAINTS.md`
§12: `D-46`'s closure really is in `git log` at `W42-SEAL`'s commit, and
`grep -rn "audit_event" src/` really does return zero writers (only test fixtures).

### 4.4 A fifth pin, found by the integrator inside this stream's own grant

While this stream was running, the integrator reported (and I did not independently
find first): `tests/contract/api_v1/test_doc_prose_facts.py::test_the_historical_section_is_excluded_from_the_live_scan`
pinned four literals tied to one wave — a commit short sha, the heading text "wave 43
(historical record)", and the live section's claim "closed as `alpha-w44`" — and it went
red the day it was written, when `CURRENT_STATE.md`'s heading was renamed closing wave
45. `tests/contract/api_v1/**` is this stream's grant, so the repair was mine to make
rather than the integrator reaching across. Rewritten to derive its expectation from the
marker `_HISTORICAL_HEADING` finds in the file as it stands, rather than typing in what
it currently says — see commit history for the exact diff and the mutation that shows it
still fails when it should. This is a fifth pin location beyond the four named in 4.1,
found only because it broke *between* wave closes rather than *at* one, which is the
detail that makes it worth recording separately: `D-105`'s "moves on its own trigger"
turns out to include "editing a heading for clarity", not only "resealing the contract"
or "closing a migration".

### 4.5 A pre-existing defect this reseal exposed but did not cause

`docs/program/CURRENT_STATE.md` still says the tagged tip "closed as `alpha-w44`"; the
real tagged tip, read from `git`, is `alpha-w45`. This is unrelated to `R-40`/`R-44` —
it predates this wave's work entirely — and was found only because running
`test_the_scanned_docs_state_the_tagged_tip_this_tree_has` (part of the canonical battery,
never previously run in isolation by this stream) surfaced it. `CURRENT_STATE.md` is not
in this stream's `allowed_paths`; reported here and in the "outside the grant" list below,
not repaired.

## 5. New guards, shown failing

1. **`tests/contract/domain_p02/test_project_section_catalog.py`.** Mutation: appended a
   fifteenth code, `"ZZ"`, to migration `0011`'s `PROJECT_SECTIONS` tuple. Failing
   assertion:
   ```
   AssertionError: assert ('AR', 'AI', ...) == ('AR', 'AI', ...)
     Left contains one more item: 'ZZ'
   ```
   (`test_the_migrations_check_constraint_matches_legacy`). Reverted; suite green
   (5 passed) both before the mutation and after the revert.

2. **`tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py::test_the_one_unaddressed_aggregate_answers_its_own_fixed_shape`.**
   Mutation: added `"page": {"next_cursor": None}` to `dashboard_summary_body`'s output,
   simulating a regression toward the page shape the guard exists to refuse for this
   operation. Failing assertion:
   ```
   AssertionError: getDashboardSummary answered a page shape; it is registered as an
   aggregate, not a collection
   ```
   Reverted; `test_an_absent_parent_is_not_an_empty_page.py` green (4 passed) after.

3. **Found the hard way, not by a planted mutation — the real bug this reseal shipped
   with until `test_router_answers.py`'s sweep caught it.** `dashboard_summary_body`
   referenced `view.run_spend.basis`; the view dataclass's actual field is `cost_basis`.
   Every call to `GET /dashboard` against the real wired application answered `500
   internal_error`. Caught by
   `test_router_answers.py::TestNoOperationAnswersWithAServerFault::test_every_declared_get_answers_without_an_internal_error`,
   a pre-existing sweep over every GET route this stream did not write — not by any unit
   test, because none drove `dashboard_summary_body` against the real view type before the
   integration sweep did. Fixed in the S2 commit (`d55012a`); the commit message says so
   rather than folding it in silently.

## 6. Risks and known limitations

- **`section` is optional, permanently, unless a later wave revisits it.** A caller can
  upload every document with no section forever; nothing in this reseal forces
  classification. That is the deliberate trade argued in section 2, but it means the
  `section_breakdown` panel may stay dominated by the unclassified bucket until the
  frontend (`W46-DASH`'s, or a later wave's) makes choosing one part of the upload flow.
- **`getDashboardSummary` has no pagination and cannot get one without a breaking change.**
  If the number of projects or the number of distinct sections ever needs paging, this
  operation's shape does not accommodate it — a deliberate choice for an alpha-scale
  deployment, named here so nobody mistakes it for an oversight later.
- **Reclassification is not published.** The migration comment says a section is "set
  once, at upload, and never rewritten"; there is no operation to change a document's
  section after the fact. If the owner wants that, it is a new write operation and a new
  reseal, not a gap in this one.
- **`web/src/**` and `web/tests/**` are outside this grant and both currently redden
  guards that read the surface this reseal moved** (see section 7). The dashboard is not
  usable from the frontend until `W46-DASH` consumes `getDashboardSummary`, and
  `npm --prefix web run test:contract` will not go green until `web/tests/contract/seam-operations.contract.test.ts`'s
  `SEAM_OPERATIONS` register gains a twentieth row.

## 7. Outside the grant — reported, not repaired

Four locations, found by running the real canonical battery rather than a narrowed scope,
that must move for a full `make gate` to pass and that this stream is not permitted to
touch:

1. **`docs/program/CURRENT_STATE.md`** and **`docs/program/ALPHA_ROADMAP.md`** — both
   still state the surface as `16 paths / 19 operations / 53 schemas` and the migration
   head as `0010_run_terminal_detail`; `CURRENT_STATE.md` also still names the tagged tip
   as `alpha-w44` (real tip: `alpha-w45`, pre-existing, see 4.4). Neither file is in this
   stream's `allowed_paths`. `tests/contract/api_v1/test_doc_prose_facts.py`'s three
   "scanned docs" tests read these files directly and stay red until an integrator-owned
   edit lands. `CURRENT_STATE.md`'s own header says it is updated by the integrator; this
   is that update.
2. **`infra/deploy/README.md`, `infra/deploy/serve.py`** — both say "the nineteen
   operations". `infra/**` is a forbidden hotspot for this stream.
3. **`web/src/app/bff/v1/[...path]/route.ts`, `web/src/shared/api/authorization.ts`** —
   the former says "nineteen operations across sixteen paths", the latter "the nineteen
   operations". `web/src/**` (except `shared/api/generated/**`) is `W46-DASH`'s, live in
   `/root/w46dash`.
   Together with (2), `tests/contract/api_v1/test_surface_counts_in_prose.py` stays red
   until both land.
4. **`web/tests/contract/seam-operations.contract.test.ts`** — `SEAM_OPERATIONS` lists
   nineteen operations and is missing `getDashboardSummary`; `npm --prefix web run
   test:contract` fails two assertions in `describe('the nineteen seam operations')` until
   a twentieth row is added. `web/tests/**` is an explicit forbidden hotspot for this
   stream regardless of who else owns it.

## 8. Verification run

- `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` — bootstrap OK.
- `.venv/bin/python -c "import boto3"` — OK.
- `npm --prefix web ci` — OK (184 packages).
- `make migrate` at `ab553f7`, then `alembic downgrade -1`, then `upgrade head` again —
  all three clean, no errors, head confirmed `0011_document_section`.
- `npm --prefix web run api:generate` — 4 files written, 20 operations, contract sha256
  `20980cb3…76f59`.
- `npm --prefix web run test:guards` — 149/149 passed, including
  `frontend-lock.guard.test.ts`.
- `npm --prefix web run typecheck` — clean.
- Targeted `pytest` at each step (see individual commit messages and section 5 above);
  full `tests/contract/api_v1`, `tests/integration/api`, `tests/integration/composition`,
  `tests/integration/ingest`, `tests/integration/p02_journey`, `tests/integration/runs`
  and `tests/contract/domain_p02/test_project_section_catalog.py` green except the four
  out-of-grant locations in section 7.
- `make gate` (the literal canonical command): see the final report handed to the
  integrator for the result of this run, taken after this document was written.
