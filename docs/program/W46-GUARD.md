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

`test_dashboard_summary_over_a_fresh_deployment.py`'s three tests, and the 612-scope
around them, all pass under X's two mutations of `_filled` -- every count forced to
`(member, 0)` (never reading the database) and `cost_basis` forced to `"measured"`
unconditionally -- because every state those tests drive is all zeros except one
`spend` call that genuinely is `measured`.

Added `test_a_deployment_with_known_data_reports_the_exact_counts` to the same file,
plus four seeding helpers (`_seed_published_document`, `_walk_run_to`, `_seed_run`,
`_seed_finding`, `_seed_model_call`). Every count is known before the read:

- **documents per project, per section:** two projects, documents with published
  current versions (`current_version_uid` set -- the one column
  `DocumentRepository._LIST_PROJECTS` and `_DOCUMENTS_BY_SECTION` both join through),
  classified `AR`, `KM`, and one left unclassified.
- **runs per state:** one run in each of the eight frozen states, including
  `cancelled` (declared directly from `created`) and `partial` (declared only from
  `validating`, with a non-empty `degradation_set`) -- neither of which
  `PublishedRun._walk_to` in `tests/integration/api/conftest.py` reaches, so
  `_walk_run_to` extends it rather than importing it (out of reach across directories
  under `--import-mode=importlib`, same as `fresh_database_url`'s own reasoning next
  to it).
- **findings per verdict:** one `pending`, two `accepted`, one `rejected`, inserted
  directly into `finding`/`finding_observation`/`expert_decision_event` (the same
  "a fixture is allowed to know the schema its own suite exists to protect" already
  used for `model_call`). `needs_manual_review` is asserted at exactly `0`, not
  seeded: `20260910_0002_pc01_schema.py`'s own comment says *"declared with no PC-01
  producer"*, and `ck_expert_decision_event_type_verdict_agree` enforces it
  structurally -- no `INSERT` into `expert_decision_event` can produce that verdict,
  under any of the four declared event types.
- **spend with one estimated call:** two `model_call` rows on one run, one `measured`
  and one `estimated`, so the aggregate basis is a real decision (`estimated`) rather
  than a copy of a single row.

**Run.** New test alone: `4 passed` (3 existing + 1 new) in the file.

**X's first mutation** (`_filled` returns `(member, 0)` for every member, in-tree,
reverted after): red -- `assert by_section["AR"] == 1` (`AR: 0`).

**X's second mutation** (`basis="measured"` unconditionally, in-tree, reverted after):
red -- `cost_basis` `'measured'` vs expected `'estimated'`.

**My own mutation** (`_DOCUMENTS_BY_SECTION` relabelled to report every document under
`'AR'` regardless of its real section, dropping the `GROUP BY`): red -- `AR: 3` vs
expected `1`. A different bug class from X's two (mislabelling rather than
zero-invention), not caught by either of X's mutations, caught by this guard's
per-section exactness.

All three reverted; `git status --porcelain -- src/auditmanager/dashboard/
repository.py` empty after each, and byte-identical to the pre-mutation file
(`diff` empty). Re-run after each revert: `4 passed`.

