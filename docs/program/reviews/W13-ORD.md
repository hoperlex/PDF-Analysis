# W13-ORD — the two order-flaky records

**Session:** `W13-ORD`, wave 13. Tests only; nothing under `src/` was touched.
**Branch:** `agent/w13-ord`, cut from `origin/dev`.
**HEAD on arrival:** `cf6861c` — *merge: D-10 and D-11*.
**Instance:** `gate-w13e`, PG 55730, S3 59330/59331, db `audit_w13e`, bucket
`auditmanager-gate-w13e`. Logs in `/root/w13ord-logs/`.

**`make gate`: GATE OK — 1643 passed, 5 skipped, 167 subtests in 195.91 s; frontend 35 files
/ 440 tests; foundation 35; whitespace clean.** 1643 is the integrator's 1628 plus this
session's 15 new tests, which is the first corroboration that nothing else moved.

---

## 1. The defect, diagnosed independently

**The brief's mechanism is right and I reproduced it from the tree rather than taking it.
Two things around it are not right, and one of them changes the method (§5).**

`published_findings` orders by `f.finding_uid COLLATE "C", o.finding_observation_id COLLATE
"C"` (`src/auditmanager/findings/queries.py:42`) and the CSV by the same family
(`src/auditmanager/exports/query.py:100-101`). A `finding_uid` is a fresh ULID allocated at
publication — `publish_gate_result` calls `FindingUid.new()` once per grounded verdict inside
one loop (`src/auditmanager/findings/publication.py:160`). And the generator declines, in so
many words, to promise what the two records were relying on:

> Randomness comes from `os.urandom`. Monotonicity inside a single millisecond is
> deliberately *not* promised: the contract forbids consumers from deriving ordering from
> the body, so guaranteeing it here would invite exactly the coupling the contract prohibits.
> — `src/auditmanager/shared/identity/ulid.py`

So two findings published in the same millisecond are separated by 80 bits of `os.urandom`,
and which comes first is a coin flip. **Measured rather than argued.**
`/root/w13ord-logs/ties.log`, 200 journeys driven through `journey.run_journey` against this
lane at HEAD `3db62d6`, 191 completed (§6.2 on the other nine):

| | |
|---|---|
| ms between the 1st and 2nd finding's ULID | `{1: 36, 2: 108, 3: 38, 4: 6, 7: 2, 8: 1}` — **never 0** |
| ms between the 2nd and 3rd | `{0: 26, 1: 144, 2: 21}` — **0 in 26 of 191** |
| journeys with a millisecond tie | **26 of 191 (13.6 %)** |
| journeys whose response order ≠ document order | **12 of 191 (6.3 %)** |
| which permutation | `(0, 2, 1)` — **all 12**, the 2nd and 3rd findings swapped |

12 of the 26 ties came back swapped. That is the coin, measured: **46 %**.

The programme had measured the same coin before, and I found the note only after measuring
it. `tests/integration/exports/test_listing_order_matches_the_export.py` opens with: "two
findings published in the same millisecond disagree about their relative order roughly half
the time. `W2-QA` measured **31 of 416 real runs** diverging" — 7.5 %, against my 13.6 % tie
rate on a busier host. Two independent measurements of one mechanism.

**So the baseline was pinning something the system does not promise. The defect is in the
baseline, not the product** — I agree with the brief, and I did not touch `src/`.

### One thing the brief understates

The flake was not confined to two records by anything structural. The journey read its
finding as `page["items"][0]`, so **every** later case that names a finding —
`09-getFinding`, `10-appendDecision`, `11-listDecisionHistory`, and `12`'s decision columns —
was on the same coin. It did not fire there because the first finding's ULID is a
millisecond clear of the second's: **0 ties in 191 journeys at that position**, though a
1 ms gap in 36 of them, so the margin is one scheduling hiccup wide. I am not claiming it
was observed; I am saying the two records the integrator saw are the two the coin reaches
*most often*, not the two it can reach. The repair closes the rest by construction (§2,
change 1) rather than leaving it to that margin.

