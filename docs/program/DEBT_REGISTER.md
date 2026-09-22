# Debt register

Written 2026-09-17 by the integrator. **Re-measured against the tree at `315de25`–`80db00f` on
2026-09-18.**

**Measured against the tree, not compiled from closure records** — `W4_CLOSURE.md` §3 records a
register that had been entirely obsolete while still reading as the list of what was open, and this
file exists to not become that. It very nearly did anyway; see the two rules below.

**What is open right now**, so a reader does not scan twenty-five rows to find out:

| | Row | Needs |
|---|---|---|
| **D-56** | project sections: navigation is free, per-section verdicts are a reseal | **owner** — and brief the two halves apart |
| D-53 | **11** English strings left, now **guarded** — a ratchet that may only shrink | the eleven; the guard is done |
| D-57 | one query key, two shapes: a finished run is polled forever | a decision, then a guard |
| D-58 | a screen names `uploadDocument` and `document_uid` to a reviewer | one sentence |
| D-52 | the legacy icon set is at least partly Feather, MIT, notice absent | a `NOTICE` file if we copy; **not** `D-11`'s shape |
| **D-46** | a failed run cannot say *which* dependency | owner — a reseal either way |
| D-50 | a character offset no second extractor can resolve | registered |
| D-51 | criterion 8 is a container restart, for a structural reason | registered; nothing to fix |
| D-1.6, D-8 | names the programme repeats without opening the file | prose |
| **D-9** | corpus: the join is local after all; segmentation is the real work | **ruled `R-9`**: after the screens |
| D-11 | a licence reading | registered |

**Closed 2026-09-21** — D-42 (the prose half; the measurement always stood) and D-47.

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

### D-15 — one `cost_basis` over a figure summed across attempts — **CLOSED, and this row's mechanism was impossible**

**Closed 2026-09-21 by `W25-COST` under `R-14`.** `metrics["cost_basis"]` is now derived from
the meter — `measured` only when **every** contribution was priced — which is the rule
`W18-SEAL` already applied to `RunStatus.cost_basis`. **Two places now say the same thing**,
which is the reason the ruling gave.

**The mechanism this row described cannot happen, and the row is mine.** I wrote *"a run whose
first attempt replayed and whose second reported a cost"*. `RETRYABLE_STAGE_ERRORS` is exactly
`dependency_unavailable`, and **every site that raises it raises it inside
`adapter.complete()`** — verified here: `complete` at `stage.py:226`, `charge` at `:244`. So a
retried attempt **charged nothing**, and a charged attempt is **never retried**, because
everything reachable after the charge is `retryable: false`.

**The disproof was already in the suite.** `test_retry_provenance_seam.py` asserts
`control_meter.call_count == 1` after a **three-attempt** run. I wrote the row without reading
it.

**The defect is real by a different mechanism:** `metrics["cost_usd"]` is the **meter's whole
spend** — a per-run object handed to every attempt so `OD-03` binds across them — while the
basis described *this call alone*.

**And the consequence, which the session raised rather than letting the close overclaim:
nothing in the deployment can currently emit a wrong `metrics["cost_basis"]`**, because there
is one charged call per run. This is a **structural guarantee about an accumulating figure**,
not a production-visible repair.

Proved without sleeping and without a clock — a retry could not have produced the case anyway:
one meter handed to two stage calls, a replay then a priced call, **both orders** asserted,
with a two-priced-call control that reddens a hard-wired answer. Through `execute_run` against
real PostgreSQL and MinIO, a meter opened at `0.90` gives `1.40 / estimated` where it read
`measured` before.

**One divergence deliberately left:** on the overrun path the `model_call` row stores
`estimated` because its figure is the pin's computation, while metrics may read `measured`.
Both are true of their own number.

**The same wrong story is quoted verbatim in five characterization records' `permitted_change`
prose.** Left as-is: that is the record of a past decision, not a live claim.

Check: `grep -n "cost_basis" src/auditmanager/analysis/text/cost.py`.

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

### D-18 — two opposite faults share one byte-identical envelope — **CLOSED**

**Closed 2026-09-21 by `W25-SEAL` under owner ruling `R-13`**, after `R-8` built it, `R-11`
reverted it, and the owner accepted the cost that revert had declined.

`staged_upload_lost` — **503, `retryable: true`**, category `dependency`, `safe_detail_keys`
exactly `["dependency"]`. It went to `TemporaryBlobLostError`, which follows from the ruling
rather than taste: `conflict`'s `retryable: false` is **right** for
`BlobAttributeConflictError` (published bytes are immutable) and **wrong** for a staged upload
the store lost. Catalog 21 → 22, `candidate_revision` 6 → 7 across all six domain files
(`W0-DOM-02`), `conflict` byte-identical to round 6, surface unmoved at 12 / 15 / 46.

**The measurement that outlives the row: `R-11`'s cost was a permission boundary, not an
amount of work.** End to end — cherry-pick, the four mechanical steps, two gates — this took
**twenty minutes**, about eleven of them waiting on gates. What had stopped it twice was a
brief that said *"No `web/`"* and a permission classifier that refused
`web/FRONTEND_LOCK.json`. **Neither of those is time**, and framing the revert as a cost
conflated the two.

**The frontend went red first and was watched doing it** —
`test_the_committed_client_was_generated_from_this_contract` on the old digest against the
new, and `npm test` at 7 failed / 699 passed — rather than assumed green after a recipe.

**Zero of 36 characterization records affected, re-measured.** Sixteen carry a non-2xx
envelope and none carries `conflict`. The method note is worth keeping: **a record stores its
body as a JSON *string*, so a structural walk for `error_code` finds nothing at all** and
would have reported the right conclusion for a wrong reason.

Check: `python3 -c "import json;print(len(json.load(open('contracts/domain/v1/error-codes.json'))['codes']))"` is 22.

### D-40 — `PC01_ERROR_CODES` was narrower than the surface — **CLOSED, and it named one code where four were missing**

**Closed 2026-09-21 by `W27-WEB`.** The row said `staged_upload_lost` was missing. Four were:
`storage_integrity_error`, `analysis_input_invalid`, `staged_upload_lost` and
`dependency_credential_refused`.

**Two were not theoretical, and the pair is the finding.**
`entities/document-version/model/upload-failure.ts` has described `storage_integrity_error` as
its own separate state since `W12-WEB`, and `features/upload-document/ui/upload-document-form.tsx`
renders it — **while `failure-surface.test.ts` asserted `isPc01ErrorCode('storage_integrity_error')`
is `false`**, with a comment calling the code *"outside the PC-01 render subset"*. Verified on
`dev` at lines 93–94 before the repair.

**A test was pinning the list's falsehood in place.** That is `D-34`'s shape one layer over:
the assertion was aimed at **what the list said** rather than at **what the screens do**. So
the list never described the screens it claimed to, and a thirteenth entry would have left
that true.

**It is derived from the contract now, and the derivation is argued.** The contract pins a
**status per response, never a code per operation** — status-only derivation gives 21 of 22
codes, which is not a subset. The only place the document says *which* code a response carries
is the response component's description. Three parts, each proved load-bearing by a mutation
that empties it: the backticked codes, the component's own name, and the **status filter** —
which matters because descriptions carry **cross-references**, `PermissionDenied` naming
`dependency_credential_refused` to say it is *not* that response.

