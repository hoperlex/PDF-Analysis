# W54-INT-CORPUS-READINESS-01 — normative corpus preflight

**Task:** `tasks/W54-INT-CORPUS-READINESS-01.md`. **Measured on:**
2026-10-15, `origin/dev` `97224aec`. This is preparation for
`W54-CORPUS-OPERATE-01`; it is not a corpus operation or a production import.

## Source and current stop

The read-only drop at `/root/projects/PDF-Analysis/.local/norms/corpus`
contains **674 document directories**, **31,619 files** and occupies about
**5.1 GiB**. `MANIFEST.json` has SHA-256
`160fdc7ea261b44298757b3a066982fd167b389fde614fb119c4c1d0d72fbb3b`.
Only the `corpus` child exists under `.local/norms/`: no `corpus-sums`,
`repairs`, `builds`, `bundles` or `promotion-dumps` was present. A manifest
hash and file count do not verify the drop's file contents.

At the latest preflight, `/` had **6,066,712,576 bytes** available and
`free -b` showed **1,641,869,312 bytes** available RAM. W54 §3.9 requires
the running step's disk increment **plus 3 GiB** and at least **6 GiB
available RAM**, excluding swap, immediately before each heavy step in a
night window. Neither a base load, dump/restore verification, repair run,
image/build, bundle export nor local rehearsal may start on this reading.
W55 §C6 estimates about **19 GiB free** for the local copy/restore rehearsal;
capacity must be provisioned and measured again, with the artifacts already
resident accounted for. No source byte, database, model or stand was changed.

## Operator sequence once capacity and a night window exist

Use the current code checkout and the absolute source drop path above; the
drop lives outside the `code-first-entry` worktree. Keep all outputs under
`.local/`, outside Git. Before each numbered heavy step, record `date -u`,
`df -B1 /`, `free -b` and the step's increment from W54 §3.9. Stop on any
failed floor or hash. The next operator task owns these actions, not this
readiness report.

1. **Source sums (W54 step 0).** In the designated window, create
   `.local/norms/corpus-sums/<date>/SHA256SUMS` by running from inside the
   absolute corpus directory:
   `find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum > <sums-path>`.
   Run `sha256sum -c <sums-path>` from that same directory and retain the
   sums file's SHA-256. `read_drop_sums` accepts relative `./` paths and
   refuses duplicate or malformed lines. If any source byte changes, stop;
   never repair against an unverified crop.
2. **Promotion base (step 1).** Use `scripts/promotion/stack.sh up`, then
   `migrate`, with its local env file and port `57190`; load the base through
   `python -m auditmanager.norms.loader --corpus <absolute-drop>` under
   `stack.sh run --` and `PYTHONPATH=src`. Record the returned opaque `ns_`,
   content key, row digest and counts. Run `scripts/promotion/dump.sh` and
   `scripts/promotion/verify-dump.sh`; only a restore-verified dump permits
   the next step. Stop the promotion database between steps. The env file
   contains credentials and is never copied to Git or printed.
3. **Durable repair (step 2).** Follow `W54-REPAIR-01.md` §5 exactly: first
   the offline `repair plan` (expect 121 pages), then the three-crop priced
   sample with the verified sums and the base `ns_`. Continue to `repair full`
   only on `proceed` or a recorded owner ruling for the sample projection.
   Preserve the fsynced journal and response bytes outside the DB volume,
   export its ledger/status, then dump and restore-verify. Any unpriced or
   wrong-model response stops; unknown outcomes count against the $10 cap
   and are never silently retried.
4. **Repaired snapshot and vectors (step 3).** Load with the exported repair
   ledger and `characters-v2:1200` chunking; record the new `ns_` and digest.
   `auditmanager.norms.embedding prepare` writes a checkpoint plan;
   `infra/norms-worker/run-build.sh` encodes bounded batches with no network;
   `embedding status` must show every batch verified before `embedding load`
   writes the completion row. Dump and restore-verify, then prune the build
   image as W54 directs. A partial build is never a promotion bundle.
5. **Verified bundle (step 4).** `auditmanager.norms.bundle export` names the
   repaired `ns_`, `characters-v2:1200`, the absolute drop, the step-0 sums,
   the ledger and `.local/norms/bundles/`. `bundle verify <directory>` must
   re-hash every file and the manifest must state `build: present`. Retain
   the bundle and latest verified dump as recovery artifacts; stop the
   promotion database.

`W55-PLAN.md` §A7 is a **separate production operation**. Once the verified
bundle exists, first establish the actually deployed SHA/migration and P3
compatibility, measure the stand's `capacity`, and complete the copy/pull and
local restore test. The owner then supplies a downtime window and directly
names the bundle key/digest. The integrator uses only the two forced-command
keys: receive before quiesce, dump/inventory/fetch/restore-test/attest,
import/report, resume, administrator designation and read-back. No `main`
push occurs during P4. The current record does not claim P3, a stand copy,
an embedding build or a deployed corpus.

## Verification, limits and handoff

The manifest hash, counts, disk/memory reading, plan hashes, current code
CLIs and absence of output directories were checked read-only. Direct task
governance, `git diff --check` and the three-path proof are recorded at
integration. No full local gate, paid call, Docker step or stand operation
ran. Contracts, migration head, source bytes, provider lock, root
dependencies/locks, composition root, global styles and `origin/main` are
unchanged. Revert these documentation files to roll back this preflight.

The next action is capacity provisioning and a fresh night-window preflight
for step 0. If the required floor fails on two nights, W54 §3.9 assigns a
`W54-INT-CARRYOVER-01` record. Production downtime is requested only after
the verified bundle and compatibility evidence exist.
