# W58-INT-TARGET-RETRY-METADATA-01 — target digest metadata on retry

**Base:** published development candidate `7b56cb451946d250b1030f61150a4979dbcfc157`.
**Status:** unactivated offline W58 helper; no real DB/S3 drill or recovery acceptance.

## Result

The target restore now checks the sealed `content-sha256` on every GetObject
response before streaming the body. An existing target object with the right
bytes but missing or wrong digest metadata refuses before a later missing
object can be uploaded. The final readback repeats this check, so metadata
drift after upload cannot return success. The conditional upload keeps
writing the sealed digest and does not overwrite existing objects.

The coordinator's fake object client now retains and returns the metadata
already passed to PutObject. This is test-fixture compatibility with the
existing production helper, not new coordinator behavior.

## Checks

- Regression before the fix: 3 failing negative cases and 1 passing positive
  retry case; the failures demonstrated the metadata gap.
- Target restore focused file: **18 passed**.
- Complete container-free recovery suite: **165 passed**.
- Programme governance: **16 passed**.
- Python compile for the three changed Python files, `git diff --check`,
  task parsing and exact five-path containment: passed.
- No PostgreSQL, S3, Docker, corpus job, paid provider, full beta gate or
  remote ref operation ran. R-135 defers the complete gate.

## Limits and integration

The frozen W58 object seal contains a content digest but does not contain
source S3 role, media type or custom metadata. This task checks only the
`content-sha256` needed by the BlobStore. A target object with exact bytes
but absent digest metadata now requires an empty disposable target and a
fresh restore; the helper never rewrites it in place. Operator proof of
source quiescence and target isolation, and a real service drill, remain
separate W58/B6 work.

Changed paths are exactly:

- `scripts/recovery/target_object_restore.py`
- `tests/integration/recovery/test_target_object_restore.py`
- `tests/integration/recovery/test_isolated_restore_drill.py`
- `docs/program/tasks/W58-INT-TARGET-RETRY-METADATA-01.md`
- `docs/program/W58-INT-TARGET-RETRY-METADATA-01.md`

No `contracts/**`, migration, storage adapter, root lockfile, composition,
global style, corpus or other recovery path changed. The integrator can
cherry-pick the exact source commit into the assigned development slot and
rerun the focused suite. Revert these five paths to roll back the unactivated
guard.
