# `W10-RUN` — mutation sweep of `runs/`, `ingest/` and the migrations

Session `W10-RUN`, wave 10. Worktree `/root/w10run`, branch `agent/w10-run`,
instance `gate-w10d`.

## Provisioning

- **HEAD on arrival: `e08da85`** ("docs: the wave 10 dispatch — five parallel sweeps of
  the rule surface"), branch `agent/w10-run`, tree clean. The brief names base `fb30e96`;
  `e08da85` is one commit *later* on the same line (`fb30e96` is its parent), so the base
  premise holds with that correction.
- Worktree was already bootstrapped by the killed first attempt: `.venv/` present,
  `web/node_modules/` present, `.env` present and carrying exactly instance `gate-w10d`
  (`POSTGRES_PORT=55620`, `S3_API_PORT=59220`, `S3_CONSOLE_PORT=59221`,
  `POSTGRES_DB=audit_w10d`, `S3_BUCKET=auditmanager-gate-w10d`).

## Sweep table

_(appended as batches complete)_
