# W25-SEAL — `R-8` reinstated, and the frontend reseal `R-13` authorises, paid

Session `W25-SEAL`. Branch `agent/w25-seal`, from `origin/dev`.

**The headline: `make gate` is green at the tip, exit 0, *including the frontend* — which is
the half that stopped `W20-CODE` twice.** `staged_upload_lost` is in the catalog, on the
wire and in the served document, the two blob faults no longer produce byte-identical
envelopes, and the client and its lock were regenerated and resealed rather than argued about.
**All six digests were re-derived with `sha256sum` against this tree; all six agree with the
`W20-CODE` record to the byte. None differed.**

> **Opened before the first edit**, as the brief's integration contract requires (commit
> `02ec7e3`, before the cherry-pick). Sections below were filled as the work landed.

## 0. Arrival

| | |
|---|---|
| HEAD on arrival | `fea3794` — *docs: R-12 through R-15 ruled by direct poll*, `origin/dev`'s tip |
| `df -h /` | **13 GB available** of 119 GB, 89% used. The brief said ~17 GB; see §7 |
| lane | `gate-w25a`, PostgreSQL **55960**, MinIO **59560/59561**, database `audit_w25a`, bucket `auditmanager-gate-w25a` |
| worktree | `/root/w25seal` |
| provisioning | `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` → `bootstrap OK`, exit 0; `npm --prefix web ci` → 184 packages, exit 0 |

The lane was **new**: `docker volume ls` and `docker ps -a` matched nothing on `w25`, and
55960 / 59560 / 59561 were unbound. **31500 was not touched**, and no image was built.

## 1. The code — `git cherry-pick b437616 271ba42`

### 1.1 It applied clean

The brief said to *"expect conflicts, since the tree has moved several waves."* **There were
none.** Both commits applied without a single conflict hunk, and the reason is that nothing
between `8a88fce` and `fea3794` touched the six domain-contract files, `storage/errors.py`,
`shared/errors/codes.py`, `api/schemas/models.py` or the migration's `ERROR_CODES` list. The
tree moved; **this** part of it did not.

The substance is `W20-CODE.md` §§1.2–1.4 and is not restated here: `staged_upload_lost`, 503,
`retryable: true`, category `dependency`, `safe_detail_keys` exactly `["dependency"]`, and
`conflict` byte-identical to round 6. `R-13` reinstates that ruling; it does not reopen it.
`conflict`'s `safe_detail_keys` were not touched, no existing code's `retryable` moved, and no
other code was re-examined — the brief's three non-goals, all held.

### 1.2 `W0-DOM-02`, re-verified against this tree

The family carries one `candidate_revision` across six files, and `W0-DOM-02` permits a
**single-value write** in four of them. Checked here rather than inherited:

```
contracts/domain/v1/identifiers.json          -  "candidate_revision": 6,  →  7,
contracts/domain/v1/identifiers.schema.json   -      "const": 6,           →  7,
contracts/domain/v1/state-machines.json       -  "candidate_revision": 6,  →  7,
contracts/domain/v1/state-machines.schema.json-      "const": 6,           →  7,
```

**Exactly one changed line each, numeric only, 6 → 7.** `git diff --check` over
`contracts/domain/v1` is clean, and the gate runs it over the whole tree as its last step.

### 1.3 Rollback / feature flag: none, and why that is the right answer

`contracts/domain/v1/error-codes.json` declares `"frozen": false` and
`"status": "draft_candidate"`. **This is an addition to a draft candidate, not a freeze-break**
— `D-8` — and the `revision_note` says so in those words, as `R-3`'s did. A catalog addition to
an unreleased candidate is not behaviour behind a flag: there is no previous value to fall back
to, because no caller could receive this code before it existed. `contract_version` stays
`1.0.0-draft.1`. **Rollback is `git revert`, which is exactly what `R-11` did.**

## 2. The four steps of `W20-CODE.md` §1.6

### 2.1 Watched red first

Before a single one of the four was written, on the cherry-picked tree:

```
FAILED tests/integration/api/test_query_surface.py::
       test_the_committed_client_was_generated_from_this_contract
AssertionError: the frozen document has moved since the client was generated from it.
  - 701ecd58a860f53762775bee353cd5461d21c9e56f0bcb8d00b45dbfe685f8fe
  + 68762ec87931ed03ee8b68d16717533c4f7f68816bc1b490b53ba8a5f50f1513
```

