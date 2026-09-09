# Prototype execution plan — P02 to P05

> **Status: candidate produced by `P0-PLN-01` on `agent/p0-pln-01`; not approved.**
> It does not modify the accepted Foundation Freeze and grants no dispatch authority.
> P01 continues independently of this document. Nothing in P02–P05 is dispatchable until
> the owner accepts this plan and its predecessor gates are genuinely complete.
>
> Base commit `1cb86cd2708f11712a0cd2f481862652fac2e377`; accepted foundation
> `0b01a3eefe0e6724f6570ccebb9154daf1fdbaec`.

## 1. What this plan is

`FF-01` froze the PostgreSQL/S3 foundation. This document turns the remaining prototype
into agent-ready tasks: two navigation tasks, thirteen P02 backend tasks, eight P03
product tasks, four P04 validation tasks and three P05 analysis tasks — **thirty task
files**. Every task file **this plan creates** carries the twelve `TASK_TEMPLATE.md`
sections plus an estimate. Allowed-path blocks are disjoint, or scoped and sequential with
the scope stated inside the claim; section 3.3 lists every shared file.

The PC-01 slice is fixed and is not widened here:

```text
PDF upload
  -> immutable DocumentVersion and InputManifest
  -> checksum-verified publication to private S3
  -> persisted AuditRun
  -> one real AR text-consistency stage
  -> finding with page number and exact quotation
  -> accept/reject/comment with append-only history
  -> UTF-8 CSV bound to project, version and run
  -> proven restart path
```

**What PC-01 deliberately does not contain.** No Job and no Attempt entity, no lease, no
heartbeat, no execution token, no fencing, no resume, no retry, no outbox, no revocation
UI, and no export aggregate. Each of those was in the first candidate and each is removed
here: they are durable-execution and product machinery that the fastest honest route to a
working prototype does not need, and the profile already defers every one of them.

## 2. Task graph and dispatch conditions

```text
FF-01 ACCEPTED
  |
  |-- P1-INT-00 ... P1-INT-01 -> PF-01                    (P01, already dispatchable)
  |        |
  |        `-- P1-NAV-01  schema, tooling, index, planned entries
  |               (dispatchable once P1-INT-00 is accepted: its `make bootstrap`
  |                creates the interpreter this task's own gates need;
  |                then parallel with the INF/DB/STO lanes)
  |
  `-- P0-PLN-01 (this plan) --> owner acceptance

PF-01 + P1-NAV-01
  -> P1-NAV-02   flip the named foundation entries to implemented, regenerate the index
       |
       v  (P02 fan-out gate: plan accepted, forecast recalibrated)
  P2-INT-00   pins, root locks, environment contract, P02_LOCK
       |-- P2-DOM-01   migration head, identity, state guard, error catalog
       |-- P2-BHV-01   synthetic AR corpus and seeded-issue oracle
                |
                |-- P2-META-01   ingest, version, manifest, blob registration
                |-- P2-ENG-01    stage engine and three deterministic stages
                          |
                          `-- P2-AI-01    text_analysis, prompt bundle, adapters
                                   |
                                   v
                          P2-FND-01   evidence gate, findings, decision ledger
                                   |
                                   v
                          P2-RUN-01   persisted AuditRun, sequential executor, restart
                                   |
                                   v
                          P2-EXP-01   synchronous CSV export use case
                                   |
                                   v
                          P2-API-01   frozen OpenAPI v1 surface
                                   |
                                   v
                          P2-INT-01   composition root and final wiring
                                   |
                                   v
                          P2-QA-01    independent journey, restart, negative paths
                                   |
                                   v
                          P2-INT-02   P02 handoff and navigation regeneration
                                   |
                                   v
  P3-WEB-00 -> P3-API-01 -+-> P3-WEB-01 -+
                          |-> P3-WEB-03 -|-> P3-WEB-02 -> P3-QA-01 -> P3-INT-01 / PC-01
                          `-> P3-WEB-04 -+
                                   |
                                   v
  (P4-QA-01 || P4-OPS-01) -> P4-BHV-01 -> P4-INT-01 / PC-02
                                   |
                                   v
  P5-ARC-01 -> P5-META-01 -> P5-INT-01 / PC-03
```

**The evidence gate precedes the runner on purpose.** `P2-FND-01` is built before
`P2-RUN-01` so the executor consumes a real gate for terminal selection and is never
authored against a stub that fakes `published`. For the same reason `P2-FND-01` has no
synthetic-payload escape hatch: it is authored against the real `analysis.text_observations`
artifact, which is why `P2-AI-01` precedes it.

**Integration order** follows `INTEGRATION_POLICY.md`: pins and contract first, then
providers, then application, then the API provider, then the generated client and the
frontend consumer, then QA evidence, then composition and navigation reconciliation.

**Graph honesty rule.** No task file lists an unfinished predecessor under `Depends on`.
Every future dependency appears under an explicit *planned predecessors and dispatch
condition* heading whose bullets are indented two spaces, and each task becomes
dispatchable only when those predecessors are genuinely accepted and integrated. The
`Depends on` section of every task this plan creates therefore reads `none complete at
plan time`, which is the literal truth on this branch.

