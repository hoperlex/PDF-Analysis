# Debt register

Written 2026-09-17 by the integrator. **Re-measured against the tree at `315de25`–`80db00f` on
2026-09-18.**

**Measured against the tree, not compiled from closure records** — `W4_CLOSURE.md` §3 records a
register that had been entirely obsolete while still reading as the list of what was open, and this
file exists to not become that. It very nearly did anyway; see the two rules below.

**What is open right now**, so a reader does not scan twenty-five rows to find out:

| | Row | Needs |
|---|---|---|
| **D-18** | a catalog code costs a frontend reseal; built, proved, reverted by **`R-11`** | owner |
| **D-15** | one `cost_basis` over a figure summed across attempts | design call |
| **D-24** | `--dry-run` under-reports the wipe, in the dangerous direction | `infra/` |
| **D-25** | a quotation's caption gives document-global offsets as page-local | `web/src` |
| **D-26** | two sentences that stopped being true | `infra/`, `web/src` |
| **D-27** | nothing notices when the deployed stack drifts from the tree | a probe |
| **D-28** | an unrouted path answers 200; a status code proves nothing | `web/src/app` |
| **D-29** | `npm run test:unit` exits 1 though its tests pass | `web/` |
| D-1.6, D-8 | names the programme repeats without opening the file | prose |
| **D-9** | corpus: the join is local after all; segmentation is the real work | **ruled `R-9`**: after the screens |
| D-11 | a licence reading | registered |

**Closed 2026-09-18** — sixteen rows: D-1.5, D-2, D-3, D-4, D-5, D-6, D-7, D-10, D-12, D-13,
D-16, D-17, D-19, D-21, D-22, and D-14, which opened and closed in the same pass.

**Two rules this register earned the hard way, both on the same day:**

1. **A row is closed in the same commit as its fix, or this register lies.** D-2 and D-4 were
   fixed **thirty-nine minutes after this file was created**, by a stream dispatched to fix them,
   with a test file that names both rows in its third line. They sat open here for a day.
2. **A row is measured across every site that can produce the behaviour, not the first one that
   explains it.** I then closed D-4 on one module's evidence while a second module still did it.
   `W16-ERR` caught it. That is `OPERATING_CONSTRAINTS.md` §12's rule about queries, applied to
   closes.

Every row names how to check it. A row nobody can re-measure is a row that will rot.

## 1. Open, and mine to schedule

### D-1 — PC-01's certification no longer describes the tree — **CLOSED**

**Closed 2026-09-17 by `W12-CERT` at `e6eae1e`: PC-01 holds, with one named exception
(`W12CERT-DEF-3`, §1.5).** Record at `artifacts/checkpoints/PC-01/recertification-e6eae1e.json`.

**This row was stale within a day of being written**, and the failure is worth keeping. It
said "126 lines across 8 files", measured at `5c84f43` — before stage A moved
`reconciliation.py`. At `e6eae1e` the same command gives **9 files, 232 insertions, 33
deletions**. `W12-CERT` caught it.

The header said which commit the measurement came from, and that was not enough: a reader
takes a figure from a row, not from a header. **A measured figure needs its commit beside it,
in the row.** Every figure below now carries one.

Check: `git diff --shortstat c0d7daf..<commit> -- src/ db/`.

### D-1.5 — `W12CERT-DEF-3`, the named exception to the certification — **CLOSED**

**Closed 2026-09-18 by `W16-WEB`.** PC-01's certification had one named exception and this was
it: 34 modules of `web/src` reached by no test, holding the rendering behind criterion 4, with
**ten mutations run and all ten surviving** on a green 440-test suite — including *"`run-progress`
stops rendering `terminal_reason`"*.

**Six of those ten are now killed**, plus **12 of 12** mutations `W16-WEB` wrote against its own
new tests — because a suite that kills someone else's mutations has not shown its own assertions
can fail. Reachability 34 unreached → **0**. Frontend **498 → 592**.

**Four survivors, each argued rather than quietly dropped:**

* **U-06/07/08** — unreddenable **by construction**: one render pass, `useRef` always fresh. The
  rule itself *is* guarded in its pure form as `resolveIntentKey`; the three hooks are hand-copies
  that each say in their own comment that they belong in `shared/lib`. **The repair is a `web/src`
  edit, not a test** — move the rule and have the three call it. Correctly not made here: D-1.5 is
  a testing row. Carried forward as **D-22**.
* **U-10** — the *effect-time* cache seed. What it costs if broken is one wasted request on an
  already-terminal run, not a wrong screen. Genuinely unguarded and deliberately left.

**U-04 and U-05 were killed by a source guard, not by a render, and the report says so in the same
breath rather than presenting the two as equivalent.** Both live in closures only an event fires.
`web/tests/guards/upload-precheck-wiring.guard.test.ts` scans the real source and then proves the
scanner fires by applying `W12-WEB`'s own `b8.json` substitutions in memory, byte for byte. **It
proves the statements are present and wired; it does not execute them.**

**And `W12-WEB` §10 is wrong** that seven of the ten are reachable by `renderToStaticMarkup`. Four
are — U-01, U-02, U-03, U-09. U-04, U-05 and U-10 are not.