## 2. The shape chosen, and the argument against the two I did not

**Chosen: pin the ordering rule instead of the order — the brief's third shape — built on
the declared-normalization machinery of the first, because the third needs it.**

That phrasing is deliberate. Shape 3 says "assert that items are ascending by `finding_uid`
and stop asserting which one is first". *Stopping* is not a null action in a byte-for-byte
comparison: the record body is a byte string with the items in one particular sequence, and a
permuted response differs from it whatever else you assert. So shape 3 **is** shape 1 plus an
assertion. What I argue against below is not shape 1 but **shape 1 alone**.

Three changes, all inside `tests/characterization/w13_baseline/**`:

**1. The finding tokens are numbered by document order, not by response order.**
`{{finding_uid_0}}`…`{{finding_uid_2}}` used to be numbered by a finding's index in the
response. That made the *name* of a value a function of an order the system does not promise:
the same finding was `{{finding_uid_1}}` in one run and `{{finding_uid_2}}` in the next. No
order-insensitive comparison can work while that is true, because the elements being compared
carry the order inside them — this is the change that makes the rest possible, and it is easy
to miss. The rank is now `(page_number, char_start)` of the finding's first evidence quote:
where in the **document** it was found, a property of the frozen AR fixture. It is a
*substitution* rule, not an expectation — it decides what a value is *called*, never what any
value must *be* — and `publication_order` asserts the key is total rather than picking a
winner on a tie. Cases 09, 10, 11 and 12 take their finding through the same rank, which is
what closes the `items[0]` exposure in §1. **The numbering it produces is the numbering
already committed**, so not one recorded body moved (§3).

**2. `O1`, declared in the two records' own bytes.** Each carries an `unordered` block
answering four questions — what, why, what it cannot hide, what is still pinned — following
`W13-CONF`'s `N1`–`N9` form in `tests/contract/api_v1/openapi_conformance.py`, which I read
first as the brief asked. The comparison cuts **both** sides with the **same** declared
splitter into `(prefix, separator, elements, suffix)` at the byte level. Nothing is parsed or
re-serialised, so key order, separators, `ensure_ascii=False` and every byte inside an element
survive the cut, and `prefix + separator.join(elements) + suffix` is asserted to reassemble to
the body it cut. Prefix, separator and suffix are compared byte for byte. The elements are
compared as a **sorted list**.

*The proof that erasing the order hides nothing else is one line:* two sequences have equal
sorted forms **exactly when** one is a permutation of the other. So "equal under `O1`" is
precisely "equal up to a permutation of the declared elements", and every difference that is
not a permutation survives — a changed category, quote, offset or verdict; a dropped,
repeated or duplicated element; a changed count; any byte outside the elements. A **set**
comparison would not have this property, which is why a duplicate plant is in the suite by
name (§3).

**3. The rule the system does promise, pinned against the live response.** `listRunFindings`
must come back **strictly** ascending by `finding_uid` under `COLLATE "C"`; the CSV
**non-descending** by `(finding_uid, finding_observation_id)` — non-descending there because
the export repeats a finding once per evidence quote, strict in the listing because the key is
unique and equal neighbours are a duplicate row rather than a tie. Both are asserted against
the response, never against a recorded sequence, which is the design of wave 3's own guard:
`test_listing_order_matches_the_export.py` "pins no sequence… only a total order on *both*
sides can keep them agreeing".

### Against shape 1 alone — a declared normalization and nothing else

It trades a small blind spot for a larger one. This ordering is not an accident of the
implementation. Wave 3 aligned the listing to the CSV's key family **on purpose** (`W3_CLOSURE`
§1, D1), `W5-ADV` later reddened the mutation that drops the tiebreaker using 20 observations
tied under one `finding_uid`, and `COLLATE "C"` is an **active override** — the database
collation is `en_US.utf8`, measured in the same place. Erase the order and say nothing else,
and a FastAPI rewrite that dropped the `ORDER BY`, or issued it without the collation, leaves
this baseline green. Noticing that kind of move is what the baseline is for. One assertion
buys the coverage back, so declining to write it is not a trade-off; it is an omission.

