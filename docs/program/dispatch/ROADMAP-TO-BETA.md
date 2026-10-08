# Roadmap after the identity block — waves 52 to 1.0, versioning and the road to beta

**Development-line adoption, 2026-10-08:** `W52-INT-ENTRY-01` copied this
planning record from `plan/roadmap-to-beta` at `2b45a11`. The W52 execution
entry is amended in `W52-PLAN.md`: W51 implementation is closed, while
D-137–D-140 defer QA, live/manual checks and complete gates. This roadmap
remains a planning and owner-answer source; its release rows are targets, not
claims that a wave was frozen, validated, tagged or deployed. `W52-RULE-01`
has recorded R-71…R-74; `W52-FREEZE-01` is still required before W52 dispatch.

**Status:** revision 3, 2026-10-06 (§10.10–§10.13 added; §6.2 restated after costing W53–W55). Revision 1 (2026-10-05, `83fb7e6`) was a proposal; the owner
then answered an eight-round poll (§10), and this revision is rebuilt on those answers.
Written by session `pdf-analysis-e5`. **Still not dispatchable and not a ruling:** the answers are
recorded here as the owner gave them; turning them into `R-` rulings is the integrator's
`*-RULE-01` act, and each block below still gets its own `*-PLAN.md` and `*-FREEZE-01`.
**Base:** `plan/identity-waves` at `b0e112d`. `IDENTITY-WAVES.md` and the W48–W51 plans stay as
written, except the navigation amendment in §10.1 (A-6), which the W50 plan must absorb before its
freeze.

## 1. What the owner asked, in the owner's order

1. W52 is reserved for quality checks, repairs and closing the debts of the W48–W51 block.
2. Then: migrate the production normative corpus to PostgreSQL + S3 on the stand.
3. Bring АР to production state.
4. Implement every section progressively (АИ, КМ, КЖ and the rest).
5. Implement the modules Блоки, Исполнители, Журнал выполнения and Оптимизация, in the order
   that is right today.
6. Fit in the important tasks the existing plans already name, between those goals.
7. Estimate the number of waves and the time; propose how to go faster.
8. Soon: a versioning system, a numbering rule and the path to beta.

## 2. Where we start (measured 2026-10-05; each figure with its source)

| Area | State | Source |
|---|---|---|
| Normative corpus | schema, idempotent DB loader, repair runner, frozen `bge-m3-dense-v1` profile and pgvector image exist; **nothing is loaded on the stand, no byte is in S3**; the promotion wave was withdrawn (`R-54`) | `NORM_CORPUS_PERSISTENCE.md`, `ADR-0020`, `src/auditmanager/norms/**` |
| Corpus size | 674 documents, 28 251 pages, 28 246 crops (4.04 GB), 348 777 paragraphs, 62 325 BGE windows | `.local/norms/corpus/MANIFEST.json`; `NORM_EMBEDDING_BAKEOFF.md` |
| Embedding speed | 1.252 windows/s on 8 CPU cores, measured on 563 windows; **≈ 13.8 h for a full build is an extrapolation**, not a measurement | `fixtures/evaluation/norms/results/bge-m3.json` |
| АР analysis | four stages, one AI stage (`text_analysis`), two finding categories (`internal_contradiction`, `explicit_placeholder`); 25 MiB / 30 pages, text layer on every page; no retry | `src/auditmanager/runs/repository.py` `PC01_STAGES`; `ingest/envelope.py` |
| АР in legacy | 17 pipeline stages, 12 АР finding categories, block (drawing) analysis, merge, critic, norm verification, optimisation | legacy `backend/app/pipeline/stages`, `prompts/disciplines/AR/finding_categories.md` |
| Sections | 14 codes in the contract; only `AR` is analysed; a document stored as another section is analysed with the АР profile (`D-110`) | `ProjectSection` in `contracts/api/v1/openapi.json`; `analysis/text/profile.py` |
| Section registry mismatch | contract has `PB` and no `PS`; legacy's registry has `PS` «Пояснительная записка» and no `PB`; five names differ | legacy `prompts/disciplines/_registry.json`; `web/src/entities/project/model/section.ts` |
| Блоки | real read-only screen over text-line geometry (W45); no drawing-block segmentation, no crops | `api/routers/blocks.py` |
| Журнал выполнения | stub; `stage_result`, `model_call`, `command_record` are persisted, no operation reads them | `_pages/logs/ui/logs-page.tsx`; `W43-PREP.md` |
| Исполнители | stub; execution is sequential and in-process; no job/attempt/worker tables | `_pages/workers/ui/workers-page.tsx`; `runs/executor.py` |
| Оптимизация | stub promising *analysis tuning*; legacy uses the word for **three** functions: project optimisation (OPT proposals under a vendor list), section optimisation (Form 7 specification across projects and replication of accepted proposals), and the model/stage configuration dialog | `_pages/optimisation/ui/optimisation-page.tsx:32`; legacy `frontend/index.html`, `backend/app/services/section_optimization_*`, `prompts/pipeline/ru/optimization_task.md` |
| Comparison | `/…/comparison` compares two **runs** of one version; legacy compared two **design stages** (sheet pairing, text differences, AI summary; no graphics) | `W43-COMPARE.md`; `docs/behavior/legacy_capability_inventory.md` CP-01…CP-06 |
| Versioning | `alpha-wNN` tags; `pyproject.toml` `0.0.0`, `web/package.json` `0.1.0`, API `info.version` `1.0.0-draft.1` unchanged through ~8 reseals; an unused CP-series plan in `CHECKPOINT_REGISTRY.md`; no definition of beta | `git tag`; `VERSIONING_AND_FREEZE_POLICY.md` |

### 2.1 Measured delivery throughput (the basis of every estimate in §6)

| Wave | Active work | Wall clock | Lanes | Judges | Judge → repair rounds |
|---|---|---|---|---|---|
| W39+W40 | 2h50 | 2h50 | 4 | 0 | 0 |
| W41 / W42 | 2h24 / 2h | same | 2 / 2 | 0 | 0 / 1 |
| W43 / W44 / W45 | 1h30–5h | 1h30–5h | 2 | 2–3 | 2 |
| W46 | ≈ 11h | 3d11h (64h weekend, 7h night) | 6 | 4 | 3 |
| W47 | ≈ 14h | 32h | 4 | 2 | 1 |
| W48 | ≈ 11h so far | > 3.5 days, open | 15 | 5, all REJECT | 4 so far |

