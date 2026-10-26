# Task SECTION-WIDEN-G1-01 — AI PS POS TX KJ: the same-document checks that the gap report marks «reinstatable now», decided one by one and added conservatively under the existing contract

task_id: SECTION-WIDEN-G1-01
status: completed in development candidate

## Outcome

For each of the sections `AI PS POS TX KJ` every topic that `ROADMAP-GAP-2026-10-27.md` section 2.3 marks «reinstatable now» has one written decision (W widen, K keep, N narrow, X exclude) with its exact sentence or its reason (`R-146an`, `A-5`, `A-7`; the conservative rules (1) to (6) of `PRODUCTION-WAVE-PW4.md` section 6 bind). Where the decision is W, the section's prompt asks for it under the existing category `internal_contradiction` with the existing evidence; the profile version moves from `1.1.0` to `1.2.0`, the section's recording is rebuilt and its expectations line follows. Nobody reviews the result (`A-7`): `reviewed` stays a status without human review.

## Depends on

- `SECTION-AI-FULL-01`, `SECTION-PS-FULL-01`, `SECTION-POS-FULL-01`, `SECTION-TX-FULL-01`, `SECTION-KJ-FULL-01` — completed; they produced the `1.1.0` prompts this lane edits.
- `SECTION-PROMPT-TOKEN-GUARD-01`, `SECTION-RECORDINGS-01` — completed; the guard and the recordings test the lane must keep green.
- `ROADMAP-GAP-2026-10-27` — completed; it names the topics.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.7.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable (the two categories, the response schema and the output contract of v1 are unchanged)
- migration head: `0033_ar_v3_cite_stage_id`, unchanged (no migration)
- base commit: `6075df88` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No section, package or route is added or removed. Each section directory under `fixtures/recorded/sections/` keeps exactly one file; for four sections its name is the new request key.

## Captured premise evidence
- premise: the packages, the legacy source, the gap-report cells, the conservative rules, the record's questions, the guard and the recordings test are as the brief says, except P-07 (the recordings test pins one file per directory), which changes how the positive and negative recordings are delivered

### P-01 — the five packages, their status and version, the prompt hashes, the recordings and the expectations lines at the base commit
- captured_at: 2026-10-27
- command: `B=6075df88; D=src/auditmanager/analysis/text/profiles; for c in ai ps pos tx kj; do git show $B:$D/$c/profile.json | python3 -I -c "import json,sys;d=json.load(sys.stdin);print(d['section_code'],d['status'],d['profile_version'])"; git show $B:$D/$c/system_prompt.md | sha256sum | cut -c1-16; git ls-tree --name-only $B fixtures/recorded/sections/$c/; done; git show $B:tests/unit/analysis/text_profiles/section_profile_expectations.json | grep -n '"AI"\|"PS"\|"POS"\|"TX"\|"KJ"'`
- captured_output:
  ```text
  AI reviewed 1.1.0
  1e5f25214401fba8
  fixtures/recorded/sections/ai/131994ad9877d623894007365c0923105c1021199d0084731743d06f90471da6.json
  PS reviewed 1.1.0
  bb5bc5a459023ba0
  fixtures/recorded/sections/ps/caf8aa0fe2a34349618b85b74dd04175f4757579f9c4d0b64f726b5c2902ab85.json
  POS reviewed 1.1.0
  ae4854f0aca52b59
  fixtures/recorded/sections/pos/e399ef16a725e478d9e15734776b81de7de726140bafbc6bea8b4126223785f1.json
  TX reviewed 1.1.0
  8c7b29c1bdb17096
  fixtures/recorded/sections/tx/1fa3402cd61588729135e440bdd0143a3d6f0e222785048771f08fcca89d9313.json
  KJ reviewed 1.1.0
  df0ac8c863bdf9eb
  fixtures/recorded/sections/kj/0f61471253016dc653d9df836d5a0449443eff32c8be2836a2f7b780459e4bea.json
  5:    {"code": "AI", "status": "reviewed", "profile_version": "1.1.0"},
  6:    {"code": "PS", "status": "reviewed", "profile_version": "1.1.0"},
  7:    {"code": "POS", "status": "reviewed", "profile_version": "1.1.0"},
  8:    {"code": "TX", "status": "reviewed", "profile_version": "1.1.0"},
  9:    {"code": "KJ", "status": "reviewed", "profile_version": "1.1.0"},
  ```
