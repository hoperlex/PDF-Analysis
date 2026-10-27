# Task RELEASE-0-9-0-DEV-01 — product version 0.9.0 on the development line, with a truthful Russian release note

task_id: RELEASE-0-9-0-DEV-01
status: completed in development candidate (lane `agent/release-0-9-0-dev-01`; nothing pushed, merged or tagged)

## Outcome

`VERSION` is `0.9.0` and `release-notes/0.9.0.json` (revision 1, dated 2026-10-28, seven items) tells an expert and an administrator, in Russian, only what the screens of this tree show, each item traced to a commit that implements it and a test or a quoted check that pins it. `RELEASES.md` records the version as a development candidate in prose (no table row, nothing is deployed). The live pins of the version are moved with it. Development publication is not a release: no tag, no `origin/main` push, no complete gate, no measured quality of any section prompt is claimed.

## Depends on

- `RELEASE-0-8-1-DEV-01` — completed; the precedent for the set of files and the claim table.
- `COMPARE-PERSISTED-SUMMARY-01` — completed; approved sheet pairings and the recorded-only summary (migration `0035`).
- `SECTION-WIDEN-G1-01`, `SECTION-WIDEN-G2-01`, `SECTION-WIDEN-G3-01` — completed; the same-document total-against-rows checks of 12 section profiles (`1.2.0`).
- `SECTION-PS-FULL-01` and `SECTION-AI-FULL-01` — completed; the model lanes of the 14 section profiles that moved them from `draft` to `reviewed` with no human review (`R-146ag`, `A-7`).
- `SECTION-CHUNKED-ANALYSIS-01` — completed; whole-page windows for a section run above one model call.
- `OPT-PROJECT-ALL-SECTIONS-01` — completed; «Спецификация и цены» and «Предложения» for every confirmed section (migration `0034`).
- `WEB-SECTION-COPY-01` — completed; the dashboard sentence about «Без раздела».
- `PROD-11-AR-V1-V2-REMOVAL-01` — completed; no text profile for АР, six-check group only.
- `SEC-RUNNER-CAP-01` — completed; the plain `http://` address rule of the connection settings (`F-15`). The SSH routing fix `4802b8a3` (`EXEC-WEB-SSH-SERVED-01`) has a report (`docs/program/EXEC-WEB-SSH-SERVED-01.md`) and no task file.

## Frozen inputs

- domain contract: unchanged
- API contract: `1.7.0`, unchanged (95 paths, 107 operations, 314 schemas)
- analysis/comparison/event contract: unchanged
- migration head: `0035_comparison_records`, unchanged
- product version before: `0.8.2` (`release-notes/0.8.2.json`, revision 1, is not edited)
- base commit: `4b93c26a82074b81c938c5802536bdd61d6ed08d` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `release-notes/`
- enumerator_owner: RELEASE-0-9-0-DEV-01
- totality_query: `ls release-notes/*.json | grep -v -e schema -e dictionary`, compared with the version lists in `tests/contract/release_notes/test_release_notes_form.py` and `tests/integration/releases/test_release_loader.py`

## Captured premise evidence

- premise: the version is pinned in five live places at the base, the section profiles moved from draft to reviewed since `0.8.2`, the web changes since the `0.8.2` commit are the ones the note must cover, the screens the note names are in today's registry, the strictly descending date rule fixes the date, and the summary model exists only for recorded mode

### P-01 — the live `0.8.2` pins at the base

- captured_at: 2026-10-27
- command: `git grep -n -o -E ".{0,40}0\.8\.2[^ ]*" 4b93c26a -- VERSION release-notes tests/contract/release_notes tests/integration/releases docs/program/CURRENT_STATE.md docs/program/RELEASES.md`
- captured_output:
  ```text
  4b93c26a:VERSION:1:0.8.2
  4b93c26a:docs/program/CURRENT_STATE.md:3:development only; product `VERSION` is `0.8.2`).**
  4b93c26a:docs/program/CURRENT_STATE.md:5:development only; product `VERSION` is `0.8.2`).**
  4b93c26a:docs/program/CURRENT_STATE.md:7: part of the day; product `VERSION` is `0.8.2`
  4b93c26a:docs/program/CURRENT_STATE.md:14:ow is accepted, `D-225`), `VERSION` is `0.8.2`,
  4b93c26a:docs/program/CURRENT_STATE.md:18:ANDIDATE-2.md`). `origin/main` carries `0.8.2`
  4b93c26a:docs/program/RELEASES.md:18:## `v0.8.2`
  4b93c26a:docs/program/RELEASES.md:20:QUEUE-01`, `EXEC-PAR-WEB-01`): `VERSION=0.8.2`
  4b93c26a:docs/program/RELEASES.md:20: and `release-notes/0.8.2.json`
  4b93c26a:release-notes/0.8.2.json:2:  "version": "0.8.2",
  4b93c26a:tests/contract/release_notes/test_release_notes_form.py:154:        "0.8.2":
  4b93c26a:tests/contract/release_notes/test_release_notes_form.py:159:        "0.8.2",
  4b93c26a:tests/integration/releases/test_release_loader.py:68:", "0.6.0", "0.7.0", "0.8.0", "0.8.1", "0.8.2",
  ```
