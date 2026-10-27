# Task PROD-01-TLS-ACME-01 — the stack terminates TLS and renews its own certificate

task_id: PROD-01-TLS-ACME-01
status: completed in development candidate (nothing run against a certificate authority or a host; see the report)

## Outcome

`ADR-0021` section 2 and `AD-01` are built in the tree and verified without a network and without a container: an ACME client as a service of the same compose project (base pinned by digest, client pinned by exact version in `infra/acme/client.pin`, HTTP-01 through a webroot the `proxy` serves, the pair in a named volume the `proxy` reads read-only on a timer, no Docker socket); the three listeners of `R-146s` (application on loopback; public 80 for the challenge and a redirect only; public 443 only when a deploy is cleared **and** a pair exists, the clearance being the explicit setting `ALPHA_PUBLISH_HTTPS=yes` until `PROD-02` replaces it); HSTS `max-age=31536000` without `includeSubDomains` or `preload`; the `Secure` session cookie through the `https` the TLS block forwards; `verify-deployed.sh` failing (exit 7) on a served certificate that is missing, staging, untrusted or has fewer than 14 days left; `readiness.sh` `tls` and `plain-http` rewritten for the new layout; and the staging rehearsal and first real issuance written as a numbered runbook procedure with the expected output of each step.

## Depends on

- `PRODUCTION-READINESS-PLAN-01` — completed; item `PROD-01` is this task.
- `ADR-0021` — accepted for production; section 2 and its commitments 1 to 6 are what this task delivers.
- `R-146a`, `R-146aa`, `R-146ac`, `R-146s` — owner rulings (the mechanism confirmed, the name given, the three listeners).

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.5.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable
- migration head: unchanged (`0032_ar_v3_run_group`)
- base commit: `0e663fd0e608fcf5f79075ea71713c24ddf027e5` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: infra/deploy/deploy.sh
- enumerator_owner: PROD-01-TLS-ACME-01 (the lane owns `infra/**` and `DEPLOYMENT_RUNBOOK.md` in wave PW2b; `test_every_guard_in_the_script_has_a_case_here` pins the set and its count)
- totality_query: `python3 -I -c "import re;print(sorted(re.findall(r'^# >>> guard: ([a-z-]+)$',open('infra/deploy/deploy.sh',encoding='utf-8').read(),re.M)))"`

The set is the marked guard blocks of `deploy.sh`: 22 before, 27 after (`acme-files-present`, `acme-settings-well-formed`, `acme-client-pinned`, `public-ports-free`, `acme-pair-answerable`). The query prints all 27; `tests/integration/composition/test_deploy_script_refusals.py` asserts the count and that every name has a case.

## Captured premise evidence

- premise: twelve reads the plan, the ADR and the brief rely on, re-run on the base commit `0e663fd0`; every one is present and matches except three facts the brief did not state and the task handles (P-04: no script of the deploy path has ever passed the TLS overlay, so a compose-file LIST is new to `deploy.sh`; P-10: PyYAML is not in the test venv; P-12: no digest for an ACME client exists in the tree or can be obtained offline, so the client version is a pin that ships unresolved)

### P-01 — compose.server.yml defines nine services and the proxy is the only one with `ports:`; its published port is the application's loopback port
- captured_at: 2026-10-26
- command: `git show 0e663fd0:infra/deploy/compose.server.yml | grep -nE '^  [a-z0-9-]+:$|^    ports:$|^      - "\$\{ALPHA_BIND'`
- captured_output:
  ```text
  30:  alpha:
  37:  postgres-data:
  39:  s3-data:
  58:  web-sessions:
  62:  postgres:
  99:  s3:
  127:  s3-init:
  149:  migrate:
  166:  release-notes:
  181:  api:
  255:  worker:
  320:  web:
  360:  proxy:
  407:    ports:
  408:      - "${ALPHA_BIND_ADDRESS:-127.0.0.1}:${ALPHA_HTTP_PORT:?ALPHA_HTTP_PORT is unset.}:8080"
  ```
- interpretation: Services (and the network and three volumes at the same indentation): postgres, s3, s3-init, migrate, release-notes, api, worker, web, proxy. `ports:` appears once, on the proxy, and publishes `${ALPHA_BIND_ADDRESS:-127.0.0.1}:${ALPHA_HTTP_PORT}:8080` (container 8080). The plan's "five files under proxy/" are the five below plus `tls/.gitignore`.

