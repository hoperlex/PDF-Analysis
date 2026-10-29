# CMP-VC-SPEC-01 — specifications of a version comparison: positions by GOST 21.110 (part A) and the whole-specification comparison on the AI-job core (part B)

Written 2026-10-29 by the Sonnet lane `CMP-VC-SPEC-01` (branch `agent/cmp-vc-spec-01`, base `901914a5` on `integration/compare-modules`, plus one merge of the AI-job core `0f6a008d` that the integrator allowed; nothing pushed, nothing merged into another branch). Task file: [`tasks/CMP-VC-SPEC-01.md`](tasks/CMP-VC-SPEC-01.md). Decisions cited are those of [`ADR-0025`](../architecture/adr/ADR-0025-comparison-modules.md) (decisions 3, 4, 10, 11, 12, 14, 15, 16, 17 to 23 and both addenda); the seal is [`CMP-SEAL-C2.md`](CMP-SEAL-C2.md) (sections 3, 4, 8, 9, 10); the wave brief is [`dispatch/CMP-WAVE-C2.md`](dispatch/CMP-WAVE-C2.md) section 1; the core is [`CMP-AI-JOBS-01.md`](CMP-AI-JOBS-01.md) section 2. The original is PDF-proverka at commit `23f379fd`, read from `https://raw.githubusercontent.com/SU10KAZ/PDF-proverka/23f379fd/<path>` into a scratch directory outside git (the inventory named `specification_*.py` unread); `file:N` below is that copy's line N.

## 1. Result

All eight operations of the lane answer instead of `503`:

| operation | served by | what it reads or does |
| --- | --- | --- |
| `getVersionPageSpecPositions` | `SpecificationReader.page_view` | part A: whether a page is a specification sheet and its positions, from the page profile's words, vector lines and stamp zone; no model |
| `getComparisonSheetPairSpecPositions` | `SpecificationReader.pair_view` | part A: the changes that fall on the pages of a pair, from the stream of positions of **each whole version** (a page move is not a change) |
| `listComparisonSpecifications` | `SpecificationService` | per transition that has a specification: method, sheets A/B, coverage, totals, reason |
| `getComparisonSpecification` | `SpecificationService` | one transition: state, phase, coverage, totals, reason, job and extraction ids |
| `listComparisonSpecificationChanges` | `SpecificationService` | the stored changes in the order changed, removed, added, unclear, renumbered, moved; `kind` filter, offset cursor |
| `estimateComparisonSpecification` | `ComparisonAiJobService.estimate` over `SpecMethod` | one request per side not stored; a stored side is `reused`; no image |
| `startComparisonSpecification` | `ComparisonAiJobService.start` over `SpecMethod` | keyed, expert's act, consent; writes the job (core), the transition's comparison row and one `comparison_spec` work item |
| `cancelComparisonSpecification` | `ComparisonAiJobService.cancel` + `SpecificationService.close_cancelled` | cancels the job and the transition's row |

The engine's channel `spec_positions` is `checked` with the number of position differences when both pages of a specification pair yield positions; `ALGO_VERSION` is `cmp-engine/4`. Every call of a model goes through `ComparisonModelCaller` (the spend journal row is `prepared` before the request); every test runs in recorded mode.

**Not done, and why** (section 9): the worker cannot bind a live executor connection (`WorkDependencies` carries no key ring, so the shipped binder refuses with `executor_route_missing` and nothing is ever sent by it); the three contract gaps and the core gap of section 9 are FIX items.

## 2. Base facts, printed before any edit

`contract 1.11.0 176 paths 198 operations 517 schemas`, `VERSION 0.9.0`, head `0040_comparison_ai_reports`, base `901914a5520a2d90b22b0c5c3fcdae1fa3f6e438` (`P-01` of the task file). They equal the brief, so the lane went on. The lane changed no contract, no migration, no dependency and no lock file.

## 3. What was built

`src/auditmanager/comparison/specification/` (new):

