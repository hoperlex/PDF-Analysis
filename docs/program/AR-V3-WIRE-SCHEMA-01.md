# AR-V3-WIRE-SCHEMA-01 — the AR v3 response schema in a form the model providers accept

Written 2026-10-29 by the integrator from the final report of the Sonnet lane `AR-V3-WIRE-SCHEMA-01` (branch `agent/ar-v3-wire-schema-01`, tip `af5460ba`, base `e01cce43`; merged as `25cc1cdf`). The lane cannot create new `.md` files, so this report is the integrator's. Task file: `docs/program/tasks/AR-V3-WIRE-SCHEMA-01.md`.

## Why

The owner activated AR v3 on the live host on 2026-10-29 (`scripts/ar-v3/activate-live.sh`, `R-146be`). The six Runs of the group all ended `failed / analysis_input_invalid` after three stages, with no `model_call` row: the first model call was refused with HTTP 400 `upstream_error`. The run route was the environment one (`AUDITMANAGER_PROVIDER_SOURCE` unset, `AUDITMANAGER_PROVIDER_MODE=proxy`, `audit_run.connection_revision_id` empty), the model `anthropic/claude-sonnet-5` behind the OpenRouter-compatible proxy. The code does not log the proxy's error body (it can hold prompt text), so the reason was read by the owner's probe (`scripts/ar-v3/live-schema-probe.py`, run in the worker container): T1 plain call 200, T2 `max_tokens` 16000 200, **T3 the AR v3 schema as sent 400 `output_config.format.schema: Schema type 'oneOf' is not supported`**, T4 the same schema without `oneOf` and the value constraints 200. The AR v3 schema had only ever been sent in recorded mode.

## What changed

`src/auditmanager/analysis/text/wire_schema.py` (new): `to_wire_schema(schema)` (`oneOf` becomes `anyOf`; `minLength`, `maxLength`, `minimum`, `maximum`, `maxItems`, `pattern` are removed; `minItems` stays only for 0 or 1; property names are names and never filtered; a new object, idempotent, depth bound 64, a non-mapping comes back unchanged; the v1 text schema comes out byte-identical) and `with_wire_schema(body)` (the same for `output_config.format.schema` of an Anthropic-shaped body; an addition of the lane to the task text). Both are re-exported by `analysis/public.py`.

Applied at the five places that hand a response schema to a provider (the lane's own grep found exactly these): the proxy translation `_to_openai_body` (also the `openai_chat` connection flavour, a subclass), `AnthropicMessagesAdapter.complete` (`anthropic_messages`), `LiveAdapter.complete` (direct Anthropic), the SSH task (`ssh_adapter._task`), the pull payload (`pull.py`, after `check_supported`, so the refusal is still judged on the sealed schema). The request's own body, its `request_sha256`, the sealed schema, the prompt, the pack, the digests and the local parser `ar_v3/response.py` are untouched; the parser re-checks every dropped constraint itself and drops a malformed proposal, so it stays the authority on what is accepted.

**Verified by the integrator against the live evidence:** for the real AR v3 schema `to_wire_schema(schema) == clean(schema)` where `clean` is the exact function of probe T4 (the schema the live proxy answered 200 to); the sealed schema object is unchanged after the call.

## Checks (measured on the merged tree `25cc1cdf`, lane stack at head `0039_comparison_core`)

- `tests/unit` + `tests/contract` (minus the three `D-220` files) + the two journey conformance files: **6554 passed, 76 skipped, 0 failed** (493 s; `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent`, CMP environment read-only, `D-256`).
- `tests/integration/{executors,analysis_text,analysis,runs}` on a real PostgreSQL + MinIO lane: **2413 passed, 22 skipped, 0 failed** (640 s).
- The lane's own run: `tests/unit/analysis tests/unit/executors tests/contract/program` 1596 passed / 73 skipped; `tests/contract/architecture` and three analysis-text integration files 172 passed.
- New tests (122): `tests/unit/analysis/text/test_wire_schema.py` (101: each rule, the real schema, eight cases where the wire schema no longer states a constraint and `parse_response` still drops the proposal), `test_wire_schema_text_transports.py` (9: the proxy POST bytes, the direct SDK kwargs), `tests/unit/executors/test_wire_schema_executor_transports.py` (12: `http_api` both flavours against a local gateway, SSH stdin, pull payload, request integrity).
- Mutation table (13 mutations, each red, each restored and byte-compared): M1 proxy call off (2 red), M2 direct adapter off (1), M3 `anthropic_messages` off (1), M4 SSH off (1), M5 pull off (2), M6 property names filtered (4), M7 idempotence broken (9), M8 `maxItems` not dropped (16), M9 `minItems` always kept (8), M10 `oneOf` not renamed (36), M11 depth bound removed (2), M12 `with_wire_schema` returns the body (3), M13 shared children (1).

## Limits (recorded as `D-280`..`D-283`)

- The wire form's path is proven by tests and by its equality with the schema of probe T4; the first live AR v3 Run after the deploy proves it end to end. Probe T4 dropped `maximum`, `pattern` and the rest together, so which of them a provider refuses alone is not known.
- Pull: the server-side `read_answer` now runs against the wire form; an over-long or out-of-pattern runner answer is no longer sent back for correction (the local parser drops it). `oneOf` becomes «at least one» (the two v3 alternatives are disjoint by the category enum).
- SSH and pull: whether the remote agent applies the schema as a provider-side structured-output schema is not verifiable here.
- A depth over 64 raises `ValueError` and is not mapped to a typed dispatch error at four of the points (the schemas are code constants about nine levels deep; pull cannot reach it).
- The environment route (`_to_openai_body`) sends no `thinking` and no `effort`; the AR v3 body is designed with adaptive thinking and an effort setting. This is the existing OpenAI-compatible translation, not new, but it is the route the live Runs take.
- ruff and mypy are not installed in the CMP environment and were not run.
