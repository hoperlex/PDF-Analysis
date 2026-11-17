# Task UI-PARITY-R3 — screens look and behave like the original PDF-proverka, in our own style

task_id: UI-PARITY-R3
status: in progress (integration branch `integration/ui-parity-r3`, published to `origin/dev` at each publication point)

## Outcome

The screens of `web/` follow the layout, composition, density and sizes of the original PDF-proverka
(`/root/projects/PDF-proverka` at `0ae48ea1`), while palette, font, radii, shadows and components stay ours
(`--am-*` tokens) and the frontend keeps its Feature-Sliced Design layers. The work is a pool of 91 tasks
(15 general `UIP-G-*`, 76 per screen `UIP-Sxx-NN`) delivered in five stages and eight publication points.

## Owner decisions (local records, not in git)

- `.local/reports/ui-compare-2026-11-16/decisions-2026-11-16.md` — global decisions G1–G13 (poll 2026-11-16).
- `.local/reports/ui-compare-2026-11-16/screen-decisions-2026-11-16.md` — per-screen variants, general UI/UX
  answers, the three principles and the administration rule.
- `.local/reports/ui-compare-2026-11-16/task-pool-draft-2026-11-16.md` — the task pool (91 tasks), the source of
  truth for each task's result, allowed paths, non-goals, FSD layers and checks.
- `.local/reports/ui-compare-2026-11-16/implementation-plan-2026-11-16.md` — stages, publication points, checks.
- `.local/reports/ui-compare-2026-11-16/ui-compare-2026-11-16-r3.pdf` — the illustrated comparison, edition 3.

Rulings that stay in force and are not to be broken without a new owner answer: the 2026-11-12 decision («Разбор»
is not renamed; no «Экспертная оценка» mode, draft or «Сохранить решения»; ✓/✕ only for the expert), R-151j
(severity is the expert's), R-153a (one-button run), G13-C (roles, no matrix), G12-B (technical details off the
main view). Administration (users, registration requests, sign-in journal) is not fitted to the original.

## Principles

1. Maximum visual closeness to the original: layout, element set, density, sizes.
2. Our own base style key: palette, font, radii, shadows, components (`--am-*`); the original's colours are not
   copied.
3. FSD: `_app → _pages → widgets → features → entities → shared`; imports only downward and only through the
   public API `@/<layer>/<slice>` (checked by `web/eslint.config.mjs` and
   `web/tests/guards/eslint-boundary.guard.test.ts`). A piece shared by two slices of one layer lives in a lower
   layer: `entities/expert-decision` («✓ ✕ Причина»), `entities/stage-layout` («Модели по этапам»),
   `entities/project` (section colours).

## Stages, publication points and slot queues

| Stage | Tasks | Publication point |
|---|---|---|
| 1. Material | G-01, G-02, G-03, G-04, G-11, G-14, G-17, G-13 | P1 |
| 2. Shell | G-05, G-06, G-07, G-08, G-16 | P2 |
| 3. Document card | G-09, S04 (P3a); S06, S07, S08, S09, S10 (P3b) | P3a, P3b |
| 4. Overview and section | G-10, S01, S02, S03 | P4 |
| 5. The rest | S05, S11–S13 (P5a); S14–S17 (P5b); S18 record, S19, S21, S22 (P5c) | P5a, P5b, P5c |

Shared slots are taken by one lane at a time, in this order:

- API contract: G-05 → S04-01 → G-10 → S03-02 → S11-05 → S12-01 → S14-01 → S15-01 → S16-02. The integrator raises
  `CONTRACT_VERSION` once per stage publication, after all contract lanes of that stage are merged.
- Migrations: G-05 (last selected object) and G-10 (document «Группа»), numbered after `0068_reviewable_findings`.
- `web/src/app/globals.css`: G-11 → G-14 → G-17.
- `web/src/shared/ui`: G-04, then G-14.
- Menu (`web/src/_app/navigation.ts`, `frame-navigation.tsx`): G-07.
- Document frame (`web/src/widgets/document-context/**`): G-09, then S04-02.

