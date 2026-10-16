# W54-CORPUS-SUMS-BINDING-01 — frozen source-listing metadata guard

**Date:** 2026-10-16. **Base:** published development commit `f0b12ea705a9ccb476b5b69a5797de7d3731f543`. **Task:** `tasks/W54-CORPUS-SUMS-BINDING-01.md`.

## Result

Every W54 preflight step after `source-sums` now requires the parsed `SHA256SUMS` listing to have the frozen digest `eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`. Before this change, `base-load`, `restore-verify` and `bundle-export` accepted any listing with the same file paths; only `repair-sample` checked the digest. A listing with changed checksum values and unchanged paths now refuses `source_sums_digest_mismatch`. The preparatory `source-sums` step retains its prior behavior. Missing, malformed or path-mismatched listings retain `source_sums_unavailable`.

This is a cheap check of the listing bytes, not a rehash of 31,619 source files. It makes no claim that a PDF matches its listed checksum. The later full `sha256sum -c`, dump restore, embedding load, bundle verification and DB/S3 publication gates remain separate.

## Evidence

- Focused preflight tests: **24 passed**. The new four-step parameterized case changes listed SHA values while keeping exactly the same paths; each later step refuses, while `source-sums` does not add a digest refusal.
- `python3 -m compileall -q scripts/norms/corpus_preflight.py tests/integration/norms/test_corpus_preflight.py`: exit **0**.
- Direct `governance_findings` on the new task: `[]` using the lock-matched virtual environment. The system `python3` attempt could not import pytest, so its result was discarded and the check was rerun correctly.
- Actual source-listing read-back: SHA-256 `eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`.
- Read-only actual `base-load` preflight with separate absolute source and promotion roots: exit **2**, `REFUSED`. It reports 674 document directories, 31,619 files, `source_sums=listed_unverified`, a restore marker for the base dump, and `memory_floor` only. The momentary measurement was 6,540,898,304 disk bytes against 6,442,450,944 required, 5,430,398,976 available RAM against 6,442,450,944 required, and one-minute load 2.30810546875 against an exclusive limit of 8. No heavy operation followed from this sample.
- W54/W55 plan, API, error catalogue and analysis registry hashes still match the task's frozen inputs. `git diff --check` and exact changed-path proof are recorded at close.

## Contracts and limits

The offline preflight's refusal behavior changes for three existing next steps; its CLI choices, JSON fields and exit-code convention remain unchanged. No product API/domain/event contract or migration changes. The `inspect` function has one optional expected-digest parameter for synthetic tests; the CLI retains the pinned production default. No source corpus, checksum listing, promotion database/dump, repair journal, embedding or bundle payload, credential, S3/stand, remote ref or tag was modified. A real repaired snapshot, complete embedding build, qualified bundle and DB/S3 corpus publication are still absent. The proxy credential for the selected `claude-opus-5` repair remains unavailable.

The changed paths are exactly `scripts/norms/corpus_preflight.py`, `tests/integration/norms/test_corpus_preflight.py`, this report and its task. The integrator can apply the clean source commit to the next development candidate. Rollback is a revert of that commit; there is no runtime flag or data rollback.
