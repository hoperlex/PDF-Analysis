# W13-API — the twelve operations, natively under FastAPI

**Session:** `W13-API`, stage 2 of wave 13 — the largest single piece of work in this road.
**Branch:** `agent/w13-api`, worktree `/root/w13api`. **Logs:** `/root/w13api-logs/`.
**Instance:** `gate-w13d`, PostgreSQL `55720`, S3 `59320`/`59321`, database `audit_w13d`,
bucket `auditmanager-gate-w13d`.

**The verdict, at the head, because it is the one thing the wave's acceptance turns on:**
**all 33 records of `tests/characterization/w13_baseline/` reproduce byte for byte** —
status, every header and every body byte — against the FastAPI implementation. **No record's
`response` section changed.** The wave's single permitted difference was spent by `W13-SEAL`
on record 31 and this session did not need another and did not take one. The conformance
gate's comparison reports **0 differences** between `contracts/api/v1/openapi.json` and
`create_documentation_app().openapi()`.

---

## 1. HEAD on arrival, and the base this stage actually needed

**HEAD on arrival: `cf6861cba2ad8df16a4a2fa49157d00d29c8b8f6`** (`cf6861c`,
*merge: D-10 and D-11*), which is what `origin/dev` pointed at when the brief's
provisioning step was run.

**That was the wrong base, and it was visible from the tree in about ninety seconds.** The
brief says stages 0, 0b and 1 have landed and that `W13-SEAL` "renamed a public symbol you
will touch", while telling the session to cut from `origin/dev`. At `cf6861c`:

```
git merge-base --is-ancestor 53994e1 cf6861c   -> false
git branch -a --contains 53994e1               -> agent/w13-seal, planning/prototype-roadmap
```

`W13-SEAL`'s merge (`e5861b8`) and `W13-CONF`'s (`3d3967d`) were on
`planning/prototype-roadmap` only. The contract at `cf6861c` declared no `securitySchemes`
and twenty error codes, and `tests/contract/api_v1/` held no conformance gate — so a session
that took the brief at its word would have built its 43 Pydantic models against a
twenty-code `ErrorCode` and had nothing to compare the generated document with.

**Action taken before the first model was written:** `git reset --hard e5861b8`, the tip of
`planning/prototype-roadmap`, which is the first commit carrying both the reseal and the
gate. The coordinator later pushed `origin/dev` to `49899df` (the same reseal plus
`W13-ORD`) and asked for a rebase; `e5861b8` is an ancestor of `49899df`, so the rebase was
clean and added only `W13-ORD`'s ordering work. **Everything in this review is measured at
`49899df` or later.**

Two things worth keeping from that: the check cost nothing and is the reason this stage did
not lose a day, and `W13-BASE` §6.1 recorded the *same class* of finding a wave earlier —
a dispatch and its plan disagreeing about what `dev` carried. That is now twice.

## 2. The 33 records, and the evidence that nothing else moved

`tests/characterization/w13_baseline` — **55 passed**, which is `W13-BASE`'s 38 plus
`W13-ORD`'s additions, including all 33 record comparisons and
`test_exactly_one_record_is_marked_as_the_permitted_exception`.

Three of the 33 needed product code that did not exist in the framework, and all three are
in §5. The other thirty reproduced on the first run of the finished implementation: the
first complete drive gave **39 passed, 1 failed**, and the one failure was record `26`,
whose message says *part* where a JSON body's says *property*.

### The one change to the corpus, what it was, and the proof of its extent

`T-6` puts an authorization dependency in front of all twelve operations, so the journey now
authenticates. That makes `test_the_baseline_makes_no_authorization_claim` — which reads the
**record files** and requires that none carries an `Authorization` header — assert something
false about the journey that produced them. `W13-SEAL` §8.5 anticipated exactly this:

> `test_the_baseline_makes_no_authorization_claim` **will go red the moment the journey
> authenticates**, which it should. Change it and the README paragraph together, in the same
> commit, and say which era the records then belong to.

Done, in one commit (`955c71d`), with the dependency. The records were **recaptured** by
`capture.py` rather than hand-edited — the same method `W13-SEAL` used and for the same
reason: a hand edit proves only that a file was edited, a recapture proves the other bytes
are what they were. The diff over all 33 files is:

```
33 x  - "captured_through": "auditmanager.api.routers.Request.build + dispatch, ..."
33 x  + "captured_through": "starlette.testclient.TestClient over ...create_asgi_app()"
33 x  - "pre_authorization": "Captured before the T-6 reseal. ..."
33 x  + "pre_authorization": "Captured after the T-6 seam landed. ..."
33 x  + ["Authorization", "Bearer w13-baseline-static-token"]
```

— 222 insertions, 78 deletions, and **not one line under `response`**. The status, every
header and every body byte of all 33 are what `W13-BASE` committed and what `W13-SEAL` left
record 31 as.

**This is not a use of the permitted difference and the count did not move.** The permitted
set is the set of records carrying an `exception` block; it is still exactly `31`, and
`test_exactly_one_record_is_marked_as_the_permitted_exception` is unchanged and passes. What
changed is the corpus's own description of the requests it makes, which `differences()` does
not read.

**The guard was replaced, not deleted.** `test_the_baseline_records_the_authenticated_era`
requires every record to present the configured credential, to carry a `pre_authorization`
declaration, and to pin neither `401` nor `403` — because no case here omits a credential
and none exercises a caller's rights. `test_the_authorization_era_check_can_fail` plants
four records (no credential, a different credential, a `401`, a missing declaration) and
requires each to be reported, through the **same** `_authorization_claims` function the
guard uses. The seam's own refusals moved to
`tests/integration/api/test_authorization.py`, which drives requests with no credential,
an empty one, a wrong one, and the configured token one character short and one long.

**If the integrator judges that the corpus's request metadata may not be touched at all,
the alternative is worse and should be named:** leave the files as they are, let the journey
send the credential from inside `Caller`, and the guard stays green while asserting
something untrue about every record in the directory. That is the shape `ALPHA_ROADMAP.md`
§4 calls a safety net somebody talks past at the end of a long wave.

## 3. How FastAPI's own error bodies are prevented from reaching a client

**Every failure leaves through `envelope_response` and nothing else.** Four registrations
and one middleware:

| raised by | mapped to | where |
|---|---|---|
| `DomainError` | itself — already typed | `handlers.on_domain_error` |
| `RequestValidationError` | the catalog, first error wins | `handlers.on_request_validation_error` |
| `StarletteHTTPException` | the catalog; **405 → 404**, **400 → 422** | `handlers.on_http_exception` |
| anything else | `internal_error`, or the SQLSTATE's code | `handlers.FailureEnvelopeMiddleware` |

The last row is the one a registration list cannot cover. Starlette's `ExceptionMiddleware`
answers only the classes registered *with it*; anything else reaches `ServerErrorMiddleware`,
which sends its own body — HTML in debug, `"Internal Server Error"` otherwise — **and
re-raises**. `FailureEnvelopeMiddleware` sits inside the correlation middleware and outside
the exception middleware, renders the envelope, and declines to re-raise.

Three details that are decisions rather than defaults:

* **`HTTPBearer(auto_error=False)`.** The default raises FastAPI's own `HTTPException`, and
  `{"detail": "Not authenticated"}` is not an `ErrorEnvelope`. `W13-SEAL` §8.1 names this
  trap; `test_the_twelve_are_all_behind_the_seam` is what holds it.
* **405 answers 404.** The surface declares twelve operations and no other method on any of
  their paths, so a method the document does not declare is simply not a resource here —
  and answering 405 would make the API an oracle for which paths exist. `records/29` pins it.
