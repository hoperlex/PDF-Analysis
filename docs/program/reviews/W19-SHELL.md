# W19-SHELL — the screens half of `D-16`: routes a fresh tab can render

**Session** `W19-SHELL`. **Branch** `agent/w19-shell`, worktree `/root/w19shell`.
**HEAD on arrival** `653152f` — *docs: record R-7 through R-10, ruled by direct poll*,
the tip of `origin/dev` at provisioning.
**Gate lane** `gate-w19a` — PostgreSQL 55820, S3 59420/59421, database `audit_w19a`,
bucket `auditmanager-gate-w19a`. **Logs** `/root/w19shell-logs/`.
**`df -h /` on arrival:** 11 GB free of 119 G (91 % used).

*This document is written as the work lands. Sections below are filled in order.*

## 1. The defect, restated from the measurement

`W15-RUN` §6 `W15RUN-3`, measured in a real browser against the deployed stack: a project
page on a fresh load makes **zero** API calls and says *"No version published in this
session"*. `W18-SEAL` closed the contract half under `R-5`; `DEBT_REGISTER.md` **D-16**
records the remaining half as *"`web/src/app/**` is untouched … no screen renders them"*.

