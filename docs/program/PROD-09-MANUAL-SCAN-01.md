# PROD-09-MANUAL-SCAN-01 — the manual scan helper, the eight-line release checklist and the dump pruning rule

Task: `docs/program/tasks/PROD-09-MANUAL-SCAN-01.md`. Branch `agent/prod-09-manual-scan-01`, base `bfcb8a97` (`integration/ar-close-1026`). Plan item `PROD-09` of `PRODUCTION-READINESS-PLAN-01.md`; owner rulings `R-146h`, `R-146n` item 5, `AD-05` confirmed by `R-146w` as written at `83600aed`; accepted risk `A-3` (no CI and no automated scan: the helper is a program a person runs, and nothing calls it).

## Result

`scripts/release/manual_scan.sh` prints an inventory and runs `pip-audit`, `npm audit` and the operator's image scanner. `--check-tools` lists the required tools and exits `2` naming each missing one. The last line of a normal run is `MANUAL SCAN RESULT: NO FINDINGS` only when every scanner was present, ran and exited `0` on a readable inventory; every other outcome is `MANUAL SCAN RESULT: NOT COMPLETE` and a non-zero exit (`1` a scanner exited non-zero, `2` not complete, `64` usage). `docs/program/RELEASE_PROCESS.md` carries the eight checklist lines, the manual scan section, the pruning rule for `infra/deploy/dumps/` and the disk-free line.

