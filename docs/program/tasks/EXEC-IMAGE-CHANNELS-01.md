# Task EXEC-IMAGE-CHANNELS-01 — image input on served executor channels

task_id: EXEC-IMAGE-CHANNELS-01

## Outcome

One verified saved PNG can reach every served executor variant: direct/VPN HTTP
OpenAI Chat or Anthropic Messages, pull command, pull local endpoint and pull MCP
session. Invalid or missing bytes fail before a model call. SSH command and SSH
tunnel remain unserved by this release and are not represented as working routes.

## Depends on

- `EXEC-IMAGE-DELIVERY-01` — completed pull image reference and verified fetch.
- `EXEC-HTTP-01` — completed HTTP connection adapters.
- `EXEC-AGENT-01` — completed command and endpoint agent.

## Frozen inputs

- base commit: `0dfc1d5ae799142ba37ed7f3bc8a1e8082b73e34`
- API contract `1.1.0`, SHA-256 `889ac164ad356674471da8de734597d118b6799f352808b80da74d2b6f295a87`;
- stage registry SHA-256 `0ca693ff1abde4016af51fac9c0465800cb2659a0047207b84299ed0929d861e`;
- crop manifest SHA-256 `0d66634a6668edf87189720644fc3c651ad09fccb7418d0c1209d2a6a6e3da7e`;
- migration head `0031_executor_pull_channel`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/EXEC-IMAGE-CHANNELS-01.md`
- `docs/program/EXEC-IMAGE-CHANNELS-01.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/dispatch/EXECUTOR-CONNECTIONS-PLAN.md`
- `src/auditmanager/analysis/text/adapter.py`
- `src/auditmanager/analysis/text/proxy.py`
- `src/auditmanager/executors/http_adapter.py`
- `src/auditmanager/executors/image_input.py`
- `tools/executor-runner/**`
- `tests/unit/executor_runner/**`
- `tests/unit/executors/test_http_adapter.py`
- `tests/unit/executors/test_image_input.py`
- `tests/integration/analysis_text/test_proxy_adapter.py`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, composition roots, root dependency and lock
files, global styles, deployed runtime files, tags and `origin/main`.

## Non-goals

No W56b prompt, visual judgment, stage activation, new assignment key, finding
publication or paid call. No claim that the unserved SSH profiles can be routed.

## Deliverables

Image byte validation, multimodal payloads for both HTTP flavours and the local
endpoint, MCP image content, opt-in runner configuration, focused tests and report.

## Required tests

- Focused image transport and existing executor runner tests.
- Python compile, `git diff --check`, exact allowed-path inspection.
- Full `make gate` deferred under `R-135` for this development slice.

## Integration contract

A future image stage supplies a single descriptor in `ModelRequest.body.images`
and the selected, Attempt-checked PNG in `ModelRequest.image_bytes`. The descriptor
includes its digest and size. Direct HTTP validates the bytes and uses each API's
image content block; pull persists the descriptor and fetches through its existing
claim-bound endpoint. Runner endpoint and MCP bridge fetch and recheck the PNG
before presenting it to the model. No image bytes are journaled or logged.

## Failure/idempotency/security cases

Wrong metadata, digest, size, PNG signature, unsupported configuration or lost
claim fails closed. One image is sent per request. The digest-bound request
identity and idempotency scope distinguish selected crops without persisting
image bytes.

## Rollback / feature flag

The image fields and opt-ins are optional; rollback is a revert before
activation of the image stage. Existing text requests remain unchanged.

## Handoff

- Changed files, test results, limits and integration instructions: paired report.
