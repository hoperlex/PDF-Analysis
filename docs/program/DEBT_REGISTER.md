# Debt register

Written 2026-09-17 by the integrator. **Re-measured against the tree at `315de25` on
2026-09-18**: D-2, D-3, D-4, D-6, D-7 and D-10 close, D-12, D-13 and D-15 open, D-14
opens and closes in the same pass, and §3's own figure turned out to be three waves
stale. **Two of those closes — D-2 and D-4 — had been true for a day**: they were fixed
thirty-nine minutes after this file was created and nobody carried it back. A row is
closed in the same commit as its fix, or this register lies.

**Measured against the tree, not compiled from closure records** — `W4_CLOSURE.md` §3 records
a register that had been entirely obsolete while still reading as the list of what was open,
and this file exists to not become that.

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

### D-1.5 — `W12CERT-DEF-3`, the named exception to the certification

**18% of `web/src` is reached by no test** — 34 of 110 modules, 1352 of 7604 lines, measured
independently by `W12-WEB` and again by `W12-CERT` (`110 76 34`). It includes
`run-progress.tsx`, and `terminal_reason` reaches a user in exactly one line of it
(`run-progress.tsx:112`).

Criterion 4 requires the **UI** to distinguish run states and provider mode. The rules behind
that are guarded; **the rendering is not.** Ten mutations inside the unreached region were all
survivors, including "`run-progress` stops rendering `terminal_reason`" with 440 frontend
tests green.

This is the certification's one named exception and the strongest candidate for the next wave.
Seven of the ten are ordinary components `renderToStaticMarkup` can reach, so most of it is
reachable with the harness that already exists.

Check: the script in `docs/program/reviews/W12-WEB.md` §11.

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

Closed by `1b2549b` alongside D-2, and stale here for the same day and the same reason. An
object recording no digest is now `validation_failed` carrying `aggregate_type="Blob"`,
`field="sha256"`, `constraint="recorded on every published object"` — not an integrity verdict
with `actual_sha256=""`, which the code's own comment calls *"an empty string where a digest
is expected, and a claim about bytes nothing has looked at"*. It is also the same answer
`BlobStore.read` gives over the same row, so the two do not disagree about one object.

**Wave 14 produced this state on a real host by accident, which is the best evidence the
choice was right.** `mc mirror` restored an object whose bytes were intact and whose
`X-Amz-Meta-Content-Sha256` was gone. Under the repaired code an operator is told the store
has compared nothing to anything — not that their bytes are corrupt, and not sent to restore
a backup they do not need.

Check: `sed -n '286,300p' src/auditmanager/ingest/reconciliation.py`.

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

### D-5 — the first browser-driven run answered 500, twice

On 2026-09-16 a manual harness outside the repository put a stdlib server in front of
`create_app()` and drove the UI against it. `GET /projects` 200, `POST /projects` 201,
`POST /projects/{uid}/documents` **201**, then `POST /api/v1/runs` **500 — twice — and the
session ends there.** Provider mode `proxy`, `operations=12`.

**`startRun` is green in every suite and in three certifications, all of which drive it in
process.** The first time a browser asked, it answered 500.

Two readings with different owners and **nothing in the evidence distinguishes them**: a real
defect on the run path that only a socket exposes, or an artefact of how that harness hands a
body to `Request.build`. The harness logged status lines only, so the envelope behind the 500
was not kept.

The part worth flagging hardest is not the 500. **The only live-transport evidence this
programme has ever produced sits outside the tree**, at `/root/pdf-prototype/bridge.log`, and
`grep -rln "pdf-prototype\|bridge.py" docs artifacts` returns nothing. Reported by
`pdf-analysis-d9`; the harness is explicitly not a deliverable.

Check: the log named above, while it exists. **It is untracked and outside the repository, so
this row may outlive its own evidence** — which is the argument for reproducing it under a
real server rather than preserving a log.

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

### D-9 — "paragraph granularity" for the normative corpus is production, not movement

The owner has directed that the normative document corpus be carried into PostgreSQL at
**paragraph granularity**, so that vectors can be laid over it afterwards. `pdf-analysis-d9`
measured the corpus against its manifest and reported a shape that makes that sentence mean
something other than a load. **Verified independently here at `85aaa24`:**

- **674 documents**, per `.local/norms/corpus/MANIFEST.json`, outside git entirely — no diff
  and no grep of the tree will show them;
- the per-document `blocks.json` is **page-level**, and a block's complete key set is
  `block_id, block_type, coords_norm, crop_url, export_status, ordinal, page_index,
  page_label, polygon_points, shape_type, status`. **There is no field carrying text**;
- `block_type: "text"` is a *type label*, not content. A substring search for `"text"` finds
  it and reads as though content were present — I made exactly that mistake and caught it by
  reading the key set instead. `OPERATING_CONSTRAINTS.md` §12, within the hour of writing it;
- the recognised content sits behind `crop_url`, pointing at an **external service**
  (`vibe.cloud-ip.cc`), not at anything on disk. The markdown beside each document is the only
  local rendering, and it carries no geometry.

So: **no paragraph in that corpus has a bounding box today, and the text and the geometry live
in two places neither of which is joined to the other.** Producing paragraph granularity means
segmenting, associating text with geometry, and deciding what to do about a remote dependency
for the content — that is a task with a design in it, not a migration.

A later task that reads "carry the corpus into PostgreSQL at paragraph granularity" and plans a
load will lose a session discovering this. That is the shape of the stale premises that have
cost this programme a session each, which is why it is here before the task exists.

Check: `python3 -c "import json;d=json.load(open('.local/norms/corpus/MANIFEST.json'));print(len(d['documents']))"`
and the key set of `blocks['blocks'][0]` in any document's `blocks.json`.

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

### D-12 — a refused model-proxy credential is pinned retryable

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

Dispatched to `W16-ERR`, wave 16.

Check: `sed -n '222,226p' src/auditmanager/analysis/text/proxy.py`, against
`codes.dependency_unavailable.retryable` in `contracts/domain/v1/error-codes.json`.

### D-13 — a deployment fault answers as the caller's validation error

`StorageBucketMissingError` (`src/auditmanager/storage/errors.py:112`) inherits
`StorageConfigurationError`, whose `code = "validation_failed"` (line 107). A missing bucket
is the **deployment's** fault: the caller sent nothing wrong and can do nothing about it, and
`validation_failed` says the opposite in both its status and its summary.

Smaller than D-12 — it does not mislead an automated client about retrying — but it is on
criterion 10's surface and it is a one-line change if a code fits.

**Whether one fits is the open part.** Dispatched to `W16-ERR` with an explicit instruction to
stop at the boundary and report if none of the 21 does, rather than force a bad fit to close a
row. A 22nd code is an owner decision.

Check: `sed -n '99,125p' src/auditmanager/storage/errors.py` against the catalog summaries.

### D-14 — `PROTOTYPE_PROFILE.md` §9 carried a duplicated, truncated bullet — **CLOSED**

Line 261 was the first half of line 262, cut off mid-sentence at *"reported as"* — two
bullets, one incomplete, in the list that defines what the learning gate measures. Closed by
the integrator at this commit; the complete bullet is the one that survived.

Reported by a reviewing session rather than found by a reader of the document, which is the
part worth keeping: §9 is quoted into briefs and nobody quoting it had opened it.

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
