# W60-PRICE-LIST-01 — «Оптимизация проекта»: project price lists and vendor lists

**Base:** `4327e61a` (`origin/dev` `0f0903f2` plus the frozen task file plus `W61-DISPATCHER-01`
phase A `3461747c`, migration head `0025_work_assignments`), branch `agent/w60-price-list-01`,
isolated worktree `w60-price-list`, lane PostgreSQL 57570 / MinIO 61170–61171. **Status:**
phases A and B complete (phase B merged `c22f2049`, then `beafeab5`, the integration tip on the
integrator's go). Development candidate under `R-135`: no full
gate, no live journey, no push, merge into another branch or tag.

## Phase A — result

An expert uploads a project's price list (CSV, or the first sheet of an XLSX); each upload is an
immutable revision bound to its file's Blob, with its parsed positions and a deterministic parse
report; the newest revision is current and every earlier one stays readable. An administrator
keeps a global vendor list per section; an expert may override it per project and section
(`list`) or remove the override (`inherit`); every change is a new immutable revision with its
actor and time. No money figure exists without a price-list position: this slice stores prices;
matching, proposals and totals are the next slice.

### Migration `0026_price_lists` (chained on `0025_work_assignments`)

| object | what it holds |
|---|---|
| `price_list_revision` | `prl_<ULID>`, project (FK), per-project `revision_number` (display order, unique, never an identity), uploader (FK `app_user`), `uploaded_at`, Blob binding (`blob_id` FK, `sha256`, `size_bytes`, `media_type`), `source_format` (`csv`/`xlsx`, paired with its media type), `source_filename` (display only, plain base name ≤ 255), `default_currency`, `parse_report` (jsonb object), data/accepted/skipped row counts (accepted ≥ 1, sum checked, ≤ 20 000); `am_immutable_row` |
| `price_list_position` | `prp_<ULID>`, revision (FK), source `row_number` (unique per revision), code?, name, mark?, unit, `unit_price` exact `numeric` (> 0, < 10^14, scale ≤ 6), ISO currency, vendor?, section? (the fifteen codes); `am_immutable_row` |
| `vendor_list_revision` | `vnl_<ULID>`, scope `global` (no project) / `project`, project (FK), section (fifteen), mode `list`/`inherit` (inherit only for a project, with no entries), `revision_number` unique per (project or global, section) via `NULLS NOT DISTINCT`, entry count ≤ 500, author (FK `app_user`), `set_at`; `am_immutable_row` |
| `vendor_list_entry` | (revision, ordinal) key, material?, vendor, note?; `am_immutable_row` |
| `am_check_price_list_blob` | BEFORE INSERT: the named Blob is `available` with the recorded digest and size, else `AM001` |
| `am_require_price_list_positions`, `am_require_vendor_list_entries` | deferred constraint triggers: a revision whose positions (entries) are not all written is refused at COMMIT (`AM001`) |

Both account columns are `RESTRICT` and registered in `access/references.py`. No backfill.
Downgrade drops the four tables and three functions only (Blob rows and objects stay) and logs
how many rows it drops.

### Context `auditmanager.optimisation`

`identity.py` (`PriceListId`, `PriceListPositionId`, `VendorListId`), `parsing/` (standard
library only), `policy.py` (pure rules), `repository.py` (statements), `uploads.py`
(`PriceListUploads`), `commands.py` (`set_global_vendor_list`, `set_project_vendor_list`),
`queries.py`, `public.py`, `README.md`. Imports only `access.public`, `documents.public`,
`ingest.public` (the shared command record), `sections.public` (section names),
`storage.public` and `shared`.

**Upload** (`uploads.py`): role `expert` → identifiers, file name, key, currency → project
exists → a key already claimed is answered before the file is parsed again → the file is parsed
(a refusal creates nothing) → the key is claimed (`command_record`, `upload_price_list`) → the
Blob is recorded `temporary` **before** the first object-store write
(`DurablePublicationStore`), staged under the command's identity, verified and recorded
`verifying` → published → one transaction re-reads the role, marks the Blob `available`, writes
the revision, every position and the command outcome. Same key + same payload (project, actor,
digest, size, file name, default currency) answers the stored revision; another payload is
`idempotency_key_reuse`. A failure after the claim terminates the record `failed`.

**Parsing** (`parsing/`): format by bytes (ZIP → XLSX, OLE2 `.xls` refused, else CSV); CSV
UTF-8 ± BOM, UTF-16 with BOM, else Windows-1251, delimiter `;`/tab/`,` chosen by where the
header is found; XLSX first sheet via the package relationships, shared/inline/rich strings,
stored numbers at fifteen significant digits, DTD/entity declarations refused, every part
decompressed through a counting reader (64 MiB). Header within the first 20 non-blank rows by
fixed Russian/English rules; `Сумма`/`Стоимость` never a unit price; two candidates for a
required column refuse the file. A price is a plain number only; anything else skips the row
with one of ten reasons; an unrecognised section is a warning. Report `report_version` 1:
format, encoding/delimiter or sheet, header row, mapped/ignored/ambiguous columns, counts,
skipped rows (first 1000 listed, counts by reason complete), warnings, currency sources.

**Vendor lists**: effective = latest project revision when `list`, else latest global, else
none; exact repeats write nothing; a stale `expected_vendor_list_id` (or `expect_current` when a
revision exists) is `conflict` (`conflict_reason: vendor_list_changed`).

**Reads**: revisions of a project (newest first, `is_current`), one revision with its report,
positions paged by offset/limit (≤ 500, `next_offset`), effective lists for all fifteen
sections, the global lists, a section's history. Any one role reads; no role is
`permission_denied` (`role:admin|expert`); a price list outside the named project is
`not_found` (`PriceList`).

Refusals use the existing catalog only: `validation_failed` (`field: content` with
`non_empty`, `byte_size <= 10485760`, `price_list_format`, `price_list_unreadable`,
`price_list_encoding`, `xlsx_part_size <= 67108864`, `price_list_header`,
`price_list_header_ambiguous`, `data_rows <= 20000`, `price_list_no_positions`; and
`inherit_has_no_entries`, `max_items`, `required`, `max_length`, `enum`, `pattern`),
`permission_denied` (`role:expert`, `role:admin`, `role:admin|expert`), `not_found`
(`Project`, `PriceList`), `conflict` (`vendor_list_changed`), the idempotency codes and the
storage codes.

### Checks (phase A)

All on the lane's own containers (`make up`, `make migrate` to `0025_work_assignments` at
the base), `.env` from `.env.example` with the lane values, the interpreter of the
`w55b-main-candidate` venv, `python -m pytest -c pyproject.toml --rootdir=. -q -p
no:cacheprovider <paths>`; host before the runs: 6.3 GiB free on `/`, 6 GiB memory available.

