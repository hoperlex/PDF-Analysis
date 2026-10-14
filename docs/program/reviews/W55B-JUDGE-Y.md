# W55B-JUDGE-Y — W55b consistency review (static)

**Reviewer:** a fresh-context subagent of the integrator, 2026-10-14.
**Subject:** `e1233e7a`; W55b range `9da3ea06..e1233e7a` (301 files, one merge of dev `9da3ea06`, 0.5.1).
**Verdict:** no blocker; one major finding (the upload envelope admits bundles that every run then refuses), six minor findings.

Method: static reading of the code against the plan (Part B), the freeze with amendment 1, `R-116`…`R-119`, the eight lane
reports and the contracts; `tests/contract/architecture/test_alr05_boundaries.py` run (2 passed); four in-process probes under
`.local/judge/` (`probe_float_int.py`, `probe_degenerate.py`, `probe_empty_pdf.py`, `probe_budget.py`, all `python -I` over the
committed fixtures; no database, no container, no network, nothing under `.local/portal-exports/` read).

## Holds

- **Lineage, bundle → version.** Four stored members under the registry's dotted manifest roles (`source.document`,
  `source.structured_companion`, `source.markdown`, `source.stamp_audit`; blob roles with underscores), one table
  (`ingest/bundle_members.py:63-72`). `_results.html` is hashed while unpacked and dropped; the fingerprint carries all five
  digests, `None` for an absent optional one (`bundle_members.py:93-99`, `service.py:433`). Every member is staged and verified
  before any is recorded, the `verifying` rows commit together, and step 6 binds blobs, version, manifest, the three counts and the
  command outcome in one transaction (`service.py:459-509`, `_commit_bundle`); no version with a partial member set can exist.
  Identical members share one content-derived blob (tested). The run's `input_basis_digest`/`frozen_input_digest` cover every
  manifest blob, the stamp audit included (`runs/commands.py:277`).
- **Version → run artefacts → API → screen.** The executor seeds the two members by contract role and feeds
  `source_preparation` (markdown + block list) and `page_geometry_extraction` (block list); absent roles are not supplied
  (`executor.py:791-818`). Outputs: `prepared.recognised_text` (optional), `geometry.portal_blocks` (optional),
  `geometry.page_crops` (required, `none` or `portal_image_blocks`), `geometry.crop_image` PNG blobs, each distinct PNG once and
  bound through the stage result. `listVersionPortalBlocks` joins the three JSON artefacts of **one** run, each read against the
  digest its stage result recorded; entries/records must be subsets of the block ids; a crop only on an `image` block of an `ok`
  page; empty recognised text and empty descriptions are omitted (`minLength: 1`) (`adapters.py:1097-1176`). «Блоки» reads
  `status`, never `items.length`, and tells "not yet run" from "bare PDF" by the manifest role (`entities/block/model/bundle.ts`).
- **Identity.** A block is addressed by `(version_uid, portal_block_id)`; the cursor key is page, ordinal, id and is located,
  not compared (`schemas/common.py:116-148`), so the non-unique ordinal never decides a position; file and member names are
  display only; the web's React key is position + id.
- **ALR-05 / AGENTS §4.** `analysis.recognised` and `analysis.geometry` import only `analysis.*`, `shared`, `storage.public`,
  `norms.public` (degeneracy) and, lazily, `ingest.public` (`PDFIUM_LOCK`). No runtime import cycle (`norms.public` does not load
  `analysis`). Transport schemas are data plus encoders. No silent fallback found: half a bundle, an unreadable member, a missing
  joined artefact and a digest mismatch all refuse with a typed error. The two temporary-file helpers are a deliberate copy
  (GEOMETRY decision 8), not a generic utility. Every `pypdfium2` call in `src/` is under the one lock.
