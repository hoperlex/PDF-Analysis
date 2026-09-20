# `W24-IDEM` — running `deploy.sh` twice changes nothing

**Session `W24-IDEM`, branch `agent/w24-idem`, from `origin/dev` at `16d3503`.**
Instance `auditmanager-w24idem` on `127.0.0.1:31524`, built and torn down by this session.
Nothing here was driven against `auditmanager-w19a` on 31500, which is `W24-CERT2`'s subject
this wave.

## 0. The answer, in one paragraph

**It can be achieved, and it was.** `infra/deploy/deploy.sh` run three times against an
unchanged tree leaves **all seven container IDs identical** — `postgres`, `s3`, `s3-init`,
`migrate`, `api`, `web` and `proxy` — both image IDs identical and both named volumes with
their original creation time. The nearest honest qualification is one sentence and it is not
about identity: **the two one-shot containers, `migrate` and `s3-init`, are started again in
place.** They keep their container IDs; only their `StartedAt` moves. `alembic upgrade head`
against a database already at head applies nothing and `migrations-at-head` proves it
afterwards, and `bucket-init.sh` is idempotent by construction and was chosen for that.

**`D-36`'s stated cause is wrong**, and finding that out was most of the work. It is not
`created` and `SOURCE_DATE_EPOCH` was never going to fix it. §3 has the measurement.

## 1. Baseline

`make gate` on `agent/w24-idem` at `e92d178`, lane `gate-w24b`
(`POSTGRES_PORT=55950`, `S3_API_PORT=59550`, `S3_CONSOLE_PORT=59551`,
`POSTGRES_DB=audit_w24b`, bucket `auditmanager-gate-w24b`), exit code read from `$?` after a
redirect and never through `| tail`:

| | |
|---|---|
| battery | **1909 passed, 5 skipped, 168 subtests**, 235.84s |
| foundation | **35 passed**, 29.04s |
| frontend | **706 passed in 48 files** |
| whitespace | clean |
| exit code | **0**, `GATE OK` |

Provisioning: `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` → `bootstrap OK`,
exit 0; `npm --prefix web ci` → exit 0.

And at the tip of this branch, `586e9d0`, same lane, same way:

| | |
|---|---|
| battery | **1932 passed, 5 skipped, 168 subtests**, 264.88s |
| foundation | **35 passed**, 28.72s |
| frontend | **706 passed in 48 files** |
| whitespace | clean |
| exit code | **0**, `GATE OK` |

**+23 on the battery and nothing else moved**, which is exactly the 23 cases of
`test_deploy_image_identity.py`. The refusals suite stays at 39: its thirteenth guard's case
lives in the new file, and its meta-test now pins 13 markers and asserts that the excused
name is actually present there.

## 2. `D-36` reproduced, and then reproduced properly

The first drive of this session ran the **unchanged** `deploy.sh` twice on a clean instance.
It reproduced the shape of `D-36` — `postgres`, `s3` and `proxy` kept their container IDs,
both volumes kept the first run's timestamp, `s3-init` kept its container ID, and `api`,
`web` and `migrate` were recreated — but **it is not the measurement `D-36` describes**, and
this file will not present it as one: between the two runs I ran `docker builder prune -f`
to recover disk, so the second run's build was **not cached** (0 `CACHED` steps) and its
layers genuinely differed. A cold rebuild of these Dockerfiles is not byte-reproducible —
`apt-get install` alone writes a dpkg status file with timestamps in it — so of course the
image changed. That drive proves nothing about an identical build.

The measurement that does is in §3, and it is stronger: it is two **fully cached** builds
with nothing else moving at all.

## 3. What actually moves the image id, measured

Three consecutive `docker compose build` invocations, same tree, warm cache, every step
`CACHED`, default BuildKit behaviour. The api image, pinned with a second tag each time so
it survived the next build:

| | image id |
|---|---|
| build 1 | `sha256:3ca63a36d198…` |
| build 2 | `sha256:e23bd025ff29…` |
| build 3 | `sha256:d037d442f9bc…` |

Now compare the pairs field by field, with `docker image inspect`:

* **build 2 against build 3**: `.Os`, `.Architecture`, `.RootFS.Layers` and the **entire
  `.Config`** are byte-identical, and `.Created` is **identical to the nanosecond** —
  `2026-09-20T11:14:08.019171657+05:00` on both. The ids differ anyway.
* **build 1 against build 2**: identical except for **one label**,
  `com.docker.compose.service`, which read `migrate` on one and `api` on the other. `api`
  and `migrate` are two services sharing one image and compose writes into it whichever one
  it credited the build to.