### Against shape 2 — make the journey deterministic

**It is not available to a test.** The identities are allocated inside `publish_gate_result`,
several layers below a `POST /runs` the journey issues as one call. Nothing in
`tests/characterization/w13_baseline/**` can interleave with that loop. Publishing the two in
different milliseconds means changing `src/auditmanager/findings/publication.py` or
`src/auditmanager/shared/identity/ulid.py`, and STEP 5 forbids exactly that: *do not change
the product to make a test stable*. The fixtures that could otherwise change the finding set
are frozen evidence.

**And it would be the wrong change if it were available.** What it asks for is a monotonic
ULID, and `new_ulid` withholds monotonicity **by decision**, because the domain contract
forbids consumers deriving ordering from a ULID body and a generator that promised it would
invite that coupling. Shape 2 asks the product to begin promising something it has decided
not to promise, so that a test's recorded sequence stays valid — the tail wagging the dog,
and the new promise would be load-bearing for nothing but this directory. The brief's own
instinct is right for a smaller reason as well: a `sleep` buys probability, not determinism,
and the probability moves with the machine. Mine moved during this session (§6.2).

### A fourth shape, considered and rejected

Construct the case instead of hoping for it — insert a finding with chosen identities, the way
`test_listing_order_matches_the_export.py` does with `fnd_000…0` and `fobs_ZZZ…Z`. That is the
right tool for *"do these two orders agree?"* and the wrong one here. It makes the divergence
certain, but this corpus's question is not whether two orders agree; it is whether a response
reproduces recorded bytes. A directly-inserted row would also put a finding into the records
that no publication produced, in a directory whose entire claim is that everything in it was
learned from a response.

## 3. The evidence the corpus still catches what it must

### Nothing recorded moved

All 33 records regenerate **byte-identically** at `cf6861c` before the change
(`probe_identity.py` → `identical=33 differing=0`). After it, `git diff` over `records/` is
50 insertions and 3 deletions: one `"unordered": null` line per record, the two declaration
blocks, and three token *reason* strings in `08`. No status, no header, no body byte anywhere.
This is the check that makes it not a re-capture:

```
git diff -U0 ad2f901^ ad2f901 -- tests/characterization/w13_baseline/records \
  | grep -E '^[+-]' | grep -v '^[+-][+-]' | grep -v '"unordered": null,'
```

`"unordered"` is written on all 33 records, `null` on 31 of them, for the same reason
`"exception"` is: a declaration you have to go looking for is one nobody counts.

### `W13-BASE`'s demonstration, re-run — and it got sharper, not weaker

**The seven permanent plants still run and still pass**, untouched:
`test_the_comparison_reddens_on_a_planted_difference` (moved status, dropped
`X-Correlation-Id`, renamed body property, re-ordered and re-separated JSON, lost CSV BOM,
CRLF→LF, stale fixture digest) plus
`test_a_content_length_that_does_not_describe_the_body_is_reported`. Two of them land on
record `12`, which is now an `O1` record, and they are caught **through** the new comparison:
the lost BOM reddens as a prefix difference, and LF-for-CRLF reddens because the declared
split no longer finds CRLF-terminated rows.

**The by-hand perturbation, repeated.** The same four records `W13-BASE` edited — `03` status
`202`→`200`, `18`'s constraint `byte_size <= 26214400`→`max_bytes`, `12`'s first CRLF→LF,
`31`'s `permission_denied`→`storage_credential_refused` — reproduced by
`scratchpad/perturb.py`. Log: `/root/w13ord-logs/perturbation-demo.log`.

```
6 failed, 47 passed
```

