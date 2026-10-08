# Task W52-DEBT-GUARDS-128F1 — discover and unify screen test providers

task_id: W52-DEBT-GUARDS-128F1

## Outcome

The D-97 screen-provider guard discovers consumers under `web/tests/unit/screens`,
rejects a new private provider there, and all tracked screen tests render through the
shared harness. The existing language guard also uses that provider contract.

## Depends on

- `W52-INT-128F11-01` — integrated and published at
  `3bf74d37f8538a2969a838fc270d1e3a4bb575c1`.

## Frozen inputs

- Exact code base `3bf74d37f8538a2969a838fc270d1e3a4bb575c1`; domain revision 9 / 29
  identities, API 27 paths / 34 operations / 77 schemas, error catalog 23, migration
  head `0015_accounts_roles_registration`. W52 has a proposal, no frozen contract change.
- D-128 F-1 in `reviews/W48-JUDGE-Z.md`; W52 proposal `2b45a11` assigns the
  guard repair. Existing test migrations and a baseline-red query-provider mount are
  included explicitly because the enlarged guard must pass honestly.
- Owner direction 2026-10-08: proceed without approval; only basic tests and lint;
  stand, QA and full gate remain D-139/D-140.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `web/tests/guards/screen-set.guard.test.ts`
- enumerator_owner: `W52-DEBT-GUARDS-128F1`
- totality_query: `walkFiles` across `web/tests/guards`, `web/tests/unit/styles`, and
  `web/tests/unit/screens` for TS/TSX consumers, excluding only the provider-owning
  `web/tests/unit/screens/harness.ts`.

## Captured premise evidence

- premise: F-1 misses tracked private mounts and the existing guard is red on a query mount.

### P-01 — exact base and private mounts

- captured_at: 2026-10-08
- command: `git rev-parse HEAD; rg -n 'AppRouterContext.Provider|QueryClientProvider' web/tests/unit/screens/*.ts web/tests/guards/rendered-language.guard.test.ts`
- captured_output:
  ```text
  3bf74d37f8538a2969a838fc270d1e3a4bb575c1
  web/tests/unit/screens/stage-comparison.test.ts:60:      AppRouterContext.Provider,
  web/tests/unit/screens/project-sections.test.ts:59:      AppRouterContext.Provider,
  web/tests/unit/screens/forms-and-pages.test.ts:141:        AppRouterContext.Provider,
  web/tests/guards/rendered-language.guard.test.ts:56:import { QueryClientProvider } from '@tanstack/react-query';
  web/tests/guards/rendered-language.guard.test.ts:1105:  return createElement(QueryClientProvider, { client }, createElement(RegistrationQueue));
  web/tests/unit/screens/run-cache-shape.test.ts:91:        AppRouterContext.Provider,
  web/tests/unit/screens/run-cache-shape.test.ts:123:        AppRouterContext.Provider,
  web/tests/unit/screens/cold-load.test.ts:113:    createElement(AppRouterContext.Provider, { value: stubRouter([]) }, element),
  web/tests/unit/screens/harness.ts:115:  return render(createElement(QueryClientProvider, { client }, withEagerWidgets(element)));
  web/tests/unit/screens/harness.ts:139:  return renderWith(client, createElement(AppRouterContext.Provider, { value: router }, element));
  ```
- interpretation: all six consumers require the shared provider contract. The
  existing `screen-set` guard fails on the query mount even before expansion.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `web/tests/guards/screen-set.guard.test.ts`
- `web/tests/guards/rendered-language.guard.test.ts`
- `web/tests/unit/screens/harness.ts`
- `web/tests/unit/screens/cold-load.test.ts`
- `web/tests/unit/screens/forms-and-pages.test.ts`
- `web/tests/unit/screens/stage-comparison.test.ts`
- `web/tests/unit/screens/run-cache-shape.test.ts`
- `web/tests/unit/screens/project-sections.test.ts`
- `docs/program/W52-DEBT-GUARDS-128F1.md`

## Forbidden hotspots

Every other path, especially contracts, migration head, dependencies/locks, runtime
code, composition root, global styles and the separate D-128 F-10 finding.

## Non-goals

No runtime behavior change, D-128 closure, W52 freeze, QA, stand, full gate, release,
tag or `origin/main` publication.

## Deliverables

- Guard discovers all three test directories and proves that a new unit screen with
  a private provider fails. Shared harness is the only provider implementation.
- Five tracked screen files use `renderScreen` without private router copies.
- Language guard seeds its queue on the same client passed to `renderScreen`.

## Required tests

- Focused Vitest run for the guard, language guard and five migrated screen files.
- `npm --prefix web run lint`; `git diff --check`. No stand or full gate.

## Integration contract

Hand back a clean branch from the exact dispatch SHA with only allowed paths. The
integrator may publish this test-only correction to `origin/dev` after exact remote-ref
and fast-forward verification. D-128 remains open for F-10 and deferred validation.

## Failure/idempotency/security cases

Adding a TS/TSX file under `unit/screens` that privately mounts either provider must
fail. The harness implementation itself must not be treated as a consumer. A screen
test importing `./harness` must be recognized. Queue variants keep their own seeded
status and repeatable markup.

## Rollback / feature flag

Revert the test commit. No runtime feature flag.

## Handoff

- changed files, commands/results, contracts, risks, integration notes, forbidden-hotspot proof.
