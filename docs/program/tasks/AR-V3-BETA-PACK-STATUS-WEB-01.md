# Task AR-V3-BETA-PACK-STATUS-WEB-01 — say whether the reviewed pack is installed, and start the six checks only then

task_id: AR-V3-BETA-PACK-STATUS-WEB-01
status: completed in development candidate

## Outcome
In the web app a reviewer can (1) see in «Настройки анализа» whether the reviewed AR v3 beta pack is installed, who attested it and when, and (2) only when it is installed, start the six AR v3 checks for a version from the same list that holds «Запустить прогон» and be taken to the existing six-scope group review (`/analysis-settings?group_id=<id>`). When the pack is not installed — or its status is loading, failed or breaks the contract — no start control is rendered at all: no disabled button, no placeholder. No contract change and no backend change; every user-visible string is Russian and is judged by the rendered-language guard.

## Depends on
- `AR-V3-BETA-PACK-STATUS-API-01` — completed; shared contract `1.5.0`, `getArV3BetaPackStatus`, `ArV3BetaPackStatus`, `ArV3BetaPackReview` and the regenerated client.
- `AR-V3-BETA-GROUP-REVIEW-SCREEN-01` — completed; the group review panel and the `group_id` address this task opens.
- `AR-V3-BETA-GROUP-API-SEAL-01` — completed; `startArV3BetaGroup`.
- `WEB-BORDER-TOKEN-01` — completed; the guard that a module reads only tokens `globals.css` defines.

## Frozen inputs
- shared domain/API/analysis/events contract: `1.5.0`, unchanged (`getArV3BetaPackStatus`, `startArV3BetaGroup`, `getArV3BetaGroupReview` consumed as generated)
- migration head: `0032_ar_v3_run_group`, unchanged; `VERSION` unchanged; error catalogue unchanged
- base commit: `ed19dc922f5d2e737ebcf3bb187c3ff8db9bc67a`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the generated client has both operations and no screen consumes either; the run list mounts only the single-run start

### P-01 — no web consumer of the pack status or the group start
- captured_at: 2026-10-26
- command: `git grep -n -E 'getArV3BetaPackStatus|startArV3BetaGroup|StartRunControl' ed19dc922f5d2e737ebcf3bb187c3ff8db9bc67a -- web/src/widgets web/src/features web/src/_pages web/src/entities`
- captured_output:
  ```text
  ed19dc922f5d2e737ebcf3bb187c3ff8db9bc67a:web/src/features/start-run/index.ts:6:export type { StartRunControlProps } from './ui/start-run-control';
  ed19dc922f5d2e737ebcf3bb187c3ff8db9bc67a:web/src/features/start-run/index.ts:7:export { StartRunControl } from './ui/start-run-control';
  ed19dc922f5d2e737ebcf3bb187c3ff8db9bc67a:web/src/features/start-run/ui/start-run-control.tsx:30:export interface StartRunControlProps {
  ed19dc922f5d2e737ebcf3bb187c3ff8db9bc67a:web/src/features/start-run/ui/start-run-control.tsx:38:export function StartRunControl({ projectUid, versionUid, onStarted }: StartRunControlProps) {
  ed19dc922f5d2e737ebcf3bb187c3ff8db9bc67a:web/src/widgets/run-list/ui/run-list.tsx:25:import { StartRunControl } from '@/features/start-run';
  ed19dc922f5d2e737ebcf3bb187c3ff8db9bc67a:web/src/widgets/run-list/ui/run-list.tsx:39:    <StartRunControl
  ```
- interpretation: at the base no file under the widgets, features, pages or entities layers names either generated operation; the run list's only start is `StartRunControl`. Absence of hits is the evidence, limited to these four layers and these three names.

