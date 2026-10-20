# NORMS-DISPLAY-DESIGNATION-01 — norm search and the norm document show the derived designation

**Task:** `tasks/NORMS-DISPLAY-DESIGNATION-01.md`. **Branch:** `agent/norms-display-01`.
**Base:** `59f976fc` (`origin/dev` plus the frozen task files). **Rulings:** `R-135`, `R-139`.

## What changed

`searchNorms`, `getNormDocument` and the paragraphs read now show the readable designation the
catalogue shows: `СП 54.13330.2022` instead of `СП 54 13330 2022`,
`Приказ МЧС России от 24.04.2013 N 288 (ред. от 27.06.2023)` instead of
`Приказ МЧС России от 24 04 2013 N 288 (ред`. No contract, schema, migration, ranking,
snapshot row or persisted citation is touched.

- **One derivation, moved, not copied.** `norms/catalogue/designation.py` was `git mv`-ed to
  `norms/search/display.py`. The catalogue already imports from `norms.search`, so the
  derivation had to sit on the search side for the search to use it without a cycle. Its
  four rules and its all-or-nothing fallback are unchanged (the 31 existing rule cases in
  `tests/unit/norms/catalogue/test_display_name.py` pass untouched, importing from
  `auditmanager.norms.catalogue`, which re-exports `DisplayName` and `display_name`;
  `norms.public` is unchanged).
- **`reader_designation(slug)`** (new, in `search/display.py`) is what the search and the
  document show: `display_name(slug).designation`, except that a derivation longer than
  `DESIGNATION_MAX_CHARACTERS = 500` is replaced by the stored projection
  `designation_of(slug)`. 500 is the `maxLength` of `NormSearchHit.designation` and
  `NormDocument.designation`. The stored projection is a prefix of a slug the column bounds
  at 500 (`ck_norm_document_slug`), so the fallback always validates.
- `search/service.py`: `_hit` (searchNorms) and `get_document` (getNormDocument, and through
  it `list_paragraphs`) call `reader_designation` instead of `designation_of`. Nothing else
  in the file moved: the SQL, the order, the window, the cursors, the fragments and the
  titles are byte-identical.
- `designation_of` stays as it was; it remains the stored projection and the fallback.

## Behaviour per case

