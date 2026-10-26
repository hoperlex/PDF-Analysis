# The deployment runbook — a machine that has never run this

**Written by `W26-HOST` on 2026-09-21, under `R-15`.** Everything in it was driven on the
development host. **No part of it has run on the `R-1` host, because that host does not
exist yet**, and where that boundary bites it is named rather than guessed past.

## Why this is here and not in `infra/deploy/README.md`

The README is the **reference**: one section per file, the mechanism, and the measurement
behind each decision. It is what you read when something behaves oddly and you need to know
why it was built that way. It is not an order of operations, and three of the things below
are not facts about `infra/deploy/` at all:

* **`R-4` is an owner ruling with one half open and one half answered.** Who uploads a
  real client document is the owner's and is **not settled** (`OWNER_RULINGS_2026-09-17.md`
  §4). What event counts as *"the end of the pilot"* **is settled**, by `R-41` and `R-42`:
  the owner declares the end explicitly, with no date and no observable event, and performs
  the wipe personally — §7 below carries it in full, and the argument this runbook lost.
  A procedure that depends on an unanswered question has to be able to say so, and
  `infra/deploy/README.md` is not a place where a programme question can be left open
  honestly;

  *(`Y-A`. This paragraph said **both** halves were open and *"not settled"* until
  2026-09-29, twenty lines above a §7 that had been rewritten the same day to say `R-41`
  answered one of them. An operator reading from the top was told the trigger was unsettled
  before reaching the section that settles it, and the preamble is the paragraph that
  justifies §7 existing at all. The repair is one sentence and not a deletion, because the
  preamble is where the reader learns which half is answered and which is not.)*
* **`PA-01` criteria 1 and 2 stay *cannot be established* for a reason that is not the
  software** (`R-1`). That belongs beside the roadmap it is a criterion of;
* the order — environment, then deploy, then prove, then TLS, then the wipe — is a
  **programme commitment**, not a property of any script.

So: the order and the decisions live here, the mechanism and the measurements live in
`infra/deploy/README.md`, and **neither restates the other**. Where you need the why, this
file points at it.

---

## 1. What the host must have

`W23-DEPLOY` deployed from a **clean clone** and recorded what it actually used. This list
is that measurement, not a wish:

| | |
|---|---|
| **`bash`** | `deploy.sh`, `reset.sh`, `verify-deployed.sh` and `reload-proxy.sh` are bash |
| **`docker`**, with the **compose v2 plugin** | `docker compose`, not `docker-compose` |
| **`curl`** | the deploy's own health questions, and the proxy check |
| **`sed`** | how every script reads the environment file, as data and never by sourcing it |
| **`git`** | to get the clone here in the first place |

**And nothing else.** No `make`, no `npm`, **no `.venv`, no `web/node_modules`** — the
clone `W23-DEPLOY` deployed had none of them and needed none, because everything is built
inside the three repository-owned images. `make bootstrap` and `npm ci` are the *developer's*
gate, not this.

One optional extra: §2 suggests `python3` for one line that generates a token.
`openssl rand -base64 32` does the same job if the host has no python.

### Ports

* **one published port** for the stack, `ALPHA_HTTP_PORT` — the proxy's, and nothing else
  leaves the host. PostgreSQL, MinIO, the API and the web app are reachable only on the
  compose network and publish nothing;
* **two more if the stack terminates TLS itself** (`ALPHA_CERT_NAME` is set, §6): public port
  `80`, which serves the ACME challenge and a redirect to HTTPS and **reaches no part of the
  application**, and public port `443` (`ALPHA_HTTPS_PORT`), which exists only for a deploy that is
  cleared to publish and has a certificate (`R-146s`). Both are the proxy's, and the proxy is still
  the only service that publishes anything.

**The application's own port is bound to `127.0.0.1` unless you say otherwise, and you reach the
stand over an SSH tunnel.** Ruled by the owner 2026-09-22, closing `D-49`:

```
ssh -L 31500:127.0.0.1:31500 <host>        # then open http://127.0.0.1:31500 locally
```

**Why the default is loopback, measured rather than assumed.** The compose file used to
publish with no interface at all, which binds `0.0.0.0`. On 2026-09-22 this host's stand
answered **`200`** on its **public** address, at `/bff/v1` — which then served **every operation
of this surface**, **writes included**, to anyone, because the browser deliberately holds no secret
and the BFF route added the credential server-side. Nothing but the network was keeping anyone out.
**That is history, not today's behaviour:** since wave 34 the BFF forwards a credential only for a
live session cookie and answers **`401`** to every other caller, and `/api/v1/openapi.json` answers
**`401`** since `R-31` (re-measured in `EXPOSURE-REVIEW-01.md` `E-8`). The loopback default below
stays as the second line of defence.

**`ufw` was not keeping anyone out either, and structurally could not.** `ufw status` reported
a single open port while this one answered the world, because **a Docker-published port never
reaches ufw's `INPUT` chain** — Docker writes its own rules into `nat/DOCKER` and
`filter/DOCKER`, and those are traversed first:

```
iptables -t nat -L DOCKER -n | grep 31500
  DNAT  tcp  0.0.0.0/0 -> 0.0.0.0/0  tcp dpt:31500 to:<container>:8080
```

**Do not read a green `ufw status` as evidence about a published container port.** It is
evidence about traffic ufw sees, and this traffic does not reach it.

**`ALPHA_BIND_ADDRESS` is how a host that genuinely should publish the plain application port
says so** — one behind a firewall you have *verified against the chains above*. Since
`PROD-01-TLS-ACME-01` it governs **only that plain listener**: the public ports 80 and 443 follow
`ALPHA_PUBLIC_ADDRESS`, and once `ALPHA_CERT_NAME` is set `deploy.sh` refuses a non-loopback value
here, because the application is then public only over TLS. `R-4` puts real client documents on
the pilot server, and these are the lines that decide who can reach them.

Check, after any deploy:

```
docker port <instance>-proxy-1                 # expect 127.0.0.1:<port>, not 0.0.0.0
curl -s -o /dev/null -w '%{http_code}\n' http://<this host's own ip>:<port>/bff/v1/projects
```

The second must fail to connect. On this host it printed `200` before the fix and `000` after.

### Behind a host nginx — the client address (`REAL-IP-EDGE-01`)

**Applies only if a nginx on the host terminates TLS and passes to the published port**
(`proxy_pass http://127.0.0.1:<ALPHA_HTTP_PORT>`), which is how the stand is served **until §6 is
done**. When the stack terminates TLS itself (`ALPHA_CERT_NAME` set) there is no host terminator
and this section is the thing to **undo**: empty `ALPHA_TRUSTED_PROXY_CIDRS` (`deploy.sh` refuses a name together with
a non-empty list), because the client address then arrives on the connection and a client in the list could name its
own bucket. Without this
step the stack is correct and safe, but every per-address throttle — sign-up, the sign-in token
exchange (`POST /api/v1/auth/token`) and the web tier's guest bucket — is **one bucket for all
visitors**, because the proxy container sees every connection from the compose network's
gateway (`D-144`, `D-191` `E-3`). The mechanism and the measurement are in
`infra/deploy/README.md`, "The client address"; what an operator does is this.

1. **Host nginx**, in the `location` that passes to the stack, this line — written by the host,
   never forwarded from the client:

   ```
   proxy_set_header X-Forwarded-For $remote_addr;
   ```

   (`$proxy_add_x_forwarded_for` is also safe; **no `X-Forwarded-For` line at all is not**: the
   client then chooses its own bucket.) Reload the host nginx.
2. **Read the address the stack sees the host from**, before changing anything:
   `docker network inspect <ALPHA_INSTANCE>-net --format '{{(index .IPAM.Config 0).Gateway}}'`,
   and cross-check the first field of `docker logs <ALPHA_INSTANCE>-proxy-1 --tail 5` after one
   request through the host nginx. They must agree.
3. **`alpha.env`**: `ALPHA_TRUSTED_PROXY_CIDRS=<that address>/32`. A comma/space list is accepted;
   `0.0.0.0/0`, host names and anything that is not an IPv4/IPv6 address or CIDR are refused by
   `deploy.sh` before it builds (guard `trusted-proxies-well-formed`).
4. **Deploy as usual** (`infra/deploy/deploy.sh`). The changed environment recreates the `proxy`
   container. Read `docker logs <ALPHA_INSTANCE>-proxy-1 2>&1 | grep trusted-proxies` — it must say
   `1 peer(s) trusted`, or `is empty` if you meant to leave it off — and run the twelve-request
   check in the README: no `429`.
5. **Rollback**: delete the line (or leave it empty) and deploy again; the proxy is back to counting
   the TCP peer, with nothing to undo in the images.

**What is trusted, and what is not.** The proxy believes `X-Forwarded-For` **only** from a peer in
the list, and from it only the rightmost address that is not itself in the list; a client cannot
write its way to another bucket, from any peer. Everything on the host that can open
`127.0.0.1:<ALPHA_HTTP_PORT>` is such a peer, an SSH-tunnelled operator included; they may name an
address for the throttles and for nothing else. If the gateway changes (network recreated), the
list stops matching and the stack **falls back to the shared bucket, never to believing a client**:
re-read step 2 after any `down` that removed the network.

