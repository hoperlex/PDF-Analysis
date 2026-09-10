# CP-00 architecture review — W0-ARC-01

## 1. Purpose and status

This document is the CP-00 **review candidate** produced by task
[W0-ARC-01](../program/tasks/W0-ARC-01.md). It reconciles the greenfield
[Architecture Bible](ARCHITECTURE_BIBLE.md), the immutable ADR-0001–ADR-0018
baseline in the [ADR index](ADR_INDEX.md) and the accepted
[legacy capability inventory](../behavior/legacy_capability_inventory.md) with the
pinned refactoring architecture source.

It **ratifies nothing by itself**. Ratification is a separate W0.3 integration act
by the program integrator after independent review. What changed in the second round
is that the repository owner has now recorded an explicit disposition for every
`PD-*` item, so this review no longer waits on those four decisions; it still is not
the ratification act.

Round 3 changes one thing only. A fifth owner disposition, on the scope of the
optimization stages, existed in `contracts/analysis/v1/stage-registry.json` under the
identifier `PD-05` but was absent from the authoritative ledger and from this matrix.
An owner decision recorded in a single contract family is exactly the split source of
truth this program exists to prevent, so round 3 reconciles it into
[CP00_OWNER_DECISIONS.md](CP00_OWNER_DECISIONS.md) and into the machine matrix. No
principle disposition, ADR disposition, integration decision or earlier owner record
was changed, and the review is still not the ratification act.

Round 4 records the owner's answers to the three questions this review raised about
records it already carried, and opens no new one. The `PD-05` identifier is
**confirmed** and stands; `U-06` is **closed** with a disposition that gives project
optimization its own bounded context; and the `FS-04` fail-soft policy is **split
into three parts with a named owner each**, machine-readably, because the defect
round 3 could only report was that half of it had no owner at all. `PD-01`–`PD-04`,
`ID-01`–`ID-03`, every principle and ADR disposition and the `ADR-0014` defer are
untouched. The review status stays `owner_decisions_recorded` and this is still not
the ratification act.

Round 5 records one thing and adds no decision. Independent review found that the
already approved `PD-03` modification let two of its own clauses cover the same
request — a repeat of a terminal Run under the **same** idempotency key and payload —
without saying which clause wins. The owner stated the priority: identical
idempotency key and payload **always** return the original Run, and a repeat of a
terminal Run creates a new Run **only** under a new idempotency key. It is recorded
**inside `PD-03`** as a precedence clarification, **not** as a new `PD-NN`: it assigns
the overlap between two clauses and changes neither of them. Both consuming families
must reflect it (§6.2, §14). Everything else stands: `PD-01`, `PD-02`, `PD-04`,
`PD-05`, `ID-01`–`ID-03`, every principle and ADR disposition, the `ADR-0014` defer,
the open `U-04`, the resolved `U-06` and the three-part `FS-04` split. The review
status stays `owner_decisions_recorded` and this is still not the ratification act.

| Item | Value |
|---|---|
| Review status | `owner_decisions_recorded` (round 5) |
| Owner decisions `PD-01`–`PD-05` | recorded 2026-09-01: `PD-01`, `PD-02`, `PD-03` **approved with modification**, `PD-04` and `PD-05` **approved** (§6, [CP00_OWNER_DECISIONS.md](CP00_OWNER_DECISIONS.md)) |
| `PD-03` precedence clarification | recorded 2026-09-01 by the repository owner **inside `PD-03`**, not as a new decision: identical idempotency key and payload always return the original Run; a repeat of a terminal Run creates a new Run only under a new idempotency key (§6.2). The record count stays five and the disposition stays `approved with modification` |
| `PD-05` identifier provenance | the number was assigned by the **analysis (ANA) lane**, not by the owner, and was **confirmed by the program integrator on 2026-09-01**: it stands, no renumbering follows and the confirmation changed no semantics. The number is a cross-artifact label, not part of the owner's statement |
| Decision authority and channel | repository owner; direct instruction to the program integrator session. `PD-05` reached this lane through the ANA lane's contract record and is reconciled here (§6.1) |
| Integration decisions `ID-01`–`ID-03` | recorded 2026-09-01 (§6.3) |
| ADR-0014 status | remains `proposed`; `U-04` stays open by explicit owner disposition |
| ADR files created by this task | none (no `supersede` disposition was issued, see §3.2) |
| Open inputs | `U-04` only (§11). `U-06` was closed by the owner on 2026-09-01; the project-optimization capability it covers stays disabled and outside CP-00 runtime semantics until `W5-OPT-01` |
| Machine matrix | [CP00_ARCHITECTURE_REVIEW.json](CP00_ARCHITECTURE_REVIEW.json) |

## 2. Frozen inputs and evidence policy

| Alias | Full anchor | Role |
|---|---|---|
| base commit | `6c82004b35f49463c8e7fc8602fbced2f374167e` | greenfield package state reviewed here |
| behavioral inventory | `667fb00fe3e45d1ce0bce7860725c1654b4cdeba` | accepted `W0-BHV-01` semantics |
| normalized evidence | `134436502b7ee40ca9abb061e0080741a863ffda` | `W0-EVD-01` immutable anchor normalization |
| legacy oracle | `32b9d903792b30506048a1d42b0e6b2d07aee403` | immutable legacy commit referenced by inventory anchors |
| refactoring architecture source | `0b937dc0e24d38fb98485a920152b83d2f19c982` | advisory engineering source, read only via `git show` |
| refactoring Bible blob | `040a514dc37113d0712cde6757900d2c7d918c10` | `docs/architecture/ADR_BIBLE.md` at that commit |

Evidence classes used in every disposition row:

| Class | Meaning | Trust level |
|---|---|---|
| `[B]` | a row/section of the accepted legacy capability inventory | frozen behavioral evidence |
| `[L]` | an immutable legacy anchor `legacy_oracle:path:symbol@line`, copied verbatim from `[B]` | frozen behavioral evidence |
| `[S]` | refactoring architecture source, read only as `git show 0b937dc0e24d38fb98485a920152b83d2f19c982:<path>` | advisory engineering input |
| `[P]` | a document of this package at the base commit | package baseline, not owner approval |
| `[O]` | an explicit repository-owner disposition recorded in [CP00_OWNER_DECISIONS.md](CP00_OWNER_DECISIONS.md) | product-semantic authority; the only class that can settle a `PD-*` item |

Method rules honoured by this task:

1. No legacy application source file was opened by this task. Every `[L]` anchor is
   copied from the accepted inventory, which recorded it at the legacy oracle commit.
2. The mutable refactoring checkout, its branch position and its worktree are not
   evidence. Only `git show <architecture source commit>:<path>` reads were used.
3. **Source ADR statuses are not inherited.** A source ADR marked `proposed`
   (`[S]` `docs/architecture/ADR_INDEX.md` rows 14, 18–24) never justifies an
   `accepted` disposition here. The refactoring Bible itself states that it becomes
   binding only after a separate approval record
   (`[S]` `docs/architecture/ADR_BIBLE.md` §9).
4. Advisory `[S]` facts in source ADR-0018 §1.1 were verified by their author at
   commit `98d075ea`, which is **not** the behavioral oracle commit and not the
   architecture source commit. They are recorded as advisory corroboration only and
   never as frozen behavioral facts.
5. Where evidence contradicts a Bible principle or an ADR, the contradiction is
   recorded in §10 and escalated. No product semantics were chosen by this task.
6. Round 2 adds exactly one new class of input: `[O]`, the owner's recorded
   dispositions. Every disposition changed in round 2 is changed **because** an
   `[O]` entry removed its stated blocker, and the reason is written into the row.
   No disposition was changed for any other reason and no evidence anchor was
   rewritten.

## 3. Disposition vocabulary

### 3.1 Definitions

| Disposition | Meaning | Effect on CP-00 |
|---|---|---|
| `ratify` | The decision is adopted as written; evidence supports it or does not contradict it. | Eligible for ratification at W0.3 with no text change. |
| `adapt` | The decision is adopted only together with an explicit, evidence-backed qualification or obligation recorded in this review. | Eligible for ratification only with the recorded qualification attached. |
| `defer` | The decision cannot be ratified at CP-00: its core statement is the subject of a pending owner decision or of missing authority. | Stays non-ratified; downstream lanes must not consume it as frozen. |
| `supersede` | Accepted evidence contradicts the decision itself, so it must be replaced by a new ADR that records `supersedes`. | Requires a new indexed ADR file; the baseline ADR is never rewritten or removed. |

An `adapt` disposition never edits the body of a baseline ADR: accepted ADR history
is immutable ([Architecture Bible](ARCHITECTURE_BIBLE.md) §14). The qualification
lives in this review and, where the review demonstrates drift, in the minimal
document updates listed in §12.

### 3.2 Why no `supersede` disposition was issued

Every contradiction found by this review is one of two kinds:

- a **legacy-versus-target divergence** (§8), where the greenfield ADR is the target
  and the legacy behavior is the evidence of why the target differs; or
- a **pending owner decision** (`PD-01`–`PD-05`), where choosing the semantics is
  reserved for the repository owner.

Neither kind is evidence that a baseline ADR is itself wrong, so replacing an ADR
would mean choosing product semantics on the owner's behalf. That is explicitly
forbidden by the task contract.

