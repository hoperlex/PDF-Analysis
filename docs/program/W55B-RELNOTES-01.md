# W55B-RELNOTES-01 — hand-back report

- Task: the 0.6.0 release notes for wave W55b. Owner ruling `R-123` (`OWNER_RULINGS_2026-09-17.md` §3.33) releases W55b
  as **0.6.0** without waiting for P4, superseding `W55-PLAN.md`'s `v0.6.1` target. The pattern is `9da3ea06` (the 0.5.1
  notes, `VERSION`, the version-set pins of two release tests). The house rules come from `W54-RELNOTES-01.md`,
  `W52-RELNOTES-01.md` and `RELEASE_PROCESS.md`.
- Branch `agent/w55b-relnotes`, worktree `.local/worktrees/w55b-relnotes`, base `1debd1b7` (`integration/w55b`).
  The implementation commit is `85c51f82`; this report is the last commit.
- Nothing was pushed, merged, tagged or stashed, and no other branch was checked out.

## 0. The 0.6.0 notes

`release-notes/0.6.0.json`, revision 1, dated `2026-10-15`. The title is «Комплекты портала распознавания, блоки и
распознанный текст» (7 words). It has six items, all visible to a user:

| # | Kind | `screen` (`where`) | What it says |
|---|---|---|---|
| 1 | new | `/projects/[project_uid]` (Работа › Проект) | A document is uploaded as the portal's bundle: one archive with the document, the block file and the recognised-text file. Limits are 500 pages and 250 MiB, up from 30 pages and 25 MiB. A bare document is refused, and the form says what to upload instead. |
| 2 | new | `/blocks` (Знания › Блоки) | «Блоки» opens on «Блоки портала» with the version's blocks by page (text, images, stamps). An image shows a fragment the system cut from the document itself. Blocks appear after the version's first run; versions uploaded earlier without a bundle have none. The old list is on the «Строки текста» tab. |
| 3 | new | `/blocks` (Знания › Блоки) | Recognised text is marked «распознано» and shows quality flags (e.g. «смешение кириллицы и латиницы», «пустой текст»). The portal's image descriptions are marked «описание портала — в анализе не используется». Analysis still reads only the embedded text; recognised text, descriptions and crops do not reach it. |
| 4 | new | `/projects/[project_uid]/versions/[version_uid]` (Работа › Версия документа) | One run accepts text up to a set volume. Above it, starting a run or «Повторный аудит» from the queue is refused at once, and no new run is created. The message gives both figures. Portal blocks are built by a run, so such a version will not get them. |
| 5 | improved | `/projects/[project_uid]` (Работа › Проект) | The bundle is checked whole at upload. On a refusal the form now names the broken rule (e.g. archive contents, size, page count, text on pages). The same rules are listed before a file is chosen. |
| 6 | improved | `/projects/[project_uid]` (Работа › Проект) | A page without embedded text (e.g. scanned) is accepted if the portal recognised at least one block on it, and its recognised text is visible in «Блоки». A page with neither is still refused. |

Left out on purpose:

- **`W55B-FIX`'s refusals** (too many blocks, an unreadable or oversized page, an unauthenticated upload, "upload busy,
  retry in N s"). FIX is in progress and is not on the base. Item 5 names only rule categories that `W55B-INGEST-01`
  delivered; each already has a sentence in `UPLOAD_CONSTRAINT_SENTENCES` on the base.
- The stored stamp audit, the page-box mismatch sentence and paging by 100. They are either invisible to a user or too
  fine for a release line.
- The start-up refusal of a cost ceiling below about $0.80 (`W55B-BUDGET-01` §3.4). It is an operator setting, not a
  screen change, and is already a stop item of `W55B-INT-MAIN-01` (the note under `R-123`).

Wording rules kept:

- Russian only, with no Latin script. The archive is «архив», not ZIP. «PDF» is a dictionary word and is not used, so
  the notes say «документ».
- Screen labels and on-screen phrases are in «».
- The size unit is «МиБ». The contract's unit is MiB, so «МБ» would be about 5 % off.
- `where` is the registry's group and label for each `screen`.
- The dictionary needed no new term.

### 0.1 Claim evidence (`RELEASE_PROCESS.md`: one commit or test per product claim)

