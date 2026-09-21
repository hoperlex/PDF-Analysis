# `W26-HOST` — everything the owner's VPS will need, prepared before it exists

**Branch `agent/w26-host` from `origin/dev` `7535a17`. Opened before the first edit.**

`R-15` names this wave: *"everything that can be prepared **before** a VPS exists: a TLS
block that activates when a certificate appears, the deployment runbook, and the disk
headroom figure."*

**The outcome asked for is that when a host, a name and a certificate appear, the remaining
work is configuration and not authorship.** `PA-01` criteria 1 and 2 stay *cannot be
established*; that is `R-1` and it was never this session's to close. What this session can
claim is narrower and checkable: **nothing in this repository is now the reason they stay
open.** Criterion 1 needs a machine. Criterion 2 needs a certificate, and §2 is the whole
of what a repository can do about a certificate it does not have.

## 0. What this session may not touch

`W26-OPS` is live in `deploy.sh`, `reset.sh`, `verify-deployed.sh` and
`compose.server.yml`. **Every one of those was read here and none was written**, and that
constraint shapes the deliverable rather than merely limiting it: a TLS path that cannot
add a port or a mount to the compose file has to be something you add *beside* it — which
turns out to be the better answer anyway, because it is also the cleanest way to turn TLS
off (§2.7).

```
$ git diff --name-only origin/dev...HEAD
docs/program/DEPLOYMENT_RUNBOOK.md
docs/program/reviews/W26-HOST.md
infra/deploy/README.md
infra/deploy/env/alpha.env.example
infra/deploy/env/provider.env.example
infra/deploy/proxy/compose.tls.yml
infra/deploy/proxy/enable-tls.sh
infra/deploy/proxy/nginx.conf
infra/deploy/proxy/tls-server.conf
infra/deploy/proxy/tls/.gitignore
tests/integration/composition/test_proxy_tls_path.py
```

`src/`, `web/`, `contracts/`, `Makefile`, `tests/e2e/`, `artifacts/`,
`DEBT_REGISTER.md` and `CURRENT_STATE.md` are untouched, as is every file `W26-OPS` owns.
No tag, no checkpoint, nothing pushed to `main`. The one change inside `proxy/nginx.conf`
is **a comment**: the paragraph that said TLS is deliberately not here was going to be read
by someone who then could not find the TLS path. The server block is unchanged, and
`test_proxy_tls_path.py` asserts it holds no TLS directive at all.

## 1. `PA-01` criteria 1 and 2, quoted rather than paraphrased

From `ALPHA_ROADMAP.md` §5, because a brief two waves ago paraphrased criterion 1's second
clause wrongly and would have had a session prove a clause nobody wrote:

> 1. `deploy.sh` brings the stack up from a clean clone on a machine that has never run it,
>    and the schema the running app serves conforms to the frozen
>    `contracts/api/v1/openapi.json` — the same check the gate runs, re-run against the
>    deployed process rather than against a build artifact;
> 2. the browser reaches the app over TLS, and a request carrying no token is refused with
>    `authentication_required` **from the application**, not by the proxy — shown for an
>    operation of each kind, so the dependency is proved to be in front of all twelve rather
>    than in front of the one that was tried;

It is the **API** schema the running app serves, against the frozen OpenAPI document. Not
the database schema. `deploy.sh`'s `schema-conforms` guard is already exactly that check,
run against the served document with the gate's own conformance engine.

## 2. The TLS path — the shape, and both halves driven

### 2.1 Why the switch cannot live in the configuration

This is nginx's behaviour, not a preference, and each clause was checked rather than
recalled:

* **`ssl_certificate` is read when the configuration is parsed**, not when a connection
  arrives. So a `listen 443 ssl` block in a file nginx always loads is a block that must
  have its certificate *at start-up* — and this stack publishes exactly one port, the
  proxy's, so a missing file is not a degraded TLS but a dark site. **Driven** in §2.3;
* **nginx has no conditional inclusion.** `include` with a wildcard that matches nothing is
  a legal no-op — but `compose.server.yml` bind-mounts exactly **one** file into
  `/etc/nginx/conf.d/`, so a wildcard there would have nothing to find, and giving it
  something means a second mount in a file `W26-OPS` owns;
