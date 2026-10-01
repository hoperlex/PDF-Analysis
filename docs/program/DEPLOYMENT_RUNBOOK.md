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
* **one more if TLS is turned on**, `ALPHA_HTTPS_PORT`, default `443` (§6).

**Both are bound to `127.0.0.1` unless you say otherwise, and you reach the stand over an SSH
tunnel.** Ruled by the owner 2026-09-22, closing `D-49`:

```
ssh -L 31500:127.0.0.1:31500 <host>        # then open http://127.0.0.1:31500 locally
```

**Why the default is loopback, measured rather than assumed.** The compose file used to
publish with no interface at all, which binds `0.0.0.0`. On this host the stand answered
**`200`** on its **public** address, at `/bff/v1` — which serves **every operation of this
surface**, **writes included**, with no credential, because the browser deliberately holds no secret and
the BFF route adds it server-side. The origin is unauthenticated *by design*; nothing but the
network was keeping anyone out.

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

**`ALPHA_BIND_ADDRESS` is how a host that genuinely should publish says so** — one behind a
firewall you have *verified against the chains above*, serving TLS under `R-1`. It governs
both ports, so a host is published or not published rather than published on one by accident.
`R-4` puts real client documents on the pilot server, and this is the line that decides who
can reach them.

Check, after any deploy:

```
docker port <instance>-proxy-1                 # expect 127.0.0.1:<port>, not 0.0.0.0
curl -s -o /dev/null -w '%{http_code}\n' http://<this host's own ip>:<port>/bff/v1/projects
```

The second must fail to connect. On this host it printed `200` before the fix and `000` after.

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
  no reviewer and into no browser — and it goes to **two** processes, not one:
  `compose.server.yml` gives it to `api`, where it belongs, and to `web`, which forwards it
  in an `Authorization: Bearer` header on the **sign-in exchange** and on no other forward.
  Every data forward carries the *reviewer's* own credential instead. The paragraph that
  used to tell operators to present it as a bearer token is corrected in
  `infra/deploy/README.md` and, since 2026-09-29, in `infra/deploy/env/alpha.env.example`
  — the file you actually edit (`Y6`).

  *(`Y-F`. Until 2026-09-29 this paragraph said the value goes to *"the API process and
  nowhere else — not to a reviewer, not into a browser, not into a request header."* Two of
  those three held; the header clause and *"nowhere else"* did not, and this is the paragraph
  written to repair an earlier falsehood of exactly this kind. Read the chain:
  `grep -n 'AUDITMANAGER_API_TOKEN' infra/deploy/compose.server.yml` → `:173` api, `:208`
  web; `grep -n "headers.set('authorization'" web/src/shared/api/credentialed-forward.ts`.
  **What it does not expose**, measured by `W47-JUDGE-X` §1.4 rather than argued: the value
  is not itself a usable credential — presented as `Authorization: Bearer` or as `X-API-Key`
  against a protected operation it answers **401**, because the seam signs with
  `HMAC(secret, context)` — and nothing about this reaches a browser. What it **is** is mint-capable
  key material in a second container's environment, which is what an operator deciding where
  this value may go needs to know. Stopping `web` from holding it at all is a decision about
  who can mint a credential, which `R-29` §2 reserves to the owner; it is not a repair a
  wave may take.)*

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
answered — and only the first is a success. Run it after every deploy. Its first live
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
* **certificate renewal.** §6 activates a certificate; nothing here renews one. Whatever
  renews it must drop the new pair into the same directory and restart the proxy
  container — one `docker compose ... restart proxy`, which re-runs the switch.

**And one thing it will not stop you doing, so it says it here.** `docker compose ... down`
leaves all three named volumes alone. **`docker compose ... down --volumes` removes them —
the documents, the objects *and* every open session.** The third of those is the one nobody
expects: it signs every reviewer out at once, and it is the only command that undoes what
`R-51` bought. `R-4` is why the first two matter: real client documents may be on that
stack, and the only sanctioned way to remove them is `infra/deploy/reset.sh`, which dumps
before it drops. **`down --volumes` dumps nothing.**

