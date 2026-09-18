# W18-SEAL — the `R-5` reseal: three list operations, and a run that says what it cost

**Session** `W18-SEAL`. **Branch** `agent/w18-seal`, from `origin/dev`.
**HEAD on arrival** `3df17a7` — *docs(register): D-19 closes, and the baseline had been
protecting half of it*. Six commits on top of it; no tag, nothing pushed, `main` untouched.

Carries out owner ruling `R-5` (`docs/program/OWNER_RULINGS_2026-09-17.md` §3.5), closing
`DEBT_REGISTER.md` **D-16** and **D-21** in one reseal.

## Summary

| | before | after |
|---|---|---|
| `contracts/api/v1/openapi.json` | 10 paths / 12 operations / 43 schemas | **12 / 15 / 46** |
| `grep -c cost` over that file | **1** (`cost_budget_exceeded`) | **7** |
| error catalog | 21 codes, `frozen: false`, `candidate_revision: 6` | **unchanged** |
| CSV columns | 17 | **unchanged** |
| characterization records | 33 | **36**, five of them moved |
| gate | 1746 / 5 / 168, foundation 35, frontend 592 | **1768 / 5 / 168, 35, 595**, exit **0** |

**No error code was added.** An unknown parent is the catalog's `not_found` and a malformed
cursor is `validation_failed`; both already existed and both already carried the detail keys
these operations need. `contracts/domain/v1/**` is byte-identical to its state at `3df17a7`,
so the `W0-DOM-02` three-catalog `candidate_revision` did not have to move. The brief hoped
for this outcome and said to say so if it happened.

## 1. Measurements taken on arrival, not inherited

The brief's figure for the base contract was checked rather than assumed, and it holds:

```
openapi 3.1.0 | 10 paths | 12 operations | 43 schemas
components.securitySchemes = ['bearerAuth'] | security = [{'bearerAuth': []}] at the root
```

`contracts/domain/v1/error-codes.json`: `frozen: false`, `status: "draft_candidate"`,
21 codes, `candidate_revision: 6` — and `identifiers.json` and `state-machines.json` carry
`candidate_revision: 6` too. `D-8` holds exactly as written.

`df -h /` on arrival: **11 GB free**, which is `R-6`'s reclamation still standing.

## 2. The shape of each operation, and the argument from the existing code

All three are the same shape, because `listProjects` already fixes what that shape is: a
`GET` of a collection, ordered newest first, paged by `cursor` and `limit`, answering the
`{items, page: {next_cursor}}` envelope. The only real decisions were **what the parent is**
and **what the item is**, and both are answered by the code rather than by taste.

### `listDocuments` — `GET /projects/{project_uid}/documents` → `DocumentVersionPage`

**The parent was already chosen.** `uploadDocument` is `POST /projects/{project_uid}/documents`.
`listProjects` is the `GET` of the path `createProject` `POST`s into, and it returns a page
of exactly the resource that `POST` returns. Applying the same rule here gives this path and
this item type, and adds **no new path** — the path item gains a `get`.

**The item is `DocumentVersion` because there is no `Document` shape and this is not the
wave to invent one.** `uploadDocument` publishes a `DocumentVersion` into this collection;
the contract has never had a `Document` resource, no operation addresses one, and adding it
would be a fourth new schema carrying a display title and nothing a caller could act on. A
`DocumentVersion` gives a screen everything a project page needs in one call — `document_uid`,
`version_uid` to start a run against, `display_title`, `page_count`, `published_at`.

**One row per document, carrying the version the document currently points at.** The join is
`document_version.version_uid = document.current_version_uid`, which `publish_version`
maintains through `_POINT_DOCUMENT_AT_VERSION`. A document whose `current_version_uid` is
still NULL is not listed, and that is written as an INNER JOIN rather than as a filter,
because there is nothing a caller could open, stream or run against.

### `listVersions` — `GET /documents/{document_uid}/versions` → `DocumentVersionPage`

**The parent is the document because the row says so.** `document_version.document_uid` is
the foreign key and `version_ordinal` is unique *per document* — `uq_document_version_ordinal`
— so the document is the aggregate a version belongs to. The ordering is
`version_ordinal DESC`, which needs no tiebreaker for that reason.