Round 2 confirms the outcome. The owner approved all four decisions — three with a
modification that **qualifies** the target semantics and none that reverses it — so
no baseline ADR was contradicted by the owner and the `supersede` branch was never
entered. `ADR-0012`, `ADR-0008`, `ADR-0007` and `ADR-0013` therefore keep their
files and index rows, and the approved modifications are attached as `adapt`
qualifications instead. Had any decision been rejected, the affected ADR would have
become a `supersede` candidate with a replacement starting at the next unused number
`ADR-0019` plus its `ADR_INDEX.md` row.

Round 3 does not change this. `PD-05` is approved without modification and decides
which legacy names belong to the core audit registry; it contradicts no baseline ADR,
so the `supersede` branch stays unentered and `adr_files_created` stays `0`.

## 4. Bible principle dispositions

All 22 mandatory principles of [ARCHITECTURE_BIBLE.md](ARCHITECTURE_BIBLE.md) §4 are
covered exactly once.

| P-NN | Principle | Bible anchor | Disposition | Evidence | Compatibility impact | Unresolved |
|---|---|---|---|---|---|---|
| P-01 | Opaque identity | `ARCHITECTURE_BIBLE.md#p-01--opaque-identity` | ratify | `[B]` EX-09 stable `MIG` origin pairs make append idempotent; `[L]` `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/findings/migrated_findings_service.py:_stable_migrated_id@1436`; `[S]` `docs/architecture/adr/ADR-0018-domain-contract-v1.md` §1.1 (`project_id` parsed as a path; advisory, verified at `98d075ea`) | Legacy path/display identifiers survive only as import evidence, never as new identity | — |
| P-02 | Path is not identity | `ARCHITECTURE_BIBLE.md#p-02--path-is-not-identity` | ratify | `[B]` WS-03 path traversal/extension rejection; `[B]` CP-01 versioned comparison-stage filesystem roots with atomic switch; `[B]` §7 gap 7 dual filesystem layouts | Storage adapter owns key layout; migration mapping must be explicit, not inferred from paths | — |
| P-03 | Immutable history, explicit mutable pointers | `ARCHITECTURE_BIBLE.md#p-03--immutable-history-explicit-mutable-pointers` | adapt | `[B]` WS-02 new version does not copy prior output; `[B]` CP-03/CP-04 deterministic artifacts are not mutated by the AI layer; `[B]` EX-02 `not observed`: legacy decision history is replaceable; `[O]` owner disposition 2026-09-01: `PD-01` approved with modification | Ratifiable for versions, runs, manifests and raw comparison evidence; the "decision events immutable" clause is now ratifiable with the approved `PD-01` modification attached: correction and revocation each create a new `decision_id`, and revocation projects the current verdict to `pending` without restoring the superseded one | — (`PD-01` decided) |
| P-04 | Contract before concurrency | `ARCHITECTURE_BIBLE.md#p-04--contract-before-concurrency` | ratify | `[P]` W0.2 wave contract runs four lanes against disjoint allowed paths after a frozen input set; `[S]` `docs/architecture/ADR_BIBLE.md:P-04@132` | No lane may treat another lane's draft as frozen | — |
| P-05 | Modular monolith by default | `ARCHITECTURE_BIBLE.md#p-05--modular-monolith-by-default` | ratify | `[B]` §2.1 23 mapped router modules in one legacy backend; `[B]` DW-01–DW-06 separate worker processes with a different resource/failure profile; `[S]` `docs/architecture/ADR_BIBLE.md:P-05@138` | Worker/engine processes are allowed; any further network service needs its own ADR | — |
| P-06 | Side effects at edges | `ARCHITECTURE_BIBLE.md#p-06--side-effects-at-edges` | ratify | `[B]` §4 "Provider boundaries" and "External side effects" rows; `[S]` `docs/architecture/ADR_BIBLE.md:P-06@145` | Domain code receives ports; adapters own I/O, retry and typed error mapping | — |
| P-07 | Transaction ends in outbox | `ARCHITECTURE_BIBLE.md#p-07--transaction-ends-in-outbox` | ratify | `[B]` DW-05 disk-first event outbox with sequence/ACK; `[B]` DW-04 staging/backup/journal before atomic project replacement | Legacy proves the recovery-journal pattern; the target adds a transactional DB outbox instead of filesystem journals | — |
| P-08 | Retry is normal | `ARCHITECTURE_BIBLE.md#p-08--retry-is-normal` | ratify | `[B]` DW-04 idempotent chunk/session/complete and same-hash replay; `[B]` CP-02 idempotent session/pair creation; `[B]` EX-09 idempotent append by stable origin pair | Idempotency key or natural key is mandatory on every write command | — |
| P-09 | State is a state machine | `ARCHITECTURE_BIBLE.md#p-09--state-is-a-state-machine` | ratify | `[B]` DW-02 state and disposition kept separate; `[B]` §7 gap 6 permissive legacy decision typing; `[S]` `docs/architecture/adr/ADR-0018-domain-contract-v1.md` §1.1 (one explicit legacy state machine only; advisory) | Boolean/status strings must be replaced by declared transitions before any writer exists | — |
| P-10 | No silent fallback | `ARCHITECTURE_BIBLE.md#p-10--no-silent-fallback` | adapt | `[B]` §7 gap 5 fail-soft branches; `[B]` OUT-02 embedded Excel failure is swallowed and the ZIP can still succeed; `[B]` CP-04 deterministic summary fallback on provider/validation failure | Ratifiable only together with the fail-soft mapping in §7: every legacy fail-soft path must resolve to a named failure, partial or observable degraded mode | — |
| P-11 | Derived data is rebuildable | `ARCHITECTURE_BIBLE.md#p-11--derived-data-is-rebuildable` | ratify | `[B]` CP-02 disposable suggestions versus the authoritative saved link file; `[B]` EX-01/EX-04 global decision-log projection and KB views | Projections may be rebuilt at any time; no projection may be the only copy | — |
| P-12 | Observability is contract | `ARCHITECTURE_BIBLE.md#p-12--observability-is-contract` | ratify | `[B]` LO-01 operational action log; `[B]` AN-01 pipeline logs and WebSocket progress; `[S]` `docs/architecture/ADR_BIBLE.md:P-13@186` | Progress remains a projection; durable audit, diagnostic logs and metrics stay separate channels | — |
| P-13 | Security fail-closed | `ARCHITECTURE_BIBLE.md#p-13--security-fail-closed` | ratify | `[B]` WS-01 auth/role gates with visible denials; `[B]` DW-01 admin routes require portal auth **or an explicit insecure-admin mode**; `[B]` §4 safe-path/archive-limit/checksum controls | The legacy insecure-admin escape hatch must not be ported; retention/classification remain with deferred ADR-0014 | ADR-0014 authority |
| P-14 | Simplicity before framework | `ARCHITECTURE_BIBLE.md#p-14--simplicity-before-framework` | ratify | `[P]` AGENTS.md §4 forbids generic repository/base service/global utils; `[S]` `docs/architecture/ADR_BIBLE.md:P-15@214` | Abstractions appear after two real uses or at a mandatory boundary | — |
| P-15 | LLM reproducibility by artifacts | `ARCHITECTURE_BIBLE.md#p-15--llm-reproducibility-by-artifacts` | ratify | `[B]` AN-09 usage/cost accounting with the explicit qualification that cost observability does not establish replayability; `[B]` §5 "Replay and cost accounting" = partial | Replay evidence needs recorded synthetic responses; live text equality is out of scope | — |
| P-16 | Cost is an operational budget | `ARCHITECTURE_BIBLE.md#p-16--cost-is-an-operational-budget` | adapt | `[B]` AN-09 budget/config validation observed, confidence medium; no legacy cost-per-accepted-finding metric was observed | Measurement obligation is ratifiable; numeric budget values and release-stopping thresholds are deferred by the owner to `W3-C-01` and must exist before the first paid-provider canary. CP-00 fixes the measurement, not the numbers | `U-01` (deferred with a deadline, §11) |
| P-17 | Evidence first, AI additive | `ARCHITECTURE_BIBLE.md#p-17--evidence-first-ai-additive` | ratify | `[B]` CP-04 additive AI review/final/summary keyed to current deterministic artifacts; `[B]` FD-02 evidence is not silently invented by the AI summary layer | Strongest legacy-supported principle in the package; AI artifacts stay separate and checksum-referenced | — |
| P-18 | Expert decision is an event | `ARCHITECTURE_BIBLE.md#p-18--expert-decision-is-an-event` | adapt | `[B]` EX-02 `not observed` and §5 "Append-only expert decision events" = **contradicted**; `[L]` `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/knowledge_base/knowledge_base_service.py:revoke_decision@861`; `[O]` owner disposition 2026-09-01: `PD-01` approved with modification | The `defer` basis was the undecided `PD-01`; it is gone. Ratifiable with the approved modification attached: correction and revocation create new `decision_id`s, revocation moves the current projection to `pending` and never auto-restores the superseded verdict, and history is preserved. Legacy overwrite/delete stays characterized legacy behavior | — (`PD-01` decided) |
| P-19 | Legacy is a read-only oracle | `ARCHITECTURE_BIBLE.md#p-19--legacy-is-a-read-only-oracle` | ratify | `[B]` §1 "Runtime execution: None" and §9 read-only Git-object method; `[P]` SOURCE_TRACEABILITY §3 records that the source Strangler model is deliberately not transferred | No runtime legacy dependency exists or is planned; parity is proven by golden/replay evidence | — |
| P-20 | Checkpoint is an evidence bundle | `ARCHITECTURE_BIBLE.md#p-20--checkpoint-is-an-evidence-bundle` | ratify | `[P]` `docs/stages/S00_architecture_and_behavior_freeze.md` exit criteria; `[P]` `docs/manual-tests/CP-00_architecture.md` | This review is one evidence input to CP-00; it is not the checkpoint | — |
| P-21 | Manual acceptance is first-class | `ARCHITECTURE_BIBLE.md#p-21--manual-acceptance-is-first-class` | ratify | `[P]` `docs/manual-tests/CP-00_architecture.md` cases MT00-01–MT00-06, including MT00-06 "Unresolved decisions" | The PD records in §6 are the input MT00-06 samples | — |
| P-22 | Agent parallelism follows ownership boundaries | `ARCHITECTURE_BIBLE.md#p-22--agent-parallelism-follows-ownership-boundaries` | adapt | `[P]` W0.2 wave contract executes four lanes concurrently in one checkout with disjoint allowed paths and single-owner hotspots; `[S]` `docs/architecture/adr/ADR-0016-workspace-isolation.md` is `proposed` with the shared-checkout/worktree choice still open | The ratifiable invariant is "one owner per hotspot and disjoint allowed paths". `U-02` is resolved: a worktree is the default and a shared checkout is admissible only with disjoint allowed paths and one owner per hotspot; the isolation mechanism stays a mechanism, not an invariant | — (`U-02` resolved, §11) |