## Roles

- Integrator (one session): plans, writes lane briefs from the pool records, holds every slot, reviews and merges
  lane branches with `git merge --no-ff`, runs publication checks, publishes to `origin/dev` by fast-forward,
  produces the static preview and the point reports in `.local/reports/ui-parity-r3/`.
- Implementation lanes (Sonnet subagents): one lane per task, or per group of one screen's tasks sharing files;
  each works in its own worktree `.local/worktrees/uip-r3-<id>` on branch `agent/uip-r3-<id>`, one commit per
  task, no push/merge/rebase.
- Data-gathering lanes (Haiku subagents): call sites, counts, preview screen lists; no product code.

## Checks

Reduced checks by direct owner instruction of 2026-11-16: no `make gate`, `make light-acceptance`,
`make gate-fast`, full `tests/unit` or `web tests/unit`, e2e or live stand. Per task: `npm --prefix web run
typecheck`, the task's named vitest files, `eslint` on the task's paths, named pytest files for server parts;
contract tasks add `api:verify`, `test:contract` and `tests/contract/api_v1`; migrations get one targeted
upgrade/downgrade/upgrade run on a throwaway in-memory Postgres+MinIO. Before each publication: the release-note
form test, typecheck, the union of the point's task tests, `npm --prefix web run build` (the only check of the
Next client/server boundary) and `git diff --check`. Publication to `origin/dev` does not wait for the owner's
preview; the preview is produced afterwards for information.

## Depends on

- `UI-PARITY-01` ([record](../UI-PARITY-01.md)) — completed; the earlier parity programme whose rulings R-150/R-151 this programme revises where
  the owner said so.

## Frozen inputs

- API contract: `1.55.0` at the base; raised by the integrator per stage publication.
- migration head: `0068_reviewable_findings` at the base.
- base commit: `ab638e460` (`origin/dev`, product 0.29.0).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: none

## Publication authority

- development_target: origin/dev
- origin_main_authority: none; `origin/main` only by a separate direct owner instruction naming the exact SHA

## Rollback

Each publication point is one fast-forward of `origin/dev`; reverting the merge commits of a point restores the
previous screens. No feature switch is introduced; the two migrations carry their downgrade.

## Publications

| Point | `origin/dev` SHA | Note revision | Tasks |
|---|---|---|---|
| P1 | `39198d68c` | 0.30.0 rev 1 | G-01, G-02, G-03, G-04, G-11, G-13, G-14, G-17; FIX-01…07 |
| P2 | `5a564a8cb` | 0.30.0 rev 2 | G-05, G-06, G-07, G-08, G-16; S04-01, G-10 (API only); CONTRACT-02 (1.56.0); FIX-02, FIX-08 |
| P3a | `907e968a8` | 0.30.1 rev 1 | G-09, S04-02..04, S06-01..03, S01-01..03; FIX-09..12 |
| P3b | `227b2586e` | 0.30.2 rev 1 | S06-04..08, S07-01, S08-01..03, S09-01, S10-01; S03-02, S11-05, S12-01, S14-01 (API) + CONTRACT-03 (1.57.0); FIX-13..16 |
| P4 | `35bc680ee` | 0.30.3 rev 1 | S03-01, S03-03, S02-01..03, S18-01, S19-01, S19-03, S21-01, S09-02..04 (publisher session; main by owner PR #59 `810fdcfe0`) |
| P5 | `1a6cf86e5` | 0.30.4 rev 1 | S02-04..07; FIX-17..20; database pins of 0068..0070 resealed by the publisher |
| P6 | `6ea6e36ac` | 0.30.5 rev 1 | S13-01..04, S15-02, S05-01..04, S11-01..04, S11-06, S12-02..04; FIX-21..23 |
| P7 | `1953f94f9` | 0.30.6 rev 1 | S14-02..04, S16-01, S17-01..03, S22-02, S22-03; FIX-24, FIX-26 |
