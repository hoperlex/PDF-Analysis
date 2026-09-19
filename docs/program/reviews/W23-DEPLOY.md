# `W23-DEPLOY` — `infra/deploy/deploy.sh`, and which half of `PA-01` criterion 1 it closes

**Session** `W23-DEPLOY`. **Base** `5ed72cc` (`origin/dev`), which contains `6e07b97`.
**Branch** `agent/w23-deploy`. **Worktree** `/root/w23deploy`.

## 0. The premise I checked first, and it was false

The brief quotes `PA-01` criterion 1 as:

> `deploy.sh` brings the stack up from a clean clone on a machine that has never run it,
> and **the schema the migrations produce is the one the application expects**.

`docs/program/ALPHA_ROADMAP.md:313` does not say that. It says:

> `deploy.sh` brings the stack up from a clean clone on a machine that has never run it,
> and **the schema the running app serves conforms to the frozen
> `contracts/api/v1/openapi.json`** — the same check the gate runs, re-run against the
> deployed process rather than against a build artifact;

The second clause is about the **API schema**, not the database schema. The brief's STEP 2
item 3 therefore points at `make check-db` and `tests/integration/db`, which bear on a
different claim entirely. **Both are answered below**, and which one the criterion actually
asks for is stated rather than blurred — but if I had followed the brief's wording I would
have produced a careful proof of a clause nobody wrote down.

`W21-CERT.md` already drove the real second clause and recorded it as holding. So the only
part of criterion 1 that was genuinely open was the first clause, and the missing artefact.

## 1. What is delivered

| Path | What it is |
|---|---|
| `infra/deploy/deploy.sh` | 12 guards, `# >>> guard:` markers, `reset.sh`'s form |
| `tests/integration/composition/test_deploy_script_refusals.py` | 39 cases; every guard shown able to fail by deletion |
| `infra/deploy/README.md` | the runbook entry, and what a second run really does |

Nothing under `src/`, `web/`, `contracts/` or the `Makefile` was touched. `OD-16` needed no
break record: this is a script, like `reset.sh`, and not a tenth root target.

## 2. The twelve guards, and the deletion proof for each

Every guard is deleted from a copy of the script and the refusal must vanish. A message can
be printed by a guard that is unreachable; a deletion cannot be faked. `docker` is replaced
on `PATH` by a stub that records arguments and answers the reads, so nothing in the suite
can build, start or replace anything.

| # | Guard | Refuses | Evidence it came first | Deletion case |
|---|---|---|---|---|
| 1 | `known-options` | `--dryrun` and anything else unrecognised | empty `docker` log | ✓ |
| 2 | `env-file-present` | a missing/unreadable `alpha.env` | empty `docker` log | ✓ |
| 3 | `instance-configured` | an environment naming no instance/port/db/bucket | empty `docker` log | ✓ |
| 4 | `placeholder-secrets` | secrets still equal to `alpha.env.example`'s published values | empty `docker` log | ✓ |
| 5 | `compose-file-present` | a missing `compose.server.yml` | empty `docker` log | ✓ |
| 6 | `build-context-complete` | a clone missing paths the Dockerfiles `COPY` | empty `docker` log | ✓ |
| 7 | `port-not-foreign` | a published port held by another instance | log has `ps`, no `up` | ✓ |
| 8 | `images-built` | a failed build, **and** a build that exits 0 with no image | log has `build`, no `up` | ✓ |
| 9 | `services-healthy` | any service not `running/healthy` (proxy: `running/none`) | stack up, still refuses | ✓ |
| 10 | `migrations-at-head` | no `FOUNDATION-CHECK OK check-db` sentinel | stack up, still refuses | ✓ |
| 11 | `proxy-answers` | 502/503/504 separately from every other non-200 | stack up, still refuses | ✓ |
| 12 | `schema-conforms` | a served document that does not conform, **and** one that is not JSON | stack up, still refuses | ✓ |

**Six refuse before `docker` is touched at all**, and for those the evidence is the strongest
this suite has: the call log does not exist. Two more sit before the `up`, and for those the
evidence is a log with no `up` in it — `up` being the only call in this script that replaces
a running container. A meta-test pins the count at 12 and fails on a guard added without a
case. A control case proves the script does not simply refuse everything.

