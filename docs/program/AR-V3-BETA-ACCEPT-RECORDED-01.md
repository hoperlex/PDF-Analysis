# AR-V3-BETA-ACCEPT-RECORDED-01 — the recorded AR v3 beta group, over HTTP

Task: `docs/program/tasks/AR-V3-BETA-ACCEPT-RECORDED-01.md`. Branch `agent/ar-v3-beta-accept-recorded-01`, base `b0644fd3` (`integration/ar-close-1026`). Wave `PW3`, lane A3; the recorded half of `AR-V3-BETA-ACCEPT-01` (the live half needs the activation data, `D-204`). One new test module and the two documents: nothing under `src/`, `contracts/`, `db/`, `infra/` or `web/` changed.

## Result

`tests/integration/runs/test_v3_recorded_group_over_http.py` (55 tests) drives the group the way a reviewer does, on a private migrated database: the sealed synthetic pack is installed by the composition root from a manifest file (`AR_V3_BETA_PACK_MANIFEST`), the application is the stock recorded one (`build_application`, only the model answer is the probe's record-on-first-sight replay), the accounts are real rows, the transport is the real ASGI application, and the six Runs are carried to `published` on the application's own `DurableCarrier`. All of it passes, and every asserted fact has been shown red under a quoted mutation (below).

## A finding the integrator has to read: a served process does not carry the group

`startArV3BetaGroup` creates the group and six Runs in state `created`, and **no Job**: `runs/v3_group.py` says «No Job or provider call is made here», and `RunAdapter.start_ar_v3_group` does not queue the Runs, enqueue a Job or submit to the carrier (unlike `start_run`). The serving carrier's poller finds work with `JobRepository.next_queued_run`, which needs a `queued` Job of a `queued` or `running` Run, and the startup reconciliation touches only `running` Runs. So in a served process the six Runs stay `created` and the group review reads six `pending` for ever; the web hook's comment («six queued Runs, six new queued jobs») describes the intent, not the fact. Measured right after the HTTP start on the real schema: six `created`, `job` rows 0, `next_queued_run()` returns `None`.

Nothing in the probe could see this (it calls `run_to_terminal` itself), and the premise of `PROD-12` («Запустить шесть проверок АР v3» works once the pack is installed) depends on it. This lane may not touch `src/**` or the register, so it (1) carries the Runs through the one product seam that takes an already-accepted Run in-process, `RunAdapter.submit_existing` -> `carrier.submit(RunAdapter._job)` -> `run_to_terminal`, and (2) pins the gap as fact 5 with a docstring that says what to flip when the product queues the Runs (mutation M10 shows the fact goes red when it does). A candidate debt row for the integrator: «the AR v3 group start leaves its six Runs `created` with no Job; no served process executes them»; the check is `pytest -q tests/integration/runs/test_v3_recorded_group_over_http.py -k unqueued`.

## Files (`git diff --name-only b0644fd3..HEAD`)

```text
docs/program/AR-V3-BETA-ACCEPT-RECORDED-01.md
docs/program/tasks/AR-V3-BETA-ACCEPT-RECORDED-01.md
tests/integration/runs/test_v3_recorded_group_over_http.py        new, 55 tests
```

## How the module works

- **Reuse.** The probe `test_v3_saved_text_layer_probe.py` is loaded by explicit path (a test module is not importable by name under `--import-mode=importlib`; `conftest.py` does the same for the harness) and only these helpers are bound: its `probe_database` fixture (a database `prod11a_probe_<hex>` migrated by the literal `alembic upgrade head` and dropped afterwards), `_publish_source`, `_seed_norms`, `_RecordOnFirstSight`, `_require_probe_database`, `_require_loopback` and the profile ids. The probe is not edited and its 18 tests are unchanged; the two modules run together in either order (73 passed).
- **The application** is `build_application(environ=...)` with the database, the lane's S3 variables, a deployment secret and, for the installed one, the sealed manifest (`seal_manifest` of the probe's `TrustedPack`). Two names of `bootstrap.composition` are patched for the duration of the call only: `_build_provider` (the adapter is swapped for a replay with a barrier in front of its first call; the stock `call` binding, PROD-11C's unmetered replay, is kept) and `RunAdapter` (a subclass that keeps the instance). A second application on the same database with no manifest is the empty registry.
- **The measurement** is one module-scoped fixture, before the suite's autouse `_no_network` installs (a `TestClient` needs a socket pair); the tests read the captured exchanges and database readings. Order: pack status (expert, admin, empty app); empty-registry start; admin, role-less and anonymous starts; a start naming a pack and scopes; the real start; SQL counts and the poller's query; group and review before; an identical start and a same-key/other-version start; `submit_existing` for each member; a read while the first Run is at the provider (barrier); release, `carrier.drain`; group, review (twice, second as admin), start and pack again; call journal rows.
- **The reply** (every Run) makes two proposals over `N1`, the first item of its scope. Ordinal 0 is grounded: the synthetic set's paragraph (set on the module's private copy of the probe) is «Минимальная ширина эвакуационных путей составляет 1,4 м.», the PDF evidence is a quote of page 7 with `1,2 м`, required value `1,4 м`, stated value `1,2 м`, severity, finding and recommendation text. Ordinal 1 states `9,9 м`, which is not on the page. Result per scope, as the policy predicts (`C05`, `C06`, `C08`, `C09`, `C10`, `C15`, `C21`, `C22` are context-only): `F1`, `F2`, `A1` start with a provisional-citation item, so ordinal 0 is one provisional citation; `A2`, `S1`, `S2` start with a context-only item, so ordinal 0 is withheld and no citation is shown; ordinal 1 is a rejected count in all six.

