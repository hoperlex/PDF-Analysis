# CMP-MATRIX-01 — the effective matrix of a document set: algorithmic build over page profiles, manual edits with a base revision and undo, the AI-link read, staleness, orphaned edits, the `matrix_build` work kind

Written 2026-10-28 by the Sonnet lane `CMP-MATRIX-01` (branch `agent/cmp-matrix-01`, base `d11c13fd` on `integration/compare-modules`; nothing pushed, nothing merged). Task file: [`tasks/CMP-MATRIX-01.md`](tasks/CMP-MATRIX-01.md). Decisions cited are those of [`ADR-0025`](../architecture/adr/ADR-0025-comparison-modules.md) (3, 7, 8, 9, 13, 14, 16, 20, 23); the plan is [`dispatch/COMPARE-MODULES-PLAN.md`](dispatch/COMPARE-MODULES-PLAN.md) sections 1.1, 3.2 (`R3-10`) and 4 wave C1; the seal it serves is [`CMP-SEAL-C1.md`](CMP-SEAL-C1.md) (section 9, its row); the lanes it builds on are [`CMP-PROFILE-01`](CMP-PROFILE-01.md), [`CMP-PROFILE-QUEUE-01`](CMP-PROFILE-QUEUE-01.md), [`CMP-WORK-01`](CMP-WORK-01.md) and [`CMP-INGEST-01`](CMP-INGEST-01.md).

## 1. Result

The six operations `getComparisonMatrix`, `prepareComparisonMatrix`, `listComparisonMatrixEdits`, `applyComparisonMatrixEdits`, `undoComparisonMatrixEdit` and `listComparisonAiLinks` are served by `ComparisonMatrixAdapter` over `ComparisonMatrixService`. The stub rows of the six operations are gone from the composition registers, and `comparison_matrix` and `comparison_matrix_edit` left `SEALED_NOT_YET_WRITTEN`; `comparison_ai_link` is only read here and stays in it for wave C2.

