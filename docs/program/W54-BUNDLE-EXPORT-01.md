# W54-BUNDLE-EXPORT-01 — the promotion bundle of the repaired snapshot

**Date:** 2026-10-20. **Base:** `origin/dev` `f942ca1ce0dff227c85b74a90e6de2faa989046e`.
**Task:** `tasks/W54-BUNDLE-EXPORT-01.md`.

## Result

The bundle was exported and verified.

| Field | Value |
| --- | --- |
| bundle directory | `/root/projects/PDF-Analysis/.local/norms/bundles/2026-07-23..2026-08-20+17d+121r.0a1bafe103ff+7792e307e39b2c1c92a852d64033b9840b48b118160768e3f02e925428815245` |
| content key | `2026-07-23..2026-08-20+17d+121r.0a1bafe103ff` |
| bundle digest (SHA-256 of `SHA256SUMS`) | `7792e307e39b2c1c92a852d64033b9840b48b118160768e3f02e925428815245` |
| `manifest.json` SHA-256 | `cc0f5ee80ef4b2be43ff41789930ed8e5d14056cdfa6101f97ef582f138f21cf` |
| format / manifest version | `auditmanager-norm-bundle/1` / 1 |
| row digest | `a3111764c9fb01796444880a979fa50530948f93d9fedde194cecb3c873ff7ac` (`norm-snapshot-rows/1`) |
| build | present: 55,855 chunks, `bge-m3-dense-v1`, `norm-embedding-set/2`, `e7fac64c90b96381ceeb41d2707c222d1ba81240ff8b4eff47fecb3293ffc5df` |
| counts | 674 documents, 350,194 paragraphs (0 unreliable), 55,855 chunks, 61,573 windows, 28,920 objects (5,055,102,708 bytes), 28,920 custody slots |
| binding digest | `d2de2a610b340d447e5cb86311823b0bab106969ec9f933b7c88c7a475398485` |
| `db_growth_bytes` | 1,352,054,572 (method `proportional-relation-size-v1`) |
| `min_migration_head` | `0018_norm_custody` |
| ledger carried | the 121 applied repairs of `ledger.json` (`9639ce91…`) |
| `bundle verify` | exit 0, 28,979 files, every byte re-hashed (8 s) |

The row digest and the build digest equal those the loader and `embedding load` reported, so the
bundle carries the rows and vectors that are in the verified dump. Command (from the
repository root, `PYTHONPATH=src`, the lock-matched interpreter):

```
python -m auditmanager.norms.bundle export --snapshot ns_01M59N8QNBVN91ACA2HCE6VE74 \
  --chunking-profile characters-v2:1200 --corpus <abs drop> \
  --drop-sums <abs corpus-sums/2026-10-15/SHA256SUMS> --ledger <abs ledger.json> \
  --out <abs .local/norms/bundles>
python -m auditmanager.norms.bundle verify <bundle directory>
```

## Footprint

The 28,920 objects are hardlinks into the drop: no regular file under `objects/` has a link
count of 1. Free disk fell from 13.31 GiB to 12.79 GiB over the export, about 0.5 GB, not the
5.3 GB that `du` reports for the directory. Do not delete the drop's PDFs or crops while the
bundle is needed as a standalone copy; deleting the bundle does not touch the drop.

## Resources, measured

The export ran in the background 19:53-19:54 UTC with the promotion database up (mem limit
1 GiB), the host quiet (load 0.6-3.4, 7.5 GiB RAM available) and 13.3 GiB of disk free; it
took about one minute. The verify took 8 s with the files in the page cache. The promotion
database is stopped at the end of the task, and the volume and the latest verified dump
are kept as the recovery artifacts.

## Limits and risks

- Nothing was imported, copied to a stand or reported. `min_migration_head` is
  `0018_norm_custody`; the promotion database is at `0023_norm_citations`. Whether the deployed
  stand's head and SHA admit this bundle is the compatibility evidence `W55-PLAN.md` §A7
  asks for first, and it is not collected here.
- `verify` proves the bundle is internally consistent and equals its manifest. It does not
  prove the vectors are good retrieval vectors; that is a W55 measurement.
- The bundle is the only standalone copy of the repaired rows outside the database dumps; the
  drop and the dump remain its sources.

## Integrator instruction

Merge the two documentation files. The owner names the bundle key and digest above for the
stand import, a separate production operation in its own window; this task makes no request
for `origin/main`.
