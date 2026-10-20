# XLSX-RU-LABELS-01 — the Excel export prints the screens' Russian labels

**Task:** `tasks/XLSX-RU-LABELS-01.md`. **Branch:** `agent/xlsx-ru-01`. **Base:** `59f976fc`
(`origin/dev` plus the task files). **Rulings:** `R-135`, `R-139`.

No layout change, no new column, no CSV change, no contract change. API 71 paths / 81
operations / 235 schemas, 25 error codes and migration head `0027_optimisation_proposals` are
untouched (`git diff 59f976fc -- contracts db src/auditmanager/api` is empty).

## What changed

| File | Change |
| --- | --- |
| `src/auditmanager/exports/xlsx/labels.py` (new) | The one Python source of the workbook's words: `SEVERITY_LABELS` (5), `CATEGORY_LABELS` (12), `VERDICT_LABELS` (4), each in the contract's value order, read-only mappings, and `label()` which raises for a value outside the table (no fallback). |
| `src/auditmanager/exports/xlsx/writer.py` | Enum cells are written as labels: «Категория» (`C`), both severity columns (`F`, `G`), «Решение эксперта» (`J`) on «Замечания», and the severity and category rows of «Сводка». `SEVERITIES` is now `tuple(SEVERITY_LABELS)`. `_validate` refuses a category outside the twelve (`xlsx_category_invalid`) and a non-empty verdict outside the four (`xlsx_verdict_invalid`); the severity refusal is as before. `""` stays the empty cell (the dataclass default: no verdict supplied). |
| `src/auditmanager/exports/xlsx/projection.py` | `_VERDICTS = frozenset(VERDICT_LABELS)` instead of a second literal of the same set. |
| `tests/unit/exports/test_xlsx_labels_lockstep.py` (new) | The lockstep test (below). |
| `tests/unit/exports/test_xlsx_writer_labels.py` (new) | Writer behaviour: all 12 × 5 × 4 values, summary rows, no raw value anywhere, identifiers and free text verbatim, no formula, fill follows the value, refusals; plus the layout pins (below): a labelled-vs-raw ZIP comparison, `LAYOUT_DIGESTS` and `TEXT_DIGESTS`. |
| `tests/integration/exports/test_xlsx_soffice_probe.py` | An opt-in (`W57B_RUN_SOFFICE=1`) LibreOffice CSV check, cell by cell, over every label. |
| `tests/unit/exports/test_xlsx_run_export.py`, `tests/integration/exports/test_xlsx_{writer_prep,projection_prep,run_export}.py` | Expected cell values re-pinned from contract values to labels (see "Re-pinning"). |

Not changed: any `web/**` file, `run_export.py` (its `_ATTRIBUTION` strings are already Russian
and carry the contract value in brackets), `query.py`, `package.py`, the certified chain, the
CSV, the layout, styles, column widths, sheet names.

### What is a label and what is not

| Cell | Written as |
| --- | --- |
| severity (both columns, summary rows) | `SEVERITY_LABELS[value]`: «Критическое», «Экономическое», «Эксплуатационное», «Рекомендация», «Проверить смежный раздел» |
| category (`C`, summary rows) | `CATEGORY_LABELS[value]`, twelve labels; summary rows stay ordered by the contract value, as before |
| «Решение эксперта» (`J`) | `VERDICT_LABELS[value]`: «не решено», «принято», «отклонено», «нужен ручной разбор» |
| project, version, run, profile, snapshot | verbatim, opaque ids |
| page/sheet label, finding text, recommendation, comment, citations, member note | verbatim |
| «также найдено», headers, «Без серьёзности», attribution | unchanged (already Russian) |

**The words are the screens', not the task text's examples.** The task wrote «критично»,
«пожарная безопасность», «ожидает решения». The screens print «Критическое», «Пожарная
безопасность», «не решено», and "the same labels the screens show" is the requirement, so those
are the words. The writer emits no "modality" cell. The other `VERDICT_LABELS` in the web
(`entities/optimisation-proposal`, accept/reject/revise) belongs to optimisation proposals and
is not in this workbook; it is deliberately not locked.

**The web sources are not where the task and brief named them.** The task lists
`web/src/entities/finding/model/category-labels.ts`; that file does not exist. The tables are:

