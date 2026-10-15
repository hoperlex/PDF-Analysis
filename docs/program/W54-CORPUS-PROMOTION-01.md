# W54-CORPUS-PROMOTION-01 — base dump awaiting restore verification

**Date:** 2026-10-15. **Task:** `tasks/W54-CORPUS-PROMOTION-01.md`.
This record is interim: the promotion base exists in an isolated named volume
and a dump has been written, but no dump has yet passed restore verification.

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

`verify-dump.sh` has **not** run: disk and RAM have remained below its fresh
6 GiB floors or CPU load has exceeded the user-requested quiet window. The
dump has no `.verified` marker. The base snapshot is therefore **not** a
restore-verified promotion artifact. The next action is to run
`verify-dump.sh` in a new resource window and compare its restored fingerprint.
Never proceed to paid repair or bundle export until the dump is marked
`.verified`.

## Boundaries

No source byte, contract, migration, root lockfile, application runtime,
production DB/S3 or `origin/main` was changed. The local promotion env,
runtime, cache, dump and DB volume remain outside Git. This task is incomplete
until the dump is restore-verified.
