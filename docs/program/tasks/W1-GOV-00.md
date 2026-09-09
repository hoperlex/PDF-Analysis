# Task W1-GOV-00 — transplant the W1 package onto the accepted CP-00 line and reconcile it

> **Status: superseded; do not dispatch.** Prototype work is governed by `P0-FND-00`/`P0-PLN-01`; the body below is retained as historical input only.

## Outcome

The fifteen prepared W1 documents live on the accepted line, reconciled with what is
actually true there, with every defect the preparation audit found either closed and
proved closed by running its gate, or recorded with an owner. After this task a reader of
`docs/program/waves/W1.*.md` and `docs/program/tasks/W1-*.md` is not told anything the
repository contradicts.

**This file is inside the globs its own gates scan.** `docs/program/tasks/W1-*.md` covers
it, so the shape, command-surface, dispatch and acceptance gates all read it. Three
defects in its first committed form came from exactly that — a task that prescribes gates
and is not measured by them is a rule with an exemption for its author.

## Depends on

- `W0-QA-04`, accepted and integrated. Round one landed at `6135f17`, round two at
  `4e916b0`; the final integration commit is supplied at dispatch, because the task
  reopened twice and a pin here has been wrong twice
- `W0-INT-02`, accepted and integrated — its integration commit is this task's base
- `W0-INT-03`, executed by the primary reviewer — the accepted CP-00 tag is its output and
  is an **input** here, not something this task may assume or invent

## Frozen inputs

- domain contract: `contracts/domain/v1/**` at `1.0.0-draft.1`, candidate revision 5 — read only
- API contract: none exists at CP-00; the foundation OpenAPI is `W1-INT-00`'s to create
- analysis/comparison/event contract: `contracts/analysis/v1/**`, `contracts/events/v1/**` at `1.0.0-draft.1` — read only
- migration head: `none`
- base commit: the accepted CP-00 ratification commit, supplied at dispatch
- accepted checkpoint tag: supplied at dispatch as `ACCEPTED_TAG`. **Do not guess it.** The
  recovery ratifies as a superseding tag and the package names the superseded one in eight
  sites carrying the literal — `grep -n "v0.0.0-architecture" docs/program/tasks/W1-*.md
  docs/program/waves/W1.*.md` over the transplant bytes gives `W1-INT-00.md:6,32,34,139`,
  `W1-ARC-00.md:28`, `W1.1_toolchain_and_contract_freeze.md:4,17,38`. Five further sites
  assert the tag as the accepted base without spelling it, for thirteen in total; the
  larger figure is a reconciliation count, not a grep count, and either is useless without
  the one that produced it
- source package: `prep/W1` at `b5d5274` **plus its uncommitted working tree**, read only.
  Re-verified byte-identical on 2026-09-08: fifteen files, 256 370 bytes, all `sha256`
  reproducing the transplant manifest

## Allowed paths

The fenced block below is the only source the CP-01 allowed-path check consults. The prose
in this section is prose: a path span written in a sentence here is not a licence, and an
earlier form of a sibling gate harvested exactly that and widened three tasks silently.

`docs/stages/S01_repository_foundation.md` is licensed for its **task-map rows only**. The
map names eight tasks where the wave has twelve, and `W1-INT-01` means two different things
in the two documents; the transplant is the moment that contradiction becomes visible, so
it is closed here rather than routed to a task that does not exist yet.

```allowed-paths
docs/program/tasks/W1-*.md
docs/program/waves/W1.*.md
docs/program/reviews/W1-PREP-AUDIT.md
docs/INDEX.md
docs/stages/S01_repository_foundation.md
```

- `docs/program/reviews/W1-PREP-AUDIT.md` — the audit's destination on this line; it is
  currently untracked in the source worktree and is the only record of why four of the
  fifteen documents differ from their committed form
- `docs/INDEX.md` — the W1 rows only, written fresh

## Forbidden hotspots

- **`prep/W1` itself.** Nothing is merged, cherry-picked or rebased. Final bytes only
- every `docs/program/tasks/W0-*.md`, `docs/program/waves/W0.*.md`,
  `docs/program/CURRENT_STATE.md`, `docs/program/CHECKPOINT_REGISTRY.md`
- `docs/program/EXECUTION_PLAN.md` — the integrator's file, and outside
  `POST_FREEZE_DELTA_CEILING`, so a W1 task writing it would void the acceptance round it
  is standing on
- `artifacts/checkpoints/**` — CP-00 evidence, frozen by its acceptance. A post-tag erratum
  against that bundle is the checkpoint owner's, not the transplant's
