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

## 3. What it counts, and why that is the only number it may be

**It counts the documents `listDocuments` would return for that project.** Not `document`
rows.

`W18-SEAL` wrote `_LIST_DOCUMENTS` as an INNER JOIN on the current version:

```sql
FROM document d JOIN document_version v ON v.version_uid = d.current_version_uid
```

so **a document whose `current_version_uid` is `NULL` is not listed**, and
`test_a_document_with_no_published_version_is_not_listed` is that assertion. A
`document_count` that counted `document` rows would therefore put "3 documents" above a list
of two — a number with nothing behind it, on a screen `W19-SHELL` is building right now.

So the count is not a second definition of "a document in this project" that has to be kept
in step with the first. **It is the same join, with the rows counted instead of returned:**

```sql
SELECT p.project_uid, p.name, p.created_at, count(v.version_uid) AS document_count
FROM project p
LEFT JOIN document d ON d.project_uid = p.project_uid
LEFT JOIN document_version v ON v.version_uid = d.current_version_uid
GROUP BY p.project_uid, p.name, p.created_at
ORDER BY p.created_at DESC, p.project_uid DESC
```

Read out of the running code, not retyped:
`.venv/bin/python -c "from auditmanager.documents.repository import _LIST_PROJECTS; print(_LIST_PROJECTS)"`.

Four decisions in it, each of which could have been the defect:

* **`LEFT JOIN`, twice.** An inner join would drop a project with no documents out of the
  listing altogether — the page would be short by exactly the projects a user most needs to
  see.
* **`count(v.version_uid)`, not `count(*)`.** `count(*)` over the outer-joined `NULL` row
  reports **1** for an empty project. `count` of a column ignores `NULL`s, so an empty
  project reports **0**.
* **`GROUP BY p.project_uid, p.name, p.created_at`** — legal on the primary key alone in
  PostgreSQL; the other two are named for a reader rather than for the planner.
* **No row multiplication.** `document_version.version_uid` is the primary key, so each
  `document` row joins at most one version row. The count is a count of documents.

**Is the unversioned document reachable?** Not through the surface today:
`IngestService._commit_publication` creates the document and publishes its first version in
one transaction, so a failure rolls both back. It is reachable in the *schema* —
`current_version_uid` is `text NULL` — and the composite foreign key
`(document_uid, current_version_uid) → document_version(document_uid, version_uid)` is not
enforced when the column is `NULL`. `D-17` also says the restore path is not yet sound for
writing. A listing has to be right where the schema allows a row, not only where today's
happy path puts one, so both tests manufacture that row and assert the two operations still
agree.

**What `document_count` is *not*, and this is deliberate:** `createProject`'s body is
unchanged. It reads no documents and claims no count, `ProjectView.document_count` stays
`None` there, and `project_body` still omits the field. That keeps record 01 where it is and
keeps `R-10` to "exactly that and nothing wider". `ProjectView`'s `None` now means "this path
did not count", which is the claim it was always meant to make, rather than "nobody has
implemented this".

## 4. One statement, not N — measured at the driver

The claim is about what reaches the database, so it is asserted there and not by reading the
source for a `for` loop:
`test_the_whole_listing_costs_one_statement_however_many_projects` registers a
`before_cursor_execute` listener on the shared `Engine`, lists **five** projects with
documents spread unevenly over them, and requires exactly one `SELECT`, containing `count(`.

Over the socket, the same property at 32 projects: one `GET /projects` returned every project
with its own count, from the one statement above. A per-project count would have been 33
round trips.

That guard is not decorative — mutation **D** below replaces the query with a perfectly
*correct* per-project loop, and this is the only test in the wave that notices.

## 5. Every change, shown able to fail

`make mutation-copy MUT=/root/w19api-mut`, run from the worktree with
`-o pythonpath=/root/w19api-mut/src` so the tests are the worktree's and the module under
mutation is the copy's. **Baselined green first: 85 passed, exit 0.** Six mutations, each
applied alone and reverted before the next; `diff` confirms the copy's sources are identical
to the worktree's afterwards.

| # | Mutation | Result | The test that reddened |
|---|---|---|---|
| **A** | every project reports the whole database — `ON d.project_uid = p.project_uid` → `ON true` | 4 failed, 50 errors | `test_each_project_counts_its_own_documents_and_not_its_neighbours`, `test_the_whole_listing_costs_one_statement_however_many_projects`, `test_document_count_is_the_length_of_the_list_it_sits_above`, `test_a_project_holding_nothing_reports_zero_on_the_wire_and_not_nothing` |
| **B** | the count includes documents `listDocuments` will not show — `count(v.version_uid)` → `count(d.document_uid)` | 2 failed | `test_the_count_is_exactly_what_list_documents_returns`, `test_document_count_is_the_length_of_the_list_it_sits_above` |
| **C** | zero becomes absent — `document_count=r.document_count` → `… or None` | **1 failed** | `test_a_project_holding_nothing_reports_zero_on_the_wire_and_not_nothing` |
| **D** | one query becomes one per project — the repository body replaced with a *correct* loop issuing `SELECT count(*) … WHERE d.project_uid = :p` per project | 1 failed | `test_the_whole_listing_costs_one_statement_however_many_projects` |
| **E** | the field drops off the wire again — the fourth keyword argument deleted from the shipped adapter | 2 failed, 50 errors | the two wire tests, and the journey's own `R-10` assertion |
| **F** | the parent is wrong, so every count is zero — `ON d.project_uid = p.project_uid` → `ON d.document_uid = p.project_uid` | 4 failed | the three ingest tests and `test_document_count_is_the_length_of_the_list_it_sits_above` |

