# ADR-0002: Modular monolith control plane

- Status: accepted
- Date: 2026-08-31; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: CP-00 (W0-ARC-01) disposition: ratify (`docs/architecture/CP00_ARCHITECTURE_REVIEW.md` §5; the review is not the ratification act); principle P-05; `R-105` (`docs/program/OWNER_RULINGS_2026-09-17.md` §3.30, `docs/program/dispatch/W54-PLAN.md` §3.6–§3.7); `R-143` (§3.43: `R-143a`, `R-143c`; priority and publication bar `R-144`; `docs/program/dispatch/EXECUTOR-CONNECTIONS-PLAN.md` §2, §4, §7)

## Context
Heavy analysis has a different resource and failure profile from the API. The legacy backend is one deployable with 24 discovered router modules (23 mapped) and a separate worker execution profile (`DW-01`–`DW-06`; CP-00 review §5).

## Decision
- **Shape.** The control plane is one deployable Python/FastAPI backend with hard bounded-context boundaries. Separate execution processes/workers are allowed because heavy analysis has a different resource/failure profile. Any additional service needs a dedicated ADR proving independent scaling, security, availability or release-cycle need.
- **Boundary.** Contexts interact through public application ports, contract events or approved read models, never internal ORM/repository imports.
- **Worker (W54 addendum, `R-105`).** The worker is the same backend, started as `python -m auditmanager.workers serve` from the API image: one codebase, one release, one PostgreSQL. It is a compose service `worker` after `migrate`, with no `ports:` and not on the session volume; it has the API's environment except `AUDITMANAGER_API_TOKEN`, plus `provider.env`.
- **Execution role.** `EXECUTION_ROLE ∈ {all, api, worker}` is set literally per service in `compose.server.yml`, never in the `.env`. `all` keeps W53's in-process execution for tests; on the stand only the worker claims Jobs and both reclaim expired leases. `deploy.sh` refuses a compose file in which either service lacks it.
- **Wake-up.** `LISTEN/NOTIFY` on a dedicated connection, with a logged warning when it is lost and a 5 s poll as the stated fallback. The authority boundary stays the database: the Job, Attempt and Lease rows with the execution token.
- **Registry.** The `worker` table of migration `0019_execution_workers`: `wrk_<ULID>` kept on tmpfs, version, start, a heartbeat every 20 s, `slots`, `intake_enabled`; stale after 90 s and offline after 600 s. `lease.worker_id` records which worker holds a lease and is frozen with the lease. `listWorkers` reads the registry for any role and `setWorkerIntake` is an administrator's switch (`R-80`).
- **Remote executors for model work (R-143 addendum, `R-143c`).** Remote workers on other hosts were out of scope (W54 non-goal; a second host would need its own ADR under this ADR's rule). For model work only, this decision is that ADR and supersedes that rule:
  - A remote party (a Claude Code session, an agent, an SSH host or an HTTP model) receives a task payload and returns an answer. It never connects to PostgreSQL or S3 and never writes metadata.
  - The local `worker` stays the only Job, Attempt and Lease authority and the only writer of metadata rows (`R-105`). A remote answer is data the worker records.
  - The stand gains exactly one new inbound surface: the runner API of `EXEC-PULL-01`, executor to stand over the stand's public HTTPS origin, with hashed runner tokens. `http_api` and `ssh_command` connections are opened by the worker and add none. A WireGuard VPN is the operator's host configuration (`R-143a`), not an application surface.
  - `R-133` stays fail closed for every kind: a reported model other than the pinned one is a typed failure and nothing from it is published. `AGENTS.md` §4 stays: no silent fallback between connections; a standby is used only when an administrator configured it, and every switch is journaled.
  - Remote execution of anything but model calls (documents, S3 objects, metadata) stays out of scope.

## Consequences
- Positive: one codebase, one release and one PostgreSQL for API and worker (W54 addendum).
- Cost: every additional service needs its own ADR; remote model executors add exactly one inbound surface (the runner API) and a remote answer is only data the worker records.

## Verification
- `deploy.sh` refuses a compose file in which the API or the worker lacks `EXECUTION_ROLE`.
- Boundary conformance: `docs/architecture/ARCHITECTURE_LINT_RULES.md` (cites this ADR's Boundary).
- What each remote-executor slice serves: `docs/program/CURRENT_STATE.md` and the `EXEC-*` task files.

## Revisit trigger
A proposed additional service (dedicated ADR required, see Decision); a second host for anything but model work.

## History
- 2026-08-31 — bootstrap baseline, status `accepted for bootstrap; ratify at CP-00`.
- 2026-09-01 — CP-00 disposition recorded: ratify (W0-ARC-01; status text unchanged).
- 2026-10-12 — W54 addendum (`W54-SEAL-01`, `R-105`), folded into Decision (Worker, Execution role, Wake-up, Registry). It applies the allowance "separate execution processes/workers are allowed" and adds no service of a different kind. Migration `0019_execution_workers` and the two sealed operations carry the schema and the surface; `W54-WORKER-01` supplies the behaviour; the addendum itself changed no runtime behaviour.
- 2026-10-22 — R-143 addendum (`EXEC-ADR-01`, `R-143c`, `R-144`), folded into Decision (Remote executors for model work). It superseded, for model work only, the W54 addendum's last bullet. As written then: nothing of it existed in the tree yet, and the slices add it in the plan's order — `EXEC-SEAL-01` (connection schema and secret sealing), `EXEC-HTTP-01` (database-sourced `http_api` connections and `R-133` on the run path), `EXEC-PULL-01` (the runner API; amends the wording of `runs/scope.py`), then `EXEC-AGENT-01`, `EXEC-SSH-01` and `EXEC-VPN-01` (the unattended agent, the SSH kinds and the WireGuard runbook); until a slice merges, W54 behaviour stands. The addendum itself changed no runtime behaviour.
- 2026-10-27 — Note (`PROD-16`): the statements «Nothing above exists in the tree yet» and «Until a slice merges, W54 behaviour stands», written before the slices, are no longer true: `EXEC-SEAL-01`, `EXEC-HTTP-01`, `EXEC-PULL-01`, `EXEC-AGENT-01`, `EXEC-SSH-01` and `EXEC-VPN-01` have merged (`git log --oneline --grep=EXEC-` lists them; `docs/program/CURRENT_STATE.md` and the `EXEC-*` task files describe what each serves). The 2026-10-22 entry is kept as the historical statement of the plan; the tree and `CURRENT_STATE.md` are the record.
- 2026-11-18 — unified to the template (`ADR-OPTIMISE-01`); addenda folded into Decision; meaning unchanged.
