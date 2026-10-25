# Task DEV-INTEGRATION-MISC-REDS-01 — the integration tests state what the tree now is

task_id: DEV-INTEGRATION-MISC-REDS-01
status: completed in development candidate

## Outcome

The eleven `tests/integration` files that were red on the clean development tip, with no product change behind them, pass against the existing integration stack: 175 passed, 0 failed. Fourteen of the seventeen failures were test lag (a pin, a version literal, a set, a kind the release now serves, a section that now has a profile, a fake or a stub older than the code it meets). Two read state the test did not own, the host's free disk and the shared database's committed rows. One is environment, the real corpus that a bare worktree does not carry. No product file changed.

## Depends on

- `AR-CLOSE-1026` — the integration branch whose tip is the base.
- `EXEC-CODEX-SSH-01` — pinned the third model identity.
- `AR-V3-BETA-PACK-STATUS-API-01` — sealed contract `1.5.0`.
- `EXEC-SSH-CROPS-01` — served the command over SSH.
- `EXEC-SSH-TUNNEL-CROPS-01` — served the SSH tunnel transport.
- `EXEC-IMAGE-DELIVERY-01` — added the fifth runner operation.
- `PB-PROFILE-01` — registered the PB section profile.
- `EXEC-HTTP-01` — added the route freezer to the re-audit port and the connection revision to the call row.

## Frozen inputs

- domain contract: `1.5.0`
- API contract: `1.5.0` (92 paths, 104 operations, 300 schemas)
- analysis/comparison/event contract: `1.5.0`
- migration head: `0032_ar_v3_run_group`
- base commit: `1ce8edd029ef1a20bec8f6ed0a49b55aeeb61186`
- provider lock: `docs/program/P02_LOCK.json`, three pinned identities.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: seventeen tests in eleven files fail on the base tree; each cause is in the tests or in the host, not in the product code they exercise

### P-01 — the failures at the base tree

