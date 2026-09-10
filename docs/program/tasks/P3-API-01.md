# Task P3-API-01 — generated OpenAPI client and typed transport seam

> **Status: delivered by Gate A session `A5`, on branch `agent/gate-a5` from base
> `5f360d8`.** Subsumed by `PROTOTYPE_WAVE_PLAN.md` §3 — this task ran inside `A5`
> together with `P3-WEB-00`, not as its own P03 dispatch. Sole writer of the generated
> API client and of all HTTP in `web/`; that ownership now sits with `A5` and is frozen
> at the Gate A commit.
>
> One defect was found in the frozen OpenAPI document and left unrepaired, per the
> rule that `contracts/api/v1/**` belongs to the seam session. See Handoff.

## Outcome

A deterministically regenerated TypeScript client plus one transport wrapper is the only
place in `web/` where HTTP exists; it injects idempotency keys, decodes the domain error
envelope into the closed `error_code` union, and consumer contract tests fail when the
P02 API drifts from the PC-01 seam.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until each
is accepted and integrated:

  - `P3-WEB-00` — frontend toolchain and seam document accepted
  - `P2-API-01` — the OpenAPI document frozen at a named commit containing the PC-01 seam

## Frozen inputs

- API contract: the P02 OpenAPI document at its accepted freeze commit, snapshotted here
  and never edited
- domain contract: `error-codes.json`, `identifiers.json`, `state-machines.json`, read only
- analysis/comparison/event contract: none consumed
- migration head: not consumed
- base commit: the accepted `P3-WEB-00` integration commit

## Allowed paths

- `web/src/shared/api/**`
- `web/openapi/**`
- `web/scripts/generate-api-client.mjs`
- `web/tests/contract/**`
- `docs/navigation/entries/p3-api-01.json`
- `docs/navigation/incidents/p3-api-01.jsonl` — created only if this task actually records an
  incident; never a shared append target
- `docs/program/tasks/P3-API-01.md`

## Forbidden hotspots

- `contracts/**` and the upstream OpenAPI source; `src/**`
- `web/package.json` and every web manifest or config, owned by `P3-WEB-00`
- every `_pages`, `widgets`, `features` and `entities` slice

## Non-goals

- No hand-edit of generated output and no bespoke domain types layered over the schema.
- No retry or backoff policy beyond the frozen polling helper, and no caching layer
  beyond the query client supplied by `_app`.

## Deliverables

- generator config plus generated client under `web/src/shared/api/generated/**` carrying
  a do-not-edit header
- a transport wrapper reading the base URL from config, setting `Idempotency-Key` on every
  write, passing the correlation id through, and decoding the envelope into exactly
  `validation_failed`, `not_found`, `conflict`, `state_transition_not_allowed`,
  `idempotency_key_reuse`, `idempotency_key_in_progress`, `idempotency_key_stale`,
  `dependency_unavailable`, `analysis_failed` and `internal_error` — the union carries no
  partial-specific refusal, because under `OD-11` a `partial` run is exported, while a run
  whose terminal does not publish a result returns `state_transition_not_allowed`, already
  listed above
- a run-state union taken from the contract, with `published` and never `succeeded`, and a
  verdict union `pending`, `accepted`, `rejected`, `needs_manual_review`
- one polling helper honoring the frozen interval and backoff and stopping on any terminal
  state
- consumer contract tests pinning the seam operations, the finding and observation field
  sets, the decision-ledger field set and the CSV column list

## Required tests

- Command: `npm --prefix web run api:generate && git diff --exit-code web/src/shared/api/generated`
  Expected: exit `0`; regeneration is deterministic.
- Command: `npm --prefix web run test:contract`
  Expected: exit `0`; every seam operation and required field present.
- Command: `npm --prefix web run test:contract -- --grep "drift probe"` against a mutated
  snapshot in which `published` is renamed
  Expected: non-zero, naming the missing state; proves the contract guard can fail.
- Command: `rg -n "fetch\(|axios|XMLHttpRequest" web/src --glob '!web/src/shared/api/**'`
  Expected: no match.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

Slices import only the public API of `shared/api`; they never see a raw response, never
construct a URL and never hand-write an error string. A P02 API change that breaks the
seam fails `test:contract` before any UI task is blamed.

## Failure/idempotency/security cases

- An unknown `error_code` surfaces as an explicit unrecognized-error state, never as
  success and never as a generic retry.
- `idempotency_key_in_progress` resolves by polling the same key; the client never mints a
  new one.
- `idempotency_key_reuse` is a terminal user-visible conflict, never a silent resubmit.
- Object keys, bucket names and the S3 endpoint never appear in typed models; a contract
  test rejects any schema property matching `bucket`, `object_key` or `s3_key`.

## Rollback / feature flag

Revert the client commit and regenerate from the previous snapshot. No server state is
involved.