- interpretation: the live pins are `VERSION`, the two release tests, the `CURRENT_STATE.md` sentences and the `RELEASES.md` prose. In `CURRENT_STATE.md` lines 3 and 14 are the live sentences and move to `0.9.0`; lines 5 and 7 are dated records of 2026-10-26 and keep what they said then; line 18 says `origin/main` carries `0.8.2`, which stays true. `release-notes/0.8.2.json` is the sealed note of the previous version and stays. A repository-wide search for `0.8.2` also hits dated task and review documents (`EXPOSURE-REVIEW-02.md`, `EXEC-CLAUDE-SONNET-01.md`, `SECTION-WIDEN-G2-01.md`), which are history and are not edited.

### P-02 — the 14 section profiles at the `0.8.2` commit and at the base

- captured_at: 2026-10-27
- command: `for c in ai eom gp itp kj km ov pb pos ps pt ss tx vk; do printf '%s %s | %s\n' $c "$(git show 8f86ddfd:src/auditmanager/analysis/text/profiles/$c/profile.json | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["profile_version"],d["status"])')" "$(git show 4b93c26a:src/auditmanager/analysis/text/profiles/$c/profile.json | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["profile_version"],d["status"])')"; done`
- captured_output:
  ```text
  ai 1.0.0 draft | 1.1.0 reviewed
  eom 1.0.0 draft | 1.2.0 reviewed
  gp 1.0.0 draft | 1.2.0 reviewed
  itp 1.0.0 draft | 1.2.0 reviewed
  kj 1.0.0 draft | 1.2.0 reviewed
  km 1.0.0 draft | 1.2.0 reviewed
  ov 1.0.0 draft | 1.2.0 reviewed
  pb 1.0.0 draft | 1.1.0 reviewed
  pos 1.0.0 draft | 1.2.0 reviewed
  ps 1.0.0 draft | 1.2.0 reviewed
  pt 1.0.0 draft | 1.2.0 reviewed
  ss 1.0.0 draft | 1.2.0 reviewed
  tx 1.0.0 draft | 1.2.0 reviewed
  vk 1.0.0 draft | 1.2.0 reviewed
  ```
- interpretation: at `0.8.2` all 14 profiles were `1.0.0` `draft` (the screen label «черновик, требует экспертной проверки»); at the base 12 are `1.2.0` and `AI`, `PB` are `1.1.0`, all `reviewed`, whose screen label is «рабочая версия, проверка человеком не проводилась» (`web/src/entities/analysis-profile/model/presentation.ts:17`). `reviewed` means a lane answered the record's open questions and no person reviewed it (`R-146ag`, `A-7`). `0.7.0` said «Профили 13 разделов — черновики»; that sentence is history.

### P-03 — the web changes since the `0.8.2` commit

