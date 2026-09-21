# W25-SEAL — `R-8` reinstated, and the frontend reseal `R-13` authorises, paid

Session `W25-SEAL`. Branch `agent/w25-seal`, from `origin/dev`.

> **Opened before the first edit**, as the brief's integration contract requires. Sections
> below are filled as the work lands; nothing here is written ahead of its measurement.

## 0. Arrival

| | |
|---|---|
| HEAD on arrival | `fea3794` — *docs: R-12 through R-15 ruled by direct poll*, `origin/dev`'s tip |
| `df -h /` | **13 GB available** of 119 GB, 89% used — the brief said ~17 GB; see §7 |
| lane | `gate-w25a`, PostgreSQL **55960**, MinIO **59560/59561**, database `audit_w25a`, bucket `auditmanager-gate-w25a` |
| worktree | `/root/w25seal` |
| provisioning | `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` → `bootstrap OK`, exit 0; `npm --prefix web ci` → 184 packages, exit 0 |

The lane was new: `docker volume ls` and `docker ps -a` matched nothing on `w25`, and
55960 / 59560 / 59561 were unbound. **31500 was not touched.**

*(sections 1–7 to follow)*