- interpretation: read from the base commit with `git show`, so the block stays true after this lane's edits: all five are `reviewed` at `1.1.0` (the state `SECTION-<CODE>-FULL-01` left), each section directory holds exactly one recording (its file name is the request key) and the expectations file has one line per section. A prompt edit changes the recording key and `profile_version` moves with it.

### P-02 — the legacy source is on the host, clean, at the pinned commit, and every pinned hash of the five sections matches
- captured_at: 2026-10-27
- command: `python3 -I -c "import json,subprocess,hashlib;print('HEAD==pinned',subprocess.run(['git','-C','/root/projects/PDF-proverka','rev-parse','HEAD'],capture_output=True,text=True).stdout.strip());print('status clean',subprocess.run(['git','-C','/root/projects/PDF-proverka','status','--short'],capture_output=True,text=True).stdout=='');[print(c.upper(),[hashlib.sha256(subprocess.run(['git','-C','/root/projects/PDF-proverka','show',m['commit']+':'+f['path']],check=True,capture_output=True).stdout).hexdigest()==f['sha256'] for f in m['files']]) for c in ['ai','ps','pos','tx','kj'] for m in [json.load(open(f'src/auditmanager/analysis/text/profiles/{c}/profile.json',encoding='utf-8'))['source']]]"`
- captured_output:
  ```text
  HEAD==pinned 16ba8e5d23e4782550e79355002fde1365f682b7
  status clean True
  AI [True, True, True, True, True]
  PS [True, True, True, True, True]
  POS [True, True, True, True, True]
  TX [True, True, True, True, True]
  KJ [True, True, True, True, True]
  ```
- interpretation: the repository `PDF-proverka` was only read (`git show`); nothing was written there. The vocabulary of the prompts below is checked against these 25 blobs by the token guard.

### P-03 — the gap report's «Reinstatable now» cell of each section (the topics this lane must decide)
- captured_at: 2026-10-27
- command: `python3 -I -c "import re;t=open('docs/program/ROADMAP-GAP-2026-10-27.md',encoding='utf-8').read();t=t[t.index('| Section | Reinstatable now |'):];[print(c[0],'::',c[1]) for c in ([x.strip() for x in l.strip().strip('|').split('|')] for l in t.splitlines()[:20] if re.match(r'^\| (AI|PS|POS|TX|KJ) \|',l))]"`
- captured_output:
  ```text
  AI :: an item on a plan or in the explication that the finishing schedule does not list (the omission pair of cross-section question 4; ex 5 is its required-presence form)
  PS :: a ТЭП total or coefficient recomputed from written areas and counts (ex 3); a flat-count total against its rows (q1); a recapped value of another volume against the same записка's ТЭП (q4, already in scope)
  POS :: a distribution total against 100 % (q2); the sum of stage durations against the total is **not** safe (overlap is legal)
  TX :: a position in the explication with no specification row, and the reverse (q4); a записка power or water total against the sum of the specification or load table (q3)
  KJ :: a steel-consumption sheet total against its rows (q4)
  ```
- interpretation: five sections, nine topics: one omission pair (AI), one omission pair and one total (TX), two totals and one coefficient and one recap (PS), one distribution total and one duration sum marked unsafe (POS), one total (KJ). Every one gets a decision in the report.