- **The budget's arithmetic.** Recomputed independently: output cap 16 000 × $25/M = $0.40; (1.00 − 0.40)/$5 per M = 120 000
  tokens × 7/5 = 168 000 − 3 639 (prompt + schema) − 12 000 (framing) = **152 361** (the function returns the same). The start-up
  floor is exactly 221 329/280 000 = **$0.790461** (0.7904 → 93 673, 0.7905 → 93 701); the report's "$0.79 + 0.0005" is a rounding.
  The unit is one everywhere: `sum(len(get_text_range()))` per page at ingest, stored as `text_character_count`, compared at
  `startRun` and at `reauditRun` (the source's version, today's budget). NULL is accepted, never read as zero; an invalid budget is
  a `ValueError`, not "no budget". The check sits after the version read and before the key claim; an unseen key is refused with
  nothing written, a known key goes to the ledger and replays; no HTTP-level idempotency cache exists to replay a 422. The only two
  run-creating paths (`RunAdapter.start_run`, `ExecutionAdapter.reaudit_run`) both pass the budget, and the one `RunAdapter`
  construction (`composition.py:244-254`) passes `settings.input_budget_characters`. API and worker read the same `provider.env`.
- **Migration `0021`.** `page_count` 1..500; three nullable columns; all-or-none `CHECK`; an `IMMUTABLE` ascending-list function;
  downgrade refused on a >30-page version or any count; no row trigger fires. Agrees with ingest (`MAX_PAGES` 500, `MAX_BYTES`
  250 MiB), the block-list schema (`PAGES_MAX` 500), OpenAPI (`page_count` ≤ 500), the web envelope (500 / 250 MiB) and the repository,
  which writes all three counts or none. There is no ORM for `document_version` (raw SQL), and the domain contracts carry no page bound.
- **Sealed surface.** Measured 47 paths / 54 operations / 123 schemas and 24 codes; `web/openapi/openapi.json` is byte-identical
  (`8e1d0b23…`), pinned by `FRONTEND_LOCK.json`; `CURRENT_STATE.md:213-215` and `expected_facts.json` name head `0021`. Remaining
  "23-code" phrases are historical task files and revision notes.
- **Error codes and constraints.** `analysis_input_budget_exceeded` is 422/policy/not retryable with two integer details, in the enum,
  the envelope schema's `retryable` pin, both web catalogues and both web classifiers (start: `unsupported`; re-audit: figures
  appended). All 18 registered bundle values are raised by ingest and each has a web sentence. The busy refusal is
  `dependency_unavailable`/`upload_capacity` with `Retry-After`, as registered. A malformed path identity is `404` by the handler.
- **Stage and artifact versions (SEAL §4).** A bump is **not required now**: the registry is an unfrozen draft (its README defers the
  bump procedure to after freeze), `stage_version` is recorded provenance only (nothing caches or selects on it), a version without
  a bundle produces byte-identical outputs, and nothing consumes the widened outputs yet. W56's freeze should bump
  `page_geometry_extraction`/`geometry.page_crops` when `block_analysis` starts reading crops, since `1.0.0` now names two shapes.
- **Two readings.** `not_produced` for a pre-W55b bare version is handled on the screen ("У этой версии нет комплекта портала.").
  The pypdfium2-vs-pdfplumber "text layer" and the 50-character `textless_pages` threshold are documented side by side in
  `P02_SEAMS.md` §4.2; the hazard that remains is Y-1(d).
- **Dev 0.5.1 merge.** `VERSION` is 0.5.1; both release tests pin `0.5.1`; none of dev's 17 files (`globals.css`, sign-in,
  user-list, version-history, release notes, tests) differs between `9da3ea06` and `e1233e7a`, so W55b undid nothing.

## Findings