### P-02 — the generated client already exports both operations
- captured_at: 2026-10-26
- command: `git grep -n -E 'getArV3BetaPackStatus|startArV3BetaGroup' ed19dc922f5d2e737ebcf3bb187c3ff8db9bc67a -- web/src/shared/api/generated/client.gen.ts`
- captured_output:
  ```text
  ed19dc922f5d2e737ebcf3bb187c3ff8db9bc67a:web/src/shared/api/generated/client.gen.ts:513:export function getArV3BetaPackStatus(
  ed19dc922f5d2e737ebcf3bb187c3ff8db9bc67a:web/src/shared/api/generated/client.gen.ts:517:  return request<GetArV3BetaPackStatusResult>(OPERATIONS.getArV3BetaPackStatus, input, options);
  ed19dc922f5d2e737ebcf3bb187c3ff8db9bc67a:web/src/shared/api/generated/client.gen.ts:1317:export function startArV3BetaGroup(
  ed19dc922f5d2e737ebcf3bb187c3ff8db9bc67a:web/src/shared/api/generated/client.gen.ts:1321:  return request<StartArV3BetaGroupResult>(OPERATIONS.startArV3BetaGroup, input, options);
  ed19dc922f5d2e737ebcf3bb187c3ff8db9bc67a:web/src/shared/api/generated/client.gen.ts:1508:  getArV3BetaPackStatus,
  ed19dc922f5d2e737ebcf3bb187c3ff8db9bc67a:web/src/shared/api/generated/client.gen.ts:1575:  startArV3BetaGroup,
  ```
- interpretation: both operations are generated and exported at the base, so this task consumes them and touches no generated file.

### P-03 — a new mutation hook under a feature must be mapped in the dashboard guard
- captured_at: 2026-10-26
- command: `git grep -n -E 'start-run/model/use-start-run.ts|function isMutationHook' ed19dc922f5d2e737ebcf3bb187c3ff8db9bc67a -- web/tests/guards/dashboard-invalidation.guard.test.ts`
- captured_output:
  ```text
  ed19dc922f5d2e737ebcf3bb187c3ff8db9bc67a:web/tests/guards/dashboard-invalidation.guard.test.ts:172:  'src/features/start-run/model/use-start-run.ts': true,
  ed19dc922f5d2e737ebcf3bb187c3ff8db9bc67a:web/tests/guards/dashboard-invalidation.guard.test.ts:217:function isMutationHook(path: string, source: string): boolean {
  ```
- interpretation: the guard discovers every `useMutation(` under `web/src/features/*/model/` and refuses to run unless its map names each one. The new hook `features/start-ar-v3-group/model/use-start-ar-v3-group.ts` therefore needs one map line, which is why that guard file is an extra allowed path below. It also shows the sibling hook is mapped `true`, which is the standard the new line follows.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `web/src/widgets/ar-v3-beta-pack/**`
- `web/src/features/start-ar-v3-group/**`
- `web/src/widgets/run-list/ui/run-list.tsx`
- `web/src/_pages/analysis-settings/ui/analysis-settings-page.tsx`
- `web/src/shared/api/query-keys.ts`
- `web/src/shared/api/index.ts`
- `web/src/entities/audit-run/**`
- `web/tests/unit/analysis-settings/**`
- `web/tests/unit/screens/**`
- `web/tests/guards/rendered-language.guard.test.ts`
- `web/tests/unit/styles/screens.ts`
- `web/tests/guards/dashboard-invalidation.guard.test.ts`
- `docs/program/tasks/AR-V3-BETA-PACK-STATUS-WEB-01.md`
- `docs/program/AR-V3-BETA-PACK-STATUS-WEB-01.md`

## Forbidden hotspots
- `contracts/**`, `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json`, `web/package.json`, `web/package-lock.json`
- global styles (`web/src/**/globals*.css`, tokens), the composition root (`web/src/_app/providers.tsx`, `src/auditmanager/bootstrap/**`)
- `src/**`, `db/**`, `infra/**`, `Makefile`, `VERSION`, `release-notes/**`
- `docs/program/CURRENT_STATE.md`, `docs/program/RELEASES.md`, `docs/program/DEBT_REGISTER.md`
- `web/src/_pages/version-detail/**` (the run list navigates by itself), `web/src/shared/lib/routes.ts` (the settings address is built beside the group-ID shape guard instead)
- `origin/main`, tags and the deployment host

## Non-goals
- Installing, approving or withdrawing a pack, or judging whether its attestation is true: the panel prints the record and says it is not checked.
- A provider-mode choice, a pack selection, any free-text input, or the legacy single-run start offered as a fallback.
- A new route, a menu entry, or any change to `StartRunControl`.
- Role gating: like the single-run start the control is drawn for every role; the server refuses a caller who may not start it (`permission_denied`) and the control says so.
- Polling the group, or showing the six Runs on the version page.

