# Task EXEC-PULL-PROBE-INT-01 — start connection probes without a private key ring

task_id: EXEC-PULL-PROBE-INT-01

## Outcome

A worker without `AUDITMANAGER_SECRETS_KEYS` takes a `pull` connection's
«Проверить» request. The pull runner can then claim and answer its synthetic
task; the request no longer expires as `no_worker` solely because the worker
has no key ring.

## Depends on

- `EXEC-HTTP-01` — completed worker probe loop and composition root.
- `EXEC-PULL-01` — completed pull probe protocol.
- `EXEC-AGENT-01` — completed outbound agent.
- `EXEC-INT-DEV-01` — completed development integration of the pull channel.
- `EXEC-CODEX-SSH-01` — completed Codex adapter and model pin on `origin/dev`.

## Frozen inputs

- base commit: `3bc7dae1a62ccd871ed42fc364ffa139cc2313f3` (`origin/dev`);
- contract `1.0.0`; API 87 paths / 99 operations / 284 schemas;
- analysis, comparison and event contracts unchanged;
- migration head `0031_executor_pull_channel`;
- existing `pull` probe needs no private secret; a keyed probe without a ring
  reports `secret_unreadable`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the composition root suppresses all worker probes when its private
  ring is absent, while `pull` probe evaluation never opens a key.

### P-01 — probe loop is suppressed at startup

- captured_at: 2026-10-23
- command: `git show 3bc7dae1:src/auditmanager/bootstrap/composition.py | sed -n '174,178p'` and `git show 3bc7dae1:src/auditmanager/workers/service.py | sed -n '233,234p'`
- captured_output:
  ```text
  probe_runner = (
      None if resolved.secrets_private_ring is None
      else runner_for(sessions, ring=resolved.secrets_private_ring, environ=env, engine=engine)
  )
  if self._probe_runner is not None:
      loops.append((self._probe_loop, "auditmanager-worker-probes"))
  ```
- interpretation: an active heartbeat and run dispatch loop do not prove the
  connection probe loop is running.

### P-02 — pull probe requires no key

- captured_at: 2026-10-23
- command: `git show 3bc7dae1:src/auditmanager/executors/probe_runner.py | sed -n '147,165p'`
- captured_output:
  ```text
  if connection.kind == "pull":
      pull_revision: RevisionRecord | None = revision
      key = ""
  else:
      pull_revision = None
      if probe.secret_id is None:
          return ProbeResult("secret_unreadable", "no key is set for this connection")
      try:
          key = open_secret(
              session, self._ring, secret_id=probe.secret_id,
              destination=destination_for(connection.kind, revision.settings, "api_key"),
              repository=self._store,
          )
      except SecretUnreadableError:
          return ProbeResult(
              "secret_unreadable",
              "the key cannot be opened here for this address; enter it again",
          )
  ```
- interpretation: the worker can safely start the shared loop without a ring;
  keyed probes then produce their existing `secret_unreadable` result.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

This integration task owns the composition-root slot for this repair and may
publish the tested candidate to `origin/dev`. Publication to `origin/main`
requires a separate direct owner instruction for an exact gated candidate and
the steps in `MAIN_AUTODEPLOY_POLICY.md`.

## Allowed paths

- `src/auditmanager/bootstrap/composition.py`
- `tests/unit/executors/test_probe_loop.py`
- `docs/program/tasks/EXEC-PULL-PROBE-INT-01.md`
- `docs/program/EXEC-PULL-PROBE-INT-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependency and lock files;
- all other composition-root files, global styles, `web/**`, `infra/**`;
- `docs/program/CURRENT_STATE.md`, tags and `origin/main`.

## Non-goals

- No changes to the runner API, token storage, routing, model pin, or UI.
- No change to the requirement that keyed connections need a readable secret
  before they can pass a probe.
- No claim of production acceptance until a deployed worker takes and finishes
  the live probe.

## Deliverables

- Wire the worker probe runner even when the private ring is absent.
- Update the composition regression test for both configurations.
- Record verification, publication and operational limits in the report.

## Required tests

- command: `../int-beta/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/executors/test_probe_loop.py tests/unit/executors/test_pull_wiring.py`; expected: pass.
- command: `../int-beta/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/executors`; expected: pass.
- command: `git diff --check`; expected: exit 0.
- command: `make gate` on any exact candidate proposed for `origin/main`; expected: literal `GATE OK`.

## Integration contract

The worker starts the probe loop regardless of whether it has a private ring.
A `pull` probe can ask the runner to answer a synthetic task. Existing keyed
connections still require a key to pass; without one they report
`secret_unreadable`. The candidate is published to `origin/dev` only.

## Failure, idempotency and security cases

- Missing private material never becomes an implicit key or a successful keyed
  probe.
- The probe loop keeps existing retry, drain and stale-request rules.
- No token, key or request content is logged by this change.

## Rollback / feature flag

No new flag. Revert this commit to restore the former wiring; a running worker
restarts on deployment. Removing a connection route or revoking its token
stops traffic without a code rollback.

## Handoff

- changed files, checks, contracts, limits and integration notes:
  `docs/program/EXEC-PULL-PROBE-INT-01.md`.
