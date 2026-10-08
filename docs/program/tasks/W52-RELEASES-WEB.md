# Task W52-RELEASES-WEB — show release history and update notices

task_id: W52-RELEASES-WEB

## Outcome

An authenticated user can read release history in the account menu, see
server-selected What's New once and dismiss a build-update banner. The panel
and dialog have Russian loading, empty and fault states.

## Depends on

- `W52-RELEASES-API`, accepted by `W52-INT-C-API-01` on `origin/dev`.

## Frozen inputs

- Start from the exact `origin/dev` SHA read back by `W52-INT-C-API-01`;
  record it in the lane report. No local pre-publication candidate is a grant.
- API 30 paths / 37 operations / 83 schemas; 23 error codes; domain
  revision 9 / 29 identities; migration head `0016_release_notes`;
  `contract_version=1.0.0-draft.1`.
- `dispatch/W52-PLAN.md` §3.5 and Stage C, sealed generated client and
  server-side `whats_new`. D-137–D-140 own deferred QA and complete gate.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `web/src/shared/api/query-keys.ts`,
  `tests/e2e/pc01/journey/manifest.json` and the rendered-language matrix
- enumerator_owner: `W52-RELEASES-WEB` for Stage C
- totality_query: query-key shape, journey-manifest and rendered-language
  guards enumerate the new release state and allowed calls.

## Captured premise evidence

- premise: the API lane is complete, with the sealed wire surface unchanged;
  the plan grants the WEB lane the named UI, BFF and inventory paths.

### P-01 — API acceptance boundary and current pin sweep

- captured_at: 2026-10-08
- command: `git rev-parse HEAD; python3 tools/plan/pin_sweep.py table | rg '^(infra/deploy/|web/src/_app/|web/src/shared/|web/tests/|docs/manual-tests/|tests/e2e/pc01/)'`
- captured_output:
  ```text
  81e5181a34dd6905814f1ecb02de305e2e99aabd
  infra/deploy/compose.server.yml table: catalogue
  infra/deploy/deploy.sh table: catalogue
  infra/deploy/reset.sh table: catalogue
  ```
- interpretation: WEB consumes the frozen API and generated client; the
  release service table is not WEB's grant.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `web/src/entities/release/**`, `web/src/widgets/version-history/**`,
  `web/src/features/mark-release-notes-read/**`
- `web/src/_app/**` — account-menu item, banner island and What's New host only
- `web/src/shared/ui/menu.tsx` — one generic client-side action item for
  opening the panel from the existing keyboard-accessible account menu;
  added by the exclusive integrator before WEB implementation because the
  sealed primitive has only link and submit items
- `web/src/shared/api/version-check.ts`, `web/src/shared/api/index.ts`,
  `web/src/shared/api/query-keys.ts` — version fetch, export, release namespace
- `web/src/shared/config/env.ts`, `web/src/shared/config/index.ts` — build-ID
  read and one export line; `web/.env.example` — one build-ID line
- `web/src/app/bff/version/route.ts` — authenticated session read through
  `../session/store`, with no server-env import
- `infra/deploy/Dockerfile.web` — build-ID computation in the existing build
  `RUN` only, no new `COPY`
- `web/tests/guards/server-credential.guard.test.ts` — public build-name list
  only; `web/tests/guards/dashboard-invalidation.guard.test.ts` — one
  mark-read mapping; `web/tests/guards/query-key-shape.guard.test.ts`,
  `web/tests/guards/rendered-language.guard.test.ts` — release namespace,
  matrix and fixtures only
- `web/tests/unit/styles/screens.ts` — panel/archive/banner contrast states;
  `web/tests/unit/api/configuration-and-cache-keys.test.ts`,
  `web/tests/contract/narrow-sets.contract.test.ts` — namespaces only
- `tests/e2e/pc01/journey/manifest.json` — optional `GET /releases` per
  route and first-route `PUT /me/release-notes` only
- `web/docs/PC01_UI_SEAM.md` — §6 release state only
- `web/tests/unit/release/**`, `docs/program/W52-RELEASES-WEB.md`
- `web/tests/unit/ui/menu.test.ts`, `web/tests/unit/shell/frame.test.ts`,
  `web/tests/unit/qa_w50/r66-navigation.test.ts`,
  `web/tests/unit/qa_w50/primitives-keyboard.test.ts` — only assertions
  about the new account-menu action and its four-item keyboard order;
  narrow integrator correction, not general W50 test ownership
- local `agent/w52-releases-web` branch/worktree and ignored environment

## Forbidden hotspots

Every other path: `contracts/**`, migrations, release backend, root
dependencies/locks, generated client, composition root, `globals.css`,
`origin/dev`, `origin/main`, tags and deployment. A newly found path
requires an integrator grant correction before editing.

## Non-goals

No new API operation or schema, server-side `whats_new` rule, release-note
prose, runbook translation, full gate, QA, live acceptance or publication.

## Deliverables

- Version-history panel with date strings, legend, archive and typed faults.
- Build-ID BFF/fetch, banner triggers on mount, focus, visible state and
  route change, and per-build Later dismissal; no polling timer.
- Server-selected What's New shown on mount and re-read at banner triggers;
  close marks the newest shown version and navigation stays available.
- Focused UI/guard/journey evidence and a six-part hand-back.

## Required checks

- Vitest release behavior including 780-px panel/400-character item,
  equal/changed build, Later per build, API-only release, unknown kind and
  loading/empty/fault states; journey manifest guard.
- `npm --prefix web run api:verify`, lint, typecheck and focused contract,
  query-key, language, contrast and credential guards.
- `git diff --check`, exact changed-path review. Report every unrun check.
  Full `make gate`, independent QA and built-stand acceptance remain D-137–D-140.

## Integration contract

The sealed API supplies `GET /system/version`, `GET /releases` with
`whats_new`, and `PUT /me/release-notes`; the web lane reads these via the
generated client and session-authenticated BFF. Use only reserved
`gate-w52web` ports `56820`, `60420/60421` if local services are required;
recheck host availability before start. Hand back a clean branch to the
integrator, who merges it before TRANSLATE and Stage C2.

## Failure / idempotency / security

On a version-fetch failure, hide the banner and retry on the next trigger;
401 returns to sign-in. Unknown note kinds show a typed fault. The dialog
can be dismissed without blocking navigation. No token or secret enters
`NEXT_PUBLIC_*` or a browser response.

## Rollback / feature flag

Revert this UI candidate on the development line if necessary. Dismissing
the banner is keyed to its build ID; there is no deployment or runtime
feature flag in this task.

## Handoff

Return changed files, checks/results, contracts, risks, integrator steps
and forbidden-hotspot proof. No checkpoint or tag.
