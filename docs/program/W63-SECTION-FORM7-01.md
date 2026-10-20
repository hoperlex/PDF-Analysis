# W63-SECTION-FORM7-01 — «Оптимизация разделов»: the section's combined Form-7 specification

**Base:** `024d1d31` (`W60-OPT-MATCH-01` phase A `67fd24c0` plus this task file), branch
`agent/w63-section-form7-01`, isolated worktree `w63-section-form7`, lane PostgreSQL 57600 /
MinIO 61200–61201, database `auditmanager_w63_section_form7`. **Status:** phases A and B complete
(the section query; one read operation, the reseal, the page replacing the stub), merged with
`integration/night-1020` at `e668171b`. Development candidate under `R-135`: no full gate, no live journey, no
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

## Phase B — the operation, the reseal and the page

### Surface

| | integration base `1c643357` | + this slice | merged with `e668171b` |
|---|---|---|---|
| paths / operations / schemas | 65 / 74 / 211 | 66 / 75 / 217 | **71 / 81 / 235** |
| API error codes / migration head | 25 / `0026_price_lists` | unchanged | 25 / `0027_optimisation_proposals` |

`getSectionSpecification` — `GET /sections/{section_code}/specification` (`project_uid`, `q`
(1..200 characters), `offset` ≥ 0, `limit` 1..200, default 50), tag `optimisation`, any one role
(`role:admin|expert`). `200 SectionSpecification`: `state` (`ready` | `section_too_large`) with
`limit_reason` (`projects` | `sources` | `rows`), `project_filter`, `query`, the two algorithm
names, `projects[]` (name, `price_state` `priced` | `price_list_missing` | `not_read`, the price-list
ref, `sources[]` — document, title, version, stage, `state` `ready` | `analysis_missing` |
`text_unavailable` | `specification_too_large` | `not_read`, run, digest, row and table counts, skipped
lines by reason — `row_count` and, only when priced, the project's own `matching`: counts, totals
per currency, exclusions by reason), `excluded[]` (current versions nobody classified, first 200,
`excluded_count` complete), `source_count`, `row_count` and `rows` (one page; each row with project,
document, version, sheet, page, line span, the Form-7 fields, `price_status` `matched` |
`ambiguous` | `unmatched` | `price_list_missing`, the match and the exact-text `amount`). There is
no section total anywhere in the schema. `404` for an unknown `project_uid` filter (`Project`) and
for a section code outside the fifteen (`SectionSpecification`, the operation's own aggregate);
`422` for malformed filters and paging; `403` for an account with no role. Six schemas built
from the priced specification's own (`SpecificationPriceListRef`, `SpecificationMatching`,
`SpecificationPricePosition`, `SpecificationSkipCounts` are reused, not repeated); no new error code,
no new detail key.

### Backend

- `api/routers/section_specification.py` (the twenty-third router module), `SectionSpecificationPort`
  (optional in `build_router`, parameter `section_specifications`), `api/security.py`
  (`getSectionSpecification: _ANY_ROLE`), `api/schemas/models.py` (six schemas),
  `optimisation/public.py` (the exports the composition root needs).
