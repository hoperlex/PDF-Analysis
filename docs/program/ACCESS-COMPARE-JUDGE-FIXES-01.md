# ACCESS-COMPARE-JUDGE-FIXES-01 — the findings of the independent judge J4 on the access and comparison lanes

Task: [ACCESS-COMPARE-JUDGE-FIXES-01](tasks/ACCESS-COMPARE-JUDGE-FIXES-01.md) (fix lane C). Branch `agent/access-compare-judge-fixes-01`, base `93bc5037` (tip of `integration/ar-close-1026`). Written 2026-10-28. No push, no tag, no container, no network. The lane had one writer in its worktree; `git log` and `git status --short` were checked before every commit.

## Result

| # | Finding (severity) | Status | Commit |
| --- | --- | --- | --- |
| 1 | a replayed `generateComparisonSummary` always said `is_current: true` (MED) | fixed: `SummaryOutcome.is_current`, judged from the sealed evidence recomputed in the same transaction (same rule as the served read: sealed, same comparison, same revision, same seal) for a first answer, an exact repeat and a replay; the adapter carries it | `89a99f82` |
| 2 | the registration day cap locked everybody out for 24 h with no lever (MED) | fixed: only `pending` and `approved` count; a rejected request frees its place; the answer is the same `conflict` / `queue_full` for any login; the screen text names both causes, no new error code | `d189e90d` |
| 3 | the run CSV tested the first character only (LOW) | fixed: one rule in `auditmanager.shared.spreadsheet.neutralise_formula`; the proposals CSV is NOT switched (see «Integration notes») | `98967a8f` |
| 4 | preset write keys were not actor-scoped (LOW) | fixed: `actor_uid` in the create, revise and archive payloads; `startRun` has the same gap and is only reported | `e73a15fb` |
| 5 | a pair hidden by another pair's change said nothing (LOW) | fixed in the widget: a per-pair line | `7a81aed1` |
| 6 | release note item 3 quoted the wrong profile versions (MED) | fixed: revision 3; a contract test reads every `profile.json` | `84cd7c4f` |
| 7 | the manual step expected a removed label (LOW) | fixed | `56df8f5e` |
| 8 | latent items (LOW) | listed in «Limits»; not changed | — |

## What changed

1. `src/auditmanager/comparison/summaries.py`: `SummaryOutcome` gains `is_current`; the `ComparisonRequest` is built once; `_describes(stored, evidence)` is the rule. `src/auditmanager/bootstrap/adapters.py`: the summary view seam passes `outcome.is_current` (one line). Premise: at the base the replay branch returned before `sealed_evidence` and the adapter wrote `True` (P-01).
2. `src/auditmanager/access/registrations.py`: `_COUNT_ACCEPTED_IN_WINDOW` adds `status IN ('pending', 'approved')`; docstrings say so. `web/src/features/register/model/exchange.ts`: `queue_full` reads «Очередь заявок заполнена или исчерпан лимит заявок на сутки. Попробуйте позже.»
3. New `src/auditmanager/shared/spreadsheet/` (`__init__.py`, `formula_text.py`); `src/auditmanager/exports/serializer.py` imports it and keeps its public names (`FORMULA_TRIGGERS`, `FORMULA_NEUTRALISER`, `neutralise_formula`). The rule: a text cell gets one leading apostrophe when it starts with TAB, CR or LF, or when its first character after space, NBSP U+00A0, U+FEFF, U+200B to U+200D, U+2060, TAB, CR, LF is `=`, `+`, `-`, `@` or the fullwidth `＝ ＋ － ＠` (U+FF1D, U+FF0B, U+FF0D, U+FF20). Every other cell is byte-identical (the golden-row, full-file and over-a-run tests of `SMALL-HARDENING-02` pass unmodified). `shared` is an exempt target of the context-boundary test, so no deep import across bounded contexts (P-05).
4. `src/auditmanager/executors/preset_commands.py`: `"actor_uid": actor_uid` in the three fingerprinted payloads. A second administrator reusing a key with the same payload gets `idempotency_key_reuse` and nothing is written; the first one's own retry still replays.
5. `web/src/widgets/version-comparison/ui/version-comparison.tsx`: for a `verified` pair with no difference under `evidence_state` `text_changed`, the line «Различия скрыты: изменился другой подтверждённый лист. Отзовите изменённую пару и подтвердите заново.» The entity file `pairing.ts` is outside the allowed paths, so the text and the predicate live in the widget.
6. `release-notes/0.9.0.json` revision 3, item 3 (396 characters): «версии с 1.1.0 по 1.3.x» (stays true when five profiles move to 1.3.1), «В пяти разделах просят сообщать и об отсутствии записи, в категории «Документация».» The sentence «Ни человек, ни реальные документы эти инструкции для модели не проверяли.» is untouched. To stay within 400 characters the category «Внутреннее противоречие» is no longer named (the «с цитатами» and the example «итога таблицы с суммой строк» stay). Pins moved: the revision map and comment of `test_release_notes_form.py`, `RELEASES.md`, `RELEASE-0-9-0-DEV-01.md` (a new «Revision 3» section, row 3 and the result paragraph). `test_note_follows_review_switch.py` pins no revision or version and is unchanged. New `tests/contract/release_notes/test_note_profile_versions.py`.
7. `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md` step 21 expects «проверен» and says that the switch `SHOW_REVIEW_INDICATION` set to `true` restores the old text.