So `D-36`'s sentence — *"BuildKit stamps a fresh `created` into the config"* — **is false on
this host.** `.Created` does not move. What moves is the **image id itself**, and the id is
the digest of the image's **manifest**, not of its config:
`docker image inspect --format '{{json .Descriptor}}'` gives
`mediaType: application/vnd.oci.image.manifest.v1+json`, `digest` equal to the id, and a
`config.digest` annotation that is a different value. BuildKit attaches a **provenance
attestation** to every build by default — the build log's own `resolving provenance for
metadata file` step — and an attestation records when the build ran. `SOURCE_DATE_EPOCH`
addresses timestamps *in the image*; it was never going to touch this, which is exactly why
`W23-DEPLOY` tried it and saw no change.

**Turning the default attestations off makes the id a digest of the content again.** Two
consecutive cached builds with `BUILDX_NO_DEFAULT_ATTESTATIONS=1`:

| | api | web |
|---|---|---|
| build 1 | `sha256:1588a443ecf0…` | `sha256:f95c0d54cf31…` |
| build 2 | `sha256:1588a443ecf0…` | `sha256:f95c0d54cf31…` |

And it is a digest of the content in the direction that matters too: after §4 changed a byte
in `infra/deploy/serve.py` and then reverted it, the api image came back to
`sha256:1588a443ecf0…` — **the same id it had before the change**.

### The second cause, which that does not fix

The `com.docker.compose.service` label flip is a real config difference, so no attestation
setting removes it. That is why `deploy.sh` also compares content and moves the tag back
(§5): the two halves answer two different causes, and `BUILDX_NO_DEFAULT_ATTESTATIONS`
alone would leave the property holding *usually*.

### Two facts about this host's docker that the mechanism rests on

Both were found by the mechanism failing on them first, and both are now in `deploy.sh`'s
own comments and modelled in the test suite's `docker` stub:

1. **This docker deletes the image a tag moved off, immediately**, even while containers are
   running on it. Measured: an id read from `docker image inspect` two seconds before a build
   answers `No such image` after it, and `docker image ls -a` shows no dangling entry at all.
   The first version of this step therefore compared a fingerprint against something that no
   longer existed and printed *"the previous one could no longer be read"* on every single
   run — a mechanism that ran, said something true, and did nothing. **A second tag taken
   before the build is what keeps the image**, and it is why `# --- 1.` pins.
2. **While the old container is still running, this docker refuses to untag the image it
   runs** — `conflict: … container <id> is using its referenced image`. So the pin cannot
   come off before `up`; it comes off in `# --- 2a.`, after. On the runs where the content
   was identical that drops a tag and nothing else; on the runs where it changed, `up` has
   already replaced the containers and dropping the pin deletes the old image, which is what
   this script did before there was a pin.

## 4. The failure mode, driven rather than reasoned about

A mechanism that preserves image identity can be wrong in exactly one way: **an image that
keeps an old identity after its content genuinely changed.** The task asked whether
`verify-deployed.sh` catches that rather than assuming it does. It was not assumed.

`infra/deploy/serve.py` is copied into the api image by the runtime stage's own `COPY` line,
so `verify-deployed.sh` derives a row for it. The probe, by hand:

1. pin the current api image, `sha256:1588a443ecf0…`;
2. append one comment line to `infra/deploy/serve.py`;
3. `compose build api` → `sha256:634fc1ce9088…`, a genuinely different image;
4. **`docker tag 1588a443… auditmanager-w24idem-api`** — the mechanism's failure mode, forced
   by hand: the name points back at an image whose content is now stale;
5. `compose up -d` → nothing is recreated, because the image id did not move. The api
   container is still running the old bytes while the tree has the new ones.

`infra/deploy/verify-deployed.sh` then **exits 6** and names the file:

```
  src/                                141 files, identical
  db/                                   9 files, identical
  contracts/                           34 files, identical
  fixtures/recorded/                    7 files, identical
  docs/program/P02_LOCK.json            1 files, identical
  /app/serve.py  DIFFERENT BYTES
      tree  9493ae538c4d830f0a1c4a5dfa6abd826f3cc853dc9de5b4db762a27eb0a6f48
      image 425b08393f4e0529f327fba1f94f28fd489d1abfada7b4c3ac25286c525f72e8
  infra/deploy/serve.py                 1 files: 0 missing, 1 different, 0 unexpected
…
verify-deployed.sh: the deployed stack is NOT this tree -- 1 file(s) disagree.
```