| Python table | Web file (exported name) |
| --- | --- |
| `SEVERITY_LABELS` | `web/src/entities/finding/model/severity-labels.ts` (`SEVERITY_LABELS`) |
| `CATEGORY_LABELS` | `web/src/entities/expert-decision/model/category-labels.ts` (`CATEGORY_LABELS`) |
| `VERDICT_LABELS` | `web/src/entities/expert-decision/ui/verdict-badge.tsx` (`VERDICT_LABELS`) |

The lockstep test reads these paths and fails loudly (`FileNotFoundError`) if one moves.

## The lockstep test

`tests/unit/exports/test_xlsx_labels_lockstep.py` is container-free and needs no node. It:

1. parses the three web tables as text with a small tolerant parser (comments, quote styles,
   trailing commas, quoted keys, escapes) that is **strict about meaning**: a concatenation, a
   `${}` template, a spread, a computed key, a non-literal value, a duplicate key, a missing or
   doubled declaration is `TsTableUnreadable`, never a skipped entry;
2. asserts each Python table equals the web table in keys and in every character;
3. asserts each Python table's key order equals the enum in `contracts/api/v1/openapi.json`
   (`Severity`, `FindingCategory`, `Verdict`);
4. proves it can fail: seven mutated table pairs (relabel on either side, trailing space, Latin
   homoglyph, a value added or dropped) must each be reported, and a relabel or an added key
   applied to the real severity file text must turn the comparison red.

A UI relabel without an export relabel, and a contract value added without a label, are red.

## Re-pinning: what moved

There is **no pinned digest and no golden workbook** in the repository: no file holds a
SHA-256 of `writer.py` or of rendered bytes (`git grep -n "exports/xlsx" -- '*.json' '*.sha256'
'*.lock'` finds nothing; the only `*xlsx*` hit outside code and docs is the operation path in
`tests/support/expected_facts.json`). What the certified chain pins is cell values in four tests,
and those are what moved, from the contract value to the label:

| Test | Moved expectations |
| --- | --- |
| `tests/unit/exports/test_xlsx_run_export.py` | `J` `pending` → `не решено`; added `C` and the summary rows |
| `tests/integration/exports/test_xlsx_writer_prep.py` | summary severity rows and category rows |
| `tests/integration/exports/test_xlsx_projection_prep.py` | `F2`, `G2`, `J2` (+ `C2`) in both rendered-row tests |
| `tests/integration/exports/test_xlsx_run_export.py` | `J` per finding; merged finding `G2` `economic` → `Экономическое`; added: `C` equals the label of each stored category |

New expectations are literals, not imports of the tables, so a table edited on both sides still
has to be edited in the tests on purpose.

### Proof that only the label cells moved

**One-off, against the real base code.** Render one fixed corpus with the **base** writer
(`git archive 59f976fc src contracts | tar -x -C <dir>`, then import from `<dir>/src`) and with
this branch, and compare the two ZIPs part by part. The corpus: 48 findings = every one of the
12 categories × every one of the 4 verdicts, all 5 severities as proposed and decided,
citations, members, a formula-like recommendation and an XML-forbidden character. For every
sheet: same cell addresses and order, same `s`/`t` attributes, same numeric values, the XML with
every cell text blanked byte-identical, and every moved cell's new text equal to
`label_table[old text]`.

```
byte-identical parts: [Content_Types].xml, _rels/.rels, xl/workbook.xml,
                      xl/_rels/workbook.xml.rels, xl/styles.xml
changed parts:        xl/worksheets/sheet1.xml, xl/worksheets/sheet2.xml
sheet1: 54 cells, 17 moved (column A)               = 5 severity + 12 category rows
sheet2: 671 cells, 150 moved (C 48, F 12, G 42, J 48)
every moved cell: new text == label_table[old text]
ZIP entry names, order, compression, timestamps, attributes: identical
OK: only label cells moved
```

(Trees `59f976fc` and `4a4775e3`; the writer is unchanged since.)

**Permanent, in `tests/unit/exports/test_xlsx_writer_labels.py`.** The one-off proof does not
survive a scratch directory, so its result is pinned in three tests over a 48-finding corpus:

1. `test_only_the_enum_cells_differ_from_the_raw_value_rendering` renders the corpus twice, with
   the label tables and with identity tables patched in (what the base writer printed), and
   requires: same parts, the two sheets alone differ, skeletons equal, moved cells are exactly
   the enum columns, each moved by its table. It cannot see a change common to both renderings.
2. `LAYOUT_DIGESTS`: SHA-256 of the five static parts and of the two sheets' skeletons, **captured
   by running the base writer** on the same corpus and equal to this writer's.
