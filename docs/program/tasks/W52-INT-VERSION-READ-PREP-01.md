# Task W52-INT-VERSION-READ-PREP-01 — read one canonical product version

task_id: W52-INT-VERSION-READ-PREP-01

## Outcome

The releases context reads the single product `VERSION` relative to the
installed package and refuses missing, multi-line or noncanonical SemVer
content without using the working directory or a package placeholder version.

## Depends on

- `W52-INT-BUILD-ID-PREP-01` — completed on `origin/dev` at
  `4e41159cb3842e803f01e8b0f7f5095c1ece8562`.

## Frozen inputs

- Exact development base `4e41159cb3842e803f01e8b0f7f5095c1ece8562`.
- Domain candidate revision 9 / 29 opaque identities; API 27 paths / 34 operations /
  77 schemas; error catalog 23; migration head `0015_accounts_roles_registration`.
- `docs/program/dispatch/W52-PLAN.md` §3.1, read from the planning-owned
  `plan/roadmap-to-beta` worktree. This is pure preparation for
  `W52-RELEASES-API`, not Stage C completion or W52 freeze.
- Owner's code-first direction: basic tests and lint; QA/live and full gate
  remain D-139/D-140. No temporary stand.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W52 declares `VERSION` the one-line canonical SemVer source and
  requires startup refusal if it is missing or invalid; this base has no file.

### P-01 — source and absence

- captured_at: 2026-10-08
- command: `rg -n 'VERSION.*one line|VERSION.*only source|Fail closed.*VERSION' /root/projects/PDF-Analysis/.local/worktrees/plan-roadmap-to-beta/docs/program/dispatch/W52-PLAN.md; test -e VERSION; printf 'version_file_exit=%s\n' "$?"; git rev-parse HEAD; git status --short`
- captured_output:
  ```text
  49:- **`VERSION`** (root, one line, canonical SemVer 2.0, no build metadata) is the only source of
  74:- **Fail closed:** `VERSION` missing or not canonical → the API refuses to start with the existing
  version_file_exit=1
  4e41159cb3842e803f01e8b0f7f5095c1ece8562
  ```
- interpretation: Stage C still owns the root file and startup wiring; the
  helper must be exercised with synthetic files until then.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/releases/product_version.py` (new)
- `src/auditmanager/releases/public.py` (one export)
- `tests/integration/releases/test_product_version.py` (new)
- `docs/program/tasks/W52-INT-VERSION-READ-PREP-01.md`
- `docs/program/W52-INT-VERSION-READ-PREP-01.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/DEBT_REGISTER.md`

## Forbidden hotspots

Everything else, especially `VERSION` itself, release notes, contracts,
migration head, root dependency/lock files, composition root, Dockerfiles,
global styles, deployment files and `origin/main`.

## Non-goals

No version bump, startup wiring, ConfigurationError translation, release
loader, API operation, contract reseal, temporary stand, full gate, QA, tag
or deployment.

## Deliverables

- Public `read_product_version()` using `auditmanager.__file__` and the
  existing canonical SemVer rule.
- Pure tests for valid one-line forms, missing file and invalid content.
- Handoff with the remaining startup integration requirement.

## Required tests

- `.venv/bin/pytest -q tests/integration/releases/test_product_version.py`
- Programme governance/prose tests, frontend lint, Python compilation and
  `git diff --check`.
- Runtime startup refusal and full gate remain deferred.

## Integration contract

The future composition root calls `read_product_version()` at startup, turns
its `FileNotFoundError`/`ValueError` into the existing `ConfigurationError`,
and uses the returned value as the single product version. The integrator
publishes a fast-forward to `origin/dev` after focused checks and exact
remote-ref review.

## Failure/idempotency/security cases

- Reject non-ASCII, whitespace, extra lines, CRLF, build metadata and leading
  zeros without silently trimming or normalizing.
- An optional final LF is a file terminator, not part of the version.
- Missing file is a hard error; no package-version fallback.

## Rollback / feature flag

Revert this integration commit to remove the unused helper. No runtime
feature flag is needed until startup wiring is owned by Stage C.

## Handoff

- Changed files, checks/results, contracts, risks, integration instruction
  and forbidden-hotspot proof are in `docs/program/W52-INT-VERSION-READ-PREP-01.md`.
