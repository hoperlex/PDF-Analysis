# W54-CORPUS-SPLIT-ROOT-PREFLIGHT-01 — source/promotion root separation

**Date:** 2026-10-16. **Base:** published `origin/dev`
`b9f1c149f004851de89a2fcc615618068e794bde`. **Task:**
`tasks/W54-CORPUS-SPLIT-ROOT-PREFLIGHT-01.md`.

## Result

The W54 metadata preflight now requires absolute `--source-root` and
`--promotion-root` values. It reads the source manifest and checksum listing only from
the first root, and the local promotion dump, build and bundle only from the second.
The disk floor is measured on the promotion root's filesystem. Relative, missing and
symlinked roots refuse before traversal; symlinked artifact directories are refused or
ignored without reading through them. No payload was copied, opened for hashing or
written. This is a correction to operator metadata reporting, not a qualification rule.

The real read-only command against
`/root/projects/PDF-Analysis/.local/norms` and
`/root/projects/PDF-Analysis/.local/worktrees/code-first-entry/.local/norms`
exited **2** with the expected source manifest SHA and 674 directories / 31,619 files.
It now reports `source_sums=listed_unverified` and
`restore_verified_dump=restore_marker_present_unrehashed`; the former one-root command
had reported the verified base dump absent because it looked in the source workspace.
`build_checkpoint=absent` and `bundle_candidate=absent` remain explicit. At the final
sample the promotion filesystem had **10,506,924,032** bytes available versus the
bundle-export metadata floor of **3,865,470,567**; RAM had **6,367,494,144** versus
**6,442,450,944** required. The CLI refused `build_checkpoint_unavailable` and
`memory_floor`. Both capacity readings are momentary. The restore marker corresponds to
the base dump documented by `W54-CORPUS-PROMOTION-01`; no repaired snapshot, qualified
embedding build, verified promotion bundle or DB/S3 publication is claimed.

## Checks

- `PYTHONPATH=src ../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/test_corpus_preflight.py` — **9 passed**. The split-root test fails if the dump is read from the source root or capacity is measured there. It also asserts that PDF/dump payload bytes are never read.
- `../../../.venv/bin/python scripts/norms/corpus_preflight.py --source-root /root/projects/PDF-Analysis/.local/norms --promotion-root /root/projects/PDF-Analysis/.local/worktrees/code-first-entry/.local/norms --next-step bundle-export` — **exit 2**, read-only output above.
- `PYTHONPATH=src ../../../.venv/bin/python -m compileall -q scripts/norms/corpus_preflight.py tests/integration/norms/test_corpus_preflight.py` and `git diff --check` — **exit 0**.
- Direct task governance on this new task returned `[]`; `git diff --name-only`
  plus `git ls-files --others --exclude-standard` listed only the four allowed paths.

No Docker, PostgreSQL, MinIO, provider call, full source hash, full gate or publication was
started while the W55b gate runs. The proxy credential is absent; `claude-opus-5` is only
the selected, priced model for a later three-page sample.

## Contracts and integration

Only these four tracked paths change: `scripts/norms/corpus_preflight.py`,
`tests/integration/norms/test_corpus_preflight.py`, this task and this report. No
product/API/domain/event contract, migration, root lock, composition root or runtime
router changes. No `CURRENT_STATE.md`, corpus source/sums, dump, repair plan, build,
bundle, credentials, stand, remote ref or tag was touched.

The integrator may cherry-pick this task's exact commit. Future preflight calls must
provide both roots; existing one-root command lines need updating at their use site.
`METADATA_READY` still means only cheap structural checks and current promotion-root
disk/RAM thresholds. Source `sha256sum -c`, base dump restore evidence, the later paid
repair journal and ledger, repaired snapshot, `embedding status/load`, full bundle
verification, stand capacity, P3 compatibility and owner-approved import remain separate
gates. Reverting the task commit restores the old CLI; no data rollback is needed.
