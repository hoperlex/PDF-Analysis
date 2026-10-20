# `optimisation` boundary

«Оптимизация проекта», storage slice (`W60-PRICE-LIST-01`; `CODE-FIRST-SCOPE-W58-W63.md` W60
PROJECT-OPT; `ROADMAP-TO-BETA.md` §10.1 A-3..A-5). An expert uploads a project's price list
(CSV or the first sheet of an XLSX); each upload is an immutable revision with its parsed
positions and a parse report, and the newest revision is current. An administrator keeps a
global vendor list per section; an expert may override it per project and section. **No money
figure exists without a price-list position**: this slice stores and shows prices; proposals,
matching and totals are the next slice.

Other contexts import `auditmanager.optimisation.public` only.

## Storage (`0026_price_lists`)

- `price_list_revision` — immutable: `prl_<ULID>`, project, per-project `revision_number`
  (display order, never an identity), uploading expert and time, the uploaded file's Blob
  binding (`blob_id`, SHA-256, size, media type — checked against the `available` Blob row at
  insert), format, file name (display only), declared default currency, the parse report and
  its row counts. A deferred trigger refuses a revision whose positions are not all written.
- `price_list_position` — immutable: `prp_<ULID>`, source row number, code?, name, mark?,
  unit, exact `numeric` unit price (> 0, < 10^14, ≤ 6 decimals), ISO 4217 currency, vendor?,
  section? (one of the fifteen sections).
- `vendor_list_revision` — immutable: `vnl_<ULID>`, scope `global` (no project) or `project`,
  section, mode `list` | `inherit`, `revision_number` per (scope, project, section), entry
  count, actor, time. `vendor_list_entry` — its ordered entries (material?, vendor, note?).

Account columns are `RESTRICT` references registered in `access/references.py`.

## Upload (`uploads.py`)

Role `expert` → project exists → the file is parsed (bounded; a refusal creates nothing) →
the idempotency key is claimed (`command_record`, type `upload_price_list`) → the Blob is
recorded `temporary` **before** the first object-store write, staged under the command's
identity, verified and recorded `verifying` (`DurablePublicationStore`) → published → one
transaction marks it `available` and writes the revision, every position and the command's
outcome. The same key with the same payload answers the stored revision; with another payload
it is `idempotency_key_reuse`.

## Parsing (`parsing/`, standard library only)

- Format by bytes: ZIP → XLSX (first sheet via the package relationships; shared strings,
  inline strings, numbers; DTD/entity declarations refused; every part decompressed through a
  counting reader); OLE2 (`.xls`) refused; anything else CSV (UTF-8 with or without BOM,
  UTF-16 with BOM, else Windows-1251; delimiter `;`, tab or `,` — the first under which a header
  is found).
- Bounds: ≤ 10 MiB, ≤ 20 000 data rows, header within the first 20 non-blank rows.
- Header mapping by fixed rules (Russian and English): наименование/name, ед. изм./unit,
  цена/price, валюта/currency, код/артикул/code, поставщик/производитель/vendor,
  марка/тип/обозначение/mark, раздел/section. `Сумма`/`Стоимость` are never a unit price.
  Two candidate columns for a required field refuse the file; for an optional one neither is
  read and the report lists them.
- A price is a plain number only (decimal comma by default, thousands by spaces, or by points
  with a decimal comma, or by commas with a decimal point); anything else skips the row with a
  reason. XLSX numbers are read at fifteen significant digits (Excel's display precision).
  Nothing is rounded to fit a bound.
- Currency per row: its cell, else the price header's (`Цена, руб.`), else the declared
  default; none → skipped.
- The report (`report_version` 1) is deterministic: format, encoding/delimiter or sheet,
  header row and mapped columns, ignored/ambiguous columns, counts, skipped rows with reasons
  (the first 1000 listed; counts by reason complete), warnings (`section_unrecognised`),
  currency sources.

## Vendor lists (`commands.py`)

- `set_global_vendor_list` — `admin`; `set_project_vendor_list` — `expert`, mode `list` or
  `inherit` (removes the override).
- Effective list of a section: the latest project revision when its mode is `list`, else the
  latest global revision, else none. A later run records the revision id it used.
- An exact repeat writes nothing; `expected_vendor_list_id` that is not the latest revision is
  `conflict` (`conflict_reason: vendor_list_changed`).

## Reads (`queries.py`)

`list_price_list_revisions`, `get_price_list_revision`, `list_price_list_positions` (offset /
limit ≤ 500, `next_offset`), `get_effective_vendor_lists` (all fifteen sections),
`list_global_vendor_lists`, `list_vendor_list_history`. Any one role reads; no role is
`permission_denied` (`R-80`); a price list outside the named project is `not_found`.

## Identity

`prl`, `prp` and `vnl` are contracted (`contracts/domain/v1/identifiers.json` revision 15) and
registered in `shared/identity`; `identity.py` validates through the registry's types and
answers a malformed value with `validation_failed` naming the field.
