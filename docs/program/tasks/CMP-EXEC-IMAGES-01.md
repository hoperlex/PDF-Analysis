# Task CMP-EXEC-IMAGES-01 — up to eight images per executor task, gated on the server by the claim's `max_images`

## Outcome
A model request carries an ordered list of up to 8 images, each addressed by an opaque crop reference, on every served executor
channel (HTTP direct, VPN and SSH tunnel, pull command, local endpoint, MCP session, SSH command); the server never hands a task to
a claim whose declared `max_images` is smaller than the task's image count (absent means 1); a runner tool that cannot serve all
the images refuses the task with `image_input_unsupported` and never answers on a subset. The one-image portal-block path of the
section runs is byte-for-byte what it was. ADR-0025 decision 18.

## Depends on
- CMP-SEAL-C0 (merged at `0990de4b`: `RunnerImage.crop_id`, `ClaimedExecutorTask.images` up to 8, `ClaimExecutorTaskRequest.max_images`)
- EXEC-IMAGE-CHANNELS-01, EXEC-SSH-CROPS-01, EXEC-SSH-TUNNEL-CROPS-01 (the one-image channels this extends)

## Frozen inputs
- domain contract: `contracts/domain/v1/**` unchanged
- API contract: `contracts/api/v1/openapi.json` `1.9.0`, 115 paths / 130 operations / 351 schemas (not edited)
- analysis/comparison/event contract: ADR-0025 decision 18 (8 images, 16 MiB each, 32 MiB in all, opaque crop reference,
  server-side gating, absent = 1, `image_input_unsupported`, never a subset answer)
- migration head: `0038_comparison_foundation` (not edited); the base commit is the tip of `integration/compare-modules` after the wave brief
- base commit: `cc3dd36b5b05b28ed0232107c8d0a437e304f07b`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: contract `1.9.0`, 115 / 130 / 351, 27 error codes, head `0038_comparison_foundation`, `VERSION` `0.9.0`

### P-01 — the base facts read before any edit
- captured_at: 2026-10-28
- command: `python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas',len(d['components']['schemas']['ErrorCode']['enum']),'error codes')"; cat VERSION; git grep -n "^revision: str" HEAD -- db/migrations/versions/ | grep 0038 | cut -d: -f3-`
- captured_output:
  ```text
  contract 1.9.0 115 paths 130 operations 351 schemas 27 error codes
  0.9.0
  revision: str = "0038_comparison_foundation"
  ```
