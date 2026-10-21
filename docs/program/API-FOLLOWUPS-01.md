# API-FOLLOWUPS-01 — hand-back report

- Task: the two open `API` follow-ups of `docs/program/DEBT_REGISTER.md`: `D-176` (wire the revocation
  memory) and `D-185` (measure the synchronous optimisation pass).
- Branch `agent/api-followups-01`, base `origin/dev` `2affede8`. Contract `1.0.0` (sealed, frozen),
  migration head `0029`, surface 73/83/242 and 27 error codes are untouched: no file under `contracts/**`,
  `db/migrations/**`, `web/**`, no dependency or lock file, no register and no `CURRENT_STATE.md` was edited.
- Light acceptance (`AGENTS.md` section 8) on this lane's own stack. The debt register is the integrator's:
  the rows proposed below are proposals.

## 1. Outcome per debt

| Debt | State after this lane | Where |
|---|---|---|
| `D-176` | **Closed in code.** `RevocationNotices` is created per assembled application in `_assemble` and passed to the seam and to the upload door. An end-to-end test over real accounts proves the second upload under a revoked credential is refused before its body is read and without a database read. | `api/app.py`, `tests/integration/api/test_upload_door_revocation_is_wired.py`, `ACCESS-STORAGE-HARDEN-01.md` section 4 |
| `D-185` | **Measured, and the worst case repaired in code.** At the bounds one pass took 206 s (`one_head_dissimilar`) and 1 853 s (`one_head_similar`) on the old code, against the 290 s of the web tier; both now take 3 s and 6 s, and the slowest shape constructed (`wide_vocabulary`, contrived) 92 s p50 / 130 s max. Outputs are byte for byte the old ones; no contract, error code, migration or web change was needed. | `optimisation/proposals/generator.py`, `optimisation/matching.py`, `tests/unit/optimisation/**`, `tests/integration/optimisation/proposals/measure_worst_case_pass.py` |

## 2. `D-176` — the revocation memory is wired

### 2.1 The change

`api/app.py`, `_assemble`: `notices = RevocationNotices()` before the application object, then
`build_authorization_dependency(..., notices=notices)` and `build_credential_precheck(environ, notices=notices)`.
It is created per call, not at module level: two applications built in one process over two databases
whose clones share a seeded account's `user_uid` and epoch must not share what either has learned.

### 2.2 The proof

`tests/integration/api/test_upload_door_revocation_is_wired.py` (5 tests) drives the application
`create_asgi_app` assembles, over cloned real PostgreSQL databases, with accounts made through `access`,
credentials from the real `POST /auth/token`, and revocations made by the operators' repositories (`archive_account`,
`revoke_credentials`) or by deleting the row.

How "no read" is asserted, and why the assertions can fail:

- **The body.** The test calls the application as a bare ASGI callable and counts how often it asked `receive` for the
  request body. A door refusal answers without calling it.
- **The database.** The account port is wrapped by a counter, and a SQLAlchemy `before_cursor_execute` listener counts
  every statement the clone's engine runs, so a read that bypassed the port would still show.
- Both counters are asserted to be **positive on the first, admitted-then-refused attempt**: the door cannot know, the
  body is asked for, the seam reads the account, refuses and notes the pair. That proves they can see a read at all.
- The later attempts (three of them) answer the identical `401 authentication_required` envelope with `body_reads == 0`,
  no `standing_of` call, no statement, and no call to the documents port.

What is covered: an archived account; a raised credential epoch; a deleted row; an unrevoked account (uploads
before and after, and beside, a revoked one: always admitted, never written down); a later generation of the same
account (signs in again after the epoch rose: admitted, while the old generation stays refused); and two applications in one
process (the same signed credential is valid in both clones, is revoked in one, and the other still admits it with its
body read until it has learned for itself).

### 2.3 Mutations (single textual replacement, run, restored)

