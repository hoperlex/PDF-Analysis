# DEV-INTEGRATION-MISC-REDS-01 — the integration tests state what the tree now is

Seventeen tests in eleven `tests/integration` files were red on the base tree (`1ce8edd0`, and the same on the clean development tip). None needed a product change. Fourteen were test lag, two read state the test did not own, one is environment. After the change the same eleven files give **175 passed, 0 failed** against the existing integration stack, with the real corpus attached. No assertion became weaker and nothing skips.

The dispatch counted fifteen reds; the base run counts seventeen. Sixteen are the tests it named. The seventeenth, `test_worker_bootstrap_lists_openrouter_and_preserves_codex_route_with_image_input`, passes on a fresh database and fails on this one (cluster 9).

## Per-cluster classification

| # | Tests | First assertion at the base | Class | Cause and change |
|---|-------|-----------------------------|-------|------------------|
| 1 | `test_provider_lock_refusals.py` (2) | `{'claude-opus…','gpt-6-sol'} == {'claude-opus…','claude-sonnet-5'}` | TEST-LAG | `P02_LOCK.json` pins a third identity (`codex_subscription`, `gpt-6-sol`, `EXEC-CODEX-SSH-01`). The set is now `PINNED_MODEL_IDS` with the Codex id named, the lock-document test reads the third entry, and the pinned-identity test admits it. The first test is renamed `..._exactly_the_three_pinned_identities`. |
| 2 | `test_status_policy_and_result_shape.py` (2), `test_the_exchange_over_real_users.py` (3) | `'1.5.0' == '1.0.0'` | TEST-LAG | The stage registry and the error envelope carry the contract family's version, which every reseal moves (`test_contract_seal.py`). The literal `1.0.0` is replaced by `FACTS.contract_version` from `tests/support/expected_facts.json`, the hand-maintained expectation, so the next reseal moves these with the facts file. |
| 3 | `test_http_operations.py::test_kinds_and_transports_...`, `test_http_probe_worker.py::test_kinds_this_release_...` | `'conflict' != 'validation_failed'`; `'secret_unreadable' == 'kind_not_served'` | TEST-LAG | `ssh_command` (`EXEC-SSH-CROPS-01`) and the `ssh_tunnel` transport (`EXEC-SSH-TUNNEL-CROPS-01`) are served; `KINDS`, `TRANSPORTS` and `SSH_PROFILES` are all registered. "Not served" is no longer a state a real connection can be in. Both tests now reach the refusal by taking the registration away with `monkeypatch` (delete `ssh_command`; narrow `http_api.serves` to `direct`/`vpn`) and first assert the other outcome with the registry intact, so the simulation is not vacuous. Renamed `..._the_registry_does_not_serve_...`. |
| 4 | `test_runner_seam.py::test_the_runner_operations_...` | `Extra items in the right set: 'getExecutorTaskImage'` | TEST-LAG | There are five runner operations; the fifth is a GET and cannot join `PATHS`, which the POST-driven cases iterate. The set test names `IMAGE_OPERATION` beside `PATHS`; the stub's `read_image` records and returns bytes; two new cases cover the seam on the GET (a token reaches it and the port sees its identity; a wrong token, none, or a user's credential is `authentication_required` and reaches no port). Renamed `..._four_posts_and_the_image_read_...`. |
| 5a | `test_embedding_bakeoff_fixture.py::test_every_relevance_anchor_...` | `real corpus required; this test never substitutes a tiny fixture` | ENV | `.local/` is untracked, so a worktree has no corpus. Attach: `mkdir -p .local/norms && ln -s /root/projects/PDF-Analysis/.local/norms/corpus .local/norms/corpus` (the symlink is ignored by git). With it the file passes (3 passed). No change. |
| 5b | `test_corpus_preflight.py::test_host_capacity_samples_one_minute_load_...` | `('disk_floor', 'load_floor') == ('load_floor',)` | TEST read the HOST | Not load: the host has 2.49 GiB free, below the 3 GiB `DISK_RESERVE`, and the test pinned memory and load but not disk. It now pins `os.statvfs` the same way. The load refusal and the unavailable-load case are still asserted exactly. This test would pass on a host with 3 GiB free and fail below it; it no longer depends on the host. |
| 6 | `test_classification_correction_over_http.py::..._without_a_profile_refuses_the_next_start` | `assert 202 == 422` | TEST-LAG | PB has a registered profile (`PB-PROFILE-01`); every catalogue section does. The seam for "a section with no profile" is a registry built without it, the one `test_w59_section_profile_recorded.py` already uses. `_client` takes a registry, the test passes `WITHOUT_PB`, and it adds the negative half: the full registry starts the same corrected version under PB's own pair. |
| 7 | `test_v2_recorded_durable_stage.py::..._numeric_costs[...]` (2) | `'SimpleNamespace' object has no attribute 'mappings'` | TEST-LAG | `complete_provider_call` reads the prepared effect through `.mappings().first()` and copies its `connection_revision_id` and `identity_basis` into the call row (migration 0030: both set or both NULL). The fake returns that pair (none for a recorded call, a revision and `reported` for a live one) and the test asserts the row carries it. |
| 8 | `test_w53c_exec_closure.py::test_the_reaudit_port_...` | `'_ConfiguredRuns' has no attribute 'route_freezer'` | TEST-LAG | `ExecutionAdapter.reaudit_run` passes `RunAdapter.route_freezer`. The stub gains `route_freezer = None`, "a wiring without the database provider source", as it already carries `section_profiles = None`. |
| 9 | `test_http_operations.py::test_worker_bootstrap_...` | `assert 5 == 2` | TEST read SHARED STATE | It counted every row of `executor_connection`. `test_secret_never_leaves.py` commits three on purpose and they stay, so the count is 2 on a fresh database and 5 here. The test now counts what it adds (`before + 2`), as the neighbouring idempotency test already counts a delta. |

