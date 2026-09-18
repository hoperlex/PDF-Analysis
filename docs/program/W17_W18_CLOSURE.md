# Waves 17–18 closure: the repairs a user's eye found, and the reseal that unblocks the screens

Written 2026-09-18 by the integrator. **`make gate` → `GATE OK`, exit 0.**

Three streams across two waves, all of them working from `W15-RUN`'s browser journey — the
first report in this programme written from a user's position. Wave 17 repaired what that
journey found in `src/`; wave 18 repaired it in `infra/` and carried out the owner's `R-5`
reseal.

## 1. The result

| Stream | Row | Outcome |
|---|---|---|
| `W17-VIEW` | `D-19` | a published run reports its timings and its finding counts |
| `W18-OPS` | `D-17` | the restore carries every published attribute, proved **by writing** |
| `W18-SEAL` | `D-21`, half of `D-16` | the `R-5` reseal: three listings and a run's cost |
| integrator | `D-4` | an unreachable branch stops inventing a digest |

**Contract: 10 paths / 12 operations / 43 schemas → 12 / 15 / 46.** No error code added.
**Gate: 1746 → 1776** in the battery, frontend 592 → 595, foundation 35 throughout.

## 2. Three instruments that reported something other than what they claimed

Wave 16's closure said its subject turned out to be measurement. These two waves made that
three more times, and none of the three failed loudly.

**A guard that had never fired, anywhere.** `reset.sh`'s `dump-verified` tested an empty
digest with `grep -q '^[^\t]*\t\t'`. **GNU grep reads `\t` outside a bracket expression as the
letter `t`.** Confirmed independently: `/usr/bin/grep` is GNU grep 3.11 and gives **no match**
on a row that should match. It looked correct only because an interactive agent shell routes
`grep` through a function to ugrep, which does read `\t` — and **a script run as a subprocess
never sees that function.** So the guard was inert in production *and inside its own test
suite*. It had no case, so it had never been shown able to fail. That is the entire argument
for the rule, demonstrated on a guard written by the programme that wrote the rule.

**A safety net that had frozen a defect.** Records 03–07 of the response baseline carried
**one substitution token for `created_at` and `terminal_at`**, possible only because the two
were byte-identical to the microsecond. `W15RUN-5` was legible in that directory for **five
waves** before a browser found it. A re-capture alone would have erased the evidence with
nobody having to say it had been there, so `W17-VIEW` asserted the repair instead.

**Thirty statements a gate structurally cannot check.** `grep` over `src/auditmanager/api/`
returned **thirty** claims about the size of the surface — docstrings, comments, `README.md`,
and one string the application **serves** on `/openapi.json`: *"The twelve operations of the
PC-01 surface"*. The conformance engine drops `description`, `summary` and `title` as
annotation, so **every one of them would have survived this reseal and gone on being read as
true.** All thirty were **re-measured, not find-and-replaced**: *"eight of the twelve"* became
*eleven of fifteen* because they were counted; *"four of the twelve declare no 422"* stayed
**four**, because that set did not change.

## 3. Defects that lived one layer below where I said

**`D-19` was two defects, and neither was where my brief pointed.**
`runs/repository.py::_SELECT_STAGE_RESULTS` never selected `started_at`/`finished_at` —
**columns its own upsert has written since the first migration** — so `StageResultRow` had
nowhere to carry them and the columns were write-only. The assembler I named **could not have
set them if it had tried.** Separately, `now()` is `transaction_timestamp()` and `start_run`
creates *and* executes inside one write, so three timestamps were three copies of one instant.
No contract change: all four fields were already declared.

**`D-17`'s key count was mine and it was one key too generous.** Read from the adapter,
`publish` writes **four** user-metadata keys plus the `Content-Type` header; the old restore
carried **one of the four** plus the header. **Three keys were lost, not one.** A fix built on
my figure would have carried `blob-role`, passed the write-back test, closed the row, and left
`content-size` lost — whose loss is **quieter rather than smaller**, because
`_record_from_head` raises `SizeMismatchError` only when the value is present. A restore
without it does not fail; it **silently stops checking**.

**`D-4` I closed on one module's evidence, then re-opened for the wrong reason.** I cited
`CHECK (sha256 IS NULL OR …)` as proof of reachability. That permits NULL *in general*; it is
not evidence that a row reaches the comparison carrying one. Measured properly, two
independent facts forbid it, so the branch is **unreachable — and saying so is the repair.**
It raises `internal_error` naming the invariant with no details, instead of inventing
`actual_sha256=""`. An unreachable branch that invents a plausible value is worse than one
that refuses: an empty string reaches an operator looking exactly like a digest of nothing.

