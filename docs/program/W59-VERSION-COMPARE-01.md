# W59-VERSION-COMPARE-01 — served comparison of two versions of one set

Status: **complete** on `agent/w59-version-compare-01`. Phase A committed alone at
`acaab454`, phase B merged from integration commit `c4cbc026` (W59-SECTION-SEAL-01 and
W59-SECTION-UI-01) once the integrator handed over the contract slot. The optional
`mode=stage` extension is included and **delivers the W62 STAGE-COMPARE code slice**.

## Result

`GET /projects/{project_uid}/documents/{document_uid}/versions/{version_uid}/comparison`
(`compareDocumentVersions`, any one role) compares the path version (older, the source)
with `target_version_uid` (newer, the target) of the same document set. The answer is one
`VersionComparison`:

- `sheets`: every page of both versions once — `unchanged` (exact text), `changed`
  (similar text, with similarity and shared-line evidence), `removed`, `added`; a blank
  page is flagged `textless` and never guessed;
- `sheet_diffs`: one page of raw line differences (`diff_offset`, `diff_limit` 1–25,
  `next_offset`), with page numbers, 0-based line ranges and changed lines; equal spans as
  ranges only; an `evidence_sha256` per sheet over the complete raw diff;
- `findings`: proposals labelled `unchanged` / `probably_fixed` / `undetermined` / `new`
  with their basis (exact issue+quotes, quotes gone from the paired sheet, quote still
  present, unpaired evidence sheet, evidence over the cap, no exact source match);
- `mode`, both sides' facts (ordinal, pages, checksum, stage, section, run, text-layer
  digest) and a `comparison_sha256` binding all inputs and every sheet suggestion.

Every pairing and finding label is a **proposal**: no SheetLink, finding match, decision
or AI artifact is written, no `ComparisonId`/`SheetLinkId` is fabricated, and no AI layer
produces or edits any value.

**Refusals.** The path is proved first (`get_version_in`): an unknown project, a document
of another project or a source version of another document is `404 not_found`, as for
every addressed read (`D-67`). A target the rule does not admit is a `200` answer with
`outcome: refused` and one closed `refusal.reason` (and `side` where it belongs to one
version): `same_version`, `version_not_found`, `different_set`, `foreign_project`,
`version_not_published`, `version_order_invalid`, `stage_unclassified`,
`section_unconfirmed`, `project_stage_mismatch`, `confirmed_section_mismatch`,
`stage_pair_invalid`, `analysis_missing`, `run_not_of_version`, `run_not_published`,
`text_unavailable`, `text_too_large`. A pair is never relabelled and nothing falls back to
another version, stage, section or run.

**Modes.** `mode=version` (default): the same explicit stage and confirmed section on both
versions (W59 rule). `mode=stage`: a `P` source and an `R` target of the same set with the
same confirmed section (`prepare_stage_section_version_pair`, the W62 П/Р slice of
`W59-SECTION-IDENTITY-DECISION-01`); any other stage pair is `stage_pair_invalid`. It never
pairs by file name, date or project name; a cross-document "same object" comparison stays
unsupported (no `ObjectUid`). Sheet pairing, diffs and finding proposals are identical in
both modes; the mode is echoed and bound into `comparison_sha256`.

**Data sources.** Classifications come from the documents projection of
`document_version_classification` (checked against `sections.public.SECTION_CODES`);
each side's newest `published` run (or `source_run_id` / `target_run_id`, which must be a
published run of that version) supplies the saved `prepared.text_layer` — read from the
store with the SHA-256 and size its `stage_result` recorded and checked as canonical text
layer for exactly that version and page count — and its published findings.

**Web.** The comparison screen (`/projects/{p}/versions/{v}/comparison`) now leads with
«Сравнение версий» (`widgets/version-comparison`): choose the other version of the set
(ordered older → newer), «Стадии П → Р» when the older version is a confirmed П and the
newer a confirmed Р of one section, refusal reasons, sheet pairing, paged line diffs and
finding proposals, all labelled as proposals. The W43 run comparison stays below,
unchanged and lazy. The version screen links here beside the UI lane's classification
panel («Сравнить с другой версией комплекта»), which is left intact.

## Bounds (500-page versions)