* **400 answers 422.** FastAPI raises exactly one 400 in this application
  (`routing.py:470`, wrapping any failure of `await request.form()`). This contract has no
  400: the status is read *from* the catalog code, never the other way round.

### The test, and the proof that it can fail

`tests/integration/api/test_no_framework_body_reaches_a_client.py`. It drives **thirteen**
requests — one of every failing kind the framework has an opinion about, including the ones
no operation declares — and requires each answer to be an `ErrorEnvelope`: `application/json`,
an `X-Correlation-Id` equal to the body's `correlation_id`, the five required properties, a
`contract_version` of `1.0.0-draft.1`, an `error_code` in the catalog, a `retryable` that
agrees with the catalog, and **no `detail` key at the top level**.

Two assertions make it more than a list of cases:

* `test_the_sweep_covers_every_status_the_framework_would_have_chosen` requires the answered
  statuses to be exactly `{401, 404, 422}` — so a case that stopped being reached is a red
  test — and that 405 and 400 are absent;
* `test_the_sweep_can_fail` runs the same checker over a **verbatim FastAPI validation
  body** and requires it to be rejected. Without that, every case above would pass against
  an application that had stopped mapping anything.

`test_an_exception_no_handler_is_registered_for_still_leaves_as_an_envelope` raises a
`ZeroDivisionError` carrying a filesystem path through a one-operation application built on
the real middleware stack, and requires `500 internal_error` with neither the path nor the
class name in the body.

## 4. The conformance gate against the real `app.openapi()`

**Yes — and it is the first time.** `W13-CONF` §6 said plainly that its gate had never seen
the real generated document, because stage 2 had not landed. It has now:

```
oc.differences(oc.surface(contract), oc.surface(create_documentation_app().openapi()))
-> []   # 0 differences
```

10 paths, 12 operations, exactly the 43 `components.schemas` names, `openapi: "3.1.0"`,
`servers: ["/api/v1"]`, and `securitySchemes.bearerAuth` = `{"type": "http", "scheme":
"bearer"}` with no `bearerFormat`.

**Wiring it is `W13-CONF`'s file and is left to it.** The entry point is
`auditmanager.api.app.create_documentation_app()`, which builds the twelve operations with
`None` behind every port — the served document is a function of the declarations and the
models, not of what sits behind the ports — so the gate needs no database, no object store
and no credential. `tests/integration/api/test_served_document_and_health_plane.py::
test_the_documented_and_the_wired_app_agree` asserts that this document is byte-identical to
the one a wired application serves, which is the assertion the gate structurally cannot
make from a tests-only stream.

### The three findings `W13-CONF` measured, and what each cost

1. **FastAPI's 422 must be displaced, not deleted.** True, and **incomplete**: it holds for
   the eight operations the contract gives a 422. **Four do not have one** —
   `getRunStatus`, `getDocumentVersion`, `getFinding`, `exportRunCsv` — and FastAPI injects
   its 422 into any operation with parameters that declares none
   (`fastapi/openapi/utils.py:517-535`; the condition is on the *absence* of a declared
   422, `4XX` or `default`, and there is no switch). See §6.1 for what this application does
   about it and why it is a statement about this application rather than a normalization.
2. **`separate_input_output_schemas=False` is required.** True, passed in `_assemble`.
3. **The multipart `encoding` is not emitted.** True. Restored with `openapi_extra` on
   `uploadDocument`. Two further things FastAPI gets wrong about that body, which the gate
   caught and the brief did not predict: it declares
   `application/x-www-form-urlencoded` for a Pydantic form model (fixed with
   `Form(media_type="multipart/form-data")`), and it spells an opaque payload as OpenAPI
   3.1's `contentMediaType: application/octet-stream` where the contract writes
   `format: binary` (fixed with `WithJsonSchema`).

Two smaller ones held: `servers=[{"url": "/api/v1"}]` with the paths declared relative to
it, and the health plane off the document entirely.

