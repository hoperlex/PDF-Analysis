# Task DESIGN-REF-05-MOTION — состояния и сдержанное движение

## Outcome

Загрузка, раскрытие навигации и фокус на рабочих карточках имеют согласованную визуальную обратную связь в светлой и тёмной темах. При `prefers-reduced-motion: reduce` декоративная анимация не запускается.

## Depends on

- `DESIGN-REF-04-DENSITY` (completed and published at `12acff4f58ac49fd0fe543a25d75cc3c2436699a`).

## Frozen inputs

- Base: `12acff4f58ac49fd0fe543a25d75cc3c2436699a` (`origin/dev` at task start).
- API/contract: `1.14.0`; migration head `0043_stage_ai_generations`.
- Existing state semantics, role gates, keyboard navigation, route destinations and dark/light tokens are frozen.
- Design sequence: `docs/program/DESIGN-REF-FOLLOWUP-1030.md`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: `web/src/shared/config/screen-registry.ts`
- enumerator_owner: existing registry owner; read-only
- totality_query: `rg --files web/src/app | rg '/page.tsx$'`

## Captured premise evidence

- Shared `LoadingState` renders the same neutral status block as other non-error states; it has no visual loading affordance.
- Disclosure panels switch with `hidden`, and CSS already has theme tokens plus a reduced-motion duration scale. Project, dispatcher and knowledge cards have distinct static surfaces; keyboard focus uses existing controls.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`
- origin_main_authority: none

## Allowed paths

- `web/src/shared/ui/states.tsx`
- `web/src/app/globals.css` — exclusive integration/global-style slot for this task
- `web/src/_pages/projects/ui/projects-page.module.css`
- `web/src/_pages/dispatcher/ui/dispatcher-page.module.css`
- `web/src/_pages/knowledge-base/ui/knowledge-base-page.module.css`
- `web/src/widgets/run-progress/ui/run-progress.module.css`
- `web/src/widgets/dashboard/ui/sections-panel.module.css`
- `web/tests/unit/ui/states.test.ts`
- `docs/program/tasks/DESIGN-REF-05-MOTION.md`
- `docs/program/DESIGN-REF-FOLLOWUP-1030.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

- Registry, APIs, contracts, migrations, root dependencies/lockfiles, composition roots, unrelated screens, application behavior and `origin/main`.

## Non-goals

- Changing loading/error wording, timed auto-dismiss, animated layout reflow, data fetching or permissions.

## Deliverables

- Decorative loading bars that retain status announcement.
- Short disclosure entrance and panel hover/focus feedback with no layout shift; reduced-motion override.
- Documentation and one fast-forward development commit.

## Required tests

- Focused state/shell/style tests; `npm run typecheck`; `npm run lint`; CSS parse; `git diff --check`.
- Basic checks only, no full gate or review window per owner instruction.

## Integration contract

- This task exclusively owns the `globals.css` change in its development commit. Components keep existing names/semantics and use the existing color and duration tokens; no new public contract.

## Failure/idempotency/security cases

- A loading announcement remains readable to screen readers, bars are decorative, hidden disclosure content stays hidden. Reduced-motion users see the final state immediately; focus indicators remain visible in both themes.

## Rollback / feature flag

- Revert this commit; no flag or migration.

## Handoff

- Changed files are limited to the allowed paths. Shared registry, API, contracts, migrations, dependencies, application composition and `origin/main` remain untouched.
- Focused state/shell/style tests: 170 passed with a single thread; typecheck, lint, CSS parse and diff check passed. The broader `lazy-boundary` guard did not complete within 25 seconds in this environment and is outside the requested basic check. Browser screenshot verification remains unavailable.
- No public contract or schema changed. Integrator fast-forwards the exact tested commit to `origin/dev` only.
