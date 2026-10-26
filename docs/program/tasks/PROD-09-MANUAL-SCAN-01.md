# Task PROD-09-MANUAL-SCAN-01 — the manual scan helper, the eight-line release checklist and the dump pruning rule

task_id: PROD-09-MANUAL-SCAN-01
status: completed in development candidate

## Outcome

`scripts/release/manual_scan.sh` exists, with `--check-tools` and a normal mode that the owner runs by hand from a machine with network access. It never prints its success line when a required tool is missing or a scanner exits non-zero, and `docs/program/RELEASE_PROCESS.md` carries the eight checklist lines of `ADR-0021` section 7, the manual pruning rule for `infra/deploy/dumps/` and the disk-free line (`R-146h`, `R-146n` item 5, `AD-05` confirmed by `R-146w`; accepted risk `A-3`).

## Depends on

- `PRODUCTION-READINESS-PLAN-01` — completed; item `PROD-09` is this task.
- `ADR-0021` section 7 and section 5 — accepted.

## Frozen inputs

- domain contract: not_applicable
- API contract: unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable
- migration head: unchanged
- base commit: `bfcb8a978e9ec9dd9fb3ac500e4b17551674e24b` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

The checklist is eight numbered lines and the scanner set is three; neither is a set another file enumerates. `test_release_process_carries_the_eight_line_checklist_and_the_manual_scan` pins the eight.

## Captured premise evidence

- premise: the plan's sentences about `scripts/release`, `RELEASE_PROCESS.md`, the tools `ADR-0021` section 7 names, the repository's script-test idiom, `D-122`, the inventory inputs and the dump directory, re-read at the base commit; one mismatch (P-03: the ADR names no image scanner)

### P-01 — `scripts/release` does not exist and `RELEASE_PROCESS.md` does, at the base commit

- captured_at: 2026-10-26
- command: `git ls-tree -r --name-only bfcb8a97 -- scripts/release docs/program/RELEASE_PROCESS.md`
- captured_output:
  ```text
  docs/program/RELEASE_PROCESS.md
  ```
- interpretation: Only `docs/program/RELEASE_PROCESS.md` is listed: `scripts/release/` is new in this task. The plan's premise (a script to create, a document to extend) holds.

### P-02 — what `RELEASE_PROCESS.md` says today about checks, scans, pruning and dumps (base commit)

- captured_at: 2026-10-26
- command: `git show bfcb8a97:docs/program/RELEASE_PROCESS.md | grep -n -i -E 'gate|check|scan|prun|dumps|checklist'`
- captured_output:
  ```text
  13:Russian, validates it against the sealed shape and the gate-time prose rules,
  16:edit to title or date. The independent `W52-NOTES-JUDGE` checks each claim
  19:independent judgment. The integration owner checks the form tests and verdict
  25:navigation later changes. The loader checks the sealed JSON shape at deploy;
  26:prose and dictionary checks run in the gate so a later dictionary change cannot
  39:The integration owner first publishes the checked development candidate to
  41:candidate's full `make gate` with literal `GATE OK`, and the required live and
  53:release-note revision, run the full gate on its exact candidate, obtain the
  56:line retains it. A rollback is a reviewed forward revert with a fresh gate and
  ```
- interpretation: The file has three sections (authors and review, version move and publication, hotfix and rollback). It names the full gate with `GATE OK`, `verify-deployed.sh` and the tag/`RELEASES.md` row, but no scan, no pruning and no numbered checklist. The eight-line list therefore fits as a new section between "Version move and publication" and "Hotfix and rollback" and contradicts nothing in the existing text.

### P-03 — the tools and commands `ADR-0021` section 7 names, and the absence of a named image scanner

