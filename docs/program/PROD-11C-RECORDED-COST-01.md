# PROD-11C-RECORDED-COST-01 — the recorded replay of an AR v3 beta Run is unmetered, and nothing else is

Task: `docs/program/tasks/PROD-11C-RECORDED-COST-01.md`. Branch `agent/prod-11c-recorded-cost-01`, base `2aec4207` (`integration/ar-close-1026`). Debt `D-225` piece 2 (found by `PROD-11a`, `PROD-11A-V3-TEXT-LAYER-PROBE-01.md` missing piece 2). Wave `PW3`, lane C. Rulings that bind: `R-29`, `ADR-0011`.

## Result

The stock recorded composition no longer ends every recorded AR v3 Run `failed / analysis_input_invalid` after its provider call. `_build_provider` (recorded branch) now gives `EnvironmentProviders` a second binding, `ar_v3_replay_call=CallBinding(unmetered=True)`, which `resolve` returns **only** for a Run whose `analysis_profile_id` and `prompt_bundle_id` are the exact sealed AR v3 beta pair (`AR_V3_BETA_PROFILE_ID`, `AR_V3_BETA_BUNDLE_ID`). The call is journalled `recorded / unmetered / 0`, the worker's cost check passes it as an explicit `unmetered`, the CITE row is written and the Run is `published`. In the probe the six Runs of the group driven through the **stock composition** publish and the specification readers answer `ready`.

The cost safety did not move, and the lane proves it three ways:

- **Nothing else can say "charges nothing".** `EnvironmentProviders.__init__` refuses (`ValueError`) a replay binding for any adapter whose `provider_mode` is not `RECORDED` (proxy, live, unbound, a stood-in live-mode adapter, an adapter without a mode, no adapter: six variants) and refuses one that is not itself `unmetered`. The live and proxy branches of `_build_provider` pass none, and their bindings are `unmetered = False` for every Run, the sealed pair included (a table over four Run kinds and three compositions).
- **A live-mode call without a cost amount is still refused, on a real database.** The probe's third group drives the **stock live composition** (its `CallBinding`, its pinned model, a stood-in LIVE adapter that answers with usage and no cost) through `run_to_terminal`: six of six `failed / analysis_input_invalid` ("no verifiable cost amount"), no CITE row, each call row `live / estimated / no amount`, the readers `analysis_missing`.
- **The old shape is still refused.** A recorded replay that is not marked (the hand-built `EnvironmentProviders(adapter, config, None)`) is kept as a control and still fails six of six the same way.

## Decision (taken by the lane; reasoning in the task file, P-03 and P-04)

**Option (a)**, mark the recorded binding unmetered in the composition root, scoped to the sealed v3 pair. Not (b): the recording format has no cost field (`RecordedAdapter.complete` builds a `ModelResponse` without `reported_cost_usd`), so a cost would mean changing `analysis/text/recorded.py` and the 20 committed recordings (outside the allowed paths), the number would be invented and enter the ledger as `measured`, and it would route the recorded kind through the very channel a live reply uses to pass the cost check. The scope to the v3 pair rather than every recorded call comes from P-03: the v1 text stage reads the same `unmetered` flag and would stop pricing recorded v1 Runs (estimated to unmetered), changing every recorded cost report and the characterisation corpora.

## Files (`git diff --name-only 2aec4207..HEAD`)

```text
src/auditmanager/bootstrap/composition.py                         recorded branch of _build_provider: builds the replay binding (+10 lines)
src/auditmanager/bootstrap/providers.py                           EnvironmentProviders: ar_v3_replay_call, the two construction guards, the exact-pair test
tests/integration/runs/test_v3_recorded_cost_binding.py           new, 26 tests, container-free
tests/integration/runs/test_v3_saved_text_layer_probe.py          facts 2 to 7 rewritten or extended (13 tests -> 18)
docs/program/tasks/PROD-11C-RECORDED-COST-01.md                   this lane
docs/program/PROD-11C-RECORDED-COST-01.md                         this report
```

## New tests (`test_v3_recorded_cost_binding.py`, 26)

