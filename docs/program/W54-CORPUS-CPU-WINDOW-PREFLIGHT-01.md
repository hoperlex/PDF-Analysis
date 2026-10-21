# W54-CORPUS-CPU-WINDOW-PREFLIGHT-01 — CPU-window metadata guard

**Date:** 2026-10-16. **Base:** published `origin/dev`
`cf9b64a0c99042cdfe207de776f0296d6857b930`. **Task:**
`tasks/W54-CORPUS-CPU-WINDOW-PREFLIGHT-01.md`.

## Result

The existing read-only `scripts/norms/corpus_preflight.py` now samples
`os.getloadavg()[0]` with disk and available RAM. Its JSON capacity includes
`load_average_1` and `load_limit_exclusive: 8.0`. Load at or above 8 refuses
with `load_floor`; unavailable, nonfinite or negative load refuses with
`capacity_unavailable`, without emitting invalid JSON. This follows the
recorded W54 promotion operation's load-under-8 window on this eight-CPU host.
W54 plan §3.9 separately sets the disk/RAM stop rule and single heavy lane; it
does not define a universal numeric CPU threshold. The CLI remains metadata
only and cannot authorize a heavy step or paid call.

The real read-only `repair-sample` command, using the exact absolute source
and promotion roots and ignored plan documented in `W54-CORPUS-REPAIR-PLAN-01`,
exited **2** with `REFUSED`. It saw the frozen manifest digest, 674 document
directories, 31,619 regular files, `source_sums=listed_unverified`,
`restore_verified_dump=restore_marker_present_unrehashed` and
`repair_plan=frozen_plan_present_unverified`. The instant sample measured
**5,774,962,688** disk bytes against **6,442,450,944** required,
**6,385,348,608** available RAM against **6,442,450,944** required, and
one-minute load **2.08447265625** against exclusive limit **8.0**.
Refusals were `disk_floor` and `memory_floor`. The low-load sample does not
reserve a future CPU window. The proxy credential is absent; no paid sample,
repaired snapshot, complete embedding build, verified bundle or DB/S3 corpus
publication exists.

## Checks

- `PYTHONPATH=src /root/projects/PDF-Analysis/.local/worktrees/code-first-entry/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/test_corpus_preflight.py` — **20 passed** after source restoration. Tests cover 7.999/8.0/8.001 boundaries, NaN/infinities/negative load, and the actual `os.getloadavg()` sampling and OS-error refusal.
- Mutation probe in the private worktree replaced the `load_floor` condition with false, ran the focused CPU tests, then restored the original source in `finally`: **3 failed, 1 passed**, exit 1 as expected. The complete focused suite then passed.
- `python3 -m compileall -q scripts/norms/corpus_preflight.py tests/integration/norms/test_corpus_preflight.py` — exit 0.
- Direct new-task `governance_findings` — `[]`; `git diff --check` — exit 0.

## Contracts, limits and integration

Only the offline CLI's additive JSON capacity fields and refusal condition
change. Existing command choices and exit codes remain 0 for `METADATA_READY`
and 2 for `REFUSED`. No product API/domain/event contract or migration changes.
The four owned paths are the script, its focused test, this task and this
report. No contract, migration, root dependency/lock, composition root,
global style, `CURRENT_STATE.md`, source corpus/sums, dump, repair journal,
build, bundle, credential, production DB/S3, stand, remote ref or tag changed.

The integrator may cherry-pick this exact task commit onto the next
development candidate. A later operator must remeasure load/disk/RAM
immediately before every heavy step and still run complete source checksum,
dump, repair-journal, embedding and bundle verification at their owning
steps. The W54 paid sample waits for a credential installed outside Git and
fresh capacity. Revert this commit to remove the guard; no data rollback or
runtime feature flag applies.
