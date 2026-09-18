# Wave 16 closure: the debt wave, in which three measuring instruments turned out to be broken

Written 2026-09-18 by the integrator. **`make gate` → `GATE OK`, exit 0**; battery 1748,
foundation 35, frontend 592.

The cadence says every third wave closes debts, analyses the code and removes blockers. This
was that wave. Two dispatched streams and the integrator's own, plus `W17-VIEW`, which was
wave 17's opener and is closed here because it belongs to the same run of repairs.

**Ten rows closed.** `D-1.5`, `D-2`, `D-3`, `D-4`, `D-5`, `D-6`, `D-7`, `D-10`, `D-12`,
`D-13`, `D-19`, and `D-14` opened and closed in the same pass.

**But the wave's subject turned out to be measurement itself.** Three separate instruments —
a coverage script, a characterization corpus, and this register — were each found to be
reporting something other than what they claimed. None of them was failing loudly.

## 1. The three broken instruments

### 1.1 A coverage script that could not see a dynamic import

`D-1.5`'s own `Check:` command — wave 12's reachability script — matches
`(?:from|import)\s+['"]…['"]`, which demands whitespace after the keyword. A dynamic import
has a parenthesis there.

```
import { a } from '@/shared/x'      -> ['@/shared/x']
await import('@/shared/api/x')      -> []
```

It had been under-reporting for two waves. Counting both forms gives `114 80 34`, **the same
34 modules and the same 1352 lines wave 12 listed**, module for module; the broken script says
`114 79 35`. **A session re-deriving this row's own check would have concluded the unreached
region grew when it had not.**

And the consequence lands on me: I told `W16-WEB` to verify `W15-AUTH` §8.4 rather than assume
it. §8.4 was right — its BFF `route.ts` *is* reached, through exactly the form the script
cannot see. **My doubt was the stale premise, not the thing I doubted.**

### 1.2 A safety net that had frozen a defect byte for byte

Records 03–07 of the response baseline carried **one substitution token for `created_at` and
`terminal_at`**. Substitution in that corpus is by exact value, so two fields earn one token
exactly when their values are identical — and they were, to the microsecond, because
`start_run` creates *and* executes inside one write and `now()` is `transaction_timestamp()`.

`W15RUN-5` was legible in `tests/characterization/w13_baseline/records/` for **five waves**
before a browser found it.

**A safety net that reproduces a defect byte for byte is protecting it.** A re-capture alone
would have erased the evidence with nobody having to say it had been there, so `W17-VIEW`
asserted the repair instead of quietly recapturing.

### 1.3 A register that was wrong in both directions on the same day

- **Stale.** `D-2` and `D-4` were fixed by `1b2549b` — **thirty-nine minutes after this
  register was created**, by a stream dispatched to fix them, with a test file naming both
  rows in its third line. They sat open for a day.
- **Over-closed.** I then closed `D-4` on `reconciliation.py`'s evidence while
  `blob_repository.py` still emitted `actual_sha256=existing.sha256 or ""`. `W16-ERR` caught
  it.
- **Wrong about why.** Re-opening it, I wrote *"it is reachable, and the schema says so"*,
  citing a `CHECK (sha256 IS NULL OR …)`. That permits NULL **in general**; it is not evidence
  that a row reaches the comparison carrying one. Measured properly, two independent facts
  forbid it, and the branch is **unreachable** — so the repair is to *say so*, raising
  `internal_error` naming the invariant with no details, rather than inventing an empty digest.

**Three rules came out of that, and they are in the register's header:**

1. A row is closed in the same commit as its fix, or the register lies.
2. A row is measured across every site that can produce the behaviour, not the first one that
   explains it.
3. A permissive constraint is not evidence of a reachable state. Check the writer.

## 2. The repairs

**`D-1.5` — the certification's one named exception, gone.** Six of wave 12's ten mutations
now killed, reachability 34 → 0, frontend 498 → 592. `W16-WEB` also wrote **12 of 12**
mutations against its *own* new tests, unasked, on the grounds that a suite which kills
someone else's mutations has not shown its own assertions can fail. Four survivors came back
**argued**: three unreddenable by construction (one render pass, `useRef` always fresh — the
repair is a `web/src` edit, carried forward as `D-22`), one deliberately left with its cost
stated. Two were killed by a **source guard rather than a render**, and the report says in the
same breath that this proves the statements are present and wired but does not execute them.

