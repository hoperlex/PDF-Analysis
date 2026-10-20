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

## Phase B — served operations and screens

The contract slot was handed over at `1af17a48`, and the branch then merged `0f0903f2`
(W59-ANALYSIS-SETTINGS-01), `a820849a` (W59-VERSION-UPLOAD-01) and `c22f2049`
(W59-DECISION-CARRYOVER-01). Each merge took the base's
contract, facts, client and lock as they were and **re-derived** this lane's additions on top
(a scratch script that re-applies the two paths, two operations, three schemas and the reseal
paragraph, then `api:generate`), rather than hand-merging generated files. **Surface at the
final merge: 54/61/158 → 56 paths / 63 operations / 161 schemas.** The error catalogue still
has 25 codes, the migration head is still `0024_version_classification`, and
`contract_version` is unchanged. `docs/program/CURRENT_STATE.md` is the integrator's and
still states the base's triple. It is the one remaining red in `tests/contract` that this lane
caused (`test_doc_prose_facts`).

### Contract (`contracts/api/v1/openapi.json`, byte copy in `web/openapi/openapi.json`)

- **`listNormDocuments`**: `GET /norm-documents`, tag `norms`, any one role
  (`role:admin|expert`). Query parameters: `q` (1..200), `kind` (1..100), `cursor`, `limit`
  (1..200, default 50). 200 returns `NormCatalogueEntryPage`; refusals are 401/403/422/500/503.
