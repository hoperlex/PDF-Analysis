# Task AR-NORM-MAP-01 — approve six scoped AR normative maps

task_id: AR-NORM-MAP-01
status: frozen; source/reviewer inputs pending; no map is approved by this task file

## Outcome

An owner-reviewed pack of six canonical maps for F1/F2/A1/A2/S1/S2 covers the approved C01–C22 branches exactly once for one explicit N/R/P scenario variant. Each included topic binds a quoted original topic, applicable source edition, complete canonical `ndoc_`/`npar_` target and project predicate. Every excluded original threshold, missing source and unresolved branch is recorded. Six independently verified prompt parts fit the unchanged 22,000-character cap. A reviewer can inspect every source text and exact map SHA before a set is built.

## Depends on

- `AR-SET-PROMOTION-01` — completed set promotion mechanism.
- `AR-NORM-MAP-APPROVAL-PREP-01` — completed C01–C22 decision sheet.
- `AR-SIX-RUN-SCOPE-BRIDGE-01` — completed six-scope draft request boundary.

## Frozen inputs

- base commit: `4d43e035f0c87ae4827494413e571cccc7c68715`
- contract `1.0.0`, migration head `0031_executor_pull_channel`;
- original AR checklist SHA-256 `eccb7879023a126427fd61a0ed36237eb42bbebd4bec63c4009004247d7f3179`; role SHA-256 `fda944f74c4a0bd7cd77339f2c2f8519f55d59e899be03da212f93d2ad432203`;
- candidate repaired snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74`, content key `2026-07-23..2026-08-20+17d+121r.0a1bafe103ff`; every map must re-qualify this identity before sealing;
- six-group composition SHA-256 `79396188486c430729213279fb7c1c8fca7c13ede3f3f13388d06d9f93bbb781`; group membership in `scope_partition.py`;
- W57 §A3 canonical map/vector/target rules and 22,000-character selected prompt-part ceiling;
- owner decision on 2026-10-23: six separate scope-bound Runs, preserving common project context and individual Run provenance.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `src/auditmanager/analysis/profiles/ar_v3/norm_map/map_pack.json`
- enumerator_owner: `AR-NORM-MAP-01`
- totality_query: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract/norm_map`

## Captured premise evidence

- premise: the six-scope bridge exists, but no C item has owner approval or production map/set authority.

### P-01 — frozen candidate

- captured_at: 2026-10-23
- command: `git rev-parse HEAD && rg -n '^\*\*Task:\*\*|^Candidate paragraph IDs' docs/program/AR-NORM-MAP-APPROVAL-PREP-01.md`
- captured_output:
  ```text
  4d43e035f0c87ae4827494413e571cccc7c68715
  3:**Task:** [AR-NORM-MAP-APPROVAL-PREP-01](tasks/AR-NORM-MAP-APPROVAL-PREP-01.md). **Frozen development base:** `b5e089b5c6a07a7bb53f6b60007c9f5041ebff8d`, 2026-10-23. **Decision state:** no C item is owner-approved; no reviewed `map_sha256`, qualified production `nrs_`, or served v3 profile exists in this tree. The original checklist supplies *topics*, never thresholds. Its 46 bullet dispositions and source hashes are in `AR-NORM-MAP-DISCOVERY-01` at `281a54181e8ae499bc8152e74d5ff646f01f44dc` on the separate `integration/ar-evidence-01` line. This packet does not import that branch or rewrite its historical reports.
  7:Candidate paragraph IDs belong only to repaired snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74` (`2026-07-23..2026-08-20+17d+121r.0a1bafe103ff`). `AR-NORM-MAP-REVIEW-PREP-01` at `bc8e296272e6b90935d187dc2f63f7ecfae2f016` verified 22 anchor paragraphs against effective recognised text and local PDF pages, and matched six PDF hashes to the offline bundle. Its promotion DB still had **zero** Blob, admission and binding rows. That proves a candidate text location, not served PDF custody or legal applicability. The later edition audit at `9956efecc7a4a7e29c0b45e1cfd70932f58ce965` found **no D1–D6 candidate with complete page-level final-edition confirmation**.
  ```
- interpretation: canonical anchors are candidate evidence, not an approval; a new map SHA must be reviewed after source/branch resolution.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v3/norm_map/**`
- `tools/norms/query_vectors/**`
- `tests/contract/norm_map/**`
- `docs/program/tasks/AR-NORM-MAP-01.md`
- `docs/program/AR-NORM-MAP-01.md`

## Forbidden hotspots

`contracts/**`, migration head, root dependencies/locks, composition root, global styles, served profile, router/UI, provider transport, existing source reports, corpus mutation, `origin/main`, tags and deployment host.

## Non-goals

No invented legal validity or original-checklist threshold, provider call, Run creation/aggregation, served profile, CITE StageResult, finding write or beta/release assertion. No six-PDF backfill in place of full corpus custody.

## Deliverables

Six canonical scope maps, one reviewed pack manifest with distinct map/vector digests, full item-by-item source/branch/exclusion report and owner decision for the exact bytes. If required source pages remain unavailable, deliver only a refusal report and no publishable map/pack.

## Required tests

- Verify each included target against an official/authorized source page, local PDF digest, exact reliable `ndoc_`/`npar_` range and the project's date/use/work boundary; record reviewer decision and source-page SHA.
- Reproduce query vectors from the frozen BGE-M3 image and compare float32/profile/model-revision SHA.
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract/norm_map tests/integration/analysis/test_ar_v3_scope_partition.py tests/contract/program` — pass; include real-bundle prompt renders with labels/windows and no truncation.
- `git diff --check` and exact allowed-path proof — pass. No full `make gate` during the R-135 intermediate series.

## Integration contract

Exactly one pack manifest represents one reviewed scenario variant and lists six distinct scope/map/vector identities; concatenated item IDs equal the approved coverage once. N/R/P and room-use branch choices must come from explicit project facts. The pack is a trusted input only after exact-byte owner approval. `AR-PROMPT-RUNTIME-01` selects one reviewed map/verified set per Run and must preserve the six-Run project relation; `AR-CITE-PUBLISH-01` retains citation/Attempt/model provenance. A pending, rejected or missing C branch is never silently omitted from a claimed all-22 review. A new snapshot or changed source/query/target/branch creates new digests and requires re-review.

## Failure/idempotency/security cases

C15 source/correction, C21/C22 row/footnote segmentation, missing official amendment text, absent СП 2/4, unqualified PDF binding, unreliable paragraph, branch ambiguity, duplicate C ID, map/vector digest drift or over-cap prompt blocks the affected pack. Exact replay retains its digest only for byte-identical approved inputs. No secret or raw external source is embedded without rights review.

## Rollback / feature flag

Before activation, revert the unserved map assets/report. After a set is pinned to a Run, retain immutable historical rows and deactivate via the later owned profile switch; never overwrite that Run's map identity.
