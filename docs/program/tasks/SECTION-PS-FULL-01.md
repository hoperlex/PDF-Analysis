# Task SECTION-PS-FULL-01 — the ПЗ (PS) section profile: every open question answered, recording rebuilt, status `reviewed` without a human review

task_id: SECTION-PS-FULL-01
status: completed in development candidate

## Outcome

The record of the `PS` section in `docs/program/W59-SECTION-PROFILES-01.md` has five «open questions for the expert reviewer» and four cross-section questions. Each now has one written decision (`K` keep, `N` narrow, `X` exclude) in `docs/program/SECTION-PS-FULL-01.md`; the prompt of the `ps` package changes only where a decision is `N` (two near-miss pairs added to condition 2, nothing widened); `profile_version` goes `1.0.0` to `1.1.0` because the prompt text changed; `profile.json` and the `PS` line of `section_profile_expectations.json` say `reviewed`; the recording under `fixtures/recorded/sections/ps/` is rebuilt by `build_fixtures.py`. **No expert and no owner reviews the section afterwards** (`R-146ag`, accepted risk `A-7`): `reviewed` here means a lane answered the questions, not that anyone verified them.

## Depends on

- `W59-SECTION-PROFILES-01` — completed; the record and the draft package.
- `SECTION-RECORDINGS-01` — completed; the builder and the recordings.
- `PROD-14-0-EXPECTATIONS-01` — completed; the one-line-per-section expectations file.
- `PRODUCTION-WAVE-PW2B` (dispatch, `R-146ag`, `R-146ah`, `R-146ai`) — the section lane template.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.5.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: the two categories `internal_contradiction` and `explicit_placeholder` and the response schema of v1, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged (`R-146ah`: no migration)
- base commit: `0e663fd0e608fcf5f79075ea71713c24ddf027e5` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No section, route, error code or migration is added. The only maintained set touched is one line of the expectations file (`PS`), whose totality against the packages is held by `test_section_profile_expectations.py`.

## Captured premise evidence

- premise: the `ps` package, the section's record, the cross-section questions, the pinned legacy source, the way `status` and `profile_version` reach the recording, and the expectations line are as the dispatch says; captured on the base tree before any edit

### P-01 — the package at the base commit

- captured_at: 2026-10-26
- command: `ls -l src/auditmanager/analysis/text/profiles/ps/ fixtures/recorded/sections/ps/ && sha256sum src/auditmanager/analysis/text/profiles/ps/system_prompt.md && grep -n '"status"\|"profile_version"\|"section_code"' src/auditmanager/analysis/text/profiles/ps/profile.json`
- captured_output:
  ```text
  $ ls -l src/auditmanager/analysis/text/profiles/ps/ fixtures/recorded/sections/ps/
  fixtures/recorded/sections/ps/:
  -rw-r--r-- 1 root root 1880 Oct 26 16:14 5dad5c5fdc7dfda6713e38aa056f833e5497e07f7d1b83a444c604617f2411f3.json

  src/auditmanager/analysis/text/profiles/ps/:
  -rw-r--r-- 1 root root  1209 Oct 26 16:14 profile.json
  -rw-r--r-- 1 root root 11475 Oct 26 16:14 system_prompt.md

  $ sha256sum src/auditmanager/analysis/text/profiles/ps/system_prompt.md
  e14d29bf163ebee0c7e43bd1b34305e3b1a03dc9098e39e16130042f111cd133  src/auditmanager/analysis/text/profiles/ps/system_prompt.md

  $ grep -n "status\|profile_version\|section_code" src/auditmanager/analysis/text/profiles/ps/profile.json
  3:  "section_code": "PS",
  6:  "profile_version": "1.0.0",
  7:  "status": "draft",
  ```