3. `TEXT_DIGESTS`: SHA-256 of every cell address and text outside the enum cells (identifiers,
   headers, counts, free text, page labels, citations, «также найдено»), also captured from the
   base writer.

A deliberate layout or text change now fails 2 or 3 and must re-pin it in the same change.
These are the "golden bytes" this slice re-pins deliberately: they did not exist before it.

## Checks and results

Python: `…/w55b-main-candidate/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q
-p no:cacheprovider <paths>`.

| Check | Tree | Result |
| --- | --- | --- |
| `tests/unit/exports` + `tests/integration/exports/test_xlsx_{writer_prep,projection_prep,soffice_probe,package,certified_package}.py`, container-free | `dfe70910` | 121 passed, 2 skipped |
| `tests/unit/exports/test_xlsx_labels_lockstep.py` + `test_xlsx_writer_labels.py` | `dfe70910` | 48 passed |
| Lane stack (`auditmanager-xlsx-ru`, postgres 57660, s3 61260/61261, migrated to `0027`), `tests/integration/exports` + `tests/unit/exports`, no bytecode cache | `dfe70910` | 224 passed, 2 skipped, 1 failed (77 s) |
| Same, two earlier runs (the first with the real workbooks dumped for LibreOffice) | `4a4775e3`, `ab9bbc94` | 221 passed, 2 skipped, 1 failed each (same failure) |
| `W57B_RUN_SOFFICE=1 … test_xlsx_soffice_probe.py` | `dfe70910` | 6 passed (the existing real roundtrip and the new CSV test) |
| `tests/contract/api_v1/test_doc_prose_facts.py`, `test_surface_counts_in_prose.py`, `tests/contract/program` | `dfe70910` + this report | 105 passed |
| `git diff --check 59f976fc` | final | clean |

**The one failure is not from this change.**
`tests/integration/exports/test_the_download_name_has_one_source.py::…::test_the_router_is_the_only_source_file_that_builds_an_attachment_name`
fails because `src/auditmanager/api/routers/optimisation_proposals.py:304` builds
`Content-Disposition: attachment; filename="<pass>.csv"` (`234a8113`, W60). The test scans
`src/**` and this branch changes nothing under `src/auditmanager/api`. It needs a decision by the
owner of the download-name guard (allow the second router or route the name through
`export.py`); it was not touched here (forbidden hotspot).

The 2 skips are the two opt-in LibreOffice tests when `W57B_RUN_SOFFICE` is unset.

Resources: before the stack came up, `free -m` showed 4,240 MiB available and `df -B1 /`
7,586,217,984 bytes at `2026-10-20T08:49Z` (peak expected under 300 MB; images already local).
After each run `make down`, then only `auditmanager-xlsx-ru-postgres-data` and
`auditmanager-xlsx-ru-s3-data` were removed; no lane container, network or port remains.

### LibreOffice (`soffice --headless`)

`/usr/bin/soffice`, LibreOffice 24.2.7.2. Every run used its own
`-env:UserInstallation=file://<temp>/profile`, private `XDG_RUNTIME_DIR` and `HOME`,
`SAL_USE_VCLPLUGIN=svp`, `timeout`. Two independent comparisons:

1. The repository's probe `scripts/rehearsal/w57b/xlsx_soffice_probe.py` (xlsx → xlsx through
   LibreOffice, every non-empty cell compared):

   | Workbook | Result |
   | --- | --- |
   | the 48-finding corpus above | **OK**, sheets «Сводка»/«Замечания», 468 cells equal |
   | real run, 3 findings (DB + S3) | **OK**, 62 cells |
   | real run with a merged finding (DB + S3) | **OK**, 69 cells |

2. A CSV of every sheet (`--convert-to 'csv:Text - txt - csv (StarCalc):44,34,76,1,,0,false,true,false,false,false,-1'`),
   compared position by position with the cells parsed from the XML, **including empty
   positions** (so a stray or formula-filled cell would show):

   | Workbook | Grid positions compared | Mismatches |
   | --- | --- | --- |
   | corpus | 725 (27×2 + 61×11) | **0** |
   | real run | 78 | **0** |
   | real run, merged finding | 100 | **0** |
   | control: the *base* writer's corpus against the new CSV | 725 | **167** (= 17 + 150 moved cells) |

   The control shows the comparison can fail. Formula-like and forbidden-character cells
   (`=1+1`, `+SUM(1,2)`, U+FFFD) read back as the literal text. The real workbooks were produced
   through the real `export_run_xlsx` over PostgreSQL and S3; their labels read «Внутреннее
   противоречие», «Явный пропуск», «не решено», «Экономическое», «также найдено».

