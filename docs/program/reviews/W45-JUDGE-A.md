# W45-JUDGE-A — sub-stage A, judged on both branches before the merge

**task_id:** `W45-JUDGE-A` · **wave:** 45, close of sub-stage A · **lane:** `gate-w45j`
**worktree:** `/root/w45j` · **branch:** `agent/w45-judge` · **base:** `1664f90`

**Subjects, unmerged:** `agent/w45-ready` at **`202d1e8`** and `agent/w45-pos` at
**`3ad3816`** — corrected mid-review from `7101560`; see §0a.

**This branch repairs nothing.** Its whole diff against `1664f90` is this file. Every
mutation made to measure something was reverted before the next measurement, and
`git status --short` was empty between measurements (checked after every revert in this
session's own history).

**Lane provisioned first:** `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` →
`bootstrap OK`; `.venv/bin/python -c "import boto3"` → `boto3 1.43.90`; `npm --prefix web ci`
→ 184 packages. PostgreSQL `127.0.0.1:56350`, S3 `59950`/`59951`. No container outside
`gate-w45j*` was created or touched by this session, at any point; the owner's stand
`auditmanager-w19a` at `127.0.0.1:31500` was never started, stopped or reconfigured
(confirmed still `Up`, `healthy` throughout).

**One host-wide action, disclosed per `OPERATING_CONSTRAINTS.md` §4.5:** `A1`'s clean-cache
measurement needed `docker builder prune -f` and, once, `docker builder prune -a -f` to
eliminate BuildKit's own local-source cache, which otherwise makes a second context-transfer
measurement of the same tree read far smaller than a first one regardless of `--no-cache`
(`--no-cache` disables layer cache, not the content-addressed context cache). `-a` removes
BuildKit's cache only, never a pulled/tagged image (verified: `auditmanager-w19a-api`,
`postgres:17.11-trixie`, `minio/minio`, `node:24-bookworm-slim` etc. were all still present in
`docker images` afterward). Reported here unprompted in case another live lane measured a
build against the tighter cache state in between.

---

## 0a. The subject correction, and whether it contaminates anything already measured

The integrator released `gate-w45a`'s containers (`docker rm -f`) believing `W45-BLOCKS` had
finished at `7101560`; the stream was mid-run, restored its own lane and produced a real
second `make gate`: foundation 35, battery **2456 passed / 16 failed**, fixed ten of those
sixteen in a follow-up commit `3ad3816`, and reported the remaining two rather than touching
files outside its grant. I was told to audit `3ad3816`, not `7101560`.

**I did not take that on trust.** `git diff --stat 7101560 3ad3816` is exactly five files —
`tests/contract/domain_p02/test_openapi_document.py`,
`tests/integration/api/test_authorization.py`, `tests/integration/api/test_operation_surface.py`,
`tests/integration/api/test_router_and_body_rules.py`,
`tests/integration/api/test_served_document_and_health_plane.py` — and confirmed empty against
every path §1–§6 below rest on: `contracts/`, `web/openapi/`, `web/FRONTEND_LOCK.json`,
`web/src/_pages/blocks/`, `web/tests/guards/`, `src/auditmanager/bootstrap/adapters.py`,
`src/auditmanager/api/schemas/blocks.py`, `src/auditmanager/api/app.py`,
`src/auditmanager/api/routers/declarations.py`, `infra/deploy/`, `db/migrations/`,
`web/src/shared/api/errors.ts`, `docs/program/P02_SEAMS.md`. **Nothing in §2–§6 (A1–A5)
changes.** §1 (F1) is rewritten below against the real, current residue rather than the
6-failure sample I had read before the correction landed.

**Whether my own measurements rest on the destroyed lane.** They do not. Every measurement in
this report ran in my own `gate-w45j` lane, provisioned and torn down by this session alone;
I never read from, wrote to, or depended on `gate-w45a`'s state at any point, before or after
the container collapse. The one artifact I read rather than re-derived, `/root/w45a-gate.log`,
was the stream's **first**, interrupted run (6 failures I had verified in isolation match a
subset of it) — I re-verify the corrected, current state directly against `3ad3816` in §1
rather than trusting that log's completeness, which is exactly what turned out to be wrong.

---

## 0. The verdict in one paragraph

