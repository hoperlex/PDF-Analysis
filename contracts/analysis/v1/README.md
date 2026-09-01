# Analysis contract v1 — candidate `1.0.0-draft.1`

Owner lane: `W0-ANA-01` (analysis contract owner). Status: **candidate draft, not frozen.**
Every artifact in this directory declares `contract_version` `1.0.0-draft.1`.

The control plane schedules work by immutable package references. The engine returns a
result package. The control plane validates schema, checksums, the attempt-authority
tuple and the required artifact roles before publication. The engine never writes
canonical metadata.

## Artifacts

| File | Role |
|---|---|
| [stage-registry.schema.json](stage-registry.schema.json) | Shape of the canonical stage registry |
| [stage-registry.json](stage-registry.json) | **The sole target source of truth** for canonical stages |
| [legacy-stage-map.schema.json](legacy-stage-map.schema.json) | Shape of the legacy declaration-**site** map |
| [legacy-stage-map.json](legacy-stage-map.json) | Evidence-only map of all 31 accepted legacy declaration sites |
| [legacy-stage-name-map.schema.json](legacy-stage-name-map.schema.json) | Shape of the legacy **name**-level alias map |
| [legacy-stage-name-map.json](legacy-stage-name-map.json) | Evidence-only map of every concrete legacy stage **name** to a canonical stage or an explicit exclusion |
| [job-package.schema.json](job-package.schema.json) | Work handed to an engine for exactly one Attempt |
| [stage-result.schema.json](stage-result.schema.json) | Result of exactly one registry stage |
| [result-package.schema.json](result-package.schema.json) | Result of exactly one Attempt |
| [examples/](examples) | Valid examples plus three `*.invalid.json` negative fixtures |

## Stage registry

`stage-registry.json` is the only target declaration of canonical stage identity,
version, dependencies, required input and output roles, execution scope and
success/partial/failed/skipped semantics. It declares nine canonical stages:

`source_preparation` → `page_geometry_extraction` → `document_context_build` →
(`text_analysis` ‖ `block_analysis`) → `finding_merge` →
(`finding_review` → `finding_correction`) ‖ `norm_verification`.

Design rules that follow from the accepted evidence:

- **No legacy order is copied.** Section 7 of the accepted inventory records at least
  five conflicting legacy notions of stage order. The target order is expressed only as
  `depends_on` in the registry; every execution or display order is derived from it.
- **`text_analysis` and `block_analysis` are independent siblings.** Legacy reordered
  them by feature flag. Declaring them as siblings removes the contradiction instead of
  ratifying one of the two legacy orders.
- **`stage_id` values are unique** inside the registry. Several legacy declaration sites
  may point at the same canonical stage; the reverse is never true.
- **Completion is never inferred from artifact presence.** Legacy inferred completed
  stages from an artifact map. The target derives completion from an explicit
  `StageResult.status` plus the registry's required output roles.
- **A skipped leg degrades explicitly.** `block_analysis` is skippable (`AN-04`, `AN-07`,
  `LSD-07`), so `finding_merge` marks `analysis.block_observations` optional and allows
  `partial`. A merge that ran without one observation leg reports `partial` with a typed
  error; it never reports `succeeded`. The legacy public skip whitelist is now enumerated
  at name level (surface `public_skip_api`, `LSD-07`): legacy let an operator skip
  `crop_blocks`, `text_analysis`, `block_analysis`, `findings_merge`, `norm_verify`,
  `excel`, `tile_audit`, `main_audit` and `prepare`. That whitelist is deliberately **not**
  adopted — skipping a mandatory preparation or merge stage is exactly the silent
  degradation this contract fails closed on. `status_policy.skip_allowed` is the only
  target answer, and the legacy names stay visible as evidence rather than as policy.
- **Execution scope follows the approved registry.** `central_only` and `remote_eligible`
  values, and the rule that a remote worker never writes canonical metadata, rest on
  `PD-02` and `PD-03`, both **approved with modification on 2026-09-01** by the repository
  owner. Remote eligibility is a target policy statement, never a legacy parity claim.

`excluded_scope` records what is deliberately **not** an analysis stage: expert
decisions (`XS-01`), knowledge base (`XS-02`), Excel/publication export (`XS-03`),
decision carryover and debt control (`XS-04`), the section optimization and replication
sub-pipelines (`XS-05`), stage-comparison input slots (`XS-06`), graphic/vector
comparison (`XS-07`), distributed worker lifecycle (`XS-08`), the experimental legacy
document-class gate (`XS-09`), intra-stage batching and retry sub-steps (`XS-10`) and
the project-optimization sub-pipeline (`XS-11`).

`XS-10` and `XS-11` are new in this round and both were found by building the name-level
alias map. `XS-10` covers the legacy names `tile_batches` and `block_retry`: splitting
work into batches and retrying part of it happens inside one stage and one Attempt.
`XS-11` covers `optimization`, `optimization_critic`, `optimization_corrector` and
`optimization_review`, which legacy ran as first-class stages of the audit pipeline body.
Before the name map these four names had no explicit resolution at all — the first-round
site map recorded the sub-pipeline sites but not the main-pipeline optimization
vocabulary.

`PD-05` is **approved on 2026-09-01** and fixes what `XS-11` is allowed to assert. The
four names form a **separate project-optimization sub-pipeline**, run standalone or as an
optional post-findings branch of an audit run. Its product is **improvement proposals,
not audit findings** — that, and nothing about ownership of another pipeline, is why the
names are not audit stages. Its owning boundary is therefore `project_optimization`, a
value distinct from `section_optimization`. **Project optimization and section
optimization are different pipelines**: `XS-05` runs **downstream** and aggregates and
replicates results that already exist across the projects of a section, so `XS-11` makes
no entry-point claim about `XS-05`. The capability is **retained, not dropped**, and it is
no longer merely waiting for somebody: the repository owner closed that question on
**2026-09-01** and `XS-11` now carries a structured `retained_capability_disposition`
naming all four facts:

| Fact | Value |
|---|---|
| Bounded context | `project_optimization`, separate from the core audit context |
| Contract family | `contracts/optimization/v1/**` |
| Contract owner | a separate **project-optimization (OPT) contract owner** — **not** ANA and **not** DOM |
| Carrying task | **`W5-OPT-01`**, scheduled **after** the core audit and decision contracts are frozen |
| Capability state | **disabled until `W5-OPT-01` is accepted**; CP-00 explicitly excludes its runtime semantics |

Until that task is accepted the capability is **switched off**: no analysis stage, package,
example or fixture may claim it, and this lane neither creates nor populates
`contracts/optimization/v1/**` — that path is outside its `allowed_paths`, so the family is
named here and created there. This closes the open input recorded as `U-06`. `XS-05` states
the same separation from its own side without changing its scope: it still covers exactly
`LSD-21`, `LSD-22` and the eight substage names.

The earlier round asserted instead that optimization *is the entry point of the section
optimization sub-pipeline recorded in `XS-05`* and gave `XS-11` the owning boundary
`section_optimization`. Neither claim followed from the evidence, and both were replaced
by the owner disposition recorded as `PD-05`; the exclusion itself stands.

Graphic/vector comparison (`XS-07`) is a future greenfield feature under `PD-04`,
**approved on 2026-09-01**: it is outside legacy parity and outside W0, and its first
contractual inclusion is **W7**, together with a separate golden graphic pair. No graphic
or vector analysis stage is fabricated here, and no W0 fixture may claim one. The only
graphic-related legacy names are the `graphics` substages of the two section
sub-pipelines, which the name map resolves to `XS-07`.

## AuditRun, Job and Attempt

`PD-03` is **approved with modification on 2026-09-01**. `AuditRun`, `Job` and `Attempt`
are distinct, and the modification fixes exactly when each is created. The approved rule
has a restrictive half and a **positive** half, and it rules on **two** entities, not one:
what happens to the `Run` *and* what happens to the `Attempt`. All of it is transferred
here. The whole rule lives as data in `stage-registry.json` → `run_lifecycle.triggers`,
one entry per trigger, and each entry carries the complete outcome tuple:

| `rule_id` | Trigger | `condition` / `idempotency_scope` | `creates_run` | `reuses_existing_run` | `reuses_job` | `creates_attempt` | `reopens_terminal_run` |
|---|---|---|---|---|---|---|---|
| `RC-01` | top-level audit or re-audit command accepted for a frozen input/config set | key not accepted before — `new_idempotency_key` | **`true`** | `false` | `false` | `true` | `false` |
| `RC-02` | same idempotency key **and** same payload | unconditional, terminal Run included — `same_key_and_payload` | `false` | `true` | `true` | **`false`** | `false` |
| `RC-03` | **inputs changed** | different frozen input set, new key — `new_idempotency_key` | **`true`** | `false` | `false` | `true` | `false` |
| `RC-04` | **explicit re-audit** | operator asks, inputs unchanged, new key — `new_idempotency_key` | **`true`** | `false` | `false` | `true` | `false` |
| `RC-05` | **repeat of a terminal Run under a NEW idempotency key** | the new key is **part of the condition** — `new_idempotency_key` | **`true`** | `false` | `false` | `true` | `false` |
| `RC-06` | `retry` | internal lifecycle event, no key — `not_a_client_submitted_command` | `false` | `true` | `true` | **`true`** | `false` |
| `RC-07` | `resume` | internal lifecycle event, no key — `not_a_client_submitted_command` | `false` | `true` | `true` | **`true`** | `false` |
| `RC-08` | `restart` | internal lifecycle event, no key — `not_a_client_submitted_command` | `false` | `true` | `true` | **`true`** | `false` |
| `RC-09` | worker failover | internal lifecycle event, no key — `not_a_client_submitted_command` | `false` | `true` | `true` | **`true`** | `false` |

