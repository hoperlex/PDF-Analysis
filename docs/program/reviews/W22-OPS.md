# `W22-OPS` — the wipe rehearsal tells the truth, and the stack can be asked whether it is the tree

## 0. Arrival, and the base measured on this lane

| | |
|---|---|
| Base | `origin/dev` = `313e753` *(docs(register): three rows from the committed journey, and D-27 measured again)* |
| Worktree | `/root/w22ops`, branch `agent/w22-ops` |
| Lane | instance `gate-w22a`, PostgreSQL `55890`, S3 `59490`/`59491`, database `audit_w22a`, bucket `auditmanager-gate-w22a` |
| Disk on arrival | `df -h /` — 119G total, 98G used, **15G available**, 87% |
| Disk at close | 101G used, **12G available**, 90%. **No image was built.** |
| Started | 2026-09-19 17:43:26 +05 |
| Finished | 2026-09-19 18:29 +05 — **46 minutes wall clock**, of which about 12 are the three full gate runs |

```
make gate                                   # exit 0, read from $?, never through | tail
  foundation   35 passed  (twice: check-db, check-storage)
  battery      1817 passed, 5 skipped, 168 subtests passed in 220.82s
  frontend     47 files, 681 tests passed
```

Identical to the figures the brief carries.

---

## 1. `D-24` — the rehearsal counts what it would destroy

### What the screen did, measured on a database I wrote myself

I brought up an alpha instance of my own (`auditmanager-w22ops`) from `compose.server.yml`
using only its pinned third-party images — **`postgres`, `s3` and `s3-init` only, so no
image was built** — migrated it, and wrote a project, a document, a version, a manifest
entry and a blob through the schema's own state machines.

Two reproductions, and the second is deterministic:

* **in one psql session, straight after a committed `INSERT`** — `count(*)` said **5**,
  `n_live_tup` said **4**. That is `W21-CERT`'s "printed `(2 rows)` where the truth was 4",
  exactly: the estimate is short by the most recent writes because the statistics are
  reported asynchronously;
* **with the statistics not yet collected** — which is what a freshly written database *is*,
  and what `pg_stat_reset()` and a crash-recovered server both reproduce on demand —
  **every table printed `(0 rows)`** while all of that data was there.

The screen, at `313e753`:

```
-- tables that would be dropped with schema public --
alembic_version  (0 rows)
...
document  (0 rows)
document_version  (0 rows)
input_manifest_entry  (0 rows)
project  (0 rows)
stage_result  (0 rows)

-- objects that would be purged from the bucket --
[2026-09-19 12:56:37 UTC]     6B STANDARD blobs/aa/bb/K0
[2026-09-19 12:56:37 UTC]     6B STANDARD blobs/cc/dd/K1
  total: 2 objects
```

Five projects and a full document chain, reported as nothing, beside a bucket half that is
exact down to the byte. `R-4` says this is the screen an operator reads before agreeing
that real client documents leave the host.

### The same screen now

```
-- tables that would be dropped with schema public --
alembic_version  (1 rows)
blob  (1 rows)
contract_state_transition  (24 rows)
document  (1 rows)
document_version  (1 rows)
input_manifest_entry  (1 rows)
project  (5 rows)
...
  total: 34 rows in 17 tables

-- objects that would be purged from the bucket --
[...]  blobs/aa/bb/K0
[...]  blobs/cc/dd/K1
  total: 2 objects
```

One statement over the seventeen tables, `query_to_xml` + `format('%I')` so a table name is
never concatenated into SQL, and a total line in the bucket half's own shape — the two
halves of the screen now answer the same way and with the same authority. The total also
tells an operator at a glance whether an instance is empty: after the live wipe below it
read `total: 25 rows in 17 tables`, which is the seeded contract rows and nothing else.

### What it costs — measured, not reasoned about

Three runs at each size; wall clock of the whole `docker exec` + psql round trip.

