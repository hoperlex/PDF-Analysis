# ADR-0021: Production topology and operations: one VPS, TLS in `infra/`, manual copies

- Status: accepted (`AD-04` is proposed and not yet confirmed; the `AD-18` choice is open: see Decision, "Open")
- Date: 2026-10-26; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: `PRODUCTION-ADR-PACK-01`; owner rulings `R-146a`, `R-146b`, `R-146h`, `R-146j`, `R-146k`, `R-146n`, `R-146p`, `R-146s`, `R-146t`; `AD-01` confirmed by `R-146p` (server name) and `R-146aa` (ACME mechanism); `AD-02`, `AD-05`, `AD-16` by `R-146w`; `AD-03` by `R-146t`; `AD-17` by `R-146x`; `AD-18` settled by `R-146y` as to what stands until the measurement; `AD-19` settled by `R-146z`; `R-153ab`, `R-153af` (2026-11-10, Alternative 4); principles P-05, P-10, P-13, P-14
- Amends: supersedes the reading of `R-1` that no host exists yet (`R-146a`); no earlier ADR is replaced

## Context

`ADR-0002` chose a modular monolith and `ADR-0020` the alpha runtime on one PostgreSQL and one private
S3 store. Neither said what production runs on, who terminates TLS, what is copied, or what is
deliberately not provided. The owner decided these by direct poll on 2026-10-26
(`OWNER_RULINGS_2026-09-17.md` section 3.46, `R-146`). Facts read from the tree at `4d7b7c38` the same
day; a fact the tree cannot show is marked "assumption".

- **Topology.** `infra/deploy/compose.server.yml`: only the `proxy` has `ports:`, its plain listener binds
  `127.0.0.1` unless `ALPHA_BIND_ADDRESS` says otherwise (`D-49`); images are built on the host; no service
  has a memory limit, CPU limit or log rotation (`D-166`); MinIO is built from source and upstream is
  archived (`D-119`).
- **TLS.** Only an overlay that mounts a hand-placed certificate pair (`infra/deploy/proxy/`); nothing in
  the tree obtains or renews a certificate. Its block sends HSTS and `X-Forwarded-Proto: https`, which makes
  the web tier issue a `Secure` session cookie (`web/src/app/bff/session/store.ts`). The stand's live
  terminator is a different nginx outside the repository, with a certificate that expires on 2026-12-30
  (`D-191`, `EXPOSURE-REVIEW-01.md` E-2); whether HSTS and `Secure` are in effect there cannot be read from
  the tree.
- **Deployment.** `.github/workflows/deploy-auto.yml` runs on a push to `main`, connects over SSH to the one
  pinned host and runs `deploy.sh` then `verify-deployed.sh`; it has no test step. There is no rollback
  tooling (`RELEASE_PROCESS.md`: a rollback is a reviewed forward revert).
- **Data.** One PostgreSQL, no replica. `migrate`, `release-notes`, `api` and `worker` share one
  `DATABASE_URL` whose user is `POSTGRES_USER`, a superuser in the official image (assumption; the check is
  row 7). Migrations run only through the one-shot `migrate`; the head was `0033` when this ADR was
  accepted. The S3 bucket is private, with no versioning, lifecycle or encryption at rest configured.
- **Copies.** No scheduled backup. A verified dump is taken by `reset.sh` and `purge-product-data.sh` (both
  then destroy data) and by the owner's forced-command key (`copy-serve.sh dump-db`; stops the writers;
  deferred to the first real upload, `R-110`). `deploy.sh` does **not** dump; its `R-93` guards refuse a
  migrating publication while an open, unattested copy record exists (`stand-copy-unattested`) or one
  attested for another commit (`stand-copy-other-target`). The last restore drill is
  `RECOVERY-DRILL-0029-01.md` (synthetic, head `0029`); none at `0032` (`D-216`).
