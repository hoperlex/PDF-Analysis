# Wave 10 plan — five parallel sweeps of the rule surface

Written 2026-09-16 by the integrator. Base `fb30e96` on `planning/prototype-roadmap`,
published as `origin/dev`. Gate at that commit: 816 passed / 5 skipped / 116 subtests,
`make gate` → `GATE OK`.

**Awaiting the owner's go-ahead.**

## 1. Why this wave, and the evidence that it pays

**PC-01 has been certified twice. Both passes established that each *criterion* can fail.
Neither established that each *rule* can.**

That distinction is not theoretical. Two waves running, a mutation sweep found guards that do
not guard:

| Wave | Swept | Found |
|---|---|---|
| 8 | three places `W6-CERT` named in passing | a cross-check the twelve operations cannot reach; the recovery carrying criterion 9's safety, with no test; a tautology standing in for the live precision measurement |
| 9 | one module (`ingest/envelope.py`) | three rules no test could redden, all on the criterion-10 surface |

Six findings from a surface of roughly 1 600 lines. The rest of `src/` is about 17 000 lines
and has never been asked the question.

**The yield will drop.** These were the places closure records already pointed at, and a
sweep of untouched trees will mostly confirm that things are fine. Every brief therefore says
that a sweep finding nothing is a successful sweep, and that a manufactured finding costs
more than a quiet wave.

## 2. The five streams

Disjoint `src/` reading sets and disjoint test-writing paths. No stream writes `src/`, `db/`,
`contracts/` or `web/`.

| Stream | Reads | Writes | Instance |
|---|---|---|---|
| `W10-ANL` | `analysis/**` — 5005 lines, 32 files | `tests/integration/analysis/**` (does not exist yet) | `gate-w10a` 55590 / 59190 / 59191 |
| `W10-FND` | `findings/**`, `decisions/**`, `exports/**` — 2524 | `tests/integration/{findings,exports}/**` | `gate-w10b` 55600 / 59200 / 59201 |
| `W10-API` | `api/**`, `shared/**`, `bootstrap/**` — 5209 | `tests/integration/{api,composition}/**` | `gate-w10c` 55610 / 59210 / 59211 |
| `W10-RUN` | `runs/**`, `ingest/**`, `db/migrations/**` — 3502 | `tests/integration/{runs,ingest,db}/**` | `gate-w10d` 55620 / 59220 / 59221 |
| **integrator** | `storage/**`, `documents/**` — 2505 | `tests/integration/storage/**` | `gate-w3` 55550 / 59150 / 59151 |

All twelve ports confirmed free on 2026-09-16. No stream needs a live provider.

## 3. Which tree I take, and why that one

`storage/` and `documents/` have **zero commits since the PC-01 acceptance** — measured, not
recalled. They are the only trees in the repository I have never touched, so a finding of
mine there carries the same weight as a dispatched session's.

The converse decides `W10-RUN`. `runs/` and `ingest/` have had the most integrator hands on
them — waves 2, 3, 6 and 8 all changed code there — so they go to an independent session
rather than to me. Wave 8's finding was that a careful independent QA had pinned a *defective*
value as its expected value; that brief accordingly tells its session to treat every existing
assertion in its own test paths as a claim rather than as evidence.

## 4. What every brief carries, and what it cost to learn

- **Pin expected values as literals.** Wave 9 wrote five green tests over three rules they
  could not check, because they imported the module's constants and built the expected value
  from them — both sides of every comparison moved together under mutation. This is the one
  instruction that can waste an entire stream.
- **Field is not reason.** Assert *which* rule refused. A test asserting only
  `details["field"]` passed whichever of three name rules fired, which is how a deleted check
  survived a sweep.
- **Three outcomes, all results.** Unreddenable-and-reachable is the yield; unreddenable *by
  construction* is reported with its argument and never faked into a test; reddened-by-
  something-else is reported too — wave 9 spent two minutes that way and saved a wave spent
  guarding something already guarded.
- **Mutate on a copy**, symlink `contracts/`, `docs/`, `fixtures/`, and prove
  `auditmanager.__file__` resolves under the copy before trusting a result.
- **Never add bytes to a corpus.** Both corpora are frozen evidence; a test builds its own
  bytes.
- **Rule 7: check every premise in the brief against the tree.** Eight stale premises are on
  record in this programme, several in briefs written by the integrator who wrote these.

## 5. How the results come together

Five reports, none subordinate to another. I reconcile them, merge the guards, route product
defects to their owning trees unrepaired, and run `make gate` on the convergence.

**If any stream finds a product defect, wave 10 does not repair it.** Repairs go in a
following wave, so that the re-certification debt stays one wave wide — the rule established
in wave 5 §4 and honoured since.

## 6. What this wave is not

It is not progress against the roadmap. P04 and P05 remain blocked on `OD-18`, and nothing
here moves them. It buys confidence that the guards behind a twice-certified checkpoint are
real, which is worth having before an expert cohort is booked against it — and it is the
largest piece of work available that does not need an owner decision first.

## 7. Still owner-blocked

- **`OD-18`** — three to five named experts with committed slots. `P4-BHV-01` waits on this
  alone.
- **`OD-17`** — the next corpus shape; PC-02's precision evidence is saturated.
- **The 21st error code.**
- **Whether `origin/main` advances** to `c0d7daf` or later. Pending four waves, blocking
  nothing.