| database | exact | estimate |
|---|---|---|
| pilot-sized (34 rows) | 0.16–0.19 s | 0.16–0.17 s |
| one table at 1 000 000 rows | 0.17–0.19 s | 0.15–0.16 s |
| one table at 10 000 000 rows | **0.32–0.47 s** | 0.15–0.17 s |

It is linear in rows, and at every size a pilot will reach the difference is smaller than
the round trip that carries it. Ten million rows buys about two tenths of a second. That is
the whole price, and it is written beside the query rather than left for the reader to
assume it is either free or ruinous.

One caveat I owe: one of the seventeen — `finding_current_verdict` — is a **view**, so its
line runs the view's query rather than a table scan. At the shapes above that is in the
noise; a view expensive enough to matter would be a reason to look at the view.

### A twelfth guard, `rehearsal-counted`

`D-24` has a second face I did not expect and found by stopping the postgres container. At
`313e753`, a rehearsal that could not reach the database printed

```
-- tables that would be dropped with schema public --
  (could not read the schema; is the stack up?)

-- objects that would be purged from the bucket --
[...]  total: 2 objects

reset.sh: a real run would first write a dump under ...
OLD_EXIT=0
```

— an exact bucket listing, a table section with no numbers in it, a calm closing sentence,
and **exit 0**. That is the same untruth as `(0 rows)` wearing different clothes. It is now
a refusal with exit 3, driven the same way before its test was written:

```
reset.sh: REFUSED: the rehearsal could not count what is in auditmanager_w22ops.
  Nothing was touched -- a rehearsal reads and never writes. But this screen
  is what you would agree to a wipe on, so it refuses rather than showing you
  a table list with no numbers beside it. Is the stack up?
EXIT=3
```

**Marker count 11 → 12**, and the meta-test moved with it.

---

## 2. `D-27` — a probe, and the argument for what it compares

### The brief's suggestion does not work, and that is measured

`D-27` proposes "the served document's digest — or simply the commit the image was built
from". I tried both against the running stack before writing anything.

1. **There is no digest to compare.** `api/app.py` generates the served document and
   `contracts/api/v1/openapi.json` is frozen by hand. They differ — and they still differ
   after dropping `description`, `summary` and `title`, in `paths`, `components`, `info`
   **and** `security`. That is not drift; it is why the tree carries
   `tests/contract/api_v1/openapi_conformance.py` as a conformance *engine* rather than a
   comparison.

2. **A document comparison is blind to the drift this row was created by.** `carrier.py`
   was missing from the deployed image. Generated from this tree, the document is
   `083b296e09d5a420…`; generated from a copy of this tree with a line appended to
   `src/auditmanager/runs/carrier.py`, it is `083b296e09d5a420…` — byte for byte. A probe
   watching the API surface would have been **green on the exact defect that made the row**,
   and green is what a session would then have certified.

3. **A commit label is the builder's claim, not the image's contents** — and it needs a
   rebuild before it can say anything, so it cannot answer for the stack already running,
   which is the only stack anybody ever needs to ask about.

### What it does instead

`infra/deploy/verify-deployed.sh`. One command. Exit **0** it is this tree, **6** it is not,
**4** the question could not be answered — and **4 is a failure**, because the thing this row
is about is a check nobody notices, and a probe that shrugs is that check.

It reads the two Dockerfiles' own `COPY` lines — the idiom `Dockerfile.api` already uses on
the Makefile's `UV_VERSION` — and for every git-tracked file under them compares the bytes in
the working tree to the bytes inside the running container. A newly copied path is covered
without anyone remembering; a parse that cannot find `src/` is exit 4 with *"do not trust
this green"* rather than a comparison of nothing.

It compares against the **working tree**, not `HEAD`: "is the deployed stack the repository
in front of me" is the question an operator has, and a dirty tree is itself a reason the
answer is no. `HEAD` and the dirty state are printed.

### It failed on its first run, and the brief is what it contradicted

> "One alpha stack answers, on 31500, rebuilt from `313e753`'s code."

