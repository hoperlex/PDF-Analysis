# W43-PREP — four prepared sections, and what each one would have to show

**task_id:** `W43-PREP` · **wave:** 43, stage A · **lane:** `gate-w43b` · **branch:** `agent/w43-prep`
**base:** `b7d9bc4` · **ruling:** `OWNER_RULINGS_2026-09-17.md` §3.11, `R-23`'s same-day addendum

`R-23`'s addendum rules **blocks, optimisation, logs and workers** wanted, each wired up as its
vertical lands, with the front-end preparation allowed now. Preparation is four things: a place in
the navigation, a `RoutePlaceholder` carrying a real `promise`, **the data shape written down and
checked against the contract**, and no invented numbers.

This file is the third of those. It is opened before the first measurement and each claim carries
the command that produced it, because the next wave budgets against these notes and **a false note
is worse than no note** — `R-11` reverted a wave over a reseal discovered at its end.

## How to read a note

Each note says what the screen would show, then **field by field** where that field comes from:

- **on the surface** — a field of the 18-operation contract, named;
- **in the tree, not on the surface** — the application computes or stores it, and no operation
  returns it. Building the screen needs a **reseal**;
- **nowhere** — nothing in this system produces it. Building the screen needs the vertical first.

Everything below was re-measured at `b7d9bc4`, in this branch's worktree, before the first gate
run. Nothing is copied from the brief; where a measurement disagrees with the brief, the note says
so.

**Where to run the corpus commands.** The norms corpus is **not in the repository and not in a
worktree**: `.local/` is git-ignored, so `git worktree add` does not carry it. It lives once, in
the original clone, at `/root/projects/PDF-Analysis/.local/norms/corpus/`, and
`corpus/MANIFEST.json` orients. Anyone re-measuring note 1 from a worktree must `cd` there first
or they will measure an empty glob and read the silence as agreement.

## The frozen inputs every note is measured against

| input | value | command |
|---|---|---|
| contract surface | **15 paths / 18 operations / 51 schemas** | `python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print(len(d['paths']),sum(1 for p in d['paths'].values() for m in p if m in ('get','post','put','patch','delete')),len(d['components']['schemas']))"` |
| corpus | **674 documents / 28 249 blocks** | `python3 -c "import json;print(json.load(open('.local/norms/corpus/MANIFEST.json'))['summary']['totals'])"` |
| PC-01 stages | **4 scheduled**, of 9 canonical | `sed -n '50,59p' src/auditmanager/runs/repository.py` |

---

## Note 1 — Блоки (`/blocks`)

**What the screen would show.** Page-level block markup: for one published version, the blocks the
analysis derived, each on its page, and a vector graph per block so a reviewer sees the shape that
was read rather than only the text that came out of it.

| field the screen needs | where it comes from |
|---|---|
| block identity | **in the tree, not on the surface.** `geometry.block_index` carries `block_id` as `b_000001`. The only block-shaped field on the whole surface is `Evidence.block_id`, and the contract says of it: *"Secondary anchor into this version's block index. Not a contract identifier."* |
| page number | **in the tree, not on the surface** for a block; `Evidence.page_number` exists but is a property of a quotation, not of a block. |
| block rectangle | **in the tree, not on the surface.** `page_geometry_extraction` writes `bbox {x0, y0, x1, y1}` with `bbox_unit = "pt"` and `bbox_origin = "top_left"`. No contract schema carries a bbox, a coordinate, a width or a height. |
| block polygon (the vector graph) | **nowhere.** Nothing in this system produces a polygon. |
| page size to scale a drawing against | **nowhere on the surface.** `streamDocumentVersionContent` streams the PDF bytes; no operation states a page's dimensions. |
| a list of a version's blocks | **nowhere.** No operation lists blocks. A blocks screen is a new operation, i.e. a reseal. |

