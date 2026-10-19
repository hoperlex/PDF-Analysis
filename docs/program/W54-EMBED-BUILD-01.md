# W54-EMBED-BUILD-01 — the BGE-M3 embedding build of the repaired snapshot

**Date:** 2026-10-19/20. **Base:** `origin/dev` `f942ca1ce0dff227c85b74a90e6de2faa989046e`.
**Task:** `tasks/W54-EMBED-BUILD-01.md`. **Rulings:** `R-137`, `R-138`; the owner's direct polls
of this session waived the RAM floor for the image build and the encode windows and approved
removing unmounted `estimat_test_*` Docker volumes.

## Result

The repaired snapshot has a complete `bge-m3-dense-v1` build in the promotion database,
restore-verified.

| Field | Value |
| --- | --- |
| snapshot | `ns_01M59N8QNBVN91ACA2HCE6VE74`, `characters-v2:1200` |
| plan SHA-256 | `5cc58390d55f177918eeb16e704fdfaa7e6e0950a983a2b707123db06f0187ee` |
| chunks / batches | 55,855 / 219 (256 per batch, 47 in the last) |
| windows (stored `norm_embedding` rows) | 61,573 |
| embedding-set SHA-256 (`norm-embedding-set/2`) | `e7fac64c90b96381ceeb41d2707c222d1ba81240ff8b4eff47fecb3293ffc5df` |
| `embedding status` | 219 verified, 0 missing, 0 invalid |
| `embedding load` | `created: true`, one transaction, completion row written |
| verified dump | `promotion-20261019T195011Z.dump`, 426,857,863 B, SHA-256 `59548d129cdc89faf4367d6ec3f8d1eaed85d38ea56534af9ccda80d72d7c865`, `.verified` |

The checkpoints' digest printed by the last encode run and the digest `load` reported are the
same value. The repository recomputes the set digest from the stored rows after the insert and
requires it to equal the checkpoints' (`D-127`); `load` succeeded, so it did. Fingerprint rows
of the dump: `norms_snapshot` 2, `norm_document` 1,348, `norm_paragraph` 698,971,
`norm_chunk_build` 2, `norm_chunk` 111,557, `norm_embedding_profile` 1,
`norm_embedding_build` 1, `norm_embedding` 61,573, and `norm_repair_call`, `norm_custody_*` 0.
The restore reproduced them. The base-only dump of the previous task was pruned by
`verify-dump.sh` as designed; its copy is under `.local/norms/promotion-dumps-keep/20261015-base/`.

The window count is 752 below the bake-off's 62,325 for the base projection. The repaired
snapshot has 153 more chunks and 121 blocks of replaced text; the difference was not
investigated.

## The steps, as run

1. **Image.** `docker build --file infra/norms-worker/Dockerfile --tag
   auditmanager-norms-worker:bge-m3-dense-v1-5617a9f .` from the repository root, 08:55-09:03 UTC,
   exit 0. Both build-time offline self-tests printed `OK` (`self-check OK: bge-m3-dense-v1
   BAAI/bge-m3@5617a9f6… dim=1024 dtype=float32 norm=1.000000`; `embedder self-test OK:
   windows=8 tokens=3732 embed-texts=stable`). Image 5.51 GB; BuildKit cache 7.7 GB, pruned
   at once. Free disk went from 11.0 GiB before the build to 0.54 GiB after it, cache included.
2. **Prepare.** `embedding prepare` against the promotion database, 4 s, 109 MB of input
   files under `.local/norms/builds/<content_key>`.
3. **One-batch measurement.** One batch through `run-build.sh`: 199 s including the container
   start and the model load, container peak 3.08 GiB of the 5 GiB limit.
4. **Encode.** `run-build.sh` under a resumable supervisor, in two stretches because of the
   incident below: 62 batches 09:08-12:20 UTC (contended host) and 157 batches 12:31-19:35 UTC
   (7.1 h), exit 0. Rate: about 100 s per batch on a quiet host, 3-5 min under other projects'
   load. `docker stats` showed 2.5-4.2 GiB per container; the cgroup split read at one point
   was anon 2.5 GB and file 2.2 GB, and the file part is evictable cache, so the encoder's
   own footprint is about 2.4 GiB.
