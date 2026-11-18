# ADR-0025: Comparison modules: «Сравнение версий» and «Сравнение стадий» on a comparison-local queue and spend journal, a raw-then-AI evidence stack and bounded compute

- Status: accepted
- Date: 2026-10-27; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: owner poll answers `Q-CMP-1`…`Q-CMP-11` of 2026-10-27, numbered `R-147a`…`R-147k` in `docs/program/OWNER_RULINGS_2026-09-17.md` section 3.47 (full wording: `docs/program/dispatch/COMPARE-MODULES-PLAN.md` section 0); the plan's judging rounds (`R3-*`, `docs/program/compare/REVIEW-R3.md`); the addenda of `CMP-MEASURE-01A` and `CMP-MEASURE-01`. A value marked «decided by CMP-ADR-01, revisable by CMP-MEASURE-01» is the architect's choice inside those answers, not confirmed by the owner, and changes only by a dated addendum (decision 27).
- Amends: nothing is superseded. It extends `ADR-0013` to the two new modules and, while the versions module is on, withdraws the controls `COMPARE-PERSISTED-SUMMARY-01` added to the version-scoped screen (decision 13).
- Related: `ADR-0007`, `ADR-0011`, `ADR-0012`, `ADR-0013`, `ADR-0021`, `ADR-0022`, `ADR-0024`; principles P-01…P-18. Owner: repository owner / `CMP-ADR-01`.

Every `CMP-*` seal and lane cites a decision of this ADR as «ADR-0025 decision n» instead of re-deciding it.

## Context

Comparing document versions and П/Р stages needs durable queued work, model calls that carry money and images, and heavy raster compute on a 4 GiB host (`R-146ad`) with one worker slot (`R-146j`). The product cannot carry it as it stands: a Job is a Run in the schema, the effect journals, `model_call`, the frozen contract and the claim path; the model channel carries one image per request and one work kind; the storage boundary has no multipart and no delete of a published blob; no raster or PDF-writer dependency is pinned. Tree facts: `docs/program/dispatch/COMPARE-MODULES-PLAN.md` section 2, `docs/program/compare/REVIEW-R2.md`, `REVIEW-R3.md`.

Owner answers: `Q-CMP-1`…`Q-CMP-11` are `R-147a`…`R-147k` in order; `Q-CMP-4` (drawing crops may go to a model) widens accepted risk `A-2` of `ADR-0022`, recorded as `A-12`; `Q-CMP-11` makes the full gate before the beta debt `D-255`.

## Decision

### 1. Where the code lives (plan `A-1`, `R3-22`, `R3-30`)

New comparison logic lives in subpackages of `src/auditmanager/comparison/`. Plain-PDF admission belongs to `ingest` and `documents`, the run-start refusal to `runs`, durable work to `comparison/work` (hosted by `workers`), model calls and images to `executors`. Contexts reach one another only through `public.py`; the composition root adapts the ports. Production hotspots (`PROD-20`, `PROD-05b`, `PROD-07`) keep their owners: a seal edits them only with that owner's grant.

### 2. Identities (plan `A-2`)

`DocumentUid` is the series; the «шифр» is stamp metadata an expert confirms, never identity. Every new identity is `<prefix>_<ULID>` of the catalogue (`contracts/domain/v1/identifiers.json`), generated once, never parsed; a path, file name, display number, «шифр» or sheet number is never an identity or a foreign key; resume and grouping identities of an upload are opaque ids plus a declared sha256 and size. A «content-keyed» row has a ULID id **and** a unique content-key digest column that is never a foreign key. The seal that adds a table adds its catalogue entry. Prefixes (decided by CMP-ADR-01, revisable by CMP-MEASURE-01; the catalogue names each entity): `cvo_` `cpr_` `cmx_` `cme_` `cak_` `cser_` `csp_` `cbt_` `cq_` `stp_` `sas_` `slk_` `crp_` `crn_` `cai_` `ccd_` `cdv_` `crt_`, and `ctn_`, `ctp_` added by `CMP-SEAL-C1`. Content-keyed: `cpr_` (page profile), `csp_` (sheet-pair result, decision 15), `ccd_` (card, decision 22).

