# Task EXEC-VPN-01 — WireGuard to a recognition machine: host template, runbook, reach probe

task_id: EXEC-VPN-01

## Outcome

The repository holds everything the operator needs to put the stand host on a WireGuard
network with a recognition or model machine:

- a `wg0.conf` template with placeholders;
- the runbook steps (key generation on each side, `AllowedIPs` limited to the peer's /32,
  firewall rules, and `systemctl enable wg-quick@wg0`);
- a reach probe.

The reach probe is `python -m auditmanager.executors reach <connection_id>`, run inside the
`worker` container. It reports whether that container can open the TCP port of an
`http_api` connection with `transport: vpn`, and it shows the same result in
«Подключения». In the application, the VPN machine is an ordinary `http_api` connection
with an internal address (`R-143a`).

**Proof needs the stand.** The tunnel itself is the operator's act on the stand host; the
lane does not run it.

## Depends on

- `EXEC-SSH-01` — merged. VPN shares the widget, the runbook, the test directories and
  `executors/__main__.py` with `EXEC-AGENT-01` and `EXEC-SSH-01`, so it runs last.

## Frozen inputs

- base commit: `origin/dev` at the integrator's freeze, after `EXEC-SSH-01`;
- plan §2 (directions; `vpn` as a transport label), §7 (what is provable without the
  stand);
- `R-143a` (VPN on the host by the operator, not from the UI), `R-29` clause 2 (covered by
  `R-143a`; the runbook still opens no inbound port except the WireGuard UDP port the
  operator chooses).

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

- `infra/deploy/wireguard/**`
- `src/auditmanager/executors/reach.py`
- `src/auditmanager/executors/__main__.py`
- `tests/unit/executors/**`
- `tests/integration/executors/**`
- `web/src/widgets/executor-connections/**`
- `web/tests/unit/workers/**`
- `docs/program/DEPLOYMENT_RUNBOOK.md`
- `docs/program/EXEC-VPN-01.md`

## Forbidden hotspots

`infra/deploy/compose.server.yml` (no `NET_ADMIN`, no `network_mode: host`; the
containers reach the peer through the host's routing). Also forbidden: `contracts/**`,
`db/migrations/**`, dependency and lock files, the composition root, global styles,
`CURRENT_STATE.md`, `DEBT_REGISTER.md`, refs, tags and **the stand**.

## Non-goals

No WireGuard inside a container, no management of the tunnel from the UI, no automatic
key exchange, and no change to the host terminator (`D-191` stays separate).

## Work

1. **`infra/deploy/wireguard/`.**
   - `wg0.conf.example` for the stand host and `peer.conf.example` for the machine.
   - `README.md`. It states that Docker's bridge egress follows the host's routes, so the
     `worker` reaches `10.x.y.z` with no container change. It also gives the
     verification commands to run on the host (`wg show`, and a `curl` from
     `docker compose exec worker`).
2. **The reach probe in `executors`.** A TCP connect and an optional HTTP `GET` of the base
   URL's `/models`, with a bounded timeout. The result is written into a probe row of
   outcome `unreachable` or `ok`; the vocabulary is `EXEC-SEAL-01`'s.
3. **A unit test** of the probe against a local port and a closed port. A syntax check of
   both templates runs where `wg-quick` is available; where it is not, the report says so.

## Deliverables

The templates, the runbook section, the probe, and the report
`docs/program/EXEC-VPN-01.md`. The report lists what was verified in the lane and what
waits for the stand.

## Required tests

- command: `python3 -m pytest -q tests/unit/executors -k reach`
- expected: all passed.
- command: `bash -n` over any shell in `infra/deploy/wireguard/`
- expected: no output.

## Integration contract

Nothing changes on the stand until the operator follows the runbook. After that, an
`http_api` connection with the peer's address passes «Проверить» like any other.

## Failure/idempotency/security cases

- The runbook limits `AllowedIPs` to the peer's /32.
- The peer's model port is bound to its WireGuard address only.
- The probe never sends a key to `/models` unless the revision is `http_api` with its own
  secret.

## Rollback / feature flag

`systemctl disable --now wg-quick@wg0` on the host, and remove the route.

## Handoff

- changed files: tabulated with the reason for each;
- commands/results: each with its exit status;
- known limits: the tunnel is unproven until the operator runs it on the stand;
- integration notes: the operator steps.
