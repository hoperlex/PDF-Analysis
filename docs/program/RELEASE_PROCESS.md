# Release process

This file describes the product release record. `VERSION` is the one-line
canonical SemVer product version; package and project metadata versions do not
move with it. The highest non-archive entry under `release-notes/` must equal
`VERSION`. A release is an owner-authorized deployment of a user-visible change
from `origin/main`, followed by a `v<VERSION>` tag. Development publication to
`origin/dev` does not create a release.

## Authors and review

The assigned release-notes author writes `release-notes/<version>.json` in
Russian, validates it against the sealed shape and the gate-time prose rules,
and records one commit or test for every product claim in the task hand-back.
The author increments `revision` for every content correction, including an
edit to title or date. The independent `W52-NOTES-JUDGE` checks each claim
against the diff and the tree; the judge runs again on the final candidate
after fixes. From W53 onward, the release integration task includes that
independent judgment. The integration owner checks the form tests and verdict
before publication.

`screen` and `where` are authored display history. The current `VERSION` entry
must point to today's screen registry and begin with the current group and
screen labels. Older entries retain their release-time paths even if the
navigation later changes. The loader checks the sealed JSON shape at deploy;
prose and dictionary checks run in the gate so a later dictionary change cannot
make a historical deployment fail.

## Version move and publication

Move `VERSION` only with a new, highest non-archive release-notes entry and a
reviewed user-visible change. Keep previous entries in the image. A file that
reached `main` is never deleted or rewritten at the same authored revision:
the loader appends a higher revision, refuses a changed equal revision, and
retains historical rows on rollback. A correction or withdrawal is expressed
by another revision of that version. The API serves the highest revision no
higher than the running `VERSION`.

The integration owner first publishes the checked development candidate to
`origin/dev`. Release validation supplies independent review, the exact
candidate's full `make gate` with literal `GATE OK`, and the required live and
manual acceptance. `origin/main` triggers deployment and requires the owner's
separate direct instruction naming that exact SHA. Follow
[`MAIN_AUTODEPLOY_POLICY.md`](MAIN_AUTODEPLOY_POLICY.md): re-read `main`, prove a
fast-forward, publish the verified SHA without a later fix, then confirm the
workflow and `infra/deploy/verify-deployed.sh` on the deployment host. The
release task tags `v<VERSION>` only after the deployment evidence is complete
and fills one measured row of `RELEASES.md`.

## Production release checklist

The eight lines of `ADR-0021` section 7 (`R-146h`, `R-146n` item 5). They are
a list a person works through; there is no CI and no machine that checks them
(accepted risk `A-3`). Each line is done on the exact candidate of line 1.

1. The candidate SHA, the owner's direct instruction naming it, and a clean
   tree ([`MAIN_AUTODEPLOY_POLICY.md`](MAIN_AUTODEPLOY_POLICY.md)).
2. The complete gate on that exact tree with the literal `GATE OK`, on a host
   that can run it (`D-205`).
3. The manual dependency and image scan: run
   `scripts/release/manual_scan.sh --check-tools`, then
   `scripts/release/manual_scan.sh` (see below), attach its whole output and
   its date to the release record, and decide each finding.
4. If the database head changes: the pre-migration copy and its receipt, in the
   `R-93` order of `ADR-0021` section 5 (`dump-db`, `inventory-s3`, fetch,
   restore test, `attest`, deploy, `resume`).
5. The heavy-step stop rule and the disk-free line (see below):
   `infra/deploy/capacity-probe.sh --path root=/ --need root=<bytes>` before
   the build, the dump's size counted in the need, and the pruning below.
6. After the push: the workflow finished successfully and
   `infra/deploy/verify-deployed.sh` exits `0` on the host. `ADR-0021` section 7
   expects that script to include the default-credential check (`ADR-0023`) and
   the certificate-expiry check; those arrive with their own items of
   `PRODUCTION-READINESS-PLAN-01.md`, and until they do the script does not run
   them, so say so in the release record instead of assuming them.
7. The public probes: rows 2 to 4 of the table "Commitments and their
   mechanical checks" in `ADR-0021`.
