# Task RELEASE-0-8-1-DEV-01 — product version 0.8.1 on the development line, with a truthful Russian release note

task_id: RELEASE-0-8-1-DEV-01
status: completed in development candidate

## Outcome

`VERSION` is `0.8.1` and `release-notes/0.8.1.json` (revision 1, 2026-10-26, seven items) tells an expert, in Russian, only what the screens of this tree show, each item traced to a commit that implements it and a test that pins it. `RELEASES.md` records the version as a development candidate in prose (no table row, nothing is deployed). The live pins of the version are moved with it. Development publication is not a release: no tag, no `origin/main` push, no complete gate, no verified AR v3 citation is claimed.

## Depends on

- `AR-V3-BETA-STATUS-VERSION-01` — completed; the `0.8.0` precedent and its set of files.
- `AR-V3-BETA-PACK-STATUS-WEB-01` — completed; the pack status panel and the pack-gated six-check start.
- `AR-V3-BETA-GROUP-REVIEW-SCREEN-01` — completed; the group review panel the start opens.
- `AR-V3-BETA-RUN-PROFILE-READ-01` and `AR-V3-BETA-RUN-REVIEW-BOUNDARY-01` — completed; the run page of an AR v3 Run.
- `AR-V3-BETA-SIX-RUN-02` — completed; the server side that creates six Runs from one start.
- `WEB-QUOTATION-RANGE-01` — completed; the page-only quotation caption (`R-43`, `D-50`).
- `WEB-BORDER-TOKEN-01` — completed; borders drawn from a defined token, and the gap token of the classification history.

## Frozen inputs

- domain contract: unchanged
- API contract: `1.5.0`, unchanged (`92` paths, `104` operations, `300` schemas)
- analysis/comparison/event contract: unchanged
- migration head: `0032_ar_v3_run_group`, unchanged
- product version before: `0.8.0` (`release-notes/0.8.0.json`, revision 1, is not edited)
- base commit: `b4fcf817281c9eb802b5f0280e592d9844df8a39` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `release-notes/`
- enumerator_owner: RELEASE-0-8-1-DEV-01
- totality_query: `ls release-notes/*.json | grep -v -e schema -e dictionary`, compared with the version lists in `tests/contract/release_notes/test_release_notes_form.py` and `tests/integration/releases/test_release_loader.py`

## Captured premise evidence

- premise: the version is pinned in five live places at the base, the web changes since the `0.8.0` note are the ones the note must cover, and the border and gap items touch screens the registry names

### P-01 — the live `0.8.0` pins at the base

- captured_at: 2026-10-26
- command: `git grep -n -o -E ".{0,40}0\.8\.0[^ ]*" b4fcf817281c9eb802b5f0280e592d9844df8a39 -- VERSION release-notes tests/contract/release_notes tests/integration/releases docs/program/CURRENT_STATE.md docs/program/RELEASES.md`
- captured_output:
  ```text
  b4fcf817281c9eb802b5f0280e592d9844df8a39:VERSION:1:0.8.0
  b4fcf817281c9eb802b5f0280e592d9844df8a39:docs/program/CURRENT_STATE.md:10:`0032_ar_v3_run_group`**, `VERSION` is `0.8.0`,
  b4fcf817281c9eb802b5f0280e592d9844df8a39:docs/program/RELEASES.md:18:## `v0.8.0`
  b4fcf817281c9eb802b5f0280e592d9844df8a39:docs/program/RELEASES.md:20:The owner requested `VERSION=0.8.0`
  b4fcf817281c9eb802b5f0280e592d9844df8a39:docs/program/RELEASES.md:20:ot** meet the previously planned W57a `v0.8.0`
  b4fcf817281c9eb802b5f0280e592d9844df8a39:docs/program/RELEASES.md:20:ts. The user-facing note `release-notes/0.8.0.json`
  b4fcf817281c9eb802b5f0280e592d9844df8a39:release-notes/0.8.0.json:2:  "version": "0.8.0",
  b4fcf817281c9eb802b5f0280e592d9844df8a39:tests/contract/release_notes/test_release_notes_form.py:148:   # for the independent judge's edits. 0.8.0
  b4fcf817281c9eb802b5f0280e592d9844df8a39:tests/contract/release_notes/test_release_notes_form.py:151:        "0.8.0":
  b4fcf817281c9eb802b5f0280e592d9844df8a39:tests/contract/release_notes/test_release_notes_form.py:156:        "0.8.0",
  b4fcf817281c9eb802b5f0280e592d9844df8a39:tests/integration/releases/test_release_loader.py:68:", "0.5.0", "0.5.1", "0.6.0", "0.7.0", "0.8.0",
  ```
