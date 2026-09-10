# `api` boundary

Transport adapters only: parse, call one port, render the frozen shape, map the typed
error. No domain logic and no transaction in any router.

The specification is `contracts/api/v1/openapi.json`, frozen at Gate A. It is read-only
from here: `A5` generates the frontend's typed client from it and a drift guard compares
the committed client against it, so an edit here reddens the web suite. A defect in the
document is reported, not repaired.

## There is no HTTP framework, and that is deliberate

`docs/program/P02_LOCK.json` pins three runtime distributions — `pdfplumber`, `pypdf`
and `anthropic` — and none of them is a web framework. Its closing line is explicit:
*every Gate B session consumes these pins and may not add or upgrade a root dependency.*
Nothing in the transitive closure serves HTTP either; `h11` and `pydantic` are there only
because `anthropic` pulls them.

So `routers/http.py` supplies the three things a router actually needs — `Request`,
`Response`, `Route`/`Router` — in about a hundred lines of standard library, and
`routers/multipart.py` reads the one multipart operation on `email.parser`. Adding a
framework is a single-owner pin request, not a lane decision.

Note that the earlier version of this file said "FastAPI transport adapters only". No
FastAPI is pinned, and none was added.

## What lives here

| Path | What it is |
|---|---|
| `routers/http.py` | `Request`, `Response`, `Route`, `Router`, path-template matching |
| `routers/errors.py` | the error middleware: any failure becomes one typed envelope |
| `routers/correlation.py` | `X-Correlation-Id` on every response, assigned when absent |
| `routers/idempotency.py` | the required `Idempotency-Key`, and path-identity validation |
| `routers/multipart.py` | a strict reader for the one `multipart/form-data` operation |
| `routers/ports.py` | the six narrow ports a composition root satisfies |
| `routers/{projects,documents,runs,findings,decisions,export}.py` | the twelve operations |
| `schemas/**` | one view type per frozen schema, and the function that renders it |

`api/app.py` and `api/composition.py` are **not** here and are not this session's to
write: they are the composition root, owned by the integrator in Gate C.
`build_router(...)` takes its six dependencies as keyword arguments and constructs none
of them.

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

Reported to the integrator; none is repaired here.

| # | Gap | Owner |
|---|---|---|
| 1 | `DocumentVersion.version_ordinal` is **required** by the frozen schema and is not on `B1`'s `DocumentVersionRecord`. `getDocumentVersion` and `uploadDocument` cannot produce a valid body from `B1`'s public surface | `B1` / seam owner |
| 2 | `DocumentVersion.display_title` is declared and nothing returns it — `GATE_B1_CLOSURE.md` item 4. Optional, so it is omitted rather than fabricated | seam owner |
| 3 | `Finding` requires `project_uid`, `version_uid` and `run_id`; `B4`'s `FindingRow` carries none of the three. The query joins `finding` and selects nothing from it | `B4` |
| 4 | There is **no by-`finding_uid` query at all**. `getFinding` has no read path in `auditmanager.findings` | `B4` |
| 5 | No query surface accepts a cursor, a limit, or a category or verdict filter, but §7 says growing lists are cursor-paginated and the document declares all four parameters. The edge pages over an ordered sequence | `B4` / `B1` |
| 6 | `listProjects` is declared "newest first"; `B1`'s `list_projects` is `ORDER BY created_at, project_uid`, which is oldest first | `B1` |
| 7 | `createProject` requires an `Idempotency-Key` and `B1` publishes no key-accepting project command, so the key is validated at the edge and stops there | `B1` |
| 8 | `appendDecision` requires the key be passed to the owning command handler; `record_decision` accepts a `command_id` and nothing in `auditmanager.decisions` claims a command record from a key. `expert_decision_event.command_id` is a foreign key into `command_record`, so the key must be *claimed*, not hashed | `B4` |
| 9 | `DocumentVersion.source_filename` is declared as an optional display field, and the `B6` brief forbids any filename crossing the boundary. It is never emitted, and the two documents disagree | contract owner |
| 10 | The frozen `DependencyUnavailable` description calls `dependency_unavailable` "the one retryable code in this surface". `idempotency_key_in_progress` is also `retryable: true` in the catalog and is reachable on every write | contract owner |

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

The twelve-operation assertion compares the router's `(operationId, method, template)`
set against the frozen document itself, never against a list in the test. Response bodies
are validated with the pinned `jsonschema` in the **governance** environment, driven
through `tests/contract/api_v1/schema_validation_check.py`; the runtime lock carries no
validator.