- `tests/unit/optimisation` — 98 passed (container-free): CSV UTF-8 ± BOM, UTF-16, cp1251,
  the three delimiters, the decimal comma and every grouping form, 18 non-prices each with its
  reason, malformed rows reported not repaired, currency precedence, section spellings, header
  tiers and ambiguity, `Сумма`/`Стоимость`, every whole-file refusal, 20 000 rows accepted and
  20 001 refused, XLSX shared/inline/rich/phonetic strings, stored numbers, first sheet by
  workbook order, DTD refusal, part-size bound; the migration's restated sections, formats and
  bounds held equal to the code and to `sections.public.SECTION_CODES`; identities free in
  the registry; the role matrix; entry normalisation.
- `tests/integration/db/test_price_lists_migration.py` — 53 passed: a populated `0025`
  database upgrades with no row changed; `AM003` on all four tables; `AM001` for a revision
  without all its positions, a vendor list without all its entries and a binding to a Blob
  that is not available with the recorded digest and size; 42 malformed-row CHECK cases and the
  bounds admitted; unique revision numbers per scope; each account column, the project and the
  Blob blocking a delete; downgrade (with its count warning) and re-upgrade.
- `tests/integration/optimisation` — 41 passed: the upload bound to its available Blob (one
  canonical object, no temporary left), XLSX, exact replay, five same-key conflicts, new
  revisions with the earlier readable, three concurrent uploads numbered 1-2-3, expert-only
  upload, eleven refused requests/files leaving no command record, Blob row, revision or object,
  a bounded handle read, a storage failure leaving its `verifying` breadcrumb and a `failed`
  record that answers its key, the role re-read in the writing transaction, paging, reads by
  role and foreign scope, purge refused; the vendor-list matrix (global/admin, project/expert,
  effective source, repeats, stale writers, history, refusals, purge refused).
- Whole `tests/integration/db` + `tests/integration/optimisation`: 467 passed, 24 failed —
  exactly the pre-existing classes `W61-DISPATCHER-01` measured at its base: 23 downgrades that
  break at `0022_findings_v2` with `cannot drop columns from view` (each passes through the
  `0026` downgrade first) and `test_norms_corpus_migration` not listing `norm_retrieval_set`.
- Inventory reseal measured from two fresh databases (`0025` vs `0026`), row-diffed: the `0025`
  database equalled the previous seal in every family; every added row is this revision's.