## The facts (tests), and what each asserts

| Test | Claim |
| --- | --- |
| `test_the_contract_names_what_this_module_assumes` | the scope labels and their order, the partition and the closed key sets come from the contract files; no schema declares a conclusion-shaped property |
| `test_every_status_observed_is_one_the_contract_declares_for_that_operation` | all 20 captured statuses are declared for their operation |
| `test_the_pack_status_is_the_sealed_synthetic_pack_the_composition_root_installed` (3 reads) | `installed`, profile and bundle ids, the digest of the sealed pack, the six scope ids, the attestation, exactly the contract's keys; also for an administrator and after the Runs |
| `test_without_a_manifest_the_pack_status_says_not_installed` | `{"state": "not_installed"}` |
| `test_a_start_with_an_empty_registry_is_refused_with_the_typed_error_and_creates_nothing` | `503 dependency_unavailable`, `dependency: ar_v3_trusted_pack`, status and `retryable` from `error-codes.json`; no group, no Run, no Job |
| `test_a_start_by_a_non_expert_is_refused_and_creates_nothing` (admin, role-less) | `403 permission_denied`, `required_capability: role:expert`; nothing created |
| `test_an_anonymous_start_is_refused_and_creates_nothing` | `401 authentication_required` |
| `test_a_request_that_names_a_pack_or_a_scope_is_refused_and_creates_nothing` | `422 validation_failed` (`additionalProperties`) |
| `test_the_start_creates_the_group_of_six_with_the_right_scope_labels` | `202`, closed keys, labels `F1 F2 A1 A2 S1 S2` in order, per scope the pack's `map_sha256` and set id, the pack digest, the profile, bundle and snapshot, `recorded`, six `created`, one group and six Runs |
| `test_the_group_read_after_the_start_is_the_group_the_start_answered` | `getArV3BetaGroup` equals the start |
| `test_the_http_start_leaves_the_six_runs_created_and_unqueued_for_the_serving_poller` | fact 5, the gap above |
| `test_the_review_read_before_the_runs_finish_says_pending` | six `pending`, no review, no reason, agrees with the group |
| `test_a_read_while_the_first_run_is_at_the_provider_says_one_running_and_five_pending` | `running` + five `created` in both answers and in the database; six `pending` |
| `test_a_second_identical_start_is_the_same_group_and_creates_no_run` | same group, Runs, maps and sets; one group, six Runs, no Job |
| `test_the_same_key_with_another_version_is_a_conflict_and_creates_nothing` | `409 idempotency_key_reuse`; nothing on the other version |
| `test_the_six_runs_reach_published_through_the_applications_own_carrier` | six `published`, six provider requests, Runs `recorded`, one call row per Run `recorded / unmetered / 0 / succeeded` |
| `test_after_they_finish_the_review_has_six_available_outcomes_that_agree_with_the_group` (2 reads) | six `available`; labels; agreement with the group; the scope's items in order; modes from the policy; provisional citation or withheld proposal per scope; one rejected each; the citation points at the one seeded paragraph |
| `test_every_topic_and_citation_is_provisional_and_labelled_for_expert_review` | every topic `requires_expert_review`; a citation names only a provisional-citation topic; a context-only topic is never cited; counts equal citations |
| `test_no_answer_carries_a_numerical_conclusion` | all 14 successful answers (pack x4, start x3, group x3, review x4): only contract keys, no conclusion-shaped key, no float, none of the model's prose or `9,9 м`, the reply's numbers only inside `quote` / `raw_quote` |
| `test_a_start_after_the_runs_finished_is_still_the_same_group_with_no_new_work` | same group, six `published`, six Jobs (created when the Runs were carried), still six provider requests |
| `test_the_acceptance_stayed_on_the_loopback` | every Python-level connection was to loopback |
| `test_every_check_can_fail` (33) | see below |