against `W13-BASE`'s `5 failed, 33 passed`. The four cases, the planted-difference test whose
precondition is record `03`, **and** `test_every_permutation_of_the_sequence_is_invisible[12]`,
which asserts the unperturbed record matches before a permutation can mean anything. The sixth
failure is the point: the order-insensitive record is *more* watched than before, not less.
`git checkout` restored the four and the suite returned `53 passed`.

### Fifteen new tests, 38 → 53

| Test | What it shows |
|---|---|
| `test_exactly_two_records_declare_an_unordered_sequence` | `O1` is **countable**, the way the permitted exception is. Each declares a splitter the comparison implements and answers all four questions. |
| `test_the_declared_split_is_lossless_and_not_vacuous` | Both records really are cut into 3 **distinct** elements and the cut reassembles — the normalization is not a no-op in costume. |
| `test_every_permutation_of_the_sequence_is_invisible` ×2 | All 6 permutations pass, and the 6 bodies are asserted distinct, so the test cannot pass by permuting nothing. |
| `test_a_changed_element_is_reported_under_every_permutation` ×2 | 6 permutations × 3 positions = 18 plants per record; every one reported. |
| `test_a_dropped_a_duplicated_and_a_repeated_element_are_reported` ×2 | Dropped (×3), repeated (×3), and **element `j` replaced by a copy of element `i`** (×6). The last is what separates a sorted-list comparison from a set comparison, which would pass it. |
| `test_the_bytes_outside_the_sequence_are_still_compared` ×2 | Prefix, separator and suffix keep byte-for-byte comparison. |
| `test_the_findings_specific_differences_o1_must_still_catch` | A changed category, evidence offset, verdict, page number and Russian quote — each planted **into a rotated array**, so what is shown is that they are caught *through* the order-insensitivity rather than beside it. |
| `test_the_published_findings_come_back_ascending_by_finding_uid` | The rule the system does promise, on the live response. |
| `test_the_csv_rows_come_back_ascending_by_finding_uid_then_observation_id` | The same for the export's key family. |
| `test_the_two_ordering_rules_can_fail` | Both guards shown **refusing**: a swap, a descent, equal neighbours in the strict case, and a pair only `COLLATE "C"` byte order gets right. |
| `test_the_document_order_rank_refuses_a_tie` | The content-determined token index shown refusing a tie, and refusing a finding with no evidence. |

### The A/B on live responses — the measurement that actually settles it

`scratchpad/probe_stability.py` drove **150 real journeys** and, for each, ran
`journey.differences()` — the function the suite runs — over all 33 committed records
**twice**: once as committed, once with `unordered` stripped, which is an order-sensitive
byte-exact comparison of the *same* response. 4 950 record comparisons per arm.

```
journeys=150  permuted=7  new_comparison_failing=0  order_sensitive_comparison_failing=7
```

and for each of the seven:

```
run N: permuted=True new_failures=[]
       order_sensitive_failures=['08-listRunFindings.success', '12-exportRunCsv.success']
```

Seven journeys came back genuinely permuted. On those same seven responses the order-sensitive
arm failed on **exactly `08` and `12` and nothing else** — which reproduces the integrator's
report from the other side, on live data, and confirms that the two records named are the
whole of what the coin reaches today. The committed arm failed on nothing, in 4 950
comparisons.

## 4. How many battery runs — and why that is the weaker number

**Five full drives of the canonical battery: `make gate` once, and the battery itself four
more times with the gate's own `--ignore` list. All five green, all five identical.**
Logs: `/root/w13ord-logs/gate-1.log`, `battery-1..4.log`, `battery-runs.log`.

```
make gate     GATE OK  1643 passed, 5 skipped, 167 subtests in 195.91s
                       frontend 35 files / 440 tests; foundation 35; whitespace clean
battery 1     exit=0   1643 passed, 5 skipped, 167 subtests in 211.45s
battery 2     exit=0   1643 passed, 5 skipped, 167 subtests in 216.75s
battery 3     exit=0   1643 passed, 5 skipped, 167 subtests in 214.03s
battery 4     exit=0   1643 passed, 5 skipped, 167 subtests in 216.57s
```