- captured_at: 2026-10-26
- command: `sed -n '211,243p' docs/architecture/adr/ADR-0021-production-topology-and-operations.md`
- captured_output:
  ```text
  ### 7. The manual release checklist and the manual scan (`R-146h`, `R-146n` item 5)

  There is no CI workflow and no automated dependency or image scan, and none is added. The
  compensation the owner accepted is one line of the release checklist. The checklist for the
  production release, kept here until a later lane writes it into `RELEASE_PROCESS.md`:

  1. the candidate SHA, the owner's direct instruction naming it, a clean tree (`MAIN_AUTODEPLOY_POLICY.md`);
  2. the complete gate on that exact tree with the literal `GATE OK`, on a host that can run it (`D-205`);
  3. **the manual dependency and image scan**: run `AD-05`'s helper, attach its output and date to the
     release record, and decide each finding;
  4. if the database head changes, the pre-migration copy and its receipt, the `R-93` order of section 5 (`dump-db`,
     `inventory-s3`, fetch, restore test, `attest`, deploy, `resume`);
  5. the heavy-step stop rule: `capacity-probe.sh --path root=/ --need root=<bytes>` before the build, with the dump's
     size counted in the need, and the pruning below;
  6. after the push: the workflow finished successfully and `verify-deployed.sh` exits `0` on the host,
     which includes the default-credential check (`ADR-0023`) and the certificate-expiry check;
  7. the public probes (the table below, rows 2 to 4);
  8. the tag and the `RELEASES.md` row only after items 6 and 7.

  **Pruning (manual).** The copy directory keeps only the latest copy by itself (`dump-db` removes older stamps).
  `infra/deploy/dumps/` (git-ignored, written by `reset.sh` and `purge-product-data.sh`) grows with every use and
  nothing prunes it: at each release the operator keeps the last two directories and any directory a release record
  names, deletes the rest by hand, and records the free space of the filesystem before and after
  (`capacity-probe.sh --path dumps=<ALPHA_DUMP_ROOT>`). A dump that holds client data is deleted by the same hand
  as soon as the release it guarded is accepted, and an erase (`ADR-0022`) is followed by the same pruning.

  `AD-05`, confirmed by `R-146w` as written at commit `83600aed`: the helper is `scripts/release/manual_scan.sh`. It prints an inventory (the
  resolved Python packages of `uv.lock`, the npm packages of `web/package-lock.json`, the image
  digests named in `compose.server.yml`) and runs whichever of `pip-audit`, `npm audit` and an image
  scanner the operator has installed, and it never prints a pass when a scanner is missing or the
  vulnerability database could not be reached. The scanners need network access to a vulnerability
  feed; the operator runs them from a machine that has it. This does not close `D-122`; it makes the
  absence of a scan visible at every release.
  ```
- interpretation: The ADR names `pip-audit` and `npm audit` exactly, the inputs (`uv.lock`, `web/package-lock.json`, the image digests of `compose.server.yml`) and the rule that the helper never prints a pass when a scanner is missing or the vulnerability database could not be reached. It says "an image scanner" and names none. MISMATCH with the lane brief, which expects every scanner to be named: this lane does not invent one; the helper takes the operator's image scanner command from `MANUAL_SCAN_IMAGE_SCANNER` and reports it missing while unset. Recorded for the integrator in the report.

### P-04 — no document under `docs` or `infra` names an image scanner

- captured_at: 2026-10-26
- command: `git grep -l -i -E 'trivy|grype|syft|osv-scanner|docker scout|image scanner' bfcb8a97 -- docs infra scripts Makefile .github`
- captured_output:
  ```text
  bfcb8a97:docs/program/DEBT-AUDIT-1.md
  bfcb8a97:docs/program/DEBT_REGISTER.md
  ```
- interpretation: At the base commit only the debt register and the debt audit match, and both discuss the absence of a scan; neither names a tool to use. (`ADR-0021` section 7 says "an image
scanner" across a line break, which a line grep does not match; P-03 shows it.)

### P-05 — how the repository tests shell scripts

- captured_at: 2026-10-26
- command: `git grep -l 'scripts/.*[.]sh' bfcb8a97 -- tests`
- captured_output:
  ```text
  bfcb8a97:tests/e2e/test_pc01_journey_conformance.py
  bfcb8a97:tests/integration/composition/test_stand_copy_refusals.py
  ```
- interpretation: Script tests run the script as a subprocess under a `PATH` of stubs (`tests/integration/composition/test_stand_copy_refusals.py`; `tests/contract/test_alpha_acceptance_command.py` builds its script path from parts, so the grep does not list it); python tools under `scripts/` are tested in `tests/unit/scripts/`. This lane's test follows the same idiom and lives in `tests/unit/scripts/` (it needs no database, docker or network, so it belongs with the unit tests, and the gate's battery collects all of `tests`).

### P-06 — what `D-122` says, and the DEBT-AUDIT-1 check that the new file touches

- captured_at: 2026-10-26
- command: `sed -n '/^### D-122/,/^### D-121/p' docs/program/DEBT_REGISTER.md; grep -n '^| D-122' docs/program/DEBT-AUDIT-1.md | cut -c1-330`
- captured_output:
  ```text
  ### D-122 — no online vulnerability, licence or image scan

  **Opened 2026-10-05 by `W48-INT-CLOSE`, from `reviews/W48-AUDIT.md` §7 question 5.** `npm ls`
  proves installation shape only. No CVE database, transitive-licence report or container-image
  scan has been run against `uv.lock`, `web/package-lock.json` or the built images.

  **Check:** `rg -n -i 'trivy|grype|osv|pip-audit|npm audit' Makefile .github infra` → empty.


  ### D-121 — the alpha acceptance verdict attests the deployed revision; it does not measure it
  20:| D-122 | STILL-OPEN | `rg -n -i 'trivy\|grype\|osv\|pip-audit\|npm audit\|dependabot\|syft\|cyclonedx' Makefile .github infra scripts tools` is empty; the only workflow is `deploy-auto.yml`; `git grep` outside the register finds no scan record in `docs/`. | unchanged |
  ```