- `docs/stages/**` except the one file licensed above
- `contracts/**`, `fixtures/**`, `scripts/**`, `tests/**`
- root dependency and lock files, migration head, composition root, global styles
- every checkpoint tag: not moved, not deleted, not re-pointed, not created

## Non-goals

- No implementation of anything. This task moves and reconciles documents.
- No resolution of `PENDING-*` tokens other than `PENDING-CP00-RATIFICATION`, whose value
  becomes knowable once the tag exists and whose resolver is the integrator's standing
  slot. Every other token resolves when its producing task integrates.
- No new W1 task and no change to the W1 task graph's shape without the integrator
  recording it in `EXECUTION_PLAN.md` first.
- No new gate. The missing pairwise-disjointness check is `W1-INT-00`'s to write; this task
  records the gap and states the batches, it does not close it.

## Deliverables

1. **The transplant.** The fifteen documents, taken as final bytes: eleven identical to
   `b5d5274`, four from the source working tree — `W1-INT-00.md`, `W1-ARC-01.md`,
   `W1-OPS-02.md` and `W1.1_toolchain_and_contract_freeze.md`, which carry the
   remediation of the audit's five blocking findings. The exact set, with per-file
   `sha256`, is in the transplant manifest the integrator supplies at dispatch. Nothing
   else from that branch: measured at `762af03` by `git diff --name-status prep/W1 main`,
   a wholesale copy would **delete 25 files** on this line — including the execution plan,
   all three recovery task files, `tests/checkpoint/**` and **this task file itself** —
   and revert 17 more, among them the test module at **14 788** changed lines. Both
   figures move every time the base moves; take them again at dispatch and report the
   command with them.
2. **Reconciliation with the accepted line**, at minimum these axes, each with the
   `path:line` it corrects:
   - the accepted tag: eight sites carry the superseded literal and five more assert it as
     the accepted base without spelling it, per the grep in Frozen inputs;
   - acceptance rounds: the package believes five; the record holds **ten**
     (`CURRENT_STATE.md:241`, `CHECKPOINT_REGISTRY.md:5`). The number the recovery lands on
     is supplied at dispatch and is not to be guessed — an earlier form of this file
     asserted eleven while the record it cites said ten;
   - the recovery tasks `W0-QA-04`, `W0-INT-02` and `W0-INT-03` occur zero times in
     fifteen documents and are the reason the base exists;
   - `tests/**`: `tests/checkpoint/` is now a second discover root with its own mandatory
     gate, which five package sites contradict — including a hard-asserted command surface
     with no entry for it;
   - `scripts/**` and `E-06`: the package closes the family to every task while
     `known-risks.md` names W1 as the owner of an open, measured security item, and five
     package gates re-run the unrepaired validator;
   - `depends_on` edges naming tasks that do not exist or are not complete;
   - the S01 task map: eight tasks against the wave's twelve, and `W1-INT-01` meaning two
     different things.
3. **The audit residue, discharged or recorded.** Thirty-five items: five blocking whose
   repairs were verified by execution — one **not closed**, one closed only in part, three
   closed but each introducing a new defect — eleven major, eight minor, and eleven newly
   opened by the repairs themselves. The integrator supplies the verified list at dispatch.
   For each: close it and prove the closure **by running its gate**, or record it with an
   owner. Reading a repair and declaring it closed is how five of these arose.

   `N-01` is no longer hypothetical. The narrowed shape-gate needle `<[a-z][a-z0-9_-]*>`
   passed an angle-bracket placeholder naming the accepted tag, which the old needle
   caught, and the remedy recorded in the audit residue misses it too because that
   placeholder contains spaces. It was live in this file until this revision, and the
   defect is described here rather than quoted: a gate cannot tell a quotation from an
   instance, so an erratum that reproduces its own subject re-plants it. Any needle proposed as its closure
   is proved by a mutation over the whole package, not by inspection.
4. **A disjointness statement for every batch this wave dispatches in parallel.** No gate
   in the package compares two `allowed-paths` blocks — the acceptance gate examines one
   block at a time and exits `0` for all twelve tasks on the resolved package, including
   pairs that then share a path. The machine form of `AGENTS.md:32` does not exist, so
   disjointness becomes decidable only when the integrator resolves the deferred tokens,
   and nothing checks it at that moment.

   Measured on the transplant bytes, twelve tasks, sixty-six pairs, nineteen concurrent:
   **W1.1 (`W1-ARC-00` ∥ `W1-API-00`) is provably disjoint**, zero overlapping lines in
   either direction. **W1.2-A and W1.2-B are not**, both on the single token
   `PENDING-PATH:W1-ARC-00` — `W1-ARC-01.md:77` against `W1-WEB-01.md:79`, and
   `W1-STO-01.md:86` against `W1-API-01.md:95`. A tenth collision,
   `PENDING-PATH:W1-INT-00` between `W1-ARC-01.md:74` and `W1-STO-01.md:85`, was created by
   the `B-04` repair rather than found by the audit. Either make the blocks concretely
   disjoint per lane, or state which batches cannot dispatch in parallel and why.

