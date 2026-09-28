# W46-GUARD — four guards that could not fail, and the sentence the contract owes about absence

**task_id:** `W46-GUARD` · **wave:** 46, sub-stage C · **lane:** `gate-w46a`
**worktree:** `/root/w46seal` · **branch:** `agent/w46-guard`, based on `dbba753`

Opened before the first measurement, per discipline. Written as the work is found, one step at a
time, and committed after each step so a session restart loses nothing.

## 0. Premises, from `docs/program/reviews/W46-JUDGE-X.md` (findings X-1, X-2, X-4, X-7, X-11)

- **X-1** — nothing in `make gate` compares `create_documentation_app().openapi()` with the
  frozen `contracts/api/v1/openapi.json`. `W13-CONF.md` §11 handed over
  `test_openapi_conformance_live.py` as *"deliberately not written"*; it never was. A
  Pydantic-only drift (`RunActivity.spend` required again, model only) passes the whole
  canonical battery, 2504/2504.
- **X-2** — `F-5a`'s new guard (`test_dashboard_summary_over_a_fresh_deployment.py`) proves
  absent-is-not-empty and nothing about present-is-counted: every count forced to `0`, and
  `cost_basis` forced to `"measured"`, both pass the new file and the 612-test scope around it.
- **X-4** — `F-5c`'s historical-section control (`test_doc_prose_facts.py`) uses
  `^#+.*historical record.*$`, which also matches a shell comment inside a fenced code block,
  and its non-vacuity check does not notice a boundary placed **after** the first claim.
- **X-7** — `_takes_caller_input` (`test_openapi_document.py`) enumerates `path`, `query`, a
  header other than `X-Correlation-Id`, and a body — OpenAPI 3.1's fourth parameter location,
  `cookie`, is not counted, so an operation that gains a malformable required cookie is still
  classified input-less.
- **X-11** — `RunActivity.spend` carries no description of what its absence means, unlike
  `RunStatus.cost_micros`, which does. The lock's `commit_note` claim *"the reason every reseal
  note below gives"* is true of three of eight prior reseal notes, not all.

## 1. Baseline

Taken at this branch's tip, `dbba753` (the dispatch commit for sub-stage C). Per the brief,
`d5c9be5` — this branch's parent commit, one before the dispatch-docs-only commit — gated
`GATE OK` under `W46-JUDGE-X` (battery 2504, frontend 1118 in 79 files). `git diff --name-only
d5c9be5..dbba753` touches only `docs/program/dispatch/**`, so that baseline stands for this tip
too.

## 2. G1 — the served-document conformance test

Wrote `tests/contract/api_v1/test_openapi_conformance_live.py`, exactly the call
`W13-CONF.md` §11 specified: `differences(surface(json.loads(CONTRACT_PATH.read_text())),
surface(create_documentation_app().openapi()))`, asserted empty. Loads the engine the same
way `test_openapi_conformance.py` does (`importlib`, anchored on `__file__`, under
`--import-mode=importlib`). `create_documentation_app()` rather than the wired app: it needs
no database, object store or credential, and `test_the_documented_and_the_wired_app_agree`
(`tests/integration/api/test_served_document_and_health_plane.py`) is what already proves
that document is the one served.

**Run on this tree first, per the brief.** `1 passed` — no difference between the served
document and the frozen contract on `dbba753`. Nothing to stop and report.