The new opt-in test `test_real_soffice_csv_shows_every_label_cell_by_cell` repeats the CSV check
on a fresh 12-finding workbook (143 non-empty cells, plus "nothing else is filled"). The previous
slice could not run LibreOffice; here it ran and agreed. This is LibreOffice only: Excel itself
was not available and has not seen the file.

## Every new guard failing under a quoted mutation

Each row: the mutation applied to the working tree, the tests run, the result; the tree was
restored after each (`git status` clean). Test set `U` is
`tests/unit/exports` + `tests/integration/exports/test_xlsx_{writer_prep,projection_prep}.py`.

| # | Mutation | Tests | Result |
| --- | --- | --- | --- |
| M1 | `writer.py`: `label(CATEGORY_LABELS, finding.category, refusal="xlsx_category_invalid"),` → `finding.category,` | U | 5 failed |
| M2 | `writer.py`: `(SEVERITY_LABELS[severity], by_severity[severity])` → `(severity, by_severity[severity])` | U | 3 failed |
| M3 | `writer.py`: `(CATEGORY_LABELS[category], by_category[category])` → `(category, by_category[category])` | U | 3 failed |
| M4 | `writer.py`: `_verdict_label(finding.expert_decision),` → `finding.expert_decision,` | U | 6 failed |
| M5 | `writer.py`: `_severity_label` body → `return severity or ""` | U | 5 failed |
| M6 | `labels.py`: `label()` → `return table.get(value, value)` (fallback) | U | **passes** alone, see below |
| M7 | `writer.py`: delete the `xlsx_category_invalid` check in `_validate` | U | 4 failed |
| M8 | `writer.py`: delete the `xlsx_verdict_invalid` check in `_validate` | U | **passes** alone, see below |
| M6+M8 | both of the above | `tests/unit/exports` | 5 failed (verdict refusals) |
| M6+sev | M6 and delete the `xlsx_severity_invalid` check | `tests/unit/exports` | 2 failed (severity refusals) |
| M9 | `labels.py`: `"critical": "Критическое"` → `"Критичное"` | U | 9 failed (lockstep and writer) |
| M10 | `severity-labels.ts`: `critical: 'Критическое'` → `'Критично'` | lockstep | 2 failed |
| M11 | `category-labels.ts`: `fire_safety: 'Пожарная безопасность'` → `'Пожарная охрана'` | lockstep | 1 failed |
| M12 | `verdict-badge.tsx`: `pending: 'не решено'` → `'ожидает решения'` | lockstep | 1 failed |
| M13 | `category-labels.ts`: add `vibration: 'Вибрация'` | lockstep | 1 failed |
| M14 | `verdict-badge.tsx`: `rejected: 'отклонено'` → `'отклон' + 'ено'` | lockstep | 1 failed (unreadable, not skipped) |
| M15 | `labels.py`: swap `critical` and `economic` | lockstep | 1 failed (contract order) |
| M16 | `labels.py`: add `"vibration"` to the categories | lockstep | 2 failed |
| M17 | lockstep test: `if web[key] != export[key]` → `if False` | lockstep | 5 failed (self-tests) |
| M18 | `writer.py`: `_string_cell` writes text as `<v>` numbers | `W57B_RUN_SOFFICE=1 … test_xlsx_soffice_probe.py` | 5 failed |
| M19 | `writer.py`: column `C` width `23` → `24` | `test_xlsx_writer_labels.py` | 1 failed (`LAYOUT_DIGESTS`) |
| M20 | `writer.py`: summary header `"Количество"` → `"Кол-во"` | same | 1 failed (`TEXT_DIGESTS`) |
| M21 | `writer.py`: severity fill index `+ 2` → `+ 1` | same | 2 failed (fill test, `LAYOUT_DIGESTS`) |
| M22 | `writer.py`: sheet name «Замечания» → «Замечание» | same | 1 failed (`LAYOUT_DIGESTS`) |
| M23 | `writer.py`: `"также найдено"` → `"Также найдено"` | same | 2 failed |
| M24 | `writer.py`: swap the «Проект» and «Версия» rows | same | 2 failed |