| Case | Result |
| --- | --- |
| a slug the rules derive | the derived designation, in search, document, paragraphs and catalogue alike |
| a slug no rule can derive (date cut short, unbalanced parenthesis that is not an edition note) | `designation_of(slug)` verbatim, as before |
| a derivation of exactly 500 characters | shown |
| a derivation of 501 or more | the stored projection (never silent: one rule, one place, tested at 500/501) |
| the catalogue, same long slug | its schema allows 520, so it keeps the derivation; the only place the two differ, and only for derivations of 501..505 characters |
| `NormCitation.designation` | not read or written: a different value on a different path |
| hit `title`, `doc_type`, `fragment`, `page_label` | unchanged (a hit's `title` is still the stored one) |

Idempotence and security: the function is pure (same slug, same text), reads no row beyond
the slug the statement already selected and writes nothing; the rows are never altered
(`test_no_row_is_altered_by_reading`).

## Measured: how many of the 674 designations change

Read-only listing of the 674 directories under `.local/norms/corpus` (their names are the
slugs; the count reproduces the W57B figure), projected through the changed code, with
nothing written there. The local real-corpus stand is gone after the reboot, so this is a
projection of the slugs, not a database read.

| Figure | Value |
| --- | --- |
| slugs | 674, all distinct |
| designations that change in `searchNorms` / `getNormDocument` vs. the base | **257 of 674** |
| designations that change in the catalogue vs. the base | **257 of 674** |
| search/document equal to catalogue | 674 of 674 |
| derivations over 500 characters | 0 (longest designation: 106 characters, longest slug: 106) |
| distinct display designations | 674 of 674 |
| cost | 7.3 ms for all 674 (about 11 µs per document); a page of 50 hits adds about 0.5 ms |

The 257 are the W57B slice: 210 dotted designation numbers, 47 dotted dates, 12 closed and 14
ellipsized edition notes, 17 act subjects moved out of the designation (these add up to more
than 257 because one name can change in more than one way). Unchanged for the reader: 417.

## Checks run

Host state before the stack run: 4014 MiB available, 7.8 GB free on `/` (the run builds no
image; the lane holds two small volumes). Lane: `auditmanager-norms-display`, PostgreSQL
`57650`, S3 `61250/61251`.

| Command (cwd = the worktree; `PY=.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider`) | Result |
| --- | --- |
| base: `tests/unit/norms` + `tests/integration/norms/search/{test_norms_surface_offline,test_query_parsing,test_w55a_fix_offline}.py` | 168 passed |
| changed tree, same paths (container-free) | 203 passed |
| changed tree, `tests/unit/norms tests/integration/norms/search tests/integration/norms/catalogue` on the lane stack | **284 passed** in 9.8 s (exit 0) |
| `tests/contract/architecture tests/contract/api_v1/{test_w55a_norms_seal,test_doc_prose_facts,test_surface_counts_in_prose}.py tests/contract/program` | 169 passed |
| `git diff --check` | clean |
| the golden on an untouched copy of the base (`git archive 59f976fc`, no change) | 12 golden/paging/agreement tests pass, twice; the 2 designation tests fail there, as they must |

Not run, by `R-135`/`R-70`: the full gate, the whole contract battery, the frontend suite
(no web file changed; the web only renders `designation`), the live journey. `ruff` and
`mypy` are not installed in the lane interpreter; nothing here was linted beyond
`python -W error` import, a 100-column check and `git diff --check`.

## Tests added or changed

- `tests/unit/norms/test_reader_designation.py` (container-free): eight real slugs with the
  text before and after written out; five underivable slugs equal the stored projection;
  search = catalogue = `public` for all of them; **one implementation** (the symbols are the
  same objects, exactly one `def display_name(` under `src/auditmanager/norms`, no
  `catalogue/designation.py`); the bound equals the `maxLength` of both sealed schemas, read
  from `contracts/api/v1/openapi.json`; derivations of 500 (kept) and 501 (stored) characters;
  a 500-character slug still fits.
- `tests/integration/norms/search/test_norms_surface_offline.py` (container-free, the shipped
  router and adapter over the fake database): the two assertions that froze the old text now
  read `СП 54.13330.2022`; four new cases: hit and document agree for a cut edition note; an
  underivable slug is shown as stored; a 501-character derivation falls back and the answer
  still validates (the shipped models enforce 500; without the fallback the route answers
  500); the service keeps the database's hit
  order (it never sorts by the display text).
- `tests/integration/norms/search/test_display_designation_window.py` (PostgreSQL): six
  documents, seven paragraphs, eight fixed queries (ranked words, designation, clause, and
  their combinations). **Golden:** the hit labels in order and, by construction, their ids,
  for every query, and again paged one and two hits at a time. It was confirmed on an
  untouched copy of the base (it passes there, twice) and passes on the changed tree. Also:
  the search, the document, the paragraphs read and the catalogue agree document by document;
  the 500-character slug is served with its stored text; no `norm_document` or
  `norm_paragraph` row changes.
- `tests/integration/norms/search/test_search_window.py`: one old assertion updated.

## Every new guard fails under a quoted mutation

Each mutation is a single textual replacement, applied to the committed tree, the named tests
run, the file restored (`git status` clean afterwards). `designation_of`-mutations use
`__import__("auditmanager.norms.search.query", fromlist=["x"]).designation_of(str(row.slug))`
so they produce the old text rather than a `NameError`.

| Mutation | Failing tests |
| --- | --- |
| `service.py` `get_document`: `reader_designation(str(row.slug))` → the old `designation_of(...)` | offline: `test_a_document_says_whether_its_pdf_is_served`, `test_a_hit_and_its_document_show_the_same_readable_designation`; PG: `test_the_document_and_its_paragraphs_show_the_same_designation` |
| `service.py` `_hit`: same replacement | offline: `test_a_page_carries_hits_...`, `test_a_hit_and_its_document_...`, `test_hits_keep_the_order_the_database_gave_them`; PG: `test_search_shows_the_readable_designation_and_one_per_document` |
| `display.py`: `if len(derived) > DESIGNATION_MAX_CHARACTERS: return designation_of(slug)` removed (fallback) | unit: `test_a_derivation_over_the_bound_is_the_stored_projection`, `test_the_stored_projection_always_fits_a_slug_the_column_allows`; offline: the over-bound case (the route answers 500 instead of 200: the shipped model refuses the 501-character text); PG: 5 tests, among them `test_the_long_document_still_validates_on_the_wire` and the golden for `карнизы` |
| `display.py`: `>` → `>=` | unit: `test_a_derivation_of_exactly_the_bound_is_shown` |
| `display.py`: `DESIGNATION_MAX_CHARACTERS = 520` | unit: `test_the_bound_is_the_sealed_schemas_bound`, both boundary tests; offline: the over-bound case |
| `catalogue/__init__.py` re-imports a restored copy `catalogue/designation.py` | unit: `test_there_is_one_derivation_not_a_copy` |
| `service.py` `search()`: items sorted by `hit.designation` (offline) | offline: `test_hits_keep_the_order_the_database_gave_them` |
| the same sort (PG) | golden `лестницы` and `п. 7.1 лестницы`, both paging variants, `test_the_search_service_and_the_adapter_agree_on_ids_and_order` |
| ordered SQL, outer `ORDER BY h.designation_key COLLATE "C"` → `... DESC` | golden and paging for `п. 7.1` |
| ranked SQL, outer `ORDER BY h.hit_rank DESC` → `ASC` | golden `СП 54 лестницы`, `лестницы`, `п. 7.1 лестницы`, paging, agreement |

(A tenth mutation, `page_limit: limit + 1` → `limit + 2`, passed because the service cuts
the page to `limit` afterwards; it is an equivalent mutant and is not counted.)

## Deferred checks

- The full gate and the live journey: under `R-135` they belong to the integration task
  after the last code block. The integrator's light acceptance for the merge is the
  `tests/integration/norms/search` and `tests/integration/norms/catalogue` directories on the
  lane's containers, which this report ran on the same tree.
- A database read of the real 674-document snapshot: the stand is gone; the figures above are
  a slug projection.

## Risks and known limitations

- **Behaviour change a reader can see.** 257 of 674 designations read differently in the
  search and on the document page, and the web renders them as given. The designation is
  display text only (the web uses it for a link label and two `aria-label`s); no stored
  value, identity or citation uses it. A reader who copied the old text into another search
  finds the same documents: the search tokenises `.`, `_`, ` ` and `-` alike
  (`norm_designation_tokens`).
- **The long-slug exception.** For a derivation of 501..505 characters the search and the
  document show the stored text while the catalogue shows the derivation (its schema allows
  520). It needs a slug of 496 or more characters with a cut edition note; the real corpus
  has none (longest slug 106). If equal text is wanted there, the search schemas' bound is
  the place to change, and that is a reseal, outside this task.
- **The catalogue's 520 is safe without a cap.** The rules never lengthen a head by more than
  five characters (an ellipsized edition note after a name with no space before the
  parenthesis: 500 becomes 505; measured), and the column bounds a slug at 500, so a
  catalogue designation is at most 505. This task adds no cap there.
- A hit's `title` is still the stored file name, while the catalogue's `title` is derived
  (and shorter). The task named the designation only.
- The derivation is applied per hit (about 11 µs). A page of 50 hits costs about half a
  millisecond; there is no cache.

## Instruction to the integrator

Merge `agent/norms-display-01` (a real merge) into `integration/night-1020`. There is no
contract, migration, reseal, lock or composition change. After the merge, on the integrator's
tree, the useful light check is the same directories: `tests/unit/norms`,
`tests/integration/norms/search`, `tests/integration/norms/catalogue` on a lane stack
(284 tests here). Revert the merge to roll back.

## Forbidden hotspots

Not touched: `contracts/**`, migrations, `src/auditmanager/api/**`, `src/auditmanager/bootstrap/**`,
other `src/**`, dependency files, `CURRENT_STATE.md`, refs and tags, snapshot rows,
`NormCitation.designation`. The changed paths are all inside the task's allowed set
(`src/auditmanager/norms/search/**`, `src/auditmanager/norms/catalogue/**`,
`tests/unit/norms/**`, `tests/integration/norms/search/**`, this report); `git diff --name-only
59f976fc` is the proof and is reproduced in the hand-back.