## 5. Three defects found by driving the retired reader's cases through the new surface

Not predicted by any brief. Each was a case the old `parse_multipart_upload` refused, driven
through FastAPI to see what it answered now.

| case | before this session | now |
|---|---|---|
| a `multipart/form-data` with no `boundary` parameter | **`500 internal_error`** | `422`, `Content-Type` / `boundary` |
| a part with no `name` | **`500 internal_error`** | `422`, `body` / `readable_multipart` |
| `file` sent twice | **accepted; the second one published, silently** | `422`, `body` / `unique_part` |

A fourth was **claimed and then withdrawn, by a mutation of this session's own code** —
recorded rather than deleted, because it is the most useful thing in this section. The claim
was that Starlette decodes a text part as latin-1 and so mojibakes every non-ASCII
`display_title`. It does not: `MultiPartParser.parse` reads `charset` off the request's
Content-Type and **defaults it to `utf-8`**; the latin-1 in `_user_safe_decode` is a
*fallback*, taken only for bytes that are not valid UTF-8. What Starlette does not do is
**refuse** them, which the retired reader did.

The first version of `_decoded_title` "recovered" the bytes by re-encoding latin-1 and
decoding UTF-8. Mutating it away did not redden the round-trip test, which is what sent me
to look — and what I found is that the recovery was itself a defect: `"coûts"` is valid
UTF-8 on the wire, every character is under `U+0100`, so it round-trips to `b"co\xfbts"`,
which is **not** valid UTF-8, and a perfectly good title was refused. Most titles in French,
German or Spanish. It is `agent/display-title`'s property — *the display title reaches the
reviewer who typed it* — broken by the code written to protect it.

The two cases are **indistinguishable from the decoded string**: `b"co\xc3\xbbts"` (valid)
and `b"co\xfbts"` (a fallback) both give `"coûts"`. So the refusal is dropped, deliberately
and once, and §6.6 records it. It is the only refusal of the retired reader this transport
does not reproduce.

The first two were `500`s because FastAPI parses a form **before** it resolves dependencies
(`routing.py:429`), so no application dependency can get in front of the parser. The
boundary is therefore checked on the header in `BodyCapMiddleware`, before anything reads
the body — read from the header and never from the parser's message, which is the rule
`routers/errors.py` already applies to a database driver.

## 6. Every behaviour that is not byte-identical to the certified surface, named

None of these is covered by a response-baseline record. Each is a deliberate decision and
each has a test.

**6.1 — the 422 FastAPI adds to four operations is removed from the served document.**
`app._drop_the_422_this_surface_cannot_answer` deletes an operation's `422` **only when the
response object is byte-for-byte FastAPI's injected literal**, and then drops
`HTTPValidationError` and `ValidationError`, refusing rather than leaving a dangling `$ref`.
Those four operations take a path identity and the optional correlation header and nothing
else; a malformed path identity is `404` by design and the correlation header is declared
but deliberately not enforced, so a `422` on them is a false statement about this
application. `test_a_declared_422_is_the_contracts_and_is_never_removed` asserts the eight
declared ones survive with `ErrorEnvelope`.

**6.2 — `Idempotency-Key`: an over-long or empty key reports `constraint: "length"`, not
`"pattern"`.** The contract declares `maxLength: 128` **and** the pattern; Pydantic reports
the specific one. A key outside the character class still reports `"pattern"`, and an absent
one still reports `"required"` with the exact bytes `records/27` pins. What moved is that
the envelope now names the bound that broke. `test_header_rules.py` pins all three.

**6.3 — a multipart part with an *absent* `name` reports `constraint:
"readable_multipart"`, not `"part_name"`.** Starlette raises one exception class for four
different causes (a missing part name, a part over its size bound, too many parts, too many
files) and this contract does not map refusals on another library's message text. A part
with an **empty** name parses and still reports `"part_name"`.