**The probe catches it, by name, with both digests.** That is the whole answer to the
question the task asked, and it is a measurement rather than a reading of the script.

The control half, on the same stack, with the changed byte still in the tree: `deploy.sh`
run normally printed

```
  auditmanager-w24idem-api     2dc5cc776502  CONTENT CHANGED; replaces 1588a443ecf0
  auditmanager-w24idem-web     f95c0d54cf31  unchanged; the build did not move the id at all
```

recreated `api` and `migrate` and **left `web`, `proxy`, `postgres` and `s3` alone** — a
second property that falls out of comparing content: a change that only reaches one image
now only replaces that image's containers. `verify-deployed.sh` then exited 0. Reverting the
byte and running once more gave `CONTENT CHANGED; replaces 2dc5cc776502`, the api id back at
`1588a443ecf0`, and `verify-deployed.sh` exit 0 against a clean tree at `2ad0fea`.

## 5. The mechanism

Two halves, in `infra/deploy/deploy.sh`:

1. **`export BUILDX_NO_DEFAULT_ATTESTATIONS=1` before `compose build`.** The id becomes a
   digest of the content. What is given up is the provenance attestation: nothing in this
   repository reads one, `verify-deployed.sh` asks the running container what bytes it holds
   rather than asking an image what it claims about itself, and the digests pinned in
   `compose.server.yml` are of third-party images this never builds.
2. **Pin, compare, move the tag back.** Before the build, each image name's current id is
   read and given a second tag, `<name>:deploy-previous`, so the image survives the build.
   After the build — and after the `images-built` guard, so the comparison only happens on a
   build that produced something — each name's new image is compared with the pinned one by
   **content**: `.RootFS.Layers` (the diffIDs, each the sha256 of a layer's uncompressed
   tar) plus `Env`, `Cmd`, `Entrypoint`, `WorkingDir`, `User`, `ExposedPorts`, `Volumes`,
   `StopSignal`, `Healthcheck` and every label that is not `com.docker.compose.*`. Identical
   → the tag is pointed back at the old image and the build's duplicate is removed. The pin
   comes off after `up`.

Five outcomes, each with its own line on stdout, none of them silent: *no previous image*,
*the id did not move at all*, *identical content, kept*, *CONTENT CHANGED*, and *the previous
one could no longer be read, so it is NOT claimed to be identical to anything*. The last one
is the shape `AGENTS.md` §4 forbids if it were left implicit: two unreadable fingerprints are
both the empty string, and a comparison that only asked whether they were equal would call
them identical.

**A thirteenth guard, `identity-policy-known`**, refuses an
`ALPHA_PRESERVE_IMAGE_IDENTITY` that is neither `yes` nor `no`, before anything is built. It
is `known-options`' argument one layer along, and it is shown able to fail by deletion like
the other twelve.

## 6. The twice-run proof

`deploy.sh` run three times in immediate succession on `auditmanager-w24idem`, tree
unchanged and clean at `2ad0fea`, a snapshot taken after each. Runs 2 and 3 each exited 0,
23 `CACHED` steps, and printed:

```
-- image identity --
  auditmanager-w24idem-api     1588a443ecf0  unchanged; the build did not move the id at all
  auditmanager-w24idem-web     f95c0d54cf31  unchanged; the build did not move the id at all
```

Container IDs, all three snapshots:

| service | after run 1 | after run 2 | after run 3 |
|---|---|---|---|
| postgres | `d8d5f4bd7f1e` | `d8d5f4bd7f1e` | `d8d5f4bd7f1e` |
| s3 | `a5b1acb4994e` | `a5b1acb4994e` | `a5b1acb4994e` |
| s3-init | `fbf4eeba1a9a` | `fbf4eeba1a9a` | `fbf4eeba1a9a` |
| migrate | `0b336f82774c` | `0b336f82774c` | `0b336f82774c` |
| api | `e70e1ec01dbe` | `e70e1ec01dbe` | `e70e1ec01dbe` |
| web | `08d25f292e1a` | `08d25f292e1a` | `08d25f292e1a` |
| proxy | `39e7201ac0b5` | `39e7201ac0b5` | `39e7201ac0b5` |

`compose up -d` reported `Running` for `postgres`, `s3`, `api`, `web` and `proxy` and
**`Recreated` for nothing**. Images `1588a443ecf0` and `f95c0d54cf31` throughout; both named
volumes at `2026-09-20T11:15:09+05:00` throughout.

`diff` of the snapshot after run 1 against the one after run 3 is **two lines**, and they are
the `StartedAt` of `s3-init` and `migrate` — the one-shot containers, started again in place
with the same ids. That is the whole residue, and it is §0's qualification.

