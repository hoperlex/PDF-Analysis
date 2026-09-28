# W46-SPEND — a spend nobody measured stops reading as measured, and three guards that can fail

**task_id:** `W46-SPEND` · **wave:** 46, sub-stage B · **lane:** `gate-w46a`
**worktree:** `/root/w46seal` · **branch:** `agent/w46-spend`, based on `2ffca8c`
**depends_on:** `W46-SEAL`, `W46-DASH`, `W46-JUDGE-A`, all merged at `2ffca8c`

Read `docs/program/reviews/W46-JUDGE-A.md` sections 3 and 6 before anything else. Its
findings are your premises. Where this brief and the report disagree, the report was measured
and this brief was written from it, so say which one is wrong and why.

## S1 — `F-1`: absent spend is absent (the reseal)

On a deployment with **no** `model_call` rows, `GET /dashboard` answers
`"spend": {"model_call_count":0,"cost_micros":0,"cost_basis":"measured"}`. The cause is at
`src/auditmanager/dashboard/repository.py:171-175`, where
`basis="measured" if int(unmeasured) == 0`, and `unmeasured` is trivially 0 over an empty
table. The per-run rule it claims to lift, `RunRepository.cost()`
(`src/auditmanager/runs/repository.py:406-420`), returns `None` when `calls == 0` and says why
in its docstring. The aggregate dropped that branch.

**The shape, decided by the integrator:** `RunActivity.spend` is removed from `required` and
is absent when the deployment has no `model_call` rows. When it is present, all three fields
stay required. This mirrors `RunStatus`, whose cost fields are absent for a run that made no
call. The record, the view and the serializer carry absence all the way to the wire; no layer
may turn it back into zeros.

**The surface does not move: still 17 paths / 20 operations / 61 schemas, error catalog 22,
migration head `0011`.** If your change moves any of those, you have done more than asked.
**No migration.** If you conclude one is needed, stop and report.

**A reseal is one commit and five documents:** `contracts/api/v1/openapi.json`, the mirror
`web/openapi/openapi.json`, `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json` with its
digests recomputed, and every pin the change moves. `D-102` and `D-105` list the pin families.
Name each pin you checked and whether it moved. **Also correct the lock's `commit_note`.**
The judge found it false: it says the pins moved *before* the reseal commit, when they moved
*in* `d7ac848`.

## S2 — `F-2`: gate red #5, restated as the judge ruled

`tests/contract/domain_p02/test_openapi_document.py::test_every_operation_can_report_not_found_or_validation`
is the tree's one known red on `2ffca8c`. **Integrator's ruling: the rule is wrong and the
operation is right. Repair it in the test, with no reseal for this.** Four parts:

1. Derive *takes caller input* from the document: a path parameter, a query parameter, a
   header other than `X-Correlation-Id`, or a request body. Do not use a list of names.
2. Every operation that takes input declares at least one of `404`/`409`/`422`.
3. **Two-sided:** an operation that takes no input declares **none** of them.
4. A literal pin: the input-less set is exactly `{"getDashboardSummary"}`. It belongs to the
   `D-105` family, so say so in its docstring.

`500` stays required for every operation. **Show the rule failing in both directions,** once
with `422` added to `getDashboardSummary` and once with an input-taking operation's client-fault
codes removed, both in a scratch copy.

## S3 — `F-5a`: absent-is-not-empty, observed on rows

The judge changed `_filled` to drop zero-count members and to append the unclassified bucket
only when it is non-zero. **Tests went 609 before, 609 after.** No existing test observes a
response row. Add one that drives the operation over a fresh database. It asserts all fourteen
sections present at `0`, the unclassified bucket present at `0`, all four verdicts present,
a project with no documents present at `0`, `spend` absent with no calls, and `spend` present
once one call exists. **Show it failing under the judge's mutation** (quoted in its report,
section 3) and under a mutation that restores zeros for absent spend.

## S4 — `F-5c`: the historical-section control gets back the half it lost

`ff686b1` made the control structural and dropped the assertion that the live section still
makes a claim. Now one heading matching `historical record`, placed too early, removes
`CURRENT_STATE.md`'s live claims from the scan, and the control stays green. **Repair:**
assert that the scanned `CURRENT_STATE.md` yields at least one `TAGGED_TIP_CLAIM` match. This
is the same move `test_the_bff_handler_still_makes_a_claim_this_guard_can_read` makes. Show it
failing under the judge's mutation (report, section 6).

**If today's live section makes no claim the regex can read, do not edit `CURRENT_STATE.md`.**
It is the integrator's. Report the sentence the guard needs.

## allowed_paths

```
contracts/api/v1/openapi.json · web/openapi/** · web/FRONTEND_LOCK.json
web/src/shared/api/generated/** · src/auditmanager/** · tests/** (NOT tests/e2e/**)
docs/program/W46-SPEND.md
```

## forbidden_hotspots

`web/src/**` except `shared/api/generated/**`, `web/tests/**` and `tests/e2e/**` belong to
`W46-WIRE`, live in `/root/w46dash`. Also forbidden: `contracts/domain/v1/error-codes.json` ·
`db/migrations/**` · `infra/**` · `docs/program/CURRENT_STATE.md` · `docs/program/DEBT_REGISTER.md` ·
`docs/program/dispatch/**` · `Makefile` · `package.json` · any container not named `gate-w46a*`.
**The owner's stand is read-only.**

## Deliverables

1. The reseal as one commit; `S2`–`S4` committed step by step.
2. `docs/program/W46-SPEND.md`, opened **before** the first measurement.
3. Every guard shown failing, with the mutation and the failing assertion quoted.
4. The pin list: every pin checked, and moved or not.
5. Anything outside the grant, reported and not repaired.

## Verification

Lane `gate-w46a`: PostgreSQL `127.0.0.1:56370`, S3 `59970`/`59971`. The worktree is already
provisioned. If `.venv` or `web/node_modules` is missing, run `make bootstrap
FOUNDATION_PYTHON=/usr/bin/python3.12`, `.venv/bin/python -c "import boto3"` and
`npm --prefix web ci`.

**Baseline: take your own on `2ffca8c` first.** Nobody has gated this tip. The judge's
measurement was on `130200d`: battery 7 failed / 2493 passed, frontend 2 failed / 1118 passed
in 79 files. `8ad692f` repaired eight of those nine reds by moving pins and counts, and red #5
is yours.

`make gate > /root/w46a-gate.log 2>&1`. Take the verdict from the **`GATE OK` line in the log**.
The harness has reported `exit code 0` over a failed gate six times. **Run the canonical battery
literally.** A chosen scope presented as the canonical one is this programme's most repeated
error.

## Discipline

**Commit after each step.** A session restart kills you, and only committed work survives it.
Do not tag, push or merge.
