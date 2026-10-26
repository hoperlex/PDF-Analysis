# Task PROD-13A-MODEL-IDENTITY-PROBE-TOOL-01 — the operator-run model identity probe (the tool half of PROD-13)

task_id: PROD-13A-MODEL-IDENTITY-PROBE-TOOL-01
status: completed in development candidate

## Outcome

`scripts/model_probe/probe.py` exists and is tested with a stub transport. For each model pinned in `docs/program/P02_LOCK.json` it sends one minimal request through the product's own adapter (`build_http_adapter`, flavour `openai_chat`, the pinned destination layer included) and writes one report block per model: `requested_slug:`, `reported_model:`, the `R-133` verdict (exact string, no alias list, `AD-13`), usage and cost. It refuses to run without `--confirm-paid`, honours a total `--max-usd` ceiling (default 0.50, refused above 5.00), stops at it, and never writes `P02_LOCK.json`. The lane itself made no network call, read no credential and spent nothing (`R-146af`, `R-146e`, `AD-13`; `R-133`, `R-29`).

## Depends on

- `PRODUCTION-READINESS-PLAN-01` item `PROD-13` — accepted; this task is its tool half. The live run and the lock are the integrator's afterwards (`R-146af`).
- `EXEC-HTTP-01`, `EXEC-ENV-OPENROUTER-01`, `MODEL-IDENTITY-CHECK-01` — completed; the adapter and the comparison this tool drives.

## Frozen inputs

- domain contract: not_applicable
- API contract: unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable
- migration head: unchanged
- base commit: `0e663fd0e608fcf5f79075ea71713c24ddf027e5` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

The probed set is read from the lock at run time; nothing in the tool enumerates models.

## Captured premise evidence

- premise: the brief's sentences about the adapter's identity comparison, the connection configuration, the lock, `W56A-MODEL-PIN-01`, an existing probe and the repository's script idiom, re-read at the base commit; the premise holds, with four refinements recorded in P-01, P-04, P-06 and P-08 (none is a stop)

### P-01 — where the reply's `model` is compared with the pinned name (the brief names `http_adapter.py`; it compares nothing itself)

- captured_at: 2026-10-26
- command: `grep -n 'identity_pinned and not _is_configured_model\|def _is_configured_model\|reported == settings.model or reported in settings.model_aliases' src/auditmanager/analysis/text/proxy.py; grep -n 'reported != expected' src/auditmanager/analysis/text/stage.py; grep -n 'response.model != call.expected_model' src/auditmanager/runs/v3_provider_call.py; grep -n 'return ("ok" if name == expected_gateway_model' src/auditmanager/executors/identity.py; echo "model_aliases= in src: $(grep -rn 'model_aliases=' src | wc -l)"`
- captured_output:
  ```text
  319:        if self.identity_pinned and not _is_configured_model(response.model, self._settings):
  452:def _is_configured_model(reported: str | None, settings: ProxySettings) -> bool:
  459:        reported == settings.model or reported in settings.model_aliases
  283:    elif not isinstance(reported, str) or reported != expected:
  279:    if mode is ProviderMode.LIVE and response.model != call.expected_model:
  86:    return ("ok" if name == expected_gateway_model else "model_mismatch"), name
  model_aliases= in src: 0
  ```
- interpretation: `http_adapter.py` compares nothing for the `openai_chat` flavour: `build_http_adapter` returns `OpenAIImageAdapter`, a subclass of `ProxyAdapter`, whose `complete` (proxy.py:319) refuses a pinned model's reply unless it equals the configured name or a listed alias; `src/` never sets an alias (0). For `anthropic_messages` the adapter only attaches the reply's `model` (http_adapter.py:217) and the run-path callers compare (`stage.py:283`, `v3_provider_call.py:279`), all by string inequality. The shared pure function for the same exact comparison is `executors/identity.py:assess_identity` (line 86), which the probe uses for its verdict. All comparisons are exact: no prefix, no case folding, no alias list (`AD-13`).

### P-02 — what the adapter does on a mismatch, and what it does not carry

- captured_at: 2026-10-26
- command: `sed -n '474,484p' src/auditmanager/analysis/text/proxy.py`
- captured_output:
  ```text
      _LOGGER.warning(
          "model proxy identity mismatch: reported=%.80r", reported,
      )
      return ProxyDispatchError(
          ErrorCode.MODEL_IDENTITY_MISMATCH, dispatch_class="outcome_unknown",
          retry_safe=False,
          message=(
              "the model proxy answered with a model other than the configured one, or "
              "named none; the answer is not published"
          ),
          received=_received_evidence(raw, latency_ms, document),
  ```
