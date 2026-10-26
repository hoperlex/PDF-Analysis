# SEC-RUNNER-CAP-01 — bound the runner long poll (`F-06`) and refuse plain-http model destinations (`F-15`)

Task file: `docs/program/tasks/SEC-RUNNER-CAP-01.md` (premises with their real output). Base `16a6596fd80db5f607b44b151c43207775f22cfc`. Findings: `EXPOSURE-REVIEW-02.md` rows `F-06` and `F-15`; debt rows `D-236` and `D-242` (the integrator updates them). Every small decision the lane took is marked **decided by the lane**.

## 1. Files

Source (2): `src/auditmanager/executors/runner.py`, `src/auditmanager/executors/model.py`. `destinations.py` is not changed (the premise did not need it).

New tests (3): `tests/unit/executors/test_runner_long_poll_cap.py` (15), `tests/unit/executors/test_model_plain_http.py` (88), `tests/integration/executors/test_plain_http_destination.py` (13).

Modified test files (8): `tests/unit/executors/fake_gateway.py`, `tests/unit/executors/test_ssh_tunnel_adapter.py`, `tests/integration/executors/http_support.py`, `test_http_operations.py`, `test_http_probe_worker.py`, `test_http_sentinel.py`, `test_http_run_path.py`, `test_explicit_executor.py` (details in section 6).

Docs (2): this file and the task file.

## 2. `F-06` — what was built

`claim_task` slept in the thread that serves the request, up to 25 s, with no counter. `runner.py` now has `LongPollSlots(per_token, total)`: a counter under a `threading.Lock`; `try_acquire(token_id)` never blocks and refuses when the token already waits `per_token` times or `total` claims wait; `release` is in a `finally`. The process's instance uses `MAX_WAITING_CLAIMS_PER_TOKEN = 1` and `MAX_WAITING_CLAIMS_TOTAL = 16`, against `SYNC_POOL_THREADS = 40` (anyio's default, measured; nothing in `src` resizes it), so **at least 24 threads (`RESERVED_SYNC_THREADS`) stay free for every other request** while long polls wait.

`claim_task(..., slots=None)` takes a slot when `wait_seconds > 0`. A claim that cannot have one is not refused: it runs `_poll` with a wait of 0, i.e. one short transaction that still redelivers its own task or claims an open one, and then returns `None`, which the router already turns into the contract's `204` with an empty body. The 200/204/401/422 wire, the lease, redelivery and `max_claimed_tasks` semantics are untouched, and `claim_task` without a competing claim behaves exactly as before (`test_the_wait_is_still_clamped_to_the_contract`).

Decided by the lane: (a) one waiting claim per token, as the brief wrote it; (b) the over-bound claim looks once instead of answering a blind `204` (a runner restarted within 25 s of its own parked claim still gets its redelivered task); (c) 16 of 40 as the total, which leaves 60 % of the pool; (d) the figure 40 is a constant tied to reality by two tests (the installed anyio's default, and a scan that nothing in `src/auditmanager` sets a limiter).

**Several processes.** The state is a counter in the process, and so is the pool it protects: each API process has its own 40 threads. `infra/deploy/serve.py` runs one process (`grep -c workers` is 0). With `N` processes each bounds its own pool, so one token can park one claim per process (`N` in all) and 16 threads per process, never more than one process's pool: it degrades to a looser per-token bound and keeps the per-process reserve, which is what protects the pool. No shared store, no database row and no lock outside the process is introduced (jobs state in memory is forbidden by AGENTS section 4; this is not job state: it is a count of threads in this process and is empty after a restart by construction).

Reproduction (before the fix, section 4 of the task evidence and these figures): 45 simultaneous claims of one token through the real `build_runner_routes` and the real `claim_task` loop, then a sync stand-in for `getMe` in the same pool: `getMe` waited behind 40 parked claims (red); with 40 tokens of one claim each the same; with two tokens of six claims each the peak of sleepers was 12 where 2 is expected. After the fix: one parks, 44 are answered `204` while it still waits, `getMe` answers.

## 3. `F-15` — what was built

`model.py` has `refuse_plain_http(base_url, transport)`. `https://` returns at once. For `http://` it asks the module that already classifies addresses, `destinations.DestinationPolicy`, built with a resolver that never resolves and no network list (the module stays pure): a loopback name or address (`localhost`, `*.localhost`, `127/8`, `::1`, an IPv4-mapped loopback) is accepted for every transport; a private literal (RFC 1918, unique-local, shared space) is accepted for `transport: vpn` only, which is the one transport `destinations.py` admits a private range for; a public address, a private literal on another transport, link-local (the metadata address), reserved and multicast addresses, and every name that is not a loopback name are refused. Refusal: `DomainError(VALIDATION_FAILED)` with `field = base_url`, `constraint = base_url_invalid` and the module's usual message, nothing of the address. The credentials-in-URL refusal of `normalise_origin` is kept (and pinned by a test).

It is called in two places: `validate_settings` (a revision is written, `reviseExecutorConnection` and `import_env`) and `destination_for` for the `api_key` purpose of an `http_api` connection, which is evaluated before `open_secret` at every call, every probe and every `setExecutorSecret`.

Decided by the lane: (a) constraint `base_url_invalid` is reused. A new value (`plain_http`) would need a sentence in `contracts/domain/v1/error-codes.json`, which is not this lane's; the web already renders `base_url_invalid` as «нужен адрес вида https://…». A distinct constraint is a follow-up for the contract slot. (b) A host name that is not a loopback name is refused even on `vpn`: without resolving, a name cannot be classified, and the module never resolves; the administrator names the VPN address or uses `https://`. (c) `ssh_tunnel` admits `http://` for loopback only (the finding's «loopback tunnel»): a private literal behind the SSH host is refused, the same rule `destinations.py` has for private ranges. (d) `destinations.py` is not edited: `check` and `classify` answer the question as they are.

