# W54-CORPUS-PROMOTION-01 — base dump restore verified

**Date:** 2026-10-15. **Task:** `tasks/W54-CORPUS-PROMOTION-01.md`.
The promotion base exists in an isolated named volume. Its dump has passed
restore verification on 2026-10-16; the original 2026-10-15 load and dump
evidence below remains unchanged.

## Prepared inputs and isolated state

The source checksum file SHA-256 is
`eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`.
The code-first `uv.lock` SHA-256 is
`461631e7a31bb27aa8058492ab5def78890be1a3c6244da2ad0dfe38932468c4`.
An offline `uv sync --frozen --group test` installed 52 packages in this
checkout's ignored `.venv`; `uv sync --check --frozen --offline` reported
"Would make no changes". The ignored promotion env has mode 0600 and the
four required fields; its credential was not printed or committed. The
promotion project uses port 57190 and volume `auditmanager-promotion-data`.

The first migration attempt from the filesystem sandbox could not connect to
127.0.0.1. The retry with local network access completed all migrations
through `0022_findings_v2`. The input source and migration files did not
change. A separate resource preflight immediately before the loader recorded
9,225,502,720 bytes free on `/`, 7,496,110,080 bytes available RAM and load
average 1 of 5.93 on 8 CPUs, passing W54's base-load floor.

## Base load result

`scripts/promotion/stack.sh run -- env PYTHONPATH=src .venv/bin/python -m
auditmanager.norms.loader --corpus /root/projects/PDF-Analysis/.local/norms/corpus`
returned:

- snapshot ID `ns_01M4ZW72BS7QHAMDJ993VHNJ7K`;
- content key `2026-07-23..2026-08-20+17d.4b74348debf7`;
- chunking profile `characters-v2:1200`;
- `created: true`, `unreliable_count: 0`;
- row digest `44a7b51500e091e85d7950df1655f995fb42563bc8094d3ad3c9abc8123ca7ac`;
- 674 documents, 348,777 paragraphs, 55,702 chunks.

The promotion container was then stopped without removing its volume because
available RAM fell below 6 GiB. A later independent preflight at
2026-10-15 13:44:48 UTC recorded 6,769,041,408 bytes free on `/`,
8,010,805,248 bytes available RAM and load average 1 of 7.63 on 8 CPUs.
`scripts/promotion/dump.sh` then wrote
`promotion-20261015T134454Z.dump` (57,445,702 bytes) with SHA-256
`e1280373ffd7fa3deaa0716429def1844d7e858e79bae7fbad5ade6d516ff74d`
and a fingerprint file. The promotion container was stopped again, retaining
its volume. The dump is ignored by Git under `.local/norms/promotion-dumps/`.

On 2026-10-16 at 07:23:50 UTC, a fresh preflight recorded 11,647,422,464
bytes free on `/`, 8,168,689,664 bytes available RAM excluding swap, and
load average 1 of 4.63 on 8 CPUs. Two preceding 15-second samples also passed
the 6 GiB disk/RAM and load-under-8 window. The exact
`scripts/promotion/verify-dump.sh
.local/norms/promotion-dumps/promotion-20261015T134454Z.dump` command exited 0
and printed `verified: .local/norms/promotion-dumps/promotion-20261015T134454Z.dump`.
The dump SHA-256 remained
`e1280373ffd7fa3deaa0716429def1844d7e858e79bae7fbad5ade6d516ff74d`.
The fingerprint file SHA-256 is
`b39d1baa293ee82c955958361b6e2611ac1de7eb076daaceaa65ad18a25c3023`;
the disposable restore reproduced all twelve recorded table counts and MD5
aggregates, including 674 `norm_document`, 348,777 `norm_paragraph`, 55,702
`norm_chunk`, and zero repair/embedding-build/custody rows. The empty
`.verified` marker exists beside the dump. The ignored operation log is
`.local/promotion/verify-dump-20261016.log`, SHA-256
`c15197b72ec16c474232f2455460678d4cf9d331813ee215193d76ba35593df5`.
No disposable verify container remains; the original
`auditmanager-promotion-postgres-1` container remains stopped with its named
volume retained.

The verified base dump can now feed the offline repair plan. The owner chose
`claude-opus-5` for the later priced three-page sample; the proxy credential
file is absent on this host, so no paid sample or full repair has run. No
repaired snapshot, embeddings, verified bundle or DB/S3 publication exists.

## Boundaries

No source byte, contract, migration, root lockfile, application runtime,
production DB/S3 or `origin/main` was changed. The local promotion env,
runtime, cache, dump and DB volume remain outside Git. The task's base-dump
restore-verification outcome is complete; step 2 repair is a separate task.
