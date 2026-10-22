# Task EXEC-AGENT-01 — an unattended pull agent on a remote machine

task_id: EXEC-AGENT-01

## Outcome

An administrator creates a `pull` connection with client `agent` and issues it a runner
token. On another machine (a recognition box, or a machine with a local model), the
operator runs `tools/executor-runner/agent.py` as a service. The agent claims tasks over
HTTPS and answers each one in one of two modes:

- a configured local command: the task JSON goes to its stdin and the answer JSON comes
  from its stdout;
- a local OpenAI-compatible endpoint, such as Ollama or vLLM.

The agent is proven on this host by a second process against the lane stand. It works
from behind NAT and needs no VPN and no open port on the machine.

## Depends on

- `EXEC-PULL-01` — merged (the runner API, the task table, tokens).
- It runs **before `EXEC-SSH-01`, not beside it**: both edit `executors/**`,
  `tools/executor-runner/**`, the connections widget and the runbook (`AGENTS.md` §3).

## Frozen inputs

- base commit: `origin/dev` at the integrator's freeze, after `EXEC-PULL-01`;
- the runner API exactly as `EXEC-PULL-01` reports it; this task changes no contract and
  no migration;
- plan §2.1 (`pull`, client `agent`), §4.3 T-2, §5.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `tools/executor-runner/**`
- `src/auditmanager/executors/**`
- `tests/integration/executors/**`
- `tests/unit/executors/**`
- `web/src/widgets/executor-connections/**`
- `web/tests/unit/workers/**`
- `docs/program/DEPLOYMENT_RUNBOOK.md`
- `docs/program/EXEC-AGENT-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, dependency and lock files (the agent uses the standard
library only), `infra/**`, the composition root, global styles, `CURRENT_STATE.md`,
`DEBT_REGISTER.md`, refs, tags and the stand.

## Non-goals

No image tasks: no stage sends one today, and a recognition key arrives with the first
stage that does (plan §2.2). No auto-update of the agent. No Windows service wrapper; the
lane provides a systemd unit example only.

## Work

1. **`agent.py`.**
   - Long-poll claim, extend while working, then submit or fail.
   - Backoff on 429 and 503.
   - Exit with a clear message on 401, for a revoked token.
   - Bounded concurrency (`--max-tasks`).
   - The command and endpoint modes.
   - The declared model comes from config and must equal the revision's pinned model, or
     the stand refuses it (`R-133`).
2. **`agent.example.toml`** and a **systemd unit example**. The token lives in an
   environment file with mode 0600, never on the command line.
3. **The UI** shows client `agent` with its last claim address and the open-task count.
   The `EXEC-PULL-01` widget is reused.
4. **The test.**
   - A run on the lane stack is answered by `agent.py` started as a subprocess with a
     stub local command.
   - A second test uses a stub OpenAI-compatible endpoint.
   - A third test kills the agent mid-task and shows the claim returning to `open`.

## Deliverables

The agent, its config example, the unit file, the runbook section, and the report
`docs/program/EXEC-AGENT-01.md`.

## Required tests

- command: `python3 -m pytest -q tests/unit/executors tests/integration/executors -k agent` on the lane's own containers
- expected: all passed.
- command: `npm --prefix web run typecheck && npm --prefix web test -- --run web/tests/unit/workers`
- expected: green.

## Integration contract

There are no new surfaces. The agent and the Claude Code bridge are two clients of one
runner API.

## Failure/idempotency/security cases

- The agent never writes the payload to disk unless the command does.
- On a schema-invalid answer it fails the task with a typed reason; it does not retry
  silently.
- A clock skew between the agent and the stand does not extend a claim beyond the
  server's lease.

## Rollback / feature flag

Revoke the agent's token, and remove the route.

## Handoff

- changed files: tabulated with the reason for each;
- commands/results: each with its exit status;
- known limits: no images;
- integration notes: the operator install steps.
