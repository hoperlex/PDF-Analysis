# Task MODEL-IDENTITY-CHECK-01 — a reply from another model than the configured one is a typed stage failure

task_id: MODEL-IDENTITY-CHECK-01

## Outcome

In proxy mode a chat-completions reply that names a model other than the configured one
fails the stage with the typed code `model_identity_mismatch`, publishes no finding and
keeps the usage evidence; a matching reply behaves exactly as before; recorded mode is
unaffected. `R-133`: the identity check fails closed, a gateway name or a tariff is never
guessed.

## Depends on

- `GATE-REPAIR-01` — completed, merged (`ba6af907`).

## Frozen inputs

- base: `origin/dev` at the freeze commit of this file (parent `b1154df2`, `integration/night-1020`);
- migration head `0029_routing_refusal_codes`; API 73/83/242; 27 error codes; contract `1.0.0`
  sealed: this task changes no contract and adds no migration;
- rulings: `R-135` (no complete gate in a lane), `R-126`, and the owner's direct instruction of
  2026-10-22 «гони до беты без вопросов»: a naming or policy choice that is not blocked by a
  recorded owner decision is taken with the default named below and reported, not asked.

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

- `src/auditmanager/analysis/text/adapter.py`
- `src/auditmanager/analysis/text/proxy.py`
- `tests/integration/analysis_text/test_model_identity.py` (new)
- `tests/integration/analysis_text/test_proxy_adapter.py`
- `tests/integration/analysis_text/test_w53c_proxy_answer_shapes.py`
- `tests/unit/analysis/**`
- `docs/program/MODEL-IDENTITY-CHECK-01.md`
- `docs/program/tasks/MODEL-IDENTITY-CHECK-01.md`

## Lane resources

- container-free: this task starts no stand and runs no database suite (`R-126`); the integrator's
  complete gate runs the database suites on the merged candidate.
- reserved and unused here: foundation_instance `auditmanager-lane-b1`, postgres_port `57620`, s3_api_port `61420`

## Forbidden hotspots

Every `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, dependency and lock files,
`src/auditmanager/bootstrap/**`, `tests/support/**`, any `conftest.py`, `tests/e2e/**`, `web/**`,
`docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`, refs, tags and the stand. The
worktree `.local/worktrees/gate-night` and the instance `auditmanager-gate-night` belong to a running
gate and are not read or run. A change that needs a path outside the allowed list is reported to the
integrator at once, not made.

## Non-goals

No live provider call, no key, no gateway probe (`W56A-MODEL-PIN-01` owns the pinned value and
stays stopped). No contract change: `model_identity_mismatch` is already in the enum and the
catalogue. No change to `runs/**`: if the failure code does not reach the stage record without
one, report the exact file and line instead of editing it.

## Work

1. `ModelResponse` (`adapter.py`) gains an optional `model: str | None = None`, last, so every
   existing constructor and the recorded adapter are unchanged.
2. `proxy.py:_from_openai_response` reads the reply's `model` string (absent stays `None`).
3. **Default taken (not asked):** the configured name is `PROXY_LLM_MODEL` as `ProxySettings`
   already holds it; the check is an exact match, with an optional alias list in
   `ProxySettings` (an empty default) for gateways that echo a dated variant; a reply with no
   `model` field when a name is configured is a mismatch (fail closed), not a pass. The check
   raises a `ProxyDispatchError` with `ErrorCode.MODEL_IDENTITY_MISMATCH`, `dispatch_class`
   `outcome_unknown`, `retry_safe=False`, and carries `received` usage like `_unusable_answer`.
4. Stub or default model names are refused in proxy mode where the settings validation already
   refuses other bad values; do not invent a new settings key beyond the alias list.
5. Tests, each failing first and then green: matching name passes; other name raises with the
   typed code and keeps usage; missing field raises; alias accepted; recorded mode unchanged.
   Quote a mutation for each new branch (`-o pythonpath=<copy>/src`, prove the copy was imported).

## Deliverables

The two changed source files, the tests, and `docs/program/MODEL-IDENTITY-CHECK-01.md` (what changed, the default taken, commands with exit status, mutations, what was not exercised).

## Required tests

`tests/integration/analysis_text/test_model_identity.py`, `test_proxy_adapter.py`,
`test_w53c_proxy_answer_shapes.py`, `test_provider_modes.py`, `tests/unit/analysis`: all green
without containers; before/after counts quoted.

## Integration contract

Merged as a real merge into `integration/night-1020` by the integrator; light acceptance only
(`AGENTS.md` §8): `git diff --check`, the named test files, `tests/contract` with the complete
gate's own three ignores. The slice is closed when its outcome is reachable and its negative case is
tested, with the quoted mutations shown failing.

## Failure/idempotency/security cases

A reply with a different model never becomes a finding. A refusal keeps the evidence of what
was spent. Nothing in the failure message carries the key or the base URL.

## Rollback / feature flag

Revert the merge. No flag.