Two guards carry an extra refusal each, because two different things must not be told to an
operator in the same words: `images-built` separates "the build failed" from "the build
exited 0 and made no image", and `schema-conforms` separates "the document could not be
read" from "the document does not conform".

**39 cases, all passing**, no daemon touched:

```
$ PYTHONPATH=src .venv/bin/python -m pytest \
    tests/integration/composition/test_deploy_script_refusals.py -q
39 passed in 15.23s
```

## 3. The clean-clone run, pasted

A `git clone` into a directory that had never run this, with its own instance and port. The
**builder cache was emptied first** (`docker builder prune -af`, `Total: 0B`) and neither
`auditmanager-w23deploy-api` nor `-web` existed, so nothing was reused: **0 of the build's
steps reported `CACHED`**. The clone has no `.venv`, no `web/node_modules` and no
`alpha.env` — and it needs none of them, because `deploy.sh` uses only `bash`, `docker`,
`curl` and `sed`. **No `make bootstrap`, no `npm ci`.**

### 3a. What a clean clone does *not* have, and the script says so

```
$ ./infra/deploy/deploy.sh
deploy.sh: REFUSED: the deployment environment /root/w23clone/infra/deploy/env/alpha.env is missing or unreadable.
  A clean clone does not carry one -- env/alpha.env is git-ignored on purpose,
  because it holds this instance's secrets. Write it first:
      cp infra/deploy/env/alpha.env.example infra/deploy/env/alpha.env
      chmod 600 infra/deploy/env/alpha.env    # then edit EVERY value in it
EXIT=3
```

Then doing exactly what it says, and **nothing more** — copying the example unedited:

```
$ cp infra/deploy/env/alpha.env.example infra/deploy/env/alpha.env
$ chmod 600 infra/deploy/env/alpha.env
$ ./infra/deploy/deploy.sh
deploy.sh: REFUSED: POSTGRES_PASSWORD is still the value shipped in alpha.env.example.
    POSTGRES_PASSWORD = change-me-disposable-postgres-password
  That value is published in this repository. It is a placeholder, not a
  secret, and alpha.env.example says so beside it. Nothing was built.
  Generate the token with:
      python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
EXIT=3
```

That is the environment being the **operator's input**, not the clone's, and it is the one
thing "with the script and nothing else" cannot cover: `env/alpha.env` is git-ignored
because it holds secrets, so a clean clone necessarily does not have one. The script
refuses rather than inventing one.

### 3b. The run itself — 21:38:28 to 21:40:13, 105 s, exit 0

Build output elided; every other line is verbatim.

```
deploy.sh: instance   auditmanager-w23deploy
deploy.sh: repository /root/w23clone3
deploy.sh: port       31520
deploy.sh: database   auditmanager_w23deploy
deploy.sh: bucket     auditmanager-w23deploy

-- building the images --
 Image auditmanager-w23deploy-web Built
 Image auditmanager-w23deploy-api Built
  auditmanager-w23deploy-api and auditmanager-w23deploy-web are built

-- bringing the stack up --
 ... postgres Healthy, s3 Healthy, s3-init Exited, migrate Exited,
     api Healthy, web Healthy, proxy Started

-- reloading the proxy --
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
reload-proxy.sh: the proxy re-resolved its upstreams.

  postgres  running/healthy
  s3        running/healthy
  api       running/healthy
  web       running/healthy
  proxy     running/none

-- the database is at the head this code expects --
  check-db: target      postgresql+psycopg://auditmanager_w23deploy:***@postgres:5432/auditmanager_w23deploy
  check-db: server      PostgreSQL 17.11 (Debian 17.11-1.pgdg13+2)
  check-db: dialect     postgresql via psycopg
  check-db: head        expected 0005_truncated_call_status
  check-db: current     0005_truncated_call_status
  check-db: write probe transaction committed nothing and rolled back cleanly
  FOUNDATION-CHECK OK check-db

-- the published port answers --
  200 on http://127.0.0.1:31520/api/v1/openapi.json

-- the served schema conforms to the frozen contract --
  frozen ops : 15
  served ops : 15
  differences: 0

deploy.sh: auditmanager-w23deploy is up at http://127.0.0.1:31520
deploy.sh: every service healthy, the database at head, the served schema conforming.
DEPLOY_EXIT=0
```