**X's mutation** (`RunActivity.spend` made required again, `src/auditmanager/api/schemas/
models.py` only): red —
`schemas.RunActivity.required: the contract has 1 entries and the generated document has 2
entries - contract ["by_state"] - generated ["by_state", "spend"]`. Reverted
(`git status --porcelain` on the file: empty), re-run: `1 passed`.

**My own mutation** (a field `stale: bool` added to `ProjectDocumentCount`, model only — a
different shape of drift, a wholly new required property rather than an existing one
changing required-ness): red —
`schemas.ProjectDocumentCount.properties.stale: present only in the generated document` and
the paired `required` count difference. Reverted, re-run: `1 passed`.

**Scope check.** `tests/contract` with `run_battery`'s three ignores: `368 passed, 49
subtests passed` — one more than X4's baseline of `367`, which is this new file's one test.

## 3. G2 — `F-5a` exact-count guard

*(filled as the work proceeds)*

## 4. G3 — the historical-section control

`_HISTORICAL_HEADING` (`^#+.*historical record.*$`) is a bare line match with no notion
of Markdown structure, so (X-4) a shell comment inside a fenced code block matches it as
readily as a real heading, and the existing non-vacuity check ("at least one claim
survives") only catches a false boundary placed *before every* claim, not one placed
*after the first* claim and before the rest — X's own mutation plants its fenced false
heading after the surface-triple paragraph and before a stale migration-head sentence,
so the surface-triple claim survives (non-vacuity passes) while the stale sentence is
silently cut away and never checked by `test_the_scanned_docs_state_the_migration_head_
this_tree_has`.

Added `_mask_fenced_code_blocks` (blanks the interior of every ``` / ~~~ fenced block,
length- and newline-preserving, so offsets still index the original text) and
`_GENUINE_HISTORICAL_HEADING_SHAPE` (this file's own convention: `## Previous release
state -- wave N (historical record)`, loose on wording between the fixed anchors,
strict on shape). `_historical_boundary(full_text)` finds `_HISTORICAL_HEADING`'s first
match in the *masked* text and asserts it also has the genuine shape, refusing to use it
as a boundary at all otherwise — closing both holes X named without weakening the
existing non-vacuity check, which stays as a second line of defence. Both call sites
(`_scanned_documents`, `test_the_historical_section_is_excluded_from_the_live_scan`) now
go through it.

**No real document is mutated** — `CURRENT_STATE.md` is a forbidden hotspot, and this
suite's own convention (its header, and `test_surface_counts_in_prose.py`'s
red/green parametrization) is to prove a guard can fail on synthetic prose. Four new
tests:

- `test_the_genuine_heading_is_still_found_as_the_boundary` — control, honest synthetic
  document, boundary lands exactly at the real heading.
- `test_a_historical_heading_inside_a_code_fence_is_not_a_boundary` — **X's mutation**,
  reproduced: a fenced shell comment plus a stale migration-head sentence between the
  live claim and the genuine heading. The fence is masked away, the boundary is the
  genuine heading, and the previously-hidden stale sentence is now inside the scanned
  prefix.
- `test_a_too_early_heading_outside_a_fence_is_still_caught` — **judge A's mutation**
  (`F-5`), reproduced: `### A note on how the historical record is kept`, directly under
  the live heading. Not fenced, but rejected by the shape check (`AssertionError`,
  *"does not look like this file's genuine heading"*).
- `test_a_too_early_heading_after_the_first_claim_is_still_caught` — **my own
  mutation**: X's second hole, reproduced *without* a fence at all — a real, unfenced,
  level-two heading (`## Note: keeping the historical record separate`) placed after the
  surface-triple claim and before a stale head sentence. Proves the positional hole is
  closed on its own, not merely as a side effect of fence-masking (X's own reproduction
  combines both defects in one mutation, so fixing only fencing would already make that
  specific case pass again without proving this one is closed). Rejected the same way.

**Run.** `tests/contract/api_v1/test_doc_prose_facts.py`: `25 passed` (21 + 4 new).
`tests/contract` scope: `372 passed, 49 subtests passed` (368 after G1, +4).

## 5. G4 — a cookie is input

`_takes_caller_input` (`tests/contract/domain_p02/test_openapi_document.py`) counted
`path`, `query` and a `header` other than `X-Correlation-Id` -- three of OpenAPI 3.1's
four parameter locations. Added `"cookie"` to the `("path", "query")` branch, no
exception by name (unlike `header`'s `X-Correlation-Id`, since nothing in the frozen
document declares a cookie today).

Four new tests, no real contract file mutated (deep copies of the session-scoped
`openapi_document` fixture only, per this file's own convention of driving the real
`_takes_caller_input`/rule logic rather than a hand-written approximation of it):

- `test_no_operation_declares_a_cookie_parameter_today` — the pin `X-7`'s reasoning
  needs: walked independently of `_takes_caller_input` (own `$ref` resolution over both
  path-item and operation parameter lists), so it does not share the blind spot it
  exists to catch a regression in.
- `test_a_required_cookie_parameter_makes_getdashboardsummary_take_input` — **X's
  mutation**: the exact parameter object X quoted, added to `getDashboardSummary`'s own
  `parameters`. `_takes_caller_input` now reports `True`; the real two-sided rule
  (factored out as `_assert_client_fault_rule`, shared with the production test rather
  than re-approximated), run against the mutation, raises exactly X's quoted message
  (*"takes caller input and declares no client-fault response"*).
- `test_a_required_cookie_parameter_with_its_client_fault_response_is_accepted` — X's
  *"honest repair"* direction: the same cookie plus a `422`. The same rule now raises
  nothing -- before this repair X measured it wrongly refused.
- `test_a_cookie_parameter_declared_on_the_path_item_also_counts` — **my own
  mutation**: the cookie placed on the *path item's* shared `parameters` instead of the
  operation's own (this document already declares `X-Correlation-Id` and every
  `{..._uid}` that way, and `_takes_caller_input` merges both lists) -- X's
  reproduction only exercises the operation-level list. Same result: `True`, and the
  rule raises the same message.

**Run.** `tests/contract/domain_p02/test_openapi_document.py`: `50 passed` (46 + 4
new). `tests/contract` scope: `376 passed, 49 subtests passed` (372 after G3, +4).

## 6. G5 — the reseal

*(filled as the work proceeds)*

## 7. Final gate

*(filled at the end)*