**The `Check:` line this row carried was broken, and had been under-reporting for two waves.**
`W12-WEB` §11's reachability script matches `(?:from|import)\s+['"]…['"]`, which demands whitespace
after the keyword. A **dynamic** import has a parenthesis there, so it is invisible to the script.
Verified here independently:

```
import { a } from '@/shared/x'      -> ['@/shared/x']
await import('@/shared/api/x')      -> []            <- the bug
```

Counting both forms gives **`114 80 34`, 1352 lines** — *the same 34 modules and the same 1352
lines* `W12-WEB` listed at `3ebe34d`, module for module. The broken script gives `114 79 35`. So a
session re-deriving this row's own check would have concluded the unreached region **grew**, when
it had not.

**A consequence worth naming: `W15-AUTH` §8.4 was right, and my dispatch's doubt about it was
itself the stale premise.** Its BFF `route.ts` *is* reached, by
`tests/unit/api/server-credential.test.ts:97`, through a dynamic import — exactly the form the
script cannot see.

The "18%" in this row's original text is **16.3%** of a tree that grew: `web/src` is 8273 lines,
not 7604.

Check: any counter that matches a dynamic import as well as `import … from`. **Not** `W12-WEB`
§11's script as written.

### D-1.6 — the programme has been naming a code that does not exist

**`checksum_mismatch` is not in the frozen catalog.** It has 20 codes and that is not one of
them; `ChecksumMismatchError` is a Python class that carries `storage_integrity_error`.

Yet "the `checksum_mismatch` limit" appears in PC-01's accepted report, in the criterion-10
limits of three certifications, in several closures and in my own briefs. Found by `W12-CERT`
while establishing the limit rather than inheriting it — the first pass to ask what the name
referred to.

Nothing is broken by it: the limit is real and the behaviour is right. But a limit named after
a non-existent code invites a reader to look for one, and that is how the 21st-code question
gets asked about the wrong thing. Worth correcting in the artifacts that state it; **not**
worth a behaviour change.

Check: `python3 -c "import json;d=json.load(open('contracts/domain/v1/error-codes.json'));print(len(d['codes']))"` and grep for the name.

### D-2 — `verify_version` compares two declarations and never hashes bytes — **CLOSED**

**Closed 2026-09-17 by `1b2549b`, thirty-nine minutes after this register was written, and
the row then sat open for a day.** The register was committed at 11:00:29; the fix landed at
11:39:47, in the same wave, by a stream dispatched to make it.

`verify_version` now asks three questions, cheapest first, and question 3 is the one this row
asked for: when the two declarations agree — *which is precisely the state in which nothing
has yet looked at the object* — the body is read and hashed against `entry.sha256`. The
manifest entry is the digest independent of the object, so it is the one compared, and the
read is `verify=False` deliberately, because the adapter's own check is the object against
its **own** record — which question 2 has already tied to the manifest — and leaving it on
would make the comparison a branch no test could redden.

Guarded by `tests/integration/ingest/test_reconciliation_reads_the_bytes.py`, whose first
case is this row's scenario verbatim: *a version whose bytes were replaced under intact
metadata is refused*.

**The failure here is this register's, not the code's.** The knowledge was in the tree the
whole time — that test file names `D-2` in its third line. Nobody carried it back. **A row is
closed in the same commit as its fix, or the register lies**, which is the exact thing
`W4_CLOSURE.md` §3 found and this file was created to avoid being.

Check: `sed -n '245,255p' src/auditmanager/ingest/reconciliation.py`.

### D-3 — `_record`'s `cost_basis` default is a defaulted provenance field — **CLOSED**

**Closed 2026-09-18 by the integrator, by removing the default.** The row said it was latent
because *"one call site exists and passes it explicitly"*. Re-measured at `315de25` that had
stopped being true: there were **two**, and the cost-overrun path passed nothing.

**The recorded value was right, and that was the problem.** The overrun figure is
`pin.cost_usd(input_tokens, output_tokens)` — the lock's per-token rates — and never consults
`response.reported_cost_usd`, so `"estimated"` was the true provenance. But it was true by
coincidence of the default rather than because the call site had decided it, on the one path
an operator reads when a budget broke. Change `overrun` to prefer the reported cost and the
provenance would have gone on saying `estimated` in silence.

`_record` now takes `cost_basis` with **no default**, so a third call site cannot be silent by
accident, and the overrun site passes `"estimated"` with the reason beside it. Two guards,
both shown able to fail: restoring the default reddens
`test_cost_basis_cannot_be_omitted_by_a_call_site`; making the overrun site copy the success
path's expression reddens `test_the_overrun_path_records_the_basis_of_the_figure_it_actually_recorded`,
which constructs the discriminating case — a response that **did** report a cost, recorded
against a figure that did not use it.

Check: `python3 -c "import inspect;from auditmanager.analysis.text.stage import _record;print(inspect.signature(_record).parameters['cost_basis'].default)"`.

### D-4 — an empty digest reaches an operator-facing envelope — **CLOSED**

**The reconciliation half** closed at `1b2549b` alongside D-2: an object recording no digest is
`validation_failed` carrying `aggregate_type="Blob"`, `field="sha256"`, `constraint="recorded on
every published object"` — not an integrity verdict with `actual_sha256=""`, which the code's own
comment calls *"an empty string where a digest is expected, and a claim about bytes nothing has
looked at"*. Guarded by `tests/integration/ingest/test_reconciliation_reads_the_bytes.py`.

**Wave 14 produced that state on a real host by accident, which is the best evidence the choice was
right.** `mc mirror` restored an object whose bytes were intact and whose
`X-Amz-Meta-Content-Sha256` was gone. An operator is told the store has compared nothing to
anything — not that their bytes are corrupt.

**The second site** — `blob_repository.py::_assert_same_content`, `actual_sha256=existing.sha256 or
""` — was found by `W16-ERR` after I closed this row on one module's evidence. Closed 2026-09-18.

**And my re-opened row was wrong about why.** I wrote *"it is reachable, and the schema says so"*,
citing `ck_blob_sha256`'s `CHECK (sha256 IS NULL OR …)`. That constraint permits NULL **in
general**; it is not evidence that a row reaches this comparison carrying one. Reading a permissive
constraint as a reachable state, without checking the writer, is `OPERATING_CONSTRAINTS.md` §12 in
its own right — **a query sharing an assumption with its subject**, three rows below where this file
records the same mistake twice already.

**Measured:** `_assert_same_content` runs only on an `available` or `verifying` row, and two
independent facts stop either carrying a NULL digest —

* `ck_blob_available_is_verified` is `CHECK (state <> 'available' OR (sha256 IS NOT NULL AND …))`,
  so the schema forbids it outright on an `available` row;
* `_INSERT` is the **only** statement in the tree that creates a `blob` row (`grep -rn "INSERT INTO
  blob" src/ db/` returns one line) and it always supplies `verified.sha256`, so a `verifying` row
  never acquires one either.

So the branch is **unreachable, and saying so is the repair.** It now raises `internal_error`
naming the invariant and carrying **no details at all**, rather than inventing an empty digest. An
unreachable branch that invents a plausible value is worse than one that refuses: the empty string
would have reached an operator looking exactly like a digest of nothing.

Two guards, each shown able to fail. Restoring `or ""` reddens the refusal test; pointing the
discriminator at a different constraint reddens the reachability test — **and the first attempt at
that second mutation was vacuous**, because it rewrote the constraint name in the docstring rather
than in the query. The name is now a module constant so the mutation lands where it matters.

Check: `grep -rn 'sha256 or ""' src/` returns nothing.

### D-15 — one `cost_basis` describes a figure summed over several attempts

Found 2026-09-18 while closing D-3. **Measured, not repaired, and the repair is a design call
rather than a fix.**

`runs/executor.py:402` calls `run_text_analysis` in a **retry loop with one meter for the
whole run** — deliberately, so a retry cannot buy a fresh USD 1.00 ceiling (`OD-03`). So a run
can make several model calls. On both the success and the overrun path the stage then emits:

* `metrics["cost_usd"] = round(cost_meter.spent_usd, 8)` — the sum **across attempts**;
* `metrics["cost_basis"] = "measured" if response.reported_cost_usd is not None else …` —
  the provenance of the **last response only**.

A run whose first attempt replayed and whose second reported a cost therefore publishes a sum
over both with one attempt's provenance attached to it. The model-call **records** are exact —
each carries its own basis — so nothing is lost, and this is about a summary field.

Not repaired here for the reason `W11-FIX` gave about this same field: wave 11 made the two
paths symmetric on purpose and changing what the key means is not a lane decision. The options
are to say `estimated` when **any** attempt was, or to drop the key from the metrics and leave
the records as the only answer. Both change what a consumer reads.