## 5. ADR dispositions

All 18 indexed ADRs are covered exactly once. "Source status" records the status of
the corresponding refactoring-source ADR, which is **not** inherited.

| ADR-NNNN | Decision | Source status | Disposition | Evidence | Compatibility impact | Unresolved |
|---|---|---|---|---|---|---|
| ADR-0001 | Greenfield product; legacy is a behavioral oracle ([file](adr/ADR-0001-greenfield-behavioral-oracle.md)) | `[S]` source ADR-0001 "hybrid Strangler" = `accepted`; deliberately **not** transferred | ratify | `[B]` §1 "Runtime execution: None"; `[B]` §9 read-only Git-object commands; `[P]` SOURCE_TRACEABILITY §3 | No runtime Strangler dependency; algorithm ports require characterize → contract → tests → parity | — |
| ADR-0002 | Modular monolith control plane ([file](adr/ADR-0002-modular-monolith-control-plane.md)) | `[S]` source ADR-0002 = `proposed`, pending `W0-DEC-01` | ratify | `[B]` §2.1 24 discovered router modules, 23 mapped, in one backend; `[B]` DW-01–DW-06 separate worker execution profile | Separate execution processes allowed; any further service requires a new ADR | — |
| ADR-0003 | Contract-first boundaries and single data owner ([file](adr/ADR-0003-contract-first-and-data-ownership.md)) | `[S]` source ADR-0003 = `accepted` | ratify | `[B]` §7 gap 7 dual filesystem layouts and shadow mirroring; `[B]` CP-02 one authoritative saved link file versus disposable suggestions | Every aggregate needs a named authoritative writer before implementation | — |
| ADR-0004 | Repository layout and module boundaries ([file](adr/ADR-0004-repository-layout-and-module-boundaries.md)) | `[S]` source ADR-0006 = `proposed`, pending `W0-DEC-01` | adapt | `[P]` ADR-0004 mandates architecture lint/test against deep cross-context and FSD cross-slice imports; `[P]` `docs/stages/S00_architecture_and_behavior_freeze.md` requires "architecture lint rules are specified" as CP-00 automated exit evidence; no lint-rule specification exists under `docs/architecture/**` at the base commit | Layout is ratifiable as written; the lint-rule specification is now an **assigned** CP-00 exit obligation: `W0-ARC-02` specifies the architectural lint rules before CP-00 and `W1-ARC-01` implements enforcement | `U-03` (assigned, §11) |
| ADR-0005 | PostgreSQL owns metadata and durable workflow state ([file](adr/ADR-0005-postgresql-metadata-and-durable-state.md)) | `[S]` source ADR-0003 = `accepted` (PostgreSQL/S3 ownership) | ratify | `[B]` §4 "Stores": filesystem JSON/directories plus SQLite plus process-local handles; `[P]` SOURCE_TRACEABILITY §3 "Legacy filesystem/SQLite pilot choices" not transferred; `[O]` owner disposition 2026-09-01: `PD-03` approved with modification | Storage canonicality is uncontested; the `AuditRun` state named by this ADR is supported by the approved `PD-03` identity separation and its recorded Run-creation rule | — (`PD-03` decided) |
| ADR-0006 | Private S3-compatible artifact storage ([file](adr/ADR-0006-private-s3-artifact-storage.md)) | `[S]` source ADR-0003 = `accepted` | ratify | `[B]` DW-04 checksum-verified assembled package, staging/backup/journal, atomic replacement; `[B]` §4 "Stores" | Temporary → verify → publish maps directly onto observed legacy import safety; no legacy S3 parity exists and none is claimed | — |
| ADR-0007 | PostgreSQL jobs/outbox; Attempt fencing ([file](adr/ADR-0007-postgres-jobs-outbox-and-attempt-fencing.md)) | `[S]` source number reserved (ADR-0009 backlog), no source ADR file; `[S]` `docs/architecture/ADR_BIBLE.md` §5.4 | adapt | `[B]` DW-02 at most one active job per project/version and one active attempt per job, attempt-scoped execution token, idempotency keys, stale/superseded rejection; `[B]` DW-05 connection-epoch fencing and the explicit statement that no domain-level `fencing_token` field was established; `[B]` §7 gap 4; `[O]` owner disposition 2026-09-01: `PD-03` approved with modification; `[O]` integration decision `ID-02` (canonical token name) | Durable job/outbox is ratifiable; the fencing clause is ratifiable only with the approved qualification: the capability is named `execution_token`, is opaque and equality-only, is refreshed on every new `Attempt` and is verified inside the publishing transaction. Fencing is a property of behavior, not a field name and not a monotonic number. Retry/resume/restart/worker failover create a new `Attempt`, never a new `AuditRun` | — (`PD-03` decided; `ID-02` fixes the name) |
| ADR-0008 | Execution engine is a package-contract boundary ([file](adr/ADR-0008-execution-engine-package-contract.md)) | `[S]` source number reserved (ADR-0012 backlog), no source ADR file | adapt | `[B]` §2.2 31 stage-declaration sites, 29 mapped, "the declaration sites conflict in membership and order"; `[B]` §5 "Versioned stage registry" = partial; `[B]` §7 gap 2; `[B]` DW-04 publication only after validation; `[O]` owner disposition 2026-09-01: `PD-02` approved with modification; `[O]` owner disposition 2026-09-01: `PD-05` approved (four optimization names excluded from the core registry); `[P]` `contracts/analysis/v1/legacy-stage-map.json` as observed when the decision was recorded: 31 declaration sites, zero name-level alias values; `[P]` a candidate `contracts/analysis/v1/legacy-stage-name-map.json` (62 names) appeared in the same working tree afterwards and is an unfrozen ANA-lane draft, not verified by this lane | The package boundary is ratifiable; the "single versioned stage registry" clause is ratifiable only with the approved `PD-02` precondition — a **name-level** alias map giving every legacy name its surface, `source_declaration_id`, immutable evidence and either a canonical target or an explicit exclusion, with `findings_merge` → `finding_merge` mandatory. Site-level mapping alone does not satisfy it; `ID-03` adds independent confirmation of the nine registry stages and of every alias-bearing declaration site. `PD-05` applies the same single-registry authority to a membership question: four legacy optimization names take the explicit-exclusion branch as a separate project-optimization sub-pipeline, which changes no registry stage and creates no second registry | `PD-02` and `PD-05` decided; ANA acceptance still blocked on the alias map |
| ADR-0009 | Next.js/React/TypeScript strict with FSD ([file](adr/ADR-0009-nextjs-react-typescript-fsd.md)) | `[S]` source ADR-0004 = `accepted`; source ADR-0017 (route strangler) = `proposed` and not applicable | ratify | `[B]` §2.2 items 24–25: the legacy UI declares its own stage/model configuration and legacy artifact aliases; `[B]` §7 gap 8 UI parity unknown | The UI consumes the stage registry and generated client; it never redeclares stage vocabulary; no route-strangler phase exists | — |
| ADR-0010 | Stable Finding identity separate from run observation ([file](adr/ADR-0010-stable-finding-identity.md)) | `[S]` no direct source ADR; `[S]` source ADR-0018 §1.1 (advisory) | ratify | `[B]` EX-09 stable `MIG` identity and idempotent append; `[B]` EX-08 existing non-empty human/auto verdict is preserved by carryover; `[B]` FD-01/FD-02 version-aware listing and strict evidence links | Display ordinals are presentation only; identity matching policy is versioned and may create a new Finding | — |
| ADR-0011 | LLM reproducibility and cost ledger ([file](adr/ADR-0011-llm-reproducibility-and-cost.md)) | `[S]` source ADR-0013 = `proposed`, pending `W0-ADR-04` | ratify | `[B]` AN-09 token/cost/usage and budget records, confidence medium, with the explicit inference that cost observability does not establish replayability; `[B]` §5 "Replay and cost accounting" = partial | Replay parity requires repository-approved synthetic recordings; budget thresholds are separate and unset (`U-01`) | `U-01` |
| ADR-0012 | Expert decisions are append-only; KB is a projection ([file](adr/ADR-0012-expert-decision-ledger-and-kb-projection.md)) | `[S]` no source ADR file for this decision | adapt | `[B]` EX-02 `not observed`: a matching decision is updated and revoke deletes from both the global log and the active review; `[B]` §5 = **contradicted**; `[B]` §7 gap 1; `[L]` `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/knowledge_base/knowledge_base_service.py:_append_to_decisions_log@683`; `[O]` owner disposition 2026-09-01: `PD-01` approved with modification | The `defer` basis was the undecided `PD-01`; it is gone. Ratifiable with the approved modification attached: correction and revocation create new `decision_id`s, revocation projects the current verdict to `pending` with no automatic restore, and the KB projection is rebuilt from preserved history. Legacy overwrite/delete is characterized legacy behavior and is not the target | — (`PD-01` decided) |
| ADR-0013 | Comparison separates approved state, raw evidence and AI synthesis ([file](adr/ADR-0013-comparison-evidence-layers.md)) | `[S]` no source ADR file for this decision | adapt | `[B]` CP-02 approved links authoritative over suggestions; `[B]` CP-03 deterministic gates and signature reuse; `[B]` CP-04 additive AI keyed to current artifacts with race rejection before atomic write; `[B]` CP-05 repair proof/undo; `[B]` CP-06 `not observed`: graphics explicitly not analyzed; `[O]` owner disposition 2026-09-01: `PD-04` approved | Text/approved-link/AI layers are ratifiable. The "raw graphic evidence" layer is approved as future greenfield scope with the recorded qualification: absent from legacy parity and from W0, first contractual inclusion in **W7** together with a dedicated golden graphic pair | — (`PD-04` decided) |
| ADR-0014 | Object authorization and classification/retention policy ([file](adr/ADR-0014-authz-classification-retention.md)) | `[S]` source ADR-0014 = `proposed`, "Утверждено: не утверждено", retention matrix values all unfilled | defer | `[S]` `docs/architecture/adr/ADR-0014-data-classification-retention-and-erasure.md` retention matrix; `[B]` WS-01 exact runtime policy not exercised; `[B]` DW-01 explicit insecure-admin mode; `[B]` LO-01 retention/immutability guarantees not established | Stays `proposed`. No TTL, tenant model, IdP or legal-hold value may be encoded. The owner kept `U-04` open with deadlines: tenant/IdP boundary before `W2-C-01`, TTL/legal hold before `W9-C-01`. Blocks the production storage/security gate, not CP-00 documentation | `U-04` **open**: tenant model, IdP, TTL matrix, legal-hold authority |
| ADR-0015 | Diagnostic logs, durable audit and metrics are separate ([file](adr/ADR-0015-observability-audit-and-redaction.md)) | `[S]` no source ADR file; `[S]` `docs/architecture/ADR_BIBLE.md:P-13@186` | ratify | `[B]` §4 security note: redaction before outbox persistence observed; `[B]` LO-01 action log present but retention/immutability not established | Durable audit retention depends on deferred ADR-0014; the channel separation itself is ratifiable | ADR-0014 authority |
| ADR-0016 | Testing is an evidence model, not a coverage quota ([file](adr/ADR-0016-testing-evidence-model.md)) | `[S]` no source ADR file; `[S]` `docs/architecture/ADR_BIBLE.md` §5.7 | ratify | `[B]` §8 candidates GJ-01–GJ-11 with required assertions; `[B]` §8 "Live LLM text equality is explicitly out of scope" | `W0-BHV-02` selects five journeys from eleven candidates; the uncovered remainder must be recorded as a known coverage gap, not silently dropped | — |
| ADR-0017 | Contract waves and worktree-per-task ownership ([file](adr/ADR-0017-contract-waves-and-worktree-ownership.md)) | `[S]` source ADR-0005 = `accepted` (parallel delivery); source ADR-0016 = `proposed` (workspace isolation unresolved, `W0-DEC-02`) | adapt | `[P]` W0.2 wave contract runs four lanes concurrently in one checkout on disjoint allowed paths; `[S]` `docs/architecture/adr/ADR-0016-workspace-isolation.md` variants A/B still open | The wave/freeze/ownership model is ratifiable; "one worktree per task" is a default mechanism, not an invariant. `U-02` is resolved: worktree is the default, and the shared checkout used by W0.2 is admissible because allowed paths are disjoint and each hotspot has one owner | — (`U-02` resolved, §11) |
| ADR-0018 | Checkpoint = tag + frozen contracts + automated and manual evidence ([file](adr/ADR-0018-checkpoint-versioning.md)) | `[S]` no source ADR file; source checkpoint artifacts exist as `docs/architecture/checkpoints/**` | ratify | `[P]` `docs/stages/S00_architecture_and_behavior_freeze.md` "Integration report must record"; `[P]` `docs/manual-tests/CP-00_architecture.md` final acceptance checklist | This task creates no tag and no checkpoint claim | — |