The bolded `creates_attempt` column is the half of `PD-03` that tells an `Attempt` from a
`Run`: *“retry/resume/restart/worker failover create no new Run — the Job is the same and
a new Attempt is created”*. `RC-06`…`RC-09` therefore carry `creates_attempt: true`, and
`RC-02` — which mints nothing whatsoever — carries `creates_attempt: false`. Every one of
those five values is now a schema constant, not a free boolean.

### `RC-02` beats `RC-05` — the recorded precedence

A repeat of an already terminal Run, submitted with the **same** idempotency key and the
**same** payload, matches the condition of `RC-02` *and* the condition of `RC-05`. The
repository owner ruled the overlap on **2026-09-01**:

> The same idempotency key and the same payload **ALWAYS** return the original Run. A
> repeat of a terminal Run creates a new Run **ONLY** under a new idempotency key.

That ruling is recorded as data in `run_lifecycle.trigger_precedence` as `RP-01`, with
`competing_rule_ids: ["RC-02", "RC-05"]`, `winning_rule_id: "RC-02"`,
`losing_rule_id: "RC-05"` and a `resolved_outcome` that is the `RC-02` outcome tuple
constant for constant. Idempotency is decided **before** Run creation, so the terminal
state of the existing Run is not an input to that decision: a client that retransmits a
request it is unsure was received must never create a duplicate audit by accident.
`RC-05` keeps its positive half — a deliberate repeat of a terminal Run *does* create a
new Run — and pays for it with a **new** idempotency key, which is exactly how the caller
signals that the second Run is intended. `RC-05`'s `condition` says so in its own words,
and the schema pins the phrase `new idempotency key` inside it with a `pattern`, so the
qualifier can no longer be implied and then lost.

**The reverse priority is unwritable.** `winning_rule_id` is `const "RC-02"` and
`losing_rule_id` is `const "RC-05"`; `owner_ruling` must contain both operative phrases;
`resolved_outcome` is five constants. Recording `RC-05` as the winner, or recording the
resolved outcome as “a new Run is created”, fails
`stage-registry.json` × `stage-registry.schema.json`.

**And `RC-02` cannot be made to mean something else.** A precedence that names a rule is
only as strong as the identity of the name it uses. `rule_id` matches `^RC-[0-9]{2}$`,
which on its own would let any `RC-NN` sit on any trigger, so each of the nine triggers
additionally pins its own identifier with a `const` in the same `if`/`then` that pins its
outcome tuple:

| `rule_id` | is fixed to trigger | `rule_id` | is fixed to trigger |
|---|---|---|---|
| `RC-01` | `top_level_audit_command_accepted` | `RC-06` | `retry` |
| `RC-02` | `idempotent_replay_same_key_and_payload` | `RC-07` | `resume` |
| `RC-03` | `inputs_changed` | `RC-08` | `restart` |
| `RC-04` | `explicit_re_audit_command` | `RC-09` | `worker_failover` |
| `RC-05` | `repeat_of_terminal_run` | | |

Renaming `RC-02`, renaming `RC-05`, swapping the two, duplicating one onto another
trigger or rotating the whole set now fails the required
`stage-registry.json` × `stage-registry.schema.json` validation. Without that pin the
swap was the dangerous one: `trigger_precedence` would keep saying “`RC-02` wins” while
`RC-02` denoted the terminal repeat, silently inverting the owner's ruling in a document
that still validated. Because every trigger value occurs exactly once and its `rule_id` is
fixed, `winning_rule_id: "RC-02"` and `losing_rule_id: "RC-05"` resolve to the idempotent
replay and to the repeat of a terminal Run **by construction**; Gate D re-checks both the
nine `trigger` → `rule_id` pairs and the resolution of both references from the outside.

### A terminal Run is never reopened

**A terminal Run is never reopened — and a repeat of a terminal Run under a new key
creates a new Run.** The two statements look like a contradiction and are not one, because
they constrain different things. *Never reopened* constrains the **existing entity**: a
Run that reached a terminal state keeps its `run_id`, its terminal state and its recorded
results forever, and no later request re-enters it. *Creates a new Run* constrains **what
the repeated request produces**: a separate `AuditRun` with its own `run_id`, Job and first
Attempt, standing beside the terminal one. The old Run is neither continued nor mutated; a
second entity simply comes into existence. `run_lifecycle.terminal_run_rule` states this,
and every trigger — `RC-05` included — carries `reopens_terminal_run: false`.

The transfer is **machine-checkable, not only prose**. `stage-registry.schema.json`
requires `run_lifecycle` at the root, requires exactly nine `triggers`, demands each of
the nine trigger values exactly once (`contains` with `minContains`/`maxContains` `1`),
and pins **the whole outcome tuple of every trigger** — `creates_run`,
`reuses_existing_run`, `reuses_job`, `creates_attempt`, `reopens_terminal_run` and
`idempotency_scope` — plus **the `rule_id` of every trigger**, with one `if`/`then` per
trigger. Two further trigger-independent
rules back that up: `same_key_and_payload` forces “mints nothing at all”, and
`not_a_client_submitted_command` forces “no Run, exactly one new Attempt”. Deleting the
`inputs_changed` or `repeat_of_terminal_run` entry, recording either with
`creates_run: false`, recording `retry`, `resume`, `restart` or `worker_failover` with
`creates_attempt: false`, recording the idempotent replay with `creates_attempt: true`,
recording the reverse `RC-02`/`RC-05` precedence, or moving a `rule_id` onto a different
trigger, each fails the required
`stage-registry.json` × `stage-registry.schema.json` validation. Gate D re-checks the same
facts from the outside over the full tuple. A half-transferred `PD-03` can no longer pass
the gates.

That is why `JobPackage` carries no run-creation intent and `ResultPackage` mints
nothing: the engine echoes the authority tuple it received. The rule is restated **in
full** in the `attempt_authority` description of both package schemas — including the
positive half, the `creates_attempt` half and the `RC-02` over `RC-05` precedence — so a
consumer reading only the schema sees all of it, and those descriptions point back at
`run_lifecycle` as the authoritative form. In each package schema the description on the
root `attempt_authority` property and the description on `$defs.attempt_authority` are the
**same string**; Gate D compares them for equality and checks both for every clause of the
rule, so the two can no longer drift apart and leave one of them abbreviated. `XS-08`
(worker lifecycle) and `XS-10` (retry sub-steps) both restate the restrictive half from
the exclusion side: a failover or a retry is a new Attempt, never a new Run and never a
stage.

## Legacy stage map — declaration sites

`legacy-stage-map.json` covers **exactly the 31 declaration sites** of section 2.2
“Pipeline stage/order declarations” in the accepted inventory, as
`LSD-01` … `LSD-31`. It is alias and traceability evidence only; it is never a source of
target truth.

- `source_declaration_site` is the normalized inventory table cell with Markdown
  backticks removed.
- `source_inventory_commit` is `667fb00fe3e45d1ce0bce7860725c1654b4cdeba` on every entry.
- `legacy_source_commit` is `32b9d903792b30506048a1d42b0e6b2d07aee403` on every entry.
- `inventory_disposition` repeats the inventory's own disposition cell, so an
  inventory-level `mapped` row that is nevertheless outside analysis scope stays visible.
- `target_kind` is one of `stage`, `control_plane`, `sub_pipeline`, `excluded`;
  `target_concern` names the specific target owner.
- `canonical_stage_id` is present **if and only if** `target_kind` is `stage`.
- `related_stage_ids` records which canonical stages a cross-stage legacy site touched. It
  is a **superset of the name-level evidence**: every canonical stage that a name declared
  at that site resolves to must appear here, and a site may additionally touch a stage it
  never names, as an orchestration body or a policy set does. Gate C enforces the superset
  direction, so the two maps can no longer drift apart silently.

Distribution: `control_plane` 25, `excluded` 3, `sub_pipeline` 2, `stage` 1.

`LSD-31` (`norms/runner.py active norm stages`) is the only declaration site whose scope
is exactly one canonical stage; it collapses the legacy norm-verification and norm-fix
set into `norm_verification`. The other 30 sites are cross-stage vocabularies, orders,
alias tables and eligibility sets, or are out of analysis scope; mapping any of them to a
single `stage` would fabricate a precision the evidence does not support. Many-to-one is
structurally supported and exercised: every canonical stage is referenced by between 16
and 26 declaration sites through `related_stage_ids`, and `stage_id` stays unique.