### P-04 — the conservative rules (1) to (6) that bind this lane, in the wave brief
- captured_at: 2026-10-27
- command: `python3 -I -c "t=open('docs/program/dispatch/PRODUCTION-WAVE-PW4.md',encoding='utf-8').read();print(t[t.index('**Conservative rules'):t.index('**Steps.**')].rstrip())"`
- captured_output:
  ```text
  **Conservative rules (decided by the integrator; there is no expert, `A-7`).** (1) Flag only when both figures are written explicitly in the text and the difference exceeds the rounding of the less precise figure (state the tolerance rule in the prompt in words, not a magic number). (2) Never recompute from a figure the text does not state; never use a value from a drawing, a picture or an OCR guess. (3) Where the section's record names a legal overlap or a stated basis (duration sums with overlapping stages; mass with or without weld metal; heat load «с учётом / без учёта» of a stated item), the prompt says not to flag unless the text states the basis. (4) Physical unit-conversion factors that are definitions, not norms (1 м³/ч = 3.6 · 1 л/с ⇒ 1 л/с = 3.6 м³/ч; 1 Гкал/ч = 1.163 МВт = 1163 кВт), may appear in the prompt and go into `prompt_token_allowlist.json` with a reason; any other number, norm reference, threshold or class designation not in the section's hash-pinned legacy source is still forbidden (`SECTION-PROMPT-TOKEN-GUARD-01`). (5) Notations that the record says experts treat as one value but the text may mean differently (`150/70 со срезкой на 130` vs `130/70`; `С345` vs `09Г2С`; `REI 60` vs `EI 60`) stay **excluded** unless a hash-pinned legacy source states the equivalence. (6) Each topic gets a decision (the existing vocabulary K/N/X plus **W — widen** for these topics) in a table; a topic the lane cannot make conservative is **X** with the reason.
  ```
- interpretation: the rules the report maps its sentences to: (1) both figures written and a tolerance stated in words, (2) never recompute from an unstated figure, (3) a stated basis, (4) no number outside the pinned source, (5) notations stay excluded, (6) every topic decided, X when it cannot be made conservative.

### P-05 — the record's own questions behind each widened topic (PS 1, POS 2, TX 3 and 4, KJ 4) and the excluded AI item
- captured_at: 2026-10-27
- command: `sed -n 295p docs/program/W59-SECTION-PROFILES-01.md; sed -n 344p docs/program/W59-SECTION-PROFILES-01.md; sed -n 397,398p docs/program/W59-SECTION-PROFILES-01.md; sed -n 453p docs/program/W59-SECTION-PROFILES-01.md; sed -n 234p docs/program/W59-SECTION-PROFILES-01.md`
- captured_output:
  ```text
  - Строка «Итого» в квартирографии и в ТЭП (всего квартир, общая площадь квартир) и сумма строк по типам квартир или секциям — считать ли их расхождение находкой (сейчас пересчёт исключён)?
  - Сумма продолжительностей этапов в календарном плане законно больше общей продолжительности из-за совмещения работ, а «Итого» распределения объёмов или капитальных вложений по периодам может не давать 100 %: считать ли находкой расхождение итоговой строки с суммой (сейчас пересчёт исключён)?
  - Считать ли находкой расхождение суммарной мощности или расхода воды в пояснительной записке с суммой строк спецификации или таблицы нагрузок (сейчас пересчёт исключён)?
  - Позиция оборудования в экспликации плана без строки в спецификации (или наоборот) — нужна ли такая находка (в v1 это не категория)?
  - Считать ли находкой расхождение строки «Итого» ведомости расхода стали или спецификации арматуры с суммой строк (сейчас пересчёт исключён)?
  - checklist.md «Ведомость отделки помещений»: «наличие всех помещений в ведомости отделки»; «Планы полов»: пороги и переходные профили, наличие гидроизоляции и звукоизоляционной подложки; «Планы потолков»: «вентиляционные решётки и ревизионные люки — наличие»; «Санузлы»: «вентиляция — наличие вытяжки, решётки», бортик, порог и трап душевой зоны; «Общие проверки»: «наличие узлов и деталей для нетиповых решений» — требование, чтобы указание было (v1, условие 5)
  ```
