# Task SECTION-REVIEW-LEDGER-01 — the ledger of the 14 section decisions and the two stale statements about the ПБ and W59 records

task_id: SECTION-REVIEW-LEDGER-01
status: completed in development candidate

## Outcome

One document, `docs/program/SECTION-REVIEW-LEDGER-01.md`, lists the 14 non-AR section profiles in one table (code, title, `profile_version`, status, the K / N / X decisions of the lane, every prompt change in one sentence with the added fragment quoted, the assumptions an expert would still want to check, and the link to the lane's report), states above the table that `reviewed` means no human reviewed it (`R-146ag`, `A-7`), and states below it the reopen triggers of `A-7` and what is pinned by what (the status and version by the expectations file and the pin tests, the prompt text only by the recording key: `D-224`). Two living statements that the section lanes left stale are corrected: the recordings README on the ПБ recording, and the top of the W59 record (one dated note). Every number in the ledger is reproduced by a command printed here.

## Depends on

- `PRODUCTION-READINESS-PLAN-01` — completed; it holds the accepted-risk register (`A-5`, `A-7`).
- `SECTION-AI-FULL-01`, `SECTION-PS-FULL-01`, `SECTION-POS-FULL-01`, `SECTION-TX-FULL-01`, `SECTION-KJ-FULL-01`, `SECTION-KM-FULL-01`, `SECTION-OV-FULL-01` — completed; their reports are the ledger's sources.
- `SECTION-VK-FULL-01`, `SECTION-PT-FULL-01`, `SECTION-EOM-FULL-01`, `SECTION-SS-FULL-01`, `SECTION-ITP-FULL-01`, `SECTION-GP-FULL-01`, `SECTION-PB-FULL-01` — completed; the same.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.5.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable
- migration head: `0033`, unchanged (P-11 prints it; no migration)
- base commit: `2d8fa1392f46eea06b964aeaa419b6e3b2d2a390` (integration/ar-close-1026, with all 14 section profiles `reviewed`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No section, package, route or error code is added or removed. The ledger enumerates the 14 packages that already exist; the registry order is printed in P-02.

## Captured premise evidence

- premise: the tree at the base commit holds 14 `reviewed` profiles at `1.1.0`, 14 lane reports, the owner's wording of `R-146ag` and `A-7`, the two stale statements, and the pins described in the ledger; captured before any edit, with the base commit named wherever a later commit could change the output

### P-01 — the base tree, its branch and the commit of the web label

- captured_at: 2026-10-26
- command: `git log -1 --format='%H %s' 2d8fa1392f46eea06b964aeaa419b6e3b2d2a390; git branch --show-current; git log -1 --format='%h %s' 607ee47a; git merge-base --is-ancestor 607ee47a 2d8fa1392f46eea06b964aeaa419b6e3b2d2a390 && echo web-label-commit-is-an-ancestor-of-the-base`
- captured_output:
  ```text
  2d8fa1392f46eea06b964aeaa419b6e3b2d2a390 docs, test(e2e): head 0033 stated; the live journey asserts a reviewed row (no draft row is left); D-226 and D-227
  agent/section-review-ledger-01
  607ee47a fix(web): the reviewed profile label no longer claims expert verification (R-146ag, A-7)
  web-label-commit-is-an-ancestor-of-the-base
  ```
- interpretation: The ledger is written on the exact tip named in the brief, on the lane branch, and the commit that corrected the web label is part of that tip.

### P-02 — status, version, title and pinned sources of the 14 profiles, in the registry order

- captured_at: 2026-10-26
- command: `sed -n 93p src/auditmanager/analysis/text/profile_registry.py; python3 -I -c "import json;[print(c,*(lambda p:(p['profile_version'],p['status'],p['source'] and len(p['source']['files']),p['source'] and p['source']['commit'][:8],p['title_ru']))(json.load(open('src/auditmanager/analysis/text/profiles/'+c.lower()+'/profile.json',encoding='utf-8')))) for c in 'AI PS POS TX KJ KM OV VK PT EOM SS ITP GP PB'.split()]"`
- captured_output:
  ```text
      "AR", "AI", "PS", "POS", "TX", "KJ", "KM", "OV", "VK", "PT", "EOM", "SS", "ITP", "GP", "PB",
  AI 1.1.0 reviewed 5 16ba8e5d Архитектурные решения (интерьер)
  PS 1.1.0 reviewed 5 16ba8e5d Пояснительная записка
  POS 1.1.0 reviewed 5 16ba8e5d Проект организации строительства
  TX 1.1.0 reviewed 5 16ba8e5d Технологические решения
  KJ 1.1.0 reviewed 5 16ba8e5d Конструкции железобетонные
  KM 1.1.0 reviewed 5 16ba8e5d Конструкции металлические
  OV 1.1.0 reviewed 5 16ba8e5d Отопление, вентиляция и кондиционирование
  VK 1.1.0 reviewed 5 16ba8e5d Водоснабжение и канализация
  PT 1.1.0 reviewed 5 16ba8e5d Противопожарный водопровод
  EOM 1.1.0 reviewed 5 16ba8e5d Электроснабжение и электрооборудование
  SS 1.1.0 reviewed 5 16ba8e5d Слаботочные системы
  ITP 1.1.0 reviewed 5 16ba8e5d Индивидуальный тепловой пункт
  GP 1.1.0 reviewed 5 16ba8e5d Генеральный план
  PB 1.1.0 reviewed None None Пожарная безопасность
  ```
- interpretation: All fourteen packages read `reviewed` at `1.1.0`; thirteen pin five legacy files at one legacy commit and PB pins none (`None`). The order of the ledger is the registry order after AR, which has no package. The ledger's columns for title, version and status are these values.

### P-03 — the K / N / X rows of the 14 reports, by class

- captured_at: 2026-10-26
- command: `awk -F'|' 'FNR==1{f=0;t=0} /^## /{f=($0=="## Decisions");next} !f{next} /^\|/{if(!t){t=1;cross=($5 ~ /specific note/);next} if($2 ~ /^ *-+ *$/)next; if($4 ~ /^ *\*\*[KNX]/){d=$4;gsub(/[ *]/,"",d);d=substr(d,1,1);id=$2;gsub(/ /,"",id);k=(cross||id ~ /^C-?[0-9]/)?"c":(id ~ /^A(-[0-9]+)?$/?"a":"q");n[FILENAME,k d]++;n[FILENAME,"all" d]++;r[FILENAME]++;if(!(FILENAME in o)){o[FILENAME]=++m;nm[m]=FILENAME}}next} {t=0} END{for(i=1;i<=m;i++){F=nm[i];c=F;sub(/.*SECTION-/,"",c);sub(/-FULL.*/,"",c);printf "%s rows=%d all K%d N%d X%d | questions K%d N%d X%d | audit K%d N%d X%d | cross-section K%d N%d X%d\n",c,r[F],n[F,"allK"],n[F,"allN"],n[F,"allX"],n[F,"qK"],n[F,"qN"],n[F,"qX"],n[F,"aK"],n[F,"aN"],n[F,"aX"],n[F,"cK"],n[F,"cN"],n[F,"cX"];R+=r[F];AK+=n[F,"allK"];AN+=n[F,"allN"];AX+=n[F,"allX"];QK+=n[F,"qK"];QN+=n[F,"qN"];QX+=n[F,"qX"];UK+=n[F,"aK"];UN+=n[F,"aN"];UX+=n[F,"aX"];CK+=n[F,"cK"];CN+=n[F,"cN"];CX+=n[F,"cX"]} printf "TOTAL files=%d rows=%d all K%d N%d X%d | questions K%d N%d X%d | audit K%d N%d X%d | cross-section K%d N%d X%d\n",m,R,AK,AN,AX,QK,QN,QX,UK,UN,UX,CK,CN,CX}' docs/program/SECTION-{AI,PS,POS,TX,KJ,KM,OV,VK,PT,EOM,SS,ITP,GP,PB}-FULL-01.md`
- captured_output:
  ```text
  AI rows=9 all K7 N2 X0 | questions K3 N1 X0 | audit K0 N1 X0 | cross-section K4 N0 X0
  PS rows=9 all K7 N2 X0 | questions K3 N2 X0 | audit K0 N0 X0 | cross-section K4 N0 X0
  POS rows=8 all K6 N2 X0 | questions K2 N2 X0 | audit K0 N0 X0 | cross-section K4 N0 X0
  TX rows=10 all K9 N1 X0 | questions K5 N1 X0 | audit K0 N0 X0 | cross-section K4 N0 X0
  KJ rows=11 all K9 N2 X0 | questions K5 N2 X0 | audit K0 N0 X0 | cross-section K4 N0 X0
  KM rows=11 all K10 N1 X0 | questions K6 N1 X0 | audit K0 N0 X0 | cross-section K4 N0 X0
  OV rows=11 all K8 N3 X0 | questions K4 N2 X0 | audit K0 N1 X0 | cross-section K4 N0 X0
  VK rows=11 all K9 N2 X0 | questions K5 N1 X0 | audit K0 N1 X0 | cross-section K4 N0 X0
  PT rows=12 all K11 N1 X0 | questions K6 N1 X0 | audit K1 N0 X0 | cross-section K4 N0 X0
  EOM rows=10 all K9 N1 X0 | questions K4 N1 X0 | audit K1 N0 X0 | cross-section K4 N0 X0
  SS rows=11 all K9 N2 X0 | questions K5 N1 X0 | audit K0 N1 X0 | cross-section K4 N0 X0
  ITP rows=10 all K8 N2 X0 | questions K4 N1 X0 | audit K0 N1 X0 | cross-section K4 N0 X0
  GP rows=10 all K7 N3 X0 | questions K3 N2 X0 | audit K1 N0 X0 | cross-section K3 N1 X0
  PB rows=16 all K15 N1 X0 | questions K10 N1 X0 | audit K1 N0 X0 | cross-section K4 N0 X0
  TOTAL files=14 rows=149 all K124 N25 X0 | questions K65 N19 X0 | audit K4 N5 X0 | cross-section K55 N1 X0
  ```
- interpretation: Each report's table rows under `## Decisions` that carry a decision, counted once and split into the section's own questions (q), the designation audit (a, an id `A` or `A-<n>`) and the cross-section questions (c: a table whose header ends in `specific note`, or an id `C<n>` / `C-<n>`). This is the second of two independent counts: a Python parser written first gave the same 14 lines and the same total, and the ledger checker below recounts them a third way from the ledger's own cells.

### P-04 — the prompt changes: the commits that touched each system_prompt.md and the size of the diff against the draft

- captured_at: 2026-10-26
- command: `for c in ai ps pos tx kj km ov vk pt eom ss itp gp pb; do p=src/auditmanager/analysis/text/profiles/$c/system_prompt.md; b=e027b0d9; [ $c = pb ] && b=bc574621; echo "$c last=$(git log -1 --format=%h 2d8fa1392f46eea06b964aeaa419b6e3b2d2a390 -- $p) commits=$(git log --oneline 2d8fa1392f46eea06b964aeaa419b6e3b2d2a390 -- $p | wc -l) draft=$b added/removed=$(git diff --numstat $b 2d8fa1392f46eea06b964aeaa419b6e3b2d2a390 -- $p | cut -f1,2 | tr '\t' '/')"; done`
- captured_output:
  ```text
  ai last=55041a3c commits=2 draft=e027b0d9 added/removed=8/5
  ps last=ca5b18d1 commits=2 draft=e027b0d9 added/removed=5/2
  pos last=339b45ac commits=2 draft=e027b0d9 added/removed=12/5
  tx last=3bf852be commits=2 draft=e027b0d9 added/removed=5/1
  kj last=43c957e0 commits=2 draft=e027b0d9 added/removed=8/2
  km last=850514b2 commits=2 draft=e027b0d9 added/removed=5/1
  ov last=17e9f551 commits=2 draft=e027b0d9 added/removed=10/5
  vk last=91a2ff33 commits=2 draft=e027b0d9 added/removed=7/4
  pt last=b71a7ec5 commits=2 draft=e027b0d9 added/removed=4/1
  eom last=4ccc8880 commits=2 draft=e027b0d9 added/removed=3/0
  ss last=b1d7573a commits=2 draft=e027b0d9 added/removed=8/3
  itp last=521cd0ad commits=2 draft=e027b0d9 added/removed=4/2
  gp last=02f30999 commits=2 draft=e027b0d9 added/removed=7/4
  pb last=a6484e75 commits=2 draft=bc574621 added/removed=5/5
  ```
- interpretation: Every prompt has exactly two commits: its draft (`e027b0d9` for the thirteen legacy ones, `bc574621` for PB) and the section lane's commit named in the ledger. The ledger's prompt column is the word-level difference between those two versions; the checker below proves each quoted fragment against them.

### P-05 — the assumption lists: how many items each report carries

- captured_at: 2026-10-26
- command: `for c in AI PS POS TX KJ KM OV VK PT EOM SS ITP GP PB; do printf '%s ' $c; awk '/^## (Assumptions an expert would still want to check|Limits and what a domain expert would still check)$/{f=1;next} /^## /{f=0} f && /^([0-9]+\.|-) /{n++} END{print n}' docs/program/SECTION-$c-FULL-01.md; done`
- captured_output:
  ```text
  AI 6
  PS 7
  POS 6
  TX 7
  KJ 5
  KM 7
  OV 8
  VK 7
  PT 7
  EOM 7
  SS 8
  ITP 7
  GP 7
  PB 9
  ```
- interpretation: The lists the ledger copies: 6, 7, 6, 7, 5, 7, 8, 7, 7, 7, 8, 7, 7 and 9 items. Only PS names its section differently (`Limits and what a domain expert would still check`), and only KJ uses bullets instead of numbers.

### P-06 — the wording of the ruling `R-146ag` and of the accepted risks `A-5` and `A-7`

- captured_at: 2026-10-26
- command: `grep -n '^| .R-146ag. ' docs/program/OWNER_RULINGS_2026-09-17.md; grep -n '^| A-[57] ' docs/program/PRODUCTION-READINESS-PLAN-01.md`
- captured_output:
  ```text
  1791:| `R-146ag` | **What a «full version» of a section is** (narrows `R-146v`). Chosen: «Дописать и сразу перевести в reviewed без приёмки». A section leaves `draft` when a lane has answered every open question of its record in `W59-SECTION-PROFILES-01.md` with a written decision, rebuilt the section's recording and the expectations line says `reviewed`; **neither an expert nor the owner reviews it**. An independent read-only judge reads the decisions (quality control, not acceptance). **Accepted risk `A-7`:** the status `reviewed` on these 14 profiles carries no human review; it must not be read as expert verification anywhere (reports, release notes, the ledger of decisions). Who the experts are (`OD-18`) stays open and becomes relevant only if the owner later wants a human review. |
  239:| A-5 | When the 14 sections become full, the quality of their output on real text is unmeasured: a section leaves `draft` when an expert has reviewed its profile, no non-synthetic field case is required, recorded cases stay synthetic. | `R-146v` (not the recommended option) | the first section whose real-text output an expert rejects, or the first client complaint |
  242:| A-7 | The status `reviewed` on the 14 section profiles carries no human review (neither an expert nor the owner); it is the outcome of a lane's written decisions on the open questions of each record and a judge's read. | `R-146ag` (not the recommended option) | the first section whose real-text output a human rejects, any client-facing statement that calls these profiles verified, or the owner naming experts (`OD-18`) |
  ```
- interpretation: The status sentence of the ledger, the quoted owner words «Дописать и сразу перевести в reviewed без приёмки» and the reopen triggers of `A-7` and `A-5` are copied from these lines.

### P-07 — what pins the status, the version, the prompt text and the recording

- captured_at: 2026-10-26
- command: `grep -rl section_profile_expectations tests web/tests | sort; grep -n 'V1_QUESTION in body\|V1_CATEGORIES in body\|body.endswith(V1_OUTPUT_CONTRACT)\|for fragment in V1_CONDITIONS\|def test_the_pb_prompt\|ALLOWED_PB_NUMBERS =' tests/unit/analysis/text_profiles/test_text_profile_packages.py; PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py --check; for d in fixtures/recorded/sections/*/; do echo "$d $(ls $d | wc -l)"; done`
- captured_output:
  ```text
  tests/integration/composition/test_analysis_profiles_over_http.py
  tests/unit/analysis/test_text_profile_registry.py
  tests/unit/analysis/text_profiles/section_profile_expectations.json
  tests/unit/analysis/text_profiles/test_section_profile_expectations.py
  tests/unit/analysis/text_profiles/test_text_profile_packages.py
  web/tests/unit/analysis-settings/analysis-settings.test.ts
  151:    assert all(fragment in SYSTEM_PROMPT for fragment in V1_CONDITIONS)
  291:        assert V1_QUESTION in body, code
  292:        assert V1_CATEGORIES in body, code
  293:        assert body.endswith(V1_OUTPUT_CONTRACT), code
  295:        for fragment in V1_CONDITIONS:
  312:ALLOWED_PB_NUMBERS = frozenset({"123", "13130"})
  328:def test_the_pb_prompt_covers_each_named_fire_safety_area() -> None:
  335:def test_the_pb_prompt_invents_no_requirement_number() -> None:
  fixtures match
  fixtures/recorded/sections/ai/ 1
  fixtures/recorded/sections/ar_specification/ 2
  fixtures/recorded/sections/eom/ 1
  fixtures/recorded/sections/gp/ 1
  fixtures/recorded/sections/itp/ 1
  fixtures/recorded/sections/kj/ 1
  fixtures/recorded/sections/km/ 1
  fixtures/recorded/sections/ov/ 1
  fixtures/recorded/sections/pb/ 1
  fixtures/recorded/sections/pos/ 1
  fixtures/recorded/sections/ps/ 1
  fixtures/recorded/sections/pt/ 1
  fixtures/recorded/sections/ss/ 1
  fixtures/recorded/sections/tx/ 1
  fixtures/recorded/sections/vk/ 1
  ```
- interpretation: Six files read the expectations file (the file itself, its own guard, the package test, the registry test, the HTTP listing test and the web test). The package test reads the v1 question, categories, the opening of each condition and the output contract in every prompt, and for PB the area markers and the numerals; nothing in it reads a sentence that a lane added. The builder agrees with the one recording of each of the 14 sections (one file per directory), and the recording's file name is the request key.

### P-08 — the debt row `D-178` / `D-224` and the check that `D-224` names

- captured_at: 2026-10-26
- command: `grep -n '^| \*\*D-224' docs/program/DEBT_REGISTER.md | cut -c1-560; grep -rnE 'prompt.*pinned source|numerals' tests/unit/analysis/text_profiles | head`
- captured_output:
  ```text
  141:| **D-224** | **Section profile edits are pinned only by their recording key.** The narrowing sentences that the section lanes added to `system_prompt.md` (AI, PS, KJ and the lanes that follow) are held by no test that reads the sentence: only the hash of the prompt bytes inside the rebuilt recording pins them, and any later edit with a consistent rebuild passes. A cross-section guard that checks every numeral and class designation of each prompt against its pinned legacy source would also keep invented numbers out (the AI lane found `(Г1–Г4)` ab
  tests/unit/analysis/text_profiles/test_text_profile_packages.py:336:    """No clause, limit or class threshold: the only numerals are the two norm identifiers."""
  ```
- interpretation: `D-224` states that only the recording key pins a lane's sentences and that any later edit with a consistent rebuild passes. Its own check finds nothing but the docstring of the PB-only numerals test, so the cross-section guard that it asks for does not exist.

### P-09 — the web label for `reviewed`

- captured_at: 2026-10-26
- command: `grep -n 'reviewed:' web/src/entities/analysis-profile/model/presentation.ts; grep -n 'проверка человеком' web/tests/unit/analysis-settings/analysis-settings.test.ts`
- captured_output:
  ```text
  18:  reviewed: 'рабочая версия, проверка человеком не проводилась',
  270:    expect(row(table(withProfile('POS', { status: 'reviewed' })), 'POS')).toContain('проверка человеком не проводилась');
  ```
- interpretation: The label and the test that holds it say that no human checked a `reviewed` profile; the ledger cites both.

### P-10 — the stale lines before the edit: the ПБ section of the recordings README and the top of the W59 record

- captured_at: 2026-10-26
- command: `git show 2d8fa1392f46eea06b964aeaa419b6e3b2d2a390:fixtures/recorded/sections/README.md | sed -n 63,68p; git show 2d8fa1392f46eea06b964aeaa419b6e3b2d2a390:docs/program/W59-SECTION-PROFILES-01.md | sed -n 1,3p`
- captured_output:
  ```text
  ## The ПБ recording is for a draft profile

  `pb/` answers the request of the **authored, draft** ПБ profile (`PB-PROFILE-01`: no legacy source, no
  expert review). Its reply says only that the three defects seeded in the AR corpus (two fire-resistance
  degrees, two exit counts, one unfilled window type) are reported in fire-safety vocabulary; it is not
  evidence that the ПБ profile finds anything in a real fire-safety volume.
  # W59-SECTION-PROFILES-01 — draft text profiles for 13 non-AR sections

  **Base:** `a1a25ebc` on `integration/night-1020` (the task's frozen `origin/dev`
  ```
- interpretation: The README still calls the ПБ profile «authored, draft» with «no expert review» and the W59 record still opens with a title that says `draft` and no note. These are the lines edited, and only these.

### P-11 — frozen inputs: the API contract version and the migration head

- captured_at: 2026-10-26
- command: `python3 -I -c "import json;print(json.load(open('contracts/api/v1/openapi.json'))['info']['version'])"; ls db/migrations/versions | sort | tail -1`
- captured_output:
  ```text
  1.5.0
  20261026_0033_ar_v3_cite_stage_id.py
  ```
- interpretation: The contract is `1.5.0` and the newest migration file is `0033`; this task touches neither.

### P-12 — stale living statements outside the allowed paths (reported, not edited)

- captured_at: 2026-10-26
- command: `grep -n 'draft' docs/program/CURRENT_STATE.md | cut -c1-150; grep -n '^| \*\*D-178' docs/program/DEBT_REGISTER.md | cut -c1-200`
- captured_output:
  ```text
  63:  through a text-profile registry — AR, 13 draft legacy-ported profiles and
  64:  an authored draft for ПБ — and refuse an unclassified version or a section
  95:  more. Expert review of the draft profiles remains open.
  95:| **D-178** | the 14 section text profiles (the 13 legacy-ported ones of `W59-SECTION-PROFILES-01` and PB, `bc574621`) are `draft`: no expert review, no field cases, no recorded responses from a re
  ```
- interpretation: Three lines of `docs/program/CURRENT_STATE.md` and the row `D-178` of `docs/program/DEBT_REGISTER.md` still say the profiles are `draft`; both files belong to the integrator and are listed in the handoff, not edited here.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

The 14 reports are immutable records of their lanes and are read, not edited. The one note added to the W59 record is a dated pointer under its title; the text below it stays as it was.

## Publication authority

- development_target: none
- origin_main_authority: none

Nothing is pushed or tagged by this task; the integrator merges the branch.

## Allowed paths

- `docs/program/SECTION-REVIEW-LEDGER-01.md`
- `docs/program/tasks/SECTION-REVIEW-LEDGER-01.md`
- `docs/program/W59-SECTION-PROFILES-01.md`
- `fixtures/recorded/sections/README.md`

`docs/program/W59-SECTION-PROFILES-01.md` is allowed for the one dated note under its title. `fixtures/recorded/sections/README.md` is allowed for the lines about the ПБ recording only (the heading and the paragraph under it, lines 63 to 68 at the base).

## Forbidden hotspots

Every other path: the 14 reports (SECTION-<CODE>-FULL-01.md in docs/program) and their task files, every profile.json, system_prompt.md and open_questions.md under `src/auditmanager/analysis/text/profiles/**`, `tests/**`, the other fixtures and `fixtures/recorded/sections/build_fixtures.py`, `contracts/**`, migrations, `web/**`, `infra/**`, `docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`, the plan, the rulings, the ADRs, root dependency and lock files, origin/main, tags and the deployment host.

## Non-goals

- No change to any profile, prompt, test, fixture or contract; no re-judging of any lane's decision; no new decision about any section.
- No claim that anyone verified anything: the ledger repeats, in its first lines, that nobody did (`R-146ag`, `A-7`).
- No new guard for `D-224` (that is a code task); the ledger only states that none exists.
- No edit of `docs/program/CURRENT_STATE.md` or `docs/program/DEBT_REGISTER.md`; the stale lines found there are listed under Handoff for the integrator.
- No push, no tag, no container command, no model call, no process killed.

## Deliverables

- `docs/program/SECTION-REVIEW-LEDGER-01.md`: the status sentence, the table of 14 rows, the totals, the reopen triggers of `A-7`, the list of what is pinned by what.
- `docs/program/tasks/SECTION-REVIEW-LEDGER-01.md`: this file, with the premise evidence above and the checks below. There is no separate report; this file and the ledger are the deliverables.
- `docs/program/W59-SECTION-PROFILES-01.md`: one dated note under the title.
- `fixtures/recorded/sections/README.md`: the ПБ recording section now says the profile is `reviewed` without a human review and the recording is synthetic, not field evidence.

## Required tests

- Ledger checker (script text below): `python3 -I check_ledger.py <repo-root>` — expected: 14 rows in registry order, 149 decision rows, K 124 / N 25 / X 0, 38 quotes proven, 30 regions of the draft-to-current word diff of the prompts each touched by a quote, 98 assumption items equal to the reports', `PROBLEMS: none`, exit 0.
- Path checker (script text below): `python3 -I check_paths.py <repo-root> docs/program/SECTION-REVIEW-LEDGER-01.md docs/program/tasks/SECTION-REVIEW-LEDGER-01.md` — expected: `MISSING: none`, exit 0.
- The governance one-liner on this file — expected: `[]`.
- `git diff --check` — expected: no output, exit 0.
- `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` on the committed tree — expected: all passed.
- Mutation proof that both checkers can fail: each mutation was applied to the ledger, the checker run, and the ledger restored (the last row shows the restored ledger green).

| Mutation | Result |
|---|---|
| AI count `K 7` changed to `K 8` | exit 1, `AI: counts {'K': 8, 'N': 2, 'X': 0} rows 9 vs report {'K': 7, 'N': 2, 'X': 0}` |
| one quoted word changed (POS durations bullet) | exit 1, `POS: quote not as claimed (adds)` |
| the TX change sentence deleted | exit 1, `TX: a difference of the prompt is in no listed change` |
| PB `adds` turned into `removes` | exit 1, `PB: quote not as claimed (removes)` and the uncovered difference |
| PS status `reviewed` changed to `draft` | exit 1, `PS: title/version/status differ from profile.json` |
| GP assumption item 1 reworded | exit 1, `GP: assumptions differ from the report` |
| rows KJ and KM swapped | exit 1, `row order` |
| VK report link broken | exit 1, `VK: report link` |
| the restored ledger | exit 0, `PROBLEMS: none` |
| path checker on a file with a missing backticked path and a missing link | exit 1, `MISSING` names both |

The scripts that were run (they live outside the repository; this is their exact text):

**check_ledger.py**

```python
"""Check docs/program/SECTION-REVIEW-LEDGER-01.md against the tree. Usage: python3 -I check_ledger.py <repo-root>
Prints one line per check and exits 1 on the first kind of failure it finds."""
import difflib, json, re, subprocess, sys
from pathlib import Path

root = Path(sys.argv[1])
ORDER = "AI PS POS TX KJ KM OV VK PT EOM SS ITP GP PB".split()
ledger = (root / "docs/program/SECTION-REVIEW-LEDGER-01.md").read_text("utf-8")
problems = []

def norm(s):
    return " ".join(s.split())

def stripped(text):
    """words with the punctuation that wrapping and clause ends attach to them removed"""
    return [w for w in (x.strip("().,;:") for x in text.split()) if w]

def git(*a):
    return subprocess.run(["git", "-C", str(root), *a], check=True, capture_output=True, text=True).stdout

# --- the table ---------------------------------------------------------------------------
rows = [l for l in ledger.splitlines() if re.match(r"\| (%s) \|" % "|".join(ORDER), l)]
codes = [r.split("|")[1].strip() for r in rows]
if codes != ORDER:
    problems.append(f"row order {codes}")
print("rows:", len(rows), "in registry order:", codes == ORDER)

n_quotes = n_items = n_regions = 0
tot = {"K": 0, "N": 0, "X": 0}
n_rows = 0
for line in rows:
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    code, title, version, status, counts, changes, assumptions, link = cells
    low = code.lower()
    prof = json.loads((root / f"src/auditmanager/analysis/text/profiles/{low}/profile.json").read_text("utf-8"))
    if (prof["title_ru"], prof["profile_version"], prof["status"]) != (title, version, status):
        problems.append(f"{code}: title/version/status differ from profile.json")
    # counts: every row of every decision table under '## Decisions' of the report
    report = (root / f"docs/program/SECTION-{code}-FULL-01.md").read_text("utf-8").splitlines()
    start = report.index("## Decisions")
    end = next(i for i in range(start + 1, len(report)) if report[i].startswith("## "))
    got = {"K": 0, "N": 0, "X": 0}
    for l in report[start:end]:
        if l.startswith("|"):
            parts = l.split("|")
            m = re.match(r"\s*\*\*([KNX])\*\*", parts[3]) if len(parts) > 4 else None
            if m:
                got[m.group(1)] += 1
    m = re.match(r"K (\d+) / N (\d+) / X (\d+)<br>(\d+) rows", counts)
    cell = {"K": int(m.group(1)), "N": int(m.group(2)), "X": int(m.group(3))}
    if cell != got or int(m.group(4)) != sum(got.values()):
        problems.append(f"{code}: counts {cell} rows {m.group(4)} vs report {got}")
    for k in tot:
        tot[k] += got[k]
    n_rows += sum(got.values())
    # prompt changes: every quote against the prompt now and at the draft commit
    path = f"src/auditmanager/analysis/text/profiles/{low}/system_prompt.md"
    new = norm((root / path).read_text("utf-8"))
    old = norm(git("show", f"{'bc574621' if code == 'PB' else 'e027b0d9'}:{path}"))
    commit = re.match(r"Commit `([0-9a-f]+)`", changes).group(1)
    if git("log", "-1", "--format=%h", "--", path).strip()[: len(commit)] != commit:
        problems.append(f"{code}: commit {commit} is not the last to touch the prompt")
    mode = None
    quoted = {"adds": [], "removes": []}
    for tok in re.finditer(r"\b(adds|removes)\b|«([^»]+)»", changes):
        if tok.group(1):
            mode = tok.group(1)
            continue
        q = norm(tok.group(2))
        quoted[mode].append(stripped(q))
        n_quotes += 1
        ok = (q in new and q not in old) if mode == "adds" else (q in old and q not in new) if mode == "removes" else False
        if not ok:
            problems.append(f"{code}: quote not as claimed ({mode}): {q[:60]}")
    # every non-equal region of the word diff (draft -> now) shares a 3-gram (or the whole side if shorter) with a quote
    ow, nw = stripped(old), stripped(new)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ow, nw, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        n_regions += 1
        def shares(words, quotes):
            n = min(3, len(words))
            return n > 0 and any(" ".join(words[k:k + n]) in " ".join(q) for q in quotes for k in range(len(words) - n + 1))
        if not (shares(nw[j1:j2], quoted["adds"]) or shares(ow[i1:i2], quoted["removes"])):
            problems.append(f"{code}: a difference of the prompt is in no listed change: {' '.join(ow[i1:i2])[:50]} -> {' '.join(nw[j1:j2])[:50]}")
    # assumptions: word for word the report's list (backticks aside)
    heads = ("## Assumptions an expert would still want to check", "## Limits and what a domain expert would still check")
    s = next(i for i, l in enumerate(report) if l.strip() in heads)
    e = next((i for i in range(s + 1, len(report)) if report[i].startswith("## ")), len(report))
    items = []
    for l in report[s + 1:e]:
        if not l.strip() or l.startswith("Short and honest"):
            continue
        m2 = re.match(r"(?:\d+\.|-) (.*)", l)
        if m2:
            items.append(m2.group(1).strip())
        else:
            items[-1] += " " + l.strip()
    cell_items = [re.sub(r"^\d+\. ", "", x).replace("`", "") for x in assumptions.split("<br>")]
    if cell_items != [i.replace("`", "") for i in items]:
        problems.append(f"{code}: assumptions differ from the report")
    n_items += len(items)
    # the link
    if link != f"[SECTION-{code}-FULL-01](SECTION-{code}-FULL-01.md)" or not (root / f"docs/program/SECTION-{code}-FULL-01.md").is_file():
        problems.append(f"{code}: report link")
print("decision rows:", n_rows, "K/N/X:", tot, "| quotes checked:", n_quotes, "| prompt diff regions covered:", n_regions, "| assumption items compared:", n_items)
print("PROBLEMS:", problems if problems else "none")
sys.exit(1 if problems else 0)
```

**check_paths.py**

```python
"""Every backticked path-like token and every markdown link target of the given documents must exist.
Usage: python3 -I check_paths.py <repo-root> <doc> [<doc> ...]   (docs relative to the root)"""
import re, sys
from pathlib import Path

root = Path(sys.argv[1])
EXT = r"\.(md|json|py|ts|tsx|sh|ya?ml|txt|toml|lock|css|js)$"
bad = []
for rel in sys.argv[2:]:
    doc = root / rel
    text = re.sub(r"(?ms)^[ \t]*```.*?^[ \t]*```", "", doc.read_text("utf-8"))   # fenced blocks are output, not claims
    checked = patterns = 0
    for tok in re.findall(r"`([^`\n]+)`", text):
        if " " in tok or not ("/" in tok or re.search(EXT, tok)):
            continue
        if re.search(r"[*<>{}]", tok):          # a glob or a placeholder is a pattern, not a path
            patterns += 1
            continue
        checked += 1
        if not (root / tok.rstrip("/")).exists():
            bad.append((rel, "backticked", tok))
    for target in re.findall(r"\]\(([^)#\s]+)\)", text):
        if "://" in target:
            continue
        checked += 1
        if not (doc.parent / target).exists():
            bad.append((rel, "link", target))
    print(rel, "paths checked:", checked, "| patterns skipped:", patterns)
print("MISSING:", bad if bad else "none")
sys.exit(1 if bad else 0)
```

## Integration contract

The integrator can rely on: the diff touches the four allowed paths only; no profile, prompt, test, fixture or contract changed, so the registry, the recordings and `build_fixtures.py --check` are as before; the ledger's numbers are those of the 14 reports at the base commit and are reproduced by P-02 to P-05; and the ledger says nowhere that a human reviewed a profile. If a later lane edits a report or a prompt, the ledger must be regenerated: the checker above fails on any drift of the counts, the quotes, the versions or the assumption lists.

## Failure/idempotency/security cases

A report whose decision table changes turns the counts check red; a prompt edit turns the quote check red (a quote that is no longer an addition, or no longer present); a profile moved back to `draft` or to another version turns the status check red; a renamed or deleted file turns the path check red. Re-running the checkers is idempotent and writes nothing. No secret, key or provider call is involved.

## Rollback / feature flag

Not applicable: documents only, no behaviour changes. A forward revert of the lane's commits restores the previous text of all four paths.

## Handoff

- changed files: `docs/program/SECTION-REVIEW-LEDGER-01.md` (new), `docs/program/tasks/SECTION-REVIEW-LEDGER-01.md` (new), `docs/program/W59-SECTION-PROFILES-01.md` (one note), `fixtures/recorded/sections/README.md` (the ПБ recording section)
- commands/results:

  - On the committed tree `75404bdb0b5e9c20e3c5436bc25862a02715efff` (the lane's first commit; `git status --short` empty):
    - check_ledger.py: `rows: 14 in registry order: True`; `decision rows: 149 K/N/X: {'K': 124, 'N': 25, 'X': 0} | quotes checked: 38 | prompt diff regions covered: 30 | assumption items compared: 98`; `PROBLEMS: none`; exit 0.
    - check_paths.py on the ledger and on this file: 33 and 27 paths checked, 0 and 6 patterns skipped (globs such as `tests/**`), `MISSING: none`; exit 0.
    - The governance one-liner on this file: `[]`.
    - `git diff --check` between the base and that commit: no output, exit 0. `git diff --stat`: 4 files changed, 559 insertions(+), 5 deletions(-); `git diff --name-only` names no path outside the four allowed ones.
    - `tests/contract/program`, `tests/contract/api_v1/test_doc_prose_facts.py` and `tests/contract/api_v1/test_surface_counts_in_prose.py`: 105 passed in 85.89s.
    - The mutation table above: eight ledger mutations and one path mutation, each red as expected.
  - The tip of the lane differs from that commit in this results text only (`git diff --stat` between them shows this one file); the checks above were repeated on the tip.

- known limits: the counts treat a decision row as the unit (a question asked in two halves has two rows), so they differ from a report's own sentence when it counts questions; the ledger separates questions, audit rows and cross-section rows for that reason. The assumption lists are copied, not judged; they are the lanes' lists and are all unverified (`A-7`). The ledger does not say whether a reopen trigger has fired.
- integration notes: (1) stale living statements outside this task's paths, for the integrator: `docs/program/CURRENT_STATE.md` lines 63 to 64 («13 draft legacy-ported profiles and an authored draft for ПБ») and line 95 («Expert review of the draft profiles remains open»), and the row `D-178` of `docs/program/DEBT_REGISTER.md` («are `draft`»); P-12 prints them. `docs/program/SECTION-RECORDINGS-01.md` and `docs/program/PB-PROFILE-01.md` also say `draft` but are records of earlier tasks and stay as they are. (2) The ledger could be linked from `docs/program/CURRENT_STATE.md` next to the `A-7` sentence. (3) `D-224` stays open: the ledger says in its last list that no test reads a lane's sentences.
