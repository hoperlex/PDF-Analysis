# BLOCK7-INT-1030 — full saved specification exports

task_id: BLOCK7-INT-1030

## Outcome

Existing technical XLSX/HTML ZIP downloads include all saved whole-specification positions (including unchanged ones), extraction/batch coverage and source custody, beyond the clipped public changes projection. No model call or recomparison.

## Depends on

- BLOCK4-INT-1030
- BLOCK6-INT-1030

## Frozen inputs

- Base dev `f4d722e5420699a0846b559d1410b7b7b683cdc7`.
- API1.14.0 (233 paths /259 operations /620 schemas), migration0043.
- Existing binary streamComparisonTechnicalReport, report adapter and stored comparison_spec_extraction/comparison_spec_comparison data.
- Owner continuous source-only blocks/dev publication; deployment by owner. All delegated sessions stopped on usage limits, root sole writer.

## Allowed paths

- `src/auditmanager/comparison/report/technical_export.py`
- `src/auditmanager/comparison/report/specification_export.py`
- `web/src/widgets/version-series/ui/projects-and-stages.tsx`
- `docs/program/**`

## Forbidden hotspots

Contracts/API/generated, routers, composition root, migrations, root dependencies/locks, global styles, tests/fixtures, paid prompt/policy/runtime/extraction code, main/deployment, other paths. No tests/build/compile/import/lint/typecheck/runtime/browser/DB/model checks.

## Non-goals

No new API format/route, expert decision/carryover, new extraction, regenerated source packet, PDF parsing, paid reply export, model call, recomparison or raw-evidence mutation. No missing/partial extraction called an empty specification.

## Deliverables

Read-only snapshot collector with project/link authority, separate extraction-origin and bound-version IDs (project source-text cache legitimately spans versions), full aggregate and referenced checked batches, counts/size/resource guards and explicit incomplete bindings. HTML ZIP contains complete saved specification JSON/CSV and hash/byte manifest. Technical XLSX contains structured positions/coverage and lossless raw JSON chunks, with marked long-cell display excerpts and full originals preserved. Existing UI download copy explains full saved data. API/migration and paid plans unchanged.

## Required tests

- command: none, explicitly deferred by owner.
- expected: UNVERIFIED source candidate.

## Integration contract

Root owns collection/render/UI slots and publishes only origin/dev, preserving incoming owner commits. Exact clean normal FF/readback, no hooks/checks/deployment. Resource overflow refuses complete export rather than dropping rows. No model/DB execution in this coding session; app feature queries are source code only.

## Rollback / feature flag

Read-only export enhancement; revert these exact files without mutating stored comparisons/replies or accepted consent.

## Handoff

Changed paths, no-check status, unchanged contracts, archive/resource/cached-origin limits, publication receipt; all acceptance D-290.

## Incoming owner authority adopted during integration

Preserve `af581631`, `adaf93d4`, `afc0f482` from origin/dev. Their SECTION-STATS-UNCAPPED-1030 explicitly owns contract numeric-limit and migration slots. Integration now adopts migration0044_section_stats_uncapped / API1.14.0 without editing or executing that migration. Incoming tests/generated/proxy/composition changes belong to that owner task, not this export slot. Combined candidate remains unverified under the current no-checks instruction; owner deploys.