| # | Claim | Commits | Tests and sources |
|---|---|---|---|
| 1 | bundle upload, 500 pages, 250 MiB | `d865898b` (reader, envelope, limits), `0333d58e` (browser), `7d8535bd` (final switch) | `tests/integration/ingest/test_bundle_envelope.py::test_the_page_ceiling_is_five_hundred_pages_inclusive`; `web/tests/unit/projects/upload-envelope.test.ts` › «states 250 MiB in bytes, not megabytes», › «states 500 pages and one ZIP archive» |
| 1 | the previous limits were 30 pages and 25 MiB | — | `4fe7615:web/src/entities/document-version/model/upload-envelope.ts` (`maxBytes: 25 * 1024 * 1024`, `maxPages: 30`) |
| 1 | a bare document is refused, and the form says what to upload | `0333d58e`, `7d8535bd` | `tests/integration/api/test_multipart_rules.py::TestEachRefusalNamesItsOwnRule::test_a_bare_pdf_is_refused_as_portal_bundle_required_and_publishes_nothing`; `upload-envelope.test.ts` › «refuses a bare PDF before it is sent, whatever its name says», › «tells a person who chose a bare PDF what to upload instead» |
| 2 | the tab, blocks by page and type, the old list on its own tab | `77d8a4a6` | `web/tests/unit/blocks/blocks-tabs.test.ts` › «opens on «Блоки портала»», › «mounts only the open tab’s content»; `web/tests/unit/blocks/portal-blocks.test.ts` › «opens one section per page, names a differing portal label, and keeps the order» |
| 2 | the image fragment is cut by the product, never taken from the portal | `2f83e608` | `tests/integration/analysis/geometry/test_geometry_stage.py::test_crop_url_and_every_url_reach_no_artifact`; `portal-blocks.test.ts` › «points an <img> at the crop address with its own size, lazily, with a Russian alt» |
| 2 | blocks appear after the first run; none for a version without a bundle | `77d8a4a6` | `web/tests/unit/blocks/portal-states.test.ts` › «says the blocks come after the first run, for a bundle no run has reached», › «says a version without a bundle has none, rather than promising them after a run» |
| 3 | «распознано», the flags, the description marker | `d9bea309`, `77d8a4a6` | `portal-blocks.test.ts` › «marks the text «распознано» and keeps the machine value in data-quote-source», › «shows each flag the backend emits as a Russian chip with a sentence, never the token», › «marks the portal description with the words the plan fixes»; the quoted labels are in `web/src/entities/block/model/vocabulary.ts` |
| 3 | analysis reads only the embedded text | `d9bea309` | `tests/integration/analysis/recognised/test_source_preparation_bundle.py::test_no_recognised_word_reaches_the_text_layer`, `::test_the_text_layer_of_a_bundle_is_byte_for_byte_the_text_layer_of_its_bare_pdf`; `src/auditmanager/analysis/README.md:166` ("No model looks at a crop in W55b") |
| 4 | start and re-audit are refused up front with both figures, and nothing is created | `90b11da2`, `a5a12cd6`, `77d8a4a6` | `tests/integration/runs/test_input_budget.py::test_a_start_above_the_budget_is_refused_with_both_figures`, `::test_a_reaudit_above_the_budget_is_refused_with_both_figures`, `::test_a_refused_start_creates_nothing_at_all`; `web/tests/unit/run/input-budget.test.ts` › «names the refusal and prints both figures after the catalog sentence», › «is a refusal, not an unknown outcome: the queue offers no repeat for it»; `W55B-REHEARSAL-01.md` §2.1 (500 pages: `422`, no row created) |
| 4 | no portal blocks without a run | `2f83e608` | `src/auditmanager/bootstrap/adapters.py:1113-1117` (`not_produced` when no run produced geometry); `api/routers/ports.py` `list_portal_blocks` docstring |
| 5 | the bundle is checked at upload, and a refusal names its rule. The per-rule sentence is new in W55b; before it, the panel printed the generic catalog sentence and the constraint name. | `0333d58e` | `web/tests/unit/projects/upload-failure.test.ts` › «adds the constraint sentence to the generic one and keeps the constraint name»; `upload-envelope.test.ts` › «names every refusal reason before a file is chosen»; the previous state is `4fe7615:web/src/entities/document-version/model/upload-failure.ts:97` |
| 6 | a page without text is admitted by a portal block and refused without one | `d865898b`, `24a5e81c`, `6a4b2a65` | `tests/integration/ingest/test_bundle_envelope.py::test_a_block_of_any_type_satisfies_the_rule_for_its_page`, `::test_a_page_with_neither_a_layer_nor_a_block_is_refused_with_the_bare_pdfs_sentence`; `tests/integration/analysis/recognised/test_source_preparation_bundle.py::test_a_textless_page_that_holds_a_portal_block_is_admitted_and_marked` |