| Test | Claim |
| --- | --- |
| `test_the_recorded_composition_marks_the_replay_unmetered_for_the_sealed_v3_pair` | recorded process, sealed pair: `call.unmetered` is true, label `anthropic`, no connection revision |
| `test_a_recorded_run_that_is_not_the_exact_v3_pair_keeps_the_binding_it_always_had` (3) | v1 pair, v3 profile with another bundle, another profile with the v3 bundle: `call is None` |
| `test_no_other_composition_builds_an_unmetered_binding_for_any_run` (12) | proxy and live: `CallBinding`, `unmetered` false, identity checked and pinned, for each of four Run kinds; api role: `call is None` |
| `test_the_live_and_the_proxy_adapters_are_not_recorded_replays` | the premise of the guard: those compositions build `LIVE`-mode adapters |
| `test_a_binding_that_charges_nothing_is_refused_for_an_adapter_that_is_not_a_recorded_replay` (6) | construction refuses proxy / live / unbound / any live-mode / modeless / no adapter |
| `test_the_replay_binding_must_itself_be_unmetered_and_a_recorded_adapter_accepts_it` | a replay binding that is not `unmetered` is refused; a recorded adapter accepts one; v3 pair marked, v1 not |
| `test_a_source_built_without_the_replay_binding_marks_nothing` | the default is the old behaviour for every Run kind |
| `test_a_run_that_froze_a_connection_is_still_refused_whatever_its_profile` | the route check stays first (`dependency_unavailable`) |

## Mutation table (each applied alone to the committed tree, tests run, then `git checkout`; `git status --short` empty after every one)

Command per row: the lane prefix with the files named; `N` = `test_v3_recorded_cost_binding.py` (26), `P` = the probe (18), `W` = `test_v3_worker_pipeline.py`. Baseline: `N` 26 passed, `P` 18 passed.

| Mutation | Files run | Result | Red |
| --- | --- | --- | --- |
| M1 `composition.py`: recorded branch builds no replay binding | N, P | 6 failed, 38 passed | `N` marks-the-replay; probe facts 2 (served), 3, 4, 5, 7b |
| M2 `composition.py`: live `CallBinding(..., unmetered=True)` | N, P | 8 failed, 36 passed | `N` no-other-composition (live, 4 Run kinds); probe facts 2, 3b, 5, 7a (live control) |
| M3 `composition.py`: proxy `CallBinding(..., unmetered=True)` | N | 4 failed, 22 passed | `N` no-other-composition (proxy, 4 Run kinds) |
| M4 `providers.py`: the recorded-adapter guard never refuses | N | 6 failed, 20 passed | all six adapter variants |
| M5 `providers.py`: the explicitly-unmetered check is gone | N | 1 failed, 25 passed | replay-binding-must-itself-be-unmetered |
| M6 `providers.py`: every Run is taken for the sealed pair | N | 4 failed, 22 passed | three non-pair Run kinds, v1 not marked |
| M7 `providers.py`: either half of the pair is enough | N | 2 failed, 24 passed | the two half-pair Run kinds |
| M8 `providers.py`: the replay binding is served before the route check | N | 1 failed, 25 passed | froze-a-connection |
| M9 `v3_worker.py`: a call with no cost amount passes `_check_completed_cost` | P, W | 4 failed, 25 passed | probe 3b (recorded control and live control), 5; `test_unknown_metered_cost_cannot_publish` |
| M10 probe instrument: the live group's binding is given `unmetered=True` | P | 3 failed, 15 passed | facts 2 (live), 3b (live), 5 |
| M11 probe instrument: the metered control uses the stock composition | P | 4 failed, 14 passed | facts 2, 3b (recorded), 5, 7a (recorded) |
| P1 fact 3 asserts the served call row is `estimated`, no amount | P | 1 failed, 17 passed | fact 3 |
| P2 fact 3b asserts the refusal message is absent | P | 2 failed, 16 passed | fact 3b (both controls) |
| P3 fact 3b asserts the refused call row is `unmetered`, zero | P | 2 failed, 16 passed | fact 3b (both controls) |
| P4 fact 5 asserts eighteen published | P | 1 failed, 17 passed | fact 5 |
| P5 fact 7b asserts the readers answer `analysis_missing` | P | 1 failed, 17 passed | fact 7b |
| P6 fact 2 asserts five requests | P | 3 failed, 15 passed | fact 2 (three groups) |
| restored | N, P | 26 passed; 18 passed | |

