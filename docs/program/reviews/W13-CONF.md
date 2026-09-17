# W13-CONF — the conformance gate

**Session:** `W13-CONF`, stage 3 of wave 13. Tests only; no product code was written.
**Branch:** `agent/w13-conf`, cut from `origin/dev`.
**HEAD on arrival:** `6c4b236` — *merge(W13-PIN): the FastAPI pin set, owner-ruled*.
**Instance:** `gate-w13c`, PG 55710, S3 59310/59311, db `audit_w13c`, bucket
`auditmanager-gate-w13c`. Logs in `/root/w13conf-logs/`.

**Did this gate reach the real `app.openapi()`? No — and it is said plainly in §6.**
Stage 2 (`W13-API`) had not landed when this work finished; `origin/dev` carried its brief
(`bf6086e`) and not its application. Neither had the reseal (`W13-SEAL`). What was reached
instead is in §6, and it is more than the brief expected to be possible: the comparison has
been run against a **real FastAPI-generated document**, just not against *the* one.

---

## 1. What was built

| File | What it is |
| --- | --- |
| `tests/contract/api_v1/openapi_conformance.py` | The comparison engine and the enumerated declaration of the normalization, `N1` to `N9`, each with its three answers. |
| `tests/contract/api_v1/test_openapi_conformance.py` | 85 cases: the frozen document's own pins, the comparison's properties, a planted difference for every declared normalization, the six the brief names by hand, and a real FastAPI application generating a real document. |

Both sit in `tests/contract/api_v1/`, whose quarantine was narrowed in wave 11 — the three
CP-00 files are excluded from the gate and the five subdirectories are in it, so these run
in `make gate`. Verified against `run_battery()` in the `Makefile` (lines 464–499), whose
`--ignore` list names the three files and not the directory.

The engine is a module beside the test rather than inside it, so the same comparison serves
the planted differences and the eventual wiring without being written twice. The brief asked
for the normalization "enumerated in the test file itself"; it is enumerated in test-tree
source, in the engine's module docstring, and the split is made **safer** than a single file
by `test_every_declared_normalization_has_a_planted_difference`, which reads the identifiers
the engine declares and fails unless this file carries a planted-difference class for each.
Adding an `N10` to the engine without proving the comparison can still fail through it is
itself a failure. Shown red under mutation `M6` in §4.

## 2. The declared normalization, entry by entry

Every entry answers **what differs**, **why FastAPI produces it**, and — the one that
decides whether this gate is worth anything — **why erasing it cannot hide a semantic
change**. The full text is in the engine's docstring; the third answers are reproduced here.

**`N1` — `$ref`s into `components.parameters`, `components.responses` and
`components.headers` are resolved in place.**
*Third answer:* a `$ref` **is** its target — the specification defines it as substitution.
The component key (`NotFound`, `RunId`) is a spelling of the document's internals and is not
observable by any caller. Resolution replaces a name with the thing it names, on both sides,
and the resolved objects are then compared in full. `components.schemas` refs are
deliberately **not** resolved: inlining those would make a renamed schema invisible, which
is the exact drift this gate exists for.
*Both directions proven:* `test_component_key_rename_is_invisible` (rename the key
everywhere → nothing reported) and `test_changed_component_target_is_caught` (change what it
resolves to → reported at all ten operations that reference it).

**`N2` — path-item parameters are merged into every operation of that item.**
*Third answer:* the specification says a path-item parameter applies to every operation of
that item and that an operation-level entry with the same `name` and `in` overrides it. The
merge computes exactly that effective set, on both sides. The override rule is not a hole —
an operation that redeclares the path parameter with a different schema is reported.
*Proven:* `test_parameter_moved_to_operation_level_is_invisible`,
`test_dropped_path_level_parameter_is_caught`,
`test_an_operation_level_override_wins_and_is_compared`.

**`N3` — parameters become a map keyed by `{in}:{name}`, response headers a map by name,
and `required` and `enum` are sorted.**
*Third answer:* the specification gives parameter order no meaning and **requires**
`(name, in)` to be unique within an operation, so the map is lossless — a collision is
impossible and an added, removed or renamed parameter changes the key set. `required` and
`enum` are unordered by JSON Schema; sorting cannot merge two members or drop one, so any
addition, removal or rename still changes the sorted list.
*Proven:* `test_reordered_parameters_are_invisible`,
`test_reordered_required_list_is_invisible`, `test_changed_required_list_is_caught`,
`test_changed_enum_member_is_caught` (the `published` → `succeeded` probe, on the Python
side of the same contract the frontend guard probes), `test_a_dropped_parameter_is_caught`,
`test_a_relaxed_parameter_requirement_is_caught`.

