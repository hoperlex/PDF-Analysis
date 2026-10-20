# W60-OPT-MATCH-01 — «Спецификация и цены»: the AR specification priced from the project's list

**Base:** `15f9715b` (`W60-PRICE-LIST-01` phase A `6d86b991` plus this task file), branch
`agent/w60-opt-match-01`, isolated worktree `w60-opt-match`, lane PostgreSQL 57580 / MinIO
61180–61181. **Status:** phase A (extractor, matcher, query) complete; phase B (one read
operation, the reseal, the «Спецификация и цены» view on «Оптимизация») waits for the contract
slot. Development candidate under `R-135`: no full gate, no live journey, no push, merge into
another branch or tag. No migration, no new dependency, no LLM, nothing persisted.

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
