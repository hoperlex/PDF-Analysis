# Domain contract v1 — candidate `1.0.0-draft.1`, revision 4

Owner lane: [W0-DOM-01](../../../docs/program/tasks/W0-DOM-01.md) (domain contract
owner). Status: **candidate draft, not frozen.** Every catalog in this directory
declares `contract_version` `1.0.0-draft.1`, `candidate_revision` `4`, `status`
`draft_candidate` and `frozen` `false`.

This family defines three primitives that every other bounded context depends on:
opaque identity, durable lifecycle and the externally visible failure shape. It is a
coordination artifact, not runtime configuration. Runtime types may be generated or
mirrored from it only with contract tests that prove equivalence.

Revision 2 applied the repository owner's disposition of **2026-09-01**: `PD-01` and
`PD-03` are **approved with modification**, and `OQ-01`, `OQ-03`, `OQ-05` and `OQ-06`
are resolved. `U-04` (tenant/IdP/TTL/legal hold), `OQ-02` and `OQ-04` stay explicitly
open. See [Owner decisions](#owner-decisions). Freeze is still the integrator's slot,
not this task's.

Revision 3 recorded **one** further owner decision, and only that: `AuditRun` and `Job`
consume the outcome of an **optional branch**, and an unsuccessful optional branch
means an explicit `partial` and **never** a full success. It is encoded in
`optional_branch_policy` and in the guards of `machines.audit_run` and `machines.job`,
and pinned row by row by the owning schema. No error code, identifier, state,
transition or machine changed; `PD-01` and `PD-03` keep the wording the owner
approved. See
[Optional branches](#optional-branches-an-unsuccessful-branch-is-a-partial-never-a-success).

Revision 4 records **no** decision and changes **no** rule. It is a correction round.
A round-3 note in this family stated that `U-06` was still open and that the fail-soft
policy of the excluded optimization names therefore *had no encoder*. That was read
from a state the architecture lane has since superseded. `U-06` is **resolved**, and
the same owner decision gives **every** part of `FS-04` an assigned encoder — this
lane's part is `FS-04-C`, already encoded here. Both statements are corrected in
`optional_branch_policy.integrator_notes` and under
[Owner decisions](#owner-decisions); nothing else moved. See
[What changed in revision 4](#what-changed-in-revision-4-and-what-breaks-for-a-reader-of-revision-3).

## Files

| File | Role |
|---|---|
| [identifiers.json](identifiers.json) | Identity catalog: prefixes, entity bindings, what is never identity |
| [identifiers.schema.json](identifiers.schema.json) | Shape of the identity catalog |
| [state-machines.json](state-machines.json) | Six closed lifecycles, guards, terminal semantics, run-creation rule, optional-branch policy, projections |
| [state-machines.schema.json](state-machines.schema.json) | Shape of the lifecycle catalog |
| [error-codes.json](error-codes.json) | 20 typed codes, categories, envelope declaration, detail-safety and internal-mapping rules |
| [error-codes.schema.json](error-codes.schema.json) | Shape of the error catalog |
| [error-envelope.schema.json](error-envelope.schema.json) | The externally visible failure envelope |
| [examples/error-envelope.example.json](examples/error-envelope.example.json) | Valid envelope (`stale_attempt`) |
| [examples/error-envelope.unknown-code.invalid.json](examples/error-envelope.unknown-code.invalid.json) | Negative fixture: an undeclared code |

## Version and revision

`contract_version` is the **only** canonical version key in this family. It carries a
string semver/draft version. `$schema` stays the JSON Schema dialect and `$id` stays
schema identity; neither is a contract version. The bare `version` key that revision 1
used as the contract-envelope version is gone.

`1.0.0-draft.1` was never committed or frozen — the repository's committed domain
contract is still `1.0.0-draft.0`. So the version line stays `1.0.0-draft.0` →
`1.0.0-draft.1`, and the review round is recorded by `candidate_revision`, which the
owning schemas pin with `const`. That gives an unreleased candidate exactly the
guarantee a released version has: it cannot change meaning while keeping its number.
Bumping to a `draft.2` instead would have published a version that exists in no
commit and would have left `supersedes` pointing at a version nobody can fetch.

### The one deviation: `version` in `error-codes.json`

`error-codes.json` still carries a bare `version` key **as a deprecated compatibility
mirror**, declared machine-readably in its `deprecated_fields` block. Reason:
`scripts/validate_bootstrap.py` — hardened and frozen by `W0-QA-02`, and not writable
by this lane — hard-requires a non-empty `version` string in that one file. The
catalog's schema pins `version` and `contract_version` to the same `const`, so they
cannot diverge, and marks `version` `deprecated: true`.

**Consumers must read `contract_version`.** Nothing may read `version`. Removal gate:
a QA-lane change that teaches `scripts/validate_bootstrap.py` to read
`contract_version`; the mirror is deleted in that same change, not before. The other
two catalogs carry no `version` key at all, and their schemas reject one.

## How the schemas fail closed

- Every **record-shaped** object — the catalog roots, each machine, each code, the
  envelope, each guard, each decision-register entry — sets
  `additionalProperties: false`. An undeclared field is rejected; nothing is silently
  carried.
- Every **map-shaped** catalog (`identifiers`, `entities`, `machines`, `codes`,
  `categories`, `projections`) pins its complete current key set in `required`,
  constrains key names with `propertyNames` and validates every value against a
  strict item schema. Losing an entry fails the schema.
- `contract`, `contract_version`, `supersedes` and `candidate_revision` are `const`.
  A released version cannot change meaning while keeping its number, and an
  unreleased candidate cannot change meaning while keeping its revision.
- `error_code` in the envelope is an `enum` **exactly equal** to the key set of
  `error-codes.json`, and `retryable` is pinned per code by `if`/`then`. A provider
  cannot invent a code or contradict the catalog's retry signal.
- The **owner-decision register** is schema-enforced: a `status` of `approved`,
  `approved_with_modification` or `rejected` requires `decided_on` and `authority`;
  `approved_with_modification` additionally requires the `modification` text; a
  `not_decided` or `pending_owner_approval` entry requires a named `gate`. An
  approval cannot be claimed without an authority and a date.
- `open_questions` requires a `status` and a named `gate` per entry, and
  `resolved_questions` keeps every closed question with its recorded resolution, so a
  closed question cannot silently reappear as an assumption.
- `machines.audit_run` is required to declare `run_creation`. The approved `PD-03`
  rule is machine-readable, not prose.
- The bootstrap validator adds what JSON Schema cannot express: globally unique
  prefixes, closed transitions, reachable declared states and terminal states without
  outgoing edges.

## Identity

`<prefix>_<ULID>`, Crockford base32, uppercase, 26 characters. 25 identifiers, 25
entity bindings, all prefixes unique.

Load-bearing rules (full text in [identifiers.json](identifiers.json)):

- An identifier is opaque, generated once, never reused, never re-issued after a
  correction and never parsed for business meaning. The ULID body is not decoded to
  derive time, ownership or ordering.
- A path, directory, uploaded file name, S3 object key, URL, display ordinal such as
  `F-014`, human sheet or document number, row number, provider request id,
  idempotency key, payload fingerprint, execution authority capability and content
  checksum are **not** identity and are never foreign keys.
- Identifiers carry no secret: they are safe to log and to place in error `details`.
- `-uid` and `-id` suffixes are carried over from `1.0.0-draft.0` for consumer
  stability. The suffix is not a type discriminator and grants no different
  guarantee.

Four distinctions are declared explicitly and machine-readably in
`distinct_identities`:

| Distinction | Rule | Authority |
|---|---|---|
| `finding_uid` vs `finding_observation_id` | durable semantic issue vs immutable evidence from exactly one `run_id` | [ADR-0010](../../../docs/architecture/adr/ADR-0010-stable-finding-identity.md) |
| `run_id` vs `job_id` vs `attempt_id` | business history vs schedulable work item vs one leased execution | [ADR-0007](../../../docs/architecture/adr/ADR-0007-postgres-jobs-outbox-and-attempt-fencing.md) |
| `decision_id` per event | every verdict, correction and revocation allocates a new one | [ADR-0012](../../../docs/architecture/adr/ADR-0012-expert-decision-ledger-and-kb-projection.md) |
| `version_uid` vs `blob_id` vs `import_id` | published input state vs content bytes vs the operation | Bible P-02, P-03 |

### `execution_token`: a capability, not an identity, and not a number

`authority_capabilities.execution_token` proves that its bearer is the current
authorized executor at the instant of a write.

- **`execution_token` is the canonical field name.** `fencing_token` and
  `authority_token` are recorded in `legacy_evidence_names` as
  `legacy_evidence_only`: they name legacy evidence (`DW-05`) and cross-lane prose,
  and they are **never** field names, payload keys, database columns or API
  parameters of the target contract. They are not aliases you may substitute.
- **Opaque and equality-only.** Every party compares it for exact equality and never
  parses, orders, ranges, increments, derives or indexes it.
- **Fencing is behavior, not a value shape.** The guarantee is that a superseded
  token can never publish again. This contract promises no monotonic number, no
  ordering and no comparability; a consumer must not assume any.
- **Verified inside the publishing transaction.** A check performed earlier in the
  request is not sufficient. It never substitutes for `attempt_id`.
- **Secret class.** `execution_token`, `fencing_token` and `authority_token` are all
  forbidden `details` keys, so neither the value nor a legacy field name can leak
  through an envelope.

`lease_id` is the durable grant that carries the token. The lease record has
identity; the token does not. Lease duration, heartbeat interval and grace window are
deferred as `OQ-02`.

### Command idempotency key and payload fingerprint

`idempotency_key` is client-supplied, scoped to command type plus authorized subject
plus target aggregate, and is never converted into a system identifier or returned in
an envelope.

`payload_fingerprint` is now fully specified (`OQ-01`, resolved 2026-09-01):

- **sha256** over the **RFC 8785 JSON Canonicalization Scheme (JCS)** serialization
- of the **schema-valid, default-normalized** command payload — validation and
  default normalization happen *before* canonicalization, so a malformed request can
  never take an idempotency key hostage
- **excluding transport headers and the idempotency key itself**, so two requests
  that differ only in transport framing replay instead of conflicting
- it is a comparison value only: never an identity, never a foreign key, never
  returned in an envelope. No provider defines a second canonical form.

## Lifecycles

Six closed machines. Each declares its entity, identifier, authoritative writer,
initial state, transitions, terminal set, per-terminal semantics
(`outcome`, `publishes_result`), guards with the error code raised on violation, and
its retry rule. Any transition that is not declared is refused with
`state_transition_not_allowed` — the catalog's `default_violation`.

| Machine | Entity | Terminal states | Retry |
|---|---|---|---|
| `import` | Import | `completed`, `rejected`, `failed` | new `import_id`; repeat under the same key replays |
| `blob` | Blob | `rejected`, `erased` | new `blob_id`; re-upload is idempotent by `(sha256, size)` |
| `audit_run` | AuditRun | `published`, `partial`, `failed`, `cancelled` | new `run_id`; a terminal run is never reopened |
| `job` | Job | `succeeded`, `failed`, `cancelled`, `dead_letter` | in place, bounded, creates a new Attempt; exhaustion is `dead_letter` |
| `attempt` | Attempt | `succeeded`, `failed`, `superseded`, `lost`, `cancelled` | new `attempt_id` under the same `job_id` |
| `command_idempotency` | CommandRecord | `succeeded`, `failed`, `abandoned` | the record *is* the retry mechanism |

### When a new AuditRun exists — `machines.audit_run.run_creation`

This is the approved `PD-03` modification, encoded as rules in the catalog rather
than as prose here. A new AuditRun is created **exactly** when a top-level audit or
re-audit command is accepted for a **frozen** set of inputs and configurations
(`frozen_at_creation`: the input manifest — the exact `version_uid`/`blob_id` set —
plus `analysis_profile_id`, `prompt_bundle_id` and `norms_snapshot_id`).

| Trigger | Effect |
|---|---|
| Top-level audit command accepted, no command record for its idempotency key | new `run_id` over the frozen set |
| Repeat, **same** idempotency key and **same** payload fingerprint | the **existing** `run_id` is returned; no second Run, Job or Attempt, whatever state that run is in |
| Repeat, same idempotency key, **different** payload fingerprint | nothing created, nothing changed → `idempotency_key_reuse` |
| Declared inputs or configuration references differ from those frozen on an existing run | **new** `run_id`; an existing run is never re-executed against changed inputs and its frozen set is never edited |
| Explicit **re-audit** command for the same target | **new** `run_id`; the earlier run, its observations and its result stay readable and unmodified |
| Top-level command under a **new** idempotency key for a target whose previous run is **terminal** | **new** `run_id`; the terminal run is never reopened or re-executed |
| **retry / resume / restart / worker failover** of work already belonging to a run | **no** new `run_id`, **no** new `job_id`; the same Job creates a new `attempt_id` whose execution token supersedes the previous one |
| Any request that would move a terminal run back to a non-terminal state | refused → `state_transition_not_allowed`; the only remedy is a new top-level command and a new `run_id` |

The same rule appears in the catalog's root `rules` and in `machines.job.retry`,
`machines.attempt.retry` and `machines.audit_run.retry`, so a reader who never opens
this README cannot miss it.

Three further properties are worth reading directly in the catalog:

- **Publication authority** lives only in `attempt`. At most one Attempt per Job may
  publish: the one in `running` presenting the current token, checked inside the
  publishing transaction. A result delivered by an Attempt in `superseded`, `lost`,
  `cancelled` or `failed` is stored as immutable evidence, never applied, and answered
  with `stale_attempt`.
- **`partial` is a first-class terminal**, not a decorated success. It publishes a
  result whose missing or degraded set is named. Operations requiring completeness
  refuse it with `partial_result_not_publishable`. An unsuccessful **optional branch**
  lands here and can never land in `published` — that is `optional_branch_policy`,
  below.
- **`dead_letter` is durable and inspectable.** A poison job is never silently
  dropped.

### Optional branches: an unsuccessful branch is a partial, never a success

Revision 3 recorded one new owner decision. `AuditRun` and `Job` are **consumers** of
an optional branch outcome: an unsuccessful optional branch means an explicit
`partial` and **never** a full success. This is `FS-04-C`, part 3 of the three-part
`FS-04` fail-soft policy and the part assigned to **this** lane. The other two parts
have owners of their own: `FS-04-A`, norm and core stage terminal semantics, belongs
to the **ANA** contract owner (`contracts/analysis/v1/**`, task `W0-ANA-01`), and
`FS-04-B`, project-optimization stage and result semantics, to the **OPT** contract
owner (`contracts/optimization/v1/**`, task `W5-OPT-01`). They are named in
`optional_branch_policy.owner_decision.parts_not_owned_here` only to point at their
owners; no semantics of theirs is described, encoded or absorbed here.

The rule is **encoded, not narrated.** `optional_branch_policy` in
[state-machines.json](state-machines.json) declares:

- a closed consumer-side outcome vocabulary — `succeeded` (successful), `failed` and
  `unknown` (both unsuccessful, both requiring a typed reason). It classifies an
  outcome **for the consumer**; it is not a branch status vocabulary and constrains
  no branch's own states;
- `unrecorded_outcome`: an admitted branch with no recorded outcome evaluates to
  `unknown`, which is unsuccessful. **Absence never evaluates as success** — the same
  fail-closed rule `command_idempotency` applies with `abandoned`;
- `recorded_outcome`: every admitted branch carries exactly one entry with an opaque
  `branch_reference`, an `outcome` and — whenever the outcome is unsuccessful —
  exactly one `error_code` declared in [error-codes.json](error-codes.json). A
  missing or untyped entry is `validation_failed`, so no branch degrades silently;
- `terminal_selection`: a **total decision table** over the terminal the core rules
  alone select and the aggregate branch status.

| `core_terminal` | `branch_status` | run terminal | forbidden terminal | refusal code |
|---|---|---|---|---|
| `published` | `all_successful` | `published` | — | — |
| `published` | **`any_unsuccessful`** | **`partial`** | **`published`** | `partial_result_not_publishable` |
| `partial` | `all_successful` | `partial` | `published` | `partial_result_not_publishable` |
| `partial` | `any_unsuccessful` | `partial` | `published` | `partial_result_not_publishable` |
| `failed` | `all_successful` | `failed` | `published`, `partial` | `analysis_failed` |
| `failed` | `any_unsuccessful` | `failed` | `published`, `partial` | `analysis_failed` |

Row 2 is the decision. The other five restate the terminal the core rules already
selected, so the table is **total** over its 3 × 2 inputs: every combination has
exactly one row, there is no default and no fall-through, and the allowed and
forbidden terminal for any input is derivable from the catalog alone. The policy
never *upgrades* a terminal; its only effect is replacing `published` with `partial`.
Which terminal the core rules select is **not** decided here — that is `FS-04-A`,
owned by the analysis lane.

The same rule appears where a reader of a single machine will hit it:

- `machines.audit_run.guards` gains `validating → published`, guarded on
  `branch_status` being `all_successful` and refused with
  `partial_result_not_publishable`; and `validating → partial`, guarded on the
  degradation record existing and being typed, refused with `validation_failed`.
  Guard rows for the same `from`/`to` pair are conjunctive — a root rule now says so
  explicitly;
- `machines.job.guards` gains `running → succeeded`, requiring that the published
  result declare the terminal the table selects. A result declaring outcome `success`
  while a branch is unsuccessful is refused and never published;
- `terminal_semantics.published` now states its own precondition, and
  `terminal_semantics.partial` names the optional-branch case as a member of its
  recorded set.

[state-machines.schema.json](state-machines.schema.json) **pins the table row by row**
(`prefixItems`, six rows, `items: false`), pins each outcome value's
`successful`/`typed_reason` pair, the fail-closed `unrecorded_outcome`, the job clause
and the CP-00 capability flags, and requires both guards through `contains`. Dropping
the policy, deleting a row, reordering the table, letting row 2 select or stop
forbidding `published`, leaving a refusal untyped, adding a permissive row or
reclassifying `failed`/`unknown` as successful all fail schema validation. The
negative probe under [Verification](#verification) runs fifteen such mutations and
requires every one of them to be rejected.

**The concrete optimization branch is switched off at CP-00, and CP-00 excludes its
runtime semantics.** `capability_status` records that machine-readably:
`enabled_at_cp_00: false`, `runtime_semantics_at_cp_00: "excluded"`, owning family
`contracts/optimization/v1/**`, a separate project-optimization contract owner who is
neither the analysis nor the domain owner, and planned task `W5-OPT-01` after the core
audit freeze and the decision contracts. Until that task is accepted no optional
optimization branch may be admitted to a run, so `branch_status` is `all_successful`
for every CP-00 run and row 2 is unreachable in practice while staying binding by
contract. This is deliberately a **consumer contract written before the capability
exists**, so the capability can never be introduced later as a silent success path.
It changes no CP-00 runtime behavior.

The disabled capability and the CP-00 exclusion are not this lane's reading of a
situation: they are the two **binding obligations** of the owner decision that
**resolved `U-06`** on **2026-09-01**, recorded in the architecture lane's ledger and
binding on every lane until `W5-OPT-01` is accepted — the capability stays disabled
and no lane models its stage vocabulary, status semantics or packages, and CP-00
explicitly excludes its runtime semantics.

`optional_branch_policy.interaction` records the compatibility check.

- **`PD-03`** — compatible and unchanged. An unsuccessful optional branch changes only
  which terminal `audit_run` selects while the run is still in `validating`. It
  creates no Run, no Job and no Attempt, never reopens a terminal Run and never
  re-executes one. Recovering an optional branch after a run is terminal is a new
  top-level command and a new `run_id` under `run_creation`, exactly like any other
  rerun.
- **`partial` semantics** — compatible and unchanged. `partial` already meant an
  explicitly recorded set of missing or degraded results, with `publishes_result:
  true` and `partial_result_not_publishable` for a consumer that needs completeness.
  This policy adds one further member to that set and changes neither the outcome
  value, nor `publishes_result`, nor the code.
- **Cancellation** — unchanged. `cancelled` is reachable only from `created`, `queued`
  and `running`, so it is not an outcome this table can select.
- **Conflicts found: none.**

An unsuccessful optional branch is also **not a Job failure**: it is not a retryable
error class, it does not move the Job to `retry_wait`, it does not consume the retry
budget and it never produces `failed` or `dead_letter` — a Job that never publishes
cannot produce the explicit `partial` the rule requires. Retry *inside* the branch,
before the branch reports an outcome, belongs to that branch's own contract family.
`machines.attempt` is untouched: publication authority is still decided by the
execution token alone.

### Unconfirmed `temporary` blobs (`OQ-05`, resolved)

A blob in `temporary` is **never readable by the business layer** and is never
referenced by a published manifest. Its only declared exits are `verifying` and
`rejected`. Storage reconciliation moves an unconfirmed `temporary` blob to the
terminal `rejected` state — it is never left in `temporary` indefinitely and never
becomes visible by timeout. **Physical destruction of bytes by reconciliation is
permitted only for an object that was never confirmed and is referenced by nothing**;
a verified, referenced or erasure-governed object is destroyed only through
`erasure_pending → erased` under an approved `erasure_request_id`. The numeric window
after which reconciliation acts stays under the open `U-04` decision — no value is
declared.

### Aggregates that deliberately have no state machine

`non_state_machine_aggregates` records why, so that "no machine" cannot be read as an
oversight: `ExpertDecision` (append-only events), `FindingObservation` (immutable run
evidence), `AuditEvent` (append-only audit trail) and `AnalysisProvenance`
(`AnalysisProfile`, `PromptBundle`, `NormsSnapshot`, `ModelCallRecord` — immutable
versioned or content-addressed).

`projections` records the three rebuildable read models —
`finding_current_verdict`, `execution_progress`, `knowledge_base` — with the rule
that a projection is never an authoritative writer and is repaired by rebuilding or
by appending a new event, never by editing history.

**Revocation projects to `pending`** (the approved `PD-01` modification, which closes
`OQ-03`): a revocation event withdraws the revoked verdict and the projection moves
to `pending`. The projection **never** restores an earlier superseded verdict
automatically. A verdict after a revocation exists only where an authorized expert
appended a new decision event.

## Errors

20 codes across 10 categories. Each code declares `http`, `retryable`, `category`, a
`summary`, its `safe_detail_keys` and its inventory evidence.

The envelope is:

```json
{
  "contract_version": "1.0.0-draft.1",
  "error_code": "stale_attempt",
  "message": "…caller-safe sentence…",
  "correlation_id": "corr_…",
  "retryable": false,
  "details": { "job_id": "job_…", "current_attempt_id": "att_…" }
}
```

- All of `contract_version`, `error_code`, `message`, `correlation_id` and
  `retryable` are **required**. `retryable` is required — and pinned to the catalog —
  because a caller must never infer retryability from an HTTP status or from message
  text (Bible P-10).
- `details` is optional, carries at most 16 scalar entries, restricts key names to
  lowercase tokens and rejects the catalog's `forbidden_detail_keys` (`path`,
  `s3_key`, `url`, `token`, `execution_token`, `fencing_token`, `authority_token`,
  `secret`, `payload`, `prompt`, `stack`, `sql`, `email`, … — 33 keys). Safety is
  therefore enforced by the schema, not only by review.
- `message` is capped at 512 characters and rejects control characters. It never
  carries a path, object key, URL, credential, token, prompt, payload, query or stack
  content.
- A code outside the catalog is never emitted; the negative fixture proves the
  envelope rejects one.

### Internal reasons never leak — `internal_mapping` (`OQ-06`, resolved)

Every internally typed failure reason is mapped to exactly one declared code before
it can leave the trust boundary.

- An internal analysis-stage, adapter or worker code with **no declared mapping** is
  reported externally as **`internal_error`**.
- The original internal code is recorded **only in protected diagnostics**,
  correlated by `correlation_id`. It never appears in `error_code`, `message` or
  `details` and never reaches the external envelope.
- An unmapped internal code is never passed through unchanged, never prefixed, never
  truncated into a new code and never used to invent a catalog entry at the edge.
- Giving a recurring internal reason its own stable external code is a deliberate
  catalog change under the versioning policy, not an edge-local decision.

Codes added in `draft.1`: `idempotency_key_in_progress`, `execution_token_invalid`,
`required_norm_unavailable`, `partial_result_not_publishable`. No code was removed or
renamed relative to `1.0.0-draft.0`, and revisions 2, 3 and 4 add and remove none.

## Evidence walks

All four walks required by the task, with the accepted inventory rows they rest on.
Row identifiers refer to
[legacy_capability_inventory.md](../../../docs/behavior/legacy_capability_inventory.md).

### Walk 1 — provider timeout, retry, new current Attempt, late stale result rejected

1. A top-level audit command is accepted for a frozen input/configuration set and a
   new `run_id` is created (`run_creation`, case 1). `audit_run created → queued →
   running`. `job queued → leased → running`. Attempt `A1 created → leased → running`
   holds the current execution token.
2. The model provider times out. `A1` reports a retryable error class
   (`dependency_unavailable`, `retryable: true`). `job running → retry_wait`.
3. The bounded budget admits a retry: `job retry_wait → queued → leased`. Creating
   `A2` and its token supersedes `A1`'s token in the same transaction, so
   `A1 running → superseded`. **No new `run_id` and no new `job_id` are created** —
   `run_creation` case 7 and `machines.job.retry` say so explicitly. Resume, restart
   and worker failover follow the identical path.
4. `A2` delivers; schema, checksums and manifest validate; `A2 running → succeeded`,
   `job running → succeeded`, `audit_run validating → published`.
5. `A1`'s result finally arrives. `A1` is terminal and not the current authority, so
   the delivery is stored as immutable evidence, project state is untouched, and the
   caller receives `stale_attempt` — exactly
   [examples/error-envelope.example.json](examples/error-envelope.example.json). The
   token itself never appears in the response, and neither does the name
   `fencing_token` or `authority_token`.
6. Re-running the audit afterwards is a **new top-level command** under a new
   idempotency key: the terminal run is not reopened, a new `run_id` is created and
   the published run stays readable (`run_creation` case 6, case 8).

Evidence: **DW-02** (at most one active job per project/version and one active
attempt per job; attempt-scoped execution token, idempotency keys and
stale/superseded checks), **DW-04** (superseded results stored without publication;
publish only after validation), **DW-05** (old connection epoch and stale/superseded
attempt rejected; no domain-level fencing field established in legacy — which is why
`fencing_token` stays *evidence*, not a field name), **AN-07** (operator
retry/resume; unsafe state conflicts are 409). **DW-03** records that legacy has no
distinct Run entity, so step 1's `audit_run` is target semantics, not a parity claim.
`PD-03` is approved with modification as of 2026-09-01.

### Walk 2 — finding rerun, new Observation, expert correction as a new decision event

1. Run `R1` publishes. `Finding fnd_…` carries observation `fobs_…₁` from `R1`.
2. The expert accepts. A decision event `dec_…₁` is appended;
   `finding_current_verdict` projects to `accepted`.
3. Rerun `R2` allocates a **new** `run_id` and emits `fobs_…₂`. `R1`'s observation is
   not rewritten, renumbered or deleted. If the versioned matching policy cannot
   justify carryover, a new `finding_uid` is allocated instead of reusing one.
4. The expert corrects the verdict: `dec_…₂` is appended with a new `decision_id`.
   `dec_…₁` is untouched. The projection recomputes to the corrected verdict.
5. The expert revokes: `dec_…₃` of revocation kind is appended. Nothing is removed
   from the ledger and **the projection moves to `pending`** — it does *not* fall back
   to the verdict of `dec_…₁` or `dec_…₂`. Re-establishing a verdict requires a new
   decision event appended by an authorized expert. This is the approved `PD-01`
   modification and it closes `OQ-03`.
6. A request to edit or delete `dec_…₁` matches no declared transition and is refused
   with `state_transition_not_allowed`. The catalog deliberately contains no
   delete-decision or overwrite-decision code, and the approved `PD-01` means none is
   needed.

Evidence: **EX-01** (per-project expert review plus a global decision-log
projection), **EX-02** and **section 7 item 1** (legacy updates a matching decision
and revoke deletes from both the global log and the active review — recorded as the
contradiction that required this owner decision), **EX-08**/**EX-09** (an existing
non-empty human verdict is preserved; provider or threshold failure yields
`needs_manual_review` with no verdict), **section 7 item 6** (legacy decision typing
is permissive, so the projection here declares a closed value set),
**FD-01**/**FD-02** (finding browsing and deterministic evidence linkage).

### Walk 3 — idempotent repeat versus same-key, different-payload conflict

1. A create-version command arrives with idempotency key `K` and payload `P`. `P`
   validates against its command schema and is default-normalized, then canonicalized
   with RFC 8785 JCS and hashed with sha256 to give the fingerprint — transport
   headers and `K` itself excluded. No record exists, so a `command_idempotency`
   record is created `in_progress` in the same transaction as the business effect, and
   the import runs `received → validating → materializing → publishing → completed`.
   The record moves `in_progress → succeeded` with the created `version_uid` and
   `import_id` recorded.
2. The client's connection dropped and it repeats with `K` and the same `P`: the
   fingerprint is identical and the recorded outcome is replayed verbatim. No second
   version, run, attempt or decision is created. For a top-level audit command the
   same rule returns the **existing** `run_id` (`run_creation` case 2).
3. A repeat arriving while the first execution is still `in_progress` returns
   `idempotency_key_in_progress` (`409`, `retryable: true`). The caller retries the
   same request; re-issuing under a fresh key would create a duplicate and is
   explicitly not the remedy.
4. A repeat with `K` but payload `P'` yields a different fingerprint and returns
   `idempotency_key_reuse` (`409`, `retryable: false`). Nothing is created or changed
   (`run_creation` case 3).
5. If the process crashed before an outcome was recorded and reconciliation cannot
   establish it, the record moves to `abandoned`; a later repeat receives
   `idempotency_key_stale` and fails closed rather than re-executing on a guess.

Evidence: **DW-04** (chunk, session and complete are idempotent; the same applied
hash replays and a different hash conflicts), **CP-02** (idempotent session and
document-pair creation), **EX-09** (stable origin pairs make the migrated-findings
append idempotent), **WS-02**/**WS-03** (duplicate and conflict statuses on ingest;
active-audit conflict is 409). The retention window that eventually makes a record
unavailable stays under `U-04` and is not invented here.

### Walk 4 — missing authoritative norm or dependency, explicit failure or partial policy

1. Scheduling requires the `AnalysisProfile`, `PromptBundle` and `NormsSnapshot`
   references to resolve to immutable versioned records — the same references
   `run_creation` freezes at Run creation. If the norms snapshot cannot be resolved,
   `created → queued` is refused with `required_norm_unavailable` (`422`, not
   retryable). No unversioned, partial or substitute norm source is used and the run
   does not start "with defaults".
2. If instead a transient adapter is down, the caller receives
   `dependency_unavailable` (`503`, retryable). Nothing was created, so a retry is
   safe — and that retry is a repeat of the same command under the same idempotency
   key, not a second Run.
3. If the dependency is lost mid-run, the affected stage fails. The delivered result
   validates for a proper subset of required outputs and the missing set is recorded
   explicitly, so `audit_run validating → partial`.
4. `partial` publishes a result that names its own gaps. An operation that requires a
   complete run — an export claiming completeness, for example — refuses with
   `partial_result_not_publishable` (`409`) instead of quietly emitting an incomplete
   artifact.
5. If nothing acceptable was produced, `validating → failed` and the operation
   reports `analysis_failed`.
6. If the engine reports an internal stage reason this catalog does not declare, the
   edge reports `internal_error` and keeps the internal code in protected diagnostics
   only (`internal_mapping`). It never invents a code and never echoes the internal
   one.
7. If the unavailable dependency belonged to an **optional branch** the run admitted,
   the branch outcome is recorded as `failed` — or `unknown`, if the outcome could not
   be established at all — with exactly one declared `error_code`, and
   `optional_branch_policy.terminal_selection` selects `partial` even though every
   required core output validated. `validating → published` is refused with
   `partial_result_not_publishable`, and the Job may not publish a result declaring
   `success`. Recovering that branch is a new top-level command and a new `run_id`;
   the `partial` run is terminal and is never reopened. At CP-00 the concrete
   optimization branch is disabled, so no run admits one and this step describes the
   contract a consumer must already satisfy, not enabled behavior.

Evidence: **AN-06** (norm and optimization branches may record degradation and
continue) and the `FS-04` fail-soft row it feeds, **section 7 item 5** (decision carryover, optimization/norm branches,
shadow mirroring and embedded Excel generation are fail-soft in legacy and require
explicit visibility), **OUT-02** (a legacy audit package can succeed without the
Excel member whose generation failed — an explicit completeness risk that this
contract refuses to reproduce), **AN-07** (unknown retry or skip name is 4xx),
**AN-09** (budget and provider errors are visible), Bible **P-10**.

## Legacy behavior deliberately not adopted

| Legacy behavior | Row | Target here |
|---|---|---|
| A matching decision-log entry is updated and revoke deletes records | EX-02, section 7.1 | Append-only events; no delete or overwrite code exists; revocation projects to `pending` |
| Path, folder and file name carry meaning across layouts | section 7.7 | Opaque identity only; paths are never identity |
| A ZIP export can silently omit the failed Excel member | OUT-02 | `partial` is explicit; `partial_result_not_publishable` refuses false completeness |
| Fail-soft branches degrade while the operation reports success | section 7.5 | Named `partial` terminal plus typed codes; no silent fallback |
| Decision typing is permissive and can carry an empty verdict | section 7.6 | Closed projection value set including explicit `needs_manual_review` |
| Attempt token and connection epoch checks without a canonical contract | DW-05, section 7.4 | One declared capability `execution_token`, equality-only, verified in the publishing transaction; `fencing_token` stays legacy evidence, not a field |
| No distinct Run entity; re-audit semantics implicit | DW-03 | `run_creation` states exactly what creates a Run and what only creates an Attempt |

## Owner decisions

The repository owner recorded a disposition on **2026-09-01**. It is stored
machine-readably in `open_owner_decisions` in all three catalogs, with `decided_on`
and `authority` enforced by schema.

| Decision | Status | Modification recorded | What depends on it here |
|---|---|---|---|
| `PD-01` — expert correction/revocation is a new append-only event | `approved_with_modification` | Revocation moves the current projection to `pending`; an earlier superseded verdict is never restored automatically. Closes `OQ-03`. | `distinct_identities.decision_identity`; `non_state_machine_aggregates.ExpertDecision`; `projections.finding_current_verdict` and `projections.knowledge_base`; the deliberate absence of a delete/overwrite code; Walk 2 |
| `PD-03` — `AuditRun`, `Job` and `Attempt` are distinct with mandatory attempt authority | `approved_with_modification` | The AuditRun creation rule, encoded as `machines.audit_run.run_creation` (see the table above). | `distinct_identities.execution_identity`; `authority_capabilities.execution_token`; `machines.audit_run`, `machines.job`, `machines.attempt` and `publication_authority`; `stale_attempt`, `execution_token_invalid`, `idempotency_key_reuse`; Walk 1 |
| Optional branch outcomes are consumed by `AuditRun` and `Job`; an unsuccessful optional branch is an explicit `partial`, never a full success (`FS-04-C`, part 3 of `FS-04`) | recorded in round 3 | The rule is a consumer contract only: `FS-04-A` (norm/core) belongs to the ANA owner (`contracts/analysis/v1/**`, task `W0-ANA-01`) and `FS-04-B` (optimization stages/results) to the OPT owner (`contracts/optimization/v1/**`, task `W5-OPT-01`), and the capability is disabled at CP-00 with its runtime semantics excluded. | `optional_branch_policy`; the new `validating → published` and `validating → partial` guards on `machines.audit_run`; the new `running → succeeded` guard on `machines.job`; `terminal_semantics.published` and `terminal_semantics.partial`; Walk 4 |
| `OPEN-RETENTION` (`external_id` `U-04`) — retention, TTL, legal hold, tenant, identity provider | `not_decided` | — | `erasure_request_id` and the `blob` erasure states describe *who must approve*, never *when*; the reconciliation window for an unconfirmed `temporary` blob; `idempotency_key_stale` names the fail-closed outcome without a window value |

`U-04` is the owner input recorded in
[CP00_ARCHITECTURE_REVIEW.md](../../../docs/architecture/CP00_ARCHITECTURE_REVIEW.md)
§11, which keeps `ADR-0014` in `proposed` status. **No numeric retention, TTL or
legal-hold value is declared anywhere in this family**, and none may be added before
that input exists.

`PD-02` (one authoritative stage registry) and `PD-04` (graphic comparison is future
scope) are approved but belong to the ANA/ARC lanes; nothing in this family encodes
them, and no stage, result-package or comparison semantics are declared here.

The round-3 decision is recorded in `optional_branch_policy.owner_decision` rather
than in `open_owner_decisions`, because that register's `id` enum is `PD-01`–`PD-04`
plus `OPEN-RETENTION` and this lane does not assign `PD-*` numbers.

**`U-06` is resolved**, by the repository owner on **2026-09-01**, and the
architecture lane holds that disposition in its ledger: project optimization is a
**separate bounded context**, contract family `contracts/optimization/v1/**`, owned by
a dedicated **OPT contract owner** who is neither the analysis nor the domain owner,
and carried by the planned task **`W5-OPT-01`** after the core audit freeze and the
decision contracts. Two obligations ride with it and both bind every lane until that
task is accepted: the capability stays **disabled** and no lane models its stage
vocabulary, status semantics or packages, and CP-00 **explicitly excludes** its
runtime semantics.

The same decision splits `FS-04` into **three owned parts**, so **no part of it is
without an encoder**:

| Part | Scope | Owner | Family | Task |
|---|---|---|---|---|
| `FS-04-A` | norm and core stage terminal semantics | ANA lane | `contracts/analysis/v1/**` | `W0-ANA-01` |
| `FS-04-B` | optimization stage and result semantics | OPT contract owner | `contracts/optimization/v1/**` | `W5-OPT-01` |
| `FS-04-C` | `AuditRun`/`Job` as consumer of a branch outcome | **this lane** | `contracts/domain/v1/**` | `W0-DOM-01` |

This family owns `FS-04-C` and encodes exactly that. **The authoritative record of
`U-06` and of the split is the architecture lane's ledger, not this file:** the
paragraphs above restate it only far enough to fix this lane's boundary, this lane may
not write those paths and does not mirror them, and if the two ever disagree the
ledger governs and the disagreement is a cross-lane mismatch for the integrator rather
than a local patch here. `optional_branch_policy.integrator_notes` says the same
machine-readably.

Round 3 stated the opposite — that `U-06` was open and `FS-04` had a part with no
encoder. That was written in good faith from the ledger state visible to this lane at
the time, while the architecture lane was closing `U-06` in parallel; revision 4
corrects it.

### Open questions

Narrower gaps that are not owner product decisions but must be closed before
implementation. Each is recorded in `open_questions` in the catalog it affects, with
a named gate.

| ID | Status | Question | Affects | Gate |
|---|---|---|---|---|
| `OQ-02` | `deferred` | What lease duration, heartbeat interval and grace window apply? | `authority_capabilities.lease` | jobs/operations slot, no later than the first task implementing an execution lease (`W4-JOB-01`, [S04](../../../docs/stages/S04_core_audit_engine.md)); no lease implementation may proceed without it |
| `OQ-04` | `deferred` | What retry budget and backoff apply per error class before `dead_letter`? | `machines.job.retry` | `W4-C-01` / `W4-JOB-01`, before the core engine executes |

No numeric value, window or vendor choice is invented for either.

### Resolved questions

Retained in `resolved_questions` so a closed question cannot silently reappear as an
assumption.

| ID | Resolution | Recorded in |
|---|---|---|
| `OQ-01` | sha256 over RFC 8785 JCS of the schema-valid, default-normalized payload; transport headers and the idempotency key excluded | `identifiers.json` → `command_keys.payload_fingerprint.canonicalization` |
| `OQ-03` | Revocation projects to `pending`; no automatic fallback to an earlier verdict (via `PD-01`) | `state-machines.json` → `projections.finding_current_verdict` |
| `OQ-05` | Unconfirmed `temporary` blob is unavailable to the business layer and reconciled to `rejected`; bytes are physically destroyed only if never confirmed and referenced by nothing; window stays under `U-04` | `state-machines.json` → `machines.blob` |
| `OQ-06` | Unknown internal stage code surfaces as `internal_error`; the internal code stays in protected diagnostics and never reaches the envelope | `error-codes.json` → `internal_mapping` |

## Compatibility

- Backward compatible with `1.0.0-draft.0`: **no**. Meaning and required semantics
  tightened.
- Version: `1.0.0-draft.0` → `1.0.0-draft.1` (`candidate_revision` 4). Safe because
  no frozen production consumer exists. After freeze, any change requires the formal
  freeze-break and version procedure.
- Breaking changes for a reader of `draft.0`:
  - the `run` machine is renamed `audit_run`; the identifier stays `run_id` and the
    prefix stays `run`;
  - `audit_run` no longer transitions `running → partial`; `partial` is reached only
    from `validating`, because publication follows validation;
  - the `blob` terminal `deleted` becomes `erased`, reached through an
    `erasure_pending` state that requires an approved `erasure_request_id`;
  - `attempt` gains the `lost` terminal, distinct from `superseded`;
  - the error envelope gains required `contract_version` and required `retryable`;
  - two identifiers are added: `lease_id` (`lse`) and `command_id` (`cmd`).

### What changed in revision 4, and what breaks for a reader of revision 3

Revision 4 is a **correction round**. No owner decision was recorded, no rule was
added, weakened or removed, and every normative element of revision 3 is byte-stable.

| Change | Consumer impact |
|---|---|
| `optional_branch_policy.integrator_notes` no longer says `U-06` is open or that the excluded optimization names have no encoder; it now records `U-06` as **resolved** by the owner on 2026-09-01 in the architecture lane's ledger, the two binding obligations, and the three-part `FS-04` split with its owner, family and task per part | **None on the contract.** These are integrator-facing notes; no code, identifier, state, transition, guard, terminal or table row changed. |
| `owner_decision.parts_not_owned_here[].part` now carries the `FS-04-A` / `FS-04-B` part identifiers | Clarifying. The `owner` and `family` strings are unchanged, and no semantics of either part is described here. |
| The README's integrator paragraph is replaced by the resolved disposition, the `FS-04` split table and an explicit statement that the architecture ledger, not this file, is the authoritative record | Clarifying. |
| `candidate_revision` `3` → `4` in all three catalogs and their schemas | Shape-neutral. A consumer pinning `candidate_revision == 3` must move. |
| `optional_branch_policy` and its six-row decision table, both `audit_run` guards, the `job` guard, `terminal_semantics`, `run_creation`, `PD-01`, `PD-03`, all 25 identifiers, all 20 error codes, six machines, the open `U-04`/`OQ-02`/`OQ-04` register and the deprecated `version` mirror | **Unchanged.** Nothing was added, removed or renamed. The mirror still waits on `W0-DOM-02` after `W0-QA-03`. |

### What changed in revision 3, and what breaks for a reader of revision 2

| Change | Consumer impact |
|---|---|
| New required top-level `optional_branch_policy` in `state-machines.json`, with its complete shape pinned by the owning schema | **Additive but normative.** A strict reader mirroring the catalog root with `additionalProperties: false` must add the key. A consumer that treated an optional branch failure as a warning must stop: the run is `partial`. |
| `machines.audit_run.guards` gains `validating → published` (`partial_result_not_publishable`) and `validating → partial` (`validation_failed`) | **Breaking for an implementation**, not for a reader: publishing a fully successful run while an admitted optional branch is unsuccessful is now refused. No state, transition or code was added. |
| `machines.job.guards` gains `running → succeeded` (`partial_result_not_publishable`) | Same: a Job may not publish a result declaring outcome `success` while an optional branch is unsuccessful. |
| `terminal_semantics.published` and `terminal_semantics.partial` descriptions extended | Clarifying. `outcome` and `publishes_result` are unchanged for both. |
| Two root `rules` added: guard rows for one `from`/`to` pair are conjunctive; an optional branch never degrades silently | Clarifying; the conjunction rule makes the existing two-row `created → queued` pair explicit as well. |
| `machines.job` gains a `notes` array | Additive. |
| `candidate_revision` `2` → `3` in all three catalogs and their schemas | Shape-neutral. A consumer pinning `candidate_revision == 2` must move. |
| Error codes, identifiers, states, transitions, machines, prefixes, `PD-01`, `PD-03`, `run_creation`, the deprecated `version` mirror | **Unchanged.** Nothing was added, removed or renamed. The `version` mirror stays until `W0-QA-03` teaches the validator `contract_version`; removing it is the separate `W0-DOM-02` task. |

### What changed in revision 2, and what breaks for a reader of revision 1

| Change | Consumer impact |
|---|---|
| `version` → **`contract_version`** in all three catalogs | **Breaking.** Any reader keyed on `version` must switch. `error-codes.json` keeps a deprecated `version` mirror only for `scripts/validate_bootstrap.py`; nothing else may read it, and the other two catalogs reject the key outright. |
| `authority_capabilities.execution_token.aliases` → `canonical_field_name` + `legacy_evidence_names` | **Breaking** for anyone who treated `fencing_token`/`authority_token` as substitutable field names. They are legacy evidence only. Analysis-lane payloads naming `authority_token` are a cross-lane mismatch for the integrator, not a local patch. |
| `command_keys.payload_fingerprint.open_question` → `canonicalization` | **Breaking** shape change; the fingerprint algorithm is now normative. A provider that chose its own serialization must adopt RFC 8785 JCS. |
| New required `candidate_revision` and `revision_note` on all three catalogs | Additive; strict readers with `additionalProperties: false` mirrors must add them. |
| New required `resolved_questions`; `open_questions` entries now require `status` and `gate` | Shape change for anyone parsing the registers. |
| `open_owner_decisions` gains `approved_with_modification`, `modification`, `decided_on`, `authority`, `resolves`, `external_id`, `gate` | Shape change. A consumer gating on `status == "pending_owner_approval"` for `PD-01`/`PD-03` will now see `approved_with_modification` and must stop blocking. |
| `machines.audit_run.run_creation` added and required | Additive but normative: run-creation behavior is now contractually fixed. |
| `blob`: new `temporary → rejected` reconciliation guard, extended `rejected` semantics and notes | Additive; `temporary → rejected` was already a declared transition, so no state set changed. |
| `authority_token` added to `forbidden_detail_keys` (32 → 33) | **Breaking** for any envelope that used that detail key. None is declared in the catalog, so no declared code is affected. |
| `internal_mapping` added and required in `error-codes.json` | Additive; makes an existing safety rule normative and machine-readable. |
| Error codes, states, transitions, prefixes | **Unchanged.** No code, state, transition or prefix was added, removed or renamed in revision 2. |

## Verification

```bash
python3 -m json.tool contracts/domain/v1/identifiers.json >/dev/null
python3 -m json.tool contracts/domain/v1/state-machines.json >/dev/null
python3 -m json.tool contracts/domain/v1/error-codes.json >/dev/null
.venv/bootstrap/bin/python scripts/validate_bootstrap.py
git diff --check -- contracts/domain/v1
```

Schema and envelope gates, as run by this lane:

```bash
# every schema is valid Draft 2020-12 and every catalog validates against its schema
.venv/bootstrap/bin/python -c "import glob,json; from pathlib import Path; from jsonschema import Draft202012Validator as V; root=Path('contracts/domain/v1'); [V.check_schema(json.loads(Path(p).read_text())) for p in glob.glob(str(root/'*.schema.json'))]; pairs=[('identifiers.schema.json','identifiers.json'),('state-machines.schema.json','state-machines.json'),('error-codes.schema.json','error-codes.json'),('error-envelope.schema.json','examples/error-envelope.example.json')]; [V(json.loads((root/s).read_text())).validate(json.loads((root/i).read_text())) for s,i in pairs]"

# the envelope enum equals the catalog exactly and an unknown code is rejected at error_code
.venv/bootstrap/bin/python -c "import json; from pathlib import Path; from jsonschema import Draft202012Validator as V; root=Path('contracts/domain/v1'); catalog=json.loads((root/'error-codes.json').read_text()); schema=json.loads((root/'error-envelope.schema.json').read_text()); assert set(schema['properties']['error_code']['enum'])==set(catalog['codes']); invalid=json.loads((root/'examples/error-envelope.unknown-code.invalid.json').read_text()); errors=list(V(schema).iter_errors(invalid)); assert errors and any(list(e.path)==['error_code'] for e in errors)"
```

Three consistency rules that no committed gate covers yet, for the independent
reviewer:

```bash
# every guard on_violation and every run_creation error_code names a declared error code
.venv/bootstrap/bin/python -c "import json; from pathlib import Path; r=Path('contracts/domain/v1'); sm=json.loads((r/'state-machines.json').read_text()); codes=set(json.loads((r/'error-codes.json').read_text())['codes']); refs={sm['default_violation']}|{g['on_violation'] for m in sm['machines'].values() for g in m['guards'] if 'on_violation' in g}|{c['error_code'] for m in sm['machines'].values() if 'run_creation' in m for c in m['run_creation']['cases'] if 'error_code' in c}; assert refs<=codes, sorted(refs-codes); print('guard and run_creation codes OK', len(refs))"

# every machine/aggregate identifier is declared, and one contract_version and revision hold across the family
.venv/bootstrap/bin/python -c "import json; from pathlib import Path; r=Path('contracts/domain/v1'); sm=json.loads((r/'state-machines.json').read_text()); idc=json.loads((r/'identifiers.json').read_text()); ec=json.loads((r/'error-codes.json').read_text()); env=json.loads((r/'error-envelope.schema.json').read_text()); ids=set(idc['identifiers']); used={m['identifier'] for m in sm['machines'].values()}|{a['identifier'] for a in sm['non_state_machine_aggregates'].values()}; assert used<=ids, sorted(used-ids); vs={c['contract_version'] for c in (idc,sm,ec)}|{ec['version']}|{env['properties']['contract_version']['const']}; assert len(vs)==1, sorted(vs); revs={c['candidate_revision'] for c in (idc,sm,ec)}; assert len(revs)==1, sorted(revs); print('identifier bindings OK', len(used), '| contract_version OK', vs.pop(), '| candidate_revision', revs.pop())"
```

The optional-branch rule, including the negative probe that a fully successful
terminal is rejected while an optional branch is unsuccessful:

```bash
.venv/bootstrap/bin/python - <<'PY'
import copy, itertools, json
from pathlib import Path
from jsonschema import Draft202012Validator as V

r = Path('contracts/domain/v1')
catalog = json.loads((r / 'state-machines.json').read_text())
schema = V(json.loads((r / 'state-machines.schema.json').read_text()))
codes = set(json.loads((r / 'error-codes.json').read_text())['codes'])
rejected = lambda doc: bool(list(schema.iter_errors(doc)))
policy = catalog['optional_branch_policy']
table = policy['terminal_selection']['table']

# 1. the decision table is a total function over its declared inputs: no default, no fall-through
combos = list(itertools.product(policy['terminal_selection']['core_terminal']['values'],
                                policy['branch_status']['values']))
index = {(row['core_terminal'], row['branch_status']): row for row in table}
assert len(table) == len(index) == len(combos) and set(index) == set(combos), 'table is not total'

# 2. the rule is derivable from the artifacts: with an unsuccessful optional branch the run
#    never selects published, published is always forbidden, and an otherwise publishable run
#    is required to end partial
unsuccessful = [row for row in table if row['branch_status'] == 'any_unsuccessful']
assert all(row['terminal'] != 'published' for row in unsuccessful)
assert all('published' in row['terminal_forbidden'] for row in unsuccessful)
assert index[('published', 'any_unsuccessful')]['terminal'] == 'partial'
assert index[('published', 'all_successful')]['terminal'] == 'published'
assert policy['job_consumer']['published_outcome_forbidden'] == ['success']
assert catalog['machines']['audit_run']['terminal_semantics']['partial']['outcome'] == 'partial'

# 3. no unsuccessful outcome is silent: it is typed, and every code named is declared
assert policy['outcome_values']['succeeded']['successful'] is True
assert sorted(k for k, v in policy['outcome_values'].items() if not v['successful']) == ['failed', 'unknown']
assert all(v['typed_reason'] == 'required' for v in policy['outcome_values'].values() if not v['successful'])
assert policy['unrecorded_outcome']['evaluates_to'] == 'unknown'
named = {row['on_violation'] for row in table if 'on_violation' in row} | {
    policy['unrecorded_outcome']['on_violation'],
    policy['recorded_outcome']['on_violation'],
    policy['job_consumer']['on_violation'],
}
assert named <= codes, sorted(named - codes)

# 4. the concrete optimization branch is off at CP-00 and its runtime semantics are excluded
assert policy['capability_status']['enabled_at_cp_00'] is False
assert policy['capability_status']['runtime_semantics_at_cp_00'] == 'excluded'

# 5. negative probes: the owning schema rejects every weakening of the rule
mutations = {
    'policy block removed': lambda d: d.pop('optional_branch_policy'),
    'unsuccessful branch allowed to publish': lambda d: d['optional_branch_policy']['terminal_selection']['table'][1].__setitem__('terminal', 'published'),
    'published no longer forbidden': lambda d: d['optional_branch_policy']['terminal_selection']['table'][1].__setitem__('terminal_forbidden', []),
    'refusal left untyped': lambda d: d['optional_branch_policy']['terminal_selection']['table'][1].pop('on_violation'),
    'row deleted': lambda d: d['optional_branch_policy']['terminal_selection']['table'].pop(1),
    'permissive extra row added': lambda d: d['optional_branch_policy']['terminal_selection']['table'].append({'core_terminal': 'published', 'branch_status': 'any_unsuccessful', 'terminal': 'published', 'terminal_forbidden': []}),
    'audit_run publish guard removed': lambda d: d['machines']['audit_run'].__setitem__('guards', [g for g in d['machines']['audit_run']['guards'] if g.get('on_violation') != 'partial_result_not_publishable']),
    'job publish guard removed': lambda d: d['machines']['job'].__setitem__('guards', [g for g in d['machines']['job']['guards'] if g.get('on_violation') != 'partial_result_not_publishable']),
    'failed reclassified as successful': lambda d: d['optional_branch_policy']['outcome_values']['failed'].__setitem__('successful', True),
    'unknown reclassified as successful': lambda d: d['optional_branch_policy']['outcome_values']['unknown'].__setitem__('successful', True),
    'missing outcome defaults to success': lambda d: d['optional_branch_policy']['unrecorded_outcome'].__setitem__('evaluates_to', 'succeeded'),
    'unsuccessful outcome untyped': lambda d: d['optional_branch_policy']['outcome_values']['failed'].__setitem__('typed_reason', 'forbidden'),
    'typed reason dropped from the record': lambda d: d['optional_branch_policy']['recorded_outcome'].__setitem__('entry_content', [e for e in d['optional_branch_policy']['recorded_outcome']['entry_content'] if e['element'] != 'typed_reason']),
    'capability declared enabled at CP-00': lambda d: d['optional_branch_policy']['capability_status'].__setitem__('enabled_at_cp_00', True),
    'job allowed to publish a success claim': lambda d: d['optional_branch_policy']['job_consumer'].__setitem__('published_outcome_forbidden', []),
}
assert not rejected(catalog), 'the catalog as written must validate'
accepted = [name for name, mutate in mutations.items()
            for d in [copy.deepcopy(catalog)]
            if not rejected([mutate(d), d][1])]
assert not accepted, accepted

print('optional-branch policy OK')
print('  table total over', len(combos), 'input combinations, no default branch')
print('  any_unsuccessful -> terminal', sorted({row["terminal"] for row in unsuccessful}),
      '| forbidden', sorted({t for row in unsuccessful for t in row["terminal_forbidden"]}))
print('  core published + any_unsuccessful ->', index[('published', 'any_unsuccessful')]['terminal'],
      '| refused with', index[('published', 'any_unsuccessful')]['on_violation'])
print('  typed reasons named:', ', '.join(sorted(named)))
print('  negative probes rejected by the schema:', len(mutations), '/', len(mutations))
PY
```

## Notes for consumers

**Jobs and workers.** Take `run_id`, `job_id` and `attempt_id` as three separate
values and never derive one from another or from `project_uid`/`version_uid`. Read
`machines.audit_run.run_creation` before writing any scheduler: retry, resume,
restart and worker failover create a new **Attempt**, never a Run and never a Job.
Verify the `execution_token` inside the transaction that performs the guarded write,
by equality only. Store a late result from a non-current Attempt; never apply it. If a
run admitted an **optional branch**, read `optional_branch_policy` before writing the
terminal-selection code: an unsuccessful branch means the run ends `partial`, the Job
may not publish a result declaring `success`, and the branch failure is neither a
retryable job error class nor a reason to reach `dead_letter`.

**Analysis.** This family does not declare stages, packages, registries or result
semantics; that is `contracts/analysis/v1`. The analysis `StageResult.error` carrier
is an *internal* typed reason. Mapping it to an externally visible `error_code` is
the control plane's job under `internal_mapping`: an internal code that is not in
this catalog surfaces as `internal_error` and the internal code stays in protected
diagnostics. The capability is named **`execution_token`** in the target contract;
`authority_token` is legacy/cross-lane evidence, not an alias you may keep as a field
name. A payload field still named `authority_token` is a cross-lane mismatch to
return to the integrator, not something either lane patches locally. Neither family
`$ref`s the other while both are candidate drafts.

**Findings and decisions.** `finding_uid` carries expert history;
`finding_observation_id` never does. Read the current verdict from the projection and
never from a mutable field on a finding. Corrections and revocations are appends, and
a revocation leaves the projection at `pending` until an authorized expert appends a
new decision.

**API.** Return exactly this envelope for every failure, with `retryable` taken from
the catalog rather than recomputed, and `contract_version` — not `version` — as the
version field. Accept an idempotency key on every write command and compute the
payload fingerprint as sha256 over RFC 8785 JCS of the schema-valid,
default-normalized payload, excluding transport headers and the key itself.
Transport-level concerns this family deliberately omits — rate limiting, payload size
limits, content negotiation — belong to the API contract family, which must not
overload a domain code for them.

**Optional branches.** This family declares no branch, no branch stage and no branch
result. It declares what a consumer must do with a branch outcome: record exactly one
typed entry per admitted branch, treat a missing outcome as `unknown` and therefore
unsuccessful, and select the terminal from `optional_branch_policy.terminal_selection`.
The project-optimization branch is disabled at CP-00 with its runtime semantics
excluded; its stages, statuses and packages belong to the project-optimization contract
owner in `contracts/optimization/v1/**` under `W5-OPT-01`, and no lane may model them
before that.

**Everyone.** No path, file name, S3 key or display ordinal is identity. No silent
fallback: an unknown state, an unknown code, a missing authoritative reference or an
unrecorded optional-branch outcome is a typed failure. No retention, TTL or legal-hold number exists in this family until
`U-04` is decided.

## Related

- [ARCHITECTURE_BIBLE.md](../../../docs/architecture/ARCHITECTURE_BIBLE.md) —
  P-01, P-02, P-03, P-07, P-08, P-09, P-10, P-11, P-12, P-13, P-18
- [DOMAIN_MODEL.md](../../../docs/architecture/DOMAIN_MODEL.md) and
  [GLOSSARY.md](../../../docs/architecture/GLOSSARY.md)
- [legacy_capability_inventory.md](../../../docs/behavior/legacy_capability_inventory.md)
- [CP00_OWNER_DECISIONS.md](../../../docs/architecture/CP00_OWNER_DECISIONS.md) —
  `PD-01`–`PD-04` records; the dispositions applied here were given by the repository
  owner on 2026-09-01
