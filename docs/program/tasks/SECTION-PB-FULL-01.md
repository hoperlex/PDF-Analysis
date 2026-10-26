# Task SECTION-PB-FULL-01 — the ПБ (PB) profile answers every open question of its record and is `reviewed`, without a human review

task_id: SECTION-PB-FULL-01
status: completed in development candidate

## Outcome

The authored fire-safety profile `PB` has no legacy source (`"source": null`) and no row in `W59-SECTION-PROFILES-01.md`: its record is `docs/program/PB-PROFILE-01.md` and the package's own `open_questions.md` (eleven numbered questions, a pointer to the four cross-section questions). Each of the eleven now has one written decision (K keep, N narrow, X exclude) appended under it in `open_questions.md` and in the report, the four cross-section decisions of `PRODUCTION-WAVE-PW2B.md` are applied, `system_prompt.md` is edited only where a decision is N, `profile_version` is bumped because the prompt text changed, the recording is rebuilt, and `profile.json` and the `PB` line of `section_profile_expectations.json` say `reviewed`. Under `R-146ag` neither an expert nor the owner reviews the section; `reviewed` here is **not** expert verification (`A-7`). Because there is no pinned source, a question that would need a fire-safety domain decision that neither v1 nor the record gives is K with the reason «no source to decide from».

## Depends on

