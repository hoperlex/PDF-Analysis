# JUDGE-FIXES-F2-01 — the judge's findings on the deployment scripts (`D-229` items 1, 2, 3, 4)

Task: `docs/program/tasks/JUDGE-FIXES-F2-01.md`. Branch `agent/judge-fixes-f2-01`, base `07e2e8ba` (`integration/ar-close-1026`), lane F2 of wave `PW2b`/`PW3`. Register row `D-229`; reports `PROD-01-TLS-ACME-01.md` and `PROD-02-03-DEPLOY-GATES-01.md`.

**Status.** Items 1, 2, 3, 4 and the README text are built and verified in the tree (no docker, no network, no host touched; the host's `docker` was never called). **Item 6 (the stand fingerprint and `access.%`) is NOT implemented**: its footprint is outside the lane's allowed paths and its premise is incomplete (section 4). One regression the brief did not name was found and fixed on the way: item 3 would have broken `reload-proxy.sh` (P-04).

## 1. What was built, and what the lane decided

| item | change |
|---|---|
| 1 MED | `deploy.sh` `public-ports-free`: a function `port_is_listened_on` reads the kernel's tables (`/proc/net/tcp`, `/proc/net/tcp6`, state `0A`, any local address); the loopback connect stays as a second witness; where no table can be read the connect is all there is and a `NOTE` says so. Refusal text: `something on this host is listening on port N (on some address; see: ss -ltnp "sport = :N")`. Name-gated and own-proxy excuse as before |
| 2 LOW | runbook section 6, "Before the first deploy of this tree on the live host": the three differences, the one command that finds them in `alpha.env`, the `--tls-dir` check, the rehearsal warning (every `deploy-auto` run red at `verify-deployed.sh` exit 7 while a name and `ALPHA_ACME_STAGING=yes`/absent are set), and a bullet pointing at the credential gate (not name-gated) |
| 3 LOW | `compose.acme.yml`: network `acme-edge` (`<instance>-acme-net`), `acme` on it alone, `proxy` on `[alpha, acme-edge]`, not `internal`. `reload-proxy.sh`: the throwaway `nginx -t` container joins the `api` container's network (P-04) |
| 4 LOW | `deploy.sh`: new guard `trusted-proxies-empty-with-name` (a name and a non-empty list are refused together, exit 3, before docker); runbook step 5, the "behind a host nginx" undo note and the message table; `alpha.env.example` comments |
| README | `infra/deploy/README.md`: the TLS listeners paragraph and table rewritten for the layout after `PROD-02` (the three conditions for 443, the two-step decision, the networks, the guards); three file-table rows updated |
| 6 LOW | not built (section 4) |

**Decided by the lane** (the window asked for no questions; each is small and reversible):

1. **The table, not `ss`.** `/proc/net/tcp*` is read with bash's `read`: no tool the target may not have (the reason the file already gave for `/dev/tcp`), and it is the same table `ss` prints. The loopback connect is kept as a second witness, so the result is a union (a refusal can only be added to, never removed).
2. **An unreadable table is a NOTE, not a refusal.** The guard is name-gated; a host without `/proc` is a development rehearsal (the message says `ALPHA_ACME_HTTP_PORT` names other ports there), and refusing would make the guard unusable where it is least needed. The note names the limit and the one command that closes it. No silent fallback.
3. **Any listener refuses, even when `ALPHA_PUBLIC_ADDRESS` names one interface.** A listener on another interface would not collide; "something holds this port" is the safer sentence for the host this stack targets, and the message says how to see what.
4. **A trust list with a name is refused, not warned.** No live configuration needs it (P-05); the host nginx it was written for is stopped before the first deploy that sets a name. A value of only separators is the empty list, exactly as `proxy/trusted-proxies.sh` reads it. The guard reads the setting itself (not `TRUSTED_PROXIES`), so deleting either guard leaves the other whole.
5. **The proxy lists both networks** in the overlay although the base already lists `alpha`: how compose merges two `networks:` lists is not observed (no docker), and with both names the result is the same if it merges or replaces. `acme-edge` is not `internal` because the client must reach the authority; what it must not reach is the data tier, which is a matter of membership.
6. **`reload-proxy.sh` takes the network from the `api` container**, not from "the proxy's first". With no running `api` the old rule stays (then `nginx -t` cannot resolve `api` anywhere and says so).
7. **`_free_port()` of the guard suite binds `0.0.0.0`**, so the port it hands out is free on every address (the guard now asks that question; a port held on one interface by an unrelated process would otherwise make a test flaky).
8. **The runbook says four things, not three, and the fourth is not about the name:** the credential gate refuses the first deploy while `admin` still accepts `password` (`PROD-02` integration note 1). It sits in the checklist because that is where an operator looks before the first deploy of this tree.
9. **One mutation was dropped as equivalent** (M4-4, `$(true; printf ...)` changes nothing); it is not in the table and not counted.
10. **Item 6 stops** (section 4).

## 2. Files

`git diff --name-status 07e2e8ba..HEAD` (11 files before this report was added; 902 insertions, 35 deletions):

```
M  docs/program/DEPLOYMENT_RUNBOOK.md                              section 6 (checklist, warning, steps 3 and 5, message table), the undo note
A  docs/program/tasks/JUDGE-FIXES-F2-01.md
M  infra/acme/compose.acme.yml                                     network acme-edge; acme and proxy memberships
M  infra/deploy/README.md                                          TLS listeners text, three table rows
M  infra/deploy/deploy.sh                                          public-ports-free; guard trusted-proxies-empty-with-name; header comment
M  infra/deploy/env/alpha.env.example                              two comments
M  infra/deploy/reload-proxy.sh                                    the network of the throwaway container
M  tests/integration/composition/test_acme_deploy_guards.py        +30 tests, helper, docstring
M  tests/integration/composition/test_acme_overlay.py              +4 tests, 1 changed, two helpers
M  tests/integration/composition/test_deploy_script_refusals.py    guard registry 30 -> 31
M  tests/integration/composition/test_proxy_config_follows_checkout.py   stub network branch, +3 tests
```

The report you are reading, `docs/program/JUDGE-FIXES-F2-01.md`, is the twelfth path (added in the last commit).

## 3. Premise

Eleven reads re-run against `07e2e8ba` and printed into the task file (P-01 to P-11). Items 1, 3, 4 and the register's wording are as described (`copy-serve.sh:429`, not 424, carries the `norm\_custody.%` filter; `copy_record.py:73` as stated). Differences that mattered: **P-04** (`reload-proxy.sh` picks the proxy's first network: with a second network it sorts to the wrong one; fixed); **P-07** (the `images built` line text changed even with an empty name: `a and b are built` became `a, b are built`; nothing matches it); **P-08 to P-11** (item 6).

