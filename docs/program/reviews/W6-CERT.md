# `W6-CERT` — PC-01 re-certification after wave 6

**Status: IN PROGRESS.** This file is committed incrementally, per dispatch rule 1.

- `HEAD` on arrival (main checkout `/root/projects/PDF-Analysis`): `04848450a84d0752d075e021a26fd7894558e4cf`
  on `planning/prototype-roadmap`. That is base `c0d7daf` plus this session's own dispatch
  commit; `git diff c0d7daf..HEAD --stat` touches only `docs/program/dispatch/W6-CERT.md`,
  which the brief names as harmless.
- Worktree: `/root/w6cert`, branch `agent/w6-cert`, from `0484845`.
- Instance `gate-w6`, POSTGRES_PORT 55580, S3_API_PORT 59180, S3_CONSOLE_PORT 59181,
  POSTGRES_DB `audit_w6`, bucket `auditmanager-gate-w6`.

## Commands so far

| Command | Exit |
|---|---|
| `git rev-parse HEAD` | 0 |
| `git worktree add /root/w6cert -b agent/w6-cert 0484845` | 0 |
| `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` (first) | 0 |
| `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` (second) | 0 |
| `git status --porcelain` after both bootstraps | 0, empty |
| `make up` | 0 |
| `make foundation` | 0 — three `FOUNDATION-CHECK OK`, 35 passed |
| `alembic current` | 0 — `0005_truncated_call_status (head)` |
| `alembic downgrade -1` then `make check-db` | 2 — `FOUNDATION-CHECK FAIL check-db` (criterion 2 red) |
| `make migrate` then `make check-db` | 0 — head restored, `FOUNDATION-CHECK OK` |
| `pytest -q tests --ignore=tests/contract --ignore=tests/checkpoint` | 0 — **803 passed, 5 skipped, 116 subtests** |
| `git diff --check` | 0 |
| `PYTHONPATH=src .venv/bin/python -m auditmanager.api.app` | 0 — `wired, provider_mode=proxy`, `operations=12` |
| same with `DATABASE_URL` unset | **2** — names `DATABASE_URL` |
| same with `S3_BUCKET` unset | **2** — names `S3_BUCKET` |
| `pytest -q tests/e2e/pc01` (recorded) | 0 — 49 passed, 5 skipped |
| `C2_PC01_LIVE=1 pytest -q tests/e2e/pc01/test_live_text_analysis.py` | 0 — 5 passed |

Recorded-adapter corpus run reports: state `published`, degradation set empty, four stages
`succeeded`, 3 findings, 0 ungrounded diagnostics, CSV 5 rows / 17 columns / 4251 bytes —
identical to the accepted record.