This introduces the one new path root, `/documents/{document_uid}`, and with it the one new
`components.parameters` entry, `DocumentUid`. There is deliberately **no** `GET
/documents/{document_uid}`: a collection path whose parent has no `GET` is already the house
pattern — `/projects/{project_uid}/documents` has existed since Gate A and there has never
been a `getProject`.

**Worth knowing before the screens are written:** through this surface a document always has
exactly **one** version. `uploadDocument` declares no `document_uid`, and `DocumentPort`
does not carry one, so every upload creates a new document with its first version. The
service underneath (`IngestService.upload_single_pdf`) does take `document_uid` and does
publish a second version onto an existing document — the capability is real and only the
transport withholds it. So `listVersions` returns one row today and is not a stub; it is the
read side of an aggregate the write side can already grow.

### `listRuns` — `GET /versions/{version_uid}/runs` → `RunStatusPage`

**The parent is the version because `startRun` says so.** `StartRunRequest` carries
`version_uid` and nothing else that identifies anything; the project is derived from it. So
the version is the run's parent in the create direction, and this is the inverse of that
direction rather than a second way of addressing a run.

**Rejected: `GET /runs?project_uid=…&version_uid=…`.** It would mirror `POST /runs`, but
every existing sub-list in this contract is a child collection under its parent —
`listRunFindings` under `/runs/{run_id}`, `listDecisionHistory` under
`/findings/{finding_uid}` — and none of them is a filtered root collection. Taking the
query-parameter route would have added two `components.parameters` entries and made
"someone else's rows" a matter of remembering a `WHERE` clause rather than of the path.

**Each item is the whole `RunStatus`.** There is a precedent for a lighter list item —
`listRunFindings` returns `Finding` while `getFinding` returns `FindingDetail` — and it does
not apply: `FindingDetail` adds evidence quotations and a decision projection, which are
genuinely large, while `RunStatus` is four small stage objects. A `RunSummary` would be a
second shape of one resource, and the first thing a second shape does is drift.
`RunAdapter.list_runs` builds every item through the same `_run_status_view` the single read
uses, and `test_a_run_in_a_listing_is_the_same_body_as_the_run_read_on_its_own` asserts the
two bodies are equal rather than merely consistent.

### What all three refuse

**An unknown parent is `404`, never an empty page.** `list_documents` calls `get_project`
first, `list_versions` calls `require_document` first, and `RunAdapter.list_runs` reads the
version before it reads the runs. "This project has nothing in it yet" is a reassuring and
wrong thing to say about a project that does not exist, and the two answers are things a
caller acts on differently. The envelope names which aggregate was missing —
`{"aggregate_type": "Project"}`, `"Document"`, `"DocumentVersion"` — so a caller can tell
*which* of the two reads failed.

The existence check for runs is in the adapter and not in `RunRepository`, because that
repository owns `audit_run` and knows nothing about `document_version`; the adapter is the
one place that holds both modules.

## 3. Cost: where it is exposed, why there, and what was done about `D-15`

**`RunStatus` gains three optional properties: `cost_micros`, `cost_basis`,
`model_call_count`.** The CSV is untouched.

### The argument for `RunStatus`, from the criterion and the schemas

`PA-01` criterion 4 is *"a live `text_analysis` run completes, with its **provider mode and
cost** visible"*. It names the two together. `provider_mode` is a **required** `RunStatus`
property, so the clause's other half belongs in the same body; a user reading one and
navigating elsewhere for the other is a user who can fail criterion 4 by not navigating.

Structurally, cost is a run-level aggregate over rows of another table — and `RunStatus`
already carries exactly that kind of property. `published_finding_count` and
`diagnostic_observation_count` are not columns on `audit_run`; they are counts computed in
`_run_status_view`, added by `W17-VIEW` under `D-19`. `cost_micros` is the same kind of
value computed in the same function, one line below them.

### The argument against the CSV, which is the boundary I stopped at

Three reasons, and any one of them is sufficient:

