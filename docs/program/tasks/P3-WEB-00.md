# Task P3-WEB-00 — frontend toolchain, composition root and UI seam contract

> **Status: delivered by Gate A session `A5`, on branch `agent/gate-a5` from base
> `5f360d8`.** Subsumed by `PROTOTYPE_WAVE_PLAN.md` §3 — this task ran inside `A5`
> together with `P3-API-01`, not as its own P03 dispatch. Sole writer of the frontend
> composition root, global styles and the web lock; that ownership now sits with `A5`
> and is frozen at the Gate A commit.
>
> Delivered in full except the Playwright configuration and the ESLint-fixture probe
> command, both recorded under Handoff. See `web/docs/PC01_UI_SEAM.md` for the frozen
> seam `B7` and `B8` consume.

## Outcome

`npm --prefix web ci && npm --prefix web run build` succeeds from a clean checkout on a
pinned toolchain, thin `app/` routes delegate to `_pages` public APIs with no domain
logic, and one frozen seam document fixes route URLs, widget public props and the
mandatory state contract every later P03 slice consumes.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until each
is accepted and integrated:

  - `P1-INT-00` — root command surface and environment names accepted
  - `P2-API-01` — the P02 OpenAPI document created and frozen at a named commit. That
    freeze, not the end of P02, is what unblocks frontend authoring: `P3-WEB-00` through
    `P3-WEB-02` may run **in parallel with the P02 tail** `P2-INT-01`, `P2-QA-01` and
    `P2-INT-02`, because they consume a frozen contract rather than a running backend.
  - owner decisions `OD-08` frontend package manager and composition owner, and `OD-09`
    the browser PDF rendering approach this task pins for `P3-WEB-02`

## Frozen inputs

- domain contract: `contracts/domain/v1/**` read only — state names, identifiers and
  error codes
- API contract: the P02 OpenAPI document at its accepted freeze commit, read only
- analysis/comparison/event contract: none consumed
- migration head: not consumed; the web tier reaches no database
- Bible §10 FSD rules and ADR-0009
- base commit: the P02 OpenAPI freeze commit, pinned by the integrator at dispatch

## Allowed paths

- `web/package.json`, `web/package-lock.json`, `web/.nvmrc`, `web/tsconfig.json`,
  `web/next.config.mjs`, `web/eslint.config.mjs`, `web/vitest.config.ts`,
  `web/playwright.config.ts`, `web/.env.example`, `web/.gitignore`
- `web/src/app/**`, `web/src/_app/**`
- `web/src/shared/ui/**`, `web/src/shared/config/**`, `web/src/shared/lib/**`
- `web/tests/guards/**`
- `web/FRONTEND_LOCK.json`, `web/docs/PC01_UI_SEAM.md`, `web/README.md`
- `docs/navigation/entries/p3-web-00.json`
- `docs/navigation/incidents/p3-web-00.jsonl` — created only if this task actually records an
  incident; never a shared append target
- `docs/program/tasks/P3-WEB-00.md`

## Forbidden hotspots

- `web/src/shared/api/**`, owned by `P3-API-01`
- every `_pages`, `widgets`, `features` and `entities` slice owned by `P3-WEB-01`–`04`
- the root `Makefile`, `pyproject.toml`, `uv.lock` and the repository-root `.env.example`
- `src/**`, `contracts/**`, `db/**`, `infra/**`, `tests/**`, CP-00 artifacts and Git tags

## Non-goals

- No product page, API call, PDF rendering, authentication or theming system.
- No root `Makefile` target and no private command alias: the nine targets are frozen by
  FF-01 and `P1-INT-00` excludes a frontend toolchain, so every P03 command is
  `npm --prefix web run …`. Adding one would be an FF-01 freeze-break and is owner decision
  `OD-16`, which this task does not take.

## Deliverables

- pinned Node, Next, React and TypeScript-strict toolchain with a reproducible
  `web/package-lock.json` and no floating range
- ESLint FSD boundary rules: downward imports only, slice public API only, no deep or
  cross-slice import, and raw `fetch`/`axios` forbidden outside `web/src/shared/api`
- the four `app/` routes `/projects`, `/projects/[project_uid]`,
  `/projects/[project_uid]/runs/[run_id]` and `.../review`, each a delegation-only file
- `_app` providers: a server-state query client and no global domain store
- shared primitives for the five mandatory states — loading, empty, error with retry,
  unsupported and not-applicable — a `RunStateBadge` whose value set is exactly
  `created`, `queued`, `running`, `validating`, `published`, `partial`, `failed`,
  `cancelled`, and a separate stage-status element whose value set is exactly `succeeded`,
  `partial`, `failed`, `skipped`. The seam document states that `succeeded` is legal on a
  stage row and illegal on a run badge
- reserved npm-script forwarders `api:generate`, `test:contract`, `test:unit`,
  `e2e:pc01` and `csv:verify` that fail explicitly until their owner lands, mirroring the
  FF-01 Makefile forwarder pattern. `web/playwright.config.ts` is delivered here with its
  test directory already pointing at the repository-root `tests/e2e/pc01`, so `P3-QA-01`
  can run the suite it owns without editing a web config it is forbidden from
- `web/docs/PC01_UI_SEAM.md` freezing route URLs, the `EvidenceViewer`, `DecisionPanel`
  and `ExportPanel` props, query-key namespaces, the run-progress polling interval and
  backoff, and the rule that only contract state names are rendered. The export panel has
  no polling contract, because the export endpoint is synchronous