## Tests added or changed, and what each modified test asserted before and after

New: `tests/integration/comparison/test_comparison_summary_db.py` (+5: fresh replay, withdrawn pair, another pair approved, withdraw then approve again, redrawn sheet), `tests/unit/comparison/test_summary_view_follows_the_outcome.py` (10: the adapter seam in four combinations, the pure rule in six), `tests/integration/access/test_registration_day_cap.py` (+1), `tests/integration/api/qa_w49/test_qa_w49_queue_cap.py` (+1, over HTTP), `web/tests/unit/session/registration-queue-text.test.ts` (3), `tests/unit/exports/test_csv_formula_neutralisation.py` (+ the cases of the new rule), `tests/unit/exports/test_csv_rule_against_the_optimisation_csv.py` (33), `tests/integration/executors/test_preset_commands.py` (+3), `web/tests/unit/comparison/sheet-pairing.test.ts` (+5), `tests/contract/release_notes/test_note_profile_versions.py` (3).

| Modified test | Before | After |
| --- | --- | --- |
| `test_registration_day_cap.py::test_decided_requests_still_count_towards_the_day` (renamed `test_a_rejected_request_frees_a_place_in_the_day_and_an_approved_one_does_not`) | 40 filler rows two hours old; one rejected, one approved; the next submit is `queue_full` (every state counts) | the same rows; refused before any decision; after one approval still refused (an approved request counts); after one rejection exactly one more is accepted and the next is refused; after a second rejection one more again. Module docstring says «pending and approved» |
| `test_csv_formula_neutralisation.py::test_a_cell_that_does_not_start_with_a_trigger_keeps_its_bytes` | the list held `" =1+1"` («a leading space is not a trigger») and `"\n=1"` («a line feed is not one of the six») as cells that keep their bytes | those two entries are removed: both are neutralised now (`test_a_trigger_behind_blanks_or_invisible_characters_is_neutralised[space-equals]`, `[line_feed-equals]`, `test_a_cell_that_itself_starts_with_tab_carriage_return_or_line_feed_is_neutralised[lf]`); every other entry stays |
| `test_release_notes_form.py::test_authored_shape_and_form` | revision map `"0.9.0": 2` | `"0.9.0": 3`, comment extended |
| `test_registrations.py::test_the_queue_holds_100_and_refuses_the_101st`, `test_qa_w49_queue_cap.py::test_the_hundredth_...`, `...::test_two_applications_racing_for_the_last_place_get_one` (the three the previous lane touched) | fillers three days old | unchanged: they sit outside the 24-hour window, so the new rule does not reach them; all green |

Not modified: the golden-row test (`test_the_neutralised_bytes_of_one_row_are_exactly_these`), the byte-for-byte no-trigger row, the carriage-return quoting test, the integer and date tests, and `test_csv_formula_neutralisation_over_a_run.py`.

## Mutation tables

Each mutation edits one thing, the named test goes red, the edit is reverted; `git status --short` is empty afterwards.

### Finding 1 (`test_comparison_summary_db.py` + `test_summary_view_follows_the_outcome.py`, 27 tests)