### P-02 — the files under infra/deploy/proxy/ and their sizes
- captured_at: 2026-10-26
- command: `for f in $(git ls-tree -r --name-only 0e663fd0 infra/deploy/proxy); do printf '%5s %s\n' "$(git show 0e663fd0:$f | wc -l)" "$f"; done`
- captured_output:
  ```text
     51 infra/deploy/proxy/compose.tls.yml
     79 infra/deploy/proxy/enable-tls.sh
    506 infra/deploy/proxy/nginx.conf
    209 infra/deploy/proxy/tls-server.conf
     16 infra/deploy/proxy/tls/.gitignore
    172 infra/deploy/proxy/trusted-proxies.sh
  ```
- interpretation: nginx.conf (the plain block, always loaded), tls-server.conf (the TLS block, never loaded by nginx unless the switch installs it), enable-tls.sh (the switch), compose.tls.yml (the overlay), trusted-proxies.sh (REAL-IP-EDGE-01) and tls/.gitignore. These are the files the plan counts.

### P-03 — what compose.tls.yml and enable-tls.sh do today: the overlay bind-mounts a host directory and three files and publishes 8443 as 443; the switch asks whether both files in /etc/nginx/tls are non-empty
- captured_at: 2026-10-26
- command: `git show 0e663fd0:infra/deploy/proxy/compose.tls.yml | sed -n '/^services:/,$p'; git grep -n -E '^(CERT|KEY|SRC|DST)=' 0e663fd0 -- infra/deploy/proxy/enable-tls.sh`
- captured_output:
  ```text
  services:
    proxy:
      volumes:
        # The certificate and its private key, placed on the host by the owner. READ-ONLY:
        # nothing in this stack ever writes a key.
        - ./proxy/tls:/etc/nginx/tls:ro
        # The TLS server block, mounted OUTSIDE conf.d so nginx does not load it by itself.
        - ./proxy/tls-server.conf:/etc/nginx/tls-server.conf:ro
        # The switch. The official image runs executable *.sh here before nginx starts.
        - ./proxy/enable-tls.sh:/docker-entrypoint.d/25-enable-tls.sh:ro
      ports:
        # 443 by default because that is what a browser reaching a host name asks for, and
        # this is the file an operator changes when the host says otherwise. The plain port
        # `compose.server.yml` publishes is untouched and keeps serving -- see the
        # "NO REDIRECT" note in `tls-server.conf`.
        # Same binding rule as `compose.server.yml`'s plain port and for the same reason
        # (`D-49`): the interface is explicit and defaults to loopback. A host that is
        # genuinely meant to serve TLS to the world sets `ALPHA_BIND_ADDRESS=0.0.0.0` in
        # `alpha.env` once, and it then applies to both ports rather than to one of them.
        - "${ALPHA_BIND_ADDRESS:-127.0.0.1}:${ALPHA_HTTPS_PORT:-443}:8443"
  0e663fd0:infra/deploy/proxy/enable-tls.sh:36:CERT=/etc/nginx/tls/fullchain.pem
  0e663fd0:infra/deploy/proxy/enable-tls.sh:37:KEY=/etc/nginx/tls/privkey.pem
  0e663fd0:infra/deploy/proxy/enable-tls.sh:38:SRC=/etc/nginx/tls-server.conf
  0e663fd0:infra/deploy/proxy/enable-tls.sh:39:DST=/etc/nginx/conf.d/tls.conf
  ```
- interpretation: Today the certificate pair is a directory the owner fills by hand (`./proxy/tls`), mounted read-only; nothing obtains or renews it (ADR-0021 context). The listener is published by an overlay nobody passes: see P-04.