* **the official image runs every executable `/docker-entrypoint.d/*.sh` before the master
  starts** (`find /docker-entrypoint.d/ -follow -type f | sort -V`). That hook is the only
  place in this stack where *"is there a certificate?"* can be asked **before** the parse
  that would refuse.

Hence the three parts: `proxy/tls-server.conf` (the block, mounted **outside** `conf.d`),
`proxy/enable-tls.sh` (the switch, mounted into the hook) and `proxy/compose.tls.yml` (the
overlay that mounts both and publishes the port). The certificate and its key go in
`proxy/tls/`, a tracked directory whose contents are ignored whole.

### 2.2 Half one — no certificate: the stack serves the plain port, and TLS is not loaded

Real containers, the pinned `nginx:1.27-alpine@sha256:65645c…`, the **real**
`proxy/nginx.conf`, the four mounts exactly as the overlay renders them (§2.6), and two
stub upstreams answering on the compose-network names `api:8000` and `web:3000`:

```
$ docker logs $PROXY
/docker-entrypoint.sh: Launching /docker-entrypoint.d/25-enable-tls.sh
enable-tls: no usable certificate pair (a missing or empty file is not a certificate).
enable-tls:   certificate: /etc/nginx/tls/fullchain.pem
enable-tls:   private key: /etc/nginx/tls/privkey.pem
enable-tls: TLS IS OFF. The stack serves plain HTTP on the published port and nothing else.
/docker-entrypoint.sh: Configuration complete; ready for start up

$ docker exec $PROXY nginx -t
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful

$ docker exec $PROXY ls -1 /etc/nginx/conf.d/
default.conf

$ curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:55992/ ; curl -sS http://127.0.0.1:55992/api/v1
200
api-stub

$ curl -sS -k --max-time 5 -o /dev/null -w '%{http_code}\n' https://127.0.0.1:55993/
curl: (35) OpenSSL SSL_connect: SSL_ERROR_SYSCALL in connection to 127.0.0.1:55993
000
```

**`conf.d` holds `default.conf` alone.** The TLS block is not disabled in the running
configuration; it is **not in it**. That is the sense in which the path is inert.

### 2.3 The control — the same block, loaded unconditionally, with no certificate

The thing the design exists to avoid, driven rather than reasoned about. Same image, same
`nginx.conf`, and `tls-server.conf` placed straight into `conf.d/`:

```
$ docker inspect -f 'state={{.State.Status}} exit={{.State.ExitCode}}' $CTL
state=exited exit=1
nginx: [emerg] cannot load certificate "/etc/nginx/tls/fullchain.pem": BIO_new_file() failed
  (SSL: error:80000002:system library::No such file or directory ...)
```

**The naive shape takes the whole site down on a host that has no certificate yet.** This
is why `W14-PKG`'s refusal was right and why the answer is a switch outside the config
language rather than a cleverer config.

### 2.4 Half two — a certificate: TLS serves, and so does the plain port

**The certificate is self-signed and was generated by this test.** No real certificate
exists, here or anywhere in this programme; nothing below should be read as one.

```
$ openssl req -x509 -newkey rsa:2048 -sha256 -days 2 -nodes \
    -keyout infra/deploy/proxy/tls/privkey.pem -out infra/deploy/proxy/tls/fullchain.pem \
    -subj "/CN=w26host-selfsigned.invalid" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
$ chmod 600 infra/deploy/proxy/tls/privkey.pem
$ docker restart $PROXY

enable-tls: a certificate pair is present; /etc/nginx/conf.d/tls.conf installed.
enable-tls: TLS IS ON. nginx will listen on 8443 in this container; ...

$ docker exec $PROXY nginx -t
nginx: configuration file /etc/nginx/nginx.conf test is successful
$ docker exec $PROXY ls -1 /etc/nginx/conf.d/
default.conf
tls.conf

$ curl -sS -o /dev/null -w 'http  -> %{http_code}\n' http://127.0.0.1:55992/
http  -> 200
$ curl -sS -k -o /dev/null -w 'https -> %{http_code}  http/%{http_version}  verify=%{ssl_verify_result}\n' \
    https://127.0.0.1:55993/
https -> 200  http/2  verify=18
$ curl -sS -k https://127.0.0.1:55993/ ; curl -sS -k https://127.0.0.1:55993/api/v1
web-stub
api-stub

$ openssl s_client -connect 127.0.0.1:55993 </dev/null | grep -E 'Protocol|Cipher|subject'
subject=CN = w26host-selfsigned.invalid
New, TLSv1.3, Cipher is TLS_AES_256_GCM_SHA384
```