### 3. Evidence layers and the effective matrix (plan `A-3`)

Raw deterministic layers (profiles, the algorithmic matrix, sheet-pair results, text fragments, differences) are immutable rows or content-addressed blobs. AI layers (pair-check answers, accepted AI links, descriptions, classes, syntheses, report text) are separate rows that reference raw ids and never rewrite them (`AGENTS.md` section 4; `ADR-0013`). The **effective matrix** is a read model: the algorithm, then accepted AI links (labelled «ИИ», never an expert act), then manual edits (manual wins); a UI «final» layer is a read model over raw and AI rows. Every AI answer passes a strict validator (schema, existing ids only, exact coverage, no invented numbers or designations); a failure keeps the deterministic layer visible and marks the AI layer `failed` or `partial`. A transition whose pairs depend on an AI link is marked in the series verdict, the MD summary and the report; masked raw differences stay listed in «Показать исходные текстовые различия» with their AI class.

### 4. Comparison work is durable and comparison-local (plan `A-4`, `R3-13`)

Comparison work does **not** enter `job` (alternative 1). The comparison context owns a durable queue (tables `comparison_work`, `comparison_work_attempt`) copying the Lease pattern of `jobs`; no progress lives only in memory. The worker hosts the comparison loop as a second loop, as `probe_runner`, counted against `AUDITMANAGER_WORKER_SLOTS`. `executor_task` gains the origin `comparison_call`, and the one-active-run-per-connection check also counts active comparison AI work under the same advisory lock. The «Очередь» screen and its contract stay run-only. **Handler registry** (decided by CMP-ADR-01, revisable by CMP-MEASURE-01): `comparison/public.py` exports one tuple of handler factories, each with a unique `kind`; the loop refuses to start on a duplicate kind or a `comparison_work.kind` with no handler.

### 5. Spend journal and the pre-call breadcrumb (plan `A-4`, `R3-01`, `R3-26`)

Comparison AI is recorded in its own journal `comparison_model_call`, with the columns and CHECKs of the `comparison_summary` precedent; a row lives `prepared → sent → completed | failed | unknown`. The `prepared` row is committed in its own transaction **before** the adapter is called, as `provider_call_effect` does. On reclaim an item whose row is `prepared` or `sent` without a completion is never re-sent automatically: it becomes `spend_unknown` and only an explicit «Повторить» clears it. On the pull channel the `executor_task` row is the breadcrumb; on HTTP direct the journal row is. The deployment spend that `R-29` reads is the union of the two journals; the per-run cost summary is untouched.

### 6. Priority and operator control (plan `R3-07`)

Section runs have strict priority: the comparison loop claims only when no Run is claimable and yields between items (an item is one page or one pair, never a series). Comparison AI takes the executor connection per call, not per job. Comparison work honours the global pause (read through `execution/public.py`) and a module that is off (decision 23). «Очередь» gets an admin-visible read-only section «Сравнение» (`CMP-WORK-01`). Measured throughput of one slot: `docs/program/compare/MEASURE-ENGINE-01.md`.

### 7. Project erase (plan `R3-25`)

`CMP-SEAL-C0` adds the non-terminal states of the two work tables to `NON_TERMINAL_STATES` (`scripts/recovery/project_erase.py`) with a test deriving that map from the migration's CHECKs; an erase during a leased comparison item is refused. The application role cannot lock a `project` row, so the queue relies on item and attempt row locks plus `ON DELETE RESTRICT` on `fk_comparison_work_project` (this replaces the planned share lock on `project`). The blob reference audit reports unreferenced comparison blobs. Every new table is reachable from `project` by foreign keys, so the erase closure holds.

### 8. Compute runs in a child process under a kernel ceiling (plan `R3-03`)

Every profile, engine and tile computation runs in a child process that sets `RLIMIT_AS`, a CPU ceiling and a wall ceiling before it loads anything, as `ingest/pdf_reader.py` does. Defaults (decided by CMP-ADR-01, confirmed by CMP-MEASURE-01): **768 MiB** address space per item for render, registration and tile children, **300 s** CPU, **600 s** wall (below the 900 s attempt watchdog); the child running `pdfplumber` words and lines gets **1024 MiB**. One item is one page per child. Any end without a result (`MemoryError`, a signal, a CPU stall) is a typed `needs_review` with reason `RENDER_FAILED` on that item only, never «Совпадает». The comparison worst case is added to `PROD-05a`'s measurement so that the `AD-04` limits include it.