## Estimate

Effort P50 0.5 person-day, P80 1.5 person-days. Basis: generation config plus one transport wrapper and consumer contract tests. Calibration pending.

## Handoff

- navigation incident status, one of `recorded`, `none_observed` or
  `practice_not_exercised`; `recorded` requires the incident file above, and the other
  two assert that no incident occurred or that the practice was not followed
- generated client version, the snapshot commit of the P02 OpenAPI and the generator pin
- commands/results including the drift probe
- seam operations actually exercised versus declared

### Delivered by `A5`

**Generator pin.** `web/scripts/generate-api-client.mjs`, generator version `1.0.0`,
plain Node 22.23.1 ESM with no dependencies — it must run before anything is installed
and must not be able to drag a transitive package into the output. Invocation
`npm --prefix web run api:generate`; `npm --prefix web run api:verify` regenerates in
memory and exits `1` on any drift.

**Snapshot.** `web/openapi/openapi.json`, byte-identical to
`contracts/api/v1/openapi.json`, sha256
`c97890c5f51c2a27adaaa7307fe65506a91fc9a884480cc54821aca8e30ecb12`. The document's
content was introduced by commit `c704458`; the dispatch brief named `9924d32`, which
does not touch `contracts/api/v1/**` and at which the bytes are identical. The digest,
not either commit name, is the anchor. All of it is recorded in `web/FRONTEND_LOCK.json`.

**Determinism.** Output is a pure function of the input bytes: no timestamp, hostname,
absolute path or environment value is emitted, and every iteration order is an explicit
locale-independent sort (`localeCompare` is locale-dependent and would make output
machine-dependent). Two consecutive runs produce byte-identical files; a contract test
asserts it, and so does a second manual run compared with `diff -r`.

**Seam operations: declared 12, generated 12, exercised 12 by the contract suite** — as
descriptors, method, path, idempotency requirement, pagination parameters and response
media type. **None was exercised against a live server**: there is no `B6` router yet,
which is the whole point of generating from a frozen contract rather than from a running
service. The transport itself is exercised only through its types.

### Defect found in the frozen OpenAPI document, left unrepaired

`contracts/api/v1/**` belongs to session `A1`. Reported here, not fixed.

**`FindingDetail` can never validate carrying the two properties it exists to add.**

```json
"FindingDetail": {
  "allOf": [
    { "$ref": "#/components/schemas/Finding" },
    { "type": "object",
      "properties": { "latest_comment": {...}, "decision_event_count": {...} } }
  ]
}
```

`Finding` declares `"additionalProperties": false`. Under JSON Schema 2020-12, which
OpenAPI 3.1 uses, `additionalProperties` is evaluated against the property annotations of
its **own** schema object; sibling `allOf` branches contribute nothing to it. So the
`Finding` branch rejects `latest_comment` and `decision_event_count` as unexpected, and
the composed schema fails for exactly the payloads it was written for.

Verified, not asserted, with a Draft 2020-12 validator against a synthetic payload:

| Payload | Against `Finding` | Against `FindingDetail` |
|---|---|---|
| base fields only | valid | valid |
| base fields plus `latest_comment` and `decision_event_count` | — | **invalid**: `Additional properties are not allowed ('decision_event_count', 'latest_comment' were unexpected)` |

`GET /findings/{finding_uid}` declares `FindingDetail` as its 200 body, and
`P02_SEAMS.md` §5.4 lists both fields in the `finding_current_verdict` projection, so
this is the response shape a review screen depends on.

**Impact.** None on the generated client: TypeScript has no `additionalProperties: false`,
so the emitted `FindingDetail = Finding & { decision_event_count?: number;
latest_comment?: string | null }` is the intended shape and the client compiles and runs.
The damage lands on anyone who validates: `B6` validating its own response against the
document, a schema-driven mock, or a contract test in the Gate C convergence.

**A shape that would work** — for `A1` to weigh, not for `A5` to apply: give `Finding` the
two optional properties directly and let `FindingDetail` be an alias; or drop
`additionalProperties: false` from `Finding`; or restate `FindingDetail` as one closed
object with the full property list rather than an `allOf`.

**Also audited, and clean.** No dangling `$ref`; no unreferenced component; every
`examples` value matches its own `pattern`; twelve unique, present `operationId`s; every
`{token}` in every path template has a declared path parameter; `FindingDetail` is the
only `allOf` in the document.

**One observation that is not a defect.** `StageState.error_code` is `string | null`
while `RunStatus.terminal_reason` is `ErrorCode | null`, which reads like a missed
narrowing. It is correct: `contracts/analysis/v1/stage-result.schema.json` defines the
stage error `code` as `^[a-z][a-z0-9_]{2,63}$`, a wider vocabulary than the twenty-code
domain catalog, so the two fields carry different vocabularies on purpose. The OpenAPI
does not repeat the analysis contract's pattern on that field; tightening it would be a
cosmetic improvement, not a correction.

