# API v1 contract area

OpenAPI is introduced in S01/S02. Do not invent hundreds of endpoints from legacy. Add endpoints per vertical slice and freeze them before frontend implementation.

Minimum conventions:

- commands accept idempotency key where replay can duplicate effects;
- errors use domain error envelope;
- opaque IDs only;
- cursor pagination for growing lists;
- object-level authorization server-side;
- file reads return safe/scoped representations, not internal S3 key.

## Combined current contract `1.13.0`

The serial CMP integrator reconciles C2–C4 with owner hotfixes06b94745/99b337fb.
The current API has228paths/254operations/614schemas; migration head0043.
Both StartRunRequest and StartArV3BetaGroupRequest retain optional relaxed_limits.
Comparison evidence, spend consent, expert review and the stage APIs remain present.
The records below describe their own historical seals, rather than the combined counts.

## Comparison C2 seal `1.11.0` (historical branch)

`CMP-SEAL-C2` (wave C2 of the comparison modules, `docs/architecture/adr/ADR-0025-comparison-modules.md`)
adds the version comparison AI, specifications, launch queue and reports as sealed stubs, every operation
answering `503 dependency_unavailable` until its lane wires it, and `comparison_modules` first while the
«Сравнение версий» module is off. The AI check of the doubtful pairs of a document set
(`estimateComparisonAiPairCheck`, `startComparisonAiPairCheck`, `getComparisonAiPairCheck`, the three controls and
`listComparisonAiPairHints`); the AI description of changes, per series (estimate, start, read and six
controls: pause, resume, cancel, «Досчитать», «Убрать из очереди», «Повторить листы с ошибкой») and per sheet pair
(read, history, estimate, start, MD of one sheet) with the «Проверить» list of a transition; the deterministic
positions of a specification page and sheet pair and the AI comparison of whole specifications per transition;
the launch queue of a project and the installation's AI queue; and the deterministic MD summary of a series and
the PDF reports (a draft with its estimate, then a start that consents to it, continue, «Пересобрать PDF»,
delete, «Подготовить отчёт для заказчика», the downloads). Fifty in all. Every AI start carries the
digest of the estimate it consents to, in micro-USD, with the ceilings of USD 10 per job and USD 50 per day for
the installation and a pause when the spend passes 1.2 times the estimate (a connection that is not metered has
no ceiling). Reads are any one role; every write is keyed and an expert's act. `ExecutorWorkKind` gains
`comparison_pair_check`, `comparison_sheet_changes`, `comparison_spec` and `comparison_report`. The contract
items wave C1 left: `ComparisonMatrixStaleReason` gains `algorithm_changed`, `ComparisonMatrixColumn` gains
`label_source`, `ComparisonPairPage` gains `raster`, and `startComparisonSeries` states
`comparison_matrix_stale` and `comparison_versions_few`. The version rule
(`docs/program/VERSIONING_AND_FREEZE_POLICY.md`) reads this as a **minor**. The surface is 176 paths, 198
operations and 517 schemas (131, 148 and 432 under `1.10.0`). No error code is added. Migration
`0040_comparison_ai_reports` adds twelve tables and widens `ck_executor_route_work_kind`.

## Owner hotfix seal `1.12.0` (historical branch)

`HOTFIX-SECTION-LIMITS-BACKEND-20261030` adds optional `relaxed_limits` to
`startRun` for all 14 non-AR sections. True selects a separate immutable
profile/bundle pair with a 64,000-token output request and disables the
application's per-Run cost halt. The 12-window operational size bound remains.
Absent or false keeps the old behavior. This is an additive minor change:
131 paths, 148 operations and 432 schemas remain.

## Owner hotfix seal `1.11.0` (historical branch)

`HOTFIX-AI-LIMITS-20261030` adds the optional `relaxed_limits` boolean to
`startArV3BetaGroup`. Absent or false preserves the current cost ceiling and
16,000-token output request. True selects no application cost halt for the six
created Runs and requests up to 64,000 output tokens; provider limits can still
refuse the request. The flag is part of the command fingerprint and is saved with
the group command so workers retain it after a restart. This is an additive
minor change: 131 paths, 148 operations and 432 schemas remain.

## Version `1.10.0`

`CMP-SEAL-C1` (wave C1 of the comparison modules, `docs/architecture/adr/ADR-0025-comparison-modules.md`)
adds the version comparison core as sealed stubs, every operation answering `503 dependency_unavailable`
until its lane wires it. The effective matrix of a document set: `getComparisonMatrix`,
`prepareComparisonMatrix`, `applyComparisonMatrixEdits` (a keyed batch that carries the base matrix revision;
a stale base is `409 conflict`), `undoComparisonMatrixEdit`, `listComparisonMatrixEdits` and
`listComparisonAiLinks` (read-only until wave C2). The series of adjacent transitions: `startComparisonSeries`,
`listComparisonSeries`, `getComparisonSeries`, `pauseComparisonSeries`, `resumeComparisonSeries`,
`cancelComparisonSeries` and `finishComparisonSeries`; the sheet pairs of a transition:
`listComparisonSheetPairs`, `getComparisonSheetPair` and `streamComparisonPairTile`; and the read models
`getComparisonOverview` and `getComparisonQueueSummary`. Reads are any one role, every write is keyed and an
expert's act. `CreateComparisonUploadRequest` gains the optional `compare_after_preparation`. While the
«Сравнение версий» module is on, `approveSheetPairing`, `withdrawSheetPairing` and `generateComparisonSummary`
answer `503 dependency_unavailable` (`comparison_versions_module`). The version rule
(`docs/program/VERSIONING_AND_FREEZE_POLICY.md`) reads this as a **minor**. The surface is 131 paths, 148
operations and 432 schemas (115, 130 and 351 under `1.9.0`, which sealed the comparison upload, the order of
the versions of a document set and the page reads). No error code is added. Migration `0039_comparison_core` adds
seven tables and migrates the active approvals of `0035` into manual matrix edits.

