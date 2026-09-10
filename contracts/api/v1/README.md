# API v1 contract area

OpenAPI is introduced in S01/S02. Do not invent hundreds of endpoints from legacy. Add endpoints per vertical slice and freeze them before frontend implementation.

Minimum conventions:

- commands accept idempotency key where replay can duplicate effects;
- errors use domain error envelope;
- opaque IDs only;
- cursor pagination for growing lists;
- object-level authorization server-side;
- file reads return safe/scoped representations, not internal S3 key.

## The frozen PC-01 surface

`openapi.json` is the frozen document for the PC-01 slice, created by session `A1`
under owner decision `OD-14` and released at Gate A. It is seam `S8` of
`docs/program/P02_SEAMS.md`.

**Twelve operations, and no thirteenth.** Exactly the eleven capabilities
`docs/program/tasks/P2-API-01.md` enumerates. Adding an endpoint is a contract change,
not an implementation detail.

| Consumer | What it does with this file |
|---|---|
| `A5` | generates `web/src/shared/api/generated/**` from it, deterministically |
| `B6` | implements `src/auditmanager/api/routers/**` against it |
| `B7`, `B8` | use `A5`'s generated client and never call `fetch` directly |

### Why JSON rather than YAML

The runtime lock carries no YAML parser and adding a root dependency is a
single-owner task under FF-01 §2.8, not a lane decision. JSON is parseable by the
standard library, by the governance environment's `jsonschema`, and by every
TypeScript generator. A YAML document would have needed a dependency to validate its
own gate.

### Validating it

```sh
.venv/bin/pytest tests/contract/domain_p02/test_openapi_document.py
.venv/bin/pytest tests/contract/api_v1
.venv/bootstrap/bin/python tests/contract/domain_p02/openapi_metaschema_check.py
```

The first runs in the runtime environment with the standard library alone, and never
skips. It checks the document's structure, that every `$ref` resolves, that no
component is unreachable, that every enum drawn from a frozen contract equals that
contract, that every identity carries its contract pattern, and that nothing in the
surface leaks an address, a credential or a model payload.

The second runs under the governance interpreter, which is the only one carrying
`jsonschema`, and validates every schema object against JSON Schema 2020-12 —
meaningful because OpenAPI 3.1 aligned its Schema Object with that dialect.

### Closed shapes, and why nothing here uses `allOf`

Response shapes are `additionalProperties: false`, because this repository refuses
silent extra fields: a field added without a contract change must fail, not pass.

That closure does not survive composition. Under JSON Schema 2020-12 — the dialect
OpenAPI 3.1 adopts — `additionalProperties` is evaluated against the property
annotations of **its own** schema object, and sibling `allOf` branches contribute
nothing to it. So `allOf: [{$ref: <a closed schema>}, {properties: {...}}]` rejects
the very properties the second branch adds. `FindingDetail` was written that way and
could never validate the body `GET /findings/{finding_uid}` returns; session `A5`
found it, `A7-FIX` repaired it by restating `FindingDetail` as one closed object.

**So: a schema that extends another restates it, and stays closed.** The document
contains no `allOf` at all. The alternative that is idiomatic in plain JSON Schema —
an open base plus `unevaluatedProperties: false` on each composed schema — is
correct, and was rejected here because it requires the base to stop declaring
`additionalProperties: false` itself, which is the property
`tests/contract/domain_p02/test_openapi_document.py` asserts directly.

Restating costs duplication, and `tests/contract/api_v1` pays it down: it asserts
`FindingDetail` is `Finding`'s property set plus exactly `latest_comment` and
`decision_event_count`, compares the shared entries by value, and searches the whole
document for any `allOf` composing a `$ref` to a closed schema. Drift is a test
failure rather than a silent divergence.

### Changing it

A breaking change is a new contract version — `contracts/api/v2/**` — never an edit
here. The frozen document stays as the record of what was promised.

A non-breaking addition is still a change to a file every Gate B and Gate C session
consumes: it goes to the integrator with the failing test that motivates it, per
`docs/program/P02_SEAMS.md` §10.