and `npm --prefix web test` was **7 failed / 699 passed in 48 files**, the seven being five in
`openapi-drift.contract.test.ts` and two in `frontend-lock.guard.test.ts`. That is
`W20-CODE`'s block reproduced exactly, at a base 25 tests larger than its own.

**So the frontend gate went red before it went green, and it was watched rather than assumed.**

### 2.2 The six digests, re-derived

`npm --prefix web run api:generate` reported `wrote 4 files, 15 operations, contract sha256
68762ec8…`, and the diff was the input digest in four generated headers, the `web/openapi/`
snapshot, and one enum member in `types.gen.ts` — nothing else. Then, with `sha256sum` against
the tree and **not** by pasting the recorded values:

| file | re-derived | vs the `W20-CODE` record |
|---|---|---|
| `contracts/api/v1/openapi.json` | `68762ec87931ed03ee8b68d16717533c4f7f68816bc1b490b53ba8a5f50f1513` | **same** |
| `web/openapi/openapi.json` | `68762ec8…f1513` (identical to the contract, as the snapshot must be) | **same** |
| `generated/client.gen.ts` | `02811af2f7373fcdfe97b50b1a68641f08bb9057b6eff59dd50df829da0adf17` | **same** |
| `generated/index.ts` | `364bfce1de63ccb60c06dfbe97b9bb1e94e7a06e22109bef03243c4a0d1e193a` | **same** |
| `generated/operations.gen.ts` | `7e8b95d5c235ecc0b667fd8f2453b4a1422c2bbf56e50938b99011166e6e3e46` | **same** |
| `generated/types.gen.ts` | `e064c3176d50f4367fd1329dd1262e8cdc1420e583f9b218fb77b855dca97483` | **same** |

**Zero differed.** That is the generator's determinism claim holding across three weeks and
several waves of unrelated tree movement, and it is worth having measured rather than trusted:
had one moved, pasting the recorded value would have produced a lock that was wrong in a way
the guard would have caught but the reviewer would not have understood.

`operations` **15** and `component_schemas` **46** in the lock are unchanged and re-asserted by
`frontend-lock.guard.test.ts` against the document itself, so nothing there needed
re-measuring. `content_commit` is `c87a630` — this branch's cherry-pick of `b437616`, which is
recorded as `dispatch_named_commit` so the provenance is not lost.

### 2.3 The two literals

`web/tests/contract/seam-operations.contract.test.ts` — *"the closed twenty-one-code set"* →
twenty-two, and the new code is now named in a `toContain` rather than only counted, so a
catalog of the right **size** with the wrong **member** is still red.
`web/tests/unit/api/failure-surface.test.ts` — `toHaveLength(21)` → `22`.

## 3. `contracts/api/v1/openapi.json`, and where the brief's boundary is wrong

The brief allows this file for **"one enum member only"**. Three lines moved, and **two of them
are forced by a guard that did not exist when `W20-CODE` wrote its §1.6**:

| line | why |
|---|---|
| the `ErrorCode` enum member | `test_the_error_code_enum_equals_the_frozen_catalog` asserts set equality against the catalog, and `uploadDocument` really emits this code |
| `info.description`: *"the twenty-one-code catalog"* → *"twenty-two"* | **`tests/contract/api_v1/test_surface_counts_in_prose.py` reads the contract's own `info` block** and compares every `<n> codes` claim against `len(catalog["codes"])`. That guard is `D-23`, it landed on `dev` from this same `W20-CODE` wave, and it makes the old wording a red test the moment the catalog reaches 22 |
| the `DependencyUnavailable` response description | it named one code for a status that now carries two. Not forced by a test; it is `b437616`'s own byte, and leaving it would have published a description that is simply false |

**No path, operation or component schema moved: still 12 / 15 / 46**, measured from the
document after the edit. `a5f4001` did precisely this for `R-3`'s twenty-first code.

The brief's *"one enum member only"* is therefore **not achievable while green**. It reads as a
tightening of `W20-CODE`'s boundary, but `W20-CODE`'s own deliverable is what closed it: the
wave that wrote the prose guard is the wave whose prose the guard now polices.

