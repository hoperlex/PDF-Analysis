# `W12-CERT` — re-certification of PC-01 after waves 11 and 12

Session `W12-CERT`, wave 12 stage B. Worktree `/root/w12cert`, branch `agent/w12-cert`,
logs `/root/w12cert-logs/`, instance `gate-w12b` (55660 / 59260 / 59261, `audit_w12b`,
`auditmanager-gate-w12b`).

**`HEAD` on arrival: `e6eae1e1a8a5a7c7bca8075ab9511e9c75a2d6f2`** — `merge: stage B's brief,
with the real base`, the tip of `origin/dev`. The dispatch names base `2be71b9`; `e6eae1e`
is two commits later on the same line (`3f49385` and the merge `e6eae1e`, both docs-only).

**Started: 2026-09-17T12:31:24+05:00.**

Status: in progress.

---

## 0. Command log

| # | command | exit |
|---|---|---|
| 1 | `git worktree add /root/w12cert -b agent/w12-cert origin/dev` | 0 |
| 2 | `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` | 0 (`bootstrap OK`) |
| 3 | `npm --prefix web ci` | 0 (184 packages) |
| 4 | `make gate` (arrival, `e6eae1e`) | 0 — `GATE OK` |

## 1. The gate at arrival

| component | expected by the brief | measured at `e6eae1e` |
|---|---|---|
| foundation | 35 | **35 passed** in 28.40 s, three `FOUNDATION-CHECK OK` sentinels |
| battery | 1505 passed / 5 skipped / 167 subtests | **1505 passed, 5 skipped, 167 subtests** in 182.38 s |
| frontend | 440 passed | **440 passed / 35 files** in 3.27 s |
| whitespace | — | clean |

`GATE OK`, exit 0. Log: `/root/w12cert-logs/gate-arrival.log`. Every figure the brief
quotes is exact.

## 2. The surface since `c0d7daf`, checked rather than taken

`git diff --stat c0d7daf..HEAD -- src/ db/` → **9 files, 232 insertions, 33 deletions**
(exit 0). `DEBT_REGISTER.md` D-1 says 8 files / 126 lines; it was measured at `5c84f43`,
before `ingest/reconciliation.py` moved in stage A, and the ninth file is that one. Not a
false premise — a figure that predates the stream it does not include.

Every row of the brief's table was read as a diff, not taken:

| File | Brief says | Verdict |
|---|---|---|
| `exports/service.py` | `CsvExport.filename` and `_FILENAME_TEMPLATE` removed | **true** — the `@property` and the module constant are both gone, `Final` no longer imported |
| `ingest/service.py` | `read_source_bytes` hashes returned bytes against the manifest digest | **true** — `sha256_of(data) != entry.sha256` → `STORAGE_INTEGRITY_ERROR` |
| `storage/s3.py` | `read(verify=True)` refuses an object with no recorded digest | **true** — `recorded is None` → `BlobMetadataInvalidError`; the old guard was `recorded is not None and recorded != actual` |
| `analysis/text/stage.py` | `cost_basis` added to the success path's metrics | **true** — added beside `cost_usd` in the success metrics dict |
| `ingest/reconciliation.py` | `verify_version` hashes bytes, after a declaration check, with an unstamped object refused first | **true** — three ordered questions, exactly as described |
| `shared/errors/envelope.py` | docstring only, six shapes named | **true** — docstring only |
| `multipart.py`, `projects.py`, `executor.py` | comments only, zero code lines | **true** — every changed line in all three is a comment |
