# PROD-02-03-DEPLOY-GATES-01 — the default-credential gate and the fresh-copy receipt in the deploy path

Task: `docs/program/tasks/PROD-02-03-DEPLOY-GATES-01.md`. Branch `agent/prod-02-03-deploy-gates-01`, base `2aec4207` (`integration/ar-close-1026`), lane I2 of wave `PW3`. Rulings: `R-146i`, `R-146s`, `R-146t`, `R-146x`, `R-146z`, `R-52`, `R-46`, `R-93` (binds); `ADR-0021` sections 2 and 5 and commitments 6 and 9; `ADR-0023` section 3 and commitment 9; `AD-03`, `AD-11`, `AD-17`, `AD-19`; debt `D-227` item 5 and item 6.

**Status.** Built and verified in the tree with stubbed `docker`; nothing was run against a host, a real compose project or a certificate authority (no docker, no network in the lane). The first real run of the restore paths and of the proxy-only recreation is the owner's or the integrator's (section 8).

## 1. What was built, and what the lane decided

**`PROD-02`.** `src/auditmanager/access/check.py --gate` answers one question: is the published pair (`admin` / `password`) valid? A finding is an **active** account with the seeded login whose stored credential *verifies* against `SHIPPED_DEFAULT_PASSWORD`; every other must-change account is a `GATE WARNING temporary password` line that never moves the status (`R-146z`); status 2 when the database or the stored credential could not be read. The default mode and its sentinels are untouched (`readiness.sh` greps them). Everything that reads the answer goes through `infra/deploy/lib/proxy-listeners.sh`: `listeners_gate_verdict` (the sentinel **and** the status must agree, anything else is `unknown`), `listeners_gate_run`, `listeners_https_wanted` (`yes` only for the setting `yes` AND a `clean` gate), `listeners_https_published`, `listeners_apply_https` (recreates **only** the proxy with the compose files the decision names) and `listeners_withhold_https`.

- `deploy.sh`: guard `default-credential-gate` after `migrations-at-head` (typed words `[default_credential]`, `[default_credential_unanswered]`, exit 3), guard `listeners-library-present` (the library is sourced for every deploy now), and a two-step 443 decision (provisional before `up`, final after the gate).
- `verify-deployed.sh`: step `default-credential-gate` after the certificate section; exit **8** on the pair, 4 when the gate could not be answered; says loudly when 443 is published meanwhile.
- `reset.sh --restore`: after the existing report it asks the gate and withdraws 443 on a finding; exit 0 for a completed restore, **5** when 443 could not be withdrawn.
- `copy-serve.sh restore-db`: after the fingerprint comparison it raises every `token_epoch` (`R-52`), asks the gate, withdraws 443 on a finding; `status` prints the library's digest.

**`PROD-03`.** `deploy.sh` guard `stand-copy-fresh` (typed word `[stand_copy_fresh]`, before the build): with the `real_data` marker present and the checkout's head differing from `alembic_version`, it refuses unless the record is open, has its dump (SHA-256), the attestation binds that SHA-256 and this commit, and `quiesced_at` is at most 24 hours old. No new dump script. Also fixed: the two stale `proxy/compose.tls.yml` hint lines of `reload-proxy.sh` (`D-227` item 5). Both `D-227` item 6 ("restore paths not wired to the gate") and the PROD-02/03 rows of the plan are what this lane delivers.

**Decided by the lane** (the window asked for no questions; each is small and reversible):