| # | Severity | Finding | Where | Disposition |
| --- | --- | --- | --- | --- |
| Y-1 | Major | **The upload envelope and the run stages judge the same stored members by different rules, so an accepted, immutable version can fail every run.** The halt removes text analysis too (`executor.py:850-855`), «Блоки» then says «появятся после первого запуска» indefinitely, and the version cannot be corrected. (a) **Confirmed by probe:** an integer-valued float (`"ordinal": 3.0`, `page_label`, `page_index`, `width_px`, `rotation`), which JSON Schema's `integer` and ingest's `_is_integer` accept, is refused `portal_blocks_invalid` by `source_preparation` (`page_index`) or `page_geometry_extraction` (the rest). (b) **Confirmed by probe:** a sub-pixel IMAGE box (`x1 − x0 = 1e-6`) passes ingest's `x0<x1, y0<y1` and fails the whole run `portal_block_degenerate`, while a page-box mismatch only marks the page and succeeds (plan §B3.7's policy). (c) Recorded by STREAM: PDFium now admits documents `pypdf`/`pdfplumber` refuse → `source_unreadable` or a page-count disagreement at run. (d) Plausible (RECOGNISED risk 2): a page where pypdfium2 sees text, pdfplumber none, and no block → accepted, then `validation_failed` at every run. | `ingest/bundle_envelope.py:120-123, 168-173, 208-213, 194`; `analysis/recognised/portal.py:78-79`; `analysis/geometry/portal.py:108-109, 131-140, 176-179`; `stages/page_geometry_extraction.py:253-262`; `W55B-STREAM-01.md:131`; `W55B-RECOGNISED-01.md:240` | `W55B-FIX`: ingest refuses (a) and (b) with `blocks_json_invalid` (strict JSON integers; the stage's degenerate bound as an IMAGE minimum), or the stages accept them, and (b) is downgraded to a visible per-block "no crop" instead of a run failure; (c)/(d) to the debt register with a rehearsal check on the real export |
| Y-2 | Minor | The crop address is built outside the transport seam: `entities/block` composes `getApiBaseUrl()` + the operation path, and two widgets take a URL-returning prop. `PC01_UI_SEAM.md` says a slice "never constructs a URL" and a widget "does not take … a URL". Recorded by the writer (risk 7) but not reconciled with the frozen seam. Confirmed. | `web/src/entities/block/api/crop-url.ts:23-45`; `widgets/portal-blocks/ui/portal-blocks.tsx:53`; `portal-block-card.tsx:122,172`; `web/docs/PC01_UI_SEAM.md:160,169` | Move `portalBlockCropUrl` into `shared/api` unchanged (the writer's own option), or amend seam §4 in the seam owner's lane |
| Y-3 | Minor | OpenAPI's "three rules [that] hold everywhere", rule 1: "Every identifier is `<prefix>_<ULID>` … every path parameter carries the pattern for its entity". `{portal_block_id}` (`blk_` + 32 hex, external) now contradicts it; only the W55B reseal paragraph at the end of the same description says otherwise. Confirmed. | `contracts/api/v1/openapi.json:7` (`info.description`, rule 1) | Next reseal: qualify rule 1 with the `external_identifiers` exception (prose only, no count moves) |
| Y-4 | Minor | The catalogue note claims the PDF member's constraint list ("pdf_magic_bytes, not_encrypted, … max_bytes"), but ingest also raises `parseable_pdf` and `non_empty` for the member (probe: an empty `.pdf` member → `content`/`non_empty`) and `plain_base_name` for the upload name; none of the three is registered anywhere in `contracts/`. The web has a sentence for `parseable_pdf` but shows `non_empty` as a bare token. Pre-existing constraints, restated incompletely by W55b. Confirmed. | `contracts/domain/v1/error-codes.json:117`; `ingest/envelope.py:150-163, 199, 341, 410`; `web/src/entities/document-version/model/upload-envelope.ts:158-165` | `W55B-FIX` or the next domain revision: list the three in the note; add a `non_empty` sentence |
| Y-5 | Minor | The budget's inputs are not quite the run's. (i) Plan §B3.3 derives it "from the configured model's context and the $1 ceiling"; the context is not modelled (BUDGET decision 1) although `P02_LOCK.json` pins `"context": "1M"`, so from a ceiling of about $5.40 the budget admits a request the context cannot hold, and R-118's "refused up front" becomes a provider failure after the run exists. (ii) The model default is the literal `"claude-opus-5"` in `settings.py`, while the run's provider config defaults to the lock's primary: equal today, divergent if the lock's primary moves, and the budget would then be priced for the wrong model. Plausible (operator settings). | `analysis/text/budget.py:38-42`; `docs/program/P02_LOCK.json:61-65`; `bootstrap/settings.py:280`; `analysis/text/config.py:124`; `W55-PLAN.md:437` | Cap the budget by the lock's context and default `model_id` from `provider_lock().primary_model_id` (W56 opens the arithmetic anyway) |
| Y-6 | Minor | `R-116` says the portal HTML is "kept as a digest only"; the implementation keeps its SHA-256 only inside the opaque payload fingerprint. No column, manifest entry or command outcome holds it, so a version cannot say which HTML accompanied it. Plan §B3.4's "the fingerprint covers" is met. Plausible (a reading of "kept"). | `ingest/bundle_members.py:93-99`; `ingest/service.py:433, 503-506`; `OWNER_RULINGS_2026-09-17.md:1531` | Owner reading; if "kept" means retrievable, add `results_html_sha256` to the upload command's outcome |
| Y-7 | Minor | The portal read model (the three-artefact join, its integrity rules and the `block_type`/`geometry` vocabulary) lives in the composition root's `BlockAdapter`, not behind `analysis.public`. W56's "serving by run or evidence" for region evidence will need the same join, which invites a second copy. Each «Показать ещё» re-reads and re-verifies three whole artefacts. Plausible (pattern inherited from `getVersionBlocks`). | `bootstrap/adapters.py:1051-1176, 1232-1262` | W56 plan: one analysis-side reader for the join; measure the 500-page page latency at REHEARSAL |

## Out-of-grant edits (item 6)

- `runs/executor.py` (RECOGNISED, GEOMETRY): **needed** (otherwise no stage ever receives a member), **minimal** (one seeding loop and two role tuples), **correct** (contract roles; absent roles not supplied; the stamp audit deliberately not passed).
- `analysis/stages/extraction.py`: **needed** for §B3.3's path form; **minimal**; **correct**: the bytes form is unchanged and `pypdf` reads an open file, not a path it would slurp.
- `ingest/public.py` (`PDFIUM_LOCK` re-export): **needed** (one lock per process); **minimal**; **correct**; nit: it is not in `__all__`.
- `tests/integration/runs/test_a_halted_chain_reaches_a_terminal.py`: **forced** by the streamed read; **minimal** (`open_stream` substituted like `read`); **correct**.
- `tests/integration/api/test_portal_block_routes.py`: **needed** (the stub assertion became false in GEOMETRY, the whole-body read in STREAM); **correct**. Its `422` for a malformed id is the bare router's; the served app answers `404`, as its docstring implies.
- `web/src/shared/api/authorization.ts`: one comment ("fifty-four operations"); **needed** by the prose guard; **correct**.
- `tools/fixtures/build_ar_corpus.py` (the brief's `ar_corpus/` path does not exist): **needed** (shared `SHA256SUMS`); **minimal** (+20 lines); **correct**, but its `--check` now carries the `bundles/` lines through unverified; only `build_portal_bundles.py --check` judges them.
- `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md` and `artifacts/manual-alpha/**`: **needed** (the deleted fixtures); **correct**: `sha256sum -c artifacts/manual-alpha/SHA256SUMS` passes, the pack's SHA-256 is the README's `89809d4e…`, and the six refusals match the code.
- `web/src/entities/execution/model/failure.ts` and `web/src/entities/audit-run/**`: **needed** (the queue's re-audit classifier lives in `execution`); **minimal**; **correct**; the cross-entity import goes through the public entry, which ALR-06 permits.
- `api/schemas/blocks.py` (docstring): **needed** (it said crops are always empty); documentation only; **correct**.

## Needs the database or the rehearsal

- A fresh upgrade, an upgrade from `0020` with rows and the refused downgrade, on the gate's database (SEAL ran them on its lane stack only).
- The real export through «Блоки»: 129 blocks and 47 crops looked at. Whether any real page's CropBox differs from its MediaBox with a near-equal aspect: the page-box check compares aspect only, so a small, uniform trim would shift crops without a mismatch.
- Y-1(c)/(d) on real documents: per page, pypdfium2 against pypdf/pdfplumber (page count and text presence).
- The 500-page low-text run: geometry took 20.7 s for 30 pages, and the full list read joins three whole artefacts per page request.
- One live run of the real АР set, to set its measured input tokens against the 1.4 characters-per-token margin; and the stand's `AUDITMANAGER_RUN_COST_CEILING_USD` must be empty or ≥ 0.80 before publication, or the processes refuse to start.
