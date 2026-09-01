# Scripts

Repository-local operational/developer scripts only. Each script must have a stable purpose, safe defaults and a documented caller. Business rules must not live only in a one-off script.

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
