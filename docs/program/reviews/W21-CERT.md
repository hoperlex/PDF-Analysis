# W21-CERT — PA-01, criterion by criterion, measured

**Session** `W21-CERT` · **branch** `agent/w21-cert` · **worktree** `/root/w21cert`
**HEAD on arrival** `0f9989a` — the tip of `origin/dev`, exactly the commit the brief names.
**Gate lane** `gate-w21a` — PostgreSQL 55870, S3 59470/59471, database `audit_w21a`,
bucket `auditmanager-gate-w21a`.
**`df -h /` on arrival** 6.8 GB free of 119 G (94 % used).

*This document is written as the work lands. It is committed before each measurement so that
a session that dies mid-wave loses nothing.*

## Status

In progress.

## Progress log (written as measurements land; the verdicts and evidence are below)

- base gate measured at `0f9989a`: battery 1806 / 5 skipped / 168 subtests, foundation 35,
  frontend 681 (47 files), `GATE_BASE_EXIT=0`. Log `/root/w21cert-logs/gate-base.log`.
- criterion 1: `infra/deploy/deploy.sh` does not exist in the tree. Conformance over HTTP
  against the running process: 0 differences, planted difference reddens.
- criterion 2: 15/15 operations answer `401 authentication_required` from the application
  with no credential; `/healthz` 200 without one.
- criteria 3–7 driven in a real browser: project, upload, live run (`running` → `published`),
  finding at its quotation, accept/reject/comment history, CSV with BOM and CRLF.
- criterion 9: five refusals, five distinct constraints, nothing left behind; a provider
  outage terminates the run `failed` / `dependency_unavailable` and publishes nothing.
- criterion 8: census of every table, run, version, decision and object identical across a
  restart of PostgreSQL, MinIO, the API process and the web process; every screen loads
  cold afterwards in a fresh browser.