* **The algorithmic matrix** is built from the stored page profiles of the versions in the confirmed order: a max-weight assignment between adjacent versions (an own `numpy` implementation, equal to the original's pair for pair and optimal against exhaustive search), the thresholds 0.55 / 0.35 / 0.20, the match rules `v1.2` (margin, resolve, package, permit, page number, group, and the direct check as a function), table-sheet groups, duplicates, splits with the text coverage of the older sheet, bridges across a version where the sheet is missing, `absent` and `unmatched` cells with their candidates.
* **Manual edits** (`link`, `unlink`, `mark_absent`) are applied as one batch against a base revision `{matrix_id, edit_no}` (`409 conflict` `comparison_matrix_stale` on a moved base, nothing written), validated as a whole (`comparison_edit_invalid`), keyed and expert-only; `undoComparisonMatrixEdit` appends an `undo` event for the latest applied edit (`comparison_edit_none` when there is none). The rows `0039` migrated from `0035` (`migrated_sheet_link`) read as edits like any other.
* **The effective matrix** is a read model, a pure function of the build, the accepted AI links and the edit history: algorithm, then AI (cells marked `ai`, never an expert act), then manual edits, and a manual edit wins; an AI link applies only while its cell is still in the state it answered, otherwise it reads `superseded`. The same inputs give the same bytes (shown across processes with different string hash seeds).
* **Staleness** compares the stored `profile_signature` (a digest of the page profiles read) and the order with the current ones: `stale_reasons` `order_changed` and `profiles_changed`. An edit whose cells do not exist in the build is **orphaned**: kept, listed in `orphaned_edit_ids` and read `orphaned` in the history; never applied silently, never dropped.
* **The work kind** `matrix_build` (the second line of `HANDLER_FACTORIES`): `prepareComparisonMatrix` enqueues the page-profile items of the versions that lack profiles through `enqueue_version_page_profiles`, then one build item; the build waits for the profile items by yielding (no attempt spent), fails with a typed reason when nothing is going to build the profiles, and writes the matrix once per input set under the lease fence.
* **For `CMP-SERIES-01`**: `read_adjacent_sheet_pairs(session_factory, *, project_uid, document_uid) -> AdjacentSheetPairs` (section 7).

## 2. Base facts, printed before any edit

`contract 1.10.0 131 paths 148 operations 432 schemas 27 error codes`, `VERSION` `0.9.0`, head `0039_comparison_core`, base `d11c13fd01f431bb081ad9f984fc6a3dc615b39e` (`P-01` of the task file). They equal the premise of the wave brief, so the lane went on. The lane changed no contract, no migration, no dependency and no lock file.

**The original's source was not where the brief says.** `/root/projects/PDF-proverka` does not exist on this host (`P-02` of the task file). The lane read the same commit `23f379fd` as raw files from `raw.githubusercontent.com/SU10KAZ/PDF-proverka` into its session scratchpad, outside the repository (the method of `CMP-ORIGINAL-READ-01`), as data, and cites file and line of those copies: `backend/app/services/version_comparison/{lineage,resolve,settings,parts,stamp,profile,jobs,pdfio}.py` and `backend/app/services/stage_comparison/document_matching.py`. Nothing of it is committed.

## 3. What was built

`src/auditmanager/comparison/matrix/` (new, 3 873 lines in 14 modules):

| module | what it holds |
| --- | --- |
| `settings.py` | every number with the original's line it is copied from; `ALGO_VERSION` `cmp-matrix/1`, `RULES_VERSION` `v1.2` |
| `assignment.py` | `maximum_weight_assignment`: the original's Hungarian algorithm on `numpy` (same float operations, same first-column tie rule) |
| `features.py` | `PageFeatures` over a `PageProfileData`: tokens outside the service zones, kind, stamp fields, footer number, permit number, masks kept compressed behind a bounded `MaskCache` (96 MiB) |
| `scoring.py` | the page score (text, layout, title, identity, image; containment, title prefix and order decide candidacy), `has_content_evidence` |
| `resolve.py` | stage two: distinctive words, mutual check, tables and blocks, twins, package, permit, footer page number, groups, `strong_pairs` (rule `direct`) |
| `lineage.py` | `assign`, `build_rows` (rows, duplicates, bridges, new sheets, candidates, absent cells), `direct_pairs`, `find_splits` and the text coverage of the parts |
| `model.py`, `repository.py` | records; the statements of `comparison_matrix` (insert, once per input set) and `comparison_matrix_edit` (insert), and the reads of `comparison_ai_link`, `comparison_page_profile` and `comparison_work` |
| `effective.py` | the effective-matrix read model: layers, edit semantics, undo, orphans, AI states, `canonical_json`, `page_index` |
| `inputs.py` | `profile_digest`, `resolve_order`, `stale_reasons`, progress, completeness |
| `pairs.py` | `adjacent_pairs`: the sheet pairs of each adjacent transition (section 7) |
| `service.py` | `ComparisonMatrixService`: the six operations, `build_matrix`, `profiles_pending`, `read_adjacent_sheet_pairs` |
| `handler.py` | `MatrixBuildHandler` (kind `matrix_build`), its factory, payload `{"document_uid": ...}` |

Wiring (the hunks of wave brief section 1 rule 4, minimal): `bootstrap/adapters.py` (the body of `ComparisonMatrixAdapter` and nothing else), `bootstrap/composition.py` (**one line**: `comparison_matrices=ComparisonMatrixAdapter(sessions, blob_store=store),`), `comparison/public.py` (imports, `matrix_build_handler` as the second line of `HANDLER_FACTORIES`, twelve names in `__all__`), the three composition registers (`SEALED_STUB_GETS` and `SEALED_STUB_ADDRESSED` lose the matrix rows, `WIRED` gains the six operations), `scripts/recovery/grant_classification.py` (`comparison_matrix` and `comparison_matrix_edit` leave `SEALED_NOT_YET_WRITTEN`). `api/routers/ports.py` needed no row. `tests/unit/comparison/work/test_composition_unit.py` needed no change: it pins the shipped kinds by membership, not by equality.

## 4. The original's rules, ported, with their lines

`P` = `backend/app/services/version_comparison/`. Lines are those of `23f379fd`.

| rule | original | here |
| --- | --- | --- |
| thresholds 0.55 / 0.35 / 0.20 | `P/settings.py:92-94` | `settings.py`; ten score bands in `test_a_pair_is_high_medium_a_candidate_or_nothing_by_the_three_thresholds` |
| rule set `v1.2` | `settings.py:120-129, 172` | `settings.RULES` (no `shx`, `chain`, `stale`: below) |
| max-weight assignment | `stage_comparison/document_matching.py:73-133`, used at `P/lineage.py:343-392` | `assignment.py`; equal to the original on 28 random shapes with ties, optimal against brute force on 432 random matrices |
| page score and its weights | `lineage.py:190-282` | `scoring.py` |
| a candidate needs content evidence | `lineage.py:284-287` | `scoring.has_content_evidence` |
| margin to the nearest competitor (rule `margin`) | `lineage.py:366-392`, `settings.py:132` | `lineage.assign` |
| duplicates in a version, two rules | `lineage.py:290-317`, `resolve.py:253-261` | `lineage.find_duplicates`, `resolve.same_drawing` |
| the build: copies, bridge, new sheets | `lineage.py:397-498` (bridge `459-476`) | `lineage.build_rows` |
| unmatched / absent cells, candidates (top 3; order only breaks ties to hundredths) | `lineage.py:578-659` (`612-640`) | `lineage._finalize` |
| resolve: distinctive words, mutual check, images, twins, titles | `resolve.py:61-229, 484-573` | `resolve.py` |
| tables and blocks; group pairing | `resolve.py:351-450` | `resolve._blocks`, `_group_pairs`, `_increasing` |
| package | `resolve.py:452-481` | `resolve.package_map`, `package_conflict` |
| permit | `resolve.py:279-287`, `lineage.py:107-114` | `resolve.permit_conflict`, `features._permit_no` |
| page number of an unstamped report | `resolve.py:127-147`, `lineage.py:121-132` | `resolve._by_page_no`, `features._footer_no` |
| direct check of two versions | `lineage.py:501-508`, `resolve.py:307-329` | `lineage.direct_pairs`, `resolve.strong_pairs` |
| splits: floors, parts | `P/parts.py:27-75` | `lineage.find_splits`, `_floors` |
| frame, kind | `P/stamp.py:62-77, 196-211`, `lineage.py:95-106` | `features.detect_frame`, `PageFeatures._kind` |
| edits `move`, `detach`, `absent`; AI link | `lineage.py:511-576`, `jobs.py:298-334` | `effective.py` (`link`, `unlink`, `mark_absent`; AI links) |

**What the page profile does not carry, and what stands in its place.** None is silent: each is here and in the modules' docstrings, and none has been measured against a real set (no one has read one with a tool that may show it).

* *The stamp's form and zone.* The original takes `kind` and the service zone from its own stamp parser (`stamp.py:80-193`). Our profile has fields only, so `drawing` stands for a recognised stamp (`drawing` and `text` are compatible in the score, `lineage.py:255`), `spec` and `permit` are decided by the original's word rules, and the stamp zone is the 185 x 55 mm block against the detected frame (190 x 60 mm against the page when no frame is found). The release-stamp zone and its QR code (`profile.py:99-106`) are not detected; the frame margins are, when the profile's lines show a frame.
* *The `shx` rule* (a stamp read from hidden AutoCAD SHX annotations, `lineage.py:48-69`): the profile holds no such text. A stamp that exists only as SHX text is not read.
* *`chain` and `stale`* belong to the series (a non-adjacent pair only through the chain of adjacent links; pair fingerprints inside a run), not to the matrix.
* *Split coverage.* The original computes it from the registered pair of each part (not read). Here it is the share, in percent, of the older sheet's words that stand in at least one part; the area coverage is the series' own.
* *`distinct` and `peel`* are not in `v1.2` and are not ported.

## 5. Decisions the lane took (the FIX slot may revise any; none edits the contract)

1. **Revision** `{matrix_id, edit_no}`: the latest build and the highest `edit_no` (undo events count). Either moved is `409 comparison_matrix_stale`; the check and the inserts run under the advisory lock the edit-chain trigger takes.
2. **Edit semantics**, over immutable page coordinates (version, page number). `link(page, other_page)`: `other_page` joins the row of `page` at its own version's column; a different page that was there gets a row of its own and is shown as touched (`manual`, as the original's `✎`); the old row keeps a hole (`unmatched`, reason `edited`, no candidates); a row left empty goes. `unlink(page)`: the page leaves for a row after the old one. `mark_absent(page, version)`: the row has no sheet there (`absent`, reason `marked_absent`, with `edit_id`); a page that stood there gets a row of its own. A row an edit created holds one page and reads `absent` / `edited` in the other versions. The build is not repeated for an edit (the original rebuilds), so a hole keeps the candidates of the build minus those an edit has since taken into a row that already holds the reference sheet.
3. **Orphaned.** Replayed in `edit_no` order on the build, an edit is orphaned when a page it names is not in the build (a version published after it, a foreign version), when `mark_absent` names a version the build does not have, or when `unlink` finds the page already alone in its row. It is kept, not applied, listed in `orphaned_edit_ids` and read `orphaned`; an undo can take it back.
4. **An AI link applies** when it is bound to the latest build, its two pages are primary cells of two different rows, and the cell it answered is still in that state: `unmatched` — the older row's cell at the other version is an `unmatched` hole and the two rows share no version (the rows are merged); `doubtful` — that cell holds another page at `medium` (the model's page replaces it, the other goes to a row of its own). After the manual layer it must still carry its mark, otherwise it reads `superseded`.
5. **Reasons** of an unmatched cell are the original's resolve codes (`twin`, `twin_sheet`, `block`, `weak`, `taken`, `not_mutual`, `below_pair`, `package`, `no_evidence`, `title_conflict`, `title_only`, `page_no_conflict`, `permit`) and `candidates_left`; of an absent cell `no_candidates`, `marked_absent`, `edited`. They are codes; the words are `CMP-VC-UI-01`'s. A cell that is `unmatched` with no candidate left becomes `absent` (`no_candidates`), as in the original.
6. **State** of a document set: `absent` (no build, nothing queued), `building` (a `matrix_build` or `page_profile` item of the set is going to run), `ready`, `stale` (the build's order or digest differ and nothing is going to run), `failed` (the latest `matrix_build` item failed; `failure_reason` is its reason). A stale build is still shown, as built, with its `stale_reasons`; its columns are the versions it walked.
7. **Order.** The latest `comparison_version_order` revision, then any version it does not list (published after it) in the document's own order; with no revision, the document's own order (`version_ordinal`, oldest first). A build binds `order_id` (empty for the own order).
8. **Preparation and the build.** `prepareComparisonMatrix` (expert, keyed) enqueues a `page_profile` item for each version with a missing page (`retry_failed` for a version with a page that ended without a result) and one `matrix_build` item (dedupe key `matrix_build:<document_uid>`, module `versions`); none if the build is current and nothing is missing; a replay of the key answers the state now. The build reads the profiles one page at a time (the archive of a page is megabytes; only compact features are kept), builds once per input set (the unique index of `0039`), and publishes under `WorkItem.require_current` in the publishing transaction (decision 7).
9. **A replay** of `applyComparisonMatrixEdits` or `undoComparisonMatrixEdit` answers the matrix as it is now, not a copy stored at the time (the command receipt holds a small outcome).
10. **Reads of other tables**, all read-only and in `repository.py`: `comparison_version_order` (the latest revision: the lane's brief lists it; `ingest.public` does not export the order reader and `ingest.comparison_pdf.public` is a deep import for a context other than the composition root, which the architecture guard `test_alr05_boundaries` refused in the first full run), `comparison_page_profile` (ids, content keys and statuses: the digest and the progress), `comparison_work` (is a build or a profile item still to run; did the last build fail) and `comparison_ai_link`. `require_expert` is the same three lines as the ingest one, kept local for the same reason.

## 6. Safety rules and their mutation proofs

Each row: the quoted mutation, the tests run, the red result, then the file restored from git (`git checkout`) and the same tests green. Tool: a script outside the repository that applies the replacement, runs `pytest` on the named files, restores, and runs again; the tree was clean after each. "U" is `tests/unit/comparison/matrix`, "I" is `tests/integration/comparison/matrix`, "C" is `tests/integration/composition`. Counts are the failures of the named files; every green was the same files again on the restored file.

| # | commitment | mutation | red (guard) |
| --- | --- | --- | --- |
| M01 | threshold 0.35 | `MATCH_MEDIUM = 0.30` | U `test_rules`: 2 failed (the literal pin, the band 0.333) |
| M02 | threshold 0.55 | `MATCH_HIGH = 0.50` | U: 2 failed (the pin, the band 0.538) |
| M03 | threshold 0.20 | `MATCH_CANDIDATE_FLOOR = 0.10` | U: 2 failed (the pin, the band 0.176) |
| M04 | the assignment is optimal | `cost = padded` (minimises) | U `test_assignment`: 1 failed (brute force) |
| M05 | rule `margin` | `margin` removed from `RULES` | U: 9 failed |
| M06 | rule `permit` | `permit_conflict` returns False | U: 1 failed |
| M07 | rule `package` | `package_conflict` returns False | U: 1 failed |
| M08 | rule `pageno` | footer number never read | U: 1 failed |
| M09 | rule `group` | `if False` for the group pairing | U: 1 failed |
| M10 | duplicates | `find_duplicates` returns `{}` | U: 1 failed |
| M11 | bridge across a gap | every bridge candidate skipped | U: 1 failed |
| M12 | splits | `len(prefixed) >= 3` | U: 1 failed |
| M13 | **a manual edit wins** (decision 3, verification row 9) | the AI layer applied after the manual layer | U `test_effective`: 1 failed |
| M14 | an AI cell is labelled `ai` | the mark not set | U: 3 failed |
| M15 | an AI link applies only while its cell is in the state it answered (decision 14) | the state and the disjoint-rows conditions removed (and each alone, M15b, M15c) | U: 1 failed each |
| M16 | an AI link binds its build | the build comparison removed | U: 1 failed |
| M17 | an edit that no longer applies is orphaned, not applied | `unlink` of a lone page applied | U: 1 failed |
| M18 | an orphan is listed, never silent | the orphan list not filled | U: 1 failed |
| M19 | undo reverses the latest applied edit | the oldest chosen | U: 1 failed (after the test was tightened: it first passed under this mutation, see section 8) |
| M20 | staleness compares the profile digest | the digest ignored | U `test_inputs_and_handler`: 1 failed |
| M21 | raw evidence is never rewritten by a layer (decision 20) | the stored rows edited in place | U: 1 failed |
| M22 | an orphan: a version the build does not have | the check removed | U: 1 failed |
| M23 | the same input is the same bytes | rows sorted by `hash()` (varies with the process) | U `test_vs1_oracle`: 1 failed (the hash-seed test) |
| M24 | the lease fence is handed to the build (decision 7) | `publish_guard=None` | U: 1 failed |
| M25 | the mask cache is bounded (decision 9) | the eviction loop removed | U `test_features`: 1 failed |
| M26 | the base revision's edit count | `newest != base_edit_no` ignored | I `test_edits`: 1 failed |
| M27 | the base revision's build | the build comparison ignored | I: 1 failed |
| M28 | a batch is validated | the validation skipped | I: 1 failed |
| M29 | **an expert's act** (decision 16) | `require_expert` removed from `apply_edits` | I: 1 failed |
| M30 | a keyed write replays | the replay branch off | I: 1 failed |
| M31 | undo with nothing to undo | the check removed | I: 1 failed |
| M32 | **the publishing transaction is fenced** (decision 7) | `publish_guard(session)` not called | I `test_prepare_and_worker`: 1 failed |
| M33 | **a module that is off claims nothing** (decision 23) | the item enqueued in module `stages` | I: 1 failed |
| M34 | missing profiles are enqueued | the loop never enqueues | I: 1 failed |
| M35 | the build waits (a yield spends no attempt) | `Failed` instead of `Yielded` | I: 1 failed |
| M36 | the kind is registered through the shipped tuple | the factory removed from `HANDLER_FACTORIES` | I: 4 failed |
| M37 | a reorder makes a build stale | the order comparison removed | I `test_edits`: 1 failed |
| M38 | the stub register no longer lists a served operation | `getComparisonMatrix` put back into `SEALED_STUB_ADDRESSED` | C `test_an_absent_parent_...`: 1 failed |
| M39 | the operation is judged as served | `getComparisonMatrix` out of `WIRED` | C `test_comparison_core_stub_operations`: 1 failed |
| M40 | the table is no longer sealed | `comparison_matrix` put back into `SEALED_NOT_YET_WRITTEN` | `tests/integration/recovery/test_grant_classification.py`: 2 failed |

ADR-0025 decisions and where they touch this lane: **3 and 14** (manual beats AI; a stale base is `conflict`; an AI link binds the build and the cell state; an orphan is never silent): M13–M19, M21, M22, M26, M27, M30, M31, M37. **7 and its addendum** (the publishing transaction is fenced; no cross-project row): M24, M32; the matrix writes no blob and takes no project lock (the addendum's wording: the queue relies on item and attempt locks and `ON DELETE RESTRICT`). **8** (compute in a ceilinged child): **not applied**, see section 9 item 1. **9** (bounded): the mask cache is bounded in bytes (M25); the matrix stores no blob; a build is one `jsonb` row. **16** (expert acts): the service checks the role in the transaction that acts (M29) beside the edge's `OPERATION_ROLES` (`test_the_roles_are_the_ones_the_adr_gives`; an administrator is `403` over HTTP). **20** (an AI layer never rewrites raw evidence): the stored build is read-only and untouched by every layer (M21), the AI-shaped cell is marked `ai` (M14) and the table is append-only. **23** (the module flag): the build item is claimed only while `versions` is on (M33; `test_with_the_module_off_...`: with `none` the item stays `queued`). **5, 10, 15, 18**: not touched by this lane (no spend, no upload, no cache key, no image).

## 7. For `CMP-SERIES-01`: the sheet pairs of each adjacent transition

```python
from auditmanager.comparison.public import read_adjacent_sheet_pairs, AdjacentSheetPairs

pairs: AdjacentSheetPairs = read_adjacent_sheet_pairs(session_factory, project_uid="prj_...", document_uid="doc_...")
pairs.matrix_id, pairs.edit_no, pairs.order_id, pairs.order      # the revision it was read at, the versions it walked
for transition in pairs.transitions:                             # one per adjacent pair of versions, in order
    transition.source_version_uid, transition.target_version_uid
    for pair in transition.pairs:                                # SheetPairSpec, in the order of the rows
        pair.page_a, pair.page_b          # PageRef(version_uid, page_number, page_profile_id) or None
        pair.relation                     # "matched" | "added" | "removed" | "unmatched"
        pair.confidence                   # the newer cell's: high | medium | group | manual | ai (None for one-page pairs)
        pair.flags                        # subset of split, duplicate, scan, bridge
        pair.ai_dependent, pair.ai_link_ids, pair.edit_ids
        pair.candidates                   # for "unmatched": the matrix's candidate pages, for information
        pair.split                        # SplitSpec(kind "floors"|"split", role "whole"|"part", source, parts, covered_percent) or None
```

It reads the effective matrix of the **latest build**: the algorithm, the accepted AI links and the manual edits applied, a manual edit winning. A document set with no build is `not_found`; read `ComparisonMatrixService.get_matrix(...)["state"]` first and start a series only for `ready` (a stale build answers with the order it walked: `order` and `order_id` say which). The function reads and writes nothing. A duplicate copy never makes a pair; the pair uses the primary page. A transition that holds an `ai_dependent` pair is marked in the series verdict (ADR-0025 decision 3). The identity a series binds to is `(matrix_id, edit_no)` (the seal's `comparison_series.comparison_matrix_id` and its stored `input_sha256`). On the synthetic corpus the four transitions read `{matched: 6}`, `{matched: 5, removed: 1, added: 1}`, `{matched: 6}` and `{matched: 6, added: 1}` (the second part of the split plan is an `added` pair with `split`).

## 8. Commands and results

Commands run from the lane worktree with `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src`, the lane's `.env` loaded for the container suites; database tests on the lane's own PostgreSQL (`57840`) and MinIO (`61840`) after `make migrate` (head `0039`). `df -h /` was read before every container start and long run: 2.2 to 2.9 GiB free (the stop line is 1.5 GiB). The host was not quiet (load average 11 to 27 while the composition directory ran; other projects' runs).

| what | command | result |
| --- | --- | --- |
| diff hygiene | `git diff --check d11c13fd..HEAD` | clean (exit 0) |
| unit directory | `pytest -q tests/unit/comparison/matrix` | **76 passed** (the real page children once per session: about 20 s) |
| integration directory | `pytest -q tests/integration/comparison/matrix` | **25 passed** (the template document of VS-1 is profiled once per database: 30 s the first time, 2 s after) |
| both | the two directories together | **101 passed** in 74 s |
| the whole composition directory | `pytest -q tests/integration/composition -rf` | **1966 passed, 4 skipped, 0 failed** in 51 min 34 s (1 970 tests; the host was loaded: the erase and stand-copy script tests took minutes each) |
| the lane's directories and the wiring files again on the final source (`556bcb44`) | `pytest -q` on `tests/unit/comparison/matrix`, `tests/integration/comparison/matrix`, `test_router_answers`, `test_an_absent_parent_is_not_an_empty_page`, `test_comparison_core_stub_operations`, `test_comparison_stub_operations`, `test_every_port_implementation_is_whole`, `test_composition_root`, `tests/integration/recovery/test_grant_classification` | **334 passed, 2 skipped, 0 failed** in 24 min (the same files after the cleanup commit: 303 passed, 1 skipped for the eight files then named) |
| whole `tests/unit` | `pytest -q -p no:cacheprovider tests/unit -rf` | **4403 passed, 76 skipped, 0 failed** in 4 min 7 s |
| `tests/contract` minus the three `D-220` files | `pytest -c pyproject.toml --rootdir=. -q tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_validate_bootstrap.py --ignore=tests/contract/test_cp00_final_state.py -rf` | **1310 passed, 19283 subtests passed, 0 failed** in 2 min 28 s |

**What the new tests prove, and against what.**

* *The answer key* (`test_build_against_the_answer_key.py`, `test_vs1_oracle.py`, the real children and the real database): the matrix of the five VS-1 versions holds, row by row, the sheets of the key's `sheet_identity` — E01…E07, no sheet in two rows except E05, whose two V5 parts are two rows (one older page is one pair), the duplicated sheet E03 as one cell with `duplicate` and its copy, the scans in V4 and V5 as `scan`, the added specification and the removed sheet 6 as rows with `absent` cells, the split as `split` on the three cells and one split record (`split`, role `part`, coverage a percentage).
* *The rules* (`test_rules.py`, hand-made pages): ten score bands around the three thresholds; equal candidates are not chosen; a permit is never linked to another permit or a sheet; the package correspondence; a footer page number decides twins whose text does not; duplicates by the stamp and by words plus drawing; a bridge across a missing version; a new sheet's row; floors and parts splits and their coverage; a table block paired as a group.
* *The layers* (`test_effective.py`, `test_layers_and_pairs.py`): link, unlink, mark-absent, undo, orphans, AI on an unmatched and on a doubtful cell, manual over AI, an AI link of another build, and the same bytes whatever order the inputs arrive in; the sheet pairs from the real matrix.
* *The writes* (`test_edits.py`, `test_http.py`): the base revision, atomic batches and every kind of invalid edit, undo down to `comparison_edit_none`, key replay and key reuse, the role in the transaction and at the edge, a migrated approval read as an edit, a reorder and a new version making a build stale, an orphaned edit kept and listed; paging by cursor; the refusals as the client reads them.
* *The work kind* (`test_prepare_and_worker.py`): the real runner built from the shipped tuple — enqueue, the build claimed before the profiles waits and spends no attempt, the profiles are built by the same runner, the build writes the matrix once; a build nothing waits for fails with its reason and no retry; a bad payload and an unknown document fail without a retry; with the module off the item stays queued; a fence that refuses the publish writes nothing.

**Scale (numbers only, a synthetic set, not a real one).** A script outside the repository builds hand-made A1-sized pages (300 words, a sparse 36 dpi mask, a stamp) and times `PageFeatures` and `build_rows`: 4 versions x 30 pages 0.6 s and 116 MiB peak RSS; 12 x 100 pages 4.6 s + 11.7 s and 230 MiB; 12 x 400 pages 18.9 s + 179 s and 541 MiB (the cost of the assignment is quadratic in the pages of a version). A real A1 sheet has more words than 300 and denser masks, so these are floors; the 900 s watchdog of `jobs/lease.py` would be reached by a set of roughly 12 x 900 such pages, far past the 500 pages a version may have (so 12 x 500 is about 5 minutes).

## 9. Limits, risks, items for the FIX slot

1. **The build runs in the worker's process, not in a ceilinged child** (ADR-0025 decision 8 says every profile, engine and tile computation does). The matrix is numpy and set arithmetic on features, not a render, and the measured peak is 230 MiB (12 x 100) to 541 MiB (12 x 400); but it is not under `RLIMIT_AS`. If the integrator wants the ceiling, the build needs a child that is handed the features (or reads the profiles itself): a change of `service.build_matrix` and `handler.py` only. Item for the integrator.
2. **`comparison_edits_limit` cannot be reached through the edge.** The request schema's `maxItems: 500` refuses a longer batch before the service, and the client reads `422 validation_failed` with `details {"field": "edits", "constraint": "length"}` (shown in `test_the_refusals_are_the_contracts`). The service raises the registered reason for a caller that does not come through the edge. FIX: drop `maxItems` from the schema or take the registered word out of the contract.
3. **`ComparisonMatrixStaleReason` has no value for a change of the algorithm or of the rules** (`ALGO_VERSION`, `RULES_VERSION`); such a build is reported `profiles_changed`. FIX: add `algorithm_changed`.
4. **No per-version label.** `ComparisonMatrixColumn.label` is optional and is not set: nothing in the document set gives a version a label (`display_title` belongs to the document). `CMP-VC-UI-01` labels columns from `listVersions` (or `CMP-INGEST-01`'s stamp reading: «Изм.N»).
5. **The copies of a duplicated page are not listed in the matrix.** The cell carries the `duplicate` flag and the primary page; the contract has no member for the other pages, and `unassigned_pages` is empty (a copy is held by its row). They are in the stored build (`dups`).
6. **The original's block detail** («A стр. 5–9 ↔ B стр. 7–12», `resolve.py:515`) does not fit a `reason` code (at most 64 characters); the cell says `block`. FIX if the screen needs the ranges.
7. **The stale docstrings.** The module docstring of `api/routers/comparison_matrix.py` and the descriptions of the six operations in the OpenAPI document still say "sealed as a stub until `CMP-MATRIX-01`". The contract text can change only in a seal or a FIX; the router file is outside this lane's paths.
8. **The six operations answer whatever the module flag says**, as the upload and the order operations do (only the worker is gated, decision 23). `prepareComparisonMatrix` with the module off enqueues items that wait.
9. **An expert's draft against a document that is being re-profiled** reads the latest build; `building` and `stale` states are shown with the rows of the build they rest on. A UI must show the state, not only the rows.
10. **What a hole keeps after an edit** (section 5 item 2): the candidates of the build, not recomputed. The original recomputes them by rebuilding; here the expert sees at most what the build offered.
11. **The `kind`, zone and `shx` approximations of section 4** are unmeasured on real stamps; a layout the profile's stamp reader does not understand leaves a field absent, and the score then leaves that part out (never a wrong part in).
12. **Host load.** The composition directory took 51 min on a host with load average up to 27; the 22-minute subset after the last source commit likewise. No test was repeated to turn a red into a green; there was none.
13. **Not run, by the brief and `R-135`:** `make gate`, the web battery (no web change), the live journey. The task touches `bootstrap/**` (AGENTS section 8 case 3 asks one full gate on the lane that changes the composition root), deferred to the gate before the beta.

The first full contract battery found two guards the lane's own directories could not: `test_alr05_boundaries` (the deep import above) and `test_surface_counts_in_prose` (a docstring that said "six operations"); both were fixed in `556bcb44` and the batteries, the lane's directories and the wiring files were run again on that source. A first version of four guards did not catch the mutation it was written for: `test_a_pair_is_high_medium_...` had three bands and M01–M03 were caught only by the literal pin (the bands were widened to ten), the page-number twins test passed under M08 because the footer token alone separated the pages by score (the shared body was lengthened until the margin could not), `latest_applied_edit` was tested with one applied edit only (M19), and the AI-state test removed one of three conditions at a time without a case for each (M15). Each was rewritten and the mutation shown red.

## 10. Notes for the next lanes

* **`CMP-SERIES-01`**: section 7. Do not start a series on a `stale`, `building` or `failed` state; bind the series to `(matrix_id, edit_no)`. `relation` `unmatched` is a pair that needs an expert (status `unmatched`), `added` and `removed` are one-page pairs. The permit and parts post-phases can use `flags`, `split` (`kind`, `role`, `source`, `parts`, `covered_percent`; the covered percentage is a text coverage). `ai_dependent` marks the transition's verdict.
* **`CMP-VC-OVERVIEW-01`** (step 3, «Сопоставление листов»): `state` `absent` is «не собрано», `building` «идёт», `stale` «устарело», `failed` «ошибка» with `failure_reason`; `counts.unmatched` is «не сопост. N», `counts.rows` and `counts.manual` are «строк N · ✎ M»; `progress` is step 2 «Разбор версий» (`ready` of `total`, `failed`). All from `getComparisonMatrix`; it starts nothing.
* **`CMP-VC-UI-01`**: the cell reasons are codes (section 5 item 5) for Russian sentences; `confidence` is absent on a first appearance of a sheet; `ai` cells are labelled «ИИ», `manual` «✎»; an unmatched cell offers `candidates` (up to three, with the score) and «Связать» is `link(page of the row, candidate)`, «⤫» is `unlink`, «Отметить, что этого листа в версии нет» is `mark_absent(page of the row, version)`; a drag of a thumbnail onto a cell is `link(page of the cell's row, dragged page)`; the draft carries `revision` and is rebased on `409 comparison_matrix_stale`; `row_id` is valid within one revision only; `orphaned_edit_ids` and the history's `orphaned` status are shown, not hidden; a stale build says why (`stale_reasons`); «Отменить правку» is `undoComparisonMatrixEdit` for a saved edit (the latest applied one, not a chosen one). `TRANSLATED_SCHEMAS` needs the new enums (the seal's note).
* **Wave C2** writes `comparison_ai_link`: bind the build (`matrix_id`) and the state (`unmatched` or `doubtful`) the model answered; the read model labels and supersedes it; it needs no change of this lane.

## 11. Contracts and hotspots, resources

* **New or changed contracts: none.** `contracts/**`, `db/migrations/**`, `pyproject.toml`, `uv.lock`, `docs/program/P02_LOCK.json` untouched (`git diff --name-only d11c13fd..HEAD -- contracts db pyproject.toml uv.lock docs/program/P02_LOCK.json web infra Makefile src/auditmanager/comparison/work src/auditmanager/comparison/profile src/auditmanager/comparison/profile_queue src/auditmanager/ingest src/auditmanager/storage src/auditmanager/jobs src/auditmanager/workers` prints nothing).
* **Files outside the lane's own paths, all by the wave brief**: `bootstrap/adapters.py` (the body of `ComparisonMatrixAdapter`), `bootstrap/composition.py` (one line), `comparison/public.py` (appends), the three composition registers, `scripts/recovery/grant_classification.py` (two names). `git diff --name-only d11c13fd..HEAD` lists 38 files.
* **Instructions for the integrator.** Merge order MATRIX first, then ENGINE, VIEWER (brief section 3): the hunks in `adapters.py`, `public.py` and the registers are line-local; `adapters.py` has the matrix adapter in place of the stub class, `HANDLER_FACTORIES` gains one line under `page_profile_handler`. `CMP-WORK-01` section 7.1 (the `comparison_work=` argument in `workers/__main__.py`) is still needed before a worker process runs the item. The item `matrix_build` of a module that is on and a build without its handler is refused at start by the worker's check, so the handler and the first `prepareComparisonMatrix` ship together, as the profile handler's did.
* **Resources.** Containers `auditmanager-cmp-matrix-01-{postgres,s3,s3-init}` on ports 57840 / 61840 / 61841, brought up with `make up` and migrated with `make migrate` from the lane worktree; at the end `make down` ran, the volumes `auditmanager-cmp-matrix-01-postgres-data` and `auditmanager-cmp-matrix-01-s3-data` were removed by those exact names, and `docker ps -a`, `docker volume ls` and `docker network ls` list nothing of the lane; the lane's git-ignored `.env` was deleted. No `web/node_modules` link was made. No process was killed, by pattern or otherwise (every run ended by itself).