TLS 1.3, HTTP/2, **200 on both `/` and `/api/v1`** with the `/api/v1` prefix stripped
exactly as on the plain port — and **the plain port still answers 200**, because there is
deliberately no redirect (§2.7). `verify=18` is `DEPTH_ZERO_SELF_SIGNED_CERT`: the
certificate is the test's own, and that number is the evidence that it is.

### 2.5 Half three — the certificate is taken away again

Not asked for, and it is the failure the design would otherwise have introduced from the
other side. A restarted container keeps its writable layer, so a `tls.conf` written by an
earlier start would still be there:

```
$ rm -f infra/deploy/proxy/tls/*.pem && docker restart $PROXY
$ docker exec $PROXY ls -1 /etc/nginx/conf.d/
default.conf
$ curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:55992/   -> 200
$ docker inspect -f '{{.State.Status}} restarts={{.RestartCount}}' $PROXY
running restarts=0
```

The disabled branch **un-installs**. Without that `rm -f`, removing a certificate and
restarting would have produced §2.3's dark site.

### 2.6 `D-37`, carried to this mount and reproduced

A `-v` source is resolved by the **daemon**, not the shell, and docker **invents an empty
directory rather than refusing**. Pointed at a path that did not exist:

```
$ docker run -d -v /root/w26host/infra/deploy/proxy/tls-does-not-exist:/etc/nginx/tls:ro ... 
state=running
enable-tls: TLS IS OFF. The stack serves plain HTTP on the published port and nothing else.
$ ls -ld /root/w26host/infra/deploy/proxy/tls-does-not-exist
drwxr-xr-x 2 root root 4096 ...      <- docker created it
```

So a mis-resolved certificate mount lands in the `TLS IS OFF` branch: **the stack stays up
on the plain port and the log names the two paths it looked at**, which is what tells that
case apart from a certificate nobody put there. The directory being tracked in git is the
other half of the answer — a clean clone already has it, so there is one fewer thing for
docker to invent.

**And a third costume of the same finding, met by this session.** `docker compose
--env-file /tmp/<scratch>/render.env …` answered *"couldn't find env file"* for a file that
was plainly there: this host's docker is the **snap** build and its `/tmp` is not the
shell's. The rule for this repository's scripts is already "keep deployment files inside
the clone"; the runbook now says it in §9.

### 2.7 The overlay, rendered — and how TLS is turned off

`docker compose --env-file … -f compose.server.yml -f proxy/compose.tls.yml config` renders
the `proxy` service with the plain port and `8443` published, and four read-only binds
whose **relative paths resolved against `infra/deploy/`** — the project directory, which is
the first `-f`'s, not this file's:

```
source: /root/w26host/infra/deploy/proxy/nginx.conf      -> /etc/nginx/conf.d/default.conf
source: /root/w26host/infra/deploy/proxy/tls             -> /etc/nginx/tls
source: /root/w26host/infra/deploy/proxy/tls-server.conf -> /etc/nginx/tls-server.conf
source: /root/w26host/infra/deploy/proxy/enable-tls.sh   -> /docker-entrypoint.d/25-enable-tls.sh
```

**Turning it off is dropping the second `-f`.** Nothing has to be un-edited and the
deployment is byte-for-byte the one that was certified; `test_proxy_tls_path.py` asserts
`compose.server.yml` contains neither `tls` nor `443`. One layer in, removing the
certificate pair and restarting the proxy does the same thing (§2.5). **What is lost is the
TLS listener and nothing else.**

