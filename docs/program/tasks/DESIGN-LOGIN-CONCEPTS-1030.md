# Task DESIGN-LOGIN-CONCEPTS-1030 — варианты экрана входа для выбора

## Outcome

Владелец получает три самостоятельных PDF-концепции входа, каждая с полноразмерными светлой и тёмной версиями и отдельной страницей с пояснениями анимации и адаптации. Светлая версия основная. Концепции показывают существующую оболочку с боковой панелью и верхним рядом.

## Depends on

- `DESIGN-REF-08-FAVICON` (completed and published at `5d7567d4b6776c7c43ec9a4abc94653ec86cad8f`).

## Frozen inputs

- Base: `5d7567d4b6776c7c43ec9a4abc94653ec86cad8f` (`origin/dev`).
- API/contract: `1.14.0`; migration head `0043_stage_ai_generations`.
- Current guest frame, sign-in form fields/copy, guard behavior, logo and two showcase palettes are reference inputs only.
- Owner-provided Hynex reference: `https://me.muz.li/orbix-studio/hynex-healthcare-dashboard-design-2`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- `web/src/_pages/sign-in/ui/sign-in-page.tsx` renders a centered card with sign-in form and access-request link; `AppFrame` wraps it with the sidebar and utility row. For a guest, `buildNavigation(session)` yields no active work links. The current logo/favicon use a three-stroke teal mark.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev` for design artifacts only
- origin_main_authority: none

## Allowed paths

- `docs/design/login-concepts/**`
- `docs/program/tasks/DESIGN-LOGIN-CONCEPTS-1030.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

- Application source, global styles, registry, APIs, contracts, migrations, dependencies, composition roots, infrastructure and `origin/main`.

## Non-goals

- Implementing or changing the sign-in page, enabling guest navigation, adding product metrics, changing authentication or deploying a chosen variant.

## Deliverables

- Three 3-page PDFs: light mockup, dark mockup, animation/UX notes.
- Generator source and short comparison/readme for review and later implementation.
- Visual inspection of rendered PDF pages and basic PDF structural checks.

## Required checks

- Generate all PDFs from the source script; verify each has three 16:10 pages and render first/second/third pages back to PNG for visual inspection.
- `git diff --check`; no full app gate or review window per owner instruction.

## Integration contract

- PDF designs are proposals. If implemented later, guest preview navigation remains inert until access is granted; the existing form, BFF action and return-path rules remain the behavioral reference. No runtime behavior changes in this task.

## Failure/idempotency/security cases

- Sample interface content is labelled demonstration; no real project/client data. Motion descriptions include reduced-motion fallback. Embedded artwork/fonts have no external network references.

## Rollback / feature flag

- Remove/revert design artifacts; no feature flag, migration or running behavior.

## Handoff

- Changed files: `docs/design/login-concepts/**`, this task file and `docs/program/CURRENT_STATE.md` only. Application source, global styles, registry, contracts, migrations, dependencies, composition roots and `origin/main` are untouched.
- Three PDFs generated; `pdfinfo` reports 3 pages at 1440 × 900 for each. All six theme pages and all three notes pages were rendered back from PDF and visually inspected. Each light preview is also saved as a PNG. `git diff --check` passed.
- No public contract or behavior changed. Design artifacts can be published as one fast-forward development commit; implementation waits for owner's variant choice.