**`N4` — annotation-only keywords are dropped: `description`, `summary`, `title`,
`examples`, `example`, `externalDocs`, `info`, and the document's top-level `tags` array.**
*Third answer:* these are display strings; none validates a request, selects a response,
names a field or constrains a value. Erasing them removes no identity — a schema's identity
is its `components.schemas` key, a property's is its key in `properties`, an operation's is
its `operationId`, and all three are compared. The walker goes by JSON Schema **keyword
position**, never by key spelling, so a schema with a property literally named `description`
or `title` keeps it (`test_a_property_named_description_is_not_mistaken_for_prose`).
The top-level `tags` array is listed separately because it earns its own answer: that array
names and describes the groups a documentation UI draws, while an operation's membership of
a group is the operation's own `tags`, which **is** compared. Removing the array cannot
change which operations exist, what they accept or what they answer.
***The cost, stated rather than hidden.*** A rule recorded **only** in a `description` is
outside this gate. That is the one declared blind spot and it is recorded as a passing test,
`test_changed_description_is_deliberately_invisible`, rather than as a promise in prose — so
a reader meets it instead of trusting it. `test_the_top_level_tag_list_is_deliberately_not_compared`
does the same for the tag array. The boundary is shown beside them:
`test_changed_pattern_is_caught`, `test_a_dropped_length_bound_is_caught`,
`test_a_relaxed_closure_is_caught` — prose moves freely, constraints do not.

**`N5` — the two-branch nullable union is canonicalized to `anyOf` with the null branch
last.** The contract spells its 21 optional fields `{"oneOf": [S, {"type": "null"}]}`;
pydantic spells `S | None` as `anyOf`.
*Third answer:* the rewrite fires **only** on a union of exactly two branches, one of which
is exactly `{"type": "null"}` **and nothing else**. For that shape `oneOf` and `anyOf` accept
exactly the same documents: `null` matches the null branch, and matches `S` only if `S`
itself admitted null — in which case the contract's own `oneOf` would already be
unsatisfiable for `null`, so the frozen document cannot be relying on the distinction. Every
other `oneOf`, `anyOf` and `allOf` is left as written and compared branch by branch, and the
inner branch `S` is still compared in full.
*Proven, including the narrowness:* `test_oneof_to_anyof_nullable_is_invisible`,
`test_dropped_null_branch_is_caught`, `test_changed_nullable_inner_branch_is_caught`,
`test_a_three_branch_union_is_not_normalized`,
`test_a_two_branch_union_without_a_null_is_not_normalized`,
`test_a_null_branch_carrying_anything_else_is_not_normalized`.

**`N6` — a `type` that only restates the JSON type of a sibling `const` is dropped.**
*Third answer:* dropped **only** when the declared `type` is the JSON type of the `const`
value, where it admits every value `const` already admits and therefore constrains nothing.
When the two disagree — `{"const": "x", "type": "integer"}`, a schema nothing can satisfy —
the `type` is **kept** and the difference is reported.
*Proven:* `test_type_beside_const_is_invisible`, `test_changed_const_is_caught`,
`test_contradictory_type_beside_const_is_caught`,
`test_the_contract_version_const_is_still_compared`.

**`N7` — an operation's security is reduced to its effective value.**
*Third answer:* the specification defines the effective value exactly — an operation's own
`security` if present, otherwise the root's. Computing it on both sides compares the thing
that decides whether a caller needs a credential; where the declaration is written has no
effect on that.
*Proven:* `test_a_resealed_contract_conforms_to_itself`,
`test_security_moved_from_root_to_operation_is_invisible`,
`test_dropped_operation_security_is_caught`, `test_a_dropped_security_scheme_is_caught`,
`test_a_weakened_security_scheme_is_caught`, `test_an_unsealed_contract_still_compares`.