And the stack it produced **is** the clone it was built from:

```
$ ./infra/deploy/verify-deployed.sh
  src/                                141 files, identical
  db/                                   9 files, identical
  contracts/                           34 files, identical
  fixtures/recorded/                    7 files, identical
  docs/program/P02_LOCK.json            1 files, identical
  infra/deploy/serve.py                 1 files, identical
  web/                                218 files, identical
verify-deployed.sh: the deployed stack IS this tree (47dbcb6).
exit=0
```

## 4. THE DEFECT MY OWN SCRIPT HAD, AND ONLY RUNNING IT FOUND IT

The first clean-clone drive reached the twelfth guard and died there:

```
-- the served schema conforms to the frozen contract --
  Traceback (most recent call last):
    File "<string>", line 7, in <module>
  IsADirectoryError: [Errno 21] Is a directory: '/served.json'

deploy.sh: REFUSED: the document this stack serves does not conform to the frozen contract.
```

The guard mounted the fetched document with `-v "$SERVED:/served.json:ro"`. `$SERVED` comes
from `mktemp`, so it is under `/tmp` — and **this host's docker is the snap build, whose
mount namespace has `/tmp/snap-private-tmp/snap.docker/tmp` mounted over `/tmp`**. Measured
minimally, with both halves side by side:

```
$ T=$(mktemp); echo '{"probe":1}' > "$T"
$ docker run --rm -v "$T:/probe:ro" alpine sh -c 'ls -ld /probe; cat /probe'
drwxr-xr-x 2 root root 4096 /probe          <- an empty DIRECTORY
$ docker run --rm -v /root/w23probe/p.json:/probe:ro alpine sh -c 'ls -ld /probe; cat /probe'
-rw-r--r-- 1 root root 12 /probe
{"probe":1}                                  <- the same bind, from /root, is the file
$ grep ' /tmp ' /proc/$(pgrep -x dockerd)/mountinfo
625 592 253:3 /tmp /tmp rw,relatime master:1 - ext4 /dev/vda3 rw
83 625 253:3 /tmp/snap-private-tmp/snap.docker/tmp /tmp rw,relatime - ext4 /dev/vda3 rw
```

Docker's answer to a bind source it cannot resolve is **not** an error: it creates an empty
directory at the destination and starts the container anyway.

**This is `reset.sh`'s `--restore` finding in a second costume.** There, a relative path
handed to `docker run -v` was a volume *name*. Here, an absolute path under `/tmp` is
nothing at all. The lesson is the same one and it is now written into both files: **a `-v`
source is resolved by the daemon, not by the shell that typed it**, and it fails by
producing something plausible rather than by stopping.

`mktemp -p` somewhere else would have fixed this one path and left the class open, so the
mount is gone: the served document is **piped in on stdin**, which is the idiom `reset.sh`
already uses (`compose exec -T postgres pg_restore ... < "$DUMP_DIR/database.dump"`). The
engine stays a mount because it lives in the repository, which the daemon does resolve —
the same place `reset.sh` mounts `object_attrs.py` from. A test pins the shape, not the
directory: the suite fails if `:/served.json:ro` ever appears in a docker call again.

It also split the refusal in two. "The document could not be read" reported as "the document
does not conform" sends somebody to look at the contract when the fault is in the fetch.

## 5. The schema clause — what answers it, and what does not

### The clause the criterion actually contains (the API schema)

**`tests/contract/api_v1/openapi_conformance.py`'s `surface()` and `differences()`, run
against the deployed process.** `deploy.sh` mounts that module into a one-off container from
the api image — which already carries the frozen `contracts/api/v1/openapi.json` — and pipes
it the bytes the proxy just served. It is **the gate's own engine**, not a second
comparison, and that is load-bearing: revision 1 of `ALPHA_ROADMAP.md` objected to FastAPI
precisely because a generated document creates a second schema authority, and §3 `T-1`
answers that with "not an assurance but a gate". A deploy script that reimplemented the
comparison would be a third authority.

Result on the deployed stack: **15 frozen operations, 15 served operations, 0 differences.**