Check: `grep -n "spent_usd\|cost_basis" src/auditmanager/analysis/text/stage.py` against
`grep -n "CostMeter(\|run_text_analysis(" src/auditmanager/runs/executor.py`.

### D-5 — the first browser-driven run answered 500, twice — **CLOSED, not reproducible**

**Closed 2026-09-18 by `W15-RUN`, with the envelope this time.** A real headless Chromium
clicked *Start run* against the deployed origin:

```
POST /bff/v1/runs -> 202  {"run_id": "run_01M2RTFR8TNHN7A6QK0WXEJ2ZV",
                           "state": "published", "provider_mode": "live"}
four stages succeeded; +11 793 ms to a terminal screen
```

Independently, through the app's own generated client over the same origin: `202`,
`published`, 10 475 ms. **The 500 does not reproduce**, in either client, on either stack.

**What that does not settle, and `W15-RUN` refused to gloss it.** The only recorded 500 with
this signature is `47469a5` *fix(C1)* **D2** — *"start_run returned a two-field receipt… the
run executed first, every row was written, and then it answered 500 with no run_id"*. It is
dated 2026-09-14, **two days before** the browser session, and is an **ancestor of `241ae92`**,
the commit that recorded D-5. So it explains the 500 only if that harness drove an older
checkout — and the harness is gone.

**The attribution is permanently unanswerable, and that is the row's whole lesson.** It closes
as *not reproducible under a real server, superseded by this measurement*, not as *explained*.
The reason is the one this row flagged hardest when it was written: the only live-transport
evidence the programme had sat outside the tree and logged status lines only.

Check: `docs/program/reviews/W15-RUN.md` §D-5, and the envelopes in `/root/w15run-logs/`
while they exist.

### D-16 — no screen can reach anything after a page reload — **CLOSED**

**Both halves closed 2026-09-18.** The API half by `W18-SEAL` under `R-5`
(10 paths / 12 operations / 43 schemas → **12 / 15 / 46**, adding `listDocuments`,
`listVersions`, `listRuns`, no new error code). The screens half by `W19-SHELL`.

**The acceptance test was a fresh tab, not navigation** — which is the whole row, because
four certifications missed this defect by never reloading a page. One separate Chromium
process per URL, no cache, no storage, no prior client state:

| screen | before | after |
|---|---|---|
| project | **0 API calls**, *"No version published in this session"* | **1** — `listDocuments` |
| document *(new route)* | — | **1** — `listVersions` |
| version *(new route)* | — | **2** — `listRuns` + `getDocumentVersion` |
| run | — | **1** |
| review | — | **5** |
| unknown project | — | `404` *"There is no such project."*, **not an empty page** |
| malformed address | — | **0 calls** — *"That is not a version address."* |

Six addressable screens where there were four, every address built once in
`shared/lib/routes.ts`, and a route back from every screen — **the review screen had none at
all**. Eleven mutations, eleven killed, and **M10 re-inserts the defect itself**: putting
*"No version published in this session"* back is red.

**A frozen document carried the defect as a sentence.** `web/docs/PC01_UI_SEAM.md` §2 is a
route table that read *"there is no route for a document version"*. That sentence **is** this
row, and it was amended with its reason in the same commit as the routes.

**The document route is an address, not a step.** The project screen links straight to the
version, because `listDocuments` already returns it and clicking through a list of one buys
nothing while `uploadDocument` declares no `document_uid`. The route exists because
`document_uid` is a value the product **already prints at a user** — a frozen CSV column, a
field of every `DocumentVersion`, the `aggregate_type` of a `404`. **An identifier a product
prints and cannot open is `D-16` one aggregate smaller.**

~~**What this does not close:** `D-20`.~~ **`D-20` closed 2026-09-18 by `W20-EXEC`**: execution
left the request thread, so `startRun` answers `queued` and a poller reads `running`.

Check: `git grep -l listDocuments -- web/src/_pages web/src/widgets web/src/entities` is
non-empty (3 files), and the browser journal in `W19-SHELL` §4.

### D-17 — a restored instance is proved by reading and broken for writing — **CLOSED**

**Closed 2026-09-18 by `W18-OPS`, and this row's own figure was one key too generous.**

**Read from the adapter rather than from the report:** `S3BlobStore.publish` is the single
publication site, one `copy_object` with `MetadataDirective="REPLACE"`, writing **four**
user-metadata keys — `blob-id`, `blob-role`, `content-sha256`, `content-size` — **plus the
`Content-Type` header**, which `_record_from_head` reads back as `media_type` and `publish`
compares. The old restore carried **one of the four plus the header**. So **three keys were
lost, not one**: `blob-role`, `blob-id` and `content-size`.

**A fix built on this row's original figure would have closed it wrongly.** It would have
carried `blob-role`, passed the write-back test, and left `content-size` lost — whose loss is
**quieter rather than smaller**, because `_record_from_head` raises `SizeMismatchError` only
`if recorded_size is not None`. A restore without it does not fail; it **silently stops
checking**.

**Proved by writing, which was the whole row.** Post-fix: upload `201` → wipe → restore → read
back byte-identical → **re-upload `201`**. Pre-fix, reproduced first-hand at `56f37ab`: read
back byte-identical → **re-upload `409`**. Reading back is **necessary** — a lost
`content-sha256` 422s the read, so wave 14 was right to check it — and **not sufficient**,
because `blob-role` is consulted by no read at all, only by `publish`.

And run against the bucket a pre-fix restore left behind, the fixed script **exits 3, names
the bad row and purges nothing**. That is `R-4`'s commitment holding: it will not destroy an
instance whose objects it cannot put back.

**A second defect, and it is the more general one: `dump-verified`'s empty-digest check had
never fired.** The test was `grep -q '^[^\t]*\t\t'`, and **GNU grep does not read `\t` as a
tab outside a bracket expression** — it is the letter `t`. Confirmed independently here:
`/usr/bin/grep` is GNU grep 3.11 and gives **no match** on a row that should match. It looked
correct only because an interactive agent shell routes `grep` through ugrep, which does read
`\t`; a script run as a subprocess never sees that, so **the guard was inert everywhere,
including inside its own test suite**. It had no case, so it had never been shown able to
fail — which is the entire argument for the rule that every guard needs one.

Guard markers stay at **11** — widened, not added — so the meta-test still pins the count and
every marker still has a case. Suite **23 → 31**; six redden against the pre-fix script, and
the two that do not are the control and the deletion proof, which should not.

Check: `grep -c 'guard:' infra/deploy/reset.sh` is 11, and
`.venv/bin/pytest tests/integration/composition/test_reset_script_refusals.py` is 31.

### D-18 — that 409 cannot be diagnosed from the wire — **OPEN, and now a narrow question**

**Measured by `W18-OPS` without touching `contracts/`.** `conflict` declares
`safe_detail_keys: ["aggregate_type", "expected_revision"]`, and `BlobAttributeConflictError`
raises `blob_id`, `role` and `media_type` — all screened off. **The message goes too**:
`envelope.py:126` uses the *catalog's* summary, so the class's own distinguishing sentence
never reaches the wire.

