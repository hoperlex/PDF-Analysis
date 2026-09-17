# Debt register

Written 2026-09-17 by the integrator. **Measured against the tree at `5c84f43`, not compiled
from closure records** — `W4_CLOSURE.md` §3 records a register that had been entirely obsolete
while still reading as the list of what was open, and this file exists to not become that.

Every row names how to check it. A row nobody can re-measure is a row that will rot.

## 1. Open, and mine to schedule

### D-1 — PC-01's certification no longer describes the tree

`W6-CERT` certified `c0d7daf`. Since then `src/` has moved by **126 lines across 8 files**,
and four of those carry behaviour rather than text:

| File | Non-comment lines | What moved |
|---|---|---|
| `exports/service.py` | ~18 | `CsvExport.filename` and `_FILENAME_TEMPLATE` removed — **a public attribute on an exported class**, the one source-compatible break |
| `ingest/service.py` | ~11 | `read_source_bytes` now hashes returned bytes against the manifest digest |
| `storage/s3.py` | ~11 | `read(verify=True)` refuses an object with no recorded digest |
| `analysis/text/stage.py` | ~3 | `cost_basis` added to the success path's metrics |
| `shared/errors/envelope.py` | ~4 | docstring restructured to name all six shapes |
| `multipart.py`, `projects.py`, `executor.py` | 0 | comments only |

Check: `git diff --stat c0d7daf..HEAD -- src/ db/`.

**Scheduled as wave 12 stage B.** It must follow any further `src/` repair, or the
certification is stale before it is written.

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

## 3. `origin/main` has been five waves behind, and that is a decision not a backlog

`main` is at `8f418e9`, carrying the `beaa7f7` certification. `dev` is at `5c84f43`.

The integrator has recommended advancing it after each of waves 7, 8, 9 and 10, when `src/`
was byte-identical to a certified commit and the only question was whether `main` should
carry the evidence as well as the behaviour. **That window has now closed**: D-1 means there
is no recent commit whose behaviour is certified, so `main` should not advance until wave 12
stage B lands.

This is recorded so the pending recommendation is not mistaken for an outstanding task. The
next time it is worth asking is when a certification exists for a commit on this line.

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