1. **The column list is frozen by a different seam and a different authority.**
   `P02_SEAMS.md` §6 freezes seventeen columns under `OD-11`, and `PA-01` **criterion 7**
   says the CSV downloads *"with its seventeen columns"*. An eighteenth column would move a
   frozen list that `R-5` does not name, and would falsify a criterion of the checkpoint the
   reseal exists to unblock.
2. **The granularity is wrong.** One CSV row is one evidence item. A run-level cost repeated
   across every row of a three-finding run is a number that looks like a per-row fact and is
   not, and a reader summing that column gets the cost multiplied by the evidence count.
3. **The CSV cannot answer the question at all for the runs that most need it.**
   `exportRunCsv` refuses any run whose terminal does not publish a result — a non-terminal
   run and the terminal `failed`. **A run that spent money and then failed produces no CSV,
   so its cost would be invisible exactly where an operator most wants it.** `RunStatus`
   answers for every run in every state.

If the owner wants cost in the CSV as well, it is a change to `OD-11` and to `PA-01`
criterion 7's wording, and it is a ruling of its own. I stopped there.

### `D-15`, and not inheriting it

`D-15` measures that `stage_result.metrics["cost_usd"]` is a sum **across retry attempts**
while `metrics["cost_basis"]` describes the **last response only**, so a run whose first
attempt replayed and whose second reported a cost publishes a two-attempt sum wearing one
attempt's provenance. `D-15` also records that repairing that pair is a design call and not
a lane decision.

**So I did not read that pair at all, and I did not repair it.**
`src/auditmanager/analysis/text/stage.py` and `runs/executor.py` are untouched; `D-15` is
open and is exactly where `W17-VIEW` left it.

The figure on the wire is computed from the `model_call` rows instead — which `D-15` itself
says are the exact ones: *"the model-call **records** are exact — each carries its own
basis"*. One statement, `RunRepository.cost`, produces three values in one pass:

* **`cost_micros`** — `sum(cost_micros)` over every `model_call` row of the run, in the
  stored integer unit. Never a float: migration `0002` says floating-point money is not
  stored, and the contract does not turn it into one on the way out.
* **`model_call_count`** — `count(*)` over the same rows. **Published rather than inferred,
  and this is the part that answers `D-15` directly:** without it a reader cannot tell a run
  answered first time from one that was retried, which is precisely the ambiguity the debt
  is about. With it, "the sum spans two calls" is a thing the client can see.
* **`cost_basis`** — an **aggregate over the contributing rows**, by the conservative rule:
  `measured` only when every one of them reported a measured cost, `estimated` the moment one
  did not. The schema description states that rule, so a consumer reads the definition rather
  than guessing it. `CostBasis` is a component schema of its own, beside `ProviderMode`.

Two details that are not decoration. **`model_call.cost_micros` is nullable**, and SQL `sum`
skips a NULL silently, so a run with one unpriced call would otherwise publish a short total
wearing the word `measured`; the `FILTER` counts `cost_micros IS NULL` as unmeasured too.
And **all three are absent, not zero, when the run made no provider call**: "it cost nothing"
and "nothing was spent here" are different claims, and `D-3` is this programme's record of
what inventing the flattering one costs. A run whose calls were genuinely free reports
`cost_micros: 0` with `model_call_count` ≥ 1, and both halves of that rule have their own test.

**One measured thing worth carrying forward:** a `recorded` run reports
`cost_basis: "estimated"`, because a replayed call reports no cost of its own. So the first
live `PA-01` run is also the first one that can print `measured` — which is what makes the
field worth reading rather than decorative.

## 4. The envelopes, over a real socket

`uvicorn` bound to `127.0.0.1:58800` against this lane's PostgreSQL (`55800`, `audit_w18a`)
and MinIO (`59400`, `auditmanager-gate-w18a`), `AUDITMANAGER_PROVIDER_MODE=recorded`, driven
with `curl`. The full journey was walked first — project, upload of
`fixtures/synthetic/ar/ar_baseline.pdf`, run — and then the three new reads. The application
serves the paths at the root; `/api/v1` is the deployment's prefix and not a mount.

**`GET /runs/{run_id}` — the cost clause of criterion 4, for the first time:**

