# Task PROD-11C-RECORDED-COST-01 — the recorded replay of an AR v3 beta Run is unmetered, and nothing else is

task_id: PROD-11C-RECORDED-COST-01
status: completed in development candidate (see the report)

## Outcome

Piece 2 of `D-225` is closed. In recorded mode the stock composition (`bootstrap/composition.py`, `_build_provider`) handed every Run `EnvironmentProviders(RecordedAdapter, config, call=None)`; a replayed reply carries no cost amount and the call was not marked unmetered, so the AR v3 worker (`_check_completed_cost`) ended every recorded v3 Run `failed / analysis_input_invalid` ("a metered AR v3 call has no verifiable cost amount") **after** the provider call. The recorded composition now hands the exact sealed AR v3 beta pair (`AR_V3_BETA_PROFILE_ID` and `AR_V3_BETA_BUNDLE_ID`) a call binding that marks the replay `unmetered`; every other Run keeps the binding it had, the live and the proxy compositions build no such binding, and `EnvironmentProviders` refuses at construction to carry one for an adapter that is not a recorded replay. The recorded v3 group of the probe `tests/integration/runs/test_v3_saved_text_layer_probe.py` publishes six of six through the stock composition; a live-mode call whose reply states no cost is still refused, on a real database.

## Depends on

- `PROD-11A-V3-TEXT-LAYER-PROBE-01` — completed (the evidence, `D-222`, `D-225`).
- `PROD-11B-V3-STAGE-ID-MIGRATION-01` — completed (migration `0033`; without it the CITE row is refused by the database and the group cannot publish whatever the cost seam says).
- `AR-V3-BETA-COST-REFUSAL-01` — completed (the cost check this lane leaves untouched).

## Frozen inputs

- domain contract: not_applicable
- API contract: unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable
- migration head: `0033_ar_v3_cite_stage_id`, unchanged
- base commit: `2aec4207` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the finding of `PROD-11A` (and the PW3 dispatch) says the v3 cost check refuses the recorded binding because the stock composition passes `call=None` and a replay has no amount. Re-read at the base commit: the check is `_check_completed_cost` in `runs/v3_worker.py`; the recorded branch of `_build_provider` builds `call = None`; the flag that satisfies the check is `CallBinding.unmetered`, read by `dispatch_v3_provider_call`; the recording format has no cost field; the baseline probe measures six of six `failed / analysis_input_invalid` for the stock-shaped group. The premise matches; nothing differs.

### P-01 — where the v3 cost check lives

- captured_at: 2026-10-26
- command: `git grep -n "verifiable cost" 2aec4207 -- src; git show 2aec4207:src/auditmanager/runs/v3_worker.py | sed -n 58,76p`
- captured_output:
  ```text
  2aec4207:src/auditmanager/runs/v3_worker.py:67:            message="a metered AR v3 call has no verifiable cost amount",

  def _check_completed_cost(call: object, ceiling_usd: float) -> None:
      basis = getattr(call, "cost_basis", None)
      micros = getattr(call, "cost_micros", None)
      if basis == "unmetered" and micros == 0:
          return
      if basis not in {"measured", "estimated"} or type(micros) is not int or micros < 0:
          raise DomainError(
              ErrorCode.ANALYSIS_INPUT_INVALID,
              message="a metered AR v3 call has no verifiable cost amount",
              stage_id="text_analysis", reason="v3_metered_cost_unknown",
          )
      if micros > ceiling_usd * 1_000_000:
          raise _budget_exceeded()
  ```
- interpretation: one place, run after the provider call and before the CITE stage, reading the completed call row (`cost_basis`, `cost_micros`). It admits an amount (`measured` or `estimated` with an integer) and an explicit `unmetered` with zero; everything else is refused. It is not edited by this lane. `tests/integration/runs/test_v3_worker_pipeline.py::test_unknown_metered_cost_cannot_publish` already pins that a row with no amount is refused.

### P-02 — how the recorded and the live bindings are built (`bootstrap/**`)

