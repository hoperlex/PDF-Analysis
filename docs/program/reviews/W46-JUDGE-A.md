# W46-JUDGE-A — the merged tip `130200d`, sub-stage A of wave 46

**Judge:** `W46-JUDGE-A` (relaunch; the first run died on a host restart before it committed
anything) · **lane:** `gate-w46j` (PostgreSQL `127.0.0.1:56390`, S3 `59990`/`59991`) ·
**worktree:** `/root/w46j` · **branch:** `agent/w46-judge` · **tree judged:** `130200d`.

This file is committed as it is written. A section marked *in progress* is not a conclusion.

## 0. Provisioning

```
make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12   -> bootstrap OK
.venv/bin/python -c "import boto3"                     -> boto3 ok
npm --prefix web ci                                    -> added 184 packages
```

## 1. Does the merged tree gate? — *in progress*

## 2. `web/FRONTEND_LOCK.json` — recomputed or carried? — *in progress*

## 3. `getDashboardSummary`, driven — *in progress*

## 4. `/dashboard` at 780 px, both palettes; the `SEEDS` and cache-state edits — *in progress*

## 5. Can the per-section panel be made to show an invented number? — *in progress*

## 6. Off the trail — *in progress*