**One task ID is never reopened in two windows.** The first candidate gave `P2-INT-00` a
"window 1" and a "window 2"; that is now three separate IDs — `P2-INT-00` pins,
`P2-INT-01` composition root, `P2-INT-02` handoff — each dispatched once.

## 3. Ownership

### 3.1 Named hotspot owners

| Hotspot | Sole owner | Note |
|---|---|---|
| P02 migration head, `db/migrations/**` | `P2-DOM-01` | no lane writes DDL; a schema need arrives as a test plus a requested constraint |
| Root dependency locks and the environment contract after P01 | `P2-INT-00` | transferred from `P1-INT-00` at `PF-01`; subject to `OD-06` |
| Backend composition root | `P2-INT-01` | `bootstrap/**`, `api/app.py`, `api/composition.py`, `tests/integration/composition/**`; subject to `OD-07` |
| Frontend composition root, global styles, web configs | `P3-WEB-00` | including `web/playwright.config.ts`, whose test directory it points at the repository-root e2e suite so `P3-QA-01` never edits a web config |
| Generated API client and all HTTP in `web/` | `P3-API-01` | `web/src/shared/api/**` |
| Server-side CSV export | `P2-EXP-01` | `src/auditmanager/exports/**`; `P2-API-01` exposes the route and calls it |
| Aggregate navigation index | one writer per batch | first generation `P1-NAV-01`; then `P1-NAV-02`, `P2-INT-02`, `P3-INT-01`, `P5-INT-01` |
| API contract family `contracts/api/v1/**` | `P2-API-01` | created and frozen there; P03 consumes a snapshot |

### 3.2 Ownership transfers recorded at `PF-01`

`src/auditmanager/shared/db/**` and `db/migrations/**` move from `P1-DB-01` to
`P2-DOM-01`; `src/auditmanager/storage/**` from `P1-STO-01` to `P2-META-01`; root locks and
`.env.example` from `P1-INT-00` to `P2-INT-00`. Each receiving task states "as the post-P01
owner" in its claim. The P01-owned test trees `tests/integration/{db,storage,foundation}/**`
stay with P01 and are forbidden to every P02 task.

`FOUNDATION_LOCK.json` records the **P01** toolchain and stays `P1-INT-00`'s. P02 pins live
in `docs/program/P02_LOCK.json`, which supersedes it for P02 dependencies; nothing edits
the P01 record, so it cannot go stale by omission.

### 3.3 Shared files with sequential writers

Five files are written by more than one task, each in a disjoint scoped section and never
concurrently: `docs/program/CHECKPOINT_REGISTRY.md`, `docs/program/CURRENT_STATE.md`,
`docs/INDEX.md`, `docs/program/ROADMAP.md` and `docs/navigation/INDEX.md`. Each claim names
its scope. No PC-01, PC-02 or PC-03 row exists in the registry today, so `P3-INT-01`,
`P4-INT-01` and `P5-INT-01` **create** their row rather than editing one.

Two glob overlaps the integrator must read narrowly, because the files that state them are
accepted P01 records this plan may not edit:

- `P1-INT-01`'s claim on `docs/program/tasks/P1-*.md` status banners is read as excluding
  `P1-NAV-01.md` and `P1-NAV-02.md`, which own their own banners and may still be authoring
  when `P1-INT-01` runs.
- `P1-NAV-01`'s `docs/navigation/entries/**` is creation-only: a fragment a later task owns
  belongs to that task, and no entry is flipped to `implemented` there.

Per-task navigation incidents are written to `docs/navigation/incidents/<task-id>.jsonl`,
one file per task, so twenty lanes never append to one shared log.

### 3.4 Seam register

Frozen here so lanes can be authored in parallel without a shared file:

| Seam | Provider | Consumers |
|---|---|---|
| S1 BlobStore by `blob_id` | P01 | `P2-META-01`, `P2-ENG-01` |
| S2 input-manifest query | `P2-META-01` | `P2-RUN-01` |
| S3 in-process stage runner returning a `StageResult` | `P2-ENG-01` | `P2-RUN-01`; `P2-AI-01` registers `text_analysis` on it |
| S4 evidence gate returning terminal, published set and diagnostics | `P2-FND-01` | `P2-RUN-01` during `validating` |
| S5 decision commands and finding queries | `P2-FND-01` | `P2-API-01`, `P2-EXP-01` |
| S6 run commands and run status | `P2-RUN-01` | `P2-API-01`, `P2-EXP-01` |
| S7 synchronous CSV export use case | `P2-EXP-01` | `P2-API-01` |
| S8 frozen OpenAPI document | `P2-API-01` | `P3-API-01` |
| S9 widget props and route URLs in `PC01_UI_SEAM.md` | `P3-WEB-00` | every P03 slice |

## 4. Estimates

