# AR v3 beta prompt seal — unserved code result

**Task:** [AR-V3-BETA-PROMPT-SEAL-01](tasks/AR-V3-BETA-PROMPT-SEAL-01.md) from the development base `5286248d68ea72740aec2130a98913333b69a9ea`. The source task lives on the published `dev` task-preparation commit; this isolated lane starts from its frozen base and changes only the task's owned code, test and report paths.

## Result

`v3_profile.py` registers a distinct, immutable AR v3 beta identity pair (`ap_01M5M28ZCDD8VPSP1BTAEW92YE`, `pb_01M5M28ZCDVCR37BX1884JGSPM`) for the six F1/F2/A1/A2/S1/S2 scopes. Resolution re-reads and verifies the frozen original topic file, the reviewed AR source material, the response schema, the Ф1.3 source policy and the fixed scope composition. Literal SHA-256 seals bind the system prompt, response schema, bundle and profile; changes fail closed under the same identity. The served AR v1 and recorded AR v2 profile identities are explicitly checked for collision and are unchanged.

`prepare_beta_v3_request` requires the exact identity pair, beta snapshot, scope/composition and caller-supplied Run/map/set/version pins. It reuses the existing canonical set parser and scoped candidate builder, then emits canonical request material with its own digest. Selected labelled paragraphs and project text appear; unselected rebinding paragraphs remain local. Its caller must independently prove current Attempt and Blob custody. Neither the function nor the synthetic tests approve a map or issue a provider request.

## Changed files and checks

- `src/auditmanager/analysis/profiles/ar_v3/v3_profile.py` — immutable manifest, resolver and scoped material builder.
- `tests/integration/analysis/test_ar_v3_profile_seal.py` — six golden material digests, source mutation, identity collision, wrong scope/set/order, oversized prompt, hidden-paragraph and project/set mutation cases.
- This report.

The task's focused profile, request, scope, prompt and historical text-profile tests: **75 passed**. Python compilation, whitespace, exact allowed-path audit and technical handoff are recorded with the lane commit. The full `make gate` remains deferred under `R-135` until the final beta candidate.

## Contracts, limits and integration

No API/domain contract, migration, composition root, provider transport, router/UI, root dependency/lock file, global style, original topic, normative map or source bytes changed. No Run, CITE StageResult, finding or numerical conclusion is created. The sealed module is still **unserved**; it cannot by itself make v3 available to users.

The six-Run owner may pin this profile/bundle pair in new Run records after an exact approved pack exists. The executor must resolve the same pair, verify the current Attempt and custody-checked set, call `prepare_beta_v3_request`, record the exact material digest and bind the provider response to that Attempt before the separate review-only CITE stage. Never switch existing v1 Run identities or infer expert approval from this seal. Before any runtime use, a forward revert removes the module and test; after a Run uses the identity, retain its bytes for replay and disable new v3 starts via the later trusted-pack switch.