## Deliverables
- `web/src/entities/audit-run`: `readArV3PackStatus` (three outcomes: installed, not installed, fault; a response that omits or invents a member, names an undeclared state, lists another scope set or carries a blank attestation member is a fault), `useArV3PackStatus` (loading / error / read, one query shared by the panel and the run list), the key `queryKeys.runs.arV3PackStatus`, and `arV3GroupReviewAddress`.
- `web/src/widgets/ar-v3-beta-pack`: the status panel in its five states, mounted in «Настройки анализа» after the frozen source preview and before the group review.
- `web/src/features/start-ar-v3-group`: `StartArV3GroupControl` with its presentational `StartArV3GroupView`, the `useStartArV3Group` command, and `classifyArV3GroupStartFailure` (13 refusals told as themselves, a generic reading for any other failure, and a fault for a 202 without a usable group address).
- `web/src/widgets/run-list/ui/run-list.tsx`: the control beside `StartRunControl`, drawn only on a valid installed pack, navigating to `/analysis-settings?group_id=<id>`.
- Tests: classification and panel states, failure sentences, the command, the control's hand-over, the run list in both start positions over every status, the started-group navigation; extensions to the rendered-language guard, the contrast census and the dashboard-invalidation map.
- This task file and the result note.

## Verification
- `npm --prefix web run lint -- --quiet`
- `npm --prefix web run typecheck`
- `npm --prefix web test -- --run tests/unit/analysis-settings tests/unit/screens tests/unit/styles tests/guards/rendered-language.guard.test.ts tests/guards/dashboard-invalidation.guard.test.ts`
- `npm --prefix web test -- --run tests/guards` (bounded: the source-scanning and rendering guards that read the files this task adds)
- `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/api_v1` (needs a `.venv` link in the lane)
- Each new guard shown red under a quoted mutation (see the result note). No live journey and no full suite (R-135).

## Integration contract
The run list draws «Запустить шесть проверок АР v3» if and only if `getArV3BetaPackStatus` answered `installed` with every member the contract requires, the six scopes in order, a 64-hex digest and a five-member non-blank attestation; every other state draws nothing in its place. The control sends `startArV3BetaGroup` with the version and one idempotency key per intent (`start-ar-v3-group:<version_uid>`), no provider mode. On 202 with a well-formed `arg_…` address the run list pushes `/analysis-settings?group_id=<id>`; a 202 without one is a fault with a same-key retry and is never handed on. An accepted start invalidates `runs`, the dashboard summary and every execution read. The panel states that the reviewer's record is attached at installation and is not checked by the system.

Two paths are beyond the lane brief's list and are reported for the integrator: `web/tests/unit/styles/screens.ts` (granted by the dispatching message: the contrast census must render the new states, as the previous slice did) and `web/tests/guards/dashboard-invalidation.guard.test.ts` (one map line, see P-03; without it that guard is red). Neither can be refused without leaving a guard red or a state unmeasured. `web/src/shared/api/index.ts` is allowed and was not needed: the generated exports are already re-exported.

Merge after `AR-V3-BETA-PACK-STATUS-API-01`. Re-run on a stand with a reviewed pack installed: open «Настройки анализа» (installed panel), open a version and start the six checks; this host has no pack, stand or browser, so that journey was not run.

## Failure/idempotency/security cases
- Loading, read failure, not installed and every contract fault draw no start control; the panel carries the explanation, with a retry that re-reads (a pure read).
- The same version keeps one idempotency key across retries; a changed version mints a new one. «Повторить с тем же ключом» is offered only where the envelope says the failure is retryable, and never for a refusal the same request would meet again.
- A reviewer's free text (name, capacity, decision reference, scope statement) is rendered as text; markup in it is escaped.
- The pack refusal (`dependency_unavailable` naming `ar_v3_trusted_pack`) offers no retry although the envelope marks a 503 retryable.

## Rollback / feature flag
Forward-revert the lane's commits: the panel, the control and the key go together, and the server operations stay harmless. No flag, no migration, no data.

## Handoff
- changed files: see the result note
- commands/results: see the result note
- known limits: no live stand, pack or browser; digest letters are not judged by the language guard (fixtures use a digit-only digest, as the other digest fixtures do)
- integration notes: merge after the API task; update nothing in `CURRENT_STATE.md` by this lane