**There is deliberately no redirect from the plain port**, and the reason is a guard rather
than a taste: `deploy.sh`'s `proxy-answers` fetches
`http://127.0.0.1:$ALPHA_HTTP_PORT/api/v1/openapi.json` and refuses anything that is not
`200`. A `301` there would turn every successful deploy into exit 3, and `deploy.sh` is not
this session's file. An operator who wants the redirect adds it when the host has a name,
and must answer for that guard.

### 2.8 `nginx -t`, said plainly, and what it cannot do off the network

**`nginx -t` was run inside the pinned image on every configuration written here** — with
no certificate (§2.2) and with one (§2.4) — and passed both times. `reload-proxy.sh`
already runs the same test before every reload and refuses if it fails, so the deployed
path is covered by a script this session did not have to write.

One thing worth recording for whoever tries to test this config off a running stack:
**`nginx -t` resolves `proxy_pass` host names at configuration-parse time**, so testing
`nginx.conf` in a container that is not on the compose network fails with *"host not found
in upstream"* — a failure about DNS, not about the file. The proofs above ran on a network
where `api` and `web` resolve, which is why they say anything at all.

### 2.9 What is **not** proved

* **No real certificate, no host name, no DNS record.** None exists. `PA-01` criterion 2
  stays *cannot be established* and this changes nothing about that;
* **no browser.** `curl` and `openssl s_client`, not a browser over a real name;
* **the stack was not brought up through `deploy.sh` with the overlay.** The proof used the
  pinned proxy image, the real `nginx.conf`, the mounts the overlay renders and stub
  upstreams — everything the proxy tier does — but not the api and web containers, because
  another lane was mid-deploy and the host had under 6 GB free (§5). The compose rendering
  in §2.6 is what connects the two; **the first run of the overlay against a full stack
  will be on the `R-1` host**, and the runbook's §6 is written for exactly that.

## 3. The credential discipline — and a claim in this repository that was not true

The rule is the owner's and is not negotiable: no credential in a chat message, `.env`
against the fifteen-name allowlist, the API token in `env/alpha.env`, the provider
credential one step further out in `env/provider.env`.

**The certificate's private key follows the same shape and is checked:**

* it lives at `infra/deploy/proxy/tls/privkey.pem`, **on the host, placed by the owner**,
  mode 600, mounted **read-only**;
* it can never be committed. `proxy/tls/.gitignore` ignores every file but itself, and
  `test_proxy_tls_path.py` asks **`git check-ignore`** about `privkey.pem`, `fullchain.pem`
  and `anything.key` — and separately asserts the directory itself stays tracked, or a
  clean clone would have no mount source for docker to find;
* **it cannot appear in `docker compose config`.** Measured with a sentinel key in place:
  `grep -c 'W26HOST-SENTINEL-KEY-MATERIAL'` over the rendered output → **0**, while the
  *path* appears → 1. A bind mount is a path; there is no substitution to leak into.

**And the thing this session found by running the same test on the other secret.** The
brief and `provider.env.example` both said the provider credential *"is never passed to
`--env-file` and therefore never appears in `docker compose config`"*. The second half is
false on this host:

```
$ printf 'ANTHROPIC_API_KEY=W26HOST-SENTINEL-PROVIDER-CREDENTIAL\n' > infra/deploy/env/provider.env
$ docker compose --env-file <alpha.env> -f infra/deploy/compose.server.yml config | grep SENTINEL
21:      ANTHROPIC_API_KEY: W26HOST-SENTINEL-PROVIDER-CREDENTIAL
$ docker compose version
Docker Compose version v5.3.1
```

`config` **resolves `env_file:` into `environment:`** before rendering. The flag that does
not is `--no-env-resolution`, which leaves the `env_file:` reference in place — driven, and
the sentinel does not appear.

**What keeping `provider.env` out of `--env-file` really buys is still real**: those names
never enter compose **substitution**, so nothing can interpolate `${ANTHROPIC_API_KEY}`
into an image tag, a container name or a label. That is worth having and it is what the
comment should have said. `env/provider.env.example` now says it, with the measurement, and
the runbook's §9 tells an operator to treat `docker compose config` output as a secret —
it also prints `AUDITMANAGER_API_TOKEN` and both passwords, which was always true.