**6.4 — `X-Correlation-Id` is declared as the contract's `$ref` and deliberately not
enforced.** A constrained parameter is a refusable one, and four operations declare no
`422`. The certified rule — *an unusable correlation id is replaced, not refused* — is
unchanged and is now pinned by
`test_an_unusable_supplied_id_is_replaced_and_not_refused`, which did not exist before.

**6.6 — a `display_title` whose bytes are not valid UTF-8 is accepted, not refused.** §5.
`test_a_display_title_that_is_not_utf8_is_accepted_and_that_is_declared` is a *passing*
test a reader meets, rather than a sentence they have to trust — the pattern `W13-CONF`
used for its own declared blind spot under `N4`.

**6.5 — an empty query value is the absent value, preserved deliberately.** `?limit=`
returns the default and `?category=` is no filter, as `parse_limit` and `_enum_filter` did.
Pydantic would refuse both. `?cursor=` is still refused, as `decode_cursor` refused it.

## 6b. The mutation sweep

`make mutation-copy MUT=/root/w13api-mut`, baselined **green at 302** on the unmutated copy
before any red was read. `src/` is copied and `contracts/`, `docs/`, `fixtures/`, `db/` and
`tools/` are symlinks, so nothing under them can be mutated — and `tests/` is not copied at
all (`D-10`), which is why every mutation below is of product code and the suites are run
from the worktree with `-o pythonpath=/root/w13api-mut/src`.

Document-level mutations are read with the conformance engine directly, against the mutated
copy; behavioural ones are read with the suites named.

| # | Mutation | Result |
|---|---|---|
| `M1` | `405` no longer maps to `404` | `record 29`, `test_no_thirteenth_operation_answers`, the status sweep |
| `M2` | `FailureEnvelopeMiddleware` removed from the stack | **9 failed** across `test_database_refusals`, `test_error_envelope`, the framework sweep |
| `M3` | the seam admits anyone | **10 failed** across `test_authorization` and the sweep's 401 case |
| `M4` | an unconfigured token *opens* the seam instead of closing it | `test_an_application_with_no_configured_token_refuses_everything` |
| `M5` | compact JSON separators in `encode_json` | **17 records** |
| `M6` | Starlette writes the header list instead of `WireResponse` | the journey's own `Content-Length` rule, aborting the capture |
| `M7` | the repeated-part rule removed | `test_a_repeated_part_is_refused_as_unique_part` |
| `M8` | `_decoded_title` short-circuited | **did not redden** — and that is how §5's fourth finding was found |
| `M9` | the boundary check removed from `BodyCapMiddleware` | `test_a_multipart_content_type_with_no_boundary_is_refused_as_boundary` |
| `M10` | the 422 removal widened to every 422 | two cases in `test_served_document_and_health_plane` |
| `M11` | the duplicate-`operationId` rule removed | two cases in `test_router_and_body_rules` |
| `M12` | `optional_property` made a no-op | **0 differences** — see below |
| `M13` | `separate_input_output_schemas=True` | **0 differences** — see below |
| `M14` | the multipart `encoding` not restored | 1 difference, at the exact dotted location |
| `M15` | FastAPI's injected 422 left in the document | 6 differences: four operations and the two schemas |
| `M16` | `provider_mode: ProviderMode \| None = None`, the ordinary Pydantic spelling | 2 differences on `StartRunRequest.properties.provider_mode` |
| `M17` | one scalar newtype spelled `Annotated[str, ...]` instead of `TypeAliasType` | **22 differences** |
| `M18` | the transport body limit raised tenfold | 2 failed + the baseline capture aborts on `record 22` |
| `M19` | the multipart media-type check removed | two `media_type` cases |
| `M20` | a malformed path identity answers `422` instead of `404` | `record 30` |
| `M21` | the `400` from the form parser left unmapped | `test_a_part_with_no_name_is_refused_as_an_unreadable_multipart` |

