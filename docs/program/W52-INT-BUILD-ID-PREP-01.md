# W52-INT-BUILD-ID-PREP-01 — content-derived API build identity

Code commit `8356895d06f1bc3545c30463c596e0e146e4914c` builds on exact
`origin/dev` base `7f401d19ffe71a8b8344f94d00552ad4984fc05d`.
`auditmanager.releases.public.compute_build_id()` locates the repository
root from `auditmanager.__file__`, walks the five W52 directory roots plus
three named files, and hashes sorted manifest lines of relative path and
SHA-256 file digest. It returns `b` plus the first 16 hex characters of the
manifest digest. It skips bytecode caches and symlinks, and refuses a missing
required root/file instead of hashing a partial image.

## Checks

- Pure build-identity tests: **7 passed**. A separately assembled manifest
  gives the same digest; an equal tree at another path and working directory
  gives the same id; changed or added included bytes move it; ignored cache
  and unrelated files do not; three required-input omissions refuse.
- Existing SemVer tests: **23 passed**; programme governance and live-prose
  tests: **60 passed**. Combined focused command: **90 passed**.
- Python compilation, frontend lint and `git diff --check`: passed.
- No current-checkout build id was asserted: `VERSION` and `release-notes/`
  are Stage C deliverables and do not yet exist on `origin/dev`. The later
  Dockerfile COPYs, `.dockerignore` coverage guard, built-image parity,
  composition startup binding, QA/live and full `make gate` remain open. No
  `GATE OK` is claimed; D-139/D-140 remain open.

## Handoff

The future `W52-RELEASES-API` lane must add `VERSION`, release notes and the
three Dockerfile COPYs, call `compute_build_id()` once during application
composition, translate a missing-input refusal into the startup
`ConfigurationError`, and compare checkout versus image output. The helper
reads only its explicit roots and exposes no file bytes.

Changed tracked files: `src/auditmanager/releases/build_id.py`,
`src/auditmanager/releases/public.py`,
`tests/integration/releases/test_build_id.py`,
`docs/program/tasks/W52-INT-BUILD-ID-PREP-01.md`, this report,
`docs/program/CURRENT_STATE.md` and `docs/program/DEBT_REGISTER.md`.
No contract, migration, root dependency/lock, composition root, Dockerfile,
global style, deployment file or product version changed. The integrator may
publish code and documentation together as a fast-forward of `origin/dev`
after exact remote-ref review. `origin/main` has no authority in this task.
Revert the integration commits to remove this unused helper.
