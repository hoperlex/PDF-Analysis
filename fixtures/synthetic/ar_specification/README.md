# Synthetic AR set with a Form-7 specification (`SPEC-TABLE-RECORDING-01`)

**Everything in this directory is synthetic.** It was written by
`tools/fixtures/build_ar_specification.py`, not extracted from any document. There are no
customer, production or real project bytes, and no real organisation, address, person or
vendor is named (`Промет`, `Завод Север` and `Нева-Строй` are invented). Owner decision **OD-17**
rules the PC-01 corpus synthetic-only.

## Why it exists

`fixtures/synthetic/ar/ar_baseline.pdf` has no specification table, and its only recorded model
response is for that PDF. A project holding only the baseline reaches «Спецификация и цены» with
no table and an optimisation pass with **0 proposals**. This set is the AR document that does
carry a specification, with a recorded response and a price list that price it, so the journey
upload -> classify -> run -> price list -> vendor list -> optimisation pass ends with
`cheaper_analog` proposals.

## The exact fixture names

| What | Path |
| --- | --- |
| the portal bundle to upload (ZIP, five members, stem `ar_specification`) | `fixtures/synthetic/ar_specification/ar_specification.zip` |
| the PDF inside it, byte for byte | `fixtures/synthetic/ar_specification/ar_specification.pdf` |
| the project price list (CSV, `;`-separated, UTF-8, ten positions) | `fixtures/synthetic/ar_specification/ar_specification_prices.csv` |
| the oracle: rows, matches, totals, proposals, in exact figures | `fixtures/synthetic/ar_specification/expected_specification.json` |
| digests of the four files above | `fixtures/synthetic/ar_specification/SHA256SUMS` |
| the recorded model response (synthetic), filed under its request key | `fixtures/recorded/sections/ar_specification/<request_sha256>.json` (currently `19fa19530edb2f0a6f0139a2e156ea1128662e52b668ea6a701bb6e946f9e584.json`) |
| its builder | `fixtures/recorded/sections/ar_specification/build_fixtures.py` |

The recorded response is **not** a model call and no money was spent: it is authored by hand,
its `origin` block says `kind: synthetic`, its finding text opens with «Синтетический ответ», it
carries no provider mode, and its token counts and latency are authored, not measured. It is found
by `RecordedAdapter()` (what the composition root serves when `AUDITMANAGER_PROVIDER_MODE=recorded`)
because that adapter searches the canonical directory and every directory under
`fixtures/recorded/sections/`. It is the **AR** profile's answer, not a section recording.

## The journey, step by step (what `tests/integration/optimisation/test_ar_specification_journey.py` drives)

| # | Step | Call | Expected |
| --- | --- | --- | --- |
| 1 | upload the bundle | `POST /projects/{p}/documents` (multipart `file`) | `201`, a document and a version |
| 2 | classify | `PUT /projects/{p}/documents/{d}/versions/{v}/classification` `{"project_stage":"P","section_code":"AR"}` | `200` |
| 3 | start a run | `POST /runs` `{"version_uid": v}` | `202`; the run reaches `published` with one finding (`explicit_placeholder`, page 2) |
| 4 | upload the price list | `POST /projects/{p}/price-lists` (multipart `file`, `default_currency=RUB`) | `201`, ten positions |
| 5 | set the AR vendor list | `PUT /projects/{p}/vendor-lists/AR` `{"mode":"list","entries":[{"vendor":"Завод Север"}]}` (an expert may; the global list is an admin's) | `200` |
| 6 | start a pass | `POST /projects/{p}/documents/{d}/optimisation-passes` | `201`: 7 rows, 5 matched, 4 rows with a proposal, 4 proposals |
| 7 | read | `GET /optimisation-passes/{id}/proposals` | four `cheaper_analog` proposals (below) |

After step 3 and before step 4, `GET .../specification-prices` answers `price_list_missing`; after
step 4 it answers `ready` with the seven rows and the totals below. The decide-and-download steps
(`POST /optimisation-proposals/{id}/decisions`, `GET /optimisation-passes/{id}/export.csv`) are the
live-journey lane's to add.

## What the document holds

Four pages: a title sheet, general data (line `1.3. Тип светопрозрачного заполнения — уточнить.` is
the one seeded issue), and the specification over two sheets (pages 3 and 4).

* Sheet 3 has the Form-7 header (split over two lines, as the print has it), the column
  numbering, the group «Изделия» and rows 1-3. Row 2's name wraps **above** its anchor line
  (`Окно ПВХ двухкамерное` over `2 ОП В2 1460х1460 шт 12`); rows 1 and 3 write the manufacturer
  with its legal form (`ООО «Промет»`).
* Sheet 4 **continues the table without a repeated header** (the group «Материалы», then rows
  4-7; the numbering goes on from 3).

## What the oracle says (RUB throughout)

| Pos. | Row | Price list | Result |
| --- | --- | --- | --- |
| 1 | Дверь противопожарная ДПМ-01/60 EI60 ООО «Промет», 4 шт | mark `ДПМ-01/60`, 25000 | matched, amount 100000; proposal: `ДПМ-02/60`, 21000, `Завод Север` (code family), saving **16000** |
| 2 | Окно ПВХ двухкамерное ОП В2 1460х1460, 12 шт | name, 18500 | matched, 222000; proposal: `…1560х1460`, 17200 (name similarity), saving **15600** |
| 3 | Анкер химический ООО «Промет», 200 шт | name + vendor `Промет` (legal form optional), 12.75 | matched, 2550; proposal: `Анкер химический усиленный`, 9.5, saving **650** |
| 4 | Профиль направляющий ПН 50х40, 120 п.м | priced per `м` | unmatched, `unit_mismatch` (no price, no amount) |
| 5 | Решётка вентиляционная РВ-200, 6 шт | none | unmatched, `no_position` |
| 6 | Монтажная пена, quantity `-` | `компл`, 450 | matched, no amount (`quantity_not_numeric`); proposal: `…армированная`, 300, saving **absent** (never 0) |
| 7 | Гидроизоляционная мембрана Техноэласт ЭПП, 340,8 м² | `м2`, 410 | matched, 139728; no cheaper analog |

Totals: RUB 464278 over 4 rows; excluded: `unit_mismatch` 1, `no_position` 1,
`quantity_not_numeric` 1. Proposals: four, total computable saving RUB 32250.

## Regenerating

```
python3 tools/fixtures/build_ar_specification.py            # rewrite the four files and SHA256SUMS
python3 tools/fixtures/build_ar_specification.py --check    # verify against what is committed
PYTHONPATH=src .venv/bin/python fixtures/recorded/sections/ar_specification/build_fixtures.py [--check]
```

The first is pure standard library and byte-deterministic (fixed dates, fixed document id, the
committed font subset, no PRNG). `--check` also reads the committed PDF back with the independent
extractor and compares every line with the authored text. The second needs the repository's
`src/` and `pdfplumber`: it extracts the text layer with the pinned stage extractor, builds the
AR request, and files the answer under the request's key. **Changing the PDF, the AR prompt
bundle or the extractor changes the key and orphans the recording**; re-run the second builder.
`fixtures/recorded` is part of `build_id` (`src/auditmanager/releases/build_id.py`), so adding
this file changes it.

## Known limits

* One document, one discipline, four pages; the unit and the money are as simple as they can be
  while still showing every outcome. It proves the pipeline, not real-world coverage.
* The figures are computed from the authored numbers in the generator, so a change to a price or a
  quantity there moves the oracle with it; the test compares the product with that oracle.
* The set is for recorded mode. Under a live or proxy provider the run would send this text to a
  model, which is not what this fixture is for.