Sixteen entries: fifteen derived plus `analysis_failed`, which the contract states in words
rather than backticks, registered in `BLIND_SPOTS` **with that reason** and guarded both ways.
No count literal survives in the three test files that carried one.

**No behaviour a user sees changed**, and the session said so rather than dressing a
structural repair as a product one.

**`W27-REFUSE` reached two of the same four independently**, from the screens rather than from
the contract.

Check: from `web/`, `npx vitest run tests/contract/pc01-error-codes.contract.test.ts` → 9 passed.

### D-41 — two comments in `errors.ts`, one falsified by its own wave — **CLOSED**

**Closed 2026-09-21 by `W27-WEB`, and there were five stale claims, not two.** The two in
`errors.ts`, plus `authorization.ts` (*"twelve operations"*), plus two the guard **cannot
read**.

**The guard's tree grew to `web/src`, and like `W22-WEB`'s widening it needed three changes
rather than one** — both extras found by **running** it: hyphenated identifiers, where `PC-01`
was read as *"01 operations"*, and the phrase *"code units"*. Both repaired **structurally**
rather than by adding phrases to an ignore list, which would have suppressed exactly the
numbers the guard exists to see.

**One class it still cannot read, repaired by hand and named:** `server-env.ts` said *"one
clear refusal into twelve confusing ones"* — a count of operations wearing the noun *"ones"*.
Teaching the guard that noun would redden ordinary prose, so the durable repair was removing
the number.

**`web/tests` is deliberately not scanned**: four files hold stale spellings **on purpose**, as
mutation fixtures — the same reason the guard excludes its own file.

Check: `.venv/bin/pytest tests/contract/api_v1/test_surface_counts_in_prose.py` → 21 passed.

### D-44 — the pre-check keeps three refusal screens truthful — **CLOSED, now enforced**

**Closed 2026-09-21 by `W28-GUARD`.** `tests/e2e/test_upload_limit_headroom.py` reads **both
numbers from where they live** — the pre-check's limit in `web/src`, `client_max_body_size`
from `infra/deploy/proxy/nginx.conf` — and reddens when the first is not strictly below the
second. Neither is restated as a literal.

**It reddens on this row's own sentence**: *raise the pre-check to 32 MiB with nginx
untouched* → 3 failed. Seven more shapes too: 64 MiB, nginx lowered to 16m, the two made
exactly equal, the directive commented out, the limit hidden behind a name, a stale label,
and a fixture shrunk under the limit. **Eight mutations, eight reds**, and the harness builds
a throwaway tree so the repository is byte-identical afterwards.

**Running the controls found a hole in the guard itself.** The first draft anchored
`client_max_body_size` to the start of a line, so `server { client_max_body_size 4m; }` — which
nginx accepts and which would decide the effective cap — was **invisible**, and the control
meant to prove the guard refuses two caps **went green**. Repaired by stripping comments line
by line and searching unanchored; both shapes are controls now.

**Reading the regex would not have found it.** Running it did.

Check: `.venv/bin/pytest tests/e2e/test_upload_limit_headroom.py` → 11 passed, and
`.venv/bin/python tests/e2e/prove_the_headroom_guard_can_fail.py` → 8 reds, exit 0.

### D-45 — `expects_rendered` was read by one driver and by no guard

**Found by `W28-GUARD` while doing something else, and repaired in the same wave.** Verified
independently on `dev`: `expects_rendered` appeared in `manifest.json`, in two reddening
fixtures and in `write.mjs` — **and nowhere else**. The conformance guard, which runs inside
the battery and exists to stop the journey rotting, **never looked at it**.

So the word `"Created"` could be changed in a screen and **the gate stayed green while the
write half went quietly red.**

**The sharp part: this is exactly the defect `W27-REFUSE` reported for its six refusal cases
— and it was already present in the half that session held up as the model.** *"The six live
in a driver the gate does not run"* was true of the write half too, and nobody had looked.

Closed for both halves at once; the guard went 30 → 47 tests.

**The general form, which is `D-23`'s at a different level:** a declaration that only its own
consumer reads is not a specification, it is a duplicate. **Ask who else reads it.**

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

### D-24 — `reset.sh --dry-run` under-reports what the wipe would destroy — **CLOSED**

**Closed 2026-09-19 by `W22-OPS`, reproduced twice on a database it wrote itself.**

* One psql session straight after a committed INSERT: `count(*)` = **5**, `n_live_tup` = **4**
  — exactly `W21-CERT`'s *"(2 rows) where the truth was 4"*.
* With statistics not yet collected — **which is what a fresh database is** — **every table
  printed `(0 rows)`** beside a byte-exact bucket listing.

Now one statement over the seventeen tables. **Cost measured rather than asserted:**
0.16–0.19 s at pilot size against 0.16–0.17 s for the estimate, 0.32–0.47 s at ten million
rows. Linear, and at any size a pilot reaches it is **smaller than the round trip carrying
it**.

**A second face of the same untruth, found by stopping the container.** A rehearsal that
could not reach the database printed *"could not read the schema"*, then an exact bucket
listing, then a calm closing sentence, and **exited 0**. Now a **twelfth guard**,
`rehearsal-counted`, exit 3 — driven live before its test was written. Markers **11 → 12**
with the meta-count and the README.

Check: write rows, then `reset.sh … --dry-run`; and `grep -c 'guard:' infra/deploy/reset.sh`
is 12.

### D-31 — `reset.sh --restore` restored the rows and not the bytes — **CLOSED**

**Found and closed 2026-09-19 by `W22-OPS`, and only driving it found it.** This is the
`R-4` path.

**The relative path the script itself prints at the end of a wipe** — the one `README.md`
documents — restored the **database** and then died. The object half mounts with
`docker run -v "$RESTORE:/dump:ro"`, and a relative path there is a **volume name** to
docker, not a directory.

Measured aftermath: **1 project, 1 document, 1 blob in the database, 0 objects in the
bucket** — precisely the instance `restore-complete`'s own comment calls *worse than an empty
one, because it looks recovered*.

Fixed twice over: the path is made **absolute before anything is touched**, and **the bytes
now go back before the rows**, so a half-failed restore leaves the half that does not
mislead. Re-driven with the same relative path: exit 0, 3 objects and 30 rows back, all five
published attributes intact.

**Three waves have now each found this class in the same script** — `W18-OPS` (a guard whose
`grep` never fired), `W22-OPS` (a rehearsal that counted nothing, and this). Every one was
invisible to reading and visible to running.

### D-25 — a quotation's caption gave document-global offsets as page-local — **CLOSED**

**Closed 2026-09-19 by `W22-WEB`.** The caption now reads **"page 2, characters 712–746 of
the whole document, not of page 2"**.

**The global range is kept and labelled, because the other two options do not exist** —
established rather than assumed: `Evidence` carries no page-start offset, **no operation in
the contract returns a page's text**, and the page pane is PDF bytes. So a page-local figure
cannot be computed on the client at all. Dropping the range would strip the numbers that the
mismatch alert refers to.

**And my brief was wrong about the way out.** I wrote that `pages.ts` already knows how to
convert; its own lines 10–12 say the opposite — it knows the **convention**, not a
conversion. The whole step turned on that.

