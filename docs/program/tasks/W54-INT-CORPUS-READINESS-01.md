# Task W54-INT-CORPUS-READINESS-01 — prepare the normative corpus operation

task_id: W54-INT-CORPUS-READINESS-01

## Outcome

The integrator has a measured, source-pinned stop/go record and a command
sequence for `W54-CORPUS-OPERATE-01` and the later `W55A-STAND-IMPORT-01`.
The record names every absent artifact and the resources required before any
heavy step. It performs no hashing of the full drop, paid call, database
write or stand import.

## Depends on

- `W54-REPAIR-01` — completed machinery and operator sequence;
- `W54-EMBED-01` — completed resumable build machinery;
- `W54-BUNDLE-01` — completed verified bundle machinery.

## Frozen inputs

- base `origin/dev` `97224aec7dad6916fafbb8108de899583db56c0e`;
- W54 plan SHA-256 `b1b4acbf7ce02c4ef8b14533dedc8d7c9e64404b2f4cc0cc5c6342c9d7fdaf71`;
- W55 plan SHA-256 `9f4e0f204284347bc3ead59423a5cff830bbc9298ceaa2d47e1412f640b92b64`;
- source manifest SHA-256 `160fdc7ea261b44298757b3a066982fd167b389fde614fb119c4c1d0d72fbb3b`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- migration head `0022_findings_v2`; promotion port `57190`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the source drop exists, but the local promotion artifacts and
  resource headroom required by W54 §3.9 are absent.

### P-01 — source and resource preflight

- captured_at: 2026-10-15
- command: `find .local/norms/corpus -type f -printf '.' | wc -c; find .local/norms/corpus -mindepth 1 -maxdepth 1 -type d -printf '.' | wc -c; df -B1 --output=avail /; free -b | awk '/^Mem:/'`
- captured_output:
  ```text
  31619
  674
       Avail
  6066712576
  Mem: 12433453056 10791583744 162594816 38424576 1845788672 1641869312
  ```
- interpretation: disk and available RAM are below the W54 heavy-step floor;
  the measurement can only be used for this preflight, not a later launch.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W54-INT-CORPUS-READINESS-01.md`
- `docs/program/W54-INT-CORPUS-READINESS-01.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

`contracts/**`, migration head, root dependencies/locks, composition root,
global styles, source corpus bytes, promotion/repair/build/bundle artifacts,
production stand, credentials, `VERSION`, tags and `origin/main`.

## Non-goals

No corpus checksum run, promotion database, paid repair, BGE image/build,
bundle export, stand copy/import, current-snapshot designation, full gate or
beta acceptance. This readiness task does not authorize P4.

## Deliverables

This task file, a source/resource/artifact inventory and a bounded operator
sequence with explicit stop and handoff conditions.

## Required tests

- compare report references with W54 §3.2–§3.5/§3.9/§4 and W55 §A7/§C6;
- direct task governance, `git diff --check`, exact changed-path proof;
- no resource-intensive tests or `make gate` under R-135.

## Integration contract

`W54-CORPUS-OPERATE-01` must remeasure disk and available RAM immediately
before each heavy step in a designated night window. It consumes this report
only as a command and dependency map, never as proof of a completed snapshot,
repair, embedding or bundle. After a verified bundle with a complete build
exists, the owner names its key/digest and a P4 downtime window; P3/stand
compatibility and copy/restore rehearsal remain separate preconditions.

## Failure/idempotency/security cases

An absent sum file, source mismatch, under-floor resource reading, unpriced
or wrong-model repair response, incomplete build or failed restore/report is
a stop. No secrets or source norm text enter Git. Rerunning this read-only
preflight changes no corpus state.

## Rollback / feature flag

Documentation-only revert. No feature flag or data rollback.

## Handoff

- changed files/checks/limits: report;
- contracts: none;
- next: provision capacity and execute W54's step 0 in an authorized night window.
