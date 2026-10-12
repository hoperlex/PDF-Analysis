# W54-JUDGE-Y — lineage, identities, ALR-05, locks, migrations versus code (static)

**Reviewer:** a fresh-context subagent of the integrator `pdf-analysis-62`, 2026-10-12.
**Subject:** `integration/w54` @ `146bff9` (base `7ebf162`).
**Mode:** static review only.

**Verdict: ACCEPT-WITH-FIXES.** No blocker was found.

## Traced and holding

- **Keys and digests.** The D-126 key composition (base → repair → `+seg-`), with the Python and shell grammars agreeing. One row-digest class at export, import and report, under `COLLATE "C"` order. `norm-embedding-set/2` binds the rebuilt chunk text. The binding digest uses no private ids.
- **Identities.** `nad`, `nbd`, `nrc` and `wrk` are fresh ULIDs. Import preserves `ns`, `ndoc` and `npar`.
- **ALR-05.** Cross-context access goes through `*.public` only, and job state stays durable.
- **Lock orders.** Worker claim, reclaim, custody, `publish_bindings`, the repair journal and the executor journal all take locks in a consistent order.
- **D-141.** The commit comes before the evidence gate.
- **Migrations.** Every column and guard transition in 0018/0019 matches the code, including the D-150 update.

## Findings

| # | Severity | Finding | Where | Fix |
| --- | --- | --- | --- | --- |
| F1 | Major | Nothing checks that the promoted rows came from the drop and ledger the bundle names. Export never recomputes the base or repaired key from the rows plus `results.md`. A ledger's `crop_sha256` is never compared with the bundled crops. The importer checks only the `+seg-` suffix. A bundle can therefore pair drop A's text with drop B's PDFs and ledger L2, and still report a full match. | `norms/bundle/export.py:337-373, 450-462`, `norms/repository.py:298-365`, `norms/bundle/stand.py:189-196` | Recompute the base and repaired keys in `write_bundle` and require equality. Require each `crop_sha256` to equal the bundled crop. Check the key's terms against the row's counts and `content_digest` in `validate_snapshot_rows`. |
| F2 | Minor | The manifest's `SnapshotFacts` are never compared with the imported rows. | `bundle/stand.py:189-196`, `bundle/manifest.py:594-598` | Require `manifest.snapshot` to equal `rows.snapshot`. |
| F3 | Minor | `SHA256SUMS` is parsed two ways: the repair parser accepts only lowercase hex and keeps the last duplicate, while the export parser refuses duplicates. The repair run does not record which sums file it checked. | `norms/__main__.py:114,182-213`, `bundle/export.py:285-312` | Use one parser. Record the sums SHA-256 in the journal header and the ledger, and compare it at export. |
| F4 | Minor | `machine="norm_custody_admission"` and `"norm_custody_binding"` are undeclared in `state-machines.json` (precedent: `analysis_artifact_publication`). | `custody/service.py:250,538,550`, `ingest/reconciliation.py:603` | Declare them at the next contract reseal (register row). |
| F5 | Minor, pre-existing | The audit_run row lock is held across the gate's S3 reads. | `runs/executor.py:856` | Read the gate's artifacts before the `advance`. |

## Needs the window

1. D-141 heartbeat during a slow gate.
2. The 0018 guards on the real sequences (requeue reset, the fifth-try poison, `prepared → abandoned`, D-150).
3. The fingerprint stays unchanged by an import, and `report` gives a full match on import, replay and discard.
4. The stored row and build digests are equal across two databases.
5. Old `norm-embedding-set/1` build rows anywhere.
6. Worker `FOR SHARE` against the registry heartbeat under a real process, and LISTEN loss.
7. `ck_norms_snapshot_raw_key` accepts repaired and `+seg-` keys.
