# `W5-CERT` — PC-01 re-certification (in progress)

Session `W5-CERT`. Started 2026-09-15T13:48Z. Base `beaa7f7` on `planning/prototype-roadmap`
(= `origin/dev`). Working branch `agent/w5-cert`, worktree `/root/w5cert`.

**HEAD on arrival: `beaa7f7`** — not `origin/main` (`6d3c0f3`, the parked PC-01 commit) and
not the brief's stated base `ef5b8bf`. `git diff ef5b8bf..beaa7f7 --stat` touches only
`docs/program/dispatch/W5-ADV.md` and `docs/program/dispatch/W5-CERT.md` (15 insertions,
11 deletions), which is the brief's own "harmless, carry on" case. Certification therefore
reports against `beaa7f7`; `src/`, `db/`, `tests/` and `contracts/` are byte-identical to
`ef5b8bf`.

## Environment

Instance `gate-w5`, `POSTGRES_PORT=55560`, `S3_API_PORT=59160`, `S3_CONSOLE_PORT=59161`,
`POSTGRES_DB=audit_w5`, bucket `auditmanager-gate-w5`. All three ports confirmed free before
`make up`. `.env` copied from `.env.example` and set to exactly this instance.
`.env.provider` is git-ignored and does **not** propagate into a new worktree; copied in
from the primary worktree, mode 600.

## Commands so far

| Command | Exit | Observed |
|---|---|---|
| `git rev-parse HEAD` | 0 | `beaa7f7` |
| `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` | 0 | `bootstrap OK` |
| `make bootstrap …` (second, deliberate) | 0 | `bootstrap OK`, `git status --porcelain` empty |
| `make up` | 0 | postgres, s3, s3-init all healthy |
| `make foundation` | 0 | 3 `FOUNDATION-CHECK OK` sentinels; 35 passed |
| `python -m auditmanager.api.app` | 0 | `wired, provider_mode=proxy`, `operations=12` |
| same, `DATABASE_URL` unset | 2 | refusal naming `DATABASE_URL` |
| same, `PROXY_LLM_TOKEN` unset | 2 | refusal naming `PROXY_LLM_TOKEN` |
| `pytest tests --ignore=tests/contract --ignore=tests/checkpoint` | 0 | **793 passed, 5 skipped, 116 subtests** |
| `git diff --check` | 0 | clean |
| `pytest tests/e2e/pc01` (recorded) | 0 | **49 passed, 5 skipped** |

Gate matches the brief exactly.
