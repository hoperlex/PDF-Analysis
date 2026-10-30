# Task DESIGN-LOGIN-ORBIT-1030 — реализовать выбранный Signal Orbit

## Outcome

Экран `/login` в обеих темах соответствует выбранной концепции `03-signal-orbit.pdf`: форма слева, декоративная схема процесса справа, визуальное превью боковой панели в гостевой оболочке. Действующие отправка формы, отказ, возврат и заявка на доступ работают как прежде.

## Depends on

- `DESIGN-LOGIN-CONCEPTS-1030` (completed, owner selected Signal Orbit).
- `DESIGN-RELEASE-NOTICE-1030` (completed and published to dev; the owner confirmed this and the Norms task are the two previously discussed tasks).

## Frozen inputs

- Base commit: `78d5799e2b1c1da8a48a0017f53deddfa8bfa6b7` (`origin/dev`).
- Reference: `docs/design/login-concepts/03-signal-orbit.pdf` and its generator, selected by owner.
- API contract `1.14.0`; migration head `0043_stage_ai_generations`; no change.
- Existing `SignInForm` POST, registry addresses, guest guard and dual-theme tokens.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- At the base commit, `SignInPage` renders a centered 30rem card in the shared `AppFrame`; `buildNavigation(null)` returns an empty menu. The concept PDF includes inert guest preview navigation and a decorative three-stage orbit. The sign-in form is a server component with a browser POST.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`
- origin_main_authority: none

## Allowed paths

- `web/src/_pages/sign-in/ui/sign-in-page.tsx`
- `web/src/_pages/sign-in/ui/sign-in-page.module.css`
- `web/src/features/sign-in/ui/sign-in-form.module.css`
- `web/src/_app/app-frame.tsx`
- `web/src/_app/app-frame.module.css`
- `web/src/_app/guest-navigation-preview.tsx`
- `web/tests/unit/session/sign-in-screen.test.ts`
- `web/tests/unit/shell/frame.test.ts`
- `docs/program/tasks/DESIGN-LOGIN-ORBIT-1030.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

- `contracts/**`, migration head, root dependencies/lockfiles, `web/src/app/globals.css`, root layout, registry, auth/BFF behavior, API and `origin/main`.

## Non-goals

- Enabling any guest work navigation; adding real project data or process state; changing account recovery, registration, auth or provider behavior.

## Deliverables

- Responsive two-theme sign-in composition and reduced-motion-aware decorative orbit.
- Guest shell preview without links or menu semantics.
- Focused tests for form and guest frame; typecheck, lint, CSS parse and production web build.

## Required checks

- `npm --prefix web test -- --run tests/unit/session/sign-in-screen.test.ts tests/unit/shell/frame.test.ts`
- `npm --prefix web run typecheck`
- `npm --prefix web run lint`
- CSS parse of modified modules; `npm --prefix web run build`; `git diff --check`.

## Integration contract

- `AppFrame` keeps the registered guest links only: brand `/` and `Вход` `/login`. Preview rows are spans inside an `aria-hidden` decorative region, never navigation or access decisions. The sign-in form still POSTs to its existing BFF endpoint with `next` preserved. The shell composition slot is exclusively owned by this task for the guest preview; global styles stay untouched.

## Failure/idempotency/security cases

- Refusals remain above fields. Inputs remain uncontrolled in a server component. Orbit and preview are decorative, have no API calls and stop moving for reduced-motion preference. Narrow screens put the form first and keep it fully usable.

## Rollback / feature flag

- Revert this presentation commit; no flag or migration is needed because sign-in behavior is unchanged.

## Handoff

- Changed files: `web/src/_pages/sign-in/ui/sign-in-page.tsx`, `sign-in-page.module.css`, `web/src/features/sign-in/ui/sign-in-form.module.css`, `web/src/_app/app-frame.tsx`, `app-frame.module.css`, `guest-navigation-preview.tsx`, focused sign-in/shell tests, this task file and `docs/program/CURRENT_STATE.md`.
- Checks: 33 focused tests passed; typecheck passed; ESLint on changed TSX passed; three changed CSS modules parsed; production web build passed; `git diff --check` passed. Repository-wide lint fails at pre-existing `web/src/entities/audit-run/lib/extended-report.ts:15` (`no-useless-escape`); broad legacy R-66 navigation test has six unrelated stale expectations after previous menu changes.
- Contracts: none changed. Preview rows are spans inside an `aria-hidden` region and have no links. Existing guest frame links remain brand and `Вход`; auth, guards and APIs are unchanged.
- Known limit: no rendered browser screenshot in this environment; installed Firefox snap cannot create its runtime directory. The selected PDF remains the visual review reference.
- Integration: fast-forward the tested commit to `origin/dev` only. Revert this commit to return to the previous login presentation. Forbidden hotspots, including global styles and `origin/main`, were not touched.
