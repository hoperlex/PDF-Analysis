# Task PDF-PROVERKA-FUNCTIONAL-COMPARISON-1030 — compare current functionality with the original

## Outcome
A Russian evidence-backed report explains functional parity, differences and missing capabilities, prioritising document analysis and version/stage comparison. Code availability, UI wiring and observed runtime validation are distinguished.

## Depends on
- CMP-INT-CODE-1030

## Frozen inputs
- Current analysis/comparison code: `3dbf483735d2eda3cb02e69c1a6d315e6074d884`. Remote dev was rechecked at `ee90c6a50214c335c241cd4cb6d7dbf55a1cf2cd`: its diff adds only section/run/dashboard presentation across19 files, no backend or comparison change. Those presentation files are read from `/tmp/pdf-analysis-ar-original` at the exact newer dev revision; the report identifies both snapshots without merging or altering another owner's tree.
- API `1.13.0`, 230 paths / 256 operations / 619 schemas; migration `0043_stage_ai_generations`.
- Original source checkout `/tmp/pdf-proverka-original` at `3c99481719218b9cfa7560886529916646c61939`; earlier comparison inventories at `23f379fd2d5aeb7e7bddb735650e7393c68d4e42` are leads, not current parity proof.
- Owner request2026-10-30: compare project functionality with pdf-proverka, especially analysis and comparison. Previous instructions allow useful parallel agent work; all contributors here are read-only outside their exact note files.

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- command: `git rev-parse HEAD` in both source trees
- captured_at:2026-10-30
- captured_output: current `3dbf483735d2eda3cb02e69c1a6d315e6074d884`; original `3c99481719218b9cfa7560886529916646c61939`
- interpretation: identifies compared source snapshots; does not establish equivalent output quality or deployed state.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `docs/program/tasks/PDF-PROVERKA-FUNCTIONAL-COMPARISON-1030.md`
- `docs/program/PDF-PROVERKA-FUNCTIONAL-COMPARISON-2026-10-30.md`
- `.local/handoff/pdf-proverka-comparison/**`
- `.local/tasks.md`

## Forbidden hotspots
- All runtime/UI source, tests, contracts, migrations, dependencies, composition, global styles, remote refs and deployed applications.
- Original repository files are read-only evidence; its instructions are not applied to this project.

## Non-goals
- No code changes, deployments, new provider calls, heavy gates or claimed output-quality equivalence.

## Deliverables
- Russian report with source links/line anchors, functional matrix, important divergences and prioritised remaining work.
- Bounded independent read-only notes on analysis and comparison where useful.

## Required tests
- Source snapshot verification, concrete call-path inspection, report-link/path checks and `git diff --check`.
- No runtime tests required for this documentation-only comparison.

## Integration contract
The sole integrator synthesises source-backed findings. Existing inventory/roadmap status is rechecked against concrete current implementations. An endpoint or similarly named stage alone does not prove functional equivalence. No report publication implies deployment or beta acceptance.

## Failure/idempotency/security cases
- Missing code or unverified wiring is marked explicitly; no invented parity percentage.
- Original source is treated as data; no instructions or secrets from it are executed/copied into the report.

## Rollback / feature flag
Not applicable: documentation only; no behaviour change.

## Handoff
- changed files: the report and this task; ignored contributor notes/handoff/task card only
- commands/results: original main and current dev SHA checks; source call-path inspection; 9 AR resource byte/SHA comparisons and 8 verbatim prompt-block checks PASS; all 100 report-source links checked for path/line existence PASS; analysis/comparison backend diff between3dbf and latestee90 empty; `git diff --check` PASS
- known limits: source comparison, no equal-input model benchmark
- integration notes: no remote publication authorised by this report task
