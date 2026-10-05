# W48-TAILS report

## Result

The remaining W48 audit tails are closed on base
`03c04a1d87fda862d085a6a49d0a46f2692f7ffd`:

- every T-1 source hit is classified below; a lookup reachable from transport data now
  fails closed with a visible typed marker, while total lookups name the executable
  narrowing that makes them total;
- `.am-history__event` and `.am-history__comment` both contain unbroken user text with
  `min-width: 0` and `overflow-wrap: anywhere`;
- the proxy comment now attributes the path count and relative-path statement to their
  separate real locations in `src/auditmanager/api/app.py`;
- the local S3 README and bucket initializer describe the repository-owned MinIO build and
  no longer present the reserved legacy `FOUNDATION_S3_IMAGE` or
  `FOUNDATION_S3_MC_IMAGE` names as live inputs.

## T-1 classification

The inventory command from the task was re-run against the task tree:

```text
rg -n 'LABELS\[|_LABEL\[|as ProviderMode' \
  web/src/widgets web/src/entities web/src/shared/ui -l
```

The two Stage-B repairs remain in `knowledge-base.tsx` and
`run-activity-panel.tsx`. The ten remaining task-base files classify as follows.

| site | classification and executable evidence |
| --- | --- |
| `widgets/decision-history/ui/decision-history.tsx` | May miss on `event_type` or `verdict`; validates both generated value sets before ordering/rendering and emits `data-history-fault="closed-vocabulary"`. Two injected unknowns are in `viewer-and-panels.test.ts`. |
| `entities/expert-decision/ui/verdict-badge.tsx` | May miss when a malformed value crosses the TypeScript-only prop boundary; checks `VERDICT_VALUES` and emits `data-closed-vocabulary-fault="verdict"`. |
| `widgets/dashboard/ui/verdicts-panel.tsx` | Total after `summarizeVerdictBreakdown`: that model refuses unknown/duplicate/missing rows and returns `ok` only for exactly `VERDICT_VALUES`; the panel itself iterates that same tuple. `widgets/dashboard.test.ts` injects the unknown `escalated` row and requires `data-panel-fault="incomplete"`. |
| `shared/ui/run-state-badge.tsx` | May miss for `RunState` or the optional provider qualifier; checks `RUN_STATE_VALUES` / `PROVIDER_MODE_VALUES` and emits a typed `run-state` or `provider-mode` fault. |
| `shared/ui/stage-status-badge.tsx` | May miss at the runtime prop boundary; checks `STAGE_STATUS_VALUES` and emits a typed `stage-status` fault. |
| `entities/audit-run/ui/stage-table.tsx` | May miss for a row stage id, status or dependency id; validates all three before any label lookup and hides the entire table behind `data-stage-table-fault="closed-vocabulary"`. Three injections cover the three keys. |
| `entities/audit-run/model/run-presentation.ts` | The provider-mode cast was unnecessary. It is replaced by `isProviderMode`, whose `Set` is built from `PROVIDER_MODE_VALUES`; only a successful membership check returns a table key, otherwise the explicit `unknown` sentinel is returned. Existing `run/provider-mode.test.ts` injects absent, empty and unrecognised modes. |
| `widgets/run-progress/ui/run-progress.tsx` | Run state, degraded-stage ids and reported stage id/status may miss; `hasKnownRunVocabulary` checks them before `runOutcome`, `stageRows` or a label lookup and the widget emits `data-run-progress-fault="closed-vocabulary"`. Four injected cases cover those fields. Provider mode and cost basis remain total through `providerModeLabel` and `runCost` narrowing respectively. |
| `widgets/stage-comparison/ui/stage-comparison.tsx` | Transport-provided run/stage keys may miss and are checked by `hasKnownRunVocabulary` before comparison. Three injections cover run state, stage id and stage status. `FACT_LABELS` is total because `comparedFacts` constructs its rows from the fixed `FactId` tuple; `COMPARISON_LABELS` is total because `compareReadings` constructs the closed `Comparison` union; provider mode and cost basis are narrowed before indexing. |
| `widgets/export-panel/ui/export-panel.tsx` | An unknown run state previously fell through as “not exportable” and then missed `STATE_LABELS`; it now checks `RUN_STATE_VALUES` first and emits `data-export-fault="closed-vocabulary"`. The injected unknown asserts that no exportability decision is shown. Provider mode is covered by `RunStateBadge`'s own typed check. |

The shared badge/table injections live in
`web/tests/unit/run/closed-vocabulary-badges.test.ts`. The screen census also renders the
new fault states, so the language and contrast instruments see their actual markup.

## T-2, T-4 and T-7 evidence