**`N8` — a JSON number is compared by value, so an integral float equals the integer.**
Not anticipated: **found by generating a document.** The contract writes `"maximum": 30`;
FastAPI 0.141.1 with pydantic 2.13.5 writes `"maximum": 30.0` for the same bound.
*Third answer:* JSON has a single number type — `30` and `30.0` are the same JSON value and
no JSON Schema keyword can tell them apart. The comparison therefore compares **numbers** by
value and only numbers: `bool` is excluded deliberately, because `True` is an `int` in
Python and is not a number in JSON, so a required flag that became the integer one is still
reported. A bound that actually moved still fails.
*Proven:* `test_an_integral_float_bound_is_invisible`, `test_a_fractional_bound_is_caught`
(`30` vs `30.5`), `test_a_widened_numeric_bound_is_caught` (`30` vs `3000`),
`test_a_boolean_is_never_a_number`, `test_a_string_that_looks_like_a_number_is_not_one`,
`test_a_true_is_not_a_one`.

**`N9` — an HTTP header's name, as a parameter or a response header, is compared case
insensitively.** Also found by generating a document: FastAPI's `Header()` turns
`x_correlation_id` into a parameter named `x-correlation-id`, not `X-Correlation-Id`.
*Third answer:* RFC 9110 §5.1 makes HTTP field names case insensitive — the two spellings
are the same header to every client, server and proxy, so they cannot denote different
headers. The fold applies **only** to `in: "header"` parameters and response header names.
Query and path parameter names, schema property names and media types are case *sensitive*
and are compared exactly as written.
*Proven, including every boundary:* `test_a_lowercased_header_name_is_invisible`,
`test_a_renamed_header_is_caught`, `test_a_recased_query_parameter_is_caught`,
`test_a_recased_schema_property_is_caught`, `test_a_recased_media_type_is_caught`.

**A note for the integrator.** `N9` is the one entry where a reasonable person could rule the
other way: stage 2 could be required to pass `Header(alias="X-Correlation-Id")` on twelve
operations and the fold removed. The spec-grounded reading is taken here, but it is a
decision and not a fact, and it is the only entry of the nine for which that is true.

## 3. What is compared after all of that

The `openapi` version string and the `servers` base paths; the set of paths and, per path,
the set of methods; per operation the `operationId`, `tags`, effective `security` and
`deprecated`; per parameter its `in`, `name`, `required` and its schema in full; the request
body's `required`, media types, schemas and **`encoding`**; per response the status code, its
media types and their schemas, and every response header with its `required` flag and
schema; `components.securitySchemes`; and all 43 `components.schemas` in full, including
`additionalProperties`, `pattern`, `minimum`, `maximum`, `minLength`, `maxLength`, `format`,
`const`, `enum`, `required` and every `$ref` target.

A difference names **what** and **where**:

```
paths./runs/{run_id}/export.csv.get.responses.200.headers.content-disposition:
  missing from the generated document (the contract has {...})
```

The three measured figures are pinned as literals — `"3.1.0"`, twelve operations, 43 schemas
— together with the twelve `(method, path, operationId)` triples and the 43 schema names
written out, so a contract that loses an operation fails at the pin rather than quietly
shrinking the surface both sides are compared through.

## 4. The evidence each planted difference fails the comparison

Two independent bodies of evidence.

### 4.1 The planted differences, permanent in the tree

**The six the brief names by hand**, each asserted to be reported at an exact dotted
location:

| Planted | Reported at |
| --- | --- |
| a moved `operationId` (`listProjects` ⇄ `getRunStatus`) | `paths./projects.get.operationId` and `paths./runs/{run_id}.get.operationId`, and **only** those two |
| a dropped response header | `paths./runs/{run_id}/export.csv.get.responses.200.headers.x-correlation-id` |
| a renamed schema property (`current_verdict` → `verdict_now`) | `schemas.Finding.properties.current_verdict` and `…verdict_now` |
| a changed `required` list (`sha256` removed) | `schemas.DocumentVersion.required` |
| a status code moved (`201` → `200` on `createProject`) | `paths./projects.post.responses.201` and `…200` |
| a media type changed (`text/csv` → `application/csv`) | `paths./runs/{run_id}/export.csv.get.responses.200.content.text/csv` and `…application/csv` |

Plus, beyond the six: a renamed schema, a missing operation, a missing path, an extra
operation (the `T-3` health plane leaking onto the contract surface), an extra schema
(`HTTPValidationError`), an undeclared 422, a changed HTTP method, a changed request-body
media type, a dropped multipart `encoding`, a relaxed request-body requirement, a changed
base path, a changed `openapi` version, a changed operation tag, a widened numeric bound, a
changed parameter default, a changed response-header schema, a response header that stopped
being required, and a dangling `$ref` refused rather than ignored.