## 4. Three count statements the tree had left behind

The cherry-pick moves the catalog to 22 and these said otherwise. Two are **asserts**:

| where | was | in the gate? |
|---|---|---|
| `tests/integration/api/test_envelope_screen_rules.py` | `assert len(raw["codes"]) == 21` | **yes** — red the moment the code lands |
| `tests/contract/test_cp00_candidate.py` | `self.assertEqual(len(catalog["codes"]), 21)` | **no** — `PROTOTYPE_PROFILE.md` §6.3 quarantines that file and the Makefile `--ignore`s it |
| `contracts/domain/v1/README.md`, the `## Errors` heading | *"20 codes across 10 categories"* | no |

The middle one is the interesting one. **Nothing would have reddened, and that is the reason to
fix it rather than the reason not to** — a false assertion nobody runs is still a false
assertion, and the next session to un-quarantine that file inherits it. The README line was
stale by two: it has said twenty since `R-3` made it twenty-one, which is `D-8` inside the
contract's own README, and it is not this round's doing. **Ten categories is still correct**:
`staged_upload_lost` joins the existing `dependency` category and the category set is unchanged,
which was checked by reading the catalog rather than by trusting the sentence.

## 5. Two residues named rather than taken, and one question for the owner

### 5.1 `web/src/shared/api/errors.ts` — outside `allowed_paths`

Two comment lines there state a catalog size:

- line 4: *"one closed **twenty**-code catalog"* — stale since `R-3`, not this round's doing;
- line 25: *"The generated `ErrorCode` union is the full **twenty-one**-code catalog"* — **true
  before this change and false after it.**

`allowed_paths` gives this session `web/src/shared/api/generated/**`; `errors.ts` is its parent
directory and is not listed. No test reads either line — `D-23`'s guard scans
`src/auditmanager/api`, `infra/deploy` and `web/src/app/bff`, not this file. So it is **named
here rather than edited**, which is `W20-CODE` §2.4's precedent for the fifth stale count. It is
one word in each of two comments and belongs to whoever owns `web/src/shared/api/`.

### 5.2 `PC01_ERROR_CODES` stays at twelve, and this one is a real question

`web/src/shared/api/errors.ts` narrows the catalog to *"the twelve codes a PC-01 screen has to
be able to render."* **`uploadDocument` can now emit `staged_upload_lost`, and it is not in that
list.** Nothing breaks: the module's own contract is that a code outside the subset but inside
the catalog is still an `ApiError`, never `UnrecognizedApiError`, so the envelope renders and
`retryable: true` reaches the caller. But the list's stated meaning is now narrower than the
surface it describes.

Widening it is a **screen** decision — the brief forbids screen changes in three directories and
`R-13` authorises *"this code and the reseal it forces, nothing wider."* `W20-CODE`'s four steps
did not include it either. **It is left at twelve and raised here** so the wave that owns the
upload screen can rule on whether an upload failure the user can retry deserves a rendering of
its own. It belongs in `DEBT_REGISTER.md`, which this session may not edit.

### 5.3 `docs/program/reviews/W20-CODE.md` is not on `dev`

`R-11` says *"the evidence is in `docs/program/reviews/W20-CODE.md`"* and this brief names it as
a frozen input. **It exists on branch `agent/w20-code` (tip `a3eb68d`) and on no other ref.** It
was never merged, so a reader on `dev` following either pointer finds nothing. Read here with
`git show agent/w20-code:docs/program/reviews/W20-CODE.md`. Landing it is the integrator's
call and outside this session's paths.

## 6. Failure / idempotency / security cases

### 6.1 The characterization records: **zero of thirty-six**, re-measured

`W20-CODE` measured zero of 36 and refused to write a `permitted_change` for a change that did
not happen. **The measurement was repeated on this tree rather than inherited**, by parsing all
36 records as JSON:

