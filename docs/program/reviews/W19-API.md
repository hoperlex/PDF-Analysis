# `W19-API` — `listProjects.document_count`, populated under `R-10`

**HEAD on arrival:** `653152f` (`docs: record R-7 through R-10, ruled by direct poll`), the tip
of `origin/dev`. Worktree `/root/w19api`, branch `agent/w19-api`, lane instance `gate-w19b`
(PostgreSQL 55830, S3 59430/59431, database `audit_w19b`, bucket `auditmanager-gate-w19b`).

**Authority:** `docs/program/OWNER_RULINGS_2026-09-17.md` §3.6, `R-10` — *"Ruled: populate it.
The field is already declared in the contract and simply unfilled… This ruling authorises
exactly that and nothing wider."* The alternative put to the owner, a screen calling
`listDocuments` once per project in a list, was rejected.

## 1. Where the field is produced, measured before anything changed

`listProjects` is four layers deep, and the layer that had to change is **not** the one that
serialises the field. Traced at `653152f`, top down:

| # | File | What it does with `document_count` |
|---|---|---|
| 1 | `src/auditmanager/api/routers/projects.py:60` | `list_projects` calls `projects.list_projects()`, paginates, maps each view through `project_body`. Names no field. |
| 2 | `src/auditmanager/api/schemas/projects.py:45` | `project_body` **already emits the field** — `if view.document_count is not None: body["document_count"] = …`. Correct as written. |
| 3 | `src/auditmanager/api/schemas/projects.py:42` | `ProjectView.document_count: int \| None = None` — the default that was never overridden. |
| 4 | `src/auditmanager/bootstrap/adapters.py:85` | `ProjectAdapter.list_projects` builds `ProjectView(project_uid=…, name=…, created_at=…)` — **three keyword arguments, no fourth**. |
| 5 | `src/auditmanager/ingest/service.py:168` | `IngestService.list_projects` returns `ProjectRecord`s unchanged. |
| 6 | `src/auditmanager/documents/models.py:87` | `ProjectRecord` has **three fields**. There is nowhere to put a count. |
| 7 | `src/auditmanager/documents/repository.py:61` | `_LIST_PROJECTS` = `SELECT project_uid, name, created_at FROM project ORDER BY created_at DESC, project_uid DESC` — **the reader never selects a count**. |

This is exactly the shape `W17-VIEW` reported yesterday: the serialiser at layer 2 is willing
and correct, and the value dies at layer 7, where the `SELECT` has three columns. **Changing
`project_body` or the router would have changed nothing.** The origin of the defect is
`_LIST_PROJECTS` and `ProjectRecord`; `adapters.py` is the seam that has to carry the value the
rest of the way.

**Nothing in `contracts/**` is wrong.** `components.schemas.Project` already declares
`document_count: {type: integer, minimum: 0}`, optional (not in `required`), and
`api/schemas/models.py:350` mirrors it. As `R-10` says, the field was declared and unfilled. No
reseal is engaged and no contract file is touched.

## 2. The envelope a client actually received, before

Over a real socket — `uvicorn` on `127.0.0.1:18930`, this lane's database, driven with `curl`.
Two projects: one holding two published documents, one empty.

```
$ curl -s -D- -H "Authorization: Bearer …" http://127.0.0.1:18930/projects
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 297
X-Correlation-Id: cid-1645c7d8d3cbfc72f5fa8f389ea3227d

{"items": [{"project_uid": "prj_01M2T6F96PJN4NPDQDCS1QMGE3", "name": "W19 empty project",
"created_at": "2026-09-18T12:04:46.420000Z"}, {"project_uid": "prj_01M2T6F967RKMKWQVTRVBKF18T",
"name": "W19 with two documents", "created_at": "2026-09-18T12:04:46.402261Z"}],
"page": {"next_cursor": null}}
```

**No `document_count` key on either item**, including the project whose `listDocuments` answers
two items. That is the `documents —` the ruling names.

*(Sections 3 onward are written as the work lands.)*
