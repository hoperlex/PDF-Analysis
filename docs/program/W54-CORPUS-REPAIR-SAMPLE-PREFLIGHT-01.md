# W54-CORPUS-REPAIR-SAMPLE-PREFLIGHT-01 — pinned offline plan check

**Date:** 2026-10-16. **Base:** published `origin/dev`
`de3d81085f30301ddc2965f7f4bf927ea738c8b3`. **Task:**
`tasks/W54-CORPUS-REPAIR-SAMPLE-PREFLIGHT-01.md`.

## Result

The W54 metadata preflight now has an explicit `repair-sample` choice. It
requires the ignored zero-call JSON plan under the promotion root and verifies
its exact pinned SHA-256, selected `claude-opus-5`, 121 pages, base content key,
three distinct sample block IDs, `$10` ceiling, positive bounded call estimate
and zero spent. It also requires the pinned source-sums digest, the base dump's
sidecar SHA-256 and empty restore marker. A conservative 3 GiB operation
increment plus the W54 3 GiB reserve is measured on the promotion filesystem;
available RAM must be at least 6 GiB without swap. Missing, changed, symlinked
or escaping plan inputs refuse. The check does not rehash the source files or
dump, and its output explicitly says the plan remains unverified for operation.

The real read-only command at 14:01 +05 against source
`/root/projects/PDF-Analysis/.local/norms`, promotion
`/root/projects/PDF-Analysis/.local/worktrees/code-first-entry/.local/norms` and
its `repairs/plan-20261016.json` exited **2**. It saw the exact source manifest,
674 directories and 31,619 regular files, `source_sums=listed_unverified`,
`restore_verified_dump=restore_marker_present_unrehashed` and
`repair_plan=frozen_plan_present_unverified`. Disk available was
**9,505,878,016** bytes against **6,442,450,944** required; available RAM was
**4,696,215,552** against **6,442,450,944** required. Its only refusal was
`memory_floor`. Both capacity readings are instantaneous. The actual small
plan and source-sums SHA-256 files matched their frozen digests; the dump
`.sha256` sidecar declared the frozen base digest. The completed
`W54-CORPUS-PROMOTION-01` is the separate evidence that dump bytes previously
passed a disposable restore.

## Checks

- `PYTHONPATH=src /root/projects/PDF-Analysis/.local/worktrees/code-first-entry/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/test_corpus_preflight.py` — **12 passed**. New cases prove a matching plan passes metadata checks without reading PDF or dump bytes; missing, changed, wrong-model and symlinked plans and wrong source/dump identity refuse.
- `python3 -m compileall -q scripts/norms/corpus_preflight.py tests/integration/norms/test_corpus_preflight.py` — exit 0.
- `python3 scripts/norms/corpus_preflight.py --help` lists all five choices, including `repair-sample`; direct task `governance_findings` returned `[]`.
- `git diff --check` — exit 0. Exact changed paths are the script, its focused test, this report and its task.

## Contracts, limits and integration

Only the operator CLI adds a `repair-sample` choice and a `repair_plan` JSON
status. Its existing choices retain their behavior. No API/domain/event
contract, migration, root dependency/lock, composition root, global style,
source corpus/sums, dump, repair journal, embedding/bundle artifact,
credential, database/S3, stand or remote ref was changed. `CURRENT_STATE.md`
remains integrator-owned.

The integrator may cherry-pick this exact task commit. Once a credential file
is separately installed and a fresh resource window passes, the operator must
still run complete source-sums verification, obey the durable journal and
three-largest-crop sample rules, inspect the sample projection and enforce the
`$10` cumulative ceiling. This preflight is only a fail-closed metadata check,
not authority to make a paid call or to publish a corpus. Revert the commit to
remove the CLI choice; there is no data rollback.