Disposition totals: **18 / 18 ADRs** — 11 `ratify`, 6 `adapt`, 1 `defer`, 0 `supersede`.
Principle totals: **22 / 22 principles** — 17 `ratify`, 5 `adapt`, 0 `defer`, 0 `supersede`.

Round-2 changes, each caused only by a recorded owner disposition:

- principle `P-18`: `defer` → `adapt`. The undecided `PD-01` was the entire `defer`
  basis; `PD-01` is approved with modification, so the qualification replaces it.
- `ADR-0012`: `defer` → `adapt`, on the same basis.
- `ADR-0014`: `defer` → `defer`, unchanged. `U-04` is still open, so the
  missing-authority basis remains and this is the only remaining `defer`.
- `P-03`, `ADR-0005`, `ADR-0007`, `ADR-0008` and `ADR-0013` keep their round-1
  dispositions; only their qualification text changes, because an approved
  modification replaced a pending decision as the attached condition.

## 6. Owner decisions recorded

### 6.1 Dispositions

Authority: **repository owner**. Channel: direct instruction to the program
integrator session. Date: **2026-09-01**. The full records — statement, evidence,
options, consequences and the filled approval blocks — are in
[CP00_OWNER_DECISIONS.md](CP00_OWNER_DECISIONS.md). This review records the
dispositions; it does not restate them as its own judgement.

`PD-05` is recorded on the same authority and date but by a different route:
`PD-01`–`PD-04` were prepared by this lane and put to the owner, while `PD-05` was
issued by the owner directly and written down first by the analysis lane in
`contracts/analysis/v1/stage-registry.json`. Round 3 reconciles it into the ledger
and this matrix. Its identifier `PD-05` was **assigned by the ANA lane, not by the
owner**, and the program integrator **confirmed the number on 2026-09-01**: it
stands, no renumbering follows, and confirming it changed no semantics. It is used so
that ledger, matrix and contract name one decision. The number is still no part of
the owner's statement, but it is no longer an open question.

| Decision | Subject | Disposition | Effect on this review |
|---|---|---|---|
| PD-01 | Correction/revocation is a new append-only decision event that changes projections, instead of the legacy overwrite/delete | **approved with modification** | `P-18` and `ADR-0012` move from `defer` to `adapt`; the `P-03` decision-event clause is settled |
| PD-02 | One versioned target stage registry is authoritative; conflicting legacy declarations are aliases/evidence | **approved with modification** | `ADR-0008` stays `adapt`; the modification adds a hard acceptance precondition for the ANA lane |
| PD-03 | `AuditRun`, `Job` and `Attempt` are distinct and current-attempt authority is mandatory | **approved with modification**, plus the precedence clarification of 2026-09-01 recorded inside the same record | `ADR-0007` stays `adapt`, `ADR-0005` stays `ratify`; the review's open sub-question "what creates a new `AuditRun`" is answered, and the overlap between the modification's idempotent-replay and terminal-repeat clauses is assigned |
| PD-04 | Graphic/vector comparison is future target scope, absent from legacy parity and not fabricated in W0 artifacts | **approved** | `ADR-0013` stays `adapt` with the recorded scope qualification |
| PD-05 | `optimization`, `optimization_critic`, `optimization_corrector` and `optimization_review` are a separate project-optimization sub-pipeline, excluded from the nine-stage core audit registry and retained as a capability with a future contract owner | **approved** (identifier assigned by the ANA lane, confirmed by the integrator, §6.2) | No principle or ADR disposition changes; `ADR-0008` keeps `adapt` and gains one membership clause; the retained capability is carried by the separate project-optimization bounded context recorded in the now-closed `U-06` |

### 6.2 The approved modifications

**PD-01 — approved with modification.** Decisions remain append-only. A correction
and a revocation each create a new `decision_id`; neither rewrites nor deletes an
earlier decision. A revocation moves the current projection to `pending` and does
**not** automatically restore the previously superseded verdict. The decision history
is preserved in full. This simultaneously closes the domain lane's open question
`OQ-03` (`contracts/domain/v1`: on revocation the verdict projection goes to
`pending`, not back to the previous verdict).

