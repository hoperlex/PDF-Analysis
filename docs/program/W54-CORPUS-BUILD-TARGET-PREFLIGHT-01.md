# W54-CORPUS-BUILD-TARGET-PREFLIGHT-01 — selected snapshot/profile in bundle preflight

**Date:** 2026-10-16. **Base:** published `origin/dev` `4c16ccd7ae975d5a32829e9bcdf975f8b12f66e1`. **Task:** `tasks/W54-CORPUS-BUILD-TARGET-PREFLIGHT-01.md`.

## Result

The read-only `bundle-export` preflight now requires `--snapshot <ns_id>` and `--chunking-profile characters-v2:<target>`, mirroring the actual bundle export command. It validates the snapshot ID and designatable profile before scanning checkpoints and counts only a canonical plan whose identity matches both. A complete checkpoint for another snapshot or profile reports `build_checkpoint=absent` and refuses. Missing or invalid target values return `build_target_required` or `build_target_invalid`, with `build_checkpoint=target_unbound`. The JSON result records the selected snapshot ID and profile so an operator can compare the preflight with the following export command.

The actual read-only command named the existing **base** snapshot `ns_01M4ZW72BS7QHAMDJ993VHNJ7K` and `characters-v2:1200` solely as a diagnostic target. It exited **2**, `REFUSED`: source manifest SHA-256 matched, 674 directories and 31,619 files were present, source sums were listed, the base dump restore marker existed, and `build_checkpoint=absent`. Refusals were `build_checkpoint_unavailable` and the momentary `memory_floor`. Capacity was 5,567,340,544 available disk bytes versus 3,865,470,567 required, 5,849,047,040 available RAM versus 6,442,450,944 required, and one-minute load 2.3564453125 below 8. The base snapshot is not a repaired qualified publication target; no export, DB/S3 access or paid provider call occurred.

## Checks

- Focused `tests/integration/norms/test_corpus_preflight.py`: **34 passed** after the target change. Tests cover a complete canonical checkpoint with missing target, another snapshot, another valid profile, invalid snapshot, non-designatable profile and CLI argument forwarding, alongside the prior source/dump/build refusal cases.
- Temporary mutation skipping the snapshot/profile comparison was restored after the targeted wrong-snapshot test failed as expected (**1 failed**); the focused suite was rerun on restored source.
- `python3 -m compileall -q scripts/norms/corpus_preflight.py tests/integration/norms/test_corpus_preflight.py`: exit **0**.
- Direct `governance_findings` on the task: `[]`. `git diff --check` and exact changed-path proof are recorded at close.

## Contracts, limits and integration

The offline preflight CLI gains two required inputs for its `bundle-export` step and two additive JSON target fields. Other next steps keep their old input behavior. No public API/domain/event contract, migration, root dependency/lock, composition root or global style changes. W54/W55 plan, API, error catalogue and stage-registry hashes match the task's frozen inputs. No source corpus/sums, promotion database/dump, repair journal, checkpoint or bundle payload, credential, S3/stand, remote ref or tag was modified.

This preflight still checks only plan identity and regular file presence; it does not hash vector bytes, certify a DB completion row, identify the repaired snapshot from the database, verify a bundle, or qualify DB/S3 publication. A future operator must pass the same exact snapshot/profile to preflight and export, then run `embedding status/load` and the bundle verifier. The 121-page `claude-opus-5` repair remains blocked by the missing proxy credential, and the repaired snapshot and complete embedding build remain absent.

Exactly four paths changed: `scripts/norms/corpus_preflight.py`, `tests/integration/norms/test_corpus_preflight.py`, this task and this report. The integrator may fetch the clean local commit from this isolated clone and cherry-pick it to a development candidate. Revert that commit for rollback; there is no data rollback or runtime flag.