**Exactly two errors in `src/` carry `conflict` with `aggregate_type: "Blob"`:**

| Class | What an operator must do |
|---|---|
| `BlobAttributeConflictError` | **stop** — the instance was restored wrong |
| `TemporaryBlobLostError` | **retry the upload** |

Their envelopes are **byte-identical apart from `correlation_id`** — same status, same code,
same message, same details, `retryable: false` on both. Opposite operator responses, one
indistinguishable answer. And `retryable: false` is right for one and arguably wrong for the
other.

**The question for the owner is narrower than "widen the detail keys":** *may a `conflict`
envelope carry a discriminator between these two, and is that a detail key or a second code?*
`R-3`'s `dependency_credential_refused` is the same shape and has been ruled once already,
which is the precedent either way.

### D-19 — a published run reports neither its timings nor its finding count — **CLOSED**

**Closed 2026-09-18 by `W17-VIEW`, and it was two defects, not one.**

**`W17VIEW-1` — four declared fields with no producer, in *two* readers.**
`runs/repository.py::_SELECT_STAGE_RESULTS` never selected `started_at`/`finished_at` — columns
**its own upsert has written since the first migration** — so `StageResultRow` had nowhere to carry
them and they were write-only. Only *then* does `bootstrap/adapters.py::_run_status_view` fail to
set `published_finding_count` and `diagnostic_observation_count`. My brief named the assembler
because that is where `W15-RUN` looked; **the assembler could not have set the timings if it had
tried.**

**`W17VIEW-2` (`W15RUN-5`) — `now()` is `transaction_timestamp()`.** `RunAdapter.start_run` creates
*and executes* a run inside one write, so `created_at`, every `updated_at` and `terminal_at` were
three copies of the instant the transaction opened. SQL rather than the assembler, and unrelated to
the first.

**No contract change:** all four fields were already declared by the frozen document. Verified over
a **real socket** — `uvicorn` on this lane's PostgreSQL and MinIO — not the in-process router.

**The finding is worth more than both repairs: the response baseline had pinned the second defect
as the expectation.** Records 03–07 carried **one token for `created_at` and `terminal_at`**,
because substitution in that corpus is by exact value and the two really were identical to the
microsecond. `W15RUN-5` was legible in `tests/characterization/w13_baseline/records/` for five
waves before a browser found it.

**A safety net that reproduces a defect byte for byte is protecting it.** A re-capture alone would
have erased that evidence with nobody having to say it had been there, so it is asserted instead:
`test_the_five_run_status_records_no_longer_pin_one_instant_for_the_whole_run`.

**One boundary flagged rather than quietly taken, and checked here.** The countability guard
asserted a *single* named exception, so a second permitted change was impossible to record without
editing it. It is now a **literal** case→debt map of six entries — not derived from the records it
checks — and additionally requires every marked record to carry a `permitted_change` and a
`decided_by`, which the one-case version did not. The count changed; the rule is strictly stronger.

Check: `grep -n "PERMITTED_EXCEPTIONS" -A 8 tests/characterization/w13_baseline/test_response_baseline.py`.

### D-20 — there is no observable `running` state — **CLOSED**

**Closed 2026-09-18 by `W20-EXEC`, and this row's diagnosis was wrong in a way that changed
the repair.**

It said the states were unreachable. They were unreachable **to a client**, not to the code:
`executor.py:589-590` has written `created → queued → running` since `B5`. What hid them was
that `RunAdapter.start_run` wrapped creation *and* execution in **one transaction**, so every
intermediate state was written and overwritten before anything committed. **This was a
transaction-boundary repair, not a write-the-missing-states repair** — and that is also what
decided the crash story.

Measured over a real socket:

```
after  : startRun 202 in 22 ms, state "queued", empty stages, no terminal_at
         poller: queued -> running (10 readings) -> published
before : 202 in 354 ms carrying "published"; poller's distinct readings ['published']
```

**The shape** is a bounded thread pool in the serving process, `RUN_CONCURRENCY = 1`, argued
from `PROTOTYPE_PROFILE.md` rather than from taste: §7 defers *remote and distributed*
workers, and §2 says run and stage state are persisted **before** execution — a clause that is
empty unless another reader can see the state in between. No `Job`, `Attempt`, lease,
heartbeat, fencing token or outbox. `execute_run` gained **one line**, a `checkpoint()` hook
defaulting to a no-op, so all 52 existing call sites keep their all-or-nothing unit of work.

**Two faults, deliberately different vocabulary.** A worker exception terminates the run
`failed` with `executor_raised_before_terminal` in a fresh transaction, because off the
request thread there is no caller left to raise at. A **process death** leaves `running` or
`queued` and is resolved by `OD-10`'s reconciler from the ASGI lifespan **before the socket
binds** — `executor_process_ended_before_terminal`, a declared terminal with the interruption
as a *column*, not an invented state.

**That reconciler has existed since `B5` and nothing in `src/` ever called it.** It could not
have found anything, because nothing ever committed an intermediate state.

**No shutdown hook**, and the argument is the right way round: it would be a second
implementation of the reconciler's rule covering strictly fewer cases, since `SIGKILL` reaches
no hook.

**`web/` needed nothing, and the frontend had been built for this all along.** `polling.ts`
loops until a terminal state and `web/tests/unit/run/polling.test.ts:108` **already scripts
`['queued','running','validating','published']`** against a fake transport. `PA-01` criterion
4's UI clause was tested against a sequence **the server could not produce**.

**The 300-second margin, and nothing was changed.** `startRun` no longer blocks, so 300 s has
stopped being the deadline for a run — a ten-minute document now finishes and the screen shows
it. What it now bounds is the slowest remaining request, a cap-sized upload, measured three
times at **0.85–0.87 s**. Nothing in the repository measures that end to end through nginx, so
trading a measured margin for a guess is the wrong direction.

**Left false and not this session's to edit:** `infra/deploy/proxy/nginx.conf:37`'s comment
(*"would cut `startRun` off mid-call"*) and `web/src/widgets/run-list/ui/run-list.tsx:10-13`
(*"a screen that waited for a `running` reading would wait forever"*). The widget's behaviour
is still right; only its reason moved.

Check: `curl` `startRun` on a running stack and read `state`; it is `queued`, not `published`.

### D-21 — cost is recorded and exposed nowhere — **CLOSED**

**Closed 2026-09-18 by `W18-SEAL` under `R-5`.** `RunStatus` gains `cost_micros`,
`cost_basis` and `model_call_count`. `grep -c cost` over the frozen contract goes **1 → 7**.

**On `RunStatus` and not in the CSV**, argued from the criterion rather than from taste.
`PA-01` criterion 4 names *"provider mode and cost"* together, and `provider_mode` is already
a required `RunStatus` property, so a user reading one and navigating elsewhere for the other
is a user who can fail the criterion by not navigating. Three reasons against the CSV, any one
sufficient: the seventeen columns are frozen by `OD-11` and named as seventeen by criterion 7,
which `R-5` does not authorise moving; one CSV row is one **evidence item**, so a run-level
cost repeated down the column is a number that looks per-row and is not, and summing it
multiplies the cost by the evidence count; and `exportRunCsv` refuses a run whose terminal
does not publish, so **a run that spent money and then failed would have its cost invisible
exactly where an operator most wants it.**

