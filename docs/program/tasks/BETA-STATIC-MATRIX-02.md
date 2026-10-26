# Task BETA-STATIC-MATRIX-02 — the static B1–B12 coverage matrix `CODE-FIRST-TO-BETA.md` §3 requires before the final gates

task_id: BETA-STATIC-MATRIX-02
status: completed in development candidate (documents only)

## Outcome

`docs/program/BETA-STATIC-MATRIX-02.md` states, for each beta criterion B1–B12 of `ROADMAP-TO-BETA.md` §9, the implemented paths (source files,
`operationId`s of `contracts/api/v1/openapi.json`, migrations, screens), the pinning tests, one status word (`code present`, `code partial (…)`,
`code missing` or `not a code property`, never `PASS`) and what still needs a stand, an expert, real documents, a policy decision or a publication,
with debt ids as the register stands on this tree. It adds the cross-cutting facts recorded in `CURRENT_STATE.md`, the honest list of code that is
still missing, and what the matrix does not establish. Every path, operationId, migration, screen, test function and debt id it cites was checked
mechanically against the tree.

## Depends on

- `BETA-MATRIX-02` — completed (the matrix this one refreshes; it stays as written).
- `AR-V3-BETA-PACK-STATUS-WEB-01` — completed (the last slice of the AR v3 beta path recorded in `CURRENT_STATE.md`).
- `AR-V3-BETA-SPANS-MEASURE-01` — completed (the measurement the activation runbook cites).

## Frozen inputs

- base: `integration/ar-close-1026` at `0dbbfc68f7a764708f40fe1fdf90017b47956569`;
- migration head `0032_ar_v3_run_group`; API 92 paths / 104 operations / 300 schemas; 27 error codes; shared contract `1.5.0`; `VERSION` `0.8.1`;
  this task changes no contract and adds no migration;
- rulings: `R-135` (no complete gate and no full battery in a code-first lane), `R-141c` (closed beta on test data; B3, B5, B10, B11 deferred by the
  owner with their text unweakened).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the matrix states the surface and version numbers, the 14 in-menu destinations, the absence of any route to a v2 Run, of a critic stage and of a norm-verification reader

### P-01 — the surface, the version and the contract version the matrix states

- captured_at: 2026-10-26
- command: `python3 -I -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print(open('VERSION').read().strip(),d['info']['version'],len(d['paths']),sum(1 for p in d['paths'].values() for m in p if m in ('get','post','put','patch','delete')),len(d['components']['schemas']))"`
- captured_output:
  ```text
  0.8.1 1.5.0 92 104 300
  ```
- interpretation: `VERSION` 0.8.1, contract 1.5.0, 92 paths, 104 operations, 300 schemas: the triple `CURRENT_STATE.md` states. The head is read in P-04.

### P-02 — the 14 in-menu destinations and the static stub scan

