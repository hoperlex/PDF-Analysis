# Task JUDGE-FIXES-F2-01 — the judge's findings on the deployment scripts (D-229 items 1, 2, 3, 4; item 6 stopped at its premise)

task_id: JUDGE-FIXES-F2-01
status: items 1, 2, 3, 4 and the README text completed in a development candidate; item 6 NOT implemented (premise and grant, see P-08 to P-11 and the report)

## Outcome

`D-229` of `DEBT_REGISTER.md` (independent judge, 2026-10-26, reviewed commit `caf67714`), the items that belong to `infra/**`:
**(1)** `public-ports-free` asks the kernel's table of listening sockets and so sees a host nginx bound to the host's own address; **(2)** the runbook says what "empty name = byte-identical" does not cover and what a staging rehearsal does to `deploy-auto`; **(3)** the `acme` service shares a network only with the `proxy`; **(4)** `deploy.sh` refuses a non-empty `ALPHA_TRUSTED_PROXY_CIDRS` once a certificate name is set; and the stale listeners text of `infra/deploy/README.md`. **(6)** (the stand fingerprint and `access.%`) is reported, not built: its footprint is outside the lane's allowed paths and the finding's own premise is incomplete (P-08 to P-11).

## Depends on

- `PROD-01-TLS-ACME-01` and `PROD-02-03-DEPLOY-GATES-01` — merged into the base `07e2e8ba`
- `D-229` (the register row), `PRODUCTION-WAVE-PW2B.md` section 2 (common rules)

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.6.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable
- migration head: unchanged (`0033_ar_v3_cite_stage_id`)
- base commit: `07e2e8ba` (`integration/ar-close-1026`), branch `agent/judge-fixes-f2-01`

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: infra/deploy/deploy.sh
- enumerator_owner: JUDGE-FIXES-F2-01 (the lane owns `infra/**` in this slot; `test_every_guard_in_the_script_has_a_case_here` pins the set and its count)
- totality_query: `python3 -I -c "import re;print(sorted(re.findall(r'^# >>> guard: ([a-z-]+)$',open('infra/deploy/deploy.sh',encoding='utf-8').read(),re.M)))"`

The set is the marked guard blocks of `deploy.sh`: 30 before, 31 after (`trusted-proxies-empty-with-name`).

## Captured premise evidence

