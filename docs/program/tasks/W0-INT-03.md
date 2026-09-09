# Task W0-INT-03 — primary reviewer: symbolic review, ratification and the superseding tag

> **Reserved for the primary reviewer. The program orchestrator prepares this file and
> does not execute it.** Nothing in this task may be performed by the agent that produced
> the candidate: the whole point of the barrier is that ratification is decided by someone
> who did not build the thing being ratified.

## How to read this file

**Part I instructs. Part II does not.** Everything an executor performs, and every path
and value it writes, is in Part I and is stated there exactly once. Part II records how
each of those instructions was arrived at, what was measured, and which earlier claims
were withdrawn; it is provenance, and **no step is to be taken from it**.

If Part I and Part II ever disagree, **Part I is the instruction and the disagreement is
a defect in this file**: name it and `REJECT`. The same rule holds for the execution
plan: `docs/program/EXECUTION_PLAN.md` is background, and where it and Part I differ,
Part I governs this task.

This file's seventh round left every correction standing beside the instruction it
corrected, and an executor reading the ordered sequence was sent to void the round it was
ratifying. Rounds eight's rule, applied throughout: **where a correction supersedes an
instruction, the instruction is gone.** Not annotated — gone.

---

# Part I — the instruction

## Outcome

CP-00 is either ratified on an exact commit and published as a new annotated tag
`v0.0.1-architecture`, or rejected with named blockers routed to owners. The decision is
the primary reviewer's and rests on their own re-execution of the evidence, not on the
orchestrator's report.

## Depends on

- `W0-QA-04`, accepted and integrated
- `W0-INT-02`, accepted and integrated — its integration commit is the candidate SHA

## Frozen inputs

- domain contract: `contracts/domain/v1/**` at `1.0.0-draft.1`, candidate revision 5
- API contract: none exists at CP-00
- analysis/comparison/event contract: `contracts/analysis/v1/**`, `contracts/events/v1/**` at `1.0.0-draft.1`
- migration head: `none`
- base commit: the round-eleven freeze commit `F`, supplied at handoff
- immutable reviewed candidate: `92e13fa496a723ed6e4c3adbf138c4f4e1d7c368`
- local tag `v0.0.0-architecture` on `39a3a6430bd97c38cb20bafc793fc9d077d0df8e` —
  **immutable, not accepted, never moved, never published**

## Allowed paths

**Twenty-two paths, and this list is the licence.** It is derived from the path set the
procedure below writes, and every member was checked against the module's own ceilings
rather than asserted. Take the path set from here and from the procedure; they agree by
construction, and if they ever do not, that is a defect in this file: name it and
`REJECT`.

The checkpoint bundle and its records — ten:

- `artifacts/checkpoints/CP-00/manifest.json`
- `artifacts/checkpoints/CP-00/acceptance.md`
- `artifacts/checkpoints/CP-00/automated-summary.txt`
- `artifacts/checkpoints/CP-00/build-info.json`
- `artifacts/checkpoints/CP-00/checkpoint-report.md`
- `artifacts/checkpoints/CP-00/contract-manifest.yaml`
- `artifacts/checkpoints/CP-00/known-risks.md`
- `artifacts/checkpoints/CP-00/manual-test-report.md`
- `artifacts/checkpoints/CP-00/migration-head.txt`
- `artifacts/checkpoints/CP-00/restore-or-rollback-note.md`

The eight of those other than `manifest.json` and `acceptance.md` are exactly
`CHECKPOINT_DELIVERABLE_PATHS`, the bundle the freeze retracts and this act restores.
**All eight, enumerated, with no member left to inference.**

The whole of `RATIFICATION_DELTA_CEILING` — five, because `_ratification_record` refuses
a record that declares a subset:

- `docs/architecture/ADR_INDEX.md`
- `docs/architecture/ARCHITECTURE_LINT_RULES.md`
- `docs/architecture/CP00_ARCHITECTURE_REVIEW.json`
- `docs/architecture/CP00_ARCHITECTURE_REVIEW.md`
- `docs/architecture/CP00_OWNER_DECISIONS.md`

The program records — seven:

- `docs/program/CHECKPOINT_REGISTRY.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/waves/W0.3_ratification_integration.md`
- `docs/program/tasks/W0-INT-01.md` — **status banner only**
- `docs/program/tasks/W0-INT-03.md` — **this task's own status banner and its handoff,
  and nothing else.** `_task_banner_problems` compares the rest of the file with the
  frozen tree byte-for-byte
- `docs/stages/S00_architecture_and_behavior_freeze.md`
- `docs/INDEX.md`

And one ref, which is not a path: the annotated tag `v0.0.1-architecture`.

**Twenty-one of the twenty-two are inside `POST_FREEZE_DELTA_CEILING`.** The exception is
`docs/program/tasks/W0-INT-03.md`, which the **use site** licenses rather than the
ceiling: `_post_freeze_delta_problems` licenses
`set(POST_FREEZE_DELTA_CEILING) | _declared_evidence_paths(manifest) | {RATIFYING_TASK_FILE}`,
and `RATIFYING_TASK_FILE` is `f"docs/program/tasks/{RATIFYING_TASK}.md"` — derived from
the resolved task, not written down. **That licence exists only if the reassignment
happened in the freeze.** Step 0.3 is the check that it did, and it is the single most
consequential check in this file.

Measured on the integration tip's module, `tests/**` at `29179c6`: the ceiling has 37
members; the sixteen it holds which this delta does **not** write are the sixteen
completed task banners other than `W0-INT-01`'s, and they are out for the reason given
under "Not in the delta, deliberately". Nothing else in the ceiling is unaccounted for.

**Two paths that are *not* licensed here and were in an earlier form of this list:**

- `artifacts/checkpoints/CP-00/erratum.md` — **removed.** It is outside
  `POST_FREEZE_DELTA_CEILING` and outside `_declared_evidence_paths`, so it is licensed
  by nothing after the freeze: editing it here makes it an unlicensed post-freeze path
  and **voids round eleven**. It is created by `W0-INT-02`, committed by the integrator,
  and final in `F`. This task does not write it. What would otherwise have been written
  there goes in `manifest.json` under `supersession`, which is a ceiling path — see
  step 2.7.
- `artifacts/checkpoints/CP-00/{manual,automated}-report-round-11.md` — **not this
  task's.** The acceptance streams write them against `F` before this task runs, and
  `_declared_evidence_paths` licenses them in the post-freeze delta once the manifest
  declares them for round eleven. This task **verifies** them at step 0.4 and never
  writes them. A ratification commit that creates or edits either is producing the
  evidence it is judging, which is the barrier this whole task exists to hold.

## Forbidden hotspots

- `contracts/**`, `fixtures/**`, `scripts/**`, `tests/**`
- `artifacts/checkpoints/CP-00/erratum.md` — for the reason above
- `artifacts/checkpoints/CP-00/check_state_records.py` — deliberately outside the
  ceiling; it is a tool, not evidence, and editing it after a freeze voids the round
- every evidence record other than the paths listed above
- every historical round report, and `docs/program/reviews/W0-QA-01.md`
- `v0.0.0-architecture`: not moved, not deleted, not re-pointed, not published

## Non-goals

- No remediation. A reviewer who finds a defect routes it to its owner and rejects; they
  do not fix it. Fixing what you are reviewing destroys the independence the barrier buys.
- No new task, no scope change, no plan edit.
- No edit to `tests/**` under any circumstance, including to turn a red guard green.

## The procedure

Six steps. Steps 0 and 1 decide; steps 2 to 5 execute and are reached only on `ACCEPT`.