**Forecast, not a commitment. Calibration PENDING until `PF-01`.**

No measured implementation throughput exists for this repository. The rows below are
derived from task decomposition and the stated assumptions, not from an observed delivery
rate. The repository's pre-pivot activity measures planning and review throughput, not
runtime delivery, and is deliberately not used as an implementation baseline.

**Recalibration trigger:** after `PF-01` is accepted and before `P02` is dispatched, the
program integrator replaces the assumption-based basis of every row with measured P01
figures — elapsed wall-clock from `P1-INT-00` dispatch to `PF-01` acceptance, per-task
authoring elapsed time, and rejection/remediation rounds per accepted task — recording for
each figure the command and the tree that produced it. Until that update is committed, no
row here may be quoted as a delivery commitment. `P5-META-01` ends the pending state
outright using measured P01–P04 throughput.

**The two tables measure different things and are never added together.** Table 4.1 is
person-effort. Table 4.2 is calendar duration. Expert scheduling latency appears only in
4.2; it is waiting, not work, and summing it with person-days would be a category error.

### 4.1 Effort — person-days, the arithmetic sum of task rows

| Stage | Rows | P50 | P80 |
|---|---:|---:|---:|
| Navigation (`P1-NAV-01` 1.0/2.0, `P1-NAV-02` 0.5/1.0) | 2 | 1.5 | 3.0 |
| P02 backend | 13 | 21.0 | 41.0 |
| P03 product and PC-01 | 8 | 8.75 | 18.0 |
| P04 field validation | 4 | 9.0 | 17.0 |
| P05 analysis and next roadmap | 3 | 6.5 | 12.0 |

P02 rows: `P2-INT-00` 0.5/1.5, `P2-DOM-01` 1.75/3.5, `P2-BHV-01` 1.0/2.0, `P2-META-01`
2.5/4.5, `P2-ENG-01` 3.0/5.5, `P2-AI-01` 2.5/5.0, `P2-FND-01` 2.5/4.5, `P2-RUN-01`
1.5/3.0, `P2-EXP-01` 0.75/1.5, `P2-API-01` 1.5/3.0, `P2-INT-01` 1.0/2.0, `P2-QA-01`
2.0/4.0, `P2-INT-02` 0.5/1.0.

P03 rows: `P3-WEB-00` 1.0/2.0, `P3-API-01` 0.5/1.5, `P3-WEB-01` 1.5/3.0, `P3-WEB-02`
2.0/4.0, `P3-WEB-03` 0.75/1.5, `P3-WEB-04` 0.5/1.0, `P3-QA-01` 1.5/3.0, `P3-INT-01`
1.0/2.0.

P04 rows: `P4-QA-01` 2.5/5.0, `P4-OPS-01` 1.5/3.0, `P4-BHV-01` **2.5/4.0 of moderator
effort only**, `P4-INT-01` 2.5/5.0. The expert scheduling wait is not here.

P05 rows: `P5-ARC-01` 2.5/5.0, `P5-META-01` 2.5/4.0, `P5-INT-01` 1.5/3.0.

**Cumulative effort.** Every total is the arithmetic sum of its rows; P50 and P80 are
totalled independently and a P50 row is never mixed into a P80 total.

| Milestone | P50 person-days | P80 person-days |
|---|---:|---:|
| to `PC-01` = navigation + P02 + P03 | **31.25** | **62.0** |
| to `PC-02` = the above + P04 | **40.25** | **79.0** |
| to `PC-03` = the above + P05 | **46.75** | **91.0** |

### 4.2 Elapsed — working days, one integrator and three worker slots

Method, stated so it is reproducible: build the graph from each task's dependency block,
treating "may not be accepted until X" as an edge into the completion node; take the
longest weighted path using the effort weights; add one serial integration and review slot
per acceptance, because a single integrator reviews everything; and never place expert
scheduling latency in a work weight. Review latency is priced at 0.25 day P50 and 0.5 day
P80 per accepted task, which is the plan's answer to its own risk 3 — in the first
candidate that cost was priced at zero.

| Leg | Composition | P50 | P80 |
|---|---|---:|---:|
| P02 critical path | 11 tasks, 17.5 work + 2.75 review | 20.25 | 40.0 |
| P03 critical path | 6 tasks, 7.5 work + 1.5 review | 9.0 | 18.5 |
| `P1-NAV-02` before P02 fan-out | 0.5 work + review | 0.75 | 1.5 |
| **`PF-01` → `PC-01`** | the three legs above | **30.0** | **60.0** |
| **`FF-01` → `PC-01`** | `FF-01`→`PF-01` from FF-01 §9, plus the above | **34–37** | **71–73** |
| **`PC-01` → `PC-02`** | corpus ∥ ledger, then sessions, then report and one owner cycle | **11–14** | **24–27** |
| **`PC-02` → `PC-03`** | three serial P05 tasks plus owner cycles | **7.25** | **13.5** |