- captured_at: 2026-10-26
- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider --tb=line -rf <the eleven files at 1ce8edd0, with .local/norms/corpus absent>`
- captured_output:
  ```text
  FAILED tests/integration/analysis/test_provider_lock_refusals.py::test_the_loaded_lock_carries_exactly_the_two_pinned_identities
  FAILED tests/integration/analysis/test_provider_lock_refusals.py::test_an_annotation_key_is_skipped_rather_than_parsed_as_a_model
  FAILED tests/integration/analysis/test_status_policy_and_result_shape.py::test_the_contract_document_declares_the_pinned_identity
  FAILED tests/integration/analysis/test_status_policy_and_result_shape.py::test_the_real_contract_document_is_accepted
  FAILED tests/integration/auth/test_the_exchange_over_real_users.py::test_every_refusal_is_the_same_refusal[the right login and a wrong password]
  FAILED tests/integration/auth/test_the_exchange_over_real_users.py::test_every_refusal_is_the_same_refusal[a login with no row]
  FAILED tests/integration/auth/test_the_exchange_over_real_users.py::test_every_refusal_is_the_same_refusal[a login of the wrong shape]
  FAILED tests/integration/executors/test_http_operations.py::test_kinds_and_transports_this_release_does_not_serve_are_refused_at_route_time
  FAILED tests/integration/executors/test_http_operations.py::test_worker_bootstrap_lists_openrouter_and_preserves_codex_route_with_image_input
  FAILED tests/integration/executors/test_http_probe_worker.py::test_kinds_this_release_does_not_serve_end_as_kind_not_served
  FAILED tests/integration/executors/test_runner_seam.py::test_the_runner_operations_are_exactly_the_four_paths_under_runner_tasks
  FAILED tests/integration/norms/test_corpus_preflight.py::test_host_capacity_samples_one_minute_load_and_refuses_unavailable_load
  FAILED tests/integration/norms/test_embedding_bakeoff_fixture.py::test_every_relevance_anchor_resolves_to_the_exact_real_corpus
  FAILED tests/integration/runs/test_classification_correction_over_http.py::TestRuns::test_a_correction_to_a_section_without_a_profile_refuses_the_next_start
  FAILED tests/integration/runs/test_v2_recorded_durable_stage.py::test_job_writer_preserves_unknown_and_existing_numeric_costs[recorded-None-None]
  FAILED tests/integration/runs/test_v2_recorded_durable_stage.py::test_job_writer_preserves_unknown_and_existing_numeric_costs[live-0.0344-34400]
  FAILED tests/integration/runs/test_w53c_exec_closure.py::test_the_reaudit_port_stamps_the_deployment_and_reports_lineage
  17 failed, 156 passed, 1 warning in 40.18s
  ```
- interpretation: the sixteen tests the dispatch named plus `test_worker_bootstrap_lists_openrouter_...` (P-05). The first assertion line of each failure is quoted in the report.

### P-02 — the lock pins three identities, the registry and the facts say `1.5.0`

- captured_at: 2026-10-26
- command: `python3 -c "import json;m=json.load(open('docs/program/P02_LOCK.json'))['models'];print({k:v['model_id'] for k,v in m.items() if isinstance(v,dict) and 'model_id' in v})"; python3 -c "import json;print(json.load(open('contracts/analysis/v1/stage-registry.json'))['contract_version'], json.load(open('tests/support/expected_facts.json'))['contract_version'])"`
- captured_output:
  ```text
  {'primary': 'claude-opus-5', 'cheaper_tier': 'claude-sonnet-5', 'codex_subscription': 'gpt-6-sol'}
  1.5.0 1.5.0
  ```
- interpretation: the lock grew a third tier in `EXEC-CODEX-SSH-01`; the stage registry carries the family version, which the hand-maintained facts file also names. It does not show that the lock's third pin is correct, only that it is what the loader returns.

### P-03 — every kind, transport and SSH profile the model validates is served

- captured_at: 2026-10-26
- command: `grep -n '^register_adapter_factory(\|^register_channel_kind(\|^    "http_api", _http_api\|^    "ssh_command", build\|^    "pull", _pull' src/auditmanager/executors/kinds.py; grep -n '^KINDS\|^TRANSPORTS\|^SSH_PROFILES' src/auditmanager/executors/model.py`
- captured_output:
  ```text
  134:register_adapter_factory(
  135:    "http_api", _http_api, purpose="api_key",
  142:register_adapter_factory(
  143:    "ssh_command", build_ssh_command_adapter, purpose="ssh_private_key",
  158:register_channel_kind(
  159:    "pull", _pull, provider_label=lambda revision: revision.settings.pull_client or "pull",
  59:KINDS: Final[tuple[str, ...]] = ("http_api", "ssh_command", "pull")
  65:TRANSPORTS: Final[tuple[str, ...]] = ("direct", "vpn", "ssh_tunnel")
  66:SSH_PROFILES: Final[tuple[str, ...]] = ("claude_code_headless", "custom_command")
  ```
- interpretation: all three kinds have a registration whose `serves` accepts every validated transport and profile, so a real connection can no longer be "not served"; the `kind_not_served` refusal is reachable only when a registration is absent or narrower. It does not show the refusal itself is correct; the tests remove a registration to reach it.

### P-04 — the runner operations and the section table

- captured_at: 2026-10-26
- command: `grep -n 'RUNNER_OPERATIONS: Final' -A3 src/auditmanager/api/security.py; PYTHONPATH=src:$BS .venv/bin/python -c "from auditmanager.analysis.text.profile_registry import load_text_profile_registry; from auditmanager.sections.suggestion import _catalogue; r=load_text_profile_registry(); print(sorted(set(s.code for s in _catalogue())-set(r.section_profiles())))"`
- captured_output:
  ```text
  261:RUNNER_OPERATIONS: Final[frozenset[str]] = frozenset({
  262-    "claimExecutorTask", "extendExecutorTaskClaim", "submitExecutorTaskAnswer",
  263-    "failExecutorTask", "getExecutorTaskImage",
  })
  []
  ```
- interpretation: five runner operations, the fifth a GET; every catalogue section has a registered profile, so "a section with no profile" exists only on a registry built without one.

### P-05 — the shared database holds committed connections of the dump tests

- captured_at: 2026-10-26
- command: `python -c "<select kind, display_name, created_at::date from executor_connection order by created_at, through DATABASE_URL of .env>"`
- captured_output:
  ```text
  ('http_api', 'dump-sentinel', datetime.date(2026, 10, 25))
  ('ssh_command', 'dump-ssh', datetime.date(2026, 10, 25))
  ('http_api', 'dump-sentinel-http', datetime.date(2026, 10, 25))
  ```
- interpretation: `test_secret_never_leaves.py::test_a_database_dump_carries_ciphertext_...` commits these on purpose ("Committed on purpose: pg_dump reads its own snapshot ... The rows stay"). A test that counts the whole table is red on any database those tests have visited, and green on a fresh one. It does not say who else commits to this database.

### P-06 — the host's free disk is below the preflight's reserve

- captured_at: 2026-10-26
- command: `df -B1 --output=avail /root/projects/PDF-Analysis/.local/worktrees/dev-integration-misc-reds-01 | tail -1; grep -n '^DISK_RESERVE\|"source-sums": 0' scripts/norms/corpus_preflight.py`
- captured_output:
  ```text
  2670686208
  62:DISK_RESERVE = 3 * GIB
  71:INCREMENTS = {"source-sums": 0, "base-load": 3 * GIB, "restore-verify": 3 * GIB,
  ```
- interpretation: 2.49 GiB free is under the 3 GiB reserve, so the real `statvfs` adds `disk_floor` to the refusal the test asserts. The test already pins memory for the same reason.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

`docs/program/reviews/W10-ANL.md` still names the renamed test `test_the_loaded_lock_carries_exactly_the_two_pinned_identities` in a sweep table; that record is immutable and is not edited.

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `tests/integration/analysis/test_provider_lock_refusals.py`
- `tests/integration/analysis/test_status_policy_and_result_shape.py`
- `tests/integration/auth/test_the_exchange_over_real_users.py`
- `tests/integration/executors/test_http_operations.py`
- `tests/integration/executors/test_http_probe_worker.py`
- `tests/integration/executors/test_runner_seam.py`
- `tests/integration/norms/test_corpus_preflight.py`
- `tests/integration/norms/test_embedding_bakeoff_fixture.py`
- `tests/integration/runs/test_classification_correction_over_http.py`
- `tests/integration/runs/test_v2_recorded_durable_stage.py`
- `tests/integration/runs/test_w53c_exec_closure.py`
- `tests/support/**`
- `docs/program/tasks/DEV-INTEGRATION-MISC-REDS-01.md`
- `docs/program/DEV-INTEGRATION-MISC-REDS-01.md`

## Forbidden hotspots

Contracts, migration head, root dependency/lock files, the Makefile, `infra/**`, composition root, global styles, `web/**`, `docs/program/DEBT_REGISTER.md`, `docs/program/CURRENT_STATE.md`, `.local/**`, every file under `src/`, and the recovery tests and migration-lifecycle and whole-journey idempotency tests owned by lane L14. No product file is changed: where a mutation proof touched one it was reverted before the commit. `test_embedding_bakeoff_fixture.py` is in the list for completeness and is not changed.

## Non-goals

No product change. No relaxation: no assertion became weaker, and no test skips. No change to the dump tests that commit connections (`test_secret_never_leaves.py`, outside this slot). No full battery, gate, live journey or paid call.

## Deliverables

- Expectations restated: the third lock identity, the registry and the response envelope versions read from `tests/support/expected_facts.json`, the runner operations (five, the fifth a GET, with its own authorization cases), the unserved kind and transport simulated through the registry, the section with no profile on a registry built without PB.
- Two doubles brought up to the code they stand in for: the call-completion fake session and the re-audit port stub.
- Two tests made independent of the host and of the shared database: the preflight load test pins the disk as it already pins memory, the OpenRouter bootstrap test counts the connections it adds.
- The real-corpus test is classified as environment; its attach step is in the report.
- Report with per-cluster classification, the mutation proofs and the final result.

## Required tests

- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider` followed by the eleven test files
- expected: `175 passed`, with `.local/norms/corpus` attached (`mkdir -p .local/norms && ln -s /root/projects/PDF-Analysis/.local/norms/corpus .local/norms/corpus`) and the existing integration stack reachable
- command: the `governance_findings` check of this file (`PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/DEV-INTEGRATION-MISC-REDS-01.md',encoding='utf-8').read())))"`)
- expected: `[]`
- command: `git diff --check` and `git diff --name-only 1ce8edd029ef1a20bec8f6ed0a49b55aeeb61186`
- expected: no output from the first; only the fourteen allowed paths from the second.

## Integration contract

A consumer can rely on the eleven files passing on a tree whose product code equals the base, against any integration database, with the corpus attached. The result over the eleven files is recorded in the report; a database re-run after the merge is cheap and not required. The lane touches no file the other lanes own.

## Failure/idempotency/security cases

The unserved-kind tests restore the registry through `monkeypatch`, so a failing assertion cannot leave a kind unregistered for the next test in the process. The disk pin and the registry edits are scoped to one test each. No test here commits a row.

## Rollback / feature flag

Not applicable: tests only. Forward-revert the commit.

## Handoff

- changed files: ten test files and this task's two documents; `test_embedding_bakeoff_fixture.py` unchanged
- commands/results: 175 passed in 48.29 s over the eleven files; 17 failed at the base; governance findings empty
- known limits: the corpus test needs the local corpus symlink; the OpenRouter bootstrap test is a database-state red that no run of the whole suite on a fresh database shows
- integration notes: merge before or after lane L14, no overlap; nothing to re-run on a database lane
