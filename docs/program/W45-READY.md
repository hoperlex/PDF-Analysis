# W45-READY — the deploy stops being a hope

- **Task:** `W45-READY`, wave 45 sub-stage A. `R1` (`D-80`), `R2` (`D-79`), `R3` (a timed
  clean-clone deploy rehearsal).
- **Worktree:** `/root/w45rdy`, branch `agent/w45-ready`, base `1664f90`.
- **Lane:** `gate-w45b` — PostgreSQL `127.0.0.1:56340`, S3 `59940`/`59941`.
- **Commits:** `0d74141` (`R2`), `173f733` (`R1`). No tag, no push, no merge.
- **This session wrote two files and repaired nothing outside its grant.** One real,
  pre-existing defect was found and reported rather than fixed: see "False premises and
  findings" below.

## R1 — `D-80`: `.dockerignore`

**Re-measured before changing anything, as the brief asked.** Confirmed: no
`.dockerignore` anywhere in the repository; both services build with `context: ../..`
(`infra/deploy/compose.server.yml:112,127,174`); `Dockerfile.web:23-26` runs `npm ci`
then `COPY web/ ./`.

**Reproduced the defect on this host, not inspected it.** After provisioning this
worktree for real (`make bootstrap`, `npm --prefix web ci`), a marker file was planted
in the host's `web/node_modules` — a string `npm ci` never produces. Built
`infra/deploy/Dockerfile.web` with no `.dockerignore`, through `docker compose build`
(the real deploy path, not a bare `docker build`): the marker was present in
`/web/node_modules/` inside the resulting image. Context transferred: **563.89 MB**.