The P02 critical path is `P2-INT-00` → `P2-DOM-01` → `P2-ENG-01` → `P2-AI-01` →
`P2-FND-01` → `P2-RUN-01` → `P2-EXP-01` → `P2-API-01` → `P2-INT-01` → `P2-QA-01` →
`P2-INT-02`. It now includes `P2-AI-01`, which the first candidate's path omitted while
its own dependency text required it. The P03 path is `P3-WEB-00` → `P3-API-01` →
`P3-WEB-01` → `P3-WEB-02` → `P3-QA-01` → `P3-INT-01`.

`PC-01` → `PC-02` is **scheduling-bound, not effort-bound**: `P4-BHV-01` contributes 5–8
days P50 and 12–15 P80 of waiting on three to five external experts, which is why the
same-day-response assumption used for P01–P03 is not extended to P04. With named experts
and committed slots under `OD-18`, that P80 falls to 8–9 days.

The `FF-01` → `PF-01` input is FF-01 §9's own 4–7 / 11–13. That figure is a wave-level
estimate: the six P01 task files carry no `## Estimate` section, so it is cited as FF-01's
stated range and not as an arithmetic sum of task rows.

## 5. PC-01 acceptance runbook

Owned by `P3-INT-01` and executed by a reviewer who authored none of the slices, from a
clean clone on a dedicated instance.

1. Clone the certified commit into an empty directory and record the commit.
2. Copy both `.env.example` files, setting a unique `FOUNDATION_INSTANCE`, ports,
   `POSTGRES_DB` and `S3_BUCKET`. Record the values.
3. `make bootstrap` twice — exit `0`, and no tracked file or lock changes on the second run.
4. `make up && make check-services` — exit `0`; both services healthy, the private bucket
   initialized and anonymous access denied.
5. `make migrate && make check-db` — exit `0` from an empty database; rerun `make migrate`
   and confirm it is safe at head.
6. `npm --prefix web ci && npm --prefix web run build` — exit `0`. Start the API, the
   execution process and the web app with the documented commands and record each.
7. Create a project; repeat under the same idempotency key and confirm no second project.
8. Upload the synthetic AR PDF. Confirm an immutable version with page count and checksum,
   and that no bucket or object key appears in the UI or in any network response. Repeat
   under the same key and confirm one version only.
9. Upload one unsupported input. Confirm an explicit unsupported result naming the reason,
   with no run created and no OCR substitution.
10. Start a run in recorded mode. Confirm the badge reads `recorded`, that progress moves
    through `queued`, `running`, `validating` to `published`, and that no **run** is
    labelled `succeeded` — that word is a stage status, not a run state.
11. Start a run in live mode. Confirm the badge reads `live`, the run reaches `published`
    and at least two seeded issues appear. Record provider latency and cost.
12. Open each published finding. Confirm the declared page opens beside a quotation
    byte-identical to the extracted text, and verify manually that each quotation exists on
    that page of the source PDF. Any mismatch is prototype-blocking.
13. Accept one finding with a comment and reject another with a comment. Confirm each
    produces a new decision identity and the expected projection values.
14. Append a later comment to the accepted finding. Confirm the earlier decision remains
    visible with its original value and identity, and that the ledger grew rather than
    changed. This is the append-only demonstration; PC-01 implements no revocation.
15. Download `GET /runs/{run_id}/export.csv` and run the CSV verifier — exit `0`. Confirm
    every row resolves to the same project, version, run, finding and observation and that
    the verdicts match steps 13 and 14. Download a second time and confirm byte-identical
    content; the endpoint creates nothing, so there is no export to duplicate.
16. Stop the web app, API and execution process; `make down && make up`; restart all three
    and confirm project, version, run state, findings and ledger remain resolvable and the
    CSV re-downloads byte-identically, with no run displayed as still running.
17. Interrupt a run by killing the execution process, restart it, and confirm the run
    reaches an explicit non-running outcome with a stated reason — never a stale `running`
    and never a fake success.
18. Stop the provider or invalidate its credential and start a run. Confirm an explicit
    `dependency_unavailable` failure with no fallback to recorded mode and no filesystem
    fallback.
19. Run the end-to-end suite and the bootstrap validator — both exit `0`. Archive every
    artifact, screenshot and measured time, with the method that measured it.

PC-01 passes only when steps 1 to 19 pass as written. Steps 11, 12, 17 and 18 are manual;
the rest are also covered automatically in recorded mode by `P3-QA-01`.

## 6. PC-02 validation protocol and criteria

Frozen before `P4-BHV-01` starts. `P4-INT-01` may not change a threshold after seeing data.

### 6.1 Corpus and protocol

**Definition.** A **measurable** document is one inside the PC-01 input envelope that the
prototype is expected to process to a terminal state and whose findings enter the study's
denominators. A **negative-envelope** document is outside the envelope, exists only to
observe explicit refusal, and enters no denominator and no gate that counts measurable
documents.

