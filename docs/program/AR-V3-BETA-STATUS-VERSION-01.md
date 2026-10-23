# AR v3 beta source-status preview — 0.8.0 development candidate

**Task:** [AR-V3-BETA-STATUS-VERSION-01](tasks/AR-V3-BETA-STATUS-VERSION-01.md). **Base:** `4b2ff2d8aa65ef959bfdebc432e40484047709e6`, 2026-10-23. **Target:** `origin/dev` only; no tag or `origin/main` update.

## Result and scope

`VERSION` is `0.8.0`. The authenticated «Настройки анализа» screen shows a read-only AR v3 Ф1.3 preview: all C01–C22 topics in the fixed F1/F2/A1/A2/S1/S2 order, with 14 preliminary-source and 8 context-only dispositions. The mirrored JSON bytes equal the server beta policy (`ab3fa01a51d6ffb7c3fc82544c2d1e93e3b66eddf7e2c31fbfae478b4c63f708` file SHA-256); the policy's own canonical digest remains `9d3b7e53b512fbde1ea478a77a63c3c48042e85ddc50d57c96241c79bcb91d58`. The screen has no action that can create a Run or write a finding and explicitly states that v3 Runs and numerical conclusions are unavailable.

The authored [0.8.0 release note](../../release-notes/0.8.0.json) states precisely that limited user-visible change. [RELEASES.md](RELEASES.md) records this as a development candidate, and the [remaining code queue](dispatch/AR-V3-BETA-CODE-QUEUE.md) names the map, set, six-Run, executor, citation and acceptance slices. The planned W57a `v0.8.0` milestone of verified citations is **not** complete. The owner may later publish to `main`, but this task provides no `GATE OK`, stand import, six verified sets, v3 model call or deployment evidence.

## Changed files

- `VERSION`, `release-notes/0.8.0.json`, `docs/program/CURRENT_STATE.md`, `docs/program/RELEASES.md` and the small status note in `docs/program/dispatch/ROADMAP-TO-BETA.md` — version and truthful development status.
- `web/src/_pages/analysis-settings/ui/analysis-settings-page.tsx` and `web/src/widgets/ar-v3-beta-status/**` — read-only topic/scope preview. The source policy mirror is byte-identical; grouped IDs and Russian topic titles have a totality check.
- `web/tests/unit/analysis-settings/analysis-settings.test.ts`, `tests/contract/norm_map/test_beta_status_mirror.py`, `tests/contract/release_notes/test_release_notes_form.py`, `tests/integration/releases/test_release_loader.py` — rendered status, source equality and version-note checks.
- Task, this report and `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md` — ownership and next steps.

## Checks

- `web` TypeScript `tsc --noEmit --project web/tsconfig.json`: passed; focused ESLint: passed; focused Vitest: **17 passed**.
- Product version/order, release-note form and beta mirror: **59 passed**. Release-loader's offline note/schema test: **1 passed**.
- `tests/contract/program/test_process_acceleration.py`: **12 passed** after reflowing `CURRENT_STATE.md` from the inherited 139 lines to 107 lines without deleting state. `tests/contract/program/test_wave_governance.py`: **15 passed, 1 failed** on the inherited `EXEC-ENV-OPENROUTER-01`, `EXEC-SSH-CROPS-01` and `EXEC-SSH-TUNNEL-CROPS-01` task files, which lack mandatory fields. This task's own governance findings are empty. These three historical files are outside this task's allowed paths.
- `git diff --check` and the exact changed-path audit: passed. Full `make gate` was not run under the R-135 development cadence.

## Contracts, risk and integrator handoff

No API/domain contract, migration, composition root, root dependency/lock, global styles, provider transport, Run executor, source bundle, stand data or `origin/main` ref changed. This candidate changes the version and one read-only web view. The existing AR section still routes to its immutable v1 profile; the preview confers no legal-edition or expert-map authority. Do not describe it as served normative citation analysis. The isolated local corpus qualifies, but the stand lacks that import and designation, and there is no approved six-map/six-set pack. No numerical conclusion may be emitted from the preview.

For the next slice, freeze [AR-V3-BETA-MAP-PACK-01](dispatch/AR-V3-BETA-CODE-QUEUE.md) from the exact current `dev` SHA, then follow the queue's set/runtime/CITE ownership boundaries. A future production candidate needs the complete gate, stand corpus and source review on its own SHA. Revert this candidate's version/note/UI changes to roll back the preview before main publication; it has no data migration or feature flag.