**Two mutations did not redden, and both are reported rather than quietly dropped.**

* **`M12`** — `optional_property` is **belt and braces, not load-bearing.** With
  `separate_input_output_schemas=False`, FastAPI generates one schema per model in
  *serialization* mode, and Pydantic omits `default` there.
  `Model.model_json_schema()` alone — validation mode — does emit it, which is what the
  helper was written against and why the claim looked true. The helper is kept, with the
  measurement in its docstring, and the **property** it declares is now pinned directly by
  `test_no_schema_property_declares_a_default`, over the contract *and* the served
  document. `M16` shows the other half of the same spelling — the *type* — is load-bearing
  at two dotted locations.
* **`M13`** — `separate_input_output_schemas=False` is **inert at this contract's shape.**
  `W13-CONF`'s finding 2 is right about the mechanism: a model with a default is emitted
  twice as `X-Input`/`X-Output`. It does not fire here because no model in this set is used
  in both positions — the four request bodies are input-only and the response models are
  output-only. Kept, because the day `Project` appears in a request body the split is a
  conformance failure and this is the flag that prevents it.

Nothing else in this session's product code survived a mutation of itself.

## 7. The 21 coupled test files: which were re-pointed, which rewritten

**The brief's query is not the one that returns 21.** Measured at `49899df`:

```
grep -rln "api.routers\|Request.build" tests/            -> 52 paths (18 .py, 1 .md, 33 records)
grep -rln "auditmanager\.api" tests/ --include=*.py      -> 21 files
```

The 33 records match the first query because their `captured_through` string names
`api.routers`. The second query is the one that means what the brief means, and it returns
21 — but it is a *different set*: it adds `tests/e2e/pc01/test_acceptance.py`,
`tests/integration/composition/test_composition_root.py` and
`tests/integration/api/test_schema_bounds.py`, which import `auditmanager.api` without
naming `dispatch`. All three needed work. **The count was right by accident.**

### Rewritten — the helpers changed shape and a re-point would have tested nothing

| File | Why |
|---|---|
| `tests/integration/api/test_header_rules.py` | `require_idempotency_key` is a FastAPI dependency whose signature *is* the contract's parameter; `resolve_correlation_id` takes a header value, not a request. Both rules — the 128-character bound and the uniqueness of an assigned id — are asserted through the surface, and one test was **added**: an unusable supplied id is replaced and not refused |
| `tests/integration/api/test_multipart_rules.py` | `parse_multipart_upload` and `MultipartUpload` are gone. Twelve refusals are driven through `uploadDocument`, which is the only place that can show they fire in the right order — and is how §5's three defects were found. One class added: a UTF-8 title survives the round trip |
| `tests/integration/api/test_router_and_body_rules.py` | `Router`, `Route` and `decode_json_object` are gone. The duplicate-`operationId` rule had to be **rewritten as product code**, in `build_router`, because FastAPI logs a warning and serves the document anyway |
| `tests/integration/api/test_schema_bounds.py` | `parse_create_project_request` is gone. The name bound is asserted through `createProject`; the cursor bound is asserted directly **and** through `listProjects`, which is the half the sweep could not redden |
| `tests/integration/api/test_query_surface.py` (one test) | `test_every_declared_query_parameter_is_read_by_the_router_that_declares_it` watched a recording `Mapping` stand in for `Request.query`. A real client has no such seam — and watching a name be *read* never proved reading it did anything. It now supplies each declared parameter and requires the answer to change |

### Re-pointed — they drive the surface, and the surface is what moved

`tests/integration/api/driver.py` is new: a `Surface` (an `APIRouter` plus the real
`FastAPI` built from it through `create_asgi_app`), a `Request` value and an `Answer` that
reads `httpx`'s **raw** headers, so a test may still assert a header's name as the contract
spells it. It keeps the call shape these suites already speak, deliberately: there are
several hundred *which rule refused* assertions in this directory and re-typing them to a
different client's spelling would put every one at risk of a transcription slip, in the one
wave whose acceptance is "the surface did not change". **What changed is the transport;
what did not change is what the suites claim about it.**