```
verify-deployed.sh: instance   auditmanager-w19a
verify-deployed.sh: proxy      http://127.0.0.1:31500

-- the proxy answers --
  200 on /api/v1/openapi.json

-- the api image against the tree --
  src/                                141 files, identical
  db/                                   9 files, identical
  contracts/                           34 files, identical
  fixtures/recorded/                    7 files, identical
  docs/program/P02_LOCK.json            1 files, identical
  infra/deploy/serve.py                 1 files, identical

-- the web image against the tree --
  /web/package.json  DIFFERENT BYTES
      tree  023d0b3e95796aa778045038c7b32d9b2c04a3f1184dca479b397db06d6ed76b
      image 73cbb4090a47c9a256510618212ea6806b5c35f8542a74d79f64ec4fd000a445
  web/                                215 files: 0 missing, 1 different, 0 unexpected

verify-deployed.sh: the deployed stack is NOT this tree -- 1 file(s) disagree.
PROBE_EXIT=6
```

The **api** image is current. The **web** image is not: it carries `web/package.json` from
before `89600f6`, whose `e2e:pc01` script still reads `node scripts/reserved-forwarder.mjs`.
The images were built at **13:31:56** and **13:32:07**; `19ad19d` merged at **13:43:31**.
**Eleven minutes.** This is `D-27`'s own story happening again, to me, in the brief that sent
me to close it — and it took one command instead of an afternoon.

### The proof it fails when the stack is stale

Two, and neither needs a rebuild.

* **Live**, above: exit 6, naming the file and both digests.
* **Against a genuinely old stack.** `auditmanager-w15b`'s api container, built on 18
  September, listed against this tree's tracked files:
  `src/auditmanager/runs/carrier.py` — **missing from the image**, by name. The file `D-27`
  is about, found by the mechanism that closes it.
* **In the gate**, hermetically: `tests/integration/composition/test_deployed_stack_probe.py`,
  17 cases against a `docker` and a `curl` that reach nothing — a file absent, a file whose
  bytes differ, a file in the image that is not in the tree, a 502, a proxy that does not
  answer, no container, a Dockerfile it cannot parse, and three that tie the probe to the
  Dockerfiles that actually ship.

### The proxy, which is the same row's other face

The brief says nginx held a dead upstream after a rebuild and everything answered 502 until
the proxy was restarted. **I did not take that on trust, and driving it changed what I wrote
down.** With a pinned nginx and a throwaway upstream on this host:

```
1. fresh stack:                      200
2. upstream container replaced:      200      <- the same address came back
...
the name 'upstream' now resolves to: 192.168.80.50
through the proxy, no reload:        502      upstream=192.168.80.7:80
after nginx -s reload:               200      upstream=192.168.80.50:80
```

The premise is true, **and it is intermittent** — a replaced container usually gets its old
address back, and then nothing looks wrong. That is why it survived three waves: *"the last
rebuild was fine"* is not evidence about the next one.

So: `infra/deploy/reload-proxy.sh`, a step with a name, because the thing that goes wrong is
that somebody stops after the build. It tests the configuration first — a reload with a
broken one is *refused* by nginx and the old workers keep serving, so the command would
otherwise succeed at leaving the 502 in place. `verify-deployed.sh` asks the proxy **before**
it compares anything, so a dead upstream is told apart from a stale image. `README.md` now
makes a rebuild three commands rather than one.

---

## 3. `D-26` — the reason, not the number

`proxy/nginx.conf`'s *"A model run is slow. The default 60 s read timeout would cut
`startRun` off mid-call"* is false, checked against the tree and not inherited: `startRun`
answers `202` and the browser polls `getRunStatus` (`routers/runs.py:46`), so the failure
the 300 s was bought against — a gateway error to a browser with a run still executing
behind it — cannot occur at any document length.

**The 300 s stands.** It now bounds a cap-sized `uploadDocument`, measured in `W20-EXEC` at
0.85–0.87 s, which is a *floor* rather than a worst case because nothing in this repository
measures an accepted cap-sized upload end to end through nginx. Lowering it would trade a
measured margin for a guess. `W20-EXEC` argued that and I agree; only the reason changed.
`nginx -t` on the edited file, inside the alpha stack's own network: syntax ok.