- interpretation: the live pins are `VERSION`, the two release tests, the `CURRENT_STATE.md` sentence and the `RELEASES.md` prose. The remaining hits of a repository-wide search (`uv.lock`, `web/package-lock.json`, `infra/norms-worker/requirements.lock`, `README.md`, `docs/stages/**`, `CHECKPOINT_REGISTRY.md`, the roadmap) name other packages or the planned `CP-08 v0.8.0-distributed` checkpoint and are not this product's version. `release-notes/0.8.0.json` is the sealed note of the previous version and stays.

### P-02 — the web changes since the `0.8.0` note was authored

- captured_at: 2026-10-26
- command: `git log --oneline --no-merges 5286248d..b4fcf817281c9eb802b5f0280e592d9844df8a39 -- web/src`
- captured_output:
  ```text
  5459a620 test(web): pack status and six-check start in the language guard and contrast census
  8e3779b3 fix(web): the character range leaves the quotation caption (R-43, D-50)
  dbcb673a feat(web): pack status panel and the six-check start from the run list
  6b57928f fix(web): classification history list gap reads a defined spacing token
  742e8e34 fix(web): eight stylesheets read a defined border token, and a guard names any undefined --am-* token
  a6761bf4 AR-V3-BETA-PACK-STATUS-API-01 seal contract 1.5.0 (92 paths, 104 operations, 300 schemas)
  354a9092 fix(beta): keep v3 run review separate from findings
  289f1eb0 fix(beta): identify in-flight v3 run before stage results
  6650f1ee fix(beta): render v3 stage and cover group review states
  d1487c75 AR-V3-BETA-GROUP-REVIEW-SCREEN-01 show six scoped reviews
  b4291c12 AR-V3-BETA-GROUP-API-SEAL-01 serve six-scope review read
  e66b2483 Seal API RunStatus for AR v3 CITE stage
  9dfa2691 Fail closed on unknown decision history severity
  a20f9211 feat: persist explicit AR v3 beta six-run groups
  ```
- interpretation: `5286248d` is the commit that authored `release-notes/0.8.0.json`. Every user-visible line of the new note is one of these changes. The group review panel (`d1487c75`) and the run page of an AR v3 Run (`289f1eb0`, `354a9092`) are not in the orchestrator's five candidate items; they are added because the pack-gated start opens the first and creates the Runs the second shows. `9dfa2691` (a closed vocabulary on a decision history reading) and the contract and API commits have no sentence an expert can read on a screen and are left out.

### P-03 — the six screens the border repair reaches, by registry label and page

- captured_at: 2026-10-26
- command: `git grep -n -E "<(RegistrationQueue|ExecutionQueue|WorkerList|ExecutionJournal|ProjectOptimisation|AnalysisProfileTable|ArV3BetaStatus|ArV3BetaReview)\b|label: 'Оптимизация'" b4fcf817281c9eb802b5f0280e592d9844df8a39 -- web/src/_pages`
- captured_output:
  ```text
  b4fcf817281c9eb802b5f0280e592d9844df8a39:web/src/_pages/admin-registrations/ui/admin-registrations-page.tsx:7:      <RegistrationQueue />
  b4fcf817281c9eb802b5f0280e592d9844df8a39:web/src/_pages/analysis-settings/ui/analysis-settings-page.tsx:30:      <ArV3BetaStatus />
  b4fcf817281c9eb802b5f0280e592d9844df8a39:web/src/_pages/analysis-settings/ui/analysis-settings-page.tsx:32:      <ArV3BetaReview groupId={groupId} />
  b4fcf817281c9eb802b5f0280e592d9844df8a39:web/src/_pages/analysis-settings/ui/analysis-settings-page.tsx:45:        <AnalysisProfileTable items={profiles.data.items} />
  b4fcf817281c9eb802b5f0280e592d9844df8a39:web/src/_pages/logs/ui/logs-page.tsx:64:        <ExecutionJournal
  b4fcf817281c9eb802b5f0280e592d9844df8a39:web/src/_pages/project-detail/ui/project-detail-page.tsx:58:  { tab: 'optimisation', label: 'Оптимизация' },
  b4fcf817281c9eb802b5f0280e592d9844df8a39:web/src/_pages/project-detail/ui/project-detail-page.tsx:108:          <ProjectOptimisation projectUid={projectUid} roles={roles} />
  b4fcf817281c9eb802b5f0280e592d9844df8a39:web/src/_pages/queue/ui/queue-page.tsx:152:        <ExecutionQueue
  b4fcf817281c9eb802b5f0280e592d9844df8a39:web/src/_pages/workers/ui/workers-page.tsx:154:          <WorkerList
  ```