**Navigation incident status:** `none_observed`. `docs/navigation/entries/p3-api-01.json`
was not written — outside the paths `A5` was given.

### Defect resolved by `A7-FIX`

Session `A7-FIX`, branch `agent/gate-a7-fix` from base `d05aefa`, repaired the defect
above in `contracts/api/v1/openapi.json`. It is closed; `A5`'s report needed no
correction, and the repair is regenerated into `A5`'s client rather than worked around
in it.

**The shape chosen.** `FindingDetail` restates `Finding`'s full property set on one
closed object and adds the two properties, instead of composing with `allOf`:

```json
"FindingDetail": {
  "type": "object",
  "additionalProperties": false,
  "required": [ ...Finding's seven... ],
  "properties": { ...Finding's nine..., "latest_comment": {...},
                  "decision_event_count": { "type": "integer", "minimum": 0 } }
}
```

`Finding` is untouched. Both schemas declare `additionalProperties: false`, so an
unknown property is still rejected on each — the closure this repository keeps is not
traded away for validity.

**The three candidates `A5` listed, and why two were rejected.**

| Candidate | Verdict |
|---|---|
| restate `FindingDetail` as one closed object | **chosen** — both shapes stay closed, `Finding` unchanged |
| drop `additionalProperties: false` from `Finding` | rejected — loses closure everywhere `Finding` is used, `FindingPage.items` included; also fails `test_response_shapes_are_closed` |
| give `Finding` the two properties, alias `FindingDetail` | rejected — `FindingPage.items` is a `$ref` to `Finding`, so a list response could carry the detail projection and still validate |

A fourth was weighed and rejected on evidence rather than taste: an open `FindingBase`
with `Finding` and `FindingDetail` each composing it under
`unevaluatedProperties: false`. That is the idiomatic 2020-12 answer and it does
validate correctly — `jsonschema` 4.26.0 was exercised on the shape directly rather
than assumed. It was rejected because it requires `Finding` to stop carrying
`additionalProperties: false` as its own key, which fails
`test_response_shapes_are_closed` in `tests/contract/domain_p02` — a directory
`A7-FIX` does not own. A repair that cannot be completed inside its own path set is
not a repair.

**Cost, and how it is paid.** Restating duplicates nine properties, and the two schemas
can now drift. `tests/contract/api_v1/test_finding_detail_composition.py` makes drift a
failure: it asserts `FindingDetail`'s property set is `Finding`'s plus exactly the two
additions, compares the shared entries by value, and asserts the `required` sets are
equal.

**Evidence.** `.venv/bin/pytest tests/contract/api_v1` exits `1` before the repair —
5 failed, 5 passed, reproducing `A5`'s message verbatim, `Additional properties are not
allowed ('decision_event_count', 'latest_comment' were unexpected)` — and exits `0`
after, 10 passed. The suite runs under the runtime interpreter and drives a real Draft
2020-12 validator through `.venv/bootstrap/bin/python`, the way
`openapi_metaschema_check.py` already does, and fails closed where that interpreter is
absent rather than skipping. `document_with_the_pre_fix_shape` rebuilds the original
composition in memory and re-evaluates it, so the guard is shown to fail on every run.

**Audit, widened.** `A5` reported `FindingDetail` as the only `allOf` in the document;
confirmed, and after the repair the document contains **no `allOf` at all**, so there is
no second instance of this shape. The audit was extended past `allOf` to the rest of the
family, all clean: no `$ref` anywhere carries a constraint-bearing sibling (only
`description`, which is an annotation); no `anyOf`; and none of the 19 `oneOf` uses
mixes a `$ref` branch with a property-bearing branch — every one is a nullable union,
whose branches are independent alternatives and leak no evaluation scope. A test now
searches the whole document for the shape on every run.

**Regenerated, not hand-edited.** The document moved from sha256 `c97890c5…0ecb12` to
`678a8bf7…add6a5`. `npm --prefix web run api:generate` was run twice and the two outputs
compared byte-for-byte with `diff -r`, identical; `web/FRONTEND_LOCK.json` carries the
recomputed digests. `A5`'s drift guard was left armed and went red against the
regenerated client before the lock was resealed — six stale entries named — which is the
guard working, not an obstacle to route around.

**`docs/program/P02_SEAMS.md` §5.4 needed no change.** The repair changes how the schema
is expressed, not which fields exist; the `finding_current_verdict` projection it lists
is unchanged.

**Left for the integrator.** `web/docs/PC01_UI_SEAM.md` still describes this defect as
open. That file belongs to `A5` and is outside the paths `A7-FIX` was given, so it was
not edited; it is now stale and wants a pointer to this section.