---

## 6. TLS — activating it, verifying it, turning it off

**Nothing about TLS is in `compose.server.yml`, and nothing in `proxy/nginx.conf` mentions
a certificate.** With no certificate on this host, the TLS path is not merely disabled; it
is **not loaded** — proved, both halves, in `docs/program/reviews/W26-HOST.md` §2.

### Turning it on

1. put the pair on the host, in the clone, **by hand, by whoever holds root**:

   ```
   infra/deploy/proxy/tls/fullchain.pem      # the certificate and its chain
   infra/deploy/proxy/tls/privkey.pem        # the private key
   chmod 600 infra/deploy/proxy/tls/privkey.pem
   ```

   That directory is tracked and its contents are ignored **whole** — `git check-ignore`
   is asked about both names by a test, not trusted to a comment. **A key is never
   committed, never pasted into a message and never leaves that host.**

2. bring the stack up with the overlay beside the compose file:

   ```
   docker compose --env-file infra/deploy/env/alpha.env \
     -f infra/deploy/compose.server.yml \
     -f infra/deploy/proxy/compose.tls.yml up -d
   infra/deploy/reload-proxy.sh
   ```

   Set `ALPHA_HTTPS_PORT` in `alpha.env` if `443` is not the port to publish.

### Reading whether it took

The switch says which branch it took, every start, on the container log:

```
docker compose --env-file infra/deploy/env/alpha.env \
  -f infra/deploy/compose.server.yml logs proxy | grep enable-tls
```

* `enable-tls: TLS IS ON.` — the block was installed and nginx has it;
* `enable-tls: TLS IS OFF.` — followed by the **two paths it looked at**. If you meant to
  turn TLS on, compare those paths with where you put the files. This is the line that
  tells a mis-resolved mount apart from a missing certificate, and `D-37` is why it prints
  the path rather than a verdict: a bind source the **daemon** cannot see becomes an
  invented empty directory, not a refusal.

Then ask the port, not the log:

```
curl -sS -o /dev/null -w '%{http_code} %{http_version} verify=%{ssl_verify_result}\n' \
  https://<the host name>/
```

`verify=0` is a certificate the client trusts. Any other value is the certificate's
problem, not the proxy's.

### Turning it off, and what is lost

**Drop the second `-f`** and bring the stack up again. Nothing has to be un-edited; the
deployment is byte-for-byte the one without TLS. Removing the certificate pair and
restarting the proxy does the same thing one layer in — the switch **un-installs** the
block it wrote earlier, which matters because a restarted container keeps its writable
layer and would otherwise try to load a certificate that is no longer there.

What is lost is exactly the TLS listener. **The plain port keeps serving in both cases** —
there is deliberately no redirect from it, because `deploy.sh`'s `proxy-answers` guard
requires **401** on `/api/v1/openapi.json` there, and a `301` is not 401, so a redirect
would turn every successful deploy into a refusal. *(`Y3`: this said 200. The conclusion
survives — a 301 was never the answer the guard wants — and the number was wrong. The guard
is at `infra/deploy/deploy.sh:751-772`; `readiness.sh` printed the same false number at the
operator and is corrected with it.)*

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
it in advance: put the certificate in that directory, add one `-f`, and the browser reaches
the app over TLS.

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
| `default-credential` | step 5 — is any account still on the password this system seeded it with? | `src/auditmanager/access/check.py`'s own stable sentinels, run inside the deployed api image the way `deploy.sh`'s `migrations-at-head` guard runs `shared.db.check` |
| `tls` | is a certificate pair on disk at `proxy/tls/`? | `enable-tls.sh`'s own test (`[ -s "$CERT" ]`, not merely present) |
| `plain-http` | is the plain port published off this host, with no way in this tree to close it once it is? | `ALPHA_BIND_ADDRESS` (`D-49`) and §6's own words: *"there is deliberately no redirect ... the plain port keeps serving in both cases"* |
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
