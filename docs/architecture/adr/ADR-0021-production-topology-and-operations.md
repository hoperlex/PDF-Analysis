# ADR-0021: Production topology and operations: one VPS, TLS in `infra/`, manual copies

- Status: accepted (open: the `AD-04` numbers, pending the `PROD-05a` measurement; the `AD-18` choice after `PROD-20`)
- Date: 2026-10-26; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: `PRODUCTION-ADR-PACK-01`; owner rulings `R-146a`, `R-146b`, `R-146h`, `R-146j`, `R-146k`, `R-146n`, `R-146p`, `R-146s`, `R-146t`, `R-146ac` (server name), `R-146ad` (host size), `R-146ae` (MinIO); `AD-01` confirmed by `R-146p` (server name) and `R-146aa` (ACME mechanism); `AD-02`, `AD-05`, `AD-16` by `R-146w` as written at commit `83600aed`; `AD-03` by `R-146t`; `AD-17` by `R-146x`; `AD-18` settled by `R-146y` (what stands until the measurement); `AD-19` by `R-146z`; `R-153ab`, `R-153af` (2026-11-10); fork section 11: `R-156b`, `R-156d`…`R-156i`, `R-156l`; decision 3's default privileges: `R-156n`; amendment `R-156o`
- Amends: supersedes the reading of `R-1` that no host exists yet (`R-146a`); no earlier ADR is replaced

## Context

`ADR-0002` and `ADR-0020` chose a modular monolith on one PostgreSQL and one private S3 store; neither
said what production runs on, who terminates TLS, what is copied or not provided. The owner decided by
direct poll on 2026-10-26 (`OWNER_RULINGS_2026-09-17.md` section 3.46, `R-146`). Forces: the live
terminator is an nginx outside the repository with a certificate expiring on 2026-12-30 (`D-191`); when decided: no scheduled backup, rollback tooling, memory limit or log rotation (`D-166`). Binding: `AGENTS.md` section
6, `MAIN_AUTODEPLOY_POLICY.md`, `R-46` (`readiness.sh` reports and blocks no deploy; narrowed by
`R-146i`, `R-146s`) and `R-88`, `R-93`, `R-110` (decision 5); `R-146` repeals none.

## Decision

Open: `AD-04` (section 4) is the architect's proposal, not polled, not confirmed; its numbers wait for
the `PROD-05a` measurement on the 4 GiB host (`R-146ad`). `AD-18` (`ADR-0024` decision 5): `R-146y`
settles only what stands until the measurement.

### 1. Topology (`R-146a`)

The production host is the single VPS pinned in `.github/workflows/deploy-auto.yml`, running
`compose.server.yml`; no standby, no failover. Recovery time is the time to restore from the last copy
(`R-146a`); no recovery time or point is promised (`R-146b`). The restoration time is measured once, in
the release rehearsal (`PROD-17`), as a measurement, not a commitment.

Amendment 2026-11-20 (`R-158f`): the workflow no longer pins the host.
- **The repository names its server.** The address, its SSH host key and the checkout path are this repository's Actions variables (`DEPLOY_HOST`, `DEPLOY_KNOWN_HOSTS`, `DEPLOY_PATH`). A repository without them deploys nowhere.
- **The server names its repository.** The host refuses, before it writes or fetches anything, a deployment whose repository is not the one its checkout was cloned from.
- **So a fork** deploys only to the server its owner names, and cannot roll this host back to the fork point even with this host's credentials.
- The host key is still verified out of band before it is stored (`DEPLOYMENT_RUNBOOK.md` section 3).

### 2. The TLS terminator and certificate renewal live in `infra/` (`R-146a`, `R-146p`)

