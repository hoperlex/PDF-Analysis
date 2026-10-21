# CFB-INT-CORPUS-MODULES-08 — integration result

## Result

The read-only corpus preflight checks the pinned 674-document manifest,
31,619 regular-file paths, current W54 disk/RAM floors and the structural
presence of source sums, a restore marker, embedding checkpoints and a bundle
candidate. It uses the same SHA256SUMS parser as repair/export and explicitly
labels its result metadata-only. On the shared source it refused: sums, dump,
build and bundle are absent, and disk and available RAM were below the floor.
The existing S3 adapter exports in `storage.public` already work; only an
outdated bundle CLI docstring was corrected.

The W58 recovery preparation seals a separately mirrored S3 object tree to
the existing stand `inventory.tsv`: exact key/size set and streamed SHA-256
for each payload, with repeat verification and no-clobber manifest creation.
It does not fetch objects or restore a database.

Two W59 modules prepare later section development. The confirmation policy
requires an authenticated expert, opaque version identity, one of 15 section
codes and a provisional P/R stage; repeated identical choices preserve the
original confirmer. The raw comparison component accepts only explicit,
approved and version-bound sheet pairs, emits deterministic immutable line
evidence and checksums, and refuses ambiguous or oversized input. Neither
module is wired to active routes, database tables or AI decisions.

## Changed files and checks

The exact 20 paths are enumerated in the integration task: five corpus
preflight paths, four recovery paths, four section-confirmation paths, four
version-comparison paths, this task/report and `CURRENT_STATE.md`.

- Combined focused corpus, bundle-refusal, recovery, section, comparison and
  architecture checks: **89 passed**. Five pytest warnings came from stale
  `/tmp/pytest-of-root` cleanup after success.
- Compilation of all new Python modules and tests: pass.
- Direct governance for the integration task and all four slice tasks:
  `[]` each. The corpus task's premise evidence was completed during
  integration with the actual JSON refusal output.
- Frozen W54/W55/scope/API digests: unchanged. Staged whitespace and exact
  changed-path proof are part of the final commit check.
- No full local `make gate` under R-135; no DB, S3, provider or heavy corpus
  operation ran.

## Contracts and limits

No `contracts/**`, migration, provider lock, root dependency/lock file,
composition root, global style, source corpus byte, production configuration,
`VERSION`, tag or `origin/main` changed. Migration head remains
`0022_findings_v2`. There are no new product contracts; the standalone
recovery manifest `offline-object-copy-v1` is an unactivated local artifact.

W54's source SHA256SUMS/verification, promotion load and restore-verified
dump, paid repair, complete embedding build and verified bundle remain
outstanding. W55 production DB/S3 import additionally needs stand capacity,
P3 compatibility, a tested copy/restore and a named bundle/downtime window.
The W58 object mirror must stay immutable after sealing; transfer, S3 readback,
DB-record binding and a recovery drill remain. W59 API/DB seal, expert
authorization, persisted confirmation, profile activation, finding carryover
and AI summary remain after W58-code close. P/R is not yet a wire enum.

## Publication and next use

Development target: `origin/dev` only, after exact staged-path review, clean
commit, remote-ref recheck and fast-forward proof. No `origin/main` authority,
release tag, complete gate or beta verdict is claimed. The next W54 operator
step is capacity provisioning and source sums in a night window. Later code
owners can use the pure W58/W59 modules only through separately frozen
integration tasks with authoritative persisted state.
