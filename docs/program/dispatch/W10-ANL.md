# `W10-ANL` dispatch prompt — mutation sweep of the analysis tree

Base `fb30e96` on `planning/prototype-roadmap`, published as `origin/dev`. Gate at that
commit: **816 passed / 5 skipped / 116 subtests**, `make gate` → `GATE OK`.

One of five parallel streams. The others sweep disjoint trees on their own instances. You do
not coordinate with them and you do not read their output.

---

You are session `W10-ANL`. Repository: /root/projects/PDF-Analysis.
Branch `agent/w10-anl`, worktree `/root/w10anl`.

## What you are for

Two waves running, a mutation sweep has found guards that do not guard. Wave 8 found three —
a cross-check the twelve operations cannot reach, a recovery carrying criterion 9's safety
with no test, and a tautology standing in for a live measurement. Wave 9 swept one module and
found three more rules no test could redden, all on the criterion-10 surface.

**PC-01 has been certified twice, and both passes established that each *criterion* can fail.
Neither established that each *rule* can.** That is the gap you are sweeping.

You read `src/auditmanager/analysis/**` — 5005 lines across 32 files, the largest rule surface in the repository.

## You own exactly these paths

- `tests/integration/analysis/**` — create it; there is no such directory today, which is itself worth noting in your report
- `docs/program/reviews/W10-ANL.md`

Nothing under `src/`, `db/`, `contracts/` or `web/`.

## Where to look first

The stage runner's status mapping, the text stage's anchors and offsets, the profile and
prompt-bundle lock, the provenance recorded per call, and the `truncated` status wave 2 made
first-class.

- **`analysis/text/lock.py`** refuses an unpinned model identity against `P02_LOCK.json`.
  Is that refusal reachable, and is it asserted by its own rule rather than by "something
  raised"?
- **stable character offsets** in `source_preparation` — criterion 5 depends on a quotation
  resolving at its declared anchor. `W6-CERT` showed the gate collapses 3 findings to 0 when
  every quotation is made unresolvable; that is the coarse case. **The subtle one is an
  off-by-one**, and nobody has tried it.
- **`page_geometry_extraction`** — block index and span anchors.
- **the fail-closed status mapping.** `truncated` was mapped onto `succeeded` before wave 2,
  filing truncated answers as clean successes. Is every status now mapped by something that
  would notice a changed mapping?
- **the cost meter** — `OD-03`'s ceiling binds across retry attempts. Wave 6 found
  `AppSettings.run_cost_ceiling_usd` was written and read nowhere; the reading half is here.

This is a starting point built from the closure records and the tree, **not a
specification**. Sweep your whole surface. If the list is wrong about something, say so.

## Provisioning — check, do not assume

`origin/main` now carries the `beaa7f7` certification, so an ordinarily-seeded worktree
should land on recent code. That is one owner decision old and has never been relied on.

```
git rev-parse HEAD
```

Base is `fb30e96` on `planning/prototype-roadmap`, published as `origin/dev`. If your HEAD is
not on that line:

```
cd /root/projects/PDF-Analysis && git fetch origin
git worktree add /root/w10anl -b agent/w10-anl origin/dev
cd /root/w10anl
```

**Do not put your worktree under `/tmp`** — docker is snap-confined and cannot see it.
Say in your report what your `HEAD` was on arrival.

## The method, and it is not negotiable

For every constant and every refusing branch in the `src/` paths you read, in turn:

1. **Mutate it on a copy.** Never edit a tracked file. Copy `src/` to a session-unique
   directory outside the worktree, **symlink `contracts/`, `docs/` and `fixtures/` into it**
   — `analysis.text.lock` resolves `docs/program/P02_LOCK.json` from `parents[4]` of its own
   module file, so a copy without `docs/` fails before reaching any assertion — and run
   `pytest -o pythonpath=<copy>/src`. **Print `auditmanager.__file__` and confirm it resolves
   under the copy before you trust a single result.**
2. **Run the suites that could plausibly cover it**, not only the one you expect. Wave 9's
   first sweep ran two suites and that is what separated "unguarded" from "guarded
   elsewhere".
3. **Record what reddened.** A mutation that reddens nothing is the finding this wave exists
   for.

### The one mistake that will cost you the whole wave

Wave 9 wrote five green tests over three rules they could not check. They imported the
module's own constants and built the expected value from them, so **both sides of every
comparison moved together under mutation**: raising a limit also lengthened the input the
test sent, the refusal still happened, and the test still passed.

