# W41-BLIND — make the guards reach the state that carries the defect

**task_id:** `W41-BLIND` · **wave:** 41 (the debt wave) · **lane:** `gate-w41b`
**worktree:** `/root/w41blind` · **branch:** `agent/w41-blind` · **base:** `6aeda82` (`alpha-w40`)

## The subject is the pattern, not any one guard

`D-69` has been re-opened in seven consecutive waves. Every instance is the same sentence:

> **the instrument rendered, saw, and permitted — because the state that carries the defect was
> never reached.**

| wave | guard | why it was blind |
|---|---|---|
| 35 | contrast census | matched **authored** class names; the markup carries the bundler's |
| 35 | `rendered-language` | rendered four of eight run states |
| 37 | `rendered-language` | the empty branch is also Russian, so the `D-57` mutation stayed green |
| 37 | seam sweep | two of six mutations reddened nothing |
| 38 | `rendered-language` | every seeded page had `next_cursor: null`, so pagination never rendered — eight English words on screen, guard green |
| 39 | three guards, reported by `W39-REVOKE` | |
| 40 | `W40-LIMIT`'s `L5` | the mutation was insufficient **and** the guard blind at once |

**In every one of the seven, a mutation dying quietly was the only thing that found it.** Nothing
structural has ever caught one. That is what this task changes.

**The common cause is structural and it is not carelessness:** a guard's seed matrix is a
hand-written literal, and **nothing anywhere checks that the literal covers the space.** The
guard answers, and an answer is read as coverage. A new enum member, a new branch, a new cache
state — each arrives silently permitted.

## Frozen inputs

| | |
|---|---|
| contract | `contracts/api/v1/openapi.json` — **frozen, and you do not reseal.** 15 / 18 / 51 |
| `web/FRONTEND_LOCK.json` | **frozen.** Touching it is a reseal and not yours |
| `TRANSLATED_SCHEMAS` | `['RunState','StageStatus','Verdict','FindingCategory','StageId','ProviderMode','CostBasis']` |

## allowed_paths

```
web/tests/**
tests/e2e/**
web/src/**          — ONLY where a defect your repaired guard newly catches requires a fix
docs/program/W41-BLIND.md
```

## forbidden_hotspots

`contracts/**` · `web/FRONTEND_LOCK.json` · `Makefile` · `src/auditmanager/**` ·
`tests/**` except `tests/e2e/**` (the rest is `W41-AUTHOR`'s, running beside you in
`/root/w41blind`'s sibling `/root/w41author`) · `db/migrations/**` ·
`docs/program/DEBT_REGISTER.md` (the integrator owns it) · `package.json` · `package-lock.json` ·
any container whose name does not begin `gate-w41b`.

---

## B1 — coverage becomes an assertion

`web/tests/guards/rendered-language.guard.test.ts` renders six screens across eleven cache
states and fails on a Latin word outside a contract-derived allowlist. Three of the seven
blindnesses above are this guard, and each time the repair was *"seed one more state"* — which
fixes the instance and leaves the cause.

**Make the matrix's coverage a thing the suite checks.** The guard must go **red** when a state
exists that it does not seed, rather than green because it seeded what somebody thought of:

- every member of every schema in `TRANSLATED_SCHEMAS`, read from the contract, not a literal;
- both sides of every branch the widgets actually have — pending / error / empty / non-empty,
  `next_cursor` null and non-null, first page and a later page;
- and the assertion fails **naming the unseeded state**, because `D-61` records that a guard
  which names the wrong offence is worse than one that misses: it sends a reader hunting a
  string that is not on the screen.

**The falsification is the deliverable, not the feature.** In a scratch copy, add a member to a
contract enum and seed nothing for it. The guard must go red *for not being seeded* — not stay
green, and not go red for the unrelated reason that the new word is English. Show both.

Do the same for the **contrast census**, whose blindness was different and is the other half of
the cause: it matched **authored** class names while the rendered markup carries the bundler's.
Measure whether that is still true before writing anything — it may have been repaired in
wave 35 and the register may be stale. **Say which you found.**

## B2 — `D-61`'s third instance, the dangerous one

`tests/e2e/test_pc01_journey_conformance.py` asserts `expects_rendered` by **substring
containment against a concatenation of `web/src`**. So the manifest asserted the sentence
`"Run"` and passed — it matched inside `RunPage`, and **no screen renders it.**

Containment has now deceived three guards (`D-40`, the language guard's `accepted` → `ed`, and
this). The first two were fixed by matching on a word boundary. **This one is not**, because the
subject is wrong, not the matcher: it searches source where it must read rendered output.

`W32-SEE` already built a renderer for exactly this. **Reuse it. Do not build a second one** —
two renderers is two truths and the older one keeps being cited.

When the repaired assertion reddens, **the manifest is what is wrong**, not the screen. Fix the
manifest to name text a screen renders, and say in the report how many of its sentences were
asserting nothing.

## B3 — leave the tally behind

Your report carries the seven-row table above, extended with **what now reaches each state** and
**which of the seven a structural check would have caught**. If the honest answer is "three of
seven and the other four need something else", write that. A debt row that overstates its own
repair is how `D-4` and `D-2` closed early, and this register has a rule about it.

---

## Deliverables

1. The repairs, committed as you finish each.
2. `docs/program/W41-BLIND.md` — opened **before** the first measurement.
3. Every guard shown to fail: mutate → red → revert → green, with the mutation and the failing
   assertion quoted. **A mutation that comes back green is a finding, not an obstacle.**
4. Anything outside the grant: reported, not repaired.

## Verification

```
cd /root/w41blind
make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12
.venv/bin/python -c "import boto3"
npm --prefix web ci
npm --prefix web run typecheck        # in the gate since wave 37; run it early, it is fast
make gate > /root/w41b-gate.log 2>&1; echo "exit=$?"
grep -c 'GATE OK' /root/w41b-gate.log
```

**Read the result from the `GATE OK` line in the log, never from a status a harness hands you.**
Report battery / foundation / frontend counts **with the commit they were taken at**.

## Integration contract

No contract, no lock, no migration, no shared module signature. `W41-AUTHOR` owns
`src/auditmanager/**` and all of `tests/**` except `tests/e2e/**`.

## Rollback

`git revert`. Nothing here changes product behaviour except where a repaired guard exposed a
real defect — and each of those is its own commit, named as such.

## Discipline

**Commit each step as you finish it.** Do not tag, do not push to `main`, do not merge.