**PD-02 — approved with modification.** One stage registry is authoritative, but the
ANA lane is accepted **only after a name-level alias map exists**. For every legacy
stage name the map must carry: the surface on which the name appears, its
`source_declaration_id`, immutable evidence, and either a canonical target stage or
an explicit exclusion. `findings_merge` → `finding_merge` is a mandatory example. At
the time of the decision `contracts/analysis/v1/legacy-stage-map.json` carries 31
declaration sites and **zero** concrete alias values, so the acceptance precondition
is not yet met.

**PD-03 — approved with modification.** `AuditRun`, `Job` and `Attempt` are distinct
entities. A new `AuditRun` is created when a top-level audit or re-audit command is
accepted for a frozen set of inputs and configurations. A repeat with the same
idempotency key and payload returns the existing Run. Changed inputs, an explicit
re-audit, or a repeat of a terminal Run create a new Run. Retry, resume, restart and
worker failover create **no** new Run: the `Job` is the same and a new `Attempt` is
created. A terminal Run is never reopened. This answers the sub-question this review
raised in round 1, because legacy supplied no Run evidence at all.

**`PD-03` precedence clarification — recorded 2026-09-01, inside `PD-03`.** This is
**not** a new decision: no `PD-06` exists, the disposition stays `approved with
modification` and the ledger still holds exactly five records. Independent review
found that two clauses of the modification above cover one and the same request — a
repeat of a Run that is already terminal, carrying the **same idempotency key and the
same payload**. One clause returns the existing Run; the other creates a new Run. No
priority was stated, so the request had two admissible outcomes and each consuming
family could pick a different one. The repository owner stated the priority:

> Identical idempotency key and payload **always** return the original Run. A repeat
> of a terminal Run creates a new Run **only** under a new idempotency key.

Only the intersection of the two clauses is assigned; neither clause is narrowed,
withdrawn or rewritten. In the overlap the idempotent-replay clause wins and the
original Run is returned whatever state it is in, creating nothing. Outside the
overlap the new-Run clause is untouched: a repeat of a terminal Run under a **new**
idempotency key creates a new Run, as do changed inputs and an explicit re-audit. The
terminal Run is reopened on neither branch — the replay returns it unchanged and the
new-key repeat produces a separate Run beside it. Both consuming families must reflect
the precedence, because a family carrying one clause without the other, or both
without the priority, is not conformant to `PD-03`: the analysis family in
`contracts/analysis/v1` → `run_lifecycle`, and the domain family in
`contracts/domain/v1` → the `AuditRun` creation rule (§14). The clarification is
machine-readable at `owner_decisions[PD-03].precedence_clarification`.

**PD-04 — approved.** No modification. Recorded qualification: graphic/vector
comparison is a future greenfield feature, absent from legacy parity and from W0.
Its first contractual inclusion is **W7**, together with a dedicated golden graphic
pair.

**PD-05 — approved.** No modification. Recorded qualification: `optimization`,
`optimization_critic`, `optimization_corrector` and `optimization_review` form a
**separate project-optimization sub-pipeline**, started on its own or as an
**optional post-findings branch**. Its product is **improvement proposals, not audit
findings**. **Section optimization is a downstream aggregation/replication pipeline,
not the same pipeline.** The four names are **excluded from the nine-stage core audit
registry** but **retained as a separate capability with a future contract owner**.

Three things about this record must travel with it:

1. **The identifier is not the owner's, and it is confirmed.** `PD-05` was assigned
   by the analysis lane and **confirmed by the program integrator on 2026-09-01**:
   the number stands, no renumbering follows and the confirmation changed no
   semantics. It is used for one-decision-one-name consistency across the ledger,
   this matrix and `contracts/analysis/v1/stage-registry.json`.
2. **It does not compete with `PD-02`.** `PD-05` creates no second registry. It is a
   membership decision taken under the single-registry authority `PD-02` established,
   and it uses the explicit-exclusion resolution that `PD-02`'s own modification
   already requires for every legacy stage name. The nine registry stages are
   unchanged, and `ID-03`'s site-level distribution is neither restated nor altered:
   `PD-05` acts at the name level of the alias map.
3. **The retained capability now has an owner, and it is switched off until its
   task.** The owner's `PD-05` disposition retains the capability and stops there;
   the gap that left was `U-06`, and the owner closed it on 2026-09-01 (§11).
   Project optimization is a **separate bounded context**: contract family
   `contracts/optimization/v1/**`, a dedicated **OPT contract owner** who is neither
   ANA nor DOM, planned task **`W5-OPT-01`** after the core audit and decision
   contracts are frozen. Two obligations ride with the closure: until `W5-OPT-01` is
   accepted the capability is **disabled** and no lane may model it (`U-06-OB-1`),
   and CP-00 **explicitly excludes** its runtime semantics (`U-06-OB-2`). The
   `FS-04` fail-soft policy of the four excluded names is part `FS-04-B` and belongs
   to that owner (§7).

### 6.3 Integration decisions

Recorded by the same authority on the same date. They are not `PD-*` items and they
create no new required-decision IDs for the wave; they resolve naming and
distribution questions raised across lanes. Execution belongs to the contract lanes;
the ARC lane only records them.

| # | Subject | Decision | Applies to |
|---|---|---|---|
| ID-01 | Canonical version key of machine contracts | `contract_version` is the canonical key and carries a string semver/draft version. `$schema` stays the JSON Schema dialect and `$id` stays the schema identity. A bare `version` key and `schema_version` used as contract-envelope versions are removed before freeze | every machine contract family (`contracts/domain/v1`, `contracts/analysis/v1`, later families) |
| ID-02 | Canonical attempt-authority token name | `execution_token` is canonical: an opaque, equality-only capability, refreshed on every new `Attempt`, verified inside the publishing transaction. Fencing is a property of the behavior, **not** a field name and not a promise of a monotonically increasing number. `authority_token` and `fencing_token` survive only in legacy evidence | `ADR-0007`; domain identifiers/state machines/error codes; the analysis result package |
| ID-03 | Legacy stage-map target-kind distribution | The distribution 25 `control_plane` / 2 `sub_pipeline` / 3 `excluded` / 1 `stage` over the 31 declaration sites is admissible **conditionally**: an independent reviewer must confirm all nine registry stages against capability evidence and separately check every alias-bearing declaration site | `contracts/analysis/v1` stage registry and legacy stage map; `PD-02` acceptance |

### 6.4 What is still blocking after these decisions

- `PD-02`'s acceptance precondition. At the moment the decision was recorded the
  name-level alias map did not exist. The ANA lane has since published a candidate
  (`contracts/analysis/v1/legacy-stage-name-map.json`, 62 names) in the shared
  working tree. That is another lane's unfrozen draft: whether it satisfies the
  precondition is decided by the integrator and the `ID-03` reviewer, not by this
  lane, and the analysis contract family cannot be accepted on `PD-02` alone.
- `ID-03`'s independent confirmation of the nine registry stages and of every
  alias-bearing declaration site.
- `U-04` (§11), precisely and only: `ADR-0014` stays `proposed`, the retention and
  legal-hold clauses of `ADR-0015` and the `P-13` classification/retention
  obligations are not ratified, and no tenant, IdP, TTL, retention or legal-hold
  value enters any contract. `U-04` does **not** block the CP-00 freeze itself: it
  carries its own deadlines, `W2-C-01` and `W9-C-01`, and demanding its closure
  before CP-00 would make those deadlines meaningless.
- `U-05` (§11): the golden selection needs a machine-readable candidate → assertion
  mapping before acceptance.
- Ratification itself: the dispositions above are recorded owner decisions, not the
  W0.3 ratification act.

`U-06`, which round 3 listed here, is no longer blocking. The owner closed it on
2026-09-01 (§11): project optimization is a separate bounded context with its own
contract family, owner and task, and until `W5-OPT-01` is accepted the capability is
disabled and CP-00 excludes its runtime semantics.

## 7. Legacy fail-soft cases mapped to explicit target policy

Deliverable requirement: every observed legacy fail-soft path resolves to an explicit
target failure, partial or named degraded policy. **No row may be implemented as a
silent success rule.**

