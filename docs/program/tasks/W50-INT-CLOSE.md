# Task W50-INT-CLOSE — close W50 on the development line

## Outcome

The W50 shell has a checked closure record, its three judge findings are open in the debt
register, its development state and lane reservations are current, and the exact accepted
closure commit is published by fast-forward to `origin/dev`.

## Depends on

- `W50-FIX` — completed at `d8ea61351489fcf08c7ebfe8ff90045b2127b559`, merged at
  `347ad2654713ff3e027ad6d0bb501090df3d4608`. Its dependencies `W50-QA-01`,
  `W50-JUDGE-X` and `W50-JUDGE-Y` are complete and merged.

## Frozen inputs

- Base integration commit: `347ad2654713ff3e027ad6d0bb501090df3d4608`.
- Last complete-gate tree: `d8ea61351489fcf08c7ebfe8ff90045b2127b559`, literal
  `GATE OK` (3201 backend passed / 6 skipped; 1660 frontend tests), then post-merge light
  acceptance on `347ad26` with literal `LIGHT ACCEPTANCE OK`.
- `origin/dev` before closure: `256e24e1d1eff61dabd3a244cef0b89d12019b41`, re-read
  before publication; `origin/main` is outside this task.
- Domain: `1.0.0-draft.1` revision 9, 29 opaque identities. API: 27 paths / 34 operations /
  77 schemas. Error catalog: 23. Migration head: `0015_accounts_roles_registration`.
- Controlling inputs: `W50-FREEZE-01.md`, `W50-PLAN.md`, both W50 judge reports,
  `W50-FIX.md`, `AGENTS.md` §8 and owner ruling `R-70` in
  `OWNER_RULINGS_2026-09-17.md` §3.25.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: `347ad26` is a clean accepted integration base, `dev` still names `256e24e`,
  and `D-133` is the highest existing debt ID

### P-01 — the next debt IDs are D-134 through D-136

- captured_at: 2026-10-07
- command: `git show 347ad2654713ff3e027ad6d0bb501090df3d4608:docs/program/DEBT_REGISTER.md | rg -o 'D-13[0-9]+' | sort -Vu`
- captured_output:
  ```text
  D-130
  D-131
  D-132
  D-133
  ```
- interpretation: three new register-only W50 findings can receive consecutive IDs.

### P-02 — the integration tree and development ref match the handoff

- captured_at: 2026-10-07
- command: `git ls-remote origin refs/heads/dev refs/heads/main`
- captured_output:
  ```text
  256e24e1d1eff61dabd3a244cef0b89d12019b41 refs/heads/dev
  3a54108ba8dbcd9723cdeb7c6ad1fb0c0209b801 refs/heads/main
  ```
- interpretation: closure begins on the accepted FIX merge; a fresh remote read is still
  mandatory immediately before push.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

Judge and lane reports stay immutable. Corrections to the source comments and the W50 plan are
future work under another grant; this close only registers their findings.

## Publication authority

- development_target: origin/dev
- origin_main_authority: none; `origin/main` and release tags are outside this task

## Allowed paths

- `docs/program/tasks/W50-INT-CLOSE.md`
- `docs/program/W50-INT-CLOSE.md`
- `docs/program/CURRENT_STATE.md` — current W50/W51 section only
- `docs/program/DEBT_REGISTER.md` — W50 debt entries and current summary only
- `docs/program/dispatch/PORT_REGISTRY.md` — W50 lane row status only
- local `integration/w50` and the fast-forward publication of that exact commit to `origin/dev`

## Forbidden hotspots

- Everything else: `contracts/**`, `db/migrations/**`, `infra/**`, root dependencies/locks,
  composition roots, product code/tests/styles, planning branches/worktrees, `origin/main`,
  tags and deployment.

## Non-goals

- No product or contract changes, judge-report rewrite, release tag, stand deployment or
  publication to `origin/main`.
- Do not repair D-134 through D-136 within this close task.

## Deliverables

- Open `D-134` … `D-136`, each with source and reproducible check.
- Current development section declaring W50 closed on `dev`, W51 next, and no deployment claim.
- W50 port rows released after confirming no W50 containers or volumes remain.
- `W50-INT-CLOSE.md` with lineage, gate/light-acceptance evidence, W49-to-W50 count deltas,
  grants, judge disposition, frozen contracts, risks, rollback and integration instructions.
- An exact tested SHA and read-back proof that `origin/dev` equals it.

## Required tests

- `git diff --check` and a path-grant diff against the pre-close base.
- Confirm the frozen API/error/domain/migration set and W50 lane cleanup from existing evidence
  and read-only host checks.
- On the clean committed close candidate: `make light-acceptance
  BASE=d8ea61351489fcf08c7ebfe8ff90045b2127b559`, requiring literal
  `LIGHT ACCEPTANCE OK`. Under `R-70`, this docs-only diff requires light acceptance; the
  complete `make gate` already passed on the FIX lane's Makefile-changing tree. Any newly
  touched `R-70` risk path instead requires another full gate.
- Re-read remote `dev`, prove ancestor relationship to the exact candidate, push without
  force, then prove `git ls-remote origin refs/heads/dev` equals that candidate.

## Integration contract

The integrator alone commits the five allowed documentation files on `integration/w50`,
accepts the clean exact commit, and publishes it to `origin/dev`. The W51 base is that verified
development ref. The older generic complete-gate wording in `IDENTITY-WAVES.md` §8 and
`W50-PLAN.md` is read under later owner ruling `R-70` and `AGENTS.md` §8.

## Failure/idempotency/security cases

- A changed remote `dev` or non-ancestor relationship stops publication pending integration.
- No force push, no edit while acceptance runs, no credential or stand mutation.
- If acceptance fails, repair within the grant, commit and rerun on the new exact tree.

## Rollback / feature flag

No behavior or flag changes. Revert the documentation close commit on `dev` if its record is
wrong; W50 product rollback would need a separately authorized integration decision.

## Handoff

- changed files: the five granted documentation files
- commands/results: exact clean candidate, literal light-acceptance sentinel, remote proof
- known limits: D-134 through D-136 remain open; `origin/main` stays unchanged
- integration notes: W51 starts from the verified `origin/dev` subject
