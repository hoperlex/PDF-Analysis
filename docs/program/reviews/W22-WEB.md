# W22-WEB — the caption, the status code, and three instruments that lie

**Session:** `W22-WEB`
**Branch:** `agent/w22-web`, worktree `/root/w22web`
**HEAD on arrival:** `313e753` — *docs(register): three rows from the committed journey, and D-27 measured again*
**Started:** 2026-09-19 12:43:58 UTC

## Base measurement (my own, before any edit)

`make gate` on `313e753`, lane instance `gate-w22b`, `POSTGRES_PORT=55900`,
`S3_API_PORT=59500`, `S3_CONSOLE_PORT=59501`, `POSTGRES_DB=audit_w22b`,
bucket `auditmanager-gate-w22b`:

| component  | measured                                        |
| ---------- | ----------------------------------------------- |
| battery    | 1817 passed, 5 skipped, 168 subtests, 220.82s   |
| foundation | 35 passed                                       |
| frontend   | 681 passed, 47 files                            |
| exit code  | `0` (from `$?`, not through a pipe)             |

Matches the brief's stated base exactly.

## Work in progress

This document is opened before the first edit and is committed as the work proceeds.
