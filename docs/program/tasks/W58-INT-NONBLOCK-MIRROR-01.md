# Task W58-INT-NONBLOCK-MIRROR-01 — refuse FIFO object paths without waiting

task_id: W58-INT-NONBLOCK-MIRROR-01

## Outcome

The W58 offline object seal and source-mirror retry refuse a FIFO occupying an
object path promptly, before a channel writer appears. Bounded subprocess
regressions prove typed refusal for both paths and keep ordinary regular-file
seal, mirror and retry behavior green.

## Depends on

- `W58-INT-OBJECT-COPY-PREP-01` — completed exact offline object manifest.
- `W58-INT-SOURCE-OBJECT-MIRROR-PREP-01` — completed private source mirror and retry.

## Frozen inputs

- base commit: `a09721a5895a0aff93d08f203fe1bedbbffffb8a`
- published development commit at dispatch:
  `a09721a5895a0aff93d08f203fe1bedbbffffb8a` (dev64);
- W58 scope/plan SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`,
  `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- object-copy/source-mirror SHA-256: `2e66ca7b30672d7118c037a35ab2ac71251082d6a8ed0602327e9e1f44195884`,
  `da1098696b2833afc91cf200172a4bb6d522bbd75e3d35e722d9c52a239db7d8`;
- their test SHA-256: `6e53dd39fbea18713e688fe331e57e4f3b6e3395a217e23fde8809af3664093e`,
  `bda016593c87c6cafa8738b6269cb4e3cb2268ffbf63c3d0927a89c2050736e1`;
- API/domain/error/stage SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`,
  `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`,
  `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`,
  `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- migration head: `0023_norm_citations`; R-135 defers the complete beta gate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: two W58 readers open an object path in blocking mode before checking
  that it is a regular file. A private FIFO can therefore stop seal or retry
  indefinitely; other W58 file readers already use `O_NONBLOCK`.

### P-01 — bounded child probes on dev64

- captured_at: 2026-10-16
- command: run each path in a child process with an owned private FIFO at
  `blobs/00/one`, join for one second, then terminate if still alive;
- captured_output:
  ```text
  object_copy.build_manifest: blocked_on_fifo= True
  source_object_mirror.mirror_source_objects retry: source_retry_blocked_on_fifo= True
  ```
- interpretation: neither path reached its existing nonregular-file refusal.
  The same path opened with `O_NONBLOCK` can be checked by `fstat` immediately.

### P-02 — source flags

- captured_at: 2026-10-16
- command: `rg -n '_FILE_FLAGS|_READ_FLAGS|O_NONBLOCK' scripts/recovery/{object_copy,source_object_mirror,target_object_restore,offline_restore_preflight}.py`
- captured_output:
  ```text
  object_copy.py: _FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW
  source_object_mirror.py: _READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW
  target_object_restore.py: _FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
  offline_restore_preflight.py: _FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
  ```

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `scripts/recovery/object_copy.py`
- `scripts/recovery/source_object_mirror.py`
- `tests/integration/recovery/test_object_copy.py`
- `tests/integration/recovery/test_source_object_mirror.py`
- `docs/program/tasks/W58-INT-NONBLOCK-MIRROR-01.md`
- `docs/program/W58-INT-NONBLOCK-MIRROR-01.md`

## Forbidden hotspots

All other `scripts/recovery/**`, `tests/**`, `src/**`, `contracts/**`,
`db/migrations/**`, `infra/**`, root dependency/lock files, composition root,
global styles, `CURRENT_STATE.md`, corpus data, service resources, refs and tags.

## Non-goals

No change to the W58 object seal, source metadata policy, S3 transport,
PostgreSQL restore, source quiescence, live drill or W58/B6 acceptance.

## Deliverables

Two nonblocking open flags, two bounded FIFO refusal regressions, passing
regular-file tests, this formal task and its result report.

## Required tests

- Run the two new regressions on the frozen base first: they must fail by
  subprocess timeout without hanging the test runner; then pass after the fix.
- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.venv/bin/python -m pytest tests/integration/recovery -q -p no:cacheprovider` — pass.
- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.venv/bin/python -m pytest tests/contract/program/test_wave_governance.py -q -p no:cacheprovider` — pass.
- Python compile, task governance, `git diff --check` and six-path containment — pass.

## Integration contract

Both open operations retain no-follow semantics and reject a nonregular object
without waiting for an external writer. Regular-file bytes, inventory, ETag,
manifest and retry checks stay the same. A partial mirror never produces a
complete manifest. No served call site is added.

## Failure/idempotency/security cases

- A FIFO listed in the object inventory refuses without a seal.
- A FIFO at an existing key on mirror retry refuses without replacing it or
  reporting a complete mirror.
- Existing regular files still rehash; unchanged source bytes retry without
  overwrite, while a differing source refuses.

## Rollback / feature flag

Revert the six task-owned paths to remove this unactivated recovery guard. No
runtime flag changes.

## Handoff

- Changed files, checks, contracts and risks: record in the result report.
- Integration owner may cherry-pick the exact source commit into a separate
  `origin/dev` slot after focused readback; this task has no push authority.