**Wrote `.dockerignore`** (excludes `.git`, `.local`, `.venv`, `**/node_modules`,
`web/.next`, `**/__pycache__`, caches and `.env*`, mirroring the row's own repair list).
Rebuilt through `docker compose build` again: context transferred **26.57 kB**, the
marker was absent, `web/node_modules` was populated (135 top-level entries) purely from
the in-image `npm ci`, and both `api` and `web` images still build. Repeated once more
after tidying the file's comments, to keep "verified by a build" true of the committed
bytes and not an earlier draft.

**Correction to the row, found by re-measuring rather than assumed:** under this host's
BuildKit (docker 29.8, the default builder), the **API** build was never the multi-GB
problem on its own. `Dockerfile.api`'s `COPY` instructions name specific paths, and
BuildKit only requests what a `COPY` names — its context measured **16.30 kB**, identical
with and without `.dockerignore`. The size half of `D-80` belongs to `Dockerfile.web`
alone, because `COPY web/ ./` names a whole subtree. `.dockerignore` is still correct for
both images — it is what makes the `node_modules` overlay structurally impossible for
`web`, and cheap insurance for `api` — the correction is about which build the SIZE half
actually costs, not about whether to write the file.

## R2 — `D-79`: the gate reads `docs/`

New file: `tests/contract/api_v1/test_doc_prose_facts.py` (not an edit to
`test_surface_counts_in_prose.py` — see "Not reused" below). Scans exactly three
documents — `docs/program/CURRENT_STATE.md`, `docs/program/ALPHA_ROADMAP.md`,
`docs/manual-tests/**/*.md` — and checks three facts against independent ground truth:

| fact | ground truth read from |
|---|---|
| migration head | `db/migrations/versions/*.py` revision graph (the id that is nobody's `down_revision`) |
| contract surface triple | `contracts/api/v1/openapi.json` + `contracts/domain/v1/error-codes.json` |
| tagged tip | `git tag --list 'alpha-w*'`, highest by wave number |

All three currently agree with the live prose except one file outside this task's grant
(below).

**How the guard tells a record from a claim — the brief's explicit question:**

1. **Scope is a fixed, named set of documents**, exactly as the sibling guard's
   `SCANNED_TREES` is a fixed set of trees. Wave reports (`docs/program/W30-CERT3.md`,
   `W37-CERT4.md`, ...) are simply never in it — nothing globs `docs/program/`.
   `test_wave_reports_are_never_scanned` asserts this by name.
2. **`CURRENT_STATE.md` marks its own history**, in its own words: everything from
   `## Previous release state — wave 43 (historical record)` onward is truncated out of
   the live scan before any regex runs. `test_the_historical_section_is_excluded_from_the_live_scan`
   proves it with content that exists only on each side (a commit SHA that appears only
   in the historical text; the live tagged-tip sentence that survives the cut).
3. **`ALPHA_ROADMAP.md`'s one correction note narrates an old triple beside the current
   one** in the same paragraph ("The surface is 13 paths / 16 operations / 48 schemas
   after wave 34's reseal ... so it is 15 paths / 18 operations / 51 schemas"). The old
   one is registered by exact file+phrase in `KNOWN_HISTORICAL_TRIPLES` — the same
   mechanism `LOCAL_COUNTS` uses next door — never a heuristic about tense or nearby
   words, because a heuristic is the kind of query `OPERATING_CONSTRAINTS.md` §12 warns
   shares an assumption with what it checks.

**Shown red, on the real documents, then reverted** (never committed):

- `docs/program/ALPHA_ROADMAP.md`, the live triple changed to
  `15 paths / 99 operations / 51 schemas` → `test_the_scanned_docs_state_the_contract_surface_this_tree_has`
  failed with `docs/program/ALPHA_ROADMAP.md: '15 paths / 99 operations / 51 schemas' states
  SurfaceTriple(paths=15, operations=99, schemas=51), tree has SurfaceTriple(paths=15,
  operations=18, schemas=51)`.
- `docs/program/CURRENT_STATE.md`, `remains **0010**` changed to `remains **0099**` →
  `test_the_scanned_docs_state_the_migration_head_this_tree_has` failed with
  `docs/program/CURRENT_STATE.md: 'migration head remains **0099' names head 0099, tree
  has 0010_run_terminal_detail`.

Both files were restored byte-for-byte (`git status --porcelain` empty afterward) and the
suite returned to 21/21 green. The full parametrized red/green pairs for all three facts,
plus the wrap-across-a-blockquote-line case, live in the file itself, mirroring
`test_surface_counts_in_prose.py`'s own established pattern.

**Not reused from `test_surface_counts_in_prose.py`:** `pyproject.toml` sets
`--import-mode=importlib` repository-wide specifically so one test module cannot import
another (the sibling file's own conftest.py says so, for the analogous `conftest`
case). So the small "count operations/paths/schemas from the two contract files" helper
is duplicated (about 15 lines) rather than cross-imported — checked, not assumed, before
writing a single line of the new file.

**Found, not fixed:** `docs/manual-tests/PC-01_prototype.md:39` states *"Observe the
migration head is `0008_sign_in_throttle`"* — stale; the tree's head has been
`0010_run_terminal_detail` since wave 42. This is the exact `D-79` shape, found live by
re-measuring the row's premise rather than injected for the demo. `docs/manual-tests/**`
is **not** in this task's `allowed_paths`, so it is registered in
`KNOWN_OUTSTANDING_CLAIMS` with a citation — not silently dropped, not silently fixed —
and `test_the_known_outstanding_claim_is_registered_and_not_silently_absent` asserts the
registered claim really does disagree with the truth, so the exception cannot go stale
without a test noticing. **Reported to the integrator; PC-01_prototype.md also has two
further stale operation-count mentions this guard deliberately does not check** ("Observe
... `operations=12`" at line 59, and "the twelve operations" at line 210 — both bare
single-noun counts, not the `N paths / N operations / N schemas` triple this task's brief
named, so out of R2's literal scope; flagged here so they are not lost).

## R3 — clean-clone deploy rehearsal, timed

Executed against `https://github.com/hoperlex/PDF-Analysis.git` cloned fresh to
`/root/w45-r3-rehearsal` (outside every worktree), torn down and deleted afterward.
**This does not establish `PA-01` criterion 1** — this host has run `deploy.sh` many
times — it is a timed checklist for the host that never has.

| step | command | measured | notes |
|---|---|---|---|
| clone | `git clone https://github.com/hoperlex/PDF-Analysis.git` | **11.3 s**, 82 MB on disk | network reachable from this host; landed at `alpha-w44` / `d6ebe3a` |
| provision (python) | `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` | **20.7 s** | benefits from this host's shared `~/.cache/uv` (91 MB) — a genuinely first-run host with a cold uv cache should budget more |
| provision (node) | `npm --prefix web ci` | **4.4 s** | 576 MB `web/node_modules`; likewise benefits from a warm host-level npm cache |
| deploy (build + up + 4 checks) | `infra/deploy/deploy.sh` | **73.6 s** total | see below — first attempt refused twice on placeholder secrets, exactly as designed |
| verify | `infra/deploy/verify-deployed.sh --env-file ...` | **3.3 s** | `the deployed stack IS this tree (d6ebe3a)` |
| teardown | `docker compose ... down --volumes` | **2.0 s** | + image removal + directory removal |

**`deploy.sh` refused twice before it ran, both by design and both real owner-supplied
values the checklist must name:**

1. `POSTGRES_PASSWORD is still the value shipped in alpha.env.example.` — refused with
   nothing built.
2. After changing that one, the same guard caught `MINIO_ROOT_PASSWORD`,
   `MINIO_ROOT_USER` and `AUDITMANAGER_API_TOKEN` together (checked as a set against
   `alpha.env.example`'s own values, not by pattern).

**Owner-supplied values the day needs, named because the checklist asked for them:**

- `POSTGRES_PASSWORD`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `AUDITMANAGER_API_TOKEN`
  — four real secrets, each individually compared against the example file's shipped
  value and refused if unchanged. Generated here with
  `python3 -c 'import secrets; print(secrets.token_urlsafe(32))'` per the file's own
  comment.
- `ALPHA_HTTP_PORT` — the one published port; must not collide with another instance's.
  Checked here (`ss -ltnp`) before picking `18099`.
- `ALPHA_BIND_ADDRESS` — deliberately left unset (defaults to `127.0.0.1`); the owner
  ruled this closed under `D-49`, and the host day must not set `0.0.0.0` without
  re-deciding that.
- `AUDITMANAGER_PROVIDER_MODE` and, if `live`/`proxy`, `infra/deploy/env/provider.env`'s
  provider credential — left at `recorded` here on purpose; this is `D-70`'s
  still-open gap, not this task's.
- A TLS certificate and key, if the host day publishes beyond loopback — not exercised
  here (`ALPHA_BIND_ADDRESS` stayed at its safe default), named because
  `deploy.sh`'s own header says the overlay is separate and reads
  `infra/deploy/proxy/tls/fullchain.pem`/`privkey.pem` if present.

**What `deploy.sh` itself verified, on this run:** all five services healthy; migration
head `0010_run_terminal_detail` (`expected` = `current`); a write-probe transaction
committed nothing and rolled back cleanly; the published port answered `401` (`T-6`'s
seam, fail-closed, confirmed rather than assumed); served operations **18**, frozen
operations **18**, **0** differences. `verify-deployed.sh` then confirmed byte-identity
across `src/` (164), `db/` (14), `contracts/` (34), `fixtures/recorded/` (7),
`docs/program/P02_LOCK.json` (1) and `web/` (309 files).

**What this run does NOT establish, named so it is not mistaken for more:** the cloned
tree was `alpha-w44` (`d6ebe3a`), which predates this task's own `.dockerignore` — so this
rehearsal ran the *unrepaired* `Dockerfile.web` and still succeeded end to end, which is
consistent with the `D-80` row rather than contradicting it: a clean clone has no
`web/node_modules` to overlay, so the defect cannot manifest here by construction — the
same trap named for `PA-01` criterion 1. A second-run idempotency timing (`D-36`'s
comment: rebuild, no layer changes, `api`/`web`/`migrate` recreated anyway) was **not**
measured this session — disk had dropped to 5.5 GB free after the first `up`, and adding
a second build risked the shared host rather than this task's own grant. Left for the
host wave or a session with more disk headroom.

## Disk, and one shared-resource action taken and disclosed

`df -h /` before any build: **17 GB** free (86% used). After `make bootstrap` + `npm ci`
in this worktree, R1's four image builds/rebuilds, and R3's clone + two more image
builds: **5.5 GB** free (96% used) at the tightest point, immediately after `deploy.sh`'s
`up`.

**Freed by removing only what this session created:** the `-before`/`-after` proof
images (`docker rmi`, ~2.9 GB), the R3 rehearsal's two images and its
volumes/containers/network (`down --volumes`, `docker rmi`), and the cloned directory
(`rm -rf /root/w45-r3-rehearsal`, 82 MB plus provisioning).

**One host-wide action, disclosed rather than silent, per `OPERATING_CONSTRAINTS.md`
§4.5:** `docker builder prune -f` (not `-a`) — removed 5.29 GB of build cache that
`docker system df` showed as **0 active / fully reclaimable** at the time (this
session's own accumulated layers from R1's repeated builds). This does not touch any
running container or any other lane's named resources; it only evicts cache no image
currently references. Freed disk from 6.3 GB to 12 GB. Final state: **12 GB free, 90%
used** — better than this session found it, and reported here unprompted in case another
live lane (`w45pos`, `w45j`, `w45k`) also measured against the tighter number in between.

## Verification

`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` → `bootstrap OK`.
`.venv/bin/python -c "import boto3"` → `boto3 OK 1.43.90`.
`npm --prefix web ci` → `added 184 packages`.
`make gate > /root/w45b-gate.log 2>&1` → exit `0`, and, read from the log itself rather
than the exit code (`OPERATING_CONSTRAINTS.md` §4.6):

```
GATE OK: battery, foundation, frontend and whitespace all pass
```

Battery **2487 passed** (`alpha-w44`'s **2466** + this session's **21** new tests in
`test_doc_prose_facts.py`), 5 skipped, 4 warnings, 169 subtests. Foundation **35
passed**. Frontend **1110 tests in 78 files** — identical to `alpha-w44`, since nothing
under `web/**` was touched.

## Forbidden hotspots — untouched

```
$ git diff --stat 1664f90..HEAD
 .dockerignore                                 |  57 +++
 tests/contract/api_v1/test_doc_prose_facts.py | 491 ++++++++++++++++++++++++++
 2 files changed, 548 insertions(+)
```

No `web/**`, no `src/auditmanager/**`, no `contracts/**`, no `db/migrations/**`, no
`docs/program/DEBT_REGISTER.md`, no `docs/program/dispatch/**`, no `Makefile`, no
`package.json`. `auditmanager-w19a` (the owner's stand, `127.0.0.1:31500`) was never
started, stopped, restarted or reconfigured by this session — confirmed still `Up`,
`healthy`, untouched, both before and after (`docker ps` re-checked at the end). The
only container names this session created all began `gate-w45b-r3rehearsal-*` (R3's
throwaway instance, named and reported per the brief) or `gate-w45b-*` (this lane's own
foundation, brought up by `make gate` itself).

## Contracts changed

None.

## Risks / known limitations

- `docs/manual-tests/PC-01_prototype.md` is stale in three places (migration head,
  `operations=12`, "the twelve operations"), sitting exactly where the row that named
  this task warns it will: a runbook a reviewer runs today. Not this task's `allowed_paths`.
- R3's idempotency (second-run) timing was not measured, for disk reasons — a real gap
  in the checklist, not an oversight to hide.
- The new guard's "tagged tip" check is intentionally narrow (`closed as
  \`alpha-wNN\`` only) to avoid the historical-narrative false positives the brief warned
  about; a future document that states the tip a different way will not be checked until
  its idiom is added.

## Instruction to the integrator

Both commits (`0d74141`, `173f733`) are on `agent/w45-ready`, unpushed, unmerged, no
tag — per discipline. `make gate` is green on this branch with the figures above. The one
real defect found (`PC-01_prototype.md`) needs an owner-authorized session with
`docs/manual-tests/**` in its `allowed_paths` to correct three lines and then remove the
matching entry from `KNOWN_OUTSTANDING_CLAIMS` in `test_doc_prose_facts.py` — at that
point the guard goes back to checking that file with no exception at all. R3's
idempotency timing is worth a five-minute rerun on a host with more than ~10 GB free
before the host wave is scheduled for real.