**The brief's premise, checked and corrected.** The brief says *"The corpus has `coords_norm =
[0,0,1,1]` on all 28 249 blocks and `polygon_points` empty. There is no geometry to draw."* Measured
over the corpus itself, the first half is exactly right and the second is right in substance and
imprecise in form — and the conclusion does **not** transfer to our own pipeline:

- every one of the **28 249** blocks has `coords_norm == [0.0, 0.0, 1.0, 1.0]` — one distinct value
  across the whole corpus, i.e. every block is the whole page;
- `polygon_points` is **`null` on all 28 249**, not an empty list. Nothing reads it today, but a
  screen written against `[]` and served `null` is a defect, so the form is recorded;
- `shape_type` is `rectangle` and `block_type` is `text` on all 28 249 — one value each;
- **but our own `page_geometry_extraction` produces real rectangles**, one per text line, with
  `x0/y0/x1/y1` in points. So *"there is no geometry to draw"* is true of the legacy corpus and
  **false of this application's block index**. What is missing is not the geometry; it is any
  operation that returns it.

**The reseal this implies.** A blocks screen needs at least one new operation returning a version's
blocks with their rectangles, plus a page-dimension field to scale them. The polygon stays
unbuildable until something produces one. Blocks are also outside PC-01 by profile: `block_analysis`
is one of the 9 canonical stage ids and is not among the 4 PC-01 schedules, and
`PROTOTYPE_PROFILE.md` §7.2 defers *"visual finding detection, block-analysis…"*.

**Commands.**

```bash
# the corpus, all 674 documents, blocks read individually rather than from the manifest summary
python3 - <<'PY'
import json, glob, collections
coords, poly, shape, btype, total = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter(), 0
for f in sorted(glob.glob('.local/norms/corpus/*/blocks.json')):
    for b in json.load(open(f))['blocks']:
        total += 1
        coords[json.dumps(b.get('coords_norm'))] += 1
        pp = b.get('polygon_points')
        poly['null' if pp is None else ('empty-list' if pp == [] else 'nonempty')] += 1
        shape[b.get('shape_type')] += 1
        btype[b.get('block_type')] += 1
print(total, dict(coords), dict(poly), dict(shape), dict(btype))
PY
# -> 28249 {'[0.0, 0.0, 1.0, 1.0]': 28249} {'null': 28249} {'rectangle': 28249} {'text': 28249}

# the contract: no geometry anywhere on the surface
grep -oiE '"(bbox|coords_norm|polygon_points|x0|y0|x1|y1|width_px|height_px)"' contracts/api/v1/openapi.json | sort -u
# -> (no output)

# what the tree does produce
sed -n '220,236p' src/auditmanager/analysis/stages/page_geometry_extraction.py
grep -n 'BBOX_UNIT\|BBOX_ORIGIN' src/auditmanager/analysis/stages/page_geometry_extraction.py
# -> BBOX_UNIT = "pt", BBOX_ORIGIN = "top_left"