Premise: **one mismatch, eight matches** (evidence P-01 to P-09 in the task file). Mismatch: `ADR-0021` section 7 names `pip-audit` and `npm audit` but only "an image scanner the operator has installed", no tool. The lane brief says to run only tools the ADR names and not to invent one, so the helper does not pick a scanner: it takes the operator's command from `MANUAL_SCAN_IMAGE_SCANNER` (words only, the helper appends one image reference, the command must exit non-zero on a finding) and reports the image scanner as `MISSING` while the variable is unset or its first word is not on `PATH`. Until the owner names a scanner the helper therefore cannot reach `NO FINDINGS` on his machine. Other differences from the plan's wording: the plan says "image digests named in `compose.server.yml`"; there are two (the proxy's nginx and the `POSTGRES_BASE_IMAGE` build argument), the other five images are built on the host and have no digest, so the helper lists them as not scanned. The receipt of `ADR-0021` section 5 is the copy record in the copy directory, not a file under `infra/deploy/dumps/`; the pruning rule says so.

## Files changed

| File | Change |
|---|---|
| `scripts/release/manual_scan.sh` | new, mode 755, 356 lines; `bash -n` and `shellcheck` 0.9.0 clean |
| `tests/unit/scripts/test_manual_scan.py` | new, 39 cases; stub `PATH`, synthetic tree, no network, no docker |
| `docs/program/RELEASE_PROCESS.md` | +88 lines: sections "Production release checklist", "The manual scan (line 3)", "Pruning `infra/deploy/dumps/` and the disk-free line (line 5)"; no existing line changed |
| `docs/program/tasks/PROD-09-MANUAL-SCAN-01.md`, this report | records |

Test location: `tests/unit/scripts/` mirrors `scripts/`, where the repository's one existing script unit test lives; the other shell-script tests (`tests/integration/composition/test_stand_copy_refusals.py`) use the same idiom of a stub `PATH` (P-05). The gate's battery collects all of `tests`.

## What the helper does and refuses

- Inventory: SHA-256 of `uv.lock`, `web/package-lock.json` and `compose.server.yml`; the 55 registry packages of `uv.lock` as `name==version` (the project's own virtual entry is named and excluded); the 260 npm packages; the two digest references; the five host-built images, labelled not scanned.
- Scanners: `pip-audit --requirement <list> --no-deps --disable-pip --strict` (`--strict` so a package that cannot be audited fails instead of being skipped); `npm audit --package-lock-only --prefix <root>/web`; `<MANUAL_SCAN_IMAGE_SCANNER words> <digest reference>` once per reference. Each output is quoted behind `    | `.
- Refuses (`NOT COMPLETE`): a missing tool (the other scanners still run), a scanner exiting non-zero (an unreachable database is the same), an unreadable or unparsable input, a `uv.lock` package from a non-registry source, no registry package, no image digest, a lock file with no package. It installs, downloads and writes nothing in the tree and removes its temporary directory. It trusts each scanner's exit status.
- Real run on this host (network reachable, `pip-audit` not installed, `MANUAL_SCAN_IMAGE_SCANNER="echo scanning"`): exit `2`; the inventory printed; real `npm audit` 10.9.8 answered exit `1` with `9 vulnerabilities (1 moderate, 5 high, 3 critical)` on `web/package-lock.json` (quoted in the output; a finding for the owner, not changed here); `NOT RUN pip-audit (missing)`; last line `NOT COMPLETE`. This is the evidence that the `npm audit` invocation is accepted by the real tool.

## Test-file changes

No existing test file was modified. `tests/unit/scripts/test_manual_scan.py` is new; the per-test before/after table is empty.

## Mutation table (every guard shown failing)

Each row is one uncommitted edit of `scripts/release/manual_scan.sh` (rows M) or `RELEASE_PROCESS.md` (rows D), applied alone, `tests/unit/scripts/test_manual_scan.py` run in full, the file restored with `git checkout -- <file>`, `git status --short` empty afterwards, the run repeated green (39 passed). Baseline 39 passed. The driver is not committed.

| # | Mutation | Result |
|---|---|---|
| M01 | pip-audit absence not recorded | 4 red (`test_check_tools_detects_each_removal_alone[pip-audit]`, ...) |
| M02 | npm absence not recorded | 4 red |
| M03 | unset image scanner not recorded | 1 red (`test_check_tools_detects_an_image_scanner_nobody_named`) |
| M04 | unresolvable image scanner not recorded | 4 red |
| M05 | python3 absence not recorded | 2 red |
| M06 | `--check-tools` exits 0 with a tool missing | 6 red |
| M07 | a scanner finding exits 0 | 5 red |
| M08 | the not-complete branch never taken | 14 red |
| M09 | scanner output not quoted | 5 red |
| M10 | scanner exit status ignored | 6 red |
| M11 | pip-audit without `--strict` | 1 red (arguments test) |
| M12 | inventory gaps and errors ignored | 2 red |
| M13 | no image digest not an input error | 1 red |
| M14 | compose comments not skipped | 4 red |
| M15 | temporary directory not removed | 2 red |
| M16 | virtual project entry counted as a gap | 9 red |
| M17 | image reference not passed to the scanner | 2 red |
| M18 | npm audit without `--package-lock-only` | 1 red |
| M19 | unknown argument accepted | 1 red |
| M20 | non-registry package not a gap | 1 red |
| M21 | `curl` added to the helper | 2 red (text guard and its own can-fail case) |
| M22 | a missing scanner skipped without a `NOT RUN` line | 3 red |
| M23 | no image digest: input error and `NOT RUN` guard both removed (vacuous image scan) | 1 red |
| M24 | a finding prints the success line | 5 red |
| M25 | empty requirement list: input error and `NOT RUN` guard both removed | 1 red |
| D01 | checklist line 7 removed | 2 red |
| D02 | `manual_scan` removed from line 3 | 1 red |
| D03 | the receipt rule removed | 1 red |
| D04 | the "free space after" step removed | 1 red |

The inventory-error guard and the `NOT RUN` guard are deliberately redundant for an empty image list and an empty requirement list. M13 removes only the input error (the `NOT RUN` guard still refuses, and the test is red because it pins the input-error message); M23 and M25 remove both guards for the image list and the requirement list.

## Commands run

| Command | Result |
|---|---|
| `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/scripts/test_manual_scan.py` | 39 passed (also after every restore) |
| `bash -n scripts/release/manual_scan.sh`; `shellcheck scripts/release/manual_scan.sh` (0.9.0 is installed) | exit 0, no output |
| `scripts/release/manual_scan.sh --check-tools` on this host | exit 2: `MISSING pip-audit`, `MISSING image scanner` |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` | 105 passed |
| governance one-liner on the task file | `[]` |
| `git diff --check` | exit 0 |
| `tests/contract/test_cp00_candidate.py -k reviewed` (not asked for; looked at because the helper is under `scripts/`) | 2 failed, 3 passed, 2 errors: the CP-00 candidate seal (`artifact_count` 100 against 256) lists hundreds of files under `contracts/`, `fixtures/`, `docs/architecture` and `scripts/` that this task did not touch as drifted. It is a historical seal and the gate ignores these tests; not caused by this task. |

## How to integrate

Merge `agent/prod-09-manual-scan-01` onto `integration/ar-close-1026`; there is no dependency on another `PROD-*` item and no shared hotspot. Row 10 of the commitments table of `ADR-0021` is now true: `grep -n "manual_scan" docs/program/RELEASE_PROCESS.md` has hits, and `scripts/release/manual_scan.sh --check-tools` exits non-zero with a scanner missing. Open for the owner: name the image scanner (and, if he wants, have the ADR say which), then `export MANUAL_SCAN_IMAGE_SCANNER="<command words>"` before the run; install `pip-audit` on the machine that runs it.

## Known limits

- The image scanner is operator-named (above); the invocation shape `<words> <reference>` is this task's choice, not the ADR's.
- The `pip-audit` flags (`--requirement`, `--no-deps`, `--disable-pip`, `--strict`) were not run against the real tool: it is not installed here and nothing may be installed. They are pinned in the test's argument assertion only. The first real run on the owner's machine is the proof.
- The helper trusts exit statuses. A scanner that exits `0` without reaching its database would be reported as clean.
- Not scanned, and printed each run: the five host-built images and the `FROM` lines of the Dockerfiles (the python, node, golang, alpine and postgres bases). `D-122` stays open; the helper does not edit it.
- The wider `D-122` check of DEBT-AUDIT-1 (`rg ... Makefile .github infra scripts tools`) now matches `scripts/release/manual_scan.sh`; the register's own check (`Makefile .github infra`) stays empty. Whoever next re-measures `D-122` should read the match as the manual helper, not a scan record.
- Checklist line 6 says what `ADR-0021` expects of `verify-deployed.sh` (default-credential and certificate-expiry checks) and that it does not run them today (`grep -n -i "credential\|checkend" infra/deploy/verify-deployed.sh` finds only lines 151 and 156, about the 401 answer of the closed API, and no certificate-expiry check); the lines of the plan that deliver them will make that sentence stale.
- `python3` 3.11 or later (`tomllib`) is required on the operator's machine; `--check-tools` says so.

## Forbidden paths untouched

`git diff --name-only bfcb8a97..HEAD`:

```text
docs/program/PROD-09-MANUAL-SCAN-01.md
docs/program/RELEASE_PROCESS.md
docs/program/tasks/PROD-09-MANUAL-SCAN-01.md
scripts/release/manual_scan.sh
tests/unit/scripts/test_manual_scan.py
```

No path under `infra/`, `.github/`, `contracts/`, `db/`, `src/`, no `Makefile`, no lock file, no `DEBT_REGISTER.md`, `CURRENT_STATE.md`, `PRODUCTION-READINESS-PLAN-01.md`, `OWNER_RULINGS_*` or ADR is in the list.