### P-04 — no script of the deploy path names the TLS overlay, and every one of them runs compose with the one base file
- captured_at: 2026-10-26
- command: `git grep -n -E 'compose\.tls|COMPOSE_FILE=' 0e663fd0 -- infra/deploy/deploy.sh infra/deploy/verify-deployed.sh infra/deploy/reload-proxy.sh infra/deploy/reset.sh infra/deploy/copy-serve.sh infra/deploy/readiness.sh infra/deploy/purge-product-data.sh`
- captured_output:
  ```text
  0e663fd0:infra/deploy/copy-serve.sh:91:COMPOSE_FILE="$CHECKOUT/infra/deploy/compose.server.yml"
  0e663fd0:infra/deploy/deploy.sh:99:COMPOSE_FILE="$HERE/compose.server.yml"
  0e663fd0:infra/deploy/purge-product-data.sh:56:COMPOSE_FILE="$HERE/compose.server.yml"
  0e663fd0:infra/deploy/readiness.sh:59:COMPOSE_FILE="$HERE/compose.server.yml"
  0e663fd0:infra/deploy/reload-proxy.sh:53:# (`proxy/compose.tls.yml`), which this script does not know about and must not drop. A
  0e663fd0:infra/deploy/reload-proxy.sh:75:COMPOSE_FILE="$HERE/compose.server.yml"
  0e663fd0:infra/deploy/reload-proxy.sh:154:        "-f files it was created with (add proxy/compose.tls.yml if TLS is on):" \
  0e663fd0:infra/deploy/reset.sh:40:COMPOSE_FILE="$HERE/compose.server.yml"
  0e663fd0:infra/deploy/verify-deployed.sh:77:COMPOSE_FILE="$HERE/compose.server.yml"
  0e663fd0:infra/deploy/verify-deployed.sh:313:# what serves, and it may carry an overlay (`proxy/compose.tls.yml`) this script never names.
  0e663fd0:infra/deploy/verify-deployed.sh:416:        "same -f files it was created with (add proxy/compose.tls.yml if TLS is on):" \
  ```
- interpretation: `compose.tls.yml` is named only in prose (reload-proxy.sh, verify-deployed.sh comments and error hints). Every script builds its own `compose()` from the single `compose.server.yml`. So the deployed stand has never run the in-tree TLS path: its terminator is the host's nginx (D-191). This is also why a list of compose files is a new thing in deploy.sh.

### P-05 — D-191: the live terminator is a host nginx outside the repository; the certificate expires 2026-12-30; E-2 (no Secure cookie, no HSTS), E-3 (shared throttle bucket), E-7 (terminator not in the repo)
- captured_at: 2026-10-26
- command: `git show 0e663fd0:docs/program/DEBT_REGISTER.md | sed -n 's/^\(| \*\*D-191\*\* | [^|]*\)|.*/\1/p'; git grep -n -E '^### E-[237] ' 0e663fd0 -- docs/program/EXPOSURE-REVIEW-01.md`
- captured_output:
  ```text
  | **D-191** | `EXPOSURE-REVIEW-01.md` E-2/E-3/E-7: the live TLS terminator is a host nginx outside the repository; the container nginx overwrites `X-Forwarded-Proto` (`nginx.conf:257`) so the session cookie is issued without `Secure` and no HSTS header appears, and the guest throttles key on the proxy's peer address, the same for every client behind the terminator; certificate renewal (expires 2026-12-30) is unverifiable from the tree
  0e663fd0:docs/program/EXPOSURE-REVIEW-01.md:46:### E-2 MEDIUM: session cookie is issued without `Secure`, and the live origin sends no HSTS (measured)
  0e663fd0:docs/program/EXPOSURE-REVIEW-01.md:67:### E-3 MEDIUM (inference, unmeasured): every caller shares one throttle bucket behind the terminator
  0e663fd0:docs/program/EXPOSURE-REVIEW-01.md:107:### E-7 LOW: the TLS terminator and the firewall are not in the repository
  ```
- interpretation: D-191 as the plan quotes it. E-3's code half is done (REAL-IP-EDGE-01); E-2 and E-7 are what this lane moves into the stack.

### P-06 — ADR-0021 commitments 1 to 6: the commitment column
- captured_at: 2026-10-26
- command: `git show 0e663fd0:docs/architecture/adr/ADR-0021-production-topology-and-operations.md | awk -F'|' 'NR>=306 && NR<=311 { print $2 "|" $3 }'`
- captured_output:
  ```text
   1 | Only the proxy publishes a port
   2 | TLS answers on the public name with a trusted chain
   3 | HSTS on every TLS answer (`R-146a`)
   4 | The session cookie is `Secure` (`R-146a`)
   5 | The certificate is renewed before it expires
   6 | A deployment is not successful while `admin`/`password` is valid (`R-146i`, `R-146s`, `R-146z`)
  ```
