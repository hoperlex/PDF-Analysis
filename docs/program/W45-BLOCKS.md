# W45-BLOCKS — working log

**task_id:** `W45-BLOCKS` · lane `gate-w45a` · worktree `/root/w45pos` · branch `agent/w45-pos`

Opened before the reseal edit, per the dispatch's deliverable #2. Provisioning and the
four re-measured premises are below; everything after "## B1" is written as the work
lands, each entry dated and each claim carrying the command that produced it.

## Provisioning (2026-09-25)

```
make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12   -> bootstrap OK
.venv/bin/python -c "import boto3; print(boto3.__version__)"  -> boto3 OK 1.43.90
npm --prefix web ci                                      -> added 184 packages
```

`.env` for this lane: PostgreSQL `127.0.0.1:56330` (`audit_w45a`), S3
`127.0.0.1:59930`/`59931` (`audit-w45a`) — matches the dispatch's `gate-w45a` lane.

## The four premises, re-measured rather than trusted

1. **`page_geometry_extraction.py:226`** (`_build_blocks`) writes `bbox {x0,y0,x1,y1}`
   in points, top-left origin, one block per extracted text line, with `bbox_unit`
   (`"pt"`) and `bbox_origin` (`"top_left"`) beside it, both module-level constants.
   Read directly from the file. **True as stated.**
2. **Two artifacts are published**, both in `run()`: `ROLE_BLOCK_INDEX` carries
   `blocks` and `text_layer_sha256`; `ROLE_PAGE_CROPS` carries `crop_policy: "none"`
   and `crops: []`, unconditionally — the call site passes a literal `[]`, not a
   computed one. The module docstring and `CROP_POLICY` both say this is `OD-04`'s
   declared decision, not a gap. **True as stated.**
3. **No adapter, no model, no provider reference.** `contracts/analysis/v1/stage-registry.json`
   declares this stage's `execution.model_routed: false`, and nothing in
   `page_geometry_extraction.py` imports `auditmanager.analysis.text` or takes an
   `adapter` argument. **True as stated — `D-70` (the owner's stub-with-no-host
   blocker) does not apply to this stage.**
4. **The only block-shaped field on today's contract surface is `Evidence.block_id`.**
   Read from `contracts/api/v1/openapi.json` `components.schemas.Evidence`: its
   description is verbatim *"Secondary anchor into this version's block index. Not a
   contract identifier."* **True as stated.** No other schema in the frozen document
   mentions a block, a bbox or page geometry.

Surface measured independently before any edit:
`python3 -c "..."` over `contracts/api/v1/openapi.json` → **15 paths / 18 operations /
51 schemas**, matching the dispatch and `WAVE_PLAN_45_48.md`.

## B1 — the operation: three decisions, argued

**Keyed by `version_uid`, not by `run_id`.** `GET /versions/{version_uid}/blocks`,
grouped with `getDocumentVersion` / `streamDocumentVersionContent` / `listRuns`. The
stage that produces this geometry carries no model and no adapter (premise 3), so its
output is a deterministic re-derivation from the immutable source bytes and the
published text layer — identical across every run of the same version that reaches
this stage successfully. Addressing it by run would ask a caller to already be holding
a `run_id` to read a fact about the *document*, and would make two successful runs of
one version disagree about their own geometry answer two different questions with the
same bytes. A reviewer tells the choice from the URL itself: it hangs off `/versions/`,
the same place `getDocumentVersion` and the content stream do, not off `/runs/`.

**Absent version vs. not-yet-produced artifact are two different answers, on the wire.**
`test_an_absent_parent_is_not_an_empty_page.py`'s sweep now covers this operation too
(it addresses a parent identity in its path) and requires `404 not_found` for a
`version_uid` that names nothing — enforced the same way as every other parented `GET`.
A version that exists but whose most recent successful run never reached
`page_geometry_extraction` — or has no run at all — answers `200` with
`status: "not_produced"` and `blocks: []`. A version whose geometry really was produced
and really has zero blocks (an edge case the stage does not refuse, but the fixture
corpus never exercises) would also answer `200` with `blocks: []`, distinguished from
the first case by `status: "produced"`. **The two `[]` answers are the same bytes for
`blocks` and different bytes for `status`** — that is the field a reviewer or a
downstream client reads to tell them apart; two dedicated integration tests assert
both directions.

**What the operation does not return.** It does not carry `crops` or `page_crops` at
all — not an empty array, no field. `ROLE_PAGE_CROPS` is a separate artifact
(premise 2) and this operation is declared, in its own `description`, as returning the
block index and nothing else; the description also states plainly that page crops are
published empty by this pipeline and are not exposed here, so a reader of the contract
sees the fact instead of inferring it from an absent field.

No new error code: the only refusal this operation adds is `not_found`, already in the
22-code catalog.

(Reseal bytes, counts, and the four-document commit are recorded below as they land.)

## B2 — the screen

(Written once B1 is committed.)