## Mutation proofs

Each mutation was applied, the named tests run, and the file restored with `git checkout`; none is in the commit.

| Guard | Mutation | Result |
|-------|----------|--------|
| 1, third identity | `lock.py`: skip tier `codex_subscription` in `load_provider_lock` | 3 failed (`..._three_pinned_identities`, `test_a_pinned_identity_is_not_refused`, `test_an_annotation_key_...`) |
| 1, lock document | `P02_LOCK.json`: `"gpt-6-sol"` to `"gpt-6-sol-x"` | 4 failed, including `test_the_lock_document_still_says_what_this_file_pins` |
| 2, versions from the facts | `tests/support/expected_facts.json`: `contract_version` `1.5.0` to `1.4.0` | 5 failed (2 registry, 3 envelope) |
| 3, route refusal | `usability.py`: `if not is_served(` to `if False and not is_served(` | 1 failed (`..._registry_does_not_serve_is_refused_at_route_time`) |
| 3, probe refusal | `probe_runner.py`: same change in `_evaluate` | 1 failed (`..._does_not_serve_ends_as_kind_not_served`) |
| 4, fifth operation | `security.py`: drop `getExecutorTaskImage` from `RUNNER_OPERATIONS` | 3 failed (set, reach, refusals) |
| 5b, load refusal | `corpus_preflight.py`: `if False and capacity.load_average_1 >= ...` | 3 failed |
| 5b, the disk pin | the pinned disk set to 1 GiB (below the reserve) | 1 failed with `disk_floor` in the tuple; with the pin removed the base red returns on this host |
| 6, refusal code | `classification.py`: `if False and str(refusal) in _PROFILE_REASONS` | 1 failed |
| 7, identity basis | `repository.py`: `"identity_basis": None` | 1 failed (`[live-0.0344-34400]`) |
| 8, re-audit stamps | `adapters.py`: a fixed profile id in the explicit pair | 1 failed |
| 9, delta count | `operations.py`: `import_env` also creates a connection on the existing path | 2 failed; the bootstrap test at the `before + 2` line |

## Result

`env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <the eleven files>`: **175 passed in 48.29 s**, exit 0. At the base the same command gave 17 failed, 156 passed. The governance check of the task file prints `[]`.

## Notes for the integrator

- Nothing outside the allowed paths changed; `git diff --name-only 1ce8edd0` lists ten test files and the two documents. `test_embedding_bakeoff_fixture.py` is unchanged; it passes only where `.local/norms/corpus` exists, as before.
- Four tests were renamed because their old names said what is no longer true (clusters 1, 3 twice and 4). `docs/program/reviews/W10-ANL.md` still cites the old lock test name in a past sweep table; that record is immutable and left alone.
- Not run: lane L14's files (`tests/integration/recovery/`, `test_migration_lifecycle.py`, `test_whole_journey_idempotency.py`). The tests committing connections on purpose (`test_secret_never_leaves.py`, `test_http_sentinel.py`) are unchanged; their rows persist in any database they visit, which is why cluster 9 is now delta-based.
- No `make gate`, no full battery, no live journey; the change does not touch a path that requires one (`tests/support/**` is in the allowed list, but no file there changed).