### D-26 — two sentences that stopped being true — **CLOSED**

`nginx.conf:37`'s reason corrected by `W22-OPS` with the number untouched; the `bff/route.ts`
counts corrected by `W22-WEB`.

**And the second half carried a trap I walked into.** I told the session that `route.ts:16`
says *"twelve paths"*. **Line 16 is the only correct count in that file** — twelve paths is
true, fifteen operations is the figure that moved — and the stale statements are on lines 14
and 20. **Repairing what I named would have broken a true statement.** The session checked
and repaired the real ones.

### D-27 — nothing notices when the deployed stack drifts from the tree — **CLOSED**

**Closed 2026-09-19 by `W22-OPS` — `infra/deploy/verify-deployed.sh`. Exit 0 it is this
tree, 6 it is not, 4 the question could not be answered, and 4 is a failure.**

**The design I proposed does not work, and that is measured rather than argued.** Comparing
the served `/openapi.json` to the frozen contract fails three ways: there is no digest to
compare (served and frozen differ in `paths`, `components`, `info` **and** `security` even
after annotations are stripped — which is why this tree has a conformance *engine*); a commit
label is the builder's claim and cannot answer for a stack already running; and decisively,
**the generated document is byte-identical with a line appended to `carrier.py`**. Such a
probe would have been **green on the exact defect that created this row.**

What it does instead: reads both Dockerfiles' own `COPY` lines — the idiom `Dockerfile.api`
already uses on the Makefile's `UV_VERSION` — and compares every git-tracked file under them
to the bytes **inside the running container**. Against the 18-September container it prints
`src/auditmanager/runs/carrier.py MISSING FROM THE IMAGE`: the file this row is about, by
name.

**It caught me on its first live run.** I had told `W22-OPS` the stack was rebuilt from
current code. The **api** image was; the **web** image carried `package.json` from before
`W21-E2E`, whose merge landed **eleven minutes after** the build. `D-27` recurring inside the
brief that asked for its closure. After a rebuild and `reload-proxy.sh` the probe exits 0 and
prints *"the deployed stack IS this tree (124056d)"* — the first time that claim has been
made by a command rather than from memory.

**The proxy half was driven rather than inherited, and that changed what was written.** A
replaced container usually gets its old address back and nothing looks wrong; forced onto a
new one, the proxy stayed on the old address and answered **502** while DNS already said
otherwise. `reload-proxy.sh` tests the config first, because a reload with a broken config is
*refused* and the old workers keep serving — so the naive command would have succeeded at
leaving the 502 in place. **It is intermittent, which is why it survived three waves.**

Check: `./infra/deploy/verify-deployed.sh`; and
`.venv/bin/pytest tests/integration/composition/test_deployed_stack_probe.py` is 17 cases.

### D-28 — an unrouted path answers 200 — **HALF CLOSED, half refused on purpose**

**Closed for malformed addresses** by `W22-WEB`: `/projects/nonexistent-abc`,
`…/runs/zzz` and `…/versions/bad` now answer **404 on the wire**, working screens unchanged
at 200. The mechanism was already proved in the tree — `app/page.tsx` calls `redirect()` from
a server component and yields a genuine 307, and `notFound()` is the same mechanism.

**Refused, deliberately and in writing: the well-formed-but-nonexistent half.** It needs a
server-side fetch on screens that fetch on the client — **and that client fetch is `D-16`'s
repair.** Moving it back would touch the credential seam, React Query, streaming and every
loading state. The refusal is **asserted in `routes.test.ts`**, so it cannot close silently.

**The network-idle half of this row was false as I stated it.** Nine of ten routes reach
`inFlight === 0`; the tenth's single open exchange is **Chrome's bundled PDF-viewer extension
page** — not the app and not this origin. Every application request finishes.

### D-29 — `npm run test:unit` exited 1 while its tests passed — **CLOSED**

**Closed 2026-09-19 by `W22-WEB`**: 38 files, 567 tests, exit 0. The stale `e2e:pc01` and
`test:unit` reservations are released from the forwarder and from `web/FRONTEND_LOCK.json`.

**Why the lock drifted is the part worth keeping: no test anywhere referenced
`reserved_scripts`.** The seal covered its digests and not its content, so that section could
say anything. A new guard binds `package.json` ↔ forwarder ↔ lock.

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

### D-32 — `D-23`'s guard read only `.py` and `.md` — **CLOSED**

**Closed 2026-09-19.** Four stale counts in `.conf`, `Dockerfile` and `.env.example` were
corrected by `W22-OPS`; `W22-WEB` widened the guard so the class is readable.

**Widening needed three changes rather than one**, and the second is the instructive one:
the file tree and suffixes; **a claim wrapped across a JSDoc line that the pattern could not
see** — widening alone would have reported the correct figure and stayed **silent on both
stale ones**; and one more surface noun. The guard also refuses *historical* counts, so a
first draft reddened and the sentence was **deleted rather than registered as an exception**.

### D-33 — the listing fixture's own anti-vacuity guard was non-deterministic — **CLOSED**

**Reported by `W22-WEB` on a branch whose diff could not reach it** — two errors, then six
consecutive passes — and closed by the integrator.

**The non-deterministic thing was an anti-vacuity guard.** The `catalogue` fixture asserts
that time order and identity order disagree, so an ordering assertion can tell
`ORDER BY published_at DESC` from `ORDER BY version_uid DESC`. It obtained that disagreement
**by luck rather than by construction**, and two orderings of three items coincide one time
in six — matching the observed two failures in eight.

Two independent sources, both removed: the stamps query **carried no `ORDER BY`** and its
result was zipped **positionally** against the version list, so the pairing was arbitrary;
and three ULIDs minted inside one millisecond sort by their **random halves**.

**Shown able to fail** — assigning identities so the two orders agree gives 21 errors.
**What could not be built is a reliable killer for the positional-zip half alone**: a
reversed pairing and an insertion-ordered one both pass, because any single permutation
differs from the sorted order five times in six. That half rests on the reasoning and the
observed rate, and no mutation proof is claimed for it.

### D-34 — a truncated analysis published as a complete one, on the live transport

**Found 2026-09-19 by `W23-PARTIAL` while investigating `PA-01` criterion 4's exception, and
repaired in the same wave. It is recorded because of what it says about how it hid.**

`proxy.py:205` mapped OpenAI's `finish_reason: "length"` to the string **`"truncated"`**. That
is a word from the **call-status** vocabulary (`succeeded | truncated | failed`) written into
the **stop-reason** field, whose vocabulary is `end_turn | max_tokens`. `adapter.py:83`
decides `truncated` by comparing `stop_reason` to `"max_tokens"`, so `ModelResponse.truncated`
**never saw it**. Verified independently by the integrator.

**The consequence on the live transport — the one `W21-CERT` certified criterion 4 on:**

* the model call recorded `succeeded`;
* `_pages_analysed` reported **every page**, because its clamp is gated on the same property;
* the run **published as a complete analysis**.

**A report cut short at the output ceiling was presented as a whole one.**

**How it survived, and this is the part that generalises.** The guard asserted
`stop_reason == "truncated"` — **the string** — and never `response.truncated`, **the
decision**. The probe was on the wrong observable, so the test **pinned the defect in place**
rather than catching it. Its justifying comment was false as well: `stop_reason` is never
persisted and `ModelCallRecord` has no such field.