**Every plant is applied to the pristine document and then re-spelled by
`fastapi_flavoured()`**, so each one is shown to survive the entire normalization rather
than merely to exist. `test_the_fastapi_flavour_is_invisible` asserts the comparison reports
nothing against that re-spelling, and `test_the_flavour_really_did_change_the_bytes` asserts
the re-spelling really did change the document — without which the first test would only
prove a document equals itself.

### 4.2 The engine mutation sweep — the proof the *tests* are not vacuous

The planted differences show the comparison can fail. They do not by themselves show the
suite would notice a comparison that had been *weakened*. Eleven mutations were applied to a
scratch copy of the tree (`/root/w13conf-enginemut`, since `make mutation-copy` copies
`src/` and not `tests/`), baselined green unmutated at 85 passed, and run:

| Mutation | Result |
| --- | --- |
| `M1` `differences()` always returns `[]` | **43 failed**, 27 passed |
| `M2` `N4` widened to swallow `pattern` | `test_changed_pattern_is_caught` |
| `M3` `N5` widened to any two-branch union | the two narrowness tests |
| `M4` `N6` widened to drop `type` beside any `const` | `test_contradictory_type_beside_const_is_caught` |
| `M5` `N1` extended to resolve `components.schemas` too | **51 failed**, 19 passed |
| `M6` an `N10` declared in the engine with no planted difference | `test_every_declared_normalization_has_a_planted_difference` |
| `M7` `N2` drops path-item parameters instead of merging them | **14 failed**, 56 passed |
| `M8` `N8` widened, the `bool` exclusion removed | `test_a_true_is_not_a_one`, `test_a_boolean_is_never_a_number` |
| `M9` `N9` widened to lowercase every parameter name | `test_a_recased_query_parameter_is_caught` |
| `M10` `N8` removed, numbers compared by Python type | `test_an_integral_float_bound_is_invisible` and the real-generator test |
| `M11` `N9` removed, header names compared case sensitively | four cases and the real-generator test |

Every mutation reddened, and each reddened the cases it should and not others.

**Method, per `OPERATING_CONSTRAINTS.md` §12's standing rule that a report saying "measured"
is worth what its query is worth:**

```
tar cf - --exclude=.git --exclude=.venv --exclude=web --exclude=.local \
    pyproject.toml contracts tests src | (cd /root/w13conf-enginemut && tar xf -)
cd /root/w13conf-enginemut && \
  /root/w13conf/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q \
    tests/contract/api_v1/test_openapi_conformance.py -p no:randomly
```

at `e8ecc09`, with the engine restored between mutations and the unmutated baseline re-run
first. The suite resolves the engine from `Path(__file__).parent`, so a copy of the tree
loads that copy's engine — which is why the sweep works at all, and why the resolution is
written that way.

## 5. `OPERATING_CONSTRAINTS.md` §12 — which side of the line each read is on

* **Expectations are literals.** The twelve `(method, path, operationId)` triples, the 43
  schema names, `"3.1.0"`, `"/api/v1"`, the nine normalization identifiers, and the exact
  dotted location every plant must be reported at. None is computed from the document or
  from the engine.
* **The contract is read as an authority**, from `Path(__file__).resolve().parents[2]`,
  which §12 names as the opposite case and which
  `tests/integration/exports/test_frozen_column_list.py` resolves the same way. It is
  re-read from disk on **every run**, never cached at import, because `W13-SEAL` reseals it
  during this same wave.
* **The engine is resolved from a path that moves with a mutation copy**
  (`Path(__file__).parent`), which is what makes §4.2 possible.
* **Both spellings searched.** The `oneOf`/`anyOf` census that produced `N5` was run over
  both keywords, not the one the contract happens to use; the `const` census over `const`
  and `type` together.

## 6. Whether the real `app.openapi()` was reached — said plainly

**No.** Stage 2 had not landed. At the last fetch `origin/dev` was `bf6086e`, which adds
`docs/program/dispatch/W13-API.md` and nothing under `src/auditmanager/api/`; that directory
still holds the hand-rolled `Router`/`http.py`/`multipart.py` layer. `W13-SEAL` had not
landed either — `origin/dev`'s contract still declares no `securitySchemes` and 43 schemas.
**A gate that has never seen the real generated document is not finished, and this one has
not.** Wiring it is one file and should not be done by guessing at the app's entry point.

