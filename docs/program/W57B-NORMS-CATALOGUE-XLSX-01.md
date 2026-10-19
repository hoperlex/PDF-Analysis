# W57B-NORMS-CATALOGUE-XLSX-01 — norms catalogue and the run's Excel export

**Task:** `tasks/W57B-NORMS-CATALOGUE-XLSX-01.md`. **Branch:** `agent/w57b-catalogue-xlsx-01`.
**Base:** `849dddd4` (`integration/night-1020`). **Rulings:** `R-135`, `R-139`.

## Phase A — services (no contract, API or web change)

### 1. Catalogue (`src/auditmanager/norms/catalogue/**`)

`list_documents(session, *, q, kind, cursor, limit)` (public as
`auditmanager.norms.public.list_norm_catalogue`) lists every document of the **current**
snapshot. With none current it answers `required_norm_unavailable` with
`reference_kind: norms_snapshot`, as `searchNorms` does.

- **One read.** A single `SELECT` takes the snapshot's documents: identity, slug, `doc_type`,
  page and paragraph counts, attribution, and `content_available`. That last one uses the same
  custody-binding expression `getNormDocument` uses. Everything after the read is pure work:
  display name, filters, order and page.
- **Row fields:** `norm_document_id`, `designation` (derived), `title` (derived, `None` when
  the file name carries nothing after the designation), `kind` (`doc_type` verbatim),
  `page_count`, `paragraph_count`, `content_available`, `source_attribution`. The page also
  carries `norms_snapshot_id`, `total` (documents the filters keep) and `kinds` (each kind of
  the snapshot with its count, most documents first). The corpus has no status column, so
  there is no status filter.
- **Filters.** `q` (1–200 characters) is folded the way search folds designations: case,
  `ё`, Latin homoglyphs, and every run of punctuation as one space. It must start a word of
  the derived designation or title. When `q` ends in a digit, it must also end a number
  there: `СП 54` finds `СП 54.13330.2022` and not `СП 542.1325800.2024`, matching
  `searchNorms`. `kind` (1–100 characters) must equal `doc_type` exactly. An unknown kind
  returns an empty page. A control character, or a `q` with nothing to filter by, is refused
  with `validation_failed` (`field: q|kind`, `constraint: format`) before any read.
- **Order and paging.** Rows sort by designation (natural, folded), then title, then
  identity. That order is total. The opaque cursor uses the search token style: base64url
  JSON `["c1", binding, ndoc]`, with the binding being 128 bits of SHA-256 over
  `(q, kind, snapshot)`. A token from another filter or snapshot is refused with
  `validation_failed` (`cursor`, `format`).
- **Display derivation** (`designation.py`). It is deterministic, pure, and never writes a
  row. It applies four rules: split at the first `__` outside parentheses, or before an
  act's subject (`Об`/`О` after `N <number>`); inside parentheses, `__` becomes `. `;
  `от_DD_MM_YYYY` becomes `от DD.MM.YYYY` for a real day and month; after a document-type
  word, the underscores between numeric tokens become dots (`СП_54_13330_2022` →
  `СП 54.13330.2022`). An edition note cut short at the end is closed when its date is
  complete (`(ред. от 25.12.2023)`). Otherwise it becomes `(ред. …)` or `(с изм. …)`. Any
  other unclosed parenthesis is **not derivable**, and the whole designation falls back to
  the stored projection `designation_of(slug)` verbatim.