- captured_at: 2026-10-27
- command: `git log --oneline --no-merges 8f86ddfd..4b93c26a -- web/src`
- captured_output:
  ```text
  4b93c26a docs+prose: surface 95/107/314 and head 0035 restated after wave B; D-244
  0cb32bfb feat(web): the summary of the approved pairs with its label, citations and a confirmed command
  003c7446 feat(api): generateComparisonSummary and approved_pairs.summary (contract content under 1.7.0, B2)
  e2857428 feat(web): approve and withdraw a sheet pairing on the comparison screen; the approved pairs with their sealed differences
  7e6eb754 fix(api): approved_pairs is optional and nullable like RunStatus.executor; the operation-surface test names a sheet link
  a4e890e1 feat(api): approveSheetPairing, withdrawSheetPairing and approved_pairs in compareDocumentVersions (contract content under 1.7.0)
  51f01c68 feat(web): specification prices and proposals offer a set of any confirmed section
  19f4781d docs(contract): section_not_ar is no longer produced; uploadDocument and the dashboard say what is true
  945808a0 docs(web): section-breakdown comment avoids the phrase the surface-count prose guard reads as an error-code count
  f72962a1 docs(web): section-breakdown comments say fifteen sections, as the contract type does
  81cad9d5 fix(web): the dashboard sections panel and the section catalogue say what is true after W59 and PROD-11
  68a03b59 fix(security): HARDEN-01 F-12 hide SQL parameters, F-13 log the type and correlation id of an internal_error, F-16 AEAD-only TLS 1.2 suites and no banner version, F-17 served-answer checks in verify-deployed, F-03 web service without the signing key
  56b25ebe PROD-11 stage 2b: regenerated web client and FRONTEND_LOCK for contract 1.7.0
  b7e5fdf1 PROD-11 stage 2b (contract version, proposed 1.7.0): shared contract_version 1.6.0 -> 1.7.0 across the families, served constants, fixtures, edge bodies and tests
  a7c0192a PROD-11 stages 2-3 (web): client regenerated from the resealed contract; АР start goes to the v3 control; the settings table shows АР without a profile
  4802b8a3 fix(web): a command over SSH is a served kind, so its connection can be routed and chosen (EXEC-WEB-SSH-SERVED-01)
  607ee47a fix(web): the reviewed profile label no longer claims expert verification (R-146ag, A-7)
  ```
- interpretation: every user-visible line of the note is one of `0cb32bfb`, `e2857428` (comparison), `51f01c68` (optimisation), `81cad9d5` (dashboard), `a7c0192a` (АР), `607ee47a` (profile label) or `4802b8a3` (SSH routing). The profiles, the windows and the plain `http://` rule are server changes (`src/auditmanager/analysis/**`, `runs/**`, `executors/model.py`) that a web screen shows through the profile table, the start refusal and the connection settings. The remaining commits are contract content, regenerated client, comments, the HARDEN-01 security slice and the contract version move `1.6.0` to `1.7.0`: none has a sentence an expert reads on a screen.

### P-04 — the registry rows of the screens the note names

- captured_at: 2026-10-27
- command: `git grep -n -A3 -E "address: '(/dashboard|/analysis-settings|/workers|/projects/\[project_uid\]|/projects/\[project_uid\]/versions/\[version_uid\]|/projects/\[project_uid\]/versions/\[version_uid\]/comparison)'" 4b93c26a -- web/src/shared/config/screen-registry.ts`
- captured_output:
  ```text
  4b93c26a:web/src/shared/config/screen-registry.ts:114:  { address: '/dashboard', label: 'Дашборд', group: 'work', access: 'session', roles: 'any-role', inMenu: true },
  4b93c26a:web/src/shared/config/screen-registry.ts-115-  {
  4b93c26a:web/src/shared/config/screen-registry.ts-116-    address: '/section-optimisation',
  4b93c26a:web/src/shared/config/screen-registry.ts-117-    label: 'Оптимизация разделов',
  --
  4b93c26a:web/src/shared/config/screen-registry.ts:137:    address: '/projects/[project_uid]',
  4b93c26a:web/src/shared/config/screen-registry.ts-138-    label: 'Проект',
  4b93c26a:web/src/shared/config/screen-registry.ts-139-    group: 'work',
  4b93c26a:web/src/shared/config/screen-registry.ts-140-    access: 'session',
  --
  4b93c26a:web/src/shared/config/screen-registry.ts:153:    address: '/projects/[project_uid]/versions/[version_uid]',
  4b93c26a:web/src/shared/config/screen-registry.ts-154-    label: 'Версия документа',
  4b93c26a:web/src/shared/config/screen-registry.ts-155-    group: 'work',
  4b93c26a:web/src/shared/config/screen-registry.ts-156-    access: 'session',
  --
  4b93c26a:web/src/shared/config/screen-registry.ts:161:    address: '/projects/[project_uid]/versions/[version_uid]/comparison',
  4b93c26a:web/src/shared/config/screen-registry.ts-162-    label: 'Сравнение прогонов',
  4b93c26a:web/src/shared/config/screen-registry.ts-163-    group: 'work',
  4b93c26a:web/src/shared/config/screen-registry.ts-164-    access: 'session',
  --
  4b93c26a:web/src/shared/config/screen-registry.ts:212:  { address: '/workers', label: 'Исполнители', group: 'system', access: 'session', roles: 'any-role', inMenu: true },
  4b93c26a:web/src/shared/config/screen-registry.ts-213-  {
  4b93c26a:web/src/shared/config/screen-registry.ts:214:    address: '/analysis-settings',
  4b93c26a:web/src/shared/config/screen-registry.ts-215-    label: 'Настройки анализа',
  4b93c26a:web/src/shared/config/screen-registry.ts-216-    group: 'system',
  4b93c26a:web/src/shared/config/screen-registry.ts-217-    access: 'session',
  ```