### Four more stale counts, and the class they live in

While in the file: `nginx.conf:7` and `:59`, `Dockerfile.api:1` and
`env/alpha.env.example:61` all still said **twelve operations** after `R-5` made it fifteen.
`nginx.conf`'s *"twelve paths"* is correct and is left alone.

**`D-23`'s guard could not see any of them.** `test_surface_counts_in_prose.py` scans
`src/auditmanager/api` and `infra/deploy`, but only files whose suffix is `.py` or `.md` —
so `.conf`, `Dockerfile.*` and `.example` are outside it. The row's own words are *"a claim a
checker cannot read is a claim nobody is checking"*, and this is that, one file class over.

**Recommended, and not mine to do:** widen `_api_source_files()`'s suffix set to take
`.conf`, `.example`, `.yml` and `Dockerfile*`. I did not touch that file — it is not in my
ownership — so this is a finding rather than a fix.

---

## 4. The live run — rehearse, wipe, restore

Driven end to end on **my own lane**, never against 31500. The api image was needed for
`object_attrs.py` and for re-running migrations; rather than build one I `docker tag`ged the
existing `auditmanager-w19a-api`, which costs no disk and no build, and removed the tag
afterwards.

```
--dry-run                  exit 0   17 tables / total 30 rows, 3 objects listed exactly
--yes-destroy-everything   exit 0   dump verified -- database.dump readable, 3/3 objects mirrored
                                    then: 0 projects, 0 objects, total 25 rows in 17 tables
--restore <dump>           exit 0   3 objects and 30 rows back, all five attributes intact
```

### And the wipe's own restore was broken

**Found only by running it, with the exact command the script prints at the end of a wipe.**

```
infra/deploy/reset.sh ... --restore infra/deploy/dumps/auditmanager-w22ops-20260919T131449Z

reset.sh: restoring from infra/deploy/dumps/auditmanager-w22ops-20260919T131449Z
Error response from daemon: create infra/deploy/dumps/auditmanager-w22ops-...:
  includes invalid characters for a local volume name ...
  If you intended to pass a host directory, use absolute path
RESTORE_EXIT=1

=== after the restore:
project|1   document|1   blob|1
  total: 0 objects
```

The object half mounts the dump with `docker run -v "$RESTORE:/dump:ro"`, and to docker a
**relative** path there is a volume *name*, not a directory. The database half had already
run. What was left is **precisely the instance `restore-complete`'s own comment calls worse
than an empty one** — *"lists a document and cannot serve it… it looks recovered"* — and the
documented way to put a dump back was the way that produced it. Both the script's closing
message and `README.md` print that relative path.

Two repairs:

* the path is resolved to an absolute one before anything is touched (a directory that does
  not exist still reaches the guard rather than dying in the shell);
* **the bytes go back before the rows.** Either half can fail; of the two halves,
  bytes-without-rows looks exactly as empty as it is, and rows-without-bytes misleads the
  person reading the screen. The misleading one goes last.

Re-driven with the same relative path: exit 0, three objects and thirty rows back, and
`mc stat` shows all five published attributes on the restored object.

---

## 5. The guards — what reddened, and how the count moved

`# >>> guard:` markers: **11 → 12**. `rehearsal-counted` is the new one, and `restore-complete`
gained a repair in front of it rather than a widening.

Every case below was run against the script as it stands at `313e753` and against the script
as it stands now. Red there, green here — the "shown able to fail" half done by deletion for
the guard, and by the base script for the repairs.

