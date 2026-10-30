# Task DESIGN-RELEASE-NOTICE-1030 — уведомление о новой версии

## Outcome

Карточка «Доступна новая версия» и связанные «Что нового» / ошибка отметки выглядят частью новой оболочки в обеих темах. «Обновить» остаётся главным действием, «Позже» — спокойным вторичным; уведомления не накладываются друг на друга на узкой ширине.

## Depends on

- `DESIGN-REF-06-CHROME` (completed and published at `209b48856b75ef2b5fa4780e11e222c34d335f1e`).

## Frozen inputs

- Base: `f2656d1e8c32e9fb55da89771517375753357f0b` (`origin/dev`).
- API/contract: `1.14.0`; migration head `0043_stage_ai_generations`.
- Existing version reads, banner conditions, `onUpdate`/`onLater`, What's New content, release mark and auth redirects are frozen.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- `release-notices.module.css` uses a plain 0.5rem bordered fixed box and both banner buttons inherit the same primary `am-button`. Notices render outside `.am-app__main`, so they do not inherit its showcase palette override; their old root colors make them stand apart from the new shell.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`
- origin_main_authority: none

## Allowed paths

- `web/src/_app/release-notices.tsx`
- `web/src/_app/release-notices.module.css`
- `web/tests/unit/release/history.test.ts`
- `docs/program/tasks/DESIGN-RELEASE-NOTICE-1030.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

- Release API/data logic, global CSS, registry, contracts, migrations, root dependencies, other composition roots, sign-in/runtime behavior and `origin/main`.

## Non-goals

- New update policy, changing check intervals, forcing reload, changing What’s New selection or modifying release records.

## Deliverables

- Cohesive two-theme banner with icon, text hierarchy and distinct update/later actions.
- Matching What’s New surface and mobile stacking; reduced-motion aware entrance.
- Focused checks and one fast-forward push to `origin/dev`.

## Required tests

- Focused release/style tests; `npm run typecheck`; `npm run lint`; CSS parse; production web build; `git diff --check`.
- Basic checks only, no full gate or review window per owner instruction.

## Integration contract

- `UpdateBannerView` keeps a status role and the same two button callbacks. `WhatsNewView` keeps a nonmodal dialog and its close callback. This task changes presentation only and uses showcase palette tokens directly inside the local module.

## Failure/idempotency/security cases

- Long version notes wrap, keyboard focus remains visible, mobile overlap is avoided when banner and What’s New appear together. Reduced motion skips decorative entrance, and absent build IDs still suppress the banner as before.

## Rollback / feature flag

- Revert the single commit; no flag or migration.

## Handoff

- Changed files are this task's allowed paths: release notice component/module, focused release test, this task and current state. Global CSS, registry, APIs, contracts, migrations, dependencies, other composition roots and `origin/main` are untouched.
- Focused release/shell/style tests: 40 passed; typecheck, lint, CSS parse, production web build and diff check passed. Browser screenshot verification remains unavailable in this environment.
- No public contract changed. Publish the exact tested fast-forward commit to `origin/dev` only.