This is `OPERATING_CONSTRAINTS.md` §12 in a fifth shape: not a query sharing an assumption
with its subject, not one read before it finished — **an assertion aimed one field to the left
of the thing that decides.**

Repaired: `length → max_tokens`, and an unrecognised `finish_reason` is **passed through
rather than guessed**, so the repair cannot manufacture a `partial`. Driven end to end through
`serve.py` in proxy mode against a stub of the proxy's own documented contract with nothing in
the application stubbed — `partial`, `degradation_set ["text_analysis"]`, one published
finding, `cost_basis measured`, terminal on the first poll 22 ms after `startRun`.

**`PA-01` criterion 4's exception falls with it**, subject to the ruling in `D-35`.

Check: `grep -n 'max_tokens' src/auditmanager/analysis/text/proxy.py` and
`.venv/bin/pytest tests/integration/analysis_text/test_proxy_truncation_reaches_partial.py`.

### D-35 — does criterion 4 need `partial` from inside the journey? — **CLOSED**

**Ruled `R-12` on 2026-09-21: the deployed path is enough.** `W24-CERT2` drove `partial` **in
a browser** — badge `queued → running → partial` at 2334 ms, `degradation_set
["text_analysis"]`, `model_call.status = truncated` with 16 000 output tokens and no error
code — against a stub of the proxy's own documented contract on the stack's own network, with
**nothing in the application stubbed**.

The criterion asks that the UI **distinguish** `running`, `published`, `partial` and `failed`,
and it does. **The alternative was deliberately not taken**: a second canonical recording
keyed by a second acceptance document would have cost a new PDF, a corpus-builder change,
`SHA256SUMS`, `expected_issues.json` and the contract tests that enumerate them — for a lever
no criterion asks for.

### D-36 — `deploy.sh` run twice recreated three services — **CLOSED, and this row named the wrong cause**

**Closed 2026-09-20 by `W24-IDEM`.** Three runs on an unchanged tree: 23 `CACHED` steps each,
**all seven container IDs identical across all three snapshots**, both image IDs identical,
both volumes keeping their creation time, `Recreated` for nothing. The entire residue is two
lines of `diff` — the `StartedAt` of `migrate` and `s3-init`, which are **started again in
place**, keeping their IDs.

**This row said the cause was BuildKit stamping a fresh `created` into the config, and that
`SOURCE_DATE_EPOCH` did not fix it. The two image IDs were real; the explanation was not.**
Two consecutive fully cached builds give images whose `.Created` is identical **to the
nanosecond**, whose `.RootFS.Layers` are identical and whose **entire `.Config`** is identical
— and whose IDs differ anyway. **The ID is the digest of the *manifest*, and BuildKit attaches
a provenance attestation carrying the build time.** `SOURCE_DATE_EPOCH` addresses timestamps
*inside* the image, so it was never the lever — which is precisely why `W23-DEPLOY` tried it
and saw nothing move.

**A second cause exists and the mechanism handles it separately:** `api` and `migrate` share
one image and compose writes `com.docker.compose.service` into it — measured coming out
`migrate` on one build and `api` on the next — so the script compares content and moves the
tag back.

**Two host facts it rests on, both found by failing on them first:** this docker deletes the
image a tag moved off **at once, even while containers run on it** (so the previous image is
pinned with a second tag before the build), and **while the old container runs it refuses to
untag the image that container uses** (so the pin comes off after `up`, not before).

**The risk it introduces was driven, not assumed.** A byte was changed in `serve.py`, the
wrong retag forced by hand, and the stack brought up on it: `verify-deployed.sh` **exits 6**
and names `/app/serve.py DIFFERENT BYTES` with both digests. So `D-27`'s probe catches exactly
the failure this mechanism could cause. Control: a normal run printed `CONTENT CHANGED`,
recreated only `api` and `migrate`, left `web` alone, and the probe returned to 0.

**Limits, stated by the session rather than found later:** it only helps when the build was
cached — a cold rebuild is not byte-reproducible (`apt-get` writes timestamps) so the content
genuinely differs and replacement is correct; `com.docker.compose.*` labels are excluded from
the comparison by judgment; the provenance attestation is gone from both images and nothing
here reads one; and it was driven on **one host with one docker**, with both daemon behaviours
above local to it — the mechanism is written to be a no-op where they do not hold.

Opt-out: `ALPHA_PRESERVE_IMAGE_IDENTITY=no`, with any other value refused before anything is
built. Guards **12 → 13**.

Check: run `infra/deploy/deploy.sh` twice and compare `docker inspect --format '{{.Id}}'`
across the two runs.

### D-37 — a `-v` source is resolved by the daemon, and docker invents a directory rather than refusing

**Found by `W23-DEPLOY` in its own script, and it is `D-31`'s finding in a second costume.**

Guard 12 died on `IsADirectoryError: Is a directory: '/served.json'`. The source came from
`mktemp`, and **this host's docker is the snap build, whose mount namespace puts a private tmp
over `/tmp`** — so a `-v` source there does not resolve for the daemon. **Docker's answer is
not to refuse: it creates an empty directory and starts the container anyway.**

`D-31` was the same class — a *relative* `-v` source is a **volume name** to docker, so
`reset.sh --restore` put the rows back without the bytes.

**The rule both instances teach: a `-v` source is resolved by the daemon, not by the shell,
and docker prefers to invent a mount point over failing.** Moving the temp file elsewhere
would have fixed one path and left the class open, so the mount was removed entirely and the
document is piped on stdin.

**Carry this to the `R-1` host.** Its docker is probably not a snap build, but the class
survives the packaging: any `-v` whose source the daemon cannot see becomes an empty directory
and a green-looking container.

### D-38 — a failed `compose up` sent the operator to a file that is fine — **CLOSED**

**Closed 2026-09-21 by `W26-OPS`, and this row's own check command gave a false negative.**

The `Check` line said *"stop one service of a running instance, re-run `deploy.sh`"*. That
**exits 0 on the unrepaired defect**, because `up` simply starts the stopped container again.
The defect needs a service that **cannot come back**.

**That is a failure mode this register had not met.** Its header warns about *a row nobody can
re-measure*. This was **a row whose own command answers green on the live defect** — a session
following it would have concluded the row was already closed.

Reproduced as `W24-CERT2` measured it — `api` removed and `s3-init` failing on an invalid
bucket name, so `up` aborts before recreating it: **exit 5** and *"Fix proxy/nginx.conf"*, a
file that is correct. After: **exit 3**, *"`compose up` failed, and the 's3-init' service is
exited/1"*, nginx unmentioned, proxy untouched. It still refuses; only the diagnosis moved.

**A second face, worse than the first: with the five long-running services healthy and only a
one-shot failing, the old script exited 0 and called it a deployment.**

**Guard count stayed at 13, forced rather than chosen** — `infra/deploy/README.md` says
*"Thirteen guards"* and belonged to another session that wave, so a fourteenth marker would
have made a forbidden file wrong. Widened `services-healthy` instead.

Check: remove the `api` container of a running instance **and** make `s3-init` fail, then
re-run `deploy.sh`. It must exit **3** naming `s3-init`, never **5** naming `nginx.conf`.

### D-39 — the wipe rehearsal's total counted a view — **CLOSED**

