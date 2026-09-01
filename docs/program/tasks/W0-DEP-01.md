# Task W0-DEP-01 — reproducible bootstrap-validation dependencies

## Outcome

Replace the ephemeral `/tmp` prerequisite with a repository-owned, hash-locked
bootstrap-validation dependency set. A clean checkout can create an isolated
workspace environment, install the lock and run the real schema validator without
choosing the CP-01 application package manager or adding production dependencies.

## Ownership

- implementation owner / root dependency hotspot owner: primary agent `/root`
- consumers: all W0.2 task owners and independent reviewers
- independent reviewer: assigned by the integrator; must not author these files
- product/domain approval authority: not required for this tooling-only dependency

## Depends on

- Completed `W0-QA-00`, accepted at
  `c25ff4a5393595260384aaffea1fddc2382189e8`.

## Frozen inputs

- base commit: `a2fc5cb20ed0f47c108e8d4a545c276efe0e528b`
- validator CLI contract from `W0-QA-00`: read-only
- application dependency/toolchain choice: deferred to `W1-INT-00`
- all machine contracts and migration head: read-only; migration head is none

## Allowed paths

- `requirements/validation.in`
- `requirements/validation.lock`
- `scripts/README.md`

No other root manifest, lock or path is writable.

## Forbidden hotspots

- `pyproject.toml`, application/backend/frontend dependency manifests and locks
- `scripts/validate_bootstrap.py` and tests
- `contracts/**`, migrations, composition root and global styles
- program/current/checkpoint docs except this integrator-authored task file
- every legacy repository path/ref/worktree entry

## Non-goals

- No selection of `uv`, Poetry, pip-tools or another CP-01 project package manager.
- No production/runtime dependency set and no editable install of the application.
- No vendored wheel, virtual environment, cache or generated package artifact.
- No validator behavior change and no weakening of fail-closed import behavior.

## Deliverables

- `requirements/validation.in` declares only the direct bootstrap validation
  dependency with an exact accepted version.
- `requirements/validation.lock` pins the complete transitive set and artifact
  hashes; installation uses `pip --require-hashes`.
- `scripts/README.md` documents clean-checkout creation of `.venv/bootstrap`, locked
  installation, the canonical validator command and rebuild policy.
- `.venv/` remains ignored and is never committed.

## Required tests

- Command: `python3 -m venv .venv/bootstrap`.
  Expected: exit `0`; the ignored local environment is created.
- Command: `.venv/bootstrap/bin/python -m pip install --require-hashes --requirement requirements/validation.lock`.
  Expected: exit `0`; every installed artifact matches the lock.
- Command: `.venv/bootstrap/bin/python -c "import importlib.metadata as m; assert m.version('jsonschema') == '4.26.0'"`.
  Expected: exit `0`.
- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`.
  Expected: exit `0` with standalone `PASS`.
- Command: `git check-ignore .venv/bootstrap`.
  Expected: exit `0` and output identifying the ignored environment.
- Command: `git diff --check -- requirements/validation.in requirements/validation.lock scripts/README.md`.
  Expected: exit `0` and no output.

## Integration contract

W0.2 commands use `.venv/bootstrap/bin/python` after the documented one-time locked
installation. No gate relies on `/tmp`, ambient site-packages or an unpinned resolver.
The lock is validation-only and does not freeze the CP-01 application toolchain.

## Failure/idempotency/security cases

- Missing Python/venv/network/cache or hash mismatch fails visibly; no fallback to
  ambient packages or unpinned `pip install jsonschema`.
- Re-running installation against the same lock is idempotent.
- Lock and logs contain no credentials, private index URL or environment values.
- A dependency update changes both `.in` and lock in a separately reviewed
  root-hotspot task.

## Rollback / feature flag

No feature flag. Revert only the validation requirements and README changes; the
ignored local environment can be discarded independently and is not repository
state.

## Handoff

- changed files and direct/transitive versions
- lock-generation command/tool version and install/validator results
- new/changed contracts: validation dependency lock only
- known platform/index limitations
- integration instruction replacing every `/tmp` gate
- proof that no application manifest, contract, migration or legacy file changed
