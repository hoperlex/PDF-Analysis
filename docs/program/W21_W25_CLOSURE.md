# Waves 21–25 closure: certification became an instrument, and it kept disagreeing with the briefs

Written 2026-09-21 by the integrator, nine waves late. **`make gate` → `GATE OK`, exit 0** at
each wave's merge; the run of figures is in §7.

These five waves have one subject even though no brief said so: **`PA-01` stopped being a
document and became something this programme can re-run.** Twice — `W21-CERT` at `0f9989a`
and `W24-CERT2` at `16d3503` — a session drove all ten criteria to a verdict and refused to
inherit a single one. Everything else in these waves was either something a certification
found, or something it could not yet reach.

## 1. The result

| Wave | Stream | Row | Outcome |
|---|---|---|---|
| 21 | `W21-CERT` | — | ten criteria driven; **seven hold**, two `cannot be established`, four named exceptions |
| 21 | `W21-E2E` | `D-5` | the browser journey moves **into the tree**, with no new dependency |
| 22 | `W22-E2E` | `D-5` | the unanswerable `POST /runs` answered: `202 queued`, kept whole on disk |
| 22 | `W22-OPS` | `D-24`, `D-27` | the wipe rehearsal counts truthfully; the stack can be asked whether it is the tree |
| 22 | `W22-WEB` | `D-25`, `D-26` | the quotation caption stops sending an expert to the wrong place |
| 23 | `W23-DEPLOY` | `D-28`…`D-31` | `infra/deploy/deploy.sh`, thirteen guards, each shown able to fail |
| 23 | `W23-PARTIAL` | `D-34` | `partial` is inducible — because the thing blocking it was a **defect** |
| 24 | `W24-CERT2` | — | all ten re-driven at `16d3503`; **eight hold**, two exceptions, none fails |
| 24 | `W24-IDEM` | `D-36` | `deploy.sh` three times, seven container IDs unchanged |
| 25 | `W25-COST` | `D-15` | `cost_basis` describes the figure beside it |
| 25 | `W25-SEAL` | `D-18`, `D-35` | `R-8` reinstated and the frontend reseal **paid** |

## 2. Certification only works because it is allowed to contradict the brief

Every one of these waves found the integrator's brief wrong about something, and in three
cases the brief would have produced a careful proof of a claim nobody had made.

**`W23-DEPLOY` §0 is the cleanest instance in the programme's history.** The brief quoted
criterion 1's second clause as *"the schema the migrations produce is the one the application
expects"*. `ALPHA_ROADMAP.md:313` says *"the schema the **running app serves** conforms to the
frozen `contracts/api/v1/openapi.json`"*. The brief's step list therefore pointed at
`make check-db` and `tests/integration/db` — a database question, for an API criterion. The
session answered both, said which one the criterion asks for rather than blurring them, and
wrote: *"if I had followed the brief's wording I would have produced a careful proof of a
clause nobody wrote down."* **The rule this establishes is that a criterion is quoted from its
file, never from the dispatch that cites it**, and both certifications now do that in §1.

**`W25-COST` found `D-15`'s mechanism impossible.** The row said a run whose first attempt
replayed and whose second reported a cost publishes a two-attempt sum wearing one attempt's
provenance. That run cannot happen, and the tree says so in three places: `RETRYABLE_STAGE_ERRORS`
holds exactly one code, `RetryPolicy.__post_init__` refuses to construct over any code the frozen
catalog does not mark retryable, and **every site that raises that code raises it from inside
`adapter.complete()`** — before `cost_meter.charge` is ever reached. The disproof was already
sitting in `test_retry_provenance_seam.py`. The repair landed anyway, on a **different and
real** argument: the rule belonged on `CostMeter` rather than repeated in two metric dicts.

**`W24-IDEM` found `D-36`'s stated cause wrong**, and says finding that out was most of the
work. It was never a `created` timestamp and `SOURCE_DATE_EPOCH` was never going to fix it; it
is BuildKit's **provenance attestation** on the manifest.

## 3. A named exception is a hypothesis, and one of them was a live defect

`W21-CERT` recorded criterion 4 as *holding with a named exception*: **`partial` is not
inducible** — it needs a truncated provider call and nothing in the operator's surface picks a
model or an output ceiling.

`W23-PARTIAL`'s first line is the finding of the whole run of waves: **"The mechanism half of
that sentence is exactly right. The diagnosis is not."**

On the `proxy` transport — the transport `W21-CERT` had itself certified criterion 4 on —
`partial` was not a state nobody could reach. **A reply cut short at the output ceiling was not
recognised as cut short at all, and published as a complete analysis.** A truncated audit
answered as a finished one. The guard that should have caught it asserted
`stop_reason == "truncated"`, a string, rather than `response.truncated`, the decision.