**Measured read-only on the real corpus.** Stand: `127.0.0.1:57490`, database
`auditmanager_w54_local_import`, snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74`. The sessions used
`default_transaction_read_only=on`. Commands: a `psql` export of the 674 rows to the
scratchpad, then the scratch probe `probe_catalogue.py`, which calls `list_norm_catalogue`
through a read-only SQLAlchemy session.

| Figure | Value |
| --- | --- |
| documents in the current snapshot | 674 (`total`), 23 kinds (`ГОСТ` 492, `СП` 101, `Приказ` 20, `Постановление` 18, …) |
| designations that change vs. today's `designation_of` | **257 of 674** (38 %); 417 unchanged |
| — designation numbers dotted (`ГОСТ 12.1.003-2014`, `СП 54.13330.2022`, `МДС 12-24.2006`) | 210 |
| — dates dotted (`от 24.04.2013`) | 47 |
| — cut edition note closed (`(ред. от 27.06.2023)`) | 12 |
| — cut edition note shown as `(ред. …)` / `(с изм. …)` | 14 |
| — act subject moved from designation to title | 17 |
| stored designations with an unbalanced parenthesis | 26 → **0** after derivation |
| distinct display designations | 674 of 674 |
| documents with no title beyond the designation | 62 |
| not derivable, kept verbatim | e.g. `Градостроительный кодекс Российской Федерации от 29 12 200` (date cut short) |
| latency (single request, idle lane) | first page 28 ms; any filter 19–22 ms; full walk at `limit=100` 7 pages / 674 unique ids / 217 ms |
| `content_available` | 50 / 50 on the first page |
| the task's example row | `Приказ_МЧС_России_от_24_04_2013_N_288_(ред__от_27_06_2023)` → `Приказ МЧС России от 24.04.2013 N 288 (ред. от 27.06.2023)`; slug re-read after the probe, unchanged |

Filter samples: `24.04.2013` → 1 (the order above); `СП 54` → 1 (`СП 54.13330.2022`);
`123-ФЗ` → 1; `ГОСТ 21.501` → 1; `Приказ МЧС` → 12; `kind=СП` → 101, starting
`СП 1.13130.2020`, `СП 3.13130.2009`, `СП 7.13130.2013`.

### 2. The run's Excel export (`src/auditmanager/exports/**`)

`export_run_xlsx(session, run_id, *, authorization, read_blob, read_citations)` (public in
`auditmanager.exports`) returns an `XlsxExport`: bytes, content type, replacement count, and
the page-label and citation source references. It composes the certified chain (preflight,
certified sources, package, projection, writer) and adds only two things: the refusals and
the choice of citation source.

- **Refusals, made as `exportRunCsv` makes them and before any other read.** An unknown run
  is `not_found` (`AuditRun`). A run whose terminal does not publish a result is
  `state_transition_not_allowed`, through the CSV's own `assert_exportable`. The DB+S3 test
  compares both answers with `export_run_csv` on the same run.
- **«Лист/стр.»** comes only from the version's verified portal companion. A version without
  a companion, or with one that does not verify, is refused with `storage_integrity_error`
  (`role: source.structured_companion`), which is the catalogue's case "a required manifest
  role is missing". A page number is never shown as if it were a sheet label. If the Blob
  reader's own `DomainError` (for example `dependency_unavailable`) is behind the refusal,
  that error is answered as it is.
- **Norm columns.** A run that pinned a retrieval set, or that has any certified partition
  (`norm_citation_count`) or citation row, goes through
  `prepare_certified_xlsx_package` with the injected verified citation reader. Any refusal
  there, or a missing reader, is `required_norm_unavailable` with
  `reference_kind: norm_retrieval_set`. The export is never produced with the citations
  dropped. A run with none of the three cannot hold citations (`0023`). Each of its findings
  gets an explicit empty tuple, and the source reference is `<run>:no-citation-partitions`.
- **No file name.** `XlsxExport` names no file, for the same reason `CsvExport` does not:
  `test_the_download_name_has_one_source.py` allows exactly one place, the router, to spell
  an attachment name. Phase B builds `"{run_id}.xlsx"` there. This deliberately departs from
  the dispatch's "bytes + filename".
- **Two defects fixed in the certified chain.** Serving real runs depends on both.
  1. `source_labels.py` refused every version over **30 pages**. That was the bound before
     `0021`; since `0021` the `ck_document_version_page_count` check allows 1..500. The
     bound is now 500, covered by a 31-page test and a 501 refusal.
  2. `xlsx/query.py` refused every **v1 finding**, because only v2 publication writes
     `canonical_observation_id`. That covers every run on the stand, which runs v1. A
     finding with no canonical identity and exactly one observation now uses that
     observation, which is the row the CSV exports. Two observations are still refused. A
     null v1 recommendation renders as an empty cell.
- **«Атрибуция»** (Сводка) shows how the model answers were obtained, in the UI's words:
  `ответы модели воспроизведены из записи (recorded)` or
  `ответы модели получены живым вызовом (live)`.

### Phase A checks (lane containers `auditmanager-w57b-catalogue-xlsx`, PG 57510, S3 61110)

Command: `.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <paths>`,
where `.venv` links to the `w55b-main-candidate` interpreter.

| Paths | Result |
| --- | --- |
| `tests/unit/norms tests/integration/norms/catalogue` | 71 passed |
| `tests/unit/exports tests/integration/exports/test_xlsx_run_export.py` | 32 passed. The DB+S3 cases drive a real recorded v1 run and a merged, v2-shaped finding over it: a canonical row followed by «также найдено» rows. |
| `tests/integration/exports tests/unit/norms tests/unit/exports tests/integration/norms/catalogue tests/integration/norms/search tests/contract/architecture` (first commit) | 410 passed, 1 skipped, 1 failed: `test_v2_csv_severity.py::test_csv_uses_canonical_proposal_and_current_expert_decision`. It fails the same way on the untouched base `849dddd4` (checked with `git archive` into the scratchpad), because it `UPDATE`s a `finding_observation` row and the 0002 immutability trigger has always refused that. |
| `tests/integration/exports/test_v2_csv_severity.py` after the fix (integrator approval) | 2 passed. The canonical and member observations are now **new rows** copied from the published one, which is what the trigger's hint says to do. The test now also proves that the published observation, once it is no longer canonical, leaves the CSV. |
| mutation: turn off the v1 canonical rule | the DB+S3 case fails with `xlsx_read_canonical_missing`, so the case exercises the rule |

## Phase B

Pending the integrator's contract slot.