## Required tests

- Command: `npm --prefix web ci`
  Expected: exit `0`; a second run leaves `git status --porcelain web` empty.
- Command: `npm --prefix web run build`
  Expected: exit `0` under `strict: true` with zero TypeScript errors.
- Command: `npm --prefix web run lint`
  Expected: exit `0`.
- Command: `npm --prefix web run lint -- web/tests/guards/deep-import.fixture.ts`
  Expected: non-zero, naming the boundary rule; proves the guard can fail.
- Command: `rg -n "succeeded" web/src/entities/audit-run web/src/widgets/run-progress`
  Expected: no match. The ban is on the **run** vocabulary only: the `AuditRun` success
  terminal is `published`. `succeeded` stays the correct `StageResult` status and is
  rendered on per-stage rows, so a repository-wide ban would fail on correct code.
- Command: compare the changed path set with `Allowed paths`.
  Expected: every changed path allowed and no forbidden hotspot present.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

Later P03 tasks rely on a building strict-TypeScript app, the four route URLs, the five
state primitives, the frozen widget props, and the rule that `web/src/app/**` and the
global stylesheet have exactly one writer. A later task fills a reserved forwarder and
never renames one.

## Failure/idempotency/security cases

- A missing API base URL fails at startup with an explicit message, never a localhost
  default.
- No secret, S3 endpoint or credential enters a client bundle; `web/.env.example` carries
  disposable values only.
- Repeated `ci` is byte-stable and the lock is never regenerated by a non-owner.

## Rollback / feature flag

Revert the web toolchain commit. No product data or migration is involved, and the
absence of the frontend does not affect P01 or P02 acceptance.

## Estimate

Effort P50 1.0 person-day, P80 2.0 person-days. Basis: toolchain pinning, four delegation routes and the state primitives. Calibration pending.

## Handoff

- navigation incident status, one of `recorded`, `none_observed` or
  `practice_not_exercised`; `recorded` requires the incident file above, and the other
  two assert that no incident occurred or that the practice was not followed
- changed files, containment proof, and the Node/Next/lock pins
- commands/results including the guard-failure probe output
- the frozen seam document version and known limits — no authentication, one reviewer

### Delivered by `A5`

**Pins.** Node `22.23.1` (`web/.nvmrc`, `engines.node`), npm `10.9.8`
(`engines.npm`, `packageManager`), Next `15.5.25`, React `19.3.0`, TypeScript `5.9.3`,
lockfileVersion 3. Every dependency and devDependency is an exact version; `.npmrc`
carries `save-exact=true` and `engine-strict=true` so a later `npm install` cannot
reintroduce a range. Recorded in `web/FRONTEND_LOCK.json`.

**Commands and results.** `npm --prefix web ci` exit `0`; `npm --prefix web run build`
exit `0` with all four routes compiled under `strict: true`,
`exactOptionalPropertyTypes` and `noUncheckedIndexedAccess`; `npm --prefix web run lint`
exit `0`; `npm --prefix web run test` exit `0`, 92 assertions; `git diff --check` exit
`0`. Guard-failure probes ran against a throwaway copy of the tree, never against a
tracked file — see `web/tests/guards/**`, where every detector is also exercised against
the defect it exists to catch.

**Seam document.** `web/docs/PC01_UI_SEAM.md`, frozen at the `A5` commit. It fixes the
four route URLs, the five mandatory states, the two badges and the `succeeded` split, the
transport surface, the query-key namespaces, the polling interval and backoff, and the
`B7`/`B8` ownership line.

**Not delivered, and why.**

- `web/playwright.config.ts` and the `@playwright/test` dependency. The package's
  install downloads browsers, which would make `npm --prefix web ci` non-hermetic and
  put the acceptance gate at the mercy of a browser CDN. `e2e:pc01` is reserved and
  fails explicitly naming `P3-QA-01`, which adds the dependency with the suite it owns.
  The intended test directory is still the repository-root `tests/e2e/pc01`.
- The literal probe command `npm --prefix web run lint -- web/tests/guards/deep-import.fixture.ts`.
  `npm --prefix web run lint` runs ESLint with `cwd=web`, so a repo-relative path does
  not resolve. The equivalent, which does: `npm --prefix web run lint -- --no-ignore
  tests/guards/fixtures/features/deep-import.fixture.ts`, exit `1`, naming
  `no-restricted-imports`. `web/tests/guards/eslint-boundary.guard.test.ts` runs it, and
  the two other violating fixtures, on every test run, with a legal fixture in the same
  directory as the control.
- The `rg` check over `web/src/entities/audit-run` and `web/src/widgets/run-progress`.
  Those trees belong to `B7` and do not exist yet. The rule they encode is carried
  instead by the type system: `RunStateBadge` takes the generated `RunState`, so
  `succeeded` does not compile onto a run badge, and a contract test asserts the run
  enum contains `published` and not `succeeded`.
- `docs/navigation/entries/p3-web-00.json`. Outside the paths `A5` was given.
  Navigation incident status: `none_observed`.

**Deferred decisions.** `OD-09`, the browser PDF rendering approach, is untaken and is
not pinned here; `B8` takes it with the evidence viewer. The transport side is settled:
`streamDocumentVersionContent` returns a `Blob` and accepts a `Range` header, with no
presigned link and no redirect.