Source: first-parent history of `integration/w48-close` and tag dates. Inside W48 a four-lane
stage took **30 minutes** from dispatch to merge, a judge **≈ 10 minutes**, a FIX **5 minutes to
1h20**; a full `make gate` is **≈ 13 minutes** (battery 11:07 in `/root/w47-close-gate.log`).
**Execution is not the bottleneck;** waiting is — owner decisions, plan judging (six rounds for
the identity plan), serial reject/repair loops, nights and weekends between hand-offs.

## 3. Order and why

Two dependencies force an interleave of the owner's list: **АР cannot reach production without
the corpus** (its legacy categories `normative_refs`, `fire_safety`, `evacuation`, `accessibility`
are checks against norms), and **neither the corpus promotion nor a production АР run survives
without durable execution** (PC-02: 3 provider failures in 17 attempts, no retry).

```text
W52 quality + versioning system + tools
  ├─► corpus: custody ─► promotion + embeddings ─► retrieval + citations ─┐
  └─► execution: jobs, retry, Журнал, Очередь ─► Исполнители, Блоки, block analysis ─► АР depth, Настройки анализа
                                                                         ▼
                                                    АР norm verification ─► beta gate
  beta:  sections (cheap first) ║ comparison (versions + carryover, then П/Р stages)
         Оптимизация проекта ║ Диспетчер ─► Оптимизация разделов ─► RC ─► 1.0 ─► График работ (1.1)
```

**Module order** (the "actual order" the owner asked for, confirmed by the poll):
Журнал выполнения and Очередь → Исполнители → Блоки → Настройки анализа → Оптимизация проекта →
Оптимизация разделов.

## 4. Wave map — scenario C, chosen by the owner (two tracks per wave)

Sizes: **M** ≈ 8–10 h active, **L** ≈ 12–15 h active, **L+** = two tracks in one wave.
Each track owns disjoint contexts; the shared hotspots — contract and migration head — are
written once at the start of the wave by one seal slot that owns both tracks' reseals and
migrations, with migration numbers assigned in the plan. Section lanes write disjoint profile
directories and the registry is generated.

| Wave | Track 1 | Track 2 | Size | Release |
|---|---|---|---|---|
| **W52** | quality, repairs, debts of W48–W51 (owner); deploy bound to the gate | **versioning system** (§8); fact registry; faster gate; pin-sweep tool | L+ | `v0.3.0` |
| **W53** | data safety: `D-119` MinIO upgrade, non-destructive backup pulled to this machine and restored with real objects, the custody design frozen (`R-W2`, documents rewritten) | E1: durable job queue on W48's tables (leases, heartbeat, reclaim, provably-safe retry, bounded resume, cancel, re-audit, pause), transactional journal; **Журнал выполнения**; **Очередь** | L+ | `v0.4.0` (execution core) |
| **W54** | corpus foundation on this machine: custody implementation and the storage role change, repairs through a durable journal (≤ $10), corpus debts `D-124`…`D-127`, pinned BGE image, promotion bundle, importer and inbound channel, rehearsed locally (`W54-PLAN.md`) | worker service and registry, **Исполнители**; report-only probes: the portal's OCR bundle and image input through the proxy | L+ | `v0.5.0` (workers) |
| **W55a** | corpus on the stand: embeddings built here (G-1), bundle pushed and imported, current snapshot set by an administrator and pinned by runs (G-6), **text search** with citations (G-5), «Нормы» screen, ranged PDF streaming (`W55-PLAN.md` Part A) | — | L | `v0.6.0` (corpus search) |
| **W55b** | AR-1a: portal bundles only (G-4, G-10), up to 500 pages / 250 MiB streamed end to end (G-2), the analysis input budget (G-11), recognised text marked, portal blocks, crops cut locally, **Блоки** made real (`W55-PLAN.md` Part B) | — | L+ | `v0.6.1` (portal bundles, blocks) |
| **W56a** | AR-2 on text: profile v2 with seven non-normative categories (H-2), severity proposed by the model and decided by the expert (H-3), deterministic `finding_merge` (H-4), recognised text as context for text-less pages (H-7), the no-regression quality gate (H-5), the seeded-corpus generator, the model identity check (H-6) (`W56-PLAN.md` Part A) | — | L+ | `v0.7.0` (АР v2 on text) |
| **W57a** | AR-3a, before W56b (I-12): the reviewed checklist map, a reproducible retrieval set pinned by the run, profile v3 with six normative categories, citations grounded by quote and value, the norm-verification report (`W57-PLAN.md` Part A) | — | L+ | `v0.8.0` (norms in the analysis) |
| **W57b** | AR-3b: `normative_refs` by the corpus (`norm_verification` deterministic), Excel in legacy's layout, the owner's review of v3 findings (`W57-PLAN.md` Part B) | — | L | `v0.8.1` (references, Excel) |
| **W56b** | `block_analysis` over the W55b crops (G-8), **region evidence**, recognised-text citations, **chunked text analysis** (G-11), **the critic** (H-10), multi-call resume, **Настройки анализа** (presets, A-8); **after W57b (I-12)**; planned after the W54 vision probe (`W56-PLAN.md` Part B) | — | L+ | `v0.9.0` (drawings, critic, presets) |
| **W58** | debts of W53–W57; live acceptance with real АР documents; 2–3 expert smoke sessions; exposure review; backup/restore drill; contract `1.0.0` | — | M | **`v1.0.0-beta.1`** |
| **W59** | S0 framework: 15 sections, stage attribute П/Р, section suggestion + confirmation, run routed by confirmed section, profile registry from legacy (§10.3); **АИ, ПЗ, ПОС, ТХ** | comparison-1: versions of one set, finding matching, decision carryover with confirmation (§10.4) | L+ | `beta.2` |
| **W60** | **КЖ, КМ, ОВ, ВК, ПТ** | **Оптимизация проекта** on АР (§10.1) | L+ | `beta.3` |
| **W61** | debts + expert validation of W59–W60 | — | M | — |
| **W62** | **ЭОМ, СС, ИТП, ГП, ПБ** | comparison-2: stages П/Р; **Диспетчер** (§10.5) | L+ | `beta.4` |
| **W63** | **Оптимизация разделов** + Оптимизация проекта for the remaining sections | — | L | `beta.5` |
| **W64** | debts, hardening (load/SLO, security review, least-privilege roles, restore drill, operator docs), release acceptance | — | M | `v1.0.0-rc.1` → `v1.0.0` |
| after 1.0 | **График работ** (`1.1.0`); remote/distributed workers; graphic comparison; SMTP and avatar upload if still wanted | | | `1.x` |