Sheet list ≤ one row per page of both versions (1,000 rows). Diffs are paged: at most 25
sheets and 500,000 changed characters per answer (the first sheet of a page is always
served whole; the page then names `next_offset` — it never truncates). A sheet over the
raw-text ceilings (200,000 characters or 1,000 lines per side) is `too_large` with the
ceiling's name. Finding proposals cover ≤ 200 findings per run; a larger run reports
`findings_over_limit` instead of a partial list; a finding with more than 8 distinct
quotes is `undetermined` (`evidence_over_limit`), never dropped. Similar-text pairing of a
synthetic 500-page pair took 0.54 s at 150 lines per page and 4.3 s at 900 lines per page
(scratch script, `/usr/bin/python3.12`, shared host; not a test assertion).

## Prepared modules: reuse, not duplication

- `raw_text.diff_page_lines` — link-free line-diff core extracted from the approved path;
  `diff_approved_pairs` calls it; its evidence digest is pinned unchanged (base `890deb80`).
- `sheet_match_suggestions.suggest_sheet_pairs` — the read path: the exact rule's core
  (`_exact_pairs`) and snapshot validation, then one-to-one pairs for the pages left by
  shared *distinctive* lines (on ≤ 8 pages of both versions), ≥ 2 shared lines and Dice
  ≥ 500‰, greedy by similarity, shared count and page.
- `finding_match_suggestions.suggest_finding_matches_on_sheet_suggestions` — the same
  exact issue+quote rule (`_unique_exact_pairs`) across suggested sheets; names the sheet
  suggestions, never a `SheetLinkId`; the approved function's digest is pinned unchanged.
- `version_section_pair.prepare_stage_section_version_pair` — the W62 guard slice.

## Contract

51 paths / 58 operations / 147 schemas (from 50/57/137); migration head unchanged
`0024_version_classification`; error catalogue unchanged (25 codes). New operation
`compareDocumentVersions` (`401, 403, 404, 422, 500, 503`); ten schemas
`ComparisonRefusal`, `ComparedVersion`, `SheetPairing`, `DiffHunk`, `SheetDiff`,
`SheetDiffPage`, `FindingRef`, `FindingMatchProposal`, `FindingComparison`,
`VersionComparison` (closed vocabularies are inline `Literal` enums). The mirror
`web/openapi/openapi.json` is byte-identical (sha256 `d7704f0a…8a2a5c`), the client is
regenerated (`api:verify` OK, 58 operations) and `web/FRONTEND_LOCK.json` carries the new
digests and counts. Pins moved: `tests/support/expected_facts.json`, the 404-reference
count and the prose-mutation strings in `tests/contract/api_v1`, `REQUIRED_OPERATIONS`,
the role register, the authorization guard list, the 422 set, the port table, the D-67
sweep (`EXPECTED_ADDRESSED` 20, with a `REQUIRED_QUERY` for the target) and the P02 seam
register table. Surface prose updated in `app.py`, `health.py`, `routers/{__init__,
declarations,errors}.py`, `api/README.md`, `P02_SEAMS.md`, `ALPHA_ROADMAP.md`,
`infra/deploy/{README.md, proxy/nginx.conf, serve.py}`, the BFF route header and
`shared/api/authorization.ts`. `CURRENT_STATE.md` is the integrator's and still states
50/57/137.

## Checks

Python: `.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider`
with the lane `.venv` (python 3.12 symlink, w55b candidate library, `.venv/bootstrap`
symlink) and the lane `.env` (`auditmanager-w59-version-compare`, PostgreSQL 57500, MinIO
61100/61101, `make up` + `make migrate` to `0024`).

- `tests/unit/comparison tests/integration/comparison`: **187 passed** (115 prepared
  tests unchanged, unit tests of pairing, diff, proposals, service and both modes, and 8
  database tests including two 500-page versions from real rows).
- `tests/integration/composition/test_version_comparison_over_http.py`: **9 passed** —
  the composed app with the recorded provider: upload, a second and third version of the
  same document, unclassified → `stage_unclassified`, classified without runs →
  `analysis_missing`, two recorded runs → compared (every sheet `unchanged`, no diffs,
  every finding proposal `unchanged`), an `R` third version refused in `mode=version`
  (`project_stage_mismatch`) and compared in `mode=stage`, P/P in `mode=stage` →
  `stage_pair_invalid`, foreign document path → `404`, malformed paging/run/mode → `422`.
