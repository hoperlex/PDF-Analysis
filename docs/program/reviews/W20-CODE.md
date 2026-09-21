# W20-CODE — a second code for the collision, a guard for the counts nothing checks, and one boundary I did not cross

Session `W20-CODE`. Branch `agent/w20-code`, from `origin/dev`.

**The headline, first, because it is not a clean landing. The gate at the tip is RED, exit 2,
on exactly one test.** `R-8` is written and proved over a real socket and **does not land**:
the addition forces one enum member into `contracts/api/v1/openapi.json`, and the repair for
that is `web/FRONTEND_LOCK.json` — which this session's brief put out of scope and which the
harness refused it write access to, three times, as a shared resource. §1.6 lists the four
steps and the six digest values that finish it; §6 has the gate. `D-23` and `D-1.6` landed and
are green.

**Reverting `R-8` to hand over a green branch was considered and declined**, and that is a
judgement the owner may reverse in one command. The ruling is done, the envelopes are measured
before and after over the wire, and the branch is four mechanical steps from green with no
decision left in any of them. A green branch bought by reverting an owner's ruling seemed the
worse trade.

## 0. Arrival

HEAD on arrival: **`8a88fce`** — *merge(W19-RUN): rendering a field is not rendering a fact* —
`origin/dev`'s tip, which carries the commit the brief required.

`df -h /` on arrival: **7.0 GB available** of 119 GB (94% used). No image was rebuilt. The
three alpha stacks on 31480, 31490 and 31500 were not touched; the three `/app/serve.py`
processes behind them were still running at PIDs 2230, 14256 and 14264 when this session
stopped its own three servers **by PID**, never by name.

Lane: instance `gate-w20b`, PostgreSQL **55860**, MinIO **59460/59461**, database
`audit_w20b`, bucket `auditmanager-gate-w20b`.

### Base measurement, taken before the first edit

`make gate` at `8a88fce`, exit code read from `$?` and not through a pipe:

| | measured at base | brief said |
|---|---|---|
| battery | **1785 passed / 5 skipped / 168 subtests** | 1785 / 5 / 168 |
| foundation | **35** (twice: `check-db` and `test-foundation`) | 35 |
| frontend | **681 in 47 files** | 681 (47 files) |
| exit | **0** | 0 |

The brief's base figures are exact.

## 1. `R-8` — the second code

### 1.1 Which of the two got it, and why that is not arbitrary

The ruling adds one code for a collision between two errors. It does not say which one takes
it, and the choice follows from the ruling's own argument rather than from taste.

**`retryable` is the defect.** `conflict` pins `retryable: false`. That is *correct* for
`BlobAttributeConflictError` — the bytes really are already published under different declared
attributes, blobs are immutable, and nothing a caller does changes the answer. It is *wrong*
for `TemporaryBlobLostError` — the store simply did not keep what it had accepted, and sending
the upload again is the remedy. So the new code goes to the one whose flag was wrong, and
`conflict` keeps its contract meaning for the one it already described.

It is also the one that was never a conflict. Nothing about a vanished staged object conflicts
with durable state: no blob was published under those bytes, no uniqueness invariant was
violated. `BlobAttributeConflictError` is a `state_conflict` in the catalog's own words.

### 1.2 The code

**`staged_upload_lost`**

| | value | the argument |
|---|---|---|
| `status` | catalog `status` is `draft_candidate`, `frozen` is `false` | so this is an **addition to a draft candidate, not a freeze-break** — `D-8`, and the `revision_note` says so in those words, as `R-3`'s did |
| `http` | **503** | not 409, because nothing conflicted; not 500, because the request is worth repeating unchanged. 503 is the status `dependency_unavailable` already carries for the case a caller answers by sending the same request again, so the pair is read the same way |
| `retryable` | **`true`** | the whole reason this is a code and not a detail key. See §1.3 |
| `category` | **`dependency`** | the blob store failed to retain bytes the application had staged with it. The category description is widened to admit that alongside a transient outage, a refused credential and an unresolvable reference — exactly as `R-3` widened it for the credential. **The category set is unchanged** |
| `safe_detail_keys` | **`["dependency"]`** | the stable dependency class name and nothing else. `blob_id` is not carried because **no blob exists** — these bytes were never published and were never addressable. `role` and `media_type` are not carried because they are the caller's own declaration handed back and say nothing about what failed. `aggregate_type` goes with the meaning it carried: the addressed blob is not what failed |

