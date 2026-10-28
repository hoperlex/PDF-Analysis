# COMPARE-MODULES-PLAN revision 2 — judging round 3 of 3 (adversarial)

Reviewer: independent round-3 judge, read-only. Plan:
`.local/worktrees/plan-compare-modules/docs/program/dispatch/COMPARE-MODULES-PLAN.md` at `fa6d21ab` (revision 2).
Tree: the same worktree (base `9e42c18a`). The integration tip was read too: `ba5fdbfc` («Merge
agent/section-category-ocr-01», so SX has merged). The original was read as data under
`scratchpad/orig-src/files/`. No suite, docker, npm, build or migration was run. Host at review time:
`df -h /` → 5.1 GB free (96 %), `free -g` → 11 GiB total, 4 GiB available.

Plan line numbers are written `plan:NNN`. Rounds 1 and 2 are not repeated unless their fix is wrong or
incomplete; where that is the case the finding says so.

---

## BLOCKER

**R3-01 · BLOCKER · A-4 (plan:243-256), CMP-SPEND-01, CMP-WORK-01, §6 mutation proof (plan:491)** — The comparison
spend journal is copied from the wrong precedent. It has no record written before the call, so a paid call
and its database row form a dual write.
- Scenario. A per-sheet description call is sent to OpenRouter. The worker is OOM-killed (see R3-03) or
  redeployed after the provider has charged the call and before `comparison_model_call` commits. The lease
  expires and the reclaim re-runs the item. The call is paid twice, and the first payment is in no journal,
  so the `R-29` union and the dashboard under-report it. Deliberately or not, the plan's own proof «a lease reclaim
  that must not double-spend» cannot pass, because nothing tells the reclaim that a call was in flight.
- Evidence.
  - The plan says the journal has «the columns and CHECKs of the `comparison_summary` precedent» (plan:249).
  - That precedent is a row written after the answer, with no prepared or in-flight state:
    `db/migrations/versions/20261027_0035_comparison_records.py:393-470` (`state`, `cost_micros`,
    `command_id`). It is also recorded-only (`CURRENT_STATE.md` item 7, `D-244`: «no live path»).
  - The run path was built the other way, for exactly this reason:
    `20261002_0014_durable_analysis_effects.py:1-9` («gives both kinds of external effect a database breadcrumb
    before they happen»).
  - The worker's reclaim relies on that breadcrumb: `workers/service.py:51` («resumed when no provider effect can
    have spent, failed otherwise»).
  - `AGENTS.md` §4 forbids «dual-write DB + external side effect without outbox/reconciliation».
- Fix.
  - Give `comparison_model_call` a `prepared → sent → completed | failed | unknown` life. Insert the
    `prepared` row (request digest, attempt id, connection revision, pinned model) in its own committed
    transaction before the adapter is called. That is the shape of `provider_call_effect` in `0014`.
  - On reclaim, an item that has a `prepared` or `sent` effect and no completion is never re-sent
    automatically. It goes to a typed `spend_unknown` state, and only an explicit «Повторить» clears it.
  - Add a mutation proof: kill the process between send and commit, and assert no second send and one
    `unknown` row.
  - On the pull channel the `executor_task` row already plays this role; say so, and require it for HTTP
    direct too.

**R3-02 · BLOCKER · A-3 (plan:234-241), A-10 (plan:318-323), CMP-STAGE-AI-01 (plan:457), §4.0 rule 6
(plan:388-390)** — The AI reviewer can turn a deterministic CHANGED into SAME. That hides a real change from
every deliverable, even though the raw row survives. The original forbids exactly this.
- Scenario.
  - Р changes «Э1 – 3 шт.» to «Э1 – 4 шт.» on a sheet.
  - Step 03 records a CHANGED fragment. The reviewer answers SAME with «high» confidence. This can be a model
    error, or the sheet's own note «Изменений нет» acting as injected text.
  - The validator accepts it: the schema is right, the ids exist, coverage is exact, and no number is invented.
  - A grey mask covers the place. No card is built, so the change is not in «Подтверждено изменений», not in
    the tab 4 journal and not in the Excel the client receives.
  - It survives only in the collapsed «Показать исходные текстовые различия», which nobody is asked to read.
  - The plan's proof «an AI SAME never removes a raw difference row» passes all the same.
- Evidence.
  - The original's chain document says the opposite:
    `orig-src/files/docs/DOCUMENT_COMPARISON_CURRENT_STATE.md:279-282`: «`SAME/MOVED` принимаются только с
    высокой уверенностью; конфликт `deterministic CHANGED → model SAME` и `MOVED` без фактического выхода за
    принятую связь также закрываются в `UNCERTAIN`». The same paragraph also says that an invented
    number/designation turns only the affected decision into UNCERTAIN.
  - The plan carries the «high confidence» half and drops the CHANGED→SAME guard (plan:457).
  - The classifier is a second, unreviewable lever: SERVICE_STRUCTURE is «one collapsed block without verdicts»
    (plan:320), so the model alone decides that an item never reaches an expert.
  - The same gap exists in version comparison. The client report checks precision only: «drops every point
    whose number, mark or direction the facts do not confirm» (plan:109). Nothing checks recall, so an omitted
    change is invisible in a document meant for the customer.
  - `AGENTS.md` §4 forbids «modification of raw deterministic comparison evidence by the AI layer». Hiding it
    from every output is that modification in effect.
- Fix.
  - Copy the original's rule into CMP-STAGE-AI-01 and ADR-0025:
    - a model SAME or MOVED on a fragment whose deterministic status is CHANGED, REMOVED or ADDED becomes
      UNCERTAIN, so it gets a REVIEW card and no mask;
    - MOVED is accepted only with a found target outside the accepted link.
  - Let an expert move any SERVICE_STRUCTURE item or any masked fragment into a REVIEW card (an expert act with
    history).
  - Print in the journal, the Excel and the PDF/HTML footer: «Скрыто ИИ как одинаковое: N; отнесено ИИ к
    служебным: M; экспертом не проверялось».
  - Add a recall line to the client report («изменённых листов N, описано в отчёте K, отброшено проверкой D»)
    and print the R-146ba unconfirmed label on every page of the PDF.
  - Add mutation proofs: deterministic CHANGED plus model SAME gives UNCERTAIN and a REVIEW card, and the
    masked count appears in the Excel.

