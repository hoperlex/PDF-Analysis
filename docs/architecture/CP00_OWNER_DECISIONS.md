# CP-00 owner decision records — `PD-01`–`PD-05`

Round 1 of `W0-ARC-01` prepared `PD-01`–`PD-04` and left every one of them
`pending_owner_approval`. Round 2 records the repository owner's explicit
disposition for each. The statement, evidence and options below are unchanged: they
are what was put to the owner. What is new is the **owner disposition** block in each
record and the filled approval block at its end.

Round 3 adds one record, `PD-05`. It was **not** prepared by this lane and put to the
owner: the owner issued the disposition directly and the analysis lane wrote it into
`contracts/analysis/v1/stage-registry.json` before it reached this ledger. An owner
decision that lives only in one contract family is a split source of truth, so round 3
reconciles it here, where the ledger is authoritative. `PD-05` changes no earlier
record.

Round 4 records the owner's answers to what round 3 had to leave open about this
ledger's own records, and adds no new decision record. The `PD-05` number is
**confirmed** and stands. The open item `U-06`, created by `PD-05`, is **closed**
with a disposition that gives project optimization its own bounded context. And the
`FS-04` fail-soft policy — half of which `PD-05` had left without an executor — is
**split into three parts, each with a named owner**. No earlier record,
modification or qualification is changed by any of that.

Round 5 adds **no decision record**. Independent review found that the already
approved `PD-03` modification let two of its own clauses cover the same request — a
repeat of a terminal Run under the same idempotency key and the same payload — without
saying which one wins. The owner stated the priority, and round 5 records it **inside
`PD-03`** as a precedence clarification, not as a new `PD-NN`. It resolves the overlap
between the two clauses and changes neither of them. `PD-01`, `PD-02`, `PD-04`,
`PD-05`, `ID-01`–`ID-03`, every disposition and the `FS-04` split are untouched.

Dispositions available to the owner for each record were: `approved`, `approved with
modification` (owner states the modification), `rejected` (owner states the
alternative semantics) or `deferred with a named blocker`.

| Field | Value |
|---|---|
| Prepared by | `W0-ARC-01`, architecture lane |
| Prepared against base commit | `6c82004b35f49463c8e7fc8602fbced2f374167e` |
| Behavioral evidence | accepted inventory at `667fb00fe3e45d1ce0bce7860725c1654b4cdeba`, anchors at legacy oracle `32b9d903792b30506048a1d42b0e6b2d07aee403` |
| Review context | [CP00_ARCHITECTURE_REVIEW.md](CP00_ARCHITECTURE_REVIEW.md) |
| Decision authority | repository owner (sole authority for product semantics) |
| Decision channel | direct instruction to the program integrator session |
| Decision date | 2026-09-01 |
| Status of the five records | `PD-01` approved with modification; `PD-02` approved with modification; `PD-03` approved with modification; `PD-04` approved; `PD-05` approved |
| Records added after round 4 | none. Round 5 records a precedence clarification **inside** `PD-03`; the ledger still holds exactly five records, `PD-01`–`PD-05` |
| Identifier provenance | `PD-01`–`PD-04` were numbered by this lane in round 1; `PD-05` was numbered by the **analysis (ANA) lane** and the number was **confirmed by the program integrator on 2026-09-01**. No `PD-*` number is itself an owner decision (see the `PD-05` provenance note) |
| Rounds recorded here | round 2: `PD-01`–`PD-04` dispositions; round 3: `PD-05` reconciliation; round 4: `PD-05` identifier confirmation, the `U-06` disposition and the three-part `FS-04` split; round 5: the `PD-03` precedence clarification, which adds no record |

An approved decision is **not** a ratification. `W0.3` ratifies; these records make
the semantics decidable for the DOM, ANA and golden lanes. Where a decision was
approved with a modification, the modification is part of the decision and must be
carried with it.

## Summary of dispositions