## 1. Changed files (`git diff --name-only 1debd1b7..HEAD`)

```
VERSION
docs/program/W55B-RELNOTES-01.md
release-notes/0.6.0.json
tests/contract/release_notes/test_release_notes_form.py
tests/integration/releases/test_release_loader.py
```

- `VERSION`: `0.5.1` → `0.6.0`, with the same byte form (`0.6.0\n`).
- `test_release_notes_form.py`: the revision map gains `"0.6.0": 1`, and the order list is
  `["0.6.0", "0.5.1", "0.5.0", "0.4.0", "0.3.0", "0.2.0"]`. Every older version stays in both. The comment names
  `W55B-RELNOTES-01` and `R-123`.
- `test_release_loader.py`: `set(_notes())` gains `0.6.0` and keeps every older version.
- Not changed:
  - `release-notes/dictionary.json`: no new term was needed.
  - `web/tests/unit/release-notes/current-screen.test.ts`: it reads `VERSION` and pins no version.

**Pin sweep.** `tools/plan/pin_sweep.py --help` lists only the events `contract-version`, `error-code`, `migration`,
`reseal-surface`, `route` and `table`. It has no version-pin event, so I ran
`git grep -n '0\.5\.1' -- tests web/tests scripts` before the edit. It printed four hits, all in the two granted files:
`test_release_notes_form.py:144` (comment), `:147` (revision map), `:150` (order list), and
`test_release_loader.py:67` (version set). All four were updated, keeping `0.5.1`. A repo-wide
`git grep -F '0.5.1' -- ':!docs' ':!release-notes'` also prints `web/package-lock.json:1718,1719,3098`. Those are
`@swc/helpers` `0.5.15`, not release pins, and outside the grant. Nothing else reads the authored notes for a version:
`verify-acceptance.mjs`, `manual-alpha-check.sh` and `test_deployed_stack_probe.py` name `VERSION` and `release-notes/`
only as paths.

## 2. Checks

Each command ran on its own, with its exit code read directly (`cmd > log 2>&1; rc=$?`). Unless a row says otherwise, the
tree was the committed `85c51f82` and `git status --porcelain -uall` was empty. Host: load 15 to 21, available memory 2 to
3 GiB.

| Command | rc | Result |
|---|---|---|
| `git diff --check 1debd1b7..HEAD` | 0 | clean |
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/release_notes` | 0 | 23 passed |
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py` (includes `test_alpha_acceptance_command.py`) | 0 | 752 passed, 18 927 subtests passed (96 s) |
| `set -a; . ./.env; set +a; .venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/releases/test_release_loader.py` (private stack) | 0 | 12 passed |
| the same, for all of `tests/integration/releases` | 0 | 59 passed |
| `cd web && npm exec -- vitest run tests/unit/release-notes` | 0 | 1 file, 3 tests passed |

**The private stack.**

- `.env` was made from `.env.example`, with both sides consistent:
  - `FOUNDATION_INSTANCE=auditmanager-w55b-relnotes`, `POSTGRES_DB=auditmanager_w55b_relnotes`;
  - PostgreSQL `57480`, and `DATABASE_URL` on 57480;
  - S3 `61080/61081`, `S3_ENDPOINT_URL` on 61080, `S3_BUCKET=auditmanager-w55b-relnotes`.
- `make up` and `make migrate` (to `0021_portal_bundles`) both returned 0. The stack was started only once `free -g`
  showed 3 GiB available.
- Teardown:
  - `make down` returned 0.
  - `docker volume rm auditmanager-w55b-relnotes-postgres-data auditmanager-w55b-relnotes-s3-data` returned 0. These were
    the only two volumes with the compose project's name.
  - `.env` was deleted.
  - Afterwards there were 0 containers, 0 volumes and 0 networks named `relnotes`, and nothing listened on 57480, 61080
    or 61081.
- The other stack (`auditmanager-w55b-fix`, 57400/61000) was neither touched nor stopped. No process was killed.

**Can-fail proofs.** Each mutation edited the committed file. The original was saved in the session scratchpad and
copied back, and SHA-256 was compared before and after.