- interpretation: The six rows this lane's mutation table answers (report, section 3). Rows 2 to 5 are claims about bytes a client receives; the tree can hold the facts that make them true, not the bytes.

### P-07 — the ruling that names the server name and releases PROD-01, and the one that fixes the ACME mechanism
- captured_at: 2026-10-26
- command: `git show 0e663fd0:docs/program/OWNER_RULINGS_2026-09-17.md | awk -F'|' '/^\| .R-146a[ac]. /{ print $2 "|" $3 }'`
- captured_output:
  ```text
   `R-146aa` | **`AD-01`, the ACME mechanism.** Chosen: «Принять механизм как написан» (recommended). An ACME client as a service of the same compose project, HTTP-01 through public port 80 (challenge and redirect only), the pair in a named volume read by the `proxy` on a timer, no Docker socket, a rehearsal on the ACME staging endpoint before the first real issuance, and `verify-deployed.sh` failing on a certificate with fewer than 14 days left, are confirmed as written in `ADR-0021` at commit `749e2efc`. DNS and inbound ports 80 and 443 on the VPS are the owner's actions.
   `R-146ac` | **The server name** (supersedes `R-146ab`). The owner named `https://audit.135.106.164.147.sslip.io/login`, i.e. the host name `audit.135.106.164.147.sslip.io`, which is already the public name of the live stand in `.github/workflows/deploy-auto.yml` and `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md`. `PROD-01` is released: the certificate name is a deploy variable set to this value on the host. **Risk recorded, not decided:** `sslip.io` is a shared zone, so Let's Encrypt rate limits are shared with other users of it; the rehearsal on the ACME staging endpoint comes first, and if the real issuance is refused for a limit the owner decides on a name of their own.
  ```
- interpretation: R-146aa confirms the mechanism as ADR-0021 wrote it; R-146ac names the live stand's name and records the shared-zone rate-limit risk. Neither name is put in any default of this lane: the certificate name is a deploy variable with a reserved placeholder.

### P-08 — the workflow pins the one host and does not change
- captured_at: 2026-10-26
- command: `git grep -n '135.106.164.147' 0e663fd0 -- .github/workflows/deploy-auto.yml`
- captured_output:
  ```text
  0e663fd0:.github/workflows/deploy-auto.yml:45:            '135.106.164.147 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPZcfVwHVIUEU7W0auTb70VKY/aLppXM/54vzpmy0+XV' \
  0e663fd0:.github/workflows/deploy-auto.yml:46:            'audit.135.106.164.147.sslip.io ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPZcfVwHVIUEU7W0auTb70VKY/aLppXM/54vzpmy0+XV' \
  0e663fd0:.github/workflows/deploy-auto.yml:61:            135.106.164.147|audit.135.106.164.147.sslip.io) ;;
  ```
- interpretation: Read only. The lane touches nothing under .github/**.

### P-09 — the existing tests, and that they run without a daemon: the baseline on the base commit
- captured_at: 2026-10-26
- command: `grep -h -E 'passed|failed' /tmp/claude-0/-root-projects-PDF-Analysis/16441722-42ee-458c-b74f-e08cf340d7b7/scratchpad/baseline-1.log /tmp/claude-0/-root-projects-PDF-Analysis/16441722-42ee-458c-b74f-e08cf340d7b7/scratchpad/baseline-2.log`
- captured_output:
  ```text
  116 passed in 54.40s
  192 passed, 1 skipped in 105.61s (0:01:45)
  ```
- interpretation: Command run before any edit, from the lane worktree at the base: `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider` on (1) test_proxy_tls_path, test_proxy_security_headers, test_readiness_command, test_proxy_rate_limits and (2) test_deploy_script_refusals, test_real_client_address_at_the_edge, test_proxy_config_follows_checkout, test_exposure_text_is_current, test_deployed_stack_probe. All green, no docker daemon: they read the files, or run the scripts against a stub `docker` on PATH.

### P-10 — PyYAML is NOT available to the test environment (the brief says to parse the compose files with it)
- captured_at: 2026-10-26
- command: `/root/projects/PDF-Analysis/.venv/bin/python -c 'import yaml' 2>&1; /usr/bin/python3 -c 'import yaml; print("system python3 has PyYAML", yaml.__version__)' 2>&1`
- captured_output:
  ```text
  Traceback (most recent call last):
    File "<string>", line 1, in <module>
  ModuleNotFoundError: No module named 'yaml'
  system python3 has PyYAML 6.0.1
  ```
- interpretation: The repository venv has no YAML library (test_session_register_volume.py says why: "a pin bought for a test"). The lane uses that file's own indentation split for every test, and parsed the three compose files once with the system python's PyYAML 6.0.1 as evidence (report, section 4). A premise of the brief that differs from the tree; it does not block the work, and it is stated so the integrator is not surprised.

### P-11 — no ACME client, certbot, lego or letsencrypt reference exists in the tree outside docs: nothing is reused
- captured_at: 2026-10-26
- command: `git grep -n -i -l -E 'certbot|letsencrypt|acme\.sh' 0e663fd0 -- . ':!docs' ':!artifacts'`
- captured_output:
  ```text
  (no output)
  ```
- interpretation: Empty output: this lane introduces the client. (The dev host has certbot 2.9.0 installed by apt; it is not used and nothing was run against it except `--help`, to confirm flag names.)

### P-12 — the digest the new image pins is a real one already in the tree
- captured_at: 2026-10-26
- command: `git grep -n -o -E 'alpine:3\.22\.1@sha256:[0-9a-f]{64}' 0e663fd0 -- infra/minio/Dockerfile`
- captured_output:
  ```text
  0e663fd0:infra/minio/Dockerfile:57:alpine:3.22.1@sha256:4bcff63911fcb4448bd4fdacec207030997caf25e9bea4045fa6c8c44de311d1
  ```
- interpretation: The same Alpine base the MinIO image pins. A digest for the certbot package or for an ACME image cannot be obtained without a network; the lane does not invent one (see `infra/acme/client.pin`, which ships UNRESOLVED and is refused by deploy.sh until resolved).

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

The lane commits to `agent/prod-01-tls-acme-01` and pushes nothing. `origin/main` triggers a deployment (`AGENTS.md` section 6) and is not touched.

## Allowed paths

- `infra/deploy/compose.server.yml`
- `infra/deploy/proxy/**`
- `infra/acme/**`
- `infra/deploy/deploy.sh`
- `infra/deploy/verify-deployed.sh`
- `infra/deploy/readiness.sh`
- `infra/deploy/reset.sh`
- `infra/deploy/copy-serve.sh`
- `infra/deploy/env/alpha.env.example`
- `docs/program/DEPLOYMENT_RUNBOOK.md`
- `tests/integration/composition/test_proxy_tls_path.py`
- `tests/contract/test_proxy_security_headers.py`
- `tests/integration/composition/test_deploy_script_refusals.py`
- `tests/integration/composition/test_readiness_command.py`
- `tests/integration/composition/test_acme_deploy_guards.py`
- `tests/integration/composition/test_acme_overlay.py`
- `tests/integration/composition/test_acme_client.py`
- `tests/integration/composition/test_verify_deployed_certificate.py`
- `docs/program/tasks/PROD-01-TLS-ACME-01.md`
- `docs/program/PROD-01-TLS-ACME-01.md`
- `infra/deploy/lib/proxy-listeners.sh`
- `infra/deploy/README.md`

The last two are additions the lane made and the report names: the shared listener function lives in `infra/deploy/lib/` (the directory `ADR-0021` section 2 names; `infra/deploy/lib/forced-command.sh` is the neighbour), and the README's TLS section and file table described the layout this task replaced. `reset.sh` and `copy-serve.sh` were allowed and are **not** touched (`PROD-02` wires the restore paths to the listener decision; the copy key's script is installed apart from the checkout and the owner repeats that install then).

## Forbidden hotspots

- `.github/**`
- `contracts/**`
- migrations and the migration head
- `src/**`
- root dependency and lock files
- any file with a real secret, or with the live name as a default
- `infra/deploy/reload-proxy.sh` (not in the allowed list; two stale hint lines in it are reported, not edited)

## Non-goals

- contacting a certificate authority, building an image, or touching the live host: the staging rehearsal and the first issuance are the owner's steps
- the default-credential check that decides 443 (`PROD-02`), database roles (`PROD-04`), limits (`PROD-05`)
- resolving the client's package version (needs a network)
- choosing between the `sslip.io` name and a name of the owner's own (`R-146ac` leaves that to the owner if the real issuance is refused)

## Deliverables

- `infra/acme/**`: `Dockerfile`, `client.pin`, `entrypoint.sh`, `export-pair.sh`, `check-served.sh`, `compose.acme.yml`
- `infra/deploy/proxy/`: `acme-challenge.conf`, `watch-certificate.sh`, `compose.tls.yml` (rewritten: publishes 443 only), `enable-tls.sh` (messages and comments), `tls/.gitignore` (comment)
- `infra/deploy/lib/proxy-listeners.sh`
- `deploy.sh` (five guards, a compose file list, the listener decision), `verify-deployed.sh` (exit 7), `readiness.sh` (`tls`, `plain-http`), `alpha.env.example`, `compose.server.yml` (comments), `README.md`
- `docs/program/DEPLOYMENT_RUNBOOK.md` section 6 rewritten as the procedure; sections 1, 5, 8, 9 and the host-nginx note adjusted
- four new test files and four modified (the report lists, per modified test, what it asserted before and after)
- the report `docs/program/PROD-01-TLS-ACME-01.md`

## Required tests

- command: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/composition/test_proxy_tls_path.py tests/contract/test_proxy_security_headers.py tests/integration/composition/test_deploy_script_refusals.py tests/integration/composition/test_readiness_command.py tests/integration/composition/test_acme_deploy_guards.py tests/integration/composition/test_acme_overlay.py tests/integration/composition/test_acme_client.py tests/integration/composition/test_verify_deployed_certificate.py`
- expected: `422 passed`
- command: `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` (after the last commit: one contract test refuses a dirty tree)
- expected: green; the counts are in the report

## Integration contract

What the integrator can rely on:

- with `ALPHA_CERT_NAME` empty or absent, every `docker compose` call `deploy.sh` makes is the call it made before this task (one `--file`, the base), and no other script's behaviour changes: `TestNoNameChangesNothing` pins it
- with a name: `deploy.sh` passes `infra/acme/compose.acme.yml`, and `proxy/compose.tls.yml` after it only when `ALPHA_PUBLISH_HTTPS=yes` and the certificate volume holds a pair; `infra/deploy/lib/proxy-listeners.sh` (`listeners_overlay_files`, `listeners_https_verdict`) is the single place that decides, as a pure function of three words, so `PROD-02` replaces the computation of `https_wanted` and nothing else
- `verify-deployed.sh` exits 7 for a certificate that is not acceptable and 4 when the question could not be asked; `--acme-rehearsal` is the one explicit way to accept a staging certificate
- the proxy's only bind mounts stay under `infra/deploy/proxy/` (the rule `reload-proxy.sh` and `verify-deployed.sh` check); the certificate and the webroot are named volumes
- `infra/acme/client.pin` ships `UNRESOLVED`; `deploy.sh` refuses a host with a name set until a person with a network replaces it (runbook section 6, step 1)

## Failure/idempotency/security cases

- a clone missing a terminator file, a bad name or setting, an unresolved pin, a held public port, an unanswerable pair question: each is a refusal before the build (or before `up`), each shown by deleting its guard block
- a second deploy: the own-proxy case of `public-ports-free` is asked of docker by container port; `acme` is healthy only once a pair is exported
- the proxy never mounts the ACME account key; the ACME service has no port, no socket, no host path
- a staging pair never replaces a production one on the volume
- a pair nginx rejects is never applied and the TLS block is taken out again so a restart cannot load it; a failure with and without the block is not blamed on the pair

## Rollback / feature flag

`ALPHA_CERT_NAME` is the flag: empty it (and the other TLS settings, which `deploy.sh` refuses without a name) and deploy; the overlays are no longer passed. The `acme` container the earlier deploy left is removed by the one command in runbook section 6 ("Turning it off"); the volumes stay.

## Handoff

- changed files: see the report, section 2
- commands/results: see the report, section 6
- known limits: see the report, section 8
- integration notes: see the report, section 7