**Pin expected values as literals.** Never import `MAX_BYTES` from the module and then assert
a message built from it. Write the number. Where an independent authority exists — a
migration's CHECK, a frozen contract, `P02_LOCK.json` — pin against that and say so, so a
constant that drifts away from it is a red test rather than a quiet agreement between a
module and itself.

### Three outcomes, and all three are results

- **Unreddenable and reachable** → write the guard. This is the yield.
- **Unreddenable *by construction*** → report it and do not fake a test. Wave 9 found
  `MIN_PAGES` looked unguarded, but a zero-page document is refused earlier by the page
  parser and no document can have fewer than zero pages. Wave 3 found a tiebreaker whose
  removal makes an order *unspecified* rather than wrong. Say which, and give the argument.
- **Reddened by something** → say what reddened it. Wave 9 spent two minutes ruling out
  `PDF_MAGIC` this way and saved a wave spent guarding something already guarded.

**A sweep that finds nothing is a successful sweep.** Report the empty result plainly. Do not
pad it. A manufactured finding costs more than a quiet wave, because the next session builds
on it.

### Field is not reason

Where a guard refuses, assert **which rule** refused, not merely that something did. Wave 9
found a test asserting `details["field"] == "source_filename"`, which passed whichever of
three name rules fired — and that is how a deleted check survived a sweep.

## Rules

1. **Commit after every meaningful step.** A dispatch here was once killed mid-run and lost
   four sessions because each held its work uncommitted.
2. **Stay inside your owned paths.** If a module's public surface does not let you reach a
   guard, **that is a finding**, not a licence to reach into another tree.
3. **You write tests, not product code.** Writing a guard for an unguarded rule is your job.
   Changing the rule is not: a product defect goes back as a precise report, unrepaired,
   naming the tree that owns it. A session that repairs the tree it measures cannot be cited
   for the measurement.
4. **Never add a root dependency.** `docs/program/P02_LOCK.json` is the pinned set.
5. **Never add bytes to a corpus.** `fixtures/synthetic/ar/**` and
   `fixtures/validation/PC-02/**` are frozen evidence; adding to either invalidates a
   measurement already taken. Build the bytes your test needs inside the test — wave 9's
   zero-page PDF is 311 bytes and `pypdf` writes it in three lines.
6. **Do not create a tag, and do not push or merge to `main`.**
7. **Check every premise in this brief against the tree.** Eight stale premises have been
   recorded in this programme, several in dispatch briefs written by the integrator who
   wrote this one. If something here is wrong, **say so in your report** — that is a useful
   finding, not an inconvenience.

## Your gate

```
make gate
```

It runs `make foundation`, the canonical battery, the frontend suite and `git diff --check`,
and fails if any fails. It replaced four things a wave had to remember;
`OPERATING_CONSTRAINTS.md` §7 names the Makefile as the authority. Expect **816 passed / 5
skipped / 116 subtests** before you add anything.

`tests/contract` and `tests/checkpoint` are CP-00 historical evidence, red before you start
and quarantined by `PROTOTYPE_PROFILE.md` §6.3. Not your gate.

A linked worktree has no `web/node_modules` — it is git-ignored. Run `npm --prefix web ci`
once; the gate will not borrow another checkout's modules and says so.

## Environment

Instance `gate-w10a`, `POSTGRES_PORT=55590`, `S3_API_PORT=59190`, `S3_CONSOLE_PORT=59191`,
`POSTGRES_DB=audit_w10a`, bucket `auditmanager-gate-w10a`. Ports confirmed free 2026-09-16.

Bootstrap with `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`; bare `make bootstrap`
is correctly refused under an active virtualenv. Copy `.env.example` to `.env` and set
exactly your instance; it is git-ignored and never committed.

You need **no live provider**. Everything in your scope is reachable with recorded and
scripted adapters; a live call would add cost and variance for nothing.

Read `OPERATING_CONSTRAINTS.md` §9 before concluding another session interfered: §6 covers
residue, not accumulated population, and telling them apart means running your suite alone
against the same database.

## Report

`docs/program/reviews/W10-ANL.md`, and in it:

- Your `HEAD` on arrival, and whether it matched the base.
- **A table of every rule you mutated and what reddened**, including the ones that reddened
  properly. That table is the deliverable even when it is entirely green.
- Each guard you wrote, mutated red and green, with the literal you pinned and the authority
  you pinned it against.
- Every rule unreddenable *by construction*, with the argument.
- Every product defect, precise, **left unrepaired**, naming the owning tree.
- Anything in this brief that turned out to be false.
- Elapsed wall-clock.
