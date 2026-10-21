# W54-SNAPSHOT-LOAD-01 — the repaired snapshot loaded into the promotion database

**Date:** 2026-10-19. **Base:** `origin/dev` `db3dd97e84dee13cde0b79f9693fafa0fc299aeb`.
**Task:** `tasks/W54-SNAPSHOT-LOAD-01.md`. **Rulings:** `R-137`, `R-138` (the ledger);
the owner's direct poll of this session waived the 6 GiB RAM floor for this step only.

## Result

The repaired snapshot is committed to the promotion database beside the base snapshot,
in one transaction, and a restore-verified dump holds both.

| Field | Value |
| --- | --- |
| `norms_snapshot_id` | `ns_01M59N8QNBVN91ACA2HCE6VE74` |
| content key | `2026-07-23..2026-08-20+17d+121r.0a1bafe103ff` (the key the ledger predicted) |
| chunking profile | `characters-v2:1200` |
| `created` / `unreliable_count` | `true` / `0` |
| row digest | `a3111764c9fb01796444880a979fa50530948f93d9fedde194cecb3c873ff7ac` |
| documents / paragraphs / chunks | 674 / 350,194 / 55,855 |
| base snapshot (unchanged) | `ns_01M4ZW72BS7QHAMDJ993VHNJ7K`, 674 / 348,777 / 55,702 |
| difference to the base | +1,417 paragraphs, +153 chunks, same 674 documents |

The loader exited 0 in 59 s (08:43:19–08:44:18 UTC). Its sampled peak RSS was 0.13 GiB
(`VmHWM` read every 15 s, so a lower bound) and the lowest available RAM on the host during
it was 4.06 GiB. The RAM watchdog (abort below 0.75 GiB, confirmed own PID only) never
fired.

**The base snapshot is untouched.** The per-table row fingerprints (count and md5 over the
md5 of every row) of the five tables, restricted to the base `ns_`, equal the base dump's
whole-table fingerprints from 2026-10-15: `norms_snapshot` `a04bc645…`,
`norm_document` `413500d9…`, `norm_paragraph` `17c0c4e6…`, `norm_chunk_build` `02d7e537…`,
`norm_chunk` `87a34372…`.

## Dump and restore-verify

`dump.sh` refused: `memory floor: 4409925632 bytes available, a heavy step needs
6442450944`. Under the waiver the same script body ran through a wrapper
(`waived.sh`, kept in the records directory) that sources the real `lib.sh`, replaces only
`promotion_require_floor` by its disk-only half, and `eval`s the repository's own
`dump.sh` / `verify-dump.sh` text with the `lib.sh` source line removed. The disk floor was
checked and held. Each run printed `waived: RAM floor not checked` with the available figure
(4.45 GB for the dump, 5.06 GB for the verify).

- dump `promotion-20261019T084523Z.dump`, 114,392,817 B, SHA-256
  `532e739062fa9489faf6e4b9ff13d5c9d2bec88a32c48d3d50a272679603f5cc`, taken with the
  fingerprint equal before and after;
- `verify-dump` restored it into a disposable network-less 1 GiB instance and reproduced
  the fingerprint; `.verified` written; the disposable container is gone;
- fingerprint rows: `norms_snapshot` 2, `norm_document` 1,348, `norm_paragraph` 698,971,
  `norm_chunk_build` 2, `norm_chunk` 111,557 (each exactly base plus repaired),
  `norm_embedding_profile` 1, and `norm_embedding_build`, `norm_embedding`,
  `norm_repair_call`, `norm_custody_*` all 0;
- `verify-dump.sh` pruned the 2026-10-15 base dump by design. A copy with its sidecars
  (SHA-256 `e1280373…`) was taken first into
  `.local/norms/promotion-dumps-keep/20261015-base/`.

The promotion container is stopped (`Exited (0)`); volume `auditmanager-promotion-data` is
kept.

## What else changed in the database

`alembic_version` was `0022_findings_v2`, behind the code head `0023_norm_citations`. The
upgrade ran through `stack.sh run` before the load. `0023` is additive (retrieval-set and
citation tables, constraints and trigger functions on `audit_run`, `finding` and
`finding_observation`, and a replaced custody-binding guard function); it writes no
`norm_*` row, which the base fingerprint above confirms.

## Resources, measured

| | before (08:42:20) | after (08:47:10) |
| --- | --- | --- |
| disk available on `/` | 12,523,311,104 B | 11,834,884,096 B (the step used 688,427,008 B) |
| RAM available | 3,830,718,464 B | 4,520,587,264 B |
| load average (1 / 5 / 15 min) | 1.86 / 1.48 / 1.27 | 18.48 / 9.21 / 4.33 |

The load average after the step is other projects' work: every process of this step had
exited and the promotion container was stopped when it was read. It shows the host
moving between 1.9 and 18 within five minutes, which the §3.9 text already says of RAM.

The §3.9 table budgets 3 GB for loading a snapshot into the promotion database and 3 GB
for a dump and restore-verify; the measured disk step is 0.69 GB including the 114 MB dump.
The RAM the step needed was 0.13 GiB plus a 1 GiB-capped database container, far below the
6 GiB stop rule, which is sized for the embedding build.

Records (ignored): `/root/projects/PDF-Analysis/.local/norms/promotion-records/20261019/`
(`preflight-load.txt`, `migrate.txt`, `load-start.txt`, `load-result.json`, `load-end.txt`,
`load-peaks.txt`, `preflight-dump.txt`, `dump-result.txt`, `verify-dump-result.txt`,
`post-step.txt`, `waived.sh`).

## Findings about the tooling

- `scripts/promotion/stack.sh migrate` calls `${PROMOTION_ROOT}/.venv/bin/python`; the
  `w54-session-repair` worktree has no `.venv`, so the upgrade was run through
  `stack.sh run -- env PYTHONPATH=src <lock-matched venv python> -m alembic …`.
- `stack.sh run` execs its argument vector as given; it uses no Python of its own.
- The memory floor is enforced only inside `dump.sh`, `verify-dump.sh` and `restore.sh`. The
  loader checks nothing, so the stop rule for a load is procedural.
- `verify-dump.sh` removes every older dump after a success. Keep a copy first when the old
  dump is the only record of a state the new one does not contain; here the new dump holds
  the base snapshot too, so the copy is insurance only.

## Limits and risks

- The load and dump ran below the §3.9 RAM floor by the owner's direction. The floor
  remains in force for the embedding steps. No other project's process was touched.
- The row digest and counts are the loader's own output for this projection; no second
  implementation re-derived them. The base-row equality above is the independent check.
- The newest dump is the only verified dump in the dumps directory; the base copy sits in
  the `keep` directory outside the pruning path.

## Next

`embedding prepare` for `ns_01M59N8QNBVN91ACA2HCE6VE74` with `characters-v2:1200`, the
`infra/norms-worker` image build (about 6.5 GB, network needed, 3.2 GiB RSS at build), the
encode windows (`run-build.sh`, 3.2 GiB RSS, about 14 h on 8 threads by the image
measurement), `status`, `load`, dump and verify, then `bundle export` and `bundle verify`.
These keep the 6 GiB available-RAM floor and the night-window rule unless the owner rules
otherwise.

## Integrator instruction

Merge the two documentation files. The recorded `ns_` and content key are inputs of the
next steps. Nothing else is to be published for this step; `origin/main` is not involved.
