# AGENTS — working rules for AI agents

This file is mandatory for every coding agent.

## 1. Before a task

1. Read `docs/program/CURRENT_STATE.md`.
2. Read the task file/description and everything in its `depends_on`.
3. Check the frozen contract set of the current wave.
4. Work only within the task's `allowed_paths`.
5. Do not change `contracts/**`, the migration head, root dependency/lock files, the composition root or global styles without owning the corresponding integration/contract slot.

A session started from a handoff file reads that file and its card in `.local/tasks.md` before
anything else, and checks their claims at their links instead of re-researching (§7).

## 2. Task format

Every task must have:

- `task_id`;
- a result that the user or a test can verify;
- frozen inputs / contract versions;
- `allowed_paths` and `forbidden_hotspots`;
- non-goals;
- deliverables;
- verification commands;
- an integration contract;
- a rollback/feature-flag policy, if behaviour changes;
- `depends_on` only on completed task IDs.

Template: `docs/templates/TASK_TEMPLATE.md`.

## 3. Ownership

One shared contract / migration head / root lockfile / composition root — one owner per wave. Two agents must not edit the same hotspot in parallel.

## 4. Architectural prohibitions

Forbidden:

- direct SQL/S3/filesystem access from a router or a React component;
- business logic in ORM/Pydantic/transport schema/UI;
- deep imports into the internals of another bounded context;
- generic repository/base service/global utils without proven semantics;
- job state held only in memory;
- path/filename/display number as identity;
- dual-write DB + external side effect without outbox/reconciliation;
- silent fallback;
- LLM output as the canonical expert decision;
- modification of raw deterministic comparison evidence by the AI layer.

## 5. Completing a task

The agent returns:

1. the list of changed files;
2. the checks run and their results;
3. new/changed contracts;
4. risks/known limitations;
5. instructions for the integrator;
6. proof that forbidden hotspots were not touched, or a reference to the task that permits touching them.

Do not create a checkpoint/tag on your own unless the task is a `W*-INT-*` task.

## 6. `origin/main` triggers deployment

Once GitHub auto-deploy is connected, any push or merge to `origin/main` is an external
deployment action, not merely a publication of Git history. Before it, you must read and
follow `docs/program/MAIN_AUTODEPLOY_POLICY.md`.

- The right to push to `origin/main` belongs only to an explicitly assigned integration task
  whose integration contract names this ref.
- Required: a clean tree, a complete `make gate` with the literal `GATE OK`, a re-check of the
  remote ref and a proven fast-forward of the exact verified SHA.
- Forbidden: force-push, an unverified “small fix” after the gate, and parallel publications.
- After the push the task is not complete until the workflow has finished successfully and the
  deployment host has passed `infra/deploy/verify-deployed.sh` for the same tree.

By default the verified working version is published to `origin/dev`. Neither the status of an
integration task, nor the completion of a wave, nor a green gate by itself grants the right to
update `origin/main`. A push/merge to `origin/main` is allowed only after a separate direct
instruction from the owner to publish the exact verified candidate; vague commands such as
“continue” or “close the wave” do not count as such an instruction.

## 7. Sessions: one session, one stage

- **One session is one stage of a task.** Every call re-reads the whole accumulated context, so
  each further step in a long session costs more than the last. At a stage boundary the work
  stops and is handed to a new session; it is not continued in this one.
- **A stage boundary** is: a wave or lane finished (committed, its runs green); a structural stage
  of a task finished (research, a plan, a review round with the owner's rulings, a gate); a plan
  approved — implementation starts in a new session, not in this one right after approval.
  Waiting inside a stage (a test run, a workflow, the owner's answer to a poll) is not a boundary.
- **At a boundary, four steps, then stop:**
  1. Reach a stable state: edits committed (a technical commit pushed when the task owns a push),
     background runs finished. A session is not closed while a workflow, gate or agent it started
     is still running.
  2. Update the task's card in `.local/tasks.md`: date of the update, progress, loose ends, and a
     `Handoff:` line that links the handoff file.
  3. Write the handoff file `.local/handoff/<topic>-<YYYY-MM-DD>.md` (contents below).
  4. In the reply to the user: the result of the stage and a ready first sentence for the new
     session — "Continue «<card title>»: stage <…>. Handoff — `.local/handoff/….md`". Do not
     start the next stage.
- **The handoff file is written for a session that has not seen the conversation.** It holds what
  is expensive to rediscover:
  - state: branch, latest commits, what is already on `origin`, what is uncommitted in which tree
    and whose it is;
  - sources (plan, owner rulings, memory, the card) as links, not retold;
  - what was done, briefly, with commits;
  - the next stage: the assignment, its acceptance criteria, the obligations of the contour;
  - open questions for the owner;
  - traps and techniques found in this stage;
  - what is frozen and is not revisited without a new fact from the code.

  The integrator's handoffs under `.local/handoff/integrator-*.md` are the pattern.
- **A new session starts from the handoff file and the card, not from re-research.** It checks the
  handoff's claims at their links and redoes something only when it finds a discrepancy with the
  code.
- **If a stage does not fit in one session** (the context has grown and the boundary is still far),
  stop at the nearest stable point — a commit, or an interim result written to a file — and hand
  over the same way. A small task that fits in one session is not split. Continue in the same
  session only at the user's direct request.

### 7.1 The integrator works to a context budget, not to a stage

The integrator's duties (merges, gates, publication, grants, rulings, dispatch, cleanup) are
continuous and have no natural stage end, so the integrator does not stop at every boundary. It
keeps integrating through lane merges, gates and wave closures while its context is within budget,
and hands the role over once the budget is spent.

- **The budget is spent** when any of these holds: the session's context has been summarised
  (compacted) once; the integrator has closed two waves — or one wave and one release — in this
  session; or it finds itself re-reading state it had already established in order to stay
  correct.
- **Once spent, it takes no new integration work** — no new dispatch, freeze or wave — and brings
  the step in hand to a safe, stable point: no gate, workflow or deployment it started is still
  running; every merge it began is committed; every grant or ruling it gave by message is
  recorded in the task file or `OWNER_RULINGS_*.md` and committed; every publication it started is
  verified with `git ls-remote`; its own lane containers are down.
- **It then writes `.local/handoff/integrator-<YYYY-MM-DD>.md`** and updates the integrator card in
  `.local/tasks.md`. Beyond the general contents above, the integrator's handoff records: every
  ref that matters (`origin/dev`, `origin/main`, tags, each `integration/*` branch and its tip);
  the worktrees with their lanes and ports; running and dispatched work with the session that owns
  each item; the gate-slot order on the host; pending owner decisions and polls; anything granted
  by message and not yet recorded; the deployment and acceptance state of the stand.
- **It tells the peer sessions** (executor, planning, acceptance) that the role is moving, gives
  the user the ready first sentence for the new integrator — "You are the exclusive integrator of
  this project. Continue from `.local/handoff/integrator-<YYYY-MM-DD>.md`." — and stops writing.
  The user appoints the new session; until then nobody integrates.
