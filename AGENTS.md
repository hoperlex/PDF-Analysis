# AGENTS — working rules for AI agents

This file is mandatory for every coding agent.

## 1. Before a task

1. Read the recent entries and task-relevant sections of
   `docs/program/CURRENT_STATE.md`; do not load its historical ledger wholesale.
2. Read the task description and its completed dependencies, if any.
3. Check the contracts relevant to the change; for a coordinated wave, check its frozen set.
4. Stay within the request's scope or the task file's `allowed_paths` when one exists.
5. Do not change `contracts/**`, the migration head, root dependency/lock files, the composition root or global styles without owning the corresponding integration/contract slot.

Use `docs/context/README.md` to select relevant source sections after reading the current
state and task. The context index is a locator only: check its links and line ranges in
the current tree, and read the cited contract, decision or evidence before acting on it.
Do not load historical task/review directories wholesale to infer current status.

How to reach a deployable result with the least time and tokens — fast path, checks by risk,
selective use of helpers — is in `docs/context/DEVELOPMENT_VELOCITY.md`, shared by Codex and
Claude (`CLAUDE.md` imports this file).

A session started from a handoff file reads that file and its card in `.local/tasks.md` before
anything else, and checks their claims at their links instead of re-researching (§7).

## 2. Task size and records

For a routine, single-owner change, the user request or issue and the commit are enough.
Record the observable result, touched paths, focused checks and any known limit in the
handoff. Do not create a task file, wave plan, frozen-version census or separate review
round just to satisfy a format. Read only contracts the change actually depends on.

Use a task file for shared-contract or migration changes, concurrent owners, a deployment,
or work that needs a durable decision or handoff across sessions. Keep it proportional:
outcome, owner and path boundary, completed dependencies, relevant frozen inputs, checks,
integration behavior and rollback. Capture exact premises only when a path/count/version
is material to the decision. `docs/templates/TASK_TEMPLATE.md` is the extended template.
No `depends_on` may name unfinished work.

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

Report changed paths, checks and results, contract impact, known limits and the next
integration action. For a coordinated task, also show that its forbidden hotspots were
untouched (`git diff --name-only <base>..HEAD`) or name the owning task. A routine edit
needs a concise handoff, not a six-part report with empty sections.

Do not create a checkpoint/tag on your own unless the task is a `W*-INT-*` task.

## 6. `origin/main` triggers deployment

Once GitHub auto-deploy is connected, any push or merge to `origin/main` is an external
deployment action, not merely a publication of Git history. Before it, you must read and
follow `docs/program/MAIN_AUTODEPLOY_POLICY.md`.

- The right to push to `origin/main` belongs to a delegated release integrator acting under
  a release task or standing owner assignment that names this ref. This delegation covers
  successive verified candidates; a second owner instruction for each SHA is unnecessary.
- Required: a clean exact candidate, the risk-based release checks in
  `docs/program/MAIN_AUTODEPLOY_POLICY.md`, a re-check of the remote ref and a proven
  fast-forward of the verified SHA. A full `make gate` is reserved for a capable runner
  when the release plan identifies a risk it uniquely covers.
- Forbidden: force-push, an unverified “small fix” after the gate, and parallel publications.
- After the push the task is not complete until the workflow has finished successfully and the
  deployment host has passed `infra/deploy/verify-deployed.sh` for the same tree.

By default the working candidate is published to `origin/dev` after focused checks. A
release integrator can promote it to `origin/main` under the delegated release assignment;
an implementation lane, a wave close or a green check alone is not release authority.

### 6.1 A user-visible change carries its version note

Owner rule of 2026-11-06. A publication to `origin/dev` that changes what a user sees carries
its release note in the same push; the note is never left for the move to `main`.

- A new capability opens a new minor version: `release-notes/<x.y+1.0>.json`, with `VERSION`
  moved in the same commit.
- A minor fix or improvement a user can see either adds items to the note of the current
  version (as a higher `revision` once that note has reached `main`) or opens a patch version
  `x.y.z+1`.
