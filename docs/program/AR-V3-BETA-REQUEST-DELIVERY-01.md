# AR v3 beta request delivery — development result

**Task:** [AR-V3-BETA-REQUEST-DELIVERY-01](tasks/AR-V3-BETA-REQUEST-DELIVERY-01.md). **Base:** published `origin/dev` `15f3e0f371b6146a8f529892270a0910792a0aaa`. **Target:** `origin/dev` only.

## Result

`build_v3_model_request` converts one sealed scoped v3 envelope into the existing `ModelRequest` consumed by HTTP, pull and SSH model adapters. It checks the immutable profile, scope membership, material JSON and SHA, response schema and explicit generation settings. The body contains the selected user prompt and original sealed system prompt; unselected rebinding paragraphs stay local. Idempotency scope is transport metadata and does not change the provider-body digest.

The six synthetic scopes have exact pinned provider-body SHA-256 values in the test. The local candidate SHA and provider-body SHA are intentionally distinct: the former binds the selected set and scope material; the latter also binds model identity and generation parameters. A future executor must record both after proving Run/Attempt/set custody and before accepting a response. No provider call, Run state or normative verdict is produced here.

## Changed files and checks

- `src/auditmanager/analysis/profiles/ar_v3/request_delivery.py` — pure checked conversion.
- `src/auditmanager/analysis/public.py` — public sealed-request and transport-builder seam.
- `tests/integration/analysis/test_ar_v3_request_delivery.py` — six golden bodies, hidden paragraph exclusion, parameter mutation and invalid-input refusals.
- Task file, this report and `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md` — ownership and remaining boundary.

The new delivery, existing profile-seal and v3 execution-guard suites: **50 passed**. Analysis package, API seal and public-seam contracts: **57 passed**. `git diff --check` and the exact allowed-path inventory passed: **6 changed files, zero outside** the task. Full `make gate` stays with final beta acceptance under `R-135`.

## Integration, risks and rollback

The builder proves internal seal consistency, but it cannot prove that a caller obtained its set bytes from a custody-verified Run. The future executor must load the verified set under current Attempt authority, build the sealed request from those bytes, commit model-call intent before dispatch, recheck authority after response, and preserve provider provenance. The production trusted-pack registry remains empty and v3 Run execution stays refused.

No contract, migration, composition root, root dependency/lock file, global style, normative source/map, provider adapter, Run executor, CITE publication, `origin/main`, tag or deployment host changed. The pure bridge can be reverted before full executor integration; the prior v3 execution guard remains active.
