# W60-PRICE-LIST-01 — «Оптимизация проекта»: project price lists and vendor lists

**Base:** `4327e61a` (`origin/dev` `0f0903f2` plus the frozen task file plus `W61-DISPATCHER-01`
phase A `3461747c`, migration head `0025_work_assignments`), branch `agent/w60-price-list-01`,
isolated worktree `w60-price-list`, lane PostgreSQL 57570 / MinIO 61170–61171. **Status:**
phase A (migration and domain context) complete; phase B (operations, reseal, the
«Оптимизация» tab) waits for the contract slot. Development candidate under `R-135`: no full
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

### Known limitations

- `prl`, `prp`, `vnl` are minted on the registry's pattern but are not contracted
  (`contracts/domain/v1/identifiers.json` and `shared/identity/ids.py` are phase B paths).
- New detail values (`vendor_list_changed`, `inherit_has_no_entries`, the file constraints) are
  to be registered in `contracts/domain/v1` / the OpenAPI document in phase B.
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
