# W52-INT-VERSION-READ-PREP-01 — canonical product VERSION reader

Code commit `3be254b895ed75388062f807fa7789fd7749177f` builds on exact
`origin/dev` base `4e41159cb3842e803f01e8b0f7f5095c1ece8562`.
`auditmanager.releases.public.read_product_version()` locates `VERSION`
relative to `auditmanager.__file__`, reads exactly one canonical SemVer 2.0
line and returns it. It accepts one optional final LF; it refuses missing,
non-ASCII, extra lines, surrounding whitespace, CRLF, leading zeros and
build metadata. It never consults the working directory or package metadata.

## Checks

- Pure product-version tests: **12 passed** on synthetic package trees.
- Existing build-id and SemVer tests: **30 passed**; programme governance and
  live-prose contract tests: **60 passed**. Combined focused command:
  **102 passed**.
- Python compilation, frontend lint and `git diff --check`: passed.
- No current-checkout read was attempted: `VERSION` is a Stage C deliverable
  and is absent on `origin/dev`. Startup `ConfigurationError` translation,
  API use, QA/live and full `make gate` remain open. No `GATE OK` is claimed;
  D-139/D-140 remain open.

## Handoff

`W52-RELEASES-API` must create the root `VERSION`, ship it in the API image,
call this public reader once at application composition, and translate
`FileNotFoundError` or `ValueError` into the existing startup
`ConfigurationError`. It must use the returned string as the sole product
version; `contract_version` stays a separate frozen value pending its owner
decision.

Changed tracked files: `src/auditmanager/releases/product_version.py`,
`src/auditmanager/releases/public.py`,
`tests/integration/releases/test_product_version.py`,
`docs/program/tasks/W52-INT-VERSION-READ-PREP-01.md`, this report,
`docs/program/CURRENT_STATE.md` and `docs/program/DEBT_REGISTER.md`.
No contract, migration, root dependency/lock, composition root, Dockerfile,
global style, deployment file or product VERSION changed. The integrator may
publish code and documentation together as a fast-forward of `origin/dev`
after exact remote-ref review. `origin/main` has no authority in this task.
Revert the integration commits to remove this unused helper.
