# Task P1-NAV-02 — reconcile the foundation navigation entries after PF-01

> **Status: specified; not dispatchable.** It becomes dispatchable when `PF-01` is
> accepted. It is the last gate before P02 fan-out.

## Outcome

The foundation seams that `P1-NAV-01` authored as `planned` are flipped to `implemented`
against the accepted `PF-01` tree, and the regenerated aggregate index resolves every one
of them to a file and a public symbol that actually exist.

## Depends on

- none complete at plan time

Planned predecessors and dispatch conditions — this task is not dispatchable until both
hold:

  - `P1-NAV-01` accepted and integrated, supplying the schema, the tooling and the named
    `planned` entry list
  - `P1-INT-01` accepted, that is `PF-01`, so that the provider files the entries name
    exist in the tree

## Frozen inputs

- the `P1-NAV-01` schema, tooling and entry inventory at their accepted commit
- the accepted `PF-01` provider commits and `FOUNDATION_LOCK.json`
- ADR-0019 item 5: only the integration owner writes generated aggregate output
- migration head: the P01 baseline, read only
- base commit: the accepted `P1-INT-01` integration commit

## Allowed paths

- `docs/navigation/entries/foundation-*.json` — the exact fragments named in the
  `P1-NAV-01` handoff, and no others
- `docs/navigation/INDEX.md` — regeneration only, as the integration owner of this batch
- `docs/program/tasks/P1-NAV-02.md` status/handoff

## Forbidden hotspots

- `docs/navigation/navigation-entry.schema.json`, `docs/navigation/incident.schema.json`,
  `docs/navigation/README.md` and `tools/navigation/**`, all owned by `P1-NAV-01`
- every navigation fragment not named in the `P1-NAV-01` handoff
- `Makefile`, root locks, `contracts/**`, `fixtures/**`, `scripts/**`, `tests/**`,
  `src/auditmanager/**`, `infra/local/**`, `db/migrations/**`, `web/**`
- `docs/architecture/**`, CP-00 evidence and Git tags

## Non-goals

- No schema or tooling change; a validator defect is returned to `P1-NAV-01`, not patched
  here.
- No new entry for code that does not yet exist, and no P02 entry.
- No provider repair and no foundation change.

## Deliverables

- each named foundation fragment moved from `planned` to `implemented`, carrying the real
  file path and public symbol of the accepted provider
- the regenerated `docs/navigation/INDEX.md`
- a short reconciliation note listing each flipped `entry_id`, the accepted provider commit
  it now points at, and any entry deliberately left `planned` with the reason

## Required tests

- Command: `.venv/bootstrap/bin/python tools/navigation/validate_navigation.py`
  Expected: exit `0`; no `implemented` entry names a path that does not exist, which is the
  check that makes this flip meaningful rather than clerical.
- Command: `.venv/bootstrap/bin/python tools/navigation/generate_index.py --check`
  Expected: exit `0`; the committed index is byte-identical to a fresh generation.
- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`
  Expected: exit `0`, standalone `PASS`.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

After this task, P02 fan-out may begin: every foundation seam a P02 task consumes resolves
through the index to a file that exists. P02 tasks then own their own fragments, and the
next aggregate regeneration belongs to `P2-INT-02`.

## Failure/idempotency/security cases

- Re-running the flip on an already reconciled tree changes no file.
- An entry whose provider path is absent fails validation rather than being flipped
  optimistically.
- No credential, payload or internal object key enters the layer.

## Rollback / feature flag

Documentation only. Revert the commit; the entries return to `planned` and P02 fan-out
stays closed, which is the correct state if `PF-01` is withdrawn.

## Estimate

Effort P50 0.5 person-day, P80 1.0 person-day. It sits on the `PF-01` to `PC-01` elapsed
path because P02 fan-out waits for it.

## Handoff

- the flipped `entry_id` list with the provider commit each now resolves to
- entries left `planned` and why
- commands and results