| # | Legacy fail-soft behavior | Evidence | Required target policy | Governing rule | Encoder |
|---|---|---|---|---|---|
| FS-01 | Portable audit package: embedded Excel generation failure is swallowed and the ZIP can still be produced without it | `[B]` OUT-02; `[L]` `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/api/routers/export.py:_download_audit_package_v2@137` | Export manifest declares required members. A missing required member yields a typed `partial` or `failed` export with a stable `error_code`; a downloadable artifact never silently omits a declared member | P-10, ADR-0015 | API/export contract owner (post-CP-00) |
| FS-02 | Decision carryover wrapper is fail-soft: provider/threshold failure yields `needs_manual_review` with no verdict | `[B]` EX-08; `[L]` `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/findings/decision_carryover_service.py:run_decision_carryover@436` | Keep the user-visible pending state, but as a declared terminal/intermediate state of a declared state machine with a recorded failure class and provenance; never an implicit empty verdict | P-09, P-10, ADR-0010 | DOM lane (`contracts/domain/v1`) |
| FS-03 | Expert-review shadow-v2 mirror failure is fail-soft | `[B]` EX-01; `[L]` `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/knowledge_base/knowledge_base_service.py:save_expert_review@220` | The target has no dual-write: the second view is a rebuildable projection. A projection build failure is an observable named degraded mode with an owner, not a swallowed exception | P-07, P-11 | DOM lane + integrator |
| FS-04-A | Norm and core-audit branches may record degradation and let an audit complete with warning artifacts | `[B]` AN-06; `[B]` §6 pipeline topology | Stage terminal semantics (`ok`, `partial`, `failed`, `skipped`) are declared in the single versioned core audit stage registry with an explicit consumer policy per state; a degraded norm branch resolves to a declared non-success terminal state | P-09, P-10, ADR-0008, `PD-02` | **ANA lane** — `contracts/analysis/v1/**`, task `W0-ANA-01` |
| FS-04-B | The optimization branch records degradation and continues, for the four names `PD-05` excluded from the core registry | `[B]` AN-06, AN-08; `[B]` §2.2 sites 10, 17 | The project-optimization bounded context declares its own stage and result terminal semantics with an explicit consumer policy per state; a degraded optimization branch resolves to a declared non-success terminal state of that family | P-09, P-10, `PD-05`, `U-06` | **OPT contract owner** — `contracts/optimization/v1/**`, task `W5-OPT-01`; not encodable before that task (`U-06-OB-1`) |
| FS-04-C | An audit completes while an optional optimization branch has failed | `[B]` AN-06, AN-08; `[B]` §6 pipeline topology | Failure of an optional optimization branch resolves the consuming `AuditRun`/`Job` to an explicit **`partial`** and **never** to a full success; the outcome is a declared transition of the domain state machines, not consumer-side tolerance | P-09, P-10, ADR-0005, ADR-0007, `PD-03`, `PD-05` | **DOM lane** — `contracts/domain/v1/**`, task `W0-DOM-01` |
| FS-05 | Comparison AI review falls back to a deterministic summary on provider/validation failure | `[B]` CP-04; `[L]` `32b9d903792b30506048a1d42b0e6b2d07aee403:backend/app/services/stage_comparison/store.py:run_text_ai_review@1068` | Allowed only as a **named, marked, observable** degraded artifact that states its own provenance; it may never be presented as completed AI synthesis | P-10, P-17, ADR-0013 | comparison contract owner (post-CP-00) |
| FS-06 | Pipeline/job state partly lives in process-local active task handles alongside persisted logs | `[B]` §4 "Stores"; `[B]` AN-02 stale `running` converted to `interrupted` at startup | Durable job/attempt state is canonical; process memory is never a status source; recovery is a declared transition, not a startup side effect | P-09, ADR-0005, ADR-0007, `PD-03` | DOM lane + jobs owner |
| FS-07 | Silent identity fallback between `<id>.pdf` and `<id>` when resolving project identity | `[S]` `docs/architecture/adr/ADR-0018-domain-contract-v1.md` §1.1 (advisory, verified at `98d075ea`) | Identity resolution is an explicit typed lookup; an unresolvable identifier is a typed error, never a guessed alternative form | P-01, P-02, P-10 | DOM lane |
| FS-08 | User-visible stage states `error`, `partial`, `skipped`, `interrupted` and comparison `not_started`/stale gates exist without one declared vocabulary | `[B]` §4 "User-visible failures"; `[B]` §2.2 alias declarations | Each state maps to exactly one declared target state with declared transitions and a declared alias table; aliases are evidence, never parallel sources of truth | P-09, ADR-0008, `PD-02` | ANA lane + DOM lane |

The `PD-*` items named in the "Governing rule" column are decided as of 2026-09-01
(§6). `FS-04-A` and `FS-08` inherit the `PD-02` acceptance precondition: their target
policies may be written against the single registry, but they cannot be frozen before
the name-level alias map exists. `FS-06` inherits the `PD-03` Run-creation rule —
recovery after a worker failover is a new `Attempt` of the same `Job`, never a new
`AuditRun`.

`FS-04` is **split into three owned parts** by an owner decision of 2026-09-01,
recorded together with the `U-06` disposition. Round 3 could only report that `PD-05`
had left half of `FS-04` without an encoder; that half now has one. The split is
machine-readable in
[CP00_ARCHITECTURE_REVIEW.json](CP00_ARCHITECTURE_REVIEW.json) at
`fail_soft_policy[FS-04].parts[]`, where every part carries `owner`, `owner_role`,
`target_contract_family`, `task_id` and `silent_success_allowed: false`, and
`FS-04-C` additionally carries the machine `consumer_rule`
(`required_outcome: partial`, `forbidden_outcome: success`). The counters
`fail_soft_policy_parts_without_owner`, `fail_soft_policy_parts_without_target_family`
and `fail_soft_policy_parts_without_task` are all `0` — that is the check for the
defect this split repairs, and it is verifiable without reading prose.

The no-silent-success rule is **not** divided with the policy. It binds `FS-04-A`,
`FS-04-B` and `FS-04-C` in full and admits no exception: no part may resolve a
fail-soft branch to a success, and `FS-04-B` may not be quietly absorbed by the
analysis contract while its own task is pending.

## 8. Legacy-versus-target divergence register

Divergences are explicit, evidence-backed and never presented as parity.

| # | Target position | Legacy observation | Evidence | Kind |
|---|---|---|---|---|
| DV-01 | Expert decisions are append-only events with projections | Matching entries are updated and revocation deletes from log and active review | `[B]` EX-02, §5, §7 gap 1 | owner decision `PD-01` **approved with modification** (§6.2); divergence from legacy is deliberate |
| DV-02 | One versioned stage registry is authoritative | 31 declaration sites with conflicting membership and ordering | `[B]` §2.2, §7 gap 2 | owner decision `PD-02` **approved with modification** (§6.2); alias map is the acceptance precondition |
| DV-03 | `AuditRun`/`Job`/`Attempt` distinct, fencing mandatory | `Job` and `Attempt` durable; no distinct `Run`; epoch/token checks instead of a fencing-token contract | `[B]` DW-02, DW-03, DW-05, §7 gap 4 | owner decision `PD-03` **approved with modification** (§6.2); Run creation rule recorded, and its idempotent-replay/terminal-repeat overlap assigned by the precedence clarification of 2026-09-01 |
| DV-04 | Graphic/vector comparison is future target scope | No graphic comparison artifact; text-difference artifact reports graphics not analyzed | `[B]` CP-06 | owner decision `PD-04` **approved** (§6.2); target scope confirmed, first contractual inclusion in W7 |
| DV-05 | PostgreSQL and private S3 are canonical | Filesystem JSON/directories, SQLite, process-local handles | `[B]` §4 "Stores"; `[P]` SOURCE_TRACEABILITY §3 | accepted greenfield divergence |
| DV-06 | Legacy is a read-only oracle | Refactoring source keeps legacy as production runtime under Strangler | `[S]` source ADR-0001 = `accepted`; `[P]` SOURCE_TRACEABILITY §3 | accepted greenfield divergence |
| DV-07 | Authorization is fail-closed per object | Admin routes accept portal auth **or** an explicit insecure-admin mode | `[B]` DW-01 | accepted greenfield divergence; must not be ported |
| DV-08 | Identity is opaque and path-free | `project_id` is a parsed path; `F-NNN` reissued per run and used as a decision key | `[S]` source ADR-0018 §1.1 (advisory) | accepted greenfield divergence; migration mapping required |
| DV-09 | Stable `error_code` envelope with correlation ID | No single error response form; error text often forwarded from exceptions | `[S]` source ADR-0018 §1.1 (advisory) | accepted greenfield divergence; DOM lane owns the envelope |
| DV-10 | Workspace ingest accepts PDF/ZIP/structured companions | ZIP ingest observed only in comparison upload | `[B]` WS-03, §5 "PDF/ZIP/structured companion ingest" = partial | scope gap; must not be claimed as parity |
| DV-11 | The core audit registry contains no optimization stage; project optimization is a separate sub-pipeline whose product is improvement proposals | Legacy coordinated review/norm/optimization inside the audit pipeline body and also exposed optimization as its own request | `[B]` §2.2 sites 10, 17, 21–22; `[B]` AN-06, AN-08; `[B]` §6 pipeline topology | owner decision `PD-05` **approved** (§6.2); the capability is retained outside the analysis boundary, not deleted, and is carried by the separate project-optimization bounded context recorded in the closed `U-06`: `contracts/optimization/v1/**`, OPT contract owner, task `W5-OPT-01`, disabled until then |

## 9. Decided-semantics register

In round 1 these package texts stated a semantics that was pending owner approval.
The owner has now decided all four items, so the register records **what each text
now means and what condition still rides on it**. The wording of the principles and
ADRs themselves is still unchanged; §12 records the guard notes.

