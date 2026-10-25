# AR-V3-BETA-PACK-STATUS-WEB-01 — pack status and the six-check start in the browser

«Настройки анализа» now has a panel that reads `getArV3BetaPackStatus` and says, in one of five states, whether the reviewed AR v3 beta pack is installed: loading, read failed («Не удалось прочитать статус пакета проверенных норм АР v3», with a retry), not installed («Пакет проверенных норм АР v3 не установлен: запуск шести проверок недоступен.»), installed (profile ID, the first twelve hex characters of the pack digest, the six scope IDs and the reviewer's five-field record, followed by the fixed sentence that the record is attached at installation and is not checked by the system), or a contract fault («Ответ сервера не соответствует контракту», never drawn as installed and never as an empty state). The version's run list draws «Запустить шесть проверок АР v3» beside «Запустить прогон» if and only if the status is a valid installed one; otherwise nothing is drawn in its place. A started group opens `/analysis-settings?group_id=<id>`.

## Handoff

- Task: [AR-V3-BETA-PACK-STATUS-WEB-01](tasks/AR-V3-BETA-PACK-STATUS-WEB-01.md), frozen from `ed19dc922f5d2e737ebcf3bb187c3ff8db9bc67a` (the integration tip carrying contract `1.5.0`, the regenerated client, the two earlier web red repairs and the border-token guard).
- Changed files (27, with the two documents): `web/src/entities/audit-run/{model/ar-v3-pack-status.ts, model/ar-v3-group-id.ts, api/use-ar-v3-pack-status.ts, index.ts}`; `web/src/shared/api/query-keys.ts` (`runs.arV3PackStatus`); `web/src/widgets/ar-v3-beta-pack/**` (panel, presentation sentences, module CSS); `web/src/features/start-ar-v3-group/**` (control and view, command, failure classifier, module CSS); `web/src/widgets/run-list/ui/run-list.tsx`; `web/src/_pages/analysis-settings/ui/analysis-settings-page.tsx`; five new test files and one fixture under `web/tests/unit/{analysis-settings,screens}`; `web/tests/guards/rendered-language.guard.test.ts`; `web/tests/unit/styles/screens.ts` (extra path, granted by the dispatching message); `web/tests/guards/dashboard-invalidation.guard.test.ts` (extra path, one map line, see below); this note and the task file.
- Design decisions worth a reviewer's eye:
  - The status read and its classification live in `entities/audit-run`, not in the widget, because the run list needs the same answer and a widget must not import a sibling widget. The widget keeps only the sentences (`widgets/ar-v3-beta-pack/model/pack-presentation.ts`).
  - The reading has exactly three outcomes. A response with a member missing or invented, a state the contract does not declare, `not_installed` carrying anything, a digest that is not 64 lowercase hex, a scope list other than `F1 F2 A1 A2 S1 S2` in order, or a blank/extra attestation member is a fault.
  - `useArV3PackStatus` returns a view (`loading` / `error` / `read`), never the raw body. React Query keeps the earlier body when a re-read fails; the view reports that as `error`, so the control disappears rather than staying on stale data.
  - The control is split into `StartArV3GroupControl` (hooks) and `StartArV3GroupView` (pure), the way the classification forms are, so the pending state and every refusal can be rendered by the instruments that cannot settle a mutation.
  - Navigation: the repository has no route builder for `/analysis-settings`, and `shared/lib/routes.ts` and the version page are outside the allowed paths. `arV3GroupReviewAddress` is built beside `looksLikeArV3GroupId` in `entities/audit-run`, and `run-list.tsx` reads `useRouter` only inside the small component that is mounted when the control is drawn. If the integrator prefers the builder in `routes.ts`, it is a one-line move.
  - Thirteen refusals of the start are told as themselves (pack unusable, other dependency, norms source, unclassified version, section other than AR, invalid input, input budget, key reused, still running, result gone, version not found, not signed in, not permitted); any other failure is the generic reading with the correlation id. The pack refusal is shown without a retry although the envelope marks a 503 retryable. A 202 without a well-formed group address is a fault with a same-key retry and is never handed to `onStarted`.
- Checks run in this tree (`5459a620` plus the two docs files):
  - `npm --prefix web run lint -- --quiet` → exit 0; `npm --prefix web run typecheck` → exit 0.
  - `npm --prefix web test -- --run tests/unit/analysis-settings tests/unit/screens tests/unit/styles tests/guards/rendered-language.guard.test.ts tests/guards/dashboard-invalidation.guard.test.ts` → 29 files, 526 tests passed.
  - `npm --prefix web test -- --run tests/guards` → 21 files, 289 tests passed (every source-scanning and rendering guard; this is how the dashboard map, the journey-evidence sentence guard and the branch-reach guard were found, see below).
  - `npm --prefix web test -- --run tests/unit/{screens,analysis-settings,run,sections,execution,lib,api,entities,widgets}` → 52 files, 839 tests passed.
  - `PYTHONPATH=src:$BS … pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/api_v1` → 342 passed. `tests/contract/web` does not exist.
  - Governance check of the task file prints `[]`.
  - New tests: 61 in five files (11 classification and panel, 26 failure sentences and views, 4 command and hand-over, 17 run list over every status, 3 started-group navigation).
- Findings made by the guards while building (each repaired in this lane):
  - The journey-evidence guard (`D-61`) refused «Ничего не отправлено повторно» in the key-reuse sentence: that phrase is the upload journey's evidence string and must not stand on a screen. The sentence now reads «Повторной отправки не было.»
  - The screen-wide provider guard (`D-97`) refuses a privately mounted router in a screen test; the run-list tests use the shared `renderScreen`, and the navigation test replaces `useRouter` with a recorder.
  - The census flagged the new module rule `.attestation` as reached by no screen until the installed panel was added to `screens.ts`.
- Guards shown red under one mutation each (the tree was restored after every one; `git status` empty):

| Guard | Mutation | Red |
| --- | --- | --- |
| scope list is exactly the six, in order | `scopes.some((scope, index) => scope !== AR_V3_PACK_SCOPE_IDS[index])` → `false` | `is a fault, never installed and never an empty state` (`scopes out of order: expected 'installed' to be 'fault'`) |
| a missing member is a fault with its own reason | the `missing_member` line removed from `readArV3PackStatus` | same test (`installed without a review: expected 'bad_attestation' to be 'missing_member'`) |
| no two refusals share a sentence | the stale-result detail replaced by the key-reuse detail | `gives each refusal a title and a detail no other refusal has` (`two refusals share a detail: expected 12 to be 13`) |
| a code outside the set is generic | `default: return null` → a `not_found` failure | `maps a catalog code the start does not raise to the generic sentence` (`internal_error: expected 'not_found' to be 'generic'`) |
| the control is absent unless installed | `packInstalled = pack.phase === 'read'` (kind check dropped) | 10 of 17 run-list tests (`not installed`, `installed without a review`, `installed with the wrong scopes`, `an undeclared state`, `not installed with a member`, in both start positions) |
| the control is absent while loading | `packInstalled = pack.phase !== 'error'` | 12 of 17, including both `loading` cases |
| the started group opens the group_id route | `?group_id=` → `?group=` in `arV3GroupReviewAddress` | `builds the address the settings route reads` and `pushes that address when the control reports a started group` |
| no provider mode is sent | `provider_mode: 'live'` added to the request body | `sends the version and the caller key — no provider mode, no pack, no scope` |
| an accepted start invalidates the dashboard | the dashboard invalidation removed from the hook | `an accepted start invalidates the run lists, the dashboard and every execution read` and the dashboard-invalidation map entry for the new hook |
| a malformed 202 is not handed on | `onStarted?.(group)` without the address check | `calls onStarted with a 202 group that carries a valid address, and with no other` |
| the module reads a defined token | `var(--am-line-soft)` → `var(--am-border, currentColor)` in the control's CSS | `tokens-defined`: `reads no token that globals.css does not define` |
| language: the pack sentence | an English clause in the not-installed sentence | `rendered-language`: `finds no English on a rendered screen` and `finds none at all` |
| language: a failure sentence | `'Pack unavailable.'` as the pack refusal's title | the same two (`expected ['Pack unavailable.'] to deeply equal []`) |
| branch reach: the pending state | the `ar-v3-group-start-states` case removed from the guard | `renders every one of them, and NAMES the branch it does not reach` |
| contrast census reaches the new rules | the `ArV3BetaPack installed` census line removed | `names every colour-bearing rule that NO rendered screen reaches` (`'._attestation_…'`) |

- Contracts: none changed. The shared contract stays at `1.5.0`; no generated file, no error code, no migration. `web/src/shared/api/index.ts` was allowed and not needed.
- Limits:
  - No stand, pack, browser or credentialed journey was available; the installed panel and the start-to-review journey are unverified against a real server.
  - The language guard cannot judge a real digest: its fixtures, like the other digest fixtures, are digit-only, because a hex letter in server data would be read as a Latin word. The unit test passes a real digest and asserts the twelve shown characters.
  - Like `StartRunControl`, the control is drawn for every role; an administrator pressing it receives the «Вам не разрешено запускать шесть проверок.» refusal.
  - The pack query uses the application's default freshness (30 s); a pack installed while a version page is open appears after the next read.
  - Pre-existing and untouched: `StartRunControl` and the legacy start remain the only run start offered when no pack is installed.
- Integration notes: merge after `AR-V3-BETA-PACK-STATUS-API-01` (already on the base). Two paths are beyond the lane brief's list: `web/tests/unit/styles/screens.ts` and `web/tests/guards/dashboard-invalidation.guard.test.ts`. Re-run on a stand with a reviewed pack: the settings panel, then a version's run list, then the start and the group review it opens.
- Forbidden hotspots (`contracts/**`, generated client, `web/FRONTEND_LOCK.json`, `web/package*.json`, global styles, composition root, `src/**`, `db/**`, `infra/**`, `Makefile`, `VERSION`, `release-notes/**`, `CURRENT_STATE.md`, `RELEASES.md`, `DEBT_REGISTER.md`, `origin/main`, tags, deployment host) were untouched; `git diff --name-only ed19dc92..HEAD` lists only the allowed paths above.
