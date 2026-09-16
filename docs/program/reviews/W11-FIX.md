# `W11-FIX` review record

Session `W11-FIX`, wave 11. Worktree `/root/w11fix`, branch `agent/w11-fix`.

**HEAD on arrival: `5d14921388a892f325520f9784708ca3598aaeab`** — `docs: the wave 11
dispatch — repair what wave 10 found`, the tip of `origin/dev`. The brief said "base
`30d129c` or later"; `5d14921` is one commit later and is that tip.

Started 2026-09-16T19:30:07+05:00. Logs in `/root/w11fix-logs/` (session-unique).
Instance `gate-w11b`: `POSTGRES_PORT=55640`, `S3_API_PORT=59240`,
`S3_CONSOLE_PORT=59241`, `POSTGRES_DB=audit_w11b`, bucket `auditmanager-gate-w11b`.

This file is appended to as the work proceeds, not written at the end.

---

## 1. Premises checked against the tree before any edit

Every premise in the brief was re-derived from the tree. Results below; the two that
were wrong are in §6.

### Defect 1 — two comments false in the dangerous direction — **CONFIRMED**

`src/auditmanager/api/routers/multipart.py:96` and
`src/auditmanager/api/schemas/projects.py:53` both say `details` values "are not
screened the way `message` is". `shared/errors/envelope.py:build` does screen them: a
string detail value is run through the same `_FORBIDDEN` tuple as a message and raises
`UnsafeDetailValue`. The screen is at `envelope.py:137-146`.

### Defect 2 — docstring undercounts the screen — **CONFIRMED, and the count is six**

Counted in the `_FORBIDDEN` tuple at `envelope.py:30-46`, not taken from the brief:

1. `a URL`, 2. `a filesystem path`, 3. `an S3-style object key`, 4. `a credential`,
5. `SQL`, 6. `a stack frame`. **Six.**

The module docstring says "paths, URLs, credentials, SQL, stack frames" — five, omitting
the S3-style object key. The brief's own account of its wave-10 predecessor saying
"seven" is therefore also confirmed as having been wrong.

### Defect 3 — `cost_basis` asymmetric — **CONFIRMED**

`analysis/text/stage.py`: the budget-overrun branch sets `"cost_basis"` in its metrics
(line 277); the success-path `metrics` dict (line 312) does not. Four returns share that
dict — truncated-with-no-observations, artifact-build failure, partial, and succeeded —
so all four lack it. `_record(..., cost_basis=...)` at line 300 does set it on the
`ModelCallRecord` for both paths, so the ledger row is fine and only the stage metrics
are asymmetric, exactly as stated.

`contracts/analysis/v1/stage-result.schema.json` admits
`number|integer|string|boolean|null` under `metrics`, so a string `cost_basis` conforms.

### Defect 4 — filename property with no consumer — **CONFIRMED (name in brief is wrong)**

`exports/service.py:30` defines `_FILENAME_TEMPLATE = "audit_run_{run_id}.csv"` and a
`filename` property at line 43. A repository-wide search for `.filename`,
`_FILENAME_TEMPLATE` and `ExportResult` finds no reader of either outside their own
definition. The sibling `byte_size` property on the same class **is** read
(`tests/integration/runs/test_corpus_measurement.py:67,75`), which is what makes the dead
one easy to miss.

The contract claim holds: `web/openapi/openapi.json`, `GET /runs/{run_id}/export.csv`,
200 response, header `Content-Disposition` — "Attachment with a display file name built
from opaque identifiers. The file name is presentation only and is never an identity."
No `enum`, no `pattern`, no `example`; schema is bare `{"type": "string"}`. The header
(`api/routers/export.py:_disposition` → `{run_id}.csv`) and the UI
(`web/src/shared/api/csv-columns.ts:csvFileName` → `{runId}-findings.csv`) differing is
permitted, and the UI already says so in its own docstring: "The server's
`Content-Disposition` wins if it sends one."