- Mutation probes, each restored afterwards: dropping the role re-read at commit, the project
  scope on a price-list read, the stale-writer check, or the ambiguous-price refusal, and
  repairing `500 руб.` into a price, each turned its test red.
- `tests/contract/architecture`, `domain_p02`, `api_v1/test_doc_prose_facts.py`,
  `tools/test_pin_sweep.py`: 200 passed, 1 failed —
  `test_the_scanned_docs_state_the_migration_head_this_tree_has`, already red at the base
  (`docs/program/CURRENT_STATE.md`, integrator-owned, and `docs/manual-tests/PC-01_prototype.md`,
  a phase B path, still say `0024`).
- `git diff --check` clean; every new module compiles. Deferred under `R-135`: the full gate,
  the whole contract battery, the frontend and the live journey.

## Phase B — operations, reseal, the «Оптимизация» tab

Merged `c22f2049` (54/61/158) on the integrator's go, then `beafeab5` (56/63/161: the norms
catalogue and the Excel export), re-deriving every generated artifact both times.

### Surface

| | before (`beafeab5`) | after |
|---|---|---|
| paths / operations / schemas | 56 / 63 / 161 | 61 / 69 / 188 |
| API error codes / migration head | 25 / `0024_version_classification` | 25 / `0026_price_lists` (this branch also carries `0025`) |

Six operations, tag `optimisation`, accepted as proposed:

| operation | method and path | role |
|---|---|---|
| `uploadPriceList` | `POST /projects/{project_uid}/price-lists` (multipart `file` + optional `default_currency`, `Idempotency-Key`) | `expert` |
| `listPriceListRevisions` | `GET /projects/{project_uid}/price-lists` | any one role |
| `listPriceListPositions` | `GET /price-lists/{price_list_id}/positions?offset&limit` (limit ≤ 500) | any one role |
| `getEffectiveVendorLists` | `GET /projects/{project_uid}/vendor-lists` | any one role |
| `setGlobalVendorList` | `PUT /vendor-lists/{section_code}` | `admin` |
| `setProjectVendorList` | `PUT /projects/{project_uid}/vendor-lists/{section_code}` (`mode` `list`/`inherit`) | `expert` |

Twenty-seven schemas (`PriceListId`, `PriceListPositionId`, `VendorListId`, `PriceListFormat`,
`PriceListField`, `PriceListRowReason`, `PriceListCurrencySource`, `PriceListColumn`,
`PriceListAmbiguousColumn`, `PriceListRowNote`, `PriceListReasonCount`,
`PriceListCurrencySourceCount`, `PriceListParseReport`, `PriceListRevision`,
`PriceListRevisionList`, `PriceListPosition`, `PriceListPositionPage`, `UploadPriceListRequest`,
`VendorListMode`, `VendorListScope`, `VendorListSource`, `VendorListEntry`, `VendorListRevision`,
`SectionVendorList`, `EffectiveVendorLists`, `SetGlobalVendorListRequest`,
`SetProjectVendorListRequest`). A unit price crosses the wire as its exact decimal text. The
stored report's maps become ordered lists in the adapter, in the context's canonical orders
(`jsonb` keeps no key order). A section code outside the fifteen in a path is `404`
(`aggregate_type: VendorList`), like a malformed identity; `setGlobalVendorList` therefore
declares `404` too. `section_code` is the one non-identity path parameter, registered in
`tests/contract/domain_p02/test_openapi_document.py` (`VOCABULARY_PATH_PARAMETERS`) and held to
the closed `ProjectSection` enum by a new test.

**Contract family placement (integrator decision on XS-11/U-06).** These operations live in
`contracts/api/v1` like every served operation; a `contracts/optimization/v1` family is reserved
for the future LLM proposal pipeline and is not created here.

Domain catalog revision 15 (`identifiers.json`, `error-codes.json`, `state-machines.json` and
their schemas move together): `price_list_id` (`prl`), `price_list_position_id` (`prp`),
`vendor_list_id` (`vnl`) with an `optimisation_identity` distinct-identity rule; notes register
`conflict_reason: vendor_list_changed` and the price-list `constraint` values. The shared
registry gains `PriceListId`, `PriceListPositionId`, `VendorListId`; `optimisation/identity.py`
now validates through them (the only phase B change inside `src/auditmanager/optimisation/`
besides two exported orders in `public.py` / `parsing/__init__.py` and three wording fixes the
error-code prose guard asked for).

### Backend

