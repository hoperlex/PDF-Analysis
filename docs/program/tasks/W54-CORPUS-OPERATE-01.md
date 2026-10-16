# Task W54-CORPUS-OPERATE-01 — verify the pinned normative source drop

task_id: W54-CORPUS-OPERATE-01

## Outcome

The 674-document local source drop has a complete, sorted SHA256SUMS file, a
successful full-file verification, and a recorded digest of the sums file.
This is the source-integrity gate for a later promotion load.

## Depends on

- `W54-INT-CORPUS-READINESS-01` — completed source and resource preflight.

## Frozen inputs

- base commit: `8069220909e40c39e2329d5f5cb9585a5a5714ec`
- source root: `/root/projects/PDF-Analysis/.local/norms/corpus`;
- source manifest SHA-256: `160fdc7ea261b44298757b3a066982fd167b389fde614fb119c4c1d0d72fbb3b`;
- domain/API/analysis contracts: current frozen W54 set in `W54-INT-CORPUS-READINESS-01`;
- migration head: `0022_findings_v2` (unchanged).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the source was inventoried, but its bytes were not verified; the
  W54 resource floor must be measured again immediately before hashing.
- source_record: `W54-INT-CORPUS-READINESS-01.md` §Source and current stop.
- captured_at: 2026-10-16
- command: `sed -n '10,25p' docs/program/W54-INT-CORPUS-READINESS-01.md`
- captured_output:
  ```text
  contains **674 document directories**, **31,619 files** and occupies about
  **5.1 GiB**. `MANIFEST.json` has SHA-256
  `160fdc7ea261b44298757b3a066982fd167b389fde614fb119c4c1d0d72fbb3b`.
  Only the `corpus` child exists under `.local/norms/`: no `corpus-sums`,
  `repairs`, `builds`, `bundles` or `promotion-dumps` was present. A manifest
  hash and file count do not verify the drop's file contents.

  At the latest preflight, `/` had **6,066,712,576 bytes** available and
  `free -b` showed **1,641,869,312 bytes** available RAM. W54 §3.9 requires
  the running step's disk increment **plus 3 GiB** and at least **6 GiB
  available RAM**, excluding swap, immediately before each heavy step in a
  night window. Neither a base load, dump/restore verification, repair run,
  image/build, bundle export nor local rehearsal may start on this reading.
  W55 §C6 estimates about **19 GiB free** for the local copy/restore rehearsal;
  capacity must be provisioned and measured again, with the artifacts already
  resident accounted for. No source byte, database, model or stand was changed.
  ```
- interpretation: this is a retrospective capture of the original readiness
  record, not a current resource measurement or a new source-byte verdict.

## Historical evidence

- correction_mode: addendum
- source_record: docs/program/tasks/W54-CORPUS-OPERATE-01.md at `e61fc457`
- addendum_path: docs/program/PROGRAM-GOVERNANCE-REPAIR-01.md

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W54-CORPUS-OPERATE-01.md`
- `docs/program/W54-CORPUS-OPERATE-01.md`
- `docs/program/CURRENT_STATE.md`
- `.local/norms/corpus-sums/**`

## Forbidden hotspots

`contracts/**`, migration head, root dependencies and locks, composition root,
global styles, source corpus bytes, promotion DB, repair journal, build/bundle
artifacts, production stand, credentials, tags and `origin/main`.

## Non-goals

No database load, paid repair, embedding build, S3 publication, production
import or current-snapshot designation. Source verification alone does not
qualify a normative snapshot.

## Deliverables

The dated `SHA256SUMS` and verification result under `.local/norms/corpus-sums/`,
plus a report with file count, sum-file digest, current resource measurements
and the next capacity gate.

## Required tests

- Immediately before hashing: `date -u`, `df -B1 /`, `free -b` and load average;
  at least 6 GiB available RAM excluding swap and 3 GiB free disk.
- From the absolute source root: sorted `find . -type f -print0` piped to
  `sha256sum`, then `sha256sum -c` on the resulting complete file.
- Confirm 31,619 verified file lines, manifest digest, no failed line, and
  `git diff --check` for the report/task.

## Integration contract

The next promotion task consumes only the exact verified sums path and its
recorded SHA-256. Any changed source byte or incomplete verification is a
hard stop. The user authorized starting when an actual RAM/CPU window appears
on 2026-10-15; resource floors remain mandatory.

## Failure/idempotency/security cases

Write to a new dated directory and atomically publish a complete sums file.
Never overwrite a previous verified run or log source text/credentials. On an
interrupted run, retain the partial temporary file outside the final path and
report it; do not treat it as verification.

## Rollback / feature flag

Delete this task's unconsumed sums/report after identifying the exact run;
the source and application behavior are unchanged. No feature flag applies.

## Handoff

- changed files, commands/results, contracts, limits and untouched hotspots:
  record in the task report after execution.
