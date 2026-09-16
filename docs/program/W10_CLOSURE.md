# Wave 10 closure: what a twice-certified checkpoint could not tell you

Written 2026-09-16 by the integrator. Convergence at `adf4bd1`, base `e08da85`.
**`make gate` → `GATE OK`**: foundation 35, battery **1264 passed** / 5 skipped / 116
subtests, frontend 289, whitespace clean.

816 → 1264. **448 tests, and 448 is exactly the sum of the five streams' additions** — no
overlap, nothing lost in convergence. **Zero lines changed in `src/`, `db/`, `contracts/` or
`web/`.** Every stream respected the rule that a session may not repair the tree it measures.

## 1. The premise, and whether it held

PC-01 has been certified twice. Both passes established that each *criterion* can fail.
Neither established that each *rule* can.

**Roughly 300 rules were mutated across five disjoint trees. About 157 could not be told
from a deleted rule.** The wave plan said the yield would drop from waves 8 and 9 because
those went where the closure records already pointed. It did not drop.

| Stream | Tree | Mutated | Unreddenable | Guarded |
|---|---|---|---|---|
| `W10-ANL` | `analysis/**` | ~150 | 94 | 234 tests |
| `W10-API` | `api/`, `shared/`, `bootstrap/` | 77 | 36 | 120 tests |
| `W10-RUN` | `runs/`, `ingest/`, migrations | ~30 | 15 | 45 tests |
| `W10-FND` | `findings/`, `decisions/`, `exports/` | 37 | 13 | 33 tests |
| integrator | `storage/`, `documents/` | 9 | 2 | 16 tests |

## 2. The single structural reason, found by `W10-API`

**`tests/contract` covers several of the rules this wave reports as unguarded, and that is
worth nothing.** `make gate` ignores it and `PROTOTYPE_PROFILE.md` §6.3 quarantines it as
red before any wave starts. `test_error_kernel.py` exercises five of the six forbidden
shapes; `test_identifier_catalog.py` covers `is_valid_ulid` and the identifier patterns.

**Anyone grepping for coverage finds it and is wrong.** That is the largest systematic
reason this surface yielded 36 from 77, and it is not a defect in any one test — it is a
quarantined suite that still reads as evidence.

## 3. The findings that matter most

**The detail-value screen — the fix `B6` paid for — had no test at all.** `UnsafeDetailValue`
appears **zero** times in the whole of `tests/`, quarantined suites included. Verified by me.
That screen exists because `B6` found a caller's property named `/etc/passwd` echoed back
inside `details.field`. Neutering the loop left 816 passing.

**Every one of the seven refusing branches of the multipart reader was unguarded.** The
module calls itself a security surface; the three tests that mention it send only well-formed
bodies.

**The CSV column order is unguarded, on criterion 7's surface.** Verified by me:
`test_csv_contract.py:82` compares the header against `list(COLUMNS)` — both sides move — and
line 69 builds every row dict by zipping the file's *own* header, so the row keys follow the
mutation too. Swapping two of `OD-11`'s frozen columns left all 302 tests green. The same
file pins `BOM` as a literal with a comment saying that phrasing once let the BOM be deleted:
**the lesson was applied to one constant and not the one beside it.**

**`OD-03`'s USD 1.00 ceiling — an owner decision — could be changed to 99.00 with everything
green.**

**Three database trigger arms had no write attempt anywhere in the repository.** The
SQLSTATEs are well guarded; per-table, per-arm reachability is not, and `test_schema_shape.py`
structurally cannot see it — it reads `pg_trigger` for the function name and never asks what
the trigger fires on.

**Wave 9's failure mode is still in the tree, twice.** A test named
`test_the_profile_is_resolved_by_a_pinned_identity` feeds `resolve_profile` the module's own
constant and asserts the result is that constant — verified by me. And
`test_reconciliation_and_terminals.py:297` asserts `interrupted_reason == INTERRUPTED_REASON`,
imported from the module under test; changing the constant leaves 154 tests passing.

## 4. Product defects, routed and unrepaired