# the one block-shaped field on the surface, and what the contract says it is not
python3 -c "import json;print(json.load(open('contracts/api/v1/openapi.json'))['components']['schemas']['Evidence']['properties']['block_id'])"
```

---

## Note 2 — Оптимизация (`/optimisation`)

**What the screen would show.** Tuning: which models and which stages are applied, and the same
choice made per section rather than once for the whole installation.

| field the screen needs | where it comes from |
|---|---|
| which analysis profile a run used | **on the surface, read-only.** `RunStatus.analysis_profile_id`. |
| which prompt bundle a run used | **on the surface, read-only.** `RunStatus.prompt_bundle_id`. |
| live or recorded provider | **on the surface, and settable.** `RunStatus.provider_mode`, and `StartRunRequest.provider_mode` — the only tunable input the surface has. |
| the stages a run ran, and their outcome | **on the surface.** `RunStatus.stages[]` is `StageState {stage_id, stage_version, status, error_code, started_at, finished_at}`. |
| **choosing** a profile, a bundle or a model | **nowhere.** `StartRunRequest` has exactly two properties, `version_uid` and `provider_mode`, and `additionalProperties: false`. No operation writes a profile, a bundle, a model name or a parameter. |
| a section to tune per | **nowhere.** There is no section field anywhere in the data; `D-56` measured this and `R-25` rules the section structure rendered without counts for the same reason. |
| the catalogue of things that could be tuned | **nowhere.** `contracts/optimization/` **does not exist in this tree**, although `CP00_ARCHITECTURE_REVIEW.md` `DV-11` names `contracts/optimization/v1/**` as the carrier for the capability. |

**The brief's premise, checked.** *"We have one visible analysis stage against legacy's
seventeen."* Both halves hold, and both need one qualification each:

- **Ours.** `PC01_STAGES` schedules **four** stages — `source_preparation`,
  `page_geometry_extraction`, `document_context_build`, `text_analysis` — and all four are visible
  to a reviewer in `RunStatus.stages`. Exactly **one** of them, `text_analysis`, is an analysis
  stage; `PROTOTYPE_PROFILE.md` §7.1 calls it *"One visible AI stage… supported by three
  deterministic preparation stages"*. So the honest form is **one analysis stage among four
  scheduled**, out of **nine** canonical stage ids in the registry.
- **Legacy's seventeen.** `docs/LEGACY_TECHNICAL_INVENTORY.md` §"Pipeline stage directories
  observed" lists exactly 17 names. They are **directories observed in the legacy tree**, not a
  declared pipeline of 17 executed stages — the same document says legacy sequencing is described
  *"in multiple places"*, which is why this programme made the stage registry a contract.

**The reseal this implies.** A screen that only *reports* what a run used needs no reseal: both ids
and the stage list are already on the surface, and a read-only optimisation screen is buildable
today. A screen that lets anyone *change* them needs new write operations plus a vocabulary for
what is tunable — and `contracts/optimization/` is an empty seat, not a contract.

**Commands.**

```bash
python3 -c "import json;s=json.load(open('contracts/api/v1/openapi.json'))['components']['schemas'];print(s['StartRunRequest'])"
python3 -c "import json;s=json.load(open('contracts/api/v1/openapi.json'))['components']['schemas'];print(sorted(s['RunStatus']['properties']))"
python3 -c "import json;print([x['stage_id'] for x in json.load(open('contracts/analysis/v1/stage-registry.json'))['stages']])"
sed -n '50,59p' src/auditmanager/runs/repository.py          # PC01_STAGES, the four
sed -n '25,30p' docs/LEGACY_TECHNICAL_INVENTORY.md           # the seventeen legacy directories
ls contracts/                                                # -> analysis api comparison domain events README.md ; no optimization
```

---

## Note 3 — Журнал выполнения (`/logs`)

**What the screen would show.** An execution journal for a run: what the server did, when, and with
what outcome — the thing an operator reads when a run behaved oddly and the run screen's terminal
reason is not enough.

| field the screen needs | where it comes from |
|---|---|
| per-stage timing and outcome | **on the surface.** `StageState.started_at`, `finished_at`, `status`, `error_code` — a coarse journal already readable through `getRunStatus`. |
| why a run ended as it did | **on the surface.** `RunStatus.terminal_reason` and, since wave 42, `RunStatus.terminal_detail`. |
| provider calls: how many, costing what | **on the surface, aggregated only.** `RunStatus.model_call_count`, `cost_micros`, `cost_basis`. The individual calls are in the `model_call` table and no operation returns them. |
| an event stream for a run | **in the tree, not on the surface.** `contract_state_transition` and `command_record` are written by the application and no operation reads them. |
| a general audit trail | **partly nowhere.** An `audit_event` table exists in migration `0002_pc01_schema` and **nothing under `src/` writes to it or reads it** — its only writers in this repository are integration tests. |
| the server's own log lines | **nowhere on the surface.** Two modules call `logging.getLogger`; those lines go to the process's output and are readable only by whoever can read the container. |

**The brief's premise, checked and qualified.** *"It exists on the server; there is no contract
operation to read it."* The second half is exactly right: **none of the 18 operations reads a log.**
The word *journal* appears in the contract six times and every one of them is the **decision**
journal — `listDecisions`, `GET /decisions`, the expert's ledger — which is a record of what a
reviewer decided, not of what the server did. The operational plane outside `/api/v1` publishes
`/healthz` and `/readyz` and nothing else.

The first half needs the qualification above: what exists server-side is **per-stage results, model
calls, state transitions, command records and stdout logging**. The `audit_event` table that looks
most like an execution journal is **never written by the application**. A logs screen that promised
to show "everything the server recorded" would be promising a table that is empty in every
deployment.

**The reseal this implies.** At minimum one new operation reading a run's execution events, and
before that a decision about what is safe to publish: the contract's standing rule is that no
response ever contains *"a bucket name, object key, filesystem path, URL to internal storage,
credential, prompt or model payload"*, and raw log lines are exactly where those leak.

**Commands.**

```bash
# every operation on the surface; read the list, do not sample it
python3 - <<'PY'
import json
d = json.load(open('contracts/api/v1/openapi.json'))
ops = [(m.upper(), p, o['operationId'], o.get('summary','')) for p, i in d['paths'].items()
       for m, o in i.items() if m in ('get','post','put','patch','delete')]
print(len(ops))
for o in ops: print(*o, sep=' | ')
PY
# -> 18 operations; none reads a log

grep -c journal contracts/api/v1/openapi.json          # every hit is the DECISION journal
grep -rn 'audit_event' src/ | wc -l                    # -> 0 : the application never writes it
grep -rn 'audit_event' tests/ | head                   # its only writers are tests
grep -rn 'LIVENESS_PATH\|READINESS_PATH' src/auditmanager/api/health.py
```

---

## Note 4 — Исполнители (`/workers`)

**What the screen would show.** Distributed executors: which workers exist, what each is doing, and
how work is leased to them.

| field the screen needs | where it comes from |
|---|---|
| a worker identity | **nowhere.** No table, no schema, no field. |
| a job or an attempt | **nowhere.** There is no job table and no attempt table; `PROTOTYPE_PROFILE.md` §7.2 defers *"automatic retry/skip/resume policy, Job/Attempt lease, heartbeat, fencing and outbox"*. |
| a heartbeat or a lease | **nowhere.** Same exclusion. |
| which stage may run remotely | **on paper only.** `stage-registry.json` declares `execution_scopes` with `central_only` and `remote_eligible`, and says in the registry itself that this is *"a target statement, never a legacy parity claim"*. |
| what actually executes a run | **in the tree.** `runs/executor.py` runs the three deterministic stages and then the AI stage in order, in process, sequentially. |

**The brief's premise, checked.** *"Workers are excluded outright by `PROTOTYPE_PROFILE.md` §7."*
Confirmed, with the precise location: §7.2's **Deferred** list, which names both *"remote/distributed
workers"* and the whole `Job/Attempt` framework around them. The word in the document is *deferred*
rather than *excluded*, and the distinction matters for the promise this screen shows: the programme
has **not** decided to build workers, so this screen must not say one is coming.

**This is the one of the four that gets no promise**, because there is nothing the programme has
promised. Its placeholder says what is true — one sequential in-process executor, distributed
executors not part of the alpha — and says it without a date.

**The reseal this implies.** None, and that is the point: a workers screen is not blocked by the
contract, it is blocked by a decision nobody has taken.

**Commands.**

```bash
sed -n '/^Deferred:/,/^## 8/p' docs/program/PROTOTYPE_PROFILE.md   # the exclusion, verbatim
grep -rn 'execution_scopes' -A 3 contracts/analysis/v1/stage-registry.json | head -8
sed -n '648,672p' src/auditmanager/runs/executor.py                # the sequential in-process executor
grep -rhoE 'CREATE TABLE (IF NOT EXISTS )?[a-z_.]+' db/migrations/versions/*.py | sort -u
# -> 16 tables; none of them is a job, an attempt, a lease or a worker
```

---

## What the four notes cost, added up

| section | buildable today | needs a reseal | blocked by something other than the contract |
|---|---|---|---|
| Блоки | no | **yes** — a blocks listing with rectangles, and a page-dimension field | the polygon: nothing produces one |
| Оптимизация | a read-only view, yes | **yes**, for anything settable | no section field exists anywhere in the data |
| Журнал выполнения | no | **yes** — an execution-event reader, plus a decision on what is safe to publish | the `audit_event` table is never written |
| Исполнители | no | no | `PROTOTYPE_PROFILE.md` §7.2 defers the whole framework |

**Three reseals are visible here now rather than at the end of the wave that tries to build them.**
`R-24`'s integrator note already says the outstanding reseals should be batched — `D-56`'s
per-section verdict aggregation and `D-63`'s dashboard counts — and these three belong in that
batch. This wave takes none of them: **wave 43 changes no contract.**

## What preparation does not buy

None of the four verticals moved. `make gate` is not one step closer to any of them, and the
surface is the same 15 paths / 18 operations / 51 schemas it was at `b7d9bc4`. What preparation
buys is that the navigation is honest about the shape of the product, and that the four reseals
above are on paper before a wave budgets against them.
