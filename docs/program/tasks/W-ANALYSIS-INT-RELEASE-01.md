# W-ANALYSIS-INT-RELEASE-01 — release the repaired analysis flow

## Outcome
Publish product 0.27.0 through the existing main deployment workflow, retain the exact revision's result and verification evidence, then create its product release tag. Do not call a pushed ref a completed release.

## Depends on
- ANALYSIS-REPAIR-INT-01 — implementation completed at `bed5a549f6df8221f3551bd492c103017e827f45` with focused checks.
- ANALYSIS-REPAIR-CONFORMANCE-01 — narrow API publication correction completed with local conformance/value/client checks.

## Frozen inputs
- Base main/dev observed remotely: `31839344eac74840be88c218f97efaf16072d705`.
- Runtime candidate: `bed5a549f6df8221f3551bd492c103017e827f45`, product 0.27.0, API/domain/analysis 1.55.0, migration `0068_reviewable_findings`.
- Independent ACCEPT_NO_SIGNIFICANT_CODE_FINDINGS for immutable tree `29c7f07e1946001841484a34cd123d52ed52c708`. Runtime, tests, contracts, migration and web bytes match the implementation commit; only its task prose differs. Exact comparison and review are in `.local/evidence/release-0270/`.
- Owner instruction: «Продолжай. Доведи план полностью до релиза».
- Owner verification constraint persists: «Работай только с локальными и точечсными и базовыми проверками». No general checks, full run or gate. Do not change verification-policy documents.
- Owner separately declined extra SSH/production preflight: «Нет, это можно опустить только локальные проверки». Do not add manual host probes or automatic setting activation. Existing deployment safety guards remain in force.

## Ownership, refs and allowed paths
Root is the sole release integrator for this task. Publication targets are `origin/dev` and `origin/main`; a separate direct instruction naming the exact checked candidate is required before main publication under the supplied AGENTS.md §6. No parallel publisher, force push or post-check runtime fix.

Allowed: this task, the review/closure entries of `docs/program/tasks/ANALYSIS-REPAIR-INT-01.md`, `docs/program/CURRENT_STATE.md`, `docs/program/RELEASES.md`, local release evidence, Git development/release refs, workflow observation and the product tag `v0.27.0` after verified deployment. Any necessary runtime repair returns to the implementation slot with focused evidence before another candidate is published.

## Forbidden hotspots / non-goals
No product, contract, migration, dependency/lock, composition, global style, deployment workflow or verification-policy change in this release slot. No paid analysis, encoder, historical run promotion, training/data-class setting change or manual activation. No extra general checks or security scan.

## Required evidence
- Reuse the recorded focused flow, publication/ledger/capture, warm-context/provider-effect, norm, migration, affected UI, TypeScript/client and touched-lint results only while the relevant files are byte-identical. The independent reviewer accepted the same code.
- `git diff --check`; clean exact candidate; current main/dev/tag refs; exact fast-forward; no other deployment in flight.
- Existing `deploy-auto` workflow must conclude successfully for the published SHA and include successful `infra/deploy/verify-deployed.sh` and its `DEPLOY OK: <sha>` marker. Do not bypass a migration-copy or deployment refusal.
- Record skipped manual host/activation checks separately; they are not proved by local fixtures.

## Integration contract
Analysis behavior is unchanged from the accepted runtime; the subsequent publication correction only reconciles CSV response metadata and an equivalent nullable-string schema. Only new consents select the flow policy, and existing one-list/critic-context switches remain authoritative. The release note states the warm-vector and switch limits. The existing CI deployment builds/migrates/verifies the exact triggering revision; no additional server workflow is introduced.

## Rollback
Keep readers, uncertain/group memory and human decisions. Disable the writer for future estimates if necessary; refuse destructive downgrade with retained rows. A failed deploy remains an open release and needs a reviewed forward fix or revert; never force-push. No product tag before successful exact deployment.

## Handoff / status
Complete: the corrected exact candidate is deployed and tagged `v0.27.0`. Main approval, focused checks, workflow/job log and exact-tree evidence are recorded in `.local/evidence/release-0270/`. Closure records travel to dev only; production activation is omitted by the owner's explicit scope instruction.

## First publication and correction
The owner explicitly approved `590bafb074b36667f34c633b39c608c21b0eb57e`, which was fast-forwarded to main. Workflow `43427506750` applied migration 0068 and started healthy services but stopped at served/frozen API conformance (five differences). No release tag was created. The correction is isolated in `ANALYSIS-REPAIR-CONFORMANCE-01`: explicit CSV ErrorEnvelope 422 and an equivalent nullable-string schema representation, with regenerated client/seal. Keep the applied migration and retained data; no analysis request/budget or setting change. A corrected exact SHA needs direct owner approval before another main publication.

## Verified release — 2026-11-13

- The owner explicitly approved `275bde8643e1e89f5f9741be2e57b7367cde44ae` with an express full-gate exception: “Опубликовать этот SHA в main без полного gate”. The exact question/answer and scoped release plan are in `takeover-release-plan.json`.
- The takeover stopped the prior session's dedicated app-server after checking that it held only that task and its guardian and had no background children. Context and task ownership moved to session `01a1d507-74d1-7ef2-882e-e69ac5aa7b8b`; `session-takeover.json` records the exited PID.
- Fresh local served/frozen/admission/nullable checks: **10 passed**; generated-client verification: **OK**; frontend-lock: **8 passed**, both commands exit 0. `git diff --check` passed. Full gate, general checks, paid analysis and encoder calls were not run.
- A clean exact tree, main ancestry, fresh main/dev refs and absence of another deploy were checked before the fast-forward. Main and dev read back as the approved SHA. The initial automatic-review refusal was resolved after recording the later direct owner exception and these new checks; no policy or workflow was changed.
- [Workflow 43433384065](https://github.com/hoperlex/PDF-Analysis/actions/runs/43433384065), job `131912221401`, completed successfully. Its actual host output at 13:30:09 UTC confirms `the deployed stack IS this tree (275bde864)` and `DEPLOY OK: 275bde8643e1e89f5f9741be2e57b7367cde44ae`. The full job log and extracted verification are retained locally.
- Annotated tag `v0.27.0` was published and its remote peeled target equals the exact verified SHA; receipt: `tag-receipt.json`. The earlier failed workflow remains part of the history.

This closeout changes only this task, `CURRENT_STATE.md` and `RELEASES.md`; no new contract, runtime, migration, dependency/lock, composition, global style or verification-policy change. The contract/migration remain the accepted 1.55.0 / 0068 implementation. Closure publication is dev-only. One-list/critic-context settings, manual host probes, cold-vector coverage and historical-run promotion remain outside this release's measured scope; no activation or data-class/training switch was changed.
