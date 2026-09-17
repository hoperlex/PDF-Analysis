# W16-ERR — three error mappings that told a caller something untrue

**Session** `W16-ERR`. **Worktree** `/root/w16err`, branch `agent/w16-err` off `origin/dev`.
**HEAD on arrival** `315de25` — *"merge: the clean-lane breaker, and the two infra lines
W15-AUTH stopped at"*. **Started** 2026-09-17T23:03Z. Disk at start: `/` 89% used, 13G free.

## 0 — the settled shape, confirmed before anything was touched

The brief asserts that `dependency_credential_refused` — the 21st code, owner ruling `R-3`,
settling `D-7` — already exists everywhere and that nothing this wave needs a catalog change.
**Confirmed, measured, not assumed:**

| where | measurement |
| --- | --- |
| catalog | `contracts/domain/v1/error-codes.json` — 21 codes; `dependency_credential_refused` = `http` 500, `retryable` false, category `dependency`, `safe_detail_keys` exactly `["dependency"]` |
| revision note | round 6 carries `R-3` of 2026-09-17 and names `D-7`; `status: draft_candidate`, `frozen: false` |
| envelope schema | `contracts/domain/v1/error-envelope.schema.json:35`, `:353` |
| enum | `src/auditmanager/shared/errors/codes.py:32`; `src/auditmanager/api/schemas/models.py:235` |
| OpenAPI | `contracts/api/v1/openapi.json:1206` (and the 403/500 prose at `:930`, `:1050`) |
| migration | `db/migrations/versions/20260910_0002_pc01_schema.py:88` |
| storage | `src/auditmanager/storage/errors.py:167` — `StorageCredentialRefusedError.code` |

So no reseal, no owner decision, no `contracts/` byte is needed. **`contracts/` was not touched.**

Command used: `python3 -c "import json; d=json.load(open('contracts/domain/v1/error-codes.json')); print(len(d['codes']))"` → `21`.