**Stored connections with an `http://` public destination** (written before this change). A read stays possible: nothing that reads a revision calls `validate_settings`, and the secret view catches the refusal of `destination_for` and shows `bound_to_current_revision: false` (`test_a_stored_plain_http_connection_is_still_read`: `listExecutorConnections` and `getExecutorConnection` answer 200). A **new run through such a connection is refused with the typed refusal** `validation_failed / base_url / base_url_invalid` raised by `bind_connection` (and by `DatabaseProviders.resolve`, which every stage of a Run calls) **before the key is opened** (`test_a_new_run_through_it_is_refused_before_the_key_is_opened` plants a spy on `open_secret`). `setExecutorSecret` on it is refused the same way, and a new revision with `https://` repairs it. A probe of it sends nothing and ends `protocol_error` (limit 1 below).

## 4. Mutation table

Each row: the code changed, the test that went red (first failure; `-x`), then the file restored (`diff` against the saved copy printed "restored" after every batch).

| # | Mutation | Red test |
| --- | --- | --- |
| M1 | `try_acquire` always grants (bound removed) | `test_many_claims_from_one_token_leave_the_pool_to_everything_else` |
| M2a | per-token check removed, only the total kept | same |
| M2b | per-token bound replaced by one global slot (`per_token=1, total=1`) | `test_a_waiting_token_does_not_stop_another_token_waiting` |
| M3a | total check removed, per-token only | `test_many_tokens_cannot_park_more_than_the_stated_share_of_the_pool` |
| M3b | the reserve removed (`MAX_WAITING_CLAIMS_TOTAL = 40`) | same |
| M4 | slot never given back | `test_a_waiting_token_does_not_stop_another_token_waiting` |
| M5 | an over-bound claim sleeps anyway | `test_many_claims_from_one_token_leave_the_pool_to_everything_else` |
| M6 | `wait_seconds: 0` takes a slot | `test_wait_zero_never_takes_a_slot` (first version of that test did not see it: M6 survived, the test was strengthened to observe the slot during the look, then red) |
| M7 | an over-bound claim does not look at the rows | `test_a_claim_over_the_bound_still_looks_once_and_returns_a_ready_task_at_once` |
| M8 | per-token cap raised to 2 | `test_many_claims_from_one_token_leave_the_pool_to_everything_else` |
| M9 | pool figure stated as 64 | `test_the_shipped_shares_state_the_reserve` |
| M10 | a limiter configured somewhere in `src` | `test_nothing_in_the_application_resizes_the_pool` |
| F1 | `refuse_plain_http` returns at once | `test_http_to_a_public_host_is_refused_on_every_transport`; also the wire test of the integration file |
| F2 | transport ignored (every route treated as `vpn`) | `test_http_to_a_private_literal_is_refused_off_a_vpn_route` |
| F3 | loopback no longer admitted | `test_http_to_a_loopback_name_or_address_is_accepted` |
| F4 | `validate_settings` call removed | `test_http_to_a_public_host_is_refused_on_every_transport`; integration wire test |
| F5 | `destination_for` call removed | `test_a_stored_http_public_revision_is_refused_where_its_key_is_bound_for_a_call`; integration `test_a_stored_plain_http_connection_is_still_read` |
| F6 | names resolved through the system resolver | `test_the_module_does_not_resolve_a_name` |
| F7 | an unclassifiable name accepted | `test_http_to_a_public_host_is_refused_on_every_transport` |
| F8 | a public address accepted | same, `93.184.216.34` |
| F9 | the scheme test matches `https` too | `test_https_is_accepted_for_every_host_as_before` |
| F10a/b/c | another constraint name on each refusing branch; another error code | the same refusal tests (first attempt F10 survived because the mutated branch is unreachable for them; split into the three reachable branches) |
| F11 | credentials check dropped from `normalise_origin` | `test_credentials_in_the_url_stay_refused` |