| Record | Disposition | One-line effect |
|---|---|---|
| [PD-01](#pd-01--expert-correctionrevocation-semantics) | **approved with modification** | Append-only stands; revocation projects to `pending` and never auto-restores; also closes `OQ-03` |
| [PD-02](#pd-02--authoritative-stage-registry) | **approved with modification** | One registry stands; the ANA lane is accepted only after a name-level alias map exists |
| [PD-03](#pd-03--runjobattempt-identity-and-attempt-authority) | **approved with modification** | Three identities stand; the rule for what creates a new `AuditRun` is recorded, and since the precedence clarification of 2026-09-01 the same idempotency key and payload always return the original Run |
| [PD-04](#pd-04--graphicvector-comparison-scope) | **approved** | Future greenfield scope; first contractual inclusion in W7 with a golden graphic pair |
| [PD-05](#pd-05--project-optimization-sub-pipeline-scope) | **approved** | Four `optimization*` names leave the nine-stage core audit registry as a separate project-optimization sub-pipeline; the capability is retained and, since the `U-06` disposition of 2026-09-01, carried by its own bounded context `contracts/optimization/v1/**` under task `W5-OPT-01`, disabled until then |

---

## PD-01 — Expert correction/revocation semantics

**Status:** `approved with modification` — repository owner, 2026-09-01

### Statement put to the owner

Expert correction or revocation creates a **new append-only decision event** and
changes the derived projections. It does **not** copy the legacy overwrite/delete
behavior.

### Why this needs an owner, not an agent

The legacy product and the target documents disagree about what a revocation *is*.
Choosing between "history is preserved and superseded" and "history is removed"
changes what a user sees after revoking a decision, what an audit trail can prove,
and what an export contains. That is product semantics.

### Evidence

| Side | Evidence |
|---|---|
| Legacy behavior | `[B]` EX-02 `not observed`: no append-only event stream; a matching decision is updated and revoke deletes from both the global decision log and the active review |
| Legacy anchors | `[L]` `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/knowledge_base/knowledge_base_service.py:_append_to_decisions_log@683`; `[L]` `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/knowledge_base/knowledge_base_service.py:revoke_decision@861` |
| Reconciliation status | `[B]` §5 "Append-only expert decision events" = **contradicted** (the only contradicted row of 36) |
| Recorded risk | `[B]` §7 gap 1: "Product/domain authority must choose the greenfield event/history semantics" |
| Related legacy nuance | `[B]` EX-04: ambiguous revoke is already refused, so legacy is not uniformly destructive |
| Target documents asserting the append-only model | `[P]` Bible §2 "current expert verdict", `[P]` Bible P-18, `[P]` ADR-0012, `[P]` DOMAIN_MODEL.md "Decision ledger", `[P]` GLOSSARY.md `ExpertDecision` |

### Options

| Option | Description | Main consequence |
|---|---|---|
| A | Append-only events; current verdict and KB are projections (the statement above) | Full history and audit provenance; revocation becomes a superseding event, so a "deleted" decision remains visible in history views unless a separate visibility rule is approved |
| B | Copy legacy semantics: update in place and delete on revoke | Exact legacy parity; the Bible, P-18, ADR-0012 and DOMAIN_MODEL.md must be superseded, and audit provenance of expert work is lost |
| C | Append-only storage with an approved redaction/erasure workflow for lawful deletion | Preserves audit provenance and satisfies erasure needs; requires the deferred retention/erasure authority of ADR-0014 |

### If approved

`ADR-0012` and `P-18` become ratifiable; `P-03`'s decision-event clause becomes
ratifiable; the DOM lane may model decision events and projections; `GJ-04` still
characterizes legacy replacement/deletion separately, as legacy behavior only.

### If rejected or modified

`ADR-0012` becomes a `supersede` candidate and requires a replacement ADR
(`ADR-0019` or the next unused number) plus an `ADR_INDEX.md` row; Bible §2, P-18,
`DOMAIN_MODEL.md` and `GLOSSARY.md` need matching updates; the domain contract
cannot be frozen until then.

### Owner disposition

**Approved with modification.** Option A is adopted with an explicit projection rule:

1. Decisions are append-only. Neither a correction nor a revocation rewrites or
   deletes an earlier decision.
2. A correction and a revocation each create a **new `decision_id`**.
3. A revocation moves the current projection to **`pending`**. It does **not**
   automatically restore the previously superseded verdict.
4. The decision history is preserved in full.

The modification also closes the domain lane's open question `OQ-03` ("on revocation,
does the verdict projection fall back to the previous valid verdict or to
`pending`?"): the answer is `pending`.

Consequences recorded in [CP00_ARCHITECTURE_REVIEW.md](CP00_ARCHITECTURE_REVIEW.md):
`P-18` and `ADR-0012` move from `defer` to `adapt` because the pending decision was
their entire defer basis; the `P-03` decision-event clause is settled. The DOM lane
must encode the `pending` projection rule and close `OQ-03` with it. Legacy
overwrite/delete remains characterized legacy behavior (candidate `GJ-04`) and is
never presented as the target.

### Approval record

```text
decision:            approved with modification
modification/alternative:
  Decisions remain append-only. A correction and a revocation each create a new
  decision_id. A revocation moves the current projection to `pending` and does NOT
  automatically restore the previous verdict. History is preserved. This also closes
  OQ-03.
owner:               repository owner
date:                2026-09-01
evidence reference:  direct instruction to the program integrator session, W0.2
                     round 2; recorded in CP00_ARCHITECTURE_REVIEW.json
                     owner_decisions[PD-01]
```

---

## PD-02 — Authoritative stage registry

**Status:** `approved with modification` — repository owner, 2026-09-01

### Statement put to the owner

One versioned target stage registry is authoritative. Conflicting legacy stage
declarations are aliases and evidence, not competing sources of truth.

### Why this needs an owner, not an agent

Deciding which stage names, order and terminal semantics the product exposes changes
the user-visible pipeline, retry/skip vocabulary and UI progress. Selecting one of
the existing legacy lists would silently promote one team's historical list to a
product contract.

### Evidence

| Side | Evidence |
|---|---|
| Legacy fragmentation | `[B]` §2.2: 31 declaration sites, 29 mapped, "the declaration sites conflict in membership and order"; at least five overlapping notions of stage order (`[B]` §6) |
| Examples of divergence | `[B]` §2.2 items 8–13: resume aliases, OCR resume order, failure-recovery order, audit-log display order, project status order |
| Alias surfaces | `[B]` §2.2 items 28–30: pipeline stage aliases, stage artifacts map, persisted stage-value aliases |
| Reconciliation status | `[B]` §5 "Versioned stage registry" = partial |
| Recorded risk | `[B]` §7 gap 2: "W0-ANA-01 must trace each legacy alias before freezing a new registry" |
| Advisory corroboration | `[S]` `docs/architecture/adr/ADR-0018-domain-contract-v1.md` §1.1: two pipeline order declarations already diverged, 15 keys against 13 (verified at `98d075ea`, not the oracle commit) |
| Target documents | `[P]` Bible §8, `[P]` ADR-0008, `[P]` GLOSSARY.md `Stage` |

### Options

| Option | Description | Main consequence |
|---|---|---|
| A | One versioned registry owns names, order, dependencies, contract versions and terminal semantics; every legacy name maps to it through a declared alias table (the statement above) | Single vocabulary for API, UI, retry/skip and workers; requires the complete alias map before freeze |
| B | Adopt one existing legacy list as canonical | Fast, but promotes an internal historical list to a product contract and keeps the other 30 declarations as hidden drift |
| C | Allow several registries per surface (execution, display, routing) | Matches legacy reality; reproduces the drift the greenfield exists to remove and breaks the single-source rule of ADR-0008 |

### If approved

`ADR-0008`'s registry clause becomes ratifiable; the ANA lane may define the
registry provided every legacy alias in `[B]` §2.2 is mapped or explicitly excluded
with a reason; `FS-04` and `FS-08` target policies become encodable.

### If rejected or modified

`ADR-0008` becomes a `supersede` candidate; Bible §8 and the analysis contract
family cannot be frozen; the ANA draft stays a draft.

### Owner disposition

**Approved with modification.** Option A is adopted, with a hard acceptance
precondition for the analysis lane:

1. One stage registry is authoritative.
2. The ANA lane is accepted **only after a name-level alias map appears**.
3. For every legacy stage name that map must carry: the **surface** on which the name
   appears, its **`source_declaration_id`**, **immutable evidence**, and either a
   **canonical target** stage or an **explicit exclusion**.
4. `findings_merge` → `finding_merge` is a mandatory example.

State at the time of the decision: `contracts/analysis/v1/legacy-stage-map.json`
contains **31 declaration sites and zero concrete alias values**. Site-level mapping
is not the required artifact, so the precondition is not yet met and `PD-02` alone
does not unblock the analysis contract freeze.

Integration decision `ID-03` (see the review, §6.3) adds the reviewer condition: an
independent reviewer must confirm all nine registry stages against capability
evidence and separately check every alias-bearing declaration site.

### Approval record

```text
decision:            approved with modification
modification/alternative:
  One stage registry is authoritative, but the ANA lane is accepted only after a
  name-level alias map appears. For every legacy name the map must carry surface,
  source_declaration_id, immutable evidence and either a canonical target or an
  explicit exclusion. Mandatory example: findings_merge -> finding_merge. At decision
  time legacy-stage-map.json holds 31 sites and zero concrete alias values.
owner:               repository owner
date:                2026-09-01
evidence reference:  direct instruction to the program integrator session, W0.2
                     round 2; recorded in CP00_ARCHITECTURE_REVIEW.json
                     owner_decisions[PD-02] and integration_decisions[ID-03]
```

---

## PD-03 — Run/Job/Attempt identity and attempt authority

**Status:** `approved with modification` — repository owner, 2026-09-01
**Precedence clarification inside this record:** repository owner, 2026-09-01
(see "Precedence clarification" below; it is not a separate decision record)

### Statement put to the owner

`AuditRun`, `Job` and `Attempt` are distinct identities, and current-attempt
authority (lease/fencing) is mandatory. This extends the partial legacy
token/epoch behavior rather than renaming it.

### Why this needs an owner, not an agent

The legacy system has no distinct `Run`. Manufacturing one from project/version or
from an attempt would invent business history semantics: what a user's "audit run"
is, what a rerun creates, and what an operator sees after a stale worker returns.

### Evidence

| Side | Evidence |
|---|---|
| What legacy has | `[B]` DW-02: persistent logical job/attempt state, at most one active job per project/version and one active attempt per job, attempt-scoped execution token, idempotency keys, stale/superseded rejection |
| What legacy lacks | `[B]` DW-03 `not observed`: "a distinct canonical Run entity/identity was not found in the bounded schema and protocol"; "Greenfield must not manufacture Run semantics from project/version or attempt" |
| Fencing status | `[B]` DW-05: connection-epoch fencing and stale/superseded rejection exist, but "no explicit domain-level `fencing_token` field was established" |
| Reconciliation status | `[B]` §5 "Run / Job / Attempt separation" = partial; "Lease, heartbeat and fencing" = partial |
| Recorded risk | `[B]` §7 gap 4: epoch and token checks "must not be relabeled as a greenfield fencing-token contract without a domain decision" |
| Advisory corroboration | `[S]` `docs/architecture/adr/ADR-0018-domain-contract-v1.md` §1.1: four forms of `run_id`, one of them equal to `job_id` (verified at `98d075ea`) |
| Target documents | `[P]` Bible §8, `[P]` ADR-0005, `[P]` ADR-0007, `[P]` DOMAIN_MODEL.md "Run / Job / Attempt", `[P]` manual case MT00-04 |

### Options

| Option | Description | Main consequence |
|---|---|---|
| A | Three distinct identities with a mandatory lease/fencing token; a stale attempt can never publish (the statement above) | Clear rerun/retry history and safe late-result handling; requires new `Run` semantics with no legacy parity, so `Run` must be defined by the owner, not derived |
| B | Two identities only (`Job`, `Attempt`), matching legacy | Closest to legacy evidence; the business history of "one audit request and its result" has no home, and `AuditRun` must be removed from Bible §8, ADR-0005, ADR-0007 and DOMAIN_MODEL.md |
| C | Three identities but fencing kept advisory, as in legacy | Preserves legacy tolerance; permits a stale attempt to publish under race conditions, which contradicts P-09/P-10 |

### If approved

`ADR-0007`'s fencing clause and the `AuditRun` naming in `ADR-0005` become
ratifiable; the DOM lane may define run/job/attempt identifiers and state machines;
`FS-06` becomes encodable. The owner must also state what creates a new `AuditRun`
(rerun, resume, retry) because legacy provides no evidence for that rule.

### If rejected or modified

`ADR-0007` becomes a `supersede` candidate; the domain identifier and state-machine
catalogs cannot be frozen; `DOMAIN_MODEL.md` and Bible §8 need matching updates.

### Owner disposition

**Approved with modification.** Option A is adopted and the missing Run-creation rule
— the sub-question this record raised, because legacy supplies no Run evidence — is
answered by the owner:

1. `AuditRun`, `Job` and `Attempt` are distinct entities.
2. A new `AuditRun` is created when a **top-level audit or re-audit command is
   accepted for a frozen set of inputs and configurations**.
3. A repeat with the **same idempotency key and payload returns the existing Run**.
4. **Changed inputs**, an **explicit re-audit**, or a **repeat of a terminal Run**
   create a new Run.
5. **Retry, resume, restart and worker failover create no new Run**: the `Job` is the
   same and a new `Attempt` is created.
6. A **terminal Run is never reopened**.

Token naming follows integration decision `ID-02`: the capability is
`execution_token` — opaque, equality-only, refreshed on every new `Attempt`, verified
inside the publishing transaction. Fencing is a property of the behavior, not the
name of a field and not a promise of a monotonically increasing number;
`authority_token` and `fencing_token` survive only in legacy evidence.

### Precedence clarification — recorded 2026-09-01, inside `PD-03`

**This is not a new decision record.** No `PD-06` is created, the disposition stays
`approved with modification`, and the ledger still holds exactly five records. What
follows resolves an **overlap between two clauses of the modification above** and
changes neither of them.

**The overlap.** Independent review of the `W0-ARC-01` candidate found that one
request satisfies two clauses at once: a repeat of a Run that has already reached a
terminal state, carrying the **same idempotency key and the same payload**. Clause 3
says such a repeat *returns the existing Run*; clause 4 says a *repeat of a terminal
Run creates a new Run*. The approved modification stated no priority between them, so
the same request had two admissible outcomes and each consuming family could pick a
different one.

**The owner's precedence, as stated:**

> Identical idempotency key and payload **always** return the original Run. A repeat
> of a terminal Run creates a new Run **only** under a new idempotency key.

| Field | Value |
|---|---|
| Kind of record | precedence clarification of `PD-03` — not a new `PD-NN`, not a new modification |
| Clarifies | `PD-03`, clauses 3 and 4 of the owner modification |
| Authority | repository owner |
| Date | 2026-09-01 |
| Channel | direct instruction to the program integrator session, confirmed on the outcome of the independent review |
| Raised by | independent review pass over the `W0-ARC-01` candidate |
| Effect on the disposition | none: `PD-03` stays **approved with modification** |
| Effect on the record count | none: `PD-01`–`PD-05` remain the five records |

**What it changes, exactly.** Only the intersection of the two clauses is assigned;
neither clause is narrowed, withdrawn or rewritten:

1. In the overlap — same key, same payload — the **idempotent-replay clause wins**:
   the original Run is returned, whatever state it is in, and nothing is created.
2. Outside the overlap the **new-Run clause is untouched**: a repeat of a terminal Run
   arriving under a **new idempotency key** creates a new Run, as does a change of
   inputs and as does an explicit re-audit.
3. The terminal Run is **never reopened on either branch**. The idempotent replay
   returns it unchanged; the new-key repeat produces a separate Run beside it. Clause
   6 is therefore also untouched, and rule 2 above is what it means for a repeat to
   "create a new Run" — a second entity, never a continuation of the first.

**Downstream obligation.** The precedence must be reflected by **both** consuming
families, because a family that carries one clause without the other, or both without
the priority, is not conformant to `PD-03`:

| Family | Carrier | Obligation |
|---|---|---|
| analysis (ANA) | `contracts/analysis/v1` → `run_lifecycle` | the run-creation triggers must state that the idempotent-replay case takes precedence, and that the terminal-repeat case creates a new Run only under a new idempotency key |
| domain (DOM) | `contracts/domain/v1` → the `AuditRun` creation rule | the same precedence over the creation cases: same key and payload return the existing run whatever state it is in; a terminal target's repeat mints a new run only under a new idempotency key |

For reference at the time of recording: the domain family already encodes the
precedence, and the analysis family is correcting its `run_lifecycle` in parallel.
Both observations are of another lane's **unfrozen working-tree draft**, read for
reconciliation only and **not certified by this lane**; what binds is the obligation,
not the observed state.

### Approval record

```text
decision:            approved with modification
modification/alternative:
  AuditRun, Job and Attempt are distinct. A new AuditRun is created when a top-level
  audit/re-audit command is accepted for a frozen set of inputs and configurations.
  A repeat with the same idempotency key and payload returns the existing Run.
  Changed inputs, an explicit re-audit or a repeat of a terminal Run create a new Run.
  Retry/resume/restart/worker failover create no new Run: same Job, new Attempt.
  A terminal Run is never reopened. This closes the raised sub-question about what
  creates a new AuditRun.
precedence clarification:
  Recorded inside this record on 2026-09-01 by the repository owner, after
  independent review found clauses 3 and 4 of the modification overlapping without a
  stated priority. Identical idempotency key and payload ALWAYS return the original
  Run; a repeat of a terminal Run creates a new Run ONLY under a new idempotency key.
  It assigns the overlap and changes neither clause; the terminal Run is reopened on
  neither branch. It is not a new decision record and creates no PD-06: the
  disposition stays approved with modification and the ledger still holds PD-01 to
  PD-05. Both consuming families must reflect it: analysis in run_lifecycle and
  domain in the AuditRun creation rule.
owner:               repository owner
date:                2026-09-01
evidence reference:  direct instruction to the program integrator session, W0.2
                     round 2; recorded in CP00_ARCHITECTURE_REVIEW.json
                     owner_decisions[PD-03] and integration_decisions[ID-02]. The
                     precedence clarification was stated in the same channel on the
                     outcome of the independent review and is recorded in W0.2
                     round 5 at owner_decisions[PD-03].precedence_clarification
```

---

## PD-04 — Graphic/vector comparison scope

**Status:** `approved` — repository owner, 2026-09-01

### Statement put to the owner

Graphic/vector comparison is future greenfield scope. It is explicitly absent from
legacy parity and must not be fabricated in W0 fixtures or contracts.

### Why this needs an owner, not an agent

Whether a shipped product must compare drawing graphics is a product-scope decision.
An agent that quietly builds a graphic-evidence contract would create the appearance
of characterized behavior where no behavior exists.

### Evidence

| Side | Evidence |
|---|---|
| Legacy behavior | `[B]` CP-06 `not observed`: no graphic/vector comparison artifact was found; the text-difference artifact explicitly reports graphics as not analyzed |
| Legacy anchors | `[L]` `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/stage_comparison/store.py:vector_graphics_comparison@1427`; `[L]` `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/stage_comparison/text_differences.py:graphics_analyzed@479` |
| Reconciliation status | `[B]` §5 "Graphic/vector comparison" = not observed; `[B]` §7 gap 3 |
| Target documents asserting the layer | `[P]` Bible §11 "raw graphic evidence", `[P]` ADR-0013, `[P]` GLOSSARY.md "Raw comparison evidence" |

### Options

| Option | Description | Main consequence |
|---|---|---|
| A | Keep the layer named in the target architecture, but mark it explicitly out of legacy parity and out of W0 artifacts (the statement above) | The comparison model stays extensible; no fixture, schema or golden journey may assert graphic behavior until a future wave designs it |
| B | Remove the graphic evidence layer from the target until it is separately requested | Smallest surface; ADR-0013 and Bible §11 must be updated, and a later reintroduction is a breaking comparison-contract change |
| C | Treat graphic comparison as in-scope for the current program | Requires new product requirements, fixtures and provider decisions with zero legacy evidence to characterize against |

### If approved

`ADR-0013` is ratifiable with the recorded scope qualification; the golden and
comparison lanes must leave graphic comparison unasserted; W0 fixtures containing
graphic-comparison expectations are a stop condition.

### If rejected or modified

`ADR-0013` becomes a `supersede` candidate for its raw-graphic clause, and Bible §11
plus `GLOSSARY.md` need matching updates before any comparison contract is frozen.

### Owner disposition

**Approved.** No modification. Option A is adopted with the recorded scope
qualification: graphic/vector comparison is a **future greenfield feature**, absent
from legacy parity and absent from W0. Its **first contractual inclusion is W7**,
together with a separate golden graphic pair.

Until then, no W0 fixture, schema, golden journey or contract may assert graphic
comparison behavior; such an artifact is a stop condition.

### Approval record

```text
decision:            approved
modification/alternative:
  none. Recorded qualification: graphic/vector comparison is a future greenfield
  feature, absent from legacy parity and from W0. First contractual inclusion is W7
  with a separate golden graphic pair.
owner:               repository owner
date:                2026-09-01
evidence reference:  direct instruction to the program integrator session, W0.2
                     round 2; recorded in CP00_ARCHITECTURE_REVIEW.json
                     owner_decisions[PD-04]
```

---

## PD-05 — Project optimization sub-pipeline scope

**Status:** `approved` — repository owner, 2026-09-01

### Identifier provenance — read before citing `PD-05`

The label `PD-05` was **assigned by the analysis (ANA) lane**, not by the repository
owner, and was **confirmed by the program integrator on 2026-09-01**. The number
stands: no renumbering is required and the confirmation changed no semantics. It is
used in this ledger, in the machine matrix and in
`contracts/analysis/v1/stage-registry.json` so that all three name the same decision
instead of three unlinked notes. The number is still **not part of the owner's
decision** — only the disposition text under "The owner's disposition, as recorded"
is the owner's — but it is no longer an open question.

### How this record differs from `PD-01`–`PD-04`

`PD-01`–`PD-04` were prepared by this lane as statements with options and put to the
owner, who answered each. `PD-05` was not: the owner issued the disposition directly
and the analysis lane recorded it in its own contract, where it was found. This
record is therefore **retrospective reconciliation** — the disposition text is the
owner's; the evidence, the ruled-out alternatives, the consistency analysis and the
downstream obligations below are this lane's reconstruction and are marked as such.
Nothing here extends the owner's statement.

### The owner's disposition, as recorded

`optimization`, `optimization_critic`, `optimization_corrector` and
`optimization_review` form a **separate project-optimization sub-pipeline**, started
on its own or as an **optional post-findings branch**. Its product is **improvement
proposals, not audit findings**. **Section optimization is a downstream
aggregation/replication pipeline, not the same pipeline.** The four names are
**excluded from the nine-stage core audit registry** but **retained as a separate
capability with a future contract owner**.

### Why the status is `approved` and not `pending`

The owner phrased the disposition as a recommendation to approve it and, as a
separate instruction, ordered it recorded. A statement that the owner both formulated
and ordered into the record is an owner decision, not an agent proposal, so the
status is `approved`. The owner stated **no modification**, so this record carries a
qualification rather than a modification — the same shape as `PD-04`.

### Why this needs an owner, not an agent

Whether four stages that legacy ran inside the audit pipeline body belong to the
audit product at all is product scope. An agent that dropped them would silently
delete a shipped capability; an agent that kept them would put improvement proposals
into a findings registry and make the core registry answer two different questions.
Either choice is a product decision.

### Evidence

| Side | Evidence |
|---|---|
| Legacy ran optimization inside the audit pipeline body | `[B]` §2.2 declaration site 10, `pipeline/manager.py` full pipeline body: "preparation, analysis, merge, review/norm/optimization, debt/carryover and Excel"; `[B]` §6 pipeline topology: the manager "merges findings, coordinates review/norm/optimization, then runs debt control, decision carryover and Excel generation"; `[L]` `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/pipeline/manager.py:_run_ocr_pipeline@5346` |
| Optimization is also reachable on its own request and as a post-findings branch | `[B]` AN-08 "Auditor requests section/project optimization and replication", `observed`, confidence high; `[B]` AN-06 "norm/optimization branches may record degradation and continue", `observed`, confidence medium; `[B]` §2.2 declaration site 17 `optimization.py`; `[L]` `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/optimization.py:router`; `[L]` `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/pipeline/manager.py:_run_post_findings_parallel@4711`; `[L]` `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/main.py:include_router@228` |
| Section optimization is a different, downstream pipeline with its own stage lists | `[B]` §2.2 declaration sites 21 and 22: "Collect/normalize/synthesize/agent/graphics/review sub-pipeline" and "Validate/package/agent/graphics/expert sub-pipeline"; `[L]` `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/section_optimization_pipeline_service.py:_STAGES@34`; `[L]` `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/section_optimization_replication_service.py:_STAGES@45` |
| Its product is separate from merged findings | `[B]` AN-08 output: "Optimization artifacts and section replication pipeline artifacts"; `[B]` §4 "Core audit artifacts" lists "review/norm/optimization" beside, not inside, "merged findings" |
| Where the decision was written down before this ledger | `[P]` `contracts/analysis/v1/stage-registry.json`: `owner_decisions[PD-05]` and `excluded_scope` `XS-11` with `owning_boundary` `project_optimization` and its `retained_capability` statement, plus the separation note on `XS-05` — another lane's unfrozen draft, read for reconciliation and **not verified** by this lane |
| Decision authority | `[O]` this record; the owner's disposition of 2026-09-01 |

### Alternatives the disposition rules out

Recorded by this lane so that the boundary of the decision is explicit. Unlike
`PD-01`–`PD-04`, these options were **not** put to the owner by this lane.

| Alternative | Description | Why the recorded disposition rules it out |
|---|---|---|
| A′ | Keep the four names as core audit stages of the registry | The core registry would carry stages whose product is improvement proposals, not audit findings; one registry would answer two different questions |
| B′ | Drop the four names entirely | Deletes a capability that `[B]` AN-08 records as `observed` with high confidence, with no owner decision to remove it. The disposition explicitly **retains** the capability |
| C′ | Treat project optimization as the entry point of the section-optimization sub-pipeline | Not evidenced: `[B]` §2.2 sites 21–22 describe a separate downstream aggregation/replication pipeline with its own stage lists. The disposition states the two are different pipelines |

### Consistency with the already approved decisions

Checked against every recorded decision; nothing below reopens one.

- **`PD-02` (one authoritative stage registry).** No conflict. `PD-05` creates no
  second registry: it is a **membership** decision taken **under** the single-registry
  authority that `PD-02` established. `PD-02`'s modification requires every legacy
  stage name to resolve to "either a canonical target stage or an **explicit
  exclusion**"; `PD-05` supplies that resolution form for four names. The nine
  registry stages are unchanged and no stage was added, renamed or reordered.
- **`ID-03` (legacy stage-map target-kind distribution).** Unchanged. `ID-03`'s
  conditional distribution — 25 `control_plane` / 2 `sub_pipeline` / 3 `excluded` /
  1 `stage` — is stated over the 31 **declaration sites** of the site-level map, while
  `PD-05` acts at the **name** level of the alias map that `PD-02` requires. `PD-05`
  adds no condition to `ID-03` and removes none; the reviewer pass `ID-03` already
  requires now simply meets the `XS-11` exclusion as part of the name-level map.
- **`PD-01`, `PD-03`, `PD-04`.** Independent subject matter; no interaction.
- **Review §7 `FS-04`.** One consequence, recorded in the review: `FS-04` maps the
  legacy fail-soft "norm/optimization branches may record degradation" to the stage
  terminal semantics of the single registry, with the ANA lane as encoder. `PD-05`
  moved half of that policy outside the analysis boundary and, in round 3, left it
  without an executor. The owner repaired that on 2026-09-01 by **splitting `FS-04`
  into three parts with a named owner each**: `FS-04-A` norm/core semantics — ANA
  lane, `contracts/analysis/v1/**`, `W0-ANA-01`; `FS-04-B` project-optimization
  stages and results — OPT contract owner, `contracts/optimization/v1/**`,
  `W5-OPT-01`; `FS-04-C` `AuditRun`/`Job` as consumer — DOM lane,
  `contracts/domain/v1/**`, `W0-DOM-01`, where the failure of an optional
  optimization branch resolves the run to an explicit `partial` and never to a full
  success. The rule itself is untouched and binds all three parts without exception:
  no fail-soft path may resolve to a silent success rule. The split is machine-
  readable in `CP00_ARCHITECTURE_REVIEW.json` at `fail_soft_policy[FS-04].parts[]`.
- **Principle and ADR dispositions.** Unchanged: 17 `ratify` / 5 `adapt` / 0 `defer`
  for principles and 11 / 6 / 1 for ADRs, the single `defer` still being `ADR-0014`
  under the open `U-04`. `PD-05` decides scope membership, contradicts no baseline
  ADR and therefore issues no `supersede` disposition.

### Downstream obligations

1. **ANA lane.** The four names stay resolved through the explicit exclusion `XS-11`
   with owning boundary `project_optimization`; the core audit registry keeps its nine
   stages; no analysis stage, package, example or fixture may claim the retained
   capability.
2. **Every lane.** Until `W5-OPT-01` is accepted the capability is **disabled**: no
   lane — the OPT contract owner included — may enable, model or expose its stage
   vocabulary, status semantics, packages or endpoints. Silence is the required
   state, not a provisional model. This is obligation `U-06-OB-1`.
3. **BHV/golden lanes.** No W0 journey or fixture may assert project-optimization
   behavior as an audit stage of the core registry.
4. **Integrator/owner.** Discharged on 2026-09-01 by the `U-06` disposition: project
   optimization is a **separate bounded context** with the contract family
   `contracts/optimization/v1/**`, a dedicated **OPT contract owner** who is neither
   ANA nor DOM, and the planned task **`W5-OPT-01`**, scheduled after the freeze of
   the core audit and decision contracts. CP-00 **explicitly excludes** the
   capability's runtime semantics until that task is accepted; this is obligation
   `U-06-OB-2`.
5. **`FS-04` fail-soft policy** for the four excluded names is part **`FS-04-B`**,
   owned by the OPT contract owner in `contracts/optimization/v1/**` under
   `W5-OPT-01`. It may not be encoded before that task and may not be absorbed by
   the analysis contract; the no-silent-success rule binds it in full.

### Open item created by this record — closed on 2026-09-01

`U-06` (review §11) recorded that the retained project-optimization capability had
**no contract owner, no target contract family and no task ID**. `PD-05` retained the
capability and stopped there, and this lane recorded no candidate owner of its own.
The repository owner closed `U-06` on 2026-09-01:

| Field | Disposition |
|---|---|
| Boundary | project optimization is a **separate bounded context** |
| Contract family | `contracts/optimization/v1/**` |
| Owner | a dedicated **OPT contract owner**, neither the ANA nor the DOM lane |
| Task | **`W5-OPT-01`**, after the freeze of the core audit and decision contracts |
| Obligation `U-06-OB-1` | until `W5-OPT-01` is accepted the capability is **disabled**; no lane may enable, model or expose its stage vocabulary, status semantics, packages or endpoints, and `contracts/optimization/v1` is not a frozen family before then |
| Obligation `U-06-OB-2` | CP-00 **explicitly excludes** the capability's runtime semantics; the checkpoint ratifies no stage, state, result package, endpoint or degradation rule of it |

The last two rows are **obligations, not explanation**. They are recorded as such in
the machine matrix under `unresolved_inputs[U-06].obligations[]`, each with the lane
it binds, the condition that lifts it and how it is verified.

### Approval record

```text
decision:            approved
modification/alternative:
  none. Recorded qualification: optimization, optimization_critic,
  optimization_corrector and optimization_review form a separate project-optimization
  sub-pipeline, started on its own or as an optional post-findings branch, whose
  product is improvement proposals rather than audit findings. Section optimization is
  a downstream aggregation/replication pipeline and not the same pipeline. The four
  names are excluded from the nine-stage core audit registry and retained as a
  separate capability with a future contract owner.
identifier:          PD-05 was assigned by the analysis (ANA) lane, not by the owner,
                     and confirmed by the program integrator on 2026-09-01. The number
                     stands, no renumbering follows and the confirmation changed no
                     semantics; the number is still not part of the decision itself.
owner:               repository owner
date:                2026-09-01
evidence reference:  owner disposition stated as a recommendation to approve, with a
                     separate instruction to record it; recorded first by the ANA lane
                     in contracts/analysis/v1/stage-registry.json owner_decisions
                     [PD-05] and excluded_scope XS-11, reconciled into this ledger and
                     into CP00_ARCHITECTURE_REVIEW.json owner_decisions[PD-05] in
                     W0.2 round 3
open item:           none. U-06 was raised by this record and closed by the owner on
                     2026-09-01: project optimization is a separate bounded context,
                     contract family contracts/optimization/v1/**, a dedicated OPT
                     contract owner who is neither ANA nor DOM, planned task
                     W5-OPT-01. Until that task is accepted the capability is disabled
                     (U-06-OB-1) and CP-00 explicitly excludes its runtime semantics
                     (U-06-OB-2).
```

---

## Related inputs `U-01`–`U-06`

`U-01`–`U-06` in [CP00_ARCHITECTURE_REVIEW.md](CP00_ARCHITECTURE_REVIEW.md) §11 are
**not** part of `PD-01`–`PD-05` and create no new decision IDs. The owner recorded a
disposition for `U-01`–`U-05` on 2026-09-01; §11 of the review holds the full text.
`U-06` was raised by this lane in round 3 as the open consequence of `PD-05` and the
owner disposed of it on the same authority and date, recorded in round 4. All six now
carry a recorded disposition.

| # | Status | Short disposition |
|---|---|---|
| U-01 | deferred with a deadline | Numeric cost thresholds go to `W3-C-01`, but must exist before the first paid-provider canary; CP-00 fixes the measurement, not the numbers |
| U-02 | resolved | Worktree is the default; a shared checkout is admissible only with disjoint allowed paths and one owner per hotspot |
| U-03 | assigned | `W0-ARC-02` specifies the architectural lint rules before CP-00; `W1-ARC-01` implements enforcement. The task file is created by the integrator under `docs/program/**` |
| U-04 | **open** | Tenant/IdP boundary required before `W2-C-01`; TTL/legal hold before `W9-C-01` |
| U-05 | conditionally accepted | Five aggregate journeys are admissible, but acceptance requires a machine-readable mapping of each of the 11 inventory candidates to concrete EO/FC assertion IDs, not only journey IDs |
| U-06 | resolved | Project optimization is a separate bounded context: `contracts/optimization/v1/**`, a dedicated OPT contract owner (neither ANA nor DOM), planned task `W5-OPT-01`. Until it is accepted the capability is disabled (`U-06-OB-1`) and CP-00 explicitly excludes its runtime semantics (`U-06-OB-2`) |

`U-04` is the only input still open, and it is open **by an explicit owner
disposition** with its own deadlines: `W2-C-01` for the tenant/IdP boundary and
`W9-C-01` for TTL and legal hold. It does **not** block the CP-00 freeze — those
deadlines would be meaningless if it did. What it blocks is exact and limited:
[ADR-0014](adr/ADR-0014-authz-classification-retention.md) stays `proposed`, the
retention and legal-hold clauses of `ADR-0015` and the `P-13` classification and
retention obligations are not ratified, and no tenant model, identity provider, TTL,
retention or legal-hold value is encoded in any contract.

`U-06` is no longer open. It was a gap this lane named in round 3, not a deferral the
owner chose, and the owner closed it on 2026-09-01 with the disposition recorded
above.

## Integration decisions recorded with these records

The same authority recorded three cross-lane integration decisions on 2026-09-01.
They are documented in [CP00_ARCHITECTURE_REVIEW.md](CP00_ARCHITECTURE_REVIEW.md)
§6.3 and in the machine matrix under `integration_decisions`:

- `ID-01`: `contract_version` is the canonical machine-contract version key with a
  string semver/draft value; `$schema` stays the JSON Schema dialect and `$id` the
  schema identity; a bare `version` key and `schema_version` as contract-envelope
  versions are removed before freeze.
- `ID-02`: `execution_token` is the canonical token name — opaque, equality-only,
  refreshed on every new `Attempt`, verified in the publishing transaction; fencing is
  behavior, not a field name and not a monotonic number.
- `ID-03`: the 25 `control_plane` / 2 `sub_pipeline` / 3 `excluded` / 1 `stage`
  distribution is admissible conditionally on an independent reviewer confirming all
  nine registry stages against capability evidence and separately checking every
  alias-bearing declaration site.