## Version `1.8.0`

`CONTRACT-1-8-0-01` seals the content that `COMPARE-PERSISTED-SUMMARY-01` added under `1.7.0` (owner
ruling `R-146ar`). Three operations: `approveSheetPairing` and `withdrawSheetPairing` (an expert stores
and ends the approval of one sheet pair that `compareDocumentVersions` proposed, append-only, keyed and
refused to an account without `expert`) and `generateComparisonSummary` (an expert asks once for an AI
summary over the approved pairs; only a recorded implementation exists, any other mode answers
`503 dependency_unavailable`). `compareDocumentVersions` gains the optional and nullable
`approved_pairs`, with the optional `summary`. The version rule
(`docs/program/VERSIONING_AND_FREEZE_POLICY.md`) reads this as a **minor**: operations, schemas and
optional fields are added and nothing disappears. The surface is 98 paths, 111 operations and 321
schemas (92, 104 and 301 under `1.7.0`). No error code or migration is added by the version move; the
content came with migration `0035_comparison_records`.

`ANALYSIS-PRESETS-01` (owner ruling `R-146av`) adds, under the same `1.8.0`, the named presets of how a run
starts: `listAnalysisPresets` (any role), `createAnalysisPreset`, `reviseAnalysisPreset` and
`archiveAnalysisPreset` (an administrator, keyed; a revision and an archive are new rows of an append-only
history), the optional `StartRunRequest.preset_id` (exclusive with `executor_connection_id`) and the
optional, nullable, read-only `RunStatus.preset`. A run start selects one setting per run, the executor
connection, so a preset is a name and that connection; the cost ceiling is a process-wide setting and no
threshold is an input of a start, so a preset holds neither. No error code is added (the refusals reuse
`validation_failed`, `conflict`, `not_found` and `permission_denied` with their existing detail keys) and
migration `0037_analysis_presets` adds one table and one nullable column of `audit_run`. The identity of a
preset and of each revision is `evt_<ULID>`, the id of the audit event written with it; a dedicated prefix
is a change of the domain contract, which this addition does not make. `2.0.0` stays reserved (owner ruling `R-146ar`,
`D-233`: the strict reading of the removal of `AnalysisProfileStatus.builtin`).

## Version `1.7.0` (historical)

`PROD-11-AR-V1-V2-REMOVAL-01` removes АР v1 and v2 from the server (`ADR-0024` section 2, `AD-12`).
`startRun` and `reauditRun` on a version classified АР answer the existing `422
section_profile_unavailable`: АР is analysed only by the six-Run group (`startArV3BetaGroup`) and has no
text profile, and the error catalogue keeps its 27 codes. `listAnalysisProfiles` returns `profile: null`
for АР (the property was already nullable). The enum `AnalysisProfileStatus` loses its member `builtin`,
which only the АР v1 profile carried, and keeps `draft` and `reviewed`; the description of `reviewed` is
corrected to what the status is, a package whose open questions a lane answered in writing with no human
review (`R-146ag`, `D-223`). `FindingCategory` is unchanged. The version rule
(`docs/program/VERSIONING_AND_FREEZE_POLICY.md`) reads this as a **minor**: no field, path or operation
disappears, a response that carried `builtin` never will, and the narrowing for АР is announced by an
existing error code. The strict reading of «remove» is a major; the task file records both and the
integrator confirms the number. The surface is 92 paths, 104 operations and 301 schemas. No error code or
migration was added.

## Version `1.6.0` (historical)

`EXEC-PAR-START-01` lets a run name its executor. `startRun` accepts an optional
`executor_connection_id`; absent, the run follows the global route exactly as before. Present,
the run freezes that connection's current revision when this release serves its kind, the
connection's current key has a passing probe and it is not archived; otherwise the start is
refused before any run exists (`validation_failed` on `executor_connection_id` for an unknown
or malformed id, `dependency_unavailable` with `dependency: executor_connection` for a
connection that cannot serve now). A named connection never falls back to the route's standby
or to another connection, and the same idempotency key with another connection is
`idempotency_key_reuse`. `reauditRun` keeps the original run's named executor. `RunStatus`
gains a read-only, optional and nullable `executor` (`RunExecutor`: `connection_id`,
`display_name`, `pin_id`); a run that froze no connection omits it, and nothing about a
connection's kind, address, key or probe is exposed. The surface is 92 paths, 104 operations
and 301 schemas. No error code or migration was added.

## Version `1.5.0` (historical)

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