## 4. `D-17` proved the way it should have been the first time

Wave 14 learned that `mc mirror` is not a backup of an object, fixed the digest, and then
**verified the fix by reading**. A key only a write path consults survived that check.

```
post-fix : upload 201 -> wipe -> restore -> read back byte-identical -> RE-UPLOAD 201
pre-fix  : ................................ read back byte-identical -> RE-UPLOAD 409
```

**A restore is proved by writing to the restored instance, not by reading from it.** Reading
back is *necessary* — a lost `content-sha256` 422s the read, so wave 14 was right to check it
— and *not sufficient*, because `blob-role` is consulted by no read at all.

And run against the bucket a pre-fix restore left behind, the fixed script **exits 3, names
the bad row and purges nothing.** That is `R-4`'s commitment holding: it will not destroy an
instance whose objects it cannot put back.

## 5. The reseal, and the boundaries it stopped at

`R-5` authorised one reseal carrying both the listings and cost visibility. Both landed.

**Cost is on `RunStatus`, not in the CSV**, and the argument is from the criterion: `PA-01`
criterion 4 names *"provider mode and cost"* together and `provider_mode` is already a
required `RunStatus` property. Three reasons against the CSV, any one sufficient — the
seventeen columns are frozen by `OD-11` and named as seventeen by criterion 7; one CSV row is
one **evidence item**, so a run-level cost repeated down the column reads as a per-row fact
and sums to the cost times the evidence count; and `exportRunCsv` refuses a run whose terminal
does not publish, so **a run that spent money and then failed would have its cost invisible
exactly where an operator most wants it.**

**`D-15` was neither inherited nor repaired.** The figure comes from the `model_call` rows —
which `D-15` itself calls the exact ones — and **`model_call_count` is published rather than
inferred**, which answers the ambiguity directly: without it a reader cannot tell a run that
answered first time from one that was retried.

**Eight boundaries were named rather than taken:** the CSV, a 22nd code, `D-15`, `D-18`,
`D-20`, `listProjects.document_count`, `web/src` screens, and `infra/`.

## 6. What this does and does not do for a user

**`D-16` closes only its API half, and the open half is the one a user feels.** The typed
client is regenerated and fifteen operations are reachable from `operations.gen.ts`, but
`web/src/app/**` is untouched — **no screen renders them**. A project page on a fresh load
still makes no listing call. The row's own text said *"a reseal adding list operations, **then
the screens**"*, and only the first clause is done.

**And `listRuns` cannot make criterion 4's `running` state observable.** Because `execute_run`
is inline, a run is `published` by the time `startRun` answers. The set of runs is reachable
now; an in-flight run is still not. That remains `D-20`'s.

## 7. The deployed stack is behind the repository, measured

The alpha stack on 31490 is wave 15's build and **exhibits every defect these waves repaired**:

```
created_at == terminal_at, to the microsecond, on a run that took 11.8 s
stage keys: stage_id, stage_version, status        (no timings, no counts)
"cost" appears nowhere in the body
GET .../documents  .../versions  .../runs  -> 404, 404, 404
deployed: 10 paths / 12 operations      repository: 12 / 15
```

Nothing is deployed by merging. **A rebuild is the next operational step**, and it is the
first one that will put today's repairs in front of a browser.

## 8. The gate

```
GATE OK: battery, foundation, frontend and whitespace all pass
1776 passed, 5 skipped, 168 subtests passed
foundation 35 passed, frontend 595 passed (44 files)
```

Every delta accounted for: 1748 → 1756 (`W18-OPS`'s eight refusal cases) → 1776 (`W18-SEAL`'s
twenty). Frontend 592 → 595. Read from a log with the exit code appended by the same shell
that ran `make`.

## 9. What these waves hand forward

- **The screens.** `D-16`'s open half, now unblocked and the shortest path to an application
  a person can drive by hand.
- **A rebuild of the alpha stack**, without which none of this reaches a browser.
- **`D-20`** — inline execution, so no `running` state exists to observe.
- **`D-18`**, now a narrow owner question: may a `conflict` envelope carry a discriminator
  between *"stop, the instance was restored wrong"* and *"retry the upload"*, and is that a
  detail key or a second code?
- **`D-15`, `D-22`, `D-1.6`, `D-8`, `D-9`, `D-11`** — unchanged and none blocking.
- **`origin/main` is nine waves behind**, and `D-1.5` — the one named exception qualifying
  `W12-CERT`'s certification of `e6eae1e` — **closed today**, so the condition
  `DEBT_REGISTER.md` §3 named is met with no caveat remaining.