**Count:** 12 waves after W52 (W53–W64) since W54 was split on 2026-10-06 (F-1); beta after **6** of them. Moving `block_analysis` to W56 (G-8) keeps the count; W55 runs as two halves, W55a and W55b (G-9), counted as one wave of the map. W56 and W57 run as halves the same way (H-1, I-9); W57a and W57b come before W56b (I-12). The debt cadence holds within
±1 (W52, W58, W61, W64). A wave in which paid model calls would exceed ≈ $5 still stops for the
owner under `R-29` — the budget-per-block measure was not adopted (§7).

## 5. Interstitial tasks — important work between the goals

| Task | Why it cannot wait | Source | Slot |
|---|---|---|---|
| `D-120` deploy not bound to the gate | production data follows in W53 | `D-120` | **owner: accepted as a process rule**, closed in W52 (§10.10) |
| Versioning system (§8), including the build-stamped version endpoint | the acceptance pack attests the deployed SHA from operator input; closes `D-121` | §8; `D-121` (registered by W48) | W52 |
| Debts registered by W48 closure, `D-120`…`D-128` | the W52 quality track's worklist, beside the debts W49–W51 register | `DEBT_REGISTER.md` on `integration/w48-close` | W52 |
| CVE/licence/image scan (`D-122`) | open audit question | `reviews/W48-AUDIT.md` §7 | **owner: not now** — W64 |
| MinIO volume inventory and backup (`D-123`) | precedes the upgrade and custody | `D-123` | W53, backups to this machine until after beta |
| `D-119` MinIO upstream archived | must precede the first custody write | `D-119` | W53: **upgrade to the 2025-10-15 security release; replacement after 1.0** |
| Blob identity vs NORM-Q05 | contract-level conflict | `storage/models.py`; NORM-Q05 | W53: **content-derived Blob + one immutable binding per admission**; NORM-Q05 wording clarified |
| Backup **and restore** rehearsal of PostgreSQL + S3 | corpus and client documents must be restorable before they exist only there | W48 audit §7 | W53 |
| Live provider credential (`D-70`) | blocks paid repairs, live acceptance and every АР wave | `D-70`; P-7 | owner, W48 |
| Retry/resume | 3/17 provider failures in PC-02 | `ALPHA_ROADMAP.md` | W53 |
| Real АР documents (`OD-17`) and named experts (`OD-18`) | АР quality cannot be measured or accepted without them | `OWNER_RULINGS` §4 | F-7: one real set + synthetic; experts before W58 |
| `D-110`: non-АР documents analysed with the АР profile | **owner: unchanged until the section framework** (§10.3, S-6) | `D-110` | W59 |
| `PS` added, five legacy names, stage attribute, section at upload (`D-107`) | the framework is built on them | §10.3 | W59 (reseal) |
| SMTP / registration mail; retention and legal hold (`U-04`) | only if beta users are external or client data is kept | P-2; `U-04` | beta gate, decision D-4.1 |

## 6. Estimates

### 6.1 Method

- Effort comes from **measured active hours** of W46–W48 (11–14 h per L-class wave); elapsed is
  a separate quantity and is never added to effort.
- Elapsed per wave = active × overhead. Measured overhead (wall clock on working days ÷ active)
  is **≈ 1.5–2.0** for W46–W48; nights and weekends are excluded, a 5-day week is assumed.
