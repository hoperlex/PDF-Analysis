# `W22-OPS` — the wipe rehearsal tells the truth, and the stack can be asked whether it is the tree

## 0. Arrival

| | |
|---|---|
| Base | `origin/dev` = `313e753` *(docs(register): three rows from the committed journey, and D-27 measured again)* |
| Worktree | `/root/w22ops`, branch `agent/w22-ops` |
| Lane | instance `gate-w22a`, PostgreSQL `55890`, S3 `59490`/`59491`, database `audit_w22a`, bucket `auditmanager-gate-w22a` |
| Disk on arrival | `df -h /` — 119G total, 98G used, **15G available**, 87% |
| Started | 2026-09-19 17:43:26 +05 |

### The gate at base, measured on this lane

```
make gate                                   # exit 0, from $?
  foundation   35 passed                    (twice: check-db, check-storage)
  battery      1817 passed, 5 skipped, 168 subtests passed in 220.82s
  frontend     47 files, 681 tests passed
```

Identical to the figures the brief carries. Nothing to report at base.

*(sections below are filled as the work lands)*
