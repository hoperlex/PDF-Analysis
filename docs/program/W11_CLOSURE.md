# Wave 11 closure: the repairs, and a quarantine that hid 212 tests

Written 2026-09-16 by the integrator. Convergence at `05b2bfb`, base `5d14921`.
**`make gate` → `GATE OK`**: battery **1492 passed** / 5 skipped / **163 subtests**, foundation
35, frontend 289, whitespace clean.

1264 → 1492. **Only 16 of those 228 are new tests.** The other 212 were already in the
repository and are the subject of §1.

Three streams: two dispatched repairs, one governance item taken by the integrator.

## 1. The quarantine was by directory and should have been by file

`PROTOTYPE_PROFILE.md` §6.3 quarantines **CP-00 ratification mechanics**. The rule was right.
Its implementation excluded the whole `tests/contract` directory — sweeping up five
subdirectories of contract tests over **live** rules.

`W10-API` found what that cost: those tests exercise five of the six forbidden shapes in the
error screen and both identifier catalogs — rules its sweep reported as unguarded, *because
the gate does not run them*. They are findable by grep and they read as evidence. **A
reviewer asking "is this rule covered?" was told yes by tests that protect nothing.** It was
the single largest systematic reason that surface yielded 36 unreddenable rules from 77.

Measured before narrowing, in a linked worktree:

| Path | Result |
|---|---|
| the five subdirectories | **212 passed, 2.5 s total**, no missing dependency |
| `test_cp00_candidate.py` | 33 failed, 126 errors |
| `test_cp00_final_state.py` | 3 failed |
| `test_validate_bootstrap.py` | 28 failed |

The three files are genuinely the CP-00 and clean-clone-bootstrap material §6.3 means.
`W6-CERT`'s finding that `tests/contract` cannot run from a linked worktree applies to
*those*; the five subdirectories run green in one, which is where the figures were taken.

The ignore now names the files. `OPERATING_CONSTRAINTS.md` §11 records the general form:
**an exclusion written as a path is a claim about everything that will ever live under it,
and nothing re-checks it when something new is added there.**

## 2. `W11-RD` — the read path now verifies what the manifest promised

It took **both** halves of the choice the brief offered, and argued why they are not
symmetric:

- `read_source_bytes` hashes the returned bytes against `entry.sha256`. **This is the
  load-bearing half.** `S3BlobStore` can only ever prove an object agrees with *its own*
  metadata, which is self-consistency; an object replaced out of band together with its
  metadata satisfies that perfectly and is still the wrong document. The manifest entry is
  the only digest independent of the object.
- `S3BlobStore.read(verify=True)` refuses an object with no recorded digest, which closes the
  hole for callers that have no manifest to compare against.

Two causes, two codes, **no new error code** — the 21st is owner-blocked, and
`BlobMetadataInvalidError` already meant "a declaration is absent; nothing was compared to
bytes". Refusing to flatten them is the same discipline wave 3 applied to `analysis_failed`.

**It found the mirror defect and left it unrepaired.** `Reconciler.verify_version` never
hashes bytes — it compares two *declarations*. So a replacement preserving metadata and
length is reported sound by reconciliation while the read path now refuses it: **the roles
exactly reversed from my brief's framing.** Measured on real MinIO rather than read off the
source. `reconciliation.py` is outside its paths and the docstring's "never lists, never reads
bytes" makes the change a design call for that tree's owner.

## 3. `W11-FIX` — four repairs, three of them text

Two comments that said `details` values "are not screened" when they are; a docstring that
undercounted the screen; `cost_basis` present on the budget-overrun path and absent on the
success path; and a filename property nothing read.

The part worth keeping is that it **made the claims executable rather than merely correcting
them**: a test now asserts the screen has six shapes, in order, against a hand-written tuple,
that the docstring names every one, and that the existing cases reach exactly those six — so
a seventh added untested reddens, and an unreachable shape reddens.

**Three numbers for one tuple.** The tuple has six, the docstring said five, my wave-10 brief
said seven. That is the argument for the executable count, better than any sentence.

One observable change for an operator: a succeeded run's metrics now carry `cost_basis`, so
whether the cost figure is provider-reported or computed is legible on a normal run and not
only on one that blew its budget. The stored `model_call` row is unchanged.

## 4. The escalation, swept and answered

`W11-FIX` escalated that its own first guards were broken **in the silent direction**: they
scanned source text through `Path(__file__).resolve().parents[3]`, which under a mutation copy
reads the *pristine checkout* — green against a tree that still had the defect. It asked
whether wave 10's evidence was void.

**Swept, and it is not.** Of 31 new test files, 15 resolve from `__file__`, and **every one of
them reads an authority** — a migration, a frozen contract, `P02_LOCK.json`, the frontend's
column list. That is correct by design: an authority must be the real one, not a copy that
might be mutated. The blindness applies only to tests that scan the *module under test's*
source, and the only three doing that predate wave 10.

Recorded because the escalation was right to make and the answer is not obvious: the same
construct is correct for one purpose and void for another, and nothing in the code
distinguishes them.

## 5. A tenth stale premise, and two smaller ones

My brief said `ExportResult.filename`. **The class is `CsvExport`**; `grep -rn ExportResult`
returns nothing tree-wide. Two line numbers had drifted. `W11-RD` found a third: my
"check `verify_version` first, the repair may be smaller than it looks" was wrong — it
compares declarations, and delegating to it would have inherited the mirror gap in §2.

## 6. Version fixation, and the debt this wave opens

`origin/dev` advances to the wave-11 merge. **`origin/main` stays at `8f418e9`.**

**`src/` changed for the first time since `c0d7daf`.** `W6-CERT`'s certification stops
describing this tree as of this merge. Seven files, 115 insertions; all additive except one —
`CsvExport.filename` was a public attribute on an exported class and is gone.

Wave 12 is the re-certification. The `W6-CERT` brief is reusable; only its base commit and
its diff table change.

## 7. Still owner-blocked

- **`OD-18`** — experts with committed slots; `P4-BHV-01` waits on this alone.
- **`OD-17`** — the next corpus shape.
- **The 21st error code** — `W11-RD` deliberately avoided needing it.
- **Whether `origin/main` advances.**
