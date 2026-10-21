# W57a/W57b seal freeze proposal from development SHA `08055ca0`

**Status: proposal only.** This document neither freezes a contract nor grants
write access to a migration, composition root or API surface. It is based on
published `origin/dev=08055ca094a9c3e4676a5907a0b3020f0bee4fb8`; every
pin and migration slot must be remeasured when the integrator dispatches a
seal task. `CODE-FIRST-TO-BETA.md` changes the check cadence to focused
development checks, not the W57 functional scope or sole-owner rules.

## Why the next XLSX code bridge must wait

The current head is `0022_findings_v2`. It has no
`finding_observation_norm_citation` relation. The pure W57a
`GroundedNormCitation` has a norm paragraph and raw span, but no persisted
finding/run association, catalogue display designation/title or authoritative
proof that a finding has zero citations. The W57b XLSX package deliberately
accepts caller-supplied `citations_by_finding`, and its authorization value is
also caller supplied. A new persisted-citation reader or an exposed route built
on those inputs would claim provenance the present database cannot prove.

The completed W57b writer, projection, finding read, package, verified page
labels and run/source preflight remain useful unactivated components. W57a's
pure citation guard and retrieval preparations are likewise unactivated.
W54 has a verified base restore but no repaired qualified snapshot, embedding
build or publication bundle. W56a code close, W57a/b formal RULE/FREEZE/SEAL,
W57a map review and verified set admission have not been recorded as complete
at this SHA.

## Sole-owner sequence for the later integration freeze

| Order | Owner and exact deliverable | Dispatch boundary |
| --- | --- | --- |
| 0 | Integrator writes the W57a code-first RULE/FREEZE tasks from the then-current `origin/dev`, reconciling the old `W57-PLAN.md` order with R-135. | Name only completed task IDs in `depends_on`; record W56a code close and W54/stand evidence as complete or explicitly pending. Run `pin_sweep.py reseal-surface migration table error-code route` and assign one contract/migration/composition owner. |
| 1 | `W57A-SEAL-01`, sole owner of planned `0023_norm_citations`, API citation/report additions and stage/identifier/category/reason enumerators. | One new migration contains the planned verified retrieval-set/custody/run pin and append-only observation citation relation together. It does not pretend a verified set or runtime CITE exists. |
| 2 | W57a MAP/RETRIEVAL/PROFILE code and then `W57A-CITE-01` publish only successfully grounded citation rows, expose the report and prove the stored quote is the canonical raw substring. | A failed citation withholds the whole observation; no LLM output or in-memory citation mapping is canonical. This is the first authoritative source a future XLSX reader may query. The W57a code close follows the required code lanes; stand acceptance stays separately pending. |
| 3 | Integrator writes W57b RULE/FREEZE from the new dev head; `W57B-SEAL-01` solely owns planned `0024_norm_references`, `exportRunXlsx`, its `_EXPERT` role and the new category/rule provenance. | `ProviderMode` remains byte-identical. The sealed route is a typed refusing stub until XLSX runtime has a verified citation reader and source policy. |
| 4 | `W57B-NORMREFS-01` supplies the deterministic reference stage, then `W57B-XLSX-01` reads the stored citation relation for the exact run/finding/observation/snapshot, resolves labels, obtains the guarded principal and state, and calls the package in one consistent read. | It proves a complete citation partition, including verified zero citations, and runs a real workbook application probe. The CSV bytes and download-name source remain stable. |

The old plan's W57b freeze depends on `W57A-INT-CLOSE`; its main publication
also depends on a verified stand set. The code-first amendment may defer stand
and full-gate acceptance, but must state the changed code-close dependency in
new task files instead of treating a missing ID as completed. No paid model or
stand operation is part of either seal.

## Proposed core path grants

These are the **minimum named hotspots** for the next two owner tasks, not an
allowlist for this proposal. Each actual task must enumerate its complete
`allowed_paths` after the fresh pin sweep, including direct category/reason
consumers and prose claims. Do not let two agents edit the same path in
parallel.

