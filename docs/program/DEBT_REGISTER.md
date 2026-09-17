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