| Location | Statement | Decision | Condition that still applies |
|---|---|---|---|
| `ARCHITECTURE_BIBLE.md` §2, row "current expert verdict" | "projection of append-only Decision events" | `PD-01` approved with modification | revocation projects to `pending`; no automatic restore of the superseded verdict |
| `ARCHITECTURE_BIBLE.md` §4, principle P-18 | "Expert decision append-only" | `PD-01` approved with modification | correction and revocation each create a new `decision_id`; history preserved |
| `ARCHITECTURE_BIBLE.md` §8, "stage registry — single versioned source" | single registry authority | `PD-02` approved with modification | ANA acceptance requires the name-level alias map; `ID-03` reviewer confirmation |
| `ARCHITECTURE_BIBLE.md` §8, "`run_id`, `job_id`, `attempt_id` различны" and "lease/heartbeat + fencing token" | Run/Job/Attempt separation and fencing | `PD-03` approved with modification, with the precedence clarification of 2026-09-01 | Run-creation rule as recorded in §6.2, including the precedence — identical key and payload always return the original Run; token is `execution_token` per `ID-02`, fencing is behavior, not a monotonic number |
| `ARCHITECTURE_BIBLE.md` §11, "raw graphic evidence deterministic and immutable" | graphic evidence layer | `PD-04` approved | out of legacy parity and out of W0; first contractual inclusion in W7 with a golden graphic pair |
| `DOMAIN_MODEL.md` "Decision ledger" and Decisions aggregate row | append-only decision ledger | `PD-01` approved with modification | DOM lane must encode the `pending` projection rule and close its `OQ-03` with it |
| `DOMAIN_MODEL.md` "Run / Job / Attempt" | three distinct identities and fencing | `PD-03` approved with modification, with the precedence clarification of 2026-09-01 | retry/resume/restart/failover create an `Attempt`, never a Run; a terminal Run is never reopened; identical idempotency key and payload always return the original Run, and a repeat of a terminal Run creates a new Run only under a new idempotency key |
| `GLOSSARY.md` rows `ExpertDecision`, `Stage`, `AuditRun`/`Job`/`Attempt` | same three semantics | `PD-01`, `PD-02`, `PD-03` | the same three conditions above |
| `CONTRACT_CATALOG.md` "Analysis package boundaries" | stage registry consumption by engine contracts | `PD-02` approved with modification | engine contracts consume the registry only after the alias map exists |

## 10. Escalations

Round 1 recorded these without resolving them. Round 2 records the outcome; the
contradictions and their evidence are not rewritten.

| # | Contradiction or gap | Evidence | Escalated to | Round-2 outcome |
|---|---|---|---|---|
| E-01 | Bible §2/P-18 and ADR-0012 assert append-only expert decisions; accepted evidence records the opposite legacy behavior | `[B]` EX-02, §5 contradicted, §7 gap 1 | repository owner via `PD-01` | **resolved**: approved with modification 2026-09-01; P-18 and ADR-0012 move `defer` → `adapt` |
| E-02 | Bible §8 and ADR-0008 assert a single versioned stage registry; accepted evidence records 31 conflicting declarations | `[B]` §2.2, §7 gap 2 | repository owner via `PD-02` | **resolved with a precondition**: approved with modification; ANA acceptance requires the name-level alias map |
| E-03 | Bible §8 and ADR-0007 require distinct Run/Job/Attempt with a fencing token; accepted evidence finds no Run entity and no domain-level fencing token | `[B]` DW-03, DW-05, §7 gap 4 | repository owner via `PD-03` | **resolved**: approved with modification, including the Run-creation rule; `ID-02` fixes `execution_token` as the canonical name. Round 5 adds the owner's precedence clarification inside `PD-03` and opens no new escalation |
| E-04 | ADR-0013 and Bible §11 name a raw graphic evidence layer; accepted evidence records graphics as not analyzed | `[B]` CP-06 | repository owner via `PD-04` | **resolved**: approved; first contractual inclusion in W7 with a dedicated golden graphic pair |
| E-05 | The ADR index labels ADR-0001–ADR-0018 (except ADR-0014) "accepted bootstrap" while several of them derive from refactoring ADRs whose source status is `proposed` | `[S]` source `ADR_INDEX.md` rows 14, 18–24; `[P]` ADR index status semantics note | integrator: keep the "not owner-approved" reading explicit at W0.3 ratification | **open**: approving `PD-01`–`PD-04` does not convert a `proposed` source status into an accepted one |
| E-06 | `S00` lists "architecture lint rules are specified" as CP-00 automated exit evidence and ADR-0004 mandates architecture lint/test, but no lint-rule specification exists in the package | `[P]` `docs/stages/S00_architecture_and_behavior_freeze.md`; `[P]` ADR-0004 | integrator: assign an owning task before CP-00 exit (`U-03`) | **assigned**: `W0-ARC-02` specifies the rules before CP-00, `W1-ARC-01` implements enforcement; the task file is authored by the integrator under `docs/program/**` |
| E-07 | `CONTRACT_CATALOG.md` names the ARC owner for `contracts/domain/v1`, while the W0.2 wave assigns that path to the DOM lane and forbids ARC writes there | `[P]` CONTRACT_CATALOG.md; `[P]` W0.2 wave frozen-hotspot table | resolved by the additive note in §12; ownership itself remains a program-governance decision | **resolved** in round 1; unchanged |
| E-08 | ADR-0017 states worktree-per-task as the default isolation, while W0.2 executes four lanes in one shared checkout | `[P]` W0.2 wave contract; `[S]` source ADR-0016 `proposed` | integrator/owner: record the workspace isolation model (`U-02`) | **resolved**: worktree is the default; a shared checkout is admissible only with disjoint allowed paths and one owner per hotspot |

## 11. Additional inputs `U-01`–`U-06` (not `PD-01`–`PD-05`)

`U-01`–`U-05` were recorded in round 1 so that they would not be silently defaulted.
They are **not** product decisions invented by this task and they create no new
decision IDs in the wave's required-decision list. The owner recorded a disposition
for each of those five on 2026-09-01. `U-06` was raised in round 3 as the open
consequence of `PD-05`; the owner closed it on the same authority and date in round
4, so all six now carry a recorded disposition and `U-04` is the only one still open.

| # | Input | Owner | Status | Recorded owner disposition |
|---|---|---|---|---|
| U-01 | Cost/budget values and the release-stopping thresholds behind P-16 and ADR-0011 | repository owner + operations | **deferred with a deadline** | Numeric cost thresholds are deferred to `W3-C-01` but must be defined before the first paid-provider canary. CP-00 fixes the measurement, not the numbers |
| U-02 | Workspace isolation model behind ADR-0017 (shared checkout versus worktree per task) | program integrator | **resolved** | A worktree is the default; a shared checkout is admissible only with disjoint allowed paths and one owner per hotspot |
| U-03 | Owning task for the architecture lint-rule specification required by ADR-0004 and S00 | program integrator | **assigned** | A separate task `W0-ARC-02` specifies the architectural lint rules before CP-00; `W1-ARC-01` implements enforcement. The task file itself is created by the integrator under `docs/program/**`, outside this lane's allowed paths; `docs/program/tasks/W0-ARC-02.md` is present in the working tree |
| U-04 | Tenant model, identity provider, retention TTL matrix and legal-hold authority behind ADR-0014 | repository owner + security/legal | **open** | Stays open by explicit disposition: the tenant/IdP boundary is required before `W2-C-01` and the TTL/legal-hold authority before `W9-C-01`. `ADR-0014` remains `proposed`. It does **not** block the CP-00 freeze; what it blocks is exact and limited (see below) |
| U-05 | Coverage policy for the `W0-BHV-02` candidate journeys not selected as golden | golden owner + integrator | **conditionally accepted** | Five aggregate journeys are admissible, but acceptance requires a machine-readable mapping of each of the 11 inventory candidates to concrete EO/FC assertion IDs, not only to journey IDs |
| U-06 | Contract owner, target contract family and task ID for the project-optimization capability retained by `PD-05` | repository owner + program integrator | **resolved** 2026-09-01 | Project optimization becomes a **separate bounded context**: contract family `contracts/optimization/v1/**`, owned by a dedicated **OPT contract owner** who is neither ANA nor DOM, carried by the planned task **`W5-OPT-01`** after the core audit and decision contracts are frozen. Two obligations ride with it: until `W5-OPT-01` is accepted the capability is **disabled** (`U-06-OB-1`), and CP-00 **explicitly excludes** its runtime semantics (`U-06-OB-2`) |

One input is open: `U-04`, and it is open **by an explicit owner disposition** with
its own deadlines — `W2-C-01` for the tenant/IdP boundary, `W9-C-01` for TTL and
legal hold. It does **not** block the CP-00 freeze; those deadlines would be
meaningless if it did. What it blocks is exact and limited:

1. `ADR-0014` stays `proposed` and is not ratified at CP-00;
2. the retention and legal-hold clauses of `ADR-0015` are not ratified;
3. the `P-13` classification and retention obligations are not ratified;
4. no tenant, IdP, TTL, retention or legal-hold value enters any contract.

Nothing else in this review waits on `U-04`.

`U-06` is closed. It was a gap left by `PD-05` and named by this lane in round 3;
the owner disposed of it on 2026-09-01. Two things in that disposition are
**obligations, not explanation**, and are recorded machine-readably as `U-06-OB-1`
and `U-06-OB-2` in
[CP00_ARCHITECTURE_REVIEW.json](CP00_ARCHITECTURE_REVIEW.json): the capability is
**disabled until `W5-OPT-01` is accepted**, so no lane — the OPT contract owner
included — may enable, model or expose its stage vocabulary, status semantics,
packages or endpoints before then; and CP-00 **explicitly excludes its runtime
semantics**, so the checkpoint ratifies no stage, state, result package, endpoint or
degradation rule of the capability and no CP-00 artifact may be read as covering
them.