- interpretation: the typed refusal `model_identity_mismatch` is `outcome_unknown` and never retry-safe, and carries usage evidence but **not the reported name**: that goes to the log only. The probe's whole value on a mismatch is the reported string (`AD-13` sets the pin to what OpenRouter reports), so the tool wraps the adapter's opener to keep the reply body (only a 200 body, never an error body), and scrubs the credential from every log record made during the run, since the adapter logs the reported string.

### P-03 — how the connection is configured

- captured_at: 2026-10-26
- command: `grep -n 'PROXY_BASE_URL_ENV: \|PROXY_TOKEN_ENV: \|PROXY_MODEL_ENV: ' src/auditmanager/bootstrap/settings.py; grep -n '^PROXY_LLM_' infra/deploy/env/provider.env.example; grep -n 'openai_chat\|Реальный платный вызов' docs/program/EXEC-ENV-OPENROUTER-01.md`
- captured_output:
  ```text
  110:PROXY_BASE_URL_ENV: Final[str] = "PROXY_LLM_BASE_URL"
  111:PROXY_TOKEN_ENV: Final[str] = "PROXY_LLM_TOKEN"
  112:PROXY_MODEL_ENV: Final[str] = "PROXY_LLM_MODEL"
  68:PROXY_LLM_BASE_URL=
  69:PROXY_LLM_TOKEN=
  76:PROXY_LLM_MODEL=proxy
  14:Для такого подключения применяется `openai_chat`: проверенный PNG идёт в
  16:изображения. Реальный платный вызов OpenRouter не выполнялся.
  ```
- interpretation: the OpenRouter connection is the `PROXY_LLM_BASE_URL` / `PROXY_LLM_TOKEN` / `PROXY_LLM_MODEL` triplet of the worker's process environment (`provider.env` on the host), flavour `openai_chat`; the example file ships empty values and `PROXY_LLM_MODEL=proxy`, a placeholder. No real paid OpenRouter call has ever been made through this adapter (`EXEC-ENV-OPENROUTER-01` line 16). The tool reads the first two names from the process environment only (a test pins them equal to the constants of `bootstrap/settings.py`); `PROXY_LLM_MODEL` is not needed because the models come from the lock. No `provider.env` was read by this lane: the example file was grepped for its three names only.

### P-04 — the shape of `P02_LOCK.json` (identities and rates), and what an identity there is

- captured_at: 2026-10-26
- command: `python3 -I -c "import json;d=json.load(open('docs/program/P02_LOCK.json'));[print(t,e['model_id'],e['input_per_mtok_usd'],e['output_per_mtok_usd']) for t,e in d['models'].items() if isinstance(e,dict) and 'model_id' in e];print('run_cost_ceiling_usd',d['models']['run_cost_ceiling_usd'])"`
- captured_output:
  ```text
  primary claude-opus-5 5.0 25.0
  cheaper_tier claude-sonnet-5 2.0 10.0
  codex_subscription gpt-6-sol 2.0 10.0
  run_cost_ceiling_usd 1.0
  ```