That is worth stating as a rule, because named exceptions accumulate quietly and each one reads
like a limit: **an exception recorded in a certification is a claim about the world, and it
expires.** Waves 22–24 cleared four of them. Criterion 5's went when `W22-WEB` repaired the
caption. Criterion 10's shrank to *the total counts a view*, which over-reports and so errs in
the safe direction. Criterion 8's is the only one that survived all five waves, and wave 30 is
re-measuring even that, because **its stated reason — three alpha stacks on the host — stopped
being true on 2026-09-21.**

## 4. `R-8`, reverted in wave 20, reinstated in wave 25, and the number that made it safe

`W20-CODE` built `staged_upload_lost` in full, proved it over a real socket, and was **blocked
from `web/FRONTEND_LOCK.json` twice** — by its brief and by the harness's permission classifier.
It stopped rather than route around either. The integrator declined to perform by hand an action
a delegated session had been refused, and put it to the owner, who ruled `R-11`: revert.

`R-13` authorised the reinstatement. `W25-SEAL` cherry-picked it and paid the reseal, and the
sentence that matters is this: **all six digests were re-derived with `sha256sum` against this
tree, and all six agree with the `W20-CODE` record to the byte. None differed.**

That is what made a five-wave-old revert safe to reinstate: not the record's authority, but the
fact that the record could be **re-derived** and was. A reverted branch that nobody can re-derive
is a story about work; one whose digests still agree is the work.

## 5. Three instruments moved into the tree, and that is the durable change

Waves 21–24 took three things that existed only as a session's transcript and made them things
the gate runs.

- **The browser journey** (`W21-E2E`). `tests/e2e/pc01/journey/`, driven over CDP with Node 22's
  built-in `WebSocket`. **`web/package-lock.json` is untouched and `web/package.json` changed by
  one line.** An instrument that costs a dependency gets removed in the wave after next.
- **`verify-deployed.sh`** (`W22-OPS`). A deployed stack can now be **asked whether it is the
  tree**, file by file, and answers with an exit code. Every claim in this programme about what
  is running at 31500 has been made through it since, including today's.
- **`deploy.sh` and `reset.sh`** (`W23-DEPLOY`, `W22-OPS`), thirteen and twelve guards, each
  marked `# >>> guard: <name>` and **each proved able to fail by deleting it and watching the
  script stop**. That discipline exists because wave 18 found a `reset.sh` guard that had been
  inert in production *and inside its own test suite* for waves, because GNU `grep` reads `\t`
  outside a bracket expression as the letter `t`.

## 6. What the integrator got wrong, collected

- **Misquoted `PA-01` criterion 1** (§2). Caught by `W23-DEPLOY` before it cost anything.
- **Told two certification sessions that 31500 was rebuilt from current code when it was not.**
  Both verified rather than accepting it, and both refused. That produced `D-27` and the probe
  that answers it, so the error bought something — but it was told twice.
- **`D-15`'s and `D-36`'s stated mechanisms were both wrong**, and both rows were written by the
  integrator from a session's report rather than from the tree.
- **`W21-CERT` arrived to 6.8 GB free of 119 GB.** Disk reached 100% twice across these waves.
  The reclaims are `docker builder prune -af` and, after `container prune`, `docker volume prune
  -af`; the standing fix is wave 30's, which is that **removing a wave's worktrees is part of
  closing it**.

## 7. The gate, wave by wave

| | battery | foundation | frontend |
|---|---|---|---|
| base of wave 21 (`0f9989a`) | 1806 / 5 / 168 | 35 | 681 in 47 files |
| wave 21 close | 1817 | 35 | 681 |
| wave 22 close | 1836 | 35 | 681 |
| wave 23 close | 1865+ | 35 | 706 in 48 |
| wave 25 close | **1942 / 5 / 168** | 35 | **706 in 48** |

Every figure read from a log with `EXIT=$?` appended by the shell that ran `make`, never through
a pipe. Sessions accounted for their deltas case by case; `W21-E2E`'s eleven are one conformance
guard, `W25-COST`'s ten are the `CostMeter` rule.

## 8. What these waves handed forward

- **`R-1`.** Criteria 1 and 2 stayed `cannot be established` through both certifications, and the
  reason is a host, a name and a certificate. Wave 26 was dispatched to make sure the repository
  was not *also* a reason.
- **`D-9`** — the norms corpus, which `R-9` placed after the owner's manual testing.
- **The four named exceptions**, three of which waves 22–24 cleared, and criterion 8's, which
  wave 30 is re-measuring for the first time on a host with one stand instead of three.