- **`exportRunXlsx`**: `GET /runs/{run_id}/export.xlsx`, tag `export`, `expert` (as
  `exportRunCsv`). 200 returns `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
  with `Content-Disposition: attachment; filename="{run_id}.xlsx"`. Refusals: 401/403/404,
  409 (`RunNotExportable`), 422 (`StorageIntegrityError`; the description also names
  `required_norm_unavailable` / `norm_retrieval_set`), 500/503.
- **Schemas:**
  - `NormCatalogueEntry`: `norm_document_id`, `designation` (≤520), `title` (string or null),
    `kind`, `page_count`, `paragraph_count`, `content_available`, `source_attribution`.
  - `NormKindCount`.
  - `NormCatalogueEntryPage`: `norms_snapshot_id`, `items`, `page`, `total`, `kinds`.
  - No error code is added.
- **Re-derived:** `api:generate` and `api:verify` (63 operations, contract SHA-256
  `40efbb75d08420a3c5da7f96a43e9d958c066fa417968f1014db114b11b4beb6`);
  `web/FRONTEND_LOCK.json` (both digests, four generated-file digests, 56/63/161,
  `content_commit` `c22f2049`); `tests/support/expected_facts.json` (56, two triples, three
  names).
- **Subset counts re-measured from the merged contract:** 45 of 63 operations declare their
  own 422 and 18 declare none; 60 of 63 need a credential; 39 operations reference `NotFound`
  (+1, `exportRunXlsx`).

### Backend

- `api/routers/norms.py`: the catalogue route. `api/routers/export.py`: the workbook route.
  The download name is still spelled only in `_disposition(run_id, *, suffix="csv")`, and the
  guard test now asserts both suffixes.
- `api/routers/ports.py`: adds `NormsSearchPort.list_catalogue` and a new `XlsxExportPort`.
  `api/routers/__init__.py`: `build_router(..., xlsx_exports=None)`. `api/security.py`:
  `listNormDocuments: _ANY_ROLE` and `exportRunXlsx: _EXPERT`.
- `bootstrap/adapters.py`:
  - `NormsSearchAdapter.list_catalogue` maps the service's page.
  - `XlsxExportAdapter` runs one read transaction. It has a Blob reader on the shared store
    (storage failures are typed by `domain_error_from_storage`, and a missing object becomes
    `storage_integrity_error` with role `source.structured_companion`). It takes W57a's
    `read_verified_citations` as the injected reader, since the composition root may import
    it and the export context may not. Its `ExportAuthorization` states the seam's role
    decision and carries the principal's `user_uid`.
- `bootstrap/composition.py` wires `xlsx_exports=XlsxExportAdapter(sessions, blob_store=store)`.
- **Prose and pins re-measured:** P02 §7 (sentence, history and table), `ALPHA_ROADMAP.md`,
  `infra/deploy/{README.md, proxy/nginx.conf, serve.py}`, `api/{README.md, app.py, health.py}`,
  `api/routers/{__init__, declarations, errors}.py`, the BFF route and `authorization.ts`. The
  two mutation lines in `test_surface_counts_in_prose.py` now read «the fifty-five paths» and
  «Sixty-two operations». The operation lists in `test_openapi_document.py`,
  `test_authorization.py`, `test_role_register.py` and
  `test_served_document_and_health_plane.py`, the NotFound count in
  `test_openapi_conformance.py`, and the composition registers (`EXPECTED_ADDRESSED` 20→21,
  `EXPECTED_UNADDRESSED` 15→16, `PORT_FOR_ARGUMENT` `xlsx_exports`) gained the two operations.
- `test_query_surface.py` now drives `listNormDocuments`'s `q`/`kind`/`cursor`/`limit` over
  a second seeded document. The test as a whole stays red for two pre-existing reasons that
  belong to other lanes: `compareDocumentVersions` is not driven, and the category case
  fails. With those excluded locally, the catalogue's parameters pass.

### Web

- **«Каталог» on `/norms`.** The view is addressed by `?view=catalogue&cq=&kind=`, and the
  route passes `catalogue={q, kind}`. The page offers «Поиск» / «Каталог» as two links with
  `aria-current`. The catalogue section has a `GET` filter form whose kind options come from
  the answer's `kinds`. The table has «Обозначение» (a link to `/norms/document?id=…`),
  «Название», «Вид», «Страниц», «Абзацев» and «PDF», plus the attribution line and a pager.
  Before a snapshot is current the section shows the search's refusal and sends no read.
  A refused filter shows «Отбор не принят»; a failed read shows «Каталог не прочитан» with
  its correlation id. Code: `widgets/norm-catalogue/**`, `entities/norms` (`useNormCatalogue`,
  `normCatalogueQueryOptions`) and `queryKeys.norms.catalogue`.
- **«Скачать Excel»** sits in the export panel beside the CSV button, under the same
  exportability rule. The panel owns its download (`useExportRunXlsx` in
  `features/export-run`), built on component state rather than a query-cache mutation: a
  download invalidates nothing, and the panel renders in static guards that have no query
  client. File name: `shared/api/xlsx.ts` `xlsxFileName` gives `<run_id>-findings.xlsx`; the
  server's header is still the authority. The two source refusals are shown in Russian
  («Excel не выгружен»).
- `rendered-language.guard.test.ts` gains `Excel` in `NOT_DERIVABLE` (a product name, from
  the plan's «Скачать Excel»), catalogue cache states and the table's empty pages. The
  contrast census (`tests/unit/styles/screens.ts`) renders the catalogue table. Route,
  catalogue and Excel unit tests were added.

### Phase B checks (lane containers; `.env` exported where a suite needs it)

| Check | Result |
| --- | --- |
| `tests/contract` (whole directory, container-free) at the final merge `bf5c1b9b` | 85 failed, 126 errors, 1,059 passed. Compared by test ID with the base clone's run at `1af17a48`, the **only** new red is `test_doc_prose_facts`, which fails on `CURRENT_STATE.md` alone (the base's triple). Everything else is pre-existing or environmental: the `test_cp00_candidate` errors come from `NotADirectoryError: .../w57b-catalogue-xlsx/.git` because a worktree's `.git` is a file; the remainder (`test_error_kernel`, `test_ar_v2_seeded`, `test_alpha_acceptance_command`, `test_cp00_final_state`, `test_validate_bootstrap`) also fails on the base. |
| `npm --prefix web run api:verify` | OK, 63 operations, SHA-256 `40efbb75…4beb6` |
| `npm --prefix web run typecheck`, `lint --quiet` | clean |
| vitest: `tests/guards tests/contract tests/unit/{norms,export,screens,styles,review,widgets,api}` | 74 files, 1,168 tests passed |
| `tests/e2e/test_pc01_journey_conformance.py` + API surface (`test_operation_surface`, `served_document_and_health_plane`, `role_register`, `authorization`, `router_and_body_rules`) + download-name guard + `tests/unit/{norms,exports}`, final merge | 265 passed |
| Previous merge (`9b8bcb6d`): the API surface files above plus `schema_conformance`, `listing_surface`, `no_internal_identifiers`, composition root, absent-parent and port-whole registers, `tests/integration/exports`, `tests/integration/norms/catalogue` | 509 passed, 1 skipped, 1 failed. The failure is pre-existing on base `0f0903f2`: `test_pre_decide_adapter_refuses_a_severity_instead_of_dropping_it` (`TypeError`). |
| Not run (R-135) | full gate, live journey, whole frontend suite, any provider call, LibreOffice |

## Risks and known limitations

- **Excel needs a portal companion.** A legacy bare-PDF version is refused with `422
  storage_integrity_error`. Uploads have required portal bundles since W55b, so this affects
  older versions only. Every v1 run on such a version exports CSV but not Excel.
- **Raw values in the workbook.** The certified writer emits contract values (`critical`,
  `fire_safety`, `pending`) and English summary keys for severities. Localised labels in the
  workbook would be a writer change, not attempted here.
- **The citation path is untested end to end.** It is wired (`read_verified_citations`
  injected; the run's own `analysis_profile_id` is passed as the profile identity) but has no
  real v3 run behind it. Its refusal mapping is unit-tested; a CITE-active run is the first
  real exercise.
- **`kind` is the stored `doc_type` verbatim.** Some values are truncated first words of
  the file name, such as `Федеральный` and `Здания`. No display mapping is applied.
- **Display derivation only on the catalogue.** `getNormDocument` and `searchNorms` still
  show the stored projection, so a row opened from the catalogue shows the old designation
  on the document page. Switching them would change two served payloads, which this task
  did not open.
- **Catalogue scale.** The catalogue reads the snapshot's documents in one statement per
  request (674 rows, about 20 ms). That is fine at corpus scale but grows linearly with it.
- `test_query_surface.py::test_every_declared_query_parameter_is_read_by_the_router_that_declares_it`
  stays red for other lanes' reasons (`compareDocumentVersions` is not driven, and the
  category case fails). The catalogue's own parameters were proven with those excluded
  locally.

## Integrator instructions

1. Merge `agent/w57b-catalogue-xlsx-01` (phase A and phase B together, one slice). It
   already contains `c22f2049`. If `integration/night-1020` has moved again, merge it and
   re-derive the generated files as this lane did: take the base's contract, facts, lock
   and generated client, re-apply the two paths, two operations, three schemas and the
   reseal paragraph, run `api:generate`, then update the lock and facts.
2. Update `docs/program/CURRENT_STATE.md` to **56 paths / 63 operations / 161 schemas**.
   The error catalogue
   (25 codes) and head (`0024_version_classification`) are unchanged. This turns
   `test_doc_prose_facts` green.
3. No migration, no new error code, no dependency change. Rollback is reverting the merge.

## Hotspot proof

Not touched: `db/migrations/**`, the dependency and lock files (`pyproject.toml`,
`uv.lock`, `web/package*.json`), `web/src/_app/providers.tsx`, `web/src/app/globals.css`,
`docs/program/CURRENT_STATE.md`, the snapshot rows and the bundle (the stand was only read,
over `default_transaction_read_only=on` sessions; one slug was re-read after the probe and
is unchanged), refs, tags and the stand. `contracts/**`, `bootstrap/composition.py` and the
API surface were edited only after the integrator's go message from `1af17a48`, which handed
over the contract slot.
