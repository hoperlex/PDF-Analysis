# W52-RELEASES-WEB — release interface hand-back

**Base:** published Stage-C WEB grant
`ffcf0ac0fe42ab8539cca9c33ee71c334f4272e0` on `origin/dev`.
**Lane:** `agent/w52-releases-web`. This lane changed no origin ref, tag or
deployed stand.

## 1. Changed files and result

An authenticated, complete account can open «История версий» from the avatar
menu. The panel shows the product version, dated release feed, legend, a
collapsed archive, and distinct loading, empty and typed-fault states.
The shell reads the current web build through a session-protected BFF route,
shows «Доступна новая версия» for a changed build, and lets the user postpone
that particular build. The same mount, focus, visibility and route triggers
re-read server-selected `whats_new`; closing «Что нового» marks its newest
version read.

Exact changed paths:

```text
infra/deploy/Dockerfile.web
tests/e2e/pc01/journey/manifest.json
web/.env.example
web/docs/PC01_UI_SEAM.md
web/src/_app/account-menu.tsx
web/src/_app/app-frame.tsx
web/src/_app/release-notices.module.css
web/src/_app/release-notices.tsx
web/src/app/bff/version/route.ts
web/src/entities/release/api/use-releases.ts
web/src/entities/release/index.ts
web/src/entities/release/model/presentation.ts
web/src/features/mark-release-notes-read/index.ts
web/src/features/mark-release-notes-read/model/use-mark-release-notes-read.ts
web/src/shared/api/index.ts
web/src/shared/api/query-keys.ts
web/src/shared/api/version-check.ts
web/src/shared/config/env.ts
web/src/shared/config/index.ts
web/src/shared/ui/menu.tsx
web/src/widgets/version-history/index.ts
web/src/widgets/version-history/ui/version-history.module.css
web/src/widgets/version-history/ui/version-history.tsx
web/tests/guards/dashboard-invalidation.guard.test.ts
web/tests/guards/rendered-language.guard.test.ts
web/tests/guards/server-credential.guard.test.ts
web/tests/unit/api/configuration-and-cache-keys.test.ts
web/tests/unit/qa_w50/primitives-keyboard.test.ts
web/tests/unit/qa_w50/r66-navigation.test.ts
web/tests/unit/release/bff-version.test.ts
web/tests/unit/release/history.test.ts
web/tests/unit/release/version-check.test.ts
web/tests/unit/shell/frame.test.ts
web/tests/unit/styles/screens.ts
web/tests/unit/ui/menu.test.ts
docs/program/W52-RELEASES-WEB.md
```

## 2. Checks

- Full frontend `npm test -- --reporter=dot`: **112 files, 1726 tests
  passed**. The first sandboxed run had six process-spawn `EPERM` errors;
  the permitted rerun passed all tests. The final edits to the banner's
  fail-closed build-ID read and contrast fixture were then covered by
  focused release/style tests: **39 passed**.
- `npm --prefix web run lint`, `typecheck` and `api:verify`: passed;
  generated client remains at 37 operations and the sealed digest.
- Journey conformance: **82 passed**. `git diff --check`: passed.
- A real local web image built from the final source. A separate Python
  computation over the planned inputs gave `wf07144b561bc2f98`; that
  same ID appeared in both the image's server and static client bundles.
  The first build exposed an absent optional `web/public` directory and a
  shell assignment that could continue with an empty ID; both were fixed
  before the successful final build.
- No full `make gate`, live journey, independent QA or deployment is claimed.
  Those belong to the later integration and acceptance tasks.

## 3. Contracts

No API, domain, generated-client, error-catalog, migration or
`contract_version` contract changed. The WEB lane adds an internal,
session-protected `GET /bff/version` response
`{ "web_build_id": string }` with `Cache-Control: no-store`; it is not an
API contract operation. The `releases` query-key namespace and journey's
optional release calls are recorded in the UI seam and guards.

## 4. Risks and limits

The 400-character release item, date, archive and panel states passed
rendered/component and contrast checks. A live 780-pixel browser layout
check remains for D-137–D-140: this host's snap Firefox could not start
inside its mount namespace, and no other browser binary is installed.
The web build ID follows the W52 input set (`src`, optional `public`,
lockfile, Next/TypeScript configs and public build arguments); a
Dockerfile-only change does not move it. No release-note prose judgment or
built-stand acceptance is claimed.

## 5. Integrator instruction

Review the clean lane against its published grant, merge into the Stage-C
integration candidate, repeat focused merged checks, then publish the
checked candidate to `origin/dev` with remote readback before starting
`W52-TRANSLATE-01`. `origin/main` requires the owner's separate direct
instruction for an exact checked SHA under `MAIN_AUTODEPLOY_POLICY.md`.

## 6. Forbidden-hotspot proof

Every path in §1 is in `W52-RELEASES-WEB`'s published allowed paths.
The generic menu action and four historical menu assertions were granted
by the exclusive integrator's `W52-INT-WEB-GRANT-01` correction before
the WEB lane edited them. No `contracts/**`, migration, generated client,
root dependency/lock, composition root, global style, `origin/main`,
tag or deployed stand changed. No checkpoint was created.
