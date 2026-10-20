# W60-OPT-MATCH-01 — «Спецификация и цены»: the AR specification priced from the project's list

**Base:** `15f9715b` (`W60-PRICE-LIST-01` phase A `6d86b991` plus this task file), then merges
of `beafeab5`, `f7664f59` (dispatcher) and `40cd159f` (price lists served, head `0026`);
branch `agent/w60-opt-match-01`, isolated worktree `w60-opt-match`, lane PostgreSQL 57580 /
MinIO 61180–61181. **Status:** phases A and B complete — extractor, matcher, query, the read
operation with its reseal, and the «Спецификация и цены» section mounted in the project's
«Оптимизация» tab. Development candidate under `R-135`: no full gate, no live journey, no
push, merge into another branch or tag. No migration, no new dependency, no LLM, nothing
persisted.

## Phase A — result

For a document set of a project the query reads the set's current version, requires the
expert's persisted classification to be section `AR`, takes the project's current price-list
revision, the version's newest **published** run and that run's verified saved
`prepared.text_layer`, extracts the specification rows deterministically and matches each one
against the price list as matched / ambiguous / unmatched with its reason. A price and an
amount appear only on a row matched to exactly one position, in the same unit, with a numeric
quantity; totals are per currency over those rows only and state how many rows each reason
leaves out.

### `optimisation/specification.py` — rows from the saved text

The saved text layer is pdfplumber's lines joined by `\n`; **a line has no column
separators**, the cells of a row are joined by single spaces and the extractor sometimes
glues words (`Наименованиеитехническаяхарактеристика`). The module therefore reads only what
plain text makes unambiguous (`EXTRACTION_ALGORITHM = specification-text-v1`):

- **Header**: one to three consecutive lines that name `Наименование`, a quantity column
  (`Кол.`, `Кол-во`, `Количество`) and at least one more Form-7 column (`Поз.`,
  `Тип, марка`/`Обозначение`, `Код`, `Завод-изготовитель`/`Поставщик`, `Ед. изм.`, `Масса`,
  `Примечание`); glued words and split headers (`Ед.` / `изм.`) are read; a title line above
  is not part of it. A drawing stamp, a room or finishing schedule (`Наименование помещения`,
  `№ пом.`) is never a header. Two quantity or two name columns make the header
  **ambiguous**: the table is reported and not read.
- **Row with a unit column**: the one place where a recognised unit is followed by a plain
  number or a dash. Before it: an optional position number and the description; after it: the
  quantity, the unit mass (when the header has a mass column) and the note. Two such places
  in a line → skipped `anchor_ambiguous`.
- **Row with the unit in the quantity header** (`Кол-во, шт.`) or none: the rightmost plain
  number with no digit after it; with a position column a row must start with a position.
- **Multi-line names**: an unanchored line continues the open row (at most 3 lines); a short
  group heading (`Оборудование`, `Материалы`…) labels the rows after it.
- **End**: a stamp line, `Примечание`/a numbered note, the next header, more than 6 unanchored
  lines in a row, the end of the page (no table crosses pages).
- **Units** normalised to `шт`, `м`, `м2`, `м3`, `кг`, `т`, `компл`, `п.м` (`м²`, `кв. м`,
  `куб. м`, `шт.`, `к-т`, `пог. м`, `м.п.`…); `п.м` is kept apart from `м`.
- **Quantities**: exact decimals with a comma or a point; a dash is `not_numeric`; `1 250`
  before a mass or note column is `ambiguous` (1250, or 1 and 250?) and never a number.