Building the name map corrected `related_stage_ids` on **13 of the 31 rows** — `LSD-02`,
`LSD-03`, `LSD-04`, `LSD-05`, `LSD-07`, `LSD-09`, `LSD-12`, `LSD-13`, `LSD-16`, `LSD-19`,
`LSD-20`, `LSD-24`, `LSD-28`. Each had at least one canonical stage that its own legacy
names demonstrably resolve to but which the first round had not listed; `LSD-07` alone was
missing five. Only additions were made: no row, id, site name, `target_kind`, provenance
SHA or the 25/2/3/1 distribution changed, and the 31/31 coverage gate still passes.

This site map answers *where legacy declared stages*. It does **not** answer *which
concrete legacy name means which canonical stage* — that is the name map below, and
`PD-02` is approved only with both present.

## Legacy stage name map — concrete names

`legacy-stage-name-map.json` is required by `PD-02` as approved with modification on
2026-09-01. Its unit is **one concrete legacy stage name**, not a declaration site. It
covers **62 names** read from the frozen legacy tree at
`32b9d903792b30506048a1d42b0e6b2d07aee403`, with **293 observations** spanning
**31 of 31** alias-bearing declaration sites.

Each name entry carries, at top level, its primary observation and its resolution:

- `legacy_stage_name` — the exact legacy string; unique across the whole map.
- `surface` — where the name is observable. Thirty surfaces are modelled, among them
  `persisted_stage_enum`, `public_retry_api`, `public_skip_api`, `resume_alias_vocabulary`,
  `status_alias_table`, `artifact_presence_map`, `persisted_stage_value_alias`,
  `routing_stage_scope_map`, `routing_preset_vocabulary`, `remote_eligibility_set`,
  `provider_requirement_set`, `ui_stage_model_config` and `ui_artifact_alias`.
- `source_declaration_id` — the `LSD-NN` site of the 31-row map the name was read from.
- `evidence` — an immutable locator
  `<legacy_commit>:<path>:<symbol>@<line>` or `…@<start>-<end>` that resolves with
  `git show` at the pinned legacy commit.
- `evidence_literal` and `evidence_line` — the exact substring carrying the name and the
  line it sits on inside the anchored region, so the locator is checkable to the name and
  not only to the region.
- `observed_surfaces` / `observed_declaration_ids` and `additional_observations[]` — every
  further place the same name appears, each with its own surface, site and locator.
- `resolution` — exactly one of `canonical_stage` (with `canonical_stage_id`) or
  `excluded` (with `excluded_scope_id`). There is no third state and no unresolved name.

Twenty-nine names resolve to a canonical stage and thirty-three are explicitly excluded.
The mandatory example is present and gated:

```
findings_merge  →  surface persisted_stage_enum, LSD-01,
                   32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/models/audit.py:AuditStage@8-27
                   →  canonical_stage_id  finding_merge
```

`findings_merge` is additionally observed on 21 sites and 22 surfaces, including the
public retry API, the public skip whitelist, the resume vocabulary and the artifact
presence map. A golden fixture carrying `public_stage_name: "findings_merge"` is
therefore resolvable to `finding_merge` by contract rather than by convention.

Resolution to a canonical stage per registry stage:

| Canonical stage | Legacy names that resolve to it |
|---|---|
| `source_preparation` | `prepare` |
| `page_geometry_extraction` | `crop_blocks` |
| `document_context_build` | `block_context`, `gemma_enrichment`, `document_graph` |
| `text_analysis` | `text_analysis`, `01_text_analysis`, `02_text_analysis` |
| `block_analysis` | `block_analysis`, `blocks_analysis`, `block_batch`, `tile_audit`, `v4_extraction`, `01_blocks_analysis`, `02_blocks_analysis`, `01_blocks_for_text`, `02_blocks_for_text` |
| `finding_merge` | `findings_merge`, `findings`, `main_audit`, `merge`, `v4_formatter` |
| `finding_review` | `findings_review`, `findings_critic` |
| `finding_correction` | `findings_corrector` |
| `norm_verification` | `norm_verify`, `norm_fix`, `norm_requote`, `norms_verified` |

Explicit exclusions: `tile_batches` and `block_retry` (`XS-10`); `debt_control` and
`decision_carryover` (`XS-04`); `excel` (`XS-03`); `optimization`, `optimization_critic`,
`optimization_corrector`, `optimization_review` (`XS-11`); the eight section
optimization/replication substages `collect`, `normalize`, `synthesize`, `agent`,
`review`, `validate`, `package`, `expert` (`XS-05`); `graphics` (`XS-07`); `stage_1` and
`stage_2` (`XS-06`); the eight distributed-task lifecycle steps `queued`, `transfer`,
`preparing`, `auditing`, `collecting`, `returning`, `importing`, `done` (`XS-08`); and the
five experimental document classes `project_documentation`, `working_documentation`,
`detailing`, `mixed`, `unknown` (`XS-09`).

**Known granularity gap.** `prepare` is the one coarse legacy name: the retry alias table
and the status alias table both fold `crop_blocks` into it, so one legacy name covered
both source registration and page cropping. It resolves to `source_preparation` and
records `also_covers_stage_ids: ["page_geometry_extraction"]`. `also_covers_stage_ids` is
never a second resolution — the control plane resolves `prepare` to `source_preparation`
and then schedules from registry `depends_on`. This is the only entry where the legacy
vocabulary is coarser than the target registry.

The name map is evidence and alias resolution only. `stage-registry.json` names it in
`alias_resolution` and stores no legacy alias itself; the control plane resolves a legacy
name at its boundary and passes only canonical `stage_id` values to the engine, which
never accepts a legacy name.

## Attempt authority and fencing

`JobPackage` and `ResultPackage` both require the complete `attempt_authority` tuple:

```
attempt_authority = { run_id, job_id, attempt_id, execution_token }
```

- All four members are required. A partial tuple is rejected; see
  [examples/result-package.missing-attempt-authority.invalid.json](examples/result-package.missing-attempt-authority.invalid.json).
- `execution_token` is the canonical field name, chosen by the repository owner on
  2026-09-01 as the integration decision across the analysis and domain families. It is an
  opaque **equality-only capability**: never ordered, parsed, decoded, compared for
  magnitude or derived from business data, and never an identity.
- It is **refreshed on every new Attempt** and **verified inside the publishing
  transaction**. Fencing is a property of that behaviour, not of the field name, and this
  contract promises **no monotonic number**. The earlier `fencing_token` field, which also
  allowed an integer and therefore implied ordering, is gone.
- `authority_token` and `fencing_token` are admissible **only as legacy evidence**. No
  schema, example, negative fixture or field in this family uses either name.
- The tuple lives in exactly one place per package. There is no duplicated top-level
  `run_id`/`job_id`/`attempt_id` that could drift from it.
- Replaying a byte-identical valid result under the same authority is idempotent. The
  same authority with different content conflicts. A stale token never publishes.

The token is an execution capability, not an identity, and it is the only
capability-class value a package carries. It never appears in an `error` message or
`details`.

