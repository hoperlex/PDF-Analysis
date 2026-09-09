# Task P0-NAV-00 — define decision-to-code navigation for AI-agent delivery

> **Status: candidate produced on `planning/prototype-roadmap`; integrate with the
> prototype-roadmap review.** This task adds no independent checkpoint and does not
> delay FF-01 or P01.

## Outcome

A post-CP-00 architecture decision and roadmap gate define a rebuildable navigation
layer through which a human or AI agent can resolve an active decision to its contracts,
owning task, implementation seams and tests, and can reverse-resolve a code path to the
decisions that constrain it.

## Depends on

- `W0-ARC-01` — accepted architecture candidate and owner decisions

## Frozen inputs

- architecture/ADR baseline: `docs/architecture/**` at
  `5e40fccd2eeadbd6f2ab77c06ebc3f57b20605b8`, read only outside the listed slots
- prototype direction and P02/P03 slice at the same commit
- task format: `docs/templates/TASK_TEMPLATE.md`
- repository-owner direction dated 2026-09-09: include indexing and decision-to-code
  linkage as an AI-agent navigation layer
- migration head: `none`, read only

## Allowed paths

- `docs/program/tasks/P0-NAV-00.md`
- `docs/architecture/adr/ADR-0019-decision-code-navigation.md`
- the ADR-0019 row/status explanation in `docs/architecture/ADR_INDEX.md`
- the CP-00 scope note and P-23 only in `docs/architecture/ARCHITECTURE_BIBLE.md`
- navigation-gate sections only in `docs/program/ROADMAP.md`
- navigation inputs/deliverables only in `docs/program/tasks/P0-PLN-01.md`
- ADR/task links only in `docs/INDEX.md`

## Forbidden hotspots

- `docs/program/PROTOTYPE_FOUNDATION_FREEZE.md` and every P01 provider task
- `contracts/**`, `fixtures/**`, `scripts/**`, `tests/**`, `src/**`, `web/**`, `infra/**`
- migration head, root dependencies/locks, Makefile, composition root and global styles
- CP-00 evidence, checkpoint registry, Git tags and history of `main`

## Non-goals

- No implementation of the navigation manifest, generator or validator in this task.
- No bulk annotation, relocation or rewriting of existing source files or ADRs.
- No semantic/vector database or LLM-generated authority index.
- No new P01 acceptance gate and no change to FF-01.

## Deliverables

- ADR-0019 defining authority, entry model, reverse lookup, ownership and validation
- post-CP-00 P-23 in the Architecture Bible without rewriting CP-00 disposition
- a roadmap rule requiring an agent-ready navigation implementation task before P02
- a P0-PLN-01 deliverable that creates that task and includes its time in the PC-01 graph

## Required tests

- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`
  Expected: exit `0`, standalone `PASS`.
- Command: `git diff --check`
  Expected: exit `0`.
- Command: compare changed paths with this task's `Allowed paths`.
  Expected: every changed path is allowed and every forbidden hotspot is absent.
- Manual review: ADR-0019 is explicitly post-CP-00, leaves canonical authority in its
  source documents/code and does not block P01.
  Expected: pass.

## Integration contract

`P0-PLN-01` must produce an agent-ready navigation implementation task. That task may
prepare its schema/index in parallel with P01, but the accepted layer and mappings for
the foundation must exist before P02 implementation fan-out. Every P02+ task then owns
one disjoint navigation entry alongside its code; an integrator alone owns generated
aggregate indexes.

## Failure/idempotency/security cases

- Missing, ambiguous or superseded decision references fail validation rather than being
  guessed by an agent.
- A navigation entry never becomes authority over an ADR, contract, task or code.
- No secret, environment value, provider payload or production data enters the index.
- Regeneration from identical entry fragments is deterministic and changes no source.

## Rollback / feature flag

Documentation only. Revert this planning commit before navigation implementation starts.
After P02 begins, removing the layer requires a replacement agent-onboarding path and an
explicit plan correction.

## Handoff

- changed files and containment proof
- validator and `git diff --check` results
- no machine/runtime contract change
- P01 remains independently dispatchable; navigation implementation is pre-P02
