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

*(filled as the work proceeds)*

## 5. G4 — a cookie is input

*(filled as the work proceeds)*

## 6. G5 — the reseal

*(filled as the work proceeds)*

## 7. Final gate

*(filled at the end)*