5. **Load.** `embedding load`, 19:46:54-19:49:54 UTC, exit 0.
6. **Dump and verify.** `dump.sh` (1 min 11 s) and `verify-dump.sh` (1 min 29 s) ran with the
   standard scripts, no wrapper: the host had 7.6 GiB of RAM available by then. The image was
   removed and the cache pruned between them to meet the 6 GiB disk floor of the verify
   (free disk was 5.78 GiB after the dump, 13.3 GiB after the removal). The promotion
   database is stopped at the end of the task.

## Incident: the disk filled up

Between 12:08 and 12:20 UTC another project's `docker build` (`mc-test-api`) took `/` from
5.5 GiB free to 0.04 GiB (5.5, 3.7, 1.8 GiB at five-minute beats, then 0.24 and 0.04 GiB within
the last minute). This task's encode writes about 1.6 MB per batch and was not the
cause (the checkpoint directory is 455 MB at the end). To release space at once, this task's
own supervisor, memory guard and container were stopped by PID/ID and its own image (5.5 GB)
was removed; free disk rose to 2.92 GiB. `embedding status` then showed 62 verified, 0 invalid
and no stray partial file: checkpoints are written to a temporary name, fsynced and renamed,
and the checksum sidecar comes last. The rebuild of the image needed 9.5 GB, so the owner was
polled; the answer was to remove unmounted `estimat_test_*` volumes. 17 volumes, 10.5 GB, were
removed under a strict rule (every database in the volume named `estimat_test_*`, unmounted
at that moment, not modified in a day), listed first in
`.local/cleanup/2026-10-19/estimat-test-volumes-removed.log`; 27 other unmounted volumes
(technic and mixed content) were left alone, and `auditmanager-promotion-data` was never a
candidate. The image was then rebuilt (new id `a83665d2…`, the first was `d67bb87e…`; layers
and timestamps differ, every pinned input and checksum is the same, both self-tests passed
again) and the encode resumed with the 62 verified batches skipped.

**Consequence for the evidence.** Batches 1-62 were encoded by the first image and 63-219 by
the second. No test compared the same batch across the two images; the identity of the inputs
is by pin and checksum, and the stored set digest equals the checkpoints'.

## Findings about the process

- A memory-pressure guard was added next to the supervisor (`encode-guard.sh`): it stops only
  this task's supervisor and container if available RAM stays below 0.8 GiB or swap above
  14.5 GiB for three samples. It never fired.
- The host's disk, not its RAM, was the binding resource: another project's builds moved free
  space by 5-6 GB within minutes, twice (12:08-12:20 UTC to 0.04 GiB, and 12:31-12:37 UTC from
  7.6 to 2.0 GiB, recovered by 12:41). A heavy step here needs the disk floor re-measured
  immediately before it, and no step should assume a number from an hour earlier.
- `pgrep -f <pattern>` followed by `kill` inside a shell whose own command line contains the
  pattern terminated that shell once (the tool shell of this session, no other process). Kill
  by a PID read from a pid file and confirmed by `/proc/<pid>/cmdline`.
- Monitors do not survive a session restart; `nohup setsid` jobs do. The supervisor finished
  the encode while the session was down, and the rc file and the logs under
  `.local/norms/promotion-records/20261019/` carried the result.

## Limits and risks

- The 6 GiB RAM floor was waived by the owner for the image build and the encode; the host
  was below it for most of the encode and above it at the dump and verify. The disk floors were
  met at every step.
- No retrieval-quality or latency measurement was made on these vectors; this is persistence
  only (W55-or-later).
- The first image no longer exists and cannot be inspected; the second was removed after the
  load. A rebuild needs about 11 GB of free disk at its peak and the network.

## Integrator instruction

Merge the two documentation files. The snapshot id and the embedding-set digest above are the
inputs of the bundle; the newest verified dump is the recovery artifact. Nothing is to be
published to `origin/main` for this step.