The first run of P1 hit `Connection refused` on the lane PostgreSQL port (1 passed, 17 errors) for a few seconds: the lane stack was momentarily unreachable. No docker command was issued by the lane; the other rows ran before and after it with proper assertion failures and P1 was repeated (row above). Noted for the integrator.

## Before and after of every modified test (`test_v3_saved_text_layer_probe.py`, 13 tests to 18)

| Before | Asserted before | After | Asserts after |
| --- | --- | --- | --- |
| `test_the_migrated_schema_admits_the_cite_stage` | nine ids plus CITE | unchanged | unchanged |
| `test_every_provider_request_was_answered_and_the_stage_rows_are_those_the_cost_seam_allows` x2 (served, hand-built unmetered) | six requests; stage rows = three deterministic (cost-refused group) or three plus CITE (unmetered group) | x3 (served = stock composition, recorded control, live control) | six requests; three plus CITE for the served group, three for each control |
| `test_the_served_recorded_composition_refuses_every_run_on_cost` | served group (hand-built `call=None`): `failed / analysis_input_invalid`, message names the missing cost | **rewritten**: `test_the_served_recorded_composition_journals_every_replayed_call_as_unmetered` | served group (stock composition): each Run has exactly one call row `("recorded", "unmetered", 0, "succeeded")` and no error. The refusal assertion lives on, stronger, in the next row |
| (none) | | **new**: `test_a_call_without_a_cost_amount_that_is_not_marked_unmetered_is_still_refused_on_cost` x2 | recorded control and live control: `failed / analysis_input_invalid`, message names the missing amount, no CITE stage row, one call row `(mode, "estimated", None, "succeeded")` (never `unmetered`, never zero) |
| `test_an_unmetered_call_publishes_every_run_with_a_succeeded_cite_row` | the hand-built unmetered group: `published`, CITE `succeeded`, review artifact bound | same name | the **served stock-composition** group: same assertions |
| `test_the_outcome_of_the_twelve_runs_is_decided_by_the_cost_seam_alone` | six `failed / analysis_input_invalid` then six `published` | `test_the_outcome_of_the_eighteen_runs_is_decided_by_the_cost_seam_alone` | six `published`, then twelve `failed / analysis_input_invalid` (the order of the groups changed with their roles) |
| `test_every_v3_run_leaves_the_saved_text_layer_whatever_its_terminal` x2 | layer saved and returned, digest equals the stage reference | x3 | same assertions on the three groups |
| `test_the_readers_find_no_published_run_of_the_cost_refused_group` | served group: `None` / `analysis_missing` | `..._of_a_cost_refused_group` x2 | same assertions on the recorded control and the live control |
| `test_the_readers_answer_ready_on_the_published_group` | hand-built unmetered group: newest published is one of six, `ready`, layer equal | same name | the served stock-composition group: same assertions |
| v1 control, loopback, guards | unchanged | unchanged | unchanged |