- interpretation: `D-122` says no online scan was ever run and gives the check `rg -n -i 'trivy|grype|osv|pip-audit|npm audit' Makefile .github infra` (empty): it stays empty, because the helper is under `scripts/`. DEBT-AUDIT-1's wider check also lists `scripts` and `tools`; it will now match `scripts/release/manual_scan.sh` and `docs/program/RELEASE_PROCESS.md` by name. That is expected and does not close the debt (the helper records no scan, and `ADR-0021` says it does not close `D-122`); the helper prints this on every run.

### P-07 — the inventory inputs: package counts and the digest references of `compose.server.yml`

- captured_at: 2026-10-26
- command: `grep -c '^\[\[package\]\]' uv.lock; grep '^source' uv.lock | cut -c1-30 | sort | uniq -c; python3 -I -c "import json;print(len(json.load(open('web/package-lock.json'))['packages'])-1)"; grep -n -E '@sha256|^ +image:' infra/deploy/compose.server.yml | cut -c1-170`
- captured_output:
  ```text
  56
       55 source = { registry = "https:/
        1 source = { virtual = "." }
  260
  67:        POSTGRES_BASE_IMAGE: postgres:17.11-trixie@sha256:67f41722b7a8cbdb868a44a4995c846eddfdc2973bccb291ce937dce88ad5675
  68:    image: ${ALPHA_INSTANCE:?ALPHA_INSTANCE is unset.}-postgres-pgvector:17.11-v0.8.6-8ee86c9
  104:    image: ${ALPHA_INSTANCE:?ALPHA_INSTANCE is unset.}-minio:RELEASE.2025-10-15T17-29-55Z-9e49d5e
  132:    image: ${ALPHA_INSTANCE:?ALPHA_INSTANCE is unset.}-mc:RELEASE.2025-08-13T08-35-41Z-7394ce0
  153:    image: ${ALPHA_INSTANCE:?ALPHA_INSTANCE is unset.}-api
  170:    image: ${ALPHA_INSTANCE:?ALPHA_INSTANCE is unset.}-api
  185:    image: ${ALPHA_INSTANCE:?ALPHA_INSTANCE is unset.}-api
  259:    image: ${ALPHA_INSTANCE:?ALPHA_INSTANCE is unset.}-api
  329:    image: ${ALPHA_INSTANCE:?ALPHA_INSTANCE is unset.}-web
  361:    image: nginx:1.27-alpine@sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10
  ```
