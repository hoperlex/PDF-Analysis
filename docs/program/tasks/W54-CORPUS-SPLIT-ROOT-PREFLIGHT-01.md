# Task W54-CORPUS-SPLIT-ROOT-PREFLIGHT-01 — bind source and promotion roots explicitly

task_id: W54-CORPUS-SPLIT-ROOT-PREFLIGHT-01

## Outcome

The read-only W54 preflight reads the verified source from its explicit absolute root and
inspects the promotion dump/build/bundle from a separate explicit absolute root. It no
longer reports a restore-verified dump absent merely because it looked under the source
drop's `.local/norms` directory. It refuses missing or escaping roots and never qualifies
a repaired snapshot or DB/S3 publication.

## Depends on

- `CFB-NORM-CORPUS-PREFLIGHT-01` — completed metadata-only CLI and tests;
- `W54-CORPUS-PROMOTION-01` — completed restore-verified base dump.

## Frozen inputs

- base/published `origin/dev`: `b9f1c149f004851de89a2fcc615618068e794bde`;
- W54 plan SHA-256: `b1b4acbf7ce02c4ef8b14533dedc8d7c9e64404b2f4cc0cc5c6342c9d7fdaf71`;
- W55 plan SHA-256: `9f4e0f204284347bc3ead59423a5cff830bbc9298ceaa2d47e1412f640b92b64`;
- source manifest SHA-256: `160fdc7ea261b44298757b3a066982fd167b389fde614fb119c4c1d0d72fbb3b`;
- verified source sums SHA-256: `eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`;
- verified base dump SHA-256: `e1280373ffd7fa3deaa0716429def1844d7e858e79bae7fbad5ade6d516ff74d`;
- API SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalogue SHA-256: `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis stage registry SHA-256: `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- migration head: `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the verified source and promotion artifacts live under two different
  `.local/norms` roots, while the existing CLI accepts only one.

### P-01 — the source and promotion artifacts have different roots

- captured_at: 2026-10-16
- command: `ls -ld /root/projects/PDF-Analysis/.local/norms/corpus /root/projects/PDF-Analysis/.local/norms/corpus-sums/2026-10-15/SHA256SUMS /root/projects/PDF-Analysis/.local/worktrees/code-first-entry/.local/norms/promotion-dumps /root/projects/PDF-Analysis/.local/worktrees/code-first-entry/.local/norms/repairs`
- captured_output:
  ```text
  drwxr-xr-x 676 root root  106496 Sep 10 12:40 /root/projects/PDF-Analysis/.local/norms/corpus
  -rw-------   1 root root 6537866 Oct 15 17:56 /root/projects/PDF-Analysis/.local/norms/corpus-sums/2026-10-15/SHA256SUMS
  drwxr-xr-x   2 root root    4096 Oct 16 12:24 /root/projects/PDF-Analysis/.local/worktrees/code-first-entry/.local/norms/promotion-dumps
  drwxr-xr-x   2 root root    4096 Oct 16 12:26 /root/projects/PDF-Analysis/.local/worktrees/code-first-entry/.local/norms/repairs
  ```
- interpretation: the old one-root CLI cannot observe both without moving or copying
  ignored artifacts. This task only changes where it reads; it does not certify their bytes.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `scripts/norms/corpus_preflight.py`
- `tests/integration/norms/test_corpus_preflight.py`
- `docs/program/tasks/W54-CORPUS-SPLIT-ROOT-PREFLIGHT-01.md`
- `docs/program/W54-CORPUS-SPLIT-ROOT-PREFLIGHT-01.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root, global styles,
`CURRENT_STATE.md`, other task/report files, source corpus/sums bytes, promotion dump and
database, repair journal, embedding/bundle artifacts, credentials, S3/stand, refs and tags.

## Non-goals

No `sha256sum -c` over source files, dump hash/re-restore, paid repair, build, bundle
export/verify, DB/S3 import, current-snapshot designation, Docker/PG/MinIO, full gate or
beta verdict. No new publication authority or provider credential is inferred.

## Deliverables

Explicit `--source-root` and `--promotion-root` CLI inputs, root and child symlink/path
guards, source reads separated from promotion reads, host disk measured at the promotion
root, focused split-root and refusal tests, and a report.

## Required tests

- `python -m pytest -q -p no:cacheprovider tests/integration/norms/test_corpus_preflight.py` — all pass;
- run the standalone CLI with the actual absolute roots and `--next-step bundle-export` —
  report the base restore marker as present, but refuse the absent build/qualified bundle;
- `python -m compileall -q scripts/norms/corpus_preflight.py tests/integration/norms/test_corpus_preflight.py`;
- `git diff --check`; direct task governance; exact changed-path proof.

## Integration contract

Every operator call provides both absolute roots; the command never guesses from cwd.
The source manifest and sums are read only from the source root, the dump/build/bundle
only from the promotion root. `METADATA_READY` means metadata and instantaneous
promotion-filesystem capacity only; W54/W55 verifiers and publication preconditions remain
mandatory. The integration owner may cherry-pick the exact task commit; this lane does
not push, tag or touch `origin/main`.

## Failure/idempotency/security cases

Absent/relative/symlink roots or symlink child artifact directories are refused before
traversal. No payload bytes, credentials or normative text are printed. Repeating the
preflight changes no artifact.

## Rollback / feature flag

Revert the CLI/test commit; no runtime feature flag or data rollback applies to this
read-only operator script.

## Handoff

- changed files, checks, contracts, limits and integration instructions: result report;
- no publication authority.
