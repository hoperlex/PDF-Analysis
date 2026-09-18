# W20-EXEC — the run leaves the request thread, and `running` becomes a reading

**Session:** `W20-EXEC`  **Branch:** `agent/w20-exec`  **Worktree:** `/root/w20exec`
**Row:** `D-20` — the contract declares a `running` state no client can observe.

## HEAD on arrival

```
8a88fce0... merge(W19-RUN): rendering a field is not rendering a fact
```

`origin/dev` was at `8a88fce` as the brief required; nothing was stale and no stop was
needed at STEP 0.

## Base gate

Measured on this lane before the first edit, instance `gate-w20a`, PostgreSQL 55850,
MinIO 59450/59451, database `audit_w20a`, bucket `auditmanager-gate-w20a`:

```
1785 passed, 5 skipped, 1 warning, 168 subtests passed in 220.32s
35 passed (foundation)
Test Files  47 passed (47)   Tests  681 passed (681)
GATE OK
GATE_BASE_EXIT=0
```

Identical to the figures the brief carries.

*(The rest of this review is written as the work lands.)*
