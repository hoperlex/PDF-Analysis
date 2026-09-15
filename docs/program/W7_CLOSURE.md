# Wave 7 closure: the gate became a command

Written 2026-09-15 by the integrator. Convergence at `75e0a5b`, base `b442840`.
**`make gate` → `GATE OK`**: foundation 35, canonical battery 803 passed / 5 skipped / 116
subtests, frontend 289, `git diff --check` clean. 3m49s end to end.

## 1. PC-01 was re-certified first

`W6-CERT`, an independent session: **PC-01 holds at `c0d7daf`.** Ten criteria, each shown
red — by downgrade, by unset configuration, by stopped containers, by `AM002` on the ledger,
and by eight mutations on an isolated `src/` copy with no tracked file edited. Live run
through the proxy: **3 of 3 seeded, 0 of 6 controls**, USD 0.038125 against the 1.00
ceiling, with the spend verified against the `model_call` row rather than read off a print.

Two things it did that a weaker pass would not have:

- **It did not accept wave 6's change on the docstring's authority.**
  `attempt_budget_exhausted` appears nowhere in `contracts/`, so it argued the case from the
  row: the old definition was a pure function of two scalars already present, so it carried
  no information while poisoning the queries it existed for. Wave 6 right, `W2-QA` wrong —
  reached independently, which is worth more than agreement taken on trust.
- **Two mutations that did not bite were chased rather than filed.** One is a real finding:
  criterion 9's safety lives in the `UNIQUE` constraint and the `IntegrityError` recovery,
  not in `CommandStore.begin`'s pre-read, whose removal leaves the suite green.

`W5CERT-DEF-1` was exercised for the first time and works: the credential resolved from
`/root/w6cert`, the layout that made `W5-CERT` error.

## 2. The gate was three quarters convention

A wave gate is four things and only one was a target. `make foundation` was in the Makefile;
the canonical battery, the frontend suite and `git diff --check` lived as prose in
`OPERATING_CONSTRAINTS.md` §7.

**It had already cost something.** The frontend is a delivered part of PC-01 and had not been
run since wave 2 — four waves, three of which changed values it renders — because no target
named it. I checked three hypotheses about what might have broken and **all three were
wrong**: `truncated` is a `model_call` status, not a run state, so the UI's vocabulary was
never stale; `terminal_reason` is rendered raw, so wave 3's improvement reached the user by
itself; and `FRONTEND_LOCK.json` matches `openapi.json` byte for byte with all four
generated files in sync. 289 of 289 pass, as at wave 2.

So nothing was broken. **My gate would not have told me if it were**, and that is the part
worth fixing.

`make gate` now runs all four, with the two CP-00 quarantine ignores applied in the target
instead of by each caller. `run_frontend` **fails rather than skips** when npm or
`node_modules` is missing, and refuses to borrow another checkout's modules: a linked
worktree is exactly where `package.json` may differ from the tree those modules were
installed for, so borrowing would run an undeclared dependency set while looking like a pass.

**Failure propagation was proved without arranging it.** The first run in a linked worktree
failed at the frontend step and make reported `Error 1` rather than continuing — the exact
property the target exists for. The empty-run guard is shown reachable too: pytest exits `5`
on a directory with no tests, and `5` is the status that looks like nothing went wrong.

§7 now names the Makefile as the authority and itself as the defect if the two disagree.

## 3. Two more stale records, both of the wave-6 shape

- **`W6CERT-DEF-1`** — the c10 unavailable-provider test carried two observations in its
  docstring rather than assertions. **Wave 3 fixed both, and the text went on describing the
  defect for three waves.** The mirror of `W2-QA` pinning a stale value: a recorded
  observation drifts silently in whichever direction the code moves. They are assertions
  now, proved load-bearing by M12 — revert `_reason_for` and the test reddens with its own
  message.

  One correction to `W6-CERT` here, found by writing the assertion: only the
  `terminal_reason` half had gone stale. The stage's own `error_code` is also
  `dependency_unavailable` today, and the frozen document requires it — `StageState`'s
  description reads "null exactly when the status is `succeeded`".

- **`W6CERT-DEF-2`** — `",live," in text or text.count("live") >= 1` was satisfiable by the
  letters "live" appearing anywhere, including inside a quotation the model wrote. Replaced
  by parsing the declared `provider_mode` column. Shown to discriminate on a real recorded
  export, **without a live run**, so proving a live-path assertion cost nothing.

## 4. Routed, not fixed

`W6CERT-DEF-3` and `-4`: `tests/contract` and `tests/checkpoint` cannot run from a linked
worktree (`copytree` meets `.git`, which is a file there), and neither venv carries their
dependencies. That is CP-00 quarantine material, excluded from the gate by
`PROTOTYPE_PROFILE.md` §6.3, and no PC-01 criterion is affected. It belongs to the CP-00
line, which is an independent obligation.

Also named and left alone: the executor's run/adapter mode cross-check is defence in depth
rather than the guard criterion 4 exercises — the refusal fires earlier, in
`bootstrap/adapters.py`. Its comment claiming to be "the only place" overstates it.

## 5. Three stale premises in my own brief, one of them a repeat

`W6-CERT` found all three and all three are mine.

The gate figure said 793; it was 803 — carried from the previous brief instead of measured
on the tree wave 6 had just changed. The provisioning paragraph still said `origin/main` was
parked at `6d3c0f3`, which the owner had moved hours earlier on my own recommendation.

**The third is the one that matters.** The brief said an accepted limit was "a claim about
exactly that code [which moved]". The code did not move. `W5-CERT` established that, wrote
the correction in its own report — and I copied the uncorrected sentence into the next
brief. **A record that had been fixed un-fixed itself, because the brief was written from
the old text rather than from the report that corrected it.**

That is the sixth instance, and the first where the correction already existed and was
discarded in the copying. The lesson is narrower than "check your premises": **a template is
a record, and copying one carries its errors forward past the report that fixed them.** The
brief is corrected in place, not just described here, because it is what the next
certification will be built from.

## 6. Version fixation

`origin/dev` advances to the wave-7 merge. **`origin/main` stays at `8f418e9`.**

`W6-CERT` certified `c0d7daf`, and `src/` and `db/` are byte-identical between `c0d7daf` and
this tip — wave 7 changed the Makefile, two tests and two documents, and nothing else. So
`main` can advance to carry the newer certification whenever the owner says so; it is the
same situation as after wave 5, and the same decision.

## 7. Still owner-blocked

- **`OD-18`** — three to five named experts with committed slots. `P4-BHV-01` waits on this
  alone.
- **`OD-17`** — the next corpus shape; PC-02's precision evidence is saturated.
- **The 21st error code.**
- **Whether `origin/main` advances** to `c0d7daf` or later.