**W57a owner:** `contracts/api/v1/openapi.json`,
`contracts/domain/v1/identifiers.json`,
`contracts/analysis/v1/stage-registry.json`,
`db/migrations/versions/20261016_0023_norm_citations.py` (candidate name),
`src/auditmanager/shared/identity/ids.py`,
`src/auditmanager/norms/custody/roles.py`,
`src/auditmanager/api/security.py`,
`src/auditmanager/api/schemas/{models,findings,runs}.py`,
`src/auditmanager/api/routers/{runs,ports}.py`,
`src/auditmanager/bootstrap/{adapters,composition}.py`, plus the cited
category/reason lists, direct contract/migration tests and pinned docs in
`W57-PLAN.md` §A3.6. `P02_LOCK.json`, old migrations, root dependency files,
global styles and active provider bodies are outside this owner.

**W57b owner:** `contracts/api/v1/openapi.json`,
`contracts/analysis/v1/{stage-registry,legacy-stage-map}.json`,
`db/migrations/versions/20261016_0024_norm_references.py` (candidate name),
`src/auditmanager/api/security.py`,
`src/auditmanager/api/routers/{export,ports,handlers}.py`,
`src/auditmanager/api/schemas/{models,findings}.py`,
`src/auditmanager/bootstrap/{adapters,composition}.py`, plus the direct
category/observation-provenance lists and tests in §B3.6. The old
`W57B-SEAL-01` inherited grant does **not** explicitly name
`src/auditmanager/api/routers/export.py`, although a served operation requires
it. The actual W57b freeze must add that exact path and the refusing-port
implementation; `W57B-XLSX-01` can replace the stub serially later.

Each OpenAPI reseal has four synchronized artifacts:
`contracts/api/v1/openapi.json`, `web/openapi/openapi.json`,
`web/src/shared/api/generated/**` and `web/FRONTEND_LOCK.json`. The exact
generated paths and any live surface-count claims come from the fresh sweep.
`docs/program/CURRENT_STATE.md` belongs to the integration task, not a seal
lane. No new error code is planned by W57 §A3.6 or §B3.6.

## Required focused evidence for the actual owner tasks

- **W57a migration:** clean 0022→0023 and populated 0022→0023 upgrade in an
  isolated PostgreSQL DB; citation FK and raw quote-offset/length CHECKs;
  append-only protection; rejected cross-observation or cross-snapshot binding;
  retained-data downgrade refusal; exactly one Alembic head. The previous
  migration remains byte-identical.
- **W57a contract:** the served OpenAPI matches its mirror/client/lock;
  citation fields are absent, never null, for v1/v2; the expanded category and
  ungrounded-reason sets are exhaustive; the `nrs_` identity and custody-role
  checks agree; `getRunNormVerification` is role registered and has a typed
  refusal while unimplemented.
- **W57b migration/contract:** clean and populated 0023→0024 upgrade;
  `rule_id` format and `rule_id IS NULL OR model_call_id IS NULL`; category
  CHECKs; `ProviderMode` byte-identical; `exportRunXlsx` in served OpenAPI,
  role register and role-sweep sample. Expert access, non-expert/roleless,
  default-credential and incomplete-profile refusals are explicit. A sealed
  stub returns typed `503 dependency_unavailable` until its owner implements
  the route; it does not return an XLSX built from unverified citations.
- **W57b runtime:** no SQL/Blob work before role refusal; missing/failed or
  non-publishing runs use the established CSV state policy; verified page
  labels and citation rows bind to the same run/version/snapshot; canonical and
  member rows retain order; an explicit zero-citation result comes from the
  authoritative read; every generated XLSX sheet opens and has equal cells in
  `soffice`; CSV byte characterization and the single filename-source test
  stay green.

R-135 calls for targeted contract/integration, type/lint and forward-migration
checks during these development slices. The complete `make gate` is deferred
to the single final beta code candidate; a separate W55b main-release gate
does not establish W57 quality. No `origin/main` push or release tag follows
from this proposal.

## Proposal checks and limits

The task's direct governance result is `[]`; its two-file diff passes
whitespace and exact-path checks. There is no code test or migration run in
this docs-only task. The path grants above are recommendations and cannot
become executable `allowed_paths` without a fresh freeze, explicit ownership
and task files. Revert these two docs to withdraw the proposal.