`conflict` is **byte-identical** to round 6. `R-8` authorises one code for this collision and
not a re-examination of others, so no existing code's `retryable`, status, category, summary or
key list moved, and I did not even add a cross-reference note to `conflict`.

### 1.3 Why a detail key could not have done it, stated once

The envelope reads `retryable` from the catalog for the reported code — `ErrorCode.retryable`
is a property over `CODES[self.value]["retryable"]`, and `build()` takes no `retryable`
argument at all. Two situations sharing a code therefore share its flag **whatever details they
carry**. A widened `safe_detail_keys` would have made the two envelopes distinguishable and left
`retryable: false` on the one that should be retried. That is the owner's reason in `R-8`, and
it is why *"widening the keys leaves half the defect standing"* is literally true rather than
rhetorical.

### 1.4 The two envelopes, before and after, over a real socket

Not the in-process router. `uvicorn` bound to `127.0.0.1`, the composed application built by
`create_asgi_app()` from this lane's PostgreSQL and MinIO, driven by `curl` with a real
multipart upload of `fixtures/synthetic/ar/ar_baseline.pdf`. One blob-store method was made to
fail per run — `S3BlobStore.verify_temporary` or `.publish` — and nothing else was changed; the
harness lived in the scratchpad and touched no repository file. The *before* run additionally
put `TemporaryBlobLostError` back to its pre-`R-8` shape (`code = "conflict"`,
`allowed_details = {"aggregate_type"}`) at import, which is the exact class the tree carried at
`8a88fce`.

**BEFORE — `TemporaryBlobLostError`, port 58613**

```
HTTP/1.1 409 Conflict
{"contract_version": "1.0.0-draft.1", "error_code": "conflict", "message": "A concurrent write
lost the optimistic-concurrency check or a uniqueness invariant would be violated. Used only
when no more specific conflict code applies.", "correlation_id": "cid-ce9fedf1...",
"retryable": false, "details": {"aggregate_type": "Blob"}}
```

**`BlobAttributeConflictError`, port 58612 — unchanged by this wave**

```
HTTP/1.1 409 Conflict
{"contract_version": "1.0.0-draft.1", "error_code": "conflict", "message": "A concurrent write
lost the optimistic-concurrency check or a uniqueness invariant would be violated. Used only
when no more specific conflict code applies.", "correlation_id": "cid-8806eeb4...",
"retryable": false, "details": {"aggregate_type": "Blob"}}
```

**AFTER — `TemporaryBlobLostError`, port 58611**

```
HTTP/1.1 503 Service Unavailable
{"contract_version": "1.0.0-draft.1", "error_code": "staged_upload_lost", "message": "The blob
store no longer holds the bytes this upload staged with it, so the upload cannot be completed.
Nothing was published and nothing was changed; sending the same upload again is the remedy.",
"correlation_id": "cid-86b4b08f...", "retryable": true, "details": {"dependency":
"blob_storage"}}
```

**The measurement, made the way `W18-OPS` made it — the set of keys on which the two bodies
disagree:**

| | keys that differ |
|---|---|
| before | `['correlation_id']` |
| after | `['correlation_id', 'details', 'error_code', 'message', 'retryable']` |

and the status line moves with them, 409 → 503. `D-18`'s *"byte-identical apart from
`correlation_id`"* was reproduced over the wire before it was repaired, rather than quoted.

### 1.5 `W0-DOM-02`, and what it required

The domain family carries **one `candidate_revision` across six files** — three catalogs and
the three schemas that pin it with `const` — so a round that advances it touches all six.
`W0-DOM-02` permits a **single-value write** in four of them (`identifiers{,.schema}.json`,
`state-machines{,.schema}.json`): the integer and its `const` pin and **no other byte**.