**Both grants are real work and I could not falsify either stream's headline claim.**
`W45-READY`'s `.dockerignore` is proven by a build, not by inspection: I independently
reproduced 563.89 MB → 26.57 kB on `Dockerfile.web` with the same planted-marker technique the
stream used, from a clean tree, myself. `W45-READY`'s new prose guard reddens naming the file
and the number on a real mutation and stays green on a wave report carrying a genuinely
historical `0005`, and its one exemption is provably narrow — a second, different stale claim
in the same exempted file still reddens. `W45-BLOCKS`'s `getVersionBlocks` gives three
genuinely different answers on the wire (I drove all three myself over a live `TestClient`,
not just its tests) and carries no `crops` field at all, confirmed at the code level, the wire
level and the contract-description level. Its screen correctly did **not** need to touch
`SEEDS`, and its 7 `UNREACHABLE_IN_ONE_PASS` entries are all individually correct against the
component's actual `useState` gating, verified by reading `blocks-page.tsx` line by line. On
`3ad3816`, `W45-BLOCKS` had already found and fixed nine-tenths of its own forbidden-hotspot
sample and correctly stopped at the two items genuinely outside its grant — see §1.

**The residue the integrator must still apply at merge is small, precisely bounded, and I
confirmed it directly against `3ad3816`, not by reading anyone's report of it:** the six
failures `W45-READY`'s and `W45-BLOCKS`'s own known-scope lists already name
(`test_openapi_conformance.py`'s four constants and one report-length literal, and
`test_surface_counts_in_prose.py`'s four `infra/deploy` sentences), plus exactly **two** more —
`tests/e2e/pc01/test_acceptance.py:307` and `docs/program/P02_SEAMS.md`'s frozen table (plus
two prose sentences in the same document no guard reads at all). §2 and §3 below add two
findings of my own that are real but do not block the merge: two live sentences inside
*guard-scanned* files the guard's own noun vocabulary cannot see, and eight more, pre-existing,
in `infra/deploy/**` files whose extensions the guard was never built to scan at all.

---

## 1. F1 — the residue at merge, verified directly against `3ad3816`

**Method.** Provisioned `gate-w45j`, checked out `3ad3816` in this worktree, ran every test
named below standalone, myself, against a fresh checkout with the lane's own migrations
applied — not by reading `W45-BLOCKS`'s commit message or gate log and trusting the count.

**Confirmed fixed, ten tests, five files, all now green:**
```
$ .venv/bin/python -m pytest tests/contract/domain_p02/test_openapi_document.py \
    tests/integration/api/test_authorization.py tests/integration/api/test_operation_surface.py \
    tests/integration/api/test_router_and_body_rules.py \
    tests/integration/api/test_served_document_and_health_plane.py -q
119 passed
```
Read the fix commit (`3ad3816`) itself, not just its effect: `REQUIRED_OPERATIONS` gained
`getVersionBlocks`; `GUARDED` gained a `getVersionBlocks` tuple; both `test_operation_surface.py`
assertions moved 15/18→16/19 **and their prose docstrings were correctly rewritten**, adding a
"nineteen until `W45-BLOCKS`" clause in the same style as every prior reseal's clause rather
than just editing the number; `test_router_and_body_rules.py`'s `18`→`19` pair and its
one-sentence docstring both moved; `test_served_document_and_health_plane.py`'s
`PATH_COUNT`/`OPERATION_COUNT`/`SCHEMA_COUNT` moved to `16`/`19`/`53`. All correct, independently
re-verified against `contracts/api/v1/openapi.json`'s actual surface
(`python3 -c "..."` → 16 paths, 19 operations, 53 schemas).

