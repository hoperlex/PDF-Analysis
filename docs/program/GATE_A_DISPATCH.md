# Gate A — dispatch record

**Dispatched 2026-09-10 from `d68c297792e6dc0153878c4b0256c9e933eb452c`** on
`planning/prototype-roadmap`. Structure: `PROTOTYPE_WAVE_PLAN.md` §3. Briefs:
`GATE_A_BRIEFS.md`. `OD-14` was ruled by the repository owner the same day, releasing
`A1b` and `A5`.

## Sessions in flight

| Session | Branch | Owns | Instance |
|---|---|---|---|
| `A1` (`A1a`+`A1b` merged — OD-14 removed the reason for the split) | `agent/gate-a1` | `db/migrations/**`, `src/auditmanager/shared/{db,identity}/**`, `contracts/api/v1/**`, `docs/program/P02_SEAMS.md` | throwaway PG on `55431`, db `audit_a1` |
| `A2` | `agent/gate-a2` | `infra/local/**` | `gate-a2`, PG `55432`, S3 `59011`/`59012`, db `audit_a2`, bucket `audit-a2` |
| `A3` | `agent/gate-a3` | `src/auditmanager/storage/**` | throwaway MinIO on `59021`/`59022`, bucket `audit-a3` |
| `A4` | `agent/gate-a4` | `fixtures/synthetic/ar/**`, `tools/fixtures/**` | none — needs no services |

`A5` (web toolchain and generated client) is released but not yet dispatched: it consumes
`A1`'s OpenAPI document and starts when that document is committed.

## Why A1 and A3 do not use `make up`

`infra/local/**` belongs to `A2` and did not exist at dispatch. `A1` and `A3` develop
against throwaway containers they start and remove themselves, on the ports above. Their
`make up`-based gates are verified at Gate A convergence, after `A2` lands. No session
waits on another.

## Environment verified before dispatch

Docker 29.6.1 with the daemon running, Compose v5.3.1, Node v22.23.1, npm 10.9.8, CPython
3.12.3 as a base interpreter, and reachable `pypi.org` and `registry.npmjs.org`.
`make bootstrap` installs pinned `uv` 0.12.11 into `.local/uv` against a hash allow-list,
so `uv` is not a host prerequisite.

## Convergence — the integrator, serially, after all four report

1. Merge in dependency order: `A2`, then `A1`, then `A3`, then `A4`.
2. Dispatch `A5` once `A1`'s OpenAPI document is on the branch.
3. Run the Gate A closing checks from `GATE_A_BRIEFS.md` §7 on one clean, dedicated
   instance that no authoring session is using.

**Do not measure during the fan-out.** The suites copy the working tree and will report
another session's state. Every figure quoted from a fan-out window is void.

## What Gate A is expected to teach

Rounds-to-accept for an implementation task has never been measured in this repository.
The estimate in `PROTOTYPE_WAVE_PLAN.md` §8 — 5–6 days P50 to PC-01 — rests on assuming
one to two rounds per gate, extrapolated from authoring times only. These four sessions
produce the first real samples. Record, for each: elapsed wall-clock from dispatch to an
accepted result, and the number of remediation rounds. Replace §8 with arithmetic
afterwards, and record the command and the tree that produced each figure.