`conftest.py`, `test_database_refusals.py`, `test_error_envelope.py`, `test_journey.py`,
`test_no_internal_identifiers.py`, `test_operation_surface.py`, `test_query_surface.py`,
`test_schema_conformance.py`, `tests/integration/composition/test_router_answers.py`,
`tests/integration/ingest/test_size_guard_boundary.py`,
`tests/integration/p02_journey/test_query_surface_over_the_corpus.py`,
`tests/integration/p02_journey/test_truncated_end_to_end.py`,
`tests/characterization/w13_baseline/journey.py`, `tests/e2e/pc01/driver.py`.

Two of those carried more than an import change:

* **`tests/e2e/pc01/driver.py` was as cheap as the brief said.** One method, `request()`,
  and the credential. Nothing else in 268 lines moved — which is what the shape promised
  and is the only prediction in the brief that was load-bearing and held exactly.
* **`test_database_refusals.py` and `test_error_envelope.py`** built two-line `Router`s
  around a failing callable. `driver.probe_surface` builds a real one-operation FastAPI
  application instead, so the probe now travels the same middlewares and handlers the twelve
  do — strictly more evidence than the old one, which exercised `dispatch`'s own try/except.

`tests/e2e/pc01/test_acceptance.py` and `tests/integration/composition/test_composition_root.py`
needed only route introspection moved from `route.method`/`route.template` to `APIRoute`'s
`methods`/`path`.

### Added

`tests/integration/api/test_authorization.py` (`T-6`),
`test_no_framework_body_reaches_a_client.py` (§3),
`test_served_document_and_health_plane.py` (`T-1` and `T-3`), and `driver.py`.

## 8. What is false, stale or incomplete in the brief

**8.1 — the base.** §1. The provisioning step and the dependency argument contradicted each
other, and the tree settled it.

**8.2 — "639 kept, 1 872 replaced" understates what is kept and what is new.** Measured at
`49899df` and at `HEAD`:

```
wc -l src/auditmanager/api/routers/*.py src/auditmanager/api/schemas/*.py
  before: 2 511      after: 3 626
git diff --numstat 49899df..HEAD -- src/auditmanager/api/
  +2 507  -1 117 across 25 files
```

`ports.py` (233) and `schemas/documents.py` (88) are **byte-identical** — `git diff` reports
no hunk for either. `errors.py` was **not** kept whole: it imported `Request`, `Response`,
`Router` and `json_response` from `http.py`, so `dispatch` and `decode_json_object` are gone
and it is 131 lines. And the **view dataclasses in `schemas/*.py` are kept**, which the
brief's figure does not allow for: they are the declared return types of the six ports and
they are constructed by `bootstrap/adapters.py`, which this session does not own. Replacing
them would have been a change to another session's file wearing this session's diff.

**8.3 — "21 coupled test files" is right by the wrong query.** §7.

**8.4 — `W13-CONF`'s finding 1 is incomplete, not wrong.** §4. Four operations declare no
422 and cannot displace one.

**8.5 — the order flake.** The coordinator has already withdrawn this: `pytest-randomly` is
not installed and `-p no:randomly` was a no-op. Recorded here because this session did pass
that flag for several hours on the brief's say-so, which cost nothing and proved nothing.
`W13-ORD` had landed by the time the two records were driven, and both pass.