## 4. Item 6 — why it stops, and what a wider lane starts from

**Stopped at the premise, not at difficulty.** Three findings, each measured (task file P-08 to P-11):

1. **The footprint is outside the grant.** The label `stand-fingerprint-v1` and its marker text are read or pinned by `scripts/stand-copy/restore-test.sh` (extracts the block by marker, compares the whole `fingerprint` JSON), `scripts/recovery/{copy_record_binding,isolated_postgres_restore (also pins the block's SHA-256),synthetic_drill_fixture,...}.py`, and `tests/integration/norms/bundle/{support,test_copy_record}.py`. The importer's caller `src/auditmanager/norms/bundle/stand.py` computes the fingerprint before it reads the record's label. A rename of label and markers alone (no SQL change) reddened **89 tests in three files** (`test_copy_record.py` 10, `test_isolated_postgres_restore.py` 8, `test_stand_copy_refusals.py` 71); measured and reverted (P-11).
2. **`access.%` alone does not fix the stated problem.** A failed sign-in, and the sign-in of an account that had a failed attempt, `UPDATE app_user` (`failed_sign_ins`, `last_failed_sign_in_at`, `sign_in_blocked_until`); `app_user` is fingerprinted whole (P-10). Only a successful sign-in of a clean account is covered by excluding the event. The complete rule needs a decision on those three columns (project `app_user` without them, or leave a failed attempt as a refusal on purpose).
3. **The scenario needs a running writer.** `dump-db` and `attest --test-data` stop `web`, `api` and `worker`, and they stay stopped until `resume`: on a compose stand no sign-in can occur in the window, and one that does means a writer was started, where `fingerprint_drifted` is the right answer. The scenario is real on the local import rehearsal (the API runs outside compose; `W54-LOCAL-IMPORT-01`).