**Closed 2026-09-21 by `W26-OPS`.** The total sums `BASE TABLE` rows only, and the view keeps
its own exact line because `DROP SCHEMA … CASCADE` destroys it too.

**Named limit:** a **materialized** view appears in neither `information_schema.tables` nor
this check, so it would **under-report** — the dangerous direction. None exists in this schema
and a case reddens if one appears.

### D-42 — the provider credential does appear in `docker compose config` — **CLOSED**

**Closed 2026-09-21 by the integrator**, in the commit carrying its last repair. The
measurement below always stood; what was open was the **prose**, and specifically whether the
false sentence survived anywhere a reader would still meet it unqualified.

Swept across every site that can produce it — `*.md`, `*.yml`, `*.example`, `*.sh`, `*.py` —
and **four** carry the sentence. Three of them (`W14_CLOSURE.md`, `W26-HOST.md`, and this row)
quote it in order to correct it. **One carried it live**: `docs/program/reviews/W14-PKG.md`,
the wave-14 review that first made the claim.

**A review record is history and is not rewritten.** It now carries an `## Erratum` block at
its head and an `[ERRATUM E-1]` marker on the sentence itself, so a reader who arrives at the
line — or who already quoted it — finds the correction at the same address rather than in a
register they may never open. That mechanism is the one `D-1.6` says the integrator owes
PC-01's accepted artifacts; this is its first use, on a document loose enough to try it on.

Check: `grep -rn "never appears in .docker compose config" docs/ | grep -v ERRATUM` returns
only lines that go on to correct themselves.


**Found by `W26-HOST`, verified independently by the integrator, and it corrects a claim this
repository has carried since wave 14.**

`compose.server.yml`, `W14_CLOSURE.md` and every brief I wrote said the provider credential is
kept out of `--env-file` *"and therefore never appears in `docker compose config`"*. **It
appears.** Measured with a sentinel on **Compose v5.3.1**: `config` resolves `env_file:` into
`environment:` and prints the value in clear. Independent check:

```
docker compose --env-file …/alpha.env -f …/compose.server.yml config | grep -c PROXY_LLM_TOKEN
-> 1
```

**What keeping it out of `--env-file` actually buys is real but different:** those names never
enter compose **substitution**. The security claim built on top of it was false.

**`config` output must be treated as a secret** — it also prints the API token and both
database and object-store passwords. `provider.env.example` and the runbook now say so.

**By contrast the TLS private key genuinely cannot appear there**, because a bind mount is a
path: sentinel test, **zero** hits for the key material and one for the path.

Check: the command above returns 0 only if a future compose stops resolving `env_file`.

### D-43 — *"about 8 GB"* was a provisioning figure read as the cost of one deploy

**Measured by `W26-HOST` on an isolated builder**, because the shared cache held another
lane's layers of the same Dockerfiles — a default-builder measurement would have measured
nothing, and pruning to fix that would have sabotaged a live lane.

| | |
|---|---|
| cold build cache, both images | **2.592 GB** |
| one clean-clone cold-cache deploy | **≈ 5.5 GB**, of which the cache is reclaimed by `docker builder prune -af` |

The repeated **8 GB** came from a **third consecutive** deploy with accumulated cache
generations. It is **right as a provisioning number and wrong as an account of one deploy**,
and the runbook now gives it with that reason.

**Also recorded because it cost a session its confidence in a number:** `df` *during* a build
on this host is worthless — another lane moved free space by gigabytes in both directions.

### D-46 — a failed run cannot say *which* dependency, and the envelope is why

**Registered by `W29-SAY` with its price, rather than worked around.** The screen now
explains what `dependency_unavailable` **means** — and it still cannot say **which**
dependency, because the information is not in the envelope.

Neither `RunStatus` nor `StageState` carries a `details` object. The catalog's
`safe_detail_keys: ["dependency"]` lives on the **error envelope**, and **a 200 run reading is
not an error envelope**. So the true sentence in `recorded` mode — *your document is fine, the
provider is fine, this deployment has no recording for it* — is not in the data, and
inventing it is the one thing that task forbade.

**Two ways to close it, cheapest first, both `contracts/**` and therefore the owner's:**

1. `RunStatus` gains an optional `terminal_detail`, restricted to the reported code's own
   `safe_detail_keys` — an `openapi.json` reseal plus a column.
2. A distinct catalog code for a replay miss, on the **`staged_upload_lost` precedent**
   (`R-8`/`R-13`): two situations demanding opposite operator responses answering one code.

**And a catalog addition is also a frontend reseal** — `D-18` measured that, and `R-13`
accepted the cost once. Whichever is chosen, it is a two-document change from the start.

Check: `grep -n terminal_reason contracts/api/v1/openapi.json` — it is `oneOf [ErrorCode, null]`
with no sibling detail object.

### D-47 — two live sessions wrote logs to the same scratchpad path in the same minute — **CLOSED**

**Closed 2026-09-21 by the integrator.** The rule is now `OPERATING_CONSTRAINTS.md` §4, which
already covered mutation trees and now covers every path a session writes outside its own
worktree — logs included — with this incident as its second recorded case. Wave 30's two
briefs were the first to hand each session a **prefix** rather than a directory.

Check: `grep -c "carries that session's name" docs/program/dispatch/OPERATING_CONSTRAINTS.md`.


**Reported by `W29-SAY`**, which noticed and moved its work into a private subdirectory.
Another wave-29 session was writing `bootstrap.log` and `npmci.log` into **the same path**.

**A session that trusted a log file it did not write would read another session's exit
code.** That is the same class as this programme's other measurement failures — an instrument
reporting about something other than its subject — and it is worse here, because the reader
has no way to notice.

**It is why the `import boto3` check earned its place.** A session had `make bootstrap` exit 0
with a `.venv` holding only `pip`; checking the interpreter rather than the exit code is what
settles it, and checking a log someone else may have written settles nothing.

**Rule for every future brief: write logs to a path that carries the session's own name**, and
never read an exit code out of a file you did not create in this session.

### D-56 — project sections are two jobs, and briefing them as one would force a contract reseal nobody asked for

**Raised by `pdf-analysis-84` from the owner directly, 2026-09-21. Verified against the
contract by the integrator the same day. Registered before anyone briefs it.**

The legacy application organises work by **project section** and carries **14** of them —
`AR, AI, KM, KJ, OV, EOM, VK, PT, PB, SS, ITP, GP, TX, POS`
(`backend/app/pipeline/stages/prepare/task_builder.py:1362`). Ours has none. The owner's
position is that analysing only `AR` today is no reason for the interface not to carry the
structure — **which is `R-18`'s own stub rule applied to sections**, and is consistent.

**The contract has no project-section field anywhere**, confirmed by reading it rather than by
taking the report:

```
CreateProjectRequest -> ['name']
Project              -> ['project_uid', 'name', 'created_at', 'document_count']
UploadDocumentRequest-> ['file', 'display_title']
```

*(A grep for `section` across the schemas returns exactly one hit, in `Evidence` — and it is
**prose in a `description` about the document's prepared text layer**, not a field and not a
project section. The claim survives the check; a careless check would have reported it
refuted.)*

**So this is two jobs with two different prices, and that separation is the whole row:**