The terminator is the repository's own `proxy` service; the host nginx leaves the design. HSTS
(`max-age=31536000`, no `includeSubDomains`, no `preload`) and a `Secure` session cookie are commitments
(`R-146a`). `AD-01`: **the certificate name is a deploy variable** the owner sets (`R-146p`, `R-146ac`);
this ADR names no host and no DNS provider. **The ACME mechanism is confirmed by `R-146aa`**: an ACME
client in the same compose project (HTTP-01 through a webroot the `proxy` serves; no Docker socket), a
rehearsal on the ACME staging endpoint before the first real issuance, and `verify-deployed.sh` failing
below 14 days of certificate life (the architect's number); settings:
`docs/program/DEPLOYMENT_RUNBOOK.md` section 6.

**First-boot and restore listener binding (`R-146s`).** Three listeners; the public application listener
is conditional:

| Listener | Where | Serves | When it exists |
| --- | --- | --- | --- |
| plain application | `127.0.0.1:${ALPHA_HTTP_PORT}` | the whole application | always |
| challenge | public port 80 | only the ACME challenge path and a redirect to HTTPS; **no application route** | once ACME is configured, so issuance and renewal work while the password is still the seeded one |
| application | public port 443 | the application over TLS with HSTS | only in a deploy whose `python -m auditmanager.access.check` exits `0` and whose certificate pair exists |

A never-published host, or one after `reset.sh`, stays on loopback until the administrator has changed
the password through an SSH tunnel; the next deploy publishes 443. **A restore can bring the default
credential back**: every restore path (`reset.sh --restore`, `copy-serve.sh restore-db`) ends with the
same check and, on exit `1`, recreates the `proxy` without the 443 overlay, so the site is unreachable
from outside until the password is changed (the consequence `R-146s` accepts). Which accounts fail the
check: `R-146z` (`ADR-0023` decision 3).

### 3. Database roles (`R-146n` item 1)

`AD-02`, confirmed by `R-146w`: the owner role (`POSTGRES_USER`) becomes the **migrator**: it owns every
object, runs `migrate` and `release-notes`, serves the operator tools and stays a superuser (migration
`0013` runs `CREATE EXTENSION vector`). A new **application** role serves `api` and `worker`: it can log
in, is not a superuser, cannot create objects or roles, owns nothing, holds `USAGE` on schema `public`,
`SELECT`, `INSERT`, `UPDATE`, `DELETE` and sequence usage, and no `TRUNCATE`; tables a trigger declares
append-only or immutable get `SELECT` and `INSERT` only, so `UPDATE` and `DELETE` are refused twice, by
privilege and by trigger.

**Grants are an idempotent step, not a migration** (a `--no-privileges` restore would lose granted
privileges, and a password cannot live in a revision): `infra/deploy/apply-grants.sh` creates the role if it is absent and derives every grant from the catalog and the grant classification. `AD-02` as confirmed also named `ALTER DEFAULT PRIVILEGES` for later tables; the first build of the step departed from that sentence (a relation the classification did not name got no rights and stopped the deploy, `[grants_unclassified]`, exit 3; `docs/program/PROD-04-DB-ROLES-01.md` item 2), and the owner reversed the departure (`R-156n`). The step now also runs, as the migrator, `ALTER DEFAULT PRIVILEGES FOR ROLE <migrator> IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES` and `GRANT USAGE ON SEQUENCES` to the application role (read and write in full; no `TRUNCATE`, nothing else), so a table or sequence a later migration creates is usable at once. A classified relation keeps exactly its class (the step runs after every `migrate` and narrows it, so an append-only table loses `UPDATE` and `DELETE` again); a relation of schema `public` that no class names keeps the default rights, and the step **warns** about it by name (`[grants_unclassified]` on stderr, exit 0, the deploy goes on; `deploy.sh` repeats the warning). The classification stays required at development time: `tests/integration/recovery/test_grant_classification.py` is red for a table with no row. `--check` verifies the default privileges as well. `deploy.sh`
runs it after `migrate` and before `api` and `worker` start; `reset.sh --restore` and `copy-serve.sh
restore-db` run it after the restore. **No Alembic revision is added.** `DATABASE_URL` stays the
application's; the migrator's URL (`MIGRATOR_DATABASE_URL`) goes only to `migrate`, `release-notes`, the
operator tools, the grants step and the ownership wrappers (`purge-product-data.sh`, the erase wrapper
of `ADR-0022`). PostgreSQL stays inside the compose network without TLS.

### 4. Memory and log limits (`R-146n` item 2, `D-166`)

`AD-04` (not polled; the architect's, to be confirmed): every long-running service gets a memory limit
and the `json-file` log driver with `max-size` and `max-file`. **This ADR fixes no number**: the host
has 4 GiB RAM (`R-146ad`), the limits plus the host's needs must fit, and a limit below a large
analysis's footprint would kill the worker mid-run (`AD-18`). The owner measures on the VPS during a
500-page analysis (`PROD-05a`) and sets each limit above the peak by a stated margin; an OOM kill is
recovered by lease expiry and retry (`ADR-0007`) at the price of a failed attempt. `compose.server.yml`
reads `mem_limit` from `ALPHA_MEM_LIMIT_<SERVICE>` for the six long-running services; the variables ship
empty (no limit) until the owner sets values (`DEPLOYMENT_RUNBOOK.md` section 19).

### 5. Copies and the dump before every migration (`R-146b`, `R-146n` item 3, `R-146t`)

Backups are manual until 1.0: no schedule, no maintained off-host target, no recovery point or time
commitment (accepted risk **A-1**, section 10). The compensation is a manual dump before every
migration, which `R-146t` makes `deploy.sh` demand as a fresh receipt. **`R-93` continues to bind**: a
one-off copy (quiesced dump, inventory, fetch to the development host, restore test, attestation)
precedes every migrating publication whenever the stand holds real client data (`R-88`, `R-93`,
`R-110`); `R-146f` makes the production release that moment.

`AD-03`, confirmed by `R-146t`: **the receipt is the copy record that `copy-serve.sh dump-db` writes**
(dump file, SHA-256, `quiesced_at`; `W54-STAND-COPY-01.md` section 3.2), not a second artefact. The
`stand-copy-fresh` guard of `deploy.sh` refuses a deploy when the `real_data` marker exists and the
checkout carries a migration the database lacks, unless the record is open, has its dump, is attested
for this commit and its `quiesced_at` is under **24 hours** old; with no pending migration no receipt is
needed, and before the marker exists (`R-110`) nothing changes. The dump is taken through the
owner-installed copy key (`DEPLOYMENT_RUNBOOK.md` section 13), whose installation is a precondition of
the production release (`PROD-03`); it covers PostgreSQL only (assumption: no migration touches the
bucket).

`AD-17`, confirmed by `R-146x`: **the full `R-93` attestation stays after 1.0**, with the receipt check
on top; the latest pre-migration copy therefore keeps leaving the host for the restore test (section 9).

### 6. Deploy, verification and rollback

The deployment path is `AGENTS.md` section 6 and `MAIN_AUTODEPLOY_POLICY.md`. **Rollback is a forward
fix**: an older image may not run against a newer schema, and the migrations' downgrades refuse where
data would be lost. A failed migrating release is recovered by a reviewed revert through the same path
and, if the schema must go back, by the owner's way back of the copy key, `copy-serve.sh restore-db
<STAMP> <dump-sha256>`, which consumes exactly the PostgreSQL-only dump the receipt names (order in the
runbook: restore, a reviewed revert re-attested for its SHA, then `resume`). `reset.sh --restore` is
**not** that restore: it accepts only its own dump format. After either restore the grants step re-runs,
the check of section 2 decides whether the application listener may stay published, and every
`token_epoch` is raised (`R-52`; `restore-db` does so since `PROD-02`, `DEPLOYMENT_RUNBOOK.md` section
6).

### 7. The manual release checklist and the manual scan (`R-146h`, `R-146n` item 5)

There is no CI workflow and no automated dependency or image scan, and none is added (`A-3`). The
compensation the owner accepted is one line of the release checklist, worked through as
`docs/program/RELEASE_PROCESS.md` "Production release checklist":

1. the candidate SHA, the release authority `MAIN_AUTODEPLOY_POLICY.md` requires, a clean tree;
2. the complete gate on that exact tree, literal `GATE OK` (`D-205`);
3. **the manual dependency and image scan** (`AD-05`'s helper): output and date in the release record,
   each finding decided;
4. if the database head changes, the pre-migration copy and receipt in the `R-93` order of section 5;
5. the heavy-step stop rule (`capacity-probe.sh`) before the build, and the pruning below;
6. after the push: the workflow finished and `verify-deployed.sh` exits `0` (default-credential and
   certificate-expiry checks included);
7. the public probes (rows 2 to 4 of the table below);
8. the tag and the `RELEASES.md` row only after items 6 and 7.

**Pruning (manual)** of `infra/deploy/dumps/` (`RELEASE_PROCESS.md` "Pruning"): keep the last two
directories and any a release record names, delete the rest by hand; a dump holding client data goes as
soon as the release it guarded is accepted, and after an erase (`ADR-0022`). `AD-05`, confirmed by
`R-146w`: the helper is `scripts/release/manual_scan.sh` (`RELEASE_PROCESS.md` "The manual scan"): it
runs the scanners the operator has installed and never prints a pass when one is missing. It does not
close `D-122`; it makes the absence of a scan visible at every release.

### 8. What is not built (`R-146j`, `R-146k`)

One worker slot and no time promise (`ADR-0024`). No JSON logs, redaction layer, metrics, tracing or
alerts; an incident is read from container logs. The only observability additions are the access audit
events of `ADR-0023` and the erase journal of `ADR-0022`. `ADR-0015` stays the design rule for what is
built; its missing channels are a known gap of 1.0 (`R-146k`).

### 9. What the host must provide, and what it does not

The host must provide: the tools of `DEPLOYMENT_RUNBOOK.md` section 1; inbound 80, 443 and SSH; a DNS
name; outbound HTTPS to the ACME service and the model provider; one filesystem for all data (size not
given: `R-146ad` gives RAM only); a synchronised clock (assumption: ACME and `ADR-0023`'s token lifetime
depend on it).

It does not provide, and this programme does not build: high availability or failover; a maintained or
scheduled off-host copy of the database or the bucket; metrics, alerts or log shipping; a service-level
objective; a second operator (`R-146am`, accepted risk `A-8`); a firewall policy beyond the published
ports (a Docker-published port bypasses `ufw`: `D-49`). Three copies leave the host, none a backup of
the live service: the offline key-ring copy (`R-146n` item 7), the latest pre-migration copy fetched for
the `R-93` restore test (while `R-146x` keeps it) and the corpus bundle on the development host
(`R-88`); the bucket is not among them.

Object store: MinIO is built from source at upstream's final release and upstream is archived (`D-119`);
the live volume was never inventoried (`D-123`). `R-146ae` (`PROD-19`): the source build stays through
1.0 without inventory (accepted risk `A-6`; reopen on a published advisory against MinIO, any loss of
objects, or a client asking for a storage statement); under `A-3` no scan covers that image.

### 10. Accepted risks

- **A-1 (`R-146b`).** Client data can be lost back to the last manual copy; the copies share the host's
  disk, except the latest pre-migration copy fetched to the development host (not a scheduled backup).
  Reopen on the first real client upload that the owner cannot afford to lose.
- **A-3 (`R-146h`).** No machine checks a push and no scan runs unless a person runs it; a vulnerable
  dependency or image can reach the host (`D-122` stays open). Reopen trigger (`AD-16`, confirmed by
  `R-146w`): before the first release after a published advisory for a component in `uv.lock`,
  `web/package-lock.json` or the pinned images, or before any release to users outside the owner's
  organisation.
- **A-4 (architect's consequence of `R-146a` and `R-146b`).** One host, no failover, no maintained copy
  off it: a host loss, a provider loss of the VPS, an operator error or a ransomware event ends the
  service and may end the data. Reopen trigger (`AD-16`, confirmed by `R-146w`): the same as A-1, and
  any decision to promise a recovery time or point to a client.

### 11. The fork server (`R-156b`, `R-156d`…`R-156i`)

- **Host.** The fork runs the stack of section 1 on its own server: 32 GB RAM, 12 CPU cores, no GPU
  (`R-156h`); development and production share the machine and its disk. The current production VPS is
  unchanged until the owner decides otherwise.
- **Data.** Only the norms corpus arrives (`R-156g`): the verified bundle, transferred once by the owner and
  imported locally.
- **Database.** PostgreSQL stays in the stack (`R-156d`); for the fork this replaces the planned managed
  cluster (`R-153ab`, `docs/program/YC-MOVE-PLAN.md`).
- **Objects.** MinIO in the stack at bring-up; an early lane of the fork moves the objects to a private Yandex
  Object Storage bucket (`R-156f`, `ADR-0006`). Region, bucket and account are the owner's when that lane
  starts.
- **Memory.** `AD-04` applies: limits are fixed by a measurement on that server. Starting budget of the fork storage plan r2 (`R-156l`):
  PostgreSQL 6 GB, embedder 8 GB and 8 cores, worker 2.5 GB, api 1.5 GB, web and proxy 0.75 GB, MinIO 1 GB
  until the bucket move, image build 3 GB, development 5 GB. Amendment 2026-11-18 (`R-156o`): the embedder's
  starting budget is 4 GB, not 8 GB (BGE-M3 F32 for the beta; the 4 GB freed go to the page cache and worker
  slots), and the `AD-04` measurement includes the embedder's p95 latency beside running LLM workers.
- **Copies.** No cross-host transport (`R-156e`): the dump before every migration, its receipt (`R-146t`) and
  the trial restore (`R-93`) stay and run on that server; the copy key (`PROD-03`) is not needed there.
- **Risk.** No copy leaves the server, so a disk loss loses the database, the objects and every copy (A-1,
  A-4); accepted while it holds only the re-importable corpus. **Open:** the off-disk backup target, decided
  after deployment and before the first client data (`R-156i`).

## Commitments and their mechanical checks

Run on the VPS from the checkout `/srv/auditmanager`; `<name>` is the public DNS name and `$DC` is
`docker compose --env-file infra/deploy/env/alpha.env -f infra/deploy/compose.server.yml`. `$DC config`
prints secrets in clear: rows pipe it into a program that prints names only, and its raw output is never
shown or pasted.

| # | Commitment | Mechanical check, which fails when the commitment is false |
| --- | --- | --- |
| 1 | Only the proxy publishes a port | `tests/integration/composition/test_acme_overlay.py`; on the VPS `$DC config --no-env-resolution --format json` lists `ports` on `proxy` alone |
| 2 | TLS answers on the public name with a trusted chain | `curl -sS -o /dev/null -w '%{http_code} %{ssl_verify_result}\n' https://<name>/login` prints `200 0` |
| 3 | HSTS on every TLS answer (`R-146a`) | `tests/integration/composition/test_proxy_tls_path.py`; on the VPS the `/login` answer carries `strict-transport-security: max-age=31536000` |
| 4 | The session cookie is `Secure` (`R-146a`) | an inert `am_session` cookie sent to `/bff/v1/projects` draws `401` and a clearing `Set-Cookie` with `Secure` (`EXPOSURE-REVIEW-01.md` E-2) |
| 5 | The certificate is renewed before it expires | `openssl x509 -noout -checkend 1209600` on the served certificate exits 0; `verify-deployed.sh` runs it |
| 6 | A deployment is not successful while `admin`/`password` is valid (`R-146i`, `R-146s`, `R-146z`) | `tests/integration/composition/test_default_credential_gate.py`; on the VPS `access.check` exits `0`, and while the gate fails 443 is unpublished |
| 7 | The application role cannot change the schema, before and after a restore (`R-146n` item 1) | `tests/integration/db/test_application_role_grants.py::test_the_adr_row_7_query_prints_f_f_f_t`, again after a `restore-db` rehearsal |
| 8 | Memory and log limits on every long-running service (`R-146n` item 2) | `tests/integration/composition/test_compose_log_and_memory_limits.py`; the rendered `$DC config` shows both on every service except `migrate`, `release-notes`, `s3-init` (memory once the owner sets values) |
| 9 | A migrating deploy follows a fresh copy receipt (`R-146n` item 3, `R-146t`) | `tests/integration/composition/test_stand_copy_fresh.py`, `test_deploy_script_refusals.py`: `REFUSED [stand-copy-fresh]`, exit `3`, before any build |
| 10 | The release checklist carries the manual scan (`R-146n` item 5) | `grep -n "manual_scan" docs/program/RELEASE_PROCESS.md` has a hit; `scripts/release/manual_scan.sh --check-tools` exits non-zero when a scanner is missing |
| 11 | No CI workflow is added (`R-146h`) | `tests/contract/test_deploy_auto_workflow.py`; `.github/workflows` holds only `deploy-auto.yml` |
| 12 | One worker slot (`R-146j`) | the `worker` table has one live row (heartbeat under 90 s) with `slots` 1 |
| 13 | No metrics, tracing or error-reporting library (`R-146k`); **documentation check only** | `rg -il "prometheus\|opentelemetry\|sentry" src infra --glob '!*.md'` prints nothing; `grep -c "@opentelemetry" web/package-lock.json` prints `2` (the web framework's optional peer) |
| 14 | The missing off-host copy stays visible (`A-1`, `A-4`); do not silence it | `readiness.sh` prints `readiness FINDING off-host-backup`; `tests/integration/composition/test_readiness_command.py` (readiness reports, never gates: `R-46`) |
| 15 | A restore drill was run at the released head; **documentation check only**: the drill is the owner's act | a `docs/program/RECOVERY-DRILL-*.md` record has `head:` equal to the released head and `result: pass`; none exists at the current head (`D-216`) |

## Consequences

- Positive: the terminator, its renewal and its headers are in the repository and deployed with the
  application (`D-191`); the API process cannot change the schema; a migrating release cannot reach a
  stand with real client data without an attested copy of the last day.
- Cost: a failed renewal takes the site off HTTPS without any alert (`R-146k`); two database roles
  double the places a credential lives.
- Cost: one host and manual copies mean a disk loss loses everything on it (`A-1`, `A-4`); rollback
  needs a gate run, which cannot run on this development host (`D-205`).

## Alternatives considered

1. **Keep the host nginx as the terminator** — rejected by `R-146a`: its configuration would stay
   outside the tests and the deploy.
2. **A certificate placed and renewed by hand** — rejected by `R-146a` (`D-191`; the interim owner item
   is `PROD-21`).
3. **Nightly dump with an off-host mirror** — the recommended option; the owner chose manual copies
   (`R-146b`); `A-1`.
4. **A managed PostgreSQL and managed object storage** — rejected for the present topology. Asked
   2026-11-10 (`OWNER_RULINGS_2026-09-17.md` section 3.55): a full move to Yandex Cloud is planned, with
   the night-window option as a temporary decision on local storage (`R-153ab`); the database is not
   moved now (`R-153af`). Decided in principle, not started: no decision here changes
   (`docs/program/YC-MOVE-PLAN.md`); `ADR-0029` temporary decision 2 (the offline encoder in a night
   window on the 4 GB host) ends when the database, the storage and a separate encoder machine are in
   place.
5. **A second receipt file or a new `dump-db.sh`** — rejected: the copy record is the receipt (section
   5).

## Verification

The commitment rows and the tests they name; the release rehearsal (`PROD-17`): a clean-clone deploy,
`verify-deployed.sh` exit `0`, the probes of rows 2 to 5, and a real `restore-db` on a copy (timed) at
the released head.

## Revisit trigger

Replace this ADR when: the first real client upload that the owner cannot afford to lose (`A-1`); a
second host, a managed database or an off-host copy is decided; a recovery time or point is promised; a
second operator joins; the VPS size is measured and does not fit the 500-page envelope (`D-171`); CI or
scanning is added (`A-3`). "A managed database is decided" is **armed, not met** (`R-153ab` decides it
in principle): replace this ADR on the day the owner orders the move to start (step 0 of
`docs/program/YC-MOVE-PLAN.md`), by an ADR recording the new topology, where the data may be held and
the new failure domains.

## History

- 2026-10-26 — accepted for production by the repository owner; the `AD-` confirmations in Basis came by
  later rulings; `AD-04` not polled.
- 2026-11-10 — addendum (`YC-MOVE-PLAN`, `R-153ab`, `R-153af`): a move to Yandex Cloud is planned, not
  started; folded into Alternative 4 and the Revisit trigger.
- 2026-11-18 — compressed (ADR-OPTIMISE-01); the full earlier text: git show fb6c2203e:docs/architecture/adr/ADR-0021-production-topology-and-operations.md
- 2026-11-18 — status statements updated to dev fb6c2203e: decision 3 (the grants step's recorded departure from `AD-02`'s `ALTER DEFAULT PRIVILEGES`; the migrator stays a superuser); decision 6 (`restore-db` raises `token_epoch`); decisions 2, 4, 9
  (`R-146ac`, `R-146ad`, `R-146ae`; limit mechanism present, values empty); the table's snapshot columns dropped.
- 2026-11-18 — section 11 added: the fork server (`R-156b`, `R-156d`…`R-156i`).
- 2026-11-18 — decision 6 and checklist item 1 follow `MAIN_AUTODEPLOY_POLICY.md` (effective 2026-11-02) and `AGENTS.md` section 6: a delegated release integrator replaces «the owner's direct instruction naming it» of the `AD-05` checklist as `R-146w` confirmed it at `83600aed`; a change by the owner's process rule, not a status update.
- 2026-11-18 — decision 3: `ALTER DEFAULT PRIVILEGES` restored and an unclassified relation warns instead of refusing (owner, R-156n).
- 2026-11-18 — section 11 amended: embedder budget 4 GB, p95 latency in the `AD-04` measurement (`R-156o`).
- 2026-11-20 — decision 1 amended: the deploy target is the repository's variables, and the host accepts only its own repository (`R-158f`).