- **Provenance**: page, sheet label (from the stamp's «Стадия Лист Листов» cell when legible),
  1-based line span, table ordinal, group; `row_id = "sr-" + sha256(algorithm | version |
  page | span)[:32]` — a provenance key, not a stored identity.
- **Report**: every line inside a detected table that becomes neither a row nor part of one
  is a skip with one of eight reasons (first 200 listed, counts complete); tables listed (200)
  with columns, implicit unit, status and row count.

In a text layer the description holds the name **and** the type/mark, code and manufacturer
cells the row fills, in Form-7 order: they cannot be told apart without column geometry,
which the saved text does not keep.

### `optimisation/matching.py` — the money rule

Per row, exact on normalised text, never fuzzy (`MATCH_ALGORITHM = price-match-v1`):

1. **code / mark**: a position's code or mark that occurs as whole tokens in the row's
   description; only specific keys (≥ 5 characters with a digit and a letter, or ≥ 6 digits;
   never a bare `ГОСТ`/`ТУ`/`СП`/`ISO`… reference). A code hit is not abandoned for a name hit.
2. **name**, only without a code hit: the description equals the position's name, or its name
   followed by any combination of mark, code and vendor in Form-7 order.
3. candidates in the row's unit: one → `matched`; several → `ambiguous`
   (`several_positions`); none → `unmatched` (`unit_mismatch`); a row without a unit →
   `row_unit_missing`; no candidate → `no_position`.

Normalisation on both sides: case, `ё`/`е`, Latin letters printed like Cyrillic ones, the
decimal comma, punctuation, whitespace (the name key drops spaces, so glued words compare
equal), and a closed abbreviation set (`мет.`/металлический, `оцинк.`/`оц.`/оцинкованный,
`нерж.`/нержавеющий, `ж/б`/железобетонный, `толщ.`/толщина, `диам.`/`∅`/диаметр). Units
compare by the canonical unit, else the compact spelling.

`amount = quantity × unit_price`, exact, never rounded (served as plain decimal text);
totals per currency, never converted; every row without an amount carries exactly one of
`no_position`, `unit_mismatch`, `row_unit_missing`, `ambiguous`, `quantity_not_numeric`. The
amount is computed behind two barriers: the unit filter of step 3 and `_contributes`
(matched position, numeric quantity, equal unit, a currency).

### `optimisation/project_match.py` — the query

`read_specification_prices(session, project_uid, document_uid, actor_roles, reader,
offset=0, limit=50)`: any one role reads (`permission_denied` `role:admin|expert`
otherwise); identifiers and paging are `validation_failed`; an unknown project is
`not_found` `Project`, a set outside the project `not_found` `Document`. Explicit states, in
order: `version_unclassified`, `section_not_ar`, `price_list_missing`, `analysis_missing`
(no published run), `text_unavailable`, `specification_too_large`, else `ready` — each with
the facts read so far (version, stage/section, price list, run, layer digest). The runs and
text come through the context's own port `SavedTextReader` (`runs_newest_first`,
`saved_page_text(run_id, version_uid, page_count)`), the comparison's pattern; an answer that
contradicts itself (malformed run id, another run's text, missing pages) is
`internal_error`. Bounds: ≤ 10 000 rows per version (more is `specification_too_large`, not
a cut table), rows served ≤ 200 per page while counts and totals cover every row, price-list
positions read in pages of 5 000 (≤ 20 000 by `0026`).

### Checks (phase A)

Lane containers (`make up`, `make migrate` to `0026_price_lists`), `.env` from
`.env.example` with the lane values, the `w55b-main-candidate` interpreter,
`python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <paths>`; host before
the runs 6.3 GiB free on `/`, 7 GiB memory available.

- `tests/unit/optimisation/test_specification.py` — 46 passed: the split Form-7 header with
  all nine columns, positions, multi-line names, groups, the eight units and their spellings,
  decimal comma, mass and note, the dash and the digit-grouping ambiguity, two anchors
  skipped, the real AR excerpt, stamps and room schedules not headers, the ambiguous header,
  the page end, continuation and unanchored bounds, the implicit unit with a mass column,
  row-id provenance, the row bound and the skip-listing cap, determinism.
- `tests/unit/optimisation/test_matching.py` — 43 passed: code and mark hits, short and
  shared keys refused, no fallback from a code hit, ties, the name normalisations and the
  non-fuzzy cases, the Form-7 combinations, unit mismatch and unit choice, rows without a
  unit or a numeric quantity, the candidate cap, per-currency totals with every exclusion
  counted, exact amounts, order independence, the guard itself.
- `tests/integration/optimisation/test_project_match.py` — 11 passed on the lane's PostgreSQL
  and MinIO (project, version, Blob, classification and two price-list uploads through their
  boundaries; runs and text through the port): every state with how far the read went, the
  priced specification from the current revision and the newest published run with totals
  RUB 502006.0 (3 rows) and EUR 2550.00 (1 row), paging, the bound, nothing written, scope,
  roles, request values, port integrity.
- Whole `tests/unit/optimisation` 187 passed; whole `tests/integration/optimisation` 52 passed.
- `tests/contract/architecture` and `tests/contract/api_v1/test_doc_prose_facts.py`: all pass
  except `test_the_scanned_docs_state_the_migration_head_this_tree_has`, red at the base
  (`CURRENT_STATE.md` and `PC-01_prototype.md` still say `0024`).
- The real AR set `13АВ-РД-АР-ТП1-ТП2` (30 pages, local portal export, extracted by
  `analysis.stages.extraction`): one table (the metal-products schedule, sheet 10), two rows,
  one skip (`position_missing`, drawing text on a row's baseline); the room and finishing
  schedules and the two-quantity masonry schedule produce no rows.
- Mutation probes, each restored afterwards (digests compared), each turned a test red:
  dropping the unit filter; dropping the filter and the amount guard (a unit mismatch into the
  total); summing totals across currencies; pricing an ambiguous row at its first candidate;
  the guard ignoring the quantity; reading `1 250` as 1250 before a mass column; admitting a
  bare standard reference as a code key; pricing a non-AR version; taking the newest run
  whatever its state; taking an older price-list revision; accepting a text layer with
  missing pages.
- Deferred under `R-135`: the full gate, the whole contract battery, the frontend, the live
  journey.

## Phase B — the operation, the reseal and the tab

### Surface

| | before (`40cd159f`) | after |
|---|---|---|
| paths / operations / schemas | 64 / 73 / 198 | 65 / 74 / 211 |
| API error codes / migration head | 25 / `0026_price_lists` | unchanged |

`getSpecificationPrices` — `GET /projects/{project_uid}/documents/{document_uid}/specification-prices`
(`offset` ≥ 0, `limit` 1..200, default 50), tag `optimisation` (the price-list slice's), any one
role (`role:admin|expert`). `200 SpecificationPrices`: `state` (`ready`, `version_unclassified`,
`section_not_ar`, `price_list_missing`, `analysis_missing`, `text_unavailable`,
`specification_too_large`) with the facts read before it stopped — version, stage and section,
price-list ref, run and text-layer digest — and, when `ready`, the extraction summary (tables,
rows, skipped lines by reason, listings capped at 200), the match counts, the totals per
currency, the excluded rows by reason and one page of rows, each with the Form-7 fields, page,
sheet, line span, the match (`status`, `reason`, `basis`, the price-list position, at most five
candidates) and `amount`/`excluded_reason`. `404` for an unknown project or a set outside it,
`422` for malformed identities or paging, `403` for an account with no role. Money is exact
decimal text (`^-?[0-9]+(\.[0-9]+)?$`), never a JSON number. Thirteen schemas, built from the
price-list slice's `PriceListId` and `PriceListPositionId`; no new error code, no new detail key.

### Backend

`api/routers/specification_prices.py` (the twenty-first router module; passes the verified
subject's identity so the read re-reads the role set in its own transaction), `SpecificationPricesPort`
(optional in `build_router`), `api/security.py` (`getSpecificationPrices: _ANY_ROLE`),
`api/schemas/models.py`, `optimisation/public.py` (the exports the composition root needs) and
`bootstrap/adapters.py`: `SpecificationPricesAdapter` maps the read model into the frozen shape
and implements the `SavedTextReader` port over the comparison's `_AnalysisReader` — the run's one
`source_preparation` artifact, read from the store with the SHA-256 and size its stage row
recorded and checked as canonical `prepared.text_layer` for exactly this version and page count.
A missing or differing blob is `storage_integrity_error`, never an empty page.

### Web

- `entities/specification-price`: `useSpecificationPrices` (one page; the previous page stays
  while the next loads), the Russian labels of every closed vocabulary (a value outside the set is
  said to be so, never guessed) and exact money formatting — the server's decimal text grouped for
  reading, never parsed into a number, an absent amount a dash and never `0`.
- `widgets/specification-prices`: `SpecificationPricesSection` (the project's АР sets from the
  `listDocuments` read the structure already makes, a chooser, «Обновить»), `SpecificationPricesAnswer`
  (every state as one sentence saying what is missing and where it is done; the rows with their
  match, basis and reason; price and amount **only on a counted row**; the totals panel per
  currency with the excluded rows counted by reason; skipped lines; a pager) and its own CSS
  module on the global tokens.
- Mounted in `widgets/project-optimisation` between «Прайс-листы проекта» and «Вендор-листы по
  разделам». Query keys under the price-list slice's `optimisation` root
  (`optimisation.specificationPrices`, `optimisation.specificationPricesAll`); a price-list upload
  invalidates the prefix, because the new revision decides every price.
- Guards moved with it: `rendered-language.guard` renders the section in every documents state
  and the answer in every state, the contrast census renders a ready and a stopped answer
  (a status badge of each tone, a group label, the totals panel), `commands.test.ts` expects the
  second invalidation, `PC01_UI_SEAM.md` §6 records the keys.

### Reseal files

`contracts/api/v1/openapi.json` (the contract text, inserted in its own style; `info.description`
gains a reseal paragraph), byte-identical `web/openapi/openapi.json`, regenerated
`web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json`, `tests/support/expected_facts.json`,
the registers in `tests/contract/domain_p02/test_openapi_document.py`,
`tests/contract/api_v1/{test_openapi_conformance,test_surface_counts_in_prose}.py`,
`tests/integration/api/{test_authorization,test_role_register,test_served_document_and_health_plane}.py`,
`tests/integration/composition/{test_every_port_implementation_is_whole,test_an_absent_parent_is_not_an_empty_page}.py`,
and the surface prose in `P02_SEAMS.md`, `ALPHA_ROADMAP.md`, `infra/deploy/{README.md,proxy/nginx.conf,serve.py}`,
`api/{README.md,app.py,health.py}`, `api/routers/{__init__,declarations,errors}.py`, the BFF
`route.ts` and `shared/api/authorization.ts`. `CONTRACT_PIN_REGISTRY.md` needed no change (no
needle moved). `docs/program/CURRENT_STATE.md` is the integrator's and still states 64/73/198.

### Checks (phase B)

Interpreter `PY=/root/projects/PDF-Analysis/.local/worktrees/w55b-main-candidate/.venv/bin/python`,
`$PY -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider`, the lane's containers
(`make up` / `make migrate` to `0026_price_lists`; they died with the 07:00 reboot and were
raised again), host before the runs 8 GB free on `/`. Merge tip checked: `40cd159f`.

| Command (paths) | Result |
|---|---|
| `npm --prefix web ci` (once) | exit 0 |
| `npm --prefix web run api:generate` / `api:verify` | 74 operations, contract SHA-256 `d8da2b79…bf081`, `--check: OK` |
| `npm --prefix web run lint -- --quiet` | exit 0 |
| `npm --prefix web run typecheck` | exit 0 |
| `vitest run tests/guards tests/contract tests/unit/{api,styles,specification-prices,optimisation,screens,shell,qa_w50,ui}` | 69 files, 1203 passed (rendered-language guard, contrast census, frontend lock, drift, screen registry among them) |
| `pytest tests/contract` (whole directory) | see below |
| `pytest tests/e2e/test_pc01_journey_conformance.py` | 87 passed |
| lane containers: `tests/unit/optimisation` + `tests/integration/optimisation` | 187 + 52 passed |
| lane containers: `tests/integration/composition/test_specification_prices_over_http.py` | 6 passed (every state appears as its input does, over the composed ASGI app, recorded run, saved text read from MinIO) |
| lane containers: `tests/integration/api` (whole) and the composition registers (`test_every_port_implementation_is_whole`, `test_an_absent_parent_is_not_an_empty_page`, `test_composition_root`, `test_router_answers`, `test_optimisation_over_http`) | all passed except the known reds below |

`tests/contract` after the merge: the failures are exactly the sandboxed CP-00 families
(`test_cp00_candidate`, `test_cp00_final_state`, `test_validate_bootstrap`: git-sandbox records
and `jsonschema` absent from the runtime interpreter), the two known reds
`test_error_kernel::test_there_are_twenty_four` and
`test_ar_v2_seeded::test_seeded_categories_equal_the_sealed_api_enum`,
`test_alpha_acceptance_command` (it refuses a tree with uncommitted changes) and
`test_doc_prose_facts::test_the_scanned_docs_state_the_contract_surface_this_tree_has`, whose
only finding is `docs/program/CURRENT_STATE.md` still stating 64/73/198 (the integrator's file).

Reds present before this change and not caused by it:
`tests/integration/api/test_query_surface.py::test_the_filter_vocabularies_are_the_frozen_ones`
(`12 == 2`, `FindingCategory`), `...::test_every_declared_query_parameter_is_read_by_the_router_that_declares_it`
(names `compareDocumentVersions` and `listPriceListPositions`, undriven by their own lanes; this
slice drives `getSpecificationPrices` in its own test in that file and is no longer in the list)
and `test_every_port_implementation_is_whole::test_pre_decide_adapter_refuses_a_severity_instead_of_dropping_it`
(`DecisionAdapter`).

Mutation probes (applied, run, restored; digests compared):

| Mutation | Result |
|---|---|
| a price/amount shown for any row with a matched position, counted or not | `tests/unit/specification-prices` 2 failed |
| an absent amount rendered as `0` | 1 failed |
| the totals panel listing one currency only | 1 failed |
| `build_router` without the `specification_prices` parameter (the merge slip this run caught) | `test_composition_root`, `test_router_answers`, the over-HTTP suites errored |
| the query parameters ignored by the handler | `test_specification_prices_reads_the_query_parameters_it_declares` fails by name |
| phase A's probes (unit filter, amount guard, currencies, ambiguity, quantity, standard references, section, run state, price-list revision, missing pages) | each red; see Checks (phase A) |

Deferred under `R-135`: the full gate, the live journey (`e2e:pc01`) and the manual acceptance
of the new section on the stand.

### Risks and integrator instructions

- Merge `agent/w60-opt-match-01` after `40cd159f`. If another reseal lands first, keep both
  sides' paths and schemas in `contracts/api/v1/openapi.json` and re-derive everything else
  (mirror copy, `api:generate`, `api:verify`, `FRONTEND_LOCK.json`, `expected_facts.json`, every
  surface count in prose — the count guard names each file).
- `docs/program/CURRENT_STATE.md` is the integrator's and must move to 65/74/211.
- Two lanes branch from phase A (`specification.py`, `matching.py`): their public names are
  stable; additions only.
- The section reads the project's first page of documents (50) for its АР sets and says so when
  there is a further page.
- The extraction limits (no column geometry in the saved text) are listed under Known
  limitations; the real АР set `13АВ-РД-АР-ТП1-ТП2` gives one table and two rows.

### Known limitations

- Column geometry is not in the saved text: the type/mark, code and manufacturer cells are
  part of the description; tables whose rows wrap above their anchored line (vertically
  centred cells) attach the wrapped lines to the wrong row or report them; a table continued
  on the next sheet without a repeated header is not read.
- `п.м` and `м` are different units for pricing; a price list in metres does not price a
  specification in running metres (reported `unit_mismatch`).
- The name tier is exact equality after normalisation; a description with extra words (a
  wrapped characteristic, a note) does not match a shorter price-list name.
- Phase B owns the composition-root adapter of `SavedTextReader` (over the runs context and
  the object store, as the comparison's `_AnalysisReader`), the operation and the view.