Instrument changes (not assertions): `RunReading` gained `model_calls` (`provider_mode, cost_basis, cost_micros, status` of every `text_analysis` call row of the Run); `_drive_group` builds the served and live providers from `_build_provider` (only the adapter and, for the recorded group, the configuration are swapped; the `call` is the composition's own); the hand-built `_unmetered` stand-in and the `CallBinding` import are gone (the served group is now the unmetered one); `_drive` publishes two more versions over the same bytes and starts the live group with `provider_mode="live"`. No test was weakened: every refusal the module asserted before is still asserted (on the controls) and the live mode is new.

## Commands and results (lane stack, one pytest at a time, no docker, no process killed)

| Command (prefix `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider`) | Result |
| --- | --- |
| `tests/integration/runs/test_v3_saved_text_layer_probe.py` on the base tree (before) | 13 passed, 7.78 s |
| `tests/integration/runs/test_v3_recorded_cost_binding.py` | 26 passed, 2 s |
| `tests/integration/runs/test_v3_saved_text_layer_probe.py` | 18 passed, 22.69 s |
| `tests/unit/executors/test_provider_source_settings.py test_explicit_executor.py test_probe_loop.py`, `tests/integration/runs/test_v3_provider_call.py test_v3_worker_pipeline.py test_v3_cost_refusal.py`, `tests/integration/composition/test_composition_root.py test_v3_pack_install.py`, `tests/integration/analysis_text/test_proxy_truncation_reaches_partial.py`, `tests/integration/releases/test_startup.py` | 122 passed, 19 s |
| `tests/integration/executors/test_http_run_path.py test_pull_run_path.py test_agent_e2e.py test_http_sentinel.py test_explicit_executor.py`, `tests/integration/composition/test_the_served_application_routes_by_section.py test_the_served_application_always_passes_a_budget.py` | 58 passed, 81 s |
| `tests/contract/architecture tests/unit/executors tests/unit/runs/test_run_status_executor.py` | 480 passed, 56 s |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` (clean committed tree) | 105 passed, 49 s |
| governance one-liner on the task file | `[]` |
| `git diff --check 2aec4207..HEAD` | exit 0 |

Free disk stayed between 1.9 and 2.4 GiB (above the 1.3 GiB line of `D-205`); the probe drops its throw-away database each run. No full gate and no whole `tests/integration` (`R-135`), no browser, no network.

## Integration notes (for the integrator)

1. Merge with `--no-ff`. Check: `rg -n "ar_v3_replay_call" src` finds the class (`bootstrap/providers.py`) and the one use (`bootstrap/composition.py`, recorded branch); the probe prints six `published` with one `recorded / unmetered / 0` call row for the stock-composition group and `failed / analysis_input_invalid` for both controls.
2. Record `D-225` piece 2 closed in the register (the lane may not edit it). Documents that still call it open and are the integrator's to touch: the `D-225` row of `DEBT_REGISTER.md`, integration note 2 of `PROD-11A-V3-TEXT-LAYER-PROBE-01.md`, the «Piece 2 stays open» sentence of `PROD-11B-V3-STAGE-ID-MIGRATION-01.md`, and the Lane C line of `dispatch/PRODUCTION-WAVE-PW3.md`.
3. `AR-V3-BETA-ACCEPT-01`'s recorded positive cases can now run on the stock recorded composition; the probe's `_drive_group` with `binding=SERVED_RECORDED` is a ready driver for them.
4. A change under `bootstrap/**` is a named case for a complete gate in `AGENTS.md` section 8 (timing under `R-135`): not run here. The behaviour change is confined to a recorded process and the sealed v3 pair; a live, proxy, `database`-source or v1 recorded process builds the same bindings as before (the first three tables above).
5. Cost reports for recorded v3 Runs will now show basis `unmetered` (the call row stores zero; the published figure follows `CostBasis.UNMETERED`, «absent, never a zero»; the schema admits the basis since `0030`). Before this change those Runs failed, so no existing report changes.
6. The lane stack was unreachable for a few seconds once (see the mutation table); no cause on the lane's side.

## Limits

- The live control stands in for the provider: the real `LiveAdapter` is constructed offline from a placeholder key and then replaced, the adapter that answers is a local stub, and the suite's `_no_network` refuses sockets. The real provider's answer shape, and a proxy that reports a cost, are not measured here.
- The cost check still sits **after** the provider call, as `AR-V3-BETA-COST-REFUSAL-01` built it: a live call whose reply states no amount is paid for and then refused. This lane keeps that, it does not move it before the call.
- The mark is by the exact sealed pair. A future AR v3 variant with another profile or bundle id gets no mark until the composition names it (a refusal, not a silent pass).
- The `database` source (live only) and its `not_metered` connections are a separate declared route and were not touched or re-measured.
- The proxy composition is covered by the binding table only (no database group); the cost check it meets is the same one the live group exercises.
- The group was driven through `run_to_terminal` (the worker entry point), not through HTTP; the group-review read model and the web screens were not read.

## Forbidden paths untouched

```text
$ git diff --name-only 2aec4207..HEAD
docs/program/PROD-11C-RECORDED-COST-01.md
docs/program/tasks/PROD-11C-RECORDED-COST-01.md
src/auditmanager/bootstrap/composition.py
src/auditmanager/bootstrap/providers.py
tests/integration/runs/test_v3_recorded_cost_binding.py
tests/integration/runs/test_v3_saved_text_layer_probe.py
```

`contracts/**`, `db/migrations/**`, `infra/**`, `web/**`, root dependency and lock files, `runs/v3_worker.py` (the cost check), `runs/v3_provider_call.py`, `analysis/text/**`, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings and the ADRs are untouched. Of the composition root only the recorded branch of `_build_provider` and the `EnvironmentProviders` class moved.