- **Process rules that bind.** `AGENTS.md` section 6 and `MAIN_AUTODEPLOY_POLICY.md` (a push to
  `origin/main` is a deployment and needs the owner's instruction naming the exact SHA); `R-46`:
  `readiness.sh` reports and blocks no deploy, narrowed for one check by `R-146i` and `R-146s`
  (`ADR-0023`); `R-88`, `R-93`, `R-110`: a one-off copy precedes every migrating publication whenever the
  stand holds real client data, which `R-146f` makes the production release; `R-146` repeals none of them.

## Decision

Open: `AD-04` (memory and log limits, section 4) was not polled; it is the architect's, proposed and not
yet confirmed, and the VPS size it depends on is open. `AD-18` (capacity envelope, `ADR-0024`
section 5) is settled by `R-146y` only as to what stands until the measurement; the choice after it is
open.

### 1. Topology (`R-146a`)

The production host is the single VPS pinned in `.github/workflows/deploy-auto.yml`, running
`compose.server.yml`. No standby host, no failover. The time to recover is the time to restore from the
last copy (`R-146a`); no recovery time or point is promised (`R-146b`). The restoration time is
measured once, in the release rehearsal of `PRODUCTION-READINESS-PLAN-01.md` (`PROD-17`), and recorded
as a measurement, not a commitment.

### 2. The TLS terminator and certificate renewal live in `infra/` (`R-146a`, `R-146p`)

The terminator is the repository's own `proxy` service; the host nginx outside the repository leaves
the design. HSTS and a `Secure` session cookie are commitments (`R-146a`); both follow from terminating
TLS in the stack, because the `$scheme` the proxy forwards is then `https`.

`AD-01`, confirmed by `R-146p` as to the server name: **the certificate name is a deploy variable** (a
setting of `alpha.env`, whose name `PROD-01` chooses), and the owner names it before `PROD-01` starts.
This ADR names no host and no DNS provider. **The ACME mechanism is confirmed by `R-146aa`**; the
commitments of `R-146a` and `R-146s` stand regardless. Procedure and settings:
`docs/program/DEPLOYMENT_RUNBOOK.md` section 6.

- An ACME client runs as a service of the same compose project from a digest-pinned image, using the
  HTTP-01 challenge through a webroot the `proxy` serves. It writes the pair to a named volume that
  the `proxy` mounts read-only and does not mount the Docker socket. The `proxy` re-reads the
  certificate on a timer (a `nginx -s reload` loop started from `/docker-entrypoint.d/`), so no service
  needs the right to restart another. A rehearsal against the ACME staging endpoint precedes the first
  real issuance.
- `verify-deployed.sh` fails when the served certificate has fewer than 14 days left (the architect's
  number). `readiness.sh` `tls` and `plain-http` are rewritten for the new layout.
- HSTS stays at `max-age=31536000`, without `includeSubDomains` and without `preload`.

**First-boot and restore listener binding (`R-146s`).** Three listeners; the public application
listener is conditional:

| Listener | Where | Serves | When it exists |
| --- | --- | --- | --- |
| plain application | `127.0.0.1:${ALPHA_HTTP_PORT}` | the whole application (`deploy.sh`'s `proxy-answers` guard requires `401`) | always |
| challenge | public port 80 | only `/.well-known/acme-challenge/` from the webroot and a redirect to HTTPS; **no application route** | always once ACME is configured, so issuance and renewal work while the password is still the seeded one |
| application | public port 443 | the application over TLS with HSTS | only in a deploy whose `python -m auditmanager.access.check` exits `0` and whose certificate pair exists: `deploy.sh` adds a second compose overlay that publishes it, and recreates the `proxy` without it otherwise |

On a never-published host, or after `reset.sh`, the stack comes up on loopback with port 80 answering the
challenge; the administrator changes the password through an SSH tunnel to the loopback port; the next
deploy publishes 443. Port 80 never reaches the application. `ALPHA_BIND_ADDRESS` alone stops being enough
and `PROD-01` replaces it with this logic. **On a published host a restore can bring the default
credential back** (a dump taken before the password was changed, or `reset.sh`): every restore path
(`reset.sh --restore`, `copy-serve.sh restore-db`) ends by running the same check and, on exit `1`,
recreates the `proxy` without the 443 overlay, so the site is unreachable from outside until an
administrator changes the password: the consequence `R-146s` accepts. The decision logic is one function of
`infra/deploy/lib/` used by the three scripts; the copy key's script is installed apart from the checkout
(`DEPLOYMENT_RUNBOOK.md` section 13), so the owner repeats that install after the change. Which accounts
make the check fail is settled by `R-146z` (`ADR-0023` section 3): only the published seeded pair.

### 3. Database roles (`R-146n` item 1)

`AD-02`, confirmed by `R-146w` as written at commit `83600aed`: the existing owner role
(`POSTGRES_USER`) becomes the **migrator**: it owns every object, runs `migrate` and `release-notes`,
and is the role the operator tools that need ownership connect as. A new **application** role is used
by `api` and `worker`: it can log in, is not a superuser, cannot create objects or roles, owns nothing,
holds `USAGE` on schema `public`, `SELECT`, `INSERT`, `UPDATE`, `DELETE` and sequence usage on the
tables, and no `TRUNCATE`. Tables that a trigger declares append-only or immutable
(`schema_coverage.TRIGGERS`; `am_append_only`, `am_immutable_row`) get `SELECT` and `INSERT` only, so
the database refuses `UPDATE` and `DELETE` for the application twice, by privilege and by trigger.

**Grants are an idempotent step, not a migration**: the dump tools use `--no-privileges`, so a restore
would lose privileges a revision granted while the unchanged head leaves `migrate` a no-op, and a
password cannot live in an Alembic revision. A new `infra/deploy/apply-grants.sh` (name chosen by the
lane; rationale in its header) creates the role if absent, derives every grant from the catalog (tables,
the trigger classification above, sequences, `ALTER DEFAULT PRIVILEGES` for later tables) and can be run
any number of times. `deploy.sh` runs it after `migrate` and before `api` and `worker` start;
`reset.sh --restore` and `copy-serve.sh restore-db` run it after the restore. **No Alembic revision is
added**; the migration head is not moved by this work (`0033` came from `D-225`). Proof: the
`tests/integration` directories of the contexts running as the application role, plus a test that a
database restored from a `--no-privileges` dump is readable by the application role after the step.
`DATABASE_URL` stays the application's; the migrator's URL is a second variable received only by
`migrate`, `release-notes`, the operator tools and the grants step, and the wrappers that need ownership
(`purge-product-data.sh`, the erase wrapper of `ADR-0022`) pass it explicitly. The connection to
PostgreSQL stays inside the compose network without TLS.

### 4. Memory and log limits (`R-146n` item 2, `D-166`)

`AD-04` (not polled; the architect's, to be confirmed): every long-running service gets a memory limit
and the `json-file` log driver with `max-size` and `max-file`. **This ADR fixes no number**: the VPS
size is not known (open), and a limit below the footprint of a large analysis would kill the worker
mid-run (the capacity envelope is `AD-18`, `ADR-0024` section 5). The owner measures on the VPS with
`infra/deploy/capacity-probe.sh` and `docker stats --no-stream` during a 500-page analysis; the limit
is set above the measured peak by a margin the lane states. An OOM kill of the worker is recovered by
lease expiry and retry (`ADR-0007`), at the price of a failed attempt.

### 5. Copies and the dump before every migration (`R-146b`, `R-146n` item 3, `R-146t`)

Backups are manual until 1.0: no schedule, no maintained off-host target, no recovery point or time
commitment (accepted risk **A-1**, section 10). The compensating measure the owner accepted is a manual
dump before every migration, and `R-146t` makes `deploy.sh` refuse to run `migrate` without a fresh
receipt of it.

**`R-93` continues to bind.** A one-off copy (quiesced dump, inventory, fetch to the development host,
restore test, attestation) precedes every migrating publication whenever the stand holds real client
data (`R-88`, `R-93`, `R-110`); `R-146f` makes the production release that moment. `R-146` does not
repeal `R-93`; `R-146t` adds a mechanical refusal on top of it.

`AD-03`, confirmed by `R-146t` (the limit is the one `R-146t` leaves to this ADR): **the receipt is the
copy record that `copy-serve.sh dump-db` already writes**, not a second artefact or command; it names
the dump file, SHA-256 and time (`dump.file`, `dump.sha256`, `quiesced_at`; format:
`W54-STAND-COPY-01.md` section 3.2). `deploy.sh` gains one guard, `stand-copy-fresh`, beside the `R-93`
guards: when the `real_data` marker exists and the checkout carries a migration the database does not
have (its highest revision differs from `alembic_version`, read before `migrate`), the deploy is refused
unless the record is open, has its dump, is attested for this commit (the existing guards) and its
`quiesced_at` is not older than **24 hours**. A deploy with no pending migration needs no receipt;
before the marker exists (`R-110`, test data only) nothing changes. The dump is taken through the
owner-installed copy key (`DEPLOYMENT_RUNBOOK.md` section 13); installing it, which `R-110` deferred, is
a precondition of the production release (`PROD-03`). The dump covers PostgreSQL only: a migration does
not touch the S3 bucket (assumption: every revision under `db/migrations/versions/` is SQL), so pairing
the two is not needed for a rollback. The copy directory keeps only the latest copy (`dump-db` removes older stamps) and
refuses to start without room (`copy-dir-has-room`).

`AD-17`, confirmed by `R-146x`: **the full `R-93` attestation stays after 1.0** (dump, fetch to the
development host, trial restore, attestation) for every migrating publication, and the receipt check
of `R-146t` sits on top of it. This is also why the latest pre-migration copy keeps leaving the host
for the restore test (section 9).

### 6. Deploy, verification and rollback

The deployment path is unchanged: owner instruction naming the SHA, fast-forward to `main`, the
workflow, `deploy.sh`, `verify-deployed.sh` (`AGENTS.md` section 6). **Rollback is a forward fix.** An
older image is not guaranteed to run against a newer schema, and the migrations' downgrades refuse
where data would be lost. A failed migrating release is recovered by a reviewed revert through the same
path and, if the schema must go back, by the owner's way back of the copy key: `copy-serve.sh
restore-db <STAMP> <dump-sha256>` consumes exactly the PostgreSQL-only `db.dump` the receipt names; the
runbook gives the order (restore, a reviewed revert re-attested for its SHA, then `resume`; a revert
alone would fail `migrations-at-head`). `reset.sh --restore <dump directory>` is **not** the restore of
this dump: it accepts only its own directory format (`database.dump`, `objects.attrs`, `objects/`,
written by `reset.sh` and `purge-product-data.sh`). After either restore the step of section 3
re-applies the grants and the check of section 2 decides whether the application listener may stay
published. A restore also raises every `token_epoch` in `reset.sh` (`R-52`); `copy-serve.sh restore-db`
does not today, so `PROD-02` adds it. Tested by an integration test that restores a `--no-privileges`
dump into a database with both roles and asserts the application role can read and cannot write where
the classification says, and by the release rehearsal (`PROD-17`), which runs a real `restore-db` on a
copy (an owner act) and records the time it took.

### 7. The manual release checklist and the manual scan (`R-146h`, `R-146n` item 5)

There is no CI workflow and no automated dependency or image scan, and none is added. The compensation
the owner accepted is one line of the release checklist. The production release checklist, worked
through as `docs/program/RELEASE_PROCESS.md` "Production release checklist" (which holds the pruning
and manual-scan procedure):

1. the candidate SHA, the owner's direct instruction naming it, a clean tree (`MAIN_AUTODEPLOY_POLICY.md`);
2. the complete gate on that exact tree with the literal `GATE OK`, on a host that can run it (`D-205`);
3. **the manual dependency and image scan**: run `AD-05`'s helper, attach its output and date to the
   release record, and decide each finding;
4. if the database head changes, the pre-migration copy and its receipt, in the `R-93` order of
   section 5 (`dump-db`, `inventory-s3`, fetch, restore test, `attest`, deploy, `resume`);
5. the heavy-step stop rule: `capacity-probe.sh --path root=/ --need root=<bytes>` before the build,
   the dump's size counted in the need, and the pruning below;
6. after the push: the workflow finished successfully and `verify-deployed.sh` exits `0` on the host,
   which includes the default-credential check (`ADR-0023`) and the certificate-expiry check;
7. the public probes (rows 2 to 4 of the table below);
8. the tag and the `RELEASES.md` row only after items 6 and 7.

**Pruning (manual)** of `infra/deploy/dumps/` (procedure: `RELEASE_PROCESS.md` "Pruning"): nothing prunes it;
at each release the operator keeps the last two directories and any directory a release record names,
deletes the rest by hand, and records the free space before and after. A dump that holds client data is
deleted by the same hand as soon as the release it guarded is accepted, and an erase (`ADR-0022`) is
followed by the same pruning.

`AD-05`, confirmed by `R-146w` as written at commit `83600aed`: the helper is
`scripts/release/manual_scan.sh` (detail: `RELEASE_PROCESS.md` "The manual scan"). It prints an inventory
(resolved Python packages of `uv.lock`, npm packages of `web/package-lock.json`, image digests in
`compose.server.yml`) and runs whichever of `pip-audit`, `npm audit` and an image scanner the operator has
installed; it never prints a pass when a scanner is missing or the vulnerability database could not be
reached, so it is run from a machine with network access to a vulnerability feed. It does not close
`D-122`; it makes the absence of a scan visible at every release.

### 8. What is not built (`R-146j`, `R-146k`)

One worker slot and no time promise: the queue grows serially (`ADR-0024`). No JSON logs, redaction
layer, metrics, tracing or alerts; an incident is read from container logs with `docker compose logs`.
The only observability additions are the access audit events of `ADR-0023` and the erase journal of
`ADR-0022`. **`ADR-0015` is not contradicted**: it separates diagnostic logs, durable audit and metrics
and asks for allow-list redaction at channel boundaries; `R-146k` decides that 1.0 does not build the
parts that do not exist (the redaction layer, metrics), so `ADR-0015` stays the design rule for what is
built, the durable audit it describes is what `ADR-0022` and `ADR-0023` add, and its missing channels
are a known gap of 1.0.

### 9. What the host must provide, and what it does not

The host must provide: `bash`, `docker` with the compose v2 plugin, `curl`, `sed` and `git`
(`DEPLOYMENT_RUNBOOK.md` section 1); inbound 80 and 443 and SSH for the deploy user; a DNS name for the
certificate; outbound HTTPS to the ACME service and to the model provider; disk for the database, the
bucket, the images and the dumps, all on one filesystem (size open); a synchronised clock (assumption:
ACME validation and the token lifetime of `ADR-0023` depend on it).

The host does not provide, and this programme does not build: high availability or failover; a
maintained or scheduled off-host copy of the database or the bucket; metrics, alerts or log shipping; a
service-level objective; a second operator; a firewall policy beyond the published ports (a
Docker-published port bypasses `ufw`: `D-49`). Three copies do leave the host, none a backup of the
live service: the offline copy of the key ring (`R-146n` item 7), the latest pre-migration copy that
`pull-copy.sh` fetches to the development host for the `R-93` restore test (only while `R-146x` keeps
that test), and the corpus bundle kept on the development host (`R-88`). The bucket is not among them.

Object store. The MinIO image is built from source at upstream's final release and upstream is archived
(`D-119`); the live volume was never inventoried (`D-123`); under `A-3` no scan covers that image.
Whether to keep the source build or qualify another S3 implementation is the owner's (`PROD-19`).

### 10. Accepted risks

- **A-1 (`R-146b`).** Client data can be lost back to the last manual copy. A disk loss on the one host
  loses the copies as well, because they sit on the same disk; the exception is the latest
  pre-migration copy fetched to the development host, which exists because `R-146x` keeps the restore
  test and is not a scheduled backup. Reopen on the first real client upload that the owner cannot
  afford to lose (`R-146b`).
- **A-3 (`R-146h`).** No machine checks a push and no scan runs unless a person runs it before a
  release; a vulnerable dependency or image can reach the host. `D-122` stays open. Reopen trigger
  (`AD-16`, confirmed by `R-146w`): before the first release that follows a published advisory for a
  component in `uv.lock`, `web/package-lock.json` or the pinned images, or before any release to users
  outside the owner's organisation.
- **A-4 (architect's consequence of `R-146a` and `R-146b`).** One host, no failover, no maintained copy
  of the database or the bucket off that host: a host loss, a provider loss of the VPS, an operator
  error or a ransomware event ends the service and may end the data. Reopen trigger (`AD-16`,
  confirmed by `R-146w`): the same as A-1, and any decision to promise a recovery time or point to a
  client.

## Commitments and their mechanical checks

Run on the VPS from the checkout `/srv/auditmanager`; `<name>` is the public DNS name and `$DC` is
`docker compose --env-file infra/deploy/env/alpha.env -f infra/deploy/compose.server.yml`.
`docker compose config` prints secrets in clear (`provider.env.example` says so): the rows pipe it
into a program that prints names only, and its raw output is never shown or pasted. "Exists" means the
check can be run today; the lane named delivers the rest (`PRODUCTION-READINESS-PLAN-01.md`).

| # | Commitment | Mechanical check, which fails when the commitment is false | Exists | Delivered by |
| --- | --- | --- | --- | --- |
| 1 | Only the proxy publishes a port | `$DC config --no-env-resolution --format json` lists `ports` on `proxy` alone (prints `['proxy']`); in the tree `tests/integration/composition/test_acme_overlay.py` | command yes | `PROD-01` keeps it true |
| 2 | TLS answers on the public name with a trusted chain | `curl -sS -o /dev/null -w '%{http_code} %{ssl_verify_result}\n' https://<name>/login` prints `200 0` | command yes | `PROD-01` |
| 3 | HSTS on every TLS answer (`R-146a`) | `curl -sSI https://<name>/login \| grep -i '^strict-transport-security: max-age=31536000'` exits 0; in the tree `tests/integration/composition/test_proxy_tls_path.py::test_hsts_is_sent_by_the_tls_block_and_never_by_the_plain_one` | yes | `PROD-01` extends it to the live name |
| 4 | The session cookie is `Secure` (`R-146a`) | `curl -sS -D - -o /dev/null -H "Cookie: am_session=$(openssl rand -hex 16)" https://<name>/bff/v1/projects \| grep -i '^set-cookie: am_session=;.*Secure'` exits 0 (an inert cookie draws `401` and a clearing `Set-Cookie` from the BFF route handler, the method of `EXPOSURE-REVIEW-01.md` E-2) | command yes | `PROD-01` |
| 5 | The certificate is renewed before it expires | `echo \| openssl s_client -connect <name>:443 -servername <name> 2>/dev/null \| openssl x509 -noout -checkend 1209600` exits 0 (valid for 14 more days) | command yes | `PROD-01` puts it in `verify-deployed.sh` |
| 6 | A deployment is not successful while `admin`/`password` is valid (`R-146i`, `R-146s`, `R-146z`) | `$DC run --rm --no-deps -T --entrypoint python api -m auditmanager.access.check` exits `0` (`1` means a must-change account; stricter than the gate, which `R-146z` narrows to the published pair); while it exits `1`, `$DC port proxy 8443` exits non-zero (443 is not published) and `curl -sS --connect-timeout 5 -o /dev/null https://<name>/login` cannot connect; after the password change and a deploy, `$DC port proxy 8443` prints a mapping | the first command yes; the rest no | `PROD-01`, `PROD-02` |
| 7 | The application connects with a role that cannot change the schema, before and after a restore (`R-146n` item 1) | `$DC exec -T postgres psql -U <migrator> -d <db> -Atc "select rolsuper, has_schema_privilege(rolname,'public','CREATE'), has_table_privilege(rolname,'public.audit_event','DELETE'), has_table_privilege(rolname,'public.audit_event','INSERT') from pg_roles where rolname='<application role>'"` prints `f\|f\|f\|t`; the same query is repeated after a `restore-db` rehearsal | no | `PROD-04` |
| 8 | Memory and log limits on every long-running service (`R-146n` item 2) | `$DC config --no-env-resolution --format json` shows a memory limit and a `max-size` log option on every service except `migrate`, `release-notes` and `s3-init` (the list of services lacking one prints `[]`); in the tree `tests/integration/composition/test_compose_log_and_memory_limits.py` | no | `PROD-05` |
| 9 | A migrating deploy follows a fresh copy receipt (`R-146n` item 3, `R-146t`) | `infra/deploy/deploy.sh` on a checkout with a newer revision, the `real_data` marker present and a record older than 24 hours (or none) ends with `REFUSED [stand-copy-fresh]` and exit `3` before any build; the guard is shown to fail by deleting its marked block, as `tests/integration/composition/test_deploy_script_refusals.py` does for the others | no | `PROD-03` |
| 10 | The release checklist carries the manual scan (`R-146n` item 5) | `grep -n "manual_scan" docs/program/RELEASE_PROCESS.md` has a hit and `scripts/release/manual_scan.sh --check-tools` exits non-zero when a scanner is missing | no | `PROD-09` |
| 11 | No CI workflow is added (`R-146h`) | `ls .github/workflows` prints only `deploy-auto.yml`; `tests/contract/test_deploy_auto_workflow.py` pins that workflow | yes | none (non-expansion) |
| 12 | One worker slot (`R-146j`) | `$DC exec -T postgres psql -U <migrator> -d <db> -Atc "select count(*), sum(slots) from worker where heartbeat_at > now() - interval '90 seconds'"` prints `1\|1` | yes | none |
| 13 | No metrics, tracing or error-reporting library is used (`R-146k`); **documentation check only**: a keyword search detects obvious libraries and cannot prove the absence of one under another name | `rg -il "prometheus\|opentelemetry\|sentry" src infra --glob '!*.md'` prints nothing, and `grep -c "@opentelemetry" web/package-lock.json` prints `2` (the optional peer of the web framework, nothing else) | yes | none |
| 14 | The missing off-host copy stays visible (`A-1`, `A-4`) | `infra/deploy/readiness.sh` prints `readiness FINDING off-host-backup`; `tests/integration/composition/test_readiness_command.py` pins that readiness reports and never gates (`R-46`) | yes | none; do not silence it |
| 15 | A restore drill was run at the head being released; **documentation check only**: it proves a record exists, the drill is the owner's act | `grep -l "^head: $(ls db/migrations/versions \| tail -1 \| sed 's/^[0-9]*_//; s/\.py$//')$" docs/program/RECOVERY-DRILL-*.md \| xargs grep -l "^result: pass$"` prints a file (the two lines are the record format `PROD-17` fixes; the 0029 record does not have them) | command yes; today it prints nothing (`D-216`) | `PROD-17` |

## Consequences

- Positive: the terminator, its renewal and its headers are in the repository, tested and deployed by the
  same workflow as the application; `D-191` stops depending on a file nobody can read.
- Positive: a compromise of the API process no longer carries the right to change the schema or truncate a
  table; with real client data on the stand a migrating release cannot reach the database without a
  quiesced, attested copy taken within the last day.
- Positive: every absence the owner accepted is listed with a check that shows it, so none is silent.
- Cost: the ACME client is a new image and a new moving part on the only public path; a failed renewal takes
  the public site off HTTPS without any alert (`R-146k`), and the 14-day check runs only when someone
  deploys or verifies.
- Cost: two database roles double the places a credential lives (`alpha.env`) and make every migration that
  adds a table carry a grant decision; memory limits can turn a large analysis into a retried or failed
  attempt.
- Cost: a single host and manual copies mean a disk loss loses everything on it (`A-1`, `A-4`); rollback
  needs a gate run, and a complete gate cannot run on this development host (`D-205`).

## Alternatives considered

1. **Keep the host nginx as the terminator and document it.** Rejected by `R-146a`: its configuration
   would stay outside the tests and the deploy.
2. **A certificate placed by hand and renewed by hand.** Rejected by `R-146a`; the live certificate
   expires on 2026-12-30 (`D-191`), which is why the plan gives `PROD-01` a deadline and an interim
   owner item (`PROD-21`).
3. **Nightly dump with an off-host mirror.** The recommended option of the poll; the owner chose manual
   copies (`R-146b`). Not built; `A-1`.
4. **A managed PostgreSQL and managed object storage.** Not asked on 2026-10-26. Asked on 2026-11-10
   (`OWNER_RULINGS_2026-09-17.md` section 3.55): «запланировать полный перенос на Яндекс. Пока выбрать
   вариант ночное окно, пометить как временное решение на локальном хранилище» (`R-153ab`), and, asked
   whether to move the database to a Yandex cluster now, «Пока не трогаем» (`R-153af`). Decided **in
   principle and not started**: nothing in this ADR's decisions changes today (one VPS, manual copies,
   accepted risks `A-1` to `A-5` and `R-146a` stand) and the alternative stays rejected for the present
   topology. `docs/program/YC-MOVE-PLAN.md` holds the provider checks (pgvector 0.8 or later for
   `hnsw.iterative_scan`; the exact `0.8.6` pin of migration `0013`), the order of steps and what a move
   touches. The first consumer of the move is the encoder: `ADR-0029` temporary decision 2 (the offline
   encoder in a night window on the 4 GB host) ends when the database, the storage and a separate encoder
   machine are in place.
5. **A new `dump-db.sh` beside the copy key's verb of the same name**, or a receipt that is a second
   file: rejected, the copy record is the receipt (section 5).

## Verification

- Automated: the commitment rows above; `tests/contract/test_deploy_auto_workflow.py`,
  `tests/integration/composition/test_deploy_script_refusals.py`,
  `tests/integration/composition/test_readiness_command.py` and
  `tests/integration/composition/test_proxy_tls_path.py`.
- Operational: the release rehearsal of `PRODUCTION-READINESS-PLAN-01.md` (`PROD-17`): a clean-clone
  deploy on the VPS, `verify-deployed.sh` exit `0`, the public probes of rows 2 to 5, and a restore
  drill at the released head with the time it took.

## Revisit trigger

Replace this ADR when any of the following holds: the first real client upload that the owner cannot
afford to lose (`A-1`); a second host, a managed database or an off-host copy is decided; a recovery
time or point is promised to anyone; a second operator joins; the VPS size is measured and does not
fit the 500-page envelope (`D-171`); a decision to add CI or scanning (`A-3`). The trigger "a managed
database is decided" is **armed, not met** (`R-153ab` decides it in principle): this ADR is replaced on
the day the owner orders the move to start (step 0 of `docs/program/YC-MOVE-PLAN.md`), by an ADR that
records the new topology, where the data may be held and the new failure domains.

## History

- 2026-10-26 — accepted for production by the repository owner (`R-146a`, `R-146b`, `R-146h`,
  `R-146j`, `R-146k`, `R-146n`, `R-146p`, `R-146s`, `R-146t`); `AD-01`, `AD-02`, `AD-03`, `AD-05`,
  `AD-16`, `AD-17` confirmed and `AD-18`, `AD-19` settled by later rulings (`R-146p`, `R-146aa`,
  `R-146t`, `R-146w`, `R-146x`, `R-146y`, `R-146z`), folded into the decisions; `AD-04` not polled.
- 2026-11-10 — addendum (`YC-MOVE-PLAN`, `R-153ab`, `R-153af`): a move to Yandex Cloud is planned, not
  started; folded into Alternative 4 and the Revisit trigger; no decision changed.
- 2026-11-18 — compressed and unified (ADR-OPTIMISE-01); no decision changed.