- `PRODUCTION-READINESS-PLAN-01` — completed; item `PROD-14` is this lane's family.
- `PROD-14-0-EXPECTATIONS-01` — completed; it created the one-line-per-section expectations file.
- `PB-PROFILE-01`, `SECTION-RECORDINGS-01` — completed; they created the package, its questions and the recording.
- `SECTION-VK-FULL-01`, `SECTION-EOM-FULL-01` — completed on this base; they set the decisions table and the designation audit that this lane follows.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.5.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable (the two categories, the response schema and the output contract of v1 are unchanged)
- migration head: `0032_ar_v3_run_group`, unchanged (`R-146ah`: no migration)
- base commit: `82068f3bfdcc54ff1725dc813482112accb17234` (`integration/ar-close-1026`, with ten sections already `reviewed`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No section, package or route is added or removed. The recording directory `fixtures/recorded/sections/pb/` keeps exactly one file; its name is the new request key.

## Captured premise evidence

- premise: the package, its status and version, the absence of any legacy source, the eleven open questions, the four cross-section questions, the expectations line and the recording are as the brief and `PB-PROFILE-01.md` describe; captured before any edit

### P-01 — the package at the base commit

- captured_at: 2026-10-26
- command: `ls -l src/auditmanager/analysis/text/profiles/pb; python3 -I -c "import json;d=json.load(open('src/auditmanager/analysis/text/profiles/pb/profile.json',encoding='utf-8'));print(d['section_code'],d['status'],d['profile_version'],d['source'],d['analysis_profile_id'],d['prompt_bundle_id'])"; sha256sum src/auditmanager/analysis/text/profiles/pb/system_prompt.md src/auditmanager/analysis/text/profiles/pb/open_questions.md`
- captured_output:
  ```text
  total 24
  -rw-r--r-- 1 root root  7018 Oct 26 17:06 open_questions.md
  -rw-r--r-- 1 root root   298 Oct 26 17:06 profile.json
  -rw-r--r-- 1 root root 11632 Oct 26 17:06 system_prompt.md
  PB draft 1.0.0 None ap_01M5G4NZVKNZJYH722M0SXXP3X pb_01M5G4NZVKHM9GP4EH22JACW2X
  6398dc86db63ff154253182c85d78ddb8eb5ae4e4d4f456be31a27b1b6dd7d9b  src/auditmanager/analysis/text/profiles/pb/system_prompt.md
  b07a2728d15332ba2b5844e24495550cabfd0363badfd89ae9763f62ed8b790f  src/auditmanager/analysis/text/profiles/pb/open_questions.md
  ```
- interpretation: the package is `draft` at `1.0.0`, `source` is `null`, and it holds the third file `open_questions.md` that only an authored package carries (the registry requires it for `AUTHORED_SECTIONS = {"PB"}`).

### P-02 — there is no legacy source for PB, here or in the legacy repository

- captured_at: 2026-10-26
- command: `sed -n 5p src/auditmanager/analysis/profiles/section_candidates/metadata.py; git -C /root/projects/PDF-proverka rev-parse HEAD; git -C /root/projects/PDF-proverka status --short | wc -l; git -C /root/projects/PDF-proverka ls-tree -r --name-only 16ba8e5d23e4782550e79355002fde1365f682b7 | grep -i -E "pb|пб|fire|пожар"`
- captured_output:
  ```text
  PB has no legacy source and must be authored separately.
  16ba8e5d23e4782550e79355002fde1365f682b7
  0
  contracts/agent_stream/v1/agent_stream_pb2.py
  contracts/agent_stream/v1/agent_stream_pb2_grpc.py
  contracts/agent_stream/v1/common_pb2.py
  contracts/agent_stream/v1/common_pb2_grpc.py
  contracts/worker_certificate/v1/worker_certificate_pb2.py
  contracts/worker_certificate/v1/worker_certificate_pb2_grpc.py
  docs/distributed_audit_workers/12d/12D_FIREWALL_DIFF.json
  "experiments/\320\261\320\273\320\276\320\272\320\270 \321\200\320\260\320\267\320\275\321\213\321\205 \320\264\320\270\321\201\321\206\320\270\320\277\320\273\320\270\320\275/\320\222\320\232/build_vk_fire_piping_graph_v02.py"
  ```
- interpretation: the only hits are protobuf modules (`*_pb2`), a firewall diff and a ВК piping script; there is no ПБ discipline directory, so there is no legacy file to pin and none was read. The legacy tree does contain fire-safety wording inside other disciplines' files (for example `prompts/disciplines/AR/checklist.md`); those files are the source of other sections, are not pinned to `PB`, and **no decision of this lane draws on them**. The rule «no norm reference, number or class designation that is not in the source» therefore becomes: none that is not in v1's prompt text or in the PB record. The legacy repository was only read (`status --short`: 0 lines).

### P-03 — the eleven open questions of the record

- captured_at: 2026-10-26
- command: `git show 82068f3b:src/auditmanager/analysis/text/profiles/pb/open_questions.md | python3 -c "…"` (prints the first 70 characters of each numbered line and whether the text holds `draft` and `D-178`)
- captured_output:
  ```text
  1. Перечень мест, которые сверяются между собой (общие данные и показател
  2. Нужно ли отдельное правило для раздела, который в комплекте разнесён н
  3. Предел огнестойкости записан в одном месте как «REI 60», в другом для 
  4. Здание смешанного назначения имеет несколько классов функциональной по
  5. Категория помещения по взрывопожарной и пожарной опасности и класс зон
  6. Нумерация этажей (подземные, технический, «-1», «цокольный») различает
  7. «Принято по специальным техническим условиям», «по СТУ», «в соответств
  8. «Уточнить на следующей стадии», «уточняется проектом противодымной защ
  9. Исключены как расчёт: время эвакуации, значение пожарного риска, расхо
  10. Нормы названы только как перечень того, что профиль не проверяет: Феде
  11. Пожарная безопасность — раздел, а не часть пояснительной записки (`PS`
  lines: 66 | contains draft: True | D-178: True
  ```
- interpretation: exactly eleven questions, numbered 1 to 11, plus a closing pointer to the four cross-section questions. Each question is single-barrelled, so there are eleven decisions. The opening paragraph says the profile «не засчитывается в приёмку беты, пока на вопросы ниже не ответит эксперт (`D-178`)» and that it has no «записанных ответов»; both sentences are untrue once the lane has answered the questions (and the second was already stale since `SECTION-RECORDINGS-01` added a synthetic recording), so they are rewritten, not deleted. The pin test `test_pb_open_questions_are_listed_in_the_package` asks for at least eight numbered questions with gap-free numbering, `D-178`, a final newline and no carriage return, and the word `draft` only while the expectations line says `draft`.

### P-04 — the four cross-section questions of the record

- captured_at: 2026-10-26
- command: `git show 82068f3b:docs/program/W59-SECTION-PROFILES-01.md | sed -n 171,187p`
- captured_output:
  ```text
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
- interpretation: the four questions that the brief fixes as K, K, K unless the section's own record names a systematic false-positive bullet (then N for that bullet only), K. The record of `PB` (`PB-PROFILE-01.md`, `open_questions.md`) names no bullet as a systematic false-positive source of detached sheet text; its last hint bullet reads «в подписях значений на планах и схемах». `W59-SECTION-PROFILES-01.md` has no per-section row for `PB` (it says PB «is excluded on purpose»); it is not edited (forbidden path).

### P-05 — the expectations line, the builder and the recording at the base commit

- captured_at: 2026-10-26
- command: `grep -n '"PB"' tests/unit/analysis/text_profiles/section_profile_expectations.json; PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py --check; ls fixtures/recorded/sections/pb`
- captured_output:
  ```text
  18:    {"code": "PB", "status": "draft", "profile_version": "1.0.0"}
  fixtures match
  153d0c01416a33ea996d8031d293f441a3e829a4e5061e111541467e90bb6ad0.json
  ```
- interpretation: one line, `draft` at `1.0.0`; the builder agrees with the one recording on disk, whose file name is its `request_sha256`, whose `origin.profile_status` is `draft`, whose `origin.prompt_bundle_sha256` begins `69f04bdc…` and whose `origin.task_id` is `SECTION-RECORDINGS-01`.

### P-06 — how `status` and `profile_version` enter the hashes

- captured_at: 2026-10-26
- command: `grep -n "status\|profile_version" src/auditmanager/analysis/text/profile.py src/auditmanager/analysis/text/prompt.py src/auditmanager/analysis/text/adapter.py`
- captured_output:
  ```text
  src/auditmanager/analysis/text/profile.py:43:    profile_version: str
  src/auditmanager/analysis/text/profile.py:60:                    "profile_version": self.profile_version,
  src/auditmanager/analysis/text/profile.py:73:    profile_version=PROFILE_VERSION,
  ```
- interpretation: `status` appears in none of the three files, so it enters no hash and no request body. `profile_version` enters the profile's `content_sha256`, not the request. The request key depends on the system prompt text through the bundle's `content_sha256`, so only a prompt edit orphans the recording; a status or version change alone does not.

### P-07 — what else carries the PB identities or the recording key

- captured_at: 2026-10-26
- command: `grep -rIl "153d0c01416a33ea996d8031d293f441a3e829a4e5061e111541467e90bb6ad0\|ap_01M5G4NZVKNZJYH722M0SXXP3X\|pb_01M5G4NZVKHM9GP4EH22JACW2X" --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.venv --exclude=.env .`
- captured_output:
  ```text
  docs/program/PB-PROFILE-01.md
  src/auditmanager/analysis/text/profiles/pb/profile.json
  fixtures/recorded/sections/pb/153d0c01416a33ea996d8031d293f441a3e829a4e5061e111541467e90bb6ad0.json
  web/tests/unit/styles/screens.ts
  ```
- interpretation: the report of the earlier task (not edited), the manifest, the recording, and a web test fixture that names the **identities** only (`web/tests/unit/styles/screens.ts:766`). The lane keeps both identities, so that fixture stays true; the recording key is held by the recording file alone, so rebuilding it leaves no dangling pin.

### P-08 — baseline of the section test set before any edit

- captured_at: 2026-10-26
- command: `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages`
- captured_output:
  ```text
  211 passed in 11.60s
  ```
- interpretation: green at the base (`build_fixtures.py --check`: `fixtures match`, P-05). `$BS` is the repository's bootstrap site-packages directory.

### P-09 — the designation audit of the PB prompt against v1 and against the PB record

- captured_at: 2026-10-26
- command: `PYTHONPATH=src python3 -I audit_pb.py <worktree> 82068f3b` (the script is printed in the report, section «Audit of numerals and designations»; it reads v1's `SYSTEM_PROMPT` and the record files `PB-PROFILE-01.md`, `tasks/PB-PROFILE-01.md`, `open_questions.md` **as they stood at the base commit**, so text this lane appends cannot vouch for itself)
- captured_output (run on the unedited prompt, before any edit):
  ```text
  digit-bearing tokens: ['123-ФЗ', '13130']
    '123-ФЗ'           in v1 prompt: False  in PB record: True
    '13130'            in v1 prompt: False  in PB record: True
  capital designations: ['TBD', 'XX', 'ГОСТ', 'ЖЕ', 'И', 'НЕ', 'ПБ', 'СП', 'ТОГО', 'ТОМ', 'ФЗ']
    'TBD'              in v1 prompt: True   in PB record: False
    'XX'               in v1 prompt: True   in PB record: True
    'ГОСТ'             in v1 prompt: True   in PB record: False
    'ЖЕ'               in v1 prompt: True   in PB record: False
    'И'                in v1 prompt: True   in PB record: True
    'НЕ'               in v1 prompt: True   in PB record: False
    'ПБ'               in v1 prompt: False  in PB record: True
    'СП'               in v1 prompt: True   in PB record: True
    'ТОГО'             in v1 prompt: True   in PB record: False
    'ТОМ'              in v1 prompt: True   in PB record: False
    'ФЗ'               in v1 prompt: False  in PB record: True
  hyphenated Latin / numero tokens: ['№ 123-ФЗ']
    '№ 123-ФЗ'         in v1 prompt: False  in PB record: True
  ```
- interpretation: no token is in neither v1's prompt nor the PB record. The prompt carries no class designation (`REI`, `EI`, `R`, `Ф1.3`, `С0` and the like are absent; `REI`/`EI`/`R` occur only in question 3 of the record), no clause number and no limit. The two norm identifiers `123-ФЗ` and `13130` are the record's, not v1's: `PB-PROFILE-01.md` traces them to `docs/program/dispatch/W57-PLAN.md` lines 52 and 87 (re-read: line 52 names «Федеральный закон N 123-ФЗ», line 87 lists `123-ФЗ` and `СП 1.13130.2020`, `СП 3.13130.2009`, `СП 7.13130.2013` in the corpus and `СП 2.13130`, `СП 4.13130` as absent). They stay (remove nothing the record itself says); they stand only in the sentence that tells the model what **not** to check. They have no pinned source: a limit, listed in the report. `TBD`, `XX`, `ЖЕ`, `И`, `НЕ`, `ТОГО`, `ТОМ` are v1's own placeholder marks and upper-case emphasis. Ordinary words (not designations): 397 distinct words of four or more letters, 88 of them share no six-letter stem with v1 or the record; they are the inflected domain vocabulary of the hint block (`гидрантов`, `клапанов`, `лестничного`, `противодымной`, …); no rule is stated by any of them.

### P-10 — where the PB prompt differs from v1 in the object kinds of condition 1, and where it speaks of totals, sheet labels and placeholders

- captured_at: 2026-10-26
- command: `grep -n "этажам, частям" -A1 src/auditmanager/analysis/text/prompt.py; git show 82068f3b:src/auditmanager/analysis/text/profiles/pb/system_prompt.md | sed -n 57,61p; git show 82068f3b:src/auditmanager/analysis/text/profiles/pb/system_prompt.md | grep -n -i "подпис\|штамп\|итог\|сумм\|частям\|смешан\|REI\|СТУ\|уточн"`
- captured_output:
  ```text
  68:1. Разные объекты. Значения относятся к разным зданиям, сооружениям, этажам, частям
  69-   здания, помещениям или конструкциям. Это не противоречие, даже если признак называется
  1. Разные объекты. Значения относятся к разным зданиям, сооружениям, пожарным отсекам,
     секциям, этажам, лестничным клеткам, эвакуационным выходам, помещениям, зонам
     противодымной защиты, системам или конструкциям. Это не противоречие, даже если
     признак называется одинаково. Ищи в тексте прямое указание на то, к чему относится
     значение.
  16:  незаполненности: «уточнить», «уточняется», «TBD», «XX», «___», «(?)» и подобное.
  51:- отметки о незаполненности («уточнить», «XX», «___») в графах таблиц и ведомостей
  53:  систем), а также в подписях значений на планах и схемах.
  72:   даже если формулировка содержит корень «уточн».
  ```
- interpretation: (1) v1's list of different objects holds «частям здания» («зданиям, сооружениям, этажам, частям здания, помещениям или конструкциям»); the PB list, which replaced v1's, keeps every other v1 kind and adds PB's own (`пожарным отсекам`, `секциям`, `лестничным клеткам`, `эвакуационным выходам`, `зонам противодымной защиты`, `системам`) but **has lost «частям здания»**. Question 4 of the record asks exactly about the parts of a mixed-use building, and `PB-PROFILE-01.md` («Risks») names mixed-use buildings as a source of false findings. That is the one mechanism the record states and the one place where v1's own wording answers it. (2) The prompt has no «Итого» and no recomputation bullet; text read from sheet labels occurs in one place only (line 53, «в подписях значений на планах и схемах»); the record names no bullet as a systematic false-positive source of it. (3) The unfilled marks are v1's («уточнить», «TBD», «XX», «___», «(?)»); the words «СТУ» and «REI» do not occur in the prompt, so questions 3 and 7 concern wording that is **not** there.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/text/profiles/pb/**` (including `open_questions.md`)
- `fixtures/recorded/sections/pb/**`
- `tests/unit/analysis/text_profiles/section_profile_expectations.json`
- `docs/program/tasks/SECTION-PB-FULL-01.md`
- `docs/program/SECTION-PB-FULL-01.md`