| Mutation | Result |
|---|---|
| W1 door built without the memory (`build_credential_precheck(environ)`) | archived-account test fails: attempt 2 asked for the body |
| W2 seam built without the memory | same test fails: nothing is ever noted |
| W3 one memory shared by every application in the process | the two-application test fails: 401 where the second clone must admit |
| W4 seam notes every credential it sees | the archived-account test fails: the first attempt after revocation is refused at the door |
| W5 door ignores the memory (`return True`) | the archived-account test fails: attempt 2 asked for the body |
| W6 seam never notes (`pass`) | the archived-account test fails: attempt 2 asked for the body |
| W7 memory answers for every generation of the user | the later-generation test fails: the renewed credential is refused |

### 2.4 Closing `D-176`: the commands

```
make up check-services migrate        # the lane's own stack; FOUNDATION_PYTHON=/usr/bin/python3.12
.venv/bin/python -m pytest -q tests/integration/api/test_upload_door_revocation_is_wired.py \
    tests/integration/api/test_upload_front_door_credentials.py       # 5 + 21 passed
git grep -n "notices=notices" src/auditmanager/api/app.py             # two sites: the seam and the door
```

## 3. `D-185` — the optimisation pass at the bounds

### 3.1 What runs inside the request

`POST /projects/{p}/documents/{d}/optimisation-passes` (`startOptimisationPass`) is a synchronous route. In one
transaction, holding one of the pool's ten connections and the version's advisory lock, it: reads the price list's
positions (at most 20 000, `MAX_DATA_ROWS`; four pages of 5 000), reads the run's saved text layer from the object store,
extracts the specification (at most 10 000 rows, `MAX_SPECIFICATION_ROWS`, else `specification_too_large`), matches every
row to the price list, generates the cheaper-analog proposals (at most 3 per row, so 30 000) and inserts them. The
bounds fix the size of the input; they say nothing of its shape, and the cost is a function of the shape.

### 3.2 The timeouts on the path

| Hop | Timeout | Source |
|---|---|---|
| proxy to the API, and to the web tier | `proxy_read_timeout 300s` (server level; the API and BFF locations set none of their own) | `infra/deploy/proxy/nginx.conf:148`, `tls-server.conf:84` |
| web tier to the API | `UPSTREAM_DEADLINE_MS = 290_000`, **only for a request that sends a body**; this route sends none, so undici's own 300 s wait applies | `web/src/shared/api/credentialed-forward.ts:123`, line 315 |
| browser | none (`transport.ts` sets no deadline) | `web/src/shared/api/transport.ts` |
| the API process | none (`uvicorn`, no per-request limit) | `infra/deploy/serve.py` |

