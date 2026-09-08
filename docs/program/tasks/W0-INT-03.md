# Task W0-INT-03 — primary reviewer: symbolic review, ratification and the superseding tag

> **Reserved for the primary reviewer. The program orchestrator prepares this file and
> does not execute it.** Nothing in this task may be performed by the agent that produced
> the candidate: the whole point of the barrier is that ratification is decided by someone
> who did not build the thing being ratified.

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
- base commit: the `W0-INT-02` integration commit, supplied at handoff as the candidate SHA
- immutable reviewed candidate: `92e13fa496a723ed6e4c3adbf138c4f4e1d7c368`
- local tag `v0.0.0-architecture` on `39a3a6430bd97c38cb20bafc793fc9d077d0df8e` —
  **immutable, not accepted, never moved, never published**

## Allowed paths

The exact minimal ratification delta, and nothing else. `W0-INT-02` writes the final list
into this section at its integration; until then it is provisionally:

- `docs/architecture/CP00_ARCHITECTURE_REVIEW.json` — the ratification fields only
- `artifacts/checkpoints/CP-00/manifest.json` — the ratification record and the sealed
  evidence digest
- `docs/program/CHECKPOINT_REGISTRY.md` — the CP-00 row's state token
- `docs/program/CURRENT_STATE.md` — the ratification sentence

## Forbidden hotspots

- `contracts/**`, `fixtures/**`, `scripts/**`, `tests/**`
- every evidence record other than the manifest's ratification fields
- every historical round report
- `v0.0.0-architecture`: not moved, not deleted, not re-pointed, not published

## Non-goals

- No remediation. A reviewer who finds a defect routes it to its owner and rejects; they
  do not fix it. Fixing what you are reviewing destroys the independence the barrier buys.
- No new task, no scope change, no plan edit.

## Deliverables

1. A symbolic review verdict — binary `ACCEPT` or `REJECT`. Every rejection names the
   blocker, its `path:line`, and the owning task to reopen.
2. On `ACCEPT`: the ratification commit applying exactly the delta above.
3. On `ACCEPT`: an annotated tag `v0.0.1-architecture` on the exact accepted commit, whose
   message states only what has been measured. The tag is created after the ratification
   commit and points at it.
4. On `ACCEPT`: publication of `main`, the integration branch and the new tag, as one
   verifiable operation, without force and without moving any existing ref.

## Required tests

Re-executed by the reviewer on the candidate, in a clean clone, with nothing else running:

- Command: `.venv/bootstrap/bin/python -m unittest discover -s tests/contract`.
  Expected: exit `0`.
- Command: `.venv/bootstrap/bin/python -m unittest discover -s tests/checkpoint`.
  Expected: exit `0`.
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

Never measure in a linked worktree, and never while anything else clones this repository.

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