**The 50 "errors" under A, E and F are not collection damage.** They are the whole
characterization suite failing at its session-scoped `exchanges` fixture, because
`run_journey` now asserts at case 16 that the item carries the field:

```
tests/characterization/w13_baseline/journey.py:1284: in run_journey
    assert "document_count" in listing["items"][0], (
E   AssertionError: the project page carries no `document_count`; the field is
    declared by the sealed `Project` and R-10 ruled that it is filled
```

### 5.1 A guard that reddened nothing, and what was done about it

**Mutation C passed on the first run.** `document_count=r.document_count or None` —
one word, and precisely the slip that `int | None` invites — turned an honest `0` into an
omitted field, and **the whole of the rest of this wave's evidence stayed green**:

* the service-layer zero test asserts on `ProjectListingRecord`, which is *upstream* of the
  adapter that was mutated;
* both wire-level projects in the agreement test hold documents, so neither is a zero;
* the characterization record's project holds **one** document, so the record did not move.

That is `D-3`'s shape exactly — the flattering default is invisible until somebody has
nothing. A guard that reddens nothing is a finding, so it is closed rather than reported:
`test_a_project_holding_nothing_reports_zero_on_the_wire_and_not_nothing` (`6dd39b3`) asserts
at the wire that an empty project carries the **key** and the **value `0`**, and that its
`listDocuments` page really is empty so the assertion is not vacuous. Re-run: mutation C
fails, and the full set is six mutations, six reds.

## 6. The envelope over a real socket, after

`uvicorn --factory auditmanager.api.app:create_asgi_app` on `127.0.0.1:18930`, this lane's
PostgreSQL and MinIO, driven with `curl`. Same two projects as section 2.

```
$ curl -s -D- -H "Authorization: Bearer …" http://127.0.0.1:18930/projects
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 339
X-Correlation-Id: cid-dbcebe03ee0b783c2cfd1113d2aeeb57

{"items": [{"project_uid": "prj_01M2T6F96PJN4NPDQDCS1QMGE3", "name": "W19 empty project",
"created_at": "2026-09-18T12:04:46.420000Z", "document_count": 0},
{"project_uid": "prj_01M2T6F967RKMKWQVTRVBKF18T", "name": "W19 with two documents",
"created_at": "2026-09-18T12:04:46.402261Z", "document_count": 2}],
"page": {"next_cursor": null}}
```

297 bytes to 339. And the number is the list, checked over the same socket:

```
$ curl -s …/projects/prj_01M2T6F967RKMKWQVTRVBKF18T/documents | jq '.items | length'
2
$ curl -s …/projects/prj_01M2T6F96PJN4NPDQDCS1QMGE3/documents | jq '.items | length'
0
```

The empty project answers **`0`**, not a missing key.

## 7. The characterization record and its exception block

`make`'s capture rewrites all 36 records. It was re-run once, deliberately, and
**`git diff --stat` over `records/` is one file**:

```
 .../records/16-listProjects.success.json | 19 +++++++++++++++----
 1 file changed, 15 insertions(+), 4 deletions(-)
```

The body moved by exactly one property and the length that follows from it:

```
-      "length": 215,
-      "text": "{\"items\": [{… \"created_at\": \"{{ts_4}}\"}], \"page\": …}"
+      "length": 236,
+      "text": "{\"items\": [{… \"created_at\": \"{{ts_4}}\", \"document_count\": 1}], \"page\": …}"
```

`exception` moved from `null` to `EXCEPTION_W19API` (`journey.py`), on the form of
`EXCEPTION_D7` and `EXCEPTION_W18SEAL`: `debt: ["D-16"]` as a **list**, `status: "taken"`,
`decided_by: "1bb15ae"` with its subject and date, a `permitted_change` that describes the
whole of the move, and `everything_else` verbatim. The `ruling` cites
`OWNER_RULINGS_2026-09-17.md section 3.6, R-10` — the way the `D-21` records cite `R-5`, and
it says in the block itself why `R-5` was the wrong authority for this and `R-10` is the
right one.

**The guard was extended, not loosened.** `PERMITTED_EXCEPTIONS` gains one literal entry,
`"16-listProjects.success": ("D-16",)` — six entries to seven, the seventh the ruling
predicted. It still requires a debt, a commit and a non-empty `permitted_change` on every
marked record, still requires the marked set to equal the literal exactly, and now **also**
requires record 16 to cite `R-10`, mirroring the existing `R-5` requirement on the `D-21`
records. `test_exactly_the_named_records_are_marked_as_permitted_exceptions` passes; deleting
the new literal entry makes it fail, which is what makes the count a count.

