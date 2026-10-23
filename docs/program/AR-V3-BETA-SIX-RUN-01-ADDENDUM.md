# Addendum to AR-V3-BETA-SIX-RUN-01 — group identity ownership

The published [six-Run task](tasks/AR-V3-BETA-SIX-RUN-01.md) was frozen before implementation. Its requested independent group identity requires a new entry in `contracts/domain/v1/identifiers.json` and a matching `ArV3RunGroupId` type. The original `allowed_paths` contain only `contracts/api/v1/**` and omit the domain catalog and shared type. The existing `run_` prefix belongs to `AuditRun`; assigning it to a separate group would change that identity's meaning.

No code was started under the original task. [AR-V3-BETA-SIX-RUN-02](tasks/AR-V3-BETA-SIX-RUN-02.md) replaces it from the current development SHA and takes the sole domain/API/analysis/events contract, migration and composition slots. It also consumes the completed v3 prompt seal. The original task remains unchanged as historical dispatch evidence; only the replacement authorizes these extra paths. `origin/main` remains outside both tasks.

Before implementation, the replacement task's allowlist was completed with `web/openapi/openapi.json`: the existing web drift guard requires that snapshot to remain byte-identical to the resealed API contract. No replacement-task code or handoff existed when this path was added.

The replacement also owns the narrow `norms.public` export needed to pass the existing typed `SetIdentity` into `select_verified_retrieval_set`. The Run side must consume that public boundary rather than import the norms retrieval internals or duplicate their custody SQL.

The full `1.2.0` reseal must also update `web/FRONTEND_LOCK.json`, the independent `tests/support/expected_facts.json` manifest and `CURRENT_STATE.md`; the previous API reseal changed all three. They were added to the replacement's allowlist before its code lane made any changes.

The Run group must load the sealed v3 profile through `analysis.public`, so that facade was added before the Run group imported it. This keeps the bounded-context public seam intact.

The existing contract seal test requires the proxy and web forwarder error envelopes to advertise the same new family version. The replacement task owns those three exact files for this reseal; no unrelated proxy or web behavior is in scope.

The P02 seam register has an exhaustive API operation table checked against the contract. The two additive group operations and their idempotency rule require updating that one program file; it is assigned to the integration task before editing.

The prose contract gate scans `docs/manual-tests/PC-01_prototype.md` for the current migration head. Updating its single head claim to 0032 belongs to this migration owner.

The same gate scans the current API surface claim in `ALPHA_ROADMAP.md`; the integration task owns the one current-count update to 90/102/290.

The API prose-count gate also scans four deployment/BFF/authorization files for literal surface totals. The replacement task owns only the 90/102/290 prose corrections in those files; their behavior is unchanged.

Generated-client `1.2.0` types require updating the web test fixtures' ErrorEnvelope literals and the keyed-operation inventory. The replacement task owns `web/tests/**` for those exact contract/typecheck repairs.