8. The tag and the `RELEASES.md` row only after lines 6 and 7.

### The manual scan (line 3)

`scripts/release/manual_scan.sh` is run by the owner by hand, from a machine
that can reach the vulnerability feeds. It installs and downloads nothing
itself, changes nothing in the checkout, and is never called from a workflow, a
Makefile target or a schedule.

- `--check-tools` lists the required tools and exits non-zero, naming each
  missing one. Run it first. Required: `python3` 3.11 or later (it reads
  `uv.lock`), `pip-audit`, `npm` (`npm audit`), and an image scanner. The image
  scanner is the operator's: `ADR-0021` section 7 says "an image scanner the
  operator has installed" and names none, so the helper takes its command from
  `MANUAL_SCAN_IMAGE_SCANNER` (words only; the helper appends one image
  reference; the command must exit non-zero on a finding).
- Without arguments it prints the inventory (the registry packages of
  `uv.lock`, the npm packages of `web/package-lock.json`, the image references
  with a digest in `infra/deploy/compose.server.yml`, each file's SHA-256),
  runs `pip-audit` on the Python packages, `npm audit` on the lock file and the
  image scanner on each digest reference, and quotes every scanner's output.
- Its last line is `MANUAL SCAN RESULT: NO FINDINGS` only when every scanner was
  present, ran and exited `0`. A missing scanner, a scanner that could not reach
  its database, a finding, an unreadable input, a package that does not come
  from a registry, or no image digest at all gives `MANUAL SCAN RESULT: NOT
  COMPLETE` and a non-zero exit (`1` a scanner exited non-zero, `2` not
  complete). It trusts each scanner's exit status.
- Not covered, and printed every time: the images the host builds (`api`,
  `web`, the worker, `postgres`, `minio`, ...; their `image:` has no digest) and
  the `FROM` lines of the Dockerfiles. The helper makes the absence of a scan
  visible at every release; it does not close `D-122`.

### Pruning `infra/deploy/dumps/` and the disk-free line (line 5)

`copy-serve.sh dump-db` keeps only the latest copy in the copy directory by
itself. `infra/deploy/dumps/` (git-ignored; `$ALPHA_DUMP_ROOT` when set) holds
the directories `reset.sh` (`<instance>-<UTC stamp>`) and
`purge-product-data.sh` (`<instance>-purge-<UTC stamp>`) write, and nothing
prunes it. At each release, by hand, after reading the list:

1. Record the free space before: `infra/deploy/capacity-probe.sh --path
   dumps=<dump root>` prints `avail_bytes=`; the same for `root=/`.
2. List the directories newest first (`ls -1t <dump root>`). Keep the newest
   two. Keep any directory a release record names (`RELEASES.md`, the release
   task's report).
3. Never delete the dump a receipt still points at. The receipt is the copy
   record `record.json` in the copy directory (`STAND_COPY_DIR`, default
   `/srv/auditmanager-copy`; `dump.file`, `dump.sha256`, `quiesced_at`); that
   dump lives in the copy directory and `dump-db` replaces it by itself. While
   `record.prev.json` exists, the previous copy's dump is still restorable and
   stays. Keep the last receipt.
4. Delete the other directories under the dump root by hand. There is no
   pruning script, on purpose: a tool that deletes dumps is a second
   destructive tool.
5. A dump that holds client data is deleted by the same hand as soon as the
   release it guarded is accepted, and an erase (`ADR-0022`) is followed by the
   same pruning.
6. Record the free space after, beside the figure from step 1, in the release
   record.

## Hotfix and rollback

Create a hotfix branch from the affected release tag. Make the bounded fix and
release-note revision, run the full gate on its exact candidate, obtain the
owner's exact-SHA `main` instruction, and fast-forward `main` through the same
deployment verification. Merge the hotfix back to `dev` so the development
line retains it. A rollback is a reviewed forward revert with a fresh gate and
deployment verification; never force-push or move `main` backward. An older
image may hide database releases above its `VERSION`, but published note files
remain part of the repository history and image input set.
