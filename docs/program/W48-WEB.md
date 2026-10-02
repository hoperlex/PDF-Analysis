# W48-WEB — shared screen harness and fail-closed rendering

## Result

**DONE.** D-97, D-112, D-113 and audit finding A-04 are repaired in the frontend lane.

- The five screen-wide consumers named by D-97 now use
  `web/tests/unit/screens/harness.ts::renderScreen`; only focused router-behaviour tests retain
  direct router mounts.
- An unknown `cost_basis` produces the dashboard's typed incomplete-data `ErrorState` rather
  than a blank label/caption.
- Unknown knowledge-base category, event type, current verdict or nullable event verdict produces
  one closed-vocabulary `ErrorState`; no partial row or raw value is rendered.
- Project/list rows and knowledge-base rows have intrinsic-width containment and inherited
  `overflow-wrap: anywhere`. Fixtures exercise a 200-character project name and an unbroken
  400-character reviewer comment.

No backend, API/generated contract, dependency, lock, migration, composition, workflow or deploy
file changed.

## Changed files

Production/UI:

- `web/src/widgets/dashboard/ui/run-activity-panel.tsx`;
- `web/src/widgets/knowledge-base/ui/knowledge-base.tsx`;
- `web/src/app/globals.css` — the W48 global-style slot.

Shared harness and consumers:

- `web/tests/unit/screens/harness.ts`;
- `web/tests/guards/prepared-sections.guard.test.ts`;
- `web/tests/guards/screen-set.guard.test.ts`;
- `web/tests/guards/gender-agreement.guard.test.ts`;
- `web/tests/guards/rendered-language.guard.test.ts`;
- `web/tests/unit/styles/screens.ts`.

Focused regressions:

- `web/tests/unit/widgets/dashboard.test.ts`;
- `web/tests/unit/screens/knowledge-base.test.ts`;
- `web/tests/unit/styles/styling-layer.test.ts`;
- this report.

## D-97 — one screen-wide provider contract

Before this task, five screen-wide files instantiated their own router and/or query provider in
addition to the shared harness. They now all import `renderScreen`, pass query state through an
explicit `QueryClient`, and rely on the same router implementation. The guard scans those five
consumer sources and fails on a private `AppRouterContext.Provider` or `QueryClientProvider`.

The remaining direct router-provider occurrences are six focused component/router tests where
mount behaviour is itself the subject; D-97 explicitly excludes replacing every provider
occurrence. A full query after repair returned only those focused tests plus the shared harness.

## D-113 / A-04 — unknown values do not look plausible

Both screens validate runtime values against generated contract arrays before indexing label
maps. The invalid value is never used as reviewer prose and never survives in a partial data row.

| injected value | old observable result | repaired result |
| --- | --- | --- |
| `cost_basis='guessed'` | empty label and caption | dashboard panel `data-panel-fault="incomplete"` |
| `current_verdict='guessed'` | raw `guessed` | knowledge-base closed-vocabulary fault |
| `category='guessed'` | empty category span | same fault |
| `event_type='guessed'` | empty event span | same fault |
| nullable event `verdict='guessed'` | raw data attribute | same fault |

The language guard now renders the new failure branch, so Russian UI coverage did not become
vacuous when the state was added.

## D-112 — hostile-width strings

The containment roots are `.am-state` (project rows on `/projects` and `/dashboard`) and
`.am-kb__record` (finding text and reviewer comments). Both declare `min-width: 0` and
`overflow-wrap: anywhere`; descendants inherit wrapping without changing stored/display text.
The style guard reads the exact declarations and fails if either property is removed. Component
fixtures prove that the maximum project name and the 400-character unbroken comment reach those
contained roots unchanged.

Pixel evidence at 780 x 900 is deliberately not fabricated by static SSR. The merged tree must be
driven by `W48-LIVE` and both closing judges; that is the integration contract of this task.

## Mutation evidence

All production mutations ran in a disposable `/tmp` copy and the copy was removed afterwards.

| reintroduced defect | focused result |
| --- | --- |
| add `AppRouterContext.Provider` to a named screen-wide consumer | screen-set guard: **1 failed / 10 passed**, naming the file |
| bypass the cost-basis validation | dashboard: **1 failed / 17 passed**, showing the old blank-label markup |
| bypass knowledge-base vocabulary validation | knowledge-base: **4 failed / 10 passed**, one per invalid field |
| replace both `overflow-wrap: anywhere` declarations with `normal` | styling layer: **1 failed / 10 passed**, naming `.am-state` |

The committed tree was re-run green after the disposable mutations.

## Checks

```text
npm --prefix web run typecheck
  exit 0

npm --prefix web run lint -- --quiet
  exit 0

focused 8 files
  122 passed

npm --prefix web test -- --run
  82 files, 1176 passed

git diff --check
  exit 0
```

The first sandboxed full-suite attempt produced six infrastructure failures because nested
`eslint`/`tsc` processes were denied with `EPERM`; it is not accepted as evidence. The complete
rerun outside that process sandbox passed all 1176 tests. Dependencies came from the existing
exact-lock installation; the temporary `web/node_modules` link was removed before handoff.

## Contracts, limits and integration

API remains 17 paths / 20 operations / 61 schemas, error catalog 22, migration head
`0013_norm_embeddings`. There is no contract or generated-client change.

Known limitation: SSR plus a CSS relationship proves the containment rule and fixture lengths,
not the browser's computed `scrollWidth`. `W48-LIVE` must measure `/projects`, `/dashboard` and
`/knowledge-base` at 780 px with those data shapes after integration.

Integration order: take `W48-PORTS` first, then this commit, run the focused frontend suite and
continue to `W48-LIVE`. No push, tag or deployment belongs to this lane. Rollback is a revert of
the task commit; stored data is unaffected.

## Forbidden-hotspot proof

The diff is limited to `web/src/**`, `web/tests/**` and this report, all explicitly allowed.
`contracts/**`, generated client files, backend sources, dependencies/locks, migrations,
`Makefile`, composition root, workflow/deploy files, programme state/register/history, refs,
tags, host state and secrets are untouched.