- `web/tests/unit/styles/styling-layer.test.ts` extracts the declarations of
  `.am-history__event` and `.am-history__comment` and requires both containment properties,
  alongside the existing project/knowledge-base selectors.
- `tests/contract/api_v1/test_surface_counts_in_prose.py` remains able to mutate the literal
  `the seventeen paths` in `nginx.conf`; the corrected comment keeps that measured literal
  while no longer merging two separate source comments into one quotation.
- `rg -n 'FOUNDATION_S3_IMAGE|FOUNDATION_S3_MC_IMAGE' infra/local/README.md
  infra/local/bucket-init.sh` returns no matches. The reserved names remain untouched in
  the Makefile, outside this task's grant.

## Mutation evidence

All mutations ran in the session-specific copy
`/tmp/w48-tails-unknown-mut.fC2ZRy/web`; the worktree was never edited for a probe.

1. Renaming every new `data-*-fault` marker to `data-*-note`, while keeping the visible
   branches, made the five unknown-injection suites red: **17 failed / 130 passed**, exit
   1. Failures named every injected class: decision event/verdict, verdict badge, run state,
   provider mode, stage status/id/dependency, run-progress state/degradation/stage, stage
   comparison state/stage, and export state.
2. Removing both containment declarations from `.am-history__event` and
   `.am-history__comment` made `styling-layer.test.ts` red: **1 failed / 10 passed**, exit 1,
   first diagnostic `.am-history__event has no overflow-wrap containment`.

## Changed files

- runtime/UI: `web/src/entities/audit-run/index.ts`,
  `web/src/entities/audit-run/model/run-presentation.ts`,
  `web/src/entities/audit-run/ui/stage-table.tsx`,
  `web/src/entities/expert-decision/ui/verdict-badge.tsx`,
  `web/src/shared/ui/run-state-badge.tsx`,
  `web/src/shared/ui/stage-status-badge.tsx`,
  `web/src/widgets/decision-history/ui/decision-history.tsx`,
  `web/src/widgets/export-panel/ui/export-panel.tsx`,
  `web/src/widgets/run-progress/ui/run-progress.tsx`,
  `web/src/widgets/stage-comparison/ui/stage-comparison.tsx`;
- the owned style slot: `web/src/app/globals.css`;
- tests: `web/tests/unit/run/closed-vocabulary-badges.test.ts`,
  `web/tests/unit/review/viewer-and-panels.test.ts`,
  `web/tests/unit/export/export-panel.test.ts`,
  `web/tests/unit/screens/run-progress.test.ts`,
  `web/tests/unit/screens/stage-comparison.test.ts`,
  `web/tests/unit/styles/screens.ts`, `web/tests/unit/styles/styling-layer.test.ts`;
- comments/docs: `infra/deploy/proxy/nginx.conf`, `infra/local/README.md`,
  `infra/local/bucket-init.sh`, and this report.

## Verification

- `npm --prefix web test -- --run` — **83 files / 1193 tests passed**, exit 0.
- `npm --prefix web run lint -- --quiet` — exit 0.
- `npm --prefix web run typecheck` — exit 0.
- `.venv/bin/python -m pytest tests/contract/api_v1 -q` — **165 passed**, exit 0.
- `git diff --check` — exit 0.

The first sandboxed full frontend attempt was not accepted as evidence: nested local
`eslint`/`tsc` subprocesses were refused with `EPERM`. The same command was re-run with
local subprocess execution permitted and produced the green result above.

## Contracts and storage

No API/domain/analysis contract, generated API client, migration, dependency or lock file
changed. There is no stored-data or feature-flag change; rollback is the revert of this
bounded UI/comment commit.

## Risks and known limitations

- The unit/style evidence proves the declarations and rendered fault states. The live
  780 x 900 hostile-string drive remains owned by `W48-JUDGE-Z` as the task states.
- Provider mode deliberately retains the pre-existing explicit `unknown` presentation:
  `providerModeLabel` proves that the subsequent lookup cannot miss. This task does not
  redefine absence/unrecognised provider provenance as a new contract state.

## Integrator handoff

Merge after `W48-GUARDS-2`, in the order fixed by `W48-CLOSE.md`. No semantic merge
resolution is expected outside the paths listed above. Re-run the required commands on the
merged closure line; `W48-JUDGE-Z` independently injects an unknown value at each T-1 site
and performs the live 780 x 900 drive.

Open questions: none.

## Forbidden-hotspot proof

`git diff --name-only 03c04a1d87fda862d085a6a49d0a46f2692f7ffd..HEAD` at handoff is restricted to the task's
allowed paths. In particular it names no `contracts/**`, `db/migrations/**`, backend,
root lock/dependency file, composition root, or global-style selector outside the two
history containment rules.