| | what it is | cost |
|---|---|---|
| **sections as navigation and stubs** | a frontend structure with 14 named sections, 13 of them honest stubs | **pure `web/src`. No contract, no migration, no reseal.** Squarely inside `R-18` |
| **verdicts aggregated per section** | what legacy's expert screen actually does | **a contract reseal plus a migration.** `Project` and the finding path both need the field, and `web/FRONTEND_LOCK.json` pins the contract's sha256 by hand |

Briefed as one job, the cheap half drags the expensive half along and a wave discovers the
reseal at the end — which is exactly how `R-11` came to revert `W20-CODE`'s work. **Briefed
separately, the first half can land in a design wave and the second waits for a ruling.**

Needs the owner: whether the second half is wanted at all for the alpha, and whether 14
sections is the right set or legacy's set is simply what legacy had.

Check: `python3 -c "import json; d=json.load(open('contracts/api/v1/openapi.json')); print(list(d['components']['schemas']['Project']['properties']))"`

### D-57 — one query key holds two incompatible shapes, and a finished run is polled forever

**Found by `W32-SEE` while rendering screens for an unrelated guard. Verified by the
integrator 2026-09-21. Opened the same day.**

`queryKeys.runs.detail(runId)` is written and read in two different shapes, into one
`QueryClient`:

| | shape | site |
|---|---|---|
| **written** | a bare `RunStatus` | `entities/audit-run/api/use-run-status.ts:79` via `setQueryData`; read back at `:43` and `:59`; also `features/start-run/api/use-start-run.ts:38` |
| **read** | the generated client's envelope, `{data: RunStatus}` | `_pages/review/ui/review-page.tsx:124`, as `runQuery.data?.data` |

**Two consequences, both reachable by a reviewer:**

1. **The review screen renders its empty branch over a run that is in the cache.** `.data` on
   a bare `RunStatus` is `undefined`, so the screen behaves as though nothing were loaded.
   That is `D-16` in reverse — that row was a screen making no call; this is a screen making
   the call and discarding the answer.
2. **A finished run is polled forever.** Returning to the run screen reads the wrapped value,
   gets `undefined`, and `isTerminalRunState(undefined)` is `false` — so the poller never
   stops on a run that terminated.

**Neither is a type error**, because `getQueryData<RunStatus>` asserts the shape rather than
checking it, and `useQuery`'s inference comes from the `queryFn`. The key is the only thing the
two sites share and it carries no shape at all.

**The repair is a decision, not a patch**: either the key carries the envelope everywhere, or
it carries the bare model everywhere and the review page unwraps at the boundary. A guard
belongs with it — a key whose value type is not one type is the same class of defect as a list
narrower than its contract, one level up.

Check: `grep -n "runs.detail" web/src/entities/audit-run/api/use-run-status.ts web/src/_pages/review/ui/review-page.tsx`

### D-58 — a screen tells a reviewer about `uploadDocument` and `document_uid`

**Found by `W32-SEE` 2026-09-21.** `web/src/_pages/version-detail/ui/version-list.tsx:7`
renders a sentence naming an **operation id** and a **contract field** to the person doing the
review.

This is the class `D-54` closed twice in wave 31 — the footer that addressed a developer, and
`RoutePlaceholder` showing developers' notes — **recurring in a third place that no wave-31
grant covered.** `R-18` names it: the alpha is shown as finished, and a finished application
does not explain its own transport to the person using it.

Check: the `W32-SEE` guard reports it as part of its outstanding list.

### D-53 — twenty user-visible English strings survive two waves that each reported the interface translated

**Measured by `W31-STYLE` 2026-09-21, in the course of restyling screens it was told not to
re-translate. Opened the same day.** `R-18`'s **first** named defect is mixed language, and
this is it.

**At least 20 user-visible English strings across 17 modules**, including *"Correlation id"* on
the very failure layer two reports called finished, *"First page"* / *"Next page"* in **all
four** list widgets, and five sentences in `run-progress`.

**The pattern is what earns this a row rather than a commit.** Three sessions have now reported
the interface translated and three have been wrong:

| | claim | found by | what was left |
|---|---|---|---|
| `26b960d` | *"every string a reviewer can see"* | itself, next commit | 106 sentences in 16 `.ts` model files |
| `b0b8148` | the failure layer too | `W31-RUS` | 18 origin groups |
| after `W31-RUS` | the failure layer, again | `W31-STYLE` | these 20, in 17 modules |

Each session measured honestly and each was working inside a grant that could not see the
rest. **The defect is not any session's diligence; it is that nothing in the gate asks the
question.** A guard that fails on a user-visible Latin string outside an allowed list would
have caught all three rounds, and is the repair — not a fourth translation pass.

Check: a sweep for Latin-script user-facing literals across `web/src/**`, with an explicit
allowlist for contract vocabulary, identifiers and code spans.

### D-54 — `web/src/_app/**` and `web/src/shared/lib/**` had no owner, and both held reviewer-facing defects

**Registered 2026-09-21, both closed the same day by the integrator.** Kept as a row because
the **cause** is open even though both instances are shut.

Wave 31 split `web/src` between two streams by naming directories. Two directories were named
by neither, and both turned out to hold exactly the kind of defect the wave existed to fix:
`shared/lib/listing-failure.ts` rendered Russian nouns inside English sentence templates, and
`_app/app-frame.tsx` held the footer `R-18` names **by name**.

**This is the sixth time an ownership line of mine has missed code**, and the previous five are
recorded in `W19_W20_CLOSURE.md` §2 and `W26_W29_CLOSURE.md` §6. The rule already exists —
*list the directories from the tree before writing the glob* — and I have now earned it six
times, which means stating it is not enough.

**The repair is mechanical and is owed to the next wave that splits a tree:** a brief that
partitions a directory must show the partition is **total**, by listing the directory and
accounting for every child. `W31-STYLE` found its gap and reported it instead of reaching
outside its grant, which is the behaviour that makes this recoverable at all.

Check: for any wave that splits a tree, `find <tree> -maxdepth 2 -type d` and account for
every entry against the briefs.

### D-55 — the browser instrument cannot take a screenshot, and a brief asked it to — **CLOSED**

**Closed 2026-09-21 by `W32-SEE`**, in the commit carrying its fix. `Page.screenshot(path, {fullPage, width, height})` is on `cdp.mjs`, with no dependency added and `Page.enable()` already being sent.

**And the brief's stated obstacle was not the obstacle.** It said `#send` being private was what had to be opened. It did not: `#send` is private **to `Page`**, so it blocks code *outside* the class — which is what `W31-STYLE` hit, having no licence to edit the file. A method **on** `Page` calls `this.#send` like every other primitive. Widening it would have exposed the whole protocol to reach one method.

**Found by `W31-STYLE` 2026-09-21.** `tests/e2e/pc01/journey/cdp.mjs` — this programme's own
CDP client, built by `W21-E2E` specifically so a browser journey needs no dependency — has no
`Page.captureScreenshot` and its `#send` is **private**, so the rendering evidence the brief
demanded **cannot be produced with the tree's own instrument**.

The session built its own harness outside the tree and delivered the evidence. But a brief that
asks for something the repository cannot do is a defect in the brief, and the gap is small:
**a `screenshot()` on `cdp.mjs` is about eight lines.**

