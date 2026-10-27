# Task SECTION-JUDGE-FIXES-01 — the fixes for the independent judge J2's findings on the section-analysis path

task_id: SECTION-JUDGE-FIXES-01
status: completed in development candidate

## Outcome

The five defects the read-only judge J2 found at `93bc5037` in the section-analysis path are fixed, each with a test that fails first and a mutation proof. (1) The omission check proves an absence over every page the model was shown except the pages of the naming quote, not only over the range the model chose, and refuses a claim that ends on the last page of a window that is not the last one; the sentence the stage appends names the pages that were searched. (2) The presence test reads the spellings a drawing set really contains (Latin look-alikes of Cyrillic letters, the decimal comma, the separators of a mark, the diameter sign, combining marks, the Roman numeral one). (3) The prompts of `AI TX EOM SS ITP` no longer say there is no third category while the schema allows `documentation` (`profile_version` `1.3.1`, five recordings rebuilt, sentence-guard table extended by its builder). (4) The check is given the version's `textless_pages` and the recognised text. (5) The one-call budget and the window size subtract the run's own system prompt and schema. (6, optional) A finding text that says the item is absent from the project or required is refused. No contract change, no migration, no web, no infra, no AR v3.

## Depends on

- `SECTION-CATEGORY-OCR-01` — completed; the omission check, the per-profile categories and the recognised-text context this lane corrects.
- `SECTION-CHUNKED-ANALYSIS-01` — completed; the window primitives and the one-call budget this lane makes bundle-aware.
- `SECTION-PROMPT-SENTENCE-GUARD-01`, `SECTION-PROMPT-TOKEN-GUARD-01`, `SECTION-RECORDINGS-01` — completed; the fragment table and its builder, the token guard and the recordings builder.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.8.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: unchanged (`analysis.text_observations` keeps its shape; the new stage metrics are additive scalar keys)
- migration head: `0037_analysis_presets`, unchanged (no migration)
- base commit: `93bc5037` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No route, screen, error code, migration or section is added or removed. The closed reason vocabulary of the omission check (seven reasons, now twelve) is a constant of `omission.py` and a pinned test (`test_the_reasons_are_the_closed_vocabulary_the_stage_counts`), not a maintained set of the product.