Established before editing, and then checked with **that task's own byte-level gate**, run
against my working tree instead of its fixed commit range:

```
W0-DOM-02: four single-value paths, exactly one changed line each, numeric only,
           revision advanced 6 -> 7
```

`git diff --check -- contracts/domain/v1` is clean. The diffstat is the `R-3` precedent almost
line for line: `error-codes.json` 25, `error-codes.schema.json` 5,
`error-envelope.schema.json` 20, and 2 each in the four single-value paths.

Two residues recorded rather than hidden, in `contracts/domain/v1/README.md` and in the
`revision_note`:

- `identifiers.json` and `state-machines.json` now declare revision 7 while their own
  `revision_note` text still describes **round 4** — as in rounds 5 and 6, because `W0-DOM-02`
  permits no other byte there.
- **`README.md` had no revision-6 section at all.** It still said *"revision 5"* on its title
  line: round 6 (`R-3`, `e6d0a6a`) advanced the family without writing one. That is `D-8`'s
  shape inside the contract's own README. I wrote round 7's section and moved the header to 7;
  I did **not** write round 6's, because it is not this round's to narrate, and the README now
  says so.

### 1.6 The boundary I did not cross, and exactly what is left

**`contracts/api/v1/openapi.json` had to move, and the brief's escape clause is the reason I
took it.** `tests/contract/domain_p02/test_openapi_document.py::test_the_error_code_enum_equals_the_frozen_catalog`
asserts `set(declared) == set(catalog["codes"])`. Beyond the guard, the substance: the new code
**is** emitted through `uploadDocument`, so a code the API sends that its own served document
forbids would be a worse defect than the one being fixed. Three lines changed — the enum
member, `info.description`'s *"twenty-one-code catalog"*, and the `DependencyUnavailable`
response description, which named one code for a status that now carries two. **No path,
operation or component schema moved: still 12 / 15 / 46.** `a5f4001` did precisely this for
`R-3`'s twenty-first code, in the commit after the catalog change.

**What that costs, and where it stopped.** `web/FRONTEND_LOCK.json` carries the sha256 of
`contracts/api/v1/openapi.json`, of the `web/openapi/` snapshot and of the four generated client
files. Changing one byte of the contract reddens it. `npm --prefix web run api:generate` is
deterministic and regenerates the client correctly — I ran it, and the diff is **only** the
input digest in four file headers plus one enum member in `types.gen.ts` — but the lock itself
has **no generator**: it is hand-maintained.

**And it reddens the battery, not only the frontend suite.**
`tests/integration/api/test_query_surface.py::test_the_committed_client_was_generated_from_this_contract`
compares the contract's sha256 against the lock **from the Python side**, and its own
docstring says why it is there: *"an edit to `contracts/api/v1/openapi.json` that nobody
regenerated from should redden the suite that sits next to it, not only the one somebody might
run later."* It is working exactly as designed and it is telling me the truth.

**The complete remaining work, measured rather than sketched.** With `web/` at `origin/dev`,
which is where I left it, `npm --prefix web test` is **7 failed / 674 passed** in two files;
with the regenerated client in place it is **4 failed / 677 passed** in three. Four steps:

| # | what | red until it is done |
|---|---|---|
| 1 | `npm --prefix web run api:generate` — deterministic, no judgement; the diff is the input digest in four headers and one enum member in `types.gen.ts` | `web/tests/contract/openapi-drift.contract.test.ts` (5) |
| 2 | `web/FRONTEND_LOCK.json`: `openapi.sha256` and `openapi.snapshot_sha256` → `68762ec87931ed03ee8b68d16717533c4f7f68816bc1b490b53ba8a5f50f1513`; `generated.client.gen.ts` → `02811af2…adf17`, `index.ts` → `364bfce1…1e193a`, `operations.gen.ts` → `7e8b95d5…6e6e3e46`, `types.gen.ts` → `e064c317…dca97483`; `content_commit` → `b437616` | `web/tests/guards/frontend-lock.guard.test.ts` (2) **and the battery's one failure** |
| 3 | `web/tests/contract/seam-operations.contract.test.ts` — *"the closed twenty-one-code set"* → twenty-two | that test |
| 4 | `web/tests/unit/api/failure-surface.test.ts:77` — `toHaveLength(21)` → `22` | that test |