`R-18` makes this structural rather than incidental. **Presentation is now an acceptance
condition, and the gate cannot see a stylesheet.** Every future design wave needs rendered
evidence, and it should come from the instrument the programme already owns rather than from a
harness that dies with the session that wrote it.

Check: `grep -n "captureScreenshot" tests/e2e/pc01/journey/cdp.mjs`.

### D-52 — the legacy icon set is at least partly Feather, and the notice MIT requires is absent

**Found by `pdf-analysis-84` while rendering the legacy front end as a visual reference for
`R-18`. Verified against the source by the integrator 2026-09-21. Opened the same day.**

`R-18` makes the interface an acceptance condition, and the reference carries **43 inline
`<svg>`** where `web/src` carries **zero**. Before that becomes a build, it has to be settled
whether it is a **copy**, because those are different obligations.

**Two conventions in the 43**: 28 at `viewBox="0 0 24 24"` with `stroke-width="2"`, round caps
and `currentColor`, and 10 at 16×16 with `stroke-width="1.5"` and short hand-drawn paths. The
16×16 set looks hand-authored — `M4 7v6h3v-3h2v3h3V7` is a house drawn straight onto a 16-unit
grid.

**The 24×24 set is Feather, and the two candidate matches are not equally strong. That
distinction is the finding.** Fetched from `feathericons/feather` and compared:

| icon | Feather's source | legacy | verdict |
|---|---|---|---|
| `dollar-sign` | `<path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>` | the same string | **byte-identical, 45 characters. Conclusive.** |
| `chevron-down` | `<polyline points="6 9 12 15 18 9"/>` | `M6 9l6 6 6-6` | **same geometry, re-encoded as a path. Not a copy of the bytes**, and on its own it would prove nothing |

The reporting session offered `chevron-down` as one of two exact matches. It is not one; it is
a re-encoding. **The conclusion survives anyway on `dollar-sign` alone**, plus Feather's whole
attribute convention, and it is recorded this way because a row that overstates its evidence
gets re-opened by the next session that checks it.

**Feather is MIT**, which requires that *"the above copyright notice and this permission notice
shall be included in all copies or substantial portions of the Software."*

**And that notice is absent from the legacy tree.** No `LICENSE`, no `NOTICE`, and **no icon
package in `frontend/package.json`** — its dependencies are `eslint`, `typescript`, `vite` and
`vitest`. The icons arrived by paste.

**Why this is good news rather than bad.** If it is Feather, an icon set stops being a design
build and becomes **a copy plus a `NOTICE` file** — much cheaper for `R-18`. What it is not is
free of obligation, and the obligation is not discharged by the legacy tree having skipped it.

**This is deliberately NOT folded into `D-11`**, and the argument is the reporting session's:
`D-11` is a **resolved dependency with a declared licence** (`certifi`, MPL-2.0, in the test
group). This is **pasted source with no declaration**. Different shape, different check; one
row answering both would answer neither.

Check:
```
curl -s https://raw.githubusercontent.com/feathericons/feather/main/icons/dollar-sign.svg
```
and compare to the `d` attribute of the legacy `dollar-sign`.

### D-49 — the alpha stand is published to every interface, and one of its two paths takes writes with no credential — **CLOSED**

**Ruled by the owner 2026-09-22: bind to `127.0.0.1` and reach the stand over an SSH tunnel.
Closed the same day, in the commit carrying the fix.**

`compose.server.yml` and `compose.tls.yml` now publish on
`${ALPHA_BIND_ADDRESS:-127.0.0.1}`, so **the safe value is what you get from an omission** and
publishing is a decision someone has to write down. Driven after redeploying:

```
docker port auditmanager-w19a-proxy-1      -> 8080/tcp -> 127.0.0.1:31500
curl http://<host public ip>:31500/...     -> 000  (was 200)
curl http://127.0.0.1:31500/...            -> 200
```

**The second half of the row is not closed by this and is not meant to be.** `/bff/v1` still
serves all fifteen operations without a credential; that is the designed posture, and what
changed is who can reach the origin. `PA-01` criterion 2's purpose — the dependency standing
in front of all fifteen — is still only true of `/api/v1`. If `R-1`'s host ever sets
`ALPHA_BIND_ADDRESS`, that question returns immediately, which is why the runbook says to
verify a firewall **against Docker's own chains** rather than against `ufw status`.

**Found by `W30-CERT3` as `W30CERT3-1`, and measured further by the integrator, who found the
second half. Opened 2026-09-21. This is the highest-severity row in this register.**

**Half one, the session's.** The published origin carries **two** paths to the same fifteen
operations, and the credential is in front of only one of them. Measured on the owner's stand:

```
GET http://127.0.0.1:31500/api/v1/projects   -> 401   (authentication_required)
GET http://127.0.0.1:31500/bff/v1/projects   -> 200
POST /bff/v1/projects, no Authorization       -> 201   (W30-CERT3, on its own stack)
```

**This is the designed posture and criterion 2 does not fail because of it.** The browser is
meant to hold no credential; `web/`'s server-side BFF route adds it. But `PA-01` criterion 2's
stated purpose is that the dependency stands *in front of all fifteen operations*, and on the
origin it stands in front of `/api/v1` and not in front of `/bff/v1`. `16d3503`'s
certification probed `/api/v1` only, which is why three certifications did not see this.

**Half two, and it is what makes the row urgent rather than architectural.**
`infra/deploy/compose.server.yml:213` publishes the proxy as
`"${ALPHA_HTTP_PORT}:8080"` — **with no interface prefix, so Docker binds `0.0.0.0`.** The
same file's own comment eleven lines above says *"the developer stack publishes `127.0.0.1`
only; this one publishes nothing at all"*, which is true of `postgres` and `s3` and is not
true of the proxy.

And `ufw` does not stand in front of it. `ufw status` reports one allowed port, `80/tcp` —
but a Docker-published port never reaches ufw's `INPUT` chain, because Docker writes its own
rules into `nat/DOCKER` and `filter/DOCKER`, which are traversed first:

```
iptables -t nat -L DOCKER -n | grep 31500
  DNAT  tcp  0.0.0.0/0 -> 0.0.0.0/0  tcp dpt:31500 to:172.27.0.4:8080
iptables -L DOCKER -n | grep 8080
  ACCEPT tcp 0.0.0.0/0 -> 172.27.0.4  tcp dpt:8080
```

Driven from this host's **public** address rather than from loopback:
`GET http://176.12.74.47:31500/bff/v1/projects -> 200`.

**Independently reached from a second origin, by a session that did not know the row existed.**
`pdf-analysis-84`, working on `agent/w31-ui`, ran a Next dev server on 31690 pointed at
`AUDITMANAGER_API_UPSTREAM=http://127.0.0.1:31500` and read through `/bff/v1` successfully —
**from outside the compose network**. That is the direction that matters: the path is not
reachable only from inside the stack or only from loopback tooling.

**So on this host, today, an unauthenticated read and write path to all fifteen operations is
bound to every interface, behind a firewall that is not in the path.** Whether a network in
front of the machine blocks 31500 is not something this repository can measure, and **not
knowing is not the same as being protected** — which is the whole of why this is a row.

**What it bears on.** `R-4` says real client documents may be uploaded to the alpha server
during the pilot. Today that would put them behind an open write path. And `R-1`'s host, when
it arrives, will run this same compose file.