- captured_at: 2026-10-26
- command: `python3 -I /tmp/claude-0/-root-projects-PDF-Analysis/16441722-42ee-458c-b74f-e08cf340d7b7/scratchpad/m1/stub_scan.py .`
- captured_output:
  ```text
  menu destinations: 14
  /	Главная	web/src/app/page.tsx	HomePage	web/src/_pages/home/ui/home-page.tsx	['entities/account', 'widgets/home-tiles', 'widgets/my-tasks']	ok
  /projects	Проекты	web/src/app/projects/page.tsx	ProjectsPage	web/src/_pages/projects/ui/projects-page.tsx	['features/create-project', 'widgets/project-list']	ok
  /dashboard	Дашборд	web/src/app/dashboard/page.tsx	DashboardPage	web/src/_pages/dashboard/ui/dashboard-page.tsx	['widgets/dashboard']	ok
  /section-optimisation	Оптимизация разделов	web/src/app/section-optimisation/page.tsx	SectionOptimisationPage	web/src/_pages/section-optimisation/ui/section-optimisation-page.tsx	['widgets/section-specification']	ok
  /dispatcher	Диспетчер	web/src/app/dispatcher/page.tsx	DispatcherPage	web/src/_pages/dispatcher/ui/dispatcher-page.tsx	['entities/account', 'entities/assignment', 'entities/user', 'features/create-assignment', 'features/transition-assignment', 'widgets/assignment-board']	ok
  /knowledge-base	База знаний	web/src/app/knowledge-base/page.tsx	KnowledgeBasePage	web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx	['entities/expert-decision', 'widgets/knowledge-base']	ok
  /blocks	Блоки	web/src/app/blocks/page.tsx	BlocksPage	web/src/_pages/blocks/ui/blocks-page.tsx	['entities/document-version', 'entities/project', 'widgets/portal-blocks']	ok
  /norms	Нормы	web/src/app/norms/page.tsx	NormsPage	web/src/_pages/norms/ui/norms-page.tsx	['entities/norms', 'features/set-current-snapshot', 'widgets/norm-catalogue', 'widgets/norm-document', 'widgets/norm-search', 'widgets/norm-snapshots']	ok
  /logs	Журнал выполнения	web/src/app/logs/page.tsx	LogsPage	web/src/_pages/logs/ui/logs-page.tsx	['entities/execution', 'widgets/execution-journal']	ok
  /workers	Исполнители	web/src/app/workers/page.tsx	WorkersPage	web/src/_pages/workers/ui/workers-page.tsx	['entities/account', 'entities/execution', 'features/set-worker-intake', 'widgets/executor-connections', 'widgets/executor-routes', 'widgets/worker-list']	ok
  /analysis-settings	Настройки анализа	web/src/app/analysis-settings/page.tsx	AnalysisSettingsPage	web/src/_pages/analysis-settings/ui/analysis-settings-page.tsx	['entities/analysis-profile', 'widgets/analysis-profile-table', 'widgets/ar-v3-beta-pack', 'widgets/ar-v3-beta-review', 'widgets/ar-v3-beta-status']	ok
  /queue	Очередь	web/src/app/queue/page.tsx	QueuePage	web/src/_pages/queue/ui/queue-page.tsx	['entities/account', 'entities/execution', 'features/cancel-run', 'features/pause-execution', 'features/reaudit-run', 'features/set-job-priority', 'widgets/execution-queue']	ok
  /admin/users	Пользователи	web/src/app/admin/users/page.tsx	AdminUsersPage	web/src/_pages/admin-users/ui/admin-users-page.tsx	['widgets/user-list']	ok
  /admin/registrations	Заявки на регистрацию	web/src/app/admin/registrations/page.tsx	AdminRegistrationsPage	web/src/_pages/admin-registrations/ui/admin-registrations-page.tsx	['widgets/registration-queue']	ok
  RoutePlaceholder referenced outside web/src/shared/ui: 0 []
  problems: 0
  ```
- interpretation: 14 rows of the registry have `inMenu: true`; each reaches a route file that awaits its own `requireScreen`, a page component exported by its `_pages` directory and at least one widget or feature, and `RoutePlaceholder` is referenced by no source file outside `web/src/shared/ui`. The scan reads source; it says nothing of what a browser renders.

### P-03 — which source files name the AR v2 recorded identities

- captured_at: 2026-10-26
- command: `grep -rlE "AR_V2_RECORDED_PROFILE_ID|recorded_v2|RecordedV2" src | sort`
- captured_output:
  ```text
  src/auditmanager/analysis/profiles/ar_v2/recorded_artifact.py
  src/auditmanager/analysis/profiles/ar_v2/recorded_call.py
  src/auditmanager/analysis/profiles/ar_v2/recorded_input.py
  src/auditmanager/analysis/profiles/ar_v2/recorded_response.py
  src/auditmanager/analysis/profiles/ar_v2/recorded_stage_result.py
  src/auditmanager/analysis/public.py
  src/auditmanager/findings/queries.py
  src/auditmanager/findings/v2_recorded.py
  src/auditmanager/runs/executor.py
  src/auditmanager/runs/recorded_v2_merge.py
  src/auditmanager/runs/recorded_v2_publication.py
  src/auditmanager/runs/recorded_v2_sources.py
  src/auditmanager/runs/recorded_v2_stage.py
  ```
- interpretation: no file under `src/auditmanager/bootstrap/` or `src/auditmanager/api/` names the v2 identities, so no API operation or screen creates a Run pinned to them; the executor branch (`src/auditmanager/runs/executor.py`) takes only a Run already pinned to them, with a recorded adapter and an explicit fixture model (`W56A-INT-RECORDED-ACTIVATION-01`). The search is textual: it proves no file in those two directories carries the three strings, not that no other path reaches a v2 Run.

### P-04 — the migration head and the base

- captured_at: 2026-10-26
- command: `ls db/migrations/versions | tail -1`
- captured_output:
  ```text
  20261023_0032_ar_v3_run_group.py
  ```