## Required tests

- Command: `.venv/bootstrap/bin/python -m unittest discover -s tests/contract`.
  Expected: the failure set is unchanged from this task's base commit. This task writes no
  test and no contract; any new failure is this task's defect. The base-commit failure set
  is supplied at dispatch, measured on a tree with nothing else running.
- Command: `.venv/bootstrap/bin/python -m unittest discover -s tests/checkpoint`.
  Expected: exit `0`.
- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`.
  Expected: exit `0`, standalone `PASS`.
- Command: `git status --porcelain -uall`.
  Expected: a path set that is a subset of the allowed paths. Assert containment, never a
  count, and accept the empty result.
- Command: `git rev-list -n1 "$ACCEPTED_TAG"`.
  Expected: unchanged from dispatch. `ACCEPTED_TAG` is supplied at dispatch; the earlier
  form of this line spelled it as an angle-bracket placeholder, which is the defect class
  the shape gate exists to catch and which the narrowed needle no longer detects.
- Command: `git rev-list -n1 v0.0.0-architecture`.
  Expected: `39a3a6430bd97c38cb20bafc793fc9d077d0df8e`, unchanged — proof the superseded
  tag did not move.

### Package gates, which must be run and not read

These are not `- Command:` entries because they are not pasteable strings: each is defined
in `W1-INT-00.md` and must be extracted from it verbatim. A gate reconstructed from a
description is not the gate.

- The **shape gate** (`W1-INT-00.md:391`) and the **command-surface gate** (`:423`), over
  the transplanted package including this file. Report the measured exit code and the full
  finding list. Both are the gates whose repairs were verified as incomplete: on the
  committed `b5d5274` bytes the command-surface gate exits `1` on a bare `` `make` `` span
  in `W1-INT-00.md` and exits `0` on the working tree, while `B-02` remains open at
  `W1-QA-01.md:214`, where `` `PENDING-W1-INT-00:stop; PENDING-W1-INT-00:test-integration` ``
  is a `;` chain the `&&`-only split does not touch.
- The **dispatch gate** (`:323`), over every transplanted task file. Expected: no
  unresolved input token in a value position, with the documented exemptions.
- The **acceptance gate** (`:358`), per task. On the transplant bytes it exits `0` for
  exactly `W1-API-00`, `W1-ARC-00`, `W1-INT-01`, `W1-INT-02` and `W1-OPS-01`; the other
  seven carry unresolved tokens. A claim about any of these that was not executed is not
  evidence.

Measure in a clone or the main checkout, **never in a linked worktree**: `.git` is a file
there, the sandbox tests cannot copy the object database, and the suite reports 202 tests
with 19 environment errors instead of the real count. Never measure while anything else
clones this repository, and never while another suite is running — the sandbox copies the
working tree.

## Integration contract

The integrator can rely on: the fifteen documents are the source's final bytes and nothing
else came across; every statement in them about the checkpoint, the rounds, the tag, the
test layout and the task graph agrees with the accepted line; every audit item is closed
with an executed gate or recorded with an owner; and for each parallel batch there is a
statement, backed by the blocks themselves, of whether its tasks are disjoint.

## Failure/idempotency/security cases

- Re-running the transplant on an already-transplanted tree changes nothing.
- A gate that cannot be executed as written is a finding, not a pass. Say so and name it.
- `E-06` remains open at this task's completion; it is `W1-QA-00`'s or its named
  successor's, and nothing here may imply it is repaired.
- No ref is written, no tag created or moved, nothing pushed.

## Rollback / feature flag

Not applicable: programme documentation. Rollback is reverting the integration commit,
which removes the fifteen documents and leaves the accepted CP-00 line untouched.

## Handoff

- changed files, proved a subset of allowed paths
- every required test verbatim, with the exit code of the measured process
- every package gate run, with its exit code and full finding list, this file included
- the audit residue table: item, verdict, and for a closure the gate output that proves it
- the per-batch disjointness statement
- every item left open, with its owner and why it cannot close here