A sixth run is not in that table and is worth having in this one. The first attempt at
`battery 1` came back `1643 passed, 5 skipped, 1 error` — every test green and a **teardown**
error from `tests/integration/foundation/conftest.py`'s session-scoped
`checkout_is_unchanged`, because I wrote this review file while the battery was running. The
brief warns that three sessions have tripped that guard by editing their review mid-gate; I am
the fourth, one layer down, in a plain `pytest` run rather than in `make gate`. I stopped the
batch, committed the review, and restarted all four on a frozen checkout — which is what the
table above is. Recorded rather than quietly re-run, because a `1 error` beside `1643 passed`
is exactly the shape somebody skims past.

**Said plainly: green battery runs are weak evidence here, and the brief's method rests on a
premise that is false in this tree.** A battery run drives the journey **once**, and a
permuted order occurs in 19 of 341 measured journeys — **5.6 %**. Five full drives therefore
exclude the flake with probability `1 − 0.944⁵ ≈ 25 %`. That is not a proof and I will not
present it as one. **The 150-journey A/B is the proof**, because it contains seven journeys
that actually permuted and puts them through the committed comparison against the committed
records.

And `pytest-randomly` is **not installed in this tree** (§5.1), so it is not what separated
the integrator's failing run from the passing one: `-p no:randomly` was a no-op and the
contrast was two samples of the same coin. Re-running "the way it was found" under a plugin
that is not there would have proved nothing in either direction — which is why the flake had
to be reproduced by driving the journey instead of by re-ordering the tests.

## 5. What is false in the brief

Checked against the tree at `cf6861c`, with the command beside each.

**5.1 — `make gate` does not run `pytest-randomly`. It is not installed and not locked.**
The brief leans on this four times: the diagnosis ("`make gate` (which runs
`pytest-randomly`)"), the contrast with `-p no:randomly`, the requirement that the corpus
"must fail under `pytest-randomly`, which is how the gate runs it", and the method in STEP 4.
Measured:

```
.venv/bin/python -m pytest … --collect-only   →  plugins: anyio-4.15.1
.venv/bin/python -c "import pytest_randomly"  →  ModuleNotFoundError
grep -in randomly uv.lock requirements/validation.lock  →  no match
```

`run_battery()` (`Makefile` 464–499) adds no plugin either. So **1628 passed vs 3 failed is
two samples of a 5.6 % coin, not a plugin effect.** This matters beyond bookkeeping: it is the
difference between "the suite is sensitive to test order" and "the suite is sensitive to a
coin flip inside one journey", and only the second is true. A session that took the brief at
its word would have spent its time re-ordering tests and would have measured nothing.

**5.2 — the M2 quotation is a line `W3_CLOSURE.md` struck through and corrected.**
The brief cites wave 3's M2 as *"dropping the tiebreaker makes the order unspecified rather
than wrong"*, as the standing record. In `docs/program/W3_CLOSURE.md` §1 that sentence sits
inside `~~…~~` under **"Wrong, and wrong in a way worth naming"**: `W5-ADV` reddened M2 with
20 observations tied under one `finding_uid`, reproduced by the integrator at `/root/w3-m2`,
**red 3 of 3**. The standing wave-3 position is the opposite of the quoted one — the
tiebreaker is load-bearing and the key family is a total order.

It does not damage the diagnosis: the tiebreaker orders observations *within* a finding, and
the flake is *between* findings, where the key is a single ULID. But it is a retracted line
offered as support, and read straight it argues for shape 1 when the standing text argues for
shape 3. I removed the same quotation from my own `journey.py` comment after finding it
(`3db62d6`) — citing a retracted line while reporting it as retracted is not a thing to leave
in a file stage 2 will read.

