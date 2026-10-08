# Task W52-DEBT-GUARDS-128F2 — discover every feature mutation hook

task_id: W52-DEBT-GUARDS-128F2

## Outcome

The dashboard invalidation guard discovers `useMutation` calls in any TypeScript file
under `src/features/**/model/`, including `model/archive.ts`, and fails when a new hook
has no explicit invalidation-map entry.

## Depends on

- `W52-INT-128F7-01` — integrated and published at
  `68fd911639406c60f6c1661c9c35ba0def1e051a`.

## Frozen inputs

- Exact base `68fd911639406c60f6c1661c9c35ba0def1e051a`; domain revision 9 / 29
  identities, API 27 paths / 34 operations / 77 schemas, error catalog 23, migration
  head `0015_accounts_roles_registration`.
- D-128 F-2 in `reviews/W48-JUDGE-Z.md`; proposed W52 plan at
  `2b45a11ec558df1452a4822149e54d2fe0ddb57e` grants this guard file.
- Owner direction 2026-10-08: proceed without approval; only basic tests and lint;
  stand, QA and full gate remain D-139/D-140.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `web/tests/guards/dashboard-invalidation.guard.test.ts`
- enumerator_owner: `W52-DEBT-GUARDS-128F2`
- totality_query: `walkFiles(FEATURES_ROOT) over model/**/*.ts(x), retaining AST useMutation calls`

## Captured premise evidence

- premise: the guard currently narrows discovery by a filename prefix.

### P-01 — exact base and discovery

- captured_at: 2026-10-08
- command: `git rev-parse HEAD && rg -n '^function discoverMutationHooks|^  return walkFiles|names exactly the mutation hooks' web/tests/guards/dashboard-invalidation.guard.test.ts`
- captured_output:
  ```text
  68fd911639406c60f6c1661c9c35ba0def1e051a
  175:function discoverMutationHooks(): string[] {
  176:  return walkFiles(FEATURES_ROOT, (path) => /\/model\/use-[^/]+\.(?:ts|tsx)$/.test(path))
  249:  it('names exactly the mutation hooks this repository has, no more and no fewer', () => {
  ```
- interpretation: the filename restriction exists; the judge's G-2c probe shows it
  misses an otherwise valid mutation hook named `archive.ts`.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `web/tests/guards/dashboard-invalidation.guard.test.ts`
- `docs/program/W52-DEBT-GUARDS-128F2.md`

## Forbidden hotspots

Every other path, especially contracts, migration head, dependencies/locks, runtime
code, composition root, global styles and the separate D-128 findings.

## Non-goals

No invalidation policy change, no D-128 closure, W52 freeze, QA, stand, full gate,
release, tag or `origin/main` publication.

## Deliverables

- Discover mutation hooks by AST call within all feature `model` TypeScript sources,
  independent of filename prefix.
- A focused in-guard regression probe for `model/archive.ts` that would be red under
  the old discovery predicate; existing mapped hooks stay green.

## Required tests

- `npm --prefix web test -- --run tests/guards/dashboard-invalidation.guard.test.ts`
- `npm --prefix web run lint`; `git diff --check`. No stand or full gate.

## Integration contract

Hand back a clean branch from the exact dispatch SHA with only allowed paths. The
integrator may publish this guard correction to `origin/dev` after exact remote-ref
and fast-forward verification. D-128 remains open for F-1/F-10/F-11 and validation.

## Failure/idempotency/security cases

An executable `useMutation` in `model/archive.ts` must be discovered; comments and
strings containing the call must not count. Files outside feature `model` directories
must not enter the map. Repeated discovery yields the same sorted keys.

## Rollback / feature flag

Revert the guard commit. No runtime feature flag.

## Handoff

- changed files, commands/results, contracts, risks, integration notes, forbidden-hotspot proof.
