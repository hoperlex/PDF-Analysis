# W57B-INT-REFERENCE-LIST-BOUNDS-01 — explicit listing preflight result

**Status:** complete as an unserved, read-only W57b slice from dev65
`8c39b9e0dfd63da7d32d1a848e609ae2dd437a01`; local source commit only.

## Changed files

- `src/auditmanager/runs/reference_pipeline.py` checks the catalogue byte
  ceiling and the tuple's nonempty, NFC, unique, UTF-8-encodable slug shape
  before either saved reader. It limits tuple length and aggregate encoded
  slug bytes by the existing catalogue byte ceiling. After verified snapshot
  custody, it refuses a list longer than the snapshot document count before
  PDF extraction.
- `tests/integration/runs/test_reference_pipeline.py` proves that malformed,
  duplicate, invalid Unicode and oversized listings do not reach either
  reader; an impossible snapshot count does not reach extraction; the regular
  empty-list current-Run path still succeeds.
- `docs/program/tasks/W57B-INT-REFERENCE-LIST-BOUNDS-01.md` freezes the exact
  task, input hashes and four allowed paths.
- `docs/program/W57B-INT-REFERENCE-LIST-BOUNDS-01.md` records this result.

## Checks

- Focused Run and canonical reference suites: **39 passed**.
- ALR-05 boundaries and wave governance: **18 passed**, with five unrelated
  pytest cleanup warnings for shared `/tmp/pytest-of-root/garbage-*` paths.
- Owned Python compilation and `git diff --check`: passed.
- Frozen API, stage registry, W57/code-first plans, migration head and both
  catalogue implementation hashes matched the task. The exact four allowed
  paths changed; forbidden hotspots were untouched.
- No Docker, provider, real DB/S3/corpus acceptance or full gate ran under
  R-135.

## Integration contract and limits

The preflight only rejects listings that cannot fit the already bounded
canonical catalogue. A valid listed slug must occur as UTF-8 text in that
catalogue, so its count and aggregate encoded bytes cannot exceed the
catalogue byte cap. The verified snapshot's document count gives a second
necessary bound after custody is established. The existing pure catalogue
validator still determines whether every listed slug is actually present,
unparsed and pinned. No reviewed-slug source or policy is supplied here.

The read remains unserved, emits no publication or external effect, and
does not establish W57b's stage seal or a qualified W54 corpus. Revert this
scoped commit for rollback; no persisted state or feature flag applies.

## Integrator note

Review the four-path source commit and rerun the focused tests on the
integration candidate. Keep this read unserved until the future caller has
an independently reviewed slug tuple and the assigned W57b seal. No
contract, migration, API route, root dependency, remote ref, checkpoint or
tag changed.