| | |
|---|---|
| records carrying a non-2xx response | **16** — one 409, eleven 422, three 404, one 500 |
| the codes they carry | `idempotency_key_reuse`, `validation_failed` ×11, `not_found` ×3, `dependency_credential_refused` |
| records carrying a `conflict` envelope | **zero** |
| records exercising `TemporaryBlobLostError` or `BlobAttributeConflictError` | **zero** |
| occurrences of the string `conflict` | one, in `05-startRun.replay_with_normalised_property.json`'s `purpose` prose — *"this replays rather than conflicting"* — which is about idempotency and not an envelope |

**So no record moved, and no `permitted_change` and no `decided_by` was written**, because
there was nothing to permit. `PERMITTED_EXCEPTIONS` is untouched: it is a literal map with tuple
values, extending it here would have been a claim that something happened, and the brief's own
instruction is *extend, never loosen*.

**One methodological note, because it nearly produced a confident wrong answer.** The first
sweep walked each record as a nested structure looking for a key named `error_code` and found
**none at all** — which is true and misleading, because a record stores its response body as a
**JSON string** under `response.body.text`, so the envelope is one level below where a
structural walk looks. The conclusion survived the second, correct measurement unchanged, but
the first one would have reported *"no record carries an error envelope"*, which is false: 16 do.
`OPERATING_CONSTRAINTS.md` §12 again — a query the checker cannot read is not a check.

### 6.2 Shown able to fail

`tests/integration/api/test_two_blob_faults_are_two_envelopes.py`, six tests, pinning the
**envelope** and not the code name — `W16-ERR`'s `D-12` precedent, where the lie was the
`retryable` flag and a test reading the class's `code` attribute would have watched it past.
Every assertion is on the rendered body and the status line, through the shipped
`domain_error_from_storage` → `envelope_response` path.

Run on a **full mutation copy outside the worktree** (`make mutation-copy MUT=/root/w25seal-mut
FULL=1`), baselined **6 passed** unmutated first:

| mutation | result |
|---|---|
| `TemporaryBlobLostError.code` `"staged_upload_lost"` → `"conflict"` (the pre-`R-8` tree) | **5 of 6 red**, 1 passed |
| `staged_upload_lost.retryable` `true` → `false` **in the catalog** | **3 of 6 red**, 3 passed |

Both figures reproduce `W20-CODE` §1.8 exactly. The one test that stays green under the first
mutation is the file's own proof-of-proof,
`test_the_comparison_reddens_when_the_two_share_a_code`, which reconstructs the pre-`R-8` shape
and asserts it still reproduces the defect.

