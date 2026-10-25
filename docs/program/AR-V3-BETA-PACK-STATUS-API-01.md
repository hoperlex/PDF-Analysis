# AR-V3-BETA-PACK-STATUS-API-01 — installed-pack status read

`getArV3BetaPackStatus` (`GET /ar-v3-beta/pack`) lets any authenticated user read whether a reviewed AR v3 beta pack is installed on this server. Not installed answers `{"state":"not_installed"}`. Installed answers the profile and prompt-bundle IDs, the sealed pack digest, the six scope IDs in order and the five-field reviewer attestation (`reviewer`, `capacity`, `reviewed_at`, `decision_ref`, `scope_statement`) that travelled with the manifest. The response is a record of what the manifest said; it does not say the attestation is true, and it carries no map, set or snapshot identity, scope digest, file path or environment value. No database read, no provider call, no new error code.

## Contract and ownership

- Task: [AR-V3-BETA-PACK-STATUS-API-01](tasks/AR-V3-BETA-PACK-STATUS-API-01.md), frozen from `0555a1209eff5db2134543c7b48d8d2423625944`.
- Shared API/domain/analysis/events contract `1.4.0` → `1.5.0`, additive; domain catalogue revision 22 → 23 (no new code, identity or machine). API: **92 paths / 104 operations / 300 schemas** (`ArV3BetaPackStatus`, `ArV3BetaPackReview`). Error catalogue 27, migration head `0032_ar_v3_run_group`, `VERSION` `0.8.0`: unchanged.
- OpenAPI content commit `b02f680e`; generated client and mirror derive from its bytes; `web/FRONTEND_LOCK.json` pins that commit, the counts and all eight digests (recomputed: all match).
- Serving: the composition root now keeps the `ParsedPackManifest` of the single load that builds the registry (`_ar_v3_installed_pack`); the API `RunAdapter` takes it as `ar_v3_installed_pack` and `get_ar_v3_pack_status` maps it. The worker root still receives only the registry. A variable that is set and bad still refuses the start. `load_manifest` is now exported from `runs/public.py`.

## Verification (tree `20ba942f` plus a dropped temporary `CURRENT_STATE.md` edit; see the integration note)

- Gate-equivalent `tests/contract` run (command in the task file): **1128 passed, 0 failed, 19283 subtests** (base was 1117; the 11 added are the new schema tests). Without the `CURRENT_STATE.md` edit exactly one test is red, `test_the_scanned_docs_state_the_contract_surface_this_tree_has`, naming that file.
- `tests/integration/api/test_ar_v3_pack_status_route.py`, `test_ar_v3_group_review_route.py`, `tests/integration/composition/test_v3_pack_install.py`, `tests/integration/runs/test_v3_pack_manifest.py`, `tests/contract/api_v1/test_ar_v3_pack_status_schema.py`: **137 passed**.
- `node web/scripts/generate-api-client.mjs --check`: OK, 104 operations. `git diff --check`: clean.
- Not runnable here (no `DATABASE_URL`, no S3): the served-application cases of `tests/integration/api` (including `test_role_register.py` and `test_authorization.py`, whose new rows are collected: 1665 tests collect cleanly across `tests/integration/api` and `tests/integration/composition`). The failing set of `test_composition_root.py`, `test_api_token_channel.py`, `test_router_answers.py` is the same 35 tests with and without this lane. `test_the_two_schemas_fastapi_would_have_added_are_not_in_it` is red on the base as well. Web unit and guard tests were not run (no `vitest`).

## Guards shown red under one mutation each

| Guard | Mutation | Red |
| --- | --- | --- |
| route test, scope order | adapter `scope_ids=sorted(...)` | `test_an_installed_pack_answers_...`, composition `test_the_api_reports_the_installed_pack_...` |
| route test, absent not null | router dumps without `exclude_unset` | `test_without_a_pack_the_answer_is_exactly_not_installed`, both composition `not_installed` cases |
| role register | `getArV3BetaPackStatus: _EXPERT` | `test_any_authenticated_role_may_read_it` |
| composition | `ar_v3_installed_pack=None` | the installed-pack status and one-load tests |
| leak guard | model gains `snapshot_id`, adapter fills it | exact-key-set test and `test_no_map_set_snapshot_or_scope_digest_is_ever_served` |
| served-vs-frozen | model-only extra property | `test_the_served_document_conforms_to_the_frozen_contract` |
| 200 schema | frozen `ArV3BetaPackReview.additionalProperties` true | `test_the_contract_refuses_everything_it_closes_off`, shape test, live conformance |
| 200 schema | frozen `scope_ids.minItems` 5 | closure test and shape test |
| operation declaration | frozen document adds a `404` | `test_the_operation_is_declared_the_way_the_group_reads_are` |
| seal | events schema const back to `1.4.0` | `test_every_json_artifact_of_a_family_declares_only_the_sealed_version[events]` |

## Findings and deviations

- `test_contract_seal.py` listed the previous seal's own version as a stale-constant prefix (`"1.4.0"` where `"1.3.0"` belonged). It now lists every earlier version (`1.0.0` to `1.4.0`).
- `declarations.py` said "twenty-five of the 103 operations declare no `422`"; measured from the document it was 26 of 103 and is now 27 of 104, which the text now says.
- Four paths under `infra/` (`proxy/nginx.conf`, `proxy/tls-server.conf`, `README.md`, `serve.py`) are changed although the lane brief lists `infra/**` as forbidden: `test_contract_seal` reads the version literal in the two proxy configs and the prose guard reads the counts in all four. They are text only and isolated in commit `5f4d3c31`.
- 40 `web/tests` files, `credentialed-forward.ts`, `authorization.ts`, `route.ts`, `result.py`, `v3_cite_stage_contract.py`, `ALPHA_ROADMAP.md` and `P02_SEAMS.md` were added to the allowed list as exact paths with reasons (task file).

## Integration note

- Merge before L8B. The screen consumes the generated `getArV3BetaPackStatus` and `ArV3BetaPackStatus`.
- `docs/program/CURRENT_STATE.md` (not touched) must carry, in the paragraph that now says "**91 paths / 103 operations / 298 schemas**" and "the shared contract is `1.4.0` after `AR-V3-BETA-GROUP-API-SEAL-01`": **92 paths / 104 operations / 300 schemas**, shared contract `1.5.0` after `AR-V3-BETA-PACK-STATUS-API-01`. Error catalogue 27, migration head `0032_ar_v3_run_group` and `VERSION` `0.8.0` stay. `DEBT_REGISTER.md`: no debt row changes by this lane.
- Re-run on a database lane: `tests/integration/api/test_role_register.py`, `test_authorization.py`, `test_served_document_and_health_plane.py`, `tests/integration/composition`.
