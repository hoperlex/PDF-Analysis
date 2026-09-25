# W45-BLOCKS — the block markup a reviewer can open

**task_id:** `W45-BLOCKS` · **wave:** 45, sub-stage A · **lane:** `gate-w45a`
**worktree:** `/root/w45pos` · **branch:** `agent/w45-pos`

`R-23` asked for `/blocks`: *«постраничная разметка документа, векторный граф блока»*. Wave 43
gave it an address and an honest stub. **This wave gives it the half that exists.**

Read `docs/program/dispatch/WAVE_PLAN_45_48.md` §W45 first.

## What is already measured, and what you must re-measure

**Measured by `W43-PREP` and by the integrator, and the first two were wrong in a register row
before somebody checked them — so check all four yourself:**

1. `src/auditmanager/analysis/stages/page_geometry_extraction.py:226` writes a real
   `bbox {x0,y0,x1,y1}` in points, **top-left origin, one per text line**, with `bbox_unit` and
   `bbox_origin` beside it.
2. That stage publishes **two** artifacts to the blob store: `ROLE_BLOCK_INDEX`, carrying
   `blocks` and `text_layer_sha256`, and `ROLE_PAGE_CROPS` — **which is published EMPTY,
   `crops=[]`.** That is not a defect to repair; it is a fact your screen must not paper over.
3. **The stage carries no adapter, no model and no provider reference**, so it produces both
   artifacts in `recorded` mode exactly as in `live`. **`D-70` does not block you.**
4. The only block-shaped field on the contract surface today is `Evidence.block_id`, which the
   contract itself calls *"Not a contract identifier"*.

**The legacy corpus is a different thing and is not your subject:** its 28 249 blocks carry
`coords_norm = [0,0,1,1]` and `polygon_points = null`. *The corpus has no geometry; this
pipeline produces it.* A register row once inferred the second from the first and was wrong.

## B1 — one operation, one reseal

**A reseal is four documents in one change** (`D-18`): `contracts/api/v1/openapi.json`, the
regenerated client in `web/src/shared/api/generated/`, the mirror `web/openapi/openapi.json`,
and the sha in `web/FRONTEND_LOCK.json` **written by hand**. Surface today: **15 paths / 18
operations / 51 schemas**. **The error catalog is 22 codes and frozen** — if you conclude you
need a new one, **stop and report**; that is a second reseal and the owner's.

The operation returns the block index for a published version. **Three things to decide and to
argue in your report, not to decide silently:**

- **What it is keyed by.** The artifact is produced by a run, but the geometry is a property of
  the *version*, not of the analysis. Say which you chose and why a reader can tell.
- **What it answers when no run has produced the artifact yet.** *Absent is not empty* — this
  programme has a whole guard family about that (`test_absent_and_empty_are_not_the_same_answer`).
- **What it does not return.** `crops` is empty; do not ship a field that is always `[]` without
  saying in the contract's own description that it is.

## B2 — the screen

`web/src/_pages/blocks/` is a `RoutePlaceholder` today. Make it show the page-by-page block
markup for a version a reviewer chooses.

**`R-39`, ruled 2026-09-24, governs what it may say:** a screen **may** state what the system
cannot do yet, in the words of the subject — *«векторный граф блока здесь пока не строится»* is
allowed and useful. **The prohibition that stays**: no operation ids, no field names, no
transport. *«операция X не отдаёт Y»* is for a comment.

**No invented numbers** (`R-23`'s addendum). A page with no blocks shows that it has none.

**Both instruments now reach every screen** — wave 44 derived the screen set from the route tree.
So your screen is rendered by the language guard and measured by the contrast census **without
you adding it to a list**, and `R-33`'s 3:1 border floor applies to whatever you draw. If you
find yourself editing `SEEDS` to make something pass, **that is a finding, not a step.**

## allowed_paths

```
contracts/api/v1/openapi.json
web/openapi/**
web/FRONTEND_LOCK.json
web/src/shared/api/generated/**
src/auditmanager/**
db/migrations/**        — only if the operation genuinely needs one; argue it
tests/**                (NOT tests/e2e/**, which nobody owns this wave — report, do not edit)
web/src/**
web/tests/**
docs/program/W45-BLOCKS.md
```

## forbidden_hotspots

`infra/**` and `.dockerignore` and `tests/contract/api_v1/**` — **`W45-READY` owns them**, live
in `/root/w45rdy` · `contracts/domain/v1/error-codes.json` · `docs/program/DEBT_REGISTER.md` ·
`docs/program/dispatch/**` · `Makefile` · `package.json` · any container not named `gate-w45a*` ·
**the owner's stand `auditmanager-w19a` is read-only to you.**

**`tests/e2e/pc01/journey/manifest.json` is the integrator's** — `D-89`. You add no address, so
you should not need it; if you do, say so and stop.

## Deliverables

1. The operation and the screen, committed step by step. **The reseal is one commit.**
2. `docs/program/W45-BLOCKS.md`, opened **before** the first measurement.
3. Every new guard **shown failing**, with the mutation and the failing assertion quoted.
4. A plain statement of **what the screen shows and what it does not**, and how a reviewer can
   tell the difference on the screen itself.
5. Anything outside the grant: reported, not repaired.

## Verification

Lane `gate-w45a` — PostgreSQL `127.0.0.1:56330`, S3 `59930`/`59931`. Provision, then
`make gate > /root/w45a-gate.log 2>&1` and read the verdict **from the `GATE OK` line in the
log**. `alpha-w44`: battery **2466**, foundation **35**, frontend **1110 in 78 files**.

## Discipline

Commit each step. Do not tag, push or merge.