### 9. Bytes, pixels, masks and tiles: refusal caps and no eviction (plan `A-5`, `R3-05`, `R3-06`, `R3-23`)

There is **no eviction** of stored blobs in the beta: the storage boundary has no delete of a published blob, and a delete from a lane would be a dual write (alternative 3). Previews and thumbnails are stored once per page. Masks are stored once per non-`same` pair as **one bit-packed blob** written by the engine in the worker; nothing is stored for a `same` pair. The API never calls PDFium: it reads mask bytes and reduces them with `numpy`. The whole tile pyramid is **not** stored: the worker stores preview and thumbnail per page and may store tile levels 2 and up, while levels 0 and 1 are rendered on request in a child process under the 768 MiB ceiling, never in the API process; whatever a level keeps counts in the page budget. The full-page renderer runs under the existing `PDFIUM_LOCK`.

Abuse and capacity are bounded by refusal, never by deletion. Defaults (decided by CMP-ADR-01, revisable by CMP-MEASURE-01); version admission stays the existing envelope (250 MiB, 1–500 pages, unencrypted):

| Quantity | Value |
| --- | --- |
| Working raster per page | at most **40 Mpx**; registration dpi = `min(200, floor(sqrt(40e6 / (w_in × h_in))))`; a page that cannot be kept under the cap is refused with a typed state |
| Stored bytes per project | at most **8 GiB**, refused when declared plus stored bytes pass it, and per item when derived data would |
| Batch | at most 10 000 files and 100 projects (the original's limits), **8 GiB** declared bytes and **10 000** declared pages, refused before the first part |
| Active batches | one per account, **two** per installation (`R-146j`) |
| Readiness | finding `comparison-disk` when the object store's filesystem has under **11 GiB** free (the 8 GiB cap plus the 3 GiB reserve of the heavy-step stop rule) (`D-205`) |

Declared pages are verified when the item is read; a mismatch refuses that item. A refusal is a typed reason under an existing error code (decision 25).

### 10. Upload transport and multipart staging (plan `A-8`, `R3-04`)

Every comparison upload is chunked, 16 MiB per chunk, on the default proxy location (under its 32 MiB body cap; no proxy file changes). The storage port gets S3 multipart staging from `CMP-STORAGE-PARTS-01`: an opaque upload token persisted **before** the first part, `UploadPart`, `Complete`, `Abort`, verification of the whole object; a chunk has a database owner (a declared blob) before its bytes are staged. A database-owned sweep of expired multipart uploads, run as comparison work, aborts them (alternative 6). «Удалить пакет» is renamed «Отменить пакет»: it aborts parts never completed; bytes of completed versions are removed only by the operator's project erase (`R-146c`). File names and folders only feed the proposal the user confirms; the batch limits of decision 9 are typed refusals; the portal-bundle upload is unchanged.

### 11. Plain-PDF admission, the version mark and the current-version rule (plan `A-8`, `R3-16`, `Q-CMP-5`)

`ingest` admits a plain PDF for comparison under a distinct manifest role (not `source.document`), so the existing start-run check refuses it. `CMP-INGEST-01` adds the reason `comparison_only_version` and its Russian sentence under the existing code `analysis_input_invalid`; the catalogue stays at 27 codes. Comparison-only admission uses its own **envelope policy** (per-page element limit 1 000 000; the portal envelope's 400 000 would refuse the real set measured), rendering and extracting only in ceilinged children; the portal-bundle envelope is unchanged. `DocumentVersion` gains an upload-kind field so every screen marks the version «загружено без пакета портала» and disables its run start (`CMP-VERSION-MARK-01`). Passports and fragments come from the page profile; portal artefacts are optional extra evidence. Stage (П/Р) and section of a plain PDF are a stamp proposal an expert confirms through the existing classification operations. A scan gives no TEXT evidence and is compared as an image only. A comparison-only version never becomes `current_version_uid` of a document that has a portal version.

### 12. ZIP sets of whole stages (plan `R3-17`, `Q-CMP-10`)

`CMP-INGEST-ZIP-01` parameterises the `bundle_archive` reader with a set policy: at most N entries (N is the slice's), a total of at most 2 GiB, a PDF envelope per member, no nested archives beyond one level, names never identity. The policy parameter is the only edit of `bundle_archive.py`; the slice has its own security judge.

### 13. One truth for sheet pairs of versions (plan `A-12`, `Q-CMP-8`)

The effective matrix (decision 3) is the only canonical store of «page X of version A ≙ page Y of version B». `CMP-SEAL-C1`'s migration converts every active approval of `comparison_sheet_link` (`0035`) into a manual matrix edit with its actor, time and `0035` ids in its provenance; the `0035` rows stay as immutable history. While the versions module is on, `approveSheetPairing`, `withdrawSheetPairing` and `generateComparisonSummary` answer `dependency_unavailable` with a reason naming the new module, and the version-scoped screen drops those controls (its heading becomes «Сравнение с другой версией: находки»). The web edits belong to `CMP-VC-UI-01`.

### 14. Matrix revisions (plan `R3-10`)

An accepted AI link binds the algorithmic matrix revision and the cell state it answered; it applies only while that cell is still unmatched or doubtful, otherwise it shows as superseded. «Применить сопоставления (N)» carries the base matrix revision; a mismatch answers `conflict` with a reason and the client rebases its draft. A manual edit binds the version-order revision; a reorder marks the edits whose cells no longer exist as orphaned and never applies them silently.

### 15. Cache key (plan `A-5`, `R3-09`)

A sheet-pair result is keyed by the content Merkle of page A (content stream and every referenced resource, XObjects and images included), the same for page B, the annotation hashes, the sorted link reasons, the split part, the parameters and `ALGO_VERSION`; the unique key also includes `project_uid`, so a result is reused within a project only. It is the content-key digest of `csp_`. The same pages with a MEDIUM link give `needs_review`; an annotation-only change gives `different` in `annotations`; a scan with a replaced image is not `same`.

### 16. Expert acts (plan `A-7`, `R3-29`)

Stage-card verdicts («Принято» / «Не принято» with a reason) are append-only, keyed, audited and need the expert role (`R-60`). Manual matrix edits, stage links and «Порядок версий» are expert acts with history; an administrator without the expert role is refused. The version order never changes the documents' ordinal that runs and finding carry-over use (`D-5`). Version comparison has no verdict in the original; its AI texts keep the label that they are model output not confirmed by an engineer, as `R-146ba` kept it above the comparison summary.

### 17. Work kinds and routing (plan `A-6`)

Model work goes through «Исполнители» only. Five work kinds are added, names fixed here: `comparison_pair_check`, `comparison_sheet_changes`, `comparison_spec`, `comparison_stage_review`, `comparison_report`. They join the executor work kinds (the contract enum `ExecutorWorkKind` and its CHECK, widened by `CMP-SEAL-C2`'s migration) and are routed in «Назначения». The routed connection's model is pinned (`R-133`: a reply from another model is a typed refusal) and every test uses recorded mode. An operator routes the new kinds on the stand after the code (plan `O-6`).

### 18. Images and server-side gating (plan `A-6`, `R3-15`, `Q-CMP-4`)

`CMP-EXEC-IMAGES-01` extends the image channel from one portal-block PNG to several images per request, each addressed by an opaque crop reference (crop id, blob id, sha256, size, media type) not bound to a portal block,. Limits (decided by CMP-ADR-01, revisable by CMP-MEASURE-01): at most **8** images per request, **16 MiB** per image (the existing `MAX_IMAGE_BYTES`) and **32 MiB** in all; the estimate counts images and image bytes. `CMP-SEAL-C0` seals the contract part; the one-image field of `ModelRequest` is granted to `CMP-EXEC-IMAGES-01` after `PW5`'s `SX` lane has merged. **Gating is on the server.** The claim request carries the runner's declared `max_images`, absent meaning 1; the server never hands out a task with more images than declared. A task a runner nevertheless fails because it does not support several images fails with `image_input_unsupported` and never answers on a subset of the images.

### 19. Money (plan `R3-08`, `Q-CMP-7`)

Estimates are in USD from the pinned rates. Ceilings are USD 10 per job and USD 50 per day per installation, enforced before each call with the meter's before/after checks. Each consent binds {estimate digest, USD ceiling, connection revision, pinned model}; a change of route or revision, or an actual spend above 1.2 × the estimate, pauses the job with a typed state and asks for a new consent. The launch queue asks for AI consent per set only when its estimate exists. Every new write carries an `Idempotency-Key`. `not_metered` connections are not limited by money. Live spend follows `R-29`.

### 20. No hidden change (plan `R3-02`)

A model's SAME or MOVED on a fragment whose deterministic status is CHANGED, REMOVED or ADDED becomes UNCERTAIN: a REVIEW card, no mask. MOVED is accepted only with a found target outside the accepted link. An invented number or designation turns only the affected decision into UNCERTAIN. An expert may move any SERVICE_STRUCTURE item or masked fragment into a REVIEW card, as an expert act with history. The journal, the Excel and every PDF/HTML print «Скрыто ИИ как одинаковое: N; отнесено ИИ к служебным: M; экспертом не проверялось»; the client PDF report prints a recall line («изменённых листов N, описано K, отброшено проверкой D») and the unconfirmed label on every page. An AI SAME never removes a raw difference row.

### 21. Stage pairs, chain runs and staleness (plan `A-9`, `R3-32`, `Q-CMP-2`)

A stage pair binds `DocumentUid`s: one on the П side, one or an assembly of several on the Р side. Each chain run pins the exact version ids of every member. A newer version marks the run stale («Есть новые документы — сравнение не обновлено»); staleness compares stored input digests, never timestamps. Cards and verdicts belong to the run they were made on.

### 22. Cards, verdicts and carry-over (plan `A-10`, `R3-11`)

A card is a Stage-5 aggregate of the chain document: class (PROJECT_CHANGE, SERVICE_STRUCTURE or REVIEW), category, title and its atomic evidence ids; its identity is a digest over the class and the sorted evidence ids. Verdicts are taken on PROJECT_CHANGE and REVIEW cards; SERVICE_STRUCTURE is one collapsed block without verdicts; «Подтверждено изменений» counts accepted PROJECT_CHANGE and REVIEW cards; «Шифр» and «Раздел» come from the documents deterministically. «Система» is a classifier field from a **closed list that the validator enforces**, its members fixed by `CMP-SEAL-C4` before `CMP-STAGE-AI-01` starts. Evidence ids are content-keyed. A verdict binds to the evidence set, not to the model's class or grouping, and carries over **per evidence** to a newer run; a card whose evidence set is a superset or a subset of a decided one shows «частично перенесено» and never loses a verdict silently; a verdict whose evidence digest changed is shown as stale. The Excel journal (`CMP-STAGE-REVIEW-01`) has no generic sheet writer (`R3-34`, `AGENTS.md` section 4); the PDF export uses the writer of decision 24.

### 23. The module flag and the screens (plan `A-11`, `R3-12`, `R3-31`)

The module set `AUDITMANAGER_COMPARISON_MODULES` (`none`, `versions`, `versions,stages`) reaches the web **through the contract**: an additive field of the product-version read or of the session subject, added by `CMP-SEAL-C0`; the navigation and `screenDecision` filter by it, and the web never imports `server-env.ts` for it. The worker loop and every comparison command refuse when the module is off, and turning a module off pauses its queued work. A module that is off has no menu entry, its operations answer `dependency_unavailable` and its route still exists in the tree and the journey manifest. New FSD slices: `version-compare`, `stage-compare`, `version-series`, `stage-pair`; the project is chosen on the screen. Styles are the product's own (`--am-*`, no UI library). On our screens the original's «проект» (a document set) is written «комплект (шифр)»; «проект» keeps our meaning. Rollback is the flag: a wave that cannot finish leaves its module off.

### 24. Dependencies (plan `A-5`, `R3-20`, `Q-CMP-9`)

`numpy` (BSD-3), `opencv-python-headless` (Apache-2.0) and `reportlab` (BSD) with a free Cyrillic font whose licence allows embedding. `CMP-SEAL-C0`, which owns the root lock slot, takes the three packages once, recording the bundled licences and the image size, before the profile and engine lanes start. The font file and its licence live together under `comparison/report/fonts/**` (`CMP-VC-REPORT-01`). PyMuPDF stays excluded (`OD-01`). A dependency that `Q-CMP-9` did not approve is a STOP.

### 25. Contract surface of the seals (plan section 4.0 rules 3–5, `R3-21`)

Seals are serial (C0 → C1 → C2 → C2 FIX → C3 → C4); each holds the contract and the migration head from its start to its merge, is one additive minor bump of the API contract and takes the migration head plus one, and owns the per-table family of the tables it adds (schema coverage, grants, purge, erase, blob audit). No new error code is added unless no existing code fits; a new reason under an existing code is the default. A lane that needs a new contract field STOPs to the wave's FIX slot and never edits the contract. Every new operation is reviewed for exposure (`CMP-EXPOSURE-01`). A sealed operation is a stub answering `503 dependency_unavailable` until its lane implements it. Before wave C0 the integrator records the poll answers as rulings (`R-147a`…`R-147k`), widens accepted risk `A-2` of `ADR-0022` to drawing images (`A-12`), extends `R-135` to the CMP waves (`R3-33`) and tells the executor workstream and the `PROD` owners of decision 1 (plan `O-8`).

### 26. Deviations from the original (plan section 1.3, `Q-CMP-10`, `R3-18`)

- **Accepted — `D-2`.** GRAPHIC evidence in stage cards is an addition beyond the original, allowed only for 1↔1 links whose registration is reliable; otherwise the card says «графика не проверялась».
- **Withdrawn — `D-1`.** The automatic link repair behaves as in the original: with HIGH proof it may change an expert's link, as a recorded, revertible act shown «Исправлено автоматически».
- **Withdrawn — `D-3`.** The AI runtime follows the original: a main call, one technical retry, one model context request and one unparsed-record pass per item; a 429 waits 20, 60, 120, 300 and 600 s; quota and authorisation failures pause the job with a typed state. Every call goes through the breadcrumb of decision 5.
- **Built as in the original.** The «ZIP-комплект» upload, with the safe reader of decision 12.
- **Deliberate, unchanged.** `D-4` grouping in tab 4 really groups and exports work; `D-5` the version order never changes the documents' ordinal.
- **Unread sources (`R3-18`).** A slice whose original source `CMP-ORIGINAL-READ-01` leaves unread is tagged `[own design]` and accepted on answer keys.

### 27. Measurement gates, fixtures and the right to revise (plan `R3-14`, `R3-19`, `Q-CMP-10`)

`CMP-FIXTURES-01` merges first after `CMP-SEAL-C0` and adds a realistic A1 generator (about 75 000 elements). `CMP-MEASURE-01` runs between C0 and the merge of the C1 engine on one version set downloaded read-only from the original's instance into `.local/` (outside git), never sent to a model and deleted afterwards; `CMP-ENGINE-01` merges only with the A1 time/RSS/bytes gate met on that set or on the generator. One live run per AI work kind on three synthetic items under USD 0.50 each records the validator pass rate; below 80 % the slice STOPs. **Every value marked «decided by CMP-ADR-01, revisable by CMP-MEASURE-01» is revised only by a dated addendum to this ADR** giving the measured figure, the command and the tree; a lane never changes such a value on its own.

## Measured values

The values of the two measurement addenda are folded into decisions 6, 8, 9 and 11. The items keep their numbers: tests and task files cite them as «addendum item N».

### CMP-MEASURE-01A, 2026-10-27 (`docs/program/compare/MEASURE-RENDER-01.md`)

1. **Decision 8 (child ceilings).** The `pdfplumber` child gets 1024 MiB.
2. **Decision 9 (caps and storage).** The 40 Mpx cap and the dpi rule stay; the whole pyramid is not stored.
3. **Admission (decision 11).** Comparison-only admission has its own envelope policy.

### CMP-MEASURE-01, 2026-10-29 (`docs/program/compare/MEASURE-ENGINE-01.md`)

1. **Decision 8 ceilings stay.** A 768 MiB extraction ceiling would pass by only 39.6 MiB, so 1024 stays.
2. **Decision 9 caps stay.** The largest working raster was 39.59 Mpx of 40; measured storage is 1.29 MB per page and 0.33 MB per masked pair.
3. **Throughput for decision 6 (one slot).** Held by `MEASURE-ENGINE-01.md`.
4. **The worker's own footprint is not bounded by a child ceiling** (up to 363 MiB; a matrix build runs in the worker, accepted for the beta).
5. **A page-profile item is a whole version**; against the 900 s attempt watchdog a 500-page version would need two of its three attempts. `CMP-C1-FIX-C` bounds the work of one item.

## Left to the named slice

This ADR adds no decision for these: the prefixes of `comparison_work_attempt` and `comparison_model_call` (`CMP-SEAL-C0`; new prefixes, not `att_` or `mc_`; the catalogue holds `cqa_` and `cmc_`); the members of the «Система» list (`CMP-SEAL-C4`); the carrier of the module flag (`CMP-SEAL-C0`); the font family (`CMP-VC-REPORT-01`; DejaVu Sans is in the tree) and the dependency pins (`CMP-SEAL-C0`); the entry limit N of a ZIP set (`CMP-INGEST-ZIP-01`); the pyramid levels beyond decision 9 (`CMP-PROFILE-01`, `CMP-VIEWER-01`); which seal first carries `comparison_stage_review` (`CMP-SEAL-C2` or `CMP-SEAL-C4`; one seal must own the CHECK's migration).

## Consequences

- Positive: comparison work cannot starve or break the primary product (own tables and journal, strict priority, the global pause); a paid call is never repeated by a reclaim; raw evidence is immutable and a bad page costs one item.
- Cost: a second queue, journal and hosted loop duplicate the Lease pattern of `jobs` and must be kept equal to it by tests; every future spend reader must remember the second journal.
- Cost: with no eviction and no delete of published blobs, a project's bytes stay until an operator erases it; a full disk is the failure mode, and the caps and the readiness finding are its only defence.
- Cost: several images per request widen accepted risk `A-2` of `ADR-0022` to drawing images (`A-12`), and a remote runner that is not updated receives no image task.
- Cost: three native dependencies enter the root lock and the image; the gate before the beta is debt (`R-147k`, `D-255`); a wrong marked default costs a refusal or a slow page, not a wrong verdict.

## Alternatives considered

1. **A shared `job` subject for comparison work** — rejected: a Job is a Run throughout the schema (`REVIEW-R2` `R2-02`).
2. **The live V3 pipeline of the original for «Сравнение стадий»** — rejected by `Q-CMP-1`.
3. **Eviction of stored blobs when disk runs low** — rejected: no delete of a published blob, and a lane delete is a dual write.
4. **Automatic re-send of an item whose call may have been sent** — rejected: it pays twice.
5. **Publishing every upload chunk as a canonical blob** — rejected: it doubles storage with no delete.
6. **A sweep through `jobs/temporaries.py`** — rejected: it never touches the object store (`R3-04`).
7. **Masks or tiles rendered in the API process** — rejected: PDFium sits behind one process-wide lock.
8. **Trusting a model's SAME on a fragment the deterministic layer calls CHANGED** — rejected (decision 20).
9. **PyMuPDF for raster and text** — rejected: AGPL, blocked by `OD-01` (`Q-CMP-9`).
10. **Reading the module flag from the environment in the browser layer** — rejected (`R3-12`): the contract carries it.
11. **Keeping the `0035` approval buttons beside the matrix** — rejected by `Q-CMP-8`: two stores of one fact drift.
12. **A `limit_req` rule at the proxy** — rejected: its zone key is empty for uploads, so they are never throttled.
13. **Keeping deviations `D-1` and `D-3`** — rejected by `Q-CMP-10`.

## Verification

Each commitment is checked by a test that must fail under a quoted mutation of the guarded behaviour (`R-70`).

| # | Commitment | Test |
| --- | --- | --- |
| 1 | New prefixes are unique (decision 2) | `tests/contract/test_domain_identifiers_schema.py` |
| 2 | No foreign key from the comparison tables to `job`, `attempt` or `audit_run` (decisions 4, 5) | `tests/integration/db/test_comparison_foundation_migration.py` |
| 3 | Reclaim never re-sends a `prepared`/`sent` call (decision 5) | `tests/integration/comparison/spend/test_reclaim_spend_unknown.py` |
| 4 | Claims only when no Run is claimable; honours the pause (decision 6) | `tests/integration/comparison/work/test_claim_gates.py` |
| 5 | An erase during a leased comparison item is refused (decision 7) | `tests/integration/recovery/test_comparison_foundation_erase.py` |
| 6 | A child past its address-space ceiling ends one item as `RENDER_FAILED` (decision 8) | `tests/unit/comparison/engine/test_ceilings_and_failures.py` |
| 7 | A page above the pixel cap is refused, not rendered (decision 9) | `tests/unit/comparison/profile/test_pixel_cap.py` |
| 8 | A comparison-only version is never `current_version_uid` (decision 11) | `tests/integration/ingest/comparison_pdf/test_confirmation_rules.py` |
| 9 | Manual beats AI; a stale revision answers `conflict` (decisions 3, 14) | `tests/unit/comparison/matrix/test_effective.py`, `tests/integration/comparison/matrix/test_edits.py` |
| 10 | The cache key follows its inputs (decision 15) | `tests/unit/comparison/engine/test_key_and_outcome.py` |
| 11 | An old-shape claim is offered no multi-image task (decision 18) | `tests/integration/executors/test_claim_image_gating.py` |
| 12 | Consent precedes a call; 1.2 × the estimate pauses (decision 19) | `tests/integration/comparison/ai_jobs/test_start_with_consent.py`, `test_spend_pause_and_reads.py` |
| 13 | A model SAME on a CHANGED fragment becomes UNCERTAIN (decision 20) | `tests/unit/comparison/stage_ai/test_core.py` |
| 14 | A rerun carries 100 % of the verdicts; a changed digest shows stale (decision 22) | `tests/integration/comparison/stage_review/test_service.py` |
| 15 | A module that is off pauses its work (decision 23) | `tests/integration/comparison/work/test_claim_gates.py`, `tests/integration/composition/test_comparison_module_env_wiring.py` |
| 16 | Every `comparison_work.kind` has exactly one handler (decision 4) | `tests/integration/comparison/work/test_worker_hosting.py` |

## Revisit trigger

A further `CMP-MEASURE-01` run revises a marked value; the production disk size is known; a second worker slot or a service-level objective is wanted (`ADR-0024` section 5); the storage boundary gains a delete of published blobs; the owner widens the comparison beyond the plan's sections; human-confirmed cards disagree with the deterministic layer often enough to change decision 20.

## History

- 2026-10-27 — accepted on `Q-CMP-1`…`Q-CMP-11`; marked values are the architect's choice, revisable by `CMP-MEASURE-01`.
- 2026-10-27 — addendum `CMP-MEASURE-01A` folded into decisions 8, 9, 11 (1024 MiB extraction child, the dpi rule, no whole-pyramid storage, envelope policy).
- 2026-10-28 — addendum `CMP-SEAL-C1`: prefixes `ctn_`, `ctp_`; decision 7's share lock on `project` replaced by row locks plus `ON DELETE RESTRICT`.
- 2026-10-29 — addendum `CMP-MEASURE-01`: ceilings and caps confirmed, measured storage figures, throughput into decision 6.
- 2026-11-18 — compressed (ADR-OPTIMISE-01); the full earlier text: git show fb6c2203e:docs/architecture/adr/ADR-0025-comparison-modules.md
- 2026-11-18 — status statements updated to dev fb6c2203e: the poll answers are numbered `R-147a`…`R-147k` and the widening of `A-2` is recorded as `A-12` (`docs/program/OWNER_RULINGS_2026-09-17.md` section 3.47); the prefixes `cqa_` and `cmc_` and the DejaVu Sans font exist (`contracts/domain/v1/identifiers.json`, `src/auditmanager/comparison/report/fonts/`).