What *was* reached goes further than stopping there. FastAPI is pinned in this tree
(`W13-PIN`, `6c4b236`), so `TestAgainstARealGeneratedDocument` builds a **real FastAPI
application** — a `MINIATURE_CONTRACT` literal written in the frozen document's own
spellings, and a FastAPI app implementing it the way stage 2 will — calls `app.openapi()`,
and asserts the comparison reports **nothing**. `test_the_generated_document_really_is_spelled_differently`
then asserts, on that same real document, that every one of the nine differences the
normalization claims to erase is genuinely present in it. So the declarations in §2 are
measured against FastAPI 0.141.1 and pydantic 2.13.5, not assumed — which is how `N8` and
`N9` were found at all, and what remains untested is only the twelve operations themselves.

### What remains, and what stage 2 will have to do about it

Three things measured here that stage 2 needs, offered as findings and not instructions:

1. **FastAPI's own 422 must be displaced, not deleted.** There is no switch that removes it.
   Declaring the contract's own `422: {"model": ErrorEnvelope, "headers": {...}}` in the
   decorator replaces it entirely and `HTTPValidationError` and `ValidationError` then never
   enter `components.schemas` — measured. An operation that omits it gets FastAPI's, and the
   gate reports it in three places (`test_the_gate_catches_fastapis_own_validation_error`).
   This is the criterion-10 regression the `W13-API` brief calls the wave's highest risk,
   and the gate fires on it.
2. **`separate_input_output_schemas=False`** is needed, or a model with a default is emitted
   twice as `X-Input`/`X-Output`. The 43 names are pinned, so the split fails the gate — the
   fix belongs in the application, never in the normalization
   (`test_the_gate_catches_a_split_input_and_output_schema`).
3. **The multipart `encoding` is not emitted by FastAPI.** The contract declares the `file`
   part of `uploadDocument` as `application/pdf`, in
   `requestBody.content.multipart/form-data.encoding.file.contentType`. That is a declared
   constraint on the part and it is compared, so stage 2 has to put it back — `openapi_extra`
   is the usual route. `test_a_dropped_multipart_encoding_is_caught` is the case that says
   so rather than letting it disappear.

Two smaller ones: the application must pass `servers=[{"url": "/api/v1"}]` rather than
pushing the prefix into the paths (`test_a_changed_base_path_is_caught`), and the health
plane of `T-3` must stay off this document entirely
(`test_an_extra_operation_is_caught`).

## 7. The two existing drift guards, and what each covers that this one does not

Both were read before a line of this was written. **This gate duplicates neither.**

**`web/tests/contract/openapi-drift.contract.test.ts`** guards the *frontend's* copy and the
*generated client*. It covers four things this gate does not:

* that `web/openapi/openapi.json` is **byte-identical** to `contracts/api/v1/openapi.json`
  — descriptions, examples, key order and all. That is precisely the prose this gate drops
  under `N4`, so the frozen document's prose is guarded, just not by me;
* that the four committed client files are exactly what the contract generates, that nothing
  was hand-edited, and that no extra file appeared in the generated directory;
* that regeneration is deterministic and emits no timestamp, hostname or absolute path;
* that the generator **refuses** a document with a missing `operationId` or a non-3.1
  version.

Its axis is *contract → TypeScript client*. Mine is *contract → generated Python document*.
Neither can see the other's drift: it would not notice a FastAPI application whose 422
carries the wrong body, and this gate would not notice a hand-edited `types.gen.ts`.

**`tests/integration/exports/test_frozen_column_list.py` (`W10-FND`)** pins the seventeen
CSV column names and their order as literals, against `docs/program/P02_SEAMS.md` §6 and
`web/src/shared/api/csv-columns.ts` — the frontend's independent copy. It covers what this
gate structurally cannot: **the bytes inside a `text/csv` response body.** The contract
describes that body as `{"type": "string", "format": "binary"}` and nothing more, so no
comparison of OpenAPI documents can reach the column list, the sort key or the
header-when-empty rule. It also catches the wave-9 defect shape directly — the assertion it
replaced was `header == list(COLUMNS)`, both sides moving together.