- interpretation: each of the four totals is a question the record left open and a `SECTION-<CODE>-FULL-01` lane answered K by the wave table; the AI omission is an excluded item that the record classes as the required-presence form of v1 condition 5.

### P-06 — the builder agrees with the on-disk recordings and the baseline section test set is green before any edit
- captured_at: 2026-10-27
- command: `PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py --check; PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages`
- captured_output:
  ```text
  fixtures match
  322 passed in 3.47s
  ```
- interpretation: green at the base (`$BS` is the repository's bootstrap site-packages directory). The 322 include the 109 cases of the token guard, which ran against the legacy repository, none skipped.

### P-07 — PREMISE DIFFERS: the section test pins exactly one file in every section directory and exactly 14 planned recordings, so the positive and negative recordings of the brief cannot be filed under fixtures/recorded/sections
- captured_at: 2026-10-27
- command: `grep -n 'iterdir\|len(planned) ==\|recording_dirs ==' tests/integration/sections/test_section_recordings.py`
- captured_output:
  ```text
  97:    assert sorted(item.name for item in directory.iterdir()) == [f"{request.request_sha256}.json"]
  156:    assert len(planned) == len(RECORDED_SECTIONS) == 14
  165:    assert served.recording_dirs == (
  173:    assert RecordedAdapter(CANONICAL).recording_dirs == (CANONICAL,)
  197:        item.name for item in SECTIONS.iterdir()
  339:    assert served.recording_dirs == (canonical, section)
  ```
- interpretation: line 97 makes a second file (or a subdirectory) in `fixtures/recorded/sections/<code>/` a failure, and lines 156 and 165 pin the builder's plan and the searched directories. The test and `build_fixtures.py` are outside this lane's allowed paths (`tests/**`, `fixtures/recorded/sections/build_fixtures.py`), and three lanes (G1, G2, G3) would edit the same builder table. The lane therefore rebuilds the existing recordings and keeps the positive and negative specimens in its report, replayed through the real stage in a scratch directory; see the report, section «Specimens».

### P-08 — the token guard's allowlist cannot take a line from this lane: disclosed_by must be a SECTION-<CODE>-FULL-01 report
- captured_at: 2026-10-27
- command: `sed -n 330p tests/unit/analysis/text_profiles/test_prompt_token_guard.py; python3 -I -c "import json;d=json.load(open('tests/unit/analysis/text_profiles/prompt_token_allowlist.json',encoding='utf-8'));print(len(d['entries']),'entries:',[(e['section'],e['token'],e['disclosed_by']) for e in d['entries']])"`
- captured_output:
  ```text
          assert re.fullmatch(r"SECTION-[A-Z]+-FULL-01\.md", entry["disclosed_by"]), identity
  8 entries: [('AI', 'КМ', 'SECTION-AI-FULL-01.md'), ('EOM', 'PE-проводника', 'SECTION-EOM-FULL-01.md'), ('GP', '0,000', 'SECTION-GP-FULL-01.md'), ('PB', '123-ФЗ', 'SECTION-PB-FULL-01.md'), ('PB', '13130', 'SECTION-PB-FULL-01.md'), ('PB', 'ПБ', 'SECTION-PB-FULL-01.md'), ('POS', 'ИТР', 'SECTION-POS-FULL-01.md'), ('PS', 'ГПЗУ', 'SECTION-PS-FULL-01.md')]
  ```
- interpretation: the pattern `SECTION-[A-Z]+-FULL-01\.md` does not admit `SECTION-WIDEN-G1-01.md`, and editing the guard test is outside the lane. So the lane writes no designation that the pinned source, v1 or the existing allowlist does not already cover, and adds no allowlist line (the report says so and shows the guard red when one is smuggled in).

### P-09 — the grounding gate: every evidence item of an observation must resolve, so a reply that quotes the total and the rows publishes only if all quotes are verbatim
- captured_at: 2026-10-27
- command: `sed -n 3,6p src/auditmanager/findings/grounding.py`
- captured_output:
  ```text
  An observation is published as a finding only when **every** one of its evidence items
  resolves on all three checks of P02 §5.1:

  1. the declared ``(char_start, char_end)`` interval lies inside the declared page's
  ```
- interpretation: the schema (`evidence`, `minItems` 1, no maximum) carries a total and its rows as quotes; it has no way to carry an absence, which is why the omission topics are decided X in the report.

### P-10 — where the extra prompt text is counted: the input budget uses the AR bundle's prompt length, not the section's
- captured_at: 2026-10-27
- command: `sed -n 105,109p src/auditmanager/analysis/text/budget.py`
- captured_output:
  ```text
  def _fixed_prompt_characters() -> int:
      """What every request carries whatever the document: the system prompt and the schema."""
      bundle = AR_TEXT_PROMPT_BUNDLE
      return len(bundle.system_prompt) + len(canonical_json(bundle.response_schema))
  ```
- interpretation: the budget subtracts the AR bundle's prompt, so a section prompt's extra characters (this lane adds 2,701 to 2,834 characters to each edited section) are already outside the budget's arithmetic; this is a property of `budget.py` (lane CH owns it), not changed here, and it is listed in the report's integration notes.

### P-11 — where condition 5 and the exclusion paragraph sit in the four prompts at the base commit
- captured_at: 2026-10-27
- command: `for c in ps pos tx kj; do git show 6075df88:src/auditmanager/analysis/text/profiles/$c/system_prompt.md | grep -n 'Ты не решаешь\|Ты НЕ проверяешь\|Сравниваются только\|прямо записанные' | sed "s/^/$c: /"; done`
- captured_output:
  ```text
  ps: 79:   Ты не решаешь, что должно было быть указано.
  ps: 81:Ты НЕ проверяешь соответствие внешним нормам (СП, СНиП, ГОСТ, ПП РФ № 87, федеральным
  ps: 84:и НЕ утверждаешь, что отсутствующее указание требовалось. Сравниваются только значения,
  ps: 85:прямо записанные в тексте.
  pos: 76:   Ты не решаешь, что должно было быть указано.
  pos: 78:Ты НЕ проверяешь соответствие внешним нормам (СП, СНиП, ГОСТ, техническим регламентам),
  pos: 81:отсутствующее указание требовалось. Сравниваются только значения, прямо записанные в
  tx: 71:   Ты не решаешь, что должно было быть указано.
  tx: 73:Ты НЕ проверяешь соответствие внешним нормам (СП, СНиП, ГОСТ, СанПиН, техническим
  tx: 76:утверждаешь, что отсутствующее указание требовалось. Сравниваются только значения, прямо
  kj: 72:   Ты не решаешь, что должно было быть указано.
  kj: 74:Ты НЕ проверяешь соответствие внешним нормам (СП, СНиП, ГОСТ, техническим регламентам),
  kj: 77:отсутствующее указание требовалось. Сравниваются только значения, прямо записанные в
  ```
- interpretation: condition 5 (pinned byte for byte by `test_every_system_prompt_keeps_the_v1_question_categories_and_output_contract`) ends two lines before a paragraph that bans recalculation in the same words in every section. The new paragraph goes between them and the ban gets one exception clause; the AI prompt is not touched.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/text/profiles/ai/**`
- `src/auditmanager/analysis/text/profiles/ps/**`
- `src/auditmanager/analysis/text/profiles/pos/**`
- `src/auditmanager/analysis/text/profiles/tx/**`
- `src/auditmanager/analysis/text/profiles/kj/**`
- `fixtures/recorded/sections/ai/**`
- `fixtures/recorded/sections/ps/**`
- `fixtures/recorded/sections/pos/**`
- `fixtures/recorded/sections/tx/**`
- `fixtures/recorded/sections/kj/**`
- `tests/unit/analysis/text_profiles/section_profile_expectations.json`
- `tests/unit/analysis/text_profiles/prompt_token_allowlist.json`
- `docs/program/tasks/SECTION-WIDEN-G1-01.md`
- `docs/program/SECTION-WIDEN-G1-01.md`

`section_profile_expectations.json` is allowed for the lines of `AI PS POS TX KJ` only; `prompt_token_allowlist.json` for append-only entries with a reason (none were needed).

## Forbidden hotspots

The other groups' files (`KM OV VK PT EOM SS ITP GP PB`), `docs/program/W59-SECTION-PROFILES-01.md`, `docs/program/SECTION-REVIEW-LEDGER-01.md`, the registry, `prompt.py`, `response.py`, `stage.py`, `docs/program/P02_LOCK.json`, `contracts/**`, migrations, `web/**`, `infra/**`, `tests/integration/sections/**`, `fixtures/recorded/sections/build_fixtures.py`, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the rulings, `origin/main`, tags and the deployment host.

## Non-goals

- No new category, field, severity or norm; no widening beyond the nine decided topics.
- No number, norm reference, threshold or class designation outside the section's pinned legacy source (conservative rule 4); no claim that an expert or the owner verified anything (`A-7`).
- No change to AR or to the web label for `reviewed`.
- No omission check (decided X, see the report), no recomputation of a coefficient, no sum of stage durations.
- No new identity, no migration, no model call, no push, no tag.

## Deliverables

- `src/auditmanager/analysis/text/profiles/{ps,pos,tx,kj}/system_prompt.md`: one paragraph after condition 5 (the only permitted addition) and two clauses in the exclusion paragraph; `profile.json`: `profile_version` `1.2.0`. AI: no change (the one topic is X).
- `fixtures/recorded/sections/{ps,pos,tx,kj}/<new request key>.json`, rebuilt by `build_fixtures.py`; the four old files removed by it.
- The `PS`, `POS`, `TX` and `KJ` lines of `section_profile_expectations.json`.
- Report `docs/program/SECTION-WIDEN-G1-01.md`: decisions table, prompt diffs in words, the added fragments verbatim (a machine-readable block), assumptions an expert would still check, token-guard additions (none), mutation table, test counts, the specimens, forbidden-path proof.

## Required tests

- command: `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages`
- expected: 322 passed (the same count as the base: no test is added or edited).
- command: with the lane stack, `tests/integration/composition/test_analysis_profiles_over_http.py` — expected 4 passed; in `web/`, `npx vitest run tests/unit/analysis-settings` — expected 96 passed.
- command: `PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py --check` — expected `fixtures match`, rc 0.
- mutations: revert one profile version only; revert one expectations line only; delete the paragraph from one prompt (recording kept, then recording rebuilt consistently, where only the fragment check of the report is red); put a numeral, a norm number or a class designation into the paragraph (token guard red).
- The governance one-liner on this file — expected `[]`; `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` and `git diff --check` after the last commit.

## Integration contract

The integrator can rely on: the diff is confined to the allowed paths; the four expectations lines are one-line changes; the other ten recordings are byte-identical after the builder runs; the registry loads the four sections as `reviewed` at `1.2.0` with unchanged identities; the response schema, the two categories and the output contract are unchanged; the shared paragraph is identical in the four prompts except for its scope sentence and the object list of its first condition, so lanes G2 and G3 can reuse it. The report lists what the integrator must decide (the recordings test, the allowlist pattern, the budget term).

## Failure/idempotency/security cases

A prompt edit without a rebuilt recording turns the builder's `--check` and the section recordings test red; a prompt edit with a consistent rebuild passes every existing test (`D-224` residual) and is caught only by the fragment check of the report. A designation not in the pinned source, v1 or the allowlist turns the token guard red. Re-running the builder is idempotent. No security surface: static data.

## Rollback / feature flag

Forward-revert of the lane's commits restores `1.1.0`, the old prompts and the old recordings together. No feature flag: the registry serves a package as soon as it is merged.

## Handoff

- changed files: see the report
- commands/results: see the report
- known limits: nothing was measured on real text; the specimens are synthetic; the positive and negative recordings are not filed as fixtures (P-07)
- integration notes: see the report
