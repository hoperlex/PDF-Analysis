# Task PROD-02-03-DEPLOY-GATES-01 — a deployment fails while admin/password is valid, and a migrating deploy follows a fresh copy receipt

task_id: PROD-02-03-DEPLOY-GATES-01
status: completed in development candidate (nothing run against a host; see the report)

## Outcome

`PROD-02` and `PROD-03` of `PRODUCTION-READINESS-PLAN-01` as one infra lane (`R-146i`, `R-146s`, `R-146t`, `R-146x`, `R-146z`; `AD-03`, `AD-11`, `AD-17`, `AD-19`): **(1)** `deploy.sh` and `verify-deployed.sh` run the default-credential gate (`python -m auditmanager.access.check --gate` in the `api` image) and end non-zero naming the login while the published seeded pair (`admin` / `password`) is valid, and 443 is published only when `ALPHA_PUBLISH_HTTPS=yes` AND a pair exists AND the gate is clean; a temporary password an administrator issued is a warning line and never fails the gate; `reset.sh --restore` and `copy-serve.sh restore-db` end with the same gate and recreate only the proxy without the 443 overlay on a finding, and `restore-db` raises every `token_epoch` as `reset.sh --restore` does. **(2)** `deploy.sh` has the guard `stand-copy-fresh`: with the `real_data` marker present and a migration pending it refuses unless the copy record is open, has its dump, is attested for this commit and was quiesced at most 24 hours ago; no new dump script. The two stale compose-hint lines of `reload-proxy.sh` are fixed.

## Depends on

- `PROD-01-TLS-ACME-01` — merged into the base (`ALPHA_PUBLISH_HTTPS`, `infra/deploy/lib/proxy-listeners.sh`, the five `deploy.sh` ACME guards).
- `ADR-0021` sections 2 and 5, commitments 6 and 9; `ADR-0023` section 3, commitment 9.
- `R-93` (continues to bind), `R-110`, `R-146i`, `R-146s`, `R-146t`, `R-146x`, `R-146z`, `R-52`, `R-46`.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.6.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable
- migration head: unchanged (`0033_ar_v3_cite_stage_id`)
- base commit: `2aec4207` (`integration/ar-close-1026`), branch `agent/prod-02-03-deploy-gates-01`

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: infra/deploy/deploy.sh
- enumerator_owner: PROD-02-03-DEPLOY-GATES-01 (the lane owns `infra/**` and `DEPLOYMENT_RUNBOOK.md` in wave PW3; `test_every_guard_in_the_script_has_a_case_here` pins the set and its count)
- totality_query: `python3 -I -c "import re;print(sorted(re.findall(r'^# >>> guard: ([a-z-]+)$',open('infra/deploy/deploy.sh',encoding='utf-8').read(),re.M)))"`

The set is the marked guard blocks of `deploy.sh`: 27 before, 30 after (`stand-copy-fresh`, `default-credential-gate`, `listeners-library-present`). `reset.sh` goes from 13 to 14 (`listeners-library-present`) and `copy-serve.sh` gains three (`listeners-library-present`, `credentials-revoked`, `https-withheld`); the three suites that pin those sets name every one.

## Captured premise evidence