| case | red at `313e753` | green now |
|---|---|---|
| `TestTheRehearsalRefusesRatherThanShowingNoNumbers::test_a_rehearsal_that_cannot_count_is_refused` | ✓ | ✓ |
| `…::test_that_guard_is_shown_able_to_fail` *(guard deleted from a copy)* | ✓ | ✓ |
| `…::test_the_count_is_a_count_and_not_the_statistics_estimate` | ✓ | ✓ |
| `test_every_guard_in_the_script_has_a_case_here` *(the 11→12 meta-count)* | ✓ | ✓ |
| `TestTheRestorePutsBothHalvesBack::test_a_relative_dump_directory_is_mounted_as_an_absolute_path` | ✓ | ✓ |
| `…::test_the_bytes_go_back_before_the_rows` | ✓ | ✓ |

The suite's two invariants are kept. Nothing in it can destroy anything — `docker` is still a
stub on `PATH` — and an empty call log is still the evidence for the guards that run before a
connection. The two that run *after* one, `dump-verified` and now `rehearsal-counted`, read
the log for what is **not** in it instead, and the module docstring now says so rather than
leaving the exception unstated.

`test_the_count_is_a_count_and_not_the_statistics_estimate` reads the script's **executable
lines only**: the comments name `n_live_tup` on purpose, because they are what records why it
is not used, and a guard that reddened on its own explanation would teach the next session to
delete the explanation.

---

## 6. The gate

```
make gate                                   # GATE_EXIT=0, read from $?
  foundation   35 passed  (check-db, check-storage)
  battery      1839 passed, 5 skipped, 168 subtests passed in 227.64s (0:03:47)
  frontend     47 files, 681 tests passed
  GATE OK: battery, foundation, frontend and whitespace all pass
```

**1817 → 1839, +22**: three for `rehearsal-counted`, two for the restore, seventeen for the
probe. Foundation and frontend unchanged.

---

## 7. What was false in the brief

| claim | what the tree and the host say |
|---|---|
| *"One alpha stack answers, on 31500, rebuilt from `313e753`'s code."* | The **api** image is `313e753`'s code. The **web** image is not — it predates `89600f6` by eleven minutes. Found by the probe on its first run, which is `D-27` recurring inside the brief that asked me to close it. |
| `D-27`: *"a probe comparing the served document's digest … would answer it"* | It would not. The served and frozen documents are not byte-comparable by design, and the generated document is byte-identical with `carrier.py` changed — so such a probe would have been green on the drift this row is about. |
| *"nginx held a dead upstream and everything answered 502 until the proxy was restarted"* | True, **and intermittent**: a replaced container usually gets its old address back and nothing looks wrong. Driven, with the addresses logged. |
| `reset.sh` is sound apart from `D-24` | Its own `--restore` invocation, as printed and as documented, restored the database and then failed on the objects. Found by driving it. |
| *"the eleven refusals"* (`README.md`) | Twelve now, and the README moved with the count. |

Everything else checked out: `313e753` is `origin/dev`, the base gate figures match to the
number, `reset.sh` has eleven marked guards each with a deletion case, the meta-test pins the
count, `startRun` no longer blocks, and the 300 s value is still the right one.

---

## 8. What I did not do, and what is left

* **No `web/`, no `tests/e2e/**`, no `src/`, no `contracts/`, no `Makefile`.** The probe needs
  no target: it is a script, invoked directly, for the same `T-4` reason `reset.sh` is.
* **`DEBT_REGISTER.md` is untouched.** `D-24`, `D-26`'s `infra/` half and `D-27` are addressed
  here; the register is the integrator's.
* **No image was built.** The one place an image was required — the live destructive run's
  `migrate` and `object_attrs.py` — was served by `docker tag`ging an existing one, removed
  afterwards. Disk went 15G → 12G free, all of it postgres WAL from the ten-million-row cost
  measurement, and all of it returned when that stack came down with `-v`.
* **Open, for whoever owns it:** widen `D-23`'s guard past `.py` and `.md`. Four stale counts
  were sitting in a file class it cannot read, and I could only fix the ones inside
  `infra/deploy/`.
* **Open:** the alpha stack on 31500 is serving a stale web image. One rebuild plus
  `reload-proxy.sh` fixes it, and `verify-deployed.sh` will then exit 0 — but a rebuild is an
  image build, and this session was told not to.