**UNVERIFIED** (the stand is not reachable from the lane that wrote this): the stand's network
name and gateway; its host nginx's actual `proxy_set_header` lines; whether its Docker runs with
the userland proxy disabled (the source address seen by the container was measured only with the
default); and that no CDN or load balancer sits in front of the host nginx (if one does, the host
nginx's `$remote_addr` is that device and the host needs real-IP handling of its own first).

### Disk

**Measured on 2026-09-21 by `W26-HOST`, on a cold cache, before the repository-owned
pgvector derivative was added.** The numbers below remain the measured application-build
baseline; they are not a fresh certification of the extra PostgreSQL compile stage.

The shared build cache on this host holds another lane's layers, so a build on the default
builder would have reused them and measured nothing. The instrument was therefore an
**isolated builder**, which starts with an empty cache and pulls its own base images —
which is also what a host that has never run this does:

```
docker buildx create --name w26cold --driver docker-container --bootstrap
docker buildx --builder w26cold build --load -f infra/deploy/Dockerfile.api -t m-api .
docker buildx --builder w26cold build --load -f infra/deploy/Dockerfile.web \
  --build-arg NEXT_PUBLIC_API_BASE_URL=/bff/v1 --build-arg NEXT_PUBLIC_INSTANCE_LABEL=alpha -t m-web .
docker buildx du --builder w26cold          # the cache the two application builds produced
docker buildx rm w26cold                    # and df before/after each removal
```

| what | measured |
|---|---|
| **application build cache**, both app images, cold | **2.59 GB** (`buildx du`), confirmed by `df`: **2.42 GiB** freed when the builder was removed |
| **the two application images** | 400 MB + 1.2 GB (`docker images`). Removing both here freed **1.01 GiB**, because this host already had the `python` and `node` bases; a host that does not will pay the full 1.6 GB |
| the four pinned third-party image inputs compose pulls | **1.08 GB** — PostgreSQL base 646 MB, MinIO 241 MB, mc 117 MB, nginx 74.5 MB |
| the clone | 69 MB, with no `.venv` and no `node_modules` |
| the named volumes, just after a first deploy | ~76 MB for the two `W26-HOST` measured (`-postgres-data`, `-s3-data`), and they grow with the documents. **There are three**: `R-51` added `<instance>-web-sessions`, which holds one small JSON file and is measured in kilobytes, not megabytes |
| both builds, wall clock, cold | about five minutes |

**The pre-pgvector clean-clone cold-cache deploy needed about 5.5 GB**, of which ~2.6 GB was
build cache that `docker builder prune -af` took straight back. Treat this as a lower bound until
the new PostgreSQL compile stage is repeated with the isolated-builder instrument above; retain
the existing **8 GB free** admission rule in the meantime.

**The figure that was being repeated is 8 GB, and it is right as a provisioning number for
the wrong reason.** It comes from `W24-CERT2` §3c, where two image builds took `/` from
8.9 GB free to **0 bytes** — on the **third** consecutive deploy, where the cache already
held earlier generations. That is the thing to plan for: **the cache grows with each build
whose sources changed, and nothing removes the old generation.** So:

* **≥ 8 GB free before the first deploy**, which leaves room for the second and third;
* **`docker builder prune -af` after each deploy**, which on that host returned 8.2 GB;
* a host at 0 bytes does not fail cleanly. MinIO refused a bucket-policy write on its
  minimum-free-drive threshold, `s3-init` exited 1, `api` never started, and the proxy
  could not resolve its upstream — a deploy that looks like four unrelated faults.

---

## 2. The one file a human must write

```
git clone <this repository> auditmanager && cd auditmanager
cp infra/deploy/env/alpha.env.example infra/deploy/env/alpha.env
chmod 600 infra/deploy/env/alpha.env
$EDITOR infra/deploy/env/alpha.env        # and change EVERY value in it
```

**`infra/deploy/env/alpha.env` is the only thing a person authors, and `deploy.sh` refuses
to invent it.** Its own words, from the `env-file-present` guard: *"A deploy that invented
an environment would deploy something nobody configured."* The file is git-ignored, so a
clean clone does not have one and never will.

Two of its values are not free choices:

* **`AUDITMANAGER_API_TOKEN`.** Generate it per deployment, never reuse the example's:

  ```
  python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
  ```

  **Since wave 34 this is the key the API signs reviewer credentials with, not a token
  anyone presents.** Whoever holds it can mint a credential for any subject, so it goes to
  no reviewer and into no browser — and **since `HARDEN-01` (2026-10-27) it goes to one
  process, `api`**, where it belongs. It used to go to `web` as well, under the belief that
  the web tier forwards it on the sign-in exchange; since `C-17` (`W53-CLOSE`) it forwards
  nothing of the kind (the sign-in exchange carries no `Authorization` header, every data
  forward carries the *reviewer's* own credential), so `web` held mint-capable key material
  it never used (`EXPOSURE-REVIEW-02` `F-03`). `compose.server.yml` no longer gives it to
  `web`; `tests/integration/composition/test_web_service_holds_no_signing_key.py` holds
  that, and fails the day a `web/src` module starts to read it. The paragraph that used to
  tell operators to present it as a bearer token is corrected in
  `infra/deploy/README.md` and, since 2026-09-29, in `infra/deploy/env/alpha.env.example`
  — the file you actually edit (`Y6`).

  *(`Y-F`. Until 2026-09-29 this paragraph said the value goes to *"the API process and
  nowhere else — not to a reviewer, not into a browser, not into a request header."* Two of
  those three held; the header clause and *"nowhere else"* did not, and this is the paragraph
  written to repair an earlier falsehood of exactly this kind. Read the chain:
  `grep -n 'AUDITMANAGER_API_TOKEN' infra/deploy/compose.server.yml` → `:173` api, `:208`
  web [now: the `api` line only]; `grep -n "headers.set('authorization'" web/src/shared/api/credentialed-forward.ts`.
  **What it does not expose**, measured by `W47-JUDGE-X` §1.4 rather than argued: the value
  is not itself a usable credential — presented as `Authorization: Bearer` or as `X-API-Key`
  against a protected operation it answers **401**, because the seam signs with
  `HMAC(secret, context)` — and nothing about this reaches a browser. What it **is** is mint-capable
  key material in a second container's environment, which is what an operator deciding where
  this value may go needs to know. Stopping `web` from holding it at all is a decision about
  who can mint a credential, which `R-29` §2 reserves to the owner; it was not a repair a
  wave could take. **`HARDEN-01` took it** inside the `PW3` window, whose owner message of
  2026-10-26 gave the permissions in advance and whose lane H names `F-03`; the change only
  narrows a credential's reach and exposes nothing that was not exposed, and the integrator
  confirms it against `R-29` §2.)*

  The seam is **fail-closed**: a container started without it exits non-zero rather than
  serving `authentication_required` to **every one of its operations**, which from a browser
  looks like a broken product rather than an unconfigured one;

  *(`Y10`: both of those read *"nineteen operations"* until 2026-09-29 and the contract
  declares **twenty**. The number is not restated here, because nothing reads this file for
  it — `test_surface_counts_in_prose.py` scans `src/auditmanager/api`, `infra/deploy` and
  `web/src`, and `docs/` is in no guard's scope (`D-104`). `deploy.sh` prints it from both
  sides on every run — `frozen ops : 20` and `served ops : 20` — and
  `python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print(sum(1
  for p,i in d['paths'].items() for m in i if m in ('get','post','put','patch','delete')))"`
  answers **20** against the tree.)*

* **the passwords.** `deploy.sh` compares what you wrote against the example file's own
  published values and refuses, by identity, if you left any of four unchanged. Those
  values are in git and are not secrets.

* **the second database password (`PROD-04`).** `api` and `worker` no longer connect as the database owner:
  they connect as an application role whose password, `ALPHA_APP_DB_PASSWORD`, is yours to choose on this host.
  The example ships the name **with no value** and `deploy.sh` refuses an empty one (`[app_db_password_unset]`);
  nothing falls back to the owner role. Section 16 is the procedure.

**No credential is ever pasted into a chat message** — `OWNER_RULINGS_2026-09-17.md` §3:
*"the credential goes on that host's disk, by the owner"*. That includes the output of
`docker compose config`, which prints **every** environment value in clear, the provider
credential included (measured — §10).

### The provider credential is a second file, and it is optional

```
cp infra/deploy/env/provider.env.example infra/deploy/env/provider.env
chmod 600 infra/deploy/env/provider.env
$EDITOR infra/deploy/env/provider.env
```

`compose.server.yml` reaches it with `env_file: required: false`, so with
`AUDITMANAGER_PROVIDER_MODE=recorded` — the example's default — it may stay empty or absent
entirely. It is never passed to `--env-file`, which keeps these names out of compose
**substitution**, where they could otherwise be interpolated into an image tag or a label.

### Updating an existing VPS to the normative-corpus foundation

The ignored `alpha.env` and `provider.env` are host state. A pull does not replace them, and an
operator updating an existing alpha must **not** copy the examples over them. From the existing
clone, with a clean tracked worktree:

```
git status --short
git fetch origin
git switch main
git pull --ff-only origin main

infra/deploy/deploy.sh --env-file infra/deploy/env/alpha.env
infra/deploy/verify-deployed.sh --env-file infra/deploy/env/alpha.env
```

`git status --short` may stay silent even though the ignored secret files exist; that is expected.
If it reports tracked changes, stop and preserve/reconcile them before pulling instead of resetting
the VPS checkout. Never force-update the checkout or remote branch as part of deployment.

The deploy first builds the repository-owned PostgreSQL 17.11 derivative with pgvector 0.8.6.
Its one-shot `migrate` service then upgrades the database through `0013_norm_embeddings` before
the API starts. It creates corpus persistence and the durable `vector(1024)` projection but does
not load corpus content or generate embeddings. The current alpha app still has no search API/UI
or production BGE runtime. Therefore this update needs no new env name. The existing `recorded`
provider mode remains the safe no-spend alpha default; a live/proxy credential still belongs only
in `provider.env`.

---

## 3. Deploy

```
infra/deploy/deploy.sh
```

Run it **from the repository root**; both builds need `src/`, `db/`, `contracts/`,
`uv.lock` and `web/` in their context.

| Exit | Meaning |
|---|---|
| **0** | the stack is up **and has answered for itself** — see below |
| **3** | it refused, and said which of **fourteen** guards refused and why |
| **2** | the arguments were wrong |

**Since `PROD-04` the order is: build; the owner migrates (`migrate` and `release-notes` as `MIGRATOR_DATABASE_URL`);
`apply-grants.sh` gives the application role its rights and verifies them; only then `up`** — so `api` and `worker`
never start against a schema their role cannot read, and a table nobody classified (`[grants_unclassified]`) stops the
deploy before anything is replaced. Section 16.

**Eight** guards answer **before docker is touched at all**, so a refusal costs nothing.
After the build and the `up`, it asks the running stack four questions it can fail: every
service healthy; the database at the head this code expects; **the published port answering
`401`** on `/api/v1/openapi.json`; and **the document the process serves conforming to the
frozen `contracts/api/v1/openapi.json`** — the gate's own conformance engine, re-run against
the deployed process. That last one is `PA-01` criterion 1's second clause and it is about
the **API schema**, not the database schema.

*(Two corrections, 2026-09-29. `Y5`: this said **thirteen** and **seven**, and this wave is
why — `W47-GATE`'s `D-103` repair added `derived-secrets-coherent`, which joins the set that
refuses before docker. Count them from the tree, and anchor the marker: `grep -cE '^# >>>
guard: ' infra/deploy/deploy.sh` → **14**, while a bare `grep -c '# >>> guard:'` answers 15,
because `deploy.sh:89` documents the marker syntax using the marker. The eight are
`known-options`, `env-file-present`, `instance-configured`, `identity-policy-known`,
`placeholder-secrets`, `derived-secrets-coherent`, `compose-file-present`,
`build-context-complete`; the ninth, `port-not-foreign`, is the first that runs `compose ps`.
`Y3`: the third question was written as **200**. `R-31` closed the four documentation routes
behind a credential and moved the guard with them, so **401 is the answer that proves life**
— only the application's own authorization seam can produce it, while nginx holding a dead
upstream answers 502/503/504 — and **a 200 there is a refusal**, in `deploy.sh`'s own words:
`sed -n '751,772p' infra/deploy/deploy.sh`.)*

A second run against an unchanged tree replaces **no container at all** (`W24-IDEM`).

**Two refusals that are about the data and not about the build (`PROD-02-03-DEPLOY-GATES-01`).** Both exit **3**
like every other refusal, and both carry a typed word that deploy-auto's log shows:

| Word | When it speaks | What it means | What to do |
|---|---|---|---|
| `stand_copy_fresh` | **before the build**, only when the `real_data` marker exists *and* this checkout carries a migration the database does not have | `R-146t`: a migrating deploy on a stand that holds real data needs a fresh copy receipt (§13) | take the copy and deploy within 24 hours of the dump (§13, "A migrating deploy needs a fresh receipt") |
| `default_credential` | **after `migrations-at-head`** (the database must exist) | `R-146i`, `R-146s`: the **published seeded pair** `admin` / `password` is valid. The deploy ends non-zero **naming the login**, public port 443 is **not published**, and every service keeps running on loopback | sign in through an SSH tunnel to the loopback port, change the password, deploy again |
| `default_credential_unanswered` | same place | the check could not be run or printed neither of its two sentinels: whether the pair is valid is **not known**, so nothing is claimed | read what it printed (it is shown above the refusal); fix the stack; deploy again |

**The gate asks one question: is the published pair valid?** Only an *active* account with the login `admin` whose stored
credential verifies against `password` fails it (`R-146z`). A temporary password an administrator issued with
`resetUserPassword` marks the account must-change too, but it prints a `GATE WARNING temporary password` line and
**never fails** the deploy; `readiness.sh` keeps asking the wider question and reports both (§9). The check is
`python -m auditmanager.access.check --gate` inside the `api` image; run by hand it prints
`access-check GATE OK no published credential` (exit 0) or `access-check GATE DEFAULT CREDENTIAL: login=admin ...` (exit 1).

**A fresh host's first deploy ends non-zero, on purpose.** The stack comes up, the services are healthy, the application
answers on `127.0.0.1:<ALPHA_HTTP_PORT>` — and the deploy refuses with `[default_credential]` because the database was
just migrated and still holds the seeded pair. That is `R-146s`: the public door never opens on a pair anyone can read in
this repository. Change the password (§6 step 10) and deploy again; the second run publishes 443 if you asked for it
and a certificate exists.

**What a redeploy no longer costs, since `R-51`: the reviewers stay signed in.** `deploy.sh`
recreates the `web` container on every run that changes it, and until wave 47 that container
held every open session in its own memory, so **every deploy signed every reviewer out** —
a support incident per deployment rather than a rare one. The register is now a file on a
third named volume, `<instance>-web-sessions`, mounted by `web` and by nothing else, and a
recreated container finds the sessions the previous one left. The mechanism and what it
costs are in `infra/deploy/README.md`; what belongs here is the order of operations, which
is the next two paragraphs and §5's line about `down --volumes`.

**So a redeploy is no longer a logout, and `down --volumes` is.** Those are the two facts an
operator needs while deciding which command to type, and until 2026-09-29 this document
carried neither (`Y1`): `grep -c -i session docs/program/DEPLOYMENT_RUNBOOK.md` answered
**0**.

---

## 4. Prove it is this tree, and keep proving it

```
infra/deploy/verify-deployed.sh
```

**0** the stack is this working tree, **6** it is not, **4** the question could not be
answered, **7** it is this tree and the certificate it serves is not acceptable (§6), **8** it is this tree and
the published `admin` / `password` pair is **valid** (it names the login, and says loudly if 443 is published
meanwhile; `PROD-02`) — and only the first is a success. Run it after every deploy. Its first live
execution found a deployed web image eleven minutes older than the commit a brief claimed
was running.

**After any rebuild, before anything else:**

```
infra/deploy/reload-proxy.sh
```

nginx resolves an upstream **once, at worker start-up, and holds it**. A rebuild replaces
the `api` and `web` containers, and when a replacement lands on a different address the
proxy answers **502 for everything** while both new containers are healthy and compose says
nothing is wrong. It is **intermittent** — a replaced container usually gets its old
address back — so *"the last rebuild was fine"* is not evidence about the next one
(`D-27`).

---

## 5. What this runbook does **not** do

* **fetch a revision, switch between versions, or roll one back.** All three are claims
  about a server that has a previous version on it. What `deploy.sh` does instead is put
  the **build before the switch**, so a failed build leaves whatever was serving still
  serving;
* **anything needing a second machine** — no blue/green, no failover, no off-host backup
  target. `reset.sh`'s dumps land on this host's disk and getting them off it is not
  automated here;
* **certificate renewal on a host whose terminator is not this stack.** With `ALPHA_CERT_NAME` set the
  stack renews its own certificate (§6). Without it nothing here obtains or renews one, and the host's
  nginx, outside this repository, is whatever it was (`D-191`).

**And one thing it will not stop you doing, so it says it here.** `docker compose ... down`
leaves all three named volumes alone. **`docker compose ... down --volumes` removes them —
the documents, the objects *and* every open session.** The third of those is the one nobody
expects: it signs every reviewer out at once, and it is the only command that undoes what
`R-51` bought. `R-4` is why the first two matter: real client documents may be on that
stack, and the only sanctioned way to remove them is `infra/deploy/reset.sh`, which dumps
before it drops. **`down --volumes` dumps nothing.**

---

## 6. TLS — the stack's own terminator, the staging rehearsal, the cutover, turning it off

**`PROD-01-TLS-ACME-01` (`ADR-0021` section 2, `R-146a`, `R-146aa`, `R-146ac`, `R-146s`) rewrote this section.**
Until then it said the owner puts a certificate pair into a directory by hand. Now the stack **obtains and
renews its own certificate**: an ACME client runs as a service of the same compose project, proves control
of the name over HTTP-01 through port 80, and writes the pair to a named volume that the `proxy` reads
read-only. **Nothing in this section has been run against a certificate authority, and nothing in it has run
on the host**: the lane that built it had no network and no docker, and its tests drive the scripts against
stand-ins (`tests/integration/composition/test_acme_*.py`). The procedure below is therefore a **rehearsal
plan with the expected output of each step**, and the first run of it is the owner's.

**Nothing about it is on by default.** With `ALPHA_CERT_NAME` empty or absent, none of this exists and the
stack is byte-for-byte the deployment that was certified before — which is also the rollback.

### The three listeners (`R-146s`)

| listener | where | serves | when it exists |
|---|---|---|---|
| plain application | `127.0.0.1:${ALPHA_HTTP_PORT}` | the whole application, as before (`deploy.sh`'s `proxy-answers` guard wants `401` on it) | always |
| challenge | public port **80** | the ACME webroot and a **redirect to HTTPS**; **no route to the application at all** | whenever `ALPHA_CERT_NAME` is set — so issuance and renewal work while the seeded password is still the seeded one |
| application over TLS | public port **443** | the application, with HSTS | only for a deploy that is cleared to publish **and** whose certificate pair exists |

So on a host that has never been published the stack comes up on loopback with port 80 answering the
challenge; you reach the loopback port through an SSH tunnel and change the administrator's password; the
next deploy publishes 443. **"Cleared to publish" is two things since `PROD-02`: the setting you write yourself,
`ALPHA_PUBLISH_HTTPS=yes`, AND a clean credential gate** (`python -m auditmanager.access.check --gate`: the
published `admin` / `password` pair is not valid; §3). The setting alone opens nothing. A deploy decides it in two
steps because the gate needs the database: the full `up` never opens 443 on a proxy that does not already publish it
(it keeps an already published one only if the setting still says `yes` and a pair exists), and the gate step after
`migrations-at-head` then opens it, or withdraws it by recreating **only the proxy** without the 443 overlay.

**A restore can bring the seeded pair back, and both restore paths now say so and close the door** (`R-52`,
`R-146s`): `reset.sh --restore` (§7) and `copy-serve.sh restore-db` (§13) end by asking the same gate. On a finding
— or on an answer they could not get, which after a restore is not "fine" — they recreate the proxy without the 443
overlay, so **the site is unreachable from outside until an administrator changes the password through the loopback
port** (the consequence `R-146s` accepts). A restore never *opens* 443; only a deploy does, after a clean gate.
`restore-db` also raises every account's `token_epoch` now, as `reset.sh --restore` always did.

### What goes in `alpha.env`

`infra/deploy/env/alpha.env.example` has the commented block ("the TLS terminator"); the values:

| setting | meaning | default |
|---|---|---|
| `ALPHA_CERT_NAME` | the public DNS name of this host; lower case, at least two labels, no wildcard, no port. A placeholder or reserved name is refused by `deploy.sh`. **The live name belongs here, on the host, and in no default anywhere in the repository** | empty: no terminator |
| `ALPHA_ACME_EMAIL` | contact address for the authority; optional | none |
| `ALPHA_ACME_STAGING` | `yes`: the authority's TEST endpoint (certificates no browser trusts, loose limits). `no`: the real issuance | **`yes`** — a forgotten line spends the test endpoint's limits and never the real one's |
| `ALPHA_PUBLISH_HTTPS` | `yes` asks for 443 for a deploy that has a certificate — **necessary, never sufficient**: the credential gate must also be clean (`PROD-02`) | `no` |
| `ALPHA_PUBLIC_ADDRESS` | the interface 80 and 443 bind | all interfaces |
| `ALPHA_ACME_HTTP_PORT`, `ALPHA_HTTPS_PORT` | the published ports; change them only for a rehearsal on a machine whose 80 and 443 are not free | `80`, `443` |
| `ALPHA_BIND_ADDRESS` | the **plain application** listener. With a name set `deploy.sh` refuses anything but loopback | loopback |

### Before the first deploy of this tree on the live host (`D-229` item 2)

"With `ALPHA_CERT_NAME` empty the stack is byte-for-byte the deployment that was certified before" is true of what is
built and started and **not** of everything the scripts refuse, print or accept. Three differences are visible on a host
that has never had a name, and the first one is a deploy that stops. Do this once, **before** the first deploy of a tree
that contains `PROD-01`, on the host (the live one included):

- [ ] `alpha.env` holds **none** of these keys with a value, unless `ALPHA_CERT_NAME` is also set: `ALPHA_ACME_EMAIL`,
  `ALPHA_ACME_STAGING` (any non-empty value), `ALPHA_PUBLISH_HTTPS=yes`. Without a name `deploy.sh` now **refuses** them
  (guard `acme-settings-well-formed`: `REFUSED: ALPHA_ACME_EMAIL, ALPHA_ACME_STAGING or ALPHA_PUBLISH_HTTPS is set in
  <env> and ALPHA_CERT_NAME is not.`, exit 3, nothing built) instead of ignoring them.
  ```
  grep -nE '^[[:space:]]*(export[[:space:]]+)?(ALPHA_ACME_EMAIL|ALPHA_ACME_STAGING|ALPHA_PUBLISH_HTTPS|ALPHA_TLS_DIR)=' \
    infra/deploy/env/alpha.env
  ```
  Expect no output. (`ALPHA_TLS_DIR` is in the list because it no longer exists: it is read by nothing, so a value
  there is a leftover to delete.)
- [ ] **Nothing passes `--tls-dir`** to `readiness.sh`, and nothing sets `ALPHA_TLS_DIR`. Both are removed: the `tls` check
  asks what the proxy *serves* (§9), not a directory, and `readiness.sh --tls-dir <path>` now ends
  `readiness.sh: unrecognised option: --tls-dir` with the usage text, exit 2. Look in the places a human put a call:
  the host's crontab and systemd units, any wrapper script, and `.github/workflows/` (the workflow in the repository
  passes no such option; a copy on the host may differ).
- [ ] If anything reads the deploy log for the line after the build: it reads `<instance>-api, <instance>-web are built`
  now, where it used to read `<instance>-api and <instance>-web are built` (and lists `<instance>-acme` as well when a name is
  set). Nothing in this repository matches that text.
- [ ] Not a PROD-01 difference but the next thing a first deploy of this tree meets, and it is **not** gated on a name:
  the default-credential gate (`PROD-02`, §3) refuses the deploy while `admin` still accepts `password`
  (`[default_credential]`, exit 3). Change the administrator's password through the loopback port first.

**A warning that is not a defect: the rehearsal turns every `deploy-auto` run red, by design.** The deploy workflow runs
`infra/deploy/verify-deployed.sh` with no arguments and cannot pass `--acme-rehearsal`. As soon as the live host's
`alpha.env` has a name **and** `ALPHA_ACME_STAGING=yes` — or no `ALPHA_ACME_STAGING` line at all, because the default is
`yes` (`R-146ac`: a forgotten line must spend the test endpoint's limits, never the real one's) — every automatic deploy
ends red at `verify-deployed.sh` with **exit 7** (`ALPHA_ACME_STAGING is yes ...: this stack is set to the authority's
TEST endpoint.`) even though the deploy itself succeeded and the stack is up. That is the intended answer to "you are
serving a certificate no browser trusts". So: keep the rehearsal (steps 5 to 8) short, do not read a red workflow during
it as a failed deploy, expect the next green one only after step 9 (`ALPHA_ACME_STAGING=no`), and remember that a push to
`origin/main` starts that workflow (`AGENTS.md` section 6) — do not publish to `main` during the rehearsal unless the red
run is acceptable.

### The procedure (the owner's; every step has the output to expect)

*Lines that a script of this repository prints are exact. Lines that certbot, docker or the operating
system print are given by shape and are marked "shape": they were not observed by the lane that wrote this,
and a difference in wording is not a failure — a difference in meaning is.*

**0. Know the deadline.** `PROD-01` is deployed, with its first real issuance, by **2026-12-16**; the live
certificate (the host nginx's) ends 2026-12-30 (`D-191`). `PROD-21` is the owner's interim renewal of that
certificate if this slips.

```
echo | openssl s_client -connect <name>:443 -servername <name> 2>/dev/null | openssl x509 -noout -enddate
```
Expect (shape): `notAfter=Dec 30 ... 2026 GMT`.

**1. Resolve the client pin once, from any machine with docker and network.** The image installs `certbot`
by exact package version from `infra/acme/client.pin`, which ships saying `UNRESOLVED`; `deploy.sh` refuses to
deploy a host with a name set until it is resolved (guard `acme-client-pinned`), and so does the image build.

```
docker run --rm alpine:3.22.1@sha256:4bcff63911fcb4448bd4fdacec207030997caf25e9bea4045fa6c8c44de311d1 \
  sh -c 'apk update >/dev/null && apk policy certbot'
```
Expect (shape): a first line `certbot policy:` and under it one or more lines `  <version>-r<n>:` each with the
repository that serves it. Write the highest one that the `community` repository serves into
`infra/acme/client.pin` as `ACME_CLIENT_APK_VERSION=<version>-r<n>`, commit it, and deploy that commit. **The
packages certbot depends on float within Alpine 3.22's repository at build time**; the image is identified by
its base digest and this version, not by a lock of its dependencies.

**2. Decide about the other application on this host.** `EXPOSURE-REVIEW-01.md` `E-6`: the host's nginx also
serves a different application on this machine. **Stopping that nginx in step 4 takes that application down
too.** If that is not acceptable, stop here: this stack cannot hold ports 80 and 443 beside another
terminator, and the layout needs a decision from the architect, not a workaround.

**3. Check the name and the ports.**
```
getent hosts <name>
```
Expect: the VPS's public address first on the line. (For a name under `sslip.io` the address is in the name.)
The provider's firewall must let **80 and 443** in. `deploy.sh` checks that nothing else holds the ports on this
host and says so (guard `public-ports-free`): `deploy.sh: REFUSED: public port 80 is already in use, and not by
<instance>'s proxy.` It asks the kernel's table of listening sockets (`/proc/net/tcp`, `/proc/net/tcp6`), so a host
nginx bound to **one address of the host** (`listen <ip>:80;`) is caught as well as one on loopback or on every
address (`D-229` item 1: a probe of `127.0.0.1` alone called that port free, and Docker's `0.0.0.0` publish then
failed on the bind after the build). On a host with no `/proc` it falls back to a connect to `127.0.0.1` and **says
so** (`deploy.sh: NOTE: no table of listening sockets could be read ...`): then check by hand with
`ss -ltnp 'sport = :80'`.

**4. The cutover window begins: stop the host's nginx.** From here the public site is down until step 9
(about ten minutes if nothing goes wrong).
```
sudo systemctl stop nginx
ss -ltn '( sport = :80 or sport = :443 )'
```
Expect: `ss` prints only its header line.

**5. The staging rehearsal.** In `alpha.env` set `ALPHA_CERT_NAME=<name>`, `ALPHA_ACME_STAGING=yes`, optionally
`ALPHA_ACME_EMAIL`, and **remove `ALPHA_TRUSTED_PROXY_CIDRS`** (the host nginx is gone; the client address now
arrives on the connection; `deploy.sh` **refuses** a name together with a non-empty list — guard
`trusted-proxies-empty-with-name`, `D-229` item 4 — because a peer left in the list could write its own address into the
guest throttle). Leave `ALPHA_PUBLISH_HTTPS` unset. Until step 9 every automatic deploy ends red at `verify-deployed.sh`
by design (see "Before the first deploy", above). Then
```
infra/deploy/deploy.sh
```
Expect, among the usual lines (exact):
```
deploy.sh: tls name   <name> (ACME: STAGING, rehearsal only)
...
-- the listeners this deploy has (provisional: the credential gate is asked after the migrations) --
  plain application listener : 127.0.0.1:<ALPHA_HTTP_PORT> (always)
  challenge listener         : public port 80 (the ACME webroot and a redirect; no application route)
  application listener (TLS) : NOT published -- the credential gate is not satisfied (ALPHA_PUBLISH_HTTPS is not yes), so 443 stays closed
...
  acme      running/healthy
...
deploy.sh: ALPHA_ACME_STAGING is yes: the certificate is the authority's TEST one, trusted by no browser.
```
If `deploy.sh` refuses with `the 'acme' service of <instance> is running/starting`, issuance is slower than the
two minutes the deploy waits: read step 6 and run `deploy.sh` again.

**6. Read the issuance.**
```
docker compose --env-file infra/deploy/env/alpha.env -f infra/deploy/compose.server.yml \
  -f infra/acme/compose.acme.yml logs acme
```
Expect (exact, from our scripts): `acme: STAGING: certificates come from the authority's test endpoint...`,
`acme: name <name>, lineage <name>-staging.`, then certbot's own output (shape: it ends in a success line and
`Certificate is saved at: /etc/letsencrypt/live/<name>-staging/fullchain.pem`), then
`export-pair: exported the pair of /etc/letsencrypt/live/<name>-staging to /export; the proxy picks it up on its next tick.`
and `acme: the certificate for <name> is in place and exported; next pass in 43200s.`
A failed attempt prints `acme: no certificate yet (attempt N)...` and the delay (60 s, 300 s, 900 s, then an
hour). **A failure here is the rehearsal doing its job**: read certbot's reason (DNS, port 80 not reaching the
proxy, the firewall) and fix it before step 8.

**7. The proxy applies it, within a minute.**
```
docker compose --env-file infra/deploy/env/alpha.env -f infra/deploy/compose.server.yml \
  -f infra/acme/compose.acme.yml logs proxy | grep -E 'watch-certificate|enable-tls'
```
Expect (exact): `watch-certificate: the certificate pair changed; applying it.`, `enable-tls: TLS IS ON.`,
`watch-certificate: nginx reloaded; the proxy serves the pair that is on the volume now.` A pair nginx refuses
prints `watch-certificate: REFUSED: nginx does not accept this pair...` with nginx's own words and is not
applied.

**8. Verify the rehearsal, and see that the production check refuses it.**
```
infra/deploy/verify-deployed.sh --acme-rehearsal
infra/deploy/verify-deployed.sh
```
Expect for the first (exact except the dates and issuer): `served-certificate: OK name=<name> mode=staging
notAfter="..." issuer="... (STAGING) ..." valid-for-at-least-days=14` and `the deployed stack IS this tree`.
Expect for the second: exit **7**, `ALPHA_ACME_STAGING is yes ...: this stack is set to the authority's TEST
endpoint.` The port-80 listener, from outside the host:
```
curl -sI http://<name>/api/v1/openapi.json
```
Expect: `HTTP/1.1 301 Moved Permanently` and `Location: https://<name>/api/v1/openapi.json` — and **not** `401`:
a `401` would mean port 80 reaches the application (`readiness.sh`'s `plain-http` check asks the same).

**9. The real issuance.** Set `ALPHA_ACME_STAGING=no` in `alpha.env` and run `infra/deploy/deploy.sh`. Expect
`(ACME: production)` on the `tls name` line, and in the log `acme: PRODUCTION: ...` and
`acme: name <name>, lineage <name>`. The production pair replaces the staging pair on the volume (the reverse is
refused: `export-pair: REFUSED: the exported certificate is a production one...`). **If the authority refuses for a
rate limit** — `R-146ac` recorded that a name under `sslip.io` shares its limits with every other user of that zone —
**stop**; the owner decides on a name of their own. Then:
```
infra/deploy/verify-deployed.sh
```
Expect (exact except dates and issuer): `served-certificate: OK name=<name> mode=production ...
valid-for-at-least-days=14` and `the deployed stack IS this tree`.

**10. Close the cutover: the administrator's password, then 443.** Reach the loopback port by tunnel
(`ssh -L 31500:127.0.0.1:31500 <host>`, `http://127.0.0.1:31500`), sign in as the seeded administrator and **change
the password**. Only then set `ALPHA_PUBLISH_HTTPS=yes` and run `infra/deploy/deploy.sh`. Expect (exact), after the
`-- the published default credential is not valid --` block (`no account accepts the published password; ...`):
`public port 443 is now published (ALPHA_PUBLISH_HTTPS=yes, a pair exists, the gate is clean).` and
`deploy.sh: TLS for <name>: the challenge listener is public on port 80; the application over TLS is` /
`deploy.sh: published on port 443 (the credential gate is clean).` On the first publication the deploy that issued the
certificate and the deploy that publishes it are two runs; if they were one, the deploy prints `no certificate pair
exists yet ...` and `run this script again`. **If you forgot to change the password**, the same deploy ends
`REFUSED: [default_credential] the published admin/password pair is valid: admin still accepts the published
password.`, prints `public port 443 is NOT published: the proxy was recreated without the 443 overlay` if it had been
published, and `docker compose ... port proxy 8443` exits non-zero (`ADR-0021` row 6).

**11. The public probes** (`ADR-0021` rows 2 to 5), from a machine outside the host:
```
curl -sS -o /dev/null -w '%{http_code} %{ssl_verify_result}\n' https://<name>/login
curl -sSI https://<name>/login | grep -i '^strict-transport-security: max-age=31536000'
curl -sS -D - -o /dev/null -H "Cookie: am_session=$(openssl rand -hex 16)" https://<name>/bff/v1/projects | grep -i '^set-cookie: am_session=;.*Secure'
echo | openssl s_client -connect <name>:443 -servername <name> 2>/dev/null | openssl x509 -noout -checkend 1209600
```
Expect: `200 0`; the HSTS header line (exit 0); the clearing `Set-Cookie` line carrying `Secure` (exit 0 — an inert
cookie draws `401` and a clearing cookie from the BFF route, the method of `EXPOSURE-REVIEW-01.md` `E-2`);
`Certificate will not expire` (exit 0). On the host: `docker compose ... port proxy 8443` prints the mapping
(`0.0.0.0:443`); with `ALPHA_PUBLISH_HTTPS=no`, or while the published pair is valid, it does not (row 6). **HSTS is a promise about the name for a
year (`max-age=31536000`, no `includeSubDomains`, no `preload`); turning TLS off again does not withdraw it.**

**12. Run the readiness command.** `infra/deploy/readiness.sh` — expect `readiness OK      tls` and
`readiness OK      plain-http` (§9).

### Renewal, and how it fails

The ACME service asks again every twelve hours (`certbot certonly --keep-until-expiring`): it renews when the
certificate is within thirty days of its end, and does nothing otherwise. The proxy picks up the new pair
within a minute, with no restart. **A failed renewal does not alert anyone** (`R-146k`): it is found by the check
that runs when somebody deploys or verifies — `verify-deployed.sh` exits 7 with `served-certificate: EXPIRING`
when fewer than **14 days** remain (the 14 is the architect's number; renewal starts at 30, so reaching 14 means
two weeks of failed renewals). To rehearse a renewal without spending the real endpoint's limits:
```
docker compose --env-file infra/deploy/env/alpha.env -f infra/deploy/compose.server.yml \
  -f infra/acme/compose.acme.yml exec acme certbot renew --dry-run --cert-name <name>
```
Expect (shape): `Congratulations, all simulated renewals succeeded`.

### The messages, and what each means

| from | line | meaning |
|---|---|---|
| `deploy.sh` | `REFUSED: ALPHA_CERT_NAME is set and this clone is missing files...` | a partial checkout; nothing was built |
| `deploy.sh` | `REFUSED: the TLS settings in <env> are not usable.` | the lines under it name each value; a setting without a name is refused, not ignored |
| `deploy.sh` | `REFUSED: the ACME client is not pinned` | step 1 |
| `deploy.sh` | `REFUSED: public port N is already in use...` | the host's nginx (or another stack) holds it, on any address of this host; step 4 |
| `deploy.sh` | `REFUSED: ALPHA_TRUSTED_PROXY_CIDRS is set in <env> and ALPHA_CERT_NAME is set too.` | the list is for a nginx in front of this stack and there is none now; remove it (step 5) |
| `deploy.sh` | `REFUSED: whether the certificate volume holds a pair could not be asked` | the acme image did not answer; nothing was started |
| `deploy.sh` | `REFUSED: [default_credential] the published admin/password pair is valid` | step 10: change the password; 443 stays closed until then (§3) |
| `deploy.sh` | `REFUSED: [default_credential_unanswered]` | the gate could not be asked; whether the pair is valid is not known (§3) |
| `deploy.sh` | `REFUSED: the proxy could not be recreated to withdraw public port 443` | the gate found the pair valid and docker would not recreate the proxy; close it by hand with the command printed |
| `verify-deployed.sh` | exit 8, `the published admin/password pair is valid` | the same finding, asked of the running stack; `PUBLIC PORT 443 IS PUBLISHED while the pair is valid` means withdraw it now |
| `verify-deployed.sh` | exit 7, `served-certificate: NOT SERVED` | no TLS answer from `proxy:8443`: the pair is not exported yet, or the proxy has not loaded it |
| `verify-deployed.sh` | exit 7, `STAGING CERTIFICATE` / `NOT TRUSTED` / `EXPIRING` | the kind, the chain or the margin; the line says which |
| `verify-deployed.sh` | exit 9, `the answer served on <name> lacks what the proxy's configuration promises` | `HARDEN-01`: HSTS, one of the four security headers, a version in `Server`, or a session cookie without `Secure` on the answer the proxy gives on the name; each finding is a line under it. `infra/deploy/reload-proxy.sh`, then verify again |
| `verify-deployed.sh` | exit 4, `the proxy's answer on <name> could not be read` / `no am_session cookie to judge` | the one request of the headers check got no HTTP answer, or no `401` with a cleared session cookie (the web tier is down?); nothing is claimed about the headers or the cookie |
| `enable-tls` | `TLS IS OFF.` | no usable pair on the volume; `docker compose logs acme` says why |
| `watch-certificate` | `the pair is not the cause` | nginx refused the configuration with and without the TLS block (an upstream restarting, usually); it retries |

### Turning it off, and what stays

Empty `ALPHA_CERT_NAME` **and remove the other TLS settings** (`deploy.sh` refuses them without a name), run
`infra/deploy/deploy.sh`, then remove the client that deploy leaves behind (the file list no longer names it, so
compose treats it as an orphan and leaves it running):
```
docker compose --env-file infra/deploy/env/alpha.env -f infra/deploy/compose.server.yml \
  -f infra/acme/compose.acme.yml rm -sf acme
```
Expect (shape): `Container <instance>-acme-1  Stopped` then `Removed`. Start the host's nginx again if it is to
terminate TLS. The volumes `<instance>-acme-state` (the account key and the lineages), `<instance>-certs` and
`<instance>-acme-webroot` stay; `down` never removes them, and `down --volumes` would — the account key with them.

### What this section does not do

* it has **not been run**: no certificate authority was contacted, no image was built, no host was touched;
* it does not resolve `infra/acme/client.pin` (step 1) or choose between a name under `sslip.io` and one of the
  owner's own (step 9) — both are the owner's;
* it does not run the restore paths for you: `reset.sh --restore` and `copy-serve.sh restore-db` close 443 after a
  restore that brings the seeded pair back (above), and what they print is §7's and §13's;
* it does not restart anything on a renewal: the proxy reloads on its own timer, so a renewal needs no right to
  touch another service.

---

## 7. `R-4` — the wipe, and who ends the pilot

> **`R-4`** | real client documents | **Permitted, wiped at the end of the pilot.**

`infra/deploy/reset.sh` is that commitment. It **dumps and verifies the dump before it
drops anything**, refuses without an explicit flag, and refuses if the database and bucket
you typed are not the ones the environment configures — so a stale environment cannot point
it at another instance.

```
# rehearse — touches nothing
infra/deploy/reset.sh --database <db> --bucket <bucket> --dry-run

# do it
infra/deploy/reset.sh --database <db> --bucket <bucket> --yes-destroy-everything
```

### Who runs it

**The owner, personally — `R-42`.** He runs the command on the server himself and decides
the fate of the dump the mechanism takes before deleting.

**Recorded as his decision and not as a role**, which is `R-42`'s own instruction: this
programme has no role vocabulary, `T-6` forbids inventing one here, and writing it as a role
would invent the thing the ruling avoided. In practice it is also the person who holds root
on the `R-1` host and wrote `alpha.env`, because the command must be typed with the database
and bucket names that file configures.

### What "the end of the pilot" is, operationally

**Answered by `R-41`: the pilot ends when the owner says so, by explicit instruction.**
No date, no deadline and no observable event — not *"the last expert filed their report"*,
not the acceptance of a named checkpoint. The wipe runs when he says it runs.

**This runbook argued the other way and was overruled, which is worth recording rather than
quietly deleting.** It held that the trigger must be a single observable event, because *"a
wipe that depends on somebody's judgment of whether the pilot has ended is a wipe that does
not happen"*. That reasoning was put to the owner and he took the other side, with the
caveat stated and accepted: there is no automatic end, so *"the pilot is over"* is a
sentence **only he can make true**. The risk the old text named did not disappear; it became
his, knowingly.

**One consequence, because the old text made it a gate.** It said no real client document
should be on the host until the trigger was written down. It is written down now, so that
gate is satisfied and no longer holds documents off the host.

`PA-01` remains a different event. The roadmap's §6 runs `reset.sh` once **after** `PA-01`
and **before** real documents arrive, to clear the pilot corpus; the `R-4` wipe is the later
one, at the end.

### The credentials, which the wipe does **not** touch — `R-26`

`reset.sh` destroys documents and rows. It does **not** invalidate credentials anybody was
given during the pilot, and until `W39-REVOKE` nothing could: a credential is a signed
statement with an expiry, so the only lever was rotating `AUDITMANAGER_API_TOKEN` — which
signs out the operator too and needs a redeploy.

There is now a command, and it publishes no HTTP operation:

**They run inside the `api` image, and that is not a style.** §1 promises this host bash,
docker, curl, sed and git and explicitly **no `.venv`**. A bare `PYTHONPATH=src python -m
auditmanager.access.revoke` on such a host dies before it does anything:

```
PYTHONPATH=src /usr/bin/python3 -m auditmanager.access.revoke --everyone
#   File ".../src/auditmanager/access/ports.py", line 52, in <module>
#     from sqlalchemy.orm import Session
# ModuleNotFoundError: No module named 'sqlalchemy'
```

The image has the interpreter and the dependencies, and `readiness.sh` already runs the same
package this way. Set this once and the three commands below are one line each:

```
DC="docker compose --env-file infra/deploy/env/alpha.env --file infra/deploy/compose.server.yml"
```

```
# end the pilot for everybody -- everyone signs in again, including you
$DC run --rm --no-deps -T --entrypoint python api -m auditmanager.access.revoke --everyone

# or one account
$DC run --rm --no-deps -T --entrypoint python api -m auditmanager.access.revoke --login <login>
```

*(`Y-C`, 2026-09-29. These three commands were written as bare `PYTHONPATH=src python` by
`W39-REVOKE` and `W40-LIMIT`, and the deployment's own migration log tells the operator to
run two of them. `R-42` makes it worse rather than milder: the person at that keyboard is
now, by ruling, the owner himself on the server. A development host's `PATH` carries a
`.venv` and hides this, which is why the reproduction above uses `/usr/bin/python3`
deliberately.)*

It raises `app_user.token_epoch`, which every credential carries a copy of, so **every
credential ever minted for those accounts stops being accepted at once** — in every
process, across a restart, without a redeploy. Exit `0` revoked something, **`1` was
well-formed and matched nothing** (a mistyped `--login` looks like this and not like
success), `2` could not reach the database. Run it with no argument and it does nothing and
exits `2`: neither "revoke everybody" nor "revoke nobody" is a defensible default.

Run it **after** `reset.sh`, in the same sitting. The two answer different halves of
*"the pilot has ended"*: one takes the documents away, the other takes the access away, and
a wipe that leaves live credentials behind has ended the pilot only for the data.

**The wipe now takes a third thing with it: the session register** (`Y8`). `R-51` put each
signed-in reviewer's API credential in `register.json` on `<instance>-web-sessions`, and
until 2026-09-29 `reset.sh` could not reach that volume and did not try — driven to the end
on a deployed stack, the file came through the wipe **byte-identical**, `md5sum` unchanged,
with three complete reviewer credentials in it. They were inert only because the account row
was gone, and a restore is exactly what brings that row back. `reset.sh
--yes-destroy-everything` now clears the register in the same movement as the database and
the bucket, **before** it drops anything, so a stack that cannot clear it refuses with the
documents still whole. The `web` container is stopped for that moment and started again,
because the register is a file *and* a map in that process.

### A restore is not a neutral act — `R-52`

**Restoring one of this script's own dumps rolls credential state back with everything
else, and that needed a ruling.** The dump is the whole database with no `--exclude-table`
and the restore is `pg_restore --clean --if-exists`, so `app_user` comes back entire —
`password_hash`, `token_epoch` **and** `is_default_credential`. Driven by `W47-JUDGE-X`
against a built API: revoke, then restore a dump taken before it, and **the revoked
credential answers `200` again**. Worse, and unbounded: restore any dump taken before the
forced password change and the deployment is back on the shipped `admin`/`password`,
silently, by a documented command. A revoked *token* at least expires within the hour; a
password does not expire at all.

**So `--restore` does two more things, after the rows are back:**

1. it raises `token_epoch` on **every** account — every restored credential is dead, and
   everyone signs in again once. You included;
2. it runs `auditmanager.access.check` and **names, by login, any account that came back on
   its default password**, and tells you what to do about it: sign in as that login and
   change the password. A default credential reaches the sign-in and the change and nothing
   else (`R-50`), so that is the only thing it can do and it is enough.
3. **since `PROD-02`, it asks the deploy's own gate and closes the door** — the narrower question,
   `access.check --gate`, *is the published `admin` / `password` pair valid again?* (`R-146i`, `R-146s`). If it is, or
   if that could not be told, it recreates **only the proxy** without the 443 overlay and says so; every service keeps
   running on loopback, and the site is unreachable from outside until an administrator changes the password through
   the loopback port. A restore never opens 443; the next deploy does, after a clean gate. Its exit status stays `0`
   for a completed restore — **except `5`: the restore completed and public port 443 could not be withdrawn**; close it
   with the `docker compose ... up -d --force-recreate --no-deps proxy` line the screen prints.

**It reports; it does not refuse**, and that is the owner's explicit choice rather than an
oversight. A restore is run **after a failure**, which is the moment when a script that
refuses does the most damage — `D-72` is the wave where a correct fail-closed repair took
this stand down for a day. If either command cannot reach the database, the restore still
completes and the screen carries a marked block naming the exact command for you to run.

Two more things an operator should know about it:

* **a password change revokes too.** Whoever changes their password through the application
  invalidates every credential that account held, by the same mechanism and in the same
  write. That is not a side effect to work around; it is what a password change means here;
* **deploying migration `0007_credential_epoch` is itself a global revocation.** Credentials
  minted before it carry no epoch and are refused. Everyone signs in again, once, at the
  upgrade. The migration says so in its own log line.

`$DC run --rm --no-deps -T --entrypoint python api -m auditmanager.access.check` is the
other half of the same operator view: it names the accounts still holding the password this
system seeded them with, without anybody signing in — and, since `W40-LIMIT`, every account
that is shut out of signing in right now. Exit `0` none are, `1` at least one is, `2` it
could not read. `reset.sh --restore` runs this for you and prints what it found (below).

### When somebody cannot sign in and the password is right — `R-26`

`W40-LIMIT` added the other two halves of `R-26`, and **they are two different things**:

* a **rate limit** — consecutive recent failed sign-ins are counted per account. It slows a
  guesser and recovers on its own. Nothing to operate;
* a **lockout** — when five consecutive recent attempts have been refused, that account is
  shut for **five minutes**, during which its password is not consulted at all, **including
  the right one**. The screen says so in general terms and never says it about the account
  in front of it, because that would tell anybody who can type a login which accounts exist
  and which are under attack.

**A lockout can be aimed.** Anybody who can reach `POST /api/v1/auth/token` can shut a named
account by typing five wrong passwords at it, and the seeded account's login — `admin` — is
published in a migration and in this runbook. What bounds it:

* it expires by itself, and the first attempt after it expires starts a fresh allowance
  rather than re-tripping;
* **credentials already minted are not touched.** Somebody who is signed in stays signed in
  and keeps working; only *getting a new credential* is refused. An unauthenticated caller
  cannot sign anybody out;
* a **password change clears it**, so a reviewer who is still holding a live credential can
  open their own door through the application;
* and there is a command, with no HTTP operation behind it:

```
# let one account sign in again, immediately
$DC run --rm --no-deps -T --entrypoint python api -m auditmanager.access.unlock --login <login>

# or everybody, when you do not yet know what is shut
$DC run --rm --no-deps -T --entrypoint python api -m auditmanager.access.unlock --everyone
```

Exit `0` released something, **`1` released nothing** — and the printed line says whether
that was because no such account exists or because nothing was shut, which is the
difference between a typo and a no-op. `2` could not reach the database. Run it bare and it
does nothing and exits `2`.

It releases a brake and **nothing else**: no password changes, no credential is issued, and
**a revocation is not undone**. `unlock` and `revoke` are opposite-looking commands over
different columns, and an account that was deliberately revoked stays revoked.

If the same account is shut again within minutes of an unlock, that is not a defect: it is
somebody still guessing, and the deployment log carries one `sign-in blocked` warning per
cooling-off period naming the account and the instant. At that point the lever is the proxy,
not this command.

**Deploying migration `0008_sign_in_throttle` locks nobody out** — every existing account
starts with a clean count and no block. That is the opposite of what deploying
`0007_credential_epoch` does, and the two land close enough together to be worth saying
separately.

### What an operator checks afterwards — by **writing**, never by reading

`W18-OPS` established this the hard way: a restored instance that **reads** perfectly can
be **broken for writing**. Three S3 user-metadata keys were lost by the old restore; the
instance read back byte-identical and then answered **409** to a re-upload. A check that
only reads would have passed on all three.

So, after a wipe:

1. the app comes back **empty** — no project, no document, no run;
2. **create a project and upload a PDF through the browser.** It must answer **201**, and
   its bytes must come back. That is the write that proves the instance is usable and not
   merely quiet;
3. `infra/deploy/verify-deployed.sh` still exits 0 — the wipe took the data, not the code.

And after a **restore** of one of its dumps, the same discipline with one more step: read
the object back byte-identical **and then re-upload**. A `409` there is the `D-17` failure
exactly.

One thing to know before reading the rehearsal's screen: **the total counts base tables
only.** It once counted a view (`finding_current_verdict`) whose rows are counted elsewhere
and so over-reported; `D-39` closed that on 2026-09-21, and the query now sums
`FILTER (WHERE kind = 'BASE TABLE')` and says `base tables` on the line
(`infra/deploy/reset.sh:429-431`). **This paragraph said the opposite for eight days**, and
both of wave 47's judges caught it — a runbook that warns about a defect its own tree has
fixed teaches an operator to distrust a correct number.

---

## 8. `PA-01` criteria 1 and 2 — what is still open, and why it is not the software

Quoted from `ALPHA_ROADMAP.md` §5:

> 1. `deploy.sh` brings the stack up from a clean clone on a machine that has never run it,
>    and the schema the running app serves conforms to the frozen
>    `contracts/api/v1/openapi.json` — the same check the gate runs, re-run against the
>    deployed process rather than against a build artifact;
> 2. the browser reaches the app over TLS, and a request carrying no token is refused with
>    `authentication_required` **from the application**, not by the proxy — shown for an
>    operation of each kind, so the dependency is proved to be in front of all twelve rather
>    than in front of the one that was tried;

Both stay **cannot be established**, and both for the same reason: **`R-1` alone** — there
is no host that has never run this, and there is no host name, certificate or DNS record.
Criterion 2's **second** clause is driven and holds today.

**Nothing in this repository is the reason they stay open.** Criterion 1 needs a machine.
Criterion 2 needs a certificate, and §6 is the whole of what this repository can do about
it in advance: set the host's name, rehearse against the authority's test endpoint, and the
stack obtains the certificate itself and the browser reaches the app over TLS.

---

## 9. Is it safe to publish? — the readiness command

```
infra/deploy/readiness.sh
```

**`R-46`, ruled 2026-09-25**: this command **reports and registers; it does not block a
deploy.** `deploy.sh` never calls it and nothing in this repository reads its exit status.
That reads backwards on a first pass, and the owner chose it deliberately, with a precedent
in hand: `D-72`'s repair was correct and fail-closed, and it took the owner's own stand down
for a day, because a configuration that had always been wrong stopped being survivable the
moment the code got strict. A readiness check that refuses is the same shape.

So its output is not a green light. It is **a corpus of problems**, each printed as one line
you can grep, and each one is a register row that needs the owner's ruling:

```
readiness OK      <check>            <what was found>
readiness FINDING <check>            <what was found -- a register row>
readiness UNKNOWN <check>            <the check could not be answered -- never read as OK>
```

Six checks, none of them re-deriving a question this tree already answers elsewhere:

| check | what it asks | reuses |
|---|---|---|
| `default-credential` | step 5 — is any account still on the password this system seeded it with? **The wider question** (default mode, no `--gate`): it also lists an administrator's temporary password, which the deploy's gate (§3) only warns about | `src/auditmanager/access/check.py`'s own stable sentinels, run inside the deployed api image the way `deploy.sh`'s `migrations-at-head` guard runs `shared.db.check` |
| `tls` | what certificate does the proxy's TLS listener serve, and is it production, trusted, for this name and good for 14 more days? (`PROD-01-TLS-ACME-01`; it used to ask whether a pair was on disk) | `infra/acme/check-served.sh`, run in a one-off container of the acme image against `proxy:8443` — the same question `verify-deployed.sh` enforces; no name set, or the test endpoint selected, are findings |
| `plain-http` | is the plain application port off this host, and, with a name, does port 80 answer an application path with a redirect to HTTPS and nothing else? | `ALPHA_BIND_ADDRESS` (`D-49`); with a name, a `curl` of the challenge listener (`R-146s`); without one, the old reading: nothing in this tree closes plain HTTP once it is published |
| `provider-mode` | is `AUDITMANAGER_PROVIDER_MODE` a real provider, and does it have the credential it needs? | `auditmanager.bootstrap.settings.load()` — the composition root's own validation, the thing that actually decides whether `api` starts |
| `cost-ceiling` | what does `AUDITMANAGER_RUN_COST_CEILING_USD` resolve to? | the same `load()` call |
| `off-host-backup` | is there a destination off this host for `reset.sh`'s dumps? | nothing — §5 above already says this is not automated anywhere in this tree, so this check always finds it open, honestly, rather than inventing a name for a mechanism that does not exist |

`default-credential` needs `docker`, because the question is about the *deployed* database;
`provider-mode` and `cost-ceiling` need this repository's own `.venv` (`make bootstrap`),
because they run the real `AppSettings.load()` rather than a second copy of its rules. Either
missing is reported `UNKNOWN`, never guessed at as `OK` — the one thing this command must
never do is claim to have checked something it could not reach.

`tests/integration/composition/test_readiness_command.py` drives every check to both an `OK`
and a `FINDING`, and — for the five that need no running stack — proves each is doing its own
job by deleting its marked block and showing the finding disappears, the same mutation
discipline `test_deploy_script_refusals.py` already holds `deploy.sh`'s guards to.

---

## 10. When it goes wrong

| What you see | What it is |
|---|---|
| **502 on everything**, containers healthy | the proxy holds a dead upstream after a rebuild. `infra/deploy/reload-proxy.sh`. Intermittent, so it is a step and not a diagnosis (`D-27`) |
| `deploy.sh` dies telling you to **fix `nginx.conf`** | `D-38`: when `compose up` fails, the reload is reached before the guard that would name the real cause, and it accuses a file that is fine. Read `docker compose ... logs` for the service that did not come up. **`nginx.conf` is almost certainly not your problem** |
| a mount arrives **empty** | `D-37`: a `-v` source is resolved by the **daemon**, not the shell, and docker **invents an empty directory rather than refusing**. A relative source is a *volume name*. This host's docker is a snap build whose private `/tmp` is not the shell's `/tmp` — `W26-HOST` hit it again from a third direction: `docker compose --env-file /tmp/...` answered *"couldn't find env file"* for a file that was plainly there. **Keep deployment files inside the clone** |
| `docker compose config` to debug | it prints **every** value in clear, including `AUDITMANAGER_API_TOKEN`, both passwords, and — measured on Compose v5.3.1, contrary to what `provider.env.example` used to say — the **provider credential**, which `config` resolves out of `env_file:`. Use `--no-env-resolution`, and treat the output as a secret either way. The TLS private key is the one thing it cannot print: the overlay reaches it through a bind mount, so what appears is the path |
| the app answers `authentication_required` to everything | the token. `T-6` is fail-closed by design |
| `[session-register] could not write /var/lib/auditmanager/sessions/register.json (…)` in the `web` container's log | `R-51`'s volume is not writable — a restored volume owned by `root`, or a full disk. **The stand keeps serving and nobody is signed out**: the sessions are live in the container's memory either way, and refusing a sign-in over a full disk would take the stand down for a reason no reviewer can act on. What it means is that **the next deploy will sign everyone out**. Check the volume: `docker compose … exec web ls -la /var/lib/auditmanager/sessions`, and `df -h` |
| `[session-register] AUDITMANAGER_SESSION_STORE is not set` | this stack is running the pre-wave-47 behaviour — sessions in memory only, and every deploy is a logout. `compose.server.yml` sets that variable; a stand that does not have it is not this compose file |
| runs stay **`queued`**, «Исполнители» shows nobody online | the `worker` service is down, draining or has intake off (`R-105`). `docker compose … ps worker`, `docker compose … logs worker`; a worker with intake off is switched back by an administrator («Разрешить») — see §12 |
| `deploy.sh` refuses with *EXECUTION_ROLE* in the message | `execution-role-declared`: `compose.server.yml` must set `EXECUTION_ROLE: api` on `api` and `EXECUTION_ROLE: worker` on `worker`, literally, and never in `alpha.env` (§12) |

---

## 11. The inbound bundle key — transport to the stand (`W54-TRANSPORT-01`)

**What it is for.** The corpus reaches the stand as a verified bundle, sent through a second
SSH key whose forced command is `infra/deploy/receive-bundle.sh` (`R-104`; `W54-PLAN.md` §3.5).
There is no interactive stand shell. The account that key logs into can run `docker`, which
is root-equivalent, so **the forced command is the boundary**. This section covers the order
of operations. The mechanism and the guard list are in the scripts' headers and in
`tests/integration/composition/test_bundle_transport_refusals.py`.

**Each use is a separate act that needs the owner's direct instruction** (`CD-3`). The bundle
import is P4 (`W55A-STAND-IMPORT-01`), and it follows `CD-16`'s sequence as `W54-PLAN.md` §3.5
and §3.10 give it. This section does not restate that sequence. It says how each verb is
called and what a refusal means.

### Installing it (the owner, once)

1. Create the staging directory **outside the checkout**. `deploy-auto` refuses a checkout
   that has untracked files. The directory must be owned by the key's account and must not
   be group- or world-writable, and it must be on a filesystem the Docker daemon can
   bind-mount (`D-37`):

   ```
   install -d -m 700 -o <account> /srv/auditmanager-bundles
   ```

   `deploy.sh` reads the import lock in this directory and the copy record in the copy
   directory (§13) before it builds anything, as the account deploy-auto logs into. If that
   is not the keys' account, it must still be able to **search** both directories: make it
   the same account, or give both directories a group that account is in and mode `710`
   (search, no read, no write). Otherwise every deploy refuses with `stand_dir_unsearchable`
   (`W54-JUDGE-A` F1), because a record or a held lock it cannot see would read as none.

2. Add one line to that account's `authorized_keys`. `restrict` turns off the pty and all
   forwarding, and `from=` names this development host:

   ```
   restrict,from="<development host>",command="BUNDLE_STAGING=/srv/auditmanager-bundles /srv/auditmanager/infra/deploy/receive-bundle.sh" ssh-ed25519 AAAA... w54-inbound
   ```

   If the defaults do not fit, the same `command=` string can set other variables:
   `STAND_COPY_RECORD`, the copy record kept by the copy key (default
   `/srv/auditmanager-copy/record.json`); `ALPHA_ENV_FILE`; `BUNDLE_MAX_BYTES`, the largest
   size accepted (default 12 GiB); and `BUNDLE_STAGING_MARGIN_BYTES`, the free space kept
   beyond twice the size (default 2 GiB). The client cannot set any of them. `LC_ALL` is
   pinned inside the script, so an `LC_*` variable admitted by `AcceptEnv` changes nothing.

3. Check the install with `status`. It prints the SHA-256 of the installed script and of its
   library. Compare both with the published tree.

**Rollback** means the owner removes that `authorized_keys` line (`W54-PLAN.md` §3.10).
Nothing else on the stand depends on the key.

### The verbs

`<KEY>` is the bundle directory's name, `<content_key>+<bundle digest>`. The bundle digest is
the SHA-256 of the bundle's `SHA256SUMS`. The exact grammar is in
`infra/deploy/lib/forced-command.sh`.

| Verb | Called as | What it does |
|---|---|---|
| `receive <KEY> <size>` | `infra/deploy/push-bundle.sh --host <user@stand> --identity <key> <bundle dir>` | refuses on size, existing bundle, a running receive, a running copy-key verb (it holds `copy.lock` from here to its end, because it may rewrite the record) or free space **before reading a byte**; then reads exactly `<size>` bytes, lists the tar before extracting it, and keeps the tree only if `SHA256SUMS` matches the name, the files are exactly the listed ones and every file re-hashes. A refusal removes `incoming/<KEY>/` and nothing else |
| `status` | `ssh -i <key> -o IdentitiesOnly=yes <user@stand> status` | read-only: staging and its free bytes, the import lock, each bundle and its import state with the log tail, and the script's SHA-256 |
| `import <KEY>` | `ssh … import <KEY>` | takes the import lock **first**, then reads the copy record under the copy key's `copy.lock` and turns it into an import record, then starts `python -m auditmanager.norms.bundle import /bundles/<KEY> --copy-record …` **detached** in a one-shot `api` container, under the import lock. Re-run it until `status` shows `import: exited 0`. A second `import`, `report` or `requeue`, and the copy key's `resume`, are refused while it runs; it is refused while `resume` (which holds the same lock) or any other copy-key verb runs |
| `report <KEY>` | `ssh … report <KEY>` | the module's `report`, run synchronously. Its exit status is passed on, and 0 means a full match. Its output is kept as `logs/<KEY>.report`; when it exits 0 **and** the last `import` of the same bundle exited 0, it then removes `bundles/<KEY>/objects/` (below) |
| `requeue <KEY>` | `ssh … requeue <KEY>` | the module's `requeue` of that bundle's poisoned admissions. Run `import` again afterwards |

`import`, `report` and `requeue` each run **one fixed command**. The bundle is mounted
read-only, and the copy record is mounted read-only for `import` and `report`. The only thing
the client supplies is the validated `<KEY>`.

### The importer and `report` (`W54-BUNDLE-01`)

The module behind `import`, `report` and `requeue` is `python -m auditmanager.norms.bundle`
(`src/auditmanager/norms/README.md`). The bundle it reads was written on this host by
`… bundle export` and checked with `… bundle verify` before `push-bundle.sh` sent it.

**`import`** works in `W54-PLAN.md` §3.5's order and can be re-run until it exits 0:

1. it verifies the bundle (name, `SHA256SUMS`, every file, the manifest), that the manifest
   declares a complete build, the database at the code's migration head, and the copy record:
   an open attested `import` copy inside 12 h of its quiesce, or an open unexpired
   `test_data_waiver` whose `real_data_marker` is `false`; in both cases the fingerprint the
   importer recomputes must equal the record's. It refuses a `rejected` manifest Blob
   (`D-143`), a snapshot conflict, and — on the first run — a manifest Blob already held by a
   client row;
2. it admits every custody slot and dispatches until idle. An admission still `pending`
   (a store outage: due again in 30 s … 2 h) or `poisoned` (five failed tries) ends the run
   with exit **75**: nothing else was written, the bundle is kept. Run `import` again later;
   for poisoned admissions run `requeue <KEY>` first;
3. in one transaction it inserts the rows with the ids the promotion database minted and
   publishes the bindings; then it loads the build; then it runs the same comparison as
   `report` and exits 0 only on a full match (1 otherwise).

`status` shows the run's exit in `import: exited <n>` and the last log lines.

| Exit | Meaning | What to do |
|---|---|---|
| 0 | imported and reported a full match | `report <KEY>` (P4 step 5), then `resume <STAMP>` with the copy key |
| 1 | imported, but the report differs | read `logs/<KEY>.import.log`; do not `resume` or designate; the owner decides |
| 2 | refused: `bundle: REFUSED [<reason>]` in the log | the reason names the rule. `copy_record_*`, `waiver_after_real_data`, `fingerprint_drifted`: open a new copy or waiver with the copy key. `build_absent`, `bundle_*`, `manifest_invalid`: export the bundle again here. `manifest_blob_rejected`, `manifest_blob_held_outside_custody`, `snapshot_conflict`: an owner decision. `blob_store_unavailable`: the deployed image lacks the storage export (`W54-BUNDLE-01` §5) |
| 75 | not finished; the bundle is kept | `import <KEY>` again later; `requeue <KEY>` first if `poisoned` is non-zero |

**`report`** is read-only. It prints, and compares with the manifest: the content key, the
recomputed row digest, documents, paragraphs, unreliable paragraphs, chunks, windows and the
build digest; admissions confirmed, pending and poisoned; the binding count and digest; the
manifest Blobs' count, bytes, `available` and `rejected` counts. It compares the client side
with the open copy record: the record still open, every client table's rows and digest, the
fingerprint, and the `rejected` Blobs outside the manifest. The other Blobs' count and bytes
are printed, not compared. Exit 0 only on a full match.

**The objects go after the match (§3.5 step 5).** The container cannot delete through its
read-only mount, so the inbound key's `report` verb does it: when the report exits 0 and
`logs/<KEY>.import.exit` holds 0, it removes `bundles/<KEY>/objects/` and nothing else, keeps
the manifest, `SHA256SUMS`, rows and build, and writes `logs/<KEY>.report` and
`logs/<KEY>.discarded`. A later `import` of the same bundle is then a no-op that needs no
object; `import` refuses `objects_discarded` if anything was still unconfirmed.

### Reading a refusal

Every refusal exits **3** and names its guard: `receive-bundle.sh: REFUSED [<guard>]: <reason>`.
`push-bundle.sh` passes the stand's exit status and message on. It refuses with its own guards
(`push-bundle.sh: REFUSED [...]`) before anything leaves this host. It re-hashes every file
first.

| Guard | What to do |
|---|---|
| `command-*`, `verb-known`, `verb-grammar` | the command was not one of the five verbs, or its arguments do not fit the grammar. Nothing ran |
| `staging-*` | the staging directory is missing or misconfigured. This is the owner's install, step 1 |
| `size-within-limit`, `staging-has-room` | the bundle is too large, or staging lacks twice its size plus the margin. Nothing was read |
| `bundle-not-received` | this `<KEY>` is already on the stand. Check `status`. A re-send needs the owner to remove the old tree |
| `receive-lock-free`, `import-lock-free` | another receive or import is running, or (`import-lock-free` on `import`) the copy key's `resume`. Wait and check `status`. A hung importer holding the lock is an owner act |
| `copy-lock-free` | a copy-key verb holds `copy.lock` beside the record (or this account cannot open it), so the record cannot be read and rewritten now. Nothing was read or started. Check the copy key's `status`; run it again once that verb has exited |
| `tar-*`, `sums-*`, `files-match-sums` | the bytes that arrived are not the bundle that was named. They were removed, inside staging only. Send it again |
| `bundle-received` | `import`, `report` or `requeue` named a bundle that was never received |
| `env-file-present`, `compose-file-present` | the deployed checkout is incomplete |
| `copy-record-present` | there is no copy record: neither the one-off copy (`R-88`) nor, while the stand holds only test data, a test-data waiver (`R-110`) has been opened. §13 |
| `copy-record-readable` | the record is not one the copy key wrote (`record_version 1`, its canonical layout). Nothing was read. The owner inspects it |
| `copy-record-open`, `copy-record-attested` | the record is closed, or open and not yet attested. Open and attest one with the copy key (§13) |
| `waiver-before-real-data` | a `test_data_waiver` after the `real_data` marker: a full copy has been attested, so `R-88` and `R-93` apply in full and only an attested copy admits an import |
| `copy-record-in-window` | the copy was quiesced more than 12 h ago, or the waiver has expired. `resume` it with the copy key and open a new one |
| `writers-still-stopped` | `web`, `api` or `worker` runs again (or docker could not say), so the database is not quiesced. `resume`, then open a new copy or waiver |

### What it does not do

* It does not delete a staged bundle as a whole. After a matched `report` that follows a
  successful `import`, the `report` verb removes `bundles/<KEY>/objects/` (above); the rest of
  the bundle stays under `bundles/<KEY>/` until the owner removes it.
* It does not open, attest or close the copy record; that is the copy key (§13). It does
  read it before an `import` (the guards above), and a `receive` or an `import` under an open
  record makes it an import record, as `W54-PLAN.md` §3.5 says.
* It does not take part in a deploy. `deploy.sh` refuses while the import lock is held
  (`stand_import_locked`), while an open record is an import record (`stand_import_open`),
  and when it cannot search the staging or the copy directory (`stand_dir_unsearchable`,
  step 1 above); §13 lists the other typed words.

---

## 12. The worker service — operations (`W54-WORKER-01`, `R-105`)

From W54 the API process answers requests and **does not execute runs**. The `worker`
service in `compose.server.yml` does: the same image, started as
`python -m auditmanager.workers serve`, with the API's environment **except
`AUDITMANAGER_API_TOKEN`** (it refuses to start if that is set) plus `env/provider.env`. No
port, no session volume. `infra/deploy/README.md` "The worker service" has the full table.

**What the owner must know before the first W54 deploy.**

* `deploy.sh` brings the new `worker` service up with the rest and now waits for its health
  check. It refuses (`execution-role-declared`) a compose file whose `api` or `worker` lacks
  the literal `EXECUTION_ROLE:` line. Nothing is added to `alpha.env`: the role is never one
  of its fifteen names.
* A deploy that recreates the worker sends it `SIGTERM`: no new claim, and the run in flight
  gets up to 270 s to finish (`stop_grace_period` 300 s). A deploy during a long live run can
  therefore take up to five minutes longer; pausing dispatch first («Очередь» → pause) and
  waiting for the queue to empty avoids that.
* `reset.sh` stops the worker before it drops or restores the schema and starts it again
  afterwards; a restarted worker registers a new identity.

**Day-to-day.**

| Task | How |
|---|---|
| is a worker online? | «Исполнители», or `GET /api/v1/execution/workers` (any role): `online` < 90 s since the last heartbeat, `stale` < 600 s, then `offline` |
| stop one worker taking new runs, keep its current one | «Не брать новые» (administrator; `PUT /execution/workers/{worker_id}/intake` `{"enabled": false}`). «Разрешить» undoes it |
| stop all dispatch | the existing pause on «Очередь» (`setExecutionPaused`) |
| restart the worker | `docker compose --env-file infra/deploy/env/alpha.env -f infra/deploy/compose.server.yml restart worker` — it drains first; the old identity goes `stale`, then `offline` |
| how many runs one worker executes at once | `AUDITMANAGER_WORKER_SLOTS` in `alpha.env`, a whole number from 1 to 16; absent or `1` is one run at a time (the rollback). Anything else stops the worker at start with `refusing to start: AUDITMANAGER_WORKER_SLOTS is …`; it is never clamped to 1. Restart `worker` for a change to take effect. Each slot adds two database connections to the worker's pool. One executor connection has at most **one** active run whatever the number: a queued run for a busy connection waits and holds no slot, and the next queued run for a free connection runs. Runs without a connection (`AUDITMANAGER_PROVIDER_SOURCE=environment`) are not limited |
| a worker was killed mid-run | nothing to do: its lease expires within 60 s and either process fences it — the run resumes when no provider effect can have spent (every recorded call, D-150), otherwise it fails as `provider_outcome_unknown` |
| `worker LISTEN connection … was lost` in its log | the database connection that delivers wake-ups dropped. The worker keeps polling every 5 s and reconnects by itself; runs are picked up at most 5 s later meanwhile |

**Rollback.** Migrations `0018`/`0019` refuse downgrade. A forward fix may set
`EXECUTION_ROLE: all` on `api` and remove the `worker` service — W53's in-process execution —
and `deploy.sh` accepts exactly that shape (`W54-PLAN.md` §3.10).

---

## 13. The copy key — the one-off copy, the test-data waiver and the way back (`W54-STAND-COPY-01`)

**What it is for.** `R-88` and `R-93` require a one-off copy of the stand — a quiesced
PostgreSQL dump and an inventory of the bucket, restored and checked on the development host —
before the corpus import and before every `origin/main` publication that migrates the stand,
until the beta backup wave. `R-110` makes that conditional: **while the stand holds only
generated test data (`R-109`), no copy is taken.** Publications deploy as before, and the
corpus import runs under a *test-data waiver* instead. A copy is taken immediately before the
first upload of real client data; from then on `R-88` and `R-93` apply in full.

The copy key is a second owner-installed SSH key whose forced command is
`infra/deploy/copy-serve.sh`. As with the inbound key (§11), the account can run `docker`, so
**the forced command is the boundary**. The verbs, guards and record layout are in the
script's header and in `tests/integration/composition/test_stand_copy_refusals.py`. The
record's schema is in `docs/program/W54-STAND-COPY-01.md` §3.

### Installing it (the owner, once — deferred under `R-110` to the first real upload)

The script is installed **apart from the checkout**, so that the candidate's script can serve
a stand whose checkout is still the older, deployed tree (`W54-PLAN.md` §3.10, P2 bootstrap).

1. Create the copy directory outside the checkout, owned by the key's account, mode 700:

   ```
   install -d -m 700 -o <account> /srv/auditmanager-copy
   ```

2. Extract the **five** files from the candidate's git objects (not from a working tree), and
   compare each SHA-256 with the gate record of that candidate:

   ```
   install -d -m 755 /srv/auditmanager/copy-serve/lib
   git -C /srv/auditmanager fetch origin
   for f in copy-serve.sh capacity-probe.sh apply-grants.sh lib/forced-command.sh lib/proxy-listeners.sh; do
       git -C /srv/auditmanager show "<candidate sha>:infra/deploy/$f" > "/srv/auditmanager/copy-serve/$f"
       sha256sum "/srv/auditmanager/copy-serve/$f"
   done
   chmod 755 /srv/auditmanager/copy-serve/copy-serve.sh /srv/auditmanager/copy-serve/capacity-probe.sh \
             /srv/auditmanager/copy-serve/apply-grants.sh
   ```

   **The fifth file is new (`PROD-04`), and it sits beside `copy-serve.sh`, not in `lib/`.** A dump carries no database
   privileges (`pg_dump --no-owner --no-privileges`) and `restore-db` drops and recreates schema `public`, so after the
   restore the application role has no rights at all; `apply-grants.sh` gives them back, right after the restore and
   before anything connects as that role. Without it, or with the second password unset in the deployed checkout's
   `alpha.env`, `restore-db` refuses (`grants-script-present`, `app-db-role-configured`) **before it stops or restores
   anything**. **A copy key installed before `PROD-04` must repeat this step**; `status` prints `grants: <digest>`
   (or `grants: absent`).

   **The fourth file is new (`PROD-02`).** `restore-db` ends by asking the credential gate and closing public port
   443 if the seeded pair came back (below); that rule is written once, in `lib/proxy-listeners.sh`, and shared with
   `deploy.sh`. Without it `restore-db` refuses (`listeners-library-present`) **before it stops or restores
   anything**; every other verb is unaffected, and `status` prints `listeners: absent`. **A copy key installed before
   `PROD-02` must repeat this step**, as it must after any change to `copy-serve.sh`.

   `/srv/auditmanager/copy-serve/` is inside the checkout's directory, but every file there is
   untracked: add `copy-serve/` to the checkout's `.git/info/exclude`, or deploy-auto refuses
   the checkout as dirty. The owner may instead install it at `/srv/auditmanager-copy-serve/`;
   only the `command=` path below changes.

3. One line in that account's `authorized_keys`:

   ```
   restrict,from="<development host>",command="ALPHA_CHECKOUT=/srv/auditmanager STAND_COPY_DIR=/srv/auditmanager-copy /srv/auditmanager/copy-serve/copy-serve.sh" ssh-ed25519 AAAA... w54-copy
   ```

   The same string may set `ALPHA_ENV_FILE`, `BUNDLE_STAGING` (its `import.lock` is read),
   `STAND_COPY_MARGIN_BYTES` (default 2 GiB beyond the database's size) and
   `STAND_COPY_WINDOW_SECONDS` (default 43200, the importer's 12 h).

4. Check it with `status`: it prints the installed script's, library's, probe's, listeners' and grants script's SHA-256 and
   the deployed checkout's `HEAD`. A later publication that changes `copy-serve.sh` asks the
   owner to repeat step 2.

**Rollback** is the owner removing the key's line. `deploy.sh` still reads the record (below),
so a record left open keeps blocking deploys until it is resumed or the owner moves it aside.

### The verbs

Every verb is `ssh -i <copy key> -o IdentitiesOnly=yes <user@stand> <verb ...>`.
`<STAMP>` is `YYYYMMDDTHHMMSSZ`, printed by `dump-db` or `attest --test-data`.

| Verb | What it does |
|---|---|
| `capacity` | read-only: free disk of the Docker data root, staging and the copy directory, the MinIO volume's free space and size, available RAM, swap, load, `pg_database_size`, the bucket's object count and bytes, and `docker system df`. P4 needs staging ≥ bundle + dump + 2 GiB, and the Docker volumes ≥ objects + `db_growth_bytes` + 2 GiB |
| `dump-db` | opens a copy: writes the record first, then stops exactly the writers running (`web`, `api`, and `worker` when the deployed compose file has it), dumps PostgreSQL (`pg_dump --format=custom --no-owner --no-privileges`), checks the dump with `pg_restore --list`, and records the fingerprint, migration head and `rejected` Blob count. Refused while any record is open. Only the latest copy is kept |
| `inventory-s3 <STAMP>` | lists every object in the bucket (`key`, size, ETag) into the copy, while the writers are still stopped |
| `fetch <STAMP> db\|inventory\|record` | streams that file; `infra/deploy/pull-copy.sh` calls it |
| `attest <STAMP> <dump-sha256> <restore-report-sha256> publish <sha>\|import` | binds the dump's and the restore report's digests and a purpose. The dump is re-hashed. A first attestation, and an import attestation, also needs the writers still stopped and the copy younger than 12 h. Re-attesting a publication rebinds it to another SHA (a forward fix). An import record is never rebound to a publication. **The first attestation of a full copy writes the `real_data` marker** |
| `attest --test-data` | `R-110`: no copy. Stops the writers, takes the fingerprint and opens a `test_data_waiver` (an import record) that expires in 12 h. **Refused once the `real_data` marker exists** |
| `verify-objects <N> [<seed>]` | reads back a seeded sample of N `available` Blobs through the api image's storage adapter and compares each with its recorded size and SHA-256. P1's read-back at P2 is a technical MinIO check (`R-109`) |
| `restore-db <STAMP> <sha256>` | the owner's way back: checks the digest against the record and the file, stops every writer running again, reopens the record, restores the dump into a recreated `public` schema, compares the fingerprint, **then (`PROD-02`) raises every account's `token_epoch` (`R-52`, as `reset.sh --restore` does) and asks the credential gate: if the published `admin`/`password` pair is valid again — or that cannot be told — it recreates only the proxy without the 443 overlay**; it leaves the writers stopped and prints `token_epoch:`, `credential_gate:` and `https_443:` lines |
| `resume <STAMP>` | starts the writers the record stopped (those the deployed file still declares) and closes the record. Refused while the importer holds its lock |
| `status` | read-only: the record and its age, the marker, the import lock, the installed SHA-256s |

### The order — with real client data on the stand

P2 (a migrating publication), in `CD-16`'s order (`W54-PLAN.md` §3.10):

```
ssh … dump-db                                   # prints <STAMP>; writers stopped
ssh … inventory-s3 <STAMP>
install -d -m 700 .local/stand-copy             # once; ignored by Git
infra/deploy/pull-copy.sh --host <user@stand> --identity <copy key> <STAMP> "$PWD/.local/stand-copy"
scripts/stand-copy/restore-test.sh .local/stand-copy/<STAMP>     # heavy step, in a window
ssh … attest <STAMP> <dump-sha256> <report-sha256> publish <candidate sha>
# push; the workflow's deploy.sh accepts exactly <candidate sha>; verify-deployed.sh
ssh … resume <STAMP>
ssh … verify-objects 50
```

### A migrating deploy needs a fresh receipt (`PROD-03`, `R-146t`, `AD-03`, `AD-17`; `ADR-0021` section 5)

`R-93` binds as before: a one-off copy (dump, inventory, fetch, restore test, attestation) precedes every migrating
publication whenever the stand holds real client data (`R-146x` keeps the full attestation after 1.0 as well).
`R-146t` adds one **mechanical refusal on top of it** — `deploy.sh`'s guard `stand-copy-fresh`. There is **no new dump
script and no second artefact**: the receipt is the record `dump-db` writes.

| `deploy.sh` refuses `[stand_copy_fresh]` unless… | where it reads it |
|---|---|
| **no** `real_data` marker exists, or the database is already at this checkout's head — then it asks nothing | the marker beside the record; `alembic_version` against `db/migrations/versions` |
| the record is **open** | `state` |
| it **has its dump** (`dump` with a SHA-256) and the attestation **binds that SHA-256** | `dump`, `attestation.dump_sha256` |
| it is attested for **this commit** (`purpose` `publish`, `target_sha` = the checkout's `HEAD`) | `purpose`, `target_sha` |
| it was quiesced **at most 24 hours ago** | `quiesced_at` |

"Pending" means the checkout's head revision differs from `alembic_version`, read **before** `migrate`. If the marker
exists and the database cannot be read, the deploy refuses and names the way out
(`docker compose ... up -d postgres`, then run it again): an unverifiable receipt is not a verified one. The three
conditions `R-93` already enforces (unattested, attested for another commit, an import record) keep refusing **first**,
in their own words (table below); this guard repeats the first two so that they hold even if one of them is ever
removed, and adds the rest. A deploy with no pending migration needs no receipt, and before the marker exists
(`R-110`, test data only) nothing changes.

**The order on deploy day** (the dump is the clock: deploy within 24 hours of `dump-db`):

```
ssh … dump-db                                   # prints <STAMP>; writers stopped; quiesced_at starts the 24 hours
ssh … inventory-s3 <STAMP>
infra/deploy/pull-copy.sh …                     # to the development host
scripts/stand-copy/restore-test.sh …            # the trial restore
ssh … attest <STAMP> <dump-sha256> <report-sha256> publish <candidate sha>
# the push; the workflow's deploy.sh now finds: marker present, migration pending, record open + dump + attested for
# this commit + quiesced < 24 h ago -- and prints "deploy.sh: migrating <from> -> <to> under the copy <STAMP> (...)"
ssh … resume <STAMP>
```

A slow restore test that runs past 24 hours costs a new `dump-db`, not a debate: `resume`, then start again.

**Owner steps, recorded here and not done by the lane that built the guard:**

1. install the copy key (the numbered steps above, **including the fourth file**), which `R-110` deferred until the
   first real upload and which the production release now requires;
2. take the first real copy — `dump-db`, `inventory-s3`, `pull-copy.sh`, `restore-test.sh`, then `attest … publish
   <sha>`. **The first attestation of a full copy writes the `real_data` marker**; from that moment `attest
   --test-data` is refused and every migrating deploy needs the receipt;
3. repeat step 2 of the install whenever `copy-serve.sh` or either library changes.

P4 (the corpus import): `capacity`; the inbound key's `receive` and `status`; then
`dump-db` → `inventory-s3` → pull → restore test → `attest <STAMP> … import`; the inbound key's
`import` and `report`; `resume <STAMP>`; `verify-objects`.

**On failure after the push:** a forward fix (re-attest `publish <fix sha>`, push), or the
owner-ordered `restore-db <STAMP> <dump-sha256>`, then a reviewed revert under
`MAIN_AUTODEPLOY_POLICY.md` (re-attest `publish <revert sha>` first), then `resume`. A revert
alone would fail `migrations-at-head`. **`restore-db` can bring the published `admin`/`password` pair back** (a dump
taken before the password was changed): it raises every `token_epoch`, asks the credential gate and, on a finding,
recreates the proxy without the 443 overlay — so check its `credential_gate:` and `https_443:` lines before `resume`,
and expect the site to be unreachable from outside until an administrator changes the password through the
loopback port (`R-146s`). A revert deployed afterwards is itself refused `[default_credential]` until that is done.

### The order — test data only (now, `R-110`)

* A publication deploys without a copy. With no record, or a closed one, `deploy.sh` changes
  nothing.
* The corpus import runs under a waiver, which is quiesced and fingerprinted like a copy, but
  has no dump:

  ```
  ssh … attest --test-data                      # prints <STAMP>; writers stopped
  # the inbound key: import <KEY>, until status shows exited 0; report <KEY>
  ssh … resume <STAMP>
  ```

* The corpus is recovered from the bundle kept on this host, not from a copy.

### `deploy.sh` and the record

`deploy.sh` reads the record (`STAND_COPY_RECORD`, default
`/srv/auditmanager-copy/record.json`) and the import lock (`BUNDLE_STAGING`, default
`/srv/auditmanager-bundles`) **before anything else and before any `docker` call**. It
refuses with exit 3 and a typed word that deploy-auto's log shows:

| Word | Meaning | What to do |
|---|---|---|
| `stand_import_locked` | the importer holds `import.lock` | wait for the import; `status` on the inbound key |
| `stand_copy_unreadable` | a record exists that the copy key did not write | the owner inspects it |
| `stand_import_open` | the open record is an import record or a waiver | finish the import, then `resume <STAMP>` |
| `stand_copy_unattested` | a copy is open and not attested | finish the copy and `attest … publish <sha>`, or `resume` it |
| `stand_copy_other_target` | the open publication record binds another SHA (or the checkout's `HEAD` cannot be read) | re-attest for this SHA, or deploy the SHA it names |
| `stand_copy_fresh` | the `real_data` marker exists, a migration is pending, and the record is not a fresh receipt (the lines under it say which condition fails) — or the migration state could not be read | take the copy and deploy within 24 hours of the dump (above) |

An open publication record attested for exactly this checkout's `HEAD` is accepted, and the
deploy prints `under the open copy <STAMP>, attested for this commit <sha>`.

### Reading a refusal

Every refusal exits **3**: `copy-serve.sh: REFUSED [<guard>]: <reason>`. `pull-copy.sh` passes
the stand's message on and removes whatever it fetched for that stamp.

| Guard | What to do |
|---|---|
| `command-*`, `verb-known`, `verb-grammar` | not one of the verbs, or bad arguments. Nothing ran |
| `checkout-present`, `env-file-present`, `instance-configured`, `copy-dir-*` | the install (steps 1–3) or the deployed checkout is incomplete |
| `copy-lock-free`, `import-lock-free` | another copy verb, or the importer, is running. `status` |
| `record-closed` | a copy or waiver is still open: `resume` it first |
| `record-open`, `record-is-open`, `record-stamp-matches`, `record-readable`, `restore-record-present`, `fetch-record-present` | there is no open record with that stamp (only the latest is kept), or it is not readable |
| `record-has-dump`, `artifact-present` | a waiver has no dump or inventory; or `dump-db`/`inventory-s3` has not finished |
| `docker-answers`, `database-answers`, `fingerprint-read`, `inventory-read`, `sample-read` | the stack did not answer a read. The record stays as it was; nothing was guessed |
| `copy-dir-has-room` | less free space than the database plus the margin. Nothing was stopped. `capacity` |
| `writers-stopped`, `writers-still-stopped`, `writers-resumed` | a writer did not stop, runs again, or did not start. The record stays open; `resume <STAMP>` restarts what it stopped |
| `dump-readable` | `pg_restore --list` cannot read the dump. The record is open without a dump; `resume`, then `dump-db` again |
| `dump-digest-matches`, `dump-digest-matches-restore`, `inventory-taken` | the digest given is not the recorded one or the file's; or there is no inventory yet |
| `window-open` | the copy is older than 12 h: `resume`, then a new copy |
| `import-record-stays-import` | an import record is not rebound to a publication: `resume`, then a new copy |
| `real-data-absent` | the `real_data` marker exists: no more waivers; take a copy |
| `objects-match` | a sampled object did not read back as recorded (or nothing was sampled). The output lists each one |
| `fingerprint-restored` | after `restore-db`, the database does not match the copy. The writers stay stopped. The owner decides |
| `listeners-library-present` | `restore-db` was asked and `lib/proxy-listeners.sh` is not installed beside `copy-serve.sh`. Nothing was stopped. Install step 2 |
| `credentials-revoked` | after the restore, `access.revoke --everyone` could not reach the database. The writers stay stopped and the record open; run the printed command, then `resume` |
| `https-withheld` | after the restore the credential gate said finding (or could not be answered) and public port 443 could not be withdrawn. The writers stay stopped; close it by hand with the printed command, then `resume` |

### Heavy steps and their floor

`scripts/stand-copy/restore-test.sh` restores a whole database into a disposable local
container. It is a heavy step (`W54-PLAN.md` §3.9) and refuses unless
`infra/deploy/capacity-probe.sh` finds four times the dump plus 3 GiB free on the Docker data
root's filesystem and at least 6 GiB of RAM available. The same probe applies the stop rule to
any heavy step here:

```
infra/deploy/capacity-probe.sh --path root=/ --need root=$(( (<increment GiB> + 3) * 1073741824 )) \
    --need-ram $(( 6 * 1073741824 ))
```

---

## 14. «Подключения» — executor connections (`EXEC-HTTP-01`, `R-143`)

Under «Исполнители» (tabs «Подключения», «Процессы», «Назначения») an administrator creates a
connection (an `http_api` address, the pinned model, the transport), pastes its key, presses
«Проверить» and assigns it to «Анализ текста». Nothing of this is run by the deploy; this section is
the operator's order for the host. `infra/deploy/README.md` and
`src/auditmanager/executors/README.md` carry the mechanism.

### What changed on the host, and what it needs first

Merging `EXEC-HTTP-01` changes the stand in **two** ways even if nobody ever opens the new screen:

* **`R-133` is enforced on the run path.** The text stage holds every live reply to the model it
  asked for. With `AUDITMANAGER_PROVIDER_SOURCE=environment` that model is `PROXY_LLM_MODEL`, so the
  stub `proxy` no longer works: every run fails closed (`model_identity_mismatch`; the stage's
  stored message names `model_not_selected`). **Before the deploy, set `PROXY_LLM_MODEL` in
  `provider.env` to the explicit name the gateway reports** (for example `anthropic/claude-opus-5`),
  then deploy, then verify one run.
* **The `api` service no longer loads `provider.env`.** It makes no model call, so it holds
  neither the provider credential nor the private ring. A deployment that relied on the api
  reading it needs nothing: the worker still does.

### The key ring (once per stand)

The key of a connection is sealed to a public key by the `api` and opened by the worker with the
private ring. Generate a pair on the host (the command is in `provider.env.example`); then

* `alpha.env`: `AUDITMANAGER_SECRETS_PUBLIC_KEYS=<kid>:<public>` and
  `AUDITMANAGER_SECRETS_ACTIVE_KID=<kid>` (public values; both services receive them);
* `provider.env` (`chmod 600`, the worker alone): `AUDITMANAGER_SECRETS_KEYS=<kid>:<private>`.

The ring is not in PostgreSQL, S3 or any backup. A restore onto another host therefore brings the
connections back as `secret_unreadable` until the ring is installed there or an administrator
pastes each key again; a restore drill can never make a paid call.

### Importing today's variables, and the switch

Run on the worker, from its image and environment:

```
docker compose --env-file infra/deploy/env/alpha.env -f infra/deploy/compose.server.yml \
    exec worker python -m auditmanager.executors import-env
```

`import-env` creates one `http_api` connection from `PROXY_LLM_BASE_URL`, `PROXY_LLM_TOKEN` and
`PROXY_LLM_MODEL` (it refuses the stub), seals the key, runs the probe itself over the worker's own
network path and, only when the probe is `ok`, assigns the connection to `text_analysis`. A second
run changes nothing and names the existing connection. Exit `3` means the connection exists but the
probe did not pass: read the outcome in «Подключения», fix it there and assign by hand.

**Baseline OpenRouter after the source switch.** With `AUDITMANAGER_PROVIDER_SOURCE=database`,
the worker now accepts a complete `PROXY_LLM_BASE_URL`, `PROXY_LLM_TOKEN`,
`PROXY_LLM_MODEL` triplet in its private `provider.env`. On first start it creates
«OpenRouter (из окружения)» as a normal `http_api` / `openai_chat` connection, seals the
key and queues its probe. It does not alter «Анализ текста»: an existing Codex route stays
in place. Once the probe reads «готово», choose OpenRouter under
«Исполнители → Назначения». The connection then owns its saved settings and key;
subsequent worker restarts never overwrite an edit made in the UI. This route uses the
same verified PNG image block as other `openai_chat` HTTP connections, once the separate
image stage creates a crop task. A model that cannot receive images will refuse that call.

**SSH command and PNG crops.** `ssh_command` is served after a successful probe
on its current SSH key and revision. In «Исполнители → Подключения» create
«Команда по SSH», install the generated public key for a dedicated remote
account, press «Проверить», confirm the observed host-key fingerprint in a new
revision, then probe again. The worker checks the destination on every call,
dials the checked IP and requires the saved host key. It sends one JSON task on
stdin with `model`, `system`, `user_text`, optional `output_schema`, and optional
`image: {media_type: "image/png", data: "<base64>"}`. The PNG bytes must match
the selected saved crop. A `custom_command` remote script must answer on stdout
with `model`, `output_text`, `stop_reason`, `input_tokens`, `output_tokens` and
optional `reported_cost_usd`; the reported model must match the gateway model.
The supplied `tools/executor-runner/ssh-forced-command.sh` implements the
`claude_code_headless` profile, including an image content block through
Claude Code's stream JSON input. It needs an API key in its protected remote
environment file and the remote `claude` binary. Check the installed CLI's
version and one real JSON result before routing a production connection; the
local automated test uses a stub CLI. No image task is created until the
separate W56b prompt and evidence policy are approved.

**HTTP-модель через SSH-туннель.** `http_api` with «SSH-туннель» uses the
existing `openai_chat` or `anthropic_messages` adapter over a short-lived
forward. Configure its HTTP API key and generated SSH key, then install the
public SSH key on a dedicated remote account with forwarding restricted to
the target host and port. An `authorized_keys` option such as
`restrict,port-forwarding,permitopen="127.0.0.1:11434"` allows exactly that
target (adjust it to the saved base URL). The worker dials the validated SSH
IP, pins the SSH host key, and keeps the original HTTP Host and TLS server
name while connecting through the local forward. It carries the same checked
PNG image block as direct HTTP. Press «Проверить» after setting both secrets;
confirm an unpinned host key in a new revision and probe again. Replacing
either secret makes the old successful probe unusable, so probe after every
rotation. The forward closes after each model call; the remote HTTP endpoint
is resolved by the SSH server, and `permitopen` should restrict it.

Then, in this order:

1. verify one run through the connection while the source is still `environment`;
2. either remove `PROXY_LLM_*` after the explicit import, or keep a complete triplet for
   automatic baseline registration; remove `ANTHROPIC_API_KEY` in both cases. The loader
   refuses an incomplete triplet or an API credential under `database`;
3. set `AUDITMANAGER_PROVIDER_SOURCE=database` and `AUDITMANAGER_PROVIDER_MODE=live` in `alpha.env`
   and redeploy. From then on a run freezes the route's revision at start and its calls, call rows
   and `connection_revision_id` go through it;
4. `infra/deploy/readiness.sh` — the `executor-source` check reports a missing ring, a public key
   without its private half, an incomplete baseline triplet or a stub model.

**Rollback** is `AUDITMANAGER_PROVIDER_SOURCE=environment` and the variables back in `provider.env`.
A run that froze a connection under `database` and is served after the switch back is refused, not
quietly served by the wrong source.

### Rotation

* **A key of a connection** is replaced in the UI. It writes a new secret and does not touch the
  revision, so runs in flight keep going and the next Attempt uses the new key. The connection must
  pass a probe on the new key before a new run can start on it.
* **A changed address** is a new revision. The stored key was entered for the old address and
  does not open for the new one: paste it again, probe again. A new revision is unusable until a
  probe passes.
* **The master key**: add a pair to the ring and change `AUDITMANAGER_SECRETS_ACTIVE_KID`, run
  `docker compose ... exec worker python -m auditmanager.executors rewrap` (it re-seals every
  current secret to the active key id and keeps each one's destination), then remove the old pair.
  A secret whose key id is no longer in the ring is `secret_unreadable`, shown in the UI and refused
  at use, never skipped.

### Where the worker may send a key

The worker refuses by default a name that cannot leave the host (`localhost`, a compose service
name such as `postgres`), loopback, link-local (cloud metadata) and the compose network, in the
probe **and** in every call, by the resolved address. A private range is accepted only for a
connection whose transport is `vpn`. `AUDITMANAGER_EXECUTOR_ALLOWED_HOSTS` in `provider.env` narrows
further. `python -m auditmanager.executors reach <url> [--transport vpn]` says whether this container
may send a key to an address and can open a connection to it.

### Reading a probe

| Outcome | Meaning |
|---|---|
| «готово» | the key, the model and the route work; the reported model and latency are shown |
| «IP стенда не допущен» | the gateway's front door refused this host (HTTP 403 with an HTML body): ask its operator to allow the stand |
| «ключ отклонён» | HTTP 401/403 with a JSON body |
| «отвечает другая модель» | the answer named no model, a stub or another model than the revision's gateway name (`R-133`), or a reported cost off the pin's rates (`rate_mismatch`) |
| «нет ответа» | no answer within the revision's timeout, or no worker took the probe within 120 s (`no_worker`) |
| «адрес недоступен» | the name does not resolve or the connection is refused |
| `destination_refused` | the address is one the worker may not send a key to |
| `kind_not_served` | a connection variant without an adapter in this worker version |

A probe never keeps a body, a header or an address; its detail is a fixed phrase.

### Long waits and cost

One Job is one run and an Attempt runs the whole run, so a slow connection occupies the single
worker slot (and the queue behind it) for the length of its call, bounded by the revision's
timeout and the 900 s watchdog. A revision with billing `not_metered` is recorded «не тарифицируется»:
a run of only unmetered calls reports cost `0` with basis `unmetered`; a mix of unmetered and
metered calls reports the metered sum, `estimated`.

---

## 15. The runner channel — tokens, the proxy reload, revocation (`EXEC-PULL-01`, `R-143`)

For the owner's **Codex subscription on a machine the stand cannot SSH into**,
use the outbound SSH local-forward setup in
`tools/executor-runner/README.md` §D. The stand sees the existing `pull`/`agent`
connection; its runner reaches the loopback proxy through SSH and answers with
the local Codex CLI. Configure billing `not_metered`, pin `gpt-6-sol`, and require
an `ok` probe before routing. No inbound port on the owner's machine, new
stand-side SSH profile, API key or deployment setting is required.

A `pull` connection (client `claude_code_session` or `agent`) is served by a *runner* that calls
the stand; the stand never calls it. The runner needs the stand's public HTTPS origin and a runner
token, and nothing else: no database, no object store, no shell on the stand. Its four calls are
`POST /api/v1/runner/tasks/claim`, `.../{task_id}/extend`, `.../answer` and `.../fail`
(`tools/executor-runner/RUNNER_API.md`).

**Issuing a token (an administrator, in «Исполнители → Подключения»).**

1. Create the connection with kind `pull`, set a revision (the pinned model, the answer deadline,
   `max_claimed_tasks`; `not_metered` for a subscription session) and route «Анализ текста» to it
   once a probe passes. «Проверить» posts a synthetic task that a runner must claim within 120 s and
   answer within 120 s; a connection with no runner online ends the probe as «ни один клиент не на
   связи» and cannot be routed. The worker takes the probe, so a worker must be up.
2. «Выпустить токен» on the connection's card (`Исполнители → Подключения`) shows the token **once**
   in a box with a copy button and a warning that it will not be shown again (`amr_` and 52 more characters). The stand keeps
   only its SHA-256, so a lost value cannot be shown again: revoke it and issue another. The
   default life is 30 days; the screen shows the prefix, the expiry, when and from where it was
   last seen.
3. The owner puts the value into the runner's environment (`PDF_ANALYSIS_RUNNER_TOKEN`), never
   into a file or a URL. `tools/executor-runner/README.md` has the `claude mcp add …` command and
   says where Claude Code keeps it in clear.

**The card.** A `pull` connection's card lists each token (prefix, issued, expires, revoked, last seen
and from which address), says «на связи» when a runner of the connection called the stand less than
60 s ago, and shows the number of tasks open now. «Отозвать» asks first.

**Revoking.** The revoke action (`POST /executor-connections/{id}/runner-tokens/{token_id}/revoke`)
takes effect on the runner's next call, which is `401 authentication_required`; a claim it holds
lapses within two minutes and its task goes back to `open` (or expires at its deadline). The
same refusal ends an expired token and any token of an archived connection. To take the whole
surface away: revoke every token, or remove the route; the proxy rule below can stay.

**The proxy.** The throttle is two `limit_req_zone`s and two `map`s at http level in
`proxy/nginx.conf` plus `limit_req` lines inside `location /api/v1/` of both server bodies. They
change the *http* context, so a deploy that carries them must reload the proxy: `deploy.sh` does
(`reload-proxy.sh` runs `nginx -t` in the pinned image first and refuses an invalid file). By hand:

```
docker exec <proxy container> nginx -t && docker exec <proxy container> nginx -s reload
```

The budget is 60 requests a minute with a burst of 30 per token (the key is the token's twelve
visible characters) and 300 a minute with a burst of 120 per client address, for
`/api/v1/runner/tasks/…` only. A runner that is throttled gets `429` with the `rate_limited`
envelope and waits (30 s when no `Retry-After` is sent). `docs/program/EXEC-PULL-01.md` replays a
scripted runner against these numbers.

**What a long wait costs.** While a runner thinks, the worker's only slot is busy inside its
Attempt and the queue waits behind it (plan section 3). With no runner online a task is not
claimed and the call ends after the revision's answer deadline (capped below the 900 s watchdog by
60 s) as `dependency_unavailable`, `no_executor_online`; it never moves to another connection
unless an administrator configured a standby. A task's text and the runner's answer are cleared
seven days after it ends.

## 16. Database roles — the migrator and the application role (`PROD-04-DB-ROLES-01`; `R-146n` item 1, `AD-02`)

**What it is.** Two PostgreSQL roles, and the processes that use each:

| Role | Name | Url (in `alpha.env`) | Used by | Can |
|---|---|---|---|---|
| **migrator** (the owner) | `POSTGRES_USER` | `MIGRATOR_DATABASE_URL` | the one-shot `migrate` and `release-notes`; `apply-grants.sh`; the operator tools that need write-everything (`purge-product-data.sh` hands it to the product purge; the project erase of `PROD-07` will) | everything: it owns every object |
| **application** | `ALPHA_APP_DB_USER` | `DATABASE_URL` | `api` and `worker` (and the `compose run` one-offs of `reset.sh`, `copy-serve.sh restore-db`, `readiness.sh`, which run application code) | log in; `SELECT` / `INSERT` / `UPDATE` / `DELETE`, `SELECT` + `INSERT`, or `SELECT` per table, as `scripts/recovery/grant_classification.py` says; sequences `USAGE`. **Cannot** create, alter or drop anything, **cannot** `TRUNCATE`, owns nothing, is a member of nothing, is not a superuser. An append-only table (`audit_event`, the ledgers, the immutable evidence) refuses `UPDATE` and `DELETE` by privilege **and** by trigger |

**The decision recorded here (decided by the lane): the migrator stays the bootstrap superuser.** The postgres image's
`POSTGRES_USER` is a superuser, and `ADR-0021` section 3 makes it the migrator. A plain (non-superuser) owner was
considered and cannot do the job: migration `0013` runs `CREATE EXTENSION vector`, and the pgvector built into this stack is
`superuser = true, trusted = false`, so a plain owner cannot migrate a fresh database
(`test_a_plain_owner_cannot_migrate_a_fresh_database` pins the premise; if it goes red the decision is open again). What
contains the superuser is that its url reaches **no always-on service**: `compose.server.yml` gives `MIGRATOR_DATABASE_URL`
to `migrate` and `release-notes` only (`test_the_application_gets_its_url_and_only_the_one_shots_get_the_owners`).

### What the owner does (once per host, and on rotation)

1. **Choose the second password** (20 to 128 characters of `A-Z a-z 0-9 . _ ~ -`; it is written into a URL without quoting;
   not the owner's):

   ```
   head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n'; echo
   ```

2. **Edit `infra/deploy/env/alpha.env`.** Add or change four lines, with the same password in the second and third:

   ```
   ALPHA_APP_DB_USER=auditmanager_alpha_app
   ALPHA_APP_DB_PASSWORD=<the password from step 1>
   DATABASE_URL=postgresql+psycopg://auditmanager_alpha_app:<the password from step 1>@postgres:5432/<POSTGRES_DB>
   MIGRATOR_DATABASE_URL=postgresql+psycopg://<POSTGRES_USER>:<POSTGRES_PASSWORD>@postgres:5432/<POSTGRES_DB>
   ```

   **An existing host's `DATABASE_URL` names the owner today; moving the owner's url to `MIGRATOR_DATABASE_URL` and writing
   the application role's into `DATABASE_URL` is the cutover.** `deploy.sh` refuses the old shape (`[app_db_role_invalid]`
   or `[database_urls_incoherent]`) before it builds anything. No value is ever pasted into a chat or a commit.

3. **Deploy.** `infra/deploy/deploy.sh`. Expected, in order, after the build:

   ```
   -- migrating as the owner, then giving the application role its rights --
   apply-grants.sh: applying the grant classification to <db> for the application role '<role>' (owner: <owner>)
   grants-ok: <role> on <db> matches the classification
   -- bringing the stack up --
   ```

4. **Check it.** Either of these, on the host:

   ```
   infra/deploy/readiness.sh            # the db-roles line: "api=<role> worker=<role> -- ... (f|f|f|t); apply-grants.sh --check: ..."
   infra/deploy/apply-grants.sh --check # prints: grants-ok: <role> on <db> matches the classification   (exit 0)
   docker compose --env-file infra/deploy/env/alpha.env -f infra/deploy/compose.server.yml exec -T postgres \
     psql -U <POSTGRES_USER> -d <POSTGRES_DB> -Atc "select rolsuper, has_schema_privilege(rolname,'public','CREATE'), has_table_privilege(rolname,'public.audit_event','DELETE'), has_table_privilege(rolname,'public.audit_event','INSERT') from pg_roles where rolname='<ALPHA_APP_DB_USER>'"
                                         # prints: f|f|f|t   (ADR-0021 row 7)
   ```

   `readiness.sh` also says **which role `api` and `worker` actually connect as** (read from the running containers'
   `DATABASE_URL`, user only) and reports a `FINDING` if either is the owner.

5. **Rotation.** Change `ALPHA_APP_DB_PASSWORD` and the password inside `DATABASE_URL`, deploy. The step sets the new
   password on the role; the old one stops working at once. (`apply-grants.sh` re-salts the stored verifier on every run;
   nothing else about the role changes.)

### When it runs (every path that makes or replaces the schema)

| Path | Where the step runs | If it cannot |
|---|---|---|
| `deploy.sh` | after `migrate` and `release-notes`, before `up` (guards `owner-migrated`, `release-notes-loaded`, `grants-applied`) | refuses `[migrate_failed]`, `[release_notes_failed]`, `[grants_not_applied]`: nothing is started or replaced |
| `reset.sh` (the wipe) | after the migrations, before the worker and the bucket | exit 4, says the schema is recreated but the role has no rights, the worker stays stopped |
| `reset.sh --restore` | after `pg_restore` and the migrations, before the worker and the credential revocation | reports (`apply-grants=<status>`), keeps the worker stopped, exit 6 |
| `copy-serve.sh restore-db` | right after `pg_restore`, before the fingerprint and anything that connects as the role | refuses `grants-applied`: the writers stay stopped, the record stays open |

`reset.sh` (both destructive modes) and `restore-db` ask **before they change anything** that the step can run: the script is
there (`grants-script-present`) and the second password is set (`app-db-role-configured`). `purge-product-data.sh` passes
`MIGRATOR_DATABASE_URL` to the product purge for every step (`migrator-url-configured` refuses an environment without it).

### What stops it, in words

| Word (exit 3 unless noted) | Meaning |
|---|---|
| `[app_db_password_unset]` | `ALPHA_APP_DB_PASSWORD` is empty or absent. Choose one (step 1). There is no fall-back to the owner |
| `[app_db_password_shape]`, `[app_db_password_is_owner_password]` | not 20-128 URL-safe characters, or the owner's password |
| `[app_db_role_invalid]`, `[app_db_role_is_owner]` | `ALPHA_APP_DB_USER` missing or malformed, or equal to `POSTGRES_USER` |
| `[database_urls_incoherent]` | `DATABASE_URL` / `MIGRATOR_DATABASE_URL` do not carry the roles and passwords the file names |
| `[grants_script_missing]` | `apply-grants.sh` is not in the clone / not installed beside `copy-serve.sh` / not executable |
| `[grants_unclassified]` | the schema holds a table, view or sequence `grant_classification.py` does not name. The role was given nothing new and the transaction rolled back. A migration that adds a table needs a classification (and `python -m scripts.recovery.grant_classification --write-script infra/deploy/apply-grants.sh`) |
| `[grants_drift]` (exit 1 of `--check`, 4 after an apply) | the role's rights differ from the classification; the lines say how (`the role holds TRUNCATE`, `the role lacks SELECT`, `the role owns table ...`) |

### What this does not do

* **No `ALTER DEFAULT PRIVILEGES`.** A table a later migration creates gets **no** rights until it is classified; that is the
  fail-closed half of the design, and the step refuses rather than guess.
* **It does not take ownership back.** An object the application role came to own is reported by `--check`
  (`owner: the role owns ...`), not repaired.
* **The role keeps the `PUBLIC` defaults** that every role has: it can connect to its database, create session-local
  temporary tables, and execute the functions an extension installs (pgvector). It cannot create a permanent object.
* **`UPDATE` on two append-only tables' key column** (`work_assignment.assignment_uid`,
  `document_version_classification.version_uid`): the code locks those rows with `SELECT ... FOR UPDATE` / `FOR NO KEY
  UPDATE`, which PostgreSQL grants only with an `UPDATE` privilege on some column. The immutability trigger fires on a row
  update and not on a lock, so the lock works and every real `UPDATE` is still refused.
* **The password is in the file**, readable by the account that deploys. `chmod 600 infra/deploy/env/alpha.env`, as always.