**Confirmed still red, exactly two, both correctly reported rather than repaired:**
```
$ .venv/bin/python -m pytest tests/contract/domain_p02/test_seam_register.py \
    tests/e2e/pc01/test_acceptance.py::test_c1_the_application_composes_from_the_environment_and_answers -q
FAILED test_seam_register.py::test_the_api_operation_table_matches_the_frozen_document
  Extra items in the right set: ('getVersionBlocks', 'GET /versions/{version_uid}/blocks')
FAILED test_acceptance.py::test_c1_the_application_composes_from_the_environment_and_answers
  assert 19 == 18
2 failed, 119 passed
```
- `tests/e2e/pc01/test_acceptance.py:307` — literal `18` → `19`. `tests/e2e/**` carries no owner
  this wave (`W45-BLOCKS`'s own grant says so explicitly), so this is squarely the integrator's.
- `docs/program/P02_SEAMS.md` — **not a test file**, and its own header
  (line 3) says why neither stream may touch it: *"Status: frozen by session `A1` on
  2026-09-10. Owner: `A1` until Gate A closes, then the integrator."* Two spots, verified by
  reading the file directly, both correctly named by the stream's own commit message:
  - the table, line 609 (header) through line 628 (`changePassword`, the last row and the
    precedent to follow) — add `| \`getVersionBlocks\` | \`GET /versions/{version_uid}/blocks\` |`.
  - lines 591 and 598, live prose no guard reads at all: *"Eighteen operations, sealed."* and
    "...eighteen after `W39-REVOKE` added `changePassword`..." — both need a `W45-BLOCKS` clause,
    the same shape every prior reseal added to this exact paragraph. **This paragraph is the
    historical record of this identical defect happening once already** (line 601: *"This
    paragraph read 'Fifteen operations, sealed' while the table below listed seventeen"* —
    caught only because `test_seam_register.py` compares the *table*, and `docs/` is explicitly
    outside `test_surface_counts_in_prose.py`'s scan). Fixing only the table and leaving the
    prose is the same defect a third time, in the same document that already names it twice.

**Confirmed still red, six, unchanged, exactly `W45-READY`'s and `W45-BLOCKS`'s own named
residue, `tests/contract/api_v1/**` (`W45-READY`'s forbidden hotspot, correctly untouched by
`W45-BLOCKS`):**
```
$ .venv/bin/python -m pytest tests/contract/api_v1/test_openapi_conformance.py \
    tests/contract/api_v1/test_surface_counts_in_prose.py -q
6 failed, 101 passed
```
`FROZEN_OPERATION_COUNT`/`FROZEN_SCHEMA_COUNT` (18/51 → 19/53), `FROZEN_OPERATIONS` (add
`("GET", "/versions/{version_uid}/blocks", "getVersionBlocks")`), `FROZEN_SCHEMA_NAMES` (add
`"VersionBlockIndex"`, `"BlockGeometry"`), `len(report) == 13` → `14`
(`TestN1ComponentReferenceResolution`; `N7`'s test self-heals once `FROZEN_OPERATION_COUNT`
moves, confirmed by reading it — it derives from the constant, asserts nothing of its own), and
the four `infra/deploy` "eighteen operations" sentences (`README.md` ×3, `serve.py` ×1).

**Total residue for the integrator at merge, verified rather than assumed: 8 fix locations,
9 executable assertions, across two files that are forbidden to both streams
(`tests/contract/api_v1/**`, owned by `W45-READY`; `tests/e2e/**`, owned by neither this wave)
plus one frozen document owned by the integrator (`docs/program/P02_SEAMS.md`, table + two
prose sentences).** Not eleven, and not the six either stream's own report names in isolation
— confirmed by running every one of them myself against the corrected tip, not by reading a
commit message.

**Not gate-blocking, found in the same sweep, worth doing in the same pass:**
- `tests/integration/api/test_operation_surface.py`'s module docstring (line 1, "the eighteen
  operations") — prose only, `3ad3816` did not touch it.
- `tests/integration/api/test_router_and_body_rules.py:12` — *"A duplicate leaves
  ``len(routes) == 15`` passing..."*, paired two lines later with *"Removing the check left
  all 816 tests green"* — read in context this is `W10-API`'s own historical measurement
  (816 is unambiguously an old total; current battery is 2456+), correctly left alone, unlike
  the module docstring above.

---

## 2. F2 — two live sentences inside files the D-23/D-79 guard **does** scan are stale and invisible to it, because its noun vocabulary doesn't cover the words these two sentences use

**Unaffected by the subject correction** — `git diff 7101560 3ad3816` does not touch either
file; both confirmed unchanged on `3ad3816`.

**Where.**
- `src/auditmanager/api/app.py:157` — `"""...the served document is a function of the
  eighteen declarations and the 51 models and not of what sits behind the ports..."""` — three
  lines below a docstring at line 143 the `W45-BLOCKS` reseal *did* correctly update to "the
  nineteen operations". Same file, same reseal pass, one sentence caught and the very next
  paragraph missed.
- `src/auditmanager/api/routers/declarations.py:3` — `"""...fifteen copies of a response
  table is fifteen places for one of them to be missing a status..."""` — untouched by this
  reseal even though the same file's lines 68 and 101 (a few lines down) *were* correctly
  updated ("The 53 schema names are pinned" / "five of the nineteen operations declare no
  `422`").

**Why the guard cannot see either.** `tests/contract/api_v1/test_surface_counts_in_prose.py`'s
`SURFACE_NOUNS` dict (line ~101) tracks exactly `operation(s)`, `schema(s)`, `path(s)`,
`code(s)`, `handler(s)` — a list that was itself widened once before, for exactly this reason
(the docstring at line ~113 records `handler(s)` being added after a stale count hid behind
that word in a BFF docstring). `declarations` and `models` are not in the list, so "eighteen
declarations" and "51 models" parse as nothing. `declarations.py`'s "fifteen copies" and
"fifteen places" have the same problem twice over.

**Reproduction — proves these are live claims, not decoration:**
```
$ python3 -c "import json; d=json.load(open('contracts/api/v1/openapi.json')); print(sum(1 for p in d['paths'].values() for m in p if m in ('get','post','put','patch','delete')), len(d['components']['schemas']))"
19 53
```
19 operations, 53 schemas — both sentences state the pre-reseal numbers (18, 51) and the
15-operation-vintage number (15) respectively, not the current ones.

**Cost if missed.** None to the gate — these are prose, not assertions, so nothing reddens.
The cost is exactly `OPERATING_CONSTRAINTS.md` §12's point: this is the third recorded instance
in this file's own history of a synonym hiding a stale count from this exact guard
(`handler`/`handlers` was the second), and it is happening again in the commit that landed
right after the guard's own docstring described the first instance.

---

## 3. F3 — eight more "fifteen operations" sentences, all pre-dating this wave, sit in `infra/deploy/**` files whose extensions the D-23 guard structurally never reads

**Also unaffected by the subject correction** — none of these paths are under `tests/`.

**Where.** `test_surface_counts_in_prose.py:191` restricts every scanned tree to
`path.suffix in {".py", ".md", ".ts", ".tsx"}`. `infra/deploy/**` contains Dockerfiles (no
matching suffix — `Dockerfile.api`'s suffix is literally `.api`), a compose file (`.yml`), an
nginx config (`.conf`), an env example (`.example`) and a shell script (`.sh`) — none of the
four allowed suffixes. Eight sentences in exactly those files still say **"fifteen
operations"**, which was already wrong before `W42-SEAL` (wave 42, which added no operation)
and is now off by **four**, not by the one this wave's reseal introduces:

```
infra/deploy/Dockerfile.api:1        "the fifteen operations under uvicorn"
infra/deploy/compose.server.yml:217  "serves all fifteen operations — writes included"
infra/deploy/proxy/nginx.conf:7      "headers on any of the fifteen operations"
infra/deploy/proxy/nginx.conf:85     "would answer 404 to all fifteen / operations"
infra/deploy/env/alpha.env.example:56   "serves all fifteen operations INCLUDING WRITES"
infra/deploy/env/alpha.env.example:117  "the fifteen operations while /healthz..."
infra/deploy/deploy.sh:215           "authentication_required to all fifteen operations"
infra/deploy/deploy.sh:837           "fifteen operations of this deployment is a claim about PC-01"
```
(Two other "fifteen" hits in this tree, `alpha.env.example:12` and `README.md:137`, are about
the **fifteen `.env` allowlist names** — `FROZEN_ENV_NAMES` — a genuinely different fifteen,
not a false positive I'm folding in.)

**Reproduction:**
```
$ grep -rn "fifteen operations" infra/deploy/
```
reproduces all eight, none of them flagged by `make gate`, on either branch, before or after
this wave.

**This predates `W45-BLOCKS` and is not its defect** — these sentences were already stale by
three when `W45-BLOCKS` started (18 vs. 15) and are stale by four now — but the reseal is the
occasion that makes the gap visible, and an integrator who fixes exactly the four "eighteen"
sentences `test_surface_counts_in_prose.py` names (`README.md` ×3, `serve.py` ×1) will leave
these eight "fifteen" ones sitting there having survived three reseals uncaught.

**Also found by the same sweep, inside `web/src` (a *scanned* tree) but past a different
adjacency gap:**
```
web/src/shared/api/errors.ts:26   "the fifteen PC-01 operations can put in front of a screen"
```
The regex requires the number and the noun adjacent (`{number}[ -]{noun}`); "fifteen **PC-01**
operations" has a word between them, so it never matches. Also predates this wave.

---

## Minor / informational — A1's absolute number does not reproduce, though its conclusion does

`W45-READY`'s `.dockerignore` comment and its own report both say `Dockerfile.api`'s build
context is **16.30 kB, identical with and without** the file. I reproduced "identical" — but
only under a fully cold BuildKit cache (`docker builder prune -a -f` between each of the two
measurements); under a warm cache (the ordering most sessions will naturally produce, build
`Dockerfile.web` then `Dockerfile.api`, or run the "with" case right after the "without" one)
BuildKit's content-addressed local-source cache makes a second identical-content transfer read
far smaller than the first, independent of `.dockerignore` and independent of `--no-cache`
(which only disables the *layer* cache). My own cold-cache figure was **2.38 MB both ways**,
not 16.30 kB either way — consistent with `src/` + `db/` + `contracts/` + `fixtures/recorded/`
(the only paths `Dockerfile.api`'s `COPY` instructions name) totalling ~2.7 MB on disk. The
qualitative claim — API image context size does not depend on `.dockerignore` because its
`COPY` instructions name specific paths — holds under my independent, cache-controlled test.
The specific absolute number in the row's own comment and in the stream's report is a
cache-state artifact, not a measurement of context size in any cache-independent sense. This
does not change anything about whether to ship the file, which both streams correctly say to
do regardless.

---

## 4. A1 — `.dockerignore`, re-taken from the working tree, not a clean clone

**Method, independent of the stream's own build:** planted `web/node_modules/.w45j-judge-marker`
(a string `npm ci` never produces) in this worktree after a real `make bootstrap` +
`npm --prefix web ci`.

```
$ docker build --no-cache -f infra/deploy/Dockerfile.web -t w45j-judge-web-nodockerignore3 .
#5 transferring context: 563.89MB
$ docker run --rm w45j-judge-web-nodockerignore3 sh -c 'cat /web/node_modules/.w45j-judge-marker'
W45J-JUDGE-MARKER-1790321276          # present
```
```
$ git checkout agent/w45-ready -- .dockerignore
$ docker build --no-cache -f infra/deploy/Dockerfile.web -t w45j-judge-web-withdockerignore .
#6 transferring context: 26.57kB
$ docker run --rm w45j-judge-web-withdockerignore sh -c 'ls /web/node_modules/.w45j-judge-marker'
ls: cannot access '/web/node_modules/.w45j-judge-marker': No such file or directory
$ docker run --rm w45j-judge-web-withdockerignore sh -c 'ls /web/node_modules | wc -l'
135
```
Both figures (563.89 MB → 26.57 kB) and the marker's presence/absence match the stream's own
report exactly, reproduced independently rather than trusted. `node_modules` in the repaired
image is populated (135 top-level entries) purely by the in-image `npm ci`. The
`Dockerfile.api` half is covered in the "Minor/informational" note above — qualitatively
confirmed, absolute number not reproduced (a cache-state artifact, not a defect).

**Both images still build** — confirmed as part of the same runs (image tags above all built
successfully). All test images removed (`docker rmi`) and `docker builder prune -f` run
afterward; final disk state better than found (13 GB free vs. 11 GB at the start of A1).

---

## 5. A2 — the prose guard, shown red and shown harmless

```
$ sed -i '70s#15 paths / 18 operations / 51 schemas#15 paths / 99 operations / 51 schemas#' docs/program/CURRENT_STATE.md
$ .venv/bin/python -m pytest tests/contract/api_v1/test_doc_prose_facts.py -q
FAILED test_the_scanned_docs_state_the_contract_surface_this_tree_has
AssertionError: docs/program/CURRENT_STATE.md: '15 paths / 99 operations / 51 schemas' states
SurfaceTriple(paths=15, operations=99, schemas=51), tree has SurfaceTriple(paths=15, operations=18, schemas=51)
$ git checkout -- docs/program/CURRENT_STATE.md   # reverted, git status clean
```
Names the file and the number, as required.

```
$ sed -i "s#migration head \`0005_truncated_call_status\`#migration head \`0099_truncated_call_status\`#; s#12 paths / 15 operations / 46 schemas#12 paths / 99 operations / 46 schemas#" docs/program/W30-CERT3.md
$ .venv/bin/python -m pytest tests/contract/api_v1/test_doc_prose_facts.py -q
21 passed
$ git checkout -- docs/program/W30-CERT3.md
```
`docs/program/W30-CERT3.md` (a wave report, correctly recording head `0005` as what was true at
wave 30) stays green even with a wildly wrong migration head and surface triple injected —
because it is simply never in `_scanned_documents()`'s three-document scope, confirmed by
reading the scope list (`CURRENT_STATE.md`, `ALPHA_ROADMAP.md`, `docs/manual-tests/**`), not
by trusting the docstring's claim.

**Exemption narrowness, checked directly** (the brief's explicit ask): appended a *second*,
*different* stale migration-head claim to the one file that carries a registered exemption
(`docs/manual-tests/PC-01_prototype.md`):
```
$ echo '

**Second check: migration head is `0007_something_else`, confirm before proceeding.**' >> docs/manual-tests/PC-01_prototype.md
$ .venv/bin/python -m pytest tests/contract/api_v1/test_doc_prose_facts.py -q
FAILED — docs/manual-tests/PC-01_prototype.md: 'migration head is `0007_something' names head 0007, tree has 0010_run_terminal_detail
$ git checkout -- docs/manual-tests/PC-01_prototype.md
```
The exemption in `KNOWN_OUTSTANDING_CLAIMS` matches on `(file, exact registered phrase
prefix)`, not on the file alone — a second stale claim in the same file is still caught. The
existing `test_the_known_outstanding_claim_is_registered_and_not_silently_absent` (line 483)
independently proves the registered exemption itself is live (re-derives that the registered
phrase really does disagree with the true migration head), so the exception cannot go stale
without a test noticing either.

**The one real, pre-existing defect this stream found and correctly did not touch**
(`docs/manual-tests/PC-01_prototype.md:39`, migration head stated as `0008`, true head
`0010`) — registered, not fixed, exactly as `W45-READY`'s grant required, and the exception's
liveness is what F1 and F2 above are asking the integrator to be equally careful about: a
guard exemption is a report, and a silent one is a hole.

---

## 6. A3 — `getVersionBlocks`, driven directly over a live `TestClient`, not read from the stream's tests

I did not trust the stream's own integration tests as the drive — I built a standalone script
against `create_asgi_app()`, minted a real signed credential with `tests/support/accounts.py`'s
`provisioned_credential`, and called the operation myself, live, three times:

```
UNKNOWN VERSION: 404 {'error_code': 'not_found', ...}
NOT PRODUCED (no run yet): 200 {'status': 'not_produced', 'produced_by_run_id': None,
  'text_layer_sha256': None, 'block_count': 0, 'blocks': []}
PRODUCED: 200 {'status': 'produced', 'block_count': 78, 'produced_by_run_id': <matches run_id>,
  'has crops key': False, 'has page_crops key': False,
  'sample block': {'block_id': 'b_000001', 'bbox': {...}, 'bbox_unit': 'pt', 'bbox_origin': 'top_left', ...}}
```

**The first two are not the same answer**, as required (404 vs. 200), and status distinguishes
the second two even though both carry `blocks: []` on the wire in the `not_produced` case and
would carry it too in a `produced`-but-zero-blocks case. `crops` is confirmed absent from the
operation *entirely* at three independent levels: the dataclass has no `crops` attribute (I
mutated one in — §7 below — and the guard caught it), the wire response has no `crops` or
`page_crops` key (confirmed above, `has crops key: False`), and
`components.schemas.VersionBlockIndex.description` states the fact in words a reviewer reads,
not just an absence a reviewer has to notice:
> *"Carries no crops: `page_geometry_extraction` also publishes a page-crop manifest... it is
> a separate artifact this operation does not expose."*

**What I could not drive: `status: "produced"` with zero blocks.** Like the stream's own
report says, the corpus fixture (`fixtures/synthetic/ar/ar_baseline.pdf`) always produces
real geometry (78 blocks in my own run) — there is no fixture in this repository that reaches
a genuinely empty *produced* result. I confirmed the code path exists and is correctly gated
(`blocks-page.tsx`'s `index.blocks.length === 0` branch, `EmptyState` title "Блоков не
обнаружено.") but could not exercise it end-to-end, for the same reason the stream itself
names. This is a disclosed, real gap, not a stream defect.

---

## 7. A4 — the `/blocks` screen, against instruments that reach it derived rather than listed

**`SEEDS` was not touched.** `git diff 1664f90 3ad3816 -- web/tests/unit/screens/route-screens.ts`
is empty. `BlocksPage` was already imported and seeded there since wave 44 (it is what made the
old `RoutePlaceholder` visible to the language guard and the contrast census in the first
place); `W45-BLOCKS` only changed what the component behind that seed renders. This is exactly
the right outcome the dispatch brief asks me to check for — a stream that *had* to add itself
to a list would be the finding, and this one did not.

**English prose, injected on the screen, reddens and names it:**
```
$ sed -i 's/Векторный граф.../Vector block graph not built yet: .../' web/src/_pages/blocks/ui/blocks-page.tsx
$ npm --prefix web test -- rendered-language.guard
FAIL ... "\"Vector block graph not built yet: ...\" ... [blocks]"
$ git checkout -- web/src/_pages/blocks/ui/blocks-page.tsx
```
`[blocks]` at the end of the failure line names the screen.

**A sub-3:1 border, injected on a really-rendered element, reddens and names the screen.**
(Inline `style` attributes are invisible to the census — it reads the CSS cascade, matching
parsed stylesheet rules against rendered markup, never a `style=` attribute — so I added a
class rule instead, `border: 1px solid var(--am-paper)` on `--am-paper` background, i.e. an
exact 1:1 ratio, applied via `className` to a paragraph in the default, no-version-chosen
render state the census actually reaches):
```
$ npm --prefix web test -- contrast.test
FAIL — "pair": "edge|--am-paper|--am-paper|-|border", "ratio": 1, "theme": "light",
  "where": ["blocks cold section.am-page > div.am-page__body > p.judge-a4-probe"]
(same for theme: "dark")
$ git checkout -- web/src/_pages/blocks/ui/blocks-page.tsx web/src/app/globals.css
```
Both themes, names the screen (`blocks`) and the exact site.

**The 7 `UNREACHABLE_IN_ONE_PASS` entries, checked individually against the component, not
just read.** Read `blocks-page.tsx` directly: `DocumentChooser` only mounts once `projectUid`
(a `useState`) is set by a project row's `onClick`; `BlockMarkup` only mounts once `version`
(a second `useState`) is set by a document row's `onClick`. A single `renderToStaticMarkup`
pass fires neither click, so `useDocumentList` and `useVersionBlocks` are never even called in
that pass — there is no query for the harness to seed an error/pending/empty state into, which
is exactly what each of the 7 `why` fields claims. The first step (`VersionChooser`'s own
project list) needs no click and is correctly *not* in the unreachable list. Confirmed the
matrix is still green with all 7 present (`npm --prefix web test -- rendered-language.guard` →
22/22).

---

## 8. A5 — mutating every new guard, quoted

In addition to A2's and A4's mutations (which are also new-guard mutations), driven
independently rather than read from either stream's report:

**`BlockAdapter.get_block_index`'s not-produced branch** (`src/auditmanager/bootstrap/adapters.py:593`):
```diff
-                status=STATUS_NOT_PRODUCED,
+                status=STATUS_PRODUCED,  # JUDGE-A MUTATION
```
```
$ .venv/bin/python -m pytest tests/integration/composition/test_version_blocks_wire_shape.py -q
FAILED test_a_version_with_no_run_answers_not_produced_not_an_empty_blocks_array
AssertionError: {'status': 'produced', 'produced_by_run_id': None, ...}
assert 'produced' == 'not_produced'
```
Reverted (`git checkout --`).

**`VersionBlockIndexView` given a `crops` field it should never carry**
(`src/auditmanager/api/schemas/blocks.py`):
```diff
     blocks: tuple[BlockGeometryView, ...] = ()
+    crops: tuple[object, ...] = ()  # JUDGE-A MUTATION
```
```
$ .venv/bin/python -m pytest tests/integration/runs/test_w45_blocks_version_block_index.py -q
FAILED test_the_view_carries_no_crops_field_at_all
AssertionError: assert not True
 +  where True = hasattr(VersionBlockIndexView(..., crops=()), 'crops')
```
Reverted.

**The seam-operations contract register** (`web/tests/contract/seam-operations.contract.test.ts:72`):
```diff
-  ['getVersionBlocks', 'GET', '/versions/{version_uid}/blocks'],
+  ['getVersionBlocks', 'GET', '/versions/{version_uid}/blocks-MUTATED'],
```
```
$ npm --prefix web test -- seam-operations.contract
FAIL — getVersionBlocks is GET /versions/{version_uid}/blocks-MUTATED
Expected: ".../blocks-MUTATED"  Received: ".../blocks"
```
Reverted. (This file predates the wave — the stream only added one row to it — so it is not a
*new* guard, but the row it added is new and bites.)

**`W45-READY`'s prose guard** — mutated twice under A2 above (red naming file+number; and the
exemption-narrowness probe), both reverted.

**`tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`'s widened
sweep** — not separately mutated (it is a generic sweep deriving `EXPECTED_ADDRESSED = 11` from
the frozen surface rather than naming operations, so the interesting mutation is the same one
already covered above: making `getVersionBlocks` answer something other than `404` for an
absent parent — not re-driven a second way here since A3 already drove the 404 case directly
and A5's `BlockAdapter` mutation already proves the adapter layer is checked).

All git state confirmed clean (`git status --porcelain`) after every mutation in this section
before moving to the next.

---

## 9. Where each stream did the right thing, plainly

- **`W45-READY`** disclosed, unprompted, the one host-wide docker action it took (§4.5-shaped,
  named and bounded: `docker builder prune -f`, verified `0 active` at the time), disclosed
  its own unmeasured gap (R3's second-run idempotency timing, and said exactly why: disk
  headroom), and found a real defect outside its own `allowed_paths`
  (`PC-01_prototype.md`'s stale migration head) and *registered* it with a self-checking
  exemption rather than editing a file it wasn't granted.
- **`W45-BLOCKS`** refused to claim a gate it had not seen finish, and that discipline is what
  makes §0a's incident recoverable rather than silent: when its containers were pulled out from
  under it mid-run, it restored only its own lane, ran the gate for real, and **found its own
  first sweep had missed ten failures** — then fixed exactly the ten inside its own grant and
  stopped at exactly the two that were not (`tests/e2e/**`, owned by nobody this wave;
  `docs/program/P02_SEAMS.md`, owned by the integrator by its own frozen header), naming precise
  line numbers for both rather than leaving them for the next reader to rediscover. I verified
  both halves of that claim independently in §1 rather than accepting the commit message. It
  also disclosed, rather than hid, that one of its own new guard's 7
  `UNREACHABLE_IN_ONE_PASS` branches (`EmptyState`/"Блоков не обнаружено.") is unreached by
  *any* instrument today including a browser, for a reason outside its control (no fixture
  produces that state) — confirmed true in §6 above rather than taken on trust.

---

## 10. What I could not answer, and why

1. **Whether the full backend battery (2456+ tests) is green on `3ad3816` beyond the two named
   residue failures and the six `tests/contract/api_v1/**` ones.** I independently re-ran every
   test named in §1 standalone and confirmed each result myself (`119 passed` / `2 failed` /
   `6 failed`, matching exactly). I did not re-run the full ~2456-test battery myself — a
   second full gate on a shared host, per `OPERATING_CONSTRAINTS.md` §4.6, risks reading
   contention as a broken guard and costs more than the answer is worth this sub-stage.
   **Every failing and every newly-fixed test independently re-verified standalone; the whole
   battery's remaining ~2440 tests read from the stream's own log, not re-run.**
2. **`status: "produced"` with zero blocks**, `getVersionBlocks`'s third answer. Confirmed the
   code path exists and is correctly gated by `status`, not by `blocks.length`, by reading
   `blocks-page.tsx` and `adapters.py`; could not drive it end-to-end because no fixture in
   this repository produces it, the same limitation the stream itself discloses. **Reasoned
   from the code, not driven.**
3. **`W45-READY`'s R3 idempotency-timing gap.** Not part of my grant to re-measure (it's R3's
   own disclosed limitation, not one of A1–A5), and re-measuring a second-run deploy timing on
   a host already tight on disk during A1 was not worth the risk to other live lanes. **Left
   to the host wave, as `W45-READY`'s own report already asks.**
4. **Whether F2's two prose spots and F3's eight `infra/deploy` sentences are the *complete*
   set of everything an untracked-noun or unscanned-suffix gap could be hiding across the
   whole repository.** I swept `src/auditmanager/api`, `web/src` and `infra/deploy`
   specifically (the three trees the guard already claims to cover, checking what it actually
   reaches vs. what it claims) rather than every file in the tree. **A targeted sweep of the
   guard's own stated scope, not an exhaustive one.**

---

## 11. Instruction to the integrator

`git diff --name-only 1664f90..HEAD` on this branch is exactly `docs/program/reviews/W45-JUDGE-A.md`.

At merge:
1. **F1, §1** — 8 fix locations, 9 assertions, verified directly against `3ad3816`: the six
   `tests/contract/api_v1/**` items both streams already name (yours to apply,
   `tests/contract/api_v1/**` is `W45-READY`'s forbidden hotspot), `tests/e2e/pc01/test_acceptance.py:307`
   (`18`→`19`), and `docs/program/P02_SEAMS.md` (a table row at line 628 plus the two live
   prose sentences at lines 591 and 598 that no guard reads — do not stop at the table, the
   document's own line 601 explains why that alone regressed once already).
2. **F2 and F3 (§2, §3) are not gate-blocking** but are real, live-wrong sentences the D-23/
   D-79 guard family cannot see today, for two structurally different reasons (untracked noun
   synonyms; unscanned file suffixes). Worth fixing in the same pass since it is the same
   18→19/51→53 correction already being made everywhere else, and worth a
   `DEBT_REGISTER.md` row if not fixed immediately, so the guard's own known blind spot
   doesn't have to be rediscovered next wave the way `handler`/`handlers` already was once.
3. Nothing in `forbidden_hotspots` for either stream was touched by either stream — confirmed
   by reading both streams' own diffs against `1664f90` (`git diff 1664f90 <tip> --stat`) and
   cross-checking every changed path against both `allowed_paths` lists, on the corrected tip.
4. **§0a**: if another live session measured anything against `gate-w45a` between the
   container collapse and the stream's restore, that measurement rests on a window this report
   cannot vouch for — worth asking `W45-JUDGE-X`/`W45-JUDGE-Y` to name explicitly rather than
   assume clean, since they run after this merge and may be the first to touch that lane again.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
