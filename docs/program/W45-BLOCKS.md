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

**Landed as two commits**, `a49d047` (the Python implementation: `BlockPort`,
`BlockAdapter`, the router, the two view types, the two Pydantic models, the composition
wiring, the two composition guards this reseal's new parented `GET` requires updating)
and `830fd76` (the reseal itself: the four documents in one commit, following
`W42-SEAL`'s discipline). Surface: **16 paths / 19 operations / 53 schemas**, up from
15/18/51. No error code added. `FRONTEND_LOCK.json`'s six digests were recomputed with
`sha256sum` against this tree, not carried from the drift check's own report.

**Guard shown failing, then reverted.** `BlockAdapter.get_block_index`'s not-produced
branch was mutated to report `status=STATUS_PRODUCED` instead of `STATUS_NOT_PRODUCED`
(everything else held). `pytest tests/integration/composition/test_version_blocks_wire_shape.py
tests/integration/runs/test_w45_blocks_version_block_index.py`:

```
FAILED test_a_version_with_no_run_answers_not_produced_not_an_empty_blocks_array
AssertionError: {'version_uid': 'ver_01M3BPG7Y787CQK3Z3R3R4BXM0', 'status': 'produced',
'produced_by_run_id': None, 'text_layer_sha256': None, ...}
assert 'produced' == 'not_produced'
1 failed, 4 passed
```

Reverted; `5 passed` again. `git diff --stat` on the file after revert shows only the
legitimate additions.

**Forbidden-hotspot residue, reported rather than repaired.** `tests/contract/api_v1/
test_openapi_conformance.py` (forbidden; `W45-READY` owns `tests/contract/api_v1/**`)
carries its own hand-written literals that this reseal makes stale:

- `FROZEN_OPERATION_COUNT = 18` (line 89) → 19
- `FROZEN_SCHEMA_COUNT = 51` (line 90) → 53
- `FROZEN_OPERATIONS` (tuple starting line 102) needs
  `("GET", "/versions/{version_uid}/blocks", "getVersionBlocks")`
- `FROZEN_SCHEMA_NAMES` (frozenset starting line 135) needs `"VersionBlockIndex"` and
  `"BlockGeometry"`
- `TestN1ComponentReferenceResolution.test_changed_component_target_is_caught`
  (line ~588): `assert len(report) == 13` → 14 (`getVersionBlocks` is a fourteenth
  operation referencing `NotFound` → `ErrorEnvelope`)
- `TestN7EffectiveSecurity.test_security_moved_from_root_to_operation_is_invisible`
  self-heals once `FROZEN_OPERATION_COUNT` moves, since it derives from that constant.

Measured by running the suite read-only (never edited): `6 failed, 112 passed` before
this list; the two forbidden-file items above account for 5 of the 6, the sixth being
`test_surface_counts_in_prose.py`'s own report of `infra/deploy/**`'s residue, next.

**`infra/deploy/**` residue, also reported rather than repaired** (forbidden;
`W45-READY` owns `infra/**`). `infra/deploy/README.md` states "eighteen operations"
three times and `infra/deploy/serve.py` once; all four now understate the surface by
one. `src/auditmanager/api/**` and `web/src/**` were swept clean by this reseal
(`test_surface_counts_in_prose.py` passes for every source tree except `infra/deploy`
after this stream's edits).

## B2 — the screen

`web/src/_pages/blocks/ui/blocks-page.tsx` is no longer a `RoutePlaceholder`. `/blocks`
carries no route parameter, so "a version a reviewer chooses" is a three-step, in-page
picker built from existing entities: a project (`useProjectList`), one of its documents
(`useDocumentList` — `listDocuments` already answers one `DocumentVersion`, the current
version, per document, so no third "all versions" step is needed), then
`getVersionBlocks` for that version's `version_uid`.

**What the screen shows.** Once a version is chosen: its blocks, grouped by page number,
each with its `block_id`, `bbox` (`x0`/`y0`/`x1`/`y1`, unit and origin) and character
span, exactly as the operation answered them.

**What it does not show, and how a reviewer tells which case they are in.** The product's
own five-state vocabulary (`shared/ui/states.tsx`) already draws the absent/empty line —
`NotApplicableState`'s own doc comment says *"distinct from empty, which means the answer
is genuinely nothing"* — so this screen did not need to invent wording for it:

- `status: "not_produced"` → `NotApplicableState`, title *"Разметка блоков для этой
  версии ещё не построена."*
- `status: "produced"` with zero blocks → `EmptyState`, title *"Блоков не обнаружено."*

Both cases answer `blocks: []`; the state a reviewer sees, and its title, differ. Once,
near the top of the screen, in the subject's own words and naming no operation, no field
and no transport (`R-39`): *"Векторный граф блока здесь пока не строится."*

**No invented numbers.** Every figure on the screen — page number, per-page block count,
each coordinate, each character offset — is read straight off the response; nothing is
computed, estimated or shown before data has arrived.

**Consequence for two existing guards, both fixed inside this stream's grant:**

- `prepared-sections.guard.test.ts` held `blocks` to the placeholder rules
  (`R-23`'s addendum, §3.11) alongside `optimisation`/`logs`/`workers`. `blocks`
  graduated; the file now holds three sections, and every "four" that meant *section
  count* became "three" — the "four rules" `R-23`'s addendum itself sets is untouched,
  since that count did not change.
- `rendered-language.guard.test.ts`'s widget-branch matrix could not reach seven of this
  screen's branches in one static render pass: the picker's second and third steps
  (document list, then block index) mount only after a client click sets `useState`,
  which the harness cannot fire — the same limitation already excuses the pager's
  "В начало" and the upload pre-check panel. Each of the seven is named individually in
  `UNREACHABLE_IN_ONE_PASS` with its own reason, not silenced by widening a selector.
  One of the seven — `EmptyState`'s "Блоков не обнаружено." for a genuinely zero-block
  **produced** version — is not reached by any instrument today, including a browser:
  the corpus fixture this product ships never produces that state. Reported here rather
  than manufactured with a synthetic fixture.

Frontend battery: `npm --prefix web test` → **1110 passed, 78 files, 0 failed**.
`npm --prefix web run typecheck` and `npm --prefix web run lint` both clean.
