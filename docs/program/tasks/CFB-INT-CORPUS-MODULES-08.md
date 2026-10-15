# Task CFB-INT-CORPUS-MODULES-08 — integrate corpus and module preparations

task_id: CFB-INT-CORPUS-MODULES-08

## Outcome

`origin/dev` contains a read-only normative-corpus metadata/capacity preflight,
an offline DB+Blob recovery object-copy verifier, and bounded W59 section
confirmation and raw version-text comparison modules. None activates a corpus
import, recovery operation or section analysis route.

## Depends on

- `CFB-INT-RECORDED-REQUEST-07` — completed at `5a51721a`;
- `CFB-NORM-CORPUS-PREFLIGHT-01` — completed standalone preflight;
- `W58-INT-OBJECT-COPY-PREP-01` — completed offline recovery preparation;
- `W59-INT-CONFIRMATION-PREP-01` — completed pure confirmation policy;
- `W59-INT-VERSION-RAW-TEXT-PREP-01` — completed raw evidence component.

## Frozen inputs

- base commit and local `origin/dev`: `5a51721a745a7bfc5c85cc4594625fa53cbce523`;
- W54 plan SHA-256 `b1b4acbf7ce02c4ef8b14533dedc8d7c9e64404b2f4cc0cc5c6342c9d7fdaf71`;
- W55 plan SHA-256 `9f4e0f204284347bc3ead59423a5cff830bbc9298ceaa2d47e1412f640b92b64`;
- W58–W63 scope SHA-256 `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis stage registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- source manifest SHA-256 `160fdc7ea261b44298757b3a066982fd167b389fde614fb119c4c1d0d72fbb3b`;
- migration head `0022_findings_v2`; `origin/main` is outside this task.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W54 corpus machinery exists but its 674-document source lacks
  verified sums, promotion dump, embedding build and bundle; W59 seal still
  depends on W58-code close, so only independent preparations can integrate.

### P-01 — exact base and current corpus stop

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && df -B1 / && free -b`
- captured_output:
  ```text
  5a51721a745a7bfc5c85cc4594625fa53cbce523
  5a51721a745a7bfc5c85cc4594625fa53cbce523
  Filesystem        1B-blocks         Used Available Use% Mounted on
  /dev/vda3      126828056576 119811473408 563113984 100% /
                 total        used        free      shared  buff/cache   available
  Mem:     12433453056  9302802432  1550282752     7745536  1915625472  3130650624
  Swap:    17179865088  8255803392  8924061696
  ```
- interpretation: the SHA is exact; this transient reading fails the W54
  disk and available-RAM floors and cannot authorize a later heavy step.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/bundle/cli.py`
- `scripts/norms/corpus_preflight.py`
- `tests/integration/norms/test_corpus_preflight.py`
- `docs/program/tasks/CFB-NORM-CORPUS-PREFLIGHT-01.md`
- `docs/program/CFB-NORM-CORPUS-PREFLIGHT-01.md`
- `scripts/recovery/object_copy.py`
- `tests/integration/recovery/test_object_copy.py`
- `docs/program/tasks/W58-INT-OBJECT-COPY-PREP-01.md`
- `docs/program/W58-INT-OBJECT-COPY-PREP-01.md`
- `src/auditmanager/sections/confirmation.py`
- `tests/integration/sections/test_confirmation.py`
- `docs/program/tasks/W59-INT-CONFIRMATION-PREP-01.md`
- `docs/program/W59-INT-CONFIRMATION-PREP-01.md`
- `src/auditmanager/comparison/raw_text.py`
- `tests/integration/comparison/test_raw_text.py`
- `docs/program/tasks/W59-INT-VERSION-RAW-TEXT-PREP-01.md`
- `docs/program/W59-INT-VERSION-RAW-TEXT-PREP-01.md`
- `docs/program/tasks/CFB-INT-CORPUS-MODULES-08.md`
- `docs/program/CFB-INT-CORPUS-MODULES-08.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

`contracts/**`, migrations, existing API/router/UI/run code, provider lock,
root dependencies/locks, composition root, global styles, source corpus
bytes, credentials, Docker/stand services, `VERSION`, tags and `origin/main`.

## Non-goals

No source SHA256SUMS verification, promotion load, repair, embedding build,
verified bundle, DB/S3 publication, W59 API/DB seal, active section profiles,
decision carryover, live calls, full local gate or beta verdict.

## Deliverables

Four bounded slices and reports, integration task/report, current state and
exact development-ref read-back.

## Required tests

- focused section, comparison, corpus-preflight, object-copy and bundle
  refusal tests;
- Python compilation, direct task governance, frozen hashes, whitespace
  and exact changed-path proof;
- no full `make gate` under R-135.

## Integration contract

Stage only the listed paths. Review each task's exact source limitations,
recheck remote `origin/dev`, commit the checked candidate, prove a
fast-forward from the exact remote SHA, push only that commit to `origin/dev`
and read back both refs. The W54/W55 corpus operation and W58/W59 seals each
need their own later grants and prerequisites. No `origin/main` authority.

## Failure/idempotency/security cases

Unexpected paths, changed frozen hashes, moved remote ref, non-fast-forward
or focused failure stop publication. The source preflight cannot certify
bytes; recovery refuses incomplete/changed object mirrors; section plans do
not grant routing authority; raw comparison evidence stays separate from AI.

## Rollback / feature flag

Revert this development commit before runtime activation. No migration or
feature flag is introduced.
