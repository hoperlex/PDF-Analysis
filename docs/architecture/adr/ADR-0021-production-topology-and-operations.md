# ADR-0021: Production topology and operations: one VPS, TLS in `infra/`, manual copies

- Status: accepted for production by the repository owner (`R-146a`, `R-146b`, `R-146h`, `R-146j`, `R-146k`, `R-146n`, `R-146p`, `R-146s`, `R-146t`); `AD-01` is confirmed by `R-146p` as to the server name and by `R-146aa` as to the ACME mechanism, `AD-03` by `R-146t`, `AD-02`, `AD-05` and `AD-16` by `R-146w` and `AD-17` by `R-146x`; `AD-04` (limits from a VPS measurement) was not polled and stays the architect's, proposed and not yet confirmed, and the ACME mechanism of `AD-01` is confirmed by `R-146aa`; `AD-18` is settled by `R-146y` as to what stands until the measurement and its later choice is open; `AD-19` is settled by `R-146z`
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
  documented behaviour; the check is the query of row 7 below). Pool 5 plus 5 overflow
  (`src/auditmanager/shared/db/config.py`). Migrations run only through the one-shot `migrate`
  service; the head is `0033_ar_v3_cite_stage_id` (it was `0032_ar_v3_run_group` when this ADR was written). The S3 bucket is private; `bucket-init.sh` and the
  adapter configure no versioning, lifecycle or encryption at rest (a search found none).
- **Copies.** No scheduled backup exists. A verified dump is taken by `reset.sh` and
  `purge-product-data.sh`, both of which then destroy data, and by the owner's forced-command key
  (`copy-serve.sh dump-db`), which stops the writers and was deferred to the first real upload
  (`R-110`). That key's record (`record.json`) already carries the dump's file name, SHA-256, the
  time the writers were quiesced, a fingerprint and the later attestation (`W54-STAND-COPY-01.md`
  section 3.2). `deploy.sh` does **not** dump: its guards of `R-93` refuse a migrating publication
  while an *open, unattested* copy record exists (`stand-copy-unattested`) or one attested for another
  commit (`stand-copy-other-target`), and say nothing when no record exists. The two dump formats differ:
  the copy key writes a PostgreSQL-only `db.dump` that `copy-serve.sh restore-db` consumes, while
  `reset.sh` and `purge-product-data.sh` write a directory (`database.dump`, `objects.attrs`, `objects/`)
  that only `reset.sh --restore` accepts (its `restore-complete` guard). The last recorded restore drill is `RECOVERY-DRILL-0029-01.md`
  (synthetic, head `0029`); none exists at `0032` (`D-216`).
- **Process rules that bind this ADR.** `AGENTS.md` section 6 and `MAIN_AUTODEPLOY_POLICY.md`: a
  push to `origin/main` is a deployment and needs the owner's separate instruction naming the
  exact SHA. `R-46`: `readiness.sh` reports and registers, and blocks no deploy; `R-146i` and
  `R-146s` narrow that for one check (see `ADR-0023`). `R-88`, `R-93` and `R-110`: a one-off copy
  precedes every migrating publication whenever the stand holds real client data; `R-146f` makes
  the production release that moment, and nothing in `R-146` repeals them (section 5).

## Decision

### 1. Topology (`R-146a`)

The production host is the single VPS pinned in `.github/workflows/deploy-auto.yml`, running
`compose.server.yml`. There is no standby host and no failover. The time to recover is the time to
restore from the last copy (`R-146a`); no numerical recovery time or recovery point is promised
(`R-146b`). The restoration time is measured once, in the release rehearsal of
`PRODUCTION-READINESS-PLAN-01.md` (`PROD-17`), and recorded as a measurement, not as a commitment.

### 2. The TLS terminator and certificate renewal live in `infra/` (`R-146a`, `R-146p`)

The terminator is the repository's own `proxy` service. The host nginx outside the repository stops
being part of the design. `R-146a` makes HSTS and a `Secure` session cookie commitments; both follow
from terminating TLS in the stack, because the `$scheme` the proxy forwards is then `https`.