The corpus is **12–16 measurable documents — 5 seeded plus 7–11 clean or representative
controls** for false-positive pressure — **plus 2–4 negative-envelope documents counted
separately**. The arithmetic is exact at both ends: 5 + 7 = 12 and 5 + 11 = 16. Total
authored is therefore 14 to 20 documents.

Participants are three to five practising AR reviewers, at least two independent of the
build team. Documents are synthetic unless `OD-17` permits anonymized real ones, in which
case no bytes are committed, quotations are stored as page, offset and hash, and all copies
are destroyed at PC-02 acceptance under a two-person attestation governed by `OD-22`.

Each session records, per finding, one mandatory label from `useful`, `incorrect` or
`unclear` with its follow-up; the moderator's independent check that the quotation is
verbatim at the declared anchor; seconds on finding; and navigation-friction incidents.
Per document it records the run identity, provider mode, duration, stage outcomes,
published and ungrounded-rejected counts, terminal state, false negatives against the
seeded manifest, total review time and a would-you-use-this answer. Post-session it records
a top-three missing-capability ranking, an audit-depth versus comparison forced choice, and
the retry question answered against the moderator's failure ledger rather than from memory.
At least two measurable documents are double-coded. The build commit is frozen for the
whole study.

### 6.2 Instrument-validity gates

A failure here is a PC-01 or P02 defect, not a product finding. Every rate is computed over
measurable documents only.

| Gate | Criterion | Threshold |
|---|---|---|
| G1 | quotation verbatim at the declared anchor | ≥ 95% of published findings |
| G2 | ungrounded items published as findings | exactly 0 |
| G3 | a failed or recorded run presented as live success | exactly 0 |
| G4 | measurable documents reaching a terminal state | ≥ 12, of which ≥ 10 `published` |
| G5 | experts, independence, coverage | ≥ 3 experts, ≥ 2 independent, ≥ 5 measurable documents each, ≥ 2 double-coded |
| G6 | record completeness and provenance | every published finding labelled; every measurable document synthetic or `OD-17`-approved |
| G7 | spend against the ceiling | at or below `OD-03` |
| G8 | build commit across all sessions | exactly one |

Failing G4, G5 or G6 is `BLOCKED` — the study was not performed — rather than `FAIL`. G4's
floor equals the corpus floor deliberately: if fewer than 12 measurable documents reach a
terminal state, the sample statement in 6.5 is recomputed at the surviving count before any
rate is reported.

### 6.3 Product-floor gates

A failure here routes to P05 as leading evidence and never authorizes a foundation change.

| Gate | Criterion | Threshold |
|---|---|---|
| G9 | median per-document share labelled `useful` | ≥ 30% |
| G10 | median per-document share labelled `incorrect` | ≤ 40% |
| G11 | findings an expert would have raised in a real review | ≥ 1 across the corpus |
| G12 | seeded issues missed | ≤ 50% |

`FAIL-PRODUCT` is an accepted outcome. It means PC-01 works and is not yet professionally
useful, and it makes "narrow, retarget or replace the product question" the leading P05
candidate. G11 is the single most consequential number in PC-02.

### 6.4 Observations

Median seconds per finding; navigation friction by class; provider latency percentiles;
cost per run, per published finding and per accepted finding; the failure distribution over
the eight observation classes `P4-OPS-01` defines; the capability ranking; the
depth-versus-comparison choice; failures the ledger shows a retry would have recovered;
self-reported agent search and rework incidents; and raw agreement on double-coded
documents. Negative-envelope documents contribute only a separate refusal-observation
count.

### 6.5 What this sample can and cannot establish

Reproduce verbatim in the PC-02 report:

> This study has 12–16 measurable documents and 3–5 experts. Across that range the 95%
> confidence interval on a rate near 50% is approximately ±24 to ±28 percentage points, and
> near 30% approximately ±23 to ±26 points; the wider figure applies at the 12-document
> floor. Finding-level counts are larger but are clustered within documents and within
> experts, so a naive finding-level interval is materially too narrow and none is reported.
> No inter-rater agreement coefficient is reported on fewer than 30 double-coded findings.
>
> This design can establish that a failure mode occurs at all, that a gross defect exists,
> the direction of a large effect, and the complete absence of a hypothesized behavior in
> this corpus. It cannot establish any rate to better than roughly ±22 percentage points at
> the very best, and no better than ±28 at the corpus floor; nor a difference smaller than
> roughly 25 points between subgroups; nor generalization to other disciplines or to real
> production documents; nor tail latency or cost behavior beyond the 95th percentile; nor
> any claim about multi-tenant, retention, backup or SLO behavior, none of which this study
> exercises.
>
> Every P05 decision therefore rests on direction plus named failure instances, not on the
> decimal places of a point estimate.

## 7. P05 next-investment decision rule

Frozen before `P4-BHV-01` runs. A candidate enters the beta roadmap only when all three
hold: a named PC-02 measurement shows that its absence blocked or measurably degraded a
real review; it is the highest-ranked such blocker under the owner's weighting; and an
owner decision records it. Every candidate without a named measurement defaults to
`defer, evidence not observed` with a written flip-condition. Backlog presence is never a
justification. `P5-ARC-01` recommends, the repository owner decides, `P5-INT-01` records,
and no agent promotes a candidate.