**The compatibility rule the lane decided, for the lane that builds it:** an old-version record is **refused with a clear message**, not re-interpreted. Both versions can be computed in principle (two blocks in `copy-serve.sh`), but `stand.py` computes before it reads the label, so choosing a definition per record needs an edit outside `copy_record.py`; records live twelve hours (`IMPORT_WINDOW`), so refusing costs one re-attest; and comparing a v1 digest under the v2 text would report a difference of definition as "something wrote while the writers were meant to be stopped". New reason, for example `copy_record_fingerprint_version`: `the record was taken under stand-fingerprint-v1; this build compares stand-fingerprint-v2; open a new copy or waiver`. The unknown-label case keeps today's `copy_record_unreadable`.

**What that lane needs in its grant:** `infra/deploy/{copy-serve.sh,lib/forced-command.sh}`, `src/auditmanager/norms/bundle/{copy_record.py,stand.py}` (only if it keeps per-record dispatch), `scripts/stand-copy/restore-test.sh`, `scripts/recovery/*.py` (at least the four above), `tests/integration/norms/bundle/**`, `tests/integration/recovery/**`, `tests/integration/composition/test_stand_copy_refusals.py`, and the prose that says "one SQL text, kept once" (`W54-STAND-COPY-01.md` section 3.5, `STAND-PURGE-TOOL-01.md`, `RECOVERY-REBASE-01.md`). **A cheaper option for the integrator to weigh:** leave the fingerprint as it is and write into the local-rehearsal runbook that the API must be stopped between attest and import (it is the stand's own rule); that costs one paragraph and no tool changes.

## 5. Mutation table

Each row: the mutation was applied to the committed file, the named tests were run with `-x` and had to turn red, the file was restored with `git checkout -- <file>` (restoration asserted by `git diff --quiet`), and the same tests were run again and had to pass. Helper outside the repository (`scratchpad/judge-fixes-f2-01/mut.py`); the table is the record. Every new guard is also shown able to fail **inside the suite** by a test that deletes its marked block from a copy (`test_that_guard_is_shown_able_to_fail`, and for item 1 two more cases with holders on other addresses).

| # | commitment, and the mutation that removes it | file | first red test | restored |
|---|---|---|---|---|
| M1-1 | item 1: the listener table is consulted -- never (the old, loopback-only probe) | `deploy.sh` | `TestPublicPortsFree::test_a_holder_on_any_address_of_the_host_is_refused_before_the_build[127.0.0.2]` | green |
| M1-2 | item 1: IPv6 listeners count -- the `tcp6` table is dropped | `deploy.sh` | `...refused_before_the_build[::1]` | green |
| M1-3 | item 1: only a LISTEN socket holds a port -- the state test is dropped | `deploy.sh` | `test_a_connected_socket_on_that_port_is_not_a_listener` | green |
| M1-4 | item 1: the port is compared -- any listener on the host holds it | `deploy.sh` | `test_the_https_port_is_asked_only_when_this_deploy_would_publish_it` | green |
| M1-5 | item 1: an unreadable table is said -- the note is switched off | `deploy.sh` | `test_without_a_table_the_limit_is_said_and_not_hidden` | green |
| M1-6 | item 1: the loopback connect stays a witness -- dropped | `deploy.sh` | `test_without_a_table_a_loopback_holder_is_still_refused` | green |
| M1-7 | item 1: the own proxy excuses its own port -- `OURS` is never yes | `deploy.sh` | `test_a_port_this_instances_proxy_publishes_on_every_address_is_still_not_foreign` | green |
| M3-1 | item 3: the client is not on the data network -- it is back on `[alpha]` | `compose.acme.yml` | `TestTheAcmeService::test_it_is_on_a_network_of_its_own_and_waits_for_the_proxy_to_have_started` | green |
| M3-2 | item 3: the client shares no network with the data tier -- it joins both | `compose.acme.yml` | `test_it_shares_no_network_with_the_data_tier` | green |
| M3-3 | item 3: the proxy bridges both networks -- it does not join the client's | `compose.acme.yml` | `test_only_the_proxy_and_the_client_are_on_the_client_network` | green |
| M3-4 | item 3: the client can reach the authority -- the network is `internal` | `compose.acme.yml` | `test_the_client_network_is_declared_by_the_overlay_and_is_not_internal` | green |
| M3-5 | item 3: nothing else is on the client network -- `api` joins it (whole file) | `compose.acme.yml` | `test_the_split_finds_what_it_claims_to` | green |
| M3-5b | the same mutation with only the membership test selected | `compose.acme.yml` | `test_only_the_proxy_and_the_client_are_on_the_client_network` | green |
| M3-6 | the throwaway `nginx -t` container is on the `api`'s network -- the proxy's first again | `reload-proxy.sh` | `TestTheThrowawayContainerJoinsTheNetworkTheUpstreamsLiveOn::test_the_throwaway_container_is_on_the_network_of_the_api` | green |
| M4-1 | item 4: the guard is gated on the name -- it fires without one | `deploy.sh` | `TestTrustedProxiesEmptyWithName::test_without_a_name_the_list_is_the_host_nginx_configuration_and_is_left_alone` | green |
| M4-2 | item 4: a list with a name is refused -- the refusal is `if false` | `deploy.sh` | `test_a_list_with_a_name_is_refused_before_docker_is_touched` | green |
| M4-3 | item 4: separators are separators -- a value of commas counts as a list | `deploy.sh` | `test_a_value_with_no_entry_is_the_empty_list_and_is_not_refused[, ,]` | green |

**17 of 17** mutations turned the named tests red, and the restored tree turned them green. Item 6: no code, so no mutations. M4-4 was an equivalent mutant and is not counted. `git status --short` was empty after the last mutation.

## 6. Modified tests: what each asserted before and after (no weakening)

- `test_acme_deploy_guards.py::_free_port` — before: bound `127.0.0.1:0` and returned the port; after: binds `0.0.0.0:0` (a port free on every address; stricter, and the guard asks that question now). Everything else in the file is unchanged; the file grows from 69 to **99** tests (16 in `TestPublicPortsFree`, 14 in the new `TestTrustedProxiesEmptyWithName`). The existing `test_a_held_challenge_port_is_refused_before_the_build`, `test_the_https_port_is_asked_only_when_this_deploy_would_publish_it`, `test_a_port_this_instances_proxy_already_publishes_is_not_foreign` and `test_a_proxy_that_does_not_publish_that_port_does_not_excuse_it` still pass unmodified.
- `test_acme_overlay.py::TestTheAcmeService::test_it_is_on_the_stacks_network_and_waits_for_the_proxy_to_have_started` — before: `networks == ["[alpha]"]`, `depends_on == ["proxy:", "condition: service_started"]`, `restart == ["unless-stopped"]`; after (renamed `test_it_is_on_a_network_of_its_own_and_waits_for_the_proxy_to_have_started`): `networks == ["[acme-edge]"]`, the other two assertions unchanged. This is the intended change of item 3, not a weakening: the new tests next to it assert more (disjoint from the data tier, membership of the client network, declaration, not internal). 125 -> **129**.
- `test_proxy_config_follows_checkout.py` — `DOCKER_STUB`'s `.Networks` branch: before: always printed `an-instance-net`; after: the same unless `STUB_PROXY_NETWORKS` is set for the proxy container (then the sorted list). `_Host.run` takes an optional environment (default none). No existing assertion changed; +3 tests, 14 -> 17 collected (**16 passed, 1 skipped**, the opt-in real stand skipped as before).
- `test_deploy_script_refusals.py::test_every_guard_in_the_script_has_a_case_here` — before: 30 markers, the covered set `BEFORE_DOCKER | STAND_GUARDS | {...} | ACME_GUARDS | DEPLOY_GATE_GUARDS`, each ACME guard named in `test_acme_deploy_guards.py`; after: 31 and `| JUDGE_FIX_GUARDS` (`trusted-proxies-empty-with-name`), which must be named in `test_acme_deploy_guards.py` by the same loop. Collected 88 before, 88 after.

## 7. Commands and results

`BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages)`, `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <file>`, one pytest at a time, no docker, no network, no database. On the committed tree before the report was added:

| target | result |
|---|---|
| `test_acme_deploy_guards.py` | 99 passed (69 before) |
| `test_acme_overlay.py` | 129 passed (125 before) |
| `test_proxy_config_follows_checkout.py` | 16 passed, 1 skipped (opt-in real stand) |
| `test_deploy_script_refusals.py` | 88 passed |
| `test_acme_client.py` / `test_proxy_tls_path.py` | 48 / 16 passed |
| `test_deploy_image_identity.py` / `test_deployed_stack_probe.py` / `test_verify_deployed_certificate.py` | 23 / 32 / 15 passed |
| `test_reset_script_refusals.py` / `test_stand_copy_refusals.py` / `test_stand_copy_fresh.py` | 61 / 158 passed + 1 skipped / 35 passed |
| `test_default_credential_gate.py` / `test_readiness_command.py` | 106 / 46 passed |
| `test_exposure_text_is_current.py` / `test_purge_product_data_script.py` / `test_session_register_volume.py` / `test_real_client_address_at_the_edge.py` | 12 / 41 / 5 / 47 passed |
| `tests/contract/test_proxy_security_headers.py` / `tests/contract/test_deploy_auto_workflow.py` | 15 / 8 passed |
| governance one-liner on the task file | `[]` |

The final doc-guard run (`tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`, `git diff --check`) is recorded in the lane's final message, after the last commit (one contract test refuses a dirty tree).

## 8. Integration notes

1. **Merge**: `infra/**`, the runbook, four test files and the two docs; no `.github/**`, `contracts/**`, migrations, `src/**`, `scripts/**`, lock files. Proof in section 10.
2. **Gate class**: `infra/**` is in the full-gate class (`AGENTS.md` section 8); under `R-135` the full gate is deferred and was not run (no docker). The container-free tests and the mutation probes were.
3. **Unobserved, by the lane's constraints**: how compose merges the proxy's two `networks:` lists and attaches a service to a second network (the overlay lists both names so either reading gives the same result); that the proxy still resolves `api` and `web` on the data network while also on `acme-edge`; that `docker run --network <data net>` for the throwaway container works as before. The first real run is a deploy with a name set.
4. **A live host that set a name before this lane and kept `ALPHA_TRUSTED_PROXY_CIDRS`** is refused at its next deploy with one line to delete. The owner's checklist is runbook section 6.
5. **`ADR-0021` row 9's spelling** (`[stand-copy-fresh]` against the printed `[stand_copy_fresh]`) and the `repository.py` docstring ("exactly two places") are the integrator's, as `PROD-02-03` said; this lane did not touch them.
6. **`D-229`'s own check command** for item 1 (`rg -n 'public-ports-free' infra/deploy/deploy.sh` shows a probe that does not use `/dev/tcp/127.0.0.1` alone) now holds; the `access\.%` check for item 6 does not, and the row should keep item 6 open with section 4 as its note.

## 9. Limits

- Item 6 is open; see section 4 for the footprint, the incomplete premise and the compatibility rule decided for it.
- `port-not-foreign` (`ALPHA_HTTP_PORT`, loopback by design) still probes `127.0.0.1` only. A wildcard listener on that port is seen by it; a listener bound to the host's own address would not collide with a loopback publish. Left as it was: it is not name-gated, and the "empty name = unchanged" claim is what item 2 is about.
- On a host with no `/proc/net/tcp*` the guard answers for loopback only and says so; a listener on another address is not seen there.
- The refusal of item 1 does not tell *which* process holds the port (the table has no process names without root); the message gives the `ss -ltnp` line that does.
- The `NOTE` and the refusals are tested against stubs for `docker`; the real daemon was never asked.

## 10. Forbidden paths are untouched

`git diff --name-only 07e2e8ba..HEAD | grep -E '^(\.github/|contracts/|db/migrations/|web/|scripts/|src/|uv\.lock|pyproject\.toml|tests/integration/(norms|recovery)/)'` prints nothing. The migration head is `0033_ar_v3_cite_stage_id`, unchanged; the API contract is `1.6.0`, unchanged. `git status --short` is clean after the last commit.