**8.6 — the brief's `T-6` requirement has no configuration channel inside this session's
scope, and it is not a small gap.** The seam needs a token. `.env.example` and
`bootstrap/settings.py` are not `src/auditmanager/api/**`. Resolved by reading
`AUDITMANAGER_API_TOKEN` from the environment `create_app(environ=...)` already carries,
which needs no other file — and **fail-closed**: an application built with no token answers
`authentication_required` to everything on this surface. That is the safe default and it is
tested, but it means **a wave-14 deployment that forgets the variable gets a surface that
refuses every request**, which is a loud failure rather than an open one. Owed to somebody
outside this session: the key in `.env.example`, a field on `AppSettings`, and a line in the
deploy runbook.

**8.7 — everything else in the brief held.** The instance and its six values,
`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`, the per-worktree `.venv`, `httpx`
0.28.1 in the test group, the ports being the reason this is a transport change, the eight
pinned constraint names surviving untouched (they are raised by `auditmanager.ingest` and
pass through as `DomainError`s), record 31 being spent, `W13-BASE` §7's warning about
`provider_mode` — cases `04`, `05` and `05b` all pass — and the driver being cheap.

## 9. Findings to report, and nothing repaired outside scope

0. **`make gate` is red on `origin/dev` right now, and it is not this stage.**
   `tests/contract/api_v1/test_openapi_conformance.py::TestN7EffectiveSecurity::
   test_an_unsealed_contract_still_compares` asserts

   ```python
   assert surface(contract)["paths"]["/projects"]["post"]["security"] is None
   ```

   with the docstring *"Before the reseal, `security` is absent on both sides"*. `W13-SEAL`
   landed; the frozen contract now declares `security: [{"bearerAuth": []}]` at its root, so
   `N7`'s effective value for every operation is that requirement and the assertion is
   false. **Diagnosed rather than assumed**, because a stale test and a real defect look
   identical in a log: this session changed no file under `contracts/` or `tests/contract/`
   (`git diff --name-only 49899df..HEAD -- contracts/ tests/contract/` is empty), and the
   same case fails in a pristine worktree of `49899df`:

   ```
   git worktree add /tmp/pristine 49899df
   .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q \
     tests/contract/api_v1/test_openapi_conformance.py::TestN7EffectiveSecurity
   -> 1 failed, 5 passed
   ```

   The fix is one assertion in `W13-CONF`'s file and is left to its owner: the case is now
   the *sealed* one, and the unsealed comparison it was written for is what
   `test_a_resealed_contract_conforms_to_itself` and the synthetic unsealed copy beside it
   already cover. **Reported, not repaired** — `tests/contract/api_v1/**` is `W13-CONF`'s.

1. **`.env.example` and `AppSettings` owe `AUDITMANAGER_API_TOKEN`.** §8.6. Not added:
   outside this session's paths.
2. **`StorageBucketMissingError` still carries `validation_failed` (422) for a server
   configuration fault**, one class along from the `D-7` case `W13-SEAL` fixed. `W13-SEAL`
   §7 noticed it and left it; this session met it again while reading the storage errors and
   also left it. It is `D-7`'s shape with a different code and it is not repaired.
3. **The frontend has no branch for `401`.** `W13-SEAL` §8.6 raised it; the seam is now live,
   so every operation can answer `401` and `web/src/shared/api/errors.ts` narrows to ten
   codes that do not include `authentication_required`. A generic `ApiError` toast is not
   what an expired credential should produce. `web/**` is not this session's.
4. **Nothing under `src/auditmanager/{ingest,runs,findings,decisions,exports,storage,analysis}/**`
   changed**, and nothing under `bootstrap/**`. `git diff --numstat 49899df..HEAD -- src/`
   touches `src/auditmanager/api/**` only.

## 10. Scope kept

Written: `src/auditmanager/api/**`, the 21 coupled test files and four new ones under
`tests/integration/api/`, `tests/characterization/w13_baseline/**` (the recapture, its
guard and its README — §2), and this file. **Not** `contracts/**`, `web/**`,
`tests/contract/api_v1/**`, `pyproject.toml`, `uv.lock` or any other `src/` package. No
dependency added beyond `W13-PIN`. No tag, no push, no merge.