The second mutation is the one that matters for `D-12`: the two envelopes still differ in
`error_code`, `message` and `details` with the flag flipped, so a test that compared only *"are
these two different"* would have stayed green. `test_the_two_envelopes_differ_in_more_than_the_
correlation_id` requires `{"error_code", "message", "retryable"}` to be a **subset** of the
differing keys, and `test_retryable_is_the_catalogs_and_not_the_call_sites` asserts the flag
comes from `ErrorCode.<CODE>.retryable` rather than from the call site. Both went red.

**No tracked file was edited to mutate**, and `/root/w25seal-mut` was removed afterwards;
`git status --porcelain` is empty.

### 6.3 The lane's `ERROR_CODES` `CHECK`, checked and not assumed

`db/migrations/versions/20260910_0002_pc01_schema.py` builds two `CHECK` constraints from
`ERROR_CODES`, and that list gains a member here. An already-migrated database keeps the old
constraint, because `make migrate` is a no-op at head — which is why `W20-CODE` destroyed its
lane's volumes by name before its confirming gate and was right to.

**This lane needed no teardown, and that was established by looking rather than by assuming.**
`gate-w25a` was created after the migration edit, so `pg_constraint` was read directly:

```
ck_command_record_error_code | CHECK (error_code IS NULL OR error_code = ANY (ARRAY[... 22 members ...]))
ck_model_call_error_code     | CHECK (error_code IS NULL OR error_code = ANY (ARRAY[... 22 members ...]))
```

Both arrays contain `staged_upload_lost`. Had they not, the gate would have been measuring this
lane's history rather than the committed tree.

### 6.4 Security

Nothing in this change touches authentication, authorization or the token seam. The new code's
`safe_detail_keys` is exactly `["dependency"]` — the stable dependency class name, never a host,
URL, bucket or object key — and
`test_neither_envelope_carries_a_location_or_the_callers_own_declaration` asserts that neither
envelope carries a location or the caller's own declaration back. `details` is
`{"dependency": "blob_storage"}` and nothing else.

## 7. The gate

Run with the tree committed and `git status --porcelain` empty, on lane `gate-w25a`, **never
through `| tail`** — the exit code is `$?` after a redirect to a file.

**Run twice: at `8183a0f`, the tree with every code change in it, and again at `49f013d`, the
tip with this review committed. Both identical, both exit `0`.**

**Exit code: `0`. `GATE OK: battery, foundation, frontend and whitespace all pass`.**

| | the brief's base | measured here |
|---|---|---|
| foundation | 35 | **35 passed** (and `check-db`, `check-services`, `check-storage` all `FOUNDATION-CHECK OK`) |
| battery | 1932 passed / 5 skipped / 168 subtests | **1938 passed / 5 skipped / 169 subtests**, 4:25 |
| frontend | 706 in 48 files | **706 passed / 48 files passed** |
| exit | 0 | **0** |

The tip run at `49f013d` reported the same four numbers — 35, `1938 passed, 5 skipped, 169
subtests`, `706 passed (48)` — and finished at **11:33:33**.

**Every delta is accounted for.** `+6` battery tests is exactly
`test_two_blob_faults_are_two_envelopes.py`; `+1` subtest is `test_error_envelope.py` iterating
the enum, which is now 22 rather than 21. The frontend total does not move because steps 3 and 4
changed two literals inside existing tests rather than adding any. The brief's base figures are
therefore confirmed to the number, arithmetically — the frontend one **directly**, since the red
run in §2.1 reported `7 failed | 699 passed (706)` across `48` files before anything was written.

**Disk.** The brief said ~17 GB; `df -h /` on arrival reported **13 GB** available, and 11 GB
after the worktree, `node_modules`, the two virtual environments and the lane's volumes. No
image was built. `/root/w25seal-mut` was removed as soon as §6.2 was measured.

**Processes.** No `uvicorn` was started: the envelope evidence over a real socket already exists
in `W20-CODE` §1.4 and re-taking it would have proved nothing new. The lane's two containers are
the only processes this session started, and the three alpha stacks were not touched.

## 8. What was false in the brief

1. **"expect conflicts, since the tree has moved several waves"** — the cherry-pick applied
   **clean**, both commits, no conflict hunk. §1.1.
2. **`contracts/api/v1/openapi.json`, "one enum member only"** — not achievable while green.
   Three lines move and two are forced, one of them by `D-23`'s guard, which is `W20-CODE`'s own
   deliverable and landed on `dev` after §1.6 was written. §3.
3. **"`df -h /` first (~17 GB)"** — **13 GB**. §7.
4. **`docs/program/reviews/W20-CODE.md` as a frozen input** — it is not on `dev`, and `R-11`
   points at it too. Only `agent/w20-code` carries it. §5.3.
5. **"Check `pg_constraint` directly before assuming your lane is clean"** — right instruction,
   and the check was made; but this lane was created after the migration edit, so there was
   nothing to destroy. The warning is not false, it simply did not bite. §6.3.

Everything else held. `W20-CODE.md` §1.6's four steps are exact, all six of its digests are
exact, `PERMITTED_EXCEPTIONS` really is a literal map with tuple values, the catalog really does
declare `"frozen": false` and `"status": "draft_candidate"`, `R-13` really does authorise
`web/FRONTEND_LOCK.json` explicitly, and the ruling's own section numbers — `R-13` at §3.8,
`R-8` at §3.6 as the `revision_note` cites it — are both right.

## 9. Elapsed

Measured, not estimated. First command **11:14:02**; the confirming gate at the tip reported at
**11:33:33**. **About 20 minutes** wall clock.

Of which roughly 11 are the two full `make gate` runs (4:25 and 4:30 of battery apiece, plus
their foundation sequences and the frontend suite), and most of the rest is `make bootstrap`,
`npm --prefix web ci`, the lane bring-up, the red measurement and the mutation copy. The editing
itself is a few minutes: the cherry-pick applied clean, the four steps are mechanical, and every
digest was already known to be correct before it was written down. **`R-11`'s cost was a
permission boundary, not an amount of work** — which is worth saying plainly, because the row
sat open for two waves.