- Focused API/composition suites that pin the surface (`test_an_absent_parent_is_not_an_
  empty_page`, `test_authorization`, `test_role_register`, `test_served_document_and_
  health_plane`, `test_operation_surface`, `test_router_and_body_rules`,
  `test_every_port_implementation_is_whole` minus one case below): all green.
- `tests/contract` (whole directory, container-free): 1,059 passed; red only as follows.
  `test_doc_prose_facts::test_the_scanned_docs_state_the_contract_surface_this_tree_has`
  — `CURRENT_STATE.md` still says 50/57/137 (integrator's file). The two failures the
  integrator listed as pre-existing (`test_error_kernel::test_there_are_twenty_four`,
  `test_ar_v2_seeded::test_seeded_categories_equal_the_sealed_api_enum`). Environmental in
  a lane worktree: `test_cp00_candidate` (174, `.git` is a file in a worktree —
  `NotADirectoryError`), `test_cp00_final_state` (3, tag `v0.0.1-architecture` and CP-00
  artifact paths absent in this checkout), `test_validate_bootstrap` (21, `jsonschema`
  absent from the symlinked runtime library).
- `tests/e2e/test_pc01_journey_conformance.py`: **87 passed**.
- Web (`npm --prefix web ci` once): `api:generate` / `api:verify` OK; `lint --quiet`
  clean; `typecheck` clean; vitest `tests/guards tests/unit/screens tests/unit/styles
  tests/unit/comparison tests/unit/sections tests/contract`: **835 passed** (50 files),
  including the rendered-language guard with four new comparison cache states.
- Not run (R-135): the full gate, the live browser journey, the whole frontend suite,
  any provider call.

## Risks and limitations

- **A second version cannot yet be uploaded through the product.** `uploadDocument`
  always starts a new document, so the comparison is reachable only for sets whose later
  versions were published another way (the end-to-end test publishes them through
  `DocumentRepository.publish_version`). An upload-a-new-version operation is a separate
  slice.
- Text comes from each side's published run: a version never analysed is refused
  (`analysis_missing`), even though its PDF is immutable.
- Every request recomputes the comparison (two text layers read and checked, pairing,
  one diff page); for two dense 500-page versions this is seconds, not milliseconds.
  There is no cache and no persistence by design.
- Similar-text pairing is a heuristic proposal: a sheet whose distinctive text was mostly
  rewritten appears as removed + added; textless sheets are never paired.
- `test_every_port_implementation_is_whole::test_pre_decide_adapter_refuses_a_severity_
  instead_of_dropping_it` fails on this base in `DecisionAdapter` (unrelated to this
  lane; not touched).
- `scripts/light_acceptance.py` maps the `comparison` context to the `analysis` suite;
  mapping it to `tests/integration/comparison` and `tests/unit/comparison` is outside
  this task's paths.

## Integrator instructions

Merge the branch head (it contains phase A, the phase B reseal, `mode=stage` and the web
page). Update `CURRENT_STATE.md` to **51 paths / 58 operations / 147 schemas** (head
`0024_version_classification`, 25 error codes), which clears the one prose red, and record
W62 STAGE-COMPARE's code slice as delivered by this task. No migration, dependency,
composition-root rule beyond the new `comparisons=` port, global style or ref changed.
Rollback: revert the merge; there is no data to migrate.

## Hotspot proof

`git diff --name-only c4cbc026..HEAD` lists only paths in this task's `allowed_paths`;
the same diff restricted to `db/migrations`, `pyproject.toml`, `uv.lock`, `requirements`,
`web/package.json`, `web/package-lock.json`, `web/src/_app/providers.tsx`,
`web/src/app/globals.css`, `docs/program/CURRENT_STATE.md`, `src/auditmanager/sections`,
`src/auditmanager/runs`, `src/auditmanager/documents` and `contracts/domain` is empty.
Phase A (`890deb80..acaab454`) touched only `src/auditmanager/comparison/**`,
`tests/{unit,integration}/comparison/**` and this report. No ref was pushed, merged or
tagged.