- The form rules choose between the two: a version holds at most seven items; when the current
  one is full, the change opens a patch version, which may carry the same date (owner
  2026-11-06).
- Moving `VERSION` moves its pins in the same commit: the revision map and the version order
  in `tests/contract/release_notes/test_release_notes_form.py`, the version set in
  `tests/integration/releases/test_release_loader.py` and the «Product `VERSION` is» line of
  `docs/program/CURRENT_STATE.md`. The current note's `screen` and `where` must match
  `web/src/shared/config/screen-registry.ts`.
- Writing or revising a note is not a code change and needs no test run. A change nothing
  user-visible depends on (internal code, tests, documentation) needs no note. Format and
  review rules: `docs/program/RELEASE_PROCESS.md`.

## 7. Sessions and handoffs

Continue a task in the same session while its context is reliable. A plan, review or test
result is not an automatic stop point. Hand off when ownership changes, context has become
unreliable, or the remaining work cannot fit safely; keep the handoff short and link to
source records instead of copying them. Do not create a new branch or session for each
small stage of one task.

A handoff states the branch and SHA, uncommitted work and its owner, checks actually run,
remaining work and any decision needed. Commit a reviewable state before leaving a task;
finish or stop background checks the session started. A compacted or interrupted session
continues from this record rather than repeating the repository-wide audit.

### 7.1 Integrator

The named integrator owns shared hotspots, merges and release publication. It may continue
through several merges while context is reliable. Before transferring the role, it records
active refs, worktrees, running jobs, pending decisions and deployment state in
`.local/handoff/` and makes the in-flight operation stable. Worktrees are created only for
concurrent or isolating work and removed after integration when their clean, contained
state has been verified. `scripts/worktree_cleanup.py` is the cautious cleanup tool.

### 7.2 Questions to the owner

Owner rule of 2026-11-10. Every question to the owner is a poll (`AskUserQuestion` or the
client's structured choice) whenever the answer can reasonably be offered as options.

- Frame the poll in the current case: the facts it rests on, concrete options, the
  recommended option first.
- Ask in prose only for a free value that options cannot carry: a name, a URL, a secret.
- A message never ends with an open question in prose.
- When a tool call is declined, stop and ask by poll what to do instead of retrying it.

## 8. Checks proportional to the change

Choose checks from the changed behavior and the failure it could cause. Record each command,
result and any unverified behavior. Do not run the whole frontend, contract battery, live
journey or `make gate` for every merge or documentation edit. A green check on another SHA
is not evidence for the candidate being accepted.

| Change | Minimum local evidence |
| --- | --- |
| Documentation or agent/process rules | `git diff --check`, affected link/policy/guard tests; no app or container suite |
| Backend behavior | focused unit/contract tests for the changed seam; relevant integration test when persistence or external effects change |
| Web behavior | focused component tests and lint/typecheck for the touched package; live journey only when the changed route or interaction needs browser proof |
| Contract, migration, auth, persistence or deployment | targeted compatibility/security tests, migration upgrade/rollback where applicable, and affected consumer checks |
| Release candidate | the exact-tree risk-based release plan in `docs/program/MAIN_AUTODEPLOY_POLICY.md` |

A task may publish an explicitly labelled unverified candidate to `origin/dev` when a check
is unavailable; it must state what was not proved and must not present it as accepted or
ready for `main`. Failed relevant checks are defects, not optional omissions. A full
`make gate` is an optional broad measurement or a release-plan requirement for a named
risk, run once on a capable runner rather than repeatedly on this shared development
host. Existing `make light-acceptance` remains a broad compatibility command, not a
mandatory prerequisite for every change.

Before a container/build run that uses substantial disk or memory, measure available
capacity and compare it with a credible peak and margin. If insufficient, use a smaller
relevant check or another capable runner; record the unverified area. Do not rerun a run
voided by host exhaustion without changing the resource condition. See
`docs/program/dispatch/OPERATING_CONSTRAINTS.md`.