## 5. Commands and counts

All with `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages)` and `PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider`:

- `tests/unit/executors/test_runner_long_poll_cap.py tests/unit/executors/test_model_plain_http.py`: 103 passed.
- `tests/unit/executors tests/unit/executor_runner`: 730 passed, 5 failed. The five are `test_ssh_forced_command.py` (the shell script exits 65 «claude returned an incomplete answer»); that file imports nothing of `auditmanager`, `tools/` is unchanged by this lane, so they fail identically without it (not run on the base: no second worktree, disk).
- Integration, on a private database created for the lane (`sec_runner_cap_01_*`, `alembic upgrade head`, 15 MB, dropped at the end), with `.env` loaded except `DATABASE_URL`: the 15 files of `tests/integration/executors` other than the two SSH ones (`ls tests/integration/executors/test_*.py | grep -v "test_ssh_local_image\|test_ssh_sshd"`): **170 passed** in 116 s (13 of them new). Baseline of the eight http-path files on the `F-06` commit before the `F-15` change: 91 passed; with the `F-15` rule and the old fixtures: 42 failed, 49 passed (every red was an `http://gateway.example.test` revision, resolved by the fixture changes of section 6); after: 0 failed. The 66 runner/pull cases (`test_runner_channel`, `test_runner_seam`, `test_runner_client_wire`, `test_runner_bridge_e2e`, `test_pull_run_path`, `test_agent_e2e`) pass with the slots in the real `claim_task`.
- `tests/contract/architecture`: 4 passed (the import-order test of `executors.public` still holds with `model.py` importing `destinations.py`).
- Docs guards and `git diff --check`: `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py tests/contract/architecture` on the committed tree: 109 passed (124 with the long-poll file added). The governance one-liner on the task file prints `[]`. `git diff --check 16a6596f..HEAD` is clean (its first run flagged one trailing-space line in the task file and a blank line at the end of a new test file; both fixed).
- Skipped: `test_ssh_local_image.py` and `test_ssh_sshd.py` (need an sshd fixture and a container; the lane may not start one). Neither goes through `destination_for`.

## 6. Modified tests: before and after

No test was weakened. For each, what it asserted and what it asserts.

