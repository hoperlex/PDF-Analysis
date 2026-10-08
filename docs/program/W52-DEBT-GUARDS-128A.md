# W52-DEBT-GUARDS-128A — executor handoff

Task: `docs/program/tasks/W52-DEBT-GUARDS-128A.md`. Exact dispatch base:
`e57ce2b899e2fa082d1110c2d115ca2d7170f992`. This is D-128 F-3…F-6 only.

## Changes

- `tests/contract/program/test_wave_governance.py`: main authority requires a direct-owner
  marker tied to a 40-hex candidate SHA and may appear only with target `origin/main`.
  Historic `none; explanation` remains valid. This is a guard on task metadata, not itself
  proof that an instruction was given.
- `tests/contract/test_alpha_acceptance_command.py`: rejects positive proof claims in the
  generated report while keeping operator-input attestation.
- `tests/contract/test_deploy_auto_workflow.py`: rejects job-level permissions and extra
  known-host lines in the workflow's pinned `known_hosts` block.
- `tests/contract/architecture/test_alr05_boundaries.py`: catches literal dynamic imports
  via `importlib.import_module`, including aliases, across bounded contexts.

## Checks and limits

The four focused files passed 46 tests with the clean-checkout acceptance case excluded
while code edits were uncommitted. Python compilation and `git diff --check` passed. The
clean-checkout case must be rerun after committing this handoff. No stand, QA or full gate
was run, under D-139/D-140. The new probes cover the judge's F-3…F-6 counterexamples;
computed dynamic import names remain outside a static syntax guard.

No contracts or migration changed. F-1/F-2/F-7/F-10/F-11 and the broader D-128 row stay
open. The changed file list is exactly this handoff plus the four test files above;
contracts, migration head, dependencies, workflow, acceptance script, application code,
composition root and global styles are untouched. Revert the code commit for rollback;
there is no runtime feature flag. Integrator may merge this code preparation to dev after
checking the exact base and basic tests; it does not close W52.