- premise: eleven reads the register row and the brief rely on, re-run against the base commit `07e2e8ba` with `git show` (so they stay true after the lane's edits). Items 1, 3 and 4 are as described. **P-04 is a regression the brief did not name** (the fix for item 3 would have broken `reload-proxy.sh`); **P-08 to P-11 are why item 6 stops**.

### P-01 — `public-ports-free` probes `127.0.0.1` only
- captured_at: 2026-10-26
- command: `git show 07e2e8ba:infra/deploy/deploy.sh | grep -n 'dev/tcp\|guard: public-ports-free'`
- captured_output:
  ```text
  850:# bash's own /dev/tcp rather than `ss`, `lsof` or `netstat`: none of the three is on a slim
  853:if (exec 3<>"/dev/tcp/127.0.0.1/$HTTP_PORT") 2>/dev/null; then
  866:# >>> guard: public-ports-free
  883:        if (exec 3<>"/dev/tcp/127.0.0.1/$public_port") 2>/dev/null; then
  899:# <<< guard: public-ports-free
  ```
- interpretation: Line 883 is the probe of the finding: a connect to `127.0.0.1` on the public port. Line 853 is the sibling guard `port-not-foreign` for `ALPHA_HTTP_PORT`, which is published on loopback by design and is not part of the finding (left unchanged; it is not name-gated and "empty name = unchanged" is the claim item 2 is about). The comment at 850 records why `ss` was not used: the target may not have it; the lane's answer reads `/proc/net/tcp*` instead (no tool).

### P-02 — the judge's measurement reproduced: a listener on another address is "free" to the old probe
- captured_at: 2026-10-26
- command: `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/composition/test_acme_deploy_guards.py -k TestPublicPortsFree` (new tests, old `deploy.sh`)
- captured_output:
  ```text
  FAILED ...::TestPublicPortsFree::test_a_holder_on_any_address_of_the_host_is_refused_before_the_build[127.0.0.2]
  FAILED ...::TestPublicPortsFree::test_a_holder_on_any_address_of_the_host_is_refused_before_the_build[OUTWARD]
  FAILED ...::TestPublicPortsFree::test_a_holder_on_any_address_of_the_host_is_refused_before_the_build[0.0.0.0]
  FAILED ...::TestPublicPortsFree::test_a_holder_on_any_address_of_the_host_is_refused_before_the_build[::1]
  FAILED ...::TestPublicPortsFree::test_a_holder_on_any_address_of_the_host_is_refused_before_the_build[::]
  FAILED ...::TestPublicPortsFree::test_https_is_checked_across_addresses_too_when_this_deploy_would_publish_it[127.0.0.2]
  FAILED ...::TestPublicPortsFree::test_without_a_table_a_loopback_holder_is_still_refused
  FAILED ...::TestPublicPortsFree::test_without_a_table_the_limit_is_said_and_not_hidden
  8 failed, 12 passed, 64 deselected
  ```
  and, with the old script, `test_the_old_loopback_connect_would_have_called_that_port_free[127.0.0.2]` and `[OUTWARD]` passed: a socket listening on `127.0.0.2` (and on this host's outward address, the one a route to a non-loopback destination uses) is refused a connect to `127.0.0.1` on the same port.
- interpretation: Reproduced before the fix. The `[0.0.0.0]` case and the two table cases fail only because they need the new message, the new note or the new table variable; the cases that show the finding itself are `[127.0.0.2]`, `[OUTWARD]`, `[::1]`, `[::]` and the https case on `127.0.0.2`. The wildcard holder was already refused by the old probe (a connect to loopback reaches it), which is why the finding is "a host nginx bound to the host's own address".

### P-03 — the `acme` service is on the data network, with every other service
- captured_at: 2026-10-26
- command: `git show 07e2e8ba:infra/acme/compose.acme.yml | grep -n 'networks'; git show 07e2e8ba:infra/deploy/compose.server.yml | grep -n 'networks'`
- captured_output:
  ```text
  61:    networks: [alpha]
  29:networks:
  69:    networks: [alpha]
  105:    networks: [alpha]
  133:    networks: [alpha]
  154:    networks: [alpha]
  171:    networks: [alpha]
  186:    networks: [alpha]
  260:    networks: [alpha]
  356:    networks: [alpha]
  367:    networks: [alpha]
  ```
- interpretation: The overlay's single `networks:` line (61) puts `acme` on `alpha`, the network of the ten base services (postgres, s3, s3-init, migrate, release-notes, api, worker, web, proxy; lines 69 to 367). The only peer `acme` needs is the proxy: `entrypoint.sh` probes `http://proxy:8081`, `check-served.sh` asks `proxy:8443`.

### P-04 — `reload-proxy.sh` takes the FIRST network the proxy lists for its throwaway `nginx -t` container (a regression item 3 would have caused)
- captured_at: 2026-10-26
- command: `git show 07e2e8ba:infra/deploy/reload-proxy.sh | grep -n -A3 'NETWORK="\$('`
- captured_output:
  ```text
  196:    NETWORK="$(docker inspect --format \
  197-        '{{range $name, $value := .NetworkSettings.Networks}}{{$name}}{{"\n"}}{{end}}' "$PROXY" \
  198-        | head -1)"
  199-    CANDIDATE=(docker run --rm)
  ```
- interpretation: `docker inspect` lists a map's keys sorted. With the proxy on `<instance>-net` and `<instance>-acme-net`, the first is `<instance>-acme-net` (`a` before `n`): the throwaway container lands where `api` and `web` do not resolve and every good, stale-config repair is refused as exit 5. The new test `TestTheThrowawayContainerJoinsTheNetworkTheUpstreamsLiveOn` was red against this line before the fix (`--network an-instance-acme-net`). No other script in `infra/` or `scripts/` picks a network by position (`grep -rn -e '--network' -e 'docker network' infra scripts`: only `--network none`).

### P-05 — nothing refuses a trust list once a name is set
- captured_at: 2026-10-26
- command: `git show 07e2e8ba:infra/deploy/deploy.sh | grep -c '^# >>> guard'; git show 07e2e8ba:infra/deploy/deploy.sh | grep -n 'TRUSTED_PROXIES\|CIDRS'`
- captured_output:
  ```text
  30
  348:# `REAL-IP-EDGE-01`. `ALPHA_TRUSTED_PROXY_CIDRS` is pasted, entry by entry, into the proxy's
  359:TRUSTED_PROXIES="$(configured ALPHA_TRUSTED_PROXY_CIDRS)"
  360:if [ -n "$TRUSTED_PROXIES" ]; then
  362:        refuse "$HERE/proxy/trusted-proxies.sh is missing, so ALPHA_TRUSTED_PROXY_CIDRS cannot be checked." \
  365:    if ! TRUSTED_WHY="$(ALPHA_TRUSTED_PROXY_CIDRS="$TRUSTED_PROXIES" sh "$HERE/proxy/trusted-proxies.sh" --check 2>&1)"; then
  366:        refuse "ALPHA_TRUSTED_PROXY_CIDRS in $ENV_FILE is not a list the proxy will accept." \
  ```
- interpretation: The only reader of the setting checks that the list is well formed, never whether a certificate name makes it wrong. The runbook's only defence is prose (P-06). The reason the setting is wrong with a name: the proxy believes `X-Forwarded-For` from the listed peers (the compose gateway, which every host process and SSH-tunnelled operator reaches the plain listener through), and with no nginx in front the list can only be abused. I found no live configuration that needs a list together with a name: the host nginx is stopped before the first deploy that sets a name (runbook step 4, and `public-ports-free` refuses otherwise), so the guard is a refusal and not a warning.

### P-06 — the runbook only says "remove it"
- captured_at: 2026-10-26
- command: `git show 07e2e8ba:docs/program/DEPLOYMENT_RUNBOOK.md | grep -n 'remove .ALPHA_TRUSTED'`
- captured_output:
  ```text
  560:`ALPHA_ACME_EMAIL`, and **remove `ALPHA_TRUSTED_PROXY_CIDRS`** (the host nginx is gone; the client address now
  ```
- interpretation: One sentence in step 5, no refusal behind it.

### P-07 — the workflow runs `verify-deployed.sh` with no arguments, and the "not byte-identical" differences are as the judge lists them
- captured_at: 2026-10-26
- command: `grep -n 'verify-deployed\|tls-dir\|TLS_DIR\|deploy.sh' .github/workflows/deploy-auto.yml; git show 0e663fd0:infra/deploy/readiness.sh | grep -n 'tls-dir\|TLS_DIR'; git show 07e2e8ba:infra/deploy/deploy.sh | grep -n 'are built'`
- captured_output:
  ```text
  112:          infra/deploy/deploy.sh </dev/null
  115:          infra/deploy/verify-deployed.sh </dev/null
  65:TLS_DIR="${ALPHA_TLS_DIR:-$HERE/proxy/tls}"
  70:usage: readiness.sh [--env-file <path>] [--provider-env-file <path>] [--tls-dir <path>]
  74:  --tls-dir <path>            default: infra/deploy/proxy/tls
  88:        --tls-dir) TLS_DIR="${2:-}"; shift 2 ;;
  160:CERT="$TLS_DIR/fullchain.pem"
  1078:echo "  ${BUILT_IMAGES// /, } are built"
  ```
- interpretation: (a) the workflow calls `verify-deployed.sh` bare (lines 112 and 115), so it cannot pass `--acme-rehearsal`, and a name with `ALPHA_ACME_STAGING=yes` (or the line absent: the default is `yes`) ends every `deploy-auto` run at exit 7 by design; (b) `--tls-dir` and `ALPHA_TLS_DIR` existed at the pre-PROD-01 commit `0e663fd0` and exist nowhere in the tree now; the workflow passes neither; (c) the line after the build was `$INSTANCE-api and $INSTANCE-web are built` and is `${BUILT_IMAGES// /, } are built` now (a different text even with an empty name). `readiness.sh` now answers `unrecognised option: --tls-dir`, exit 2. Nothing in the repository matches the "are built" text (`grep -rn 'are built' .github scripts infra tests`).

### P-08 — item 6: the fingerprint exclusion is where the register says, and the version is carried in far more places than the two it names
- captured_at: 2026-10-26
- command: `git show 07e2e8ba:infra/deploy/copy-serve.sh | grep -n 'LIKE'; git show 07e2e8ba:src/auditmanager/norms/bundle/copy_record.py | grep -n 'LIKE'; git grep -n 'stand-fingerprint-v1' 07e2e8ba -- scripts infra src tests | sed 's/^07e2e8ba://' | cut -d: -f1 | sort | uniq -c`
- captured_output:
  ```text
  429:        WHEN c.relname = 'audit_event' THEN 'WHERE x.event_type NOT LIKE ''norm\_custody.%'''
  430:        WHEN c.relname = 'command_record' THEN 'WHERE x.command_type NOT LIKE ''norm\_custody.%'''
  440:  AND c.relname NOT LIKE 'norm%'
  73:        WHEN c.relname = 'audit_event' THEN 'WHERE x.event_type NOT LIKE ''norm\_custody.%'''
  74:        WHEN c.relname = 'command_record' THEN 'WHERE x.command_type NOT LIKE ''norm\_custody.%'''
  84:  AND c.relname NOT LIKE 'norm%'
        2 infra/deploy/copy-serve.sh
        1 infra/deploy/lib/forced-command.sh
        1 scripts/recovery/copy_record_binding.py
        2 scripts/recovery/isolated_postgres_restore.py
        1 scripts/recovery/isolated_restore_drill.py
        1 scripts/recovery/product_purge.py
        3 scripts/recovery/schema_coverage.py
        4 scripts/recovery/synthetic_drill_fixture.py
        2 scripts/stand-copy/restore-test.sh
        6 src/auditmanager/norms/bundle/copy_record.py
        1 tests/integration/composition/test_bundle_transport_refusals.py
        5 tests/integration/composition/test_stand_copy_refusals.py
        2 tests/integration/norms/bundle/support.py
        2 tests/integration/norms/bundle/test_copy_record.py
        1 tests/integration/recovery/test_blob_object_binding.py
        1 tests/integration/recovery/test_copy_record_binding.py
        1 tests/integration/recovery/test_isolated_postgres_restore.py
        1 tests/integration/recovery/test_isolated_restore_drill.py
        1 tests/integration/recovery/test_offline_restore_audit.py
        1 tests/integration/recovery/test_offline_restore_preflight.py
        1 tests/integration/recovery/test_schema_coverage.py
  ```
- interpretation: The exclusion is at `copy-serve.sh:429` and `copy_record.py:73` (the register says 424 and 73). The label and the marker text `stand-fingerprint-v1` are read or pinned by files the lane may not edit: `scripts/stand-copy/restore-test.sh` (extracts the block by its markers and compares the whole `fingerprint` JSON), `scripts/recovery/{copy_record_binding,isolated_postgres_restore,synthetic_drill_fixture,...}.py` (`isolated_postgres_restore.py` also pins the SHA-256 of the block: `_STAND_SQL_SHA256`) and `tests/integration/norms/bundle/{support,test_copy_record}.py`. The importer's caller, `src/auditmanager/norms/bundle/stand.py` (another `src/` file, forbidden), computes `compute_fingerprint(stand.engine)` BEFORE it looks at the record's label, so the importer cannot choose a definition by the record's label from `copy_record.py` alone.

### P-09 — the scenario "a sign-in between attest and import" needs a writer that is running
- captured_at: 2026-10-26
- command: `git show 07e2e8ba:infra/deploy/copy-serve.sh | sed -n '24p;47p'; git show 07e2e8ba:docs/program/W54-LOCAL-IMPORT-01.md | sed -n '56,58p'`
- captured_output:
  ```text
  #   dump-db                     opens a copy: stops exactly the writers that are running
  #   resume <STAMP>              starts the stopped writers and closes the record, holding
  exactly that verb's fields: `kind: test_data_waiver`, `state: open`, `purpose: import`,
  `writers_present` and `writers_stopped` both empty (no web, API or worker was running), the
  migration head read from `alembic_version`, `rejected_blob_count`, a 12 h `waiver.expires_at`,
  ```
- interpretation: On a compose stand `dump-db` (and `attest --test-data`) stops `web`, `api` and `worker` and they stay stopped until `resume`, so no sign-in can reach the stand between the fingerprint and the import: a sign-in there means someone started a writer, and `fingerprint_drifted` is the right answer. The scenario is real on the **local import rehearsal** (`W54-LOCAL-IMPORT-01`: the API runs outside compose, `writers_present` is empty, nothing stops it, the owner signs in through it).

### P-10 — excluding `access.%` is not enough: a FAILED sign-in writes `app_user`, and `app_user` is fingerprinted whole
- captured_at: 2026-10-26
- command: `git show 07e2e8ba:src/auditmanager/access/repository.py | sed -n 414,434p | grep -n 'UPDATE app_user\|failed_sign_ins =\|last_failed_sign_in_at\|sign_in_blocked_until ='; git show 07e2e8ba:infra/deploy/copy-serve.sh | sed -n 425,436p`
- captured_output:
  ```text
  10:    UPDATE app_user SET
  11:        failed_sign_ins = {_NEXT_FAILED_SIGN_INS},
  12:        last_failed_sign_in_at = now(),
  13:        sign_in_blocked_until = CASE
          'SELECT %L || ''|'' || count(*) || ''|'' || encode(sha256(convert_to(coalesce(string_agg(r.t, E''\n'' ORDER BY r.t COLLATE "C"), ''''), ''UTF8'')), ''hex'') FROM (SELECT x::text AS t FROM %I AS x %s) AS r',
          c.relname,
          c.relname,
          CASE
              WHEN c.relname = 'audit_event' THEN 'WHERE x.event_type NOT LIKE ''norm\_custody.%'''
              WHEN c.relname = 'command_record' THEN 'WHERE x.command_type NOT LIKE ''norm\_custody.%'''
              WHEN c.relname = 'blob' AND to_regclass('norm_custody_admission') IS NOT NULL
                  THEN 'WHERE NOT EXISTS (SELECT 1 FROM norm_custody_admission AS a WHERE a.blob_id = x.blob_id)'
              ELSE ''
          END)
  ```
- interpretation: `app_user` has no filter: its rows are hashed as `x::text`. A successful sign-in of an account with nothing to clear writes only the `access.sign_in_succeeded` event (`_CLEAR_ONE` has a predicate for exactly that), so excluding `access.%` fixes that case. A failed sign-in, or the sign-in of an account that had a failed attempt, updates `app_user.failed_sign_ins`, `last_failed_sign_in_at` and `sign_in_blocked_until`, which the fingerprint still counts: with only `access.%` excluded a bot's failed attempt during the window still makes the import refuse. The complete fix also decides what the fingerprint does with those three columns (project `app_user` without them, or accept the refusal), which changes what the fingerprint means and is an owner/architect decision, not a mechanical one.

### P-11 — measured: a version bump of the label and markers alone reddens 89 existing tests in three files, two of them outside the grant
- captured_at: 2026-10-26
- command: `sed -i 's/stand-fingerprint-v1/stand-fingerprint-v2/g' infra/deploy/copy-serve.sh src/auditmanager/norms/bundle/copy_record.py infra/deploy/lib/forced-command.sh` (applied in the lane's worktree, the files below run one at a time, then `git checkout -- .`; nothing of it is committed)
- captured_output:
  ```text
  tests/integration/norms/bundle/test_copy_record.py: 10 failed, 15 passed in 1.16s
  tests/integration/recovery/test_copy_record_binding.py: 12 passed in 0.02s
  tests/integration/recovery/test_isolated_postgres_restore.py: 8 failed, 16 passed in 0.12s
  tests/integration/recovery/test_synthetic_drill_fixture.py: 16 passed in 0.42s
  tests/integration/composition/test_stand_copy_refusals.py: 71 failed, 87 passed, 1 skipped in 30.48s
  tests/integration/composition/test_bundle_transport_refusals.py: 122 passed in 7.85s
  ```
- interpretation: 89 reds from the rename alone, before any SQL change. They are not noise: `restore-test.sh` (its guard cases are among the 71, because the suite extracts its block by the old marker) and `isolated_postgres_restore.py` (8, marker plus the pinned SHA-256) read the old marker; `tests/integration/norms/bundle/test_copy_record.py` (10) and `support.py` pin the old label and the byte-for-byte block. Making them green needs edits to `scripts/stand-copy/restore-test.sh`, `scripts/recovery/*.py` and `tests/integration/norms/bundle/**`, none of them allowed to this lane. Item 6 therefore stops here (the report carries the design a wider lane can start from).

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

The lane commits to `agent/judge-fixes-f2-01` and pushes nothing. `origin/main` triggers a deployment (`AGENTS.md` section 6) and is not touched.

## Allowed paths

- `infra/deploy/**`
- `infra/acme/**`
- `src/auditmanager/norms/bundle/copy_record.py`
- `tests/unit/norms/**`
- `tests/integration/composition/**`
- `tests/integration/recovery/**`
- `docs/program/DEPLOYMENT_RUNBOOK.md`
- `docs/program/tasks/JUDGE-FIXES-F2-01.md`
- `docs/program/JUDGE-FIXES-F2-01.md`

`infra/deploy/README.md` is covered by `infra/deploy/**`. Of these, the lane edited `infra/deploy/{deploy.sh,reload-proxy.sh,README.md,env/alpha.env.example}`, `infra/acme/compose.acme.yml`, `tests/integration/composition/{test_acme_deploy_guards,test_acme_overlay,test_deploy_script_refusals,test_proxy_config_follows_checkout}.py`, the runbook and the two deliverables. `copy_record.py`, `tests/unit/norms/**` and `tests/integration/recovery/**` were not needed (item 6 stopped).

## Forbidden hotspots

- `.github/**`
- `contracts/**`
- `db/migrations/**` and the migration head
- the web
- every other `src/**`
- `scripts/**`, `tests/integration/norms/**` (outside the grant: they are what item 6 would have needed)
- docs other than the runbook and the two deliverables (`ADR-0021` row 9's spelling is the integrator's)
- lock files and dependency manifests

## Non-goals

- anything that touches the live host, a container or a certificate authority
- the stand fingerprint (item 6): reported, not built
- changing `port-not-foreign` (the loopback `ALPHA_HTTP_PORT` guard) or the order of the existing guards
- resolving `infra/acme/client.pin`

## Deliverables

- `deploy.sh`: `public-ports-free` reads `/proc/net/tcp` and `/proc/net/tcp6` (any local address), keeps the loopback connect as a second witness and says so when no table can be read; the new guard `trusted-proxies-empty-with-name`
- `compose.acme.yml`: the network `acme-edge` (`<instance>-acme-net`), shared by `acme` and `proxy` only; `reload-proxy.sh`: the throwaway container's network is the `api` container's
- `DEPLOYMENT_RUNBOOK.md` section 6: the "before the first deploy of this tree" checklist and the rehearsal warning, plus the step 3, step 5 and message-table lines; `infra/deploy/README.md` TLS section; `alpha.env.example` comments
- tests (new and modified, the report lists them) and the report `docs/program/JUDGE-FIXES-F2-01.md`

## Required tests

- command: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/composition/test_acme_deploy_guards.py tests/integration/composition/test_acme_overlay.py tests/integration/composition/test_proxy_config_follows_checkout.py tests/integration/composition/test_deploy_script_refusals.py` (one file at a time on a shared host; none needs a database or docker)
- expected: all pass; the counts are in the report
- command: `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` (after the last commit: one contract test refuses a dirty tree)
- expected: green

## Integration contract

What the integrator can rely on:

- with `ALPHA_CERT_NAME` set, `deploy.sh` refuses (exit 3, before any `docker` call) when any socket of the host listens on the challenge port, or on the TLS port when this deploy would publish it, on any address; the own-proxy excuse (`docker port`) is unchanged; on a host with no `/proc/net/tcp*` it prints `deploy.sh: NOTE: no table of listening sockets could be read ...` and falls back to the loopback connect
- with `ALPHA_CERT_NAME` set and a non-empty `ALPHA_TRUSTED_PROXY_CIDRS`, `deploy.sh` refuses with `[...] ALPHA_TRUSTED_PROXY_CIDRS is set in <env> and ALPHA_CERT_NAME is set too.`; a value of separators alone is the empty list; without a name nothing changes
- the `acme` container is on `<instance>-acme-net` only; the proxy is on both networks. The merge of the two `networks:` lists by compose is **not observed** (no docker in the lane): the overlay lists both names on the proxy so the result is the same whether compose merges or replaces
- with `ALPHA_CERT_NAME` empty the stack, the compose files and every `docker` call are as before; the three differences the register names are in the runbook checklist
- no file under `contracts/**`, `db/migrations/**`, `.github/**`, the web, `scripts/**` or any other `src/**` is touched

## Failure/idempotency/security cases

- the table of listeners: IPv4 and IPv6 files, `LISTEN` state only (a connected socket on that port is not a holder), exact port, a held port on any of five addresses, the unreadable-table path says so
- the own proxy publishing on every address still excuses its own port (the second deploy of the same tree goes on)
- the trust-list guard: six spellings refused, three empty spellings accepted, no name accepted, a malformed list refused by either guard
- every new refusal is shown able to fail by deleting its marked block and by the single-line mutations in the report

## Rollback / feature flag

No flag. The guards act only with `ALPHA_CERT_NAME` set; rolling the lane back is reverting its commits. A host that set a name before this lane and left `ALPHA_TRUSTED_PROXY_CIDRS` in place will be refused at its next deploy (one line to delete).

## Handoff

- changed files: see the report, section 2
- commands/results: see the report, section 5
- known limits: see the report, section 7
- integration notes: see the report, section 6