| Candidate | Wins if | Loses if |
|---|---|---|
| more deterministic or AI stages | a named missing stage is top-ranked by at least two experts and at least three documents produced zero findings for want of it | the binding complaint is the precision of the existing stage, which routes to prompt and gate work |
| Job, Attempt, retry, outbox, fencing | at least two distinct ledger failure classes needed a manual re-run and would have been recovered automatically, or a run lost canonical state | fewer than three failures across the corpus, or the dominant class is provider-side and answered by one in-process retry |
| stable finding identity and carryover | experts re-ran at least three documents and re-decided at least 30% of carried findings by hand | reruns averaged under one per document |
| decision revocation in the product | an expert needed to withdraw a verdict during a session and had no way to | no reviewer attempted it; the ledger already supports it without a schema change |
| knowledge projection | at least 20% of decisions repeat a previously recorded verdict on the same semantic issue | below that; do not build on an untested reuse hypothesis |
| deterministic comparison | a majority pick comparison over depth and at least half the corpus exists as revision pairs | experts pick depth, or single-version review dominates |
| remote or distributed workers | a measured execution constraint actually blocked a session | otherwise; provider latency alone is a provider question |
| multi-tenant, retention, backup, SLO | never on P04 evidence, which used no production data; only an owner decision to go to external use unlocks it | — |
| richer navigation graph or semantic search | the self-reported search and rework incidents exceed the owner's tolerance | the validated repository-native index already reduced them, or no task recorded an incident, in which case the metric is absent and the candidate stays deferred |

## 8. Unresolved owner decisions

**Identifier stability.** `OD` ids are append-only. They are never reused and never
renumbered: a decision added later takes the next free number, and a reworded decision
keeps its number. The first candidate's P04 tasks cited a local five-entry list that had
been merged into this register, which mis-mapped five decisions — this rule exists so that
cannot recur.