- `tests/unit/executors/test_ssh_tunnel_adapter.py`: helper `revision(...)` gains the keyword `plain_loopback=False`. The three tests that bind through `destination_for` (`test_resolver_opens_both_bound_secrets`, `test_resolver_refuses_a_tunnel_without_current_ssh_key`, `test_worker_probe_opens_both_secrets`) asserted that both secrets are opened for `ssh_tunnel|…` destinations, that a missing SSH key raises `SecretUnreadableError`, and that the probe delivers `("http-key", "ssh-key")`: before, with `base_url = http://gateway.example.test:PORT/api/v1`; after, with `http://localhost:PORT/api/v1` (the remote host's loopback, the one plain-http tunnel target `F-15` admits). The assertions are identical; the other tests of the file keep the public name because they call the adapter directly.
- `tests/unit/executors/fake_gateway.py`: adds `VPN_HOST = "10.8.0.2"` and `vpn_url()`; `base_url()` and `policy()` are unchanged.
- `tests/integration/executors/http_support.py`: `settings()` sets `transport` to `vpn` when the URL starts with `http://` (a caller's `transport=` still wins). Before it always defaulted to `direct`.
- `test_http_run_path.py`, `test_explicit_executor.py`, `test_http_probe_worker.py`, `test_http_sentinel.py`, and 24 lines of `test_http_operations.py`: every `fake.base_url(` is now `fake.vpn_url(` (`http://gateway.example.test:PORT/…` direct becomes `http://10.8.0.2:PORT/…` on `vpn`), `.replace("gateway.example.test", "other.example.test")` is `.replace("10.8.0.2", "10.8.0.3")` and one literal URL follows. Checked mechanically: applying the inverse substitution to the new text gives the old file byte for byte for the four files named first. The fake policy dials any address as the harness server, so the destination checks, the probe outcomes and the key scans run exactly as before; they now run over the one route a plain-http connection can take.
- `test_http_operations.py`, the import-env trio (`test_import_env_makes_the_first_connection_probes_routes_and_is_idempotent`, `test_worker_bootstrap_lists_openrouter_and_preserves_codex_route_with_image_input`, `test_import_env_refuses_a_stub_model_and_does_not_route_a_refused_probe`): `import_env` always names `transport: direct`, where plain `http://` is now admitted for a loopback host only. They asserted: first import creates, probes ok, routes, a second import is a no-op, the key opens for the revision's address, the stub model is refused, a refused probe is not routed. They assert the same; the environment URL is `http://127.0.0.1:PORT/agent/v1` and the policy is `_LoopbackAllowed`, a subclass of `DestinationPolicy` that classifies loopback as public (every other class still refuses). `assert route.primary.settings.base_url == fake.base_url()` is `== _loopback_url(fake)`.
- `test_reach_says_refused_unresolvable_unreachable_or_reachable` is unchanged (`reach` is not a revision).

## 7. Limits

1. The probe of a stored `http://` public connection ends `protocol_error` ("the probe failed unexpectedly", logged as an error): `probe_runner.py` catches `DomainError` from `destination_for` as a generic failure and does not map it to `destination_refused`. It is outside the allowed paths; the integration test pins the current outcome so a later mapping shows.
2. A runner kept at the bound (more than 16 runners polling at once, a restarted runner within 25 s of its parked claim, or an MCP bridge session that issues claims in parallel) gets `204` at once and, as `RUNNER_API.md` 2.1 says, claims again at once. That loop is limited by nginx (60 r/m, burst 30 per token), after which the stand answers `429` and the client waits `Retry-After`. A `limit_conn` on `/api/v1/runner/` and a shorter poll are `PROD-05`'s.
3. A rogue token's over-bound claims still take a pool thread for one short transaction each. This is bounded by the proxy's rate, not by this slice; the thread-hold time is milliseconds, not 25 s.
4. A sync handler cannot be cancelled when the client disconnects: a slot is held until the claim's wait ends, at most 25 s.
5. The reserve protects against long polls, not against other long holders of the pool (PBKDF2 sign-ins `F-18`, uploads `F-10`).
6. `http://` plus a host name is refused on every transport, including a name a real VPN resolves to a private address; and a private literal behind an SSH host is refused. Both are the conservative reading (decided by the lane); loosening either needs the destination module to classify tunnel targets, which it deliberately does not.
7. The call-time guard is in `destination_for` because the adapters, the resolver and the probe worker are outside the allowed paths; `destinations.py` `check` still does not know the scheme. A stored `http://` revision on `vpn` with a name that resolves to a public address is refused by this guard (a name is not a loopback name); a stored revision on `direct` with a loopback address is accepted here and refused later by `check` as before.
8. No web change: the connection form can still submit `http://…`; the server answers the typed refusal the screen already renders.

## 8. Integration notes

- Contract: none changed. `claimExecutorTask` answers the same `200`/`204`/`401`/`422`; the new refusal is `validation_failed`/`base_url`/`base_url_invalid`, already listed. No migration, no head change.
- Any other lane or script that seeds an `http_api` connection through the commands with `http://` on `direct` is now refused; use `FakeGateway.vpn_url()` (private literal, `transport: vpn`) or a loopback host.
- Debt rows: `D-236` (`F-06`) can cite the unit reproduction `test_many_claims_from_one_token_leave_the_pool_to_everything_else`; its second check (`limit_conn` in `nginx.conf`) is still open and belongs to `PROD-05`. `D-242` item `F-15` is closed by the two refusals; its other items are untouched.
- After the merge the integrator can re-run the targeted directories: `tests/integration/executors` on the lane stack.

## 9. Forbidden paths untouched

`git diff --name-only 16a6596fd80db5f607b44b151c43207775f22cfc..HEAD` (printed in the lane's final report) lists only the paths of section 1; nothing under `contracts/`, `db/migrations/`, `infra/`, `web/`, `tools/`, any other `src/` file, `bootstrap/`, the debt register, `CURRENT_STATE.md`, the plan, the rulings or the ADRs.
