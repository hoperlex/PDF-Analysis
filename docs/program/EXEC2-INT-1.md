# EXEC2-INT-1 — stage 1 of EXEC-2 (capacity, pull claims, enrollment, agent)

Unverified development candidate published to `origin/dev`. Plan `dispatch/EXEC2-PLAN.md`, decisions `ADR-0026`, rulings `R-149a`…`R-149f`.

## What is in

| Task | Result |
|---|---|
| `EXEC2-SEAL-1` | Contract 1.15.0: 241 paths / 267 operations / 644 schemas. Migration `0046_executor_capacity_enroll`; the file `20261102_0046_executor_capacity_enrollment.py` keeps the longer name because `alembic_version.version_num` is `varchar(32)`. The seal also moved the pins and inventories. |
| `EXEC2-CAP-01` | Capacity units per connection in the Run claim, the dispatcher hint and the comparison call. Capacity 1 behaves exactly as before. Coupled limits are validated. `occupancy` and `queue_reason` are read: `runner_offline` takes precedence over `executor_at_capacity`. |
| `EXEC2-PULL-01` | The claim locks the runner-token row first and re-checks its usability under that lock. `runner_instance_id` limits redelivery. The agent keeps a registry of task ids in work. `D-215` is closed. |
| `EXEC2-ENROLL-01` | Enrollment grant and exchange: random runner token, rotated on a same-instance repeat. Agent health report. Package download. Agent-install API side: sessions end after 1800 s. The `R-149b` mark. Proxy zones `enrollment_exchange` and `agent_package`. |
| `EXEC2-AGENT-01` | `install.sh` for paths A and B. The model comes only from `AUDITMANAGER_AGENT_MODEL` or `--model`, and the CLI is derived from it. `detect.py`, the health reporter, a deterministic package built into the API image. |
| `EXEC2-WEB-CAP-01` | The capacity field, occupancy on the card, waiting reasons, the `R-149a` notice. |

## Integrator edits

- Granted pins the static sweep missed: the web contract snapshot, about 20 version and count pins, `bootstrap/runner.py`, the run-status schema and others. Each grant is one `chore:` commit on `integration/exec2`.
- `bootstrap/adapters.py` and `api/routers/ports.py` were shared by region among CAP, PULL and ENROLL.
- Conflicts between CAP-01 and ENROLL-01, all resolved:
  - one `RUNNER_ONLINE_SECONDS = 120`;
  - `OccupiedConnectionSummary` carries both occupancy and the integration mark.
- The path-B command carries the connection's pinned `gateway_model`, so the installer never picks a model.

## Checks (`R-149d`: no test, build, typecheck, lint, database or browser run)

- `git diff --check`: clean.
- Every changed Python file parses, every changed JSON file loads, and `bash -n` passes. That is 230 changed files.
- `node web/scripts/generate-api-client.mjs --check`: OK, 267 operations.
- Every contract operation is declared by a router. This was checked statically.
- One independent read-only review of the server diff (`ece9d1ef..dc4d601b`):
  - No BLOCKER or HIGH.
  - Fixed before publication:
    - origin taken only from configuration (MEDIUM);
    - install-session lifetime (MEDIUM);
    - token usability under the claim lock (LOW);
    - a single redemption timestamp (LOW);
    - a bounded package read (LOW).

## Known limits

- No acceptance test has run (`D-292`). The written database tests include multi-process races.
- `allow_client_documents` is not enforced (`D-291`). Capacity above one is for test data only.
- Accepted review findings:
  - two concurrent same-instance repeats rotate the token twice;
  - a fleet mixing agents with and without instance ids can redeliver across instances;
  - a restarted agent waits up to 120 s for its claim to lapse;
  - an abandoned, lapsed claim blocks the product purge until a poll sweeps it.
- A holder of both the enrollment secret and the instance id can rotate the runner token inside the 15-minute window. This is a visible takeover; a dedicated column is the clean follow-up.
- `test_doc_prose_facts` probably fails already on dev: older surface triples (1.11–1.14) sit in the live part of `CURRENT_STATE`.
- The dispatcher-hint query plan is unmeasured. `D-260` stays open.
- Unverified on a host:
  - `StateDirectory` on a home created by `useradd`;
  - the minimum Claude Code version that has `auth status`.

## Next

Stage 2: `EXEC2-ENROLL-SSH-01`, `EXEC2-WEB-WIZARD-01` and `EXEC2-SEAL-2` → `EXEC2-GROUP-STORE-01`.