- An orchestration day of ≈ 8 h is an assumption.
- Russian public holidays (4 November, 31 December – 8 January, 23 February, 8 March) are not
  working days (from revision 3's restatement on; the W54 row moved by one day).
- **Extrapolated, not measured:** every future wave's size class; the АР quality iteration
  (§11 R-1), which the beta gate bounds and effort does not.

| Elapsed per wave, working days | M | L | L+ |
|---|---:|---:|---:|
| current process | 1.75 | 2.5 | 3.5 |
| with the adopted measures (A2–A6, A8) | 1.0 | 1.5 | 2.0 |

### 6.2 Forecast for the chosen scenario

Counted in working days from 2026-10-06 (day 1). **Restated 2026-10-06** after the W53–W55 plans were
costed task by task (below the table).

| Leg | Waves | Working days | P50 date | P80 (× 1.35) |
|---|---|---:|---|---|
| rest of W48, W49 (L), W50 (M), W51 (M) — current process | 4 | 7.0 | ≈ 2026-10-14 | — |
| W52 (L+; ≈ 16 h critical path, `W52-PLAN.md` §9) | 1 | 2.75 | ≈ 2026-10-19 | — |
| W53 (L+; ≈ 22 h critical path, Stage B sequential on this host, `W53-PLAN.md` §9) | 1 | 4.0 | ≈ 2026-10-23 | — |
| W54 (L+; ≈ 40 h critical path at the measured overhead, `W54-PLAN.md` §9) | 1 | 7.5 | ≈ 2026-11-05 | — |
| W55a (L; ≈ 30 h, `W55-PLAN.md` §A6) | ½ | 5.75 | ≈ 2026-11-12 | — |
| W55b (L+; ≈ 57 h, `W55-PLAN.md` §B6) | ½ | 10.75 | ≈ 2026-11-27 | — |
| W56a (L+; ≈ 62 h, `W56-PLAN.md` §A6) | ½ | 11.75 | ≈ 2026-12-15 | — |
| W57a (L+; ≈ 66.5 h, `W57-PLAN.md` §A6) | ½ | 12.5 | ≈ 2027-01-12 | — |
| W57b (L; ≈ 35 h, `W57-PLAN.md` §B6) | ½ | 6.5 | ≈ 2027-01-21 | — |
| W56b (L+; ≈ 75 h, extrapolated, `W56-PLAN.md` Part B; after W57b, I-12) | ½ | 14.25 | ≈ 2027-02-11 | — |
| W58 to beta (≈ 20 h, extrapolated) | 1 | 3.75 | **≈ 2027-02-17** | **≈ 2027-04-05** |
| W59–W64 to RC (≈ 45 + 45 + 20 + 45 + 30 + 25 h, extrapolated) | 6 | 40.0 | **≈ 2027-04-16** | **≈ 2027-06-18** |

**Restated again 2026-10-07** for W57: costed task by task and split (I-9), it is ≈ 101.5 h against the ≈ 30 h
extrapolated here, and it runs before W56b (I-12); beta moves by ≈ 3 weeks. The P80 column is × 1.35 of
the working days counted from day 1, as before.

**Why the dates moved (restatement of 2026-10-06).** The class table above assumed the two tracks of an
L+ wave run side by side. Costing W53–W55 task by task showed two things the class table did not hold:
(1) **on this host the lanes of one wave run one after another** — 11 GiB of memory shared with other
projects, 1–4.8 GiB available, does not hold two executor lanes with their test stands (`W53-PLAN.md` §9,
`W54-PLAN.md` §9); (2) each wave's scope, once written down and judged, is 22–87 active hours, not the 12–15 of an
L wave (W55: 51 h in revision 1, 87 h after its two judging rounds; W56 ≈ 137 h after its first judging round, split). The plans convert hours to days at ≈ 5.3 active hours per working day (the measured overhead).
W56–W64 are given here in hours by the same reading of their scope and converted the same way;
they are **extrapolated**, not costed. The previous figures (beta ≈ 11-18, RC ≈ 12-01) assumed the
parallelism the host does not give. §7 A13 is the measure that buys it back.

Against revision 1's scenario C (beta ≈ 10-27, RC ≈ 11-09) the poll added the versioning system
to W52 and comparison, Диспетчер, Настройки анализа, Оптимизация проекта and Оптимизация
разделов to the map: **≈ +2 working days**, absorbed as second tracks rather than new waves.
For reference, the sequential order at the current process (scenario A of revision 1) gave beta
≈ 2026-11-11 and RC ≈ 2026-12-08 **before** these additions.

**Outside these numbers:** owner decision latency (§10.9), `R-29` stops in paid waves, expert
sessions for the beta gate (`OD-18`), live acceptance on the stand, and the embedding build
(≈ 14 h CPU, extrapolated), which runs here in the owner's night windows (G-1, F-10) and stays off the
critical path only while those windows come.

## 7. Acceleration measures and their status

| # | Measure | Status | Saves |
|---|---|---|---|
| A1 | Two-track waves, one seal slot per wave, migration numbers assigned in the plan | **adopted** (scenario C); **the saving is not realised on this host** — the lanes run one after another (§6.2) | the wave count holds; elapsed time does not shrink |
| A2 | No idle hand-offs: next block planned while the current one executes; freeze at close; owner decisions asked one block ahead in packs | **adopted** | overhead 1.8 → 1.2 |
| A3 | Risk-tiered judging: two cross-judges only for contract, migration, security, data custody; one judge otherwise; section profiles judged by the evaluation harness | **adopted** | 2–4 h per wave |
| A4 | Plan judging capped at two rounds, plus a pin-sweep tool deriving `allowed_paths` grants from the fact a task changes | **adopted** | ≈ 1 day per block plan |
| A5 | Fact registry: one generated file for surface triple, migration head, error count; guards and live prose read it | **W52 deviation confirmed in R-74:** the file is hand-written (a generated one would be a tautology under `CONTRACT_PIN_REGISTRY.md`) and live prose does not read it (`W52-PLAN.md` §3.6) | a reseal touches 1 file, not ~27 |
| A6 | Faster gate: parallel battery (per-worker database and bucket), impacted-test selection for lane gates; full gate on the merged candidate | **W52 serial half confirmed in R-74:** template database, no duplicate foundation run, hazards removed; no `pytest-xdist` in W52. R-70's diff-derived light acceptance remains. A later measurement determines whether to add parallelism. | 13 → ≈ 5 min per gate |
| A7 | Milestone deployment (`main`, live acceptance and tag per milestone) | **not adopted** — per-wave `main` on owner instruction stays | — |
| A8 | Legacy discipline profiles ported as reviewed input data, gated by evaluation | **adopted** — relaxes "not a wholesale port" for profiles only | ≈ half of each section lane |
| A9 | Evaluation harness (precision/recall per category) as a gate | **adopted** (tools) | finite АР iteration |
| A10 | Background compute off the critical path (overnight build or rented GPU) | **adopted as night windows here** (F-10, G-1): repairs, image builds, the embedding build, rehearsals | heavy steps leave the working day |
| A11 | LLM budget per block instead of a stop per wave | **not adopted** — `R-29` ≈ $5 per wave stands | — |
| A12 | One fixture generator for seeded-issue documents | **adopted** (tools) | per-section fixture cost |
| A13 | **Executor capacity:** a host (or a memory upgrade here) where two executor lanes with their test stands fit at once, sized from a measured per-lane peak | **owner: measure first** (G-12) — the per-lane peak is measured during W55, then sized and decided | restores A1: an L+ wave's Stage B halves; ≈ 25–35 % of the remaining elapsed time (extrapolated) |
| A14 | Split an L+ wave into two halves with their own releases | **adopted for W55** (G-9) **and W56** (H-1); offered per wave after it | costs ≈ 6–8 h of a second freeze, seal, judging and close; the first release lands ≈ 10 working days earlier; risks stop mixing |

## 8. Versioning — the owner's choices (§10.6–§10.8) as a design

### 8.1 Numbers

**SemVer 2.0: `MAJOR.MINOR.PATCH[-PRERELEASE]`.**

| Phase | Form | Rule |
|---|---|---|
| alpha | `0.MINOR.PATCH` | MINOR = a completed milestone, in the order milestones complete; PATCH = a later release inside it |
| beta | `1.0.0-beta.N` | N increments with each release during beta |
| release candidate | `1.0.0-rc.N` | feature freeze; fixes only |
| release | `1.0.0`, then `1.MINOR.PATCH` | MINOR = new capability (График работ, remote workers…); PATCH = fixes |

**A release** is an owner-instructed deploy to `main` that changes something a user can see. A
deploy with no user-visible change keeps the version and changes only the build identifier,
which still triggers the update banner. A wave that reaches only `dev` is not a release.

| Version | Content | When |
|---|---|---|
| `0.1`, `0.2` | prototype (PC-01) and the deployed alpha line `alpha-w18` … `alpha-w51` | retroactive labels; **one archive entry** in the history (§10.8) |
| `v0.3.0` | accounts, roles, registration, shell, version history | W52 close |
| `v0.4.0` | durable execution core: Журнал выполнения, Очередь, retry and resume | W53 |
| `v0.5.0` | worker service, Исполнители | W54 |
| `v0.6.0` | corpus on the stand, text search and citations | W55a |
| `v0.6.1` | portal bundles, recognised text, Блоки | W55b |
| `v0.7.0` | АР v2 on text: categories, severity, merge, quality gate | W56a |
| `v0.8.0` | norms in the analysis: the reviewed checklist map and verified citations | W57a |
| `v0.8.1` | the project's own references and Excel | W57b |
| `v0.9.0` | drawings, region evidence, long documents, the critic, Настройки анализа | W56b (after W57b, I-12) |
| `v1.0.0-beta.1` … `beta.5` | beta gate, then sections, comparison, optimisation, Диспетчер | W58–W63 |
| `v1.0.0-rc.1`, `v1.0.0` | hardening and release acceptance | W64 |
| `v1.1.0` | График работ | after 1.0 |

### 8.2 Identifiers and where they live

- **`VERSION`** at the root is the single source of the product version; `W*-INT-MAIN` checks
  that the tag equals it, and the hermetic gate never reads git tags. `pyproject.toml` and
  `web/package.json` keep placeholder versions and are not synchronised, because they sit under
  lock files (`W52-PLAN.md` §3.1).
- **Build identifier** = a digest of the API's own files computed by the API at start-up (not the
  git SHA: the deploy judges images by content and a per-commit value would recreate every
  container on every deploy). The web image has its own content identifier, which the update
  banner compares (`W52-PLAN.md` §3.1).