**R3-03 · BLOCKER · A-5 (plan:258-273), A-4 «counted against `AUDITMANAGER_WORKER_SLOTS`» (plan:251), §8
«Memory» (plan:520)** — The memory design rests on the wrong host. Its «per-job memory budget» cannot be
enforced inside a process, and the way it fails takes paid section runs down with it.
- Scenario.
  - The production host has 4 GiB for postgres, MinIO, api, worker, web and proxy together.
  - The worker renders an A1 pair at 200 dpi. PDFium's BGRA bitmap is about 124 MB per page. Two pages plus
    PIL copies, nine boolean mask layers (about 31 MB each), an int32 label plane (about 124 MB) and float
    planes come to roughly 0.8–1.2 GiB. pdfplumber on a page at the element ceiling can add up to about
    800 MiB more.
  - The comparison loop runs inside the same worker process as the section-run slot. A kill takes both.
  - The section run's attempt had already spent a provider call, so the reclaim fails it: a paid run of the
    primary product (`R-146l`) is lost.
  - Until PROD-05b sets limits, `mem_limit` defaults to 0, so the host OOM killer may pick postgres or MinIO
    instead.
- Evidence.
  - The plan computes memory against «the host: 11 GiB, about 3 GiB available» (plan:266). That is this
    development host.
  - `OWNER_RULINGS_2026-09-17.md:1788` (`R-146ad`): «Host size … 4 ГБ RAM … `AD-04` (memory and log limits)
    is taken from a measurement made within a 4 GiB host».
  - `R-146j` (:1768): one worker slot.
  - `infra/deploy/compose.server.yml:301` `mem_limit: ${ALPHA_MEM_LIMIT_WORKER:-0}` and `:349`
    `AUDITMANAGER_WORKER_SLOTS: ${…:-1}`.
  - `ingest/envelope.py:188-190`: pdfplumber «bounds a run's page at about 800 MiB».
  - Reclaim fails runs: `jobs/repository.py:680,779` (`fail_reclaimed_run`) and `workers/service.py:51`.
  - The repository already has the right tool: the envelope runs PDFium in a child process under a kernel
    ceiling (`envelope.py:43-55`, `READER_ADDRESS_SPACE = 512 MiB`, `READER_SECONDS = 60`).
  - PROD-05a's measurement is «during a 500-page analysis» (`PRODUCTION-READINESS-PLAN-01.md:74`). It does not
    include comparison.
- Fix.
  - Run every profile, engine and tile computation in a child process under `RLIMIT_AS` and a CPU and wall
    ceiling, the way `ingest/pdf_reader.py` does. An overrun becomes a typed `needs_review`/`RENDER_FAILED`
    on that item only and never touches the run slot.
  - State the per-item ceiling against a 4 GiB host (for example 768 MiB) and make the engine tile its
    full-resolution work to fit it.
  - Add the comparison worst case to PROD-05a's measurement, so that `AD-04` limits include it.
  - CMP-PROFILE-01 and CMP-ENGINE-01 measure under that ceiling on a realistic A1 input (R3-19), not on the
    11 GiB host.

**R3-04 · BLOCKER · A-8 (plan:302-308), §1.1 upload (plan:58-64), CMP-INGEST-01/02, CMP-SEAL-C0** — The
resumable chunked upload cannot be built on the storage port inside the granted paths. Two of the plan's
safety claims about it are false.
- Scenario.
  - A 200 MiB drawing arrives in 13 chunks. Each chunk must be staged durably to survive a broken
    connection and an API redeploy. The API container is recreated whenever its image id moves, which is
    every code deploy (`infra/deploy/deploy.sh:73-76`), so the container's local disk does not survive.
  - The port can stage a temporary, verify it and discard it, but it cannot read a temporary back or compose
    one. To reassemble the file, the lane must either:
    1. publish every chunk as a permanent canonical blob, which doubles storage forever with no delete
       (A-5), or
    2. add S3 multipart support to `storage/**`, which no slice owns.
  - A user who presses «Удалить пакет» on a batch of the wrong client's documents sees it vanish. The bytes
    stay in MinIO until an operator erases the whole project with the owner's permission (`R-146aj`).
  - An abandoned batch is never swept.
- Evidence.
  - `storage/port.py:66-101` has `stage_temporary`, `temporary_exists`, `verify_temporary`, `publish` and
    `discard_temporary`. `read` and `open_stream` take a published `blob_id` only.
  - `storage/s3.py:139-260` has no multipart path.
  - The plan says «an abandoned batch is swept by the existing temporaries sweep (`jobs/temporaries.py`)»
    (plan:307). That sweep removes three exact local file names in the container's `/tmp`, «only the three
    exact names» (`jobs/temporaries.py:1-34`). It never touches object storage.
  - Own paths: INGEST-01 has `ingest/comparison_pdf/**` and `documents/**`; INGEST-02 has
    `ingest/comparison_batch/**`. No `storage/**`.
- Fix.
  - Add a small `CMP-STORAGE-PARTS-01` (S/M, C0, before INGEST-01). It owns `storage/**`, the port test,
    `blob_reference_audit.py` and the recovery coverage. It provides staged parts (S3 multipart upload with
    an opaque upload token persisted before the first part, `UploadPart`, `Complete`, `Abort`) plus
    verify-whole.
  - Add a database-owned sweep of expired multipart uploads, as a comparison work item that aborts them.
  - Rename «Удалить пакет» to «Отменить пакет». State that bytes of completed versions are removed only by
    the operator's project erase (`R-146c`). Abort parts that were never completed.
  - Strike the `jobs/temporaries.py` claim.

---

## MAJOR

**R3-05 · MAJOR · A-5 «no eviction» (plan:269-271), CMP-PROFILE-01, CMP-VIEWER-01** — Disk use has no budget,
and on this product's storage a full disk is an outage, not a degradation.
- Scenario: one 12-version × 100-sheet A1 project stores:
  - its sources (about 1–2 GB);
  - previews and thumbnails (1 200 pages × 0.3–1 MB ≈ 0.4–1.2 GB);
  - the masks the overlay tiles need (the original stores `masks.npz` per pair: 1 100 pairs × 0.5–3 MB ≈
    0.5–3 GB);
  - chunk blobs if R3-04 is solved by publishing chunks (+100 % of the sources);
  - a full new mask set after every `ALGO_VERSION` bump or «Пересчитать».

  Nothing is ever deleted except by an operator's project erase. MinIO refuses writes at about 1 % free, and
  then every upload, run publication and crop fails with `dependency_unavailable`. That is not only
  comparison: it is the whole product, on a single host with manual copies only (`A-1`, `A-4`).
- Evidence:
  - `orig-src/.../version_comparison/tiles.py:33-44` (`np.load(result_dir / "masks.npz")`);
  - `D-205` (DEBT_REGISTER on the tip, row 122): «MinIO refuses writes once free disk is below its own
    minimum-free-drive threshold».
  - The plan has no bytes-per-project figure. The production disk size was never asked («the host's measured
    size» is open, `OWNER_RULINGS:1817`).