These semantics extend legacy behavior; they are **not** a legacy parity claim. The
accepted inventory found `Job` and `Attempt` but no distinct `Run` entity, and found
connection-epoch and attempt-token checks rather than a canonical fencing contract.
`PD-03` is **approved with modification on 2026-09-01**; the Run/Job/Attempt creation
rules it fixes are written out under [AuditRun, Job and Attempt](#auditrun-job-and-attempt)
above.

## Status and error semantics

`StageResult.status` is one of `succeeded`, `partial`, `failed`, `skipped`.

- `failed`, `partial` and `skipped` **require** a typed `error` object
  (`code`, `message`, `retryable`, optional `details`).
- `succeeded` **forbids** `error`. A succeeded stage carries no hidden error state.
- `skipped` additionally requires an empty `artifacts` array and `retryable: false`; its
  `error.code` names the skip reason. Skipping is an explicit decision, never silence.
- `succeeded` also requires, per registry, every output role marked `required: true`.
  That rule is enforced by the consumer against the registry; JSON Schema alone cannot
  express it.

Negative fixtures: [stage-result.failed-missing-error.invalid.json](examples/stage-result.failed-missing-error.invalid.json),
[stage-result.succeeded-with-error.invalid.json](examples/stage-result.succeeded-with-error.invalid.json).

`error.details` carries safe scalar diagnostics only: never a path, object key, URL,
credential, execution or authority token, prompt or raw protected content.

`error.code` is a lowercase snake_case token in the **stage-reason namespace**: it names
why one stage did not fully succeed. It is deliberately not the externally visible domain
error-envelope code. The control plane maps a stage reason onto a domain envelope code
when it surfaces a failure to a caller; the engine never emits an API envelope. The domain
error catalog in [../../domain/v1/README.md](../../domain/v1/README.md) is a parallel W0.2
candidate, so this contract does not `$ref` it and does not fork it. Whether the two
namespaces should be unified is an integrator/owner question, not a lane-local edit.

## Artifact references

Every artifact reference exposes `role`, `blob_id`, `sha256`, `size_bytes`,
`media_type` and an optional display-only `logical_name`. `additionalProperties` is
`false`, so an object key, bucket name, URL, presigned link, credential or secret cannot
be carried. `logical_name` excludes `/`, `\` and `:` and is never identity.

## `ResultPackage` references `StageResult`

`result-package.schema.json` no longer defines its own copy of the StageResult rules. Its
`stage_results[].items` is `{"$ref": "urn:auditmanager:analysis:stage-result:v1"}`, the
canonical `$id` of [stage-result.schema.json](stage-result.schema.json). The resource is
carried as a JSON Schema 2020-12 bundled resource under `$defs/stage_result` because the
pinned validation toolchain resolves no external file or network reference; that is a
transport mechanism, not a second definition. The invariant is mechanically checkable:

```
.venv/bootstrap/bin/python -c "import json; a=json.load(open('contracts/analysis/v1/result-package.schema.json')); \
b=json.load(open('contracts/analysis/v1/stage-result.schema.json')); \
assert a['\$defs']['stage_result']==b; print('bundled == standalone')"
```

Any change to StageResult is made in the standalone file first and then re-bundled.

## Compatibility

- Backward compatible with `1.0.0-draft.0`: **no**.
- Breaking changes: `schema_version: 1` replaced by `contract_version: "1.0.0-draft.1"`
  as the single envelope version key — `version` and `schema_version` appear nowhere in
  this family and Gate A enforces that; `fencing_token` replaced by the required
  `attempt_authority` tuple whose capability member is `execution_token`; `stage_name`
  replaced by registry-bound `stage_id`; `error_code`/`error_message` replaced by the
  typed `error` object; `stage_registry` reference required in both packages;
  `usage_summary` members required.
- Changed inside this round: `authority_token` renamed to `execution_token` in both
  package schemas, in both valid examples and throughout this README. The
  missing-authority negative fixture omits the token entirely and now fails closed on the
  required `execution_token` member. `legacy-stage-name-map.json` and its schema added;
  `stage-registry.json` gained
  the required `alias_resolution` block, exclusions `XS-10` and `XS-11`, and recorded
  owner decisions. `legacy-stage-map.json` is unchanged — the 31/31 site gate keeps
  passing byte-for-byte. `XS-11` was then re-grounded on `PD-05`: `owning_boundary`
  moved from `section_optimization` to the new `project_optimization` value, the
  entry-point claim about `XS-05` was removed, and a `retained_capability` statement was
  added; `stage-registry.schema.json` gained the `project_optimization` boundary value,
  the optional `retained_capability` member and `PD-05` in both decision enums.
  `legacy-stage-name-map.json` is byte-identical across that correction, so all 293
  evidence locators, 62 legacy names and 31/31 alias-bearing sites are untouched.
- Changed in the second review round, contract text only: `XS-01` and `XS-04` no longer
  call the approved `PD-01` "proposed" and cite it through the new `external_decision`
  block; `stage-registry.json` gained the root `run_lifecycle` block carrying all nine
  `PD-03` creation triggers, including the two positive cases (`inputs_changed`,
  `repeat_of_terminal_run`) that the prose transfer had dropped, plus the root
  `fail_soft_policies` block holding this lane's half of `FS-04`; `XS-11` gained
  `retained_capability_disposition` (family, OPT owner, `W5-OPT-01`, capability disabled,
  CP-00 runtime exclusion) closing `U-06`; `PD-05` gained `identifier_assigned_by`,
  `identifier_confirmed_by` and `identifier_confirmed_on`; `PD-03`'s recorded modification
  was completed; both package schemas restate the completed rule in `attempt_authority`.
  `stage-registry.schema.json` makes each of those checkable rather than declarative.
  Nothing in `legacy-stage-map.json`, `legacy-stage-name-map.json`, the stage list or the
  examples changed: 9 stages, 62 names, 293 locators, 31/31 sites and the 25/2/3/1 site
  distribution are byte-for-byte the same.
- Changed in the third review round, contract text only: `run_lifecycle` now pins the
  **whole outcome tuple** of every trigger instead of `creates_run` alone — each of the nine
  triggers carries a `condition` and an `idempotency_scope`, and
  `stage-registry.schema.json` fixes `creates_run`, `reuses_existing_run`, `reuses_job`,
  `creates_attempt`, `reopens_terminal_run` and `idempotency_scope` per trigger with one
  `if`/`then` each, so `retry`/`resume`/`restart`/`worker_failover` with
  `creates_attempt: false` and the idempotent replay with `creates_attempt: true` are now
  schema-invalid; `run_lifecycle.trigger_precedence` records the owner's `RC-02`-over-`RC-05`
  ruling as `RP-01` with constant winner, loser and resolved outcome, so the reverse priority
  cannot be written; `RC-05`'s `condition` names the **new idempotency key** and the schema
  pattern-pins that phrase; the `attempt_authority` description of each package schema is now
  one string used verbatim in both the root property and `$defs`, carrying the complete rule;
  Gate D checks the full tuple, the precedence and the description parity. Nothing in
  `legacy-stage-map.json`, `legacy-stage-name-map.json`, the stage list, `stage-result.schema.json`
  or any example changed: 9 stages, 62 names, 293 locators, 31/31 sites and the 25/2/3/1 site
  distribution are byte-for-byte the same.
- Changed in the fourth review round, contract text only: `run_creation_rule` now pins the
  **identity** of every trigger as well as its outcome — the `rule_id` of each of the nine
  triggers is a `const` in the same `if`/`then` that pins its tuple, so renaming `RC-02`,
  renaming `RC-05`, swapping them, duplicating one onto another trigger or rotating the
  whole set fails `stage-registry.json` × `stage-registry.schema.json` instead of silently
  re-pointing the recorded `RC-02`-over-`RC-05` precedence; Gate D gained the exact
  `trigger` → `rule_id` map for all nine pairs and a referential-integrity check that both
  precedence references resolve to the triggers the owner ruling is about, not merely to
  identifiers that exist. The same question was then asked of every other cross-artifact
  ID reference: Gate C now pins each `stage_id` to its capability evidence and produced
  artifact roles and each `excluded_scope_id` to its `owning_boundary` (so those targets
  cannot be swapped or duplicated under a surviving reference) and resolves every
  `depends_on` edge; Gate B binds each name observation to the legacy file its own
  declaration site names; Gate A resolves every `stage_id` named by a valid example. The
  new "Referential integrity" section lists every ID reference, what pins it and the one
  deliberate residue. `stage-registry.json`, `legacy-stage-map.json`,
  `legacy-stage-name-map.json`, `stage-result.schema.json`, both package schemas and every
  example are unchanged in this round: 9 stages, 62 names, 293 locators, 31/31 sites and
  the 25/2/3/1 site distribution are byte-for-byte the same, and
  `idempotency_scope: new_idempotency_key` on `RC-01`, `RC-03` and `RC-04` stands as the
  owner confirmed it.
- Unknown registry version, unknown `stage_id` and unknown package version fail closed.
- This draft is **not frozen**. Before freeze, this task's path may simply be reverted.
  After freeze, changes follow the version-bump and freeze-break procedure in
  [../../../docs/program/waves/W0.2_architecture_domain_contract.md](../../../docs/program/waves/W0.2_architecture_domain_contract.md).

## Owner decisions

The repository owner is the sole authority for these product-semantic decisions. The
states below were ruled by the repository owner on **2026-09-01** and are recorded with
that date and authority in `stage-registry.json` `owner_decisions`. A claim of approval
relayed by any other party is not a decision and must not be written here.

| Decision | State | Effect here |
|---|---|---|
| `PD-02` one versioned stage registry is authoritative | `approved_with_modification` (2026-09-01) | `stage-registry.json` plus the required name-level `legacy-stage-name-map.json`; the registry's `alias_resolution` binds the two |
| `PD-03` distinct Run/Job/Attempt plus mandatory current-attempt authority | `approved_with_modification` (2026-09-01) | `attempt_authority` in both packages; the complete nine-trigger creation rule as data in `run_lifecycle`, each trigger carrying its whole outcome tuple including `creates_attempt`; the `RC-02`-over-`RC-05` precedence in `run_lifecycle.trigger_precedence`; the same rule restated in full and identically in the root property and `$defs` description of both package schemas; `XS-08` and `XS-10` |
| `PD-04` graphic/vector comparison is future greenfield scope | `approved` (2026-09-01) | `excluded_scope` `XS-07`; first contractual inclusion is W7 with a separate golden graphic pair; no graphic analysis stage |
| `PD-05` project optimization is a separate sub-pipeline, retained outside the analysis boundary | `approved` (2026-09-01); number assigned by this lane, **confirmed by the program integrator on 2026-09-01** | `excluded_scope` `XS-11` with `owning_boundary` `project_optimization`, its `retained_capability` statement plus `retained_capability_disposition`, and the separation note on `XS-05`; the `project_optimization` boundary value in `stage-registry.schema.json` |
| `PD-01` (**not** an analysis-family decision; recorded for provenance only) | `approved_with_modification` (2026-09-01), owned by the domain and architecture lanes | cited from `XS-01` and `XS-04` through `external_decision`; no `owner_decisions` entry and no analysis semantics derived from it |

`PD-02`'s modification is that this lane is accepted **only** with a name-level alias map
whose unit is a concrete legacy name, each carrying a surface, a `source_declaration_id`,
immutable evidence and either a canonical target or an explicit exclusion, with
`findings_merge` → `finding_merge` present as a checkable entry.

`PD-03`'s modification is the nine-trigger Run/Job/Attempt creation rule above — including
its positive half, where a **change of inputs**, an **explicit re-audit** and a **repeat of
a terminal Run under a new idempotency key** each create a **new** Run, and including its
**Attempt** half, where `retry`, `resume`, `restart` and worker failover each create a new
`Attempt` on the same `Job` and an idempotent replay creates nothing at all — plus the field
name `execution_token`; fencing is a behaviour, not a monotonic number, and `authority_token`
and `fencing_token` survive only as legacy evidence. The rule is carried as data in
`run_lifecycle.triggers`, where the schema forces every case to be present **with every
member of its outcome tuple**, and the one overlap between two triggers is resolved by the
owner ruling recorded in `run_lifecycle.trigger_precedence`: the same idempotency key with
the same payload **always** returns the original Run, and a repeat of a terminal Run creates
a new Run **only** under a new idempotency key.

`PD-05` has no modification: `optimization`, `optimization_critic`,
`optimization_corrector` and `optimization_review` are a separate project-optimization
sub-pipeline, started on its own or as an optional post-findings branch, whose product is
improvement proposals rather than audit findings; section optimization is a downstream
aggregation and replication pipeline and not the same pipeline; the four names leave the
nine-stage core audit registry and are retained as a distinct capability whose bounded
context, contract family (`contracts/optimization/v1/**`), OPT contract owner and carrying
task (`W5-OPT-01`) the owner named on 2026-09-01, and which stays **disabled** until that
task is accepted. `PD-05` changes no canonical stage, no locator and no legacy name
resolution — every one of the four names already resolved to `XS-11`.

The **number** `PD-05` was assigned by this lane rather than issued by the repository
owner, and the **program integrator confirmed it on 2026-09-01**. The record therefore
carries `identifier_assigned_by: "analysis (ANA) lane"`, `identifier_confirmed_by:
"program integrator"` and `identifier_confirmed_on: "2026-09-01"`; the schema requires all
three on `PD-05`. The label is a name for the owner's disposition and is never part of it.

`PD-01` (append-only expert decisions) is **approved with modification on 2026-09-01** by
the repository owner. It is **not an analysis-family decision** — it is owned by the
domain and architecture lanes — so it carries no entry in `owner_decisions` and is not
referenceable from an exclusion's `owner_decision`. That ownership is the only reason this
lane takes no position on it; it is emphatically **not** an open proposal. Its approved
modification is that correction and revocation each create a **new `decision_id`**, that
history is **preserved** rather than overwritten or deleted, and that a revocation moves
the derived projection to **`pending`** without automatically restoring the previously
current verdict. `XS-01` and `XS-04` record only the exclusion of expert decisions,
knowledge base and decision carryover from the analysis stages, and cite `PD-01` through
the structured `external_decision` block, which carries its state, date, deciding
authority, owning lanes and modification. The block's `state` enum admits only decided
values and its `analysis_family_decision` is fixed to `false`, so an approved
cross-family decision can no longer be written down here as a proposal — the earlier
wording of both notes, which called `PD-01` merely proposed, would now fail schema
validation.

### `FS-04` is split — this lane encodes the norm/core part only

The repository owner split the `FS-04` fail-soft policy on **2026-09-01**. Only the first
row below is analysis policy; `stage-registry.json` → `fail_soft_policies` records it that
way, with the other two rows listed as `parts_outside_this_lane` so the split stays visible
and cannot be quietly absorbed here.

| Part | Owner | Recorded here as |
|---|---|---|
| **norm / core stage terminal semantics** | **this lane (ANA)** | `analysis_part` — the whole target policy is `status_semantics` plus each stage's `status_policy`: `succeeded` only with every required output role and no error at all, a norm or core branch that could not complete reports `partial`/`failed` with a typed error, a stage that did not run reports `skipped` with a typed reason, and no warning artifact ever lets a degraded stage claim `succeeded` |
| project-optimization stages and results | **OPT contract owner**, `contracts/optimization/v1/**`, task `W5-OPT-01` | `parts_outside_this_lane` — named, not encoded; the terminal semantics of the four `optimization*` names left this boundary with `PD-05`/`XS-11` |
| `AuditRun`/`Jobs` as **consumer** | **domain (DOM) lane**, `contracts/domain/v1/**` | `parts_outside_this_lane` — the inbound expectation "failure of the optional optimization branch yields an explicit `partial`, never a full success" is recorded verbatim as somebody else's rule, and no analysis schema restates it as its own |

No freeze is declared by this lane, and consumers must not treat this draft as frozen
until the W0.2 integrator records acceptance.

## Gates

Run from the repository root with the provisioned validator interpreter:

```
.venv/bootstrap/bin/python -c "import glob,json; from jsonschema import Draft202012Validator as V; [V.check_schema(json.load(open(p))) for p in glob.glob('contracts/analysis/v1/*.schema.json')]"
.venv/bootstrap/bin/python -m jsonschema -i contracts/analysis/v1/stage-registry.json contracts/analysis/v1/stage-registry.schema.json
.venv/bootstrap/bin/python -m jsonschema -i contracts/analysis/v1/legacy-stage-map.json contracts/analysis/v1/legacy-stage-map.schema.json
.venv/bootstrap/bin/python -m jsonschema -i contracts/analysis/v1/legacy-stage-name-map.json contracts/analysis/v1/legacy-stage-name-map.schema.json
.venv/bootstrap/bin/python -m jsonschema -i contracts/analysis/v1/examples/job-package.example.json contracts/analysis/v1/job-package.schema.json
.venv/bootstrap/bin/python -m jsonschema -i contracts/analysis/v1/examples/stage-result.example.json contracts/analysis/v1/stage-result.schema.json
.venv/bootstrap/bin/python -m jsonschema -i contracts/analysis/v1/examples/result-package.example.json contracts/analysis/v1/result-package.schema.json
.venv/bootstrap/bin/python scripts/validate_bootstrap.py
```

The three `examples/*.invalid.json` fixtures must exit **non-zero** against their schema.
The 31/31 coverage command is recorded in
[../../../docs/program/tasks/W0-ANA-01.md](../../../docs/program/tasks/W0-ANA-01.md);
its frozen input is section 2.2 of
[../../../docs/behavior/legacy_capability_inventory.md](../../../docs/behavior/legacy_capability_inventory.md)
read from commit `667fb00fe3e45d1ce0bce7860725c1654b4cdeba`, not from the working tree.

### Referential integrity — what every ID reference resolves to

Every identifier one artifact of this family points at is pinned twice: the reference must
**resolve**, and the target must still **be the thing it was**. Existence alone is not
enough — an ID that can be renamed, swapped with another or duplicated lets a reference
survive while silently denoting something else.

| Reference | Resolves to | What pins it |
|---|---|---|
| `trigger_precedence.winning_rule_id` / `losing_rule_id` / `competing_rule_ids` | `run_lifecycle.triggers[].rule_id` | `const` on each reference, plus `const` `rule_id` per trigger; Gate D re-resolves both references to the triggers the ruling is about |
| `run_lifecycle.triggers[].rule_id` | the trigger it denotes | one `const` per trigger in `stage-registry.schema.json`; each of the nine `trigger` values required exactly once; Gate D checks all nine pairs |
| name map `canonical_stage_id`, `also_covers_stage_ids`; site map `canonical_stage_id`, `related_stage_ids` | registry `stages[].stage_id` | Gate A existence; the 31/31 required test checks `stage_id` uniqueness; Gate C pins each `stage_id` to its capability evidence and produced artifact roles, and resolves every `depends_on` edge |
| name map `excluded_scope_id` | registry `excluded_scope[].excluded_scope_id` | Gate A existence; Gate C pins each of the eleven ids to its `owning_boundary`, requires distinct titles and tells `XS-01` from `XS-04` by title |
| name map `source_declaration_id`, `observed_declaration_ids`, `alias_bearing_declaration_ids` | site map `declarations[].source_declaration_id` | Gate A existence and set equality; Gate B binds each observation to the legacy file its own site names; the 31/31 required test pins all 31 `(LSD-NN, site)` pairs against the frozen inventory ledger, so an `LSD` id cannot be renamed, swapped or duplicated |
| registry `evidence.legacy_declaration_ids`, exclusion `legacy_declaration_ids` | site map `LSD-NN` | Gate C subset check against the 31 sites |
| example `stage_id` values | registry `stages[].stage_id` | Gate A resolves every `stage_id` occurring in the valid examples |
| package `stage_registry` block | the registry contract and version | `const` in both package schemas |
| registry `alias_resolution.name_map_contract` / `site_map_contract` | the two map contracts | `const` in `stage-registry.schema.json` |
| `owner_decisions[].decision_id`, exclusion `owner_decision`, `external_decision.decision_id`, `fail_soft_policies[].policy_id` | the recorded decisions and policies | schema enums; Gate D pins `PD-05`'s identifier provenance, `PD-01` as non-analysis, `FS-04`'s split and `XS-11`'s disposition |
| `result-package.schema.json` `$defs.stage_result` | `stage-result.schema.json` | Gate D equality check plus the bundled-vs-standalone command above |

**One residue, stated deliberately.** Which of the nine canonical stages a given legacy
name maps to is this lane's recorded judgment, not a resolvable reference: re-pointing a
name from one *existing* stage to another *existing* stage leaves every reference valid,
and no gate rejects it. Detecting it mechanically would mean restating all 62 name→stage
pairs inside the gate, i.e. duplicating the artifact it checks. What the gates do enforce
around that judgment is everything that is checkable: the name exists in the frozen legacy
tree at a pinned locator inside the file its declaration site names (Gate B), the target
`stage_id` exists and still denotes the same stage (Gate C), the owner-mandated
`findings_merge` → `finding_merge` pair is fixed (Gate A), and every stage keeps at least
one legacy name (Gate A/C). The judgment itself is carried per name with its `rationale`
and is what the independent `PD-02` reviewer reads.

### Gate A — name-level alias map structure

Checks legacy-name uniqueness, that every `source_declaration_id` resolves into the
31-row site map, that every name has exactly one resolution, that every
`canonical_stage_id` exists in the registry and every `excluded_scope_id` exists in
`excluded_scope`, that every `stage_id` named by a valid example resolves in the registry,
that `findings_merge` resolves to `finding_merge`, that every registry
stage has at least one legacy name, that the alias-bearing site set equals the observed
site set, and that the envelope version key is `contract_version` with no `version`,
`schema_version`, `authority_token` or `fencing_token` field anywhere in the family.

```
.venv/bootstrap/bin/python -c "
import json,glob
from pathlib import Path
P=lambda n: json.loads(Path('contracts/analysis/v1/'+n).read_text())
r=P('stage-registry.json'); s=P('legacy-stage-map.json'); n=P('legacy-stage-name-map.json')
sites={d['source_declaration_id'] for d in s['declarations']}
stages={x['stage_id'] for x in r['stages']}; xs={x['excluded_scope_id'] for x in r['excluded_scope']}
names=[e['legacy_stage_name'] for e in n['names']]
obs=[(e,o) for e in n['names'] for o in [e]+e.get('additional_observations',[])]
assert len(names)==len(set(names))==n['name_count'], 'legacy stage names are not unique'
assert all(o['source_declaration_id'] in sites for _,o in obs), 'unresolvable source_declaration_id'
assert all((e['resolution']=='canonical_stage')==('canonical_stage_id' in e) for e in n['names'])
assert all((e['resolution']=='excluded')==('excluded_scope_id' in e) for e in n['names'])
assert all(e['canonical_stage_id'] in stages for e in n['names'] if e['resolution']=='canonical_stage'), 'canonical_stage_id absent from registry'
assert all(e['excluded_scope_id'] in xs for e in n['names'] if e['resolution']=='excluded'), 'excluded_scope_id absent from registry'
assert all(t in stages for e in n['names'] for t in e.get('also_covers_stage_ids',[]))
m={e['legacy_stage_name']:e.get('canonical_stage_id') for e in n['names']}
assert m['findings_merge']=='finding_merge', 'mandatory findings_merge -> finding_merge missing'
ab=set(n['alias_bearing_declaration_ids'])
assert ab<=sites and ab=={o['source_declaration_id'] for _,o in obs}, 'alias-bearing site set does not match observations'
assert stages=={e['canonical_stage_id'] for e in n['names'] if e['resolution']=='canonical_stage'}, 'a registry stage has no legacy name evidence'
assert all(set(e['observed_declaration_ids'])=={o['source_declaration_id'] for o in [e]+e.get('additional_observations',[])} for e in n['names'])
assert all(set(e['observed_surfaces'])=={o['surface'] for o in [e]+e.get('additional_observations',[])} for e in n['names'])
assert all(len(s['declarations'])==31 and d['source_declaration_id'] in sites for d in s['declarations'])
def keys(o,req=False):
    if isinstance(o,dict):
        for k,v in o.items():
            yield k
            yield from keys(v,k=='required')
    elif isinstance(o,list):
        for v in o:
            if req and isinstance(v,str): yield v
            else: yield from keys(v)
for p in sorted(glob.glob('contracts/analysis/v1/*.json'))+sorted(glob.glob('contracts/analysis/v1/examples/*.json')):
    d=json.loads(Path(p).read_text())
    assert 'version' not in d and 'schema_version' not in d, p
    assert d.get('contract_version')=='1.0.0-draft.1', p
    if p.endswith('.schema.json'):
        pr=d.get('properties',{})
        assert 'contract_version' in pr and 'version' not in pr and 'schema_version' not in pr, p
    used=set(keys(d))
    assert 'schema_version' not in used and 'version' not in used, p
    assert 'authority_token' not in used and 'fencing_token' not in used, p
def sids(o):
    if isinstance(o,dict):
        for k,v in o.items():
            if k=='stage_id' and isinstance(v,str): yield v
            else: yield from sids(v)
    elif isinstance(o,list):
        for v in o: yield from sids(v)
ex=sorted(glob.glob('contracts/analysis/v1/examples/*.example.json'))
ref=[x for f in ex for x in sids(json.loads(Path(f).read_text()))]
assert ex and ref, 'no valid example names a stage'
assert set(ref)<=stages, ('an example names a stage_id absent from the registry',sorted(set(ref)-stages))
print('name-map gate PASS: %d unique names, %d observations, %d/%d alias-bearing sites, findings_merge->finding_merge, %d example stage_id references resolve in the registry, envelope key contract_version only'%(len(names),len(obs),len(ab),len(sites),len(ref)))
"
```

### Gate B — every evidence locator resolves in the frozen legacy commit

Reads only immutable Git objects at `32b9d903792b30506048a1d42b0e6b2d07aee403`; the
mutable legacy working checkout is never opened. Each observation is also checked against
the declaration site it claims: where the accepted inventory names that site by a legacy
file, the evidence locator must resolve inside that same file, so an observation cannot be
re-pointed at a site that does not carry the name. Six of the 31 sites are named by concern
rather than by path in the accepted inventory (`LSD-21`…`LSD-26`); their observations carry
the file-level binding of Gate C's site/name evidence instead.

```
.venv/bootstrap/bin/python -c "
import json,subprocess
from pathlib import Path
n=json.loads(Path('contracts/analysis/v1/legacy-stage-name-map.json').read_text())
m=json.loads(Path('contracts/analysis/v1/legacy-stage-map.json').read_text())
site={x['source_declaration_id']:x['source_declaration_site'].split(' ')[0] for x in m['declarations']}
named=lambda f: f.endswith('.py') or f.endswith('.js')
C=n['legacy_source_commit']; R='/root/projects/PDF-proverka/PDF-proverka'; cache={}
def src(p):
    if p not in cache:
        cache[p]=subprocess.run(['git','-C',R,'--no-replace-objects','show',C+':'+p],check=True,capture_output=True,text=True).stdout.splitlines()
    return cache[p]
c=0; bd=0
for e in n['names']:
    for o in [e]+e.get('additional_observations',[]):
        commit,path,anchor=o['evidence'].split(':',2)
        assert commit==C, o['evidence']
        f=site[o['source_declaration_id']]
        if named(f):
            assert path==f or path.endswith('/'+f), ('the evidence is not in the file this declaration site names',o['evidence'],o['source_declaration_id'],f)
            bd+=1
        sym,span=anchor.rsplit('@',1); a,_,b=span.partition('-'); a=int(a); b=int(b or a)
        L=src(path); assert 1<=a<=b<=len(L), o['evidence']
        if sym not in ('module','lines'):
            assert sym.split('.')[-1] in L[a-1], ('symbol not at start line',o['evidence'])
        ln=o['evidence_line']; assert a<=ln<=b, ('line outside region',o['evidence'])
        lit=o['evidence_literal']; assert lit in L[ln-1], ('literal absent',o['evidence'],lit)
        assert e['legacy_stage_name'].lower() in lit.lower(), ('literal does not carry the name',o['evidence'],lit)
        c+=1
print('evidence gate PASS: %d/%d locators resolve at %s; %d of them are additionally bound to the legacy file their own declaration site names, the remaining %d belong to the %d of 31 sites the accepted inventory names by concern rather than by path'%(c,c,C,bd,c-bd,sum(1 for f in site.values() if not named(f))))
"
```

### Gate C — independent reviewer checks, made mechanical

`PD-02`'s conditional acceptance requires an independent reviewer to confirm all nine
registry stages against capability evidence and, separately, every alias-bearing
declaration site. This gate makes both checkable: each stage's
`evidence.inventory_capabilities` must appear as a capability row of the accepted
inventory at `667fb00f…`, each stage must be the canonical target of at least one legacy
name, and every one of the 31 declaration sites must be bound to concrete names.

It also pins the **identity** of the two registry IDs that the other artifacts point at,
not merely their existence: each of the nine `stage_id` values is checked against the
capability evidence **and** the produced artifact roles that give that stage its meaning,
and each of the eleven `excluded_scope_id` values against its `owning_boundary`. Renaming,
swapping or duplicating one of those IDs therefore fails here instead of silently
re-pointing every `canonical_stage_id` or `excluded_scope_id` reference at a different
concern. `XS-01` and `XS-04` share the `expert_decisions` boundary, so the gate
additionally keeps them apart by their own titles. Every `depends_on` edge must resolve to
a declared stage.

```
.venv/bootstrap/bin/python -c "
import json,re,subprocess
from pathlib import Path
P=lambda f: json.loads(Path('contracts/analysis/v1/'+f).read_text())
r=P('stage-registry.json'); s=P('legacy-stage-map.json'); n=P('legacy-stage-name-map.json')
inv=subprocess.run(['git','--no-replace-objects','show',r['evidence_baseline']['inventory_commit']+':docs/behavior/legacy_capability_inventory.md'],check=True,capture_output=True,text=True).stdout
sites={d['source_declaration_id'] for d in s['declarations']}
bysite={}
for e in n['names']:
    for o in [e]+e.get('additional_observations',[]):
        bysite.setdefault(o['source_declaration_id'],set()).add(e['legacy_stage_name'])
assert len(r['stages'])==9, 'registry no longer declares nine stages'
STG={'source_preparation':       (['AN-02','WS-03'],['prepared.page_inventory','prepared.text_layer']),
     'page_geometry_extraction': (['AN-02','FD-02'],['geometry.block_index','geometry.page_crops']),
     'document_context_build':   (['AN-02'],        ['context.document_graph']),
     'text_analysis':            (['AN-03'],        ['analysis.text_observations']),
     'block_analysis':           (['AN-04','AN-07'],['analysis.block_observations']),
     'finding_merge':            (['AN-05','AN-07'],['findings.merged']),
     'finding_review':           (['AN-06'],        ['review.findings_assessment']),
     'finding_correction':       (['AN-06','EX-07'],['review.corrected_findings']),
     'norm_verification':        (['AN-06'],        ['norms.verification_report'])}
XSB={'XS-01':'expert_decisions','XS-02':'knowledge_base','XS-03':'publication_export',
     'XS-04':'expert_decisions','XS-05':'section_optimization','XS-06':'comparison',
     'XS-07':'future_comparison_scope','XS-08':'distributed_execution','XS-09':'experimental_legacy',
     'XS-10':'engine_internal','XS-11':'project_optimization'}
sids=[x['stage_id'] for x in r['stages']]
assert len(sids)==len(set(sids))==len(STG) and set(sids)==set(STG), ('the nine canonical stage_id values are not the ones every canonical_stage_id reference resolves against',sorted(sids))
for st in r['stages']:
    exp=STG[st['stage_id']]
    got=(sorted(st['evidence']['inventory_capabilities']),sorted(o['role'] for o in st['produced_outputs']))
    assert got==(sorted(exp[0]),sorted(exp[1])), ('a stage_id no longer denotes the stage whose capability evidence and produced roles it carries',st['stage_id'],got)
assert all(dep in set(sids) for st in r['stages'] for dep in st['depends_on']), 'a depends_on edge does not resolve to a declared stage'
xids=[x['excluded_scope_id'] for x in r['excluded_scope']]
assert len(xids)==len(set(xids))==len(XSB) and set(xids)==set(XSB), ('the eleven exclusion ids are not the ones every excluded_scope_id reference resolves against',sorted(xids))
assert all(x['owning_boundary']==XSB[x['excluded_scope_id']] for x in r['excluded_scope']), ('an excluded_scope_id no longer denotes the boundary it is recorded against',[x['excluded_scope_id'] for x in r['excluded_scope'] if x['owning_boundary']!=XSB[x['excluded_scope_id']]])
ttl={x['excluded_scope_id']:x['title'] for x in r['excluded_scope']}
assert len(set(ttl.values()))==len(ttl), 'two exclusions share a title'
assert 'revocations' in ttl['XS-01'] and 'carryover' in ttl['XS-04'], 'the two expert_decisions exclusions are no longer told apart by their own titles'
for st in r['stages']:
    caps=st['evidence']['inventory_capabilities']
    assert caps, st['stage_id']
    for cap in caps:
        assert re.search(r'^\| '+cap+r' \|',inv,re.M), ('capability not in accepted inventory',st['stage_id'],cap)
    assert set(st['evidence']['legacy_declaration_ids'])<=sites, st['stage_id']
    assert any(e.get('canonical_stage_id')==st['stage_id'] for e in n['names']), ('stage without legacy name evidence',st['stage_id'])
assert set(bysite)==sites, sorted(sites-set(bysite))
canon={}
for e in n['names']:
    if e['resolution']!='canonical_stage': continue
    for o in [e]+e.get('additional_observations',[]):
        canon.setdefault(o['source_declaration_id'],set()).add(e['canonical_stage_id'])
        canon[o['source_declaration_id']].update(e.get('also_covers_stage_ids',[]))
for d in s['declarations']:
    rel=set(d.get('related_stage_ids',[]))
    if d.get('canonical_stage_id'): rel.add(d['canonical_stage_id'])
    miss=canon.get(d['source_declaration_id'],set())-rel
    assert not miss, ('site claims fewer stages than its own names prove',d['source_declaration_id'],sorted(miss))
dist={}
for d in s['declarations']: dist[d['target_kind']]=dist.get(d['target_kind'],0)+1
assert dist=={'control_plane':25,'sub_pipeline':2,'excluded':3,'stage':1}, dist
print('reviewer gate PASS: 9/9 stages carry accepted capability evidence and name-level evidence, and each stage_id still denotes the stage whose capabilities and produced roles it carries; 11/11 exclusion ids still denote their recorded owning boundary; %d/%d alias-bearing declaration sites bound to concrete names; related_stage_ids is a superset of name evidence on all %d sites; site distribution %s'%(len(bysite),len(sites),len(s['declarations']),dist))
"
```

### Gate D — owner decisions are transferred completely and by their real state

Schema validation of `stage-registry.json` (the second required test) already enforces the
nine `run_lifecycle` triggers, **the whole owner-ruled outcome tuple of each of them**
(`creates_run`, `reuses_existing_run`, `reuses_job`, `creates_attempt`,
`reopens_terminal_run`, `idempotency_scope`), **the identity of each trigger** — the
`rule_id` of every trigger is pinned by a `const` in the same `if`/`then` that pins its
outcome — the `RC-02`-over-`RC-05` precedence, `PD-05`'s identifier provenance and
`XS-11`'s capability disposition. This gate re-checks the same facts from the outside, in
the shape a reviewer states them — over the full tuple rather than `creates_run` alone —
checks the **exact `trigger` → `rule_id` mapping of all nine pairs**, checks the
**referential integrity of `trigger_precedence`**: that `winning_rule_id` and
`losing_rule_id` resolve to declared triggers *and* that they resolve to the triggers the
owner ruling is about, not merely to identifiers that happen to exist. That closes the
last unmutated link of `PD-03`: renaming `RC-02`, renaming `RC-05`, swapping the two or
duplicating one would otherwise leave `trigger_precedence` naming `RC-02` while `RC-02`
denoted a different trigger, inverting the recorded priority in a document that still
validated. The gate further verifies that the recorded precedence resolves to the outcome
its own winner produces, that the `PD-03` restatement in both package schemas is complete
and identical between the root property and `$defs`, and it forbids the "proposed" wording
for any decision that is in fact approved.

```
.venv/bootstrap/bin/python -c "
import json,glob
from pathlib import Path
r=json.loads(Path('contracts/analysis/v1/stage-registry.json').read_text())
POS={'top_level_audit_command_accepted':      (True, False,False,True, 'new_idempotency_key'),
     'idempotent_replay_same_key_and_payload':(False,True, True, False,'same_key_and_payload'),
     'inputs_changed':                        (True, False,False,True, 'new_idempotency_key'),
     'explicit_re_audit_command':             (True, False,False,True, 'new_idempotency_key'),
     'repeat_of_terminal_run':                (True, False,False,True, 'new_idempotency_key'),
     'retry':                                 (False,True, True, True, 'not_a_client_submitted_command'),
     'resume':                                (False,True, True, True, 'not_a_client_submitted_command'),
     'restart':                               (False,True, True, True, 'not_a_client_submitted_command'),
     'worker_failover':                       (False,True, True, True, 'not_a_client_submitted_command')}
RID={'top_level_audit_command_accepted':'RC-01','idempotent_replay_same_key_and_payload':'RC-02',
     'inputs_changed':'RC-03','explicit_re_audit_command':'RC-04','repeat_of_terminal_run':'RC-05',
     'retry':'RC-06','resume':'RC-07','restart':'RC-08','worker_failover':'RC-09'}
rl=r['run_lifecycle']; tr={x['trigger']:x for x in rl['triggers']}
tup=lambda x:(x['creates_run'],x['reuses_existing_run'],x['reuses_job'],x['creates_attempt'],x['idempotency_scope'])
assert rl['owner_decision']=='PD-03' and rl['decision_state']=='approved_with_modification'
assert set(tr)==set(POS) and len(rl['triggers'])==len(POS), 'PD-03 transfer is incomplete'
for k,v in POS.items(): assert tup(tr[k])==v, ('a PD-03 trigger has the wrong outcome tuple',k,tup(tr[k]),v)
assert {k:tr[k]['rule_id'] for k in RID}==RID, ('a trigger carries a rule_id the owner ruling does not give it',{k:tr[k]['rule_id'] for k in RID if tr[k]['rule_id']!=RID[k]})
ids=[x['rule_id'] for x in rl['triggers']]
assert len(ids)==len(set(ids))==len(RID) and set(ids)==set(RID.values()), ('the nine rule_id values are not exactly the owner-ruled identifiers',sorted(ids))
assert tr['inputs_changed']['creates_run'] and tr['repeat_of_terminal_run']['creates_run'], 'positive half missing'
assert all(tr[k]['creates_attempt'] is True for k in ('retry','resume','restart','worker_failover')), 'the Attempt half of PD-03 is missing'
assert tr['idempotent_replay_same_key_and_payload']['creates_attempt'] is False, 'an idempotent replay must mint nothing at all'
assert all(x['reopens_terminal_run'] is False for x in rl['triggers']), 'a terminal Run would be reopened'
assert all(not x['reuses_existing_run'] and not x['reuses_job'] for x in rl['triggers'] if x['creates_run'])
assert [x['rule_id'] for x in rl['triggers'] if x['idempotency_scope']=='same_key_and_payload']==['RC-02']
assert 'never reopened' in rl['terminal_run_rule'] or 'never re' in rl['terminal_run_rule']
assert 'new idempotency key' in tr['repeat_of_terminal_run']['condition'], 'RC-05 does not carry the new idempotency key in its own condition'
assert 'same idempotency key and the same payload' in tr['idempotent_replay_same_key_and_payload']['condition']
byid={x['rule_id']:x for x in rl['triggers']}
assert len(rl['trigger_precedence'])==1, 'exactly one PD-03 trigger overlap is ruled on'
pc=rl['trigger_precedence'][0]
assert pc['precedence_id']=='RP-01' and pc['competing_rule_ids']==['RC-02','RC-05']
assert pc['winning_rule_id']=='RC-02' and pc['losing_rule_id']=='RC-05', 'RC-02 must win over RC-05'
assert {pc['winning_rule_id'],pc['losing_rule_id']}==set(pc['competing_rule_ids'])
refs=[pc['winning_rule_id'],pc['losing_rule_id']]+list(pc['competing_rule_ids'])
assert all(x in byid for x in refs), ('a trigger_precedence reference does not resolve to a declared trigger',[x for x in refs if x not in byid])
assert byid[pc['winning_rule_id']]['trigger']=='idempotent_replay_same_key_and_payload', ('the winner no longer denotes the idempotent replay',byid[pc['winning_rule_id']]['trigger'])
assert byid[pc['losing_rule_id']]['trigger']=='repeat_of_terminal_run', ('the loser no longer denotes the repeat of a terminal Run',byid[pc['losing_rule_id']]['trigger'])
assert [byid[c]['trigger'] for c in pc['competing_rule_ids']]==['idempotent_replay_same_key_and_payload','repeat_of_terminal_run'], 'the competing pair no longer denotes the two overlapping triggers'
assert byid[pc['winning_rule_id']]['idempotency_scope']=='same_key_and_payload' and byid[pc['losing_rule_id']]['idempotency_scope']=='new_idempotency_key', 'the ruled pair no longer separates same key and payload from a new idempotency key'
w=byid[pc['winning_rule_id']]
assert pc['resolved_outcome']=={k:w[k] for k in pc['resolved_outcome']}, 'the precedence outcome is not the outcome its own winner produces'
assert pc['resolved_outcome']['creates_run'] is False and pc['resolved_outcome']['creates_attempt'] is False
assert 'ALWAYS return the original Run' in pc['owner_ruling'], 'the owner ruling lost its unconditional half'
assert 'ONLY under a new idempotency key' in pc['owner_ruling'], 'the owner ruling lost its new-key half'
assert pc['decided_on']=='2026-09-01' and pc['decided_by']=='repository owner'
DEFS=chr(36)+'defs'
CL=('PD-03','ALWAYS returns the existing Run','under a NEW idempotency key','exactly one new Attempt','never reopened','creates_attempt','RC-02 over RC-05','run_lifecycle','execution_token')
for f in ('job-package.schema.json','result-package.schema.json'):
    d=json.loads(Path('contracts/analysis/v1/'+f).read_text())
    a=d['properties']['attempt_authority']['description']; b=d[DEFS]['attempt_authority']['description']
    assert a==b, ('the attempt_authority description differs between the root property and '+DEFS,f)
    for c in CL: assert c in a, ('a PD-03 clause is missing from the attempt_authority description',f,c)
sr=json.loads(Path('contracts/analysis/v1/stage-result.schema.json').read_text())
assert json.loads(Path('contracts/analysis/v1/result-package.schema.json').read_text())[DEFS]['stage_result']==sr, 'the bundled StageResult drifted from the standalone contract'
xs={x['excluded_scope_id']:x for x in r['excluded_scope']}
for i in ('XS-01','XS-04'):
    e=xs[i]['external_decision']
    assert e['decision_id']=='PD-01' and e['state']=='approved_with_modification'
    assert e['decided_on']=='2026-09-01' and e['decided_by']=='repository owner'
    assert e['analysis_family_decision'] is False and set(e['owning_lanes'])=={'domain','architecture'}
d=xs['XS-11']['retained_capability_disposition']
assert d['owner_input_id']=='U-06' and d['contract_family']=='contracts/optimization/v1/**'
assert d['planned_task']=='W5-OPT-01' and d['capability_state']=='disabled_until_task_accepted'
assert d['cp00_excludes_runtime_semantics'] is True and 'OPT' in d['contract_owner']
f=[x for x in r['fail_soft_policies'] if x['policy_id']=='FS-04'][0]
assert f['analysis_part']['part']=='norm_core' and f['analysis_part']['encoder_lane']=='analysis (ANA)'
own={x['owner'] for x in f['parts_outside_this_lane']}
assert own=={'project-optimization (OPT) contract owner','domain (DOM) lane'}, own
p5=[x for x in r['owner_decisions'] if x['decision_id']=='PD-05'][0]
assert p5['identifier_assigned_by']=='analysis (ANA) lane'
assert p5['identifier_confirmed_by']=='program integrator' and p5['identifier_confirmed_on']=='2026-09-01'
assert not any(x['decision_id']=='PD-01' for x in r['owner_decisions']), 'PD-01 is not an analysis decision'
for path in sorted(glob.glob('contracts/analysis/v1/*.json'))+sorted(glob.glob('contracts/analysis/v1/examples/*.json'))+['contracts/analysis/v1/README.md']:
    txt=Path(path).read_text()
    bad='proposed as '; assert not any(bad+q+'PD-' in txt for q in ('',chr(96))), ('approved decision called proposed',path)
print('decision-transfer gate PASS: PD-03 has all %d creation triggers with the complete owner outcome tuple and the exact owner-ruled rule_id on each of them; inputs_changed and repeat_of_terminal_run create a new Run; retry/resume/restart/worker_failover each create exactly one Attempt and no Run; the idempotent replay creates neither; RC-02 beats RC-05, both precedence references resolve to the triggers the ruling is about, and the resolved outcome is the winner outcome; no trigger reopens a terminal Run; both attempt_authority descriptions are identical and complete; PD-01 approved_with_modification on XS-01/XS-04; U-06 closed on XS-11 (OPT / contracts/optimization/v1/** / W5-OPT-01 / disabled); FS-04 norm_core owned here, 2 parts elsewhere; PD-05 identifier confirmed'%len(POS))
"
```

## Non-goals

No production engine, worker, scheduler, control-plane or publication code. No domain,
API, event or comparison contract change. No stage-specific analysis payload schema yet:
those arrive with the S03/S04 contracts. No live provider call, customer payload,
credential or legacy execution. All example values are synthetic.