**5.3 — record 31 is named wrongly and has not been spent on this branch.**
The brief says `31-…storage_credential_refused.json`, "already spent by `W13-SEAL`". The file
is `31-streamDocumentVersionContent.storage_permission_denied.json`; `storage_credential_refused`
is the *error code* the reseal introduces, and it appears in this repository only as one of
`W13-BASE`'s hand perturbations. `W13-SEAL` is **not on `origin/dev`**
(`git log --oneline origin/dev --grep=SEAL` → empty; `origin/dev` is `cf6861c`). Record 31
still carries its pre-reseal expectation and reproduces byte for byte — it is one of the 33
identical regenerations in §3. The exception is **declared and reserved** here, not spent. No
consequence for this work: I added no second exception and
`test_exactly_one_record_is_marked_as_the_permitted_exception` still passes. But a stage-2
session cutting from `dev` will find that record unchanged, not resealed.

**5.4 — "two records are order-flaky" is true but not structural.** See §1. Not false, but it
describes what fires rather than what can fire, and a repair scoped to the sentence would have
left `09`, `10`, `11` and `12`'s decision columns on the same coin.

**5.5 — everything else held.** The base commit and the worktree; the instance and its six
values; `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`; 33 records; both `ORDER BY`
clauses and their collations; `W3_CLOSURE.md` §1 as where wave 3 aligned the listing to the
CSV's key family; `W13-CONF`'s nine normalizations at
`tests/contract/api_v1/openapi_conformance.py`, whose three-answer form I followed; the seven
permanent plants; `W13-BASE`'s four-record perturbation; the reported byte-1671 difference,
which is the second item's `"category"`; and that `08` and `12` are the two records the coin
reaches.

## 6. Scope, findings, and elapsed

### 6.1 Scope kept

Written: `tests/characterization/w13_baseline/**` and this file. **Nothing else** —
`git diff --name-only origin/dev...HEAD` outside those two paths is empty. No `src/`
(`W13-API` owns `src/auditmanager/api/**`; I did not open it to edit), no `contracts/`, no
`db/`, no `web/`, no `fixtures/`. No dependency added. No second permitted exception. No tag,
no push, no merge.

I concluded the product is **not** wrong, so there was nothing to stop on: `new_ulid`
withholds monotonicity by decision and says so, and the ordering rule the two queries
implement is the one wave 3 chose deliberately. The defect was the baseline asking for more
than that rule gives.

### 6.2 One environmental observation, recorded so it is not later mistaken for a finding

Nine consecutive journeys at the **start** of the 200-journey probe failed with
`KeyError('version_uid')` — `uploadDocument` answering something without a `version_uid` — and
an earlier probe lost one journey to `KeyError('run_id')` on `startRun`. **Zero** in the 191
journeys that followed, and zero across the 150-journey A/B.

The window: `df -h /` at **97 % used, 4.4 G free**; four other lane instances up on this host
(`gate-w13c`, `gate-w13d`, `gate-w3` and mine); load average 3.3; and my own `gate-w13e`
containers reporting a recent restart. I read this as the host, not the product, and I am
**not** offering it as a data point for `D-5` — the envelope was not kept, which is precisely
the gap `D-5` itself records about the harness that found it. It is here so that a later
reader who sees the same shape knows it has been seen, and under what conditions.

### 6.3 Commits

| | |
|---|---|
| `2041106` | open the review at `cf6861c` |
| `ad2f901` | `O1` — the tokens, the declaration, the comparison, 15 tests |
| `a58b25d` | the README meets `O1` where a reader meets the exception |
| `3db62d6` | cite the standing wave-3 measurement, not the struck-through M2 |
| `ee6303e` | this review |
| `46f689a` | the measured numbers |
| `5th` | this correction — three references above carried a commit hash I had written down before reading it back. They are `3db62d6`. Recorded rather than amended away: a figure that travels by being repeated is the failure `OPERATING_CONSTRAINTS.md` §12 names, and a hash is a figure. |

**Elapsed wall-clock:** 50 minutes — `2026-09-18T01:14:49+05:00` to `2026-09-18T02:05:06+05:00`. Roughly half of it is the 341 live journeys and the five full battery drives; the measurements are the expensive part, and §4 says which of them was worth the time.