| Mutation | Result |
| --- | --- |
| M1a a replay is always current (the old behaviour) | 4 failed (withdrawn, another pair, withdraw and approve again, redrawn sheet) |
| M1b revision not compared | 1 failed (`[revision]`) |
| M1c seal not compared | 1 failed (`[seal]`) |
| M1i comparison not compared | 1 failed (`[comparison]`) |
| M1d a missing seal does not make it old | 2 failed |
| M1j a refused comparison (`None`) not handled | 1 failed |
| M1e adapter writes `True` | 2 failed |
| M1f adapter writes `False` | 2 failed |
| M1g a first answer is never current | 1 failed |
| M1h an exact repeat under another key is never current | 1 failed |

### Finding 2 (`test_registration_day_cap.py` + `test_qa_w49_queue_cap.py`, 13 tests; web 3 tests)

| Mutation | Result |
| --- | --- |
| M2a every state counts (the old rule) | 3 failed |
| M2b only `pending` counts | 1 failed |
| M2c only `approved` counts | 7 failed |
| M2d `rejected` counts, `approved` does not | 3 failed |
| M2e the day cap removed | 7 failed |
| M2f window 25 hours | 2 failed |
| M2g off by one | 7 failed |
| M2h the web text reverted | 1 failed |

### Finding 3 (`test_csv_formula_neutralisation.py`, `test_csv_rule_against_the_optimisation_csv.py`, `test_csv_formula_neutralisation_over_a_run.py`, 261 tests)

| Mutation (in `formula_text.py`) | Result |
| --- | --- |
| skip set lacks space / NBSP / U+FEFF / U+200B / U+200C / U+200D / U+2060 | 53 / 35 / 19 / 17 / 9 / 9 / 17 failed |
| skip set lacks tab / carriage return / line feed | 16 / 16 / 17 failed |
| triggers lack `=` / `+` / `-` / `@` | 46 / 25 / 24 / 24 failed |
| triggers lack `＝` / `＋` / `－` / `＠` | 17 / 16 / 16 / 16 failed |
| control starters lack tab / carriage return / line feed | 9 / 9 / 4 failed |
| the old rule (first character only) | 123 failed |
| the scan does not stop at the first real character | 20 failed |
| the control-starter clause removed | 21 failed |
| the empty cell gets a lone apostrophe | 2 failed |
| the prefix is a space / goes after the first character | 218 / 175 failed |

A first run of «skip set lacks tab» and «lacks carriage return» survived (a leading TAB or CR is caught by the control-starter clause); the five stacked-blank cases (`' \t'`, `' \r'`, `' \n'`, NBSP+TAB, NBSP+CR) were added and both now fail.

### Finding 4 (`test_preset_commands.py`, 38 tests)

| Mutation | Result |
| --- | --- |
| create payload without the actor / revise without / archive without | 1 failed each (the matching new test) |
| create payload with a constant actor | 1 failed |

### Finding 5 (`sheet-pairing.test.ts`, 26 tests)

| Mutation | Result |
| --- | --- |
| the line for any evidence state | 2 failed |
| the line also on the changed pair | 2 failed |
| the line even where a difference is shown | 1 failed |
| the line never / always | 1 / 5 failed |
| wording changed | 1 failed |

### Finding 6 (`tests/contract/release_notes`, 29 tests)

| Mutation (in `0.9.0.json`) | Result |
| --- | --- |
| item 3 back to «версия 1.1.0 или 1.2.0» | `test_the_current_note_quotes_a_range_that_holds_every_profile_version` red |
| the range stops at 1.2.x / starts at 1.2.0 | the same, red |
| the item stops mentioning the profiles | the same, red (nothing left to judge) |
| `"revision": 3` back to 2 | `test_authored_shape_and_form` red |
| item 3 above 400 characters | `test_authored_shape_and_form` red (`text_length`) |

Finding 7 is a document; no machine check reads that step.

## Commands and counts

Private database `auditmanager_acjf01` created on the integrator's lane PostgreSQL, migrated to `0037_analysis_presets` and dropped at the end; the stack's own database was not written. `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <paths>` with the stack's `.env` variables and `DATABASE_URL` / `POSTGRES_DB` pointed at the private database. One pytest at a time.