## Captured premise evidence
- premise: the judge's findings hold at the base (P-01 to P-11); the premise differences that change a deliverable are: (1) the start-time budget check in `runs/commands.py` and the settings check in `bootstrap/settings.py` call `input_budget_characters` with the deployment's one figure and no section is known there, so finding 5 is closed where a run is planned (`text_window_policy`, called by the executor with the profile's bundle) and the start-time check is left as a stated follow-up outside this lane's paths; (2) the wider OCR scope: the brief names the recognised text of a range page, the lane applies it to every searched page, as finding 1 does for the text layer.

### P-01 — the base and the branch
- captured_at: 2026-10-28
- command: `git rev-parse --abbrev-ref HEAD; git rev-parse 93bc5037 | cut -c1-12; git log -1 --format=%s 93bc5037 | cut -c1-70`
- captured_output:
  ```text
  agent/section-judge-fixes-01
  93bc5037a564
  docs(rulings): R-146bd standing disk maintenance
  ```
- interpretation: the branch exists and starts at the base the brief names (`93bc5037`, tip of `integration/ar-close-1026` at launch).

### P-02 — the omission check as it stood: the range-only search, the old view, the signature without textless pages or recognised text
- captured_at: 2026-10-28
- command: `git grep -n "def decide\|    visible: \|if visible is not None\|    if occurs(claim.term\|^_LOOSE\|^USABLE_PAGE_CHARACTERS" 93bc5037 -- src/auditmanager/analysis/text/omission.py | cut -c10-170`
- captured_output:
  ```text
  src/auditmanager/analysis/text/omission.py:47:USABLE_PAGE_CHARACTERS: Final[int] = 50
  src/auditmanager/analysis/text/omission.py:78:_LOOSE = re.compile(r"[\s\-]+")
  src/auditmanager/analysis/text/omission.py:151:def decide(
  src/auditmanager/analysis/text/omission.py:155:    visible: tuple[int, int] | None,
  src/auditmanager/analysis/text/omission.py:180:    if visible is not None and not (visible[0] <= claim.first_page and claim.last_page <= visible[1]):
  src/auditmanager/analysis/text/omission.py:195:    if occurs(claim.term, [page.text for page in in_range]):
  ```
- interpretation: `decide` takes `visible` and nothing about the version's text-less pages or recognised text (finding 4); the only absence test is `occurs` over `in_range` (line 195, finding 1); the loose view strips whitespace and hyphens only (line 78, finding 2).

### P-03 — the three contradictory sentences in the five prompts, with the judge's line numbers
- captured_at: 2026-10-28
- command: `for c in ai tx eom ss itp; do git show 93bc5037:src/auditmanager/analysis/text/profiles/$c/system_prompt.md | grep -n "Ровно две категории\|одну из двух категорий\|строго одно из двух" | sed "s/^/$c:/"; done`
- captured_output:
  ```text
  ai:12:Ровно две категории, третьей нет:
  ai:20:находок; сообщай только то, что подпадает под одну из двух категорий выше:
  ai:94:- category — строго одно из двух значений выше.
  tx:12:Ровно две категории, третьей нет:
  tx:20:находок; сообщай только то, что подпадает под одну из двух категорий выше:
  tx:132:- category — строго одно из двух значений выше.
  eom:12:Ровно две категории, третьей нет:
  eom:20:находок; сообщай только то, что подпадает под одну из двух категорий выше:
  eom:114:- category — строго одно из двух значений выше.
  ss:12:Ровно две категории, третьей нет:
  ss:20:находок; сообщай только то, что подпадает под одну из двух категорий выше:
  ss:139:- category — строго одно из двух значений выше.
  itp:12:Ровно две категории, третьей нет:
  itp:20:находок; сообщай только то, что подпадает под одну из двух категорий выше:
  itp:135:- category — строго одно из двух значений выше.
  ```
- interpretation: lines 12, 20 and 94 / 132 / 114 / 139 / 135 are exactly the judge's: fifteen occurrences, three per prompt (finding 3).

### P-04 — the callers of `decide`: neither passes the version's text-less list or the recognised text
- captured_at: 2026-10-28
- command: `git grep -n "decide(\|textless_pages" 93bc5037 -- src/auditmanager/analysis/text/stage.py src/auditmanager/analysis/text/windowed.py | cut -c10-160`
- captured_output:
  ```text
  src/auditmanager/analysis/text/stage.py:189:            decision = decide(text_layer, proposal, resolutions, visible=None)
  src/auditmanager/analysis/text/windowed.py:235:                decision = decide(
  ```
- interpretation: two call sites, no `textless_pages` anywhere in the two files (finding 4); `runs/executor.py` holds the version's list (`textless_pages` parameter, line 483) and hands it to the recognised-text loader only.

### P-05 — where the budget takes its fixed term
- captured_at: 2026-10-28
- command: `git grep -n "_fixed_prompt_characters\|AR_TEXT_PROMPT_BUNDLE" 93bc5037 -- src/auditmanager/analysis/text/budget.py src/auditmanager/analysis/text/windows.py | cut -c10-150`
- captured_output:
  ```text
  src/auditmanager/analysis/text/budget.py:62:    AR_TEXT_PROMPT_BUNDLE,
  src/auditmanager/analysis/text/budget.py:105:def _fixed_prompt_characters() -> int:
  src/auditmanager/analysis/text/budget.py:107:    bundle = AR_TEXT_PROMPT_BUNDLE
  src/auditmanager/analysis/text/budget.py:141:        Fraction(AR_TEXT_PROMPT_BUNDLE.max_output_tokens)
  src/auditmanager/analysis/text/budget.py:150:        - _fixed_prompt_characters()
  ```
- interpretation: `_fixed_prompt_characters()` takes no argument and reads the АР v1 bundle (lines 105-108); the output cap is priced from the same bundle (line 141) (finding 5).

### P-06 — the figures: the АР v1 bundle's system prompt and schema against the section prompts at the base
- captured_at: 2026-10-28
- command: `PYTHONPATH=src:$BS .venv/bin/python -c "import subprocess;from auditmanager.analysis.text.budget import _fixed_prompt_characters as f;from auditmanager.analysis.text.prompt import canonical_json,response_schema_for,CATEGORIES;print('AR bundle', f());sch=len(canonical_json(response_schema_for(CATEGORIES)));sch3=len(canonical_json(response_schema_for((*CATEGORIES,'documentation'))));g=lambda c:subprocess.run(['git','show','93bc5037:src/auditmanager/analysis/text/profiles/'+c+'/system_prompt.md'],capture_output=True,text=True).stdout[:-1];print('PB base', len(g('pb'))+sch);print('AI base', len(g('ai'))+sch3);print('SS base', len(g('ss'))+sch3)"`
- captured_output:
  ```text
  AR bundle 3639
  PB base 7163
  AI base 8673
  SS base 11832
  ```
- interpretation: the АР bundle reserves 3,639 characters; the section prompts with their schema run from 7,163 (ПБ, the shortest) to 11,832 (СС, the longest) at the base: the judge's figures.

### P-07 — the pins of `profile_version` `1.3.0` that a prompt edit moves
- captured_at: 2026-10-28
- command: `git grep -n "1\.3\.0" 93bc5037 -- tests/unit/analysis/text_profiles/section_profile_expectations.json src/auditmanager/analysis/text/profiles | cut -c10-150`
- captured_output:
  ```text
  src/auditmanager/analysis/text/profiles/ai/profile.json:6:  "profile_version": "1.3.0",
  src/auditmanager/analysis/text/profiles/eom/profile.json:6:  "profile_version": "1.3.0",
  src/auditmanager/analysis/text/profiles/itp/profile.json:6:  "profile_version": "1.3.0",
  src/auditmanager/analysis/text/profiles/ss/profile.json:6:  "profile_version": "1.3.0",
  src/auditmanager/analysis/text/profiles/tx/profile.json:6:  "profile_version": "1.3.0",
  tests/unit/analysis/text_profiles/section_profile_expectations.json:5:    {"code": "AI", "status": "reviewed", "profile_version": "1.3.0"},
  tests/unit/analysis/text_profiles/section_profile_expectations.json:8:    {"code": "TX", "status": "reviewed", "profile_version": "1.3.0"},
  tests/unit/analysis/text_profiles/section_profile_expectations.json:14:    {"code": "EOM", "status": "reviewed", "profile_version": "1.3.0"},
  tests/unit/analysis/text_profiles/section_profile_expectations.json:15:    {"code": "SS", "status": "reviewed", "profile_version": "1.3.0"},
  tests/unit/analysis/text_profiles/section_profile_expectations.json:16:    {"code": "ITP", "status": "reviewed", "profile_version": "1.3.0"},
  ```
- interpretation: ten lines: five `profile.json` and five lines of the expectations file (the registry test `test_the_registry_serves_three_categories_to_exactly_the_five_and_two_to_the_rest` pins the same string).

### P-08 — the sentence-guard builder's sources at the base
- captured_at: 2026-10-28
- command: `git grep -n "\"C1\"\|^WIDEN" 93bc5037 -- tests/unit/analysis/text_profiles/build_section_prompt_fragments.py | cut -c10-150`
- captured_output:
  ```text
  tests/unit/analysis/text_profiles/build_section_prompt_fragments.py:46:WIDEN = {
  tests/unit/analysis/text_profiles/build_section_prompt_fragments.py:51:    "C1": "SECTION-CATEGORY-OCR-01",
  ```
- interpretation: the table is generated from the documents named in `WIDEN`; a new fragment block needs a new key there (`J1`), and the table is rewritten by the builder, never by hand.

### P-09 — the container-free battery before the first edit
- captured_at: 2026-10-28
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis tests/integration/sections tests/integration/analysis_text tests/contract/analysis_packages`
- captured_output:
  ```text
  1406 passed, 73 skipped in 34.30s
  ```
- interpretation: the figure the final battery is compared with (the 73 skips are the token guard's sourced part and the legacy-commit hash check, both needing the legacy repository, absent on this host). This run read `DATABASE_URL` from the copied `.env` for the one stack test of the battery: see the report, «Disclosed».

### P-10 — the private database the stack tests use
- captured_at: 2026-10-28
- command: `DATABASE_URL=$PRIVATE_URL PYTHONPATH=src:$BS .venv/bin/python -m alembic --config db/migrations/alembic.ini current`
- captured_output:
  ```text
  0037_analysis_presets (head)
  ```
- interpretation: a database created for this lane on the lane's PostgreSQL and migrated to the head the brief names; every later pytest ran with `DATABASE_URL` pointing at it, and it is dropped at the end.

### P-11 — the judge's reproduction against a copy of the base `omission.py`
- captured_at: 2026-10-28
- command: `git show 93bc5037:src/auditmanager/analysis/text/omission.py > $SCRATCH/omission_base.py; PYTHONPATH=src:$BS .venv/bin/python $SCRATCH/repro.py $SCRATCH/omission_base.py`
- captured_output:
  ```text
  visible=(1, 3): published
  оверка программой: запись «Д-5» не найдена в текстовом слое на странице 3 (буквальное совпадение без учёта регистра); другие написания не проверялись.
  occurs('ВК-1', ['Позиция BK-1 Кран']) = False
  occurs('ВРУ-1', ['Щит BPY-1']) = False
  occurs('3х2,5', ['Кабель 3х2.5']) = False
  occurs('Г-3', ['Светильник Г.3']) = False
  occurs('Ø20', ['Труба Ф20']) = False
  occurs('ЩО-1', ['Щит ЩО-I']) = False
  ```
- interpretation: the defect is real at the base: term on page 1, heading on page 3, the schedule continues on page 4 with the term; the claim «pages 3 to 3» with `visible=(1, 3)` is published as «не найдена на странице 3», and none of the six spellings of the judge's list is a presence. The script is the report's Appendix A.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

`SECTION-CATEGORY-OCR-01.md` and the widen reports are immutable and are not edited; this lane's report supersedes their statements about the omission check's reasons (seven, now twelve), the sentence the stage appends, and the prompt sentences that said «two categories».

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/text/omission.py`
- `src/auditmanager/analysis/text/stage.py`
- `src/auditmanager/analysis/text/windowed.py`
- `src/auditmanager/analysis/text/budget.py`
- `src/auditmanager/analysis/text/windows.py`
- `src/auditmanager/runs/executor.py`
- `src/auditmanager/analysis/text/profiles/ai/**`
- `src/auditmanager/analysis/text/profiles/tx/**`
- `src/auditmanager/analysis/text/profiles/eom/**`
- `src/auditmanager/analysis/text/profiles/ss/**`
- `src/auditmanager/analysis/text/profiles/itp/**`
- `fixtures/recorded/sections/ai/**`
- `fixtures/recorded/sections/tx/**`
- `fixtures/recorded/sections/eom/**`
- `fixtures/recorded/sections/ss/**`
- `fixtures/recorded/sections/itp/**`
- `tests/unit/analysis/**`
- `tests/integration/sections/**`
- `tests/integration/analysis_text/**`
- `docs/program/SECTION-JUDGE-FIXES-01.md`
- `docs/program/tasks/SECTION-JUDGE-FIXES-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, `web/**`, `infra/**`, `bootstrap/**` (the composition root: the start-time budget check stays a follow-up), `src/auditmanager/runs/commands.py`, `src/auditmanager/findings/**`, the AR v3 modules, the nine other section packages (`ps pos kj km ov vk pt gp pb`) and their recordings, `fixtures/recorded/text_analysis/**`, root dependency and lock files, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the rulings, the ADRs, `P02_LOCK.json`.

## Non-goals

- No change of the contract, the finding CHECKs, the artifact shape or any web label.
- No new category, no new profile field, no new package format; no change to the nine other sections; no AR v3 path change.
- No per-section start-time budget check (needs the composition root); no change to the symmetric window-start case; `recommendation_text` is not read by the overclaim check.
- No model call, no push, no tag, no docker command; the lane stack is used through a copy of the integrator's `.env` and a private database that is dropped at the end.
- No claim that any prompt sentence, specimen or decision was reviewed by anyone (`A-5`, `A-7`).

## Deliverables

- `src/auditmanager/analysis/text/omission.py` (the search over every visible page, the window-end refusal, the text-less and recognised-text reasons, the overclaim reason, the wider fold, the sentence), the edits of `stage.py`, `windowed.py`, `budget.py`, `windows.py` and the two call sites in `runs/executor.py`.
- The five prompts (three sentences each), `profile_version` `1.3.1`, the five rebuilt recordings, the expectations lines, the sentence-guard table regenerated by its builder (new source key `J1`).
- Tests: `test_omission_judge_fixes.py`, `test_omission_spelling.py`, `test_section_omission_judge_fixes.py`, `test_section_input_budget.py`, and the edits listed in the report under «Modified tests».
- Report `docs/program/SECTION-JUDGE-FIXES-01.md` (per finding: what was wrong, the fix, the failing-first test, the mutation table, before/after of every modified test, commands with counts, limits).

## Required tests

- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent DATABASE_URL=$PRIVATE_URL PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis tests/integration/sections tests/integration/analysis_text tests/contract/analysis_packages`
- expected: 1578 passed, 73 skipped (base 1406 passed, 73 skipped).
- command: the same with `tests/integration/runs` on a private, migrated, freshly created database — expected 944 passed; `python3 fixtures/recorded/sections/build_fixtures.py --check` — `fixtures match`; `python3 -I tests/unit/analysis/text_profiles/build_section_prompt_fragments.py` — `fragments match`; `python3 -I fixtures/recorded/sections_widen/omission/build_specimens.py` — `specimens match`; web `npx vitest run tests/unit/analysis-settings` (with the shared `node_modules` linked, then unlinked) — 142 passed.
- mutations: one per guard (the report's table): the other-pages search, the window end, the naming-page exemption, the window bound, each wiring call, each fold element and the over-folds, the sentence, the overclaim stems, the prompt sentences, the versions, the recordings, the budget's bundle, schema, output cap and call sites.
- The governance one-liner on this file — expected `[]`; `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` (on the committed tree) and `git diff --check`.

## Integration contract

The integrator can rely on: no contract, migration, web, infra, `bootstrap/**` or AR v3 file is touched; the nine other packages and recordings are byte-identical; the five sections' request keys change (new prompt text, `profile_version` `1.3.1`). `input_budget_characters` and `text_window_policy` gain an optional `bundle` keyword whose default is today's behaviour, so the start-up check, `startRun` and the AR v3 path are unchanged; the executor passes the run's bundle. `run_text_analysis` and `run_text_analysis_windows` gain an optional `textless_pages`. Five stage metrics are added for the five sections only. The omission check is stricter by design: true omissions are dropped more often, counted by reason. The start-time check per section is a follow-up (report, finding 5).

## Failure/idempotency/security cases

A pair that fails any check is not written and is counted under its reason; nothing is retried or repaired. Recognised text and the version's text-less list can only refuse a pair, never publish one. A recognised text is data: it is compared with the term and never rendered or followed by this code. A refusal is explicit, never a silent fallback: a version with no list of text-less pages (`None`) applies the text layer's own 50-character rule, as before.

## Rollback / feature flag

Revert the commits: the five packages return to `1.3.0` and their old recordings, the check returns to the range-only search, the budget to the АР figure for every run. No feature flag; every change applies to the omission category of five profiles or to the window decision of a section run.

## Handoff

- changed files: see the report («Files»)
- commands/results: see the report («Commands and counts»)
- known limits: nothing ran against a model; the check is a literal term in the saved text layer, not a proof of absence from the project; the start-time budget check and the symmetric window-start case are open (report «Limits»)
- integration notes: see the report («Integration notes»)
