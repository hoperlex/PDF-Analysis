# Wave 2 closure: what shipped, what was found, and what my own briefs got wrong

Written 2026-09-15 by the integrator. Convergence at `ecfdadf`; the gate is green:
**783 passed, 5 skipped, 116 subtests** under the canonical battery, `make foundation` 35
passed, frontend 289 passed, `git diff --check` clean.

Three implementation sessions in parallel over disjoint path sets, then one independent
convergence QA. Twenty-one commits merged, sixty-one mutation exercises across the four
sessions, **zero sessions returned for remediation** and one returned for a repair it had
caused itself.

## 1. What shipped

| Session | Result | Elapsed |
|---|---|---|
| `W2-RUN` | a bounded in-process retry for `dependency_unavailable`, in the executor rather than in each caller | 21 min |
| `W2-PROV` | `truncated` as a first-class `model_call` status with two invariants giving it content; the provider's output-token figure into the metrics and the ledger; migration `0005` | 31 min |
| `W2-API` | tests that can tell the query surface from a passthrough, plus one live ordering defect | 27 min + 13 min repair |
| `W2-QA` | the composition verified, the seam explained rather than assumed | 39 min |

**All four reported that `HEAD` matched the dispatched base on arrival.** That is the first
practical confirmation that publishing `origin/main` closed the worktree-seeding defect
`GATE_B1_CLOSURE.md` §6 records — every one of the nineteen sessions before them arrived on
`43a84d9` and had to detect it.

## 2. My briefs were wrong twice, and both times for the same reason

Recorded because the failure mode is systemic, not clerical.

- **`W2-API`'s premise was stale.** The brief said the four query parameters were declared
  and unimplemented. At the base all four were implemented end to end. `cursor` appears 28
  times and `limit` 16 in the routers and schemas at `c509950`; the shipped adapter filters.
  A seam repair had closed the gap and `GATE_B2_CLOSURE.md` §5.3 and the API README were
  never updated.
- **`W2-PROV`'s premise was wrong in direction.** The brief said the executor mapped
  `truncated` onto `failed`. It mapped it onto **`succeeded`** — so the ledger PC-02 will
  cite had been filing truncated answers as clean successes, which is worse. And
  `0003_open_items` had already widened the CHECK to admit the value; the column could hold
  it and never did.

Both briefs were written from closure records rather than from the tree. **A brief written
from a record inherits that record's drift.** The commit that most recently reconciled the
closure records against the tree is `80ff9d8`, titled for exactly that job, and it missed
both lines. The cheap defence is the one both sessions applied unprompted: check the premise
against the tree before building on it, and report when it does not hold.

## 3. Defects found

**Closed in the wave.**

- The API suite's `conftest` reversed `B1`'s rows to force newest-first. `B1`'s query had
  since become `ORDER BY created_at DESC`, so the compensation inverted the listing to
  oldest-first — the opposite of the contract. Nothing caught it because no test asserted an
  order. (`W2-API`)
- A paging test asserted a property of a small table: it walked at most 400 rows and
  compared against a request capped at 200. It failed against the shared database's 495
  accumulated projects **on its own**, which makes it a test defect rather than
  `OPERATING_CONSTRAINTS.md` §6 interference. Repaired by deriving the bound from the
  measured population and taking the expected sequence from the rows. (`W2-API`)

**Open, unrepaired, named.**

- **D1 — the API page order and the CSV row order diverge, and a docstring denies it.**
  `src/auditmanager/api/routers/findings.py:78` claims `_finding_sort_key` uses "the same key
  family the CSV sorts on … so a page boundary and a CSV row order cannot disagree about what
  'next' means". They disagree: `findings/queries.py:42` orders by `o.finding_observation_id`
  alone, while `exports/query.py:99` orders by `f.finding_uid COLLATE "C"`,
  `o.finding_observation_id COLLATE "C"`, `e.evidence_ordinal`. The cursor key is a pair; the
  row order is one key. The two ULIDs are allocated independently, so within a millisecond
  their random tails disagree — **31 of 416 runs measured on one instance**, with collation
  ruled out as the cause. Owned jointly by the `api` and `findings` trees. It predates wave 2
  (both files date to `3ec0106`) and is **not a blocker**: `paginate` locates the key rather
  than comparing, so no walk skips or repeats. `P02_SEAMS.md` §6 makes the CSV order
  canonical, so the fix direction is known; it is left for its own session because aligning
  it touches two trees and wants a guard proving the two orders agree, not just that each is
  stable.
- **D2 — the property that makes the walk safe was unasserted.** Because `paginate` locates
  rather than compares, the sequence need not be sorted by the cursor key, but the key must be
  *unique* within it or a resumption lands on the wrong row. `W2-QA` added the guard.
- **D3 — a stale figure in `B-III`'s own evidence note.** `journey.py` records CSV 4497
  bytes; `GATE_B2_CLOSURE.md` §1, `artifacts/checkpoints/PC-01/report.json` item 7 and the
  PC-01 manual runbook all say 4251, and 4251 is what is measured today. `W2-QA` annotated it
  rather than overwriting, so the disagreement stays visible, and pinned the current figures
  in a test so the next reader gets a failure instead of a comment.
- **D4 — `OD-03` across attempts is only partially observable.** No code path charges the
  meter and *then* fails retryably, so at most one call is charged across attempts. The
  shared-meter property is real and was proved with a pre-spent meter; the scenario the
  docstring describes is not reachable from a live failure mode today. Worth knowing before
  someone adds a retryable post-charge failure.

## 4. Two mutations that failed to fail, and what came of them

The discipline earns its keep at the margin, not in the table of successes.

- `W2-API`'s **M17** — a cursor whose key is absent restarting the listing instead of
  returning an empty page — reddened nothing, because every test walked keys that were
  present. That is a coverage hole, not a dud: a cursor minted on one filtered listing carries
  a key a differently filtered listing does not contain, and `paginate`'s own docstring already
  promised an empty page. A test was added and M17 then reddened. **The suite gained a test
  from a mutation that could not fail.**
- `W2-PROV` caught a vacuity in its own work: an explicit `continue` for truncated calls that
  no mutation could redden, because the conditions below already excluded it. It deleted the
  branch and let the database CHECK be the guard.

## 5. Three operating rules, learned at cost, now written down

Added to `docs/program/dispatch/OPERATING_CONSTRAINTS.md` as §§7–9.

- **There is one battery command and nobody had named it.** Three sessions invented three and
  reported 708, 718 and 729 — none comparable. The canonical form is
  `.venv/bin/pytest tests --ignore=tests/contract --ignore=tests/checkpoint`, which keeps
  covering a directory a later wave adds where a positive list silently stops.
- **Commit before running the battery.** `P1-QA-00`'s autouse guard compares the tracked
  checkout before and after the foundation suite and fires on your own mid-run edits.
  `W2-PROV` lost two runs that way.
- **§6 covers residue, not population.** It tells you to file a cross-suite failure as
  interference; that is right and narrower than it looks. The database is long-lived and
  append-only, so rows accumulate across days. Run your suite alone against the same database:
  if it still fails, §6 does not cover it.

## 6. What this wave does not claim

It does not re-certify PC-01, whose record stays bound to `6d3c0f3`, and it does not shorten
the path to PC-02. That path is owner-blocked on `OD-18` (3–5 named experts with committed
slots) and `OD-17` (the shape of the next corpus — the precision evidence is saturated, so
what is needed is documents of a different kind, not more of the same). The 21st error code
remains an owner decision; `W2-PROV` fenced it off rather than pre-empting it, so a
`truncated` row cannot now conflate a call status with a catalog code one INSERT at a time.