**Two candidate repairs, and they are not alternatives — the second is needed either way:**

1. **Bind the published port to an interface**, `"127.0.0.1:${ALPHA_HTTP_PORT}:8080"`, and
   reach the stand over an SSH tunnel. Correct for a developer host; it changes how the owner
   reaches 31500, so **it is the owner's call and has not been made.**
2. **Put the credential in front of `/bff/v1` as well**, or state in the runbook that the
   origin must never be published to an untrusted network without it. The BFF exists so the
   *browser* holds no credential; that argument says nothing about the *origin*.

Check:
```
docker port auditmanager-w19a-proxy-1          # expect 0.0.0.0 today
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:31500/bff/v1/projects   # 200 today
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:31500/api/v1/projects   # 401
```

### D-50 — a character offset with no coordinate system any second extractor can resolve

**Found by `W30-CERT3` as `W30CERT3-2`. Opened 2026-09-21. Criterion 5 is unaffected** — the
quotation is exact, occurs once, and is on the page named, confirmed with an extractor the
application does not use.

The review screen prints *"characters 707–746 of the whole document"*. The offsets are
length-exact and internally consistent, and **no second extractor resolves them**: pdfminer
puts the same string at 726, and the drift grows at every page boundary. The number is
therefore true only in the coordinate system of the extractor that produced it, and that
system is **not named anywhere the reader can see**.

This is `D-25`'s shape one level down. `W22-WEB` repaired a caption that printed a
document-global offset beside a page number as though the two shared a coordinate system; this
row is that the surviving offset does not identify its own system either.

Check: extract the same version with a second library and compare the index of the quotation.

### D-51 — criterion 8 is a container restart, and the reason is now structural

**Raised by `W30-CERT3` as `W30CERT3-3`, replacing a reason that was false.** Registered
rather than open-for-repair: there is nothing here to fix in the software.

`PA-01` criterion 8 has been certified three times as *holding with a named exception*, and the
exception said the restart could not be a host reboot because **the host carries three alpha
stacks**. It carries one, since 2026-09-21 and ruling `R-6`. The real limits, measured:

- the owner drives 31500 by hand, and other lanes' services run on this machine;
- **the certifying session runs on the host it would have to reboot, and a session cannot
  witness its own reboot.**

The third is structural and does not go away with a tidier host. What *was* driven is stronger
than the previous rounds': `docker compose down` without `-v`, all five containers destroyed,
`deploy.sh` back up, and a 73-line census that **diffs to nothing**.

Check: `artifacts/checkpoints/PA-01/certification-ac7c348.json`, criterion 8.

### D-48 — a constant that promised a ceiling, and nothing was standing on it — **CLOSED**

**Found by `W30-LISTS`, reported rather than repaired because the module claimed two
derivations that produce different sets. Closed 2026-09-21 by the integrator, in the commit
carrying its fix.**

`src/auditmanager/storage/errors.py`. `SAFE_DETAIL_KEYS` omitted `aggregate_type` while
**two of the package's own error classes declare it** in `allowed_details` — and
`BlobNotFoundError.__init__` sets it by default on **every instance**.

**It was not a leak, and that is what makes it worth a row.** `ingest/failures.py:40` narrows
details to `code.safe_detail_keys` before an envelope is built, and `envelope.build` refuses
an undeclared key. So nothing was rendered that should not have been. The defect is that
`SAFE_DETAIL_KEYS` **had no functional consumer anywhere in `src/`** — exported from
`storage/__init__.py`, named in two docstrings, read by nothing. It could not redden. A
reviewer asking it *"may this error carry `aggregate_type`?"* was told **no** by a constant
that had been wrong since it was written.

**Which of the two derivations the module means was settled from the module's own mechanism,
not from taste.** `StorageError.__init__` checks a detail against `self.allowed_details`,
never against `SAFE_DETAIL_KEYS`. So the only claim this set can be making is the one the
module docstring makes to a reader — *"a name that is not in this set can never be rendered
into an error message"* — and that is a statement about the **union of the subclasses**, not
about the catalog. The catalog is where most of these names came from; it is not what the set
is. `expected_revision` stays out for the same reason: the catalog permits it for `conflict`
and no class in this package carries it.

The repair is one member and **two guards, which are the set's first consumers**: every
subclass's `allowed_details` is inside it, and it carries nothing no subclass can use. The
first was red before `aggregate_type` was added — the D-48 state is its own mutation.

Check: `.venv/bin/python -m pytest tests/contract/domain_p02/test_narrow_sets_against_contracts.py -k safe_detail -q`

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

**Re-measured 2026-09-21.** Two of the four rows this table carried had been **ruled and were
still listed as open** — the 21st code (`R-8`, reverted by `R-11`, reinstated by `R-13` and
paid by `W25-SEAL`) and whether `origin/main` advances (`R-7`; it has advanced twice, to
`alpha-w18` and `alpha-w25`). A table of what the owner still owes that lists things the owner
already decided is the same failure this register's rule 1 exists to prevent, pointing the
other way.

| # | Item | Blocks | Since |
|---|---|---|---|
| `R-1` | **a host, a name, a certificate, DNS** | `PA-01` **criteria 1 and 2**, and nothing else — `W26-HOST` established that no part of this repository is still a reason | 2026-09-17 |
| `R-4`(a) | who uploads real client documents to the alpha server | the pilot's start | 2026-09-17 |
| `R-4`(b) | what event ends the pilot, at which the uploads are wiped | the pilot's end, and `reset.sh`'s trigger | 2026-09-17 |
| `D-46` | may a failed run name **which** dependency was unavailable | one sentence on one screen; **a reseal either way**, and §1's row says why both answers cost one | 2026-09-21 |
| `R-9` | the owner drives the application by hand | **`D-9`**, the norms corpus — the owner placed it there deliberately | 2026-09-18 |
| `OD-18` | three to five named experts with committed slots | `P4-BHV-01`, and it alone | pre-programme |
| `OD-17` | the shape of the next corpus; PC-02's precision evidence is saturated | the P05 corpus decision. **`R-16`/`R-17` bear on it and do not close it** | pre-programme |
| `R-18`(c) | **is the alpha dark by default** | the design wave's palette. The legacy reference defaults to dark; `globals.css` says in its own header that *"a theme toggle is a decision nobody has taken"*, and that is still true. **Not a styling decision, so no stream may settle it** | 2026-09-21 |
| `R-18`(a) | is the **contract vocabulary** translated — `published`, `partial`, `failed`, `cancelled`, `accept`/`accepted`, `recorded`, the finding categories | one pass either way; every badge already carries its machine value in a `data-` attribute, so `PA-01` criterion 4 is unaffected whichever way it goes | 2026-09-21 |
| `R-18`(b) | is the **stub boundary** the one proposed — no stubs on `upload → run → finding → verdict → export` | the size of the design wave. Proposed by a session, adopted by the integrator, **never put to the owner in those words** | 2026-09-21 |

**`R-9` is the one that moved.** It gated `D-9` on manual testing, and until 2026-09-21 the
stand was several waves behind the tree, so the owner could not have done that testing against
current code even if they had sat down to it. As of `ac7c348` the stand **is** the tree, proved
file by file by `verify-deployed.sh`. The thing in the way was ours and it is gone.

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