- interpretation: equal to the premise, so the lane did not STOP. The report is `docs/program/CMP-EXEC-IMAGES-01.md`.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/executors/image_input.py`
- `src/auditmanager/executors/pull.py`
- `src/auditmanager/executors/http_adapter.py`
- `src/auditmanager/executors/ssh_adapter.py`
- `src/auditmanager/executors/ssh_tunnel_adapter.py`
- `src/auditmanager/executors/runner_repository.py`
- `src/auditmanager/analysis/text/adapter.py`
- `tools/executor-runner/**`
- `tests/unit/executors/**`
- `tests/integration/executors/**`
- `src/auditmanager/executors/runner.py`
- `src/auditmanager/executors/public.py`
- `src/auditmanager/bootstrap/runner.py`
- `src/auditmanager/api/routers/runner.py`
- `src/auditmanager/api/routers/ports.py`
- `tests/unit/executor_runner/**`
- `docs/program/tasks/CMP-EXEC-IMAGES-01.md`
- `docs/program/CMP-EXEC-IMAGES-01.md`

## Lane resources
- foundation_instance: `auditmanager-cmp-exec-images-01`
- postgres_port: `57740`
- s3_api_port: `61740`
- s3_console_port: `61741`
- postgres_db: `auditmanager_cmp_exec_images_01`
- s3_bucket: `auditmanager-cmp-exec-images-01`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, root dependency and lock files
- `src/auditmanager/bootstrap/composition.py`, `src/auditmanager/bootstrap/adapters.py`, global styles
- `src/auditmanager/api/schemas/models.py` (the wire models already carry `crop_id` and `max_images`)
- `src/auditmanager/comparison/**`, `src/auditmanager/executors/model.py`

## Non-goals
- no comparison stage creates an image task here (the comparison AI layers are later lanes); this lane only makes the channel able to carry one
- no new error code, contract field or migration: a missing field is a STOP to the wave's FIX slot
- `claude_answer.py` keeps refusing every image (the CLI is started with no tool); only its agent declaration is documented
- no live model, provider or real runner call; every test is local or recorded

## Deliverables
- `ModelRequest.images_bytes` (ordered list), `executors/image_input.py` with the limits, the shared descriptor check, `CropImage`, `attach_images`, `image_load`
- the pull task payload with up to 8 references; the claim gating in `runner_repository.claim_next` and `redeliver`; `max_images` carried from the wire model to the SQL
- direct HTTP (OpenAI Chat, Anthropic Messages), SSH tunnel and SSH command carry every image in order
- `tools/executor-runner`: `max_images` declared by the agent and the MCP bridge, all images fetched, verified and delivered, refusal on a subset, `RUNNER_API.md` and `README.md`
- tests: unit and integration with a mutation proof for each guard; the report `docs/program/CMP-EXEC-IMAGES-01.md`

## Required tests
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/unit/executors tests/unit/executor_runner`
- expected: green; the figures are in the report
- command: the same with `tests/integration/executors` on the lane's own PostgreSQL and MinIO (ports above)
- expected: green; the figures are in the report

## Integration contract
- A comparison caller builds a request with `attach_images(request, [CropImage(crop_id, png_bytes), ...])` from `auditmanager.executors.public`; the order is the order the model sees.
- A task is handed only to a claim whose `max_images` is at least the task's image count; a claim without `max_images` is a claim for one.
- `getExecutorTaskImage` serves a crop by its blob id from the current claim exactly as it serves a portal-block crop.
- The wiring hunks outside the explicit path list above (`executors/runner.py`, `executors/public.py`, `bootstrap/runner.py`, `api/routers/runner.py`, the `RunnerPort` protocol in `api/routers/ports.py`) are the claim path of the sealed operation `claimExecutorTask` and are kept to the lines that carry `max_images`; the wave brief (section 1 rule 4) gives the lane that implements a sealed operation its router file and port rows.

## Failure/idempotency/security cases
- a descriptor that is not exactly one of a portal-block reference or a crop reference, a duplicate crop id, a ninth image, an image above 16 MiB, a set above 32 MiB, bytes that do not match their digest: refused before any key, prompt or image is sent
- a claim with `max_images` below the task's count is never offered it, on a fresh claim and on a redelivery
- an old remote SSH script that does not know a list of images refuses the task (fail closed); it never answers from the text alone
- a runner that cannot deliver every image fails the task with `image_input_unsupported` or `image_delivery_failed` and submits nothing

## Rollback / feature flag
No flag. Nothing creates a multi-image task until a comparison stage does, so reverting this slice changes no behaviour for the section runs.

## Handoff
- changed files: 40 against `cc3dd36b` (12 source files, 7 tool files, the runner and executor tests, this task file and the report); no contract, migration, dependency, composition-root or web file
- commands/results: `tests/unit/executors` + `tests/unit/executor_runner` 897 passed; `tests/integration/executors` on the lane database 248 passed, 16 skipped (opt-in sshd); `tests/contract` minus the three `D-220` files 1307 passed; 38 quoted mutations all red; `git diff --check` clean; details and commands in `docs/program/CMP-EXEC-IMAGES-01.md` sections 7 and 8
- known limits: no real Codex or runner call (the `-` before `--image` is tested against a fake only); MCP result-size limit for many crops; no early signal when no runner can serve a wide task (`no_executor_online` after the answer window); transfer time of 32 MiB unmeasured; see section 9 of the report
- integration notes: merge after `CMP-SPEND-01`; hunks outside the explicit own paths are the claim path of `claimExecutorTask` (section 10 of the report); no stub-enumerator row to remove; comparison callers use `attach_images` from `auditmanager.executors.public` (section 2 of the report)
