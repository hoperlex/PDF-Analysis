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