**The journey asserts the value rather than only pinning it.** At case 16 the field must be
present, an `int` and `>= 0`; at case 32 — where `listDocuments`' answer is finally in hand —
`project_document_count == len(listed_documents["items"])`. Against the length, never against
a literal: a literal stays green if both halves drift together.

## 8. The gate

Run on the committed tree with nothing else touching lane `gate-w19b`; the socket server was
stopped first.

```
$ make gate > gate.log 2>&1
$ echo $?
0
```

| | Base (brief) | Here | |
|---|---|---|---|
| battery | 1778 / 5 skipped / 168 subtests | **1785 passed, 5 skipped, 168 subtests** | +7 |
| foundation | 35 | **35** | — |
| frontend | 595 (44 files) | **595 (44 files)** | — |
| whitespace | — | pass | — |

`GATE OK: battery, foundation, frontend and whitespace all pass`.

The +7 is exactly the seven tests added: five in
`tests/integration/ingest/test_project_document_count.py` and two in
`tests/integration/api/test_listing_surface.py`. The frontend figure is unchanged because
`web/**` was not touched — `W19-SHELL` owns it.

## 9. What was in the brief that the tree did not bear out

Little, and nothing that changed a decision. Recorded so the next brief is measured rather
than recalled:

1. **"`records/` compares 33+ responses."** It is **36** records covering the fifteen
   operations. "33+" is true and reads as an estimate; the number is measurable
   (`ls tests/characterization/w13_baseline/records | wc -l`).
2. **"`W18-SEAL` made `exception.debt` a list."** True of the record's JSON. In
   `test_response_baseline.py` the `PERMITTED_EXCEPTIONS` values are **tuples**, compared
   with `tuple(block["debt"]) == …`. The new entry follows the file's spelling, not the
   brief's.
3. **"You own `src/auditmanager/documents/**` and whatever else you prove produces this
   field."** The field could not be produced from `documents/**` alone. It needed
   `bootstrap/adapters.py` (the seam that drops it), `ingest/service.py` (a type annotation)
   and `tests/integration/api/conftest.py` (the suite's own second copy of the adapter). The
   brief's escape clause covered it; naming the four files up front would have been better.
4. **The base gate figures were taken on trust for the battery.** Foundation 35 was measured
   at base on arrival, before any edit. The battery and frontend figures at base were
   **not** independently re-measured — the +7 accounting is consistent with the brief's
   1778 and that is the whole of the evidence for it. Stated because a figure inherited from
   a brief is not a figure this session measured.

Everything else in the brief held: `R-10` §3.6 reads as quoted, `listProjects` did render
`documents —`, `listDocuments` is an INNER JOIN on the current version, the record moved is
the seventh, and `contracts/**` needed no edit — `Project.document_count` is declared
`{type: integer, minimum: 0}` and optional, exactly as the ruling says.

## 10. For the integrator, not done here

* **`DEBT_REGISTER.md` `D-16`** carries a paragraph headed *"Flagged for the owner, not
  decided: `listProjects.document_count` is still unpopulated"*, which now reads false. It
  even predicts this work — *"moves a seventh characterization record, which `R-5` does not
  authorise"*. The register is not in this session's ownership and a row is closed by
  measurement, so it is reported rather than edited. The check that closes it:
  `curl -s .../projects | jq '.items[0].document_count'` is a number, and
  `grep -n "document_count" src/auditmanager/documents/repository.py` is non-empty at
  `1bb15ae`.
* **`createProject` still omits `document_count`.** A project one request old holds zero
  documents and the answer would be `0`, but filling it moves record 01 and `R-10`
  authorises `listProjects` and "nothing wider". If `W19-SHELL` renders a count on the screen
  it reaches after creating a project, that is a question for the owner and not a defect
  here.

## 11. Ledger

| | |
|---|---|
| HEAD on arrival | `653152f` |
| Commits | `b19f94c` (review opened, measurement recorded before any edit), `1bb15ae` (the implementation), `150d835` (record 16 and the guard), `6dd39b3` (the gap mutation C exposed) |
| Branch | `agent/w19-api`, from `origin/dev`. No tag, no push to `main`, no merge. |
| Lane | `gate-w19b` — PostgreSQL 55830, S3 59430/59431, `audit_w19b`, `auditmanager-gate-w19b`. No image rebuilt; 31480 and 31490 untouched. |
| Files outside `src/auditmanager/documents/**` | `src/auditmanager/bootstrap/adapters.py`, `src/auditmanager/ingest/service.py`, `src/auditmanager/api/schemas/projects.py` (docstring only), `tests/integration/api/conftest.py`, `tests/integration/api/test_listing_surface.py`, `tests/characterization/w13_baseline/{journey.py,test_response_baseline.py,records/16-listProjects.success.json}` |
| `contracts/**`, `web/**`, `infra/`, `Makefile` | untouched |
| Elapsed, wall clock | **27 minutes**, measured: `date +%s` was `1789732838` on arrival and `1789734465` at this line. Not an estimate. |
