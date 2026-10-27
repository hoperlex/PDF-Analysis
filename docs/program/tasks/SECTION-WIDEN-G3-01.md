# Task SECTION-WIDEN-G3-01 — EOM SS ITP GP: the same-document checks that the gap report marks «reinstatable now», decided one by one and added conservatively under the existing contract

task_id: SECTION-WIDEN-G3-01
status: completed in development candidate

## Outcome

For each of the sections `EOM SS ITP GP` every topic that `ROADMAP-GAP-2026-10-27.md` section 2.3 marks «reinstatable now» has one written decision (W widen, K keep, N narrow, X exclude) with its exact sentence or its reason (`R-146an`, `A-5`, `A-7`; the conservative rules (1) to (6) of `PRODUCTION-WAVE-PW4.md` section 6 and the integrator's decisions (a) to (d) bind). Where the decision is W, the section's prompt asks for it under the existing category `internal_contradiction` with the existing evidence; the profile version moves from `1.1.0` to `1.2.0`, the section's recording is rebuilt and its expectations line follows. Nobody reviews the result (`A-7`): `reviewed` stays a status without human review.

## Depends on

- `SECTION-EOM-FULL-01`, `SECTION-SS-FULL-01`, `SECTION-ITP-FULL-01`, `SECTION-GP-FULL-01` — completed; they produced the `1.1.0` prompts this lane edits.
- `SECTION-WIDEN-G1-01` — completed and merged into the base; its method, decision-table format, specimens and fragment table are copied.
- `SECTION-PROMPT-TOKEN-GUARD-01`, `SECTION-RECORDINGS-01` — completed; the guard (which now accepts a `SECTION-WIDEN-G<n>-01` report as disclosure) and the recordings test the lane must keep green.
- `ROADMAP-GAP-2026-10-27` — completed; it names the topics.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.7.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable (the two categories, the response schema and the output contract of v1 are unchanged)
- migration head: `0033_ar_v3_cite_stage_id`, unchanged (no migration)
- base commit: `d1400994` (`integration/ar-close-1026`, which contains lane G1's merge)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No section, package or route is added or removed. Each section directory under `fixtures/recorded/sections/` keeps exactly one file; for four sections its name is the new request key.

## Captured premise evidence
- premise: the packages, the legacy source, the gap-report cells, the conservative rules, the record's questions, the guard and the recordings test are as the brief says, except P-07 (the recordings test pins one file per directory), which changes how the positive and negative recordings are delivered, and P-08 (the guard now admits a `SECTION-WIDEN-G<n>-01` report), which makes the unit-conversion tokens of rule 4 possible

### P-01 — the four packages, their status and version, the prompt hashes, the recordings and the expectations lines at the base commit
- captured_at: 2026-10-27
- command: `B=d1400994; D=src/auditmanager/analysis/text/profiles; for c in eom ss itp gp; do git show $B:$D/$c/profile.json | python3 -I -c "import json,sys;d=json.load(sys.stdin);print(d['section_code'],d['status'],d['profile_version'])"; git show $B:$D/$c/system_prompt.md | sha256sum | cut -c1-16; git ls-tree --name-only $B fixtures/recorded/sections/$c/; done; git show $B:tests/unit/analysis/text_profiles/section_profile_expectations.json | grep -n '"EOM"\|"SS"\|"ITP"\|"GP"'`
- captured_output:
  ```text
  EOM reviewed 1.1.0
  e3fc00da1d0d4f4d
  fixtures/recorded/sections/eom/966f4f6fd773c064d26b8e27a798967a919be2aa1d0c04ba80497829637d8098.json
  SS reviewed 1.1.0
  3eeda3480fcb343d
  fixtures/recorded/sections/ss/dd6ccee83f95994a6bff7ae3c088fbc56e29d8b4908178c44bea313b89cc70fa.json
  ITP reviewed 1.1.0
  151a9419db94592d
  fixtures/recorded/sections/itp/b9b9d6a8dc98d75291fd0ad13bf1d532204a25270691511d4e6522f61279953b.json
  GP reviewed 1.1.0
  5d6f4e1cd2369d0a
  fixtures/recorded/sections/gp/9dbe139a3b025683b91448992b6890a0a7bd54750e95969a3a396c60b7a8b959.json
  14:    {"code": "EOM", "status": "reviewed", "profile_version": "1.1.0"},
  15:    {"code": "SS", "status": "reviewed", "profile_version": "1.1.0"},
  16:    {"code": "ITP", "status": "reviewed", "profile_version": "1.1.0"},
  17:    {"code": "GP", "status": "reviewed", "profile_version": "1.1.0"},
  ```
- interpretation: read from the base commit with `git show`, so the block stays true after this lane's edits: all four are `reviewed` at `1.1.0` (the state `SECTION-<CODE>-FULL-01` left), each section directory holds exactly one recording (its file name is the request key) and the expectations file has one line per section. A prompt edit changes the recording key and `profile_version` moves with it.

### P-02 — the legacy source is on the host, clean, at the pinned commit, and every pinned hash of the four sections matches
- captured_at: 2026-10-27
- command: `python3 -I -c "import json,subprocess,hashlib;print('HEAD==pinned',subprocess.run(['git','-C','/root/projects/PDF-proverka','rev-parse','HEAD'],capture_output=True,text=True).stdout.strip());print('status clean',subprocess.run(['git','-C','/root/projects/PDF-proverka','status','--short'],capture_output=True,text=True).stdout=='');[print(c.upper(),[hashlib.sha256(subprocess.run(['git','-C','/root/projects/PDF-proverka','show',m['commit']+':'+f['path']],check=True,capture_output=True).stdout).hexdigest()==f['sha256'] for f in m['files']]) for c in ['eom','ss','itp','gp'] for m in [json.load(open(f'src/auditmanager/analysis/text/profiles/{c}/profile.json',encoding='utf-8'))['source']]]"`
- captured_output:
  ```text
  HEAD==pinned 16ba8e5d23e4782550e79355002fde1365f682b7
  status clean True
  EOM [True, True, True, True, True]
  SS [True, True, True, True, True]
  ITP [True, True, True, True, True]
  GP [True, True, True, True, True]
  ```
- interpretation: the repository `PDF-proverka` was only read (`git show`); nothing was written there. The vocabulary of the prompts is checked against these 20 blobs by the token guard.

### P-03 — the gap report's «Reinstatable now» cell of each section (the topics this lane must decide)
- captured_at: 2026-10-27
- command: `python3 -I -c "import re;t=open('docs/program/ROADMAP-GAP-2026-10-27.md',encoding='utf-8').read();t=t[t.index('| Section | Reinstatable now |'):];[print(c[0],'::',c[1]) for c in ([x.strip() for x in l.strip().strip('|').split('|')] for l in t.splitlines()[:20] if re.match(r'^\| (EOM|SS|ITP|GP) \|',l))]"`
- captured_output:
  ```text
  EOM :: a panel on a scheme absent from the specification (ex 7); a load table total against its rows (q2)
  SS :: a ППКП capacity against the number of connected addressable devices (q5); a cable-journal or specification total against its rows (q5); a list that is shorter in one place than in another (q3)
  ITP :: the same load in Гкал/ч, кВт, МВт (q1); a requested value (questionnaire) against the selected one for the exchanger and the pump (ex 15, q3); a scheme item with no specification row (ex 13); a loads total against its circuits (q5); the notations «150/70 со срезкой на 130» and «130/70» as one curve (q2, conditional)
  GP :: the land-balance items against 100 % and against the site area (ex 1 first clause, q1)
  ```
- interpretation: four sections, eleven topics: a load-table total and an omission (EOM); a capacity against a count, a journal or specification total, and a shorter list (SS); the same load in three units, a requested value against the selected one, a scheme item with no specification row, a loads total and a pair of temperature-graph notations (ITP); the land-balance items against 100 % and against the site area (GP). Every one gets a decision in the report.

### P-04 — the conservative rules (1) to (6) that bind this lane, in the wave brief
- captured_at: 2026-10-27
- command: `python3 -I -c "t=open('docs/program/dispatch/PRODUCTION-WAVE-PW4.md',encoding='utf-8').read();print(t[t.index('**Conservative rules'):t.index('**Steps.**')].rstrip())"`
- captured_output:
  ```text
  **Conservative rules (decided by the integrator; there is no expert, `A-7`).** (1) Flag only when both figures are written explicitly in the text and the difference exceeds the rounding of the less precise figure (state the tolerance rule in the prompt in words, not a magic number). (2) Never recompute from a figure the text does not state; never use a value from a drawing, a picture or an OCR guess. (3) Where the section's record names a legal overlap or a stated basis (duration sums with overlapping stages; mass with or without weld metal; heat load «с учётом / без учёта» of a stated item), the prompt says not to flag unless the text states the basis. (4) Physical unit-conversion factors that are definitions, not norms (1 м³/ч = 3.6 · 1 л/с ⇒ 1 л/с = 3.6 м³/ч; 1 Гкал/ч = 1.163 МВт = 1163 кВт), may appear in the prompt and go into `prompt_token_allowlist.json` with a reason; any other number, norm reference, threshold or class designation not in the section's hash-pinned legacy source is still forbidden (`SECTION-PROMPT-TOKEN-GUARD-01`). (5) Notations that the record says experts treat as one value but the text may mean differently (`150/70 со срезкой на 130` vs `130/70`; `С345` vs `09Г2С`; `REI 60` vs `EI 60`) stay **excluded** unless a hash-pinned legacy source states the equivalence. (6) Each topic gets a decision (the existing vocabulary K/N/X plus **W — widen** for these topics) in a table; a topic the lane cannot make conservative is **X** with the reason.
  ```
- interpretation: the rules the report maps its sentences to: (1) both figures written and a tolerance stated in words, (2) never recompute from an unstated figure, (3) a stated basis, (4) conversion definitions only, (5) notations stay excluded, (6) every topic decided, X when it cannot be made conservative. The integrator's decisions (a) omission topics are X, (b) the specimens go into the report, (c) conversion factors may go into the allowlist, (d) a topic that needs an unsourced number is X, bind in addition.

### P-05 — the record's own open questions behind each topic (EOM q2 and q3, SS q3 and q5, ITP q1, q2, q3 and q5, GP q1 and q2)
- captured_at: 2026-10-27
- command: `sed -n 694,695p docs/program/W59-SECTION-PROFILES-01.md; sed -n 752p docs/program/W59-SECTION-PROFILES-01.md; sed -n 754p docs/program/W59-SECTION-PROFILES-01.md; sed -n 808,810p docs/program/W59-SECTION-PROFILES-01.md; sed -n 812p docs/program/W59-SECTION-PROFILES-01.md; sed -n 861,862p docs/program/W59-SECTION-PROFILES-01.md`
- captured_output:
  ```text
  - Считать ли находкой расхождение строки «Итого» таблицы нагрузок или спецификации с суммой строк (сейчас пересчёт исключён)?
  - Щит или аппарат, названный на схеме, но отсутствующий в спецификации, — нужна ли такая находка (в v1 это не категория)?
  - Если перечень сигналов, выводимых на диспетчерский пункт, или состав оборудования точки доступа в одном месте короче, чем в другом, — это противоречие или неполнота, о которой по условию 5 не сообщают?
  - Строка «Итого» спецификации или кабельного журнала против суммы строк, ёмкость ППКП против числа адресных устройств — сейчас пересчёт и такое сравнение исключены; нужна ли какая-либо из этих находок?
  - Тепловые нагрузки в одних местах записаны в Гкал/ч, в других — в кВт или МВт: считать ли значения, совпадающие после перевода единиц, согласованными, и не даст ли округление при переводе ложных находок?
  - Температурный график, записанный в одном месте как «150/70 со срезкой на 130 °C», а в другом как «130/70», — противоречие или один и тот же график в разной записи?
  - Параметры насоса или теплообменника в спецификации (выбранное изделие) и в опросном листе или таблице расчёта (требуемые значения) сейчас считаются разными признаками (условие 2); нужна ли когда-нибудь находка о таком расхождении?
  - Строка «Итого» тепловых нагрузок против суммы нагрузок по контурам — сейчас пересчёт исключён; нужна ли такая находка?
  - Если сумма позиций баланса территории не равна 100 % или площади участка, считать ли это находкой (сейчас арифметический пересчёт исключён)?
  - Площадь участка по ГПЗУ, площадь в границах благоустройства (включая благоустройство за границей участка) и площадь в границах проектирования часто приводятся рядом: не даёт ли пункт о балансе территории систематических ложных находок?
  ```
- interpretation: each is a question the record left open and a `SECTION-<CODE>-FULL-01` lane answered K (ITP q1 answered N: the sentence this lane replaces). Two of the nine (ITP q2, ITP q3) are not widened by this lane; see the decisions table of the report.

### P-06 — the builder agrees with the on-disk recordings and the baseline section test set is green before any edit
- captured_at: 2026-10-27
- command: `PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py --check; PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages 2>&1 | tail -3`
- captured_output:
  ```text
  fixtures match
  322 passed in 2.97s
  ```
- interpretation: captured on the base tree before the first edit (re-running it on the final tree prints `fixtures match` and a larger count, because the report and the allowlist are part of that tree). green at the base (`$BS` is `/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages`; `.venv` is a symlink to the shared virtual environment, untracked). The 322 include the 109 cases of the token guard, which ran against the legacy repository, none skipped.

### P-07 — PREMISE DIFFERS from the brief: the section test pins exactly one file in every section directory and exactly 14 planned recordings, so the positive and negative recordings of the brief cannot be filed under fixtures/recorded/sections
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
- interpretation: line 97 makes a second file (or a subdirectory) in `fixtures/recorded/sections/<code>/` a failure, and lines 156 and 165 pin the builder's plan and the searched directories. The test and `build_fixtures.py` are outside this lane's allowed paths; the integrator's decision (b) says the specimens go into the report, replayed through the real stage, and an integrator lane files them later. This lane rebuilds the four existing recordings only.

### P-08 — the token guard accepts a SECTION-WIDEN-G<n>-01 report as the disclosure of an allowlist entry (changed since lane G1), and the allowlist has eight entries at the base
- captured_at: 2026-10-27
- command: `sed -n 330p tests/unit/analysis/text_profiles/test_prompt_token_guard.py; git show d1400994:tests/unit/analysis/text_profiles/prompt_token_allowlist.json | python3 -I -c "import json,sys;d=json.load(sys.stdin);print(len(d['entries']),'entries:',[(e['section'],e['token'],e['disclosed_by']) for e in d['entries']])"`
- captured_output:
  ```text
          assert re.fullmatch(r"SECTION-(?:[A-Z]+-FULL|WIDEN-G[0-9]+)-01\.md", entry["disclosed_by"]), identity
  8 entries: [('AI', 'КМ', 'SECTION-AI-FULL-01.md'), ('EOM', 'PE-проводника', 'SECTION-EOM-FULL-01.md'), ('GP', '0,000', 'SECTION-GP-FULL-01.md'), ('PB', '123-ФЗ', 'SECTION-PB-FULL-01.md'), ('PB', '13130', 'SECTION-PB-FULL-01.md'), ('PB', 'ПБ', 'SECTION-PB-FULL-01.md'), ('POS', 'ИТР', 'SECTION-POS-FULL-01.md'), ('PS', 'ГПЗУ', 'SECTION-PS-FULL-01.md')]
  ```
- interpretation: the pattern admits `SECTION-WIDEN-G3-01.md` (integration commit `fa7f2ae6`), and the guard requires the named report to exist and to contain the token. So a unit-conversion definition that this lane needs can go into the allowlist, and the report must name each token.

### P-09 — the grounding gate: every evidence item of an observation must resolve, so a reply that quotes the total and the rows publishes only if all quotes are verbatim
- captured_at: 2026-10-27
- command: `sed -n 3,6p src/auditmanager/findings/grounding.py`
- captured_output:
  ```text
  An observation is published as a finding only when **every** one of its evidence items
  resolves on all three checks of P02 §5.1:

  1. the declared ``(char_start, char_end)`` interval lies inside the declared page's
  ```
- interpretation: the schema (`evidence`, `minItems` 1, no maximum) carries a total and its rows, or a capacity and a count, as quotes; it has no way to carry an absence, which is why the omission topics are decided X in the report.

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
- interpretation: the budget subtracts the AR bundle's prompt, so a section prompt's extra characters are outside the budget's arithmetic; this is a property of `budget.py` (lane `SECTION-CHUNKED-ANALYSIS-01` owns it), not changed here. This lane keeps its addition compact: 2,394 to 2,827 characters per prompt (lane G1's were 2,701 to 2,834).

### P-11 — where condition 5, the exclusion paragraph and the ITP heat-load sentence sit in the four prompts at the base commit
- captured_at: 2026-10-27
- command: `for c in eom ss itp gp; do git show d1400994:src/auditmanager/analysis/text/profiles/$c/system_prompt.md | grep -n 'Ты не решаешь\|Ты НЕ проверяешь\|между собой не сравнивай' | sed "s/^/$c: /"; done`
- captured_output:
  ```text
  eom: 59:   Ты не решаешь, что должно было быть указано.
  eom: 61:Ты НЕ проверяешь соответствие внешним нормам (СП, СНиП, ГОСТ, ПУЭ, техническим
  ss: 77:   Ты не решаешь, что должно было быть указано.
  ss: 79:Ты НЕ проверяешь соответствие внешним нормам (СП, СНиП, ГОСТ, техническим регламентам),
  itp: 27:  между собой не сравнивай: пересчёт единиц и округление при нём — вычисление, которого
  itp: 73:   Ты не решаешь, что должно было быть указано.
  itp: 75:Ты НЕ проверяешь соответствие внешним нормам (СП, СНиП, ГОСТ, Правилам коммерческого
  gp: 74:   Ты не решаешь, что должно было быть указано.
  gp: 76:Ты НЕ проверяешь соответствие внешним нормам (СП, СНиП, ГОСТ, СанПиН, нормативам
  ```
- interpretation: condition 5 ends two lines before a paragraph that bans recalculation in the same words in every section. The new paragraph goes between them and the ban gets one exception clause. Only the ITP prompt carries the sentence «между собой не сравнивай» (the `ITP-1` narrowing of `SECTION-ITP-FULL-01`), and this lane replaces it.

### P-12 — the ITP pinned source holds the unit kW but neither Гкал/ч nor МВт nor any conversion factor, and its example total equals the sum of its three circuits
- captured_at: 2026-10-27
- command: `python3 -I -c "import json,subprocess,re;m=json.load(open('src/auditmanager/analysis/text/profiles/itp/profile.json',encoding='utf-8'))['source'];t=''.join(subprocess.run(['git','-C','/root/projects/PDF-proverka','show',m['commit']+':'+f['path']],check=True,capture_output=True).stdout.decode('utf-8') for f in m['files']);print({w:t.count(w) for w in ['МВт','Гкал','1163','1,163','кВт']});print(re.findall(r'(heat_load_\w+) \| [^|]+\| (\d+)',t))"`
- captured_output:
  ```text
  {'МВт': 0, 'Гкал': 0, '1163': 0, '1,163': 0, 'кВт': 4}
  [('heat_load_heating_kW', '850'), ('heat_load_dhw_kW', '420'), ('heat_load_ventilation_kW', '180'), ('heat_load_total_kW', '1450')]
  ```
- interpretation: `Гкал`, `МВт` and both spellings of the factor occur in none of the five files, so the token guard needs allowlist entries for `1,163`, `1163` and `МВт` (`кВт` is sourced). The source's example parameter template writes 850 + 420 + 180 = 1450 kW, a total that is the sum of its circuits (a template value, not a document); that is the only support the pinned source gives for the loads-total topic.

### P-13 — the lane G1 paragraph is in the base: four prompts carry the sentence that this lane's fragments reuse, and the AI prompt does not
- captured_at: 2026-10-27
- command: `for c in ai ps pos tx kj; do git show d1400994:src/auditmanager/analysis/text/profiles/$c/system_prompt.md | python3 -I -c "import sys;t=' '.join(sys.stdin.read().split());print('$c',len(t),'Единственное сложение, которое тебе разрешено' in t)"; done`
- captured_output:
  ```text
  ai 5996 False
  ps 9267 True
  pos 9252 True
  tx 8768 True
  kj 8857 True
  ```
- interpretation: G1's paragraph is present in `ps pos tx kj` (True) and absent from `ai` (False); the base already contains lane G1's merge, so this lane copies its method and reuses its shared sentences byte for byte where its text is identical.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/text/profiles/eom/**`
- `src/auditmanager/analysis/text/profiles/ss/**`
- `src/auditmanager/analysis/text/profiles/itp/**`
- `src/auditmanager/analysis/text/profiles/gp/**`
- `fixtures/recorded/sections/eom/**`
- `fixtures/recorded/sections/ss/**`
- `fixtures/recorded/sections/itp/**`
- `fixtures/recorded/sections/gp/**`
- `tests/unit/analysis/text_profiles/section_profile_expectations.json`
- `tests/unit/analysis/text_profiles/prompt_token_allowlist.json`
- `docs/program/tasks/SECTION-WIDEN-G3-01.md`
- `docs/program/SECTION-WIDEN-G3-01.md`

`section_profile_expectations.json` is allowed for the lines of `EOM SS ITP GP` only; `prompt_token_allowlist.json` for append-only entries with a reason (three were needed, all ITP).

## Forbidden hotspots

The other groups' files (`AI PS POS TX KJ KM OV VK PT PB`), `docs/program/W59-SECTION-PROFILES-01.md`, `docs/program/SECTION-REVIEW-LEDGER-01.md`, the registry, `prompt.py`, `response.py`, `stage.py`, `budget.py`, `docs/program/P02_LOCK.json`, `contracts/**`, migrations, `web/**`, `infra/**`, `tests/integration/sections/**`, `tests/unit/analysis/text_profiles/test_prompt_token_guard.py`, `fixtures/recorded/sections/build_fixtures.py`, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the rulings, `origin/main`, tags and the deployment host.

## Non-goals

- No new category, field, severity or norm; no widening beyond the decided topics.
- No number, norm reference, threshold or class designation outside the section's pinned legacy source, except the unit-conversion definition of rule 4 (`1 Гкал/ч = 1,163 МВт = 1163 кВт`), disclosed in the allowlist; no claim that an expert or the owner verified anything (`A-7`).
- No omission check (decision X for the EOM, SS and ITP omission topics), no check of a requested value against a selected one, no comparison of the two notations of a temperature graph, no recomputation of a design power or of a count the text does not write.
- No change to AR, to the web label for `reviewed`, to `budget.py`, to the recordings test or the builder; no new identity, no migration, no model call, no push, no tag.

## Deliverables

- `src/auditmanager/analysis/text/profiles/{eom,ss,itp,gp}/system_prompt.md`: one paragraph after condition 5 (SS: also the capacity rule; ITP: also the unit rule and the replacement of one sentence of the heat-load bullet) and the exclusion paragraph's exception clauses; `profile.json`: `profile_version` `1.2.0`.
- `fixtures/recorded/sections/{eom,ss,itp,gp}/<new request key>.json`, rebuilt by `build_fixtures.py`; the four old files removed by it.
- The `EOM`, `SS`, `ITP` and `GP` lines of `section_profile_expectations.json`.
- Three append-only entries of `prompt_token_allowlist.json` (`ITP`: `1,163`, `1163`, `МВт`).
- Report `docs/program/SECTION-WIDEN-G3-01.md`: decisions table, prompt diffs in words, the added fragments verbatim (a machine-readable block), the specimens with their replay snippet, assumptions an expert would still check, token additions, mutation table, test counts, forbidden-path proof.

## Required tests

- command: `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages`
- expected: 328 passed (the base's 322 plus six token-guard cases, two per new allowlist line; no test is added or edited).
- command: with the lane stack, `tests/integration/composition/test_analysis_profiles_over_http.py` — expected 4 passed; in `web/`, `npx vitest run tests/unit/analysis-settings` — expected 96 passed.
- command: `PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py --check` — expected `fixtures match`, rc 0.
- mutations: revert one profile version only; revert one expectations line only; delete the paragraph from one prompt (recording kept, then recording rebuilt consistently, where only the fragment check of the report is red: the `D-224` residual); put a numeral, a norm number or a class designation into the paragraph; remove an allowlist entry; make the report forget a token.
- The governance one-liner on this file — expected `[]`; `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` and `git diff --check` after the last commit.

## Integration contract

The integrator can rely on: the diff is confined to the allowed paths; the four expectations lines are one-line changes; the other ten recordings are byte-identical after the builder runs; the registry loads the four sections as `reviewed` at `1.2.0` with unchanged identities; the response schema, the two categories and the output contract are unchanged; the fragment table of the report is the machine-readable list of added sentences for `SECTION-PROMPT-SENTENCE-GUARD-01`; the allowlist gained exactly three lines, each disclosed by the report. The report lists what the integrator must decide (filing the specimens, the superseded `ITP-1` ledger fragment, the budget term).

## Failure/idempotency/security cases

A prompt edit without a rebuilt recording turns the builder's `--check` and the section recordings test red; a prompt edit with a consistent rebuild passes every existing test (`D-224` residual) and is caught only by the fragment check of the report. A designation not in the pinned source, v1 or the allowlist turns the token guard red; an allowlist line whose report does not mention the token turns it red. Re-running the builder is idempotent. No security surface: static data.

## Rollback / feature flag

Forward-revert of the lane's commits restores `1.1.0`, the old prompts, the old recordings and the old allowlist together. No feature flag: the registry serves a package as soon as it is merged.

## Handoff

- changed files: see the report
- commands/results: see the report
- known limits: nothing was measured on real text; the specimens are synthetic and not filed as fixtures (P-07)
- integration notes: see the report