```json
{
  "state": "published",
  "provider_mode": "recorded",
  "published_finding_count": 3,
  "diagnostic_observation_count": 0,
  "cost_micros": 34400,
  "cost_basis": "estimated",
  "model_call_count": 1,
  "terminal_at": "2026-09-18T06:55:53.028259Z"
}
```

**`GET /projects/{project_uid}/documents` → `200`, `X-Correlation-Id: cid-2776e02e…`:**

```json
{
  "items": [
    {
      "version_uid": "ver_01M2SMSNT3HHW0MJRQWJGEFCB4",
      "document_uid": "doc_01M2SMSNT254V7MQY1964B3T5Q",
      "project_uid": "prj_01M2SMSNE5361YHGS0HZK5ABPF",
      "version_ordinal": 1,
      "media_type": "application/pdf",
      "byte_size": 58978,
      "sha256": "6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f",
      "page_count": 8,
      "published_at": "2026-09-18T06:55:52.642022Z",
      "input_manifest": [
        {
          "role": "source.document",
          "sha256": "6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f",
          "size_bytes": 58978,
          "media_type": "application/pdf"
        }
      ],
      "display_title": "АР"
    }
  ],
  "page": { "next_cursor": null }
}
```

**`GET /documents/{document_uid}/versions` → `200`** returns the same single row, with
`version_ordinal: 1` — the one-version-per-document fact of §2 measured rather than asserted.

**`GET /versions/{version_uid}/runs` → `200`** (abridged to the keys under discussion; the
item is the whole `RunStatus` and was compared equal to `GET /runs/{run_id}` byte for byte):

```json
{
  "items": [
    {
      "run_id": "run_01M2SMSNWFJ3NHRAEPY7X7VMEE",
      "project_uid": "prj_01M2SMSNE5361YHGS0HZK5ABPF",
      "version_uid": "ver_01M2SMSNT3HHW0MJRQWJGEFCB4",
      "state": "published",
      "provider_mode": "recorded",
      "published_finding_count": 3,
      "cost_micros": 34400,
      "cost_basis": "estimated",
      "model_call_count": 1,
      "created_at": "2026-09-18T06:55:52.716028Z",
      "terminal_at": "2026-09-18T06:55:53.028259Z"
    }
  ],
  "page": { "next_cursor": null }
}
```

### The 401s, presented and absent, over the wire

Not assumed from the root-level `security` declaration. The refusal is the `T-6` dependency,
not the document, so each new operation was driven with **no** credential and with a **wrong**
one:

```
/projects/{project_uid}/documents   absent=401  wrong=401  ok=200
/documents/{document_uid}/versions  absent=401  wrong=401  ok=200
/versions/{version_uid}/runs        absent=401  wrong=401  ok=200
```

and the body in every one of those six cases, with no `detail` key and no hint about the
resource:

```json
{"contract_version": "1.0.0-draft.1", "error_code": "authentication_required",
 "message": "No valid authenticated subject was presented. The response carries no hint about the addressed resource.",
 "correlation_id": "cid-aa447cf58298438e0ebbd601e196164c", "retryable": false}
```

### The refusals, over the wire

```
GET /projects/prj_01M2545JSD15ETSNNV904X991F/documents   → 404 not_found  {"aggregate_type": "Project"}
GET /documents/doc_01M2545JSD15ETSNNV904X991H/versions   → 404 not_found  {"aggregate_type": "Document"}
GET /versions/ver_01M2545JSD15ETSNNV904X991J/runs        → 404 not_found  {"aggregate_type": "DocumentVersion"}
GET /versions/{version_uid}/runs?cursor=not-a-cursor     → 422 validation_failed  {"field": "cursor", "constraint": "format"}
```

### Paging, over the wire

Two more documents were uploaded and the listing walked at `limit=1`, following the server's
own `next_cursor`:

```
page: ['doc_01M2SMV9PMV9STRKXQG15HHA8K']  next_cursor: WyJ2ZXJfMDFNMlNNVjlQTkdY…
page: ['doc_01M2SMV9KKBR6FXMWX9CVVJE46']  next_cursor: WyJ2ZXJfMDFNMlNNVjlLTTdX…
page: ['doc_01M2SMSNT254V7MQY1964B3T5Q']  next_cursor: null
one maximal call: ['doc_01M2SMV9PMV9STRKXQG15HHA8K', 'doc_01M2SMV9KKBR6FXMWX9CVVJE46', 'doc_01M2SMSNT254V7MQY1964B3T5Q']
```

### The served document, from the running process

`GET /openapi.json` off the socket, compared against the sealed contract through
`W13-CONF`'s own comparison engine: **0 differences**, `12 paths / 15 operations /
46 schemas`. That is `PA-01` criterion 1's check, run against a real process rather than a
build artefact.

## 5. Which test reddened for each guard

`make mutation-copy MUT=/root/w18seal-mut FULL=1`, baselined green first (110 passed), one
mutation at a time, restored between each. **Eleven mutations, eleven reds.**

| # | Mutation | Test that reddened |
|---|---|---|
| M1 | `_LIST_DOCUMENTS` loses `WHERE d.project_uid` | `test_list_documents_returns_this_project_and_not_the_next_one` |
| M2 | it joins `v.document_uid = d.document_uid` instead of `current_version_uid` | `test_list_documents_shows_the_version_the_document_currently_points_at` |
| M3 | `_LIST_VERSIONS` orders `version_ordinal ASC` | `test_list_versions_returns_this_document_and_not_a_sibling` |
| M4 | `list_documents` drops its `get_project` check | `test_an_unknown_parent_is_not_found_and_never_an_empty_page` |
| M5 | `listRuns` always answers `next_cursor: null` | `test_the_walk_returns_every_row_exactly_once` (both `limit` cases) |
| M6 | the cost `FILTER` stops counting a NULL as unmeasured | `test_a_call_with_no_recorded_cost_cannot_leave_the_total_called_measured` |
| M7 | a run with no calls reports `RunCost(0, 0, "measured")` | `test_a_run_that_made_no_provider_call_reports_no_cost_at_all` |
| M8 | `_COST_SUMMARY` loses `WHERE run_id` | `test_another_runs_cost_never_reaches_this_run` |
| M9 | `require_authorization` returns without comparing | `test_the_fifteen_are_all_behind_the_seam` |
| M10 | `listRuns` and `RunStatusPage` deleted from the sealed document | `tests/contract/api_v1` — 4 failed |
| M11 | `listVersions` renamed in the router only | `tests/integration/api/test_operation_surface.py` — 2 failed |

M9 is the one worth reading in full, because it is the answer to "is the top-level `security`
declaration doing it for you?". With the seam opened, the failure names each of the three
individually:

```
these operations answered something other than 401 with no credential:
  ('listDocuments', 404), ('listVersions', 404), ('listRuns', 404), …