- interpretation: the package is `profile.json` plus `system_prompt.md` (no `open_questions.md`, which is `PB`'s), `draft` at `1.0.0`, with exactly one recording keyed `5dad5c5f…`. The prompt is the v1 text with the six anchored substitutions of the W59 record.

### P-02 — the open questions of the `PS` record

- captured_at: 2026-10-26
- command: `awk '/^### PS /{f=1} /^### POS /{f=0} f' docs/program/W59-SECTION-PROFILES-01.md | sed -n '/^Open questions for the expert reviewer:/,$p' | sed '/^$/d'`
- captured_output:
  ```text
  Open questions for the expert reviewer:
  - Строка «Итого» в квартирографии и в ТЭП (всего квартир, общая площадь квартир) и сумма строк по типам квартир или секциям — считать ли их расхождение находкой (сейчас пересчёт исключён)?
  - Значения из ГПЗУ и технических условий, приведённые в записке (предельная этажность, максимальный процент застройки, разрешённая мощность по ТУ), стоят рядом с проектными значениями; по условию 2 это разные признаки (предел и проектное значение) — верно ли, что такие пары не сравниваются, или эксперт ждёт этих находок?
  - Формулировки «будет определено на стадии РД», «уточняется заданием на проектирование», «ТУ будут получены» — заполнитель или принятое решение отложить?
  - Записка часто пересказывает значения других томов («по разделу АР общая площадь …»): расхождение такого пересказа с ТЭП самой записки — internal_contradiction (оба значения в одном документе) или по сути межтомная сверка, которую нужно исключить?
  - Расчётные температуры наружного воздуха разной обеспеченности и для разных систем, архитектурная и пожарно-техническая высота здания — хватает ли условия 2, или пункты о климатических данных и высоте дадут систематические ложные находки?
  ```
- interpretation: five questions, none answered in the record (it says the expert answers them). They are the ones the report's decision table closes: Итого against the sum of rows; limits of the ГПЗУ and the technical conditions against design values; deferral phrases; values retold from other volumes; outdoor-air temperatures of different probability and building heights.

### P-03 — the cross-section questions

- captured_at: 2026-10-26
- command: `git show 0e663fd0:docs/program/W59-SECTION-PROFILES-01.md | sed -n 169,187p`
- captured_output:
  ```text
  ## Cross-section questions for the expert reviewer

  These questions apply to every profile, so they are asked once here:

  1. **Site and contractor phrases.** «уточнить по месту», «уточнить при монтаже»,
     «уточняется в ППР», «по проекту оператора» and similar phrases. Under v1's
     wording each is an explicit placeholder. Are they placeholders, or accepted site
     or contractor instructions that should go into condition 4?
  2. **«Итого» against the sum of rows.** An «Итого» line in a specification, a ТЭП
     table or a schedule that disagrees with the sum of its rows. Recomputation is
     excluded today. Should this one arithmetic case be an `internal_contradiction`?
  3. **Text read from sheets.** Values read from the text layer of drawing sheets
     (labels, title blocks, leaders). These are text, but they are often detached from
     their objects. Do the bullets that name "подписи планов/схем" give systematic false
     findings?
  4. **Missing items.** An item named in one place and absent from another (a panel on
     a scheme but not in the specification). This is an omission, not two
     incompatible values. Is a third kind of observation wanted? That would be a
     contract change, not a profile edit.
  ```
- interpretation: the four questions the dispatch decides once for every lane: (1) site and contractor phrases `K`; (2) «Итого» against the sum `K`; (3) text read from sheets `K` unless the section's record names a systematic false-positive bullet; (4) missing items `K`.

### P-04 — the legacy source is on this host at the pinned commit with the pinned hashes

- captured_at: 2026-10-26
- command: `git -C /root/projects/PDF-proverka rev-parse HEAD && cd /root/projects/PDF-proverka && sha256sum prompts/disciplines/PS/role.md prompts/disciplines/PS/checklist.md prompts/disciplines/PS/drawing_types.md prompts/disciplines/PS/project_params.md prompts/disciplines/PS/finding_categories.md`
- captured_output:
  ```text
  $ git rev-parse HEAD
  16ba8e5d23e4782550e79355002fde1365f682b7
  $ sha256sum prompts/disciplines/PS/{role,checklist,drawing_types,project_params,finding_categories}.md
  9999c2e3398db818d1b85941473db785b8b132558c95661c016ad845a437b7fa  prompts/disciplines/PS/role.md
  c3dd8f7b7f84ecd23de8e353071b0f400ef9be4863de1c6b3691083ffeee9a93  prompts/disciplines/PS/checklist.md
  bfbf147ce3449ee293f194430d1aafa91898036f09f3cf9fe250c3c41cbee7d4  prompts/disciplines/PS/drawing_types.md
  eb8dcb54b22371673195d0985d8bca6ca4a01d152d590567abdddb7313376a51  prompts/disciplines/PS/project_params.md
  60dfdf036131121a97477e7cd0630f89fdf36a56d7c3e93dbb6123bfe204d907  prompts/disciplines/PS/finding_categories.md
  ```
- interpretation: the commit and all five hashes equal the `source` block of `ps/profile.json`. The lane only read the legacy repository. Words the lane checked for in these five files and did not find: «ГПЗУ», «температур», «обеспеченност», «предельн», «пожарно-техническ» (each `grep -c` printed 0); they are named in the report as vocabulary of the W59 record, not of the legacy source, and none of them is a number, a norm reference or a class designation.

### P-05 — how `status` and `profile_version` reach the identity and the recording

- captured_at: 2026-10-26
- command: `git show 0e663fd0:src/auditmanager/analysis/text/profile.py | grep -n 'profile_version\|"status"'; git show 0e663fd0:fixtures/recorded/sections/build_fixtures.py | grep -n 'profile_status\|prompt_bundle_sha256'; git show 0e663fd0:fixtures/recorded/sections/README.md | sed -n '/^## Refreshing/,/^## The ПБ/p'`
- captured_output:
  ```text
  $ grep -n "profile_version\|status" src/auditmanager/analysis/text/profile.py | head -5  (base 0e663fd0)
  43:    profile_version: str
  60:                    "profile_version": self.profile_version,
  73:    profile_version=PROFILE_VERSION,
  $ grep -n "profile_status\|prompt_bundle_sha256" fixtures/recorded/sections/build_fixtures.py
  345:                "prompt_bundle_sha256": profile.prompt_bundle.content_sha256,
  346:                "profile_status": registered.status,
  $ sed -n "/^## Refreshing/,/^## The ПБ/p" fixtures/recorded/sections/README.md
  ## Refreshing

  ```
  PYTHONPATH=src .venv/bin/python fixtures/recorded/sections/build_fixtures.py
  PYTHONPATH=src .venv/bin/python fixtures/recorded/sections/build_fixtures.py --check
  ```

  Editing a section's `system_prompt.md` (or anything in
  `auditmanager.analysis.text.prompt`) changes its key and orphans its recording; re-run
  the builder.

  ## The ПБ recording is for a draft profile
  ```
- interpretation: `profile_version` is part of the profile hash (`content_sha256`); `status` is not, but the builder writes it into `origin.profile_status` of the recording, so moving a status alone makes `build_fixtures.py --check` report drift. The recording key is the digest of the request body, which contains the prompt: a prompt edit orphans the old file and the builder both writes the new one and removes the old.

### P-06 — the expectations line and the baseline of the section's tests

- captured_at: 2026-10-26
- command: `grep -n '"PS"' tests/unit/analysis/text_profiles/section_profile_expectations.json`, then on the unedited base tree `pytest -q tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles`, `pytest -q tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages` and `python fixtures/recorded/sections/build_fixtures.py --check`
- captured_output:
  ```text
  6:    {"code": "PS", "status": "draft", "profile_version": "1.0.0"},
  50 passed in 2.30s
  161 passed in 4.64s
  fixtures match
  ```
- interpretation: one line for `PS`, on its own physical line; the baseline is green, so any red after the edit is the lane's.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

`W59-SECTION-PROFILES-01.md` is immutable here (the dispatch forbids editing it); the decisions live in the report of this lane.

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/text/profiles/ps/**`
- `fixtures/recorded/sections/ps/**`
- `tests/unit/analysis/text_profiles/section_profile_expectations.json`
- `docs/program/tasks/SECTION-PS-FULL-01.md`
- `docs/program/SECTION-PS-FULL-01.md`

The only line of `section_profile_expectations.json` the lane edits is the `PS` line.

## Lane resources

None of its own: the HTTP test reads the integrator's lane stack (`.env` copied untracked from `ar-close-1026`) and only reads it.

## Forbidden hotspots

Every other section's package and recording, `fixtures/recorded/sections/build_fixtures.py` and its README, `W59-SECTION-PROFILES-01.md`, the registry and the loader, `P02_LOCK.json`, `contracts/**`, `db/migrations/**`, `web/**`, `infra/**`, root dependency/lock files, the composition root, global styles, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs, `origin/main`, tags.

## Non-goals

- No third category, no widening of what a finding is, no new schema field (a contract change).
- No normative number, norm reference, threshold or class designation that is not in the five hash-pinned legacy files.
- No claim that an expert verified anything; no field evaluation; no model call.
- No edit of the builder, the web label of `reviewed`, the journey manifest or any shared test.

## Deliverables

- `src/auditmanager/analysis/text/profiles/ps/system_prompt.md` (condition 2 only), `profile.json` (`status`, `profile_version`).
- `fixtures/recorded/sections/ps/<new key>.json` built by `build_fixtures.py`, the old file removed by the same run.
- The `PS` line of `tests/unit/analysis/text_profiles/section_profile_expectations.json`.
- This task file and the report `docs/program/SECTION-PS-FULL-01.md`: decisions table, the prompt diff in words, the mutation table, test counts, assumptions an expert would still check.

## Required tests

- `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles` — expected: 50 passed.
- `tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages` — expected: 161 passed; `build_fixtures.py --check` — expected: `fixtures match`.
- `tests/integration/composition/test_analysis_profiles_over_http.py` with the lane `.env` exported — expected: 4 passed.
- `npx vitest run tests/unit/analysis-settings` in `web/` (node_modules linked from `gate-night`) — expected: 95 passed.
- `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` and `git diff --check`.
- Mutations: status reverted in `profile.json` only, version reverted only, the `PS` expectations line reverted only, each added phrase of condition 2 removed, the new recording deleted, the old recording restored beside it — each red, then green after restoring (table in the report).

## Integration contract

The integrator can rely on: `ps/profile.json` declares `reviewed` at `1.1.0`; its expectations line says the same; the recording key is the digest of the request built from the new prompt; the lane edits no file outside the allowed paths (`git diff --name-only 0e663fd0..HEAD`). It merges without conflict with other section lanes (one line each in the expectations file). A section's `reviewed` carries no human review (`A-7`). One thing outside the lane for the integrator: the web label for `reviewed` reads «проверен экспертом» (`web/src/entities/analysis-profile/model/presentation.ts`), which contradicts `A-7`; and `tests/e2e/pc01/journey/manifest.json` selects `tr[data-profile="draft"]`, which needs at least one draft row while the last section lane merges (see the report).

## Failure/idempotency/security cases

The new recording replays only the new prompt's request (a request of any other section, or of the old prompt, is `recording_missing`; the same key in two directories is refused). Rebuilding is idempotent: `--check` prints `fixtures match`. No credential, no network, no provider call.

## Rollback / feature flag

Forward-revert of the lane's commits restores `draft` at `1.0.0` and the old recording (git history). Runs keep the profile id and version they started with (`R-146ah`), so no data migrates. No feature flag.

## Handoff

- changed files: the five paths above
- commands/results: see the report
- known limits: see the report (no field evaluation, no expert; vocabulary taken from the W59 record)
- integration notes: see the report