- **Version read:** `getVersion` for any signed-in account returns product version, build
  identifier and contract version. Nothing is opened to a guest, so nothing new is exposed under
  `R-29` clause 2; migration head and the rest stay in the technical record.
- **Contract version:** unchanged in W52 — it is shared by the API, domain, analysis and events
  families and pinned in about 45 files (`W52-PLAN.md` §3.1). The move to `1.0.0`, and which
  families move together, is decided at the beta freeze (B9) with the error catalog (`D-8`);
  semver rules of `VERSIONING_AND_FREEZE_POLICY.md` apply after that.
- **Tags:** `vX.Y.Z[-pre.N]`, annotated, on owner-instructed `main` commits that passed live
  acceptance. `alpha-wNN` ends with `alpha-w51`. The unused CP-series plan in
  `CHECKPOINT_REGISTRY.md` is retired.

### 8.3 Release notes: written in the repository, stored and served from the database

The owner's condition is that release descriptions are stored in the database; the poll chose
that they are **authored and verified in the repository and loaded into the database at deploy**.
The binding design is `W52-PLAN.md` §3.2–§3.5 (revision 3, after two judging rounds); in short:

- **Authoring.** One file per release, `release-notes/<version>.json`, with an authored integer
  `revision`; entries `{kind, screen, where, text}` — `kind` Новое / Улучшено / Исправлено, `screen`
  the address key of a W50 screen-registry entry, `where` the display path as it read at release
  time, `text` in the user's words with on-screen labels in «ёлочки». The texts are written by a
  lane of the releasing wave (in W52 `W52-RELNOTES-01`), not by the integrator. A file that reached
  `main` is never deleted; corrections are new revisions.
