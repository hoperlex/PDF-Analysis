# Task AR-V3-ACTIVATION-FEASIBILITY-01 — what of the AR v3 beta activation can be done on this host

task_id: AR-V3-ACTIVATION-FEASIBILITY-01
status: completed in development candidate (lane AR-F of wave PW5; read-only report)

## Outcome

One report, `docs/program/AR-V3-ACTIVATION-FEASIBILITY-01.md`, that says for each step of `AR-V3-BETA-ACTIVATION-RUNBOOK-01.md` whether it is done on this host, possible here, needs the owner's live host, or impossible here, with the command that proves each line, and ends with a numbered step plan for the integrator (who, disk peak, time, dependencies) and the list of steps that cannot be done here. No code, data, download, docker action or database connection.

## Depends on

- `AR-V3-BETA-MAP-TOOL-01` — completed; the decision schema and `map_pack`.
- `AR-V3-BETA-SET-TOOL-01` — completed; `promote_cli`.
- `AR-V3-BETA-PACK-INSTALL-01` — completed; `v3_pack_cli` and `AR_V3_BETA_PACK_MANIFEST`.
- `AR-V3-BETA-SPANS-MEASURE-01` — completed; the exporter and the measured spans.
- `AR-BETA-LOCAL-CUSTODY-01` — completed; the qualified local snapshot.
- `AR-NORM-MAP-APPROVAL-PREP-01` — completed; the decision sheet.

## Frozen inputs

- domain contract: unchanged
- API contract: `1.8.0`, unchanged
- analysis/comparison/event contract: unchanged
- migration head: `0035_comparison_records`, unchanged
- base commit: `9e42c18a` (`integration/ar-close-1026`)
- rulings `R-146ba` and `R-146bb` (`docs/program/OWNER_RULINGS_2026-09-17.md`); accepted risks `A-10` and `A-11`
- snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74`; frozen embedding profile `bge-m3-dense-v1`, revision `5617a9f61b028005a4858fdac845db406aefb181`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the snapshot lives only in two stopped local lanes and files under `.local/norms`; the disk cannot hold a corpus copy or the weights with the 1.2 GiB floor; three evidence PDFs answer HEAD 200; the weights header equals the Dockerfile checksum; the policy shows six of fourteen provisional items with a fetchable evidence source; repository prose and local logs disagree about the stand import

### P-01 — the verified bundle is on this host and its checksum file equals its name

- captured_at: 2026-10-27
- command: `cd /root/projects/PDF-Analysis/.local/norms/bundles/*/ && pwd | sed 's#.*/bundles/##' && sha256sum SHA256SUMS | cut -c1-64 && stat -c '%h %s' objects/71/71d29803dd45a6b3093688fb0c92a0a97f2535fecc337c65fd3bbc0c5e80255f.pdf`
- captured_output:
  ```text
  2026-07-23..2026-08-20+17d+121r.0a1bafe103ff+7792e307e39b2c1c92a852d64033b9840b48b118160768e3f02e925428815245
  7792e307e39b2c1c92a852d64033b9840b48b118160768e3f02e925428815245
  2 145486
  ```
- interpretation: the name's tail equals the digest of `SHA256SUMS`; the object has two links (hardlinked with the corpus drop), so the bundle is not a second copy on disk. It does not re-hash the 28,978 files.

### P-02 — no running database holds the snapshot; the lane stack has pgvector; the qualified lane is stopped

- captured_at: 2026-10-27
- command: `docker ps -a --format '{{.Names}}  {{.Status}}  {{.Image}}' | grep -E 'ar-close-postgres|ar-beta-custody-postgres|promotion-postgres'`
- captured_output:
  ```text
  auditmanager-ar-close-postgres-1  Up 52 minutes (healthy)  auditmanager-postgres:17.11-pgvector0.8.6-8ee86c9
  auditmanager-ar-beta-custody-postgres-1  Exited (0) 35 hours ago  auditmanager-postgres:17.11-pgvector0.8.6-8ee86c9
  auditmanager-promotion-postgres-1  Exited (255) 3 days ago  auditmanager-postgres:17.11-pgvector0.8.6-8ee86c9
  ```
- interpretation: the lane stack could hold an import functionally; the stopped custody lane (`AR-BETA-LOCAL-CUSTODY-01`) is the qualified copy. Volume sizes are in the report (1.9 GB + 5.2 GB custody, 2.6 GB promotion, 139 MB + 409 MB lane stack).

### P-03 — free disk against the import and the weights

- captured_at: 2026-10-27
- command: `df -B1 / | tail -1`
- captured_output:
  ```text
  /dev/vda3 126828056576 116829814784 3544772608  98% /
  ```
- interpretation: 3,544,772,608 bytes (3.30 GiB) are available. The import adds 7.1 to 7.6 GB; the weights (2,293,331,623 bytes) plus the venv (estimated 1.0 GB) need 4.4 to 4.9 GB free before the step to keep the 1.2 GiB floor of `R-146bb`.

### P-04 — the weights header equals the Dockerfile checksum