`AD-01`, confirmed by `R-146p` as to the server name: **the certificate name is a deploy variable** (a
setting of `alpha.env`, whose name `PROD-01` chooses) and the owner names it before `PROD-01` starts.
This ADR names no host and no DNS provider, and decides nothing about one. The mechanism below is what
`PROD-01` builds around that variable. `R-146p` confirms the name rule; **the ACME mechanism below is confirmed by `R-146aa`** (the commitments that `R-146a` and `R-146s` make, TLS in the stack, HSTS, a
`Secure` cookie, the conditional public listener, stand regardless):

- An ACME client runs as a service of the same compose project, from a digest-pinned image built
  or pulled like every other image, using the HTTP-01 challenge through a webroot the `proxy`
  serves. It writes the pair to a named volume that the `proxy` mounts read-only. It does not mount
  the Docker socket. The `proxy` re-reads the certificate on a timer (a `nginx -s reload` loop
  started by an executable in `/docker-entrypoint.d/`, the mechanism `enable-tls.sh` already
  uses), so no service needs the right to restart another. A rehearsal against the ACME staging
  endpoint comes before the first real issuance.
- `verify-deployed.sh` fails when the served certificate has fewer than 14 days left (the 14 is the
  architect's number). `readiness.sh` `tls` (which today only tests that a pair exists on disk) and
  `plain-http` are rewritten for the new layout.
- HSTS stays at `max-age=31536000` without `includeSubDomains` and without `preload`, exactly as
  `tls-server.conf` sends it today.

**First-boot and restore listener binding (`R-146s`).** Three listeners, and the public application
listener is conditional:

| Listener | Where | Serves | When it exists |
| --- | --- | --- | --- |
| plain application listener | `127.0.0.1:${ALPHA_HTTP_PORT}` | the whole application, as today (`deploy.sh`'s `proxy-answers` guard requires `401` on it) | always |
| challenge listener | public port 80 | only `/.well-known/acme-challenge/` from the webroot, and a redirect to HTTPS for every other path; **no application route** | always once ACME is configured, so that issuance and renewal work while the password is still the seeded one |
| application listener | public port 443 | the application over TLS with HSTS | only in a deploy whose `python -m auditmanager.access.check` exits `0` and whose certificate pair exists: `deploy.sh` adds a second compose overlay that publishes it, and recreates the `proxy` without that overlay otherwise |

So on a host that has never been published, or after `reset.sh`, the stack comes up on loopback with
port 80 answering the challenge; the administrator reaches the loopback port through an SSH tunnel and
changes the password; the next deploy publishes 443. Port 80 never reaches the application, and a
redirect to an unpublished 443 is a refused connection, which is the intended effect. The single
variable `ALPHA_BIND_ADDRESS` stops being enough and `PROD-01` replaces it with this logic. **On an
existing published host a restore can bring the default credential back** (a dump taken before the
password was changed, or `reset.sh`): every restore path (`reset.sh --restore` and `copy-serve.sh restore-db`)
ends by running the same check and, on exit `1`, recreates the `proxy` without the 443 overlay, so the
site is unreachable from outside until an administrator changes the password: the consequence `R-146s`
accepts. The decision logic lives in one function of `infra/deploy/lib/` used by the three scripts; the
copy key's script is installed apart from the checkout (`DEPLOYMENT_RUNBOOK.md` section 13), so the owner
repeats that install after the change. Which accounts make the check fail is settled by `R-146z` (`ADR-0023` section 3): only the published seeded pair.

### 3. Database roles (`R-146n` item 1)

`AD-02`, confirmed by `R-146w` as written at commit `83600aed`: the existing owner role (`POSTGRES_USER`) becomes the **migrator**: it
owns every object, runs `migrate` and `release-notes`, and is the role the operator tools that need
ownership connect as. A new **application** role is used by `api` and `worker`: it can log in, is not a
superuser, cannot create objects or roles, owns nothing, holds `USAGE` on schema `public`, `SELECT`,
`INSERT`, `UPDATE`, `DELETE` and sequence usage on the tables, and holds no `TRUNCATE`. Tables that
a trigger declares append-only or immutable (`schema_coverage.TRIGGERS`, trigger functions
`am_append_only` and `am_immutable_row`) get `SELECT` and `INSERT` only, so the database refuses
`UPDATE` and `DELETE` for the application twice, by privilege and by trigger.

**Grants are an idempotent step, not a migration.** The dump tools run `pg_dump --no-owner --no-privileges` (`reset.sh`, `purge-product-data.sh`, `copy-serve.sh`) and restore with `--no-owner`;
`copy-serve.sh restore-db` first runs `DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public`. Privileges
granted by a revision would therefore be lost by every restore, and the `migrate` that follows applies
nothing because the head is unchanged: the application would answer "permission denied". A new
`infra/deploy/apply-grants.sh` (name chosen by the lane) creates the role if it is absent (a password
cannot live in an Alembic revision), then derives every grant from the catalog (tables, the trigger
classification above, sequences, `ALTER DEFAULT PRIVILEGES` for later tables) and can be run any number of
times. `deploy.sh` runs it after `migrate` and before `api` and `worker` start; `reset.sh --restore` and
`copy-serve.sh restore-db` run it after the restore. **No Alembic revision is added**, so the migration
head `0033_ar_v3_cite_stage_id` is not moved by this ADR's work (migration `0033` came from `D-225`, not from here) and none of the files that pin the head changes for it. The proof that the
grants are enough is the `tests/integration` directories of the contexts running as the application role,
plus a test that a database restored from a `--no-privileges` dump is readable by the application role after
the step. Connection: `DATABASE_URL` stays the application's; the migrator's URL is a second variable that
only `migrate`, `release-notes`, the operator tools and the grants step receive. The wrappers that run
Python in the `api` image with the api's `DATABASE_URL` (`purge-product-data.sh` runs `product_purge` that
way, and `product_purge.py`'s `owner-may-write` guard would refuse a restricted role) pass the migrator URL
explicitly; so will the erase wrapper of `ADR-0022`. The connection to PostgreSQL stays inside the compose
network without TLS, as today.

### 4. Memory and log limits (`R-146n` item 2, `D-166`)

`AD-04` (not polled; the architect's, to be confirmed): every long-running service gets a memory limit and the `json-file` log
driver with `max-size` and `max-file`. **This ADR fixes no number**: the VPS size is not known
(open), and a limit set below the footprint of a large analysis would kill the worker mid-run (the
capacity envelope itself is `AD-18`, `ADR-0024` section 5). The owner measures on the VPS with
`infra/deploy/capacity-probe.sh` (free disk and RAM) and `docker stats --no-stream` during a
500-page analysis; the limit is set above the measured peak by a margin the lane states. An OOM kill
of the worker is recovered by the existing lease expiry and retry (`ADR-0007`), at the price of a
failed attempt.

### 5. Copies and the dump before every migration (`R-146b`, `R-146n` item 3, `R-146t`)

Backups are manual until 1.0. There is no schedule, no maintained off-host target, and no recovery
point or recovery time commitment. This is accepted risk **A-1** (below). The compensating measure the
owner accepted is a manual dump before every migration, and `R-146t` makes `deploy.sh` refuse to run
`migrate` without a fresh receipt of it.

**`R-93` continues to bind.** A one-off copy (a quiesced dump, an inventory, a fetch to the development
host, a restore test, an attestation) precedes every migrating publication whenever the stand holds real
client data (`R-88`, `R-93`, `R-110`). `R-146f` makes the production release that moment; `R-146` does
not repeal `R-93`. `R-146t` adds a mechanical refusal on top of it; it does not replace it.

`AD-03`, confirmed by `R-146t` (the limit is the one `R-146t` leaves to this ADR): **the receipt is the
copy record that `copy-serve.sh dump-db` already writes**, not a second artefact and not a second command
with the same name. It names the dump file, its SHA-256 and the time (`dump.file`, `dump.sha256`,
`quiesced_at`). `deploy.sh` gains one guard, `stand-copy-fresh`, beside the `R-93` guards: when the
`real_data` marker exists and the checkout carries a migration the database does not have (the checkout's
highest revision differs from `alembic_version`, read before `migrate`), the deploy is refused unless the
record is open, has its dump, is attested for this commit (the existing guards) and its `quiesced_at` is not
older than **24 hours**. A deploy with no pending migration needs no receipt. Before the marker exists
(`R-110`, test data only) nothing changes. The manual dump is taken through the owner-installed copy key
(`DEPLOYMENT_RUNBOOK.md` section 13); installing that key, which `R-110` deferred, is a precondition of the
production release (`PROD-03`). The dump covers PostgreSQL only; the S3 bucket is not touched by a migration
(assumption: every revision under `db/migrations/versions/` is SQL), so the pairing of the two is not needed
for a rollback. The copy directory keeps only the latest copy (`dump-db` removes older stamps) and refuses to
start without room (`copy-dir-has-room`).

`AD-17`, confirmed by `R-146x`: **the full `R-93` attestation stays after 1.0** (dump, fetch to the development host, trial restore,
attestation) for every migrating publication, and the receipt check of `R-146t` sits on top of it. This is also why the latest
pre-migration copy keeps leaving the host for the restore test (section 9).

### 6. Deploy, verification and rollback

The deployment path is unchanged: owner instruction naming the SHA, fast-forward to `main`, the
workflow, `deploy.sh`, `verify-deployed.sh` (`AGENTS.md` section 6). **Rollback is a forward fix.**
An older image is not guaranteed to run against a newer schema, and the migrations' downgrades refuse where data would be lost
(`0006_app_user` and `0032_ar_v3_run_group` say so). A failed migrating release is recovered by a reviewed revert deployed
through the same path and, if the schema must go back, by the owner's way back of the copy key:
`copy-serve.sh restore-db <STAMP> <dump-sha256>` consumes exactly the `db.dump` that the receipt names, and the runbook
gives the order (restore, then a reviewed revert re-attested for its SHA, then `resume`; a revert alone would fail
`migrations-at-head`). `reset.sh --restore <dump directory>` is **not** the restore of this dump: it accepts only its
own directory format and refuses anything else. After either restore the step of section 3 re-applies the grants and the
check of section 2 decides whether the application listener may stay published; a restore also raises every `token_epoch`
in `reset.sh` (`R-52`), which `copy-serve.sh restore-db` does not today, so `PROD-02` adds it there. How this is tested:
an integration test restores a `--no-privileges` dump into a database with both roles and asserts the application role can
read and cannot write where the classification says; and the release rehearsal (`PROD-17`) runs a real `restore-db` on
a copy, which is an owner act and is listed there, with the time it took.

### 7. The manual release checklist and the manual scan (`R-146h`, `R-146n` item 5)

There is no CI workflow and no automated dependency or image scan, and none is added. The
compensation the owner accepted is one line of the release checklist. The checklist for the
production release, kept here until a later lane writes it into `RELEASE_PROCESS.md`:

1. the candidate SHA, the owner's direct instruction naming it, a clean tree (`MAIN_AUTODEPLOY_POLICY.md`);
2. the complete gate on that exact tree with the literal `GATE OK`, on a host that can run it (`D-205`);
3. **the manual dependency and image scan**: run `AD-05`'s helper, attach its output and date to the
   release record, and decide each finding;
4. if the database head changes, the pre-migration copy and its receipt, the `R-93` order of section 5 (`dump-db`,
   `inventory-s3`, fetch, restore test, `attest`, deploy, `resume`);
5. the heavy-step stop rule: `capacity-probe.sh --path root=/ --need root=<bytes>` before the build, with the dump's
   size counted in the need, and the pruning below;
6. after the push: the workflow finished successfully and `verify-deployed.sh` exits `0` on the host,
   which includes the default-credential check (`ADR-0023`) and the certificate-expiry check;
7. the public probes (the table below, rows 2 to 4);
8. the tag and the `RELEASES.md` row only after items 6 and 7.

**Pruning (manual).** The copy directory keeps only the latest copy by itself (`dump-db` removes older stamps).
`infra/deploy/dumps/` (git-ignored, written by `reset.sh` and `purge-product-data.sh`) grows with every use and
nothing prunes it: at each release the operator keeps the last two directories and any directory a release record
names, deletes the rest by hand, and records the free space of the filesystem before and after
(`capacity-probe.sh --path dumps=<ALPHA_DUMP_ROOT>`). A dump that holds client data is deleted by the same hand
as soon as the release it guarded is accepted, and an erase (`ADR-0022`) is followed by the same pruning.

`AD-05`, confirmed by `R-146w` as written at commit `83600aed`: the helper is `scripts/release/manual_scan.sh`. It prints an inventory (the
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
`ADR-0023` and the erase journal of `ADR-0022`. **`ADR-0015` is not contradicted by this.** It separates
diagnostic logs, durable audit and metrics and asks for allow-list redaction at channel boundaries; `R-146k`
decides that 1.0 does not build the parts that do not exist (the redaction layer, metrics), so `ADR-0015`
stays the design rule for what is built and the durable audit it describes is what `ADR-0022` and `ADR-0023`
add; its missing channels are a known gap of 1.0, not a decision against the ADR.

### 9. What the host must provide, and what it does not

The host must provide: `bash`, `docker` with the compose v2 plugin, `curl`, `sed` and `git`
(`DEPLOYMENT_RUNBOOK.md` section 1); inbound 80 and 443 and SSH for the deploy user; a DNS name
for the certificate; outbound HTTPS to the ACME service and to the model provider; disk for the
database, the bucket, the images and the dumps, all on the same filesystem (the size is open); a
synchronised clock (assumption: ACME validation and the one-hour token lifetime depend on it).

The host does not provide, and this programme does not build: high availability or failover; a
maintained or scheduled off-host copy of the database or the bucket; metrics, alerts or log shipping; a
service-level objective; a second operator; a firewall policy beyond the published ports (a
Docker-published port bypasses `ufw`: `compose.server.yml`, `D-49`). Three copies do leave the host, and
none is a backup of the live service: the offline copy of the key ring (`R-146n` item 7), the latest
pre-migration copy that `pull-copy.sh` fetches to the development host for the `R-93` restore test (only while
`R-146x` keeps that test), and the corpus bundle kept on the development host (`R-88`). The bucket is not
among them.

Object store. The MinIO image is built from source at upstream's final release and upstream is archived
(`D-119`); the live volume was never inventoried (`D-123`). Under `A-3` no scan covers that image. The
decision whether to keep the source build or qualify another S3 implementation is the owner's and is item
`PROD-19` of the plan.

### 10. Accepted risks

- **A-1 (`R-146b`).** Client data can be lost back to the last manual copy. A disk loss on the one host
  loses the copies as well, because they sit on the same disk; the exception is the latest pre-migration copy
  that `pull-copy.sh` fetches to the development host, which exists because `R-146x` keeps the restore test
  and is not a scheduled backup. Reopen on the first real client upload that the owner cannot afford to lose
  (`R-146b`).
- **A-3 (`R-146h`).** No machine checks a push and no scan runs unless a person runs it before a release. A
  vulnerable dependency or image can reach the host. `D-122` stays open. Reopen trigger
  (`AD-16`, confirmed by `R-146w`): before the first release that follows a published advisory for a
  component in `uv.lock`, `web/package-lock.json` or the pinned images, or before any release to users
  outside the owner's organisation.
- **A-4 (architect's consequence of `R-146a` and `R-146b`).** One host, no failover, no maintained copy of
  the database or the bucket off that host. A host loss, a provider loss of the VPS, an operator error or a
  ransomware event ends the service and may end the data. Reopen trigger (`AD-16`, confirmed by `R-146w`): the same as A-1,
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
| 6 | A deployment is not successful while `admin`/`password` is valid (`R-146i`, `R-146s`, `R-146z`) | `$DC run --rm --no-deps -T --entrypoint python api -m auditmanager.access.check` exits `0` (`1` means a must-change account; stricter than the gate, which `R-146z` narrows to the published pair); while it exits `1`, `$DC port proxy 8443` exits non-zero (443 is not published) and `curl -sS --connect-timeout 5 -o /dev/null https://<name>/login` cannot connect; after the password change and a deploy, `$DC port proxy 8443` prints a mapping | the first command yes; the rest no | `PROD-01`, `PROD-02` |
| 7 | The application connects with a role that cannot change the schema, before and after a restore (`R-146n` item 1) | `$DC exec -T postgres psql -U <migrator> -d <db> -Atc "select rolsuper, has_schema_privilege(rolname,'public','CREATE'), has_table_privilege(rolname,'public.audit_event','DELETE'), has_table_privilege(rolname,'public.audit_event','INSERT') from pg_roles where rolname='<application role>'"` prints `f\|f\|f\|t`; the same query is repeated after a `restore-db` rehearsal | no | `PROD-04` |
| 8 | Memory and log limits on every long-running service (`R-146n` item 2) | `$DC config --no-env-resolution --format json \| python3 -I -c "import json,sys;c=json.load(sys.stdin)['services'];print(sorted(k for k,v in c.items() if k not in ('migrate','release-notes','s3-init') and not ((v.get('mem_limit') or v.get('deploy',{}).get('resources',{}).get('limits',{}).get('memory')) and v.get('logging',{}).get('options',{}).get('max-size'))))"` prints `[]` | no | `PROD-05` |
| 9 | A migrating deploy follows a fresh copy receipt (`R-146n` item 3, `R-146t`) | `infra/deploy/deploy.sh` on a checkout with a newer revision, the `real_data` marker present and a record older than 24 hours (or none) ends with `REFUSED [stand-copy-fresh]` and exit `3` before any build; the guard is shown to fail by deleting its marked block, as `tests/integration/composition/test_deploy_script_refusals.py` does for the others | no | `PROD-03` |
| 10 | The release checklist carries the manual scan (`R-146n` item 5) | `grep -n "manual_scan" docs/program/RELEASE_PROCESS.md` has a hit and `scripts/release/manual_scan.sh --check-tools` exits non-zero when a scanner is missing | no | `PROD-09` |
| 11 | No CI workflow is added (`R-146h`) | `ls .github/workflows` prints only `deploy-auto.yml`; `tests/contract/test_deploy_auto_workflow.py` pins that workflow | yes | none (non-expansion) |
| 12 | One worker slot (`R-146j`) | `$DC exec -T postgres psql -U <migrator> -d <db> -Atc "select count(*), sum(slots) from worker where heartbeat_at > now() - interval '90 seconds'"` prints `1\|1` | yes | none |
| 13 | No metrics, tracing or error-reporting library is used (`R-146k`); **documentation check only**: a keyword search detects obvious libraries and cannot prove the absence of one under another name | `rg -il "prometheus\|opentelemetry\|sentry" src infra --glob '!*.md'` prints nothing, and `grep -c "@opentelemetry" web/package-lock.json` prints `2` (the optional peer of the web framework, nothing else) | yes | none |
| 14 | The missing off-host copy stays visible (`A-1`, `A-4`) | `infra/deploy/readiness.sh` prints `readiness FINDING off-host-backup`; `tests/integration/composition/test_readiness_command.py` pins that readiness reports and never gates (`R-46`) | yes | none; do not silence it |
| 15 | A restore drill was run at the head being released; **documentation check only**: it proves a record exists, the drill is the owner's act | `grep -l "^head: $(ls db/migrations/versions \| tail -1 \| sed 's/^[0-9]*_//; s/\.py$//')$" docs/program/RECOVERY-DRILL-*.md \| xargs grep -l "^result: pass$"` prints a file (the two lines are the record format `PROD-17` fixes; the 0029 record does not have them) | command yes; today it prints nothing (`D-216`) | `PROD-17` |

## Consequences

### Positive

- The terminator, its renewal and its headers are in the repository, are tested, and are deployed by
  the same workflow as the application; `D-191` stops depending on a file nobody can read.
- A compromise of the API process no longer carries the right to change the schema or truncate a
  table.
- Once real client data is on the stand, a migrating release cannot reach the database without a quiesced, attested copy taken within the last day.
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
2. **A certificate placed by hand and renewed by hand.** Rejected by `R-146a`, which puts the terminator and its
   ACME renewal in `infra/`; the certificate of the live stand expires on 2026-12-30 (`D-191`), which is why the plan
   gives `PROD-01` a deadline and carries an interim owner item (`PROD-21`).
3. **Nightly dump with an off-host mirror.** The recommended option of the poll; the owner chose
   manual copies (`R-146b`). Not built; `A-1`.
4. **A managed PostgreSQL and managed object storage.** Not asked; would contradict `ADR-0020`'s single
   failure domain and `R-146a`'s single host.
5. **A new `dump-db.sh` beside the copy key's verb of the same name**, or a receipt that is a second file: rejected, the copy record is the receipt (section 5).

## Verification

- automated check/test: the rows above; existing guards `tests/contract/test_deploy_auto_workflow.py`,
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
