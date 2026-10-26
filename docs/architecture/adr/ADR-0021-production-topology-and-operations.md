# ADR-0021: Production topology and operations: one VPS, TLS in `infra/`, manual copies

- Status: accepted for production by the repository owner (`R-146a`, `R-146b`, `R-146h`, `R-146j`, `R-146k`, `R-146n`); the implementation choices marked `AD-` are the architect's, proposed and not yet confirmed
- Date: 2026-10-26
- Owners: repository owner / `PRODUCTION-ADR-PACK-01`
- Supersedes: the reading of `R-1` that no host exists yet (`R-146a`); no earlier ADR is replaced
- Related principles: P-05, P-10, P-13, P-14

## Context

`ADR-0002` chose a modular monolith and `ADR-0020` fixed the alpha runtime on one PostgreSQL and
one private S3 store. Neither said what the production release runs on, who terminates TLS, what
is copied, or what is deliberately not provided. The owner decided these by direct poll on
2026-10-26 (`OWNER_RULINGS_2026-09-17.md` section 3.46, `R-146`). The facts below were read from
the tree at `integration/ar-close-1026` (`4d7b7c38`) on the same day; a fact the tree cannot show
is marked "assumption".

- **Topology.** `infra/deploy/compose.server.yml` defines `postgres` (a repository-owned
  derivative of a digest-pinned base plus pgvector), `s3` (MinIO built from source,
  `RELEASE.2025-10-15T17-29-55Z`, upstream archived: `D-119`), `s3-init`, `migrate` and
  `release-notes` (one-shot), `api`, `worker`, `web` and `proxy` (nginx 1.27). The proxy is the
  one service with `ports:`; its plain listener binds `127.0.0.1` unless `ALPHA_BIND_ADDRESS` says
  otherwise (`D-49`). Images are built on the host. No service has a memory limit, a CPU limit or
  a log-rotation option (`D-166`). Restart policy is `unless-stopped`. Health checks exist on
  `postgres`, `s3`, `api`, `worker` and `web`.
- **TLS.** `infra/deploy/proxy/compose.tls.yml` is an overlay that mounts a certificate pair
  from `infra/deploy/proxy/tls/` and `enable-tls.sh` installs `tls-server.conf` only when both files
  are non-empty. That block sends `Strict-Transport-Security: max-age=31536000` and sets
  `X-Forwarded-Proto` to `https`, which is what makes the web tier issue a `Secure` session
  cookie (`web/src/app/bff/session/store.ts`). Nothing in the tree obtains or renews a
  certificate. The stand's live terminator is a different nginx on the host, outside the
  repository, with a certificate that expires on 2026-12-30 (`D-191`, `EXPOSURE-REVIEW-01.md`
  E-2); its configuration, and therefore whether HSTS and `Secure` are in effect today, cannot
  be read from the tree.
- **Deployment.** `.github/workflows/deploy-auto.yml` runs on a push to `main`, connects over SSH to
  the one pinned host, requires a clean checkout, selects the triggering SHA, runs
  `infra/deploy/deploy.sh` and then `infra/deploy/verify-deployed.sh`. It has no test step. There
  is no rollback tooling: `RELEASE_PROCESS.md` makes a rollback a reviewed forward revert.
- **Data.** One PostgreSQL, no replica; `migrate`, `release-notes`, `api` and `worker` all
  connect with the same `DATABASE_URL`, whose user is `POSTGRES_USER` (`alpha.env.example`). In
  the official PostgreSQL image that bootstrap user is a superuser (assumption: the image's
  documented behaviour; the check is the query in `AD-02`). Pool 5 plus 5 overflow
  (`src/auditmanager/shared/db/config.py`). Migrations run only through the one-shot `migrate`
  service; the head is `0032_ar_v3_run_group`. The S3 bucket is private; `bucket-init.sh` and the
  adapter configure no versioning, lifecycle or encryption at rest (a search found none).