`section_profile_expectations.json` is allowed for the `PB` line only.

## Forbidden hotspots

Every other section's files, `docs/program/W59-SECTION-PROFILES-01.md`, the registry (`profile_registry.py`), `P02_LOCK.json`, `contracts/**`, migrations, `web/**`, `infra/**`, `fixtures/recorded/sections/build_fixtures.py`, `fixtures/recorded/sections/README.md`, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs, `PB-PROFILE-01.md`, `origin/main`, tags and the deployment host.

## Non-goals

- No new finding category, no widening of what a finding is, no change to v1's two categories, response schema or output contract (`contracts/**` untouched).
- No normative number, norm reference, threshold or class designation that is not in v1's prompt text or in the PB record; no fire-safety rule invented. In particular the designations of question 3 (`REI`, `EI`, `R`) and the words of questions 7 and 8 (`СТУ`, «расчёт пожарного риска») are not written into the prompt.
- No claim that an expert or the owner verified anything (`A-7`).
- No new identity (`analysis_profile_id`, `prompt_bundle_id`): the lane does not mint ids.
- No migration (`R-146ah`), no model call, no push, no container command.
- No edit of the registry or of a test: the pin test of `open_questions.md` stays as it is and the lane keeps it green.

## Deliverables

- `src/auditmanager/analysis/text/profiles/pb/system_prompt.md`: one edit (N for question 4: «частям здания» restored in the object kinds of condition 1).
- `src/auditmanager/analysis/text/profiles/pb/profile.json`: `status` `reviewed`, `profile_version` `1.1.0`.
- `src/auditmanager/analysis/text/profiles/pb/open_questions.md`: the opening paragraph rewritten to tell the truth under `R-146ag`/`A-7`, a decision appended under each of the eleven questions, the cross-section pointer turned into a short section with the four decisions; questions kept, numbering and `D-178` kept.
- `fixtures/recorded/sections/pb/<new request key>.json`, rebuilt by `fixtures/recorded/sections/build_fixtures.py`; the old file removed by the builder.
- The `PB` line of `tests/unit/analysis/text_profiles/section_profile_expectations.json`.
- Report `docs/program/SECTION-PB-FULL-01.md`: decisions table, the diff of the prompt in words, the designation audit, assumptions an expert would still want to check, mutation table, test counts, integration notes.