- interpretation: the labels and groups give the display prefixes «Работа › Дашборд», «Работа › Проект», «Работа › Версия документа», «Работа › Сравнение прогонов», «Система › Настройки анализа» and «Система › Исполнители» (group labels `web/src/_app/navigation.ts:23-28`). `web/tests/unit/release-notes/current-screen.test.ts` checks the current note against the registry.

### P-05 — the SSH routing and the plain `http://` rule at the base

- captured_at: 2026-10-27
- command: `git grep -n -E "refuse_plain_http\(|base_url_invalid:|return kind ===" 4b93c26a -- src/auditmanager/executors/model.py web/src/entities/executor-connection/model/failure.ts web/src/entities/executor-connection/model/readiness.ts`
- captured_output:
  ```text
  4b93c26a:src/auditmanager/executors/model.py:196:def refuse_plain_http(base_url: str, transport: str | None) -> None:
  4b93c26a:src/auditmanager/executors/model.py:245:        refuse_plain_http(settings.base_url, settings.transport)
  4b93c26a:src/auditmanager/executors/model.py:296:        refuse_plain_http(settings.base_url, settings.transport)
  4b93c26a:web/src/entities/executor-connection/model/failure.ts:44:  base_url_invalid:
  4b93c26a:web/src/entities/executor-connection/model/readiness.ts:79:  return kind === 'http_api' || kind === 'pull' || kind === 'ssh_command';
  ```
- interpretation: `kindIsServed` now includes `ssh_command`; `refuse_plain_http` runs when a revision is written (`validate_settings`) and where a key is bound for a call (`destination_for`). The screen sentence for a refused address is the generic `base_url_invalid` one, «нужен адрес вида https://узел …».

### P-06 — the date rule fixes the date at 2026-10-28

- captured_at: 2026-10-27
- command: `PYTHONPATH=src:/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages /root/projects/PDF-Analysis/.venv/bin/python -c "import sys,importlib.util;spec=importlib.util.spec_from_file_location('f','tests/contract/release_notes/test_release_notes_form.py');f=importlib.util.module_from_spec(spec);sys.modules['f']=f;spec.loader.exec_module(f);e=f._read_entries();print('0.8.2 date',e[1][1]['date'],'0.9.0 date',e[0][1]['date']);e[0][1]['date']='2026-10-27';print(sorted(f.form_failures(e,version='0.9.0',terms=f._dictionary())))"`
- captured_output:
  ```text
  0.8.2 date 2026-10-27 0.9.0 date 2026-10-28
  ['descending_dates']
  ```
- interpretation: `0.8.2` carries 2026-10-27 (it was dated a day ahead for the same reason), and the form rule `descending_dates` requires a strictly later date for a higher version. A `0.9.0` dated 2026-10-27 fails the gate-time test; the note is dated 2026-10-28. The rule and `release-notes/0.8.2.json` are outside this task, so the date is the integrator's to change together with whichever of the two it decides to move.

### P-07 — the summary model exists only in recorded mode, with one synthetic recording

- captured_at: 2026-10-27
- command: `git grep -n -c "Синтетический ответ, не результат вызова модели" 4b93c26a -- fixtures/recorded/comparison`
- captured_output:
  ```text
  4b93c26a:fixtures/recorded/comparison/225dae82b7cddffbafa1816d697b9d77910b3e4a3b9a3615ea4c0f4387821875.json:1
  4b93c26a:fixtures/recorded/comparison/README.md:1
  4b93c26a:fixtures/recorded/comparison/build_fixtures.py:1
  ```
