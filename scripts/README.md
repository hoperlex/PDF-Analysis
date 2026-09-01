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

The Python environment running the command must provide a compatible `jsonschema`
package with `Draft202012Validator`. This is a mandatory prerequisite: if the
package cannot be imported or is unusable, the validator reports `jsonschema`,
prints the action needed to provision it in that Python environment, and exits
non-zero without printing `PASS`.

`requirements/validation.in` contains the direct validation dependency;
`requirements/validation.lock` pins its full transitive set and artifact hashes.
The lock was generated with `pip-tools 7.5.0` under Python 3.12. Regeneration is a
separately reviewed root dependency-hotspot change and must update both files. This
validation-only lock does not select the CP-01 application package manager.

Exit code `0` together with a standalone `PASS` line means schema tooling was
available and every validator check completed successfully. Any missing prerequisite
or failed check produces a non-zero exit code and no standalone `PASS` line.