## 7. What is tested, and what a test here cannot show

`tests/integration/composition/test_deploy_image_identity.py`, 23 cases, the sibling of
`test_deploy_script_refusals.py` and built the same way: `docker` is replaced on `PATH` by a
stub that reaches no daemon, builds no image and starts no container. The stub is a small
image store — tags point at ids, ids carry a content fingerprint — and it models the two
host facts from §3: a build always mints a new id, and **the image a tag moved off is
deleted unless something else tags it**. That second one is what makes the suite able to
catch a regression that removed the pin: without it every case would pass with the pin gone.

It pins: the second run leaves both ids where the first left them; the build really does mint
a new id, so the case is not vacuous; the duplicate is not left behind; a changed `api` or
`web` never keeps the old identity and the *other* image is not disturbed; an unreadable
previous image is not claimed identical; a first run on a host that has neither is not an
error; a `docker tag` that fails is said and does not fail the deployment; the switch turns
the retag off and does not turn the attestation setting off with it; the pin is taken before
the build and removed after `up`; the fingerprint contains `.RootFS.Layers` and does **not**
contain `.Created`; and the identity step runs after the build and before `up`.

**What it cannot show is that a real cached rebuild produces an identical fingerprint.** That
is a fact about BuildKit and this daemon, it is measured in §3 and §6, and the test that
guards the part of it the mechanism depends on is
`test_the_fingerprint_is_built_from_the_layer_digests_and_not_from_a_timestamp`: a
fingerprint that carried `.Created` could never match, and the mechanism would quietly do
nothing — which is `D-17`'s shape, a guard that was never shown able to fail and had
therefore never fired.

## 8. Rollback

`ALPHA_PRESERVE_IMAGE_IDENTITY=no` in `infra/deploy/env/alpha.env`. It turns off the pin, the
comparison and the retag; `deploy.sh` then says so on stdout and its closing lines revert to
the old wording. What an operator loses is only this: every run mints a new image and `api`,
`web` and `migrate` are recreated, as before `W24-IDEM`. It does **not** turn off
`BUILDX_NO_DEFAULT_ATTESTATIONS`, which is a fact about how the image is built rather than a
policy about identity; an operator who wants the provenance attestation back edits that one
line of the script, and there is no environment name for it because nothing here has ever
read an attestation. Any value that is neither `yes` nor `no` is refused before anything is
built. The switch is documented in `infra/deploy/env/alpha.env.example`, commented out, with
`yes` as the value it has when absent.

## 9. Costs and known limitations

* **The mechanism only helps when the build was cached.** A cold rebuild of these Dockerfiles
  is not byte-reproducible, so its content genuinely differs and the containers are replaced
  — correctly. §2 is what that looks like. The property this closes is "run it twice on the
  same host", which is the clause the roadmap and `D-36` are about.
* **One extra tag exists between the build and `up`.** It is removed in `# --- 2a.`; a
  removal that could not happen is reported and left, and the next run re-points it. It never
  accumulates: there is at most one per image.
* **`migrate` and `s3-init` are started again on every run.** They are not recreated and they
  keep their container IDs. Making them not run at all would need an "already deployed"
  branch, which this script deliberately does not have.
* **`com.docker.compose.*` labels are excluded from the comparison**, and that is a judgment:
  they are the builder's record of which service was credited with the build. Every other
  label is compared, so a label a Dockerfile sets is a changed image.
* **The provenance attestation is gone from both images.** Stated in §5; nothing here reads
  one.
* This was driven on **one host, one docker**. Both §3 facts — the eager delete and the
  untag conflict — are properties of this daemon, and the mechanism is written to survive
  their absence: a pin that was not needed is a spare tag, and a previous image that survived
  on its own compares the same way.

## 10. For the integrator

* **`D-36` is closed by this branch, and its text is wrong about the cause.** I may not edit
  `docs/program/DEBT_REGISTER.md` — it is a forbidden hotspot for this task — so the
  correction is owed there by whoever closes the row: it is not `created`, which is identical
  to the nanosecond across cached builds, and `SOURCE_DATE_EPOCH` was never the lever. §3 has
  the figures to quote.
* `docs/program/CURRENT_STATE.md` says `D-36` is *"the only part of criterion 1's row that
  `R-1` does not block"* and that it needs the owner. It no longer needs the owner. That file
  is also a forbidden hotspot here.
* No tag, no checkpoint, nothing pushed to `main` — `AGENTS.md` §5.