**This is a candidate register row and this session may not write one** (`DEBT_REGISTER.md`
is a forbidden hotspot here). Handed to the integrator in §8.

## 4. The runbook, and why it is not in the README

`docs/program/DEPLOYMENT_RUNBOOK.md`. The argument is in its own first section and is
briefly: `infra/deploy/README.md` is the **reference** — one section per file, the
mechanism, the measurement behind each decision — and three things the runbook must carry
are not facts about `infra/deploy/` at all. **`R-4` has two halves still open** and a
procedure that depends on an unanswered owner question has to be able to say so; `PA-01`'s
two criteria belong beside the roadmap they are criteria of; and the order of operations is
a programme commitment rather than a property of any script. The README gained a pointer, a
TLS section and four rows in its file table, and **neither document restates the other**.

It names every prerequisite the clean-clone proof revealed, as `W23-DEPLOY` measured them:
**bash, docker with the compose v2 plugin, curl, sed** — plus `git` to obtain the clone —
and **no `make`, no `npm`, no `.venv`, no `web/node_modules`**. And the one file a human
must write: **`infra/deploy/env/alpha.env`**, which `deploy.sh` refuses to invent in its own
words — *"A deploy that invented an environment would deploy something nobody configured."*
`provider.env` is the second file and is optional: `env_file: required: false`, and
`recorded` mode reads none of it.

## 5. The disk headroom figure — measured, and it is not 8 GB

**The instrument had to be chosen before the number could mean anything.** The shared build
cache on this host held another lane's layers of these same two Dockerfiles, so a build on
the default builder would have hit that cache and measured nothing; and pruning it to get a
cold cache would have sabotaged a live lane. So: an **isolated builder**, which starts
empty and pulls its own base images — which is also what a machine that has never run this
does.

```
docker buildx create --name w26cold --driver docker-container --bootstrap
docker buildx --builder w26cold build --load -f infra/deploy/Dockerfile.api -t m-api .
docker buildx --builder w26cold build --load -f infra/deploy/Dockerfile.web \
  --build-arg NEXT_PUBLIC_API_BASE_URL=/bff/v1 --build-arg NEXT_PUBLIC_INSTANCE_LABEL=alpha -t m-web .
docker buildx du --builder w26cold ; docker buildx rm w26cold      # with df around each
```

| what | measured |
|---|---|
| build cache, both images, cold | **2.592 GB** (`buildx du`); `df` freed **2.42 GiB** when the builder was removed — the two agree |
| the two images | 400 MB + 1.2 GB (`docker images`). Removing both freed **1.01 GiB** here, because this host already had the `python` and `node` bases |
| the four pinned third-party images | **1.08 GB** — postgres 646 MB, MinIO 241 MB, mc 117 MB, nginx 74.5 MB |
| the clone | 69 MB, no `.venv`, no `node_modules` |
| both named volumes after a first deploy | ~76 MB |
| both builds, cold, wall clock | about five minutes |

**One clean-clone cold-cache deploy needs about 5.5 GB**, of which ~2.6 GB is build cache
that `docker builder prune -af` takes straight back.

**So the repeated figure differs, and the difference is worth more than the number.**
*"About 8 GB of build-cache headroom"* comes from `W24-CERT2` §3c, where two builds took
`/` from 8.9 GB to **0 bytes** — on the **third** consecutive deploy, with earlier cache
generations still resident. It is not what one deploy costs; it is what three cost, because
**the cache grows with every build whose sources changed and nothing removes the old
generation.** As a provisioning number 8 GB stands, and the runbook now gives it with that
reason and with the prune that keeps it true.

**The `df` measurement during the build itself was worthless and is not reported**: free
space moved by gigabytes in both directions while another lane deployed and then pruned.
The figures above are attributable — `buildx du` for a builder only this session used, and
`df` across the removal of exactly the artefacts this session created.

**Disk on arrival 11 GB, low point 2.0 GB, 9.5 GB after the teardown.** Nothing of another
lane's was pruned, and the cold builder was removed with its cache.