M6 and M8 survive on their own **by design**: a value is refused twice, in `_validate` (before
anything is written, the existing boundary) and again in `label()`; removing one layer leaves the
other. M7 fails alone because the summary indexes the table directly and would raise `KeyError`.
Removing both layers (M6+M8, M6+sev) is caught. No single mutation prints a raw value without a
red test. M19 and M20 first **passed** when only the labelled-vs-raw comparison existed (both
renderings carried the same mutation); that is why `LAYOUT_DIGESTS` and `TEXT_DIGESTS` were added.

**Method trap, found and fixed.** A same-size mutation (M15, M19, M21) restored within the same
second leaves a stale `__pycache__` entry (CPython compares source mtime in whole seconds and
size), so the next run executes the mutated bytecode. It showed up as a baseline digest that
differed for no visible reason. After it was found every `__pycache__` under `src`, `tests` and
`scripts` was deleted, later mutation runs used `PYTHONDONTWRITEBYTECODE=1`, and the final
integration run below was made on a tree with no bytecode cache.

## Behaviour, failure and security cases

- **Unknown value.** A category outside the twelve, a severity outside the five, or a non-empty
  verdict outside the four raises `ValueError` (`xlsx_category_invalid`, `xlsx_severity_invalid`,
  `xlsx_verdict_invalid`) before any part is written. Case, padding, an already-translated word
  («Пожарная безопасность») and a proposal verdict (`accept`) are all refused: no
  double-translation and no silent fallback (`AGENTS.md` §4). The database `CHECK`s bound
  `finding.category` to the twelve and the verdict to the four, so this is unreachable for stored
  data; it is a guard against a future value arriving without a label.
- **Idempotency.** Two renders of one input are byte-identical (the writer reads no clock and the
  tables are fixed): the existing repeat-bytes test and the real-run `export.content ==
  export.content` assertion pass.
- **Formula hardening is unchanged and re-proven.** Cells stay `t="inlineStr"` (text) or counts;
  no `<f>` in any part; XML-forbidden characters → U+FFFD; ≤ 32,767 characters. No label begins
  with `= + - @ \t \r`; LibreOffice reads the formula-like cells back as text.
- **Identity.** No identifier passes through a table; a finding whose free text, page label,
  comment or citation equals a contract value (`critical`, `fire_safety`, `pending`) is written
  verbatim while the enum cells of the same row are labelled.
- **Role/transport.** No change: the operation, its authorization, refusals and download name are
  untouched.

## Risks and known limitations

- **Column width.** «Внутреннее противоречие» is 23 characters in column `C` (width 23); the
  other labels fit their columns (`F`/`G` 28 for a 24-character label, `J` 27, «Сводка» `A` 30).
  Widths were not changed (no layout change). Cyrillic lowercase is narrower than the digit the
  width unit is measured in, so it should fit, but it has not been looked at in Excel.
- **Excel itself was not used**; LibreOffice 24.2 is the only spreadsheet application tested.
- **A second place to relabel.** The web and the workbook are now two copies held together by one
  test. The test only reads the three named files; a screen that adds its own private table for
  these enums would not be seen. Moving a file breaks the test loudly rather than silently.
- **Unknown value becomes an internal error.** `run_export._refusal` maps only the page-source
  and citation refusals to domain errors, so `xlsx_category_invalid` and its siblings would be a
  500 if a value ever arrived unlabelled; unreachable today (see above), and preferable to a
  workbook with a raw English cell.
- **Summary order.** Category rows keep the order of the contract value, so the Russian list is
  not alphabetical («Доступность», «Размеры помещений», «Документация», …). Re-ordering by label
  would be a visible layout decision, not made here.
- **Download-name guard is red on the base** (above), unrelated to this change.

## Deferred (R-135)

Not run: the web label tests and any `npm` step (no `web/**` file changed; the web tables are
only read as text), the whole `tests/contract` battery (only the three documentation prose guards
above ran), the live journey, a full gate. Nothing here claims `GATE OK`.

## Instruction to the integrator

Merge `agent/xlsx-ru-01` (a real merge) into `integration/night-1020`. No contract, migration or
reseal; no `web/**` file is in the diff. If a later task renames or moves one of the three web
files, update `LOCKSTEP` in `tests/unit/exports/test_xlsx_labels_lockstep.py` and the table in
`labels.py`'s docstring in the same change. Open item for the owner of the download-name guard:
the red `optimisation_proposals.py` hit above.
