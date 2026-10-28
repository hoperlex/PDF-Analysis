# Scripts

Repository-local operational/developer scripts only. Each script must have a stable purpose, safe defaults and a documented caller. Business rules must not live only in a one-off script.

## Lane preparation and technical handoff

The integrator assigns a full base SHA and, if services are needed, the six lane
resources in `docs/program/tasks/<TASK_ID>.md`. `Allowed paths` uses one exact path
or one `directory/**` prefix per bullet. Commit the task file before running the
preparation command. Before creating a worktree, inspect the
task's dependencies and frozen contract set as `AGENTS.md` requires.

```bash
python3 scripts/lane_prepare.py --task docs/program/tasks/<TASK_ID>.md --dry-run
python3 scripts/lane_prepare.py --task docs/program/tasks/<TASK_ID>.md
```

`lane_prepare.py` creates `.local/worktrees/<TASK_ID>` at the exact base on
`agent/<TASK_ID>`, writes only disposable `.env.example` values with the assigned
instance and ports, then runs `make bootstrap` and `npm --prefix web ci` in that
worktree. Use `--foundation-python /absolute/path/to/python3.12` when it is not
on `PATH`. `--no-install` prepares the worktree and `.env` without installing
dependencies. A repeat on the same untouched worktree is safe; a conflicting
base, branch, environment or resource reservation is refused. The integrator
continues to own port assignment. Finished lanes are inspected and removed only
through `scripts/worktree_cleanup.py` under its existing safety checks.

After the lane is committed and clean, run the handoff tool from the checkout
holding the committed task file. The task's frozen base may precede the
dispatch commit, so the lane worktree need not contain the task file:

```bash
python3 scripts/task_handoff.py --task docs/program/tasks/<TASK_ID>.md \
  --worktree .local/worktrees/<TASK_ID> \
  --check-json '["git","diff","--check"]'
```

Each `--check-json` is one argv array, executed without a shell. The tool checks
the task's exact base, every changed path (including both sides of a rename),
`git diff --check`, clean status and an unchanged HEAD around each check. It
writes a technical Markdown report and full check logs under ignored `.local/`.
The report labels absent or red checks as incomplete and leaves contract changes,
risks, integration notes and required test coverage for a reviewer. It does not
replace the six-item task handoff, authorise a merge or publish a ref.
Do not put credentials in check arguments or run checks that print credentials:
arguments and output are retained in the local evidence files.

## Bootstrap validator

From a clean checkout, create the repository-local validation environment and
install the hash-locked dependency set:

```bash
python3 -m venv .venv/bootstrap
.venv/bootstrap/bin/python -m pip install --require-hashes --requirement requirements/validation.lock
```

Then run `.venv/bootstrap/bin/python scripts/validate_bootstrap.py` from the
repository checkout to check the bootstrap JSON schemas and examples, domain
invariants, internal Markdown links and required repository shape.

The validator must run inside a Git checkout. It discovers both tracked files and
untracked work through Git while honoring repository ignore rules. Ignored/private
or generated trees such as `.venv`, `node_modules`, `.local`, caches and
`fixtures/private` are neither opened nor counted. A Git discovery failure is a
validation failure; the script never falls back to scanning the entire filesystem
tree. The private/dependency/cache deny policy is unconditional: content under a
denied path remains excluded even if it was force-added to the Git index, including
nested `.venv`, `node_modules`, cache directories and any `fixtures/private`
component sequence regardless of depth.

The Python environment running the command must provide a compatible `jsonschema`
package with `Draft202012Validator`. This is a mandatory prerequisite: if the
package cannot be imported or is unusable, the validator reports `jsonschema`,
prints the action needed to provision it in that Python environment, and exits
non-zero without printing `PASS`.

`requirements/validation.in` contains the direct validation dependency;
`requirements/validation.lock` pins its full transitive set and artifact hashes.
The lock was generated with `pip-tools 7.5.0` under Python 3.12. Regeneration is a
separately reviewed root dependency-hotspot change and must update both files. This
validation-only lock is generated and maintained for CPython 3.12. It is a
verification prerequisite only: it does not select or freeze the CP-01 application
runtime or application package manager.

Exit code `0` together with a standalone `PASS` line means schema tooling was
available and every validator check completed successfully. Any missing prerequisite
or failed check produces no standalone `PASS` line. Exit `1` means repository
discovery or content/invariant validation failed with accumulated artifact-specific
diagnostics. Exit `2` means required `jsonschema` machinery was unavailable or
unusable. Expected malformed or missing repository inputs never emit a traceback.

Domain error-catalog validation reads `contract_version` from
`contracts/domain/v1/error-codes.json` and requires it to be a non-empty string. That
key is canonical by owner decision `ID-01`. The bare `version` key is neither required
nor rejected: it remains only as a transitional deprecated mirror, and its removal is
the domain contract owner's follow-up (`W0-DOM-02`). A catalog that declares only the
bare `version` key fails with an accumulated, artifact-specific diagnostic naming the
missing `contract_version`.

ADR validation preserves baseline IDs ADR-0001 through ADR-0018 and requires exact
agreement between current ADR files and `docs/architecture/ADR_INDEX.md`. Additional
uniquely numbered ADRs are allowed only when indexed.

## AR v3 live activation

`scripts/ar-v3/activate-live.sh` — the owner's one-script path for steps 10a, 10b and 11 of `docs/program/AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01.md` (`R-146be`). Caller: the owner, in the deployed clone on the live host. Safe default: `--check` writes nothing; every write step asks for a typed word; `--rollback` withdraws the pack. Tested with a stand-in `docker` only.
