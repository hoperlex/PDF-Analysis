# Task W49-ACCESS-01 — migration 0015, the access domain and its repository (01a, 01b, 01c)

## Outcome

Accounts carry an e-mail login, names, a role set, archive state and profile completion; registration requests have a lifecycle; every invariant of `W49-PLAN.md` §3.1–§3.3 holds at repository level; migration `0015` upgrades a `0014` database holding the seeded account.

## Depends on

- `W49-FREEZE-01`

## Frozen inputs

- domain contract: revision 8, 27 opaque identities (moves only in `W49-SEAL-01`)
- API contract: 17 / 20 / 61 (moves only in `W49-SEAL-01`)
- error catalog: 22 codes (moves only in `W49-SEAL-01`: `rate_limited`)
- migration head: `0014_durable_analysis_effects` (moves only in `W49-ACCESS-01`)
- code base: `23e0579`, the W48 closure published to `origin/dev`
- controlling plan: `docs/program/dispatch/W49-PLAN.md` at the freeze commit

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `db/migrations/versions/`
- enumerator_owner: `W49-ACCESS-01`
- totality_query: `PYTHONPATH=src .venv/bin/alembic -c db/migrations/alembic.ini heads` → exactly one head

## Captured premise evidence

- premise: the migration head is 0014 and exactly one head exists

### P-01 — base measurement

- captured_at: 2026-10-05
- command: `PYTHONPATH=src .venv/bin/alembic -c db/migrations/alembic.ini heads`
- captured_output:
  ```text
  0014_durable_analysis_effects (head)
  ```
- interpretation: measured on the code base before dispatch; the lane re-measures it first.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/dispatch/W49-PLAN.md`
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/access/**`
- `db/migrations/versions/` — one new file for revision `0015`
- `tests/integration/access/**`
- `tests/integration/db/**`
- `tests/integration/p02_journey/journey.py` — `P02_TABLES` only
- `tests/contract/api_v1/test_doc_prose_facts.py` — the migration-head pin line only
- `docs/program/CONTRACT_PIN_REGISTRY.md` — the migration-head rows only
- `docs/program/CURRENT_STATE.md` — the one live sentence naming the migration head
- `docs/manual-tests/PC-01_prototype.md` — the one live sentence naming the migration head
- `docs/program/W49-ACCESS-01a.md`, `docs/program/W49-ACCESS-01b.md`, `docs/program/W49-ACCESS-01c.md`

## Forbidden hotspots

- every path not listed above; `contracts/**` outside `W49-SEAL-01`; root locks; refs, tags, deployment and secrets; `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md` except an exact sentence named here; `src/auditmanager/api/**`, `src/auditmanager/bootstrap/**`, `src/auditmanager/decisions/**`, `web/**`

## Non-goals

- no router, no contract, no screen; `expert_decision_event.author_user_uid` is added as a column only (its writer is `W49-DECISIONS-01`)

## Deliverables

- 01a: migration `0015` (every table, column, index, foreign key and trigger of `W49-PLAN.md` §3.1–§3.3, the role backfill, a downgrade that refuses while `app_user_role` or `registration_request` hold rows), the reference-register test against the schema's foreign keys to `app_user`, CLIs `python -m auditmanager.access.profile` and `python -m auditmanager.access.grant`, the head pins of `W49-PLAN.md` §3.6
- 01b: normalisation and name rules, `display_label` precedence, the repository read of roles/archive/profile, archive/restore/purge against the register, every §3.2 invariant
- 01c: role grant/revoke with epoch bump; registration submit, approve (one transaction, `FOR UPDATE`), reject, status read with constant work, password-column nulling, queue cap, throttle columns
- three reports, one per part

## Required tests

- fresh upgrade to `0015`; downgrade on an empty tree; upgrade from a `0014` database holding the seeded `admin` with a changed password, and from one holding a legacy non-e-mail login
- the trigger refuses a second decision, a password-column write after decision and a manual `created_user_uid` UPDATE; the partial unique index proven by two rows
- 01a: `.venv/bin/python -m pytest tests/integration/db tests/integration/p02_journey tests/contract/api_v1/test_doc_prose_facts.py -q`
- 01b: `.venv/bin/python -m pytest tests/integration/access -q`
- 01c: `make gate` with literal `GATE OK`

## Integration contract

`access` exposes, through `auditmanager.access.public`, the repository methods `W49-SEAL-01` wires: profile read/update, roles, archive/restore/purge, registration lifecycle and the standing read (roles, archived, profile_complete).

## Failure/idempotency/security cases

- unique lane ports taken with `ss -ltn` and recorded; owned disposable services only; never kill a process by pattern; no credential in evidence
- every invariant tested without the router; concurrency of approve tested with two sessions

## Rollback / feature flag

`0015` is forward-only on any real database after its backfill; the rollback of W49 is a database restore. On an empty tree the downgrade is tested.

## Handoff

- changed files: listed in `docs/program/W49-ACCESS-01.md` with `git diff --name-only <base>..<sha>`
- commands/results: verbatim with exit status; every mutation with its red output
- known limits: listed, never decided silently
- integration notes: hand back branch `agent/w49-access-01` at a recorded SHA