- captured_at: 2026-10-26
- command: `git show 2aec4207:src/auditmanager/bootstrap/composition.py | sed -n 546,568p; git show 2aec4207:src/auditmanager/bootstrap/providers.py | sed -n 82,95p`
- captured_output:
  ```text
          call = CallBinding(expected_model=settings.proxy_model, check_identity=True)   # proxy branch
      elif settings.provider_mode == "live":
          if settings.api_key is None:  # pragma: no cover - settings.load refuses first
              raise ConfigurationError("live mode requires a credential")
          adapter = LiveAdapter(api_key=settings.api_key)
          call = CallBinding(expected_model=config.model_id, check_identity=True)
      else:
          adapter = RecordedAdapter()
          call = None
      return (
          adapter, config, identity[0], identity[1],
          EnvironmentProviders(adapter, config, call),
      )

  class EnvironmentProviders(ProviderSource):
      def __init__(self, adapter: Any, config: Any, call: CallBinding | None = None) -> None:
          self._binding = ProviderBinding(adapter=adapter, config=config, call=call)
          self.freeze = None

      def resolve(self, session: Session, run: Any, context: Any) -> ProviderBinding:
          if getattr(run, "connection_revision_id", None) is not None:
              ...
              raise route_missing()
          return self._binding
  ```
- interpretation: one binding for every run of the process. The live and proxy branches pin the reply's model (`check_identity`) and leave `unmetered` false; the recorded branch has no call binding at all. The neighbour this lane edits is `src/auditmanager/bootstrap/composition.py` (the recorded branch of `_build_provider`, nine lines) and `src/auditmanager/bootstrap/providers.py` (the class `EnvironmentProviders`); nothing else of the composition root moves. The resolver receives the `run`, which carries `analysis_profile_id` and `prompt_bundle_id` (the executor reads the same two to decide `v3_exact`).

### P-03 — what the `unmetered` flag does, and where else it is read

- captured_at: 2026-10-26
- command: `git grep -n "unmetered" 2aec4207 -- src/auditmanager/runs/v3_provider_call.py src/auditmanager/analysis/text/stage.py src/auditmanager/bootstrap/providers.py src/auditmanager/runs/executor.py`
- captured_output:
  ```text
  src/auditmanager/analysis/text/stage.py:410:    unmetered = call is not None and call.unmetered
  src/auditmanager/analysis/text/stage.py:416:        cost_meter.record_unmetered() if unmetered else cost_meter.charge(
  src/auditmanager/analysis/text/stage.py:479:            "unmetered" if unmetered
  src/auditmanager/bootstrap/providers.py:164:            check_identity=True, unmetered=settings.billing == "not_metered",
  src/auditmanager/runs/executor.py:856:        if prior_cost.basis == "unmetered":
  src/auditmanager/runs/executor.py:859:            meter.unmetered_calls = prior_cost.model_call_count
  src/auditmanager/runs/v3_provider_call.py:284:    unmetered = call is not None and call.unmetered
  src/auditmanager/runs/v3_provider_call.py:285:    cost_usd = 0.0 if unmetered else reported
  src/auditmanager/runs/v3_provider_call.py:286:    basis = "unmetered" if unmetered else "measured" if reported is not None else "estimated"
  ```
- interpretation: the flag is read by two stages. The v3 call (`v3_provider_call.py`) records `cost_basis = unmetered`, cost 0 when it is set, `measured` when the reply states an amount and `estimated` with no amount otherwise (which the cost check then refuses). The **v1 text stage** (`stage.py:410`) also reads it: an unmetered call is charged nothing instead of the pin estimate. So a flag set on every recorded call would change the cost basis of every recorded v1 Run (estimated to unmetered) and with it the cost reports and the characterisation corpora. The flag is already produced by one declared live route: the `database` source's `billing = not_metered` connections (`providers.py:164`), which this lane does not touch.

### P-04 — the recording format has no cost

- captured_at: 2026-10-26
- command: `git show 2aec4207:src/auditmanager/analysis/text/recorded.py | sed -n 106,137p | grep -n "cost\|usage\|latency"; git show 2aec4207:src/auditmanager/analysis/text/recorded.py | sed -n 218,225p; find fixtures/recorded -name '*.json' | wc -l`
- captured_output:
  ```text
  8:    latency_ms: int,
  24:        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
  25:        "latency_ms": latency_ms,
              return ModelResponse(
                  output_text=str(document["output_text"]),
                  stop_reason=str(document["stop_reason"]),
                  input_tokens=int(usage["input_tokens"]),
                  output_tokens=int(usage["output_tokens"]),
                  latency_ms=int(document["latency_ms"]),
              )
  20
  ```