- captured_at: 2026-10-27
- command: `curl -sI https://huggingface.co/BAAI/bge-m3/resolve/5617a9f61b028005a4858fdac845db406aefb181/pytorch_model.bin | grep -iE '^(x-linked-size|x-linked-etag)'`
- captured_output:
  ```text
  x-linked-size: 2271145830
  x-linked-etag: "b5e0ce3470abf5ef3831aa1bd5553b486803e83251590ab7ff35a117cf6aad38"
  ```
- interpretation: `infra/norms-worker/Dockerfile` pins `sha256:b5e0ce3470abf5ef3831aa1bd5553b486803e83251590ab7ff35a117cf6aad38` for this file. Equal. Nothing was downloaded.

### P-05 — the torch wheel of the lock and its size

- captured_at: 2026-10-27
- command: `curl -sI "https://download-r2.pytorch.org/whl/cpu/torch-2.7.1%2Bcpu-cp312-cp312-manylinux_2_28_x86_64.whl" | grep -iE '^(HTTP|content-length)'`
- captured_output:
  ```text
  HTTP/2 200
  content-length: 175833687
  ```
- interpretation: the wheel's SHA-256 `8f8b3cfc53010a4b4a3c7ecb88c212e9decc4f5eeb6af75c3c803937d2d60947` is a line of `infra/norms-worker/requirements.lock` (957). With the 32 PyPI wheels (101,376,675 bytes, derived from the PyPI JSON metadata by hash) the download is 277,210,362 bytes. The installed size is not derivable and is an estimate in the report.

### P-06 — which provisional items have a fetchable evidence source

- captured_at: 2026-10-27
- command: `python3 /tmp/ar-f/evidence_map.py | tail -3`
- captured_output:
  ```text
  provisional 14 with>=1 fetchable evidence source 6 ['C01', 'C02', 'C03', 'C11', 'C19', 'C20']
  without 8 ['C04', 'C07', 'C12', 'C13', 'C14', 'C16', 'C17', 'C18']
  context_only ['C05', 'C06', 'C08', 'C09', 'C10', 'C15', 'C21', 'C22']
  ```
- interpretation: the script (source in the report, appendix) reads `beta_sources.json` and `spans.proposal.json` and joins the HEAD results of the report's section 4.2: the three PDFs that answered 200 serve six items; the `nav.tn.ru` copies answered 403.

### P-07 — repository prose and local logs disagree about the stand import

- captured_at: 2026-10-27
- command: `grep -n -i "have not run" docs/program/CURRENT_STATE.md; grep -o -E 'import: exited [0-9]+|report: full match' /root/projects/PDF-Analysis/.local/stand-import/last-status.txt`
- captured_output:
  ```text
  46:designation of a current snapshot have not run; they need an owner window.
  import: exited 0
  report: full match
  ```
- interpretation: not resolvable from this host; the report names the read-only checks that settle it on the stand.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/AR-V3-ACTIVATION-FEASIBILITY-01.md`
- `docs/program/tasks/AR-V3-ACTIVATION-FEASIBILITY-01.md`

## Forbidden hotspots

All of `src/**`, `tests/**`, `contracts/**`, `db/**`, `infra/**`, `web/**`, `scripts/**`, `docs/program/DEBT_REGISTER.md`, `docs/program/CURRENT_STATE.md`, `docs/program/OWNER_RULINGS_*.md`, the migration head, root dependency/lock files, the composition root, global styles, any corpus text in git, `origin/main`, tags, other worktrees and the lane stack. No container is started or stopped; no database is opened.

## Non-goals

No decision for any C item, no query text, no vector, no map, no set, no pack, no attestation is produced. No download of weights, wheels or documents. The stand is not touched. The report proposes; the integrator and the owner decide.

## Deliverables

- the report with the verdict table, the six sections answering the questions of `PRODUCTION-WAVE-PW5.md` section 3, the plan, the list of what cannot be done here, the limits and an appendix with the two small scripts the numbers come from;
- this task file.

## Required tests

- governance: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/AR-V3-ACTIVATION-FEASIBILITY-01.md',encoding='utf-8').read())))"` — expected `[]`.
- references: `python3 /tmp/ar-f/check_refs.py` — expected `N checked, 0 missing` (the number is in the handoff below).
- prose guards: the same pytest invocation as `AR-V3-BETA-SPANS-MEASURE-01` over `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` — expected green apart from failures present at the base (named in the handoff).
- `git diff --check` clean; exactly the two allowed paths changed.

## Integration contract

Documentation only. The integrator reads section 1 (verdicts) and section 8 (plan), settles section 2.4 at the stand, and dispatches lane AR-B with the decision file inputs of section 3. Nothing imports either file.

## Failure/idempotency/security cases

The report contains no secret, no corpus text and no signed URL (the redirect target of the weights header carries a signature and is not quoted). The lane read no `.env`. A number that could not be measured is marked as an estimate or as not measured.

## Rollback / feature flag

Not applicable: two documents. Revert the commit to remove them.

## Handoff

- changed files: the report and this task file
- commands/results: see the report; governance prints `[]`; the reference checker line and the test results are recorded in the lane's final message
- known limits: the installed size of the locked closure, the download rates, the runtime of `promote_cli plan` and the bitwise equality of the venv with the image are not measured; the stand import state is a contradiction not resolved from this host
- integration notes: merge-independent; the scratch files are in `/tmp/ar-f/` and are not part of the deliverable