- `api/schemas/models.py` (27 models), `api/routers/ports.py` (`OptimisationPort`),
  `api/routers/optimisation.py` (six routes; the upload uses `UploadRoute`'s bounded form parser
  and `require_a_strict_multipart_body`, **not** the upload gate: 10 MiB is inside the
  ordinary 26 MiB body cap and nginx's 32m default, so `_UPLOAD_ROUTE`, `nginx.conf` locations and
  `tls-server.conf` are unchanged), `api/routers/__init__.py` (nineteenth router module),
  `api/routers/handlers.py` (`price_list_id` → `PriceList`, `section_code` → `VendorList` for a
  malformed path), `api/security.py` (role table).
- `bootstrap/adapters.py` — `OptimisationAdapter` (reads roles in each transaction, maps records
  to the frozen shapes); `bootstrap/composition.py` wires it over the same sessions and store.

### Web

- The project screen has two tabs, «Документы» (default; the cold load still makes only the
  documents' calls) and «Оптимизация»; the route passes the guard's `roles`.
- `entities/price-list` (query options, Russian labels for every reason, source, field, format
  and currency, the refusal sentences for every file constraint), `features/upload-price-list`
  (multipart upload under an intent key, optional default currency, 10 MiB pre-check),
  `features/set-vendor-list` (project and global commands with `expected_vendor_list_id`, a row
  editor), `widgets/project-optimisation` (revisions with the current one marked, positions with
  exact prices and the parse report — skipped rows with reasons, warnings, ambiguous and ignored
  columns, currency sources — paging, and the fifteen sections' vendor lists with the controls
  each role is given). Own module CSS on the global tokens only.
- New query root `optimisation` (`priceLists`, `positions`, `vendorLists`,
  `projectVendorLists`), recorded in `web/docs/PC01_UI_SEAM.md` §6.

### Reseal files

`contracts/api/v1/openapi.json` and byte-identical `web/openapi/openapi.json`, regenerated
`web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json` (both digests, the four generated
files, 61/69/188), `tests/support/expected_facts.json` (surface and head `0026`), the registers in
`tests/contract/domain_p02/test_openapi_document.py`, `tests/contract/api_v1/
{test_openapi_conformance,test_w55b_portal_bundle_seal,test_surface_counts_in_prose}.py`,
`tests/integration/api/{test_authorization,test_role_register,test_served_document_and_health_plane,
test_operation_surface}.py`, `tests/integration/composition/{test_every_port_implementation_is_whole,
test_an_absent_parent_is_not_an_empty_page}.py`, the surface prose in `P02_SEAMS.md` (history,
table, keyed-write rule), `ALPHA_ROADMAP.md`, `infra/deploy/{README.md,proxy/nginx.conf,serve.py}`,
`api/{README.md,app.py,health.py}`, `api/routers/{declarations,errors}.py`, the BFF `route.ts` and
`shared/api/authorization.ts`; `docs/manual-tests/PC-01_prototype.md` (head) and
`ALPHA_PUBLIC_ACCEPTANCE.md` (A09 item 3). Web registers: `narrow-sets`, `seam-operations`,
`dashboard-invalidation` (both hooks `false`), `configuration-and-cache-keys`, `routes.test.ts`,
the rendered-language guard (`optimisationShapes()`), the contrast census (and `.am-form__chosen`
left its excuse list, now rendered). `CONTRACT_PIN_REGISTRY.md` needed no change (no needle
moved). `docs/program/CURRENT_STATE.md` is the integrator's and still states 56/63/161 and head
`0024`.

### Checks (phase B, on the merged tree)

| command | result |
|---|---|
| `tests/contract/api_v1/test_openapi_conformance_live.py` | passed (served document = contract) |
| `pytest tests/contract` (whole directory) | 1059 passed; 86 failed + 126 errors, all known: `test_cp00_candidate` 48 + 126 errors, `test_validate_bootstrap` 21 (`jsonschema` absent), `test_cp00_final_state` 3, `test_doc_prose_facts` 2 (`CURRENT_STATE.md` only), `test_error_kernel::test_there_are_twenty_four`, `test_ar_v2_seeded::test_seeded_categories_equal_the_sealed_api_enum` |
| `npm --prefix web ci` / `api:generate` / `api:verify` | exit 0; 69 operations, `--check: OK` |
| `npm --prefix web run lint -- --quiet`, `typecheck` | exit 0, exit 0 |
| vitest `tests/guards tests/contract tests/unit/api tests/unit/styles tests/unit/screens tests/unit/qa_w50 tests/unit/optimisation tests/unit/projects tests/unit/upload` | 70 files, 1180 passed (rendered-language guard included) |
| `pytest tests/e2e/test_pc01_journey_conformance.py` | 87 passed |
| lane: `tests/integration/composition/test_optimisation_over_http.py` | 4 passed (upload, replay, `409`, `422 price_list_format`, `403`, `404`; revisions; positions with the report and exact prices; vendor lists global and project, stale `409`, inherit, `404` for a section outside the fifteen) |
| lane: `tests/integration/api/{test_authorization,test_role_register,test_served_document_and_health_plane,test_operation_surface,test_router_and_body_rules,test_multipart_rules,test_identity_rules,test_schema_conformance,test_schema_bounds,test_no_internal_identifiers,test_query_surface,test_listing_surface,test_absent_and_empty_are_not_the_same_answer}.py`, `tests/integration/composition/{test_every_port_implementation_is_whole,test_an_absent_parent_is_not_an_empty_page,test_composition_root,test_router_answers}.py` | all pass except three pre-existing: `test_query_surface::test_the_filter_vocabularies_are_the_frozen_ones` (`FindingCategory` has 12 members since W56a), `test_query_surface::test_every_declared_query_parameter_is_read_by_the_router_that_declares_it` (already red for the offset-paged `compareDocumentVersions`; `listPriceListPositions` joins it, see risks), `test_every_port_implementation_is_whole::test_pre_decide_adapter_refuses_a_severity_instead_of_dropping_it` (W59 noted it) |
| lane: `tests/unit/optimisation tests/integration/optimisation tests/integration/db/{test_price_lists_migration,test_schema_shape,test_schema_invariant_inventory,test_accounts_migration}.py` | 252 passed (6 downgrade cases deselected: the known `0022` view failure) |

Deferred under `R-135`: the full gate, the live journey, the whole frontend suite.

### Risks and limits

- `test_query_surface`'s driver pages by cursor; neither offset-paged operation
  (`compareDocumentVersions`, now `listPriceListPositions`) is driven by it. The positions'
  `offset`/`limit`/`next_offset` are driven by `tests/integration/optimisation` and the
  over-HTTP suite instead.
- The journey manifest declares no optimisation call: the tab reads nothing until opened, and
  the journey does not open it. The live journey was not run.
- No price date or VAT flag is parsed (the price header's text is in the report).

### Known limitations
- `auditmanager.ingest.reconciliation` does not know `price_list_revision`: an available
  price-list Blob appears in its `unattributed_blobs` (visible and adoptable, never
  action-ready). The interrupted states (`temporary`/`verifying` Blob, `in_progress` command)
  are enumerable as for any upload. Teaching the reconciler the new binding is outside this
  task's paths.
- The global vendor list starts empty: seeding it from legacy (A-3) is not in this slice.
- No price date column and no VAT flag are parsed; the price column's header text is kept in
  the report so the expert sees «с НДС»/«без НДС».
- A replay of a stored key re-reads the file to compute its digest, but is answered before the
  file is parsed again.
- A single domain-catalog revision (15) is claimed here; if another lane contracts an identity
  first (the dispatcher's `asg`), the later merge must renumber, not keep two revision 15s.

## Integrator instructions

1. Merge `agent/w60-price-list-01` (phases A and B are one slice) after `W61-DISPATCHER-01`'s
   final. Keep both sides of `contracts/api/v1/openapi.json`, `contracts/domain/v1/**` and
   every register; re-derive the mirror, `api:generate`, `api:verify`, `FRONTEND_LOCK.json`,
   `expected_facts.json` and every count — never hand-merge generated files. `migration_head`
   stays `0026_price_lists`.
2. Move `docs/program/CURRENT_STATE.md` to the merged surface and head `0026_price_lists`.
3. `make migrate` on the stand applies `0026` (and `0025`) with no backfill.

## Hotspot proof

- `git log --no-merges 4327e61a..HEAD -- docs/program/CURRENT_STATE.md web/src/_app/providers.tsx
  web/src/app/globals.css src/auditmanager/dispatch pyproject.toml uv.lock web/package.json
  web/package-lock.json` lists only the integrator's three `docs(state)` commits that arrived
  with the merged integration tips (`a820849a`, `c22f2049`, `beafeab5`); no commit of this task
  touches any of them.
- `git diff 3461747c HEAD -- src/auditmanager/dispatch
  db/migrations/versions/20261020_0025_work_assignments.py` is empty: the dispatcher's phase A is
  carried unchanged.
- No dependency was added; no ref, tag or push was made. Phase A touched only its seven paths and
  the two docs; phase B's `contracts/domain/v1/**` and `shared/identity/**` edits are the
  integrator's grant.