- **Form test in the gate** (from EstiMat's `releaseProblems()`, with its self-test); only the
  entry equal to `VERSION` is checked against the live screen registry, so history does not turn
  red when navigation moves.
- **Judge** against the release diff before the `main` instruction, re-run on the closing candidate.
- **Loading.** A one-shot service after migrations appends revisions (append-only, enforced by
  triggers); a newer release in the database than the image's `VERSION` is left and hidden, so a
  rollback works; a missing older release refuses.
- **Two layers.** The Russian user layer, and an English technical record per release in
  `docs/program/RELEASES.md`.
- **Interface.** «История версий» in the account menu; a banner «Доступна новая версия — Обновить /
  Позже» checked on mount, focus, visibility and route change, **no interval timer**, through a
  session-only `/bff/version`; «Что нового» decided on the server, shown once per account through a
  per-account high-water mark (`account_release_mark`), never for releases loaded before the
  account existed.
- **Contract cost in W52:** three **authenticated** operations (`getProductVersion`,
  `listReleases`, `markReleaseNotesRead`) and migration `0016_release_notes`; nothing is opened to a
  guest.

## 9. Path to beta

**Beta** is the product that named experts use on real АР projects on the deployed stand,
under their own accounts, with the full АР pipeline including norm verification, durable
execution with a run journal, restorable data and a versioned release. Sections, comparison,
optimisation and Диспетчер arrive as `beta.N` releases.

| # | Entry criterion (measured on the deployed stand) |
|---|---|
| B1 | accounts, roles, registration, shell accepted live |
| B2 | corpus snapshot loaded, every PDF and crop in S3 with a confirmed binding, embedding build complete, search answers with citations |
| B3 | АР pipeline: block analysis, merge, review, norm verification; every published finding grounded; quality at or above the thresholds of decision D-3.4 |
| B4 | durable execution: provider failure retried, restart resumes, Журнал выполнения shows it |
| B5 | real АР documents within the agreed envelope accepted end to end |
| B6 | backup and restore drill passed within the last wave |
| B7 | deploy bound to the gate; version endpoint reports the tagged version; release history shows `v0.3.0` onward |
| B8 | exposure review: nothing reachable that the owner did not decide to expose (`R-29` clause 2) |
| B9 | contract `1.0.0` and error catalog frozen |
| B10 | 2–3 expert smoke sessions completed with no blocking finding |
| B11 | if beta users are external: licensing (NORM-Q04), retention (`U-04`) and registration mail (P-2) decided |

Beta → RC: all 15 sections, both optimisations, comparison and Диспетчер delivered and validated
by experts. RC → 1.0: hardening, no open blocking debt, release acceptance.

## 10. Owner answers — poll of 2026-10-05/06

Recorded as given. Each needs a ruling number from the integrator before the wave that builds it
freezes; numbers are deliberately not taken here.

### 10.1 Оптимизация (rounds 1–2)

| # | Question | Answer |
|---|---|---|
| A-1 | which legacy functions enter the product | **all three**: project optimisation, section optimisation, model/stage configuration |
| A-2 | form of an optimisation proposal | **separate entity** beside findings, with its own expert decisions, export and counts |
| A-3 | vendor list | **global list per section kept by an administrator (seeded from legacy), overridable by a project's own list**; a run records the list version it used |
| A-4 | money figures | **only from uploaded prices**; no price, no figure |
| A-5 | first price source | **Excel/CSV price list attached to a project** (position, manufacturer, mark, unit, price, date); a figure only for matched positions |
| A-6 | navigation | **split by meaning**: project optimisation is a project tab «Оптимизация» and section optimisation is «Оптимизация разделов» under **Работа**; model/stage configuration is **Система → Настройки анализа**. *This amends P-11 (`W50-PLAN.md` §3.1), where «Оптимизация» sits under Система.* |
| A-7 | order | **by readiness**: Настройки анализа with АР (W55; the wave map places it in W56 with AR-2); Оптимизация проекта right after beta on АР (W59); Оптимизация разделов after the sections (W62) |
| A-8 | who changes model configuration | **an administrator keeps presets (global and per section); an expert picks an allowed preset when starting a run**; the run records the exact configuration |

### 10.2 What the answers change in plans already written

- **Accepted by the W48–W51 integrator on 2026-10-06** for W50-FREEZE-01, under its own new ruling: Работа = Проекты, Дашборд, «Оптимизация разделов» (stub); Знания = База знаний, Блоки, «Нормы» (stub); Система = Журнал выполнения, Исполнители, «Настройки анализа» (stub), «Очередь» (stub); project «Оптимизация» becomes a project tab, the existing `/optimisation` screen stays reachable until W59. State then: W48 closed locally at `23e0579` (`GATE OK`, not yet on `origin/dev`); W49 running on `integration/w49`, migration head `0015_accounts_roles_registration`; next free ruling `R-62`.
- **`W50-PLAN.md` §3.1 (P-11):** «Оптимизация» leaves Система; Работа gains «Оптимизация
  разделов», Система gains «Настройки анализа» and «Очередь», Знания gains «Нормы». Under `R-23`'s
  rule (structure first, honest stubs) W50 can place these as stubs now; otherwise W53–W62 move
  navigation entries one by one.
- **W52 scope** grows by a second track: the versioning system of §8 and the adopted tools
  (A4, A5, A6). The `D-110` refusal proposed by revision 1 for W52 is dropped (S-6).
- **Contract in W58:** `PS` added, five names changed, stage attribute on the version — one
  reseal and one `CHECK` migration.

### 10.3 Sections (rounds 3–4)

| # | Question | Answer |
|---|---|---|
| S-1 | classification system | **flat list as in legacy, plus a separate stage attribute П/Р on the version** |
| S-2 | ПЗ and ПБ | **both: 15 sections** — add `PS` «Пояснительная записка» (legacy profile exists), keep `PB` (profile written from scratch) |
| S-3 | names | **legacy names**: АИ «Архитектурные решения (интерьер)», ОВ «Отопление, вентиляция и кондиционирование», ЭОМ «Электроснабжение и электрооборудование», ПТ «Противопожарный водопровод», ПОС «Проект организации строительства» |
| S-4 | how a document gets its section (`D-107`) | **suggested from file name and text keywords (legacy patterns), confirmed by the expert; analysis does not start without a confirmed section** |
| S-5 | order after АР | **cheap first**: АИ → ПЗ, ПОС, ТХ → КЖ, КМ → ОВ, ВК, ПТ → ЭОМ, СС, ИТП → ГП → ПБ |
| S-6 | non-АР documents before their profiles (`D-110`) | **unchanged until the section framework** (W59); today uploads carry no section anyway |

### 10.4 Comparison (rounds 4–5)

| # | Question | Answer |
|---|---|---|
| C-1 | what is compared | **all three**: stages П and Р of one object; versions of one set; runs of one version (kept) |
| C-2 | depth for documents | **text + AI summary**: sheet pairing, deterministic text differences as evidence, AI classification and summary on top; AI never alters the raw differences |
| C-3 | when | **second track during beta**: versions and carryover first (W59), stages П/Р second (W62) |
| C-4 | decision carryover | **with confirmation**: a matched finding is offered its previous decision marked «из версии N»; the expert confirms singly or in bulk; fixed findings are marked resolved |

### 10.5 Screens of `R-23` missing from revision 1 (round 5)

| # | Screen | Answer |
|---|---|---|
| Q-1 | Очередь | **with Исполнители**: queue tab in Система (enqueue, priority, pause, cancel), built with the job queue (W53) |
| Q-2 | Диспетчер and График работ | **Диспетчер in beta** (assign project/document to an expert, statuses, «мои задачи»; W61); **График работ after 1.0** (`1.1.0`) |

### 10.6 Versioning (round 6)

| # | Question | Answer |
|---|---|---|
| V-1 | numbering | **SemVer** |
| V-2 | how descriptions reach the database | **repository → database at deploy** |
| V-3 | what a release is | **a deploy with user-visible changes** |
| V-4 | where users see it | **panel + update banner + «Что нового» once after an update**, read mark per user |

### 10.7 Versioning (round 7)

| # | Question | Answer |
|---|---|---|
| V-5 | item form | **kind / where / what now, `where` starting from the screen registry** |
| V-6 | editing a published entry | **only by a new revision**; history kept |
| V-7 | technical journal | **two layers**: Russian user notes in the database, English technical record in the repository |
| V-8 | truthfulness | **form test in the gate + an independent judge against the diff** |

### 10.8 Versioning and plan (round 8)

| # | Question | Answer |
|---|---|---|
| V-9 | when | **everything in W52** |
| V-10 | where history starts | **`v0.3.0` plus one archive entry** for `0.1–0.2`, each claim judged against the code |
| P-1 | scenario | **C — two tracks + measures** |
| P-2 | measures | **adopted:** process without idle hand-offs (A2, A3, A4), tools (A5, A6, A9, A12), legacy profiles as data (A8). **Not adopted:** deployment and budget (A7, A10, A11) |

The owner's framing of the EstiMat material: *good practices to consider, not truth* — §8.3 takes
the typed entries, the form test with its self-test, the judge and the banner, and replaces the
bundled file with database storage as the owner asked.

### 10.9 Still open — needed before the named wave

| Pack | Needed before | Decisions |
|---|---|---|
| 2 | — | **answered**: D-2.4 by G-1 (§10.13); D-2.1, D-2.2, D-2.3 and D-2.5 in §10.10 |
| 3 | W56 | D-3.1 answered by F-7 (one real set, not anonymised; anonymisation registered); D-3.3 answered by G-2 and G-4 (portal bundles, 500 pages / 250 MiB); D-3.4 answered by H-5 for now (no regression; beta thresholds at W58); **open:** D-3.2 named experts with slots (`OD-18`, before W58); the drawing-analysis budget and the W56b poll pack (after the W54 vision probe, G-3) |
| 4 | W58 | D-4.1 beta users internal or external (with NORM-Q04, `U-04`, SMTP) |
| — | W57 | **answered** by I-1…I-12 (§10.15); run-time query embedding on the stand is not needed for W57 (I-2) — D-2.4's stand-capacity question stays open only for semantic retrieval from document text, which no wave plans |
| — | W52 freeze | R-71…R-74 recorded by `W52-RULE-01`; W50 already absorbed the P-11 navigation amendment (A-6). Current-tree grant and pin sweep remain for `W52-FREEZE-01`. |

### 10.10 Second poll (2026-10-06): W52 and pack 2

| # | Question | Answer |
|---|---|---|
| W-1 | binding deploy to the gate (`D-120`) | **accept the risk and close `D-120`**: only the integrator pushes `main`, after literal `GATE OK` on the exact SHA and the owner's instruction |
| W-2 | depth of the W52 quality track | **audit + attack + debts** |
| W-3 | online vulnerability and licence scanners (`D-122`) | **not now** — moved to RC hardening (W64) |
| W-4 | budget for the 121 corpus repairs (W54) | **up to $10**, a one-time exception to `R-29` for that run only; price still measured by dry-run first |
| D-2.1 | MinIO (`D-119`) | **upgrade to the 2025-10-15 security release** after inventory and backup (`D-123`) and a rehearsal on a copy; **replacement after 1.0** |
| D-2.2 | Blob identity | **content-derived Blob + an immutable binding per admission**; NORM-Q05's wording is clarified, the storage model is unchanged |
| D-2.4 | where to build embeddings | **open**: the owner checks the stand's capacity and load first; this machine is available only in 3–4 days and at lower overall load |
| D-2.5 | backup target | **this machine until after beta** (cheap while real data is small); then encrypted off-stand storage or another option, decided with the storage questions later |

The W52 plan built on these answers is `docs/program/dispatch/W52-PLAN.md`.

### 10.11 W53 poll (2026-10-06)

| # | Question | Answer |
|---|---|---|
| E-1 | who controls the queue (cancel, retry, priority, pause) | **all administrator**; experts start runs; everyone signed in reads the queue and journal |
| E-2 | automatic retry of provider calls | **only provably safe**: no connection established, or an explicit 429/503; an ambiguous failure ends the run `outcome_unknown` and nothing is re-spent automatically |
| E-3 | how backups reach this machine | **this machine pulls over SSH** with a dedicated key the owner installs on the stand, restricted by a forced command to backup and read |
| E-4 | how many backups to keep here | **one latest verified copy**; the previous one is deleted only after the new one verifies |

Follow-up poll the same day, after the first judging round of `W53-PLAN.md` showed that a failed
run is never reopened (so «Повторить» is a re-audit creating a new run), that cancel is a product
mutation as well, and that roles are any-of:

| # | Question | Answer |
|---|---|---|
| E-5 | may an administrator-only account cancel runs and start a re-audit (`R-60`) | **experts and administrators both** may cancel and re-audit — a narrow exception to `R-60` for these two actions; priority and pause stay administrator-only |
| E-6 | equal bytes in the corpus and in a project | **roles live on bindings; equal bytes are stored once and reused** — the storage rule "one role per object" is replaced |
| E-7 | retry and timeout numbers (OQ-04) | **as proposed**: provider 3 tries, 2 s / 8 s, `Retry-After` ≤ 60 s; a Job at most 3 Attempts, then `dead_letter`; lease 60 s, heartbeat 20 s; custody 5 tries (30 s … 2 h), then `poisoned` |
| E-8 | 503 from the provider path | **retry only the proxy's own 503 envelope**; any other 503 is `outcome_unknown` |

### 10.12 W54 polls (2026-10-06)

| # | Question | Answer |
|---|---|---|
| F-1 | W54 does not fit one wave | **W54 is the foundation, W55 the stand and AR-1**: corpus pipeline built and rehearsed here ∥ worker service, «Исполнители», probes; W55 imports the corpus and builds AR-1 |
| F-2 | how the corpus reaches the stand | **a verified bundle, a second forced-command key for inbound transfer, a one-shot importer**; a transient non-serving copy recorded as an `ADR-0020` addendum |
| F-3 | where the paid repairs run | **here, before the bundle is built**, with the proxy credential in a local file outside the repository; price measured on a sample first |
| F-4 | pages still degenerate after two attempts | **loaded and flagged unreliable**, excluded from search and citations, listed for manual review |
| F-5 | external OCR in the alpha | **the portal "vibe" used by legacy** |
| F-6 | what OCR does | **segmentation into blocks, text of scanned pages, crops**; its text is marked as recognised and is never text-layer evidence |
| F-7 | real АР documents | **the one real set plus synthetic fixtures** — quality on real documents stays unmeasured before beta (risk R-1, R-4) |
| F-8 | worker service credentials | **as the API's**; least-privilege roles for both are a debt before external beta users |
| F-9 | how the portal's output enters the product | **the portal's ZIP upload now** (PDF, blocks, recognised text; crops cut locally), **the portal API later** when its team provides one |
| F-10 | the host is shared and loaded (load 25–37, ≈ 1 GB free memory at times) | **night windows will be provided**: heavy steps (image builds, corpus loads, the repair run, bundle export, rehearsals, a local embedding build) are scheduled into them |

### 10.13 W55 polls (2026-10-06)

| # | Question | Answer |
|---|---|---|
| G-1 | where the embeddings are built (D-2.4) | **here, in night windows**: resumable, streaming; the bundle ships with the build |
| G-2 | envelope limits for a project document | **up to 500 pages and 250 MiB** |
| G-3 | the budget for drawing analysis by a vision model | **decided after the W54 vision probe** (cost per crop measured there) |
| G-4 | what the upload accepts | **only the portal bundle** (PDF, `_blocks.json`, `_results.md`, optional `_results.html`); a bare PDF is refused with a message saying how to obtain the bundle |
| G-5 | search on «Нормы» | **text search now** — PostgreSQL full text with Russian morphology plus document and clause-number lookup; **semantic retrieval is for analysis** (W57, the BGE worker inside a Job) |
| G-6 | which norms snapshot a run uses | **the current one, designated by an administrator**; only a snapshot with a complete embedding build qualifies; the run records it and shows it in its status |
| G-7 | the portal model's descriptions of IMAGE blocks | **not used in analysis**; stored and shown in «Блоки» marked «описание портала» |
| G-8 | where `block_analysis` goes | **W56, together with AR-2**; the wave count is unchanged |

Follow-up poll the same day, after the first judging round of `W55-PLAN.md`:

| # | Question | Answer |
|---|---|---|
| G-9 | one wave or two | **split**: W55a (corpus, search, «Нормы») and W55b (portal bundles, «Блоки»), each with its own freeze, judges and release; W55a first by default, the order checked at W55a's freeze by which inputs are ready |
| G-10 | the portal's `<stem>_stamp_audit.json`, present in every corpus bundle | **accept and store** as a version input; not used in analysis; any other extra member is refused |
| G-11 | 500 pages vs a text analysis that sends the whole text in one call | **accept up to 500 pages; analysis up to an input budget** (≈ 50 pages of text, the number fixed at the freeze from the model and the $1 ceiling), refused up front with a clear reason; chunked analysis in W56 |
| G-12 | executor capacity (A13) | **measure first**: the per-lane memory peak is measured during W55; the owner then decides on a host or memory |

The W55 plan built on these answers is `docs/program/dispatch/W55-PLAN.md`.

### 10.14 W56 polls (2026-10-06)

| # | Question | Answer |
|---|---|---|
| H-1 | W56 is ≈ 100–120 h | **two waves, text first**: W56a AR-2 on text; W56b drawings, region evidence, chunking and «Настройки анализа» |
| H-2 | categories of profile v2 | **without norms now**: v1's two plus dimensions, layout, facade, roof, documentation as consistency and completeness questions; norm categories with `norm_verification` in W57 |
| H-3 | severity | **legacy's five levels; the model proposes, the expert decides** in the decision; exports carry the expert's level with the proposal beside it |
| H-4 | merge and critic | **deterministic merge; the critic only assesses** — shown beside the finding, never hides or changes it |
| H-5 | quality thresholds (D-3.4) | **"no worse than the measured baseline" now**, on recorded responses in the gate; beta thresholds set by the owner at W58 from measured figures |
| H-6 | the gateway answers with another model | **refuse on mismatch** — a typed stage failure, no silent substitution; live recordings only after the model is verified |
| H-7 | recognised (OCR) text in W56a | **context now, citations from OCR in W56b** with region evidence |
| H-8 | labelling real documents | **the owner reviews v2's output in the product** (accept or reject per finding) — a precision figure, not a gate |
| H-9 | live spend in W56a | **within $5 (`R-29`)**; a projection above it stops for the owner |

Follow-up the same day, after the first judging round of `W56-PLAN.md` showed that the critic is a second
paid stage W53's single-call execution model does not cover, that FS-04 makes a run with a failed optional
stage `partial`, and that the critic takes a large share of the $5:

| # | Question | Answer |
|---|---|---|
| H-10 | where the critic goes | **W56b**, together with the multi-call resume it needs; it then assesses text and drawing findings alike |

The W56 plan built on these answers is `docs/program/dispatch/W56-PLAN.md`.

### 10.15 W57 polls (2026-10-07)

Asked by the planning session `pdf-analysis-e6`: I-1…I-8 after the research digest
(`reviews/W57-RESEARCH.md`), I-9…I-12 after the plan's first judging round
(`reviews/W57-PLAN-JUDGING.md`); answers, not rulings — `W57A-RULE-01` and `W57B-RULE-01` number them.

| # | Question | Answer |
|---|---|---|
| I-1 | how norm verification is built | **in the same analysis call, then a deterministic check**: the analysis receives the norm paragraphs selected for the checklist and proposes a finding with a citation (document, clause, verbatim quote); a step without a model checks that the paragraph exists in the pinned snapshot and the quote is verbatim; an unconfirmed citation is not published. One paid call per run; no dependency on W56b's multi-call resume |
| I-2 | how norms are selected | **a checklist map**: each АР checklist item mapped to documents and clauses (ported from legacy and checked, since part of its clause numbers are phantom); query vectors for the items built here in advance with the pinned BGE image; at run time SQL only — exact clause lookup plus pgvector; **no BGE on the stand** |
| I-3 | the norms the project itself cites (`normative_refs`) | **by the corpus only**, without a model: "in the corpus" / "a newer edition in the corpus: …" / "not in the corpus"; no claim of "cancelled" or "replaced", because the corpus holds no document status |
| I-4 | which normative categories | **all seven**: evacuation, fire safety, accessibility, thermal protection, insolation, sound insulation, plus `normative_refs`; each checked as "the values the document states against the norm's thresholds", with no independent calculation |
| I-5 | a citation that fails the check | **the quote decides**: a quote found verbatim in another clause of the same document rebinds the citation to that clause without a model; a quote found nowhere in the document withholds the finding — counted in the evaluation and shown in the run's summary as withheld, never shown to the expert |
| I-6 | which edition applies when the corpus holds several | **the newest in the pinned snapshot**; a project citing an older edition gets a separate `normative_refs` finding, and the expert decides |
| I-7 | Excel | **legacy's layout, export only**: «Сводка» (counts by the five severities) and a findings sheet — № \| Лист/стр. \| Категория \| Замечание \| Рекомендация \| Серьёзность (the expert's decision and the model's proposal) \| Норма (document, clause) \| Цитата нормы \| Решение эксперта \| Комментарий; merged members as «также найдено» rows; no re-import; the CSV stays as it is |
| I-8 | who checks the checklist map | **an automatic check plus the owner's review**: every mapped clause must exist in the snapshot or the row is dropped; the lane's report shows each checklist item beside its clause texts; the owner reviews the list once (≈ 25 rows) before the map enters the profile |
| I-9 | W57 at ≈ 85–95 h (the judges' estimate after round 1) | **two waves**: W57a — the map, the retrieval set, profile v3, citations, screens; W57b — the project's own references and Excel; each with its own freeze, judges and release |
| I-10 | live spend | **$5 (`R-29`) per half**; the expensive recordings fall in W57a; a re-record after FIX is a stop for the owner when the projection passes $5 |
| I-11 | norm text in the repository | **allowed — the repository is internal**: fragments of norms (quotes in recordings, paragraph texts in test fixtures) are committed with their source attribution |
| I-12 | W56b or W57 first | **W57 first**: W57a and W57b follow W56a; W56b is planned after the W54 vision probe and follows W57b; releases W57a `v0.8.0`, W57b `v0.8.1`, W56b `v0.9.0` |

The W57 plan built on these answers is `docs/program/dispatch/W57-PLAN.md`.

## 11. Risks

| # | Risk | Effect | Mitigation |
|---|---|---|---|
| R-1 | АР quality iteration is open-ended | AR-2/AR-3 repeat | thresholds set in advance (D-3.4); harness as gate (A9) |
| R-2 | real АР sets carry raster drawing sheets whose content the text layer does not hold (11 of 30 pages of the one real set) | the analysis is blind to them | F-5, F-6, F-9: the portal's OCR bundle in W55; the W54 probes measure it |
| R-3 | vision cost on real sets under `R-29` | a stop for the owner in W56–W57 (G-3, G-8) and in every section wave | ask the spending question at the start of each such wave, not mid-run |
| R-4 | experts unavailable | beta gate slips by calendar | ask now (D-3.2) |
| R-5 | host capacity: corpus, crops, embeddings, backups, worker pool | promotion fails late | measured in W53 before any write |
| R-6 | governance overhead keeps growing | scenario C degrades towards A | A2–A4 adopted |
| R-7 | single executor on a shared host | two-track waves serialise — **observed** in the W53–W55 plans (§6.2) | A13 (executor capacity); A14 (split a wave into two releases) |
| R-8 | the A-6 navigation amendment misses the W50 freeze | W50 ships «Оптимизация» under Система and W55 moves it again | hand to the integrator now |

## 12. Not decided here

No ruling number is taken (`R-53`…`R-61` are provisional in `IDENTITY-WAVES.md` §4); no task file
is written; no contract, migration or code changes; nothing in `CURRENT_STATE.md`,
`DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md` or any `integration/*` branch is
touched.
