# Task W48-GOV — make ownership and evidence discipline executable

## Outcome

D-89, D-96, D-117, the D-77 branch lesson and the stale D-52 evidence become maintained rules:
tasks name enumerator owners, exact premises carry captured dated output, historical records are
annotated rather than rewritten, and development publication stops at `origin/dev` unless the
owner directly authorises an exact `origin/main` candidate.

## Depends on

- `MAIN-REF-POLICY-01` — completed at `6118e66`
- `W48-AUDIT` — completed at `c11f1b6`
- `W48-JUDGE-A` — completed at `d5655ec`
- `W48-FIX` — completed at `fad3c28748ef52bc9b5f711191ff0130483e0055`

## Frozen inputs

- Stage-B base: `fad3c28748ef52bc9b5f711191ff0130483e0055`
- API: 17 paths / 20 operations / 61 schemas; error catalog: 22
- migration head: `0013_norm_embeddings`
- policy: development candidates publish to `origin/dev`; `origin/main` requires a separate
  direct owner instruction and triggers deployment
- findings: D-52, D-77, D-89, D-96, D-117 and `W48-AUDIT` A-05

## Allowed paths

- `docs/templates/TASK_TEMPLATE.md`
- `docs/program/WAVE_EXECUTION_GUIDE.md`
- `docs/program/dispatch/OPERATING_CONSTRAINTS.md`
- `docs/program/W46-HISTORICAL-ADDENDUM.md`
- `tests/contract/program/test_wave_governance.py`
- `docs/program/W48-GOV.md`

## Forbidden hotspots

- historical W46 stream reports and all other historical reports
- `CURRENT_STATE.md` and `DEBT_REGISTER.md` — integration-close ownership
- contracts, generated clients, error catalog, migrations and all runtime sources
- dependencies/locks, `Makefile`, composition/global styles, workflow/deploy files
- refs, tags, host state and secrets

## Non-goals

- no retroactive rewrite of a report or fabricated missing command output
- no publication to either remote ref
- no runtime/API/deployment change
- no claim that D-52 was never real; record the later repair and proof as an addendum

## Deliverables

- task template fields for enumerator ownership and dated captured premise evidence
- execution/operating rules for historical addenda and branch roles
- immutable W46 addendum correcting D-117 without editing original reports
- executable documentary guard with invalid examples that fail
- completion report `docs/program/W48-GOV.md`

## Required tests

- `.venv/bin/python -m pytest tests/contract/program/test_wave_governance.py -q`
- invalid examples: missing enumerator owner, command without dated output, rewritten-history
  instruction and implicit `main` publication each fail for their intended rule
- query verifies the original W46 reports are byte-identical to the Stage-B base
- `git diff --check` and an allowed-path-only diff

## Integration contract

Any task adding a route, screen, error or migration names the enumerating file and sole owner.
Any exact path/line/count premise includes captured query output and its date. Corrections to
immutable task/review evidence are new addenda. `origin/dev` is the integration-candidate ref;
`origin/main` is a separately authorised auto-deploy ref and is never an implicit close step.

## Failure/idempotency/security cases

- a superficially complete task that omits enumerator ownership fails the guard
- a plausible command without captured dated output does not satisfy the evidence rule
- branch wording cannot equate a dev candidate with a deployed main SHA
- no credential, remote write or mutable external state participates in the guard

## Rollback / feature flag

Documentation and tests only. Revert the task commit if the rule is unsound; no feature flag or
data rollback applies.

## Handoff

- changed files/checks: recorded in `docs/program/W48-GOV.md`
- contracts/runtime: unchanged
- known limit: `W48-INT-CLOSE` alone reconciles live state/register rows
- integration note: merge after LIVE so final branch wording can be reviewed against the command