```

`404`, not `200`, because those requests carry identities that do not exist — which is the
point: without the dependency they are *answered*, and the answer reveals that the path is a
resource.

The remaining guards are the ordering and isolation ones, whose ability to fail is built into
the fixture rather than into a mutation. `Catalogue` stamps `published_at` and `created_at`
values whose order **disagrees** with the identity order and asserts that disagreement before
any ordering assertion leans on it — without it, every ordering test would pass against
`ORDER BY version_uid DESC`. That is the same property `Ladder` establishes for projects in
`test_query_surface.py`, and for the same reason.

## 6. What the lock and the conformance gate required

**The contract was never hand-written beside the application.** It was edited, then compared
against `app.openapi()` through `tests/contract/api_v1/openapi_conformance.py` until the
report was empty, and the comparison was re-run against the *served* document off the socket.
The one thing the comparison caught that reading would not have: I had written `cost_basis`
as `{"allOf": [{"$ref": …}], "description": …}` and Pydantic emits a bare `$ref`, which the
engine reported at `schemas.RunStatus.properties.cost_basis` in both directions. The
description moved onto the `CostBasis` schema and the report went to zero.

**The lock required a full regeneration**, and that is guarded from both sides.
`web/tests/guards/frontend-lock.guard.test.ts` recomputes the contract digest, the snapshot
digest, the generator script digest and all four generated-file digests, and separately
compares `lock.openapi.operations` and `component_schemas` against the document itself.
`tests/integration/api/test_query_surface.py::test_the_committed_client_was_generated_from_this_contract`
repeats the first two on the backend side, so an unregenerated contract reddens the suite
next to it and not only the one somebody might run later. So: `npm --prefix web run
api:generate` (15 operations), `web/openapi/openapi.json` rewritten as a byte copy, six
digests updated, the counts moved to 12 / 15 / 46, and a `commit_note` saying what `R-5` did
and why.

**Every pinned literal was moved deliberately rather than loosened.** The bill:

| File | Pin |
|---|---|
| `tests/contract/api_v1/test_openapi_conformance.py` | `FROZEN_OPERATION_COUNT`, `FROZEN_SCHEMA_COUNT`, `FROZEN_OPERATIONS`, `FROZEN_SCHEMA_NAMES`, and the `== 10` count of operations referencing `NotFound` → `== 13` |
| `tests/contract/domain_p02/test_openapi_document.py` | `REQUIRED_OPERATIONS`, `PAGINATED_OPERATIONS` |
| `tests/integration/api/test_operation_surface.py` | `== 12` twice, `len(paths) == 10`, and the path-sample map, which needed `document_uid` |
| `tests/integration/api/test_served_document_and_health_plane.py` | `PATH_COUNT`, `OPERATION_COUNT`, `SCHEMA_COUNT`, and the set of operations declaring their own `422` |
| `tests/integration/api/test_router_and_body_rules.py` | `len(router.routes)`, `len(router.operation_ids)` |
| `tests/integration/api/test_authorization.py` | `TWELVE` → `FIFTEEN`, with the three new `(operation, method, path)` triples |
| `tests/e2e/pc01/test_acceptance.py`, `tests/integration/composition/*.py` | three route-count assertions |
| `tests/characterization/w13_baseline/test_response_baseline.py` | `TWELVE_OPERATIONS` → `FIFTEEN_OPERATIONS` |
| `web/tests/contract/seam-operations.contract.test.ts` | `SEAM_OPERATIONS`, `toHaveLength(12)`, `toHaveLength(43)` |
| `web/tests/unit/api/authorization-state.test.ts` | `toHaveLength(12)` |
| `docs/program/P02_SEAMS.md` §7 | the seam register table, which `tests/contract/domain_p02/test_seam_register.py` compares against the document row for row |

Two of those are outside the tree the brief assigned me and are declared here rather than
quietly taken. **`web/tests/**`**: three literals pinning 12 operations and 43 schemas. They
are guards over the *contract*, in the same class as the lock, and the frontend gate is red
without them; no screen was written and `web/src/app/**` is untouched. **`docs/program/P02_SEAMS.md`**:
the seam register is compared to the document by a backend guard, so it is a copy of the
contract rather than a document about the programme.

**`tests/integration/api/conftest.py`** also gained three methods, on `IngestDocumentAdapter`
and `SeamRunAdapter`. Both delegate to the shipped code — the real `IngestService` and the
real `RunRepository.list_for_version` — for the reason that file already gives at length: a
fixture adapter that filters proves only that the fixture filters.

### The prose sweep, which is `D-8`'s lesson applied to my own change

`grep -rn "twelve\|43 " src/auditmanager/api/` returned **thirty** statements about the size
of the surface, in module docstrings, in comments, in `README.md`, and in one string the
application **serves**: `_DESCRIPTION`, *"The twelve operations of the PC-01 surface"*, which
goes out on `/openapi.json`. None of them can fail a gate — the conformance engine drops
`description`, `summary` and `title` as annotation (`N4`) — so every one of them would have
survived this reseal and gone on being read as true.

That is `D-8` exactly (*"a name repeated often enough stops being checked"*) and `D-22`
(*"one rule, three hand-copies, and the copies are what ship"*). All thirty were re-measured
and corrected, not find-and-replaced: `"Eight of the twelve operations"` displacing FastAPI's
422 became **eleven of fifteen**, because I counted them; `"four of the twelve declare no 422"`
stayed **four**, because that set did not change.

## 7. Characterization records

**Thirty-three became thirty-six, and the change set was measured rather than eyeballed.**
Comparing the directory before and after the recapture, key by key:

| | records |
|---|---|
| new | 3 — `32-listDocuments.success`, `33-listVersions.success`, `34-listRuns.success` |
| differ under `response` **and** `exception` | 5 — the `RunStatus` bodies, `03`–`07` |
| differ under `exception` only | 1 — record `31`, the `debt` list format |
| byte-identical | 27 |

The five response diffs are **three added keys each and nothing else**: no status moved, no
header moved, no existing property changed value.

`test_every_one_of_the_twelve_operations_is_covered` asserted set equality against a written-out
tuple, so adding three operations *required* moving that literal — which is right, and is what
the brief means by "adding is not a permitted change and needs no exception block". The three
new records carry none.

**The five that changed already carried one**, for `D-19`, and they now carry two. I made
`exception.debt` a **list** on all six marked records and `PERMITTED_EXCEPTIONS` a map of
case → tuple, rather than writing `"D-19, D-21"` into the existing string. A comma inside a
sentence keeps the shape and loses the property: a list of debts is countable and a sentence
is not, and this guard exists to make exceptions countable. Record 31's `"D-7"` became
`["D-7"]` so there is one spelling and not two — a metadata-only change; its response bytes
did not move.

The new block, `EXCEPTION_W18SEAL`, follows record 31's form exactly: `debt`, `ruling`,
`status`, `decided_by` (`6398bcc`), `decided_by_subject`, `decided_on`, `permitted_change`
describing the whole of both moves, `everything_else`. And a new assertion requires every
record marked `D-21` to cite `R-5` in its `ruling`, beside the one that already required
record 31 to cite `R-3` — because `D-19` needed no ruling (it repaired a declared field that
had no producer) while adding a property is the owner's act.

## 8. Every boundary I stopped at

1. **The CSV.** §3. Seventeen columns, frozen by `OD-11` / `P02_SEAMS.md` §6 and named as
   seventeen by `PA-01` criterion 7. Not mine, not `R-5`'s.
2. **A 22nd error code.** Not needed, so not taken. `contracts/domain/v1/**` is byte-identical
   to `3df17a7`.
3. **`D-15`.** Not repaired. `stage.py` and `executor.py` untouched. The contract reads the
   `model_call` rows instead and states its own aggregation rule, so the ambiguity is not
   inherited — but it is also not resolved where it lives, and it is still open.
4. **`D-18`** — `conflict`'s safe detail keys. Untouched.
5. **`D-20`** — `execute_run` off the request thread. Untouched, **and it bears on `listRuns`
   in a way worth stating**: because execution is inline, a run is `published` by the time
   `startRun` answers, so a run list can show what *ran* but can never show something
   *running*. `listRuns` makes the set of runs reachable; it does not make criterion 4's
   `running` state observable. That remains `D-20`'s to close.
6. **`listProjects.document_count`.** Still not populated, so a project list still reads
   `documents —` — the complaint `W15-RUN` raised in the same breath as D-16. Populating it
   would change an existing operation's body and move a seventh characterization record, and
   `R-5` authorises three new operations and cost, not a change to `listProjects`. A screen
   can now get the number itself from `listDocuments`, at one call per project. **Flagged for
   the owner rather than decided.**
7. **`web/src/**` — no screen.** The client is regenerated because the lock guard requires it;
   the fifteen operations are reachable from `web/src/shared/api/generated/operations.gen.ts`
   and nothing renders them yet.
8. **`infra/**`** — untouched; `W18-OPS` is live there.

## 9. The gate

Run at `87f8e0b`, on instance `gate-w18a`, with the tree committed and
clean, no `pytest` and no `uvicorn` of mine running against this lane's database, and the
exit status read from `$?` after a redirect — never through a pipe.

```
foundation : 35 passed
battery    : 1768 passed, 5 skipped, 168 subtests passed   (3:35)
frontend   : 44 files, 595 passed
GATE OK: battery, foundation, frontend and whitespace all pass
GATE_EXIT=0
```

**Exit code `0`.**

Against the base the brief quotes — 1746 / 5 / 168, 35, 592 — the battery is **+22**: the
nineteen cases of `tests/integration/api/test_listing_surface.py` and the three new
characterization records. The frontend is **+3**, and that is not new test code:
`seam-operations.contract.test.ts` generates one `it` per entry of `SEAM_OPERATIONS`, so the
three rows added to that literal are three cases.

An earlier full gate at `ed73c04`, before the prose sweep, exited `0` with the same three
counts (battery 3:35, this one 3:29). The sweep touches only docstrings, comments, one README
and one served description, so the two runs agreeing is the expected result rather than a
second measurement of anything.

## 10. What is false or imprecise in the brief

Fewer than usual, and the two headline measurements were both right.

**10.1 — `DEBT_REGISTER.md` is not at the repository root.** It is
`docs/program/DEBT_REGISTER.md`. The brief cites it as a bare filename three times and the
first read of it failed. Trivial, and recorded because §2.5 of the register says the
stale-premise count has no register of its own.

**10.2 — the gate figures are right, and I doubted one for no reason.** *"battery 1746 passed
/ 5 skipped / 168 subtests, foundation 35, frontend 592 (44 files)"* — the frontend number
looked wrong to me once my own count came back 595, so I built a throwaway worktree at
`3df17a7`, ran `npm --prefix web ci` and `npm --prefix web test`, and measured **592 passed,
44 files**. The brief was accurate and the delta is mine. Recorded because the wrong move
here would have been to assume the brief was stale, which is what the last five waves have
trained the session to expect.

**10.3 — `make mutation-copy` copies more than the brief says.** The brief says it *"now
carries `tests/` and `pyproject.toml` as copies and links `.venv`, so a **tests-only**
mutation runs inside the copy"*. `src/` is copied too (`cp -a src "$dest/src"`), so a **src**
mutation also runs inside the copy — which is how nine of my eleven mutations were run, with
the copy's own interpreter and its own `pyproject.toml`. The five symlinked trees are
`contracts`, `docs`, `fixtures`, `db` and `tools`, and `FULL=1` copies **all five**, not only
"a migration". The probe did not refuse anything; `MUTATION-COPY OK` on the first try.

**10.4 — "`tests/integration/foundation/conftest.py:542` compares `git status --porcelain`
around the run" is right in substance and one line off.** The comparison is the session-scoped
autouse fixture `checkout_is_unchanged`, which begins at line 541; `_tracked_state` ends at
538. Not worth a correction except that the brief's line numbers are otherwise exact.

**10.5 — the served document is not the contract's `info` block, and the brief's framing hides
it.** `app.py` builds the served document with its own `_TITLE` (`"AuditManager API"`, against
the contract's `"AuditManager PC-01 API"`) and its own `_DESCRIPTION`. The conformance gate
never notices, because `N4` drops `title`, `summary` and `description` everywhere. So *"the
document is verified against what the app generates"* is true of the whole **surface** and
not true of the prose a reader of `/openapi.json` sees — which is how the served description
came to claim twelve operations. §6 fixes it; the general point is that the contract's `info`
block is an unguarded copy, and it is the kind of thing `D-22` is a register entry about.

**10.6 — "the largest single item between here and a version a human can test by hand" is
right about the contract and incomplete about the product.** The operations exist and answer,
and after a reload a client can now reach every project, document, version and run. But
`D-16`'s user-visible symptom — *"a project page on a fresh load makes zero API calls"* —
is **still true**, because the screens are a later session's. This wave makes the reload
survivable; it does not make it survived.

## 11. Elapsed

Measured, not estimated. First command of this session **11:24:27**; the confirming gate
exited at **12:12:15** local. **47 minutes 48 seconds** wall clock.

About twenty of those minutes are runs the session spends waiting rather than working: two
full gates at 3:35 and 3:29 of battery apiece plus their foundation and frontend steps, one
whole-`tests/integration` run at 3:10, `npm ci` and `make bootstrap` on arrival, `make up`
and `make migrate` for the lane, and one more `npm ci` in a throwaway worktree at `3df17a7`
to check §10.2.
