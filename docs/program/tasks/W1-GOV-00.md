# Task W1-GOV-00 — transplant the W1 package onto the accepted CP-00 line and reconcile it

## Outcome

The fifteen prepared W1 documents live on the accepted line, reconciled with what is
actually true there, with every defect the preparation audit found either closed and
proved closed by running its gate, or recorded with an owner. After this task a reader of
`docs/program/waves/W1.*.md` and `docs/program/tasks/W1-*.md` is not told anything the
repository contradicts.

## Depends on

- `W0-QA-04`, accepted and integrated at `6135f17fb76758dc1ab3a7c1195f5421814ba2fb`
- `W0-INT-02`, accepted and integrated — its integration commit is this task's base
- `W0-INT-03`, executed by the primary reviewer — the accepted CP-00 tag is its output and
  is an **input** here, not something this task may assume or invent

## Frozen inputs

- domain contract: `contracts/domain/v1/**` at `1.0.0-draft.1`, candidate revision 5 — read only
- API contract: none exists at CP-00; the foundation OpenAPI is `W1-INT-00`'s to create
- analysis/comparison/event contract: `contracts/analysis/v1/**`, `contracts/events/v1/**` at `1.0.0-draft.1` — read only
- migration head: `none`
- base commit: the accepted CP-00 ratification commit, supplied at dispatch
- accepted checkpoint tag: supplied at dispatch. **Do not guess it.** The recovery
  ratifies as a superseding tag and the prepared package names the superseded one in
  thirteen places
- source package: `prep/W1` at `b5d5274` **plus its uncommitted working tree**, read only

## Allowed paths

- `docs/program/tasks/W1-*.md`
- `docs/program/waves/W1.*.md`
- `docs/program/reviews/W1-PREP-AUDIT.md` — the audit's destination on this line; it is
  currently untracked in the source worktree and is the only record of why four of the
  fifteen documents differ from their committed form
- `docs/INDEX.md` — the W1 rows only, written fresh

## Forbidden hotspots

- **`prep/W1` itself.** Nothing is merged, cherry-picked or rebased. Final bytes only
- every `docs/program/tasks/W0-*.md`, `docs/program/waves/W0.*.md`, `docs/stages/**`,
  `artifacts/checkpoints/**`, `docs/program/CURRENT_STATE.md`,
  `docs/program/CHECKPOINT_REGISTRY.md`, `docs/program/EXECUTION_PLAN.md`
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

## Deliverables

1. **The transplant.** The fifteen documents, taken as final bytes: eleven identical to
   `b5d5274`, four from the source working tree — `W1-INT-00.md`, `W1-ARC-01.md`,
   `W1-OPS-02.md` and `W1.1_toolchain_and_contract_freeze.md`, which carry the
   remediation of the audit's five blocking findings. The exact set, with per-file
   `sha256`, is in the transplant manifest the integrator supplies at dispatch. Nothing
   else from that branch: a wholesale copy would delete 24 files on this line, including
   the execution plan, all three recovery task files and `tests/checkpoint/**`, and revert
   17 more including the test module at 14 695 changed lines.
2. **Reconciliation with the accepted line**, at minimum these axes, each with the
   `path:line` it corrects:
   - the accepted tag: thirteen sites name the superseded one;
   - acceptance rounds: the package believes five, the record holds eleven;
   - the recovery tasks `W0-QA-04`, `W0-INT-02` and `W0-INT-03` occur zero times in
     fifteen documents and are the reason the base exists;
   - `tests/**`: `tests/checkpoint/` is now a second discover root with its own mandatory
     gate, which five package sites contradict — including a hard-asserted command surface
     with no entry for it;
   - `scripts/**` and `E-06`: the package closes the family to every task while
     `known-risks.md` names W1 as the owner of an open, measured security item, and five
     package gates re-run the unrepaired validator;
   - `depends_on` edges naming tasks that do not exist or are not complete.
3. **The audit residue, discharged or recorded.** Thirty-five items: five blocking whose
   repairs were verified by execution — one **not closed**, one closed only in part, three
   closed but each introducing a new defect — eleven major, eight minor, and eleven newly
   opened by the repairs themselves. The integrator supplies the verified list at dispatch.
   For each: close it and prove the closure **by running its gate**, or record it with an
   owner. Reading a repair and declaring it closed is how five of these arose.
4. **A disjointness statement for every batch this wave dispatches in parallel.** No gate
   in the package compares two `allowed-paths` blocks, so disjointness becomes decidable
   only when the integrator resolves the deferred tokens, and nothing checks it at that
   moment. Today one pair is provably disjoint and both W1.2 batches are not. Either make
   the blocks concretely disjoint, or state which batches cannot dispatch in parallel and
   why.

## Required tests

- Command: `.venv/bootstrap/bin/python -m unittest discover -s tests/contract`.
  Expected: the failure set is unchanged from this task's base commit. This task writes no
  test and no contract; any new failure is this task's defect.
- Command: `.venv/bootstrap/bin/python -m unittest discover -s tests/checkpoint`.
  Expected: exit `0`.
- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`.
  Expected: exit `0`, standalone `PASS`.
- Command: the shape gate and the command-surface gate, verbatim from `W1-INT-00.md`, over
  the transplanted package.
  Expected: **run them and report the measured exit code and output.** Both are the gates
  whose repairs were verified as incomplete; a claim about either that was not executed is
  not evidence.
- Command: the dispatch gate, verbatim, over every transplanted task file.
  Expected: no unresolved input token in a value position, with the documented exemptions.
- Command: `git status --porcelain -uall`.
  Expected: a path set that is a subset of the allowed paths. Assert containment, never a
  count, and accept the empty result.
- Command: `git rev-list -n1 <the accepted tag>` and `git rev-list -n1 v0.0.0-architecture`.
  Expected: both unchanged from dispatch — proof that no tag moved.

Measure in a clone or the main checkout, **never in a linked worktree**: `.git` is a file
there, the sandbox tests cannot copy the object database, and the suite reports 202 tests
with 19 environment errors instead of the real count. Never measure while anything else
clones this repository.

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
- the audit residue table: item, verdict, and for a closure the gate output that proves it
- the per-batch disjointness statement
- every item left open, with its owner and why it cannot close here