### Step 0 — verify what must already be true. Build nothing.

Everything in this step is a **check on work someone else did**. If any check fails, this
task returns `REJECT` naming the failure and its owner; it does not adjust the delta, and
it does not repair `tests/**`.

**0.1 — the module still resolves the tag rather than pinning it.**

```
grep -n 'v0\.0\.0-architecture' tests/contract/test_cp00_candidate.py
```

The failure this looks for is **one specific line shape**: an equality asserting the
module's *live resolved* tag value against the literal — `assertEqual(CHECKPOINT_TAG,
"v0.0.0-architecture")`. That is what stood at `:11342` on `W0-INT-02`'s base `6135f17`
and what `4e916b0` removed. Every other hit is legitimate and you should expect several:
the floor constant `CHECKPOINT_TAG_FLOOR` and the assertion that pins it, prose comments,
a live `assertIn` naming the old tag as the *subject of a historical annotation*, and
`_tree(...)` fixtures feeding the resolver its own test cases. Measured on the final
module, `tests/**` at `5d07fe3`: **eleven** hits, of which one is the floor constant at
`:222`, one pins the floor at `:12424`, five are comments, one is the historical `assertIn`
needle at `:8314` and three are resolver fixtures at `:12535`, `:12545` and `:12575`.
**Judge the shape, not the count.** The count no longer moves — `tests/**` is final — but
it is the line shape that decides: an equality against the literal is the pin, and no
other hit is.

If the pin is back: `REJECT`, owner `W0-QA-04`.

**0.2 — the ratifying task is resolved from the records, not pinned.**

```
grep -n 'RATIFYING_TASK *=' tests/contract/test_cp00_candidate.py
grep -n 'RATIFYING_TASK_FLOOR\|RATIFYING_TASK_SERIES\|_resolved_ratifying_task' \
     tests/contract/test_cp00_candidate.py
```

If the first shows a task id assigned as a literal, the old pin is back: `REJECT`, owner
`W0-QA-04`. If it shows a call to `_resolved_ratifying_task`, proceed.

**0.3 — the act was reassigned inside the freeze. This is the licence check.**

`_ratifying_task_claims` reads **exactly two** records: `manifest.json`'s
`ratification.task`, and the W0.3 wave plan's single row containing
`CP-00 review ratification`. The round-eleven opening removes the `ratification` object,
so on `F` **the wave plan's assignment row is the only claim there is**. `RATIFYING_TASK`
resolves from it; `RATIFYING_TASK_FILE` is derived from `RATIFYING_TASK`; and
`docs/program/tasks/W0-INT-03.md` — a file this act is *required* to rewrite, because
`_task_banner_problems` moves the ratifying task's banner in both directions — is
licensed in the post-freeze delta by nothing else.

Run this on `F`:

```
.venv/bootstrap/bin/python -c "import sys; sys.path.insert(0, 'tests/contract'); \
import test_cp00_candidate as t; print(t.RATIFYING_TASK, t.RATIFYING_TASK_FILE)"
```

It must print `W0-INT-03 docs/program/tasks/W0-INT-03.md`.

If it prints `W0-INT-01`, the wave plan's assignment row was not moved into the freeze.
**Stop. `REJECT`, owner the integrator.** Do not proceed and do not move the row now:
`W0-INT-03.md` would then be an unlicensed post-freeze path, and
`_post_freeze_delta_problems` reports *"round 11 is void: these paths differ from the
tree frozen at … and nothing licenses them: ['docs/program/tasks/W0-INT-03.md']"*. The
round is spent and a new one must be opened.

Two freezes differing **only** in that row were measured. Both pass the rest of step 0
and both return `[]` from all twelve root-argument checkers; the one with the row moved
gives `_post_freeze_delta_problems` = 0 and the one without gives 1, naming that file.
**The row is not cosmetic and it is not part of this delta.** It moves in the freeze.

**0.4 — `F` contains what a round-eleven freeze must contain.**

Twelve items. Check each; `REJECT` naming any that is missing. Owner throughout is
`W0-INT-02` and the integrator — never `W0-QA-04`, and never this task.

1. **The wave plan's `CP-00 review ratification` assignment row names `W0-INT-03`.**
   Exactly one row contains that string and exactly one task id appears in it. This is
   step 0.3, listed again here because this list is what a reviewer checks `F` against
   and an item absent from it is an item nobody checks.
2. **The round-eleven opening**, in `manifest.json`: `ratified: false`; the top-level key
   literally named `ratification_blocked` restored; the `ratification` object removed;
   `tag` and `tag_planned` at `v0.0.1-architecture`; round ten marked `void` with its
   sealed digests untouched; a round-eleven entry; `current_round: 11`; and
   `artifact_manifest_sha256` recomputed. Built from the **tip** manifest, not from the
   frozen one, or `_retro_edited_digests` catches round ten's `evidence_bundle_digest`
   being blanked.
3. **All eight bundle deliverables retracted** from the frozen tree — the eight named
   under Allowed paths — and round ten's `automated_report` claim retracted *with* them,
   or the contour reports a claim on a path the tree does not track.
4. **The reviewed-family files returned to a pre-ratification state.** Which files, and
   from which revision, is a legitimate choice the integrator makes at the freeze — see
   step 2.2, which tells you how to find out which one you have.
5. **The denials restored, resolved to `W0-INT-03`**: the wave plan's two forms
   (`` `W0-INT-03` is blocked `` and `` | `W0-INT-03` | blocked | ``), `docs/INDEX.md`'s
   `program/tasks/W0-INT-03.md` row, and `W0-INT-03.md`'s own banner carrying
   `RATIFYING_TASK_BANNER_DENIAL`. These are **denials**; item 1 is an **assignment
   row**, a third and different string in the same document, and the two are not
   substitutes.
6. **`docs/INDEX.md` carries the literal `specified; blocked on acceptance`.**
   `_CheckpointSandbox.publish_program_documents` retracts that exact string and, unlike
   the wave plan's, it is **not** resolved through the `{task}` placeholder. Any other
   wording of a denial that satisfies `_publication_record_problems` still aborts the
   harness.
7. **No denial phrase straddles a blockquote line break.** `_flat` normalises whitespace
   but leaves the `>` markers, so `ratification and\n> publication blocked` does not
   match. Measured: the phrase on one line takes `_task_banner_problems` 1 → 0.
8. **No licensed banner names `v0.0.1-architecture` while `ratified` is false** — the
   anti-vacuity half of `_task_banner_problems`. This lands on the ten banners
   `W0-INT-02` writes.
9. **The registry's CP-00 row rewritten, not restored**: it cites `ratification_blocked`
   in a code span, its status cell carries a non-terminal token (`open`/`owed`/`blocked`),
   and it names no round but eleven. A restored row says round ten is owed.
10. **The wave plan and the S00 checklist do not carry `S01`, and the S00 boxes are
    unticked**, while `ratified` is false.
11. **`W0-INT-03.md`'s body is final.** Its banner is the one part that may move after
    the freeze; `_task_banner_problems` compares everything outside the banner, and
    outside this task's `## Handoff`, byte-for-byte with the frozen tree.
12. **Every path outside the ceiling that anything still needs to write is already
    written.** `docs/program/EXECUTION_PLAN.md`, `docs/program/reviews/**`,
    `docs/program/tasks/{W0-INT-02,W0-QA-04,W1-GOV-00}.md`, the `tests/**` modules and
    `artifacts/checkpoints/CP-00/erratum.md` are licensed by nothing after the freeze.
    This is how round ten died.

**The digest order inside the freeze is load-bearing.** Every other computed value —
`artifact_manifest_sha256` first — then `git add -A`, then `tested_candidate_digest`,
then the commit. `_digest_paths` reads `git ls-files --cached`, so an unstaged deletion
leaves a retracted path in the recipe's set and the digest raises `FileNotFoundError`;
and computing the tested digest before writing `artifact_manifest_sha256` invalidates it,
because the manifest participates in its own digest with only the field being computed
blanked. This is the integrator's step and is stated here so the reviewer can check it.

**0.5 — the two round-eleven primary reports exist, and are the streams'.**

`_canonical_report_paths` honours exactly two names and a prefix will not do:
`artifacts/checkpoints/CP-00/manual-report-round-11.md` and
`artifacts/checkpoints/CP-00/automated-report-round-11.md`. A report filed under any
other name is not licensed by the round however the manifest names it.

Each must declare its subject commit **within its own first 26 lines** —
`cp00_final_state.py` pins `HEADER_LINES = 26` and searches that head with
`SUBJECT_DECLARATION` — and the value must be `F` in both. Since `F` does not exist until
the freeze is committed, **the reports cannot have been written before it**; a report
declaring anything else is judging a different tree.

Both must carry a real verdict token **and both must carry `PASS`**, a declared
non-placeholder tester, and no placeholder tokens: since `29179c6` the reports are read,
not merely counted. The `PASS` clause is not redundant with step 2.10: 2.10 writes both
streams `PASS` into the ratified manifest, so without it a stream that filed `FAIL` on a
freeze this file calls expectedly red would satisfy a presence rule here and have its
verdict overwritten there. **This task does not write a verdict a stream did not file.**

If either is missing, misnamed, declares a commit other than `F`, or carries any verdict
other than `PASS`: `REJECT`, owner the acceptance streams and the integrator.

### Step 1 — the symbolic review, on `F`

Re-execute the evidence yourself, on the freeze commit, in the main checkout or a `cp -a`
copy of it. **Never in a `git clone` and never in a linked worktree** — the suite copies
the working tree, and `.venv/` is gitignored with zero tracked files, so a clean clone has
no `.venv/bootstrap/bin/python` and every command below fails before it measures anything.

The expected result on `F` is **not** exit 0, and that is the recorded state of the
mechanism rather than a defect in this delta. **It is four failures, and these are their
names:**

- `TagIntegrityTests.test_the_tag_has_not_moved_and_its_message_is_true_of_its_commit`
- `TableExpectationTests.test_the_checkpoint_tag_resolves_and_the_rule_can_fail`
- `CrossGateAgreementTests.test_the_two_ratification_gates_agree`
- `test_a_publication_document_missing_its_statement_or_its_subject_is_named`

Each is inherent to a freeze commit: the tag does not exist until step 3, the bundle the
tag rule reads is retracted at the freeze, the two gates are *made* to agree by the
ratification, and `evidence_bundle_digest` does not reproduce on `F`. **Compare failure
names against those four; treat any name not on the list as a finding.** Why each is
inherent, and why nothing in this delta closes any of them, is in "What remains red on
`F`" in Part II.

`REJECT` ends the round: it is spent, and the integrator opens round twelve.

### Step 2 — the ratification commit

One commit. **Three orderings inside it are load-bearing and each fails silently if it is
broken**; they are the whole of what is forced, and they were measured:

- **(a)** `artifact_manifest_sha256` is recomputed **after** the last `docs/architecture`
  write. Computing it before describes a tree that no longer exists.
- **(b)** `evidence_bundle_digest` is computed **last**, after `git add -A`. Anywhere
  else and it does not reproduce.
- **(c)** the bundle files are written **after** the reconciliations, or
  `contract-manifest.yaml` carries the pre-ratification reviewed-family digest.

The order below satisfies all three. Vary it if you must; do not break them.

**2.1 — `manifest.json`, the `ratification` object.** `task: "W0-INT-03"`,
`decided_on`, `decided_by`, `reason`, and `allowed_delta_paths` naming **the whole of
`RATIFICATION_DELTA_CEILING` — all five files, never a subset.** `_ratification_record`
computes `understated = RATIFICATION_DELTA_CEILING - set(declared)` and reports a record
that declares fewer as inadmissible; and on any problem it returns an **empty** allowed
set, so an inadmissible record licenses nothing and all five reconciliations then read as
undeclared drift.

`task` is `W0-INT-03`. **It may not be left at `W0-INT-01` to keep a check green** — that
records the task which did not perform the ratification as having performed it, a false
statement about the actor bought for a green suite. It agrees with the wave plan's row,
which moved in the freeze; this object is the second of the two records and writing it
here makes them agree. **The wave plan's assignment row is not written in this commit.**

This is first because everything after it is a reconciliation that this record licenses.

**2.2 — the five `docs/architecture` ceiling files.**

`F` reverted these; this act re-makes them. All five are in the delta and all five are in
`allowed_delta_paths`. `_reconciliation_problems` requires each of the four
`RECONCILIATIONS` entries — `CP00_ARCHITECTURE_REVIEW.md`, `CP00_OWNER_DECISIONS.md`,
`ARCHITECTURE_LINT_RULES.md`, `ADR_INDEX.md` — to have its named stale claim gone and its
replacement present; `CP00_ARCHITECTURE_REVIEW.json` is the fifth ceiling file and carries
`review_status`.

**Two freezes are legitimate here and you must find out which one you have** rather than
assume. `review_status` is not forced back by the freeze: restoring the four to their
round-ten-freeze content while leaving `review_status: "ratified"` in place gives
`_reconciliation_problems` = 0, so the JSON may cross `F` unchanged. Reverting it with
the rest is equally reachable. Ask `F`:

```
git show <F>:docs/architecture/CP00_ARCHITECTURE_REVIEW.json \
  | .venv/bootstrap/bin/python -c "import json,sys; print(json.load(sys.stdin)['review_status'])"
```

- prints `ratified` → the JSON crosses `F` unchanged; here it is a **confirmation**, and
  you write the four.
- prints anything else → the JSON was reverted; here it is a **write**, and you write all
  five.

`CP00_ARCHITECTURE_REVIEW.md` is a write in **both** cases: the PD-02 sentence is one of
the four reconciliations. `_review_consistency_problems` requires the Markdown to quote
the JSON's value verbatim as a code span, so the JSON and its three quotations move
together or the suite goes red.

**2.3 — recompute `artifact_manifest_sha256`. Confirm; do not edit.**

This is a real recomputation and not a formality. Run the manifest's own recipe over the
reviewed families *after* the last write of step 2.2. On the reconciled tree it reproduces
`a78572288a28b88be7f5dd58b9e79254a9e4f61cb55838ba4308b3be91109b84` over 100 files, which
is what `manifest.json`, `contract-manifest.yaml` and `build-info.json` already publish —
`W0-INT-02` set the field to the ratification-tree value, and step 2.2 is what brings the
tree back to it. So the expected outcome is **no edit**.

If it does not reproduce, **stop**. The reconciliations are incomplete. Do not edit a
digest to make a row true.

One latent property, stated because nothing else states it: this value is computed while
`HEAD` is still `F` and checked when `HEAD` is the ratification commit. It converges only
because this act adds and removes no file in the four reviewed families. If your delta
adds one, this step is wrong and so is the field.

**2.4 — `docs/program/CHECKPOINT_REGISTRY.md`.** The CP-00 row: round eleven, the new
tag, the accepted commit, and the code span moved from `` `ratification_blocked` `` to
`` `ratification` ``. `_registry_state_problem` compares the cited token against
`manifest.ratified` and reads the identifier, not the prose.

**2.5 — `docs/program/CURRENT_STATE.md`.** The denial `Nothing is ratified, nothing is
tagged` removed; the active checkpoint is `v0.0.1-architecture` and no round is owed.

**2.6 — `docs/program/waves/W0.3_ratification_integration.md`,
`docs/stages/S00_architecture_and_behavior_freeze.md`, `docs/INDEX.md`.**

The wave plan: its two denial forms retracted, the S01 preparation tasks named, and the
`{task}` code span and a tag of the series still present — `must_still_contain` is
anti-gutting and refuses a retraction made by deleting what the claim was about. The S00
checklist: `S01` named and every automated and manual exit-criterion box ticked.
`docs/INDEX.md`: the `program/tasks/W0-INT-03.md` row reads `accepted and integrated`.

**The wave plan's `CP-00 review ratification` assignment row is not touched here.** It
already names `W0-INT-03`; it moved in the freeze; changing it now moves a record that is
already correct.

**2.7 — `docs/program/tasks/W0-INT-01.md`, status banner only**, naming
`v0.0.1-architecture` — the tag the ratification it records publishes.

**2.8 — `docs/program/tasks/W0-INT-03.md`, status banner and handoff only.** The banner
closes: `RATIFYING_TASK_BANNER_DENIAL` gone, `v0.0.1-architecture` named. This is the file
licensed by `{RATIFYING_TASK_FILE}` and by nothing else; everything outside the banner and
`## Handoff` must be byte-identical to `F`.

**2.9 — the eight bundle files**, all of them, restored and current:

- `checkpoint-report.md` — the `Tag:` line and the verdict section state
  `v0.0.1-architecture` and round eleven
- `contract-manifest.yaml` — `tag:` at `v0.0.1-architecture`, and the reviewed-family
  digest recomputed from the tree, which lands back on the value of step 2.3
- `build-info.json` — `tag_planned` at `v0.0.1-architecture`, and the same digest.
  `build-info.json:tag_planned` is **not** one of the three claims `_checkpoint_tag_claims`
  resolves the tag from, so leaving this file alone would not red the tag checks; it would
  red `cp00_final_state.accounting_problems`, as two live records giving one top-level
  field two values. That is why the file is named here rather than left to the tag checks
- `automated-summary.txt` — regenerated for round eleven, declaring its own subject
  commit, carrying `round 11` and `PASS`
- `manual-test-report.md` — round eleven's manual report, not round ten's
- `known-risks.md` — the procedural-residue paragraph counts eleven rounds, not ten
- `restore-or-rollback-note.md` — restores to `v0.0.1-architecture`, and its "Publication
  state" paragraph no longer says the checkpoint is unpublished
- `migration-head.txt` — restored; the whole file is the literal `none`

Also here, and in `manifest.json` rather than in the erratum: the `supersession` record
of the `T-1`, `T-2` and `T-3` tag dispositions, which are recorded in `erratum.md` as open
against a tag this act supersedes. `erratum.md` is unlicensed after the freeze; the
manifest is a ceiling path; this costs nothing.

**2.10 — `manifest.json`, the ratified state.** Written together, because `classify`
reads them as one state and any of them alone leaves the tree `unclassified`:

- `ratified: true`
- `status: "ratified"`
- round eleven's entry `status: accepted`, `verdict: "PASS"`, both streams `PASS`, the two
  canonical report paths, and `candidate_frozen_at_commit`
- `tag` and `tag_planned` already read `v0.0.1-architecture` from the freeze; confirm them
- `manual_acceptance` and `automated_acceptance` moved to round eleven
- the top-level key `ratification_blocked` **may** be dropped as spent history or kept.
  `_registry_state_problem` deliberately does not read key presence — "a ratified one may
  drop `ratification_blocked` as spent history" — and
  `RatificationRecordTests.test_the_comparison_does_not_depend_on_manifest_history` requires the
  verdict to be the same either way. Dropping it is recommended, because a key of that name
  in a ratified manifest is a false statement no check happens to read; keeping it costs
  nothing. Find the test by symbol, not by line.

**`tested_candidate_digest` is not written in this commit.** It is `F`'s value, sealed at
the freeze at the top level and in the round-eleven entry, and `_tested_digest_problems`
recomputes it over the **blobs of the freeze commit**. Rewriting it here breaks it.

**2.11 — `artifacts/checkpoints/CP-00/acceptance.md`.** The round-eleven row becomes an
accepted `PASS` row under `## Rounds`.

**2.12 — `git add -A`, then `evidence_bundle_digest`, last.** The recipe blanks only the
field being computed, at the top level and in every `acceptance_rounds` entry. Write it,
then commit. This is commit `R`.

### Step 3 — the tag

An annotated `v0.0.1-architecture` on `R`, created after the commit and pointing at it.
Its message states only claims true of that commit. `v0.0.0-architecture` is not moved,
not deleted, not re-pointed.

### Step 4 — verify `R`

```
.venv/bootstrap/bin/python -m unittest discover -s tests/contract
.venv/bootstrap/bin/python -m unittest discover -s tests/checkpoint
.venv/bootstrap/bin/python tests/checkpoint/cp00_final_state.py --tag v0.0.1-architecture
.venv/bootstrap/bin/python tests/checkpoint/cp00_final_state.py
```

**The third and fourth commands must produce identical output, and the comparison is the
check.** `--tag` defaults to `None` and resolves through `contour.recorded_tag(tree)`, so
on a tree whose records all name the successor the default and the explicit flag ask the
same question. If they disagree, the contour's default resolution has drifted from the
records this delta just moved: `REJECT`, owner `W0-QA-04`. A figure is not written here
because `W0-QA-04` may work the same module again.

The third command names an owner for every finding it reports. **A finding owned by
anyone other than `W0-INT-03` after the ratification means this delta is wrong, not that
the finding may be waived.**

The first two commands are **expected to be empty at `R`, and that expectation is
unverified**: the round-eleven ratification commit does not exist, because building it
means opening round eleven and holding both round-eleven primary reports, which no task may
do before the streams have run. (Round eight's review built a freeze and a ratification
commit of its own to test this file as its executor. That is a review measurement, taken on
a tree with part of step 2 deliberately unwritten, not the `R` these two commands
describe.) Treat a non-empty result as a finding to be diagnosed against the
two causes recorded in Part II and reported — not as a state this file has predicted.

### Step 5 — publish

`main`, the integration branch and the new tag, as one verifiable operation, without force
and without moving any existing ref.

## Deliverables

1. A symbolic review verdict — binary `ACCEPT` or `REJECT`. Every rejection names the
   blocker, its `path:line`, and the owning task to reopen.
2. On `ACCEPT`: the ratification commit applying exactly the twenty-two paths above.
3. On `ACCEPT`: an annotated tag `v0.0.1-architecture` on the exact accepted commit, whose
   message states only what has been measured.
4. On `ACCEPT`: publication of `main`, the integration branch and the new tag, as one
   verifiable operation.

## Required tests

Re-executed by the reviewer, in the main checkout or a `cp -a` copy of it. **Never in a
`git clone`** — the suite copies the working tree, and a clone has no
`.venv/bootstrap/bin/python` because `.venv/` is gitignored with zero tracked files, so
every command here fails before it measures. **Never in a linked worktree, and never while
anything else clones this repository.**

**Every claim in this file about how `tests/**` behaves names the commit it was taken on**,
because `W0-QA-04` moved this module underneath earlier figures more than once. It has
stopped moving: `W0-QA-04` is closed at `5d07fe3`, `tests/**` is final, and there is no
licensed writer left, so the figures below are the last ones this file needs. They were
taken with the module at `5d07fe3`. Re-derive rather than trust: symbols with `grep`,
behaviour by running the command.

**On `F`, at step 1:**

- Command: `.venv/bootstrap/bin/python -m unittest discover -s tests/contract`.
  Expected: **not exit `0`, and this is the recorded state of the mechanism rather than a
  defect in the delta.** Measured on a round-eleven freeze `F` built to step 0.4, with
  `tests/**` at `5d07fe3`: `Ran 346 tests`, `FAILED (failures=4)`, exit 1 — four, and all
  four are inherent to a freeze commit. That figure is the round-eight review's, taken on
  the checkout at `4a1610c` and recorded in `EXECUTION_PLAN.md` §3.18; its contour half,
  `Ran 346`, was re-taken for round nine on the main checkout at `5ca78e2` with
  `W0-INT-02`'s 27 paths in a `cp -a` copy. `tests/**` is byte-identical from `5d07fe3`
  through `5ca78e2`, so the contour does not move with the documentation commits above it.
  **The expectation is the named set and nothing else**: compare failure names against the
  four named at step 1 and treat any name not on the list as a finding.
- Command: `.venv/bootstrap/bin/python -m unittest discover -s tests/checkpoint`.
  Expected on `F`: `Ran 59 tests`, `FAILED (failures=1)` —
  `RealRepositoryTests.test_the_tree_view_reads_this_repository`, which reads the live
  tree and cannot pass at a freeze that is by construction unratified.

**On `R`, at step 4:**

- Command: `.venv/bootstrap/bin/python -m unittest discover -s tests/contract`.
  Expected: exit `0`. **Unverified** — see step 4.
- Command: `.venv/bootstrap/bin/python -m unittest discover -s tests/checkpoint`.
  Expected: exit `0`.
- Command: the two `cp00_final_state.py` runs of step 4.
  Expected: identical output; every finding owned by `W0-INT-03`.
- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`.
  Expected: exit `0`, standalone `PASS`.
- Command: the exact ratification assertion recorded in `W0-INT-01`.
  Expected: exit `0`.
- Command: `git rev-list -n1 v0.0.0-architecture`.
  Expected: `39a3a6430bd97c38cb20bafc793fc9d077d0df8e` — proof the old tag did not move.
- Command: `git merge-base --is-ancestor origin/main HEAD`.
  Expected: exit `0` — the publication is a fast-forward and needs no force.
- Command: `git ls-remote --tags origin`.
  Expected: no `v0.0.1-architecture` before publication; exactly one after.

## Integration contract

Downstream can rely on: `v0.0.1-architecture` is annotated, points at the exact accepted
commit, and that commit's tree is what both acceptance streams measured;
`v0.0.0-architecture` is unchanged and remains unpublished; and the tag message states
only measured facts.

## Failure/idempotency/security cases

- A second run of the ratification must be a no-op, not a second commit.
- If any required test fails, the task stops and returns `REJECT`; it does not repair.
- No force-push, no ref move, no history rewrite, under any circumstance.
- Publication is a single operation over `main`, the integration branch and the new tag.

## Rollback / feature flag

The ratification commit is revertable before publication. **After publication the tag is
immutable**: a defect found later is corrected by a further superseding checkpoint and a
new version, never by moving or deleting `v0.0.1-architecture`. That rule is what makes
the version mean anything.

## Handoff

- verdict, with every blocker's `path:line` and owning task
- on `ACCEPT`: the ratification commit SHA, the tag object SHA and its target
- commands/results: every required test, re-executed by the reviewer, with measured exit
  codes
- proof of no ref move: the old tag's target before and after
- publication result: the refs updated, and that none was forced

---

# Part II — rationale, provenance and measurement

**Nothing in this part instructs.** It records how Part I was arrived at, what was
measured and on which tree, and which earlier claims were withdrawn and why. An executor
who takes a step from this part is reading the wrong half of the file.

Every figure below names the tree it was taken on. Where this part gives a procedure
instead of a number, that is deliberate: `W0-QA-04` has moved `tests/**` twice underneath
figures written here, which is `erratum.md`, `E-13` and `L-7`.

## How the delta was established

By construction and by measurement, not by reading the plan. For each item the named
check was made to fail by leaving that item out of an otherwise complete delta, applied
to a `cp -a` copy of the reconciled tree. Two classes of item are distinguished and the
distinction is the point: an item is **machine-forced** when a frozen check fails without
it, and **truth-forced** when no check fails but a statement in the tree becomes false.

**What is machine-forced**, with the check that fires without it:

| Written at | Path | The check that fails without it |
|---|---|---|
| 2.1 | `manifest.json` | `RATIFICATION_REQUIRED_FIELDS`, `_ratification_delta_problems`, `_ratifying_task_problems` |
| 2.2 | the five ceiling files | `_reconciliation_problems`; `_review_consistency_problems` for the Markdown's three code spans |
| 2.3 | — (confirmation) | `test_the_external_record_describes_the_reviewed_families`; `cp00_final_state.tag_integrity_problems` |
| 2.4 | `CHECKPOINT_REGISTRY.md` | `cp00_final_state._checkpoint_row_problems`; `_registry_state_problem` |
| 2.5 | `CURRENT_STATE.md` | `_state_document_problems` |
| 2.6 | wave plan, S00, `INDEX.md` | `_publication_record_problems`, `_checklist_problems` |
| 2.7 | `W0-INT-01.md` | `_task_banner_problems` — "the banner does not name v0.0.1-architecture, the tag the ratification it records publishes" |
| 2.8 | `W0-INT-03.md` | `_task_banner_problems` — the ratifying task's banner moves in both directions |
| 2.9 | the eight bundle files | `_checkpoint_bundle_problems`, `_deliverable_content_problems`, `cp00_final_state.accounting_problems` (b) |
| 2.10 | `manifest.json` | `classify` / `terminal_state_problems`; `_acceptance_record_problems`; `_checkpoint_tag_problems` |
| 2.11 | `acceptance.md` | `_acceptance_record_problems` — "records round 11 as … while manifest.json declares ratified=true" |
| 3 | the tag | `cp00_final_state.tag_integrity_problems`, all three live claim checks |

**What is truth-forced** — no check fails and a statement in the tree becomes false:

| Path | What becomes false if it is left alone |
|---|---|
| `docs/program/CURRENT_STATE.md` | says the active checkpoint is `v0.0.0-architecture` and that round eleven is owed |
| `docs/program/waves/W0.3_ratification_integration.md` | says round eleven is owed and S01 opens after the superseding checkpoint is accepted |
| `docs/stages/S00_architecture_and_behavior_freeze.md` | its target-checkpoint line names the old tag and says the supersession is pending |
| `docs/INDEX.md` | the `W0-INT-01` row says the checkpoint is being superseded |
| `artifacts/checkpoints/CP-00/restore-or-rollback-note.md` | restores to the old tag, and its "Publication state" paragraph says the checkpoint is unpublished |
| `artifacts/checkpoints/CP-00/manual-test-report.md` | is the round-ten manual report standing in the accepted round's deliverable slot |
| `artifacts/checkpoints/CP-00/known-risks.md` | "Ten acceptance rounds were opened, the tenth being this closeout" — true today, false the moment `manifest.json` carries eleven |
| `manifest.json`, `supersession` | `erratum.md`'s `T-1`, `T-2` and `T-3` are recorded as open against a tag that has been superseded |

The restore note is worth a sentence. It is not machine-forced because it already names
`v0.0.1-architecture` in its rollback section — it did so before the recovery began — so
the deliverable guard, a substring test, is satisfied by that mention. `W0-INT-02` removed
the equivalent mention from `checkpoint-report.md` and from the `W0-INT-01` banner exactly
so those two guards stay sharp; it did not remove it here, because the sentence is the
rollback instruction itself.

`erratum.md` used to appear in this table. It is out of the delta entirely — see
"Why the erratum is forbidden" — and the obligation moved to `manifest.json` under
`supersession`.

## Why the reassignment happens in the freeze and not here

Four guards read the resolved ratifying task rather than a literal: `_ratification_record`,
`RATIFYING_TASK_FILE`, the `{task}` placeholder in `RATIFICATION_PUBLICATION_RECORDS`, and
the row `_publication_record_problems` reads out of `docs/INDEX.md`. Reassigning the act
therefore moves four documents' obligations onto a task that has never carried them, and
those obligations are discharged **in the freeze**.

Measured with `W0-INT-02`'s 27 paths copied into a `cp -a` copy of integrated main; `.git`
verified a real directory, never a clone and never a linked worktree; every exit code read
from the process that produced it. Each row names the tree it was taken on. `F` is a
commit, built by `EXECUTION_PLAN.md` §3.8 with §3.9.4's corrections.

| the tree | `_ratifying_task_problems` | `_ratification_delta_problems` | `discover -s tests/contract` |
|---|---|---|---|
| as `W0-INT-02` ships it, on `5ca78e2` | 0 | 0 | `Ran 346`, `failures=4`, exit 1 |
| the freeze `F`, act still `W0-INT-01` | 0 | 0 | `Ran 346`, `failures=4`, exit 1 |
| **`F` with the act reassigned inside the freeze** | **0** | **0** | **`Ran 346`, `failures=4`, exit 1** |

Row one was re-taken for round nine on the main checkout at `5ca78e2` with `W0-INT-02`'s 27
paths in a `cp -a` copy, `.git` verified a real directory and each exit code read from the
process that produced it; its four failures are the base's own, recorded in `erratum.md`
`L-1`, and they are **not** the four of rows two and three. Rows two and three are freeze
figures with `tests/**` at `5d07fe3`, from the round-eight review recorded in
`EXECUTION_PLAN.md` §3.18. Until `5d07fe3` repaired the sandbox probe all three rows read
`Ran 343`, and rows two and three read `failures=5, errors=11`; those figures are withdrawn
under "What remains red on `F`".

**The reassignment costs nothing when it is made inside the freeze.** Rows two and three
are the same four failures with the same names: moving the act adds none. That was
re-established independently in round eight — two freezes differing only in the assignment
row have identical failure sets, name for name — and no construction was found in which
the reassignment costs anything.

A fourth row stood here measuring what the reassignment costs when the act moves *after*
the freeze: round seven recorded `failures=52, errors=10` on `29179c6`, and the round-eight
reviewer, re-taking it, measured `failures=49, errors=10` and could not reproduce the
construction exactly. **The disagreement is recorded rather than resolved**, and neither
figure is relied on by anything: Part I moves the act in the freeze, so the row describes a
path the instruction does not take. What both measurements agree on is the direction and
the largest single cause — `W0-INT-01`'s banner still carrying
`RATIFYING_TASK_BANNER_DENIAL` in the tree `F` froze, which is a statement only the
resolved ratifying task may make.

**This reverses the third row of the `F-5` table, and the reason is worth keeping.** That
row measured that moving the assignment row in `W0-INT-02`'s own commit reds the suite, and
concluded the row belongs to the ratification commit. It was taken on a tree whose manifest
still carried a `ratification` object naming `W0-INT-01`: two records then disagree and the
resolver falls to the floor. The round-eleven opening removes that object (§3.8.2), so on
`F` the wave plan's row is the only claim `_ratifying_task_claims` reads, and it cannot
disagree with a second record because there is no second record. Measured on `F`:
`RATIFYING_TASK` resolves to `W0-INT-03`, the twelve root-argument `_*_problems` checkers
all return `[]`, and `_registry_state_problem` returns `None`.

**Why `W0-INT-03.md` needs that row.** The claim that the file must be final at the freeze
because it is absent from `POST_FREEZE_DELTA_CEILING` was read off a constant instead of
taken from the function that runs. The constant does not contain it; the **use site** does.
`RATIFYING_TASK_FILE` is derived, so it *becomes* `docs/program/tasks/W0-INT-03.md` the
moment the act is reassigned — and only then. Measured on two freezes differing only in the
assignment row: with the row moved, `_post_freeze_delta_problems` is `[]`; without it, it
is one finding, *"round 11 is void: these paths differ from the tree frozen at … and
nothing licenses them: ['docs/program/tasks/W0-INT-03.md']"*.

That is why step 0.3 exists and why the row is item 1 of step 0.4. In round seven the row
appeared in the ordered sequence as something this commit writes, in item 6 as something
the freeze writes, and **not at all** in the list a reviewer checks `F` against — so a
reviewer following the file would not have caught its absence, and an executor following
the sequence would have voided round eleven. That is the defect round eight was opened
for.

## Why the erratum is forbidden

`artifacts/checkpoints/CP-00/erratum.md` is inside `_digest_paths` and outside
`POST_FREEZE_DELTA_CEILING`, outside `RATIFICATION_DELTA_CEILING` and outside
`_declared_evidence_paths`. Nothing licenses it after the freeze. It is created by
`W0-INT-02`, committed by the integrator, and final in `F`; changing nothing in it keeps
it out of the post-freeze delta. **If this task edits it, it becomes an unlicensed
post-freeze path and voids round eleven** — the way round ten died, one file over.

Round seven both licensed it in Allowed paths and forbade it here, and listed it in the
truth-forced table as a path that must change. All three cannot hold. Part I resolves it
by removing it from the licence and moving the obligation to `manifest.json` under
`supersession`, which is a ceiling path and costs nothing.

## Why the two round-eleven reports are not this task's

`_canonical_report_paths` licenses exactly two names for a round, and each report must
declare `F` as its subject commit inside its own first 26 lines. `F` does not exist until
the freeze is committed, so the reports cannot precede it; and the acceptance streams
write them, against `F`, before this task runs.

Round seven's ordered sequence had this commit write them at step 11, while three other
passages said this task does not produce them. The sequence was wrong: a ratification
commit that writes the evidence it is judging is the barrier failing. They are licensed in
the post-freeze delta by `_declared_evidence_paths` once the manifest declares them, which
is why they need no entry in Allowed paths and why their absence from that list was never
the defect — step 11 was.

**Round ten's `automated_report: automated-summary.txt` was never a name the round
licensed.** It survived because `automated-summary.txt` is separately inside
`POST_FREEZE_DELTA_CEILING`, not because `_canonical_report_paths` recognises it. Round
eleven gets no such reprieve: its two reports are new files whose only licence is their
canonical names.

## What remains red on `F`

Four failures, `Ran 346 tests`, exit 1 — the four Part I names at step 1.

**There were sixteen, and twelve of them were one cause, which has since been repaired.**
`RatificationRecordTests.test_the_new_licences_are_named_files_and_not_directories` wrote
over `docs/program/tasks/W0-INT-02.md` in the class-level sandbox and `unlink()`ed it with
no `_remember`/`restore_one` pair. On a round-eleven freeze that file is a **tracked** path
in the frozen tree, so the probe destroyed it and everything downstream that digests the
tree failed: **eleven errors as `FileNotFoundError` — one of which was the first subtest of
`test_the_ratifying_task_banner_moves_in_both_directions` — plus that test's second
subtest.** Eleven plus one is the twelve. It was proved by repair rather than argued: with
the probe restoring the path instead of deleting it, and the freeze re-taken, the suite went
**16 → 4** with no other change.

**`W0-QA-04` then made that repair its own and closed on it.** `5d07fe3` gives the probe the
`_remember`/`restore_one` pair, and adds
`test_the_licence_probe_puts_back_every_path_it_displaces` as the guard that proves the
restoring can fail. The twelve are gone, and `Ran 343`/`failures=5, errors=11` — the figure
this section carried while that repair was in flight — is withdrawn.

Round seven's form of this paragraph named thirteen items for a set of twelve and
mis-assigned one of them; the correction was that the two `banner_moves` subtests are
counted separately and that
`test_a_publication_document_missing_its_statement_or_its_subject_is_named` is **not**
downstream of the probe at all — it survived the repair, and its cause is the fourth one
below.

This was `EXECUTION_PLAN.md` §3.8.6's impossibility **B**, and §3.8.7's claim that it was a
base defect already closed by `c4f2d82` did not hold for a round-eleven freeze: it was
closed only while `_pre_ratification_baseline()` walks back to a tree without that file, and
`F` is frozen with `ratified: false`, so the baseline is `F` itself and the file is present.
`5d07fe3` closes it for the round-eleven freeze too, and closes it inside `tests/**` rather
than by exception. **`tests/**` is final from `5d07fe3` on and has no licensed writer, so
anything found in it from here is a limitation to record and not a repair to request** — but
this one was repaired before that door shut, and none of the four below is it.

**`discover -s tests/contract` → exit `0` is still unreachable at `F`, and the four reasons
are inherent to a freeze commit:**

1. `TagIntegrityTests.test_the_tag_has_not_moved_and_its_message_is_true_of_its_commit` —
   the records name `v0.0.1-architecture` and it does not exist until step 3.
2. `TableExpectationTests.test_the_checkpoint_tag_resolves_and_the_rule_can_fail` — the tag
   must resolve from three sites in two records, one of them `contract-manifest.yaml`,
   which §3.9.4's first correction **removes from the frozen tree**. The two corrections
   are in tension; §3.9.3 attributed this failure to the missing tag alone, and on a tree
   built to §3.9.4 the cause is the retracted bundle.
3. `CrossGateAgreementTests.test_the_two_ratification_gates_agree` — `W0-INT-01.md` asserts
   `ratified` true and the reverted review JSON carries false. The gates are *made* to
   agree by the ratification; they cannot agree at a freeze that is by construction
   unratified.
4. `test_a_publication_document_missing_its_statement_or_its_subject_is_named` — because
   `evidence_bundle_digest` does not reproduce on `F`. Round seven recorded this as
   downstream of the probe, which is the right classification for the wrong reason: it is
   inherent to the freeze, not a consequence of the sandbox defect, and it survives the
   probe's repair.

**None of these four is closed by anything in this delta, and none is a reason to
`REJECT`.**

## Why the freeze commit cannot be green, established twice

`restore_one` deletes only when the remembered payload is falsy — only when the path was
**absent** from the frozen tree — so all eight `CHECKPOINT_DELIVERABLE_PATHS` must be
absent from `F`, while the tag rule requires `contract-manifest.yaml` **present** in that
same tree. Those are one tree. The candidate escape was built by an independent reviewer
and fails first at that deliverable, net 10 against 4. **No construction escapes**, and
this is now established independently twice.

The consequence is recorded in Part I's required tests: the expected result on `F` is a
named failure set, not exit 0, and a stream reporting `PASS` for round eleven is reporting
a verdict about a candidate that is red for reasons this file enumerates. §3.9.3 states the
same conclusion from the other side.

## The two causes recorded for the ratification commit

The sentence "the ratification commit is the first commit after it that can be green" was
false and is withdrawn, and its required test — `discover -s tests/contract` → exit `0` —
is unreachable at `F`. Two causes were recorded and both were re-taken.

1. **Cause 1 was never a `tests/**` defect. It was a defect in this delta.** The recorded
   form was "`RATIFYING_TASK = "W0-INT-01"`, the module constant, refuses delta item 6",
   owner `W0-QA-04`. That constant no longer exists: `c4f2d82` replaced it with the
   resolver. The value is resolved from `manifest.json`'s `ratification.task` and the wave
   plan's assignment row, and the reason the item was refused is that the delta moved the
   first and not the second. The guard was right and the delta was wrong, which is the
   reverse of what this section used to say. Repaired: the row moves in the freeze, the
   object here.
2. **Cause 2 named the wrong function, and the mechanism is repaired.** The recorded form
   was "`_reset_to_the_frozen_tree` rebuilds every sandbox from the freeze commit".
   `_reset_to_the_frozen_tree` does still resolve `_freeze_commit`, and that is correct:
   its whole question is "is this the tree the acceptance streams judged?" The method that
   builds the *unratified* anchor is `normalise_to_candidate`, and `c4f2d82` changed it to
   resolve `_pre_ratification_baseline()`. Verified on the integration tree, exit code read
   from the process: `SandboxResetTests.test_the_baseline_is_a_tree_that_denies_the_ratification`
   and `SandboxResetTests.test_MUTATION_taking_the_baseline_from_the_freeze_commit_goes_red`
   both pass, the second being the guard that proves the first can fail. **And the cause
   does not arise for a correctly opened round eleven at all**: `F` is frozen with
   `ratified: false`, so `_was_ratified_at(F)` is false, the walk never runs, and the
   baseline is `F` itself. `erratum.md`, `L-6`.

**Owner of cause 1: this delta, repaired. Owner of cause 2: nobody — closed in `c4f2d82`
and verified.** Neither is a reason to soften the delta, and the repair of cause 2 is not a
claim that the ratification commit is green.

## What moving `ratification.task` alone costs

Two findings, not one, and on the tree this task receives rather than at some later commit.
The first is the resolver: "ratification.task is 'W0-INT-03'; only W0-INT-01 may ratify
CP-00", which is `_resolved_ratifying_task` falling back to the floor as seen from inside
`_ratification_record`. The second is a cascade in the same function: on any problem
`_ratification_record` returns an **empty** allowed set, so an inadmissible record licenses
nothing and every reviewed-family file the ratification legitimately reconciled reads as
undeclared drift, naming all five ceiling files.

Re-taken on the integration tree with `ratification.task` moved and nothing else:
`_ratification_delta_problems` is **2**, both findings already present, while
`_reconciliation_problems` is **0**. The five ceiling files have *already* moved relative
to the reviewed candidate `92e13fa` — round ten's own ratification moved them — so the
drift the record has to license exists on this tree. An earlier form of this paragraph
postponed to a commit nobody has built a cost that was measurable in front of it.

**Both findings are recorded here rather than only the first**, because a reviewer who
expects one and meets two reads the second as a defect in the delta rather than as the
first one function downstream.

## Rows re-measured after an audit

All taken on a `cp -a` copy of the reconciled tree, each figure read from the process that
produced it.

*The `build-info.json` half was missing entirely.* With `manifest.json`'s `tag` and
`tag_planned` and `contract-manifest.yaml`'s `tag` moved to `v0.0.1-architecture` and
`build-info.json` left alone, `cp00_final_state.py` reports:

```
tag_planned: two live checkpoint records give this top-level field different values, and
neither says which tree it describes: artifacts/checkpoints/CP-00/build-info.json =
v0.0.0-architecture; artifacts/checkpoints/CP-00/manifest.json = v0.0.1-architecture
```

One accounting finding on a licensed path the delta simply did not name.
`build-info.json:tag_planned` is not one of the three claims `_checkpoint_tag_claims`
resolves the tag from — those are `manifest.json:tag`, `manifest.json:tag_planned` and
`contract-manifest.yaml:tag` — which is why the tag checks stayed quiet and the accounting
axis did not.

*Step 2.3 writes no new value, and that is not because the reviewed families hold still.*
The manifest's own recipe over the reviewed families of the reconciled tree gives
`a78572288a28b88be7f5dd58b9e79254a9e4f61cb55838ba4308b3be91109b84` over 100 files, which is
exactly what `manifest.json`, `contract-manifest.yaml` and `build-info.json` already
publish. The reviewed families do move inside this act — the four reconciliations — and the
recomputation lands back on the published value because the act restores those files to
exactly the tree that value was computed over. Measured on the integration tree: as it
ships, the recipe over the 100 tracked reviewed files gives `a785722…`; with round eleven's
`ratified: false` and the four files carrying pre-ratification prose again it gives a
different digest, and the last `docs/architecture` write is what brings it back.

## Withdrawn figures

- **The aggregate at the ratification commit.** 340 tests, 141 failures, exit 1 — the
  integrator's licence-audit measurement on a simulated ratification commit, attributed and
  never re-taken. Taken before `c4f2d82` and before the contour grew to its final 346; both its
  causes have been re-derived and one is closed; and building the commit it describes means
  opening round eleven and fabricating both primary reports, which no task may do. Stale in
  its tree, its contour and its causes. Replaced by the procedure at step 4.
- **The path count.** Two figures stood here: 24, from a first derivation, and 23, from a
  parallel derivation attributed to freeze `d9b918ce` and ratification `b8b85432`. Round
  eight checked: **neither commit exists in this repository**, so neither figure can be
  re-derived or audited, and a count nobody can reproduce is not evidence. Both are
  withdrawn. Part I's licence is an **enumeration** instead, derived from the procedure and
  checked path-by-path against `POST_FREEZE_DELTA_CEILING`, `RATIFICATION_DELTA_CEILING`,
  `CHECKPOINT_DELIVERABLE_PATHS` and the `{RATIFYING_TASK_FILE}` use site. It comes to
  twenty-two, and the twenty-two are named. Where an earlier form said "this list is a
  licence, not a size", the size is now a consequence of the licence rather than a rival
  claim to it.
- **131 extra failures** for the reassignment, measured in round six. An artefact of the
  tree the delta was applied to, not a property of the delta. Round seven built the freeze
  the delta is written for and re-took every figure on it.
- **`failures=134, errors=1`** as the expected state on `F`. Taken with the reassignment
  applied to a tree that had never been prepared. The reassignment applied inside the
  freeze costs zero additional failures.
- **The `--tag` default reporting four findings against one.** True on `W0-INT-02`'s base
  `6135f17`, false on any tree carrying `4e916b0`: the flag now defaults to `None` and
  resolves through `contour.recorded_tag(tree)`. Step 4 states the comparison instead of
  either number.
- **"All thirteen checker functions return `[]`."** Loose. There are **twelve**
  root-argument `_*_problems` checkers — `_checkpoint_tag_problems`,
  `_ratifying_task_problems`, `_tested_digest_problems`, `_post_freeze_delta_problems`,
  `_state_document_problems`, `_checkpoint_bundle_problems`, `_acceptance_record_problems`,
  `_publication_record_problems`, `_task_banner_problems`, `_acceptance_problems`,
  `_reconciliation_problems`, `_ratification_delta_problems` — plus `_registry_state_problem`,
  which takes a root and returns `str | None`, not a list. Enumerated on `29179c6`.
- **"A clean clone."** Round seven's required tests opened with "Re-executed by the
  reviewer on the candidate, in a clean clone", contradicting two other passages of the
  same file and unrunnable in any case: `.venv/` is gitignored with zero tracked files, so
  a clean clone has no `.venv/bootstrap/bin/python`. Self-arresting, but it is the first
  line an executor reads under that heading. Part I says `cp -a` or the main checkout,
  once, in both places it is stated.
- **"Every hit must be a floor, a series, or a comment."** False for four of the eleven
  hits: on the final module at `5d07fe3`, `:8314` is a live `assertIn` needle naming the old
  tag as the subject of a historical annotation, and `:12535`, `:12545` and `:12575` are
  `_tree(...)` fixtures feeding the resolver. Step 0.1 names the line shape it is looking
  for instead. **Step 0.1's own count said ten against this eleven-item breakdown**; eleven
  is what the grep returns on `29179c6` and on `5d07fe3` alike.

## Not in the delta, deliberately

- **The sixteen completed task banners other than `W0-INT-01`'s.** After the round-eleven
  freeze none is rewritten relative to the frozen tree, so `_task_banner_problems` asks
  nothing of them. Rewriting one would oblige it to name the new tag for no reason. They are
  the sixteen `POST_FREEZE_DELTA_CEILING` members Part I's licence does not claim.
- **The `PD-05` enumeration gap in `docs/architecture/ADR_INDEX.md`** (`erratum.md`, E-8) —
  the gap, not the file: the file is in the delta as one of the four reconciliations. The
  gap is real and this is the only task licensed to reach it, but no check fails without the
  fix, so closing it is not part of the minimal set. Part I's first Non-goal disposes of it
  without a rule here: a reviewer routes a defect to its owner rather than fixing it, and
  `W1` is the owner. Nothing in Part I enlarges the delta to accommodate it.
- **`artifacts/checkpoints/CP-00/check_state_records.py`.** Deliberately outside the
  ceiling. It is a tool, not a gate of this checkpoint, and editing it after a freeze voids
  the round.
- **Every historical round report, `docs/program/reviews/W0-QA-01.md`, and the annotation of
  `v0.0.0-architecture`.** Immutable; corrected by erratum only.
- **The whole of `RATIFICATION_DELTA_CEILING` is *in* the delta**, and an earlier form of
  this section said it was not. Three sentences claimed the review pair and the other four
  ceiling files were out because "the ratification act no longer touches a reviewed family
  at all". They are false: a reviewer who followed them would write a ratification commit
  whose `_reconciliation_problems` is non-empty. What was true is only that `W0-INT-02`
  already applied the `review_status` disposition, so the values those writes land on are
  the ones this candidate ships — the act restores them, it does not invent them.

  *The measurement that settles it*, taken on the integration tree — the main checkout at
  `89d2303` with `W0-INT-02`'s 27 paths copied in. Round eleven cannot be opened while
  `ratified` is `true`: adding an open round-11 entry there makes `_acceptance_problems`
  report "CP-00 cannot ratify on round 11, whose verdict is None". And setting
  `ratified: false` on a `cp -a` copy makes `_reconciliation_problems(root)` return **4** —
  one each for `CP00_ARCHITECTURE_REVIEW.md`, `CP00_OWNER_DECISIONS.md`,
  `ARCHITECTURE_LINT_RULES.md` and `ADR_INDEX.md`, every one reading "the stale claim … was
  removed without a recorded ratification. Reconciling it is ratification's job and needs
  the record that authorises the delta." The round-eleven freeze therefore **un-makes** all
  four reconciliations, and the ratification commit re-makes them. "Re-making them is not
  possible without un-making them first" was the right observation attached to the wrong
  conclusion: the freeze is the un-making.