- interpretation: the directory holds one recording keyed by the request digest of a synthetic pair (`fixtures/recorded/comparison/225dae82….json`, plus `README.md` and the builder); `summary_model_for` (`src/auditmanager/bootstrap/composition.py:77-87`) returns `RecordedSummaryModel()` for `recorded` and `None` otherwise. For a pair of a project there is no recording, so the button ends in the refusal «Для этих подтверждённых пар нет записанного ответа…», and in any other mode in «В этом запуске системы нет модели для сводок…».

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `VERSION`
- `release-notes/0.9.0.json`
- `docs/program/RELEASES.md`
- `docs/program/CURRENT_STATE.md`
- `tests/contract/release_notes/test_release_notes_form.py`
- `tests/integration/releases/test_release_loader.py`
- `docs/program/tasks/RELEASE-0-9-0-DEV-01.md`
- `docs/program/RELEASE-0-9-0-DEV-01.md`

## Forbidden hotspots

`contracts/**`, `src/**`, `web/**`, `db/**`, `infra/**`, `Makefile`, root dependency and lock files, `release-notes/0.8.2.json` and the older notes, `docs/program/DEBT_REGISTER.md`, rulings, historical task files and reports, `origin/main`, tags and the deployment host.

## Non-goals

No tag, no `origin/main` publication, no release table row, no complete gate, no stand deployment, no live or credentialed journey. No claim that any section prompt finds a defect on a real document, that the summary works on a project's documents, that windows make a large document cheaper, or that the specification of a section other than АР is read correctly. No change to a screen or to a test rule: the note describes what the tree already does. No debt-register edit.

## Deliverables

- `VERSION` = `0.9.0`; `release-notes/0.9.0.json`.
- The pins moved in the same commit: the revision map, the ordered version list and the comment in `test_release_notes_form.py`, the note-file set in `test_release_loader.py`, the two live sentences « `VERSION` is `0.9.0` » in `CURRENT_STATE.md` (nothing else of those paragraphs).
- The `RELEASES.md` prose entry `v0.9.0 development candidate`.
- This task file and the result note with the evidence table (claim, commits, pinning tests, rendering file and line), the disposition of every candidate and the mutation table.

## Required tests

- `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/release_notes tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py tests/integration/releases` (the loader tests against a private database cloned by the suite's own fixtures; the lane's main database is not touched)
- `npx vitest run tests/unit/release-notes tests/unit/release` in `web/` (the current note's `screen` and the start of `where` against today's screen registry; read-only use of a symlinked `node_modules`)
- the pinned tests named in the evidence table, run unchanged
- `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/RELEASE-0-9-0-DEV-01.md',encoding='utf-8').read())))"` prints `[]`
- each changed pin shown red under one quoted mutation (result note)

## Integration contract

Publish to `origin/dev` only. The loader appends `0.9.0` revision 1 at the next deploy and serves the highest revision no higher than the running `VERSION`; `0.8.2` stays. Any later `main` publication needs its own exact-tree gate, the independent note judge of `RELEASE_PROCESS.md` on the final candidate and the owner's direct instruction. The date of the note (2026-10-28) is a consequence of the strictly descending date rule and the `0.8.2` date; if the integrator prefers 2026-10-27 it must change that rule or the `0.8.2` date by its own decision.

## Failure/idempotency/security cases

A note item that names a screen or path the registry does not hold fails `web/tests/unit/release-notes/current-screen.test.ts`. A prose rule break (length, straight quotes, a dictionary word outside «…», a code trace, a date not strictly below the previous version's) fails `test_authored_shape_and_form`. Editing a note after it reached a published ref needs a higher `revision`; this note is revision 1 and unpublished.

## Rollback / feature flag

Forward revert of the version, the note file and the pins together; the note file is additive and the version returns to `0.8.2`. No flag, no migration, no data.

## Handoff

- changed files: the eight paths above
- commands/results: see `docs/program/RELEASE-0-9-0-DEV-01.md`
- known limits: the executor-level and PostgreSQL-backed tests of the windows, the pairing and the summary were not re-run by this lane; the note judge has read the first revision of the note, not the final one; no live check of any screen
- integration notes: merge after wave PW4; the note date and the strictly descending date rule need the integrator's decision before `main`
