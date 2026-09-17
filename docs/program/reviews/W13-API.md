# W13-API — the twelve operations, natively under FastAPI

**Session:** `W13-API`, stage 2 of wave 13. **Branch:** `agent/w13-api`, worktree `/root/w13api`.
**Logs:** `/root/w13api-logs/`.
**Instance:** `gate-w13d`, PostgreSQL `55720`, S3 `59320`/`59321`, database `audit_w13d`,
bucket `auditmanager-gate-w13d`.

## HEAD on arrival

`cf6861cba2ad8df16a4a2fa49157d00d29c8b8f6` (`cf6861c`, `origin/dev`) — **and that was the
wrong base.** See §"Anything false in this brief", item 1. The tree this session actually
builds on is `e5861b8` (`planning/prototype-roadmap`), *merge(W13-SEAL): the contract reseal
— bearer scheme and a 21st code*, which is the first commit carrying both `W13-CONF`'s gate
and `W13-SEAL`'s reseal. `origin/dev` carries neither.

*(This file is written as the work proceeds. Sections below fill in.)*
