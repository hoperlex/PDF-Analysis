# Task AR-NORM-MAP-APPROVAL-PREP-01 — prepare the AR norm-map decision

task_id: AR-NORM-MAP-APPROVAL-PREP-01

## Outcome

One owner-readable C01–C22 decision sheet distinguishes corpus anchors, source-edition evidence, object/applicability predicates and the stops that prevent approval or v3 activation. It gives the next map and runtime owners a precise refusal boundary without asserting a reviewed map.

## Depends on

- `AR-SET-PROMOTION-01` — completed development seam.
- `AR-V3-ORIGINAL-TOPICS-01` — completed source-bound topic guide.
- `AR-CORPUS-CITATION-BRIDGE-01` — completed unserved Run/set bridge.

## Frozen inputs

- base commit: `b5e089b5c6a07a7bb53f6b60007c9f5041ebff8d`;
- API contract `1.0.0`, migration head `0031_executor_pull_channel`;
- repaired corpus candidate `ns_01M59N8QNBVN91ACA2HCE6VE74`, content key `2026-07-23..2026-08-20+17d+121r.0a1bafe103ff`;
- original role/checklist SHA-256 in `AR-V3-ORIGINAL-TOPICS-01`;
- frozen citation mechanics in `docs/program/dispatch/W57-PLAN.md` §A3 and the completed bridge task;
- prior review material identified by immutable commits in the report, read as evidence only: no branch or report grants owner approval.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the development tree has no approved AR map or served v3 identity.

### P-01 — source and profile boundary

- captured_at: 2026-10-23
- command: `git log -1 --format=%H && rg -n 'AR-NORM-MAP-01|norm_map/|still maps AR|unserved' docs/program/AR-ORIGINAL-CITATIONS-PLAN-01.md docs/program/dispatch/W57-PLAN.md docs/program/AR-CORPUS-CITATION-BRIDGE-01.md`
- captured_output:
  ```text
  b5e089b5c6a07a7bb53f6b60007c9f5041ebff8d
  docs/program/AR-CORPUS-CITATION-BRIDGE-01.md:17:This is an **unserved code seam**. It makes no provider call and writes no
  docs/program/AR-CORPUS-CITATION-BRIDGE-01.md:40:The new bridge is additive and unserved; a forward revert removes it and the
  docs/program/AR-ORIGINAL-CITATIONS-PLAN-01.md:8:2. The served section registry still maps AR to the narrow v1 text-consistency profile (`analysis/text/profile_registry.py`). The reviewed original topics exist in six `analysis/profiles/ar_v2/*.md` files, but v2 is recorded only and v3's prompt, response and grounding modules are draft/unserved. Changing the v1 prompt in place would change its content hash and invalidate historical recordings; the live successor needs a new profile and bundle identity.
  docs/program/AR-ORIGINAL-CITATIONS-PLAN-01.md:16:| `AR-NORM-MAP-01` | A reviewed map from the original AR checklist's *topics* to canonical DB paragraph identities and editions; one owner for the map and its review record. Reuse `norms/retrieval/{targets,source_reader,qualification_reader,qualification_decision}.py`. | Every included item has a quoted source topic, current corpus document/paragraph identity and applicability note; every original threshold or absent corpus document is excluded explicitly. No model call. |
  docs/program/AR-ORIGINAL-CITATIONS-PLAN-01.md:22:Each code task must be frozen from the fresh integrated tree after the currently in-flight PDF, EXEC and edge branches. The contract/migration, composition-root and profile identity slots are assigned to exactly one task at a time; the table does not grant them. `AR-NORM-MAP-01` and `AR-SET-PROMOTION-01` precede `AR-PROMPT-RUNTIME-01`; publication follows runtime and grounding. The current `R-135` development cadence permits bounded lane tests, while any `origin/main` update still follows `AGENTS.md` §6 and `MAIN_AUTODEPLOY_POLICY.md` for an exact gated SHA.
  docs/program/dispatch/W57-PLAN.md:95:- **Items** (`analysis/profiles/ar_v3/norm_map/items.json`, ≈ 22–25): id, one of the five categories, the
  docs/program/dispatch/W57-PLAN.md:119:- **Map identity** (`norm_map/map.json`): items and vectors digests, resolved targets, the excluded list,
  docs/program/dispatch/W57-PLAN.md:389:  `src/auditmanager/analysis/profiles/ar_v3/norm_map/**` (new), `tools/norms/query_vectors/**` (new),
  docs/program/dispatch/W57-PLAN.md:390:  `tests/contract/norm_map/**` (new: shape, provenance digests, no number in an item text, vector
  docs/program/dispatch/W57-PLAN.md:402:  W56a-only items and **minus** `tests/contract/norm_map/**`, plus the files named here and every path
  docs/program/dispatch/W57-PLAN.md:430:   not `norm_map/`), `src/auditmanager/analysis/text/{profile,prompt,response,stage,provenance,artifact,recorded,__init__}.py`,
  ```
- interpretation: this task may prepare decisions but cannot claim a registered map/profile or a verified production set.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/AR-NORM-MAP-APPROVAL-PREP-01.md`
- `docs/program/AR-NORM-MAP-APPROVAL-PREP-01.md`

## Forbidden hotspots

`contracts/**`, migration head, root dependencies/locks, composition root, global styles, corpus/Blob/DB state, served profile, provider, router, UI, `origin/main`, tags and deployment host.

## Non-goals

No legal-status ruling, owner signature, map JSON/vector generation, 22-item qualification, production set, model call, saved citation, profile activation or run aggregation.

## Deliverables

This task and a self-contained review decision sheet with source links, candidate status, exact stop conditions and a downstream integration contract.

## Required tests

- `/root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/program` — pass;
- `git diff --check` — pass;
- exact changed-path comparison with the two allowed paths — pass.

## Integration contract

The next `AR-NORM-MAP-01` owner may use the cited C01–C22 evidence as candidate input only. It must record explicit item/branch decisions, verify complete source editions and project predicates, qualify snapshot/PDF custody and prompt budget, then seal reviewed canonical map bytes. `AR-PROMPT-RUNTIME-01` may consume only that sealed identity and a verified Run-pinned set. A missing or ambiguous map/set refuses before provider dispatch.

## Failure/idempotency/security cases

An absent official amendment page, unresolved C15 correction, merged acoustic row/footnote, missing object fact or >22,000 rendered prompt prevents that branch from approval. A repeated review of identical bytes may retain its digest; any change requires a new review record. The report contains no secrets.

## Rollback / feature flag

Revert the two documents. There is no runtime flag or data migration.
