# Debt register

Written 2026-09-17 by the integrator, revised the same day. **Measured against the tree at `e6eae1e`, not compiled
from closure records** — `W4_CLOSURE.md` §3 records a register that had been entirely obsolete
while still reading as the list of what was open, and this file exists to not become that.

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

### D-2 — `verify_version` compares two declarations and never hashes bytes

Found by `W11-RD`, verified by me at `ingest/reconciliation.py:203-232`. It calls
`self._store.inspect(...)`, which is a `head_object` returning **recorded metadata**, and
compares that against the manifest. A replacement that leaves the metadata and length intact
is therefore reported **sound** by reconciliation while the read path — repaired in wave 11 —
refuses it. `W11-RD` measured this on real MinIO rather than reading it off the source.

The docstring's second sentence is accurate about what the code does. **The first sentence,
"Prove one published version is still readable", is not** — it proves neither readability nor
byte integrity. Same class as the comments wave 11 repaired: a promise stronger than the code.

Not simply a bug to fix: `reconciliation.py`'s own docstring makes "never lists, never reads
bytes" a deliberate property, so changing it is a design call and is written up as one in the
wave-12 brief.

Check: read the method; or `grep -n "def inspect" src/auditmanager/storage/s3.py` and see
what it returns.

### D-3 — `_record`'s `cost_basis` default is a defaulted provenance field

`analysis/text/stage.py`: `cost_basis: str = "estimated"`. A forgetful call site would
silently record a provenance it never established. **Latent, not live** — one call site
exists and passes it explicitly. Flagged by `W11-FIX`, which correctly declined to change
behaviour with no defect behind it.

Check: `grep -n "_record(" src/auditmanager/analysis/text/stage.py`.

### D-4 — an empty digest reaches an operator-facing envelope

Against an unstamped object, `inspect` yields `sha256=""` and `verify_version` emits
`actual_sha256=""`. Wave 11 made that object unreadable through `read(verify=True)`, so the
reachable path narrowed, but the envelope can still carry an empty string where a digest is
expected. Found by `W11-RD`.

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

### D-6 — the contract has no security scheme at all, and the alpha now needs one

The owner has ruled that this is ultimately a **public application requiring HTTPS and
authorization tokens**. Measured against the frozen contract at `2593862`:

- `contracts/api/v1/openapi.json` declares **no `securitySchemes`**, no top-level `security`,
  and **zero** operations carrying their own — the twelve operations are unauthenticated by
  construction;
- `authentication_required` is in the catalog and is **raised nowhere**;
- `permission_denied` **is raised** — corrected below.

So the transport was never given a way to raise `authentication_required`. Adding tokens is
therefore a **contract change** — a reseal of the document and of `web/FRONTEND_LOCK.json`,
not a lane decision.

**Correction, 2026-09-17.** This row first said both codes were "used nowhere in `src/`". That
was wrong for `permission_denied`, and wrong for a reason worth keeping: I grepped for the enum
constant `PERMISSION_DENIED`, and `storage/errors.py:153` carries the **string**
`code = "permission_denied"` on a `ClassVar`. Found by `pdf-analysis-d9` checking the row
against the tree. **A row that says "measured" is only as good as the query behind it**, and
mine matched one of the two spellings the codebase uses.

Note what this is *not*: the current alpha draft's §11 excludes "no in-app authorization" and
its `R-3` proposes **one shared secret at the proxy**. A shared secret is a gate; a token is an
identity. They are different deliverables and only the second answers the owner's statement.

Check: the `python3 -c` one-liner over `openapi.json` in this row's history, and
`grep -rn "AUTHENTICATION_REQUIRED\|PERMISSION_DENIED" src/`.

### D-7 — one code, two situations, and they cannot be told apart in the envelope

**This collision exists today, before any token work.** It is the thing to settle at the
reseal, and the settlement is the owner's because it touches the catalog.

The catalog defines `permission_denied` as: *"The **authenticated subject** is not permitted to
perform this operation on this resource. Authorization is decided server-side."*

`StoragePermissionDeniedError` raises it for *"the configured application credentials were
refused by the store"* — our own credentials against the private bucket. **There is no
authenticated subject in that scenario at all.** So the API meaning is the one the contract's
own text describes, and the storage use is the borrowed one.

**They are indistinguishable in the envelope by construction.** Both declare exactly
`aggregate_type` and `required_capability`; neither carries a discriminator. So once API
authorization also raises it, one 403 means either *"you lack rights"* — the caller's problem —
or *"our S3 credential was rejected"*, which is an operator being paged. **Nothing in the
response separates them.**

That is the shape wave 3 had to undo: `terminal_reason` flattened every failure to
`analysis_failed`, and an operator could not tell a model that answered badly from a provider
that never answered. `W11-RD` refused the same flattening again and said so.

**Recommendation, and it is a recommendation.** At the reseal, `permission_denied` keeps the
contract's meaning — the caller. The storage case needs its own code: it is not retryable and
not a degraded service (which is why `dependency_unavailable` was avoided, per that class's own
docstring), and it is not about a subject's rights. **This is a second, independent candidate
for the 21st code**, alongside "usable output over a strict subset of the input" — and unlike
`checksum_mismatch` (D-1.6), which turned out to be a class name rather than a missing code,
this is a real gap.

If no code is added, the storage case must at least become distinguishable in the envelope —
and it cannot, on the declared keys, which is itself the argument that a code is the answer.

Check: the `summary` of `permission_denied` in `contracts/domain/v1/error-codes.json`, against
the docstring of `StoragePermissionDeniedError`.

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

## 3. `origin/main` has been five waves behind, and that is a decision not a backlog

`main` is at `8f418e9`, carrying the `beaa7f7` certification. `dev` is at `5c84f43`.

The integrator has recommended advancing it after each of waves 7, 8, 9 and 10, when `src/`
was byte-identical to a certified commit and the only question was whether `main` should
carry the evidence as well as the behaviour. That window closed when wave 11 changed `src/`, and **it has now reopened**:
`W12-CERT` certified `e6eae1e` on 2026-09-17, so the condition this section named — "a
certification exists for a commit on this line" — **is met**.

`main` can advance to `e6eae1e` or later, carrying certified behaviour for the first time in
six waves. It is the owner's decision and the integrator does not take it. The one thing a
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