- premise: fourteen reads the plan, the ADRs and the brief rely on, re-run against the base commit `2aec4207` with `git show` (so they stay true after the lane's edits); all are present, the differences that matter are P-03 (`authenticate` writes, so the gate reads the credential itself), P-05 (the database exists only after `up`, so the 443 decision is made in two steps) and P-10 (the head is `0033`, not `0032`)

### P-01 — check.py at the base has the default mode only: three statuses, two stable sentinels, no gate mode and no argument handling
- captured_at: 2026-10-26
- command: `git show 2aec4207:src/auditmanager/access/check.py | grep -nE '^(CLEAN_SENTINEL|FINDING_PREFIX)|^def (main|run_check)|^    return [012]$|gate'`
- captured_output:
  ```text
  11:It is **not** wired into ``make check-db`` or any gate. That target belongs to
  62:CLEAN_SENTINEL = "access-check OK no default credentials"
  65:FINDING_PREFIX = "access-check DEFAULT CREDENTIAL"
  88:def run_check(settings: DatabaseSettings | None = None) -> int:
  158:    return 1
  161:def main() -> int:
  ```
- interpretation: `main()` takes no arguments; `run_check` returns 0 (nothing on a default credential) or 1 (at least one account has `is_default_credential`), `main` returns 2 on a read failure. `readiness.sh` greps `CLEAN_SENTINEL` and `FINDING_PREFIX`, so the default mode keeps them. The narrower mode does not exist (the ADR's "stricter than the gate" remark describes this default mode).

### P-02 — the published pair exists twice, in migration 0006 and in policy.py, and that is the pair the gate looks for
- captured_at: 2026-10-26
- command: `git show 2aec4207:db/migrations/versions/20260922_0006_app_user.py | grep -nE '^SEED_(LOGIN|PASSWORD)'; git show 2aec4207:src/auditmanager/access/policy.py | grep -n '^SHIPPED_DEFAULT_PASSWORD'`
- captured_output:
  ```text
  99:SEED_LOGIN = "admin"
  100:SEED_PASSWORD = "password"  # noqa: S105 - the owner's deliberate default; see the docstring
  101:SHIPPED_DEFAULT_PASSWORD: Final[str] = "password"  # noqa: S105 - the published default
  ```
- interpretation: Login `admin` (seeded by 0006, the migration's `SEED_LOGIN`) and password `password` (`SEED_PASSWORD`, and `SHIPPED_DEFAULT_PASSWORD` in `policy.py`). The login has no second copy in `src/` at the base, so the lane adds `SEEDED_ADMIN_LOGIN` to `check.py` and guards it, like the password, with a unit test that reads the migration's literal.

### P-03 — UserRepository.authenticate WRITES (counts a failed attempt, can shut the account, journals a success), and the credential columns are documented as read in exactly two places
- captured_at: 2026-10-26
- command: `git show 2aec4207:src/auditmanager/access/repository.py | grep -nE 'exactly two places|def authenticate|self._note_a_failed_sign_in\(session|session.execute\(_CLEAR_ONE'`
- captured_output:
  ```text
  10:**The credential columns are read in exactly two places, and both are named.**
  273:#: "credential columns are read in exactly two places" claim above -- the login already
  556:    def authenticate(self, session: Session, login: str, password: str) -> UserRecord | None:
  635:                self._note_a_failed_sign_in(session, normalized)
  639:            self._note_a_failed_sign_in(session, normalized)
  645:        session.execute(_CLEAR_ONE, {"login": normalized})
  839:                self._note_a_failed_sign_in(session, login)
  844:            self._note_a_failed_sign_in(session, login)
  969:            rows = session.execute(_CLEAR_ONE, {"login": normalize_login(login)}).all()
  ```
- interpretation: So the gate cannot ask the password through `authenticate`: a failed attempt would count against the seeded account (and five of them shut it), a shut account answers `None` without consulting the password (a locked seeded account would read as clean), and a success would clear counters and journal an event. The brief forbids editing `repository.py`, so `check.py` reads the four credential columns itself with one read-only SELECT. That is a third reader; the docstring above still says two. Reported for the integrator, not edited here.

### P-04 — the shared listener library at the base: three functions, and a `https_wanted` argument that the caller computes from the setting alone and that PROD-02 is to replace
- captured_at: 2026-10-26
- command: `git show 2aec4207:infra/deploy/lib/proxy-listeners.sh | grep -nE '^listeners_[a-z_]+\(\)|PROD-02|In THIS lane'`
- captured_output:
  ```text
  5:# Sourced, never run. `deploy.sh` and `verify-deployed.sh` source it today; `PROD-02` makes
  9:# install when `PROD-02` wires it in; nothing in this lane changes `copy-serve.sh`.)
  27:#   https_wanted    `yes` when the credential gate is satisfied. In THIS lane that is the explicit
  28:#                   setting `ALPHA_PUBLISH_HTTPS=yes`; `PROD-02` replaces the caller's computation of
  43:listeners_name_problem() {
  83:listeners_overlay_files() {
  108:listeners_https_verdict() {
  ```
- interpretation: `listeners_name_problem`, `listeners_overlay_files`, `listeners_https_verdict`; the header says `PROD-02` makes `reset.sh --restore` and `copy-serve.sh restore-db` call the same functions. Nothing in the library runs docker or asks about the credential.

### P-05 — deploy.sh at the base: 27 guards; the one `up` precedes `migrations-at-head`; no call to access.check; PUBLISH_HTTPS is the whole of the 443 decision
- captured_at: 2026-10-26
- command: `git show 2aec4207:infra/deploy/deploy.sh | grep -nE '^compose up -d|^# >>> guard: migrations-at-head|access[.]check|^PUBLISH_HTTPS=|listeners_overlay_files "[$]HERE" "[$]CERT_NAME" "[$]PUBLISH_HTTPS"'; git show 2aec4207:infra/deploy/deploy.sh | grep -c '^# >>> guard: '`
- captured_output:
  ```text
  371:# word by the exit status of `python -m auditmanager.access.check` without touching the rest.
  375:PUBLISH_HTTPS="$(configured ALPHA_PUBLISH_HTTPS)"
  1023:    done < <(listeners_overlay_files "$HERE" "$CERT_NAME" "$PUBLISH_HTTPS" "$PAIR_PRESENT")
  1047:compose up -d || UP_STATUS=$?
  1189:# >>> guard: migrations-at-head
  27
  ```
- interpretation: The listener decision is made before `up` from `$PUBLISH_HTTPS` and the pair alone (lines 1023-1024); the database exists only after `up`, so the gate cannot be asked before it. The lane therefore makes the decision in two steps: provisional before `up` (keep an already published 443 only if the setting still says yes and a pair exists; never open one), final after `migrations-at-head` (the gate decides). 27 guards at the base; the lane adds three (30).

### P-06 — verify-deployed.sh at the base: exit statuses 0, 4, 6 and 7; no credential question
- captured_at: 2026-10-26
- command: `git show 2aec4207:infra/deploy/verify-deployed.sh | grep -nE '^(DRIFT|UNANSWERABLE|CERTIFICATE)=|access[.]check'`
- captured_output:
  ```text
  82:DRIFT=6
  83:UNANSWERABLE=4
  84:CERTIFICATE=7
  ```
- interpretation: A new reason takes the next free status, 8, with its own refusal text; the existing ones are unchanged.

### P-07 — reset.sh --restore at the base reports an account on its default password and exits 0; it never touches the proxy
- captured_at: 2026-10-26
- command: `git show 2aec4207:infra/deploy/reset.sh | grep -nE 'access[.](check|revoke)|proxy-listeners|up -d --no-deps|^    exit 0$'`
- captured_output:
  ```text
  204:    compose up -d --no-deps worker
  303:            echo "reset.sh: !!   docker compose --env-file $ENV_FILE --file $COMPOSE_FILE up -d --no-deps worker"
  340:    # `PYTHONPATH=src python -m auditmanager.access.revoke` dies on `ModuleNotFoundError:
  346:        -m auditmanager.access.revoke --everyone || REVOKE_STATUS=$?
  359:        echo "reset.sh: !!     -m auditmanager.access.revoke --everyone"
  366:        -m auditmanager.access.check || CHECK_STATUS=$?
  388:        echo "reset.sh: !!     -m auditmanager.access.check"
  393:    exit 0
  521:    exit 0
  670:    compose up -d --no-deps web
  ```
- interpretation: `revoke --everyone` (line 346) and the default-mode `access.check` (line 366) run; the block ends in a report and `exit 0` (`R-52`: reports, does not refuse). There is no listener step. The lane keeps the report and the exit status 0 and adds the gate and the withdrawal of 443 after it; the only new status is 5 (the door could not be shut).

### P-08 — copy-serve.sh restore-db at the base neither raises token_epoch nor asks the credential question nor touches the proxy
- captured_at: 2026-10-26
- command: `git show 2aec4207:infra/deploy/copy-serve.sh | grep -nE 'access[.](check|revoke)|proxy-listeners|^verb_restore_db|# >>> guard: fingerprint-restored|^    take_fingerprint$'`
- captured_output:
  ```text
  522:    take_fingerprint
  872:verb_restore_db() {
  936:    take_fingerprint
  939:    # >>> guard: fingerprint-restored
  ```
- interpretation: `verb_restore_db` (line 872) ends after the fingerprint comparison. The fingerprint hashes `app_user` rows, so raising `token_epoch` must come AFTER the comparison. The script is installed apart from the checkout (runbook section 13), so a library it sources must be extracted there too.

### P-09 — the receipt: the fields copy-serve.sh writes into the record, and the marker the first attestation writes
- captured_at: 2026-10-26
- command: `git show 2aec4207:infra/deploy/copy-serve.sh | grep -nE '^MARKER=|set_rec (dump|quiesced_at|attestation|purpose|target_sha) |real_data_marker true'`
- captured_output:
  ```text
  100:MARKER="$COPY_DIR/real_data"
  515:    set_rec quiesced_at "\"$(fc_now)\""
  643:    set_rec dump "{\"file\": \"db.dump\", \"size_bytes\": $size, \"sha256\": \"$sha\"}"
  763:    set_rec attestation "{\"dump_sha256\": \"$dump_sha\", \"restore_report_sha256\": \"$report_sha\", \"attested_at\": \"$(fc_now)\"}"
  764:    set_rec purpose "\"$purpose\""
  766:        set_rec target_sha "\"$target\""
  768:        set_rec target_sha null
  776:    set_rec real_data_marker true
  ```
- interpretation: `dump` is `{"file": "db.dump", "size_bytes": N, "sha256": "..."}` on one line, `quiesced_at` a UTC `%Y-%m-%dT%H:%M:%SZ` string, `attestation` carries `dump_sha256`, `purpose`/`target_sha` bind the commit, and `MARKER=$COPY_DIR/real_data` is written by the first attestation. `deploy.sh` already reads the other keys with its own one-key-per-line reader; the lane reuses it. The dump FILE sits in a 0700 stamp directory of the key's account, so the guard does not stat it.

### P-10 — the migration head at the base is 0033, not 0032 (the PW2B text and the ADR were written at 0032)
- captured_at: 2026-10-26
- command: `git show 2aec4207:db/migrations/versions/20261026_0033_ar_v3_cite_stage_id.py | grep -nE '^(revision|down_revision)'`
- captured_output:
  ```text
  52:revision: str = "0033_ar_v3_cite_stage_id"
  53:down_revision: str | None = "0032_ar_v3_run_group"
  ```
- interpretation: Not blocking and not touched (`db/migrations/**` is forbidden). The pending-migration test reads the head out of `db/migrations/versions/*.py` (every revision that is no other's `down_revision`), so it follows whatever the head is.

### P-11 — the two stale `proxy/compose.tls.yml` hint lines in reload-proxy.sh (`D-227` item 5)
- captured_at: 2026-10-26
- command: `git show 2aec4207:infra/deploy/reload-proxy.sh | grep -n 'compose.tls.yml'`
- captured_output:
  ```text
  53:# (`proxy/compose.tls.yml`), which this script does not know about and must not drop. A
  154:        "-f files it was created with (add proxy/compose.tls.yml if TLS is on):" \
  ```
- interpretation: Line 53 (the comment that says the TLS overlay is the only one this script does not know about) and line 154 (the hint printed to the operator). `verify-deployed.sh` already carries the complete hint (`infra/acme/compose.acme.yml` if `ALPHA_CERT_NAME` is set, `proxy/compose.tls.yml` if 443 is published); the lane makes both lines say the same.

### P-12 — there is no unit test of check.py at the base; the existing coverage is subprocess runs against a database
- captured_at: 2026-10-26
- command: `git ls-tree -r --name-only 2aec4207 tests/unit/access; git grep -l 'auditmanager.access.check' 2aec4207 -- tests/integration | cut -d: -f2`
- captured_output:
  ```text
  tests/unit/access/test_access_audit_payloads.py
  tests/integration/auth/test_sign_in_throttle.py
  tests/integration/auth/test_the_reviewer_name_is_visible.py
  tests/integration/composition/test_readiness_command.py
  tests/integration/composition/test_reset_script_refusals.py
  ```
- interpretation: The brief's "check tests" under `tests/unit/access/**` do not exist yet; the existing ones are `tests/integration/auth/*` and `tests/integration/composition/test_{reset_script_refusals,readiness_command}.py` (stubbed `docker`). The lane adds `tests/unit/access/test_access_check_gate.py` (no database).

### P-13 — the stubs of the existing suites answer nothing for the new calls, so the suites that run deploy.sh, verify-deployed.sh or a restore to the end need their stubs taught the gate
- captured_at: 2026-10-26
- command: `git grep -c 'access[.]check' 2aec4207 -- tests/integration/composition/test_deploy_script_refusals.py tests/integration/composition/test_acme_deploy_guards.py tests/integration/composition/test_deploy_image_identity.py tests/integration/composition/test_deployed_stack_probe.py tests/integration/composition/test_proxy_config_follows_checkout.py`
- captured_output:
  ```text
  (no output; exit status 1)
  ```
- interpretation: No output: none of the five names `access.check` at the base. A stub that exits 0 with no output is exactly the `unknown` verdict, which the new code refuses on. Each stub gets one branch that answers the gate (clean by default, the case's choice through the environment); the report lists them as modified tests with what each asserted before and after.

### P-14 — the guard-count pin at the base, and the baseline test counts by collection (no execution)
- captured_at: 2026-10-26
- command: `git show 2aec4207:tests/integration/composition/test_deploy_script_refusals.py | grep -nE 'assert len[(]markers[)] == '`
- captured_output:
  ```text
  1224:    assert len(markers) == len(set(markers)), markers
  1225:    assert len(markers) == 27, markers
  ```
- interpretation: Collected at the base in a throw-away detached worktree (removed after): test_deploy_script_refusals 88, test_acme_deploy_guards 69, test_deploy_image_identity 23, test_deployed_stack_probe 32, test_verify_deployed_certificate 15, test_reset_script_refusals 52, test_stand_copy_refusals 147, test_proxy_config_follows_checkout 14, test_acme_overlay 125, test_readiness_command 46, tests/unit/access 88. The after-counts are in the report.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

The lane commits to `agent/prod-02-03-deploy-gates-01` and pushes nothing. `origin/main` triggers a deployment (`AGENTS.md` section 6) and is not touched.

## Allowed paths

- `infra/deploy/deploy.sh`
- `infra/deploy/verify-deployed.sh`
- `infra/deploy/readiness.sh`
- `infra/deploy/reset.sh`
- `infra/deploy/copy-serve.sh`
- `infra/deploy/reload-proxy.sh`
- `infra/deploy/lib/**`
- `infra/deploy/env/alpha.env.example`
- `src/auditmanager/access/check.py`
- `tests/unit/access/**`
- `tests/integration/composition/**`
- `docs/program/DEPLOYMENT_RUNBOOK.md`
- `docs/program/tasks/PROD-02-03-DEPLOY-GATES-01.md`
- `docs/program/PROD-02-03-DEPLOY-GATES-01.md`

`tests/integration/recovery/**` (allowed for restore-path tests that already exist) was not needed: the restore paths' tests are in `test_reset_script_refusals.py` and `test_stand_copy_refusals.py`. `readiness.sh` was not edited (the brief keeps `R-46` for it).

## Forbidden hotspots

- `.github/**`
- `contracts/**`
- `db/migrations/**` and the migration head
- every other `src/**` — in particular `src/auditmanager/access/repository.py` (`PROD-06` edits it)
- the web
- lock files and dependency manifests
- `infra/deploy/README.md` (not in the allowed list; one sentence in it is reported, not edited)

## Non-goals

- installing the copy key or taking the first real copy (owner steps, recorded in runbook section 13)
- database roles (`PROD-04`), limits (`PROD-05`), anything that touches the live host
- changing what `readiness.sh` reports (it keeps the wider question and `R-46`)
- a new dump script (the receipt is the record `dump-db` writes)

## Deliverables

- `src/auditmanager/access/check.py`: `--gate` (`GATE_*` sentinels, `SeededAccount`, `gate_report`, `run_gate`); the default mode and its sentinels unchanged
- `infra/deploy/lib/proxy-listeners.sh`: the credential gate (`listeners_gate_verdict`, `listeners_gate_logins`, `listeners_gate_run`, `listeners_https_wanted`, `listeners_https_published`, `listeners_apply_https`, `listeners_withhold_https`)
- `deploy.sh` (three guards, a two-step 443 decision), `verify-deployed.sh` (exit 8), `reset.sh` (restore ends with the gate; exit 5), `copy-serve.sh` (`restore-db`: revoke, gate, withdraw; `status` prints the library's digest), `reload-proxy.sh` (two hint lines), `alpha.env.example` (comment)
- `docs/program/DEPLOYMENT_RUNBOOK.md`: sections 3, 4, 6, 7, 9 and 13
- new tests: `tests/unit/access/test_access_check_gate.py`, `tests/integration/composition/test_default_credential_gate.py`, `tests/integration/composition/test_stand_copy_fresh.py`; modified tests (the report lists, per test, what it asserted before and after)
- the report `docs/program/PROD-02-03-DEPLOY-GATES-01.md`

## Required tests

- command: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/access tests/integration/composition/test_default_credential_gate.py tests/integration/composition/test_stand_copy_fresh.py tests/integration/composition/test_deploy_script_refusals.py tests/integration/composition/test_acme_deploy_guards.py tests/integration/composition/test_deploy_image_identity.py tests/integration/composition/test_deployed_stack_probe.py tests/integration/composition/test_verify_deployed_certificate.py tests/integration/composition/test_reset_script_refusals.py tests/integration/composition/test_stand_copy_refusals.py tests/integration/composition/test_proxy_config_follows_checkout.py tests/integration/composition/test_acme_overlay.py tests/integration/composition/test_readiness_command.py` (one file at a time on a shared host; none needs a database or docker)
- expected: all pass; the counts are in the report
- command: `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` (after the last commit: one contract test refuses a dirty tree)
- expected: green

## Integration contract

What the integrator can rely on:

- the gate is `python -m auditmanager.access.check --gate`: exit 0 and `access-check GATE OK no published credential` (last line) when no active `admin` account accepts `password`; exit 1 and `access-check GATE DEFAULT CREDENTIAL: login=admin ...` when one does; exit 2 when the database or the stored credential could not be read. Temporary passwords are `access-check GATE WARNING temporary password: ...` lines at any status. The default mode, its sentinels and statuses are unchanged
- `deploy.sh` refuses `[stand_copy_fresh]` (before the build) and `[default_credential]` / `[default_credential_unanswered]` (after `migrations-at-head`) with exit 3; `verify-deployed.sh` exits 8 on the published pair and 4 when the gate could not be answered; `reset.sh --restore` exits 0 for a completed restore and 5 when 443 could not be withdrawn
- `ALPHA_PUBLISH_HTTPS=yes` is necessary and no longer sufficient; with `ALPHA_CERT_NAME` empty nothing about the listeners changes, and the gate still guards the deploy
- `copy-serve.sh restore-db` needs `lib/proxy-listeners.sh` installed beside it: the owner repeats the install of runbook section 13 after this merges; the other verbs do not need it
- no file under `contracts/**`, `db/migrations/**`, `.github/**`, the web or any other `src/**` is touched

## Failure/idempotency/security cases

- the table of 24 end states (`publish` x `pair` x gate verdict x 443 open before): 443 is published at the end only on three yeses, and never while the pair is valid
- a deploy that changes nothing recreates nothing (an already published, still wanted, clean host issues no proxy-only `up`)
- an unanswered gate refuses by itself and opens nothing; after a restore the same unanswered gate is treated as a finding
- an unreadable database with the `real_data` marker present is a refusal naming the way out; a database ahead of the checkout also needs the receipt
- every refusal is shown able to fail by deleting its marked block; the mutation table is in the report

## Rollback / feature flag

No new flag. The behaviour with `ALPHA_CERT_NAME` empty and no `real_data` marker is the previous deploy plus one extra question to the api image (the gate), which a clone cannot skip. Rolling the lane back is reverting its commits; the copy key's installed files then need the previous `copy-serve.sh` (the library is simply unused).

## Handoff

- changed files: see the report, section 2
- commands/results: see the report, section 6
- known limits: see the report, section 8
- integration notes: see the report, section 7