| ID | Decision | Blocks | Default if unanswered | Needed by |
|---|---|---|---|---|
| `OD-01` | PDF text-extraction library | `P2-INT-00` pin, `P2-BHV-01`, `P2-META-01`, `P2-ENG-01` | a permissively licensed extractor giving per-character boxes plus a separate page-count and encryption probe; a copyleft library is blocked until the owner rules on its licence | `P2-INT-00` dispatch |
| `OD-02` | model provider and model id | `P2-INT-00` pin, `P2-AI-01` | Anthropic first-party API with `claude-opus-5` (1M context; $5.00 per MTok input and $25.00 per MTok output on the 2026-06-24 cached rate table), with `claude-sonnet-5` ($2.00/$10.00) as the cheaper alternative. Confirm current pricing at decision time rather than quoting this row | `P2-INT-00` dispatch |
| `OD-03` | live-run cost ceiling, payer and halt behavior | `P2-AI-01` guard, `P4-OPS-01`, `P4-BHV-01` | a per-run ceiling enforced by `cost_budget_exceeded` that never truncates the document, plus a campaign ceiling; automated tests make zero live calls | before the first live run |
| `OD-04` | `geometry.page_crops` policy | `P2-ENG-01` scope and estimate | emit a schema-valid manifest with an empty crop list under a declared `crop_policy: none`, recorded in the stage metrics. Its only contract consumer is `block_analysis`, which is out of PC-01 scope and would fail closed rather than degrade. **Flip-condition:** if any task adds a content schema for the crop manifest, this decision reopens | `P2-ENG-01` dispatch |
| `OD-05` | finding and recommendation text language | `P2-AI-01` prompt bundle | Russian prose for reviewers, with machine fields, categories and identities ASCII | `P2-AI-01` dispatch |
| `OD-06` | post-P1 root-lock owner | every P02 dependency addition | `P2-INT-00`, recorded as an ownership transfer at `PF-01` | `PF-01` acceptance |
| `OD-07` | backend composition-root owner | all wiring | `P2-INT-01`, a single task dispatched once | `PF-01` acceptance |
| `OD-08` | frontend package manager and composition owner | `P3-WEB-00` | npm with a committed lockfile and a pinned Node version, owned by `P3-WEB-00` | `P3-WEB-00` dispatch |
| `OD-09` | browser PDF rendering approach | `P3-WEB-00` pins, `P3-WEB-02` | a pinned client-side renderer as a bounded island; server-rendered page rasters only if the pin proves unworkable | `P3-WEB-00` dispatch |
| `OD-10` | reconciliation vocabulary for a stale `running` run | `P2-RUN-01`, `P3-WEB-01` | `failed` plus an explicit interrupted reason code; the contract has no `interrupted` state and the UI invents none | `P2-RUN-01` dispatch |
| `OD-11` | CSV byte details — encoding and byte-order mark, delimiter, line ending, quoting — and whether a `partial` run may be exported | `P2-EXP-01`, `P3-WEB-04`, `P3-QA-01` verifier | UTF-8 with BOM, comma delimiter, CRLF, RFC 4180 quoting; a `partial` run is exportable with its state visible, because field validation needs partial runs visible | `P2-EXP-01` dispatch |
| `OD-12` | decision author identity without authentication | `P2-DOM-01` schema, `P2-FND-01`, `P3-WEB-03` | one configured local reviewer label persisted server-side with each event | `P2-DOM-01` dispatch, because it owns the column |
| `OD-13` | is a live provider call part of automated acceptance | `P3-QA-01` scope, `P3-INT-01` | automated suites are recorded-only and deterministic; the live run is manual runbook steps 11 and 12 | `P3-QA-01` dispatch |
| `OD-14` | does P02 dispatch require CP-00 acceptance round eleven and `W0-INT-03` first | the whole P02 graph | see section 9; this plan assumes P02 approval lifts the hold for the P02 paths, and the assumption is recorded rather than hidden | before `P2-INT-00` dispatch |
| `OD-15` | ADR-0019 acceptance, and who records the status transition | `P1-NAV-01` dispatch | accept ADR-0019 together with this plan. No task may edit the ADR or its index row, so the owner records the transition, as with `FF-01` | with this plan |
| `OD-16` | command-surface extension for app startup | P03 developer experience | no `Makefile` edit; the nine targets stay frozen. A new target is an FF-01 freeze-break needing an explicit break record | before P03 |
| `OD-17` | may P04 use anonymized real documents | `P4-QA-01` corpus, `P4-BHV-01` provenance | synthetic only, which tightens the generalization limits in 6.5 | `P4-QA-01` dispatch |
| `OD-18` | expert recruitment and time budget | `P4-BHV-01` | named experts with committed slots; this is the largest driver of the `PC-01`→`PC-02` elapsed leg | before `P4-QA-01` completes |
| `OD-19` | acceptance authority for PC-02 and PC-03, and reviewer independence | `P4-INT-01`, `P5-INT-01`, `P4-BHV-01` | the repository owner is the sole authority, as for `FF-01`; a build-team member does not count toward the independent-expert minimum | `P4-INT-01` dispatch |
| `OD-20` | may `P4-QA-01` corpus authoring overlap P03 | the `PC-01`→`PC-02` leg | no overlap; if permitted, the row moves into the P03 band and the P04 total is restated rather than counted twice | before P03 fan-out, since that is when the overlap would start |
| `OD-21` | the stop rule on `FAIL-PRODUCT` | P05 scope, `P4-BHV-01` framing | a pivot budget fixed before the data exists, so it stays a decision rather than a rationalization | before `P4-BHV-01` |
| `OD-22` | retention and disposal of session evidence | `P4-BHV-01` | pseudonymous identities in committed evidence, the mapping uncommitted, and disposal at PC-02 acceptance. Study governance only; it does not reopen the retention questions FF-01 left unfrozen | `P4-BHV-01` dispatch |
| `OD-23` | disposition when `P4-OPS-01` finds required telemetry absent | `P4-BHV-01` start | the task halts with `BLOCKED` and its gap register, and the owner rules whether to proceed without the metric, add instrumentation as a new P02 task, or narrow PC-02. `P4-OPS-01` never instruments the runtime itself | at the `P4-OPS-01` precondition |

## 9. Conflicts found against the frozen contracts

**C-1 — a required output PC-01 has no consumer for.** `page_geometry_extraction` declares
`geometry.page_crops` a required output, `succeeded` requires every required output role,
and that stage allows neither `partial` nor `skipped`. PC-01 does no visual detection. The
resolution is a real, schema-valid crop manifest with an empty list under a declared
`crop_policy: none`, published as a normal checksum-verified artifact and echoed in the
stage metrics: the required *role* is present, no schema anywhere in `contracts/` constrains
the manifest's body, and the emptiness is declared, attributable and tested, so it is not a
silent fallback. Its only contract consumer, `block_analysis`, is out of PC-01 scope and
would fail closed on an empty list rather than degrade silently. This is `OD-04`, and it
carries a flip-condition.

**C-2 — `published` versus `succeeded`.** The `audit_run` machine has no `succeeded` state;
its success terminal is `published`. `succeeded` exists only as a `StageResult` status on a
different aggregate. The contract wins: the column, the API field, the CSV and every event
use the machine vocabulary. The ban is scoped to run state — `succeeded` is correct on a
per-stage row, and a repository-wide ban would fail on correct code.

