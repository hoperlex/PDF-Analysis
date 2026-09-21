# The deployment runbook — a machine that has never run this

**Written by `W26-HOST` on 2026-09-21, under `R-15`.** Everything in it was driven on the
development host. **No part of it has run on the `R-1` host, because that host does not
exist yet**, and where that boundary bites it is named rather than guessed past.

## Why this is here and not in `infra/deploy/README.md`

The README is the **reference**: one section per file, the mechanism, and the measurement
behind each decision. It is what you read when something behaves oddly and you need to know
why it was built that way. It is not an order of operations, and three of the things below
are not facts about `infra/deploy/` at all:

* **`R-4` is an owner ruling with two halves still open.** Who uploads a real client
  document, and what event counts as *"the end of the pilot"*, are the owner's and are
  **not settled** (`OWNER_RULINGS_2026-09-17.md` §4). A procedure that depends on an
  unanswered question has to be able to say so, and `infra/deploy/README.md` is not a place
  where a programme question can be left open honestly;
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
inside the two images. `make bootstrap` and `npm ci` are the *developer's* gate, not this.

One optional extra: §2 suggests `python3` for one line that generates a token.
`openssl rand -base64 32` does the same job if the host has no python.

### Ports

* **one published port** for the stack, `ALPHA_HTTP_PORT` — the proxy's, and nothing else
  leaves the host. PostgreSQL, MinIO, the API and the web app are reachable only on the
  compose network and publish nothing;
* **one more if TLS is turned on**, `ALPHA_HTTPS_PORT`, default `443` (§6).

### Disk

<!-- W26-HOST-DISK -->

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

  The seam is **fail-closed**: a container started without it exits non-zero rather than
  serving `authentication_required` to all fifteen operations, which from a browser looks
  like a broken product rather than an unconfigured one;

* **the passwords.** `deploy.sh` compares what you wrote against the example file's own
  published values and refuses, by identity, if you left any of four unchanged. Those
  values are in git and are not secrets.

**No credential is ever pasted into a chat message** — `OWNER_RULINGS_2026-09-17.md` §3:
*"the credential goes on that host's disk, by the owner"*. That includes the output of
`docker compose config`, which prints **every** environment value in clear, the provider
credential included (measured — §9).

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
| **3** | it refused, and said which of thirteen guards refused and why |
| **2** | the arguments were wrong |

Seven guards answer **before docker is touched at all**, so a refusal costs nothing. After
the build and the `up`, it asks the running stack four questions it can fail: every service
healthy; the database at the head this code expects; the published port answering 200; and
**the document the process serves conforming to the frozen
`contracts/api/v1/openapi.json`** — the gate's own conformance engine, re-run against the
deployed process. That last one is `PA-01` criterion 1's second clause and it is about the
**API schema**, not the database schema.

A second run against an unchanged tree replaces **no container at all** (`W24-IDEM`).

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
requires 200 on that port and a `301` would turn every successful deploy into a refusal.

---

## 7. `R-4` — the wipe, and the question that is still the owner's

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

**Whoever holds root on the `R-1` host and wrote `alpha.env`** — because the command must
be typed with the database and bucket names that file configures, and because the wipe
destroys real client documents. `R-4` does not name that person, and this runbook does not
appoint them: it records that **one named person must own it before a real document is
uploaded**, and that it is the same person who holds the credential.

### What "the end of the pilot" is, operationally

**This is not answered, and it is not this runbook's to answer.**
`OWNER_RULINGS_2026-09-17.md` §4 still lists both halves of `R-4` as open: *who uploads a
real document*, and *what event counts as "the end of the pilot" and therefore triggers the
wipe*.

What can be said without answering it, because it follows from the shape of the commitment
rather than from anyone's preference:

* **the trigger must be a single observable event** — a date, or a named person saying so
  in writing, or the acceptance of a named checkpoint. A wipe that depends on somebody's
  judgment of whether the pilot has "ended" is a wipe that does not happen;
* **until that event is written down, no real client document should be on the host.** A
  wipe commitment with no trigger is not a commitment, and `R-4` permits the documents
  *because* the wipe is promised;
* it is not the same event as `PA-01`. The roadmap's §6 already runs `reset.sh` once
  **after** `PA-01` and **before** real documents arrive, to clear the pilot corpus. The
  `R-4` wipe is the later one, at the end.

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

One thing to know before reading the rehearsal's screen: `--dry-run`'s **per-table figures
are exact**, and its **total is not** — it counts one view (`finding_current_verdict`)
whose rows are already counted elsewhere, so the total **over-reports**. It never tells you
there is less to lose than there is (`D-39`).

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

## 9. When it goes wrong

| What you see | What it is |
|---|---|
| **502 on everything**, containers healthy | the proxy holds a dead upstream after a rebuild. `infra/deploy/reload-proxy.sh`. Intermittent, so it is a step and not a diagnosis (`D-27`) |
| `deploy.sh` dies telling you to **fix `nginx.conf`** | `D-38`: when `compose up` fails, the reload is reached before the guard that would name the real cause, and it accuses a file that is fine. Read `docker compose ... logs` for the service that did not come up. **`nginx.conf` is almost certainly not your problem** |
| a mount arrives **empty** | `D-37`: a `-v` source is resolved by the **daemon**, not the shell, and docker **invents an empty directory rather than refusing**. A relative source is a *volume name*. This host's docker is a snap build whose private `/tmp` is not the shell's `/tmp` — `W26-HOST` hit it again from a third direction: `docker compose --env-file /tmp/...` answered *"couldn't find env file"* for a file that was plainly there. **Keep deployment files inside the clone** |
| `docker compose config` to debug | it prints **every** value in clear, including `AUDITMANAGER_API_TOKEN`, both passwords, and — measured on Compose v5.3.1, contrary to what `provider.env.example` used to say — the **provider credential**, which `config` resolves out of `env_file:`. Use `--no-env-resolution`, and treat the output as a secret either way. The TLS private key is the one thing it cannot print: the overlay reaches it through a bind mount, so what appears is the path |
| the app answers `authentication_required` to everything | the token. `T-6` is fail-closed by design |
