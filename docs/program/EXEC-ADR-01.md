STATUS: committed, awaiting integrator merge (11:34 +05)

# EXEC-ADR-01 — ADR-0002 addendum for remote executors (R-143c)

**Task:** `tasks/EXEC-ADR-01.md`. **Branch:** `agent/exec-adr-01`. **Depends on:** `EXEC-RULE-01` (merged).
Documentation only; no runtime behaviour changes.

## 1. Result and changed files

- `docs/architecture/adr/ADR-0002-modular-monolith-control-plane.md` — new "R-143 addendum"
  (27 lines, the W54 addendum's shape). It supersedes, for model work only, the W54 addendum's
  last bullet; the W54 text is unchanged. It states: the remote party answers model calls and
  never reaches PostgreSQL or S3; the local `worker` stays the Job/Attempt/Lease authority
  (`R-105`); the stand gains exactly one new inbound surface, the runner API of `EXEC-PULL-01`;
  `R-133` fail closed and no silent fallback stay.
- `docs/program/dispatch/ROADMAP-TO-BETA.md` and `docs/program/dispatch/CODE-FIRST-TO-BETA.md` —
  one-line pointers that `R-143d` moves executor connections into the beta scope.
- `docs/program/EXEC-ADR-01.md` — this report.

## 2. Checks and results

| Command | Result |
| --- | --- |
| `git diff --check` | exit 0, no output |
| `python3 -m pytest -q -p no:cacheprovider tests/contract/api_v1/test_doc_prose_facts.py tests/contract/program` | exit 0, 72 passed |

Container-free only: a complete gate runs on this host, so no docker, make or npm was used
(`R-144d`). Not run: the whole contract battery, the full frontend suite, the live journey
(`R-144b` waivers; documentation-only task).

## 3. Contracts, risks, limits

- New or changed contracts: none.
- The addendum describes scope the slices add and says so: `EXEC-SEAL-01` (schema, sealing),
  `EXEC-HTTP-01` (database-sourced `http_api`, `R-133` on the run path), `EXEC-PULL-01` (runner
  API, `runs/scope.py` wording), `EXEC-AGENT-01`, `EXEC-SSH-01`, `EXEC-VPN-01`. Until a slice merges,
  W54 behaviour stands. Slices run as parallel lanes where file ownership is disjoint
  (`R-144e`); the addendum claims no order or behaviour beyond its slice list.
- Known limits: none.

## 4. Integrator instruction and forbidden hotspots

Merge beside `EXEC-SEAL-01`; the two share no path. Revert the merge to roll back.
Forbidden hotspots (`src/**`, `web/**`, `contracts/**`, `db/migrations/**`, `infra/**`, dependency and
lock files, `runs/scope.py`, `CURRENT_STATE.md`, `DEBT_REGISTER.md`) are untouched: the diff names only
the four allowed paths.
