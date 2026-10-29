# Task AR-V3-WIRE-SCHEMA-01 — the AR v3 response schema in a form the model providers accept

task_id: AR-V3-WIRE-SCHEMA-01
status: completed in development candidate (lane `af5460ba`, merged `25cc1cdf`; report `docs/program/AR-V3-WIRE-SCHEMA-01.md`, written by the integrator from the lane's hand-back)

## Outcome

On the live stand all six AR v3 Runs failed on their first model call: the model proxy answered HTTP 400 `upstream_error`, the provider's own text being `output_config.format.schema: Schema type 'oneOf' is not supported` (premise P-02). The AR v3 response schema carries keywords that strict structured-output providers reject (`oneOf`, `minLength`, `maxLength`, `minimum`, `maxItems`, `pattern`; premise P-01), and every transport hands that schema to the provider unchanged. After this task each transport hands the provider a **wire form** of the schema (`oneOf` becomes `anyOf`; the unsupported constraints are dropped); the sealed schema, the prompt, the pack, every digest and the local parser (`analysis/profiles/ar_v3/response.py`, which re-checks every dropped constraint itself and drops a malformed proposal) are untouched.

## Depends on

- `AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01` (the activation that produced the failing Runs), `R-146be`.
- Owner's live probe of 2026-10-29 (P-02), `scripts/ar-v3/live-schema-probe.py`.

## Frozen inputs

- domain contract: unchanged
- API contract: `1.10.0`, `131` paths / `148` operations / `432` schemas, unchanged (no operation, schema or error code moves)
- analysis/comparison/event contract: not_applicable
- migration head: `0039_comparison_core`, unchanged
- base commit: `origin/dev` `0277e4ef`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the lane reads the schema keywords and every hand-over point from the code and from the owner's live probe before it writes

### P-01 — the keywords of the AR v3 response schema that strict providers refuse

- captured_at: 2026-10-29
- command: `PYTHONPATH=src .venv/bin/python -c "from auditmanager.analysis.profiles.ar_v3 import response_schema as rs;s=rs.response_schema;s=s() if callable(s) else s;k=set();w=lambda o:[(k.update(o) if isinstance(o,dict) else None),[w(v) for v in (o.values() if isinstance(o,dict) else o if isinstance(o,list) else [])]];w(s);print(sorted(k&{'oneOf','minLength','maxLength','minimum','maxItems','minItems','pattern'}))"`
- captured_output:
  ```text
  ['maxItems', 'maxLength', 'minItems', 'minLength', 'minimum', 'oneOf', 'pattern']
  ```
- interpretation: the schema uses all of `oneOf`, `minLength`, `maxLength`, `minimum`, `maxItems`, `pattern` and `minItems` (value 1). The v1 text-analysis schema uses only `minItems: 1`, `additionalProperties: false` and `enum`, which is why the other sections ran live.

### P-02 — what the provider says (owner's live probe, worker container, 2026-10-29)

- captured_at: 2026-10-29
- command: `docker compose --env-file infra/deploy/env/alpha.env --file infra/deploy/compose.server.yml exec -T worker python - < scripts/ar-v3/live-schema-probe.py`
- captured_output:
  ```text
  base: https://proxyllm.fvds.ru | model: anthropic/claude-sonnet-5 | token set: True
T1 plain, small max_tokens -> 200
T2 plain, max_tokens 16000 -> 200
T3 v3 schema as sent -> 400 {"error":{"message":"Provider returned error","code":400,"metadata":{"raw":"{\"type\":\"error\",\"error\":{\"type\":\"invalid_request_error\",\"message\":\"output_config.format.schema: Schema type 'oneOf' is not supported\"},...","provider_name":"Google","is_byok":false,"previous_errors":[{"code":400,"message":"Provider returned error","provider_name":"Claude Platform on AWS",...}]}}}
T4 v3 schema without unsupported keywords -> 200
  ```
- interpretation: route, model and `max_tokens` are fine (T1, T2); the schema as sent is refused for `oneOf` (T3); the schema with `oneOf` replaced by `anyOf` and the six constraints dropped is accepted (T4). The provider names `oneOf` first; whether `pattern` alone would pass was not tested, so the wire form drops it too (the local parser checks the label itself).

### P-03 — the places that hand a response schema to a provider

- captured_at: 2026-10-29
- command: `grep -rn -E 'output_config|output_schema|messages\.create' src/auditmanager/executors/http_adapter.py src/auditmanager/executors/ssh_adapter.py src/auditmanager/executors/pull.py src/auditmanager/analysis/text/proxy.py src/auditmanager/analysis/text/live.py`
- captured_output:
  ```text
  src/auditmanager/executors/http_adapter.py:200:            message = self._client.messages.create(**body, timeout=allowed)
  src/auditmanager/executors/ssh_adapter.py:69:    output = body.get("output_config")
  src/auditmanager/executors/ssh_adapter.py:73:            task["output_schema"] = schema
  src/auditmanager/executors/pull.py:178:    """``system``, ``user_text`` and ``output_schema`` out of the Anthropic-shaped body the
  src/auditmanager/executors/pull.py:186:    output = body.get("output_config")
  src/auditmanager/executors/pull.py:200:        "output_schema": schema if isinstance(schema, Mapping) else {"type": "object"},
  src/auditmanager/executors/pull.py:249:            check_supported(payload["output_schema"])
  src/auditmanager/executors/pull.py:405:        "output_schema": {
  src/auditmanager/analysis/text/proxy.py:410:        source.get("output_config", {}).get("format", {}).get("schema")
  src/auditmanager/analysis/text/proxy.py:411:        if isinstance(source.get("output_config"), Mapping)
  src/auditmanager/analysis/text/live.py:80:            message = self._client.messages.create(**dict(request.body))
  ```
- interpretation: five hand-over points — the proxy translation (`_to_openai_body`, the `openai_chat` flavour is a subclass), the `AnthropicMessagesAdapter` (`messages.create(**body)`), the direct `analysis/text/live.py` adapter (`messages.create(**dict(request.body))`), the SSH task (`task["output_schema"]`) and the pull payload (`output_schema`). The lane confirms the list with its own grep and states any further site it finds before it writes.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/text/wire_schema.py` (new: the one function) and the module the other adapters import the request types from, for its re-export
- `src/auditmanager/analysis/text/proxy.py`, `src/auditmanager/analysis/text/live.py`
- `src/auditmanager/executors/http_adapter.py`, `src/auditmanager/executors/ssh_adapter.py`, `src/auditmanager/executors/pull.py`
- `tests/unit/analysis/text/**`, `tests/unit/executors/**` (new test files; an existing test changes only if its expectation was the bug)
- nothing else; a further hand-over point found by the grep is added to this list in the lane's report and edited only if it is one of the five kinds above

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependency/lock files, `src/auditmanager/bootstrap/**`
- the sealed schema and its profile: `src/auditmanager/analysis/profiles/**`, including `ar_v3/response_schema.py`, `ar_v3/response.py` and `ar_v3/request_delivery.py`
- `src/auditmanager/jobs/**`, `src/auditmanager/runs/**`, `src/auditmanager/comparison/**`, `web/**`
- `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the rulings, ADRs (the integrator edits these)

## Non-goals

- changing the sealed AR v3 schema, prompt, pack, digests or the local parser; a new profile version
- per-provider capability negotiation; a configuration switch; a live call
- the `answers.py` runner-side validator (`check_supported` keeps accepting every keyword it accepts today)
- the choice of route (environment versus connections)

## Deliverables

- `to_wire_schema(schema)` with these rules, each with a test:
  1. returns a **new** object and never mutates its argument; idempotent;
  2. in a **schema position** (the schema itself, `items`, each value of `properties`, `anyOf`/`oneOf`/`allOf` members, `additionalProperties` when it is a mapping) `oneOf` becomes `anyOf`, and `minLength`, `maxLength`, `minimum`, `maximum`, `maxItems`, `pattern` are removed; `minItems` is kept only when its value is 0 or 1 and removed otherwise;
  3. in a **name position** nothing is filtered: the keys of a `properties` mapping (and of `$defs`/`definitions`/`patternProperties`) are property names and are kept even when a name equals a keyword (a property called `pattern`, `oneOf` or `maxLength` survives, its own schema is cleaned);
  4. everything else is kept as is: `type`, `enum`, `const`, `required`, `additionalProperties`, `items`, annotations, `anyOf`;
  5. a schema that is not a mapping is returned unchanged; a depth above 64 is refused with `ValueError`;
  6. the v1 text-analysis schema (`analysis/text/prompt.py`) comes out equal to what went in (no change for the sections that already ran live).
- each of the five hand-over points sends the wire form; the **request's own body, its `request_sha256` and the recorded journal are not changed** (the translation is at the edge, like the existing OpenAI translation).
- tests: the function (rules 1-6, one case each, plus the real AR v3 schema: no `oneOf`, none of the six constraints, still all `required` and `enum` entries); per hand-over point the body or task actually produced carries the wire form (capture the bytes a fake opener or fake client receives; assert on the payload, not on a helper call); a test that the v3 parser still rejects an over-long or out-of-range proposal that the wire schema no longer forbids (the safety net).
- a mutation table in the report: for each hand-over point, turn the call off and show the test red; break rule 3 (filter property names) and show red; break idempotence and show red.

## Required tests

- command: `BS=$(ls -d /root/projects/PDF-Analysis/.local/worktrees/cmp-seal-c0/.venv/bootstrap/lib/python3*/site-packages); PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.local/worktrees/cmp-seal-c0/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis tests/unit/executors tests/contract/program`
- expected: all pass. The shared `.venv` has no numpy/opencv/reportlab (`D-256`): use the CMP lane's environment read-only as above. `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent` for any run that reaches the legacy-prompt test (`D-252`). `tests/unit/executors/test_runner_long_poll_cap.py` is a known thread-timing flake (`D-254`): rerun it alone before suspecting code.

## Integration contract

The integrator can rely on: (1) every provider-bound schema in the five transports passes through `to_wire_schema`; (2) the sealed request, `request_sha256`, the recorded fixtures and the journal are byte-identical to before; (3) the local parser remains the authority on what is accepted; (4) the v1 sections' provider bodies are unchanged.

## Failure/idempotency/security cases

- a property named like a keyword is not dropped (rule 3); a schema with nested `oneOf` inside `items` and inside `properties` is cleaned at every level; a non-mapping schema (the pull default `{"type": "object"}` is a mapping, `None` is not) is not turned into something else;
- no log line, error or journal row gains schema text or document text.

## Rollback / feature-flag policy

Not a flag. Revert the commit; the transports then send the schema as before.

## Handoff

- the lane hands back: changed files, the commands run with results, the hand-over points found (confirming or extending P-03), the mutation table, known limits;
- known limits to state: whether the remote agent behind an `ssh_command` or `pull` connection applies the schema as a provider-side structured-output schema is not verifiable here; the live stand shows it on first use.
