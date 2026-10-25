# API v1 contract area

OpenAPI is introduced in S01/S02. Do not invent hundreds of endpoints from legacy. Add endpoints per vertical slice and freeze them before frontend implementation.

Minimum conventions:

- commands accept idempotency key where replay can duplicate effects;
- errors use domain error envelope;
- opaque IDs only;
- cursor pagination for growing lists;
- object-level authorization server-side;
- file reads return safe/scoped representations, not internal S3 key.

## Version `1.5.0`

`AR-V3-BETA-PACK-STATUS-API-01` adds the authenticated, read-only
`getArV3BetaPackStatus` operation. It reports whether a reviewed AR v3 beta pack is
installed on the server and, when it is, the pack's profile and prompt-bundle IDs, the
sealed pack digest, the six scope IDs and the reviewer attestation that came with the
manifest. The attestation is a record the server shows, not a statement that it is true;
no map, set or snapshot identity, scope digest, file path or environment value is
exposed. The surface is 92 paths, 104 operations and 300 schemas. No error code or
migration was added.

## Version `1.4.0` (historical)

`AR-V3-BETA-GROUP-API-SEAL-01` adds the authenticated, read-only
`getArV3BetaGroupReview` operation. Its six ordered members expose only verified,
review-only topics and provisional citations, or an explicit pending, failed or
verification-refused state. The surface is 91 paths, 103 operations and 298
schemas. No error code or migration was added.

## Version `1.3.0` (historical)

`AR-V3-BETA-RUN-STAGE-SEAL-01` adds a profile-specific AR v3 beta stage ID to
`RunStatus.stages` and `degradation_set`. The nine legacy `StageId` values and
analysis stage registry remain unchanged. The surface is 90 paths, 102
operations and 291 schemas. Domain, analysis and events version pins move
together.

## Version `1.2.0` (historical)

`AR-V3-BETA-SIX-RUN-02` adds explicit start and read operations for one AR v3
beta group with six durable Run IDs. Start requires an installed reviewed pack;
without one it refuses before writing. The surface is 90 paths, 102 operations
and 290 schemas. Domain, analysis and events version pins moved together.

## Version `1.1.0` (historical)

`EXEC-IMAGE-DELIVERY-01` adds `getExecutorTaskImage` and an optional image descriptor
on a claimed runner task. The binary read is restricted to the token holding the
current claim; the image bytes are checked against the saved Blob reference and
never stored a second time in the task table. The surface is 88 paths, 100 operations
and 286 component schemas; the 27 error codes and migration head are unchanged.
The domain, analysis and events `contract_version` literals move with the API.
The active text stage does not emit images.

## Version `1.0.0` (historical)

`info.version` and the `ErrorEnvelope.contract_version` const read `1.0.0` since
`BETA-CONTRACT-SEAL-01`; they were `1.0.0-draft.1`. The domain, analysis and events families
moved with them, and `getProductVersion` reports the same string. The surface the seal froze is
73 paths, 83 operations and 242 component schemas, with a 27-code error catalog. A change after
the seal follows `docs/program/VERSIONING_AND_FREEZE_POLICY.md`: an optional addition is a minor
version, a removal, a rename or a change of meaning a major one. Every consumer of the literal is
listed by `python3 tools/plan/pin_sweep.py contract-version`.

## The frozen PC-01 surface

`openapi.json` is the frozen document for the PC-01 slice, created by session `A1`
under owner decision `OD-14` and released at Gate A. It is seam `S8` of
`docs/program/P02_SEAMS.md`.

**Twelve operations at Gate A, and no thirteenth without a reseal.** Exactly the eleven
capabilities `docs/program/tasks/P2-API-01.md` enumerated. Adding an endpoint is a contract
change, not an implementation detail, and every one since was added by a recorded reseal:
the document's own `info.description` narrates each, ending with `W52-SEAL-01` (the release
version, history and account read mark), and it states the
current totals once, in its last paragraph. `tests/contract/api_v1/test_doc_prose_facts.py`
pins those totals independently.

**Authorization since `W49-SEAL-01`.** The document still declares one bearer scheme and
no format, issuer or flow. What a subject may do is the account's role set, read by the
server on every request against written registers in `src/auditmanager/api/security.py`;
a refusal is `403 permission_denied` with `required_capability` naming what is missing.
Three operations take no credential: `issueToken`, `submitRegistration` and
`readRegistrationStatus`. The domain catalog code `rate_limited` is answered by the edge in
front of `/api/v1`, before any operation, and is therefore not declared on an operation --
as the edge's own body-size refusal is not.

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