- interpretation: `uv.lock` has 56 packages (55 from the PyPI registry, 1 virtual: the project itself); `web/package-lock.json` has 260 packages besides the root; `compose.server.yml` carries two image references with a digest (the `POSTGRES_BASE_IMAGE` build argument and the proxy's nginx) and builds the other images on the host (their `image:` has no digest). So `the image digests named in compose.server.yml` are two, and the helper lists the host-built images as not scanned.

### P-08 — where the dumps are written, and what the receipt is

- captured_at: 2026-10-26
- command: `grep -n -E 'infra/deploy/dumps' .gitignore; grep -n -E '^DUMP_DIR=' infra/deploy/reset.sh infra/deploy/purge-product-data.sh; grep -n -E 'record.prev.json|record.json' infra/deploy/copy-serve.sh | head -6`
- captured_output:
  ```text
  35:infra/deploy/dumps/
  infra/deploy/reset.sh:525:DUMP_DIR="$DUMP_ROOT/$CONFIGURED_INSTANCE-$STAMP"
  infra/deploy/purge-product-data.sh:357:DUMP_DIR="$DUMP_ROOT/$CONFIGURED_INSTANCE-purge-$STAMP"
  41:#                               -- the previous record's (`record.prev.json`)
  55:#                                /srv/auditmanager-copy). Holds `record.json`, while a new
  56:#                                copy is incomplete `record.prev.json`, the marker
  64:# THE RECORD (`record.json`, schema in `docs/program/W54-STAND-COPY-01.md` §3) is kept on
  67:# stays beside it as `record.prev.json`, and its dump stays restorable (`W54-JUDGE-A` F6).
  98:RECORD="$COPY_DIR/record.json"
  ```
- interpretation: `infra/deploy/dumps/` is git-ignored; `reset.sh` writes `<instance>-<UTC stamp>` and `purge-product-data.sh` `<instance>-purge-<UTC stamp>`. The receipt of `ADR-0021` section 5 is the copy record `record.json` in the copy directory (with `record.prev.json` while a new copy is incomplete), not a file under `dumps/`. So the plan's "never prune the dump a receipt points at" concerns the dump in the copy directory, which `dump-db` replaces itself; the pruning rule says so.

### P-09 — the disk-free command the checklist cites exists and is read-only

- captured_at: 2026-10-26
- command: `infra/deploy/capacity-probe.sh --path dumps=/tmp; echo exit=$?`
- captured_output:
  ```text
  path dumps: /tmp filesystem=/dev/vda3 mount=/ avail_bytes=2914148352 size_bytes=126828056576
  ram_available_bytes: 6760849408
  swap_total_bytes: 17179865088
  swap_free_bytes: 10518036480
  load: 2.72 2.96 4.90
  exit=0
  ```
- interpretation: `capacity-probe.sh --path <label>=<absolute path>` prints `avail_bytes=` for the path's filesystem and exits 0; it is the command `ADR-0021` section 7 names for the disk-free line.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `scripts/release/manual_scan.sh`
- `tests/unit/scripts/test_manual_scan.py`
- `docs/program/RELEASE_PROCESS.md`
- `docs/program/tasks/PROD-09-MANUAL-SCAN-01.md`
- `docs/program/PROD-09-MANUAL-SCAN-01.md`

## Forbidden hotspots

`infra/**`, `.github/**`, `Makefile`, root dependency and lock files (`uv.lock`, `web/package-lock.json`, `pyproject.toml`), `contracts/**`, `db/**`, `src/**`, the composition root, global styles, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, `PRODUCTION-READINESS-PLAN-01.md`, `OWNER_RULINGS_*`, the ADRs.

## Non-goals

- No scanner is installed, downloaded or chosen: the helper runs `pip-audit` and `npm audit` (named by the ADR) and the operator's own image scanner.
- No CI workflow, schedule, Makefile target or gate step calls the helper (`R-146h`, `A-3`).
- No pruning script: the pruning rule is documentation (the ADR says "by hand"), and nothing under `infra/**` changes.
- `D-122` is not closed and not edited.

## Deliverables

- `scripts/release/manual_scan.sh`: `--check-tools` (lists the required tools, exits 2 naming each missing one) and the normal mode (inventory, then `pip-audit`, `npm audit` and the operator's image scanner; every output quoted; the last line is `MANUAL SCAN RESULT: NO FINDINGS` only when everything ran and exited 0; exit 0/1/2/64).
- `tests/unit/scripts/test_manual_scan.py`: 39 cases under a stub `PATH` with a synthetic tree (no network, no docker, no installed scanner).
- `docs/program/RELEASE_PROCESS.md`: the section "Production release checklist" (eight lines), "The manual scan", "Pruning `infra/deploy/dumps/` and the disk-free line".
- Report `docs/program/PROD-09-MANUAL-SCAN-01.md`.

## Required tests

- `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/scripts/test_manual_scan.py` — expected: 39 passed.
- `bash -n scripts/release/manual_scan.sh` and `shellcheck scripts/release/manual_scan.sh` — expected: exit 0 (shellcheck 0.9.0 is installed on this host).
- `scripts/release/manual_scan.sh --check-tools` on this host — expected: exit 2 naming `pip-audit` and the image scanner (neither is installed here).
- Docs guards: `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`, and `git diff --check`.
- Mutations: 29 edits of the helper and the checklist, each shown red and restored (table in the report).

## Integration contract

The integrator can rely on: `scripts/release/manual_scan.sh --check-tools` exits non-zero and names the missing tool whenever `pip-audit`, `npm`, `python3` (3.11+) or the image scanner is missing; a normal run prints `MANUAL SCAN RESULT: NO FINDINGS` only if every scanner ran and exited 0 on a readable inventory; nothing outside the five allowed paths changed; commitment row 10 of `ADR-0021` (`grep -n "manual_scan" docs/program/RELEASE_PROCESS.md` has a hit and `--check-tools` exits non-zero with a scanner missing) is true.

## Failure/idempotency/security cases

A missing tool, a scanner that exits non-zero (a finding or an unreachable database), an unreadable or unparsable lock file, a package from a non-registry source, a compose file with no image digest and an empty package list each make the run `NOT COMPLETE`. The helper changes no file in the tree and removes its temporary directory; a second run gives the same result. It prints no credential: it reads none.

## Rollback / feature flag

Forward-revert. The helper is not called by any other file, so there is no behaviour to flag.

## Handoff

- changed files: the helper, its test, `RELEASE_PROCESS.md`, this task file and the report
- commands/results: see the report
- known limits: see the report (the image scanner is operator-named; `pip-audit` flags untested against the real tool; host-built images and Dockerfile `FROM` lines are not scanned)
- integration notes: merge any time; no dependency on another `PROD-*` item