**`D-15` was neither inherited nor repaired.** `stage.py` and `executor.py` are untouched. The
figure is computed from the `model_call` rows — which `D-15` itself calls the exact ones — and
**`model_call_count` is published rather than inferred**, which is what answers the ambiguity
directly: without it a reader cannot tell a run that answered first time from one that was
retried. `cost_basis` aggregates conservatively (`measured` only when every contributing row
reported one) and the schema states that rule so a consumer reads it rather than guessing.

Two details that are not decoration: `model_call.cost_micros` is **nullable** and SQL `sum`
skips NULL silently, so the `FILTER` counts a NULL as unmeasured; and all three are **absent
rather than zero** when no provider call was made, because *"it cost nothing"* and *"nothing
was spent here"* are different claims — `D-3` is this programme's record of what inventing the
flattering one costs.

**Worth carrying forward:** a `recorded` run reports `cost_basis: "estimated"`, because a
replayed call reports no cost of its own. So the first live `PA-01` run is also the first that
can print `measured`, which is what makes the field worth reading rather than decorative.

### D-6 — the contract has no security scheme at all — **CLOSED**

**Closed 2026-09-18. `W13-SEAL` sealed `bearerAuth` at the document root at `e6eae1e`;
`W14-PKG` gave the deployment a token channel; `W15-AUTH` gave the browser a way to send
one.** Measured at `315de25`:

```
python3 -c "import json;o=json.load(open('contracts/api/v1/openapi.json'));\
print(o.get('security'), list(o['components']['securitySchemes']))"
-> [{'bearerAuth': []}] ['bearerAuth']
```

A top-level `security` means all twelve operations carry it rather than each declaring its
own. `authentication_required` is now raised — by `api/security.py`, driven live through the
deployed stack by `W14-PKG` §2 (no credential → 401, wrong credential → 401) and again by
`W15-AUTH` §6.

**What the row got right and what it missed.** It said correctly that adding tokens is a
contract change rather than a lane decision, and it was resealed as one. It did not see that
the frontend had no way to *send* a credential — that was `W14-PKG` §7.2, and it cost wave 15.

Check: the one-liner above, and `grep -rn "AUTHENTICATION_REQUIRED" src/`.

### D-7 — one code, two situations — **CLOSED, and it recurred elsewhere**

**Closed 2026-09-17 by owner ruling `R-3`, sealed by `W13-SEAL` at `e6eae1e`.** The 21st
code, `dependency_credential_refused`: 500, `retryable: false`, category `dependency`,
`safe_detail_keys` exactly `["dependency"]`. `permission_denied` keeps the contract's meaning
— an authenticated subject's rights — and the blob store's refused-credential case, which has
no subject in it at all, moved to the new code.

Measured at `315de25`: 21 codes in the catalog; `storage/errors.py:167` carries it;
`tests/integration/storage/test_unavailable.py:116` guards it; and record 31 of the
characterization baseline states the permitted change and its reasoning in its own
`permitted_change` field rather than in a commit message.

**The recommendation this row made was taken, and the alternative it offered was refused for
the right reason.** It said that if no code were added the storage case must at least become
distinguishable on the declared keys — and that it could not, which was the argument that a
code was the answer. That argument held.

**It recurred.** The same shape — a code borrowed for a scenario its own summary does not
describe — is live in a second place, and there it is worse. See **D-12**.

Check: the `summary` of `permission_denied` against the docstring of
`StorageCredentialRefusedError`.

### D-8 — the catalog is not frozen, and the whole programme says it is

`contracts/domain/v1/error-codes.json` declares `"frozen": false`, `"status":
"draft_candidate"`, `"contract_version": "1.0.0-draft.1"`.

"The frozen 20-member catalog" appears in closures, in certifications, in dispatch briefs and
in this register — written by me more often than by anyone. The freeze is real **in practice**,
by `P02_LOCK.json` and by CP-00 never having been ratified, but **the document does not say
it**, and every brief that called it frozen inherited the phrase rather than opening the file.

Third instance of the same shape: D-1.6 (`checksum_mismatch` is not a code), D-1.9 (a pin set
read as overruling an ADR), and now this. **A name repeated often enough stops being checked.**

Found by `pdf-analysis-d9`. Consequence for the reseal: adding a code is a smaller act than
"unfreezing a frozen catalog" made it sound.

Check: the top-level keys of that file.

### D-9 — "paragraph granularity" for the normative corpus — **RE-MEASURED 2026-09-18, and this row was wrong in the favourable direction**

The owner has directed that the normative corpus be carried into PostgreSQL at **paragraph
granularity**, so vectors can be laid over it. This row previously said the text and the
geometry *"live in two places neither of which is joined to the other"* and that the content
*"sits behind `crop_url`, pointing at an **external service**, not at anything on disk."*

**That is false, and the correction matters because it changes the size of the task.**

Measured at `e43e7ea`:

| | |
|---|---|
| documents | **674**, 5.1 GB, under `.local/` — invisible to git |
| blocks | **~15 500** (median 23 per document, range 1–188); every one `block_type: "text"` in a 60-document sample |
| local crops | **1106 of 1106** blocks in a random 25-document sample have `crops/<block_id>.pdf` — **zero missing** |
| text layer | a crop yields **2 865 characters** through `pdfminer` — the crops are not rasters |

So **the join key exists and is local**: `blocks.json` carries the geometry
(`coords_norm`, `polygon_points`, `page_index`), `crops/<block_id>.pdf` carries the text, and
`block_id` joins them. **`crop_url` is a convenience, not the only path to the content.** No
remote dependency is required to build this.

**What remains true, and is the actual work.** A block is **not** a paragraph — 23 blocks for a
whole normative document, and one crop yielding 2 865 characters, is a region of several
paragraphs. Paragraph granularity therefore needs **segmentation inside a block**, and each
paragraph's box derived from the block's box plus its offset within the crop. That is a
design task, not a load — which is what this row got right.

**Two lessons, and the second is about this row.** `block_type: "text"` is a *type label* and
a substring search for `"text"` reads as though content were present; the original author made
that mistake and caught it. But the correction then over-shot: **a `crop_url` field was read as
evidence that the content is only remote, without listing the directory beside it.** That is
`OPERATING_CONSTRAINTS.md` §12 once more — a query sharing an assumption with its subject —
and it is the same shape as `D-4`, where I read a permissive constraint as proof of
reachability without checking the writer.

Check: `ls .local/norms/corpus/<any>/crops | wc -l` against the block count in that document's
`blocks.json`, and `pdfminer.high_level.extract_text` on any crop.

### D-10 — `make mutation-copy` cannot serve a tests-only stream — **CLOSED**

**Closed 2026-09-18 by the integrator.** `tests/` and `pyproject.toml` are now copied and
`.venv` is linked, so a stream whose deliverable is a test module mutates it in the copy:

```
cd /root/<name>-mut && ./.venv/bin/pytest <path>
```

`pyproject.toml` has to come too, because pytest's `pythonpath = ["src"]` and
`--import-mode=importlib` are root-owned and rootdir is that file's directory — without it
the copy would collect under a different import mode from the gate, so a red there would not
be a red in the tree. `.venv` is linked rather than copied because it is not a thing anyone
mutates, and because `tests/integration/db/conftest.py:217` requires
`REPOSITORY_ROOT/.venv/bin/python` — and once `tests/` is copied, that root *is* the copy.

**`tests/` is copied, never linked, and the probe checks it by identity rather than by
policy** — it resolves the path and refuses one that lands outside the copy. A symlinked
`tests/` would hand a stream exactly what `mutation_copy`'s own guard refuses in its own
words (*"no tracked file is ever edited to mutate"*), by a different route.

**Proved, not asserted.** Unmutated copy green first (`16 passed, 26 subtests`), then `21`
→ `99` in the copy's `test_error_kernel.py`: copy red, `git status --porcelain tests/` empty,
tracked tree still green. The probe's four refusals were each driven to red — no `tests/`, a
symlinked `tests/`, no `pyproject.toml`, no reachable `.venv` — and then green again on a
restored copy, which is the control.

**And it closed a caveat this Makefile has carried since wave 10.** The note said *"a
MIGRATION cannot be mutated by any copy"*. With `FULL=1` it now can: the copy's root is
where alembic runs, and `db/` is a real copy. Driven — unmutated FULL copy, `102 passed`;
then `BEFORE UPDATE OR DELETE` → `BEFORE DELETE` on the immutability trigger, **7 failed /
95 passed**, all seven being immutability guards across three test files.

Guarded by `tests/integration/composition/test_mutation_copy_serves_a_tests_only_stream.py`,
because `make mutation-copy` is not part of `make gate` and deleting the recipe line and the
probe branch together would otherwise redden nothing. Four mutations of the Makefile, four
killed, control green.

Check: `make mutation-copy MUT=/root/x-mut` and read the probe's output.

### D-11 — `certifi` is MPL-2.0, and `OD-01` is narrower than the programme quotes it

`W13-PIN` added six pins; the resolution added three transitives, one of them **`certifi`
2026.7.22, MPL-2.0** — weak, file-level copyleft.

Two things bound it, and both are measured rather than reassuring:

- **`OD-01` is about the PDF text-extraction library specifically.** Its own words
  (`PROTOTYPE_EXECUTION_PLAN.md` line 574): *"a permissively licensed extractor giving
  per-character boxes… a copyleft library is blocked until the owner rules on its licence"*.
  `ALPHA_ROADMAP.md` §4 quotes it as "`OD-01` blocks copyleft", which **widens a decision past
  what it says** — the same scope inflation as D-1.9.
- **`certifi` reaches the tree only through `httpx` → `httpcore`, and `httpx` is in the test
  group.** The runtime closure stays entirely permissive.

So nothing is blocked today. It is registered because the *next* pin request will be argued
against whichever reading of `OD-01` is at hand, and the narrow one is the one the decision
supports.

Check: `python3 -c "import tomllib;print(tomllib.load(open('uv.lock','rb')))"` for the
provenance chain, and line 574 of `PROTOTYPE_EXECUTION_PLAN.md` for the wording.

### D-12 — a refused model-proxy credential is pinned retryable — **CLOSED**

**This is D-7's shape in a second place, and it is worse.** Measured at `315de25`:

```python
# src/auditmanager/analysis/text/proxy.py:222
    if exc.code == 401:
        return DomainError(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            message="the model proxy refused the token",
        )
```

The catalog pins `dependency_unavailable` **`retryable: true`**. So when the model proxy
rejects our credential, the envelope tells the caller to **retry a rejected credential** — an
operation that cannot succeed until an operator changes something.

D-7's collision made one 403 ambiguous between two readings. This one is not ambiguous; it is
**wrong in the single field a client automates against**. A retry loop built on `retryable`
will spin against a 401 forever.

`dependency_credential_refused` — `retryable: false`, `safe_detail_keys` exactly
`["dependency"]` — already exists and fits exactly. **No catalog change, no reseal, no owner
decision.** It is a mapping, not a contract.

Why it is likely rather than theoretical: `R-1`'s open items include whether the model proxy
is reachable from the alpha host at all, and `R-4` puts real client documents on that host. A
misconfigured proxy credential is a plausible first failure there, and this is what the
operator would be shown.

**Closed 2026-09-18 by `W16-ERR`.** The envelope went from `503 / retryable: true / no details`
to `500 / retryable: false / {"dependency": "model_provider"}`. Reverting the mapping reddens
two tests, one of which pins the **envelope** rather than the code name — because the lie was the
flag, not the name.

Check: `sed -n '222,226p' src/auditmanager/analysis/text/proxy.py`, against
`codes.dependency_unavailable.retryable` in `contracts/domain/v1/error-codes.json`.

### D-13 — a deployment fault answers as the caller's validation error — **CLOSED**

`StorageBucketMissingError` (`src/auditmanager/storage/errors.py:112`) inherits
`StorageConfigurationError`, whose `code = "validation_failed"` (line 107). A missing bucket
is the **deployment's** fault: the caller sent nothing wrong and can do nothing about it, and
`validation_failed` says the opposite in both its status and its summary.

Smaller than D-12 — it does not mislead an automated client about retrying — but it is on
criterion 10's surface and it is a one-line change if a code fits.

**Closed 2026-09-18 by `W16-ERR`** as `internal_error`, argued from the catalog's own
`internal_mapping` **rule 1** — the destination for *"adapter code with no declared mapping"* —
rather than from taste. Envelope `422 validation_failed + {field: S3_BUCKET…}` → `500
internal_error`, no details. `field` and `constraint` stay on the exception for logs;
`domain_error_from_storage` narrows them out of the envelope.

**The boundary held.** `dependency_unavailable` was rejected (retryable, and retrying never
creates a bucket); `dependency_credential_refused` was rejected because nothing refused a
credential — *borrowing it would repeat D-7 while citing it*. A 22nd **dependency-misconfigured**
code would say more, and `internal_mapping` rule 4 makes that the owner's. Recorded as a
candidate, **not proposed as a reseal**.

Check: `sed -n '99,125p' src/auditmanager/storage/errors.py` against the catalog summaries.

### D-14 — `PROTOTYPE_PROFILE.md` §9 carried a duplicated, truncated bullet — **CLOSED**

Line 261 was the first half of line 262, cut off mid-sentence at *"reported as"* — two
bullets, one incomplete, in the list that defines what the learning gate measures. Closed by
the integrator at this commit; the complete bullet is the one that survived.

Reported by a reviewing session rather than found by a reader of the document, which is the
part worth keeping: §9 is quoted into briefs and nobody quoting it had opened it.

### D-22 — one rule, three hand-copies, and the copies are what ship — **CLOSED**