1. **The gate reads the credential itself, with one read-only SELECT in `check.py`.** `UserRepository.authenticate` writes (a failed attempt counts and five shut the account; a shut account answers "no" without consulting the password, so a locked seeded account would read as clean; a success journals). `repository.py` is not to be edited, so `check.py` becomes a third reader of the credential columns; the repository docstring still says "exactly two places" (section 7).
2. **The 443 decision is two steps** because the gate needs the database and the database needs `up`: the full `up` never *opens* 443 (it keeps an already published one only if the setting still says `yes` and a pair exists); the gate step then opens it (`yes` + pair + clean) or withdraws it (a recreate of the proxy alone). A deploy that changes nothing issues no proxy-only `up` (`W24-IDEM`).
3. **A deploy leaves the proxy as it is when the gate is `unknown`** (the deploy refuses, opens nothing, closes nothing: the door was cleared by an earlier clean gate and the deploy does not change `app_user`); **a restore treats `unknown` as a finding** (the credentials were just replaced wholesale, so "I could not look" is not "fine").
4. **A completed restore keeps exit 0 on a finding** (`R-52`, the cases above it assert it); only "the door could not be shut" is a new status, 5. In `restore-db` the same two failures are guards (`credentials-revoked`, `https-withheld`) because its writers are still stopped: refusing there exposes nothing and keeps `resume` from following a restore whose credentials are live.
5. **The typed word is `[stand_copy_fresh]`**, the family's spelling (`[stand_copy_unattested]`, `[stand_import_open]`); `ADR-0021` row 9 writes `[stand-copy-fresh]`, which is the guard's name. The message names both. Section 7.
6. **The dump file is not stat'ed.** Its stamp directory is `0700` and may be unsearchable to the deploy account; the attestation of the dump's SHA-256 is what proves the dump was read.
7. **"Pending" is "the checkout's head set differs from `alembic_version`"** (the ADR's wording): a database *ahead* of the checkout also needs the receipt, and two heads in the checkout are two heads. A database that cannot be read while the marker exists is a refusal that names the way out (`docker compose ... up -d postgres`).
8. **24 hours is a literal** (`STAND_FRESH_SECONDS=86400`), not an environment override; a `quiesced_at` more than 5 minutes in the future is refused (clock skew tolerated, a forged future is not).
9. **`readiness.sh` is not edited**: it keeps the wider question and `R-46`; the new tests pin that its call has no `--gate`.
10. **`restore-db` needs `lib/proxy-listeners.sh` installed beside `copy-serve.sh`** and refuses without it *before it stops anything* (`listeners-library-present`); every other verb is unaffected, so an unreinstalled copy key degrades one verb and not all of them.

## 2. Files

`git diff --name-status 2aec4207..HEAD` before this report was added (20 files, 2880 insertions, 81 deletions):

```
M  docs/program/DEPLOYMENT_RUNBOOK.md                              sections 3, 4, 6, 7, 9, 13
A  docs/program/tasks/PROD-02-03-DEPLOY-GATES-01.md
M  infra/deploy/copy-serve.sh                                      restore-db: revoke, gate, withdraw; status; 3 guards
M  infra/deploy/deploy.sh                                          3 guards; two-step 443 decision
M  infra/deploy/env/alpha.env.example                              comment: the setting is the operator's half
M  infra/deploy/lib/proxy-listeners.sh                             the credential gate (7 functions)
M  infra/deploy/reload-proxy.sh                                    the two stale hint lines
M  infra/deploy/reset.sh                                           --restore ends with the gate; 1 guard
M  infra/deploy/verify-deployed.sh                                 exit 8
M  src/auditmanager/access/check.py                                --gate
A  tests/unit/access/test_access_check_gate.py                     29 tests, no database
A  tests/integration/composition/test_default_credential_gate.py   106 tests
A  tests/integration/composition/test_stand_copy_fresh.py          35 tests
M  tests/integration/composition/test_acme_deploy_guards.py        (section 5)
M  tests/integration/composition/test_deploy_image_identity.py
M  tests/integration/composition/test_deploy_script_refusals.py
M  tests/integration/composition/test_deployed_stack_probe.py
M  tests/integration/composition/test_proxy_config_follows_checkout.py
M  tests/integration/composition/test_reset_script_refusals.py
M  tests/integration/composition/test_stand_copy_refusals.py
```

The report you are reading, `docs/program/PROD-02-03-DEPLOY-GATES-01.md`, is the twenty-first path (added in the last commit).

## 3. Premise

Fourteen reads, re-run against `2aec4207` and printed into the task file (P-01 to P-14). All present. The three that changed the design: **P-03** (`authenticate` writes, so the gate reads the credential itself), **P-05** (the database exists only after `up`: two-step decision) and **P-10** (the head is `0033_ar_v3_cite_stage_id`, not `0032` as the PW2B text says; the pending test reads the head out of the files). **P-12**: there was no unit test of `check.py` (the existing ones are subprocess runs against a database), so the brief's "check tests" are new.

## 4. Mutation table

Each row: the mutation was applied to the committed file with the named tests run `-x`, had to turn them red, and the file was restored with `git checkout` (restoration is asserted by the helper). Scratch helper outside the repository (`scratchpad/i2-deploy-gates/mut.py`); the table is the record.

| # | commitment, and the mutation that removes it | file | first red test |
|---|---|---|---|
| C1 | a finding exists: the finding branch of `gate_report` is `if False` | `check.py` | `test_the_published_pair_is_the_finding_and_only_it` |
| C2 | the credential is verified: `seeded_account_accepts_...` returns `False` | `check.py` | `test_the_seeded_credential_verifies` |
| C3 | an archived `admin` is not the pair: `archived_at IS NULL` dropped | `check.py` | `test_it_is_one_read_only_statement_addressed_to_the_active_seeded_login` |
| C4 | the seeded account is a finding, not also a warning: the skip removed | `check.py` | `test_the_published_pair_is_the_finding_and_only_it` |
| C5 | a temporary password only warns (`R-146z`): status 1 when `must_change` is non-empty | `check.py` | `test_a_temporary_password_an_administrator_issued_only_warns` |
| C6 | the gate never signs in: `authenticate` called | `check.py` | `test_the_pair_valid_exits_1_names_the_login_and_touches_nothing_else` |
| C7 | a credential that cannot be verified is not "no": the exception swallowed | `check.py` | `test_a_credential_this_build_cannot_verify_is_an_error_and_not_a_no` |
| C8 | an unknown argument is status 2: the refusal removed | `check.py` | `test_an_argument_it_does_not_know_is_status_2_and_runs_neither[--gtae]` |
| C9 | a locked account is still a finding: `sign_in_blocked_until IS NULL` added | `check.py` | `test_it_is_one_read_only_statement_...` |
| L1 | `https_wanted` needs the gate: the verdict ignored | `proxy-listeners.sh` | `TestHttpsIsWantedOnlyOnTwoYeses::test_the_table[finding-yes]` |
| L2 | sentinel and status must agree: status ignored for `clean` | `proxy-listeners.sh` | `test_the_table[clean-text-and-status-1]` |
| L3 | the sentinel is a whole line: `-x` dropped | `proxy-listeners.sh` | `test_the_table[the-sentinel-must-be-a-whole-line]` |
| L4 | a withdrawal is checked: the second `docker port` removed | `proxy-listeners.sh` | `TestWithdrawing443::test_a_published_443_is_withdrawn_and_then_asked_again` |
| L5 | the recreate uses the decision: forced `yes yes` | `proxy-listeners.sh` | `test_the_overlay_list_follows_the_decision[yes-no-False]` |
| L6 | only the proxy is recreated: `--no-deps` dropped | `proxy-listeners.sh` | `test_the_overlay_list_follows_the_decision[yes-yes-True]` |
| L7 | the gate does not read the caller's stdin: `</dev/null` dropped | `proxy-listeners.sh` | `test_it_does_not_read_the_callers_standard_input` |
| L8 | the narrow mode is asked: `--gate` dropped | `proxy-listeners.sh` | `test_the_command_and_the_three_globals` |
| D2 | an unanswered gate refuses | `deploy.sh` | `test_a_gate_that_cannot_be_answered_refuses_by_itself[unknown]` |
| D3 | 443 needs the gate: `HTTPS_FINAL` is the setting alone | `deploy.sh` | `test_443_is_published_at_the_end_only_on_three_yeses[yes-pair-present-finding-443-closed-before]` |
| D4 | the gate step converges the proxy: `if false` | `deploy.sh` | `test_443_is_published_at_the_end_only_on_three_yeses[yes-pair-present-clean-443-closed-before]` |
| D5 | the full `up` never opens 443: provisional = the setting | `deploy.sh` | same row, `first_full` assertion |
| D6 | 24 hours: the constant is 240 hours | `deploy.sh` | `test_it_refuses_before_any_build[older-than-24-hours]` |
| D7 | the marker is read: the path is wrong | `deploy.sh` | `TestTheControls::test_no_pending_migration_needs_no_receipt_at_all` |
| D8 | a pending migration needs the receipt: `if false` | `deploy.sh` | `test_a_good_receipt_lets_the_migrating_deploy_through_and_says_which` |
| D9 | a forged future `quiesced_at` is refused | `deploy.sh` | `test_it_refuses_before_any_build[from-the-future]` |
| D10 | the attestation binds this dump | `deploy.sh` | `test_it_refuses_before_any_build[attests-another-dump]` |
| D11 | the record must be open | `deploy.sh` | `test_it_refuses_before_any_build[closed-record]` |
| D12 | an unreadable database is a refusal | `deploy.sh` | `test_a_database_that_cannot_be_read_is_a_refusal_with_the_way_out` |
| D13 | attested for this commit | `deploy.sh` | `test_the_r93_guard_speaks_first_and_this_one_agrees_without_it[attested-for-another-commit]` |
| D14 | the library must be there | `deploy.sh` | `test_a_clone_without_it_is_refused_before_docker_is_touched` |
| V2 | exit 8 is its own status | `verify-deployed.sh` | `test_the_published_pair_is_exit_8_and_names_the_login` |
| V3 | an unanswered gate is not a pass | `verify-deployed.sh` | `test_a_gate_that_cannot_be_answered_is_exit_4_and_never_a_pass[unknown]` |
| V4 | a published 443 is said loudly | `verify-deployed.sh` | `test_and_it_says_so_loudly_when_443_is_published_meanwhile` |
| R2 | a finding withdraws 443 | `reset.sh` | `test_the_published_pair_back_recreates_the_proxy_without_the_443_overlay` |
| R3 | a door that cannot be shut is exit 5 | `reset.sh` | `test_a_door_that_cannot_be_shut_is_exit_5_and_says_the_command` |
| R4 | after a restore `unknown` is a finding | `reset.sh` | `test_an_unanswerable_gate_after_a_restore_is_treated_as_a_finding` |
| R5 | the gate is actually asked | `reset.sh` | `test_the_gate_is_asked_inside_the_api_image_after_the_credentials_are_revoked` |
| S1 | `restore-db` raises every epoch | `copy-serve.sh` | `test_restore_db_raises_every_epoch_after_the_fingerprint_check_and_asks_the_gate_last` |
| S2 | after a restore `unknown` is a finding | `copy-serve.sh` | `test_the_published_pair_back_recreates_the_proxy_without_the_443_overlay[2-unknown]` |
| S3 | `status` prints the library's digest | `copy-serve.sh` | `test_status_prints_the_digest_of_the_installed_library` |
| S4 | a failed revoke refuses | `copy-serve.sh` | `test_each_guard_refuses_and_its_deletion_stops_the_refusal[copy-serve.sh:credentials-revoked]` |
| H1 | the reload-proxy hint names both overlays | `reload-proxy.sh` | `test_reload_proxy_names_both_overlays_in_its_hint` |

**Guard deletions inside the suites** (a test deletes the marked block from a copy and shows the refusal gone, as the repository's other guards are held): `deploy.sh` `stand-copy-fresh` (ten wrong receipts, each also run unguarded: the deploy goes on to build), `default-credential-gate` (the pair no longer fails the deploy, and a published 443 stays open), `listeners-library-present`; `verify-deployed.sh` step `default-credential-gate`; `reset.sh` `listeners-library-present`; `copy-serve.sh` `listeners-library-present`, `credentials-revoked`, `https-withheld`. `stand-copy-unattested` and `stand-copy-other-target` are deleted *together* (and not `stand-copy-fresh`) to show the new guard refuses those two states on its own, then all three are deleted to show the deploy goes on.

## 5. Modified tests: what each asserted before and after

No assertion was weakened. Where a count or a call shape had to move, both are stated.

- `test_deploy_script_refusals.py`: `_stage` — before: staged `deploy.sh` alone; after: also `lib/proxy-listeners.sh` (the library is sourced for every deploy; param `with_listeners=True`). `DOCKER_STUB` — after: one branch answering the gate (clean by default). `test_every_guard_in_the_script_has_a_case_here` — before: 27 markers, the set `BEFORE_DOCKER | STAND_GUARDS | {...} | ACME_GUARDS`; after: 30 and `| DEPLOY_GATE_GUARDS`, and each of the three must be named in `test_stand_copy_fresh.py` / `test_default_credential_gate.py`. Collected 88 before, 88 after.
- `test_acme_deploy_guards.py`: stub answers the gate and (new) every test passes. `_up_line` — before: exactly one `up` in the log; after: exactly one **full** `up` (not `up -d --no-deps proxy`), plus `_proxy_up_lines`. `test_cleared_and_a_pair_publishes_443_after_the_acme_overlay` — before: the single `up` carried the acme then the tls overlay and stdout said `-- published`; after: the full `up` carries acme and not tls, exactly one proxy-only `up` carries acme then tls, stdout says `published on port` and `(the credential gate is clean)`. `test_a_pair_but_not_cleared_keeps_443_closed` — before: no tls on the `up`; after: also no proxy-only `up` (strengthened). 69 before, 69 after.
- `test_deploy_image_identity.py`: staging copies the library; stub answers the gate; assertions unchanged. 23 / 23.
- `test_deployed_stack_probe.py`: `world` stages the library; stub answers the gate (and the harness exposes `docker port` to the new file); assertions unchanged. 32 / 32. `test_verify_deployed_certificate.py` is unchanged and passes through that harness (15 / 15).
- `test_reset_script_refusals.py`: `_staged` and `_mutant` copy the library; `STAGING_STUB` gains the gate, `ps --quiet proxy`, `docker port` and the proxy-only `up` (stateful: after it the proxy publishes nothing). `test_a_dump_directory_that_is_not_one_of_ours_is_refused` — before: staged `reset.sh` by hand in a directory without the library; after: uses `_staged` (same assertions; the restore now sources the library before `restore-complete`). Guard count 13 → 14 (`listeners-library-present`). The `R-52` cases (exit 0 on a finding, the report, the revoke order) are unchanged and green. 52 → 61.
- `test_stand_copy_refusals.py`: the stage installs `lib/proxy-listeners.sh` beside the script; the `docker` stub reads the compose sub-command after any number of `--env-file`/`--file` pairs (before: `argv[5]`, which assumed one file) and answers `access.revoke`, `access.check --gate`, a proxy-only `up` and `docker port`; `GUARD_CASES` +3. `test_restore_db_quiesces_again_checks_the_digest_and_leaves_the_writers_stopped` is unchanged and green. 147 → 159 (158 passed, the one window-gated test skipped as before).
- `test_proxy_config_follows_checkout.py`: `_Host` and `Stand` stage the library and their stubs answer the gate; assertions unchanged. 14 → 14 (13 passed; the opt-in real-docker stand skipped, as before).

## 6. Commands and results

One pytest at a time, `PYTHONPATH=src:$BS`, `-c pyproject.toml --rootdir=. -q -p no:cacheprovider`; none of these needs docker (the host's `docker` was never called) and none needs a database except where stated.

| target | result |
|---|---|
| `tests/unit/access` | 117 passed (88 before + 29 new) |
| `test_default_credential_gate.py` | 106 passed |
| `test_stand_copy_fresh.py` | 35 passed |
| `test_deploy_script_refusals.py` | 88 passed |
| `test_acme_deploy_guards.py` | 69 passed |
| `test_deploy_image_identity.py` | 23 passed |
| `test_deployed_stack_probe.py` | 32 passed |
| `test_verify_deployed_certificate.py` | 15 passed |
| `test_reset_script_refusals.py` | 61 passed |
| `test_stand_copy_refusals.py` | 158 passed, 1 skipped (window-gated, as before) |
| `test_proxy_config_follows_checkout.py` | 13 passed, 1 skipped (opt-in real stand, as before) |
| `test_acme_overlay.py` / `test_readiness_command.py` / `test_proxy_tls_path.py` | 125 / 46 / 16 passed |
| `test_exposure_text_is_current.py` / `test_purge_product_data_script.py` / `test_session_register_volume.py` | 12 / 41 / 5 passed |
| with the lane `.env`: `test_settings_defaults.py`, `test_reset_rehearsal_counts_base_tables.py` | 34, 5 passed (they error without the lane stack; unrelated to this change) |
| `tests/integration/releases/test_deployment_flow.py`, `tests/integration/norms/bundle/test_copy_record.py`, `tests/unit/scripts/test_manual_scan.py` | 2, 25, 39 passed |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` (after the last code commit) | 105 passed |
| `tests/contract/test_proxy_security_headers.py tests/contract/test_deploy_auto_workflow.py` | 23 passed |
| `git diff --check 2aec4207..HEAD` | clean |
| governance one-liner on the task file | `[]` |
| `shellcheck -s bash` on the six scripts | only findings that were already there (`SC1087` in `reset.sh`, `SC2034 FC_NAME`, `SC1091`/`SC2016` info) |

**One real-database confirmation** (read-only SELECTs, the integrator's lane DB, nothing written): `python -m auditmanager.access.check --gate` against it printed `access-check GATE DEFAULT CREDENTIAL: login=admin ...` and exited 1 (its seeded `admin` is still on `password`); the default mode exited 1 with its unchanged lines; `--gtae` exited 2. The clean and the temporary-password rows are covered by the unit tests only.

## 7. Integration notes

1. **A stand whose `admin` is still on `password` will refuse its next deploy** (`[default_credential]`, exit 3; the workflow's verify step then does not run). That is `R-146s` working, but it lands on a stand the lane could not inspect: confirm the administrator's password has been changed before this reaches `origin/main`, or expect the first deploy after it to fail once.
2. **The copy key must be re-installed** (runbook section 13, step 2 now lists four files): `restore-db` refuses without `lib/proxy-listeners.sh` and says so before stopping anything; `status` shows `listeners: absent`. Recorded as an owner step with installing the key and taking the first real copy (runbook section 13, "Owner steps").
3. **Not edited, by the allowed paths; the integrator may want to:** `infra/deploy/README.md` (its TLS section, around line 394, describes the listeners and says nothing of the gate); the docstring of `src/auditmanager/access/repository.py` ("the credential columns are read in exactly two places"), which `check.py --gate` now makes three; `ADR-0021` row 9 spells the typed word `[stand-copy-fresh]` where the deploy prints `[stand_copy_fresh]` (the guard's name is the former).
4. The 24-case table `test_443_is_published_at_the_end_only_on_three_yeses` is the executable form of `ADR-0021` row 6; the stateful stub models "recreating a compose service changes its published ports" (the unobserved assumption of section 8).
5. A `main` window needs a complete gate for a change under `infra/**` (`AGENTS.md` section 8); `make gate` was not run (`R-135`, no docker). The deferred checks are section 8.
6. `tests/integration/composition/**` is shared by the PW2b/PW3 lanes only through files this lane edited; no `conftest.py`, `tests/support/**` or fixture file changed.
7. The scratchpad directory is **shared by concurrently running lanes**: another lane overwrote a helper of this lane's (`mutate.py`) mid-session. The lane moved to its own subdirectory; the integrator may want to put the lane id in the scratchpad path in future briefs.

## 8. Limits and what was not done

- **Not observed**: a real `docker compose up -d --no-deps proxy` with and without the 443 overlay (that compose recreates the proxy alone, leaves the other services, and that `docker port` then answers as the stub models); a real `restore-db` or `reset.sh --restore` on a copy; a real migrating deploy under the receipt. The stubs are exact about argument shapes, not about docker.
- **Unresolved by design**: the first deploy on a fresh host ends non-zero (documented in runbook section 3). A restore that brings the pair back makes the site unreachable from outside until an administrator changes the password through the tunnel (`R-146s`).
- **Owner steps recorded, not done**: install the copy key (four files) and take the first real copy (runbook section 13), which writes the `real_data` marker that arms `stand-copy-fresh`.
- The gate ignores `is_default_credential` on the seeded account: if its digest verifies against `password` it is a finding even with the flag clear (a restored or hand-edited row); the flag is used only for the warning lines.
- `tests/integration/auth/*` (subprocess runs of `access.check` against the lane database, which insert and delete `app_user` rows) were not run: `main()` kept its default behaviour and the manual run above exercised the module entry point.
- The opt-in disposable-stand tests of `test_proxy_config_follows_checkout.py` need real containers and were not run; their staging was updated for the library and the gate.
- Time-dependent cases use the real clock with margins of minutes; a host with a clock more than five minutes off would see the 24-hour boundary cases shift.

## 9. Forbidden paths are untouched

`git diff --name-only 2aec4207..HEAD | grep -E '^(\.github/|contracts/|db/migrations/|web/|uv\.lock|pyproject\.toml|infra/deploy/README\.md|infra/deploy/readiness\.sh|src/)'` prints one line, `src/auditmanager/access/check.py`, which is allowed. No file under `.github/`, `contracts/`, `db/migrations/`, the web, any other `src/` (in particular not `access/repository.py`), a lock file, `infra/deploy/README.md` or `readiness.sh` is in the diff. The migration head is `0033_ar_v3_cite_stage_id`, unchanged; the API contract is `1.6.0`, unchanged. `git status --short` is clean after the last commit.