- **Copies.** No scheduled backup exists. A verified dump is taken by `reset.sh` and
  `purge-product-data.sh`, both of which then destroy data, and by the owner's forced-command key
  (`copy-serve.sh dump-db`), which stops the writers and was deferred to the first real upload
  (`R-110`). `deploy.sh` does **not** dump: its only guard is `R-93`, which refuses a migrating
  publication while an *open, unattested* copy record exists (`stand-copy-unattested`) and says nothing
  when no record exists. The last recorded restore drill is `RECOVERY-DRILL-0029-01.md`
  (synthetic, head `0029`); none exists at `0032` (`D-216`).
- **Process rules that bind this ADR.** `AGENTS.md` section 6 and `MAIN_AUTODEPLOY_POLICY.md`: a
  push to `origin/main` is a deployment and needs the owner's separate instruction naming the
  exact SHA. `R-46`: `readiness.sh` reports and registers, and blocks no deploy; `R-146i` is the
  one ruling that narrows that (see `ADR-0023`).

## Decision

### 1. Topology (`R-146a`)

The production host is the single VPS pinned in `.github/workflows/deploy-auto.yml`, running
`compose.server.yml`. There is no standby host and no failover. The time to recover is the time to
restore from the last copy (`R-146a`); no numerical recovery time or recovery point is promised
(`R-146b`). The restoration time is measured once, in the release rehearsal of
`PRODUCTION-READINESS-PLAN-01.md` (`PROD-17`), and recorded as a measurement, not as a commitment.

### 2. The TLS terminator and certificate renewal live in `infra/` (`R-146a`)

The terminator is the repository's own `proxy` service. The host nginx outside the repository stops
being part of the design. `R-146a` makes HSTS and a `Secure` session cookie commitments; both follow
from terminating TLS in the stack, because the `$scheme` the proxy forwards is then `https`.