- Fix: CMP-PROFILE-01 and CMP-ENGINE-01 report bytes per A1 page and per pair, alongside RSS. The ADR states a
  per-project byte estimate, a per-project byte cap enforced by refusal, and a readiness finding when free
  disk is under N GB. Do not store masks for `same` pairs. Store masks as one bit-packed blob per pair. Put
  the owner's disk size in the end-of-plan poll.

**R3-06 · MAJOR · A-5 «tiles are rendered on demand with a bounded in-process cache» (plan:271), CMP-VIEWER-01**
— Where the overlay tiles' masks come from is undecided, and both possible answers hurt.
- Scenario A: the masks are not stored. Each tile request then re-runs registration and mask computation in
  the **API** process. PDFium is guarded by one process-wide lock (`ingest/envelope.py:171` `PDFIUM_LOCK`,
  «the process's one PDFium lock»), so one expert zooming an A1 overlay issues dozens of tile requests that
  queue on that lock. They hold the API's thread pool and slow every other user's requests on a 4 GiB host.
- Scenario B: the masks are stored. Then they belong to R3-05's disk budget and need a format decision in
  SEAL-C1, which VIEWER (parallel to ENGINE) depends on.
- Evidence: `orig-src/.../tiles.py:1-80` builds overlay tiles from stored masks. The plan stores only
  «previews and thumbnails» (plan:270).
- Fix: decide in ADR-0025. Store one bit-packed mask blob per non-`same` pair, written by the engine in the
  worker. The API reads bytes and reduces them with numpy; it never calls PDFium. A/B page tiles at a level
  come from a bounded pyramid rendered in the worker (or the R3-03 child process), never in the API.

**R3-07 · MAJOR · A-4 (plan:250-256), D-3 (plan:176-178), CMP-WORK-01, CMP-VC-AISHEET-01, CMP-VC-QUEUE-01** —
Comparison work starves the primary product, and the operator loses the controls for it.
- Scenario.
  - One A1 project needs about 3 h of profiles (about 10 s a page with pdfplumber vector lines) plus 3–10 h
    of engine time (1 100 pairs at 10–30 s) on the **only** worker slot (`R-146j`).
  - Its step 6 needs about 440 vision calls. Each holds the executor connection, because «the
    one-active-run-per-connection check also counts active comparison AI work» (plan:253). A 429 may then
    wait up to 600 s per retry (D-3, the original's 20/60/120/300/600 s).
  - The original ran these with `sc_parallel` (default 5–10). Here they are serial, so 4–11 h on one
    connection.
  - Meanwhile a section run or an AR v3 group on the same OpenRouter connection (`R-146e`) waits behind it,
    for hours. Nothing states a priority.
  - When the operator sees spend running away, `setExecutionPaused` (PUT `/execution/dispatch`) does not
    stop it. That pause is checked only in the run claim (`jobs/repository.py:92`). «Очередь» and «Воркеры»
    show an idle worker that is not taking queued runs.
- Evidence:
  - the probe loop the plan copies is a separate thread, not slot-counted (`workers/service.py:290-292,
    379-389`), so «counted against» is a new mechanism;
  - the connection limit: `jobs/repository.py:46-66`;
  - `orig-src` inventory: «all sheets of all transitions share one concurrency limit (`sc_parallel`)».
- Fix:
  - section runs have strict priority: the comparison loop claims only when no run is claimable, and it
    yields between items, where an item is one page or one pair, never a series;
  - comparison AI takes the connection per call, not per job, so a run waits at most one call;
  - comparison work honours `execution_control.paused`, read through `jobs.public`;
  - an admin-visible read-only «Сравнение» section in «Очередь» or «Воркеры» (or state that B4 covers runs
    only);
  - write the throughput figures (pages/h, pairs/h, calls/h on the 4 GiB host) into the ADR, so that the
    owner sees what «Полный паритет» costs in waiting.

**R3-08 · MAJOR · A-6 (plan:289-290), §8 «Model cost» (plan:523-524), CMP-SPEND-01, CMP-VC-QUEUE-01** — A
comparison AI job has no money ceiling, and the consent is not bound to anything.
- Scenario 1 (size).
  - At the pinned primary rates ($5/M input, $25/M output, `docs/program/P02_LOCK.json`), one sheet
    description with 4–6 crops is about 10k tokens in and 1.5k out, so about $0.09.
  - At about 40 % changed sheets, one 12 × 100 project's step 6 is about 440 calls, about $40.
  - «выбрать все» for 20 sets and «Запустить выбранные по очереди» is then about $800 from one click.
  - The product's only spend rule is `OD-03`: USD 1.00 **per run** (`P02_LOCK.json` `run_cost_ceiling_usd`,
    `analysis/text/cost.py:1-16`). A comparison job is not a run.
  - `R-29` is the integrator's per-wave development stop, not a product control. «Spend counted under
    `R-29`» (plan:524) therefore enforces nothing in production.
- Scenario 2 (order). The launch queue runs «luna → series → ai → report» per set (plan:434). When the user
  consents at enqueue time, step 5 has not run, so the number of changed sheets, which is the AI estimate,
  does not exist yet. The consent is to an unknown amount.
- Scenario 3 (recipient). The consent names a model, but the job is queued for hours (the per-install AI
  queue). Meanwhile an administrator re-routes `comparison_sheet_changes` from a local endpoint to OpenRouter.
  The drawings go to a recipient the consent did not name (`A-2`).
- Scenario 4 (doubles). The plan names no `IdempotencyKey` for any new write. 28 of the 51 existing
  mutations carry one (contract `components.parameters.IdempotencyKey`). A retried POST «Запустить» creates
  two paid jobs.
- Fix.
  - Put a per-job and per-day comparison ceiling in USD in the end-of-plan poll (the owner decides spending).
    Enforce it with the existing meter's before/after checks.
  - Show the estimate in USD from the pinned rates.
  - Bind each consent to {estimate digest, USD ceiling, connection revision, pinned model}. A route or
    revision change, or an actual spend above 1.2 × the estimate, pauses the job with a typed state and a
    new consent.
  - The queue asks for AI consent per set only when its estimate exists.
  - Every new mutation takes `IdempotencyKey`. Add a unique constraint «one active AI job per (series, work
    kind)».

**R3-09 · MAJOR · A-5 cache key (plan:265-266), A-2 content-keyed rows (plan:230-232), §4.0 rule 3
(plan:378-380), CMP-ENGINE-01** — The cache key leaves out what the original's key includes. A doubtful link
can then show «Совпадает» from a cached result. The cache's scope also contradicts the erase closure.
- Scenario 1.
  - Sheet 12 of version 3 and sheet 12 of version 4 are first linked with HIGH confidence, and the result is
    `same`.
  - After a reorder or a matrix change, the same two pages are linked with MEDIUM confidence, or as a
    duplicate «⧉». The original adds the forcing reason `MATCH_LOW_CONFIDENCE`/`DUPLICATE_SHEET` →
    `needs_review`.
  - The plan's key («both page contents, parameters and `ALGO_VERSION`») returns the cached `same`.
  - `same` sheets are not sent to the AI description, so the doubtful pair is never looked at.
- Scenario 2. A page whose only change is a PDF annotation (a cloud or a «Изм.» note) keeps the same content
  hash, so the `annotations` channel result is reused.
- Scenario 3. Scanned pages: if «page contents» means the content stream, every scan page's stream (`q … /Im0
  Do Q`) is identical across versions. The original's `identical_content` shortcut (`engine.py:506`) then
  says `same` without rendering.
- Scenario 4. If the content-key digest is UNIQUE globally, the second project with an identical page reuses
  the first project's row: a cross-project reference that breaks `project_erase` closure, the very thing
  rule 3 promises cannot happen. If it is unique per version, there is no cache.
- Evidence:
  - `orig-src/.../version_comparison/jobs.py:586-592` (`_cache_key` hashes both content hashes, **both
    annotation hashes**, params including the split `part`, **sorted reasons** and `ALGO_VERSION`);
  - `status.py:16-20,58-59` (forcing reasons → `needs_review`);
  - `profile.py:143-145` (content hash by a Merkle walk, plus a separate annotations hash);
  - `project_erase.py:8-15` (FK closure).
- Fix:
  - key = (content Merkle of A, content Merkle of B, annotation hashes, link reasons sorted, split part,
    params, `ALGO_VERSION`);
  - define the content hash as a Merkle walk over the content stream and every referenced resource,
    XObjects and images included;
  - the unique key includes `project_uid`, so reuse is within a project only;
  - mutation proofs: «same pages, MEDIUM link → `needs_review`», «annotation-only change → `different` in
    `annotations`», «scan with a replaced image → not `same`».

**R3-10 · MAJOR · A-3 effective matrix (plan:237-238), CMP-MATRIX-01, CMP-VC-AIPAIR-01** — The effective
matrix has no concurrency or revision rules, and an old AI link can override a newer deterministic match.
- Scenario 1 (AI over algorithm).
  - An accepted AI link was made when sheet B7 was unmatched.
  - A new upload, a reorder or an `ALGO_VERSION` bump rebuilds the algorithmic matrix, and B7 is now a HIGH
    match to A9.
  - The read order «algorithm, then accepted AI links, then manual» applies the stale AI link over the new
    deterministic HIGH link. That breaks the original's own rule «never … a B already linked» (plan:431).
- Scenario 2 (lost edit).
  - Expert 1 drafts ten edits on revision r5. Expert 2 applies three edits, giving r6.
  - Expert 1's batch applies on r6, and its «листа нет» for sheet 17 silently replaces Expert 2's «Связать»
    of sheet 17, because the last manual edit wins.
  - Both stay in history, and nobody is told.
- Fix.
  - Bind each accepted AI link to the algorithmic matrix revision and the cell state it was answered for.
    It applies only while its cell is still unmatched or doubtful, and is otherwise shown as superseded.
  - «Применить сопоставления (N)» carries the base matrix revision. A mismatch is `conflict` with a reason
    (rule 5: no new code), and the client rebases the draft.
  - Bind manual edits to the version-order revision they were made under, and say what a reorder does to
    them.
  - Mutation proofs for both.

**R3-11 · MAJOR · A-9 / A-10 (plan:313-323), CMP-STAGE-REVIEW-01, CMP-STAGE-REPAIR-01** — Verdict carry-over
cannot work as specified, so expert work is thrown away on every recompute.
- Scenario. A card's identity is «a digest over its class and sorted evidence ids». Evidence ids are new ULIDs
  per chain run (A-2 lists only profile, sheet-pair result and card as content-keyed), and the class is model
  output. Every rerun produces new evidence ids and possibly a different class, so no card digest is ever
  equal. Every one of these marks all of an expert's 200 verdicts «stale»:
  - «Перезапустить анализ пары»;
  - «Откатить» of a repair (which «recompute[s] steps 02–07», plan:458);
  - a newer version arriving;
  - an AI reclassification.
- Evidence: plan:230-232 (content-keyed list), plan:319, plan:458. The original's chain document gives every
  atomic difference «устойчивый `evidence_id`» (`DOCUMENT_COMPARISON_CURRENT_STATE.md:343`).
- Fix:
  - evidence ids are content-keyed: side, document and version, sheet, normalised text, box anchor rounded;
  - a verdict binds to the evidence set, not to the model's class or grouping;
  - carry-over is per evidence: a card whose evidence set is a superset or subset shows the verdict as
    «частично перенесено», never silently lost;
  - mutation proof: rerun with no input change → 100 % of verdicts carried.

**R3-12 · MAJOR · A-11 flag (plan:330-335), A-12 (plan:337-343), CMP-SEAL-C0, CMP-VC-UI-01** — The rollback
flag cannot be built as written. The A-12 edits sit in a slice nobody owns.
- Evidence.
  - `web/tests/guards/server-credential.guard.test.ts:88-95` requires that `@/shared/config/server-env` is
    «imported by exactly the BFF route handler and nothing else». The menu is built from the static
    `SCREEN_REGISTRY` in `web/src/_app/navigation.ts:15-16`. The pairing controls and the summary are client
    components: `web/src/entities/version-comparison/ui/sheet-pairing-controls.tsx:1` and
    `comparison-summary.tsx:1` (`'use client'`).
  - So «read by `server-env.ts`… a module that is off has no menu entry», and A-12's «while the versions
    module is on, the version-scoped screen stops offering `approveSheetPairing`…», can be built only by
    breaking a security guard or by adding a read the plan does not have.
  - The A-12 controls live in `web/src/entities/version-comparison/**`, which is not in CMP-VC-UI-01's own
    paths (plan:421 lists `widgets/version-comparison/**` only).
  - The worker's comparison loop is not said to read the flag. With the module off, queued comparison AI
    still spends.
- Fix:
  - SEAL-C0 exposes the module set through the contract, as an additive field of `getProductVersion` or of
    the session subject that `screenDecision` already gets;
  - `navigation.ts` and `screenDecision` filter by it;
  - grant `web/src/entities/version-comparison/**` to CMP-VC-UI-01;
  - the worker loop and every comparison command refuse when the module is off;
  - add a test that turning the flag off pauses queued comparison work.

**R3-13 · MAJOR · §4.0 rule 1 (plan:354-362), CMP-WORK-01 (R2-01 fix incomplete)** — Rule 1 wires API
operations only. The worker side has the same defect R2-01 found for the API side.
- Evidence: the worker's dependencies are built in `bootstrap/composition.py` `build_worker_runtime`
  (`:164-246`, where `probe_runner` is built). Rule 1 reserves `composition.py` and `workers/service.py` to
  the seal and WORK (plan:361-362). Yet each of these lanes adds a comparison work handler that needs
  storage, executors, sessions and its service built in the worker runtime: PROFILE, INGEST-02, SERIES,
  AIPAIR, AISHEET, SPEC, QUEUE, REPORT, STAGE-TEXT, STAGE-AI, STAGE-REPAIR and STAGE-RUN, twelve in all.
- Scenario: every one of those lanes either STOPs or writes its handler into WORK's directory.
- Fix: WORK designs one handler registry: `comparison/work` iterates a tuple of handler factories exported from
  `comparison/public.py` (rule 2 already grants the appends), with one dependency bundle built once in
  `build_worker_runtime` by WORK. Write this in ADR-0025 and WORK's task file, with a test that every
  `comparison_work.kind` value has exactly one handler.

**R3-14 · MAJOR · C0 merge order (plan:407-409), CMP-FIXTURES-01** — The corpus merges last in C0, but the C0
lanes that merge before it need it.
- Scenario. CMP-INGEST-01 (stamp reading: designation, «Изм.», date, stage and section) and CMP-PROFILE-01
  (words, lines, scan flag, A1 measurement) need fixture PDFs with stamps, a scan page and annotations. Both
  merge before FIXTURES (merge order «…, INGEST-01, INGEST-02, PROFILE, VERSION-MARK, FIXTURES»).
  `fixtures/comparison/**` belongs to FIXTURES. Each lane either authors a private corpus outside its paths
  (STOP), or tests on nothing.
- Fix: FIXTURES merges first after SEAL-C0, as an S lane that is a generator plus answer keys. It touches no
  wiring file, so it can lead the merge order at no cost. Add the realistic A1 generator of R3-19 to it.

**R3-15 · MAJOR · A-6 compatibility (plan:288-289), CMP-EXEC-IMAGES-01** — The promise that an old runner
«fails the task with `image_input_unsupported` and never answers on a subset of the images» is false for two
of the deployed runners.
- Evidence.
  - `tools/executor-runner/agent.py:479-486` (endpoint mode) loops over `task["images"]` and keeps only the
    **last** `image_bytes`.
  - `tools/executor-runner/mcp_bridge.py:393` fetches `task["images"][0]`, only the **first**.
  - Only `codex_answer.py:54-55` refuses `len(images) > 1`.
  - Runners already on remote hosts cannot be fixed by this repository's commit.
- Scenario. A deployed endpoint-mode runner with `accept_images` claims a 4-crop «Изменения в листе» task,
  answers from one crop, and the server records a valid «с изображения» description.
- Fix: gating is server-side. The claim carries the runner's declared `max_images` (absent means 1, the
  shape every deployed runner sends today). The server never hands a task with more images than declared.
  A test claims with an old-shape request and asserts that no multi-image task is offered.

**R3-16 · MAJOR · A-2 «`DocumentUid` is the series» (plan:225), §1.1 «Добавить версии в «…»» (plan:58),
CMP-VERSION-MARK-01** — A plain-PDF version added to an analysable document becomes its current version.
That changes the main product's screens and passes.
- Evidence.
  - `dashboard/repository.py:115-129` and the optimisation project match
    (`optimisation/project_match.py:183,264`), plus `section_specification.py:435,454`
    (`list_current_versions_in_section`), all select `document.current_version_uid`.
  - The section panel, «Спецификация и цены» and «Предложения» would then read a comparison-only version
    that has no run text layer.
  - VERSION-MARK covers only the version screens and the run start (plan:405).
- Fix: decide in the ADR:
  - either comparison-only versions never become `current_version_uid` of a document that has a portal
    version,
  - or they live only in comparison-only documents, with «Добавить версии» to a portal document refused.

  Add a test per consumer of `current_version_uid`.

**R3-17 · MAJOR · §1.2 tab 1 upload «ZIP-комплект» (plan:130), §8 «ZIP members under the archive rules of
`ingest`» (plan:528), CMP-STAGE-PAIR-01** — No safe reader exists for a ZIP of a whole set, and the new one
has no owner.
- Evidence: ingest's archive rules are the portal bundle's:
  - `ingest/bundle_archive.py:118-120`: `TOTAL_BYTES = 300 MiB`, `MAX_RATIO = 100`, `MAX_ENTRIES = 8`;
  - `:158`: the required roles `pdf`, `blocks` and `results_md`;
  - `:1-40`: «exactly one `<stem>.pdf`…».

  A set ZIP of 40 PDFs is refused at rule 0. CMP-STAGE-PAIR-01 owns `comparison/stage/**` and web only;
  `ingest/comparison_pdf/**` belongs to INGEST-01 in C0.
- Scenario: the lane writes a generic ZIP reader in its own directory to make the button work. Without the
  care `bundle_archive.py` took (raw names, declared vs. actual sizes, ratio per member, symlink bits,
  ZIP64), it is open to a zip bomb or a slip.
- Fix: either cut «ZIP-комплект» (folders and PDFs only; the browser already enumerates a folder), or add
  `CMP-INGEST-ZIP-01` in C0. It parameterises `bundle_archive`'s reader with a set policy (entries ≤ N,
  total ≤ 2 GiB, per-member PDF envelope) and gets its own security judge.

**R3-18 · MAJOR · §1.2, §2 G-14/15/21-26, CMP-STAGE-*, CMP-VC-SPEC-01, CMP-VC-REPORT-01 («Полный паритет»)** —
Parity is promised for functions whose source was never read. Lanes will invent their behaviour, and judges
will have nothing to compare against.
- Evidence (the inventories' own lists):
  - `ORIGINAL-STAGE-COMPARISON-INVENTORY.md:713-731` — not downloaded: `sheet_link_repair.py` and
    `content_sheet_link_repair.py` (→ STAGE-REPAIR-01), `document_matching.py` (→ STAGE-PAIR suggestion),
    `expert_review.py` (→ verdict persistence), and `:704` `text_comparison.py` (71 KB) and
    `text_fact_producer.py` (63 KB), which are Stage 2 itself (→ STAGE-TEXT-01).
  - `ORIGINAL-VERSION-COMPARISON-INVENTORY.md:509-520` — the whole-specification internals, the
    `md_report` prompts, `client_edit.py` and the Luna payload and prompt are unconfirmed.
  - Headline 2 of the stage inventory (`:35-39`): the chosen chain's buttons were dead in the original's
    live UI. The chain was never run by the original's users.
- Fix:
  - before dispatch, fetch these files read-only (the same channel as the inventories, about 1 h of a Haiku
    gatherer) and add the facts to the inventories;
  - otherwise tag those slices `[own design]` and accept them on answer keys, not «parity»;
  - tell the owner at the end-of-plan poll that Q-CMP-1's chain had no live users in the original.

**R3-19 · MAJOR · §6 Fixtures (plan:495-498), §6 Live AI (plan:503-504), A-5 measurements** — The tests can
see none of the defect classes that real drawings bring, and the A1 measurement has no input.
- What the synthetic corpus cannot produce, and what each does in production. The writer has one CID font,
  uncompressed content and A4 at low dpi (`tools/fixtures/ar_corpus/pdfwrite.py:1-8`).
  - SHX text exported as strokes. There is no text layer, so the stamp (шифр, «Изм.», sheet number), the
    passports for stage links, the text channel and the TEXT evidence are all empty. Matching falls back to
    raster.
  - `/Rotate 90` and a CropBox other than the MediaBox (common on A1 sheets). pdfplumber word boxes and the
    PDFium raster then disagree, registration fails, and false geometry differences appear.
  - Hidden optional-content (OCG) layers. pdfplumber reads text that PDFium does not draw, which gives false
    text differences or a stamp read from a hidden layer.
  - A different producer between versions (AutoCAD vs. nanoCAD vs. Revit, other line joins or
    anti-aliasing). Noise thresholds tuned on synthetic pages either flood `different` or hide real changes
    as «шум».
  - Pages near the measured 75 486 drawing elements (`ingest/envelope.py:180-186`). Their time and RSS are
    what A-5 has to measure, and A4 low-dpi fixtures cannot provide them.
- Recorded responses only. They are authored by the same lanes to pass the same validators, so the
  validators' real pass rate is unknown. The pinned OpenRouter model's acceptance of N images in one Chat
  request is never exercised.
- Live checks need the owner's key in a session (`R-146bb`), once per AI slice. That is an owner-calendar
  dependency, five to six times over.
- `R-146bb` rules «работаем на синтетике», so a real set needs an explicit owner exception.
- Fix (minimal):
  - extend CMP-FIXTURES-01 with a «realistic A1» generator: strokes-only text, `/Rotate`, CropBox offset,
    one OCG layer, hatches and dashes, about 75k elements, a second «producer» rendering of the same sheet;
  - the A5 measurement runs on it in the R3-03 child process;
  - one live run per work kind on 3 synthetic items under $0.50 each, with the validator pass rate
    recorded, and STOP below 80 %;
  - ask the owner by poll for one non-client real set (his own old project, or a published sample) for a
    measurement-only check: time, RSS, bytes, and false-`same` on 20 human-labelled pairs.

**R3-20 · MAJOR · A-5 / O-1 «own numpy code (recommended)» (plan:261-263)** — The recommendation is a
performance trap, and a later change of mind has no lock owner.
- Evidence: numpy has no connected-component labelling. A pure-Python or vectorised union-find over a 31 Mpx
  mask runs for minutes per page. The original calls `cv2.connectedComponentsWithStats` on full-resolution
  masks (`orig-src/.../version_comparison/engine.py:201,253`, `profile.py:69`). Morphology is available through Pillow's
  `ImageFilter.MaxFilter`/`MinFilter`; labelling is not. The dependency lock is held only by SEAL-C0 and,
  implicitly, SEAL-C2. If CMP-ENGINE-01 in C1 finds its own labelling too slow, nobody may add `scipy` or
  `opencv-python-headless` until the C1 FIX.
- Fix: recommend `scipy` (BSD-3; `ndimage.label`, `binary_dilation`, `fourier_shift`) or
  `opencv-python-headless` (Apache-2.0) in O-1. Take it in SEAL-C0. Give CMP-ENGINE-01 a time gate: one A1
  pair within N s inside the R3-03 ceiling, or STOP.

**R3-21 · MAJOR · §4 seals, §5 «Seals are serial» (plan:473-474)** — Each seal freezes schemas before the lanes
that fill them exist. A misfit costs a FIX bump that nobody priced.
- Scenario. SEAL-C1 freezes the sheet-result schema (8 channels, regions, layers, `aligned_blocks`,
  `text_changes`), the matrix and the series before ENGINE and MATRIX are written. When ENGINE needs one more
  field (a channel's reason detail, a transform variant), the contract and head belong to nobody until the
  C1 FIX. The FIX is then another minor bump: about 75 literal rewrites (`pin_sweep.py contract-version`),
  a `FRONTEND_LOCK` reseal and the infra surface pins. That happens five waves running.
- Fix: price one amendment bump per wave in §7, or let each seal publish the per-sheet result as one
  versioned object schema with explicitly optional members, so additions are not breaking. State that a lane
  needing a field STOPs to the FIX, never edits the contract.

**R3-22 · MAJOR · §7 estimate (plan:506-516)** — The estimate is the optimistic edge with a P80/P50 spread of
only 1.3 for a programme of 35 slices with novel algorithms.
- Undercounted or unpriced:
  - C0's eight wiring merges are serialised (plan:408-409), and VERSION-MARK and FIXTURES wait behind
    PROFILE: about +1 step. C1 has 8 steps, not 7.
  - The XL engine at «+6 h» covers registration, phase correlation, labelling, glyph and overdraw logic,
    8 channels and the A1 measurement, written without OpenCV. The original's engine with its helpers is
    about 2 100 lines (inventory §6.3), so +15–20 h is realistic.
  - New STOP/regrant cycles from this review: R3-04, R3-12, R3-13, R3-14, R3-17 and R3-20, at least
    6 × 1.5 h.
  - Contract FIX bumps (R3-21): 2–3 × 2 h.
  - Owner-gated live checks (R3-19) and the O-1…O-6 poll before SEAL-C0.
  - `CODE-FIRST-TO-BETA.md:151-169` (§2.2): while the owner has not decided the host, «блоки идут не более
    чем в одной-двух линиях». The C0 line of six parallel lanes does not run here; the critical path is
    already almost serial, so this costs little, but say so.
  - The complete gate needs a host that does not exist: `D-205`, «A complete `make gate` cannot run on this
    host». The plan's «≤ 1 day» assumes it does.
- Restated (same method, 3.5 h per step including merge and acceptance, 36 steps, plus the items above):
  about 165 h for P50 (16–17 working days) and about 195 h for P80 (about 20 days). From a C0 start on
  2026-10-29, code-complete P50 is about 2026-11-20 and P80 about 2026-11-25. **Beta P80 is about
  2026-11-27…12-02**, provided a gate host exists. That is about 3–5 working days later than the plan's P80
  (11-25), and it uses up the buffer before the 2026-12-16 TLS deadline (PROD-01's first live issuance,
  `PRODUCTION-READINESS-PLAN-01.md:43`).
- It also collides with production items the plan does not mention:
  - PROD-20 owns `src/auditmanager/jobs/`, which SPEND-01 edits (`PRODUCTION-READINESS-PLAN-01.md:224`);
  - PROD-05b owns `compose.server.yml` (SEAL-C0 edits it);
  - PROD-07's wrapper owns `infra/**` and `product_purge.py`, which every seal edits under rule 3/4.
- Fix: restate §7 with these items. Add the PROD lanes to §5's hotspot list. Make «a complete-gate host
  exists» an explicit precondition of the beta date.

**R3-23 · MAJOR · A-8 limit_req (plan:303-304, 531), §8 «Upload abuse», B8** — The rate-limit check is vacuous.
The new published surface has no exposure review and no abuse cap.
- Evidence.
  - `infra/deploy/proxy/nginx.conf:91-99`: the key is empty for every request except registration, token
    exchange and the runner, and «`limit_req` does not account a request whose key is empty — so uploads,
    runs, verdicts … are never throttled».
  - INGEST-01's «measure a 10 000-chunk batch against the `limit_req` zones and STOP if a zone refuses» will
    always pass.
  - B8 requires that «nothing [is] reachable that the owner did not decide to expose»
    (`BETA-STATIC-MATRIX-02.md:38`). `R-29` clause 2 stops the integrator at «a published surface». The
    modules add on the order of a hundred operations: chunk upload, tiles, previews, MD/PDF/Excel downloads.
  - No slice re-runs the exposure review (`EXPOSURE-REVIEW-02`, PROD-15).
- Scenario. One expert account, or a stolen session, starts several 10 000-file batches. Each file passes two
  60-second sandboxed readers in the API, and every page is then profiled on the single worker slot. That is
  weeks of worker time and an unbounded volume in MinIO, with nothing refused before the 10 000-file cap.
- Fix:
  - an application-side cap: at most one active batch per account and N per install, total declared bytes
    and pages per batch, refused before the first chunk;
  - drop the vacuous limit_req STOP;
  - add an exposure-review slice to C4 (or to CMP-CLOSE-01) that names every new operation, as PROD-15 did.

**R3-24 · MAJOR · A-12 «decided at revision 2» (plan:337-343), O-4 «kept here for the owner's information»
(plan:543)** — A planner decision hides three operations the owner ruled into the product a day earlier.
- Evidence.
  - `R-146ar` (`OWNER_RULINGS:1802`) put `approveSheetPairing`, `withdrawSheetPairing` and
    `generateComparisonSummary` into 1.8.0 by the owner's choice.
  - `R-146ba` kept «the label above the comparison summary» by the owner's choice.
  - The project's working rule (memory «Owner decisions by direct poll») is that any fork for the owner goes
    to a direct poll framed in the concrete case.
  - A-12 hides the generation and approval controls and renames the heading, and asks nobody.
  - It also leaves two stores of «page X ≙ page Y» alive: when the flag goes off (rollback), the old
    approvals reappear stale against a matrix that has moved on.
  - It does not break carry-over: `comparison/service.py:932` uses `suggest_finding_matches_on_sheet_
    suggestions`, not approvals. So the decision is cheap to ask about.
- Fix: put A-12 in the end-of-plan poll as a real question. The options are «скрыть», «оставить оба с
  пометкой» and «перенести утверждения в матрицу», with the concrete screens named.

**R3-25 · MAJOR · §4.0 rule 3 (plan:371-380), `R-146c`/`R-146o` erasure** — A project erased mid-series can leave
client bytes behind.
- Evidence: the erase guard's list of «work in flight» is hard-coded: `scripts/recovery/project_erase.py:109-117`
  (`audit_run`, `job`, `attempt`, `executor_task`). A `comparison_work` row is not in it, and rule 3's
  «from its probe» will not surface this list (it is semantic, not a table count).
- Scenario. The operator erases project P while its series is rendering. The erase commits and deletes the
  rows. The comparison item then publishes a preview blob and fails on its FK. The object is in MinIO, but no
  row of P references it, so the erase's object phase never saw it. A client's drawing survives an erasure
  the owner promised to be complete. (HTTP-direct AI calls also have no `executor_task`, so they are not
  guarded either.)
- Fix:
  - SEAL-C0 adds `comparison_work`/`comparison_work_attempt` non-terminal states to `NON_TERMINAL_STATES`,
    with the derivation test;
  - the comparison loop re-checks that the project exists under a share lock before publishing a blob;
  - `blob_reference_audit.py` reports unreferenced comparison blobs;
  - test: erase during a leased comparison item is refused.

---

## MINOR

**R3-26 · MINOR · CMP-SPEND-01 own paths (plan:399), A-4 (plan:254-255)** — `runs/repository.py` `_COST_SUMMARY`
is per run (`:179-186`, `WHERE run_id = :run_id`), so «unions the two journals» there either does nothing or
mis-attributes comparison spend to runs. Only `dashboard/repository.py` `_SPEND` (`:105-112`) is a global sum.
Drop the `runs/repository.py` grant. Add a per-job and per-project comparison cost read for the screens.

**R3-27 · MINOR · CMP-SEAL-C2 own paths (plan:430), O-2 (R2-27 fix incomplete)** — SEAL-C2 takes «PDF writer
per O-2», which is a new dependency (`reportlab`) and a full Cyrillic font. Its row does not grant
`pyproject.toml`, `uv.lock`, `docs/program/P02_LOCK.json`, `tests/contract/test_w55b_direct_pins.py` or a
font asset path. R2-27 asked for SEAL-C0 **and SEAL-C2**; the disposition (plan:618) names only SEAL-C0.

**R3-28 · MINOR · §3 headings A-1…A-12, §1.3 D-1…D-5** — The identifiers collide with live registers.
- Accepted risks `A-1`…`A-11` exist (`OWNER_RULINGS:1760-1811`).
- §0 «widens accepted risk `A-2`» and §3 «A-2 Identities» sit in the same document.
- D-1 says «Reason: A-7». In the rulings, A-7 is «sections reviewed without human review»; in the plan it
  is «Expert acts».
- The next accepted risk the integrator records, for Q-CMP-4's image widening, would naturally be `A-12`,
  the same id as the plan's A-12.
- `CHECKPOINT_REGISTRY.md:16,20` uses D-1, D-2 and D-4.

Rename them to `CMP-A1…` and `CMP-D1…`.

**R3-29 · MINOR · O-3 (plan:293-294, 542)** — «Administrator» as the one who saves «Порядок версий» or edits the
matrix contradicts `R-60`/`R-80`: product mutations require `expert`, and an admin alone is
`permission_denied`, as `comparison/carryover.py:20-21` enforces. Offer «эксперт» or «эксперт и
администратор с ролью эксперта» only.

**R3-30 · MINOR · §4.0 rule 1 «a lane may develop in parallel and wait for its merge turn» (plan:360-361)** —
Parallel edits of `bootstrap/adapters.py` (about 5 000 lines) by up to six lanes of a wave contradict
`AGENTS.md` §3: «one composition root — one owner per wave. Two agents must not edit the same hotspot in
parallel». Use the `W53-CLOSE-PLAN.md:66-68` precedent. Each lane puts its adapter class in its own new module
under `bootstrap/`, and the shared file gets one import line per lane in merge order.

**R3-31 · MINOR · §1.1 (plan:43-64)** — «Проект» means two things on one screen. The original's «проект» is a
document set, so «Новый проект», «Загрузка нескольких проектов» and «100 projects» mean document sets. In
this product «Проект» is the container of the projects list. A 100-«project» batch also fills **one** of our
projects with 100 new documents that show up on its section-grouped screen. Use «комплект» or «шифр» for the
original's sense in every label, and state where a batch's sets go.

**R3-32 · MINOR · CMP-SERIES-01, CMP-VC-AISHEET-01, CMP-VC-REPORT-01, CMP-VC-OVERVIEW-01** — Two staleness
markers can be wrong.
1. After a reorder, paid AI items queued for transitions that no longer exist keep running. The plan only
   marks the series stale.
2. Step 7, the MD/PDF report, is never marked stale after a matrix edit, an AI-link change or a reorder. A
   user downloads a report that no longer matches the matrix, as if it were current.

Each report must carry the digest of its inputs (matrix revision, order revision, series and description
digests). The overview must show «устарел» when the digest differs. A reorder cancels the queued AI items
of transitions that disappeared, and says so.

**R3-33 · MINOR · §4.0 rule 4 (plan:386-387)** — «Under `R-135` that gate is the one before beta». `R-135` is
written for «W56a–W63» (`OWNER_RULINGS:1605`), and the CMP waves are not named. Without a recorded extension,
`AGENTS.md` §8 case 3 asks for a full gate on every lane that touches `bootstrap/**`, `contracts/**` or
`db/migrations/**`. That is nearly all of them, and `D-205` makes it impossible here. The integrator records
the extension before C0.

**R3-34 · MINOR · CMP-STAGE-REVIEW-01 (plan:460)** — A «generic sheet writer» built for one consumer is the
`AGENTS.md` §4 item «generic … global utils without proven semantics». Either migrate the run XLSX writer
(`exports/xlsx/writer.py`) onto it in the same slice, or keep a stage-journal writer inside
`comparison/stage_review/**`, which is the second option R2-16 offered.

---

## What to cut if the beta date matters

These are owner answers (Q-CMP-1, -3, -4), so each cut is a poll item, not a planner decision. The days are
working days of about 10 h on the restated critical path (R3-22). They are approximate and do not add up
exactly, because some judge and FIX steps are shared.

1. **Move the whole stage module (C3 + C4 except JOURNEY and CLOSE) to after the beta, behind
   `AUDITMANAGER_COMPARISON_MODULES=versions`.** Saves about 4.5–5.5 days: 13 serial steps, two seals with
   about 16 tables, and two contract bumps. It also removes BLOCKER R3-02 and MAJORs R3-11, R3-17 and most
   of R3-18 from the beta. This is the least validated part: the original's chain had no live users, and
   its core files were never read.
2. **Cut the PDF report (client and analytic kinds, O-2 writer and font), keeping the deterministic MD
   summary download.** Saves about 1.5 days (REPORT L, part of VC-UI-02, the O-2 lock and font). It removes
   the recall problem of R3-02 from a document meant for the customer.
3. **Cut the multi-project resumable batch (CMP-INGEST-02), keeping single chunked upload with grouping.**
   Saves about 1 day and most of R3-23's DoS surface.
4. **Cut CMP-VC-SPEC-01 part B (AI whole-specification comparison), keeping part A (deterministic spec
   positions).** Saves about 0.5–1 day.
5. **Cut CMP-VC-AIPAIR-01 (AI check of doubtful pairs and accepted AI links), keeping algorithmic candidates
   and manual «Связать».** Saves about 0.5–1 day and removes R3-10 scenario 1.
6. **Cut the cross-set launch queue and the per-install AI queue (CMP-VC-QUEUE-01), keeping per-set
   buttons.** Saves about 0.5 day and removes R3-08 scenario 2.

All six together save about 8.5–10.5 days, which brings code-complete P80 back to about the plan's own P50.
Cuts 1–3 alone save about 7–8 days.

## Verdict

As written, this plan is not fit to dispatch as one 35-slice programme.
- Four blockers are design defects, not wording:
  - a spend journal without a pre-call record (R3-01);
  - an AI that can hide a deterministic change from every deliverable (R3-02);
  - a memory model built for the wrong host, which fails paid section runs (R3-03);
  - an upload that the storage port cannot carry and whose «delete» deletes nothing (R3-04).
- The majors show the same pattern three times: the plan copies an existing precedent's shape without its
  safety mechanism.
  - The summary journal is copied without the effect breadcrumb.
  - The original's cache key is copied without its reasons.
  - The probe loop is copied without a priority rule.
- It also treats `R-29` as if it controlled spending in production. It does not.
- Each fix is cheap and has a precedent in this repository: the `0014` breadcrumb, the `pdf_reader`
  sandbox, S3 multipart in `storage/**`, the original's CHANGED→UNCERTAIN rule, `IdempotencyKey`, a USD
  ceiling as in `OD-03`.

After those fixes, wave C0 and wave C1 are fit to dispatch, with C1's engine behind a measured A1 time,
RSS and bytes gate on a realistic input. C2–C4 should be re-judged after C1 against measured validator pass
rates and engine results. The stage module (cut 1) is the first candidate to leave the beta if the owner
keeps the date.

ROUND 3 VERDICT: 4 BLOCKER, 21 MAJOR, 9 MINOR
