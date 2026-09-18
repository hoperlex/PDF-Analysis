# `api` boundary

Transport adapters only: parse, call one port, render the frozen shape, map the typed
error. No domain logic and no transaction in any router.

The specification is `contracts/api/v1/openapi.json`, frozen at Gate A. It is read-only
from here: `A5` generates the frontend's typed client from it and a drift guard compares
the committed client against it, so an edit here reddens the web suite. A defect in the
document is reported, not repaired.

## FastAPI, natively, with the frozen contract built under it

**`T-1`, owner decision 2026-09-17, landed by `W13-API` in wave 13.** The operations
are typed FastAPI path operations, the `components.schemas` are Pydantic models, and the
hand-rolled `Router` / `dispatch` / `http.py` / `multipart.py` layer is retired.

### What this section used to say, and why it is worth keeping the correction

It said "there is no HTTP framework here, and that is a pin-set consequence, not a
decision", and before *that* it said the absence was deliberate. `ADR-0002` names "one
deployable Python/**FastAPI** backend"; `TECHNOLOGY_BASELINE.md` names "Python,
FastAPI/ASGI"; `ARCHITECTURE_BIBLE.md` P-05 and `PROTOTYPE_PROFILE.md` §2 say the same.
`docs/program/P02_LOCK.json` pinned three runtime distributions and none of them was a web
framework, so `B6` wrote about a hundred stdlib lines instead — which was the right call
**for a lane that may not add a root dependency**, and the wrong sentence to write about it.
A lane-level pin set records what a lane may install; it cannot overrule an ADR. `W13-PIN`
added the pins on the owner's ruling and this is what was always meant to be here.

### The second authority, and the machine that checks it

A framework that generates its own OpenAPI document over a frozen one creates a **second
routing and schema authority**, and that is a real drift risk — it is the objection revision
1 of `ALPHA_ROADMAP.md` raised against this decision. What answers it is not an assurance
but a gate: `tests/contract/api_v1/test_openapi_conformance.py` compares
`create_documentation_app().openapi()` against `contracts/api/v1/openapi.json` under a
declared normalization, and every entry of that normalization carries a planted difference
proving the comparison can still fail.

**The contract stays the authority. The generated document is what has to move.** Three
places in this package exist only because of that, and each says so at its own site:

* `schemas/models.py` spells "optional but not nullable" as
  `Field(default=None, json_schema_extra=optional_property)`, because Pydantic's ordinary
  `X | None = None` emits a null branch and a `default` the contract does not declare;
* the scalar newtypes are `TypeAliasType` aliases, because the contract spells them as
  `$ref`s and only an alias is *also* a scalar FastAPI will accept as a path, query or
  header parameter;
* `app.py` removes the `422` FastAPI injects into the four operations that declare none,
  and only when the response object is byte-for-byte FastAPI's own. Those four answer `404`
  for a malformed path identity by design and enforce nothing else, so a `422` on them is a
  false statement about this application.

## What lives here

| Path | What it is |
|---|---|
| `app.py` | `create_app`, `create_asgi_app`, `create_documentation_app`, and the document's own metadata |
| `composition.py` | the thin seam to `auditmanager.bootstrap` |
| `security.py` | `T-6` — the bearer seam, and the alpha's static token behind it |
| `health.py` | `T-3` — liveness and readiness, a **separate application** on a second port |
| `routers/wire.py` | `WireResponse`: the exact header list, in the exact order and case |
| `routers/declarations.py` | the response table and the parameters every operation repeats |
| `routers/handlers.py` | where FastAPI's own failures stop being FastAPI's |
| `routers/errors.py` | classification: a DBAPIError's SQLSTATE, and the envelope renderer |
| `routers/correlation.py` | `X-Correlation-Id` on every response, assigned when absent |
| `routers/idempotency.py` | the required `Idempotency-Key`, as a declared parameter |
| `routers/multipart.py` | the transport body cap, and the four rules a closed model cannot state |
| `routers/ports.py` | the six narrow ports a composition root satisfies |
| `routers/{projects,documents,runs,findings,decisions,export}.py` | the fifteen operations |
| `schemas/models.py` | the 46 `components.schemas`, as Pydantic models |
| `schemas/{common,projects,documents,runs,findings,decisions}.py` | the view types the ports return, and the functions that render their bytes |

**`build_router(...)` takes the same six keyword-only ports it always did and constructs
none of them**, which is what made `T-1` a transport change rather than a rewrite of the
application: `bootstrap/composition.py` — another session's file — did not move a line.

**Why the bodies are not rendered by the Pydantic models.** A handler returns a
`WireResponse`, which FastAPI passes through untouched, so `response_model` describes a
response without serializing it. `model_dump_json` would emit compact separators and its
own key order, and every one of the 33 records in
`tests/characterization/w13_baseline/records/` would differ from what it recorded in a way
that means nothing — inside the one safety net this wave has for differences that mean
something.

The task file `docs/program/tasks/P2-API-01.md` also lists `api/errors.py` and
`api/idempotency.py` as allowed paths. The `B6` dispatch brief is narrower —
`routers/**`, `schemas/**` and this README — so both modules live under `routers/`
instead. Same code, inside the narrower boundary.

## The error middleware

`docs/program/P02_SEAMS.md` §3.2. Three custom SQLSTATEs, all reporting one catalog code:

| SQLSTATE | Fires when | Catalog code |
|---|---|---|
| `AM001` | an undeclared state edge, or an aggregate inserted in a non-initial state | `state_transition_not_allowed` |
| `AM002` | UPDATE or DELETE on an append-only ledger | `state_transition_not_allowed` |
| `AM003` | UPDATE or DELETE on an immutable row, or an edit to a frozen column | `state_transition_not_allowed` |

Four properties are structural rather than reviewed:

* **the mapping is `auditmanager.shared.db.schema.SQLSTATE_TO_CATALOG_CODE`**, read from
  the shared kernel and never restated here. The SQLSTATE comes from
  `documents.sqlstate_of`, which reads the driver's structured field. **Never the message
  text** — a PostgreSQL message can be localised, reworded by an upgrade, or carry a row
  value;
* **`retryable` is pinned by the catalog.** It is not a parameter of
  `shared.errors.build`, so no call site can disagree with it. The HTTP status travels
  the other way, read from `ErrorCode.http_status`. A caller never infers one from the
  other, and `tests/integration/api/test_error_envelope.py` pins that with two codes that
  share a status and disagree on retryability;
* **nothing from the driver reaches the envelope.** Not the message, not the SQLSTATE,
  not the exception class. An unmapped failure is `internal_error` carrying nothing;
* **`details` are screened.** Only the `safe_detail_keys` the catalog declares for the
  reported code are accepted; anything else raises. A caller-supplied string is never
  echoed into a detail value — see the note below.

### One defect this session introduced and fixed

The first version of the `additionalProperties` refusal put the client's own property
name into `details.field`. `message` is screened by the envelope; `details` values are
not. A client sending a property named `/etc/passwd` had it reflected straight back
inside the envelope. The same defect was in the multipart reader twice. All four sites
now refuse without echoing the name.

It was found by `tests/integration/api/test_no_internal_identifiers.py` walking a real
response body — not by reading the code, which is exactly why the gate asks for the walk.

## Ports, and why they exist

A router depends on a protocol in `routers/ports.py`, never on a bounded-context module
directly. Two reasons, both recorded:

1. **`auditmanager.runs` and `auditmanager.exports` did not exist when this was
   written.** Session `B5` is building them in parallel. `RunPort` and `CsvExportPort`
   are written against `contracts/api/v1/openapi.json` and `P02_SEAMS.md` §6 — the same
   frozen declarations `B5`'s public surface is being built against.
2. **Some shapes the frozen document requires have no producer yet.** They are listed
   below. Declaring one on a port states the requirement precisely without widening
   another session's projection.

## Gaps between the frozen document and the modules that must feed it

Ten were reported here by `B6`, none repaired at the time. Two were ruled Gate C blockers
in `GATE_B2_CLOSURE.md` §5.1 and closed by the seam repair; eight were carried forward by
§5.3. **All eight are now closed.** The table records each one and what closed it, because
a gap that vanishes without a record is a gap nobody can re-check.

Four of the eight were this boundary's own — the query surface, the `listProjects`
ordering, and the two claims in the frozen document itself. Session `W2-API` closed those.
The other four sat in `B1`'s and `B4`'s public surfaces and were closed by the seam repair
before `W2-API` began; they are restated here as they now stand, and they are **verified**
statements, not inherited ones: each was re-read in the tree this README ships with.

| # | Gap as reported | Owner | Now |
|---|---|---|---|
| 1 | `DocumentVersion.version_ordinal` is required by the frozen schema and is not on `B1`'s `DocumentVersionRecord` | `B1` / seam owner | **Closed.** `DocumentVersionRecord.version_ordinal` exists and `bootstrap.adapters._version_view` reads it. `GATE_B2_CLOSURE.md` §5.1 ruled that foundation invariant 3 makes a display ordinal a non-identity, not a non-field |
| 2 | `DocumentVersion.display_title` is declared and nothing returns it | seam owner | **Closed.** `DocumentVersionRecord.display_title` exists and is emitted |
| 3 | `Finding` requires `project_uid`, `version_uid` and `run_id`; `B4`'s `FindingRow` carries none of the three | `B4` | **Closed.** All three are on `FindingRow` and are selected by `published_findings` |
| 4 | There is no by-`finding_uid` query at all, so `getFinding` has no read path | `B4` | **Closed.** `auditmanager.findings.finding_by_uid` |
| 5 | **No query surface accepts a cursor, a limit, or a category or verdict filter**, but §7 says growing lists are cursor-paginated and the document declares all four | `B4` / `B1` — **and this boundary** | **Closed by `W2-API`.** All four are implemented; see the section below. None was removed from the contract |
| 6 | `listProjects` is declared "newest first"; `B1`'s `list_projects` is `ORDER BY created_at, project_uid`, which is oldest first | `B1` | **Closed.** The repository query is `ORDER BY created_at DESC, project_uid DESC`. `W2-API` removed the reversal the API suite's own test adapter still applied on top of it — a compensation for the old query that had turned into a defect — and `tests/integration/api/test_query_surface.py` asserts the order over timestamps proved distinct and deliberately out of step with the identity order |
| 7 | `createProject` requires an `Idempotency-Key` and `B1` publishes no key-accepting project command | `B1` | **Closed.** `IngestService.create_project_under_key` claims the key |
| 8 | `appendDecision` requires the key reach the owning command handler, and nothing in `auditmanager.decisions` claimed a command record from one | `B4` | **Closed.** `append_decision_under_key` claims through `ingest.CommandRepository`, the same primitive `start_run` uses |
| 9 | `DocumentVersion.source_filename` is declared as an optional display field and the `B6` brief forbids any filename crossing the boundary; the two documents disagree | contract owner — **this boundary** | **Closed by `W2-API`, as a non-disagreement.** The property is optional and nullable, so omitting it is conformant: the contract permits the field, PC-01's policy is not to emit it, and `test_the_uploaded_filename_never_comes_back` pins that policy. Nothing to repair in either document; what was missing was the sentence saying so |
| 10 | The frozen `DependencyUnavailable` description calls `dependency_unavailable` "the one retryable code in this surface", while `idempotency_key_in_progress` is also retryable | contract owner — **this boundary** | **Closed.** Corrected in `contracts/api/v1/openapi.json` and resealed in `web/FRONTEND_LOCK.json` on 2026-09-11; the description now names both codes and tells a caller to read `retryable` from the envelope. `W2-API` re-read the document and confirms the wrong claim is gone |

### The four declared query parameters

`cursor`, `limit`, `category` and `verdict`. Every one is **implemented**; none was removed
from the contract.

| Parameter | Where | How |
|---|---|---|
| `limit` | `listProjects`, `listRunFindings`, `listDecisionHistory` | `declarations.LimitParam`, which is the frozen `1..200 default 50` and is also what puts those three numbers in the served document. Out of range or not an integer is `validation_failed`, never a clamp — a silently clamped page is a page the caller is wrong about. An **empty** value is the absent value, as it was before `T-1` |
| `cursor` | the same three | `schemas.common.encode_cursor` / `paginate`. Base64url of the **last sort key emitted**, and nothing else |
| `category` | `listRunFindings` | typed with the frozen `FindingCategory` enum and passed to the port; the shipped `FindingAdapter` filters |
| `verdict` | `listRunFindings` | typed with the frozen `Verdict` enum and passed to the port; filtered on the **projection** over the decision ledger, not on a column |

Three things about the cursor are worth stating, because each is a claim a test has to
carry rather than a property of the code anyone can see by reading it:

* **It carries no position.** `P02_SEAMS.md` §2.2 lists a row number or a sequence value
  among the things that are never an identity, and §5.3 repeats it for the decision ledger.
  The token holds the sort key — for projects the `project_uid` the page already returned,
  for decisions the declared `(recorded_at, decision_id)` pair. It is opaque because a
  client has no reason to read it, not because reading it would reveal anything.
* **It resumes by locating its key, not by comparing against it.** A comparison assumes an
  ascending order and returns the wrong page for a descending one — and `listProjects` is
  descending, so the assumption would be wrong on the first operation. Locating works in
  either direction and survives an insert anywhere in the sequence.
* **A token that does not decode is refused.** Restarting the listing from the top would
  read to a caller as data loss.

`limit` and `cursor` are applied at the edge, over the ordered sequence a port returns, and
`category` and `verdict` are applied by the adapter behind `FindingPort`. For PC-01 — a run
publishes a handful of findings — that is the right place: a predicate pushed into SQL adds
a second home for the ordering contract to drift from. The port signature does not change
when that stops being true, which is the point of it being a port.

**The suite that proves this runs on the shipped adapters.** `tests/integration/api`
otherwise wires three test adapters, for the seams that had no producer when it was
written, and a filter asserted through a fixture that filters proves only that the fixture
filters — which is precisely how the shipped `FindingAdapter` came to take `**_` and drop
both filters while every filter test here stayed green. `conftest.shipped_router` wires
`auditmanager.bootstrap.adapters` for the three ports that carry a query parameter, and
`test_this_suite_really_drives_the_shipped_adapters` asserts that wiring, so re-pointing it
at the fixtures to make a failure go away is itself a failure.

## Reading the bytes

`streamDocumentVersionContent` returns bytes with `Range` support, **no redirect and no
presigned link**: a URL into object storage is the internal address the contract forbids
in a response, and it would outlive the request that authorised it. The bytes arrive as
`bytes` from `DocumentPort.read_content`, resolved from a `blob_id`; nothing on the path
knows a bucket or a key.

`BlobStore.read` has no ranged form, so a ranged request reads the object and slices it.
For a 25 MiB ceiling that is fine; if it stops being fine, a ranged read is a request to
the storage port, not a shortcut around it.

## Tests

`tests/integration/api` — real PostgreSQL, real MinIO, never a skip.

The fifteen-operation assertion compares the router's `(operationId, METHOD, path)` set
against the frozen document itself, never against a list in the test. `build_router` also
refuses a duplicate `operationId` at construction — FastAPI logs a warning and serves a
document declaring the id twice, which leaves `len(routes) == 12` passing while one frozen
operation is no longer addressable. Response bodies
are validated with the pinned `jsonschema` in the **governance** environment, driven
through `tests/contract/api_v1/schema_validation_check.py`; the runtime lock carries no
validator.

`test_query_surface.py` covers the four query parameters, and two of its guards are
structural rather than behavioural, because a behavioural test only catches the parameters
somebody remembered to write one for:

* **every query parameter the frozen document declares is supplied and required to change
  the answer.** Before `T-1` this watched a recording mapping stand in for `Request.query`
  and asserted the handler *looked each name up*; a real HTTP client has no such seam, and
  the stronger question is the one that catches a parameter accepted and ignored. A
  parameter added to the document and acted on by nothing fails here without anyone writing
  a test for that parameter;
* **the committed client cannot drift from the contract unnoticed in this suite either.**
  `web/tests/guards/frontend-lock.guard.test.ts` already checks the digests, in the
  frontend suite — but the contract and the routers change in one commit and the frontend
  suite is a separate command, so an unregenerated client now reddens the suite sitting
  next to the edit.

A paging test carries one trap worth naming, because this suite fell into it. `project`
is append-only and projects accumulate across sessions and days, so the steady state of a
long-lived database is a table of any size — 495 rows in the shared checkout when this was
written. A walk bounded by a constant number of pages, or compared against a single
`?limit=200` request, is asserting a property of a *small* table: the frozen maximum is
200, so one request stops being the whole listing long before anyone notices. **Derive the
bound from the measured population and take the expected sequence from the rows.** The
fixture that guarantees the size is `crowd`, and scoping such a walk to the handful of rows
the test created would be the vacuous repair — a cursor that restarts, repeats or resumes
by position still serves those.


## The one failure shape, and the four ways it could have been broken

`routers/handlers.py` is the single highest-risk module this package acquired in wave 13,
and `tests/integration/api/test_no_framework_body_reaches_a_client.py` is the sweep that
holds it. FastAPI's own answer to a bad request is

```
422 {"detail": [{"type": "string_too_short", "loc": ["body", "name"], ...}]}
```

— a status a reader would accept, with no `error_code`, no `contract_version`, no
`correlation_id` and no `details.constraint`. Four certifications and the response baseline
assert *which rule refused*, so that body reaching a client is a criterion-10 regression
wearing a 422.

Every exception is registered, and the one that cannot be is caught anyway:

| raised by | mapped to |
|---|---|
| `DomainError` | itself — already typed, passes through |
| `RequestValidationError` | the catalog, by `handlers._REFUSALS` and the rules beside it |
| `StarletteHTTPException` | the catalog; **405 becomes 404**, so the API is not an oracle for which paths exist |
| anything else | `internal_error`, or the SQLSTATE's code, carrying nothing from the original |

The last row is `FailureEnvelopeMiddleware`, which sits *inside* the correlation middleware
and *outside* Starlette's `ExceptionMiddleware`. Starlette's own last resort sends an HTML
or plain-text 500 and re-raises; this one sends an envelope and does not.

## `T-6` and `T-3`

**The authorization seam is fail-closed.** `security.py` reads `AUDITMANAGER_API_TOKEN`
from the environment `create_app(environ=...)` already carries, and an application built
without one answers `authentication_required` to every request on this surface. "No token
configured, so let everyone in" is a switch that turns the seam off by omission. The
variable is **not** in `.env.example` and **not** on `AppSettings`: both are outside
`W13-API`'s scope and the gap is reported in `docs/program/reviews/W13-API.md`.

**The health plane is a different ASGI application**, built by `health.py` and served on its
own port. Not a route on this one with the dependency excluded: "excluded from the app-wide
dependency" is one edit away from "included again", and the failure mode is a health check
that starts returning 401 in a deployment.
