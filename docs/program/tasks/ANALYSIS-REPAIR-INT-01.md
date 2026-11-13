# ANALYSIS-REPAIR-INT-01 — preserve meaningful issues for human review

## Outcome
Fresh V2 consents keep meaningful issues reviewable without inventing source grounding. Valid paid work survives partial failures; text/drawing origins, normative uncertainty and real human decisions remain distinct. Existing stages, identities, ledger and memory services are reused.

## Depends on
- ANALYSIS-REPAIR-PLAN-01 — completed, approved revision 2.

## Frozen inputs
- Base: `31839344eac74840be88c218f97efaf16072d705`.
- Base API/domain/analysis 1.54.0; migration `0067_precedents_wave5`; product 0.26.0.
- Plan: `/root/projects/PDF-Analysis/.local/plans/analysis-flow-repair-2026-11-13.md`, SHA-256 `407b134ccfb698d92d6b02a3b59e7ba2778c7de10713c0dfc62c7ec58b97c66b`.
- Original donor: PDF-proverka `dd974b2bcc8523cb303cf04fb9fb3760bede3246`, read only.
- Owner authorized continuation and subsequently required only local, focused, basic checks; no general checks, gate or full run.
- Owner confirmed stopping the previous session. Its last shared-tree changes were captured by per-file hashes before continuing in `integration/analysis-flow-continuation-1113`. The original worktree is retained.

## Ownership and allowed paths
Root owns this integration's contract, migration and consumer compatibility. Allowed paths:
- `src/auditmanager/**`, `tests/**`, `contracts/**`, `db/migrations/**`, `web/**`.
- `scripts/recovery/**` and the two export query allowlists in `infra/deploy/proxy/{nginx.conf,tls-server.conf}`.
- This task, `docs/program/CURRENT_STATE.md`, `docs/program/{P02_SEAMS,CONTRACT_PIN_REGISTRY}.md`, and only the current migration-head pin in `docs/manual-tests/PC-01_prototype.md`.
- `VERSION`, `release-notes/0.27.0.json`, local evidence in `.local/evidence/continuation/`.

## Forbidden hotspots and non-goals
No root dependency/lock file, composition root, global style, verification-policy document, infrastructure topology, original repository or historical run evidence is changed. No new stage, independent decision ledger, training export, synchronous encoder, paid analysis, historical run promotion or human-verdict revoke.

## Integration contract
- Output: API/domain/analysis **1.55.0**, migration **0068_reviewable_findings**, product **0.27.0**; surface remains 300 paths / 329 operations / 820 schemas.
- `unverified` has a real Finding identity, an explicit limitation and no fabricated evidence. The ordinary expert command and atomic memory capture handle it.
- Fresh-policy publication is idempotent by run/member; exact primary origins retain their existing Finding. Conflicting existing identities are retained with a conflict receipt.
- Semantic T/G relationships preserve raw members and disagreement. Valid records are saved before subsequent calls and one addressed repair cannot replace accepted rows.
- Missing normative query is not by itself not-required. A failed broader search is pending. The existing corpus context reader supplies exact per-input fragment context; missing, nonliteral or truncated required context affects that input only.
- Moderate correction is additive. CSV/XLSX follow the selected real human verdict; reject then accept changes the active set without deleting history.
- V2 critic context reuses exact compatible finding_v1 vectors. Current scope/status/content/votes/comments are checked under existing transaction locks before effect registration. Paid responses replay first; unknown effects require reconciliation.
- New source/parser/context helpers are included in the flow manifest. Old quality-bundle files and old consent paths remain unchanged.

## Donor → adapter → focused evidence
- Original `findings_merge_task` rules → `analysis/extended/flow_repair.py` and existing comprehensive/finding_merge → semantic match/extension/disputed and pair-repair fixtures in `test_flow_repair.py`.
- Original deterministic critic/corrector → existing structural core plus additive current corrections → suggested-fix/context and preserved-raw fixtures.
- Original norm execution/status separation → `_flow_norm_verification`, `flow_norm_context`, existing public corpus reader → negative/timeout, per-input fragment and incomplete-context fixtures.
- Existing durable provider journal → `_call` / `jobs.extended_review` → actual paid replay/unknown/not-processed tests in `test_candidate_context.py`.
- New integration (no original donor): existing human memory/vector services → `precedents/candidate_context.py` → positive new-running-candidate, withdraw/forget, scope and actual-dispatch fixtures.

## Deliverables and checks
Code, additive schema/migration, generated client, compatible readers/exports, release note and focused regressions are in this candidate. Exact commands, logs, changed-file list and observed results are in `.local/evidence/continuation/verification.md`; this record does not transfer an earlier result to a changed file.

Focused boundaries checked during continuation: fresh flow/norms; uncertain transport; publication/ledger/capture; warm context/provider effects; active CSV/XLSX after human reject/accept; affected UI; package TypeScript, generated client and touched ESLint. The isolated test database is `analysis_repair` on loopback 55468. Upgrade/downgrade checks use that database only and refuse downgrade with new retained data.

## Failure / rollback / feature flag
Disable `AUDITMANAGER_V2_FLOW_REPAIR` for future estimates to roll back the writer. Keep compatible readers, unverified findings, decisions and memory. Existing one_list and critic_context journalled switches are honored; no switch is changed automatically. Old consents retain their original builders and limits; unknown provider effects are not retried. Downgrade refuses while new-policy findings or group/uncertain memory exist.

## Limits and publication boundary
- This continuation produces a local development commit. It grants no right to push or merge `origin/main`; the user's supplied policy requires a separate direct instruction for the exact verified candidate. No deployment or publication is performed here.
- No general checks, full suite, make gate, full live analysis, paid provider/encoder call or browser deployment journey is run. Only the current focused checks are completed under the owner's latest instruction.
- Production activation and exact deployed-tree verification remain operator acceptance, not established by code or isolated fixtures. No training-use/data-class switch is changed.
- Warm retrieval is explicitly limited to existing compatible vectors; cold inputs are unavailable.
- Machine reject/uncertainty never supplies a human vote or hides a candidate. Without an independently verified counterproof receipt, the issue remains active conservatively.
- The independent preliminary review's J1–J4 and hybrid capture gap have focused regressions. Final independent judgment of the complete candidate is not claimed.

## Handoff
Use `integration/analysis-flow-continuation-1113` and the local commit reported by this continuation. Do not resume writing in the prior shared worktree or silently publish/promote historical runs. Review the candidate and the recorded activation limits before any separately authorized rollout.