**Closed 2026-09-18 by `W19-SHELL`, on its way past `D-16`.** Three byte-identical
`useIntentKey` copies deleted; the rule is now **one pure function over an opaque signature**
in `web/src/shared/lib/intent-key.ts`, with `mint` injected. `entities/expert-decision` keeps
`intentSignature` and delegates, and its nine tests are unchanged.

**The point of the row was never the duplication — it was that the duplicates could not be
tested.** `W16-WEB` measured U-06/07/08 as *"unreddenable by construction"*: one render pass
with a `useRef` always fresh means a mutation inside a copy changes nothing observable from
outside. With one definition, **they are reddenable for the first time**, which is the repair
the row asked for and which `W16-WEB` correctly declined to make (`D-1.5` was a testing row).

Check: `ls web/src/features/*/model/use-intent-key.ts` finds nothing;
`git grep -c "export function useIntentKey" -- web/src` returns one line.

### D-23 — the contract's prose is an unguarded hand-copy — **CLOSED**

**Closed 2026-09-19 by `W20-CODE`'s guard**, `tests/contract/api_v1/test_surface_counts_in_prose.py`,
ten tests. Every count is **read from the documents** — `(path, method)` pairs,
`len(components.schemas)`, `len(paths)`, `len(codes)` — and **no literal appears anywhere**,
because a literal would need editing at the next reseal, which is the failure mode itself.

Shown able to fail against the tree: `app.py`'s `_DESCRIPTION` — **the string served on
`/openapi.json`** — reddens at fifteen→twelve, and `declarations.py` at 46→43.

**It found the thirty-sixth on its first widening, and there were four.**
`infra/deploy/README.md` ×3 and **`infra/deploy/serve.py:4`, the process entry point's own
docstring**, all still said *"twelve operations"*. `W18-SEAL` had swept `src/` only. A fifth,
in `web/src/app/bff/v1/[...path]/route.ts:16`, is **left standing and named** — outside that
session's ownership, and now the only one left.

**One of its own parametrised proofs had to move when `R-11` reverted `R-8`.** The example
*"the twenty-one-code catalog"* stopped being a stale spelling the moment the catalog went
back to twenty-one — so it now uses the pre-`R-3` *"twenty-code"*. The test's own docstring
had anticipated exactly that: it says so rather than enforcing a claim that has become true.

Check: `.venv/bin/pytest tests/contract/api_v1/test_surface_counts_in_prose.py` is 10 passed.

### D-24 — `reset.sh --dry-run` under-reports what the wipe would destroy

**`W21CERT-1`, and it is wrong in the direction that gets data destroyed.** The rehearsal's
row counts come from `pg_stat_user_tables.n_live_tup` — an **asynchronous estimate** — printed
in a column headed *"rows"*.

Measured: on a freshly written database the first rehearsal printed **`(0 rows)` for every
table** while a project, a document, a version and a manifest entry all existed. Later it
printed `(2 rows)` where the truth was **4**. The bucket half of the same screen is exact,
which makes the database half read as though it were too.

**`R-4` is what makes this load-bearing.** The wipe is the commitment that real client
documents leave the alpha host, and `--dry-run` is the screen an operator reads **before**
agreeing to destroy them. An operator shown `(0 rows)` may reasonably conclude there is
nothing to lose.

Tree: `infra/deploy/**`.

Check: write four projects, then `reset.sh … --dry-run | grep '^project '` — it is red while
that figure is below `select count(*) from project`.

### D-25 — a quotation's caption says "page 2, chars 707–746" and those offsets are not page-local

**`W21CERT-2`.** `web/src/entities/finding-observation/model/quotation.ts:53` renders the
character range beside the page number, but the range is **document-global** — the frozen
`Evidence` schema says so, and `pages.ts:10` already knows it. Page 2's own text is 539
characters; the quotation sits at page-local 198–237.

**The data is right and the caption is wrong**, which is the more dangerous half: an expert
checking the citation by hand looks at the wrong place on the right page and concludes the
tool is lying about something it has correct.

Tree: `web/src`.

### D-26 — two sentences that stopped being true and are still in the tree

Both were reported by the session that made them false, and neither was that session's to
edit.

- **`infra/deploy/proxy/nginx.conf:37`** — *"A model run is slow. The default 60 s read
  timeout would cut `startRun` off mid-call."* False since `W20-EXEC`: `startRun` no longer
  blocks. The 300 s value is still right and now bounds a cap-sized **upload**, measured at
  0.85–0.87 s. **The number is correct and its stated reason is not.**
- **`web/src/app/bff/v1/[...path]/route.ts:16`** — still says *"twelve paths"*; the contract
  has declared **fifteen operations across twelve paths** since `R-5`. This is the **fifth**
  stale count, the one `636b850` named and left standing because it is outside `src/`.

**The cheap repair for the second is to widen `D-23`'s guard to `web/src/app/bff/`**, which
already reads its counts from the document and would then catch the sixth.

### D-27 — nothing notices when the deployed stack drifts from the tree

**Found by my own false premise, which is the honest provenance.** I told `W21-CERT` that the
stack on 31500 was *"rebuilt from current code"*. It was not: the image was created at
**13:25 UTC** and `W20-EXEC` merged at **14:47 UTC**, so `carrier.py` is not in it —
verified by listing the directory inside the running container.

A session that had trusted me would have driven a stack **without the repair it was
certifying**, reported criterion 4 exactly as `W15-RUN` did in the morning, and blamed
`W20-EXEC`.

**This is the third wave running in which "deployed ≠ repository" has had to be re-measured
by hand.** There is no mechanism that says so. The stack serves `/openapi.json` and the tree
has a contract; a probe comparing the served document's digest — or simply the commit the
image was built from — to `HEAD` would answer it in one command.

**Until such a probe exists, every claim about the deployed stack must name the image's build
time**, and a rebuild is a step in closing a wave rather than an afterthought.

Check: `docker exec <api> ls /app/src/auditmanager/runs/` against `git log -1` for the file
in question.

### D-28 — an unrouted project path answers 200, so a status code cannot tell a screen from a soft error

**`W21-E2E`.** `/projects/<anything>` renders the project screen in an error state rather
than answering `404`, because the dynamic segment matches any string. Only an unrouted
**top-level** path 404s.

**The consequence is about instruments, not about users.** A journey, a monitor or a probe
that reads a status code cannot distinguish *"this screen exists and works"* from *"this
screen exists and is telling the user something went wrong"*. Every such check on this app
must read the rendered body, and `W21-E2E`'s journey does — which is why it found this.

Related and measured in the same pass: **no route here is ever network-idle** — at least one
request per screen never emits `loadingFinished`. Any harness waiting for idle waits forever.

Tree: `web/src/app`.

### D-29 — `npm run test:unit` exits 1 while the tests it names all pass

**`W21-E2E`, and it is live rot rather than a stale name.** `web/tests/unit/` holds 38 test
files. They **do** run under `npm test`, so `make gate` covers them and nothing is unguarded
— but the named command lies, and a person who runs it concludes the suite is broken.