| Paths | Result |
| --- | --- |
| `tests/unit/exports tests/unit/access tests/unit/comparison tests/unit/executors tests/unit/api` | 1259 passed |
| `tests/contract` without `test_cp00_candidate.py`, `test_validate_bootstrap.py`, `test_cp00_final_state.py` | 1191 passed, 19283 subtests passed |
| `tests/integration/access tests/integration/comparison tests/integration/exports` | 620 passed, 2 skipped |
| `tests/integration/api` | 681 passed |
| web `npx vitest run` (whole suite, once) | 208 files, 3237 tests passed |
| web `tsc --noEmit`, `eslint .` | clean |
| `git diff --check` | clean |
| governance one-liner for the task file | `[]` |

`tests/integration/exports/test_tiebreaker_is_load_bearing.py::test_the_tie_is_real_and_the_two_orders_can_differ` failed in four consecutive runs (once in a group, three alone) and passed in every later run, including one on an untouched copy of the base tree: its own comment calls the heap-order precondition «rightly flaky», and it reads only SQL. It does not touch this diff.

## Integration notes

- **Contract prose, for the contract slot (not touched here).** `submitRegistration` in `contracts/api/v1/openapi.json` and `contracts/domain/v1/state-machines.json` still describe the 100-pending cap only; the day cap now counts `pending` and `approved`. `exportRunCsv` says nothing of the apostrophe. `generateComparisonSummary` already declares `summary.is_current`; its description may say it is judged on replay too. No shape changed.
- **The proposals CSV keeps its own rule.** Adopting `neutralise_formula` there would change its bytes in two classes: blanks, then TAB/CR/LF, then nothing dangerous (`' \nx'`, `' \tx'`: neutralised today, not by the new rule) and invisible or fullwidth characters before a trigger (`NBSP=1`, `FEFF=1`, `＝1`: not neutralised today, neutralised by the new one). `test_csv_rule_against_the_optimisation_csv.py` pins the relation row by row, so neither rule can move unnoticed. If the owner wants the proposals CSV hardened too (its cells come from uploaded price lists), the change is `escape_formula = neutralise_formula` plus that test's two difference lists.
- **`startRun` key not actor-scoped** (`src/auditmanager/runs/commands.py`, the fingerprint document has no `actor_uid`): same class as finding 4, not changed here.
- **Day cap trade.** An administrator can now clear a spent day by rejecting; a flood that is rejected can be repeated at the cost of the administrator's attention and the edge's rate limit. Approved requests still count (40 accounts opened in one day is the onboarding event the cap is about).
- **Release note.** Revision 3 has not reached `main`. When the pending prompt fix moves five profiles to `1.3.1`, the note stays true («по 1.3.x») and the new contract test stays green.
- **A-10.** The sentence «Ни человек, ни реальные документы эти инструкции для модели не проверяли.» is untouched.

## Limits

- Finding 8, latent while the only model is the recorded one (cost zero, no network): (a) `web/src/entities/version-comparison/ui/comparison-summary.tsx:100` says «Будет сделан один запрос к модели…» even in recorded mode; (b) `summaries.py` `_READY_FOR` (line 141-144) finds only a `ready` row, so a `rejected` reply is paid for again under every new key; (c) `reply = self._model.complete(prompt)` (line 336) runs before `if not self._model.unmetered` (line 337) refuses, so a model with `unmetered` false is called before it is refused. All three need a decision before a metered model is connected.
- The stepped-over set is exactly the ten characters of the brief. Other Unicode spaces (U+3000, U+2000 to U+200A, U+202F, U+205F) are not skipped: `'　=1'` keeps its bytes (a test says so).
- `is_current` on a replay costs one recomputation of the sealed evidence (reads only; no lock; the pair is not locked on a replay).
- The release note no longer names the category «Внутреннее противоречие» (length); the row in `RELEASE-0-9-0-DEV-01.md` says so.

## Proof that nothing forbidden was touched

`git diff --name-only 93bc5037..HEAD` lists only the files named in the task file's allowed paths: `src/auditmanager/{access/registrations,bootstrap/adapters,comparison/summaries,executors/preset_commands,exports/serializer}.py`, `src/auditmanager/shared/spreadsheet/{__init__,formula_text}.py`, `web/src/{features/register/model/exchange.ts,widgets/version-comparison/ui/version-comparison.tsx}`, `release-notes/0.9.0.json`, the tests above, and the four docs. No `contracts/**`, `web/openapi/**`, generated client, `db/migrations/**`, `infra/**`, `runs/**`, `analysis/**`, section package, `optimisation/proposals/export.py` or composition root.