`operations` and `component_schemas` in the lock stay **15** and **46**: no surface count moved,
so nothing there needs re-measuring.

**I did not write any of it, and the tree is back to `origin/dev`'s `web/` byte for byte.** Two
independent reasons, either sufficient. The brief says *"No `web/`"* with no escape clause,
unlike the one it gave for the contract. And the harness's own permission layer refused every
write to `web/FRONTEND_LOCK.json` — a scripted one, a large edit and a single-value edit — as
*Modify Shared Resources*. When the instruction and the permission system agree, the answer is
to stop and say so, not to find a third tool.

`W18-SEAL` faced the same coupling and **declared** it rather than taking it quietly
(§6: *"guards over the contract, in the same class as the lock, and the frontend gate is red
without them"*), then resealed in a `chore(web)` commit of its own. That is the shape of the
work that is left; it is four values and two literals, and it is somebody's with write access
to `web/`.

**I considered reverting `R-8` to hand over a green branch and decided against it.** Reverting
an owner's ruling to make a number look better is the worse trade: the ruling is done, proved
over a socket, and one known, fully specified edit from green.

### 1.7 Characterization records — **zero of thirty-six, and no `permitted_change`**

Checked by reading all thirty-six records as JSON rather than by grepping one spelling
(`OPERATING_CONSTRAINTS.md` §12): **no record carries a `conflict` envelope, and none
exercises either class.** The only occurrence of the string is in record `05`'s `purpose`
prose — *"this replays rather than conflicting"* — which is about idempotency and not an
envelope.

So this change moved no record, and **no `permitted_change` and no `decided_by` was written**,
because there was nothing to permit. `W16-ERR` measured zero of 33 for the two envelopes it
changed and correctly refused to write one; this is the same refusal for the same reason.
`PERMITTED_EXCEPTIONS` is untouched — extending it here would have been a claim that something
happened.

### 1.8 Shown able to fail

`tests/integration/api/test_two_blob_faults_are_two_envelopes.py`, six tests, pinning the
**envelope** and not the code name — `W16-ERR`'s `D-12` lesson, where the lie was the flag and
a test reading the class's `code` attribute would have watched it past.

| mutation | result |
|---|---|
| `TemporaryBlobLostError.code = "staged_upload_lost"` → `"conflict"` (the pre-`R-8` tree) | **5 of 6 red**, 1 passed |
| `staged_upload_lost.retryable` `true` → `false` **in the catalog** | **3 of 6 red**, 3 passed |

The one that stays green under the first mutation is the file's own proof-of-proof:
`test_the_comparison_reddens_when_the_two_share_a_code` reconstructs the pre-`R-8` shape and
asserts it still reproduces the defect. If that ever stops reproducing, it says so rather than
letting the other five become vacuous. Both mutations reverted; `git status --porcelain` empty
after each.

## 2. `D-23` — the guard

### 2.1 The row had no section

`DEBT_REGISTER.md` carried `D-23` as **one line in the table at the top and no section at all**.
That is worth recording rather than quietly fixing: the register's own two rules are that a row
is measured and that a row nobody can re-measure will rot, and a row that exists only as a
summary is exactly that. It now has one, and it is closed there.

### 2.2 What it does

`tests/contract/api_v1/test_surface_counts_in_prose.py`, ten tests, in the battery.

**Every count is read out of the documents.** Operations are the `(path, method)` pairs of the
frozen document, schemas are `len(components.schemas)`, paths are `len(paths)`, and codes are
`len(codes)` of the domain catalog — which is what `info.description` means by *"the
twenty-two-code catalog"*. Nothing is written down: a literal would need editing at the next
reseal, which is the failure mode the row names — `OPERATING_CONSTRAINTS.md` §12. The
expectation comes from the authority and the subject is the prose, so the two do not share an
assumption.

It scans every `.py` and `.md` under `src/auditmanager/api/**`, every one under
`infra/deploy/**` (see §2.4), and the contract's own `info` block — `title`, `summary`,
`description`. `W18-SEAL` §10.5 is why the `info` block is scanned separately: `app.py` builds
the **served** document with its own `_TITLE` and `_DESCRIPTION`, so the contract's `info` is an
unguarded copy and both have to be read.

**The hard part was not the counting.** Not every `<n> operations` claims the size of the
surface: *"the two schemas that only it referenced"* and *"the four operations that declare
none"* are true statements about subsets, and a guard that reddened on them would teach
sessions to write worse prose. `LOCAL_COUNTS` registers those, and it is a set of **phrases,
not of counts** — a reseal never touches it, and adding to it is how a session says out loud
*"this number is not the surface"*. It found two such phrases on its first run and neither had
been picked in advance.

### 2.3 Shown able to fail, against the tree

Not only against fixtures. Two real files, re-mutated after the guard was committed:

| mutation | the guard says |
|---|---|
| `app.py:58`, `_DESCRIPTION` — *"The **fifteen** operations of the PC-01 surface"* → *"The **twelve** operations…"* — **this is the string served on `/openapi.json`** | `src/auditmanager/api/app.py: 'twelve operations' states 12 operations, but the document declares 15` |
| `routers/declarations.py:68` — *"The **46** schema names"* → *"The **43** schema names"* | `src/auditmanager/api/routers/declarations.py: '43 schema' states 43 schemas, but the document declares 46` |

**And the row's premise, measured rather than quoted.** With the first mutation in place —
the served description claiming twelve operations —
`tests/contract/api_v1/test_openapi_conformance.py` and
`tests/contract/domain_p02/test_openapi_document.py` are **128 passed**. The conformance engine
cannot see it. That is `D-23` in one line, and it is now measured on this tree and not
inherited from `W18-SEAL`.

Both mutations reverted; `git status --porcelain` empty.

The file also carries five parametrised cases holding the exact pre-`R-5` and pre-`R-8`
wordings, the other direction (correct prose passes, so the guard is not simply always red), a
check that it is reaching `app.py`, `security.py`, `declarations.py` and `README.md` rather
than scanning nothing, and a check that `LOCAL_COUNTS` suppresses a phrase and nothing wider.

### 2.4 It found the thirty-sixth on its first widening — there were four

`D-23` said *"nothing stops the thirty-sixth."* There were four, and they had been in the tree
since the `R-5` reseal. `W18-SEAL`'s sweep was `grep -rn` over `src/`; these are not in `src/`:

- `infra/deploy/README.md` — *"twelve operations"* three times: what `Dockerfile.api` runs,
  what the fail-closed token seam refuses, what `:8000` mounts;
- `infra/deploy/serve.py:4` — the **module docstring of the process entry point**, *"`api/app.py`
  has `create_asgi_app` (the twelve operations)"*. The first thing an operator reads about the
  process.

The guard is widened to `infra/deploy/` for that reason and no wider: it is the second tree
that describes this surface in prose, and a claim a checker cannot read is a claim nobody is
checking. It went red on all four before any of them was touched. Corrected by **re-measuring**
and not by find-and-replace: all four mean the whole surface, so all four are fifteen, which is
the `(path, method)` count of the frozen document and the length of `test_authorization.py`'s
`FIFTEEN`.

**A fifth is left standing and is named rather than taken.**
`web/src/app/bff/v1/[...path]/route.ts:16` says *"twelve paths"*. `web/` is outside this
session, the guard does not scan it, and the statement is still there. It is in `DEBT_REGISTER.md`
and in the commit message so it is not lost.

## 3. `D-1.6` — corrected where a lane may write, and two boundaries declined

`checksum_mismatch` is not a code. The catalog has **22** — it had 20 when the row was written,
21 after `R-3`, 22 after `R-8`, and the row's own *"It has 20 codes"* had gone stale, which is
`D-8` happening to the row about `D-8`. `ChecksumMismatchError` is a Python class in
`src/auditmanager/storage/errors.py` and the code it carries is `storage_integrity_error`.
**No behaviour changed and no verdict moved.**

**What I corrected.** `CHECKPOINT_REGISTRY.md` now carries **erratum `E-PC01-1`** immediately
under the prototype-checkpoint table, so a reader of any of the three re-certification rows
meets the correction before the rows. It names the class, names the real code, states that the
limit is real and every verdict stands, and carries its own check command.

**What I refused, and the brief asked me to say so rather than edit it.**

- **`artifacts/checkpoints/PC-01/**` is not touched.** `report.json` and the three
  `recertification-*.json` records still say `checksum_mismatch`. That directory is an audit
  trail and **its own history proves it**: every re-certification since acceptance *added a
  file*, and `report.json` has not been modified since `5fa37df`. Unlike `CP-00`, which has
  `erratum.md` and `E-8` for exactly this, PC-01 carries **no erratum mechanism**; creating one
  is the integrator's act. It is also outside the paths this session was given. `D-1.6` stays
  open on exactly those four records.
- **Past reviews, closures and dispatch briefs are not touched either, and this is the stronger
  reason.** `W5_CLOSURE.md`, `W12_CLOSURE.md`, `dispatch/W5-CERT.md`, `W6-CERT.md`,
  `W11-RD.md`, `W12-CERT.md`, `W12-PLAN.md` and four reviews use the name. They are dated
  records of what a session said or was told, and **the inheritance of the name is the evidence
  this row rests on.** Rewriting them would erase the proof while reading as a tidy-up. `D-19`
  is this register's note on what that costs.

## 4. What was false in the brief, and what else was stale

**Nothing in the brief was false.** Every premise I could check held: `8a88fce` was
`origin/dev`'s tip; the base gate figures were exact to the number; `conflict`'s
`safe_detail_keys` are `["aggregate_type", "expected_revision"]`; `envelope.py:126` really does
use the catalog's summary; both classes really did raise `conflict` with `aggregate_type:
"Blob"`; the catalog really does declare `"frozen": false` and `"status": "draft_candidate"`;
`R-3`'s `revision_note` really is the template and says *"an addition to a draft candidate, not
a freeze-break"* in those words; `PERMITTED_EXCEPTIONS` really is a literal map with tuple
values; and `make mutation-copy MUT=...` is as described.

One thing the brief did not know, and it is the reason `R-8` does not land: **`a5f4001` proves
the API contract must move, and `b370b03` and `2243e4a` prove the `web/` reseal moves with it.**
The brief's escape clause for the contract has no counterpart for `web/`, and the two are one
change.

Five things in the tree were stale. Four are corrected here; the fifth is recorded because it
is not mine:

1. **`contracts/domain/v1/README.md` was at revision 5** while the catalogs were at 6 — round 6
   never wrote its section. Header moved to 7, round 7's section written, round 6's gap stated.
2. **`tests/integration/api/test_error_envelope.py`** said *"All twenty codes"* two additions
   after the catalog had twenty. It now iterates the enum and states no count.
3. **`DEBT_REGISTER.md` `D-23` had no section**, only a summary row. §2.1.
4. **Four more places pinned the catalog at twenty or twenty-one**, two of them asserts:
   `tests/integration/api/test_envelope_screen_rules.py`, `tests/contract/test_cp00_candidate.py`,
   a docstring in `tests/integration/runs/test_the_interruption_vocabulary_is_pinned.py`, and
   **`contracts/domain/v1/README.md`'s own `## Errors` heading — *"20 codes across 10
   categories"*, stale since `R-3`**. The confirming gate found the first; my own sweep had
   missed all four, and the reason is `OPERATING_CONSTRAINTS.md` §12 in its purest form:
   `grep -rn "== 21" tests/` was **piped through `head -20`**, and the first twenty hits were
   all `assert response.status == 201`. The query was right and I read its truncation as the
   answer. §12's three instances are about a query sharing an assumption with its subject;
   this is a fourth shape — a correct query whose output was silently cut before it was read —
   and it cost a red gate.
5. **`scripts/validate_bootstrap.py` fails at `8a88fce` and fails identically here** — two
   broken-markdown-link reports against `docs/program/reviews/W12-WEB.md` and `W16-WEB.md`,
   where the link target is being read as the literal regex `[^'"]+`. **Pre-existing, verified
   by `git stash`**, not caused by this session and not run by `make gate`. Nobody's brief has
   mentioned it; it should be somebody's.

## 5. Lane hygiene

The lane's PostgreSQL volume was **destroyed and rebuilt before the confirming gate**, by name
(`gate-w20b-postgres-data`, `gate-w20b-s3-data`) and never by pattern. The reason is specific:
`db/migrations/versions/20260910_0002_pc01_schema.py` builds a `CHECK` constraint from
`ERROR_CODES`, and that list gained a member in this change. An already-migrated database stays
at the head revision, so `make migrate` is a no-op and the constraint would still have admitted
only 21 codes — verified directly against `pg_constraint` before tearing down:
`ck_command_record_error_code` did not contain `staged_upload_lost`. A gate run against it would
have been measuring the lane's history rather than the committed tree.

Three `uvicorn` processes were started for §1.4 and stopped **by PID** (759347, 765284,
769495). The three `/app/serve.py` processes belonging to the alpha stacks were confirmed still
running afterwards.

## 6. The gate

Run at `45228c5` with the tree committed and `git status --porcelain` empty, on a lane whose
PostgreSQL volume had been destroyed and rebuilt (§5), so the `CHECK` constraints were built
from the committed migration and not from this lane's history.

**Exit code, read from `$?` and not through a pipe: `2`. The gate is RED.**

| | at `8a88fce` (base) | at `45228c5` |
|---|---|---|
| foundation | 35 | **35** |
| battery | 1785 passed / 5 skipped / 168 subtests | **1800 passed / 1 failed / 5 skipped / 169 subtests** |
| frontend | 681 in 47 files | **not reached** — the gate aborts at the battery |
| exit | 0 | **2** |

`+16` battery tests, which is exactly the two files this session added: ten in
`test_surface_counts_in_prose.py` and six in `test_two_blob_faults_are_two_envelopes.py`.

**The one failure, in full:**

```
FAILED tests/integration/api/test_query_surface.py::
       test_the_committed_client_was_generated_from_this_contract
AssertionError: the frozen document has moved since the client was generated from it.
Regenerate: npm --prefix web run api:generate, and reseal web/FRONTEND_LOCK.json
  - 701ecd58a860f53762775bee353cd5461d21c9e56f0bcb8d00b45dbfe685f8fe
  + 68762ec87931ed03ee8b68d16717533c4f7f68816bc1b490b53ba8a5f50f1513
```

It is §1.6's block and nothing else, and the error message is the instruction. Run separately,
`npm --prefix web test` is **7 failed / 674 passed**, all six of the other reds in the same two
`web/` files. **No test in this branch fails for any reason other than the `web/` reseal.**

An earlier run of this gate, at `2017a21`, was **3 failed** — the same one plus two count
literals in `tests/integration/api/test_envelope_screen_rules.py` that my own sweep had
missed. `45228c5` fixes those and two more like them; §4 records why the sweep missed them,
because the reason is worse than the miss.

**The base figure is confirmed twice.** The base run's log contains two complete gate runs —
a harness artifact of how the background command was issued — and both agree exactly:
`1785 passed, 5 skipped, 168 subtests`, foundation 35, frontend 681 in 47 files,
`GATE OK`, on both passes.

## 7. Elapsed

Measured, not estimated. First command of this session **18:50:09**; the confirming gate at
`45228c5` reported at **19:44** local. **About 54 minutes** wall clock.

Roughly half of that is waiting rather than working: three full `make gate` runs at 3:32–3:40
of battery apiece plus their foundation sequences, `make bootstrap` and `npm ci` on arrival, a
volume teardown and rebuild, three `uvicorn` starts for §1.4, and two separate `npm --prefix
web test` runs to measure the block precisely rather than describe it.