## Required tests

- `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages` — expected: 211 passed.
- With the lane stack: `tests/integration/composition/test_analysis_profiles_over_http.py` — expected: 4 passed.
- In `web/`: `npx vitest run tests/unit/analysis-settings` — expected: 95 passed.
- `PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py --check` — expected: `fixtures match`, rc 0.
- Mutations: revert the status in `profile.json` only, and separately the `PB` line only — expected: red naming `PB`; also the prompt only and the recording only — expected: red; and the pin test of `open_questions.md` (remove `D-178`, strip a number, delete a question).
- The governance one-liner on this file — expected: `[]`; `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` and `git diff --check` before the last commit.

## Integration contract

The integrator can rely on: the diff is confined to the five allowed path groups, the `PB` line of the expectations file is a one-line change (and the last line of the array, so a neighbouring section's line changes do not conflict), the other thirteen recordings are byte-identical after the builder runs, the registry loads `PB` as `reviewed` at `1.1.0` with the same identities, and `--check` of the builder is clean. The points under «Integration notes» of the `AI` and `EOM` reports (the web label for `reviewed`, the stored runs of the draft profile) apply to `PB` unchanged. One more: `fixtures/recorded/sections/README.md` still has a section «The ПБ recording is for a draft profile» (forbidden path for this lane); see the report.

## Failure/idempotency/security cases

A prompt edit without a rebuilt recording turns the builder's `--check` and seven cases of `test_section_recordings.py` red; a status or version in `profile.json` that differs from the expectations line turns the registry, package and guard tests red (and the HTTP and web tests, which read the same line). A damaged `open_questions.md` (fewer than eight questions, a gap in the numbering, no `D-178`) turns `test_pb_open_questions_are_listed_in_the_package` red. Re-running the builder is idempotent. No security surface: static data, no code.

## Rollback / feature flag

Forward-revert of the lane's commits restores `draft`, `1.0.0`, the old prompt, the old questions file and the old recording together. No feature flag: the profile is served by the registry as soon as it is merged, as before; `draft` and `reviewed` are both executable.

## Handoff

- changed files: see the report
- commands/results: see the report
- known limits: see the report (assumptions an expert would still want to check; nothing was measured on real text; the profile has no pinned source at all)
- integration notes: see the report
