# Task W58-INT-SOURCE-OBJECT-MIRROR-PREP-01 — prepare exact S3 payload mirror

task_id: W58-INT-SOURCE-OBJECT-MIRROR-PREP-01

## Outcome

An unactivated recovery helper reads every key in a verified W54 S3 inventory
through an injected GetObject reader into a private local objects directory.
It checks the conditional read's ETag, declared and actual size, hashes all
bytes, and hands the complete mirror to the existing W58 manifest verifier.
Interrupted or changed input never produces a complete result.

## Depends on

- `W54-STAND-COPY-01` — completed dump/inventory/copy-record format.
- `W58-INT-OBJECT-COPY-PREP-01` — completed strict inventory parser and
  full-mirror manifest verifier.
- `W58-INT-COPY-RECORD-BINDING-PREP-01` — completed record/inventory/seal
  binding for the later full recovery operator.

## Frozen inputs

- base commit: `08055ca094a9c3e4676a5907a0b3020f0bee4fb8` (`origin/dev`);
- W58–W63 scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- W54 `copy-serve.sh` SHA-256: `998442c31a583831d3dd941e81cb7ef039045a2212a25bfb47c8ce14bbfa4f86`;
- W54 `pull-copy.sh` SHA-256: `7e44d3f6f3126d8b758f85e031cc9a8bacb69023b5ac02f9616b60b397e341da`;
- W58 object-copy SHA-256: `2e66ca7b30672d7118c037a35ab2ac71251082d6a8ed0602327e9e1f44195884`;
- API SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- domain identifiers SHA-256: `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`;
- error catalog SHA-256: `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis stage registry SHA-256: `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- migration head: `0022_findings_v2`; R-135 and W58 RECOVERY-CODE prerequisite.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W54 exports the dump, copy record and inventory but no S3 payload
  bytes; W58 can seal a separately prepared mirror but cannot yet create it.

### P-01 — copy-key transfer boundary

- captured_at: 2026-10-16
- command: `git show HEAD:infra/deploy/copy-serve.sh | rg '^fc_register fetch '`
- captured_output:
  ```text
  fc_register fetch "^fetch ${FC_STAMP_ERE} (db|inventory|record)\$" verb_fetch
  ```
- interpretation: this helper is not callable through the current stand copy
  key and cannot prove source-writer quiescence. The later W58 transport owner
  must add a narrowly authorized payload channel and full-copy lock/lease.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `scripts/recovery/source_object_mirror.py`
- `tests/integration/recovery/test_source_object_mirror.py`
- `docs/program/tasks/W58-INT-SOURCE-OBJECT-MIRROR-PREP-01.md`
- `docs/program/W58-INT-SOURCE-OBJECT-MIRROR-PREP-01.md`

## Forbidden hotspots

`contracts/**`, migrations, existing recovery and storage code,
`infra/deploy/**`, `scripts/stand-copy/**`, root dependencies/locks,
composition root, routers/API/UI, global styles, `CURRENT_STATE.md`,
production configuration, client copy data, Docker resources, refs and tags.

## Non-goals

No stand copy-key verb, credential or network configuration, source quiescence
proof, actual stand transfer, target S3 restore/readback, database restore,
RPO, W58-code close, full gate, publication or beta claim. ETag is a
conditional-read change token, never a content digest or Blob identity.

## Deliverables

One additive private-mirror helper with a typed injected GetObject port,
focused fake-S3 tests, formal task and result report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/recovery/test_source_object_mirror.py tests/integration/recovery/test_object_copy.py` — pass;
- Python compile, direct and full task governance, frozen SHA readback,
  `git diff --check` and exact four-path proof — pass;
- no Docker, live DB/S3/network or complete gate under R-135.

## Integration contract

The caller must provide a verified, frozen W54 inventory and an exclusive,
owner-private objects directory. It supplies a source S3 reader configured
outside Git. On success this helper returns a canonical W58 manifest built
from every local payload; the operator still writes/seals it through the
existing `object_copy` flow and binds it to the W54 record. A later W58 owner
must keep writers quiesced for the entire source transfer, verify source and
target bytes and complete an isolated DB+Blob restore before any recovery
claim. The helper itself does not hold a stand lock.

## Failure/idempotency/security cases

Invalid/duplicate/unsafe inventory, non-private root, symlink/hardlink,
missing or extra object, wrong ETag or ContentLength, short/long/non-byte or
interrupted stream and changed existing mirror refuse. Files are created
privately with no-follow opens, fsynced and atomically linked without
overwriting a prior object. A failed transfer leaves no complete result;
retry reads source again and accepts only identical existing bytes.

## Rollback / feature flag

Remove the additive helper before transport wiring. No application behavior,
data migration or feature flag.

## Handoff

- changed files/checks/limits: accompanying result report;
- contracts: none;
- next: W58 source-transport security freeze after W56b code close.
