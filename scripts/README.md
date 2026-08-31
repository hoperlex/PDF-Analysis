# Scripts

Repository-local operational/developer scripts only. Each script must have a stable purpose, safe defaults and a documented caller. Business rules must not live only in a one-off script.

## Bootstrap validator

Run `python3 scripts/validate_bootstrap.py` from the repository checkout to check
the bootstrap JSON schemas and examples, domain invariants, internal Markdown links
and required repository shape.

The Python environment running the command must provide a compatible `jsonschema`
package with `Draft202012Validator`. This is a mandatory prerequisite: if the
package cannot be imported or is unusable, the validator reports `jsonschema`,
prints the action needed to provision it in that Python environment, and exits
non-zero without printing `PASS`.

Exit code `0` together with a standalone `PASS` line means schema tooling was
available and every validator check completed successfully. Any missing prerequisite
or failed check produces a non-zero exit code and no standalone `PASS` line.