**And the live check is shown able to fail**, because a comparison that has never reddened
is not evidence. Driven against the running stack, statuses taken from `$?` directly and
never through a pipe:

```
served document, unmodified                         -> exit 0   differences: 0
the same document, paths./projects.post.operationId
  changed to "plantedDifference"                    -> exit 1   differences: 1
    paths./projects.post.operationId: the contract has "createProject",
                                      the generated document has "plantedDifference"
a body that is not JSON                             -> exit 2
    the document served at /api/v1/openapi.json is not JSON: Expecting value: line 1 column 1
```

`verify-deployed.sh` deliberately does **not** make this comparison, and its header says
why: the frozen and generated documents legitimately differ, so there is no digest to
compare, and a probe watching the API surface was green on the exact drift that created
`D-27`. That script answers "is this stack this tree"; this guard answers "is what it serves
the contract". Two different questions, and both now have an answer.

### The clause the brief substituted (the database schema)

`make check-db` **is** the right instrument and `deploy.sh` runs it — but it must be said
exactly what it proves. `auditmanager.shared.db.check` proves **connectivity, the dialect, a
real authenticated write probe, and that the revision stamped in the database equals the
head the code declares**. It does *not* compare columns, constraints or triggers against
what the application expects; it is a revision-identity claim.

What proves the *shape* is `tests/integration/db/` — `test_schema_shape.py` reads
`information_schema` and `pg_trigger` against declared expectations,
`test_schema_invariants.py` performs the write each guard exists to stop, and
`test_migration_lifecycle.py` asserts clean install and re-run safety. Those run in the gate
against a freshly migrated database, **not against the deployed one**.

So the honest split: *the deployed database is at the revision this code expects* is proved
on the deployed stack, by the application's own check, in the application's own image —
with the `FOUNDATION-CHECK OK check-db` sentinel as the evidence rather than an exit code,
which is that module's own stated rule. *That revision's schema is the shape the application
expects* is proved in the gate, and running the gate's db suite against a deployed instance
is not something this script does or should do: those tests create and drop databases.

## 6. Idempotence — the part that is true, and the part that is not

Run twice from the same clone. Measured, not asserted:

* **no layer is rebuilt** — every step of both images reports `CACHED`;
* **no data is touched** — `postgres`, `s3` and `proxy` report `Running` and keep their
  container IDs; both named volumes keep the first run's creation timestamp;
* **`api`, `web` and `migrate` ARE recreated.**

The cause is not the script. A fully cached `compose build` still yields a **new image ID**,
because BuildKit writes a fresh `created` timestamp into the image config; `compose up -d`
then recreates every service using that image. Two consecutive builds of an untouched tree:

```
df1242a7736d06877fdbc7877ba1f413bd05c9a834fbbdbe766f8a7939eb4d29
3be029727fb6fde71cf57ffb9a6c45df234b7eacfe845ebee90788232b1244f8   DIFFERENT
```

`SOURCE_DATE_EPOCH=1700000000` was tried on both builds and does **not** fix it on this
compose/BuildKit. `migrate` re-running is a no-op by construction — `alembic upgrade head`
against a database already at head applies nothing, and `migrations-at-head` proves it
afterwards.

**So the roadmap's acceptance clause *"deploy.sh run twice changes nothing the second time"*
is NOT yet true, and I have recorded it as not-yet-true rather than working around it.** The
header comment of `deploy.sh` said "a second run changes nothing" until I ran it twice; that
sentence was false and is now the measurement above. Making the clause true means preserving
the image *identity* when a build produced identical content — a mechanism with its own
failure modes, which is not something to smuggle in at the end of a session.

## 7. Which half of criterion 1 I proved, and which I did not

> *"`deploy.sh` brings the stack up from a clean clone on a machine that has never run it,
> and the schema the running app serves conforms to the frozen
> `contracts/api/v1/openapi.json`."*

**PROVED, on this host, today:**

* `deploy.sh` exists, and `W21-CERT`'s *"there is nothing to run"* no longer holds;
* it brings the whole stack up **from a clean clone** — a directory that had never run it,
  with an empty builder cache and no images, 0 cached build steps, exit 0 in 105 s;