- interpretation: a recording is `request_sha256`, `model_id`, `stop_reason`, `output_text`, `usage` (tokens), `latency_ms`, `note`, `origin`; `RecordedAdapter.complete` builds a `ModelResponse` with no `reported_cost_usd`. Giving the recordings a cost would change the recording format (`src/auditmanager/analysis/text/recorded.py`, outside this lane), rewrite the 20 committed recordings under `fixtures/recorded` (and `build_fixtures.py`, which writes the section ones), and put an invented number into the ledger under the basis `measured`.

### P-05 — the probe's cost facts, and the baseline run before any change

- captured_at: 2026-10-26
- command: `git show 2aec4207:tests/integration/runs/test_v3_saved_text_layer_probe.py | sed -n 748,754p`; then the module on the base tree with `-s` (command in the report), the `PROD11A-MEASUREMENT` line summarised per group by a three-line script
- captured_output:
  ```text
  def test_the_served_recorded_composition_refuses_every_run_on_cost(measured: Measurement) -> None:   # docstring omitted
      for run in measured.groups[SERVED_RECORDED].runs:
          assert (run.state, run.terminal_reason) == ("failed", "analysis_input_invalid")
          assert run.error is not None and "no verifiable cost amount" in run.error
  13 passed in 7.78s
  recorded replay, call marked unmetered: requests=6 runs=6 outcome=[('published', None)] newest_published=run_01M5WE3S38PE120B8RGTREXNBT source_state=ready errors=['']
  served recorded composition: requests=6 runs=6 outcome=[('failed', 'analysis_input_invalid')] newest_published=None source_state=analysis_missing errors=['DomainError: a metered AR v3 call has no verifiable cost amount <- None']
  ```
- interpretation: the finding holds at the base: the stock-shaped group is refused six of six on cost after the provider call, and a binding marked unmetered publishes six of six (on migration `0033`). The probe builds the "served" binding by hand (`EnvironmentProviders(adapter, config, None)`), so it never ran the composition code; this lane makes it build the binding from `_build_provider`.

### P-06 — ADR-0011 and `R-29`

- captured_at: 2026-10-26
- command: `sed -n 6p docs/architecture/adr/ADR-0011-llm-reproducibility-and-cost.md; sed -n 622,629p docs/program/OWNER_RULINGS_2026-09-17.md`
- captured_output:
  ```text
  Published runs reference immutable AnalysisProfile, PromptBundle and NormsSnapshot. Every provider call creates ModelCallRecord with model/provider/params, request/response checksums, provider ID when available, token usage, latency, status and measured/estimated cost. Replay tests use recorded synthetic/anonymized responses; live quality is evaluated semantically.
  ### `R-29` — autonomy: everything except security decisions and spending

  **Ruled.** The integrator runs waves without asking: contract reseals, migrations, screens,
  guards, advancing `origin/main`, tagging. **It stops at two things:**

  1. **spending above roughly $5 in a wave**, and
  2. **anything that changes who can reach the system, or exposes something that was not
     exposed** — a port binding, a credential's reach, a default account, a published surface.
  ```
- interpretation: ADR-0011 says the ledger holds the measured or estimated cost of a call that happened; `R-29` makes spending a stop. A recorded replay spends nothing, which the ledger already has a basis for (`unmetered`, zero, admitted by `ck_model_call_cost_basis` since migration `0030`); a live call must keep reporting its own amount, and the cost check is the only fence that notices when it does not.

## Decision (taken by the lane; the owner asked for no questions)