- interpretation: three pins, each a `model_id` with an input and an output rate per million tokens (USD). A lock `model_id` is a **pin id** (what gives tariffs and the budget), not a gateway name: `http_adapter.py` says the revision's `gateway_model` is what is sent and what the reply must report. `W56A-PROBE-01` requested `anthropic/claude-opus-5`, a provider-prefixed name. So the tool does not send the pin id: it requires an explicit `--slug PIN=SLUG` for every probed model and never guesses a gateway name. The third pin (`gpt-6-sol`) is recorded for the owner's Codex subscription through the pull agent (`billing=not_metered` in the lock's own comment); whether OpenRouter serves it is unknown, so `--only` lets the integrator leave it out. The tool treats every probed model as metered.

### P-05 — what `W56A-MODEL-PIN-01` recorded and why it stopped

- captured_at: 2026-10-26
- command: `grep -n 'STOP before any new paid request' docs/program/W56A-MODEL-PIN-01.md; grep -n 'requested .anthropic/claude-opus-5. but received' docs/program/W56A-MODEL-PIN-01.md; grep -n '\$5 cap' docs/program/W56A-FREEZE-01.md | cut -c1-140`
- captured_output:
  ```text
  3:**Status: STOP before any new paid request.** The task remains the sole
  10:`W56A-PROBE-01`: that probe requested `anthropic/claude-opus-5` but received
  127:   all four probe calls against the wave's $5 cap (`R-29`, `R-134`). A projection
  ```
- interpretation: the earlier pin task stopped before a new paid request: the stand's configuration selected the `proxy` placeholder and the client policy at the time ignored an explicit `model`, so the failed probe received `meta/muse-spark-1.3-contributor` for a requested `anthropic/claude-opus-5`. It wrote no pin. `ADR-0024` `AD-13` makes this tool its successor. The `$5` wave cap is the `R-29` stop the ceiling's hard limit mirrors.

### P-06 — whether a probe or pin-checking script already exists

- captured_at: 2026-10-26
- command: `git ls-tree -r --name-only 0e663fd0 -- tools/provider tests/contract/provider; grep -n 'env-file\|urllib.request.urlopen\|primary_model_id' tools/provider/identity_probe.py; echo "http_adapter mentions: $(grep -c 'http_adapter' tools/provider/identity_probe.py)"`
- captured_output:
  ```text
  tests/contract/provider/test_identity_probe.py
  tools/provider/__init__.py
  tools/provider/identity_probe.py
  150:    opener: Any = urllib.request.urlopen,
  158:    pin = provider_lock().model(provider_lock().primary_model_id)
  196:    parser.add_argument("--env-file", type=Path, required=True)
  0
  ```
- interpretation: one exists: `tools/provider/identity_probe.py` (W56a). It makes **one** request per invocation, for the **primary** model only, reads a `provider.env` file named on the command line (a credential file), talks to `urllib` directly and never touches `http_adapter.py`. The brief's tool is a different thing (every pin, the product's adapter, no credential file, a total ceiling), so this lane builds a new one and does not edit `tools/provider/**` (outside the allowed paths). The product already ported its assessment into `executors/identity.py`, which the new tool reuses.

### P-07 — the repository's idiom for operator scripts and their tests

- captured_at: 2026-10-26
- command: `git ls-tree -r --name-only 0e663fd0 -- tests/unit/scripts scripts/model_probe; grep -n 'spec_from_file_location' tests/unit/scripts/test_export_paragraph_rows.py | cut -c1-110; echo "from scripts. imports in tests: $(grep -rl '^from scripts\.' tests --include=*.py | wc -l)"`
- captured_output:
  ```text
  tests/unit/scripts/test_export_paragraph_rows.py
  tests/unit/scripts/test_manual_scan.py
  29:SPEC = importlib.util.spec_from_file_location(
  from scripts. imports in tests: 24
  ```
- interpretation: `scripts/model_probe/` does not exist at the base. Python operator scripts live under `scripts/<topic>/` without `__init__.py` (a namespace package: `python -m scripts.<topic>.<module>` from the repository root with `PYTHONPATH=src`), and their unit tests live in `tests/unit/scripts/`, loading the script by file location (`test_export_paragraph_rows.py`) or by namespace import (24 tests). This lane uses `scripts/model_probe/probe.py` and file-location loading.

### P-08 — the owner's order for the live run (`R-146af`)

- captured_at: 2026-10-26
- command: `grep -n '^| `R-146af`' docs/program/OWNER_RULINGS_2026-09-17.md | cut -c1-420`
- captured_output:
  ```text
  1790:| `R-146af` | **Paid model-identity probes (`PROD-13`).** The owner declined both offered options (a pre-set ceiling; a question before each run) and ordered: «проведи сам на sonnet локально без внешних агентов субагентом по минимальной [смете]». The integrator has the probe tool written and run by a local Sonnet subagent, with no external agent,
  ```
- interpretation: the tool is written by this lane; the integrator runs it afterwards at the tool's own minimum ceiling (default 0.50 USD in total; the `R-29` stop at about 5 USD per wave still applies) and only if the process environment holds a credential, which must not be searched for in files. The line is longer than the cut; the part that binds this lane is the first half.

### P-09 — the adapter's transport seam the stub replaces

- captured_at: 2026-10-26
- command: `grep -n '__slots__ = ("_settings", "_opener")\|with self._opener(http' src/auditmanager/analysis/text/proxy.py; grep -n '^class OpenAIImageAdapter\|__slots__' src/auditmanager/executors/http_adapter.py`
- captured_output:
  ```text
  213:    __slots__ = ("_settings", "_opener")
  260:            with self._opener(http, timeout=_TIMEOUT_SECONDS) as response:
  114:    __slots__ = ("_director", "_timeout_seconds", "_context")
  161:    __slots__ = ("_client", "_gateway_model", "_timeout_seconds", "_context")
  259:class OpenAIImageAdapter(ProxyAdapter):
  ```