**C-3 — the package schemas require an attempt-authority tuple PC-01 has no producer for.**
`job-package.schema.json` and `result-package.schema.json` both list `attempt_authority` in
their top-level `required` array, and that object requires `run_id`, `job_id`, `attempt_id`
and `execution_token`. PC-01 therefore publishes **no** JobPackage and **no** ResultPackage
and claims **no** conformance to those two schemas. The one analysis object PC-01 publishes
as a contract is the `StageResult`, whose `required` array is `contract_version`,
`stage_id`, `stage_version`, `status`, `artifacts`, `metrics` and contains **no**
`attempt_authority`; PC-01 claims full conformance to that schema and validates every
emitted result against it. No contract file is edited: both package schemas keep their
`required` arrays unaltered, and `PROTOTYPE_PROFILE.md` §5 already scopes the claim to
objects actually published as those contracts. Because PC-01 runs one sequential in-process
executor with no Job, Attempt, retry, resume or failover, the two `audit_run` guards whose
predicate names a Job or the current Attempt — `queued -> running` and
`running -> validating` — are recorded as **unevaluated in PC-01**, with no producer for
`execution_token_invalid` or `stale_attempt`. Restoring Job, Attempt and package
conformance is a P05 candidate under the section 7 rule, not a PC-01 deliverable.

**C-4 — CP-00 is mid-supersession.** `CURRENT_STATE.md` records that acceptance round
eleven is owed, that `W0-INT-03` performs the superseding ratification, and that
implementation outside the frozen P01 provider paths remains locked until the detailed
P02–P05 plan is accepted and its dependencies complete. P02 writes production code and
creates a new contract family. This plan assumes that accepting it, together with `PF-01`
and the navigation gate, is what lifts the hold for the P02 paths, and that round eleven is
an independent obligation of the CP-00 line rather than a P02 predecessor. That assumption
is `OD-14`; if the owner rules the other way, the whole P02 graph shifts by the
round-eleven duration and the forecast is restated.

**C-5 — smaller frictions, recorded not resolved.** The run's frozen-at-creation set
includes a norms snapshot that PC-01 never populates. The `import` machine is designed for
bundle ingest, and PC-01's single PDF passes through all five of its states rather than
bypassing them. The finding categories `internal_contradiction` and `explicit_placeholder`
appear nowhere in `contracts/`: they are new product vocabulary declared by the PC-01
analysis profile, not domain-contract terms, and the plan says so wherever they are used.
Ten catalogued identifiers, including `export_id`, `job_id` and `attempt_id`, are
deliberately unallocated in PC-01 and are listed in the `P2-DOM-01` handoff so the catalog
does not silently promise an aggregate nobody builds.

## 10. Risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | PC-01 findings are grounded but professionally useless — the programme's premise, not a stage, is falsified | make it a named acceptable outcome through G9–G11 rather than a surprise; include clean controls so precision is measurable; ask the would-you-have-raised-this question per finding; fix a stop budget in advance under `OD-21` |
| 2 | PDF extraction fidelity for Russian AR documents corrupts spans, so quotations are wrong and every downstream metric is contaminated | assert extractable text and recoverable seeded quotations before sessions; build the corpus from at least three producers; keep the moderator's objective anchor check separate from the expert's opinion; treat any G1 result under 95% as a P02 defect |
| 3 | single-integrator contention — every stage ends in a serial acceptance by one writer and 21 P02/P03 tasks converge on it | the elapsed table now prices one review slot per acceptance instead of zero; enforce disjoint allowed paths so integration is review rather than merge repair; cap concurrent lanes at the integrator's measured review rate once P01 supplies it; escalate a twice-repeated defect shape to the owner as a plan error |
| 4 | expert availability dominates the `PC-01`→`PC-02` leg | resolve `OD-18` before `P4-QA-01` completes, with named people and committed slots; recruit five to land three; design the protocol so a three-expert, twelve-measurable-document study still satisfies G4 and G5 |
| 5 | live-provider cost, latency and nondeterminism — the same document yields different findings on different runs | a hard ceiling with an automatic halt under `OD-03`; the build commit frozen for the study; every label attached to one immutable run identity; the same run reused when a document is reviewed twice; never assert wording equality |
| 6 | corpus realism versus the no-production-data rule | default to synthetic and put the burden on `OD-17`; have a practising reviewer confirm each seeded contradiction is plausible; if anonymized documents are permitted, commit no bytes and destroy copies at acceptance under `OD-22` |
| 7 | calibration never happens and assumption-based rows get quoted as commitments | the recalibration is a required deliverable of `P1-INT-01`'s handoff and a dispatch precondition of P02; every row carries its own basis and pending marker; both tables carry the forecast caption |
| 8 | scope drift under disappointing P04 results | freeze the section 7 rule before `P4-BHV-01` runs; default unbacked candidates to defer with a flip-condition; keep recommendation, record and decision in three different hands |
| 9 | the navigation layer becomes a shared hotspot or goes stale | one entry fragment and one incident file per owning task, integrator-only regeneration of the aggregate, and deterministic-regeneration validation. The incident metric is self-reported, not instrumented, and an empty set is reported as absent rather than as zero |
| 10 | the P02/P03 seam is agreed late — the version-content route, the export endpoint and the CSV column list span both plans | the seam register in section 3.4 freezes them here; the CSV column contract belongs to `P2-EXP-01` and is frozen before `P3-WEB-04` dispatches; the API document is frozen before P03 fan-out |