The smallest timeout on the path is 290 s (the web tier's, taken here even though this route does not reach it) and the
smallest that applies to this route is 300 s. When it passes, the proxy answers a `504` HTML page, the API goes on
computing and commits the pass after the caller has gone, and the connection and the lock were held throughout.

### 3.3 Method

- **Stack.** This lane's own: PostgreSQL 17 and MinIO in containers on loopback, `make up check-services migrate`.
  The host is shared (8 cores, 11.8 GB, other lanes and projects building images): load average 4 to 26 during the
  runs, so wall times are inflated and the CPU time (`time.process_time()`) is given beside them.
- **The request is the real one** (`tests/integration/optimisation/proposals/measure_worst_case_pass.py`): the assembled
  application (`create_asgi_app`), the real seam and credential exchange, the shipped `OptimisationProposalAdapter` over the
  clone database, a price list uploaded through `PriceListUploads` into a real bucket, an AR version classified by an
  expert. The saved text layer is served from memory (the composition root's reader fetches one blob of about a megabyte).
  Each repetition publishes a new vendor-list revision (the notes differ), which changes the inputs the pass pins and so
  makes the server compute a fresh pass instead of answering the stored one.
- **Largest legal input.** 20 000 positions, 10 000 rows on 250 pages, a 500-entry vendor list; the shape is
  one of the scenarios below.
- **Memory** is the kernel's high-water mark of the test process (`VmHWM`, reset by writing `5` to
  `/proc/self/clear_refs` before each request), so it includes about 150 MiB of the process itself before the request.
- **p50/p95/max** over N runs by nearest rank; with N from 3 to 10, p95 is the maximum.
- **Pure stage costs** (no stack): `tests/unit/optimisation/proposals/measure_stage_costs.py`, same scenarios.

Commands:

```
D185_SCENARIO=<scenario> D185_RUNS=<n> .venv/bin/python -m pytest -q -s \
    tests/integration/optimisation/proposals/measure_worst_case_pass.py
PYTHONPATH=src .venv/bin/python tests/unit/optimisation/proposals/measure_stage_costs.py <scenario>
```

| Scenario | The shape |
|---|---|
| `catalogue` | 200 head words of about 100 positions each, every row matches one by name. A real price list at the maximum size. |
| `one_head_similar` | One head word, unit and currency; every pair of names differs by one word, so every pair is an analog. |
| `one_head_dissimilar` | The same bucket; no pair is similar enough, nothing is proposed. |
| `two_words` | `Профиль 17`: names that differ by one number each. |
| `common_code_token` | Every code opens with `ПК` and every row names it. |
| `rich` | Code, mark and a 300-character name on every position: what the 10 MiB file cap allows at 20 000 rows. |
| `flat_price` | Contrived: half the list at one price, all names alike; every row has one equal-price group of 10 000 analogs. |
| `long_overlap`, `wide_vocabulary` | Contrived: 60-token names (about 400 bytes) from 200 tokens, or from as many tokens as there are positions; rows on the dearest positions. |
| `overlap_dissimilar` | Contrived: six words drawn from slots of twenty, so nearly every pair shares a word and almost none reaches the threshold; the rows are the dearest positions, whose cheaper prefix is the longest. |

### 3.4 Measurements

Every row is one scenario: the whole request through the assembled application, on this lane's stack. "Before" is `origin/dev`
`2affede8`; "after" is this lane's tip. Wall is the request as the caller sees it; CPU is `time.process_time()` of the whole test
process during the request. The host was shared and busy (load average in the last column), and wall time follows it; the first
series of this campaign, at a load of 4 to 5 and one revision earlier, ran the `catalogue` request in 5.1 s p50.

| Scenario | Before: wall (CPU), runs | After: wall p50 / p95 / max (CPU p50), runs | Peak RSS (start) | Load |
|---|---|---|---|---|
| `catalogue` | 7.6 s p50, 8.3 max (5.2), 5 | 6.7 / 8.4 / 8.4 s (3.4), 10 | 247 MiB (153) | 17 to 20 |
| `one_head_similar` | **1 853 s** (1 489), 1 | 6.2 / 6.2 / 6.2 s (3.4), 5 | 233 MiB (153) | 15 to 17 |
| `one_head_dissimilar` | **206 s** (199), 1 | 3.1 / 3.5 / 3.5 s (2.9), 5 | 220 MiB (154) | 14 to 15 |
| `two_words` | not run | 2.1 / 2.1 / 2.1 s (2.0), 3 | 209 MiB (154) | 15 |
| `common_code_token` | not run (matching alone: 21 s CPU, below) | 6.3 / 6.5 / 6.5 s (3.8), 3 | 237 MiB (152) | 12 to 14 |
| `rich` | not run (the generator alone did not finish in 300 s) | 26.0 / 31.8 / 31.8 s (17.9), 3 | 529 MiB (198) | 11 to 15 |
| `flat_price` | not run (4 000 x 2 000: 21 s CPU, below) | 56.6 / 57.5 / 57.5 s (29.4), 3 | 215 MiB (153) | 21 to 24 |
| `overlap_dissimilar` | not run (4 000 x 2 000: 10 s CPU, below) | 42.4 / 58.4 / 58.4 s (36.6), 3 | 228 MiB (152) | 13 to 19 |
| `long_overlap` | not run | 82.6 / 87.6 / 87.6 s (70.0), 3 | 373 MiB (124) | 13 to 17 |
| `wide_vocabulary` | not run | 92.3 / 130.3 / 130.3 s (83.7), 3 | 440 MiB (187) | 8 to 20 |

The smallest timeout on the path is 290 s (section 3.2). The two bold "before" figures are 0.7 and 6.4 times it; the largest "after"
figure is 0.45 times it. The "before" load was 6 to 8 for the first two rows and rose to 26 during the last (its CPU time, 1 489 s,
is twice the 753 s the same stage took at a load of 11 in the stage table below: what a loaded host does to a CPU-bound request).

Stage costs without the stack (`measure_stage_costs.py`, CPU seconds, 20 000 positions and 10 000 rows; "before" is the same
script on the old code):

| Scenario | extract | match: before -> after | generate: before -> after |
|---|---|---|---|
| `catalogue` | 0.4 | 0.46 -> 0.50 | 2.7 -> 1.0 |
| `one_head_similar` | 0.4 | 0.54 -> 0.47 | **753** (838 wall) -> 1.0 |
| `one_head_dissimilar` | 0.5 | 0.56 -> 0.55 | **151** (173 wall) -> 0.9 |
| `two_words` | 0.3 | - -> 0.38 | not run -> 0.6 |
| `common_code_token` | 0.4 | **21.1** (23.0 wall) -> 0.85 | stopped, not measured -> 0.9 |
| `rich` | 1.5 | 9.7 -> 9.5 | did not finish in 300 s -> 3.5 |
| `flat_price` | 0.4 | - -> 0.48 | 4 000 x 2 000: 21.1 -> 0.9; full size: 21.7 |
| `overlap_dissimilar` | 0.7 | 0.9 -> 0.82 | 4 000 x 2 000: 10.0 -> 1.1; full size: 31.8 |
| `long_overlap` | 2.7 | 5.2 | before the masks, full size: 587 (740 wall); now 41.4 |
| `wide_vocabulary` | 2.5 | 5.1 | full size: 84.5 (104.6 wall) |

Not part of the cost above: the saved text layer of the largest specification (250 pages, 520 KB of JSON) is read from the
object store in 9 ms (p50 of 20 reads, 12.5 ms max), SHA-256 0.3 ms, parse 1.2 ms. The `catalogue` request's CPU is 3.4 s against
1.9 s for the three stages: the rest is the read of the 20 000 positions and the insert of 29 400 proposals. Memory: at 6 000 x
3 000 the new code peaks 9 % (`rich`) and 15 % (`wide_vocabulary`) above the old (110 and 118 MiB against 101 and 103).

### 3.5 What was found and what changed

**The bounds fix the size of the input and not its shape, and the cost is a function of the shape.** A real catalogue at the maximum
size (`catalogue`) was a 5 to 8 s request before this lane. Shapes the bounds allow were far outside the proxy's 300 s:

1. **The generator walked every position of a row's bucket** (same unit, currency and head word), built a candidate for each that
   qualified, sorted all of them and kept three. A list whose names share one head word (`Профиль ...` 20 000 times) made that
   10 000 rows x 20 000 positions: 753 s of CPU when every pair qualified, 151 s when none did; `rich` (30-word names) did not
   finish in 300 s.
2. **The matcher's code index held every code that opens with one token in one list** and compared a row that names the token
   with each: 21 s for 10 000 rows against 20 000 `ПК ...` codes.

What changed (`optimisation/proposals/generator.py`, `optimisation/matching.py`). Only how the answer is found: the proposals,
their order, bases, similarities and savings are byte for byte what they were, so `GENERATOR_VERSION` and `MATCH_ALGORITHM` do not
move (a bump would make a stored pass stop being "the pass with exactly these inputs").

- Unit price is the first key of the analog order, so the search needs the cheapest analogs, not all of them. A bucket holds only
  the positions whose vendor is on the list, ordered by price; a row reads the strictly cheaper prefix (rules 1 and 4 at once, by
  `bisect`) one equal-price group at a time and stops after the first group that completes three.
- Inside a group only the best places are kept, by similarity compared by cross-multiplication (exactly) and then source row; only
  those are judged and turned into candidates.
- How many words two names share is `popcount(mask & mask)` over the bucket's 4 096 most frequent words plus the intersection of
  two small sets of the rare ones: exact, and not the intersection of two sets of sixty words for every pair visited.
- A row in a large bucket is searched through lists instead of the prefix when they are small against it: the ranks that carry a
  word of the row besides the head word, that share its code family, or that are short enough to qualify on the head word alone.
  Every qualifying position is in their union; every member is still judged by the same rule.
- Rows matched to the same position share one search. A position keeps its words once.
- Matcher: codes are looked up by their whole token sequence under their first token, one dictionary per distinct code length.

Proof that the output is the old output:

- **At scale, by digest.** `measure_stage_costs.py` ends with a SHA-256 over every proposal (ordinal, row, matched and proposed
  position, bases, similarity, saving, rationale). On `origin/dev` (`git archive origin/dev src contracts` into a directory on
  `PYTHONPATH`) and on this tip it prints the same digest for `catalogue` at 20 000 x 10 000 (29 400 proposals, `0362b5364645e2eb`),
  for `one_head_similar`, `one_head_dissimilar`, `two_words`, `common_code_token`, `rich`, `flat_price` at 4 000 x 2 000,
  `overlap_dissimilar` at 2 000 x 1 000 and `long_overlap` at 1 500 x 800.
- **On small inputs, by construction.** `tests/unit/optimisation/proposals/test_generator_search.py` and
  `tests/unit/optimisation/test_matching_code_index.py`: the proposals equal those of an independent full-scan transcription of the
  module note's six rules (public helpers only) on 1 500 seeded inputs built to collide, 60 buckets of 250 to 450 positions searched
  through the lists, 120 buckets with equal-price groups of dozens, and again with only two or no words covered by the masks;
  `by_code` equals a naive scan of every code and mark on 1 500 seeded inputs. Against the unchanged code six equality tests
  (five of the generator, one of the matcher) pass, as they must, and the six that guard the work or name the new lists fail.
- **The work no longer grows**: a row whose cheapest analogs qualify builds at most three candidates among 399 cheaper positions
  (399 before); an equal-price group of 2 000 builds three (2 000 before); four analogs of one price in rising similarity build
  three; a row whose cheaper prefix has nothing in common is not walked; a row naming a token shared by 2 000 codes makes one lookup.

Mutations (single textual replacement, then restored; every one fails a test named in the table):

| Mutation | First failing test |
|---|---|
| G1 no early exit after three; G2 whole bucket instead of the cheaper prefix; G3 vendor filter off; G4/G5/G6 short-name/family/word lists dropped; G8 a tie displaces the earlier arrival; G9 threshold excludes exactly one half; G10 one search for all rows; G11 short names stop at one word; G12 similarity compared by shared words, not ratio; G14 code family makes no analog; G17 popcount replaced by presence | equality with the full scan |
| G7 lists never used | the through-the-lists test |
| G13 group not cut to the places left | the rising-similarity test (it builds four candidates) |
| G15 rare shared words not counted; G16 rare words not recorded | the masks-cover-two-words test |
| M1 every code length asked for | the shared-token test (59 lookups) |
| M2 a mark overrides a code; M3 codes of more than two tokens never found | `by_code` equality with the naive scan |

### 3.6 What remains, and what is blocked

**No stop rule was reached.** Every shape constructed finished inside the 290 s: the slowest is `wide_vocabulary` (60-token names
drawn from as many tokens as there are positions, rows on the dearest positions) at 92 s p50 and 130 s max wall on a host at load 8 to
20 (84 s of CPU). The shapes that look like a price list take 2 to 26 s.

**What is not proved.** What is left of the search is the walk of a row's cheaper prefix when the lists are not small against it. Its
bound is structural: one walk per distinct matched position, each at most the position's rank in its bucket, so at most 1.5 x 10^8
visits for 10 000 positions in a bucket of 20 000. A visit costs 0.2 to 0.6 us in every shape measured (that bound is 30 to 90 s of
CPU) but the cost depends on the names: a shape that defeats both the masks and the lists (very long names, nearly all of whose words
lie outside the 4 096 most frequent of the bucket and are shared often) would cost more per visit. An XLSX price list may carry names of
2 000 characters (`MAX_NAME_LENGTH`), longer than any shape measured (60 tokens, about 400 bytes: what a 10 MiB CSV allows at 20 000
rows). Such a shape was not constructed and is not excluded. If it matters, the unconditional bound is a refusal from a work estimate
before the generator runs (the sum over the matched positions of their cheaper prefix, one `bisect` each), and the frozen contract
has no code for it: `specification_too_large` is documented as "more than 10 000 rows" (`openapi.json`, `error-codes.json`,
`web/src/entities/optimisation-proposal/model/failure.ts`), and the `conflict_reason` set of `startOptimisationPass` is closed, so
a new reason is a contract change (openapi, error-codes, generated client, web messages). An asynchronous pass or smaller
`MAX_DATA_ROWS` / `MAX_SPECIFICATION_ROWS` (migration `0026`'s CHECKs) are the alternatives. None was started.

**Proposed register wording for `D-185`** (the register is the integrator's): "measured and repaired (`API-FOLLOWUPS-01`): at 20 000
positions x 10 000 rows the request was 206 s to 1 853 s for two shapes the bounds allow and is 3 s to 6 s; the slowest contrived shape
is 92 s p50. Open, narrowed: no work-estimate refusal exists (needs a new `conflict_reason`), so a price list of 2 000-character names
built against the masks is unmeasured; only `cheaper_analog` exists and LLM proposal generation waits for U-06 as before."

## 4. Checks

All on this lane's stack (`auditmanager-api-followups`, ports 57780 / 61400 / 61401), one pytest process at a time, the tree
committed before each run, pytest's own exit status (never a pipe's). Results are at the tip before this section was last edited (`28cab0e6`).

| Command | Result |
|---|---|
| `git diff --check origin/dev..HEAD` | exit 0 |
| `pytest tests/contract` with `--ignore` of `test_cp00_candidate.py`, `test_cp00_final_state.py`, `test_validate_bootstrap.py` | 983 passed, 19 283 subtests, exit 0 (1 min 17 s) |
| `pytest tests/unit/optimisation` | 328 passed, exit 0 |
| `pytest tests/integration/api` (upload door, authorization, surface, journey) | 658 passed (7 min 49 s), exit 0 |
| `pytest tests/integration/optimisation` | 102 passed, exit 0 (1 min 25 s) |
| `pytest tests/integration/access` | 246 passed, exit 0 |
| the two upload-door files (`..._is_wired.py` and `test_upload_front_door_credentials.py`) | 26 passed, exit 0; each of W1 to W7 fails the first (section 2.3) |
| the new generator and matcher files, then each of G1 to G17 and M1 to M3 | pass; each mutation fails one (section 3.5) |

Skipped, by `AGENTS.md` section 8 and the lane's brief: the full gate, the e2e suites, the web battery, the stand.

## 5. Known limitations

- `measure_worst_case_pass.py` and `measure_stage_costs.py` are not collected by a directory run (their names do not match
  `test_*.py`); the first needs a stack. They are the method, not a regression guard: wall time on this host moves with its load, so
  no test asserts a duration. What is asserted is the work (candidates built, lookups made, ranks walked) and equality with the full scan.
- Each end-to-end figure is 3 to 10 runs on a shared host; p95 is the maximum at those counts. The "before" rows for the two slow
  shapes are single runs (14 and 31 minutes).
- The revocation memory, like the pool and the bulkhead, is per process (the freeze states one API process per stand), and its first
  attempt per credential still reads the body, as `ACCESS-STORAGE-HARDEN-01` section 4 says; the three options there are unchanged.
- The pass still holds a pool connection and the version's advisory lock for as long as it runs.
- The residual of section 3.6.