- interpretation: the adapter calls `self._opener(request, timeout=...)` as a context manager and reads `.status` and `.read()`; `OpenAIImageAdapter` adds no slots, so the base slot `_opener` is assignable. That is the one seam, and it is private: the tool wraps it to observe the reply and **refuses to run** if the adapter ever loses it (a test), instead of silently probing without seeing the reported model. The tests put the stub exactly there, under the product's real builder.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `scripts/model_probe/**`
- `tests/unit/scripts/test_model_probe.py`
- `docs/program/tasks/PROD-13A-MODEL-IDENTITY-PROBE-TOOL-01.md`
- `docs/program/PROD-13A-MODEL-IDENTITY-PROBE-TOOL-01.md`

## Forbidden hotspots

`src/**`, `docs/program/P02_LOCK.json`, every `provider.env` or `*.env` file with a value, `infra/**`, `tools/provider/**`, `.github/**`, `Makefile`, root dependency and lock files (`uv.lock`, `web/package-lock.json`, `pyproject.toml`), `contracts/**`, `db/**`, the composition root, global styles, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, `PRODUCTION-READINESS-PLAN-01.md`, `OWNER_RULINGS_*`, the ADRs.

## Non-goals

- No live call, no credential read, no spend: the live run and the lock are the integrator's (`R-146af`).
- No change to `ProxySettings.model_aliases` or any alias list (`AD-13`); no change to `src/**`.
- No edit of `tools/provider/identity_probe.py` (W56a), which stays as it is.
- No `anthropic_messages` flavour: OpenRouter, the base connection (`R-146e`), is `openai_chat`.
- No writing of `P02_LOCK.json`: the tool states `lock_candidate: yes|no`; the integrator writes the lock from the report.

## Deliverables

- `scripts/model_probe/probe.py`: the tool (`python3 -m scripts.model_probe.probe`, from the repository root with `PYTHONPATH=src`).
- `tests/unit/scripts/test_model_probe.py`: 53 cases with a stub transport.
- Report `docs/program/PROD-13A-MODEL-IDENTITY-PROBE-TOOL-01.md`, with the operator procedure for the live run.

## Required tests

- `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/scripts/test_model_probe.py` — expected: 53 passed.
- Docs guards: `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`, and `git diff --check`.
- Mutations: 41 edits of the tool, each shown red and restored (table in the report).

## Integration contract

The integrator can rely on: the tool exits 2 before any call (and creates no report) without `--confirm-paid`, without `PROXY_LLM_BASE_URL` and `PROXY_LLM_TOKEN` in the process environment, with a ceiling above 5.00 or not positive, with a probed model lacking an explicit non-placeholder `--slug`, or with a report path that exists; it exits 0 only when every probed model answered with exactly the requested name; the report holds one `requested_slug:` and one `reported_model:` line per probed model (`none` for a model not called) and never the credential; the lock is read and never written; `lock_candidate: yes` appears only when every model the lock pins was probed, matched exactly and had its reported cost within 20 % of the lock's rates (the tolerance of `executors/identity.py`). Nothing outside the four allowed paths changed.

## Failure/idempotency/security cases

A mismatch (another name, an alias, a case-folded or prefixed name, no name, a placeholder) is exit 1 and does not stop the other models. A reply over the ceiling, or a call that could pass it, is exit 3. A refused credential, a gateway error and an unexpected exception are a `no_verdict` block, counted at zero or at the worst case (`outcome_unknown` may have been billed), never retried. The credential value is redacted from the report, the console and the log records of the run (exit 5 if it was there). The report is created exclusively with mode 0600 and rewritten after each model, so an interrupt keeps the evidence. A re-run uses a new idempotency scope, so it is a fresh paid call, not a gateway replay.

## Rollback / feature flag

Forward-revert. Nothing else calls the tool, so there is no behaviour to flag.

## Handoff

- changed files: the tool, its test, this task file and the report
- commands/results: see the report
- known limits: see the report (the live behaviour of a real gateway is untested; `gpt-6-sol` may not be served by OpenRouter; the tool depends on one private adapter slot)
- integration notes: merge any time; no dependency on another `PROD-*` item; the live run follows `R-146af`