`AD-01` (architect's implementation decision within `R-146a`, to be confirmed):

- An ACME client runs as a service of the same compose project, from a digest-pinned image built
  or pulled like every other image, using the HTTP-01 challenge through a webroot the `proxy`
  serves. It writes the pair to a named volume that the `proxy` mounts read-only. It does not mount
  the Docker socket. The `proxy` re-reads the certificate on a timer (a `nginx -s reload` loop
  started by an executable in `/docker-entrypoint.d/`, the mechanism `enable-tls.sh` already
  uses), so no service needs the right to restart another.
- Three listeners: public port 80 serves only the challenge path and a redirect to HTTPS; public
  port 443 serves the application with HSTS; the existing plain application listener stays on
  loopback, because `deploy.sh`'s `proxy-answers` guard requires `401` on it and a redirect
  there would fail every deploy (`DEPLOYMENT_RUNBOOK.md` section 6). The single variable
  `ALPHA_BIND_ADDRESS` therefore stops being enough and the lane splits it.
- `verify-deployed.sh` fails when the served certificate has fewer than 14 days left (the 14 is the
  architect's number). `readiness.sh` `tls` (which today only tests that a pair exists on disk) and
  `plain-http` are rewritten for the new layout.
- A rehearsal against the ACME staging endpoint comes before the first real issuance.

Open and not decided by this ADR: the DNS name the certificate is issued for. The temporary
address in `MAIN_AUTODEPLOY_POLICY.md` is an `sslip.io` name. Whether ACME issuance for a name under
a shared public domain is practical is an external fact the tree cannot show; the owner's own
domain, if there is one, is not recorded anywhere in the tree.

HSTS stays at `max-age=31536000` without `includeSubDomains` and without `preload`, exactly as
`tls-server.conf` sends it today.

### 3. Database roles (`R-146n` item 1)

`AD-02` (to be confirmed): the existing owner role (`POSTGRES_USER`) becomes the **migrator**: it
owns every object, runs `migrate` and `release-notes`, and is the role the operator tools that need
ownership connect as (`product_purge.py` refuses any other: its `owner-may-write` guard; the
operator erase of `ADR-0022` has the same need). A new **application** role is used by `api` and
`worker`: it can log in, is not a superuser, cannot create objects or roles, owns nothing, holds
`SELECT`, `INSERT`, `UPDATE`, `DELETE` and sequence usage on the tables, and holds no `TRUNCATE`.
Tables that a trigger declares append-only or immutable (`schema_coverage.TRIGGERS`, trigger
functions `am_append_only` and `am_immutable_row`) get `SELECT` and `INSERT` only, so the database
refuses `UPDATE` and `DELETE` for the application twice, by privilege and by trigger.

The role is created by an idempotent step of `deploy.sh` before `migrate` (a password cannot live in
an Alembic revision); the grants, and `ALTER DEFAULT PRIVILEGES` so that a later migration's table
is covered, are applied by a revision at the migration head, with a guard test that fails when a
table is neither granted nor listed as migrator-only. The proof that the grants are enough is the
`tests/integration` directories of the contexts running as the application role. Connection:
`DATABASE_URL` stays the application's; the migrator's URL is a second variable that only
`migrate`, `release-notes` and the operator tools receive. The connection to PostgreSQL stays inside
the compose network without TLS, as today.

### 4. Memory and log limits (`R-146n` item 2, `D-166`)

`AD-04` (to be confirmed): every long-running service gets a memory limit and the `json-file` log
driver with `max-size` and `max-file`. **This ADR fixes no number**: the VPS size is not known
(open), and a limit set below the 500-page analysis footprint (`D-171`: 307 s plus 415 s on a loaded
host) would kill the worker mid-run. The owner measures on the VPS with
`infra/deploy/capacity-probe.sh` (free disk and RAM) and `docker stats --no-stream` during a
500-page analysis; the limit is set above the measured peak by a margin the lane states. An OOM kill
of the worker is recovered by the existing lease expiry and retry (`ADR-0007`), at the price of a
failed attempt.

### 5. Copies and the dump before every migration (`R-146b`, `R-146n` item 3)

Backups are manual until 1.0. There is no schedule, no off-host target, and no recovery point or
recovery time commitment. This is accepted risk **A-1** (below). The compensating measure the owner
accepted is a manual dump before every migration.

`AD-03` (to be confirmed): the tree has no non-destructive operator command that dumps and verifies
(the dump tools above either destroy data afterwards or are a forced-command interface for the
owner's remote key). A new `infra/deploy/dump-db.sh` takes `pg_dump --format=custom` into
`infra/deploy/dumps/` (git-ignored), reads it back with `pg_restore --list`, and writes a receipt
containing the database's current Alembic head and the dump's SHA-256. `deploy.sh` gains a guard in
the `R-93` pattern that refuses a deploy whose checkout carries a revision above the database's head
unless a receipt for that head exists and is newer than 24 hours. The alternative is a checklist
line without a guard, which is what the owner's wording literally says; the guard is proposed
because a dump nobody is stopped from forgetting is the failure `R-93` was written against. The dump
covers PostgreSQL only; the S3 bucket is not touched by a migration (assumption: every revision under
`db/migrations/versions/` is SQL), so the pairing of the two is not needed for a rollback.

### 6. Deploy, verification and rollback

The deployment path is unchanged: owner instruction naming the SHA, fast-forward to `main`, the
workflow, `deploy.sh`, `verify-deployed.sh` (`AGENTS.md` section 6). **Rollback is a forward fix.**
An older image cannot be started against a newer schema, so a failed migrating release is
recovered by a reviewed revert deployed through the same path and, if the schema must go back, by
restoring the pre-migration dump with `infra/deploy/reset.sh --restore <dump directory>`, whose
behaviour (every credential revoked, default credentials reported) is `R-52`.

### 7. The manual release checklist and the manual scan (`R-146h`, `R-146n` item 5)

There is no CI workflow and no automated dependency or image scan, and none is added. The
compensation the owner accepted is one line of the release checklist. The checklist for the
production release, kept here until a later lane writes it into `RELEASE_PROCESS.md`:

1. the candidate SHA, the owner's direct instruction naming it, a clean tree (`MAIN_AUTODEPLOY_POLICY.md`);
2. the complete gate on that exact tree with the literal `GATE OK`, on a host that can run it (`D-205`);
3. **the manual dependency and image scan**: run `AD-05`'s helper, attach its output and date to the
   release record, and decide each finding;
4. if the database head changes, the pre-migration dump and its receipt (section 5);
5. the heavy-step stop rule: `capacity-probe.sh` before the build;
6. after the push: the workflow finished successfully and `verify-deployed.sh` exits `0` on the host,
   which includes the default-credential check (`ADR-0023`) and the certificate-expiry check;
7. the public probes (the table below, rows 2 to 4);
8. the tag and the `RELEASES.md` row only after items 6 and 7.

`AD-05` (to be confirmed): the helper is `scripts/release/manual_scan.sh`. It prints an inventory (the
resolved Python packages of `uv.lock`, the npm packages of `web/package-lock.json`, the image
digests named in `compose.server.yml`) and runs whichever of `pip-audit`, `npm audit` and an image
scanner the operator has installed, and it never prints a pass when a scanner is missing or the
vulnerability database could not be reached. The scanners need network access to a vulnerability
feed; the operator runs them from a machine that has it. This does not close `D-122`; it makes the
absence of a scan visible at every release.

### 8. What is not built (`R-146j`, `R-146k`)

One worker slot and no time promise: the queue grows serially (`ADR-0024` states what that means).
No JSON logs, redaction layer, metrics, tracing or alerts; an incident is read from container logs
with `docker compose logs`. The only observability additions are the access audit events of
`ADR-0023` and the erase journal of `ADR-0022`.

### 9. What the host must provide, and what it does not

The host must provide: `bash`, `docker` with the compose v2 plugin, `curl`, `sed` and `git`
(`DEPLOYMENT_RUNBOOK.md` section 1); inbound 80 and 443 and SSH for the deploy user; a DNS name
for the certificate; outbound HTTPS to the ACME service and to the model provider; disk for the
database, the bucket, the images and the dumps, all on the same filesystem (the size is open); a
synchronised clock (assumption: ACME validation and the one-hour token lifetime depend on it).

The host does not provide, and this programme does not build: high availability or failover; a copy
of anything off the host (the dumps, the key ring and the bucket live on one machine); metrics,
alerts or log shipping; a service-level objective; a second operator; a firewall policy beyond
the published ports (a Docker-published port bypasses `ufw`: `compose.server.yml`, `D-49`).

### 10. Accepted risks

- **A-1 (`R-146b`).** Client data can be lost back to the last manual copy. A disk loss on the one host
  loses the copies as well, because they sit on the same disk. Reopen on the first real client upload
  that the owner cannot afford to lose (`R-146b`).
- **A-3 (`R-146h`).** No machine checks a push and no scan runs unless a person runs it before a release. A
  vulnerable dependency or image can reach the host. `D-122` stays open. Proposed reopen trigger
  (`AD-16`, the architect's, to be confirmed): before the first release that follows a published advisory for a
  component in `uv.lock`, `web/package-lock.json` or the pinned images, or before any release to users
  outside the owner's organisation.
- **A-4 (architect's consequence of `R-146a` and `R-146b`).** One host, no failover, no copy of
  anything held off that host. A host loss, a provider loss of the VPS, an operator error or a
  ransomware event ends the service and may end the data. Proposed reopen trigger (`AD-16`): the same as A-1,
  and any decision to promise a recovery time or recovery point to a client.

## Commitments and their mechanical checks

Run on the VPS from the checkout `/srv/auditmanager`, `<name>` being the public DNS name and `$DC`
being `docker compose --env-file infra/deploy/env/alpha.env -f infra/deploy/compose.server.yml`.
`docker compose config` prints secrets in clear (`provider.env.example` says so); the rows below pipe it
into a program that prints names only, and its raw output is never shown or pasted.
"Exists" means the check can be run today; the lane named delivers the rest
(`PRODUCTION-READINESS-PLAN-01.md`).

| # | Commitment | Mechanical check, which fails when the commitment is false | Exists | Delivered by |
| --- | --- | --- | --- | --- |
| 1 | Only the proxy publishes a port | `$DC config --no-env-resolution --format json \| python3 -I -c "import json,sys;print(sorted(k for k,v in json.load(sys.stdin)['services'].items() if v.get('ports')))"` prints `['proxy']` | command yes | `PROD-01` keeps it true |
| 2 | TLS answers on the public name with a trusted chain | `curl -sS -o /dev/null -w '%{http_code} %{ssl_verify_result}\n' https://<name>/login` prints `200 0` | command yes | `PROD-01` |
| 3 | HSTS on every TLS answer (`R-146a`) | `curl -sSI https://<name>/login \| grep -i '^strict-transport-security: max-age=31536000'` exits 0; in the tree `tests/integration/composition/test_proxy_tls_path.py::test_hsts_is_sent_by_the_tls_block_and_never_by_the_plain_one` | yes | `PROD-01` extends it to the live name |
| 4 | The session cookie is `Secure` (`R-146a`) | `curl -sS -D - -o /dev/null -H "Cookie: am_session=$(openssl rand -hex 16)" https://<name>/bff/v1/projects \| grep -i '^set-cookie: am_session=;.*Secure'` exits 0 (an inert cookie draws `401` and a clearing `Set-Cookie` from the BFF route handler, the method of `EXPOSURE-REVIEW-01.md` E-2) | command yes | `PROD-01` |
| 5 | The certificate is renewed before it expires | `echo \| openssl s_client -connect <name>:443 -servername <name> 2>/dev/null \| openssl x509 -noout -checkend 1209600` exits 0 (valid for 14 more days) | command yes | `PROD-01` puts it in `verify-deployed.sh` |
| 6 | A deployment is not successful while `admin`/`password` is valid (`R-146i`) | `$DC run --rm --no-deps -T --entrypoint python api -m auditmanager.access.check` exits `0` (`1` means a default credential) | command yes; wiring no | `PROD-02` |
| 7 | The application connects with a role that cannot change the schema (`R-146n` item 1) | `$DC exec -T postgres psql -U <migrator> -d <db> -Atc "select rolsuper, has_schema_privilege(rolname,'public','CREATE') from pg_roles where rolname='<application role>'"` prints `f\|f`; and `select has_table_privilege('<application role>','public.audit_event','DELETE')` prints `f` | no | `PROD-04` |
| 8 | Memory and log limits on every long-running service (`R-146n` item 2) | `$DC config --no-env-resolution --format json` has `mem_limit` (or `deploy.resources.limits.memory`) and `logging.options.max-size` for each service except the one-shot ones | no | `PROD-05` |
| 9 | A migrating deploy follows a dump (`R-146n` item 3) | run `infra/deploy/deploy.sh` on a checkout with a newer revision and no receipt: exit `3` and `REFUSED [dump-receipt]`; the guard is shown to fail by deleting its marked block, as `tests/integration/composition/test_deploy_script_refusals.py` does for the others | no | `PROD-03` |
| 10 | The release checklist carries the manual scan (`R-146n` item 5) | `grep -n "manual_scan" docs/program/RELEASE_PROCESS.md` has a hit and `scripts/release/manual_scan.sh --check-tools` exits non-zero when a scanner is missing | no | `PROD-09` |
| 11 | No CI workflow is added (`R-146h`) | `ls .github/workflows` prints only `deploy-auto.yml`; `tests/contract/test_deploy_auto_workflow.py` pins that workflow | yes | none (non-expansion) |
| 12 | One worker slot (`R-146j`) | `$DC exec -T postgres psql -U <migrator> -d <db> -Atc "select count(*), sum(slots) from worker where heartbeat_at > now() - interval '90 seconds'"` prints `1\|1` | yes | none |
| 13 | No metrics, tracing or error-reporting library (`R-146k`) | `rg -il "prometheus\|opentelemetry\|sentry" src infra --glob '!*.md'` prints nothing | yes | none |
| 14 | The missing off-host copy stays visible (`A-1`, `A-4`) | `infra/deploy/readiness.sh` prints `readiness FINDING off-host-backup`; `tests/integration/composition/test_readiness_command.py` pins that readiness reports and never gates (`R-46`) | yes | none; do not silence it |
| 15 | A restore has been shown to work at the head being released | `grep -l "$(ls db/migrations/versions \| tail -1 \| sed 's/^[0-9]*_//; s/\.py$//')" docs/program/RECOVERY-DRILL-*.md` prints a file | command yes; today it prints nothing (`D-216`) | `PROD-17` |

## Consequences

### Positive

- The terminator, its renewal and its headers are in the repository, are tested, and are deployed by
  the same workflow as the application; `D-191` stops depending on a file nobody can read.
- A compromise of the API process no longer carries the right to change the schema or truncate a
  table.
- A migrating release cannot reach the database without a verified dump taken just before it.
- Every absence the owner accepted is listed with a check that shows it, so none is silent.

### Negative / cost

- The ACME client is a new image and a new moving part on the only public path; a failed renewal
  takes the public site off HTTPS without any alert (`R-146k`). The 14-day check runs only when
  someone deploys or verifies.
- Two database roles double the places a credential lives (`alpha.env`) and make every migration
  that adds a table carry a grant decision.
- A single host and manual copies mean a disk loss loses everything on it (`A-1`, `A-4`).
- Memory limits can turn a large analysis into a retried or failed attempt.
- Rollback needs a gate run, and a complete gate cannot run on this development host (`D-205`).

## Alternatives considered

1. **Keep the host nginx as the terminator and document it.** Rejected by `R-146a`: its
   configuration would stay outside the tests and the deploy.
2. **A certificate placed by hand and renewed by hand.** Rejected by `R-146a` ("ACME renewal"): the
   current certificate expires on 2026-12-30 and a manual renewal is exactly the single point of
   failure the owner asked to remove.
3. **Nightly dump with an off-host mirror.** The recommended option of the poll; the owner chose
   manual copies (`R-146b`). Not built; `A-1`.
4. **A managed PostgreSQL and managed object storage.** Not asked; would contradict `ADR-0020`'s single
   failure domain and `R-146a`'s single host.
5. **Checklist line only for the dump** instead of a guard: see `AD-03`.

## Verification

- automated check/test: the fifteen rows above; existing guards `tests/contract/test_deploy_auto_workflow.py`,
  `tests/integration/composition/test_deploy_script_refusals.py`,
  `tests/integration/composition/test_readiness_command.py` and
  `tests/integration/composition/test_proxy_tls_path.py`
- manual/operational evidence: the release rehearsal of `PRODUCTION-READINESS-PLAN-01.md` (`PROD-17`):
  a clean-clone deploy on the VPS, `verify-deployed.sh` exit `0`, the public probes of rows 2 to 5, and a
  restore drill at the released head with the time it took

## Revisit trigger

Replace this ADR when any of the following holds: the first real client upload that the owner cannot
afford to lose (`A-1`); a second host, a managed database or an off-host copy is decided; a
recovery time or recovery point is promised to anyone; a second operator joins; the VPS size is
measured and does not fit the 500-page envelope (`D-171`); a decision to add CI or scanning
(`A-3`).