| Mutation | Command | rc | Result | Restored |
|---|---|---|---|---|
| `0.6.0.json` `date` → `2026-10-14` (equal to 0.5.1's) | `pytest -q tests/contract/release_notes/test_release_notes_form.py::test_authored_shape_and_form` | 1 | `AssertionError: assert {'descending_dates'} == set()` | `6accb02b…3377` before and after; `git status` empty; the release-notes suite then gave 23 passed, rc 0 |
| `0.6.0.json` item 2 `where` → «Работа › Блоки» | `cd web && npm exec -- vitest run tests/unit/release-notes` | 1 | 2 failed with `wrong display path: Работа › Блоки` | same SHA-256; vitest then gave 3 passed, rc 0 |

`test_bad_fixture_fails_named_rule` (19 named rules) passes on the new tree. Its fixtures now take 0.6.0 as the current
entry and 0.5.1 as the second.

## 3. Contracts

None new or changed. The notes follow `release-notes/schema.json` unchanged. No change touched `contracts/**`, the
OpenAPI document, the error catalog, migrations or the screen registry.

## 4. Risks and known limitations

1. **The date is `2026-10-15`, one day after today.** `descending_dates` is strict, and 0.5.1 already holds
   `2026-10-14`. The integrator may re-date the entry at publication while it is still revision 1 and not yet loaded.
   Moving it to `2026-10-14` or earlier turns the form test red; that was checked above.
2. **Item 4 reports a product gap honestly.** A version above the input budget can never be run, so it never gets portal
   blocks. Meanwhile «Блоки» tells it «Блоки портала появятся после первого запуска анализа этой версии.», which is a
   promise such a version cannot meet. The notes say plainly that such a version will not get blocks. The screen sentence
   is outside this grant, and I registered no debt. I recommend the integrator log it next to D-162 (blocks for a version
   no run can start, or a different sentence when the version is over the budget).
3. **Item 6 depends on item 3.** A page admitted only by its portal block reaches analysis with no text, because
   recognised text is not an input of analysis in W55b. The notes say both things, in items 3 and 6. Analysis of such pages
   arrives with W56's consumption of `prepared.recognised_text`.
4. **`W55B-FIX` is not described.** If FIX lands before release and adds user-visible refusals (too many blocks, an
   oversized page, "busy, retry in N s"), this entry needs revision 2 or a later integrator edit before it is loaded.
   Item 5 is worded with «например», so it does not claim a closed list.
5. **The figures are configuration-dependent.** Item 4 deliberately gives no number. The budget is derived at start-up
   from the model and the cost ceiling (152 361 characters at the $1.00 default), and the message on screen gives the real
   figures.
6. `screen` uses parameterised registry addresses (`/projects/[project_uid]`,
   `/projects/[project_uid]/versions/[version_uid]`) for the first time in authored notes. The served schema types
   `screen` as a free string, the version history renders only `where`, and the registry vitest matches these addresses
   exactly. Still, a judge may prefer `/projects` with «Работа › Проекты».
7. The independent notes judge for W55b has not yet read this entry (`RELEASE_PROCESS.md`, "Authors and review").

## 5. Integrator instructions

1. Read the diff and §0.1, then merge `agent/w55b-relnotes` into `integration/w55b`. The lane touches only the five
   paths in §1. Its only possible conflict is with another lane that moves `VERSION` or the two pins, and none is
   expected.
2. Have the W55b notes judge check each item against §0.1 on the final candidate. If `W55B-FIX` lands first, decide
   whether item 5 needs revision 2 (risk 4).
3. Re-date the entry if publication falls on another day (risk 1). If you re-date it, keep `revision: 1` only while
   the entry has never been loaded on a stand.
4. Consider registering the «Блоки» promise for over-budget versions (risk 2).
5. `origin/main`, deployment and the `v0.6.0` tag belong to `W55B-INT-MAIN-01` and need the owner's separate instruction
   naming the exact SHA (`R-123`, `AGENTS.md` §6). This lane did none of them.

## 6. Containment

`git diff --name-only 1debd1b7..HEAD` lists exactly the five paths in §1, all inside the grant:

- `release-notes/0.6.0.json`;
- `VERSION`;
- the version-set pins in `tests/contract/release_notes/test_release_notes_form.py` and
  `tests/integration/releases/test_release_loader.py`;
- this report.

Not touched:

- `release-notes/dictionary.json`, `web/tests/**`, `contracts/**`, migrations, `src/**`, `web/src/**`;
- `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `CURRENT_STATE.md`, root dependency and lock files;
- `.venv` and `web/node_modules` (shared symlinks);
- `.local/portal-exports/` (not read);
- any other worktree, refs or tags.

Nothing was pushed, merged, tagged or stashed, and no external network call was made. After this commit,
`git status --porcelain -uall` is empty.
