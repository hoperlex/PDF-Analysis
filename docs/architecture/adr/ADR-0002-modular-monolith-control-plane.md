# ADR-0002: Modular monolith control plane

- Status: accepted for bootstrap; ratify at CP-00
- Related principles: P-05

## Decision
The control plane is one deployable Python/FastAPI backend with hard bounded-context boundaries. Separate execution processes/workers are allowed because heavy analysis has a different resource/failure profile. Any additional service needs a dedicated ADR proving independent scaling, security, availability or release-cycle need.

## Boundary
Contexts interact through public application ports, contract events or approved read models, never internal ORM/repository imports.

## W54 addendum — R-105, 2026-10-12

Recorded by `W54-SEAL-01` under owner ruling R-105 (`OWNER_RULINGS_2026-09-17.md` §3.30) and
`docs/program/dispatch/W54-PLAN.md` §3.6–§3.7. It applies the Decision's "separate execution
processes/workers are allowed" and adds no service of a different kind.

- The worker is the same backend, started as `python -m auditmanager.workers serve` from the
  API image: one codebase, one release, one PostgreSQL. It is a compose service `worker`
  after `migrate`, with no `ports:` and not on the session volume; it has the API's
  environment except `AUDITMANAGER_API_TOKEN`, plus `provider.env`.
- `EXECUTION_ROLE ∈ {all, api, worker}` is set literally per service in `compose.server.yml`,
  never in the `.env`. `all` keeps W53's in-process execution for tests; on the stand only the
  worker claims Jobs and both reclaim expired leases. `deploy.sh` refuses a compose file in
  which either service lacks it.
- Wake-up is `LISTEN/NOTIFY` on a dedicated connection with a logged warning when it is lost
  and a 5 s poll as the stated fallback. The authority boundary stays the database: the Job,
  Attempt and Lease rows with the execution token.
- The registry is the `worker` table of migration `0019_execution_workers` (`wrk_<ULID>`
  kept on tmpfs, version, start, a heartbeat every 20 s, `slots`, `intake_enabled`; stale
  after 90 s and offline after 600 s). `lease.worker_id` records which worker holds a lease and
  is frozen with the lease. `listWorkers` reads the registry for any role and
  `setWorkerIntake` is an administrator's switch (R-80).
- Remote workers on other hosts remain out of scope (W54 non-goal); a second host would need
  its own ADR under this one's rule.

Migration `0019_execution_workers` and the two sealed operations carry the schema and the
surface; `W54-WORKER-01` supplies the behaviour. This addendum itself changes no runtime
behaviour.

## R-143 addendum — remote executors for model work, 2026-10-22

Recorded by `EXEC-ADR-01` under owner ruling R-143 (`OWNER_RULINGS_2026-09-17.md` §3.43,
`R-143c`; priority and publication bar `R-144`) and `docs/program/dispatch/EXECUTOR-CONNECTIONS-PLAN.md`
§2, §4, §7. For model work only, it supersedes the W54 addendum's last bullet ("Remote workers on
other hosts remain out of scope (W54 non-goal); a second host would need its own ADR under this
one's rule"); this is that ADR. The W54 text above stays as written.

- A remote party (a Claude Code session, an agent, an SSH host or an HTTP model) receives a task
  payload and returns an answer. It never connects to PostgreSQL or S3 and never writes metadata.
- The local `worker` of the W54 addendum stays the only Job, Attempt and Lease authority and the
  only writer of metadata rows (`R-105`). A remote answer is data the worker records.
- The stand gains exactly one new inbound surface: the runner API of `EXEC-PULL-01`, executor to
  stand over the stand's public HTTPS origin, with hashed runner tokens. `http_api` and `ssh_command`
  connections are opened by the worker and add none. A WireGuard VPN is the operator's host
  configuration (`R-143a`), not an application surface.
- `R-133` stays fail closed for every kind: a reported model other than the pinned one is a typed
  failure and nothing from it is published. `AGENTS.md` §4 stays: no silent fallback between
  connections; a standby is used only when an administrator configured it, and every switch is journaled.
- Remote execution of anything but model calls (documents, S3 objects, metadata) stays out of scope.

Nothing above exists in the tree yet; the slices add it, in the plan's order. `EXEC-SEAL-01` adds
the connection schema and secret sealing. `EXEC-HTTP-01` adds database-sourced `http_api`
connections and `R-133` on the run path. `EXEC-PULL-01` adds the runner API and amends the wording
of `runs/scope.py`. `EXEC-AGENT-01`, `EXEC-SSH-01` and `EXEC-VPN-01` add the unattended agent, the
SSH kinds and the WireGuard runbook. Until a slice merges, W54 behaviour stands. This addendum
itself changes no runtime behaviour.

> **Note 2026-10-27 (`PROD-16`, superseding the closing paragraph above).** That paragraph was written before the slices. `EXEC-SEAL-01`, `EXEC-HTTP-01`, `EXEC-PULL-01`, `EXEC-AGENT-01`, `EXEC-SSH-01` and `EXEC-VPN-01` have merged (`git log --oneline --grep=EXEC-` lists them; `docs/program/CURRENT_STATE.md` and the `EXEC-*` task files describe what each serves), so «Nothing above exists in the tree yet» and «Until a slice merges, W54 behaviour stands» are no longer true. The paragraph is kept as the historical statement of the plan; the tree and `CURRENT_STATE.md` are the record.
