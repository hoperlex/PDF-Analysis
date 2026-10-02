# Task W48-LIVE — repository-owned external alpha acceptance gate

## Outcome

D-108 closes with a named non-hermetic release command that cannot pass without executing every
requested automated phase and that records candidate SHA separately from deployed SHA. The
deterministic `make gate` remains host- and credential-free.

## Depends on

- `ALPHA-MANUAL-01` — completed at `a20d890`
- `W48-JUDGE-A` — completed at `d5655ec`
- `W48-FIX` — completed at `fad3c28748ef52bc9b5f711191ff0130483e0055`

## Frozen inputs

- Stage-B base: `fad3c28748ef52bc9b5f711191ff0130483e0055`
- API: 17 paths / 20 operations / 61 schemas; error catalog: 22
- migration head: `0013_norm_embeddings`
- PC-01 manifest: 16 address records, 3 write steps, 6 refusal cases, 780 x 900 viewport
- public origin and reviewer credential: required runtime inputs, never repository defaults

## Allowed paths

- `Makefile`
- `scripts/manual-alpha-check.sh`
- `tests/e2e/pc01/**`
- `tests/contract/test_alpha_acceptance_command.py`
- `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md`
- `docs/program/W48-LIVE.md`

This task is the sole W48 owner of `Makefile`.

## Forbidden hotspots

- workflow and `infra/deploy/**`
- contracts, generated clients, error catalog and migrations
- production backend/frontend code, dependencies/locks, composition root and global styles
- programme state/register/history, refs, tags, host mutation and secret stores

## Non-goals

- no external system inside `make gate`
- no default origin, login, password, cookie, token or provider credential
- no automated claim that the human A01-A12 checklist was performed
- no deployment, push, tag or mutation of public-alpha data during command-surface tests

## Deliverables

- explicit `make alpha-acceptance` release target beside, not inside, `make gate`
- command preflight plus sign-in, 3/3 writes, 16/16 cold routes, six refusals and width assertion
- evidence schema with candidate/deployed SHA, phase outcomes and `PASS`/`FAIL`/`BLOCKED`
- updated runbook and focused command-surface tests
- completion report `docs/program/W48-LIVE.md`

## Required tests

- `bash -n scripts/manual-alpha-check.sh`
- `scripts/manual-alpha-check.sh --files-only`
- `.venv/bin/python -m pytest tests/contract/test_alpha_acceptance_command.py
  tests/e2e/test_pc01_journey_conformance.py -q`
- command-surface stubs prove missing origin/credential/SHA, skipped requested phase, live failure
  and dependency outage cannot print `PASS`
- `make gate` remains hermetic and contains no alpha-acceptance prerequisite
- `git diff --check` and an allowed-path-only diff

## Integration contract

`make alpha-acceptance` requires explicit origin, reviewer credential channel, candidate SHA and
deployed SHA evidence. Exit 0 and `ALPHA ACCEPTANCE PASS` mean every requested automated phase
ran successfully and the two SHAs satisfy the documented release rule. Missing access or an
unreachable external dependency is `BLOCKED`; an observed product violation is `FAIL`. Human
A01-A12 is recorded separately and remains required for release closure.

## Failure/idempotency/security cases

- no requested phase may be silently skipped or converted to success
- credentials are accepted only through the journey's existing environment boundary and are
  never written to evidence or argv examples
- candidate and deployed SHA are distinct named facts; hostname is not identity
- test doubles use temporary evidence directories and leave no public data or secret behind

## Rollback / feature flag

Command/runbook only. Rollback is a revert; no runtime feature flag or data migration applies.

## Handoff

- changed files/checks: recorded in `docs/program/W48-LIVE.md`
- contracts/runtime: unchanged
- known limit: a real public run and human signature remain closing evidence, not lane evidence
- integration note: execute only after WEB is merged; no push to `main` belongs to this task