- interpretation: the head file is `0032_ar_v3_run_group`, the head `CURRENT_STATE.md` states. The base is `0dbbfc68f7a764708f40fe1fdf90017b47956569` (`git rev-parse integration/ar-close-1026` at the start of the lane).

### P-05 — there is no critic stage in the source

- captured_at: 2026-10-26
- command: `grep -rniw critic src`
- captured_output:
  ```text
  src/auditmanager/analysis/text/budget.py:37:  reserved. A stage that adds calls (W56's block analysis and critic) must revisit this.
  ```
- interpretation: the one occurrence of the word in `src` is a comment that names the critic as future work; `ROADMAP-TO-BETA.md` §10.14 (H-10) puts the critic in W56b.

### P-06 — `getRunNormVerification` has no reader

- captured_at: 2026-10-26
- command: `grep -n -A9 "def get_norm_verification" src/auditmanager/bootstrap/adapters.py`
- captured_output:
  ```text
  1098:    def get_norm_verification(self, *, run_id: str) -> models.NormVerificationReport:
  1099-        """Refuse until a reader proves the 0023 partition and the pinned set.
  1100-
  1101-        An empty citation SELECT is not a certificate of zero. CITE will replace this
  1102-        seam after it checks stage success and every canonical/member partition.
  1103-        """
  1104-        raise DomainError(
  1105-            ErrorCode.DEPENDENCY_UNAVAILABLE,
  1106-            dependency="norm_verification_reader",
  1107-        )
  ```
- interpretation: the served adapter of the operation refuses with `dependency_unavailable` and the dependency `norm_verification_reader`; the router's description says the same (`src/auditmanager/api/routers/runs.py`).

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/BETA-STATIC-MATRIX-02.md`
- `docs/program/tasks/BETA-STATIC-MATRIX-02.md`

## Forbidden hotspots

Everything else. In particular `docs/program/BETA-MATRIX-01.md` and `docs/program/BETA-MATRIX-02.md` (earlier immutable records), `docs/program/DEBT_REGISTER.md`,
`docs/program/CURRENT_STATE.md`, `contracts/**`, `db/migrations/**`, root dependency and lock files, `Makefile`, `infra/**`, global styles, the composition
roots, `src/**`, `web/**`, `tests/**`, refs, tags and any stand.

## Non-goals

No code, test, contract or migration change; no stand, container, battery, gate or live journey; no `PASS` for any criterion; no claim of approval,
expert decision or legal-source check; no change to the register or to `CURRENT_STATE.md` (statements found stale there are reported, not edited); no push.

## Deliverables

- `docs/program/BETA-STATIC-MATRIX-02.md`: the matrix table, one section per criterion, "Cross-cutting facts measured on 2026-10-26", "Code that is still
  missing", "What this matrix does not establish".
- This task file.

## Verification

Run from the lane worktree `.local/worktrees/beta-static-matrix-02`; results are in the Handoff section below.

1. `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/BETA-STATIC-MATRIX-02.md',encoding='utf-8').read())))"` must print `[]`.
2. `git diff --check`.
3. `python3 -I <scratchpad>/m1/verify_matrix.py . docs/program/BETA-STATIC-MATRIX-02.md`: the existence check (outside git); it must end with `N checked, 0 missing`.
4. `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`.
5. `pytest --collect-only -q` over the Python test files the matrix names (no test is run).

## Integration contract

The integrator may merge this lane after the lanes that edit `CURRENT_STATE.md` or `DEBT_REGISTER.md`, or before: the matrix reads both and writes neither. If a
debt id changes state after the merge, the matrix's `(closed)` marks and the existence check (re-run it with the new register) are the places to look. The
matrix is a record of 2026-10-26 on tree `0dbbfc68`; a later matrix is a new file, not an edit.

## Failure/idempotency/security cases

Documents only. A stale citation is the failure mode; the existence check is the defence, and its own mutation proofs are in the Handoff.

## Rollback / feature flag

Forward revert of the two files. Behaviour is unchanged.

## Handoff

- changed files: `docs/program/BETA-STATIC-MATRIX-02.md`, `docs/program/tasks/BETA-STATIC-MATRIX-02.md`.
- commands/results: filled after the final run (see the lane's hand-back).
- known limits: no test was run, only collected; stand state is unreadable from the tree.
- integration notes: none beyond the integration contract above.