## 6. `R-4` — what the runbook can say, and what it must not

`R-4` permits real client documents and requires them wiped at the end of the pilot;
`reset.sh` is that commitment, and it dumps and verifies the dump before it drops anything.
**Both halves of `R-4` are still open** (`OWNER_RULINGS_2026-09-17.md` §4: who uploads, and
what event counts as "the end of the pilot"). The runbook therefore:

* **does not appoint anybody.** It records that the person who runs it is whoever holds
  root and wrote `alpha.env` — because the command must be typed with the database and
  bucket names that file configures — and that **one named person must own it before a real
  document is uploaded**;
* **does not invent the trigger.** It states what follows from the shape of the commitment
  rather than from a preference: the trigger must be **a single observable event**, because
  a wipe that waits on somebody's judgment of whether the pilot has "ended" is a wipe that
  does not happen; and **until it is written down, no real client document should be on the
  host**, since `R-4` permits them *because* the wipe is promised. It also separates this
  wipe from the roadmap §6 one, which runs after `PA-01` and before real documents arrive;
* **proves the wipe by writing.** `W18-OPS`: a restored instance that reads perfectly can
  be broken for writing — three S3 metadata keys lost, byte-identical reads, and **409** on
  re-upload. So the after-check is: the app comes back empty, **then a project is created
  and a PDF uploaded and it answers 201 and its bytes come back**, then
  `verify-deployed.sh` still exits 0. After a *restore*, read back byte-identical **and
  re-upload**;
* warns that `--dry-run`'s per-table figures are exact and its **total over-reports**,
  counting one view (`D-39`) — an operator is never told there is less to lose than there
  is, but that screen is the one `R-4` asks them to believe.

## 7. Tests and gate

`tests/integration/composition/test_proxy_tls_path.py` — **9 cases**, no daemon. It holds
the parts of §2 that can stop being true without anyone noticing: no TLS directive in the
always-loaded config; the block staying out of `conf.d`; the three mounts at their exact
targets and read-only; the switch still **`100755` in git**, because a bind mount carries
the host's mode and the image silently ignores a non-executable hook; the disabled branch
still un-installing; the two server bodies not drifting; `git check-ignore` refusing a
private key; the overlay introducing no variable but a port; and `compose.server.yml`
mentioning neither `tls` nor `443`.

**The drift check is shown able to fail** — `test_the_drift_check_can_fail` puts a
one-directive mutation in front of the same function the real check uses, which is the only
form of that proof worth having.

<!-- W26-HOST-GATE -->

## 8. For the integrator

1. **Merge order.** This branch touches nothing `W26-OPS` owns, so it merges in either
   order. The only overlap is textual: both sessions' work is described in
   `infra/deploy/README.md`, and this branch edits its file table, its TLS bullet and adds
   one section. If `W26-OPS` also edits that file, expect a conflict there and nowhere else.
2. **A register row this session could not write.** `DEBT_REGISTER.md` is a forbidden
   hotspot here. The row: *`docker compose config` prints the provider credential*, because
   `config` resolves `env_file:` into `environment:` (Compose v5.3.1) — the comment in
   `env/provider.env.example` claimed otherwise and has been corrected in place. Check:
   put a sentinel in `infra/deploy/env/provider.env` and
   `docker compose --env-file infra/deploy/env/alpha.env -f infra/deploy/compose.server.yml config | grep SENTINEL`.
   Tree: `infra/deploy/`. It is a **documentation** defect, not a leak — nothing in this
   repository runs that command and sends the output anywhere — but it is the kind of
   sentence an operator trusts.
3. **What still blocks `PA-01` 1 and 2 is `R-1` and only `R-1`**: a host, a name, a
   certificate, a DNS record, and who holds root.
4. **What the owner is still owed on `R-4`**: who uploads a real document, and the single
   observable event that triggers the wipe. The runbook's §7 states the shape the answer
   has to take and refuses to guess it.
5. **No tag, no checkpoint, nothing pushed to `main`.** Every stack and container this
   session created was removed by ID; the cold builder was removed with its cache; no other
   lane's cache, container or volume was touched.