## 12. Evidence-required documentation updates applied by this task

Only drift demonstrated above was changed. No ADR body was rewritten and no status
was upgraded.

| Round | File | Change | Justification |
|---|---|---|---|
| 1 | `ARCHITECTURE_BIBLE.md` | Added a CP-00 review pointer under the status header naming the qualified principles (P-03, P-10, P-16, P-22) and the deferred one (P-18) | §4 dispositions; prevents reading P-18 as ratified |
| 1 | `ADR_INDEX.md` | Added a "CP-00 disposition" section referencing this review and listing the `adapt`/`defer` ADRs in plain text (no new ADR links) | §5 dispositions; the index previously implied one uniform bootstrap state |
| 1 | `DOMAIN_MODEL.md` | Added a pending-decision guard note before the aggregate table | §9; the DOM lane consumes this file while `PD-01`/`PD-03` are open |
| 1 | `CONTRACT_CATALOG.md` | Added a per-wave ownership note under the contract-family table | `E-07`; catalog ownership contradicted the active wave assignment |
| 2 | `ARCHITECTURE_BIBLE.md` | Replaced the round-1 pointer: P-18 is no longer deferred, and the note now names the approved `PD-01` modification and the still-open `U-04` | §4 round-2 dispositions; the old note would misstate P-18 as deferred |
| 2 | `ADR_INDEX.md` | Updated the "CP-00 disposition" section to the round-2 lists and to the recorded owner dispositions | §5 round-2 dispositions; ADR-0012 is no longer `defer` |
| 2 | `DOMAIN_MODEL.md` | Replaced the pending-decision guard with the decided semantics of `PD-01`/`PD-03`, including the `pending`-on-revocation rule and the Run-creation rule | §6.2; the DOM lane consumes this file and the round-1 guard is now wrong |
| 5 | `DOMAIN_MODEL.md` | Attached the `PD-03` precedence clarification to the decided semantics, and pointed the "Run / Job / Attempt" narrative line at it instead of restating the overlap loosely | §6.2; this file restated both overlapping clauses without the priority, which is exactly the ambiguity the owner resolved |

Round 3 applied **no** further package-documentation updates: recording `PD-05`
changes no principle text, no ADR body, no Bible section and no domain-model
statement, so the table above is unchanged. Round 3 wrote only
`CP00_OWNER_DECISIONS.md`, `CP00_ARCHITECTURE_REVIEW.md` and
`CP00_ARCHITECTURE_REVIEW.json`.

Round 4 applied none either. Confirming the `PD-05` identifier, closing `U-06` and
splitting `FS-04` into three owned parts changes no principle text, no ADR body, no
ADR status, no Bible section and no domain-model statement; round 4 wrote the same
three CP-00 files and nothing else.

Round 5 applied exactly one, the `DOMAIN_MODEL.md` row above. That file is the only
package document that restated **both** overlapping `PD-03` clauses without the
priority, so leaving it unchanged would have kept the ambiguity alive in the very
document the DOM lane consumes. No principle text, ADR body, ADR status, Bible
section or catalog entry was touched, and no new decision was introduced anywhere.

New files created by this task: `CP00_ARCHITECTURE_REVIEW.md`,
`CP00_ARCHITECTURE_REVIEW.json`, `CP00_OWNER_DECISIONS.md`. No ADR body, ADR status
or evidence anchor was rewritten in any round.

## 13. Coverage and verification

| Check | Result |
|---|---|
| Bible principles covered | 22 / 22, each exactly once (`P-01`–`P-22`) |
| Indexed ADRs covered | 18 / 18, each exactly once (`ADR-0001`–`ADR-0018`) |
| ADR files / index rows / matrix rows | identical sets; no ADR added or removed |
| Owner decisions recorded | 5 / 5: 2 `approved`, 3 `approved with modification`, 0 pending (`PD-05` added in round 3; its identifier was assigned by the ANA lane and confirmed by the program integrator on 2026-09-01). Round 5 added **0** records |
| Owner precedence clarifications | 1, inside `PD-03` (`owner_decisions[PD-03].precedence_clarification`); it creates no `PD-NN`, changes no disposition and changes no clause of the modification it clarifies |
| Integration decisions recorded | 3 (`ID-01`–`ID-03`) |
| `U-01`–`U-06` | 6 inputs, 6 recorded dispositions; 1 open (`U-04`, open by owner disposition and not a CP-00 freeze blocker); `U-06` closed in round 4 |
| Principle dispositions | 17 `ratify`, 5 `adapt`, 0 `defer`, 0 `supersede` |
| ADR dispositions | 11 `ratify`, 6 `adapt`, 1 `defer` (`ADR-0014`), 0 `supersede` |
| Legacy fail-soft cases mapped | 8, none mapped to a silent success rule; `FS-04` is split into 3 parts (`FS-04-A` ANA, `FS-04-B` OPT, `FS-04-C` DOM) |
| `FS-04` parts without a named owner, family or task | 0 / 0 / 0 (`fail_soft_policy_parts_without_owner`, `fail_soft_policy_parts_without_target_family`, `fail_soft_policy_parts_without_task`) |
| `supersede` dispositions | 0 (see §3.2) |

Verification commands are listed in the task contract's "Required tests" section and
were executed against this review; the machine matrix
[CP00_ARCHITECTURE_REVIEW.json](CP00_ARCHITECTURE_REVIEW.json) is the source for the
automated cross-check.

## 14. Consumer notes for the DOM and ANA lanes

After integrator acceptance, downstream lanes may rely on:

- the `ratify` dispositions in §4 and §5;
- the recorded owner decisions in §6, **with their modifications attached** — the
  modification is part of the decision, not commentary on it, and the `PD-03`
  precedence clarification of 2026-09-01 travels with `PD-03` on the same terms;
- the integration decisions `ID-01`–`ID-03` in §6.3 for contract version keys and
  token naming;
- the data-ownership and authoritative-writer statements of ADR-0003, ADR-0005 and
  ADR-0006;
- the fail-soft target policies in §7, which are obligations rather than options.

They may **not** rely on:

- the remaining `defer` disposition, `ADR-0014`, or on anything downstream of the
  still-open `U-04` (tenant model, IdP, TTL matrix, legal hold);
- `PD-02` as sufficient for freezing the analysis registry: its approval carries the
  name-level alias-map precondition and the `ID-03` reviewer confirmation;
- an approved decision as a ratification: §6 records decisions, W0.3 ratifies;
- the project-optimization capability as available scope: `U-06` gives it a bounded
  context, an owner and the task `W5-OPT-01`, but it stays **disabled** and outside
  CP-00 runtime semantics until that task is accepted, and no lane may model it in
  the meantime;
- a `PD-*` number as owner-issued: `PD-05` was numbered by the ANA lane and confirmed
  by the program integrator; the number is a cross-artifact label, not part of the
  owner's statement;
- refactoring-source ADR statuses, legacy implementation details, or another lane's
  unfrozen draft.

Lane-specific obligations created by rounds 2–4:

| Lane | Obligation |
|---|---|
| DOM | Encode the `PD-01` modification (new `decision_id` per correction/revocation, `pending` projection on revocation, no auto-restore) and close its own `OQ-03` with that rule; encode the `PD-03` Run-creation rule **with its precedence clarification** — identical idempotency key and payload always return the original Run whatever state it is in, and a repeat of a terminal Run creates a new Run only under a new idempotency key; use `execution_token` per `ID-02` and `contract_version` per `ID-01`; encode `FS-04-C` in the state machines — failure of an optional optimization branch resolves the consuming `AuditRun`/`Job` to an explicit `partial` and never to a full success |
| ANA | Reflect the `PD-03` precedence clarification in `run_lifecycle`: the idempotent-replay case takes precedence over the terminal-repeat case, which creates a new Run only under a new idempotency key; produce the name-level legacy alias map required by `PD-02` (surface, `source_declaration_id`, immutable evidence, canonical target or explicit exclusion, `findings_merge` → `finding_merge`); carry `contract_version`; expect the `ID-03` reviewer pass over the nine registry stages and every alias-bearing site; keep the four `PD-05` names on the explicit-exclusion branch with owning boundary `project_optimization` and claim none of the retained capability; own `FS-04-A` and absorb no part of `FS-04-B` |
| BHV/golden | Assert no graphic comparison anywhere in W0 (`PD-04`); supply the `U-05` candidate → EO/FC assertion mapping before acceptance |
| OPT contract owner (`W5-OPT-01`) | Own the project-optimization bounded context in `contracts/optimization/v1/**` and encode `FS-04-B` there: a degraded optimization branch resolves to a declared non-success terminal state, never a success. Encode nothing before `W5-OPT-01` is accepted — the capability is disabled until then (`U-06-OB-1`) |
| Integrator | Create the `W0-ARC-02` task file for the lint-rule specification (`U-03`), assign the independent reviewer for `ID-03`, keep `U-04` visibly open against its own deadlines (`W2-C-01`, `W9-C-01`) without treating it as a CP-00 freeze blocker, and schedule `W5-OPT-01` after the core audit and decision contracts are frozen while keeping the project-optimization capability disabled and out of CP-00 scope (`U-06-OB-1`, `U-06-OB-2`) |

Cross-lane mismatch is returned to the integrator. No lane forks terminology to fix
its own build.