- interpretation: the eight widgets named by `WEB-BORDER-TOKEN-01` appear on six screens, not eight: «Заявки на регистрацию», «Настройки анализа» (three widgets), «Журнал выполнения», the «Оптимизация» tab of «Проект», «Очередь» and «Исполнители» (their registry labels are `screen-registry.ts` lines 250, 215, 206, 221 and 212). The note names these six, so the orchestrator's «eight screens» is corrected.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `VERSION`
- `release-notes/0.8.1.json`
- `docs/program/RELEASES.md`
- `docs/program/CURRENT_STATE.md`
- `tests/contract/release_notes/test_release_notes_form.py`
- `tests/integration/releases/test_release_loader.py`
- `docs/program/tasks/RELEASE-0-8-1-DEV-01.md`
- `docs/program/RELEASE-0-8-1-DEV-01.md`

## Forbidden hotspots

`contracts/**`, `src/**`, `web/**`, `db/**`, `infra/**`, `Makefile`, root dependency and lock files, `release-notes/0.8.0.json` and the older notes, `docs/program/DEBT_REGISTER.md`, historical task files and reports, `origin/main`, tags and the deployment host.

## Non-goals

No tag, no `origin/main` publication, no release table row, no complete gate, no stand deployment, no live or credentialed journey. No claim that a reviewed pack is installed anywhere, that AR v3 citations are verified, or that a numerical conclusion is available. No change to a screen: the note describes what the tree already does. No debt-register edit (marking `D-50` repaired belongs to the integrator).

## Deliverables

- `VERSION` = `0.8.1`; `release-notes/0.8.1.json`.
- The pins moved in the same commit: the revision map and the ordered version list in `test_release_notes_form.py`, the note-file set in `test_release_loader.py`, the one sentence « `VERSION` is `0.8.1` » in `CURRENT_STATE.md` (nothing else of that paragraph).
- The `RELEASES.md` prose entry `v0.8.1 development candidate`.
- This task file and the result note with the evidence table (claim, commits, pinning tests, rendering file and line).

## Required tests

- `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/release_notes tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/integration/releases/test_product_version.py tests/integration/releases/test_release_loader.py` (the loader test against the existing integration stack through a copied `.env`; no container is started or touched)
- the whole `tests/contract` once, on a clean committed tree
- `npm --prefix web exec vitest run tests/unit/release-notes` (the current note's `screen` and the start of `where` against today's screen registry; read-only use of a symlinked `node_modules`)
- the pinned tests named in the evidence table, run unchanged
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/RELEASE-0-8-1-DEV-01.md',encoding='utf-8').read())))"` prints `[]`
- each changed pin shown red under one quoted mutation (result note)

## Integration contract

Publish to `origin/dev` only. The loader appends `0.8.1` revision 1 at the next deploy and serves the highest revision no higher than the running `VERSION`; `0.8.0` stays. Any later `main` publication needs its own exact-tree gate, the independent note judge of `RELEASE_PROCESS.md` and the owner's direct instruction. When the pack is installed on a stand, the three AR v3 items become checkable by a person: open «Настройки анализа», open a version's run list, press the start, read the group review. Until then they describe screens that no deployed stand has data for.

## Failure/idempotency/security cases

A note item that names a screen or path the registry does not hold fails `web/tests/unit/release-notes/current-screen.test.ts`. A prose rule break (length, straight quotes, a dictionary word outside «…», a code trace) fails `test_authored_shape_and_form`. Editing a note after it reached a published ref needs a higher `revision`; this note is revision 1 and unpublished.

## Rollback / feature flag

Forward revert of the version, the note file and the pins together; the note file is additive and the version returns to `0.8.0`. No flag, no migration, no data.

## Handoff

- changed files: the eight paths above
- commands/results: see `docs/program/RELEASE-0-8-1-DEV-01.md`
- known limits: no live check of the AR v3 screens (no pack, stand or browser); the server creation of six Runs is pinned by a PostgreSQL-backed test this task did not run
- integration notes: merge after the three web lanes already on the integration branch; mark `D-50` repaired in the register