**`D-12` — a refused credential that told the caller to retry.** A 401 from the model proxy
mapped onto `dependency_unavailable`, which the catalog pins `retryable: true`. `D-7` made one
403 ambiguous; this was **wrong in the single field a client automates against**, so a retry
loop would spin forever against a rejected credential. Now `500 / retryable: false /
{"dependency": "model_provider"}`. The test that catches its reversion pins the **envelope**,
not the code name, because the lie was the flag.

**`D-13` — a deployment fault answering as the caller's validation error**, argued to
`internal_error` from the catalog's own `internal_mapping` rule 1 rather than from taste, with
`dependency_credential_refused` explicitly rejected because **borrowing it would repeat `D-7`
while citing it**.

**`D-19` — two defects, and neither where my brief said.** `_SELECT_STAGE_RESULTS` never
selected `started_at`/`finished_at` — columns **its own upsert has written since the first
migration** — so the assembler I pointed at could not have set them if it had tried. No
contract change was needed: all four fields were already declared.

**`D-10` — the mutation copy carries the tests.** A stream whose deliverable *is* a test module
can now mutate its own code, and with `FULL=1` a **migration is mutable for the first time**:
unmutated FULL copy `102 passed`, then `BEFORE UPDATE OR DELETE` → `BEFORE DELETE` on the
immutability trigger gives **7 failed / 95 passed**, all seven immutability guards.

## 3. Two sessions reported their own errors rather than burying them

`W16-ERR` voided its own first gate: it left a `pytest` running on its own lane while the gate
ran, so two runs fought over one database. It killed both, re-ran from a committed-clean tree,
and **said so**. Lane isolation held.

I did worse and record it here: **I staged a merge into the working tree while a gate was
measuring it** — the exact discipline I had written into that session's brief an hour earlier.
Aborted within the minute; the run survived. And when proving the `D-4` guards I ran
`git checkout` on a file holding uncommitted tests and destroyed them, then wrote a mutation
that rewrote a constraint name **in a docstring rather than in the query**, so it killed
nothing and nearly recorded a kill that never happened.

**The generalisation is `W16-ERR`'s and it is better than the memory rule it replaces:** one
measurement at a time, per lane — not only during subagent fan-out.

## 4. What was false in my briefs

Four, and one would have fabricated evidence.

- **"Every repair here is a characterization change."** False: **zero of the 33 records**
  exercise either envelope `W16-ERR` touched. It read record 31 first as instructed, measured,
  and **refused to write a `permitted_change` for a change that did not happen.** The useful
  corollary is that those two envelopes are not byte-pinned by the corpus at all.
- **`_run_status_view` named as the site of `D-19`.** It is one of two, and the other is a
  layer below where the data was already being written and never read.
- **`W12-WEB` §10's "seven of ten are reachable by `renderToStaticMarkup`"** — four are.
- **Provisioning**: a fresh worktree needs `npm --prefix web ci` or the gate exits 2 at the
  frontend, and `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`. Neither was in any
  brief until now.

## 5. The gate

```
GATE OK: battery, foundation, frontend and whitespace all pass
1748 passed, 5 skipped, 168 subtests passed
foundation 35 passed, frontend 592 passed (44 files)
```

Every delta accounted for commit by commit: 1726 → 1734 (the mutation-copy guard) → 1736
(`D-3`) → 1746 (`W16-ERR`'s 2, `W17-VIEW`'s 8) → 1748 (`D-4`'s 2); frontend 498 → 592 is
`W16-WEB`'s 94.

## 6. What wave 16 hands forward

- **Open now:** `D-16`, `D-21` (both the `R-5` reseal), `D-17`, `D-20`, `D-18`, `D-22`,
  `D-15`, plus the prose rows `D-1.6` and `D-8`.
- **`R-5` and `R-6` were ruled on 2026-09-18** and are recorded in
  `OWNER_RULINGS_2026-09-17.md` §3.5.
- **`D-1.5` closing removes the qualification on `W12-CERT`'s certification of `e6eae1e`** —
  it was the one named exception. `origin/main` is eight waves behind and the condition
  `DEBT_REGISTER.md` §3 names is now met without a caveat.
