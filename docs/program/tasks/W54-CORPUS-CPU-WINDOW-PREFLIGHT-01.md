# Task W54-CORPUS-CPU-WINDOW-PREFLIGHT-01 — expose and refuse a saturated CPU window

task_id: W54-CORPUS-CPU-WINDOW-PREFLIGHT-01

## Outcome

The read-only W54 corpus preflight includes the current one-minute CPU load in its
capacity result and refuses `METADATA_READY` when the recorded eight-CPU host's
load is at least 8 or the measurement is invalid. It makes no heavy operation
or publication decision.

## Depends on

- `W54-CORPUS-SPLIT-ROOT-PREFLIGHT-01` — completed separated source and promotion roots;
- `W54-CORPUS-REPAIR-SAMPLE-PREFLIGHT-01` — completed pinned plan check.

## Frozen inputs

- base/published `origin/dev`: `cf9b64a0c99042cdfe207de776f0296d6857b930`;
- W54 plan SHA-256: `b1b4acbf7ce02c4ef8b14533dedc8d7c9e64404b2f4cc0cc5c6342c9d7fdaf71`;
- W54 §3.9: one heavy step at a time, step increment plus 3 GiB free and 6 GiB available RAM;
- recorded successful promotion window: `W54-CORPUS-PROMOTION-01.md`, one-minute load below 8 on eight CPUs; this is an operational criterion for this host, not a frozen cross-host W54 contract;
- source manifest, sums, base dump and zero-call plan pins already in `scripts/norms/corpus_preflight.py`; none changes;
- development API 48 paths / 55 operations / 131 schemas; error catalogue 25; migration head `0023_norm_citations` (all unchanged).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the existing preflight can report `METADATA_READY` during a saturated
  CPU window because it measures only disk and available RAM.

### P-01 — current preflight has no CPU measurement

- captured_at: 2026-10-16
- command: `rg -n 'MEMORY_FLOOR|DISK_RESERVE|def _capacity|def inspect|capacity.disk_available_bytes|capacity.memory_available_bytes|load_average' scripts/norms/corpus_preflight.py`
- captured_output:
  ```text
  49:MEMORY_FLOOR = 6 * GIB
  50:DISK_RESERVE = 3 * GIB
  66:    memory_required_bytes: int = MEMORY_FLOOR
  297:def _capacity(promotion_root: Path, next_step: str) -> Capacity:
  305:    return Capacity(disk_available, DISK_RESERVE + INCREMENTS[next_step], memory_available)
  308:def inspect(
  383:        if capacity.disk_available_bytes < capacity.disk_required_bytes:
  385:        if capacity.memory_available_bytes < capacity.memory_required_bytes:
  ```
- interpretation: on base `cf9b64a0`, disk and RAM can pass while CPU load is saturated; the CLI cannot
  display or refuse that condition. The evidence does not alter the separate
  owner-authorized window or W54's published disk/RAM stop rule.

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
- `docs/program/tasks/W54-CORPUS-CPU-WINDOW-PREFLIGHT-01.md`
- `docs/program/W54-CORPUS-CPU-WINDOW-PREFLIGHT-01.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root, global
styles, `CURRENT_STATE.md`, other task/reports, source corpus/sums bytes,
promotion dump/database/volume, repair journal, embedding/bundle artifacts,
credentials, S3/stand, refs and tags.

## Non-goals

No source rehash, dump rehash/restore, proxy credential discovery or paid call,
embedding build, bundle export/verification, DB/S3 import, Docker, full gate,
deployment or beta verdict. A passing sample never authorizes a heavy step.

## Deliverables

Additive load evidence and strict refusal in the existing JSON preflight, focused
boundary/invalid-measurement tests and a read-only real-host result report.

## Required tests

- `PYTHONPATH=src <lock-matched-venv>/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/test_corpus_preflight.py`;
- real standalone `repair-sample` metadata preflight with both absolute roots and
  pinned ignored plan; report only status and nonsecret capacity/refusals;
- `python3 -m compileall -q scripts/norms/corpus_preflight.py tests/integration/norms/test_corpus_preflight.py`;
- `git diff --check`, direct task governance and exact allowed-path proof.

## Integration contract

The existing CLI choices and exit statuses remain: 0 for `METADATA_READY`, 2
for `REFUSED`. The JSON capacity gains `load_average_1` and an exclusive
`load_limit_exclusive=8.0`. At or above 8, add `load_floor`; a nonfinite or
negative measurement adds `capacity_unavailable` and no capacity object. This
is only a host-window metadata guard; the operator still performs separate
step-specific source/dump/build/bundle verification and immediate resource
measurement. The integrator may cherry-pick the exact task commit; no push.

## Failure/idempotency/security cases

Missing OS measurement, NaN, infinity and negative load refuse without a JSON
NaN. Repeating the command reads only metadata and writes no corpus artifact.
No credentials or source document bytes appear in output.

## Rollback / feature flag

Revert this script/test/docs commit. No runtime feature flag or data rollback
applies to this offline operator preflight.

## Handoff

- changed files, checks, contracts, limits and exact commit: result report;
- no publication authority.
