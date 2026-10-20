# W63-SECTION-FORM7-01 — «Оптимизация разделов»: the section's combined Form-7 specification

**Base:** `024d1d31` (`W60-OPT-MATCH-01` phase A `67fd24c0` plus this task file), branch
`agent/w63-section-form7-01`, isolated worktree `w63-section-form7`, lane PostgreSQL 57600 /
MinIO 61200–61201, database `auditmanager_w63_section_form7`. **Status:** phase A (the section
query) complete; phase B (one read operation, the reseal, the page replacing the stub) waits
for the contract slot. Development candidate under `R-135`: no full gate, no live journey, no
push, merge into another branch or tag. No migration, no new dependency, no LLM, nothing
persisted.

## Phase A — result

`src/auditmanager/optimisation/section_specification.py` —
`read_section_specification(session, section_code, actor_roles, reader, project_uid=None,
query=None, offset=0, limit=50)`. It reuses «Спецификация и цены» additively: the port
`SavedTextReader` and its run/text checks, the price-list position read, the extractor and the
matcher (`project_match.py`, `specification.py`, `matching.py` are not edited).

### Composition

1. **Membership** from the documents projection (`DocumentRepository.list_projects` and
   `list_documents`, the current version of every set with its persisted classification):
   a set whose **current** version is confirmed in the section is a *source*. A current
   version confirmed in another section is absent from the answer — not a project, not an
   exclusion, not a row, its price list not read. A current version nobody classified is
   listed in `excluded` (`reason: version_unclassified`) and contributes nothing; an older
   version's classification never counts (the warehouse case in the integration test).
2. Per project, its **current price-list revision** and all positions, or the price state
   `price_list_missing`. Rows are still served without one, with no match at all and no
   figure (`price_status: price_list_missing`).
3. Per source, the newest **published** run and its verified saved text layer through the
   port, or the source state `analysis_missing` / `text_unavailable` /
   `specification_too_large`; the other sources of the same project are still read.
4. Extraction (`specification-text-v1`) and matching (`price-match-v1`) of each source's
   rows against **its own project's** positions only.

**The section code is a filter, not an identity** (`W59-SECTION-IDENTITY-DECISION-01`): every
row carries project, document set, version, page, sheet label and line span (plus the
extractor's `row_id`); rows are never merged across projects — the same product in two
projects is two rows, each priced from its own list. **Totals exist only per project and per
currency** (`SectionProject.totals`, over that project's ready sources); the read model has
no section total and converts nothing.

### Order, filters, paging

- Projects by display name (case-folded), then `project_uid`; a project's sources by set
  title, then `document_uid`; rows by project, source, page, line. Names order the view;
  identities stay the uids.
- `project_uid` narrows projects, exclusions and rows to one project; an unknown project is
  `not_found` `Project`; a known one without a member set answers an empty section.
- `query` (≤ 200 characters) keeps the rows whose own Form-7 text — position, description,
  group heading, unit as printed, note — contains it after case folding, `ё`→`е` and
  whitespace folding. It never narrows projects, their states or totals; `row_count` counts
  every row in scope, `rows.total` the rows kept.
- Rows paged `offset` ≥ 0, `limit` 1..200 (default 50), as in «Спецификация и цены».

### Bounds (documented caps)

| Cap | Value | Over it |
| --- | --- | --- |
| projects scanned for membership (one documents read each) | 1000 | `section_too_large`, `limit_reason: projects`, nothing listed |
| member sets read (one run lookup, one text layer, one extraction each) | 20 | `section_too_large`, `limit_reason: sources` |
| rows in all (each version also ≤ 10 000 by the extractor) | 20 000 | `section_too_large`, `limit_reason: rows` |
| rows per page | 200 | `validation_failed` |
| exclusions listed | 200 | count complete |

Over the sources or rows cap the membership is still served (projects, sets, versions,
exclusions) with every source and price state `not_read` and no rows or totals; one project
named is the way in. Never a cut list.

### Refusals

Any one role reads (`permission_denied`, `required_capability: role:admin|expert`,
`aggregate_type: SectionSpecification`); `section_code` outside the fifteen codes, a malformed
`project_uid`, a non-text or over-long query and out-of-range paging are `validation_failed`
with the field; a port or projection answer that contradicts itself (a version listed under
another project, a classification of another version, a newest price list not current, a
malformed run id, text of another run or with missing pages) is `internal_error`.

### Checks (phase A)

Lane containers (`make up`, `make migrate` to `0026_price_lists`), `.env` from `.env.example`
with the lane values, `.venv` linked to the `w55b-main-candidate` interpreter,
`$PY -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <paths>`. Host before the
runs: `df -h /` 7.7 GiB free, `free -g` 6 GiB available (2026-10-20).

- `tests/unit/optimisation/test_section_specification.py` — 21 passed (in-memory documents
  projection, price lists and port): membership and order, another section absent everywhere,
  the unclassified version excluded, several member sets per project, provenance on every row,
  rows never merged, own price list per row, no figure without a price list, totals per
  project and currency and no section total, explicit source states, the empty section, the
  project filter, the folded query that never narrows totals, paging, the three bounds, the
  exclusion cap, roles and request values, contradictory answers, determinism.
- `tests/integration/optimisation/test_section_specification.py` — 9 passed on the lane's
  PostgreSQL and MinIO (projects, sets, versions, Blobs, classifications and price-list uploads
  through their boundaries; runs and text through the port): two AR projects with the same
  sheet and different lists (door 4 × 25 000 = 100 000 RUB vs 4 × 31 000 = 124 000 RUB), a KJ
  project never seen in AR and alone in KJ, a project whose older version was AR and whose
  current version is unclassified listed as excluded and never read, an AR project without a
  price list, a set without a published run, filter + query + paging, the source bound,
  nothing written, roles.
- Whole `tests/unit/optimisation`, `tests/integration/optimisation` and
  `tests/contract/architecture`: 272 passed, exit 0.
- Mutation probes (each applied to the module, both new suites run, the module restored and
  its SHA-256 `d719e193…dba1ee` compared): every one turned tests red —
  M1 every row priced from the first project's list (5 failed); M2 a version of another
  section admitted (16); M3 unclassified versions not listed (8); M4 a project's totals
  accumulating earlier projects' rows (9); M5 identical rows merged across projects (6);
  M6 the source bound ignored (2); M7 a project without a price list matched against nothing
  (2); M8 the query narrowing the projects' totals (2); M9 the rows bound ignored (1).
- Deferred under `R-135`: the full gate, the whole contract battery, the frontend, the live
  journey.

### Known limitations

- Membership scans every project (one `list_documents` per project, capped at 1000): the
  documents boundary publishes no "current versions confirmed in section X" statement, and
  `documents/**` is outside this task. A follow-up can add it there without changing this
  read model.
- Each request re-reads every member set's text layer and price list (≤ 20 sets): nothing is
  cached or persisted, by the non-goals.
- The extractor's limits carry over: type/mark, code and manufacturer stay inside the
  description (the saved text has no column geometry), tables continued without a header are
  not read.
- A project's own price list prices all of its sets in the section; a per-section price list
  does not exist (`0026` positions carry an optional section that the matcher does not filter
  on — unchanged from «Спецификация и цены»).

## Phase B

Pending the integrator's go: proposed operation
`GET /sections/{section_code}/specification?project_uid&q&offset&limit`, `operationId
getSectionSpecification`, any one role, read only.
