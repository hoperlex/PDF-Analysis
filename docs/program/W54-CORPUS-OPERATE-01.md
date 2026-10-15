# W54-CORPUS-OPERATE-01 — source checksum verification

**Date:** 2026-10-15. **Checkout:** `integration/code-first-entry` at
`8069220909e40c39e2329d5f5cb9585a5a5714ec` before this report.
**Task:** `tasks/W54-CORPUS-OPERATE-01.md`.

## Result

The source drop at `/root/projects/PDF-Analysis/.local/norms/corpus` passed
the complete W54 step-0 checksum run. The absolute sums path is
`/root/projects/PDF-Analysis/.local/norms/corpus-sums/2026-10-15/SHA256SUMS`.
It contains 31,619 sorted relative `./` paths. Running `sha256sum -c` from
the source root returned zero and produced 31,619 `OK` lines, with no failed
or warning line. The sums file SHA-256 is
`eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`.
The source `MANIFEST.json` SHA-256 remained
`160fdc7ea261b44298757b3a066982fd167b389fde614fb119c4c1d0d72fbb3b`.
The sums, verification log, digest file and preflight record are retained
together outside Git in the dated sums directory.

## Resource and command evidence

The immediate prestart at 12:55:58 UTC showed 4,394,106,880 bytes free on
`/`, 7,741,108,224 bytes available RAM excluding swap, and load average 1
of 4.13 on 8 CPUs. This passed the step-0 3 GiB disk reserve, 6 GiB RAM floor
and the user-authorized CPU window. The shell wrote a temporary sums file
with `find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum`, checked
its 31,619 lines, ran `sha256sum -c` from the absolute corpus root, checked
the 31,619 verification lines, and only then moved the complete files to
their final names. No partial file remains.

At 17:56:50 +05, after verification, `/` had 4,382,003,200 bytes free and
available RAM was 5,163,773,952 bytes. W54's next promotion base step needs
its estimated 3 GiB increment plus 3 GiB reserve, or 6 GiB free, and at
least 6 GiB available RAM immediately before it starts. Both floors failed
at this reading, so no promotion stack, DB load or S3 write was started.
The host's free disk and RAM have varied rapidly under other workload; this
record cannot be reused as a later launch preflight.

## Checks and boundaries

- `sha256sum -c` on the complete source drop: exit 0, 31,619 `OK` lines.
- `sha256sum -c SHA256SUMS.sha256`: `SHA256SUMS: OK`.
- Source manifest digest: matched the frozen W54 input.
- Changed tracked paths: this task and this report only. No contract,
  migration, root lockfile, composition root, global style or source byte
  changed. The local cleanup ledger and checksum artifacts are ignored.

The next operator step is the W54 promotion base load in a fresh actual
resource window. Recheck the sums digest and all resource floors immediately
before it, then follow `W54-INT-CORPUS-READINESS-01.md` §Operator sequence.
This step does not claim a qualified DB snapshot, repair, embedding build,
verified bundle, S3 publication or production designation.