| # | Tree | Defect |
|---|---|---|
| 1 | `ingest/`, `storage/` | `read_source_bytes` holds `entry.sha256` and never compares it to what came back; `s3.read` re-hashes against the **object's own** metadata digest, and skips the check entirely when that metadata is absent. The read path can hand a reviewer the wrong document silently while reconciliation over the same row raises `storage_integrity_error`. **Verified by me.** Still not inducible through the twelve operations — it needs out-of-band replacement — so PC-01's accepted criterion-10 limit and both certifications stand |
| 2 | `api/routers/`, `api/schemas/` | two docstrings state that `details` values "are not screened the way `message` is". They are, since the `B6` fix. False **in the dangerous direction** |
| 3 | `shared/errors/` | the `envelope.py` docstring lists five forbidden shapes; there are six |
| 4 | `analysis/text/` | `cost_basis` is in the metrics on the budget-overrun path and absent on the success path — a `KeyError` for a consumer. Reads as the unfinished half of a repair its own comment describes |
| 5 | `exports/`, `api/routers/`, `web/` | three disagreeing CSV download names, one of which has no consumer anywhere |

Repairs are wave 11, deliberately. The rule from wave 5 §4: batching them keeps the
re-certification debt one wave wide.

## 5. Four defects in my own planning

**The mutation-copy recipe has been wrong since wave 3.** Every brief said to symlink
`contracts/`, `docs/`, `fixtures/`. `db/` and `tools/` are also resolved from the copy's
root, and without `tools/` four `p02_journey` tests fail against an **unmutated** copy. The
recipe did not merely miss coverage — **it manufactured reds**. Found independently by
`W10-FND` and `W10-RUN`; reproduced by me; now `make mutation-copy`, which proves the copy is
the tree that will be imported and refuses the old three-link shape.

**I then shipped a false affordance in the fix itself**, claiming `FULL=1` was the way to
mutate a migration. It is not: `tests/integration/db/conftest.py` derives the repository root
from *its own file* and runs alembic with that cwd, so no copy makes a migration mutable.
Corrected within the hour, and recorded because it is the same class the wave exists to find
— a facility that looks like it works, raises no error, and yields a no-op mutation
indistinguishable from a covered rule.

**My brief said "seven forbidden shapes" twice. There are six.**

**The five streams were less isolated than the plan claimed.** They shared one scratchpad
directory — `W10-RUN` wrote its `gate-baseline.log` over `W10-API`'s, which read its arrival
gate as "3 failed, 813 passed" from another lane entirely — and `ps` showed their pytest
processes in one container. "Disjoint trees on their own instances" was true of the database
and the bucket and false of everything else.

## 6. What the streams reported about themselves

Every stream reported a fault of its own that nothing would have caught: a shared mutation
copy producing a false green, discarded and re-run; three miscounted summaries corrected in
separate commits; two mutation streams corrupting each other through one MinIO bucket,
discarded and re-taken serially; an out-of-memory kill recorded as a red, and a 931-second
run recorded as a red, both re-run isolated and re-judged — *"where a test derives its input
from the constant it tests, raising the constant is not a red test, it is an unbounded
allocation."* That is wave 9's lesson in a third form.

Four streams independently wrote mutations that did not mutate, including mine. Each caught
it by re-reading the mutated line for meaning after the textual check passed.

**A stream that reports none of this is not necessarily cleaner.**

## 7. Version fixation

`origin/dev` advances to the wave-10 merge. **`origin/main` stays at `8f418e9`.**

`src/` and `db/` are untouched, so `W6-CERT`'s certification of `c0d7daf` still describes
this tree's behaviour exactly. `main` can advance whenever the owner chooses; pending five
waves now, blocking nothing.

## 8. Still owner-blocked

- **`OD-18`** — three to five named experts with committed slots. `P4-BHV-01` waits on this
  alone.
- **`OD-17`** — the next corpus shape; PC-02's precision evidence is saturated.
- **The 21st error code.**
- **Whether `origin/main` advances** to `c0d7daf` or later.
