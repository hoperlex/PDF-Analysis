# Wave 12 closure: PC-01 holds again, and the frontend is the exception

Written 2026-09-17 by the integrator. Convergence at the wave-12 merge, base `3ebe34d`.
**`make gate` → `GATE OK`**: battery **1505 passed / 5 skipped / 167 subtests**, frontend
**440 passed**, foundation 35, whitespace clean.

Battery 1492 → 1505. Frontend **289 → 440**.

Two stages: three parallel streams, then a certification. `DEBT_REGISTER.md` D-1 is closed.

## 1. The verdict

**`W12-CERT`: PC-01 holds at `e6eae1e`, with one named exception.** Ten criteria, each shown
able to fail — twelve mutations against an isolate whose liveness was proved by a control that
reddened 47 of 49 tests, plus a migration downgrade, unset variables, stopped containers, and
an out-of-band replacement of a published object. Live run through the proxy: **3 of 3 seeded,
0 of 6 controls**, USD 0.0387 read from the `model_call` row rather than from a print.

**Both accepted limits re-established, and one is now narrower in the right direction.** The
checksum limit still cannot be induced through the twelve operations — the session expanded
every `$ref` and found 13 distinct input names, none digest-shaped, then injected three and
got `validation_failed` each time. But **the same failure arriving from outside the twelve is
now detected**: a corrupted object answers 422 and 200 again after restore. That is what waves
11 and 12 bought.

## 2. The exception, and it is about what a user sees

**18% of `web/src` is reached by no test** — 34 of 110 modules, 1352 of 7604 lines, measured
by `W12-WEB` and independently again by `W12-CERT`.

Criterion 4 requires the **UI** to distinguish run states and provider mode. `terminal_reason`
reaches a user in exactly one line, `run-progress.tsx:112`, inside an unreached module. Ten
mutations in that region were **ten survivors**, including "`run-progress` stops rendering
`terminal_reason`" with 440 frontend tests green.

**The rules are guarded. The rendering is not.** Recorded as `DEBT_REGISTER.md` D-1.5 and it
is the strongest candidate for the next wave; seven of the ten are ordinary components the
existing harness can reach.

## 3. The frontend had never been swept, and the harness was the hard part

`W12-WEB` ran **257 mutations**; 58 of 183 survived the first sweep. `shared/api/transport.ts`
was **7 for 7** — writes no longer requiring an idempotency key, a missing path parameter
becoming the empty string, no percent-encoding, all green. Four modules were read by **no test
at all**.

The part worth carrying is the harness. A path-alias copy is **not sufficient**: the web suite
reaches `web/src` by two routes, and the second reads source as **text**, resolving its root
from its own `import.meta.url`. An alias-only harness leaves that route scanning the pristine
tree — the failure the brief warned about, which the session hit while building the obvious
thing first. Its provenance evidence was read out of a **V8 stack frame** rather than declared
by the test.

It also caught **its own invalid mutation**: one of 64 re-runs survived because the mutation
removed an outer length prefix and left an inner one, so no two intents could collide. Filed
as *not a valid mutation* and rewritten.

## 4. `W12-RCN` corrected the premise its own brief rested on

My brief framed the reconciliation repair as a **design call**, because
`reconciliation.py` makes *"never lists, never reads bytes"* a deliberate property.

Verified by me: that is the docstring of **`_object_exists`**, a private helper.
`verify_version` does not call it, walks **one** manifest rather than sweeping, and **has no
caller in `src/` or `tools/` at all.** I attributed a helper's docstring to the method being
changed. That did not merely mislead — **it manufactured a design dilemma that did not
exist.**

The session did not inherit it. It checked, corrected it, and argued its choice on independent
grounds: the invariant `service.py:204` states, which wave 11 spent a session making true.
Correcting the promise instead of the code would have made that false by hand, for the exact
fault the method exists to find. **That argument survives the brief being wrong**, which is
why the repair stands.

Cost measured on live MinIO, not estimated: 2.08 → 4.11 ms on the AR baseline, 2.23 → 50.10 ms
on a 25 MiB object. Proportional to bytes rather than rows.

## 5. Three defects in my own documents, all found by the sessions reading them

- **`W12-PLAN.md` §1 contradicted the dispatch it planned.** It read "why this wave is
  sequential, and parallel would be wrong" and listed one stage-A session; three were
  dispatched. I had written the correction **in a commit message** and never brought it to the
  document. That is the same defect this programme keeps repairing in other people's comments.
  Found by `W12-DEC` while checking its brief against the tree.
- **`cost_basis` is invisible to the frontend.** My brief told `W12-WEB` that wave 11 added it;
  it appears **zero** times in the API contract, in the web copy of it, and in `web/src`. I
  also asked a `csv-columns.ts` question already answered twice, once by `W10-FND` in wave 10.
- **The debt register was stale within a day.** Its D-1 row said "126 lines across 8 files",
  measured at `5c84f43` before stage A moved `reconciliation.py`; at `e6eae1e` it is 9 files
  and 232 insertions. The header named the commit and that was not enough: **a reader takes a
  figure from a row, not from a header.** Every figure now carries its commit beside it.

## 6. The programme has been naming a code that does not exist

**`checksum_mismatch` is not in the frozen catalog.** Twenty codes, and that is not one of
them; `ChecksumMismatchError` is a Python class carrying `storage_integrity_error`. Yet "the
`checksum_mismatch` limit" appears in PC-01's accepted report, in the criterion-10 limits of
three certifications, in closures, and in my briefs.

Found by `W12-CERT` because it established the limit instead of inheriting it — **three passes
had re-proved that limit without asking what the name referred to.** Nothing is broken; the
limit is real. But a limit named after a non-existent code is how the 21st-code question gets
asked about the wrong thing. `DEBT_REGISTER.md` D-1.6.

## 7. Version fixation, and a decision that is now live

`origin/dev` advances to the wave-12 merge.

**`DEBT_REGISTER.md` §3's condition is met.** `main` has been six waves behind; it can now
advance to `e6eae1e` or later, carrying certified behaviour for the first time since
`8f418e9`. It is the owner's decision. The one thing worth weighing: **the certification holds
with a named exception, and that exception is about what a user sees rather than what the
system does.**

## 8. Still owner-blocked

- **`OD-18`** — experts with committed slots; `P4-BHV-01` waits on this alone.
- **`OD-17`** — the next corpus shape.
- **The 21st error code** — and see §6 before asking the question.
- **Whether `origin/main` advances**, now unblocked and live.