**Provisioning note.** `gate-w46a`'s own containers (`postgres`, `s3`, `s3-init`) were
not running at the start of this task (only `gate-w46k-*`, judge Y's lane, was up) --
started with `make up` in this worktree, then `PYTHONPATH=src .venv/bin/python -m
alembic --config db/migrations/alembic.ini upgrade head` to bring `audit_w46a` to
head (the gate database this suite's other fixtures and `make gate` itself use). No
container outside `gate-w46a*` was touched. `pg_database` in `gate-w46a-postgres-1`
holds no leftover `w46_spend_fresh_*` database after this section's runs
(`fresh_database_url`'s own `finally` drops it every time, mutation or not).

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

## 6. Four strengthenings from `W46-JUDGE-Y`'s cross-examination of `X`

The coordinator relayed four items from `agent/w46-judge-y` at `df78a89` (final
section, cross-examining `X-1`, `X-2`, `X-4`, `X-7`). Read directly
(`git show agent/w46-judge-y:docs/program/reviews/W46-JUDGE-Y.md`) before acting, per
discipline. All four measured true; none disagreed with the brief.

- **G1 / X-1.** Y measured that X's drift (`RunActivity.spend` required again) changes
  nothing on the *wire* -- the serializer omits the key regardless -- so X's
  reproduction is a document-only drift. Y mutated `AppendDecisionRequest.comment`'s
  `max_length` `4000` -> `400` instead: the served API then refuses a 401-character
  comment the contract and generated client call valid, and `tests/integration/api
  tests/integration/composition tests/contract tests/e2e` still ran green (1119
  passed). Added to `test_openapi_conformance_live.py`'s docstring as a second
  reproduction and shown failing in-tree, reverted: red -- `schemas.
  AppendDecisionRequest.properties.comment.anyOf[0].maxLength: the contract has 4000,
  the generated document has 400`. Re-run: `1 passed`.
- **G2 / X-2.** Y found a wrong *non-zero* spend count already caught
  (`model_call_count=calls+1` reddens), but wrong run-state and section counts were
  not covered by any test that both seeds a run and reads its state -- an accurate
  narrowing of X-2's *"cannot fail on a count"*, since the third pre-existing test
  seeds a document and a run and only asserts `spend`. My `test_a_deployment_with_
  known_data_reports_the_exact_counts` (added in step 3) already asserts exact numbers
  for both dimensions; shown explicitly against Y's own two reproductions, in-tree,
  reverted after each: `_DOCUMENTS_BY_SECTION` relabelled to report every document as
  `'KM'` -- red, `{'AR': 0, ..., 'KM': 3, ...}` (Y's own *"КМ: 3, Без раздела: 0"*
  shape); `_RUNS_BY_STATE` relabelled to report every run as `'published'` -- red,
  `{'published': 9, 'created': 0, ...}`. Re-run: `4 passed`.
- **G3 / X-4.** Y measured that X's code fence is incidental: an ordinary, non-fenced
  `### What the historical record below keeps`, placed after the first claim, gave `21
  passed` with a stale migration head, under the pre-repair guard. My shape check
  (step 4) already closes this class generically (it does not depend on fencing), and
  `test_a_too_early_heading_after_the_first_claim_is_still_caught` already covers the
  same shape with wording of my own -- added `test_judge_ys_own_heading_after_the_
  first_claim_is_still_caught`, reproducing Y's exact heading text literally, so
  nothing about the repair depends on a paraphrase happening to be caught too. Red
  before the repair existed (this is what step 4 fixed); with the repair,
  `_historical_boundary` raises *"does not look like this file's genuine heading"* on
  Y's exact text, same as my own. `tests/contract/api_v1/test_doc_prose_facts.py`:
  `26 passed` (25 + 1 new).
- **G4 / X-7.** Y measured that the correlation-header exemption compared the header's
  *spelling* (`resolved["name"] != "X-Correlation-Id"`), not the HTTP header -- RFC
  9110 section 5.1, header field names are case-insensitive -- so `x-correlation-id`
  or `X-CORRELATION-ID` was counted as caller input it is not (harmless today: nothing
  in the document spells it any other way). Changed the comparison to
  `resolved["name"].lower() != "x-correlation-id"`. Added `test_the_correlation_
  header_exemption_is_case_insensitive`: a differently-cased correlation header alone
  is not caller input; the same header plus a genuinely new one still is (the
  exemption is for one header, not for every header once any capitalisation of it is
  present). Shown failing under the pre-repair comparison (reverted just that one line
  in-tree, ran the new test, reverted back): red -- `assert True is False`.
  `tests/contract/domain_p02/test_openapi_document.py`: `51 passed` (50 + 1 new).

**Run, all four together.** `tests/contract` scope: `378 passed, 49 subtests passed`
(376 after G4, +2 -- the two brand-new permanent tests; the G1 and G2 strengthenings
are additional demonstrations on already-existing tests, not new test functions).
`git status --porcelain` on every mutated source file, after each revert: empty.

## 7. G5 — the reseal

`RunActivity.spend` ($ref to `RunActivitySpend`) carried no `description` at all.
`RunStatus.cost_micros` already says in the contract *"Absent when the run made no
provider call at all, which is a different fact from a cost of zero"*; the reseal that
made `spend` optional (`W46-SPEND`, `069f656`) gave it the same behaviour without
writing what the absence means into the contract, so a client author reading the
generated type had nothing to read (`types.gen.ts:484`, `spend?: RunActivitySpend`, no
doc comment) -- X-11, confirmed by Y's cross-examination.

**One sentence, as a `description` sibling to the `$ref`** -- the same shape
`DocumentVersion.section` and `SectionDocumentCount.section` already carry in this
contract (a description beside a `$ref`, not inside the target schema, because the
sentence is about *this property's absence*, not about `RunActivitySpend` in general):
*"Absent when the deployment has made no provider call."* Edited directly in
`contracts/api/v1/openapi.json`, copied byte-for-byte onto `web/openapi/openapi.json`
(`cmp`: byte-identical before and after), then `npm --prefix web run api:generate`.

**Shape, checked.** `RunActivity.required` untouched (still `["by_state"]`); `paths` /
`operations` / `component_schemas` stay `17` / `20` / `61`; the error catalog stays
`22` (`contracts/domain/v1/error-codes.json` untouched). The regenerated
`types.gen.ts` gains exactly one line, a JSDoc comment above `spend?:
RunActivitySpend` -- the property declaration itself is byte-for-byte the same
(`spend?: RunActivitySpend;` before and after); `client.gen.ts`, `index.ts` and
`operations.gen.ts` each change exactly one line, the embedded contract-digest
comment. `npm --prefix web run api:verify` → *"OK - 20 operations"*.

**Digests recomputed with `sha256sum` against this tree**, not copied forward: contract
= mirror = `78eccd9e01de92…`; `client.gen.ts` `f5ab53b9…`; `index.ts` `16841483…`;
`operations.gen.ts` `6223d863…`; `types.gen.ts` `ec030263…`. Generator script digest
unchanged (`787c744d…` -- the script itself was not touched). `lockfile_sha256`
unchanged (no dependency moved).

**`content_commit` moved to `069f656`** (*"feat(reseal, F-1): run_activity.spend
optional -- one commit, five documents"*, `W46-SPEND`'s own reseal commit) --
`dispatch_named_commit` copied alongside it, per the convention `X-11` measured
(*"the field has simply copied `content_commit` since `W45-BLOCKS`"*). A commit cannot
name itself; `069f656` is the nearest commit that made *"absent when the deployment
has made no provider call"* real in behaviour, the same reasoning `W42-SEAL`'s own note
already uses for a description-only reseal.

**The `commit_note` correction, same commit.** The sentence in the (now second)
paragraph -- *"which content_commit names for the reason every reseal note below
gives: a commit cannot name itself"* -- is false as X measured it: three of the eight
notes below it give that reason (`W46-SEAL`, `W45-BLOCKS`, `W42-SEAL`), five do not
(`W18-SEAL`, `W25-SEAL`, `W34-CONTRACT`, `W38-KB`, `W39-REVOKE`). Corrected in place to
name the three.

**Run.** `npm --prefix web run typecheck`: clean. `npm --prefix web run test:guards`:
`149 passed` (15 files), including `frontend-lock.guard.test.ts`'s own digest
recomputation. `npm --prefix web run test:contract`: `104 passed`. Backend:
`test_openapi_conformance_live.py`, `test_doc_prose_facts.py`,
`test_openapi_conformance.py`, `test_surface_counts_in_prose.py`: `134 passed`.
`tests/contract` scope, whole: `378 passed, 49 subtests passed` -- unchanged from step
6, as expected for a description-only reseal (the conformance engine drops
`description` as annotation under `N4`).

**Files changed by this reseal, all five plus the mirror:**
`contracts/api/v1/openapi.json`, `web/openapi/openapi.json`, `web/FRONTEND_LOCK.json`,
`web/src/shared/api/generated/{client.gen.ts,index.ts,operations.gen.ts,types.gen.ts}`.

## 8. Final gate

*(filled at the end)*