**What this gate covers that neither does:** whether the document FastAPI *generates at
runtime* still declares the same twelve operations, parameters, status codes, media types,
response headers, security and 43 schemas as the frozen contract. Before wave 13 there was
no generated document to drift; `T-1` creates the second authority, and this is the machine
that checks it. The three guards are `contract → client`, `contract → CSV bytes`, and
`contract → served schema`, and the third had no guard until now.

## 8. Anything false in this brief

**One material stale premise, and it is not in the brief's argument — it is in the tree.**

> *"Gate: `make gate`. Expect **1543 passed / 5 skipped / 167 subtests**."*

`make gate` on the arrival tree, at `6c4b236`, **before this session wrote a line**, gives
**1 failed, 1542 passed, 5 skipped, 167 subtests**, exit 2. The red is not mine and is not in
anything I own:

```
FAILED tests/characterization/w13_baseline/test_response_baseline.py::
       test_the_response_reproduces_the_record[16-listProjects.success]
  expected ..."created_at": "{{ts_4}}"}], "page": {"next_cursor": "{{next_cursor}}"}}
  got      ..."created_at": "{{ts_3}}"}], "page": {"next_cursor": null}}
```

**Diagnosed, because a stale figure and a real defect look identical in a log.** That record
drives `GET /projects?limit=1` (`journey.py:849–878`). `next_cursor` is non-null only when a
**second project already exists in the shared database**, and `journey.py` knows it — it
guards the cursor assertion with `if cursor is not None:`. The record was captured in a
database that held other projects, so it froze the branch where the cursor is present. The
suite therefore depends on residue that the rest of the battery also writes.

Measured, both queries:

* `.venv/bin/pytest tests/characterization/w13_baseline -p no:randomly` in isolation →
  **38 passed**, against a database then holding 29 projects;
* the same tests inside `make gate`'s battery → **1 failed**, with the page reporting
  exactly one project.

So `16-listProjects.success` is **order- and residue-dependent**, and it is `W13-BASE`'s
deliverable, not mine. This matters beyond a counting discrepancy: the response baseline is
the wave's safety net, and stage 2 is about to be judged by it. A record that can flip on
database residue is the one that will be argued past at the end of a long wave, exactly as
`ALPHA_ROADMAP.md` §4 warns about a safety net with an unnamed exception. **Reported to the
integrator; not fixed here — `tests/characterization/` is not mine to write.** The likely
repair is to have the case create a second project of its own so the cursor is present by
construction rather than by luck.

Everything else in the brief checked out against the tree: `6c4b236` is `origin/dev`'s head
on arrival and `import fastapi` works; the contract is OpenAPI 3.1.0 with 12 operations and
43 schemas; `tests/contract/api_v1/` is in the gate and the three CP-00 files are the
`--ignore` list; `make mutation-copy` does symlink `contracts/` without `FULL=1`; both
existing drift guards exist and say what the brief says they say.

**Two brief premises that were simply not yet true, stated so they are not read as claims:**
`W13-SEAL` is described as "running now", and stage 2 as building the app beside me. At the
last fetch neither had landed on `origin/dev` — no `securitySchemes` in the contract, no
FastAPI application in `src/`. The comparison was built to handle the resealed contract
anyway (`N7`, and `TestN7EffectiveSecurity` runs every case against a synthetic resealed
copy), and it re-reads the contract from disk on every run rather than caching it, which is
what the brief asked for.

**One small correction to the brief's own framing.** It says `make mutation-copy` is how to
show the gate can fail. For a tests-only stream that is not quite right: `mutation_copy`
copies `src/`, `contracts/`, `db/`, `docs/`, `fixtures/` and `tools/` — **not `tests/`** — so
it cannot mutate this gate's engine. The sweep in §4.2 uses a scratch copy of the tree
instead, and the engine is resolved from `__file__` so that this works.

## 9. Figures

| | |
| --- | --- |
| New tests | **85**, all in `tests/contract/api_v1/test_openapi_conformance.py` |
| New product code | **none** |
| New dependencies | **none** — FastAPI and pydantic were pinned by `W13-PIN` |
| Files touched outside my ownership | **none** |
| `make gate` on arrival, `6c4b236` | 1 failed, 1542 passed, 5 skipped, 167 subtests; foundation 35; exit 2 |
| `make gate` with this work | recorded in §10 |
