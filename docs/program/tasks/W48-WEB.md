# Task W48-WEB — one honest screen harness and hostile-string rendering

## Outcome

D-97, D-112 and D-113 close under one frontend owner: screen-wide instruments share one
router/query harness, unknown closed-vocabulary values render a typed fault, and maximum-length
unbroken user text does not overflow the measured 780 px screens.

## Depends on

- `W48-JUDGE-A` — completed at `d5655ec`
- `W48-FIX` — completed at `fad3c28748ef52bc9b5f711191ff0130483e0055`

## Frozen inputs

- Stage-B base: `fad3c28748ef52bc9b5f711191ff0130483e0055`
- API: 17 paths / 20 operations / 61 schemas, SHA-256
  `f043eb6c3a5bbba3cb95fff59039fff42582c79ae0dc8ff2ba261e2cb4583585`
- generated frontend contract and root dependency/lock files: frozen
- error catalog: 22; migration head: `0013_norm_embeddings`
- findings: D-97, D-112, D-113 and `W48-AUDIT` A-04

## Allowed paths

- `web/src/**`
- `web/tests/**`
- `docs/program/W48-WEB.md`

This task owns the single W48 global-style slot in `web/src/app/globals.css`.

## Forbidden hotspots

- backend sources, `contracts/**`, generated client files and error catalog
- root and frontend dependency/lock files
- migrations, `Makefile`, composition root, workflow and deployment files
- programme state/register/history, refs, tags, host and secrets

## Non-goals

- no backend/API/schema/error-catalog change
- no replacement of focused router mounts that are not screen-wide instruments
- no generic browser/layout framework or new dependency
- no raw fallback for an unknown transport enum and no invented server truth

## Deliverables

- shared screen harness used by all six screen-wide consumers named by D-97
- explicit typed failures for unknown cost basis and the wider A-04 closed-vocabulary cases
- focused user-string wrapping rules/tests for 200-character project names and 400-character
  unbroken comments
- completion report `docs/program/W48-WEB.md`

## Required tests

- focused harness/screen/dashboard/knowledge-base/style tests
- `npm --prefix web run lint -- --quiet`
- `npm --prefix web run typecheck`
- `npm --prefix web test -- --run`
- mutations: restore one private screen-wide provider copy; inject each unknown vocabulary value;
  remove the hostile-string wrapping rule — each must fail for its intended reason
- `git diff --check` and an allowed-path-only diff

## Integration contract

Every screen-wide guard obtains the same query client and mounted router from the shared harness,
while focused component tests may keep minimal mounts. Closed transport vocabularies fail closed
through `ErrorState`; raw values are never echoed as reviewer prose. User-controlled unbroken
strings may wrap within their container and cannot widen the document at 780 px.

## Failure/idempotency/security cases

- unknown `cost_basis`, verdict, category or event type is a visible typed fault
- query/router/session state differences remain explicit inputs rather than harness defaults
- maximum contract lengths and empty/null cases remain distinguishable
- no secret, live host, provider call or persistent browser state is used by the tests

## Rollback / feature flag

No feature flag: this is fail-closed rendering and CSS containment. Rollback is a revert of the
task commit; it changes no stored data or contract.

## Handoff

- changed files/checks: recorded in `docs/program/W48-WEB.md`
- contracts: unchanged
- known limit: final browser width evidence belongs to `W48-LIVE` and closing judges
- integration note: merge before LIVE evidence is taken, then drive the complete live journey