- `bootstrap/adapters.py`: `SectionSpecificationAdapter` over **the match lane's**
  `_SpecificationTextReader` (the `SavedTextReader` port over the comparison's `_AnalysisReader`);
  nothing duplicated — the price-list ref, price position and matching mappings of
  `_specification_prices_view` were extracted into three helpers both views call, behaviour
  unchanged (its over-HTTP suite passes).
- `api/routers/handlers.py`: `AGGREGATE_OF_OPERATION_PATH_PARAMETER` — the path parameter
  `section_code` already meant a vendor-list slot (`VendorList`); for `getSectionSpecification`
  a malformed code is `404` naming `SectionSpecification`.
- `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`: a third kind of
  `GET` (`SECTION_FILTER_OPERATIONS`): addressed by a closed code, not by a parent identity; swept
  for its own two refusals.

### Web

- `entities/section-specification`: `useSectionSpecification` (the previous page of the same
  section, project and search stays while the next loads; `staleTime: 0` — see risks), the
  Russian labels of the section's states, bounds and exclusions; the match labels and exact
  money formatting are `entities/specification-price`'s.
- `widgets/section-specification`: `SectionSpecificationSection` (the section picker in the
  owner's `S-5` order, АР first; the project filter, offered from the unnarrowed answer; the
  search; «Обновить»), `SectionSpecificationAnswer` (one panel per project — sets, its own price
  list or «нет прайс-листа», its own totals per currency; the excluded versions; the Form-7 table
  with project, set, version, sheet/page and line span on every row and the match against that
  project's list; a bound said in words with the way in; a pager) and its own CSS module.
- `_pages/section-optimisation` replaces the honest stub; the route file's comment and the screen
  registry's commentary say so (the row, group, access and menu place are unchanged).
- Guards moved with it: `prepared-sections.guard` has no stub left (an explicitly empty,
  typed list; its `can fail` cases still run), `r66-navigation` holds `/section-optimisation` as a
  graduated screen with its ruled row, a cold-route read and the guest redirect,
  `rendered-language.guard` renders the container (pending, refused) and the answer in thirteen
  shapes, the contrast census renders a ready and a bound answer, the journey manifest declares
  the cold read, `ALPHA_PUBLIC_ACCEPTANCE.md` item 19 says what to look at, `PC01_UI_SEAM.md`
  records the query key.

### Reseal files

`contracts/api/v1/openapi.json` (path and six schemas inserted in the contract's own style,
`info.description` gains a reseal paragraph), byte-identical `web/openapi/openapi.json`,
regenerated `web/src/shared/api/generated/**` (`npm --prefix web run api:generate`),
`web/FRONTEND_LOCK.json` (digests recomputed from the files), `tests/support/expected_facts.json`,
the registers in `tests/contract/domain_p02/test_openapi_document.py`,
`tests/contract/api_v1/{test_openapi_conformance,test_surface_counts_in_prose}.py`,
`tests/integration/api/{test_authorization,test_role_register,test_served_document_and_health_plane,test_query_surface}.py`,
`tests/integration/composition/{test_every_port_implementation_is_whole,test_an_absent_parent_is_not_an_empty_page}.py`,
and the surface prose in `P02_SEAMS.md`, `ALPHA_ROADMAP.md`, `infra/deploy/{README.md,proxy/nginx.conf,serve.py}`,
`api/{README.md,app.py,health.py}`, `api/routers/{__init__,declarations,errors}.py`, the BFF
`route.ts` and `shared/api/authorization.ts`. `CONTRACT_PIN_REGISTRY.md` needed no change (no
needle moved). `docs/program/CURRENT_STATE.md` is the integrator's and still states 70/80/229.
After the merge of `e668171b` every generated artifact and count was re-derived from the merged
contract, not merged by hand (the contract's path and schemas were re-inserted into the
integration side's document by the same script).

### Checks (phase B)

Interpreter `PY=/root/projects/PDF-Analysis/.local/worktrees/w55b-main-candidate/.venv/bin/python`,
`$PY -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider`, the lane's containers
(`make up` / `make migrate`; they died with the 07:00 reboot and were raised again, migrated to
`0026` and then, after the merge, to `0027_optimisation_proposals`), host before the runs 6–7.7 GiB
free on `/`, 4 GiB memory available. The tree is the merge commit; the integration tip checked is
`e668171b`.

| Command (paths) | Result |
|---|---|
| `npm --prefix web ci` (once) | exit 0 |
| `npm --prefix web run api:generate` / `api:verify` | 81 operations, contract SHA-256 `8894201e…7a5b`, `--check: OK` |
| `npm --prefix web run lint -- --quiet` | exit 0 |
| `npm --prefix web run typecheck` | exit 0 |
| `vitest run tests/guards tests/contract tests/unit/{api,styles,section-specification,specification-prices,optimisation,optimisation-proposals,screens,shell,qa_w50,ui,journey,projects}` | 84 files, 1389 passed (rendered-language guard, contrast census, frontend lock, drift, screen registry, prepared-sections, R-66 navigation among them) |
| `pytest tests/contract` (whole directory) | only the known reds: the sandboxed CP-00 families (`test_cp00_candidate`, `test_cp00_final_state`, `test_validate_bootstrap`), `test_error_kernel::test_there_are_twenty_four`, `test_ar_v2_seeded::test_seeded_categories_equal_the_sealed_api_enum`, `test_alpha_acceptance_command` (refuses an uncommitted tree) and `test_doc_prose_facts::test_the_scanned_docs_state_the_contract_surface_this_tree_has`, whose only finding is `docs/program/CURRENT_STATE.md` stating 70/80/229 (the integrator's file) |
| `pytest tests/e2e/test_pc01_journey_conformance.py` | 87 passed |
| lane containers: `tests/unit/optimisation` | 213 passed |
| lane containers: `tests/integration/optimisation/{test_section_specification,test_project_match}.py` | 9 + 11 passed |
| lane containers: `tests/integration/composition/test_section_specification_over_http.py` | 11 passed (membership across projects, each project's price state, a recorded run publishing and its saved text read from MinIO, the search, both `404`s, `422`s, `401`) |
| lane containers: `tests/integration/api` (whole) and the composition registers (`test_every_port_implementation_is_whole`, `test_an_absent_parent_is_not_an_empty_page`, `test_composition_root`, `test_specification_prices_over_http`) | 982 passed in all, 3 failed — the known reds below |

Reds present before this change and not caused by it:
`tests/integration/api/test_query_surface.py::test_the_filter_vocabularies_are_the_frozen_ones`
(`12 == 2`, `FindingCategory`),
`...::test_every_declared_query_parameter_is_read_by_the_router_that_declares_it` (names
`compareDocumentVersions` and `listPriceListPositions`, undriven by their own lanes; this slice
drives `getSectionSpecification` in its own test in that file and is not in the list) and
`test_every_port_implementation_is_whole::test_pre_decide_adapter_refuses_a_severity_instead_of_dropping_it`
(`DecisionAdapter`).

Mutation probes (applied, run, restored; digests compared). Backend, on the lane stack:

| Mutation | Result |
|---|---|
| the section `404` naming another operation's aggregate | 3 failed (the query-surface test, the absent-parent sweep, the over-HTTP `404` test) |
| the operation limited to experts | 3 failed (`test_role_register`) |
| the project filter dropped by the adapter | 4 failed (over HTTP) |
| a `matching` built for a project without a price list | 3 failed (over HTTP) |
| the search text not passed by the handler | `test_section_specification_reads_the_query_parameters_it_declares` fails by name |
| the adapter not handed to the router | 6 failed (over HTTP, the port-completeness register) |

Web:

| Mutation | Result |
|---|---|
| a price and an amount on every row with a matched position, counted or not | 1 failed |
| an absent amount written as `0` | 3 failed |
| a total for the whole section | 1 failed |
| identical products of two projects shown once | 4 failed |
| a project without a price list given a total | 1 failed |
| an English sentence in the bound message | 2 failed (`rendered-language.guard`) |
| an empty search / an empty project filter sent to the server | 2 / 1 failed |
| the picker in a different order than `S-5` | 1 failed |
| the excluded versions hidden | 1 failed |
| phase A's nine probes (another project's list for every row, another section admitted, unclassified versions unlisted, totals accumulating across projects, rows merged, the source and row bounds ignored, a list-less project matched against nothing, the search narrowing the totals) | each red; see Checks (phase A) |

Deferred under `R-135`: the full gate, the live journey (`e2e:pc01`; `tests/e2e/pc01/qa_w50/r66.mjs`
still lists `/section-optimisation` among the stubs it expects to say «не готов» — it already
listed three screens that graduated earlier, and is not run by any code-first check) and the
manual acceptance of the page on the stand.

### Risks and integrator instructions

- Merge `agent/w63-section-form7-01` after `e668171b`. If another reseal lands first, keep both
  sides' paths and schemas in `contracts/api/v1/openapi.json` and re-derive everything else
  (mirror copy, `api:generate`, `api:verify`, `FRONTEND_LOCK.json`, `expected_facts.json`, every
  surface count in prose — the count guard names each file). The lock digests and the contract
  insertion were produced by scripts, not typed.
- `docs/program/CURRENT_STATE.md` is the integrator's and must move to 71/81/235.
- **Membership scans every project** (one `listDocuments` per project, ≤ 1000) and each request
  re-reads the text layers of ≤ 20 member sets: the documents boundary publishes no "current
  versions confirmed in section X" statement and `documents/**` is outside this task. Over a
  bound the answer is a state, not an error, and one project is the way in; over 1000 projects
  the project filter has nothing to offer from the answer (a project list for the filter is a
  follow-up).
- Prices are read from each project's current price list on every request. The price-list
  upload command lives in `features/**`, outside this task's paths, so it does not invalidate the
  section's query key; the section's query is `staleTime: 0` instead and re-reads on every
  mount. If the owner of that feature wants an upload to refresh an open page, one line adds
  `queryKeys.optimisation.sectionSpecification` as a prefix to its invalidations.
- The saved text has no column geometry (see phase A): type/mark, code and maker are part of the
  description on every row, and the page says so under the table.
- `prepared-sections.guard` now holds an empty list of stubs. It stays as the mechanism for the
  next stub; delete it with the last reference if the owner prefers.

### Hotspot proof

No migration, dependency file, `web/src/_app/providers.tsx`, global style, `specification.py`,
`matching.py`, `project_match.py` or `CURRENT_STATE.md` was touched; the three optimisation
modules are used additively (`project_match`'s helpers `_checked_text`, `_newest_published`,
`_positions` are imported inside the same context). Every path in `git diff --name-only e668171b HEAD`
is granted by the task file: `src/auditmanager/optimisation/{section_specification,public}.py`,
`src/auditmanager/{api,bootstrap}/**`, `contracts/api/v1/**`, `tests/{support,contract,e2e/pc01}/**`,
`tests/integration/{api,composition,optimisation}/**`, `tests/unit/optimisation/test_section_specification.py`,
`web/{openapi,docs,tests}/**`, `web/FRONTEND_LOCK.json`, `web/src/{shared/api,shared/config/screen-registry.ts,entities/section-specification,widgets/section-specification,_pages/section-optimisation,app/section-optimisation,app/bff/v1}/**`,
`docs/manual-tests/**`, `docs/program/{P02_SEAMS,ALPHA_ROADMAP,W63-SECTION-FORM7-01}.md` and
`infra/deploy/{README.md,proxy/nginx.conf,serve.py}`.
