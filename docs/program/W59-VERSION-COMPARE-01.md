# W59-VERSION-COMPARE-01 — served comparison of two versions of one set

Status: **phase A complete** (comparison service, read model and tests). Phase B
(contract, API, web page) follows from the integration commit the integrator names.

## Phase A result

`auditmanager.comparison.service.VersionComparisonService.compare(session, request)`
returns one `VersionComparison` read model for two explicitly named versions of one
set. It composes the prepared W59 modules and writes nothing:

1. `read_ordered_version_pair` proves both versions are published versions of the
   named set in the named project, source before target (one SELECT);
2. `prepare_same_section_version_pair` requires the same explicit `P`/`R` stage and
   the same confirmed section, read through the `VersionClassificationReader` port
   (the seal's persisted `document_version_classification`) and checked against the
   sealed fifteen-code catalogue the composition root passes in;
3. each side's newest `published` run — or the run the caller names, which must be a
   published run of that version — supplies its verified saved text layer and its
   published findings through the `VersionAnalysisReader` port;
4. `suggest_sheet_pairs` proposes sheet pairs, `diff_page_lines` diffs them, and
   `suggest_finding_matches_on_sheet_suggestions` proposes finding matches.

Every failed precondition is an explicit `ComparisonRefusal(reason, side)`:
`same_version`, `version_not_found`, `different_set`, `foreign_project`,
`version_not_published`, `version_order_invalid`, `stage_unclassified`,
`section_unconfirmed`, `project_stage_mismatch`, `confirmed_section_mismatch`,
`analysis_missing`, `run_not_of_version`, `run_not_published`, `text_unavailable`,
`text_too_large`. A mismatch is never relabelled and nothing falls back to another
version, stage, section or run. A stored fact that contradicts its own constraints
(an incomplete text layer, a classification outside the catalogue) raises
`ComparisonIntegrityError`; a malformed request raises `ComparisonRequestInvalid`.

### Changes to the prepared modules (reuse, not duplication)

- `raw_text.diff_page_lines` — the link-free line-diff core, extracted from the
  approved path. `diff_approved_pairs` now calls it; its evidence digest is pinned
  unchanged against base `890deb80`.
- `sheet_match_suggestions.suggest_sheet_pairs` — the read path. It reuses the exact
  rule's core (`_exact_pairs`) and snapshot validation, then proposes one-to-one
  pairs for the pages the exact rule left unpaired by shared *distinctive* lines
  (a whitespace-collapsed line on at most 8 pages of both versions), needing at
  least 2 shared lines and a Dice similarity of at least 500 permille, chosen
  greedily by similarity, shared count and page. No `ComparisonId` is fabricated:
  the read path has no Comparison identity, so its digests bind the pair, both
  version checksums and the page texts instead.
- `finding_match_suggestions.suggest_finding_matches_on_sheet_suggestions` — the same
  exact issue+quote rule (shared `_unique_exact_pairs`) across suggested sheet pairs;
  its result names the sheet suggestions it relied on, never a `SheetLinkId`. The
  approved function's digest is pinned unchanged against base `890deb80`.

### Read model and bounds

- `sheets`: every page of both versions once — `unchanged` (exact text),
  `changed` (similar text, with similarity and shared-line evidence), `removed`,
  `added`; a blank page is flagged `textless` and never guessed. At most 1,000 rows.
- `sheet_diffs`: a page over the sheets that have text differences, `diff_offset` /
  `diff_limit` (1–25, default 10) and `next_offset`. A page also ends before
  500,000 changed characters (its first sheet is always served whole); equal spans
  carry line ranges only; every sheet carries an `evidence_sha256` over the complete
  raw diff, equal lines included. A page over the raw-text ceilings (200,000
  characters or 1,000 lines per side) is `too_large` with the ceiling's name.
- `findings`: proposals labelled `unchanged` (exact match), `probably_fixed` (no
  match and every quote gone from its paired sheet), `undetermined` (a quote still
  on the paired sheet, an unpaired evidence sheet, or more than 8 distinct quotes)
  and `new` (a target finding with no exact source match). More than 200 findings
  on either run reports `findings_over_limit` instead of a partial list.
- `comparison_sha256` binds both versions, stages, sections, runs, text layers and
  every sheet suggestion.

A synthetic 500-page pair pairs in 0.54 s at 150 lines per page and 4.3 s at 900
lines per page (`/usr/bin/python3.12` on the shared host, one process, scratch
script; not a test assertion).

### Phase A checks

All with `.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider`
(`.venv` symlinked to the w55b candidate's library, as the seal lane does):

- `tests/unit/comparison tests/integration/comparison` on the lane's own PostgreSQL
  (`auditmanager-w59-version-compare`, port 57500, `make up` + `make migrate` to
  `0023_norm_citations`): **173 passed** — 115 existing comparison tests unchanged,
  50 new unit tests, 8 new database tests (two 500-page versions, every version
  refusal from stored rows, an unclassified stored version).
- `tests/contract/architecture`: **3 passed** (ALR-05 boundaries).

### Phase A paths

`src/auditmanager/comparison/{README.md, raw_text.py, sheet_match_suggestions.py,
finding_match_suggestions.py, read_model.py, service.py, public.py}`,
`tests/unit/comparison/**`, `tests/integration/comparison/{conftest.py,
test_service_db.py}`, this report. No contract, migration, API, web, dependency,
composition root, global style, `CURRENT_STATE.md` or ref changed in phase A.
