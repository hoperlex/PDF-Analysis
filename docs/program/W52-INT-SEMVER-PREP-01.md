# W52-INT-SEMVER-PREP-01 — canonical release ordering

Code commit `73bdf86cb33f748a3601ef4e600eed78bc622d40` builds on exact
`origin/dev` base `b91138c6a4942959e5287df07193ea4d485b5776`.
The new `auditmanager.releases.public.canonical_semver_sort_key` accepts
canonical SemVer 2.0 versions without build metadata and returns an ASCII text
key. Its bytewise order handles numeric major/minor/patch width, numeric versus
alphanumeric prerelease identifiers, identifier prefixes, list length and the
final release above its prereleases. Invalid spelling raises `ValueError`.

## Checks

- Pure releases tests: **23 passed**. They include the SemVer precedence
  example, `0.9.0 < 0.10.0`, `beta.2 < beta.11`, numeric versus alphanumeric
  identifiers and invalid forms. An initial test run had one incorrectly
  ordered expected example (`a-` versus `a.1`); the example was corrected and
  the suite rerun green.
- Programme governance and live-prose contract tests: **60 passed**; combined
  focused command: **83 passed**.
- Python compilation, frontend lint and `git diff --check`: passed.
- No database-backed ordering, full `make gate`, QA, live/manual acceptance or
  release was run. No `GATE OK` is claimed; D-139/D-140 remain open.

## Integration condition

The future `0016_release_notes` migration must store this text key with
bytewise PostgreSQL collation (`COLLATE "C"`), and the loader must call the
public function. Locale-dependent text collation is not an ordering proof.
The code has no runtime consumer yet, so it does not activate release
behaviour. W52 owner confirmations, SEAL, API/WEB, loader, release notes and
validation remain pending.

Changed tracked files: `src/auditmanager/releases/__init__.py`,
`src/auditmanager/releases/versioning.py`,
`src/auditmanager/releases/public.py`,
`tests/integration/releases/test_version_order.py`,
`docs/program/tasks/W52-INT-SEMVER-PREP-01.md`, this report,
`docs/program/CURRENT_STATE.md` and `docs/program/DEBT_REGISTER.md`.
No contract, migration, root dependency/lock, composition root, global style,
deployment file or product version changed. The integrator may publish the
code and documentation together as a fast-forward to `origin/dev` after exact
remote-ref review. `origin/main` has no authority in this task. Revert the
integration commits to remove this unused helper.