Beside it, two reservations that are now stale: `web/FRONTEND_LOCK.json` still lists
`e2e:pc01` as reserved for `P3-QA-01`, and `reserved-forwarder.mjs` still carries a dead
`e2e:pc01` entry. `W21-E2E` took that name and could not edit the lock.

Tree: `web/`.

### D-30 — the committed journey covered the read half only — **CLOSED**

**Closed 2026-09-19 by `W22-E2E`.** The headline is one request:

```
POST /bff/v1/runs -> 202 Accepted
{"run_id": "run_01M2WW7N94M2GQG96E9PFVMB2G", "state": "queued", "provider_mode": "recorded"}
x-correlation-id: cid-686376aa...
```

**That request is `D-5`.** On 2026-09-16 the same operation answered 500 twice through a
browser; the harness logged status lines only, and the attribution is permanently
unanswerable. It is now driven by a real click and kept whole on disk.

Create `201`, upload `201` multipart with `byte_size` **58978** — `ar_baseline.pdf` exactly,
read by the browser through `DOM.setFileInputFiles` — then the `202`. The read walk then
walked **the very project the write half had just made**, because the list is newest-first:
one story end to end, 7/7 routes, 206 exchanges, 5.3 MB of envelope, exit 0.

**The bound is the app's own state, not a sleep.** The journey reads `data-run-outcome`,
which the run screen's own polling loop writes, and the bound lives in the manifest because
`polling.ts` deliberately has no deadline. At the bound it produces **a finding with every
reading attached and exit 1 — never a skip.** A committed fixture with the bound set to
**1 ms** proves it.

**The guard was widened from 11 tests to 30**, still stack-free, and now checks declared
statuses against the contract — so a `202` reddens if execution ever moves back inside the
request. Plus a re-runnable proof that mutates the real manifest ten ways for ten reds.

**What it still cannot see, stated rather than left silent: the guard cannot see a 500.**
`D-5` itself is invisible at gate time by construction, because the gate runs without a
stack. That check lives only in the journey, where any `/bff/v1` call returning ≥ 400 during
a step is a finding carrying its correlation id and body.

**And one of its own controls was wrong when written** — it reddened on an unfillable
placeholder instead of on the missing-call check. Found by **running** it, which is the same
trap `W21-E2E` hit the day before and the reason every control gets run rather than read.

Check: `npm run e2e:pc01 -- --phase all` against a writable stack; and
`.venv/bin/pytest tests/e2e/` is 30 passed with no stack at all.

## 1.9 — the authority order, ruled 2026-09-17

**The ADRs and the architecture corpus are the primary source of truth. A roadmap is a draft
and a recommendation.** Ruled by the owner; recorded here because a register that cites the
wrong authority produces confident wrong rows.

The concrete instance that prompted it: `src/auditmanager/api/README.md` opened *"There is no
HTTP framework, and that is deliberate"* and justified it from `docs/program/P02_LOCK.json` —
a lane-level dependency pin. Against that stand **`ADR-0002`** ("one deployable Python/FastAPI
backend"), `TECHNOLOGY_BASELINE.md` ("Backend — Python, FastAPI/ASGI"), `ARCHITECTURE_BIBLE.md`
P-05 and `PROTOTYPE_PROFILE.md` §2 ("FastAPI remains the backend/control-plane direction"). The
same file admits its earlier version said *"FastAPI transport adapters only"*.

**A pin set records what a lane may install. It cannot overrule an ADR**, and the absence that
followed from it was described as a decision. Corrected in that file at this commit.

This is the programme's most-repeated failure in its sharpest form yet — a claim written at one
scope and read as authority at another. `W12_CLOSURE.md` §4 records me doing it with a private
helper's docstring; this one shaped what got built.

## 2. Owner-blocked, and not mine

| # | Item | Blocks |
|---|---|---|
| `OD-18` | three to five named experts with committed slots | `P4-BHV-01`, and it alone |
| `OD-17` | the shape of the next corpus; PC-02's precision evidence is saturated | the P05 corpus decision |
| — | the 21st error code, for "usable output over a strict subset of the input" | nothing today — `W11-RD` deliberately avoided needing it |
| — | whether `origin/main` advances | nothing; see §3 |

## 2.5 — the stale-premise count has no register, and two documents disagree

The wave-12 dispatch says **ten** stale premises are on record; the launch brief said
**twelve**. `W12-CERT` checked and found **no document enumerates them**, so it recorded the
disagreement rather than picking a number — which was right.

I have been counting in prose across closures, which is how a figure drifts. Either the count
gets a register with one row per instance and where it was found, or briefs stop quoting a
number and say "several, most of them mine". **Until one of those happens, no brief should
quote a count.**

## 3. `origin/main` is eight waves behind, and that is a decision not a backlog

**Re-measured 2026-09-18.** `main` is at `8f418e9`, carrying the `beaa7f7` certification. `dev` is at `315de25` — the previous figure in this line, `5c84f43`, was three waves stale, in the register whose own header says a row nobody re-measures will rot.

The integrator has recommended advancing it after each of waves 7, 8, 9 and 10, when `src/`
was byte-identical to a certified commit and the only question was whether `main` should
carry the evidence as well as the behaviour. That window closed when wave 11 changed `src/`, and **it has now reopened**:
`W12-CERT` certified `e6eae1e` on 2026-09-17, so the condition this section named — "a
certification exists for a commit on this line" — **is met**.

`main` can advance to `e6eae1e` or later, carrying certified behaviour for the first time in
six waves. **What has landed since that recommendation makes the gap matter more, not less:**
the FastAPI transport (wave 13), the deployable stack (wave 14) and the credential path
(wave 15). A reader who trusts `main` today is reading a prototype with no HTTP server in
it. `315de25` is gated green — `1726 passed / 5 skipped / 168 subtests`, foundation 35,
frontend 498 — but a green gate is not a certification, and this line does not pretend it
is one. It is the owner's decision and the integrator does not take it. The one thing a
decision-maker should weigh: the certification holds **with a named exception**, D-1.5, and
that exception is about what a user sees rather than about what the system does.

## 4. Closed, with where to find the evidence

Kept because `W4_CLOSURE.md` §3 found that silently emptying a register teaches nothing about
how long it was wrong.

| Item | Closed by |
|---|---|
| the read path did not verify what the manifest promised | wave 11, `W11-RD` |
| two comments claiming `details` values are unscreened | wave 11, `W11-FIX` |
| a docstring undercounting the error screen | wave 11, `W11-FIX` — and made executable |
| `cost_basis` absent from the success path | wave 11, `W11-FIX` |
| a filename property with no consumer | wave 11, `W11-FIX` |
| the quarantine excluding 212 live contract tests | wave 11, integrator; `OPERATING_CONSTRAINTS.md` §11 |
| the mutation-copy recipe that manufactured reds | wave 10, integrator; `make mutation-copy` |
| the gate carried as convention in three of its four parts | wave 7, integrator; `make gate` |