## Mutations: every asserted fact flipped once

### In the module (33 cases, `test_every_check_can_fail`)

Each assertion is a pure check; for each, the real answer passes it and one fact of a deep copy is flipped: scope labels in another order, a label outside the six; a group member with an extra property, a group without its digest, a member bound to another map, a group pinned to another pack, a `published` group with a failed Run; a pending review that shows a review, one that is not pending; a review that disagrees with its group about a Run, a review of another group; an injected numeric field in a review proposal; a topic without the expert-review label, a cited context-only item, a citation outside its scope, a wrong topic count; a withheld proposal shown as a citation, a citation that quotes something else, a missing rejected count; a model field, a severity, the model's sentence, a stated value outside a quote field, a float in an answer; the empty-registry refusal under another code, answered 202, naming another dependency; a non-expert start that was accepted; a second start that is another group or made other Runs; a refusal that created a group, a replay that made a seventh Run or a second group. 33 of 33 raise `AssertionError`.

### On the committed tree (source mutations; each applied alone, the module run, then `git checkout -- src`; `git status --short` showed no tracked change after every one)

`facts red` = tests other than `test_every_check_can_fail`; `params red` = cases of that test that go red only because the real answer no longer passes their precondition. Baseline: 55 passed.

| Mutation | Result | Facts red |
| --- | --- | --- |
| M1 `runs/v3_group.py`: the group lists its members reversed | 29 failed (8 + 21) | status declared, start/scope labels, pending (x2), published, available review, provisional label, numeric |
| M2 `runs/v3_review_artifact.py`: the topic label `requires_expert_review` -> `reviewed` | 15 failed (2 + 13) | available review, provisional label |
| M3 `api/schemas/models.py`: `required_value` added to `ArV3BetaVisibleProposal` | 11 failed (2 + 9) | available review (closed keys), numeric conclusion |
| M4 `bootstrap/adapters.py`: every start gets a fresh idempotency key | 7 failed (3 + 4) | identical start, key reuse, start after the Runs |
| M5 `runs/v3_group.py`: empty registry refused with `not_found` | 4 failed (1 + 3) | empty-registry refusal |
| M6 `api/security.py`: `startArV3BetaGroup` open to any role | 13 failed (9 + 4) | the admin refusal and every refusal that checks nothing was created (the admin's group is counted), start, identical start, key reuse, start after |
| M7 `runs/v3_group_review.py`: an unfinished Run reported `failed` | 4 failed (2 + 2) | pending before, pending midway |
| M8 `runs/v3_group_review.py`: a pending member reports `queued` | 4 failed (2 + 2) | pending before, pending midway (agreement with the group) |
| M9 `runs/v3_citations.py`: every grounded proposal is provisional (context-only laundered) | 12 failed (4 + 8) | published, available review, provisional label, start after |
| M10 `bootstrap/adapters.py`: the start queues the Runs and enqueues Jobs (the fix of the gap) | 11 failed (7 + 4) | **fact 5**, start, group read, pending before and midway, identical start, key reuse |
| M11 `api/schemas/models.py`: the request model accepts `pack_sha256` and `scopes` | 12 failed (9 + 3) | the authority refusal and the facts that depend on a clean count |
| M12 `bootstrap/composition.py`: recorded composition without PROD-11C's replay binding | 18 failed (4 + 14) | published, available review, provisional label, start after |
| M13 `bootstrap/adapters.py`: the pack status always `not_installed` | 1 failed (1 + 0) | the pack status |
| restored | 55 passed; the probe 18 passed; both together, either order, 73 passed | |

## Before and after of modified tests

None modified. `git diff --name-only b0644fd3..HEAD` lists no existing test; the probe and every other module are byte-identical.

## Commands and results (lane stack, one pytest at a time, no docker, no process killed)

| Command (prefix `env $(grep -v '^#' .env \| grep -v '^$' \| xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider`) | Result |
| --- | --- |
| `tests/integration/runs/test_v3_saved_text_layer_probe.py` on the base tree (before) | 18 passed, 24.19 s |
| `tests/integration/runs/test_v3_recorded_group_over_http.py` | 55 passed, 7.3 s |
| `tests/integration/runs/test_v3_saved_text_layer_probe.py` after | 18 passed |
| the two modules together, either order | 73 passed, 16.5 s |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` (clean committed tree) | 105 passed, 20 s |
| governance one-liner on the task file | `[]` |
| `git diff --check b0644fd3..HEAD` | exit 0 |

Free disk stayed between 2.1 and 2.3 GiB for the whole lane (above the 1.5 GiB line of this lane and the 1.3 GiB line of `D-205`); the module's database is dropped by the probe's fixture and `SELECT datname FROM pg_database WHERE datname LIKE 'prod11a_probe_%'` was empty after the last run. No full gate and no whole `tests/integration` (`R-135`), no browser, no network.

## Integration notes (for the integrator)

1. Merge with `--no-ff`. Check: `pytest -q tests/integration/runs/test_v3_recorded_group_over_http.py` shows 55 passed on the lane stack; `rg -n "submit_existing" tests/integration/runs/test_v3_recorded_group_over_http.py` finds the one carry call.
2. **Record the gap** (above) as a debt row; it should be closed before `PROD-12` activates the group. A fix belongs in `RunAdapter.start_ar_v3_group` (queue the Runs and enqueue their Jobs in the start's transaction, as `start_run` does) or in a group-aware poller; either flips fact 5 and the facts that read the state right after the start (they say `created`), and replaces the carry step by the serving poller started by the lifespan. M10 is a working sketch of the first, not a proposal to merge.
3. `AR-V3-BETA-ACCEPT-01`'s recorded positive cases (`PROD-11A`, `PROD-11C`) are now covered over HTTP. The activation runbook's step 9 also names recorded negative cases; this module has none of its own beyond the refusals above and, inside every Run, one withheld proposal (context-only scopes) and one rejected proposal (ungrounded values), visible as counts. Reply-level negatives stay below the HTTP line where they already are (`test_v3_corpus_citation_bridge.py`, the probe's cost controls).
4. No change to `bootstrap/**` or any `src` file, so no named case of `AGENTS.md` section 8 is triggered by this lane.

## Limits

- The reply is synthetic and the sets are synthetic canonical sets: the review text, the topics' reasons and the sources are the real beta policy's, the citations are not a legal reading, and nothing here is an expert decision.
- The Runs are carried by `submit_existing` on an unstarted `DurableCarrier`, not by the serving poller, for the reason above; the carrier's thread pool is the product's, the claim, lease and Job creation are the executor's own. A worker process (`EXECUTION_ROLE=worker`) and the `api` role's reclaim-only carrier were not exercised.
- The Russian label «требует проверки эксперта» is a web rendering: the module asserts the wire value `requires_expert_review` and the contract's key sets, not the widget.
- «`ready`» in the dispatch is `available` on the wire (decided by the lane).
- The lifespan was not entered, so startup reconciliation and the poller did not run; the claim «a served process never carries the group» rests on the poller's own query returning `None` (fact 5), the static reading of `DurableCarrier._poll` and `STRANDED_STATES = ("running",)`, not on a long-running served process.
- One barrier decides the mid-flight read (no timer); if the provider is never reached the fixture fails after 180 s rather than hanging.
- A live provider, the cost check on a real reply, the real pack and the stand are the live half of `AR-V3-BETA-ACCEPT-01`, not measured here.

## Forbidden paths untouched

```text
$ git diff --name-only b0644fd3..HEAD
docs/program/AR-V3-BETA-ACCEPT-RECORDED-01.md
docs/program/tasks/AR-V3-BETA-ACCEPT-RECORDED-01.md
tests/integration/runs/test_v3_recorded_group_over_http.py
```

`src/**`, `contracts/**`, `db/migrations/**`, `infra/**`, `web/**`, root dependency and lock files, the probe and every other test, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings and the ADRs are untouched.