* the second clause, **0 differences** between the frozen contract and what the deployed
  process serves, by the gate's own engine, with the comparison shown able to fail;
* the deployed stack is byte-identical to the clone it came from (`verify-deployed.sh`, 0);
* every one of the twelve guards is shown able to fail by deletion.

**NOT PROVED, and why:**

* **"on a machine that has never run it"** — this machine has run this stack many times. The
  *clone* had never run it; the *host* is not clean and cannot be made so. That is the
  honest limit of the word "machine" here, and only `R-1`'s host settles it.
* **The operator's environment is not in the clone.** `env/alpha.env` is git-ignored because
  it holds secrets, so "with the script and nothing else" is true of everything except the
  one file a human must write. The script refuses rather than inventing one. This is a
  finding about the criterion's wording, not about the script.
* **"run it twice and the second changes nothing"** — §6. Not true yet, measured.
* **Fetch, switch, and rollback on a failed health check** — absent on purpose. All three
  are claims about a server with a previous version on it. What *is* here is the ordering
  they rest on: build before switch, so a failed build leaves whatever was serving still
  serving. That is proved by deletion (`images-built`), not by a host.
* **TLS** — untouched, still `R-1`.

**Criterion 1 remains "cannot be established" in full**, but the reason has changed. It was
*"there is nothing to run"*. It is now *"there is no host that has never run it, and no
previous version to roll back to"* — which is `R-1`, and `R-1` alone.

## 8. Anything false in the brief

1. **The criterion 1 quotation is not the roadmap's.** §0. The second clause is about the
   served API schema, not the database schema; the brief's STEP 2 item 3 sends the session
   at `make check-db` and `tests/integration/db`, which answer a different claim. This is
   the material one.
2. **"the missing piece is a script nobody has written"** — true, and confirmed:
   `git log --all -- '**/deploy.sh'` is empty and no `deploy.sh` exists in the tree.
3. **"`W14-OPS` … was never dispatched — there is no review file for it"** — true. It is
   named in `ALPHA_ROADMAP.md`, `W14-PKG.md` and `W21-CERT.md`, and there is no
   `docs/program/reviews/W14-OPS.md`.
4. **`reset.sh`'s twelve guards, markers, deletion proof, meta-test** — all true, verified.
5. **"One alpha stack answers on 31500 and is not yours"** — true, and untouched. See §9.
6. Minor: `W21-CERT.md` cites `infra/deploy/README.md:142` for the `deploy.sh` boundary; at
   this base it is line 209. The content held, the line number had drifted.

## 9. The alpha stack on 31500

**I did not touch it**, and it still answers `200` on `/api/v1/openapi.json`. Its containers
were created at 13:32Z and 2026-09-18; this session began at 16:11Z.

`verify-deployed.sh` against it and the `planning/prototype-roadmap` working tree exits
**6 — it does not match**, with **17 files disagreeing, every one of them under `web/`**:
3 missing from the image, 14 with different bytes. The api image is identical on all six of
its mappings (`src/` 141 files, `db/` 9, `contracts/` 34, `fixtures/recorded/` 7,
`P02_LOCK.json`, `serve.py`).

**This drift is not mine and predates me.** My branch touches exactly three files —
`infra/deploy/deploy.sh`, `tests/integration/composition/test_deploy_script_refusals.py` and
this review — and none is under `web/`. I ran nothing against `auditmanager-w19a`. **So: I
did not leave it matching, because it was not matching when I arrived**, and repairing it
would mean rebuilding an instance I do not own with `web/` changes I may not touch.

## 10. Measurements

| | |
|---|---|
| HEAD on arrival | `5ed72cc`, clean; contains `6e07b97` |
| Disk before | 12 GB free (90% used) |
| Disk after, pruned | 9.7 GB free (92% used) |
| `docker builder prune -af` | run three times; 4.398 GB, 2.29 GB, and 0 B reclaimed |
| Clean-clone deploy | 105 s, 0 cached build steps, exit 0 |
| Second run on the same clone | 16 s, every step `CACHED`, exit 0 |
| Refusal suite | 39 passed |

Every stack this session created was torn down with `down --volumes`, and both instance
images were removed. No `w23deploy` container, volume, network or image remains.