- decided by the lane: **option (a)**, mark the recorded provider binding explicitly unmetered in the composition root. Why not (b): the recording format has no cost field and a recording's reply would have to carry an amount (P-04): that is a change to `analysis/text/recorded.py` and to the 20 committed recordings, outside the allowed paths; the amount would be invented and enter the ledger as `measured`, the basis the live path earns by really paying; and it would put the recorded kind through the very channel a live reply uses to pass the cost check, so a wrong or copied number would be indistinguishable from a real one. (a) says what is true (nothing was spent), uses the basis the ledger already has for it, and cannot be reached by a live adapter.
- decided by the lane: the mark is scoped to **the exact sealed AR v3 beta pair** (profile and bundle both) and not to every recorded call (P-03: the v1 stage reads the same flag and would stop pricing recorded v1 Runs). A half-matching pair is refused by the executor before any call and gets no mark.
- decided by the lane: the guard sits in `EnvironmentProviders.__init__` (a `ValueError` at start-up, not a settings option): a replay binding is accepted only with an adapter whose `provider_mode` is `RECORDED`, and only if itself `unmetered`. No setting turns the mark on; the live and proxy branches of `_build_provider` do not pass one.
- decided by the lane: in the probe, the old hand-built group is kept as a **control** ("recorded replay, call not marked unmetered"), the stock composition becomes the served group, and a third group drives a **live-mode** call (stock live composition, a stood-in LIVE adapter that answers with usage and no cost) to show the refusal on a real database. The old hand-built `_unmetered` stand-in is removed (the served group is now the unmetered one).
- decided by the lane: the new binding tests are container-free and sit in `tests/integration/runs/test_v3_recorded_cost_binding.py` beside the other v3 cost tests; the live end-to-end proof stays in the probe module because it owns the seeded pack and the throw-away database.
- decided by the lane: a placeholder string builds the stock live composition offline (`placeholder-not-a-credential`); the real adapter is replaced before any request exists and the suite's autouse `_no_network` refuses sockets.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/bootstrap/composition.py`
- `src/auditmanager/bootstrap/providers.py`
- `tests/integration/runs/test_v3_recorded_cost_binding.py`
- `tests/integration/runs/test_v3_saved_text_layer_probe.py`
- `docs/program/tasks/PROD-11C-RECORDED-COST-01.md`
- `docs/program/PROD-11C-RECORDED-COST-01.md`

## Lane resources

- foundation_instance: the integrator's lane stack (`ar-close-1026`), not stopped, reset or written to by this lane
- postgres_db: one throw-away database per run of the probe (`prod11a_probe_*`), created and dropped by its fixture
- s3_bucket: the lane bucket, used by the probe only (content-addressed objects)

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, `infra/**`, `web/**`, root dependency/lock files, global styles
- every other file of the composition root and of `src/**`, in particular `runs/v3_worker.py` (the cost check), `runs/v3_provider_call.py`, `analysis/text/**`
- any live-mode behaviour change
- documents other than the two deliverables, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs

## Non-goals
- No change to the cost check itself, to the recordings, to the recording format or to the v1 cost estimate.
- No refusal before the provider call: the v3 cost check still runs after the call (a live call without an amount is paid and then refused; that ordering is `AR-V3-BETA-COST-REFUSAL-01`'s and is not moved here).
- No activation of the group (`PROD-12`).

## Deliverables
- the two bootstrap edits, the new container-free test module, the rewritten probe
- this task file and `docs/program/PROD-11C-RECORDED-COST-01.md` (premise, decision, mutation table, before/after of modified tests, commands with counts, integration notes)

## Required tests
- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/runs/test_v3_recorded_cost_binding.py tests/integration/runs/test_v3_saved_text_layer_probe.py`
- expected: `26 passed` and `18 passed` (counts in the report)

## Integration contract

The integrator merges with `--no-ff`. After the merge: `rg -n "ar_v3_replay_call" src` finds the one use in `composition.py` (recorded branch) and the class in `providers.py`; the probe shows the stock-composition group `published` six of six with one `recorded / unmetered / 0` call row per Run, and the two controls `failed / analysis_input_invalid`. `D-225` piece 2 can be recorded closed (the register row is the integrator's). A change under `bootstrap/**` is one of the named cases for a complete gate in `AGENTS.md` section 8 (timing under the `R-135` override): this lane ran the bounded tests named in the report, not the gate. Behaviour changes only for a recorded process, and only for the sealed AR v3 beta pair; a live, proxy, `database`-source or v1 recorded process builds the same bindings as before.

## Failure/idempotency/security cases
- a live or proxy call with no cost amount: still `failed / analysis_input_invalid`, call row `estimated` with no amount (probe, live control; mutation M9 shows it goes red when the cost check is loosened)
- a live-mode adapter handed a replay binding: refused at construction (six variants)
- a replay binding that is not `unmetered`: refused at construction
- a v1 Run, or a Run with only one half of the sealed pair, in a recorded process: no call binding, as before
- a Run that froze a connection revision: still refused by the route check, before the replay binding is considered
- a resumed Attempt of a recorded v3 Run: the call row already says `unmetered`, which the check accepts (`test_explicit_unmetered_call_may_publish`)

## Rollback / feature flag
No flag. Rollback is reverting the lane: the recorded v3 beta group then fails on cost again, as before. Nothing is stored that depends on the change except call rows with basis `unmetered` and cost zero for recorded v3 calls, a basis the schema has admitted since `0030`.

## Handoff

- changed files: see the report
- commands/results: see the report
- known limits: see the report
- integration notes: see the report