| file | what it holds |
| --- | --- |
| `table.py` (pure, standard library only) | the parser of a specification page (header, columns by vertical rules, rows by horizontal rules, row type by filled cells) and the stream of positions across pages |
| `diff.py` (pure) | the order-independent comparison of two streams of positions (part A and the compare of a page pair) |
| `views.py` | contract-shaped dictionaries: positions (cut at the contract's bound with an ellipsis), changes, page view, pair view |
| `reader.py` | `SpecificationReader`: the two part-A reads and `version_stream` (the specification pages of a version, read once each) |
| `source.py` (pure) | the numbered text a model reads: one block per specification page, absolute line numbers, a repeated header, a plain line for a title across the table, the 140 000-character cap |
| `prompt.py` (pure) | the rules and the closed schema of the model's answer, the request digest, `content_key(project, source digest, prompt version)` |
| `check.py` (pure) | the program's check of the answer (coverage, exact quotes, grounded values, no hidden rows), the coverage the contract carries and the reason of an incomplete side |
| `whole.py` (pure) | the order-independent comparison of two checked specifications and the changes in the contract's kinds |
| `repository.py` | the statements of `comparison_spec_extraction` (immutable, content-keyed) and `comparison_spec_comparison` |
| `transition.py` | `prepare_side` / `read_side` (the store first, one request only if nothing is stored, an answer that failed the check is kept), `compare_sides`, `TransitionRun` |
| `service.py` | the three reads of part B; a transition whose two readings are stored is read without a job |
| `method.py` | `SpecMethod` (the core's `AiMethod`), `SpecHandler` (kind `comparison_spec`), `build_request`, the shipped `unbound_binder` |

Outside the package, inside the allowed paths: `engine/child/job.py` (`spec_positions_channel`), `engine/child/program.py` (loads the two pure modules by path as `_amc_spec`, the way it loads the mask codec), `engine/child/settings.py` (`ALGO_VERSION` `cmp-engine/4`); `bootstrap/adapters.py` (the body of `ComparisonSpecificationAdapter`), `bootstrap/composition.py` (its one constructor line, now two physical lines), `comparison/public.py` (appends of this lane's names and `spec_handler` in `HANDLER_FACTORIES`), `scripts/recovery/grant_classification.py` (`comparison_spec_extraction`, `comparison_spec_comparison` leave `SEALED_NOT_YET_WRITTEN`), and the registers named in section 8.

### 3.1 The original's rules and prompts that were ported (file:line of the original)

| what | where in the original | where here |
| --- | --- | --- |
| a specification page is a table by GOST 21.110, columns by the vertical rules of the header, rows by the horizontal rules, the row type by the filled cells and not by the number, an unclear boundary is flagged and never guessed | `spec.py:1-21`, `:237-246` | `table.py` |
| the nine fields, the header keys, the size pattern, the key of a comparison (`norm`, `quantity`) | `spec.py:38-57` | `table.py` (`FIELDS`, `HEADER_KEYS`, `SIZE_RE`, `norm`, `quantity`) |
| vertical and horizontal rules of a page | `spec.py:62-83` | `table.segments` (from the profile's lines instead of `get_drawings`) |
| the header: «Поз.» and «Наименование» on one line in the upper 30 %, at least five of nine columns named | `spec.py:96-112` | `table.find_header` |
| the columns between the vertical rules that cross the header; no `name` and no quantity or unit column is no table | `spec.py:115-143` | `table.find_columns` |
| the rows: rules covering half the table, the title block cut out, a merged cell is a section title, the row of column numbers is skipped | `spec.py:146-232` | `table.parse_page` |
| the stream: parent and sub-rows, continuation of a phrase, sub-titles, a sub-row at the top of a page belongs to the last parent, a boundary at a page break that is not obvious is `ambiguous` | `spec.py:249-325` | `table.assemble` |
| the stamp test of a specification sheet | `spec.py:380-396` (its converse) and `stamp.py:190-204` as the engine ports it | `table.is_spec_stamp` |
| three passes of matching (key, rename or other mark with similarity 0.8, same name unit and section), `changed` / `renumbered` / `unclear` / `removed` / `added`, the order of the list | `spec.py:405-536`, `:568-571` | `diff.py` (indexed, so thousands of rows are not quadratic) |
| the channel `spec_positions`: `checked(0)` when graphics, colour and text agree | `engine.py:995-1000` | `job.spec_positions_channel` |
| ambiguous boundary leaves the channel unchecked; only changed, added and removed count | `jobs.py:801-815`, `:855-864` | `job.spec_positions_channel` (the cross-page ambiguity is the version-wide read's) |
| the packet is the authoritative text, a hole in it is a hole in the answer, not an empty specification; the size cap; a version that cannot be read whole is described by the sheet AI | `docs/whole_specification_comparison.md:18-21`, `:121-123`, `:362-371`; `specification_run.py:24` | `source.py`, `transition.py`, `service.py` |
| the rules of the request (RULES 1 to 7) | `specification_run.py:27-53` | `prompt.RULES` |
| the closed schema of the answer | `specification_source.py:34-83` | `prompt.extraction_schema` (`quantity` for `qty`) |
| the strict check: exact substring quotes, grounded values (numeric-safe), grounded section and parent, one claim per line, ignored lines only when the text bears them out, every data row extracted, every non-blank line accounted for, one issue makes the side incomplete and yields no row | `specification_source.py:299-611`, `docs/whole_specification_comparison.md:33-35` | `check.py` |
| the store of answers is by what was asked, a stored answer is checked again and not paid for twice | `docs/whole_specification_comparison.md:70-74` | `transition.read_side` |
| order-independent comparison: identical records cancel (multiplicity), unambiguous identities by tier, a name match with two codes is a substitution, moved between sections, shared identities stay `unclear`, additions and removals only from a complete comparison, renamed section titles | `specification_compare.py:75-107`, `:192-226`, `:233-285`, `:316-487`, `:619-641`, `docs/whole_specification_comparison.md:36-40` | `whole.py` |
| the sentences («Добавлено: не было → …», «Удалено: … → отсутствует», «Перенесено без изменения: раздел …», «Заголовок группы изменён …», «Несколько строк имеют общие признаки …») | `specification_compare.py:588-652`, `:425` | `diff.render_text`, `whole.changes_of` |

**Deliberately different from the original**: the profile has no font weight, so a bold title is not recognised (`bold` is always false; a title is a merged or a centred row); the band flaw of `spec.py:159` (the header's bottom was the lowest word of a band around the labels, which dropped the first row of a compact form) is replaced by *the first row rule below the label line*; `norm` maps the Latin look-alikes **before** lowering the case (`spec.py:52` lowers first, after which `B`, `H`, `K`, `M`, `T` can no longer match); `separation.separate` (the release mark and the QR over the table) is not applied, since the profile has no such separation; `spec.py`'s `_totals` (sums by mark) and `moved_between_pages` have no counterpart in the contract and are not built; the structure mode (`specification_structure.py`, `specification_portions.py`, `specification_inherit.py`, `specification_reconcile.py`) is **not ported**, only the full-extraction mode with quotes, which is what the strict check judges; `unresolved_groups` of a partial markup therefore do not exist and a side is complete or not.

## 4. Corpus results against the answer keys

Oracle: `fixtures/comparison/vs1/answer_key.json`, V4 to V5, sheet E07 (page 6 of V4, page 7 of V5): position 7 added, position 6 removed, quantity of position 3 from 2 to 3.

* **The parser reads the key's tables.** The positions of V5 page 7 read through the real page profile (`cmp-profile/3`) are exactly `positions_after` of the key (`pos`, `designation` as `mark`, `name`, `quantity`, `mass`: six positions), V4 page 6 `positions_before`; the title line «Примечание: масса единицы указана справочно.» is a section, not a position (`test_the_positions_of_a_specification_page_are_those_of_the_key`).
* **The engine channel.** V4 to V5 E07: `spec_positions` is `{"state": "checked", "diffs": 3}`, no reason `UNCHECKED_CHANNEL_SPEC_POSITIONS`, status equal to the key's; V3 to V4 E07 is `checked(0)`; a sheet that is not a specification is `not_applicable`. The named disagreement `("V4->V5", "E07", "spec_positions")` is removed from `tests/unit/comparison/engine/test_against_the_answer_keys.py` (the test fails if it comes back: `the named disagreement is gone`).
* **The sheet-pair read** (version-wide stream): totals `{changed 1, added 1, removed 1, unclear 0, renumbered 0, moved 0}`, changes in the order changed, removed, added; `changed` has the field `quantity` was `2` now `3`, `old.pos` `3`, `removed.old.pos` `6`, `added.new.pos` `7`, page references to the right versions.
* **Part B, recorded.** The whole path (the real parser, the real packet, a recorded careful model, the real check, the real comparison, the database) gives the same three changes for the transition V4 to V5, with coverage `{blocks_total 1, blocks_covered 1, rows_total 6, rows_unresolved 0}` on each side; V3 and V4 have the same specification text, so they share one stored reading and the second transition sends nothing.

## 5. Safety proofs (mutation)

Each: the file changed, the named guard run **red**, the file restored with `git checkout`, the same guard run **green**, `git status --porcelain` empty afterwards (a driver kept outside the repository; the tree was clean for every row). Counts are the guard files' own at the time.

| # | mutation | guard | red | restored |
| --- | --- | --- | --- | --- |
| M1 | `spec_positions` counts a side with no positions as an empty side (**checked only when both sides have positions**) — `engine/child/job.py` | `tests/unit/comparison/engine/test_spec_positions_channel.py` | 4 failed, 7 passed | 11 passed |
| M2 | an evidence quote need not be a substring of its line (**a quote not found is never a confirmed change**) — `specification/check.py` | `test_source_and_check.py`, `test_part_b_whole.py` | 2 failed, 19 passed | 21 passed |
| M3 | the stored extraction is not looked up before the request (**a stored extraction is re-requested**) — `specification/transition.py` | `test_part_b_whole.py` | 3 failed, 5 passed | 8 passed |
| M4a | `getVersionPageSpecPositions` skips the **module gate** — `bootstrap/adapters.py` | `test_part_a_over_http.py` | 1 failed, 4 passed | 5 passed |
| M4b | `startComparisonSpecification` (an AI command) skips the module gate | `test_part_b_job_over_http.py` | 1 failed, 6 passed | 7 passed |
| M18 | `estimateComparisonSpecification` skips the module gate | `test_part_b_job_over_http.py` | 1 failed, 6 passed | 7 passed |
| M5 | the **expert role**: `startComparisonSpecification` opened to an administrator — `api/security.py` | `test_comparison_ai_stub_operations.py`, `test_part_b_job_over_http.py` | 1 failed, 181 passed | 182 passed |
| M6 | the **key**: `startComparisonSpecification` takes an optional key — `api/routers/comparison_specification.py` | the same two | 3 failed, 179 passed | 182 passed |
| M14 | the **key replay**: the start is keyed anew on every request — `bootstrap/adapters.py` | `test_part_b_job_over_http.py` | 1 failed, 6 passed | 7 passed |
| M15 | the **consent**: an unconfirmed consent is taken as confirmed | `test_part_b_job_over_http.py` | 1 failed, 6 passed | 7 passed |
| M16 | the handler sends although the job is paused or cancelled — `specification/method.py` | `test_part_b_job.py` | 4 failed, 7 passed | 11 passed |
| M19 | the handler writes the comparison without proving in the writing transaction that the job still runs | `test_part_b_job.py` | 1 failed, 10 passed | 11 passed |
| M17 | a cancelled job leaves the transition's row running | `test_part_b_job_over_http.py` | 1 failed, 6 passed | 7 passed |
| M13 | an answer that failed the check is not kept under the key (**it would be paid for again**) | `test_part_b_whole.py` | 1 failed, 7 passed | 8 passed |
| M7 | the first row under the header is dropped (the original's band flaw) — `table.py` | `test_table_parser.py`, the channel test | 11 failed, 21 passed | 32 passed |
| M8 | positions are matched by their place and not by what they are — `diff.py` | `test_diff.py` | 4 failed, 12 passed | 16 passed |
| M9 | a stream with a hole (a specification page whose table was not read) still claims removals — `reader.py` | `test_part_a_reads.py` | 1 failed, 9 passed | 10 passed |
| M10 | additions and removals are published from an incomplete comparison — `whole.py` | `test_whole_compare.py` | 1 failed, 10 passed | 11 passed |
| M11 | `ALGO_VERSION` back to `cmp-engine/3` | channel test, `test_key_and_outcome.py` | 2 failed, 30 passed | 32 passed |
| M12 | a number is confirmed inside a longer number (`numeric_safe` off) — `check.py` | `test_source_and_check.py` | 1 failed, 12 passed | 13 passed |

**Two guards that were green under their mutation, found and fixed.** M9's first guard monkeypatched the pair's own page, which an earlier check caught, so the stream-hole rule was never reached; it stayed green (`9 passed`). A second test puts the hole on a page that is not the pair's own (`test_nothing_is_claimed_over_a_stream_with_a_hole_that_is_not_the_pairs_own_page`) and M9 is red. M13 was first written as "the state column says complete" which changes nothing observable; it is now "the failed answer is stored under another key", red in `test_an_answer_that_failed_the_check_is_kept_and_not_paid_for_twice`. M19 stayed green until a test cancelled the job *during* the last request (`test_a_job_cancelled_while_the_last_request_is_in_flight_records_nothing`).

The AI commands' role, key and module-gate guards are shown red on the commands of this lane (M4b to M6, M14, M15, M18). The seal's own M1 to M14 (`CMP-SEAL-C2.md` section 7) are unchanged and still cover the stubs of the other lanes.

## 6. Commands and results

All Python commands: worktree `.venv/bin/python`, `PYTHONPATH=$PWD/src`, `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent`, `--basetemp=/tmp/pytest-cmp-vc-spec-01/<run>` (outside the repository, removed after each run), the lane's `.env` loaded (`set -a; . ./.env; set +a`) for integration. `df -h /` before each long run: 8.2 to 9.2 GiB free, never below the 2.0 GiB line. The lane's containers `auditmanager-cmp-vc-spec-01-{postgres,s3,s3-init}-1` on 57950 / 61950 / 61951; the stack was brought down and its two volumes removed by exact name once to give the spend suite an empty day (section 9, item 7), and brought up again after a restart of the tool.

| check | command | result |
| --- | --- | --- |
| whitespace | `git diff --check 901914a5..HEAD` | exit 0, no output |
| unit, pure modules and views | `pytest -q tests/unit/comparison/specification` | 66 passed |
| unit, engine channel | `pytest -q tests/unit/comparison/engine` | 302 passed (the channel's 11, the key test, the answer-key test, the handler pin) |
| integration, the lane | `pytest -xq tests/integration/comparison/specification` | 49 passed, 1 warning on the integrator's merged tree; 35.43 s |
| integration, the comparison directory in **one process** | `pytest -q tests/integration/comparison` | Wave C2 integration check after the remaining method lanes merge |
| integration, the whole composition directory | `pytest -q tests/integration/composition` | Wave C2 integration check after the remaining method lanes merge |
| `tests/unit` + `tests/contract` minus the three `D-220` files, after the last code commit | `pytest -q tests/unit tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_validate_bootstrap.py --ignore=tests/contract/test_cp00_final_state.py` | Wave C2 integration check after the remaining method lanes merge |
| recovery pins | `pytest -q tests/integration/recovery/test_grant_classification.py` | passed in the run that touched `SEALED_NOT_YET_WRITTEN` (242 passed with the three composition files) |

## 7. Safety rules of ADR-0025 where they touch this lane

* **No hidden change (decision 20), AI output is never the expert's decision.** The model reads text; the program confirms every value by an exact quote (`check.py`); an unconfirmed answer yields no row, the comparison is `incomplete` and publishes no addition, removal or claim of "no change". Raw evidence is never rewritten: the part-A positions are read from the profile and compared deterministically. Every text a model answer produced is in a comparison whose description in the contract carries "not confirmed by an engineer".
* **Spend before the call (decisions 10, 11).** The handler asks only through `ComparisonModelCaller`; a refusal that pauses the job pauses it through the core; a reply that takes the job over a ceiling is kept and stored and the job pauses before the next request. A recorded process journals `unmetered`.
* **Content-keyed answers never re-sent (rule 5, decision 15).** The key is `sha256{project, prompt version, source digest}`; a stored reading is used whether complete or not.
* **The module gate (decision 23, `A-12`).** `_require_versions_module()` is the first statement of every wired method; the core checks again in the transaction. No image is sent (the packet is text).
* **Expert acts (decision 16).** Start and cancel are the expert's, keyed; an administrator is refused at the edge and again by the core.

## 8. Wiring (the hunks other lanes will also edit)

* `bootstrap/adapters.py`: the body of `ComparisonSpecificationAdapter` only (the module-flag refusal kept as the first statement of every method).
* `bootstrap/composition.py`: the one constructor line of that adapter (`sessions, blob_store=store, comparison_modules=..., provider_mode=_provenance_mode(resolved.provider_mode)`).
* `comparison/public.py`: an import block and the names of the lane at the end of `__all__`, and `spec_handler` at the end of `HANDLER_FACTORIES`.
* `scripts/recovery/grant_classification.py`: the two tables leave `SEALED_NOT_YET_WRITTEN`.
* `tests/integration/composition/test_router_answers.py` (`SEALED_STUB_GETS`: the four paths), `test_an_absent_parent_is_not_an_empty_page.py` (`SEALED_STUB_ADDRESSED`: the six reads), `test_comparison_ai_stub_operations.py` (`WIRED`: the eight operations, and the bounds test now expects `404` for the two served lists), `tests/unit/comparison/engine/test_handler_unit.py` (the kind `comparison_spec` in the shipped tuple).
* **A hunk every C2 lane needs and the integrator should keep once:** the `app` fixtures of `test_an_absent_parent_is_not_an_empty_page.py` and `test_router_answers.py` now serve the versions module (`"AUDITMANAGER_COMPARISON_MODULES": "versions"`). A wired C2 read refuses first while the module is off (`CMP-SEAL-C2.md` section 8), so the sweeps that ask every `GET` for its answer to an identity that names nothing would otherwise read `503 comparison_modules` for every wired operation. The text of the hunk is the same in both files for every lane, so a textual conflict resolves by keeping one copy.

## 9. Limits, risks and FIX items

**FIX items (none blocks the merge of this lane):**

1. **The live binding of a routed connection is the composition root's, and is missing.** `WorkDependencies` (`comparison/work/**`) carries no key ring and no destination policy, so a handler factory cannot call `bind_connection`. `SpecHandler` takes a `binder(session, job) -> CallRoute`; the shipped one refuses with `executor_route_missing` (`Failed(retry=True)`), so the worker never sends. The four AI lanes need the same seam; one owner should add it (a `ModelGateway` or a binder in the bundle, built in `build_comparison_work`) and pass it to the four handlers. Tests bind `RecordedAnswers`.
2. **The core cannot complete a single-item job from its handler.** `complete_if_drained` counts the calling item as live (`terminal_at IS NULL`), so it answers `False` for the last item. `SpecHandler._complete` falls back to `jobs._repo.move(...)` (a private member of the core). The core should take the calling item out of the count (`complete_if_drained(session, job_id, excluding_work_id=...)`) or end the job in the queue's terminal hook.
3. **Two contract gaps in part A.** `ComparisonSpecPage` and `ComparisonSheetPairSpecPositions` have no member for the reason a table was not read: a page whose header is found and whose table is not read is `is_specification: true` with no positions, and a pair over a stream with a hole lists no change, silently. An additive optional `reason` (`SPEC_NOT_PARSED`) on both would let the screen say so. `ComparisonSpecState` has no `queued`: a queued job reads `running` with phase `preparing`.
4. **The profile has no font weight.** A bold, left-aligned title directly after a parent without children is read as a continuation of the parent's name (the original used the font flag). An additive flag on the profile's words (the profile owner) would restore the rule; the packet the model reads shows such a line as a plain line, which the model can classify.
5. **The release mark and the QR over a table** are not separated before reading (the profile has no such separation); words of a mark over the table would be read as cells. The check of part B turns such a case into an incomplete side, never into a claim.
6. **The structure mode of the original is not ported** (see 3.1): an answer that fails the check makes the whole side incomplete, where the original's partial markup could keep the groups that passed. A large specification (over 140 000 characters) is incomplete and is described by the sheet AI.
7. **A recorded request is journalled in the append-only `comparison_model_call`, which the spend suite's `clean_day` check cannot tolerate from another project.** The tests of the handler therefore run in a rolled-back, savepoint-joined transaction (`iso`), and the lane's database was reset once after the first full run found 82 journalled rows. Any lane whose tests journal a call must do the same (or the whole `tests/integration/comparison` directory reds in the spend suite).
8. **`comparison_spec_extraction.state = 'partial'`** holds an answer that failed the check (no positions; the issues and the reason are in `coverage`, beyond the four keys the contract carries). The name suggests partial rows; the table has no other state to use. The failed answer is kept so it is not paid for again; a changed prompt version or text is a new key. There is no way to ask again for the same text under the same prompt: a deliberate "retry" would need a new prompt version, or a column.
9. **Positions in the contract are cut at the contract's bounds** (name 400, mark 200, note 400, ...) with an ellipsis; the stored extraction keeps the full value.
10. **The page-local channel and the version-wide read can differ** for a specification that spans pages: the engine channel compares the two pages alone (a position moved from page 1 to page 2 shows as removed on one and added on the other, beside the graphics difference that already makes the pair `different`); `getComparisonSheetPairSpecPositions` is the answer that sees the stream.
11. **A specification sheet is found by its title block for the counts and the version-wide stream** (`is_spec_stamp`: the designation ends in «СО» or the title says «Спецификация»), then confirmed by the header; a specification with neither in its stamp is not counted. The page-level read and the engine channel use the header alone.
12. **`SpecificationService.list_specifications` opens the archives of the spec pages of both versions of each transition that has no row** (to see whether both readings are stored); a series of dozens of transitions pays for it on every list. A cache keyed by the profile content keys would remove it.

**Limits.** Live money paths of the handler (a ceiling mid-job, the ×1.2 pause) are the spend wrapper's and the core's, covered there; the handler's own branch (`result.pause` → `pause_for_spend`, then no further request) is not exercised by a test. The estimate's output size (`600 + 160 tokens` a line, at most 32 000) is `[own design]`; the overrun pause measures the truth. No live model call was made.

## 10. Notes for the next lanes

* **`CMP-VC-REPORT-01`.** The series summary can take, per transition, the stored changes of `comparison_spec_comparison` (source `whole`, state `completed`, `changes` in the contract's shape) and, for a transition with both readings stored and no row, `SpecificationService.get_specification` / `list_changes` (computed on the read). A transition `incomplete` reads «листовой ИИ»: the sheet descriptions cover it; do not print its changes. `totals.moved` and `totals.renumbered` are not changes.
* **`CMP-VC-QUEUE-01`.** The AI step «спецификации» starts with `ComparisonAiJobService.start` and the scope `spec_scope(project, document, transition)` (`method.py`); its estimate is `estimate`; a transition with nothing to send answers `409 comparison_ai_nothing_to_do` (and may already be readable). The handler needs the live binder of FIX item 1 before the queue can run it for real.
* **`CMP-VC-UI-02`.** The block «Полные спецификации (СО)» reads `listComparisonSpecifications` (method, sheets, coverage, totals «изменено / +добавлено / −удалено / ?неясно», reason); the viewer's «Спецификация по позициям» reads `getComparisonSheetPairSpecPositions` (deterministic, no consent); the reasons of an incomplete side are `SPEC_NOT_PARSED`, `SPEC_SOURCE_INCOMPLETE` and `SPEC_ANSWER_UNCONFIRMED`; a comparison text is model output and carries the unconfirmed label; `kind` `changed` with the field `section` and no `old` / `new` is a renamed section title.
* **Merge order** (brief section 3): after AI-JOBS (which this branch already contains by the allowed merge `35910615`; the integrator takes this branch and the merge commit is redundant), before AIPAIR, AISHEET, REPORT. The shared hunks are in section 8.

## 11. Resources and proof that the forbidden hotspots were not touched

`git diff --name-only 901914a5..HEAD` outside this lane's own paths and the allowed wiring hunks lists only the merge of the core (`comparison/ai_jobs/**`, `docs/program/CMP-AI-JOBS-01.md`, its task file, `public.py`, `grant_classification.py`, `tests/integration/comparison/ai_jobs/**`, which are the integrator's merge). No contract, migration, dependency, lock file, `web/**`, `infra/**`, `comparison/{profile,matrix,tiles,series,work,spend}/**` or `executors/**` file is in the diff; `engine/**` holds the channel, `program.py`'s loading of the two pure modules and `ALGO_VERSION` only. `src/auditmanager/optimisation/**` (the Form-7 extractor) is not used.

Containers `auditmanager-cmp-vc-spec-01-{postgres,s3,s3-init}-1` and the network were removed with `make down`; the volumes `auditmanager-cmp-vc-spec-01-postgres-data` and `auditmanager-cmp-vc-spec-01-s3-data` were removed by those exact names; the git-ignored `.env` and the basetemp directories were deleted. No process was killed by a pattern: the two test processes that were ended (a superseded composition run after the merge) were identified by their command line and ended by PID.
