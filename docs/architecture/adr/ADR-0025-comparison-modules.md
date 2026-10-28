# ADR-0025: Comparison modules: «Сравнение версий» and «Сравнение стадий» on a comparison-local queue and spend journal, a raw-then-AI evidence stack and bounded compute

- Status: accepted by the repository owner (poll answers `Q-CMP-1`…`Q-CMP-11` of 2026-10-27, recorded in `docs/program/dispatch/COMPARE-MODULES-PLAN.md` section 0; the integrator numbers them as rulings (plan open item `O-8`), and until it does they are cited by these ids). Every item marked «decided by CMP-ADR-01, revisable by CMP-MEASURE-01» is the architect's choice inside those answers: the owner has not confirmed it one by one, and `CMP-MEASURE-01` or the owner may change it by a dated addendum to this ADR
- Date: 2026-10-27
- Owners: repository owner / `CMP-ADR-01`
- Supersedes: nothing. It extends `ADR-0013` to the two new modules and, while the versions module is on, withdraws the controls `COMPARE-PERSISTED-SUMMARY-01` added to the version-scoped screen (decision 13)
- Related principles: P-01, P-02, P-03, P-06, P-07, P-08, P-10, P-11, P-13, P-15, P-16, P-17, P-18
- Related ADRs: `ADR-0007`, `ADR-0011`, `ADR-0012`, `ADR-0013`, `ADR-0021`, `ADR-0022`, `ADR-0024`

Every `CMP-*` seal and lane cites a decision of this ADR as «ADR-0025 decision n» instead of re-deciding it.

## Context

### The owner's answers

| Id | Answer in one line |
| --- | --- |
| `Q-CMP-1` | «Цепочка + ИИ-слой» for «Сравнение стадий»: deterministic sheet links and differences; the AI only classifies and summarises into «Было/Стало» cards that point at places in the sheets; an expert confirms each card. The live V3 pipeline of the original is not copied |
| `Q-CMP-2` | A stage comparison compares document pairs inside one project: one stage П document against one or several stage Р documents as an assembly («сборка»); a new stage-pair entity, no «object» entity |
| `Q-CMP-3` | «Сравнение версий» to full parity: projects table with seven steps, sheet matrix across all versions, deterministic per-sheet comparison in eight channels, overlay viewer, AI check of doubtful pairs, AI description of sheet changes, specification comparison, MD summary and PDF report |
| `Q-CMP-4` | Both modules are beta scope, and crops of drawings may be sent to a model in the comparison AI layers (this widens accepted risk `A-2` of `ADR-0022` to drawing images; the integrator records it) |
| `Q-CMP-5` | Plain PDFs in batches are admitted for comparison, marked as uploaded without a portal bundle; a section analysis on such a version still needs a portal bundle; a scan without text is compared as an image only |
| `Q-CMP-6` | Both modules in full before the beta |
| `Q-CMP-7` | Every AI job shows an estimate in USD and starts after consent; hard ceilings USD 10 per job and USD 50 per day per installation; an actual spend above 1.2 × the estimate pauses the job; `not_metered` connections are not limited by money |
| `Q-CMP-8` | The approved sheet pairs of migration `0035` become manual matrix edits by a data migration; the old buttons are removed; one history of pairs |
| `Q-CMP-9` | `numpy`, `opencv-python-headless` and `reportlab` with a free Cyrillic font whose licence allows embedding |
| `Q-CMP-10` | One deviation is accepted (GRAPHIC evidence in stage cards only for 1↔1 links); the automatic repair that may change an expert's link, the context-request loop of the AI runtime and the «ZIP-комплект» upload are built as in the original; one version set may be downloaded read-only into `.local/` to measure memory, time and bytes |
| `Q-CMP-11` | The complete gate before the beta is moved to debt; the estimate counts code writing only |

### Facts read from the tree

Read at `5867d704` on branch `agent/cmp-adr-01` (the base `cccdb6b8` plus the three CMP task files): contract `1.8.0`
(95 paths, 107 operations, 314 schemas), migration head `20261027_0036_cite_partition_v3`, `VERSION` `0.9.0`.

- **A Job is a Run.** `job.run_id text NOT NULL REFERENCES audit_run`, with `uq_job_run_id UNIQUE (run_id)` and
  `uq_job_run_job UNIQUE (run_id, job_id)` (`db/migrations/versions/20261002_0014_durable_analysis_effects.py:140`, `:159-160`).
  The claim locks the Run, then the Job (`src/auditmanager/jobs/repository.py:872-877`). `run_id` appears in 91 source files
  (`grep -rl run_id src --include=*.py | wc -l` prints `91`) and 123 times in `jobs/repository.py` alone
  (`grep -c run_id src/auditmanager/jobs/repository.py` prints `123`). The frozen contract requires `run_id` in `ExecutionQueueItem`
  and `ExecutionJournalEntry` (`contracts/api/v1/openapi.json`, `components.schemas`, `required`). The `job` state machine has no paused
  state (`contracts/domain/v1/state-machines.json`, machine `job`).
- **Spend is a Run's too.** `model_call.run_id NOT NULL` and `ck_model_call_stage_id`
  (`db/migrations/versions/20260910_0002_pc01_schema.py:820-840`); `provider_call_effect.run_id NOT NULL`, `ck_provider_effect_stage_id
  CHECK (stage_id = 'text_analysis')` (`0014:238-267`); the cost sums read by Run (`src/auditmanager/runs/repository.py:179`
  `_COST_SUMMARY`) and for the deployment (`src/auditmanager/dashboard/repository.py:105` `_SPEND`); the meter is per run
  (`src/auditmanager/analysis/text/cost.py:29` `BUDGET_SCOPE_RUN`, `:54` `CostMeter`).
- **The breadcrumb precedent.** `provider_call_effect` is committed in state `prepared` before a provider is called and runs
  `prepared → response_received → completed | outcome_unknown` (`0014:249`, `:275-276`). `comparison_summary` (migration `0035`) is the
  precedent for a comparison-owned cost record: `provider_mode`, `cost_basis`, `cost_micros` and their CHECKs
  (`db/migrations/versions/20261027_0035_comparison_records.py:394-409`, `:441-472`).
- **One image per request.** `checked_png` refuses any request with other than one image
  (`src/auditmanager/executors/image_input.py:39`) and accepts only a descriptor that carries a `portal_block_id`
  (`image_input.py:32-53`); the pull channel allows at most one (`src/auditmanager/executors/pull.py:194`); the contract caps
  `ClaimedExecutorTask.images` at `maxItems: 1` and requires `portal_block_id` in `RunnerImage`; `ModelRequest` carries one `image_bytes`
  (`src/auditmanager/analysis/text/adapter.py:44`). The runners already refuse an image task they cannot serve with
  `image_input_unsupported` (`tools/executor-runner/agent.py:291`, `claude_answer.py:78`, `mcp_bridge.py:384`). Nothing in `src/`,
  `tools/` or `contracts/` mentions `max_images`.
- **Work kinds.** `WORK_KINDS = ("text_analysis",)` (`src/auditmanager/executors/model.py:68`); `ExecutorWorkKind` is the enum
  `["text_analysis"]`; `ck_executor_route_work_kind CHECK (work_kind IN ('text_analysis'))`
  (`db/migrations/versions/20261022_0030_executor_connections.py:360`); `ck_executor_task_origin CHECK (origin IN ('run_call', 'probe'))`
  with a shape check that makes `run_call` require `run_id` and `attempt_id` (`20261022_0031_executor_pull_channel.py:163-167`).
- **A plain PDF is refused.** `refuse("portal_bundle_required")` (`src/auditmanager/ingest/bundle_archive.py:786`, message at `:200`).
  A version whose manifest has no `source.document` entry already fails the run start with `analysis_input_invalid`, reason
  `missing_required_input` (`src/auditmanager/runs/commands.py:385-392`). The error catalogue holds 27 codes, among them
  `dependency_unavailable`, `conflict`, `analysis_input_invalid` and `staged_upload_lost`.
- **Sheet pairs today.** `comparison_sheet_link` is append-only with a chain trigger (`0035:272`, `:115`); the comparison package has a
  text-line diff and match suggestions (`src/auditmanager/comparison/raw_text.py`, `sheet_match_suggestions.py`, `pairing.py`) and no
  raster code. The only renderer clips a crop plan (`src/auditmanager/analysis/geometry/render.py:121`) under the process-wide
  `PDFIUM_LOCK` (`src/auditmanager/ingest/envelope.py:171`).
- **Kernel-ceiling precedent.** The PDF reader runs in a child process that sets `RLIMIT_CORE`, `RLIMIT_AS` and `RLIMIT_CPU` first
  (`src/auditmanager/ingest/pdf_reader.py:62-68`); the envelope gives it 512 MiB and 60 s (`envelope.py:206`, `:209`) and admits one
  unencrypted PDF of at most 250 MiB and 1–500 pages (`envelope.py:153`, `:156`).
- **The worker.** Loops are started as threads and a `probe_runner` is hosted as one more loop
  (`src/auditmanager/workers/service.py:290`, `:381`; the runner is built in `src/auditmanager/bootstrap/composition.py:159-164`);
  `AUDITMANAGER_WORKER_SLOTS` defaults to one (`workers/service.py:25`; `R-146j`); heartbeat 20 s and attempt watchdog 900 s
  (`src/auditmanager/jobs/lease.py:20-21`). One connection serves at most one active Run under an advisory lock
  (`jobs/repository.py:50-65`, `:957-970`). The claim excludes a paused system (`jobs/repository.py:92`); the setter is exported by
  `jobs/public.py:8`, `:55`, and the reader by `execution/public.py:189` (`ExecutionRepository.dispatch_status`).
- **Storage.** The `BlobStore` port stages a temporary, verifies and publishes it, and can discard a temporary
  (`src/auditmanager/storage/port.py:66-101`); it has no multipart path and no operation that deletes a published blob (the only delete
  is the private `_delete` behind `discard_temporary`, `src/auditmanager/storage/s3.py:576`). The default proxy body cap is 32 MiB
  (`infra/deploy/proxy/nginx.conf:219`).
- **Erase.** `scripts/recovery/project_erase.py:112` lists the non-terminal states that refuse an erase (`audit_run`, `job`,
  `attempt`, `executor_task`).
- **Dependencies.** `pyproject.toml` pins `pdfplumber`, `pypdf`, `pypdfium2==5.13.0` (`:46`) and `Pillow==12.3.0` (`:48`) and records
  PyMuPDF as excluded (`:30-32`, `OD-01`); it names neither `numpy`, `opencv` nor `reportlab`, and `uv.lock` holds no `numpy`
  (`grep -c 'name = "numpy"' uv.lock` prints `0`).
- **Identity catalogue.** 48 prefixes in `contracts/domain/v1/identifiers.json`, format `<prefix>_<ULID>`, prefix pattern
  `^[a-z][a-z0-9]{1,7}$`; its rules say an identifier is never parsed, a path, file name, display ordinal or checksum is never an
  identity, and a new entity needs a new catalogue entry with a globally unique prefix.
- **Screens and the flag.** One screen exists under a version, «Сравнение прогонов»
  (`web/src/shared/config/screen-registry.ts:161`); no `AUDITMANAGER_COMPARISON_MODULES` exists outside the plan
  (`git grep -l COMPARISON_MODULES 5867d704` prints only `docs/program/compare/REVIEW-R3.md` and
  `docs/program/dispatch/COMPARE-MODULES-PLAN.md`). `getProductVersion` (`GET /system/version`) returns `ProductVersion {product_version, build_id, contract_version}`.
- **The host.** 4 GiB of RAM (`R-146ad`) and one worker slot (`R-146j`); the production disk size was never asked
  (`REVIEW-R3.md` `R3-05`).

## Decision

The numbering below is the numbering that seals and lanes cite. After each heading the plan items it fixes are named; where the plan
leaves a choice to this ADR the choice is stated and marked. Section 3.2 of the plan overrides the earlier text of the plan where they
differ.

### 1. Where the code lives (plan `A-1`, `R3-22`, `R3-30`)

New comparison logic lives in subpackages of `src/auditmanager/comparison/` created by the slices that need them. Plain-PDF admission
belongs to `ingest` and `documents`; the run-start refusal to `runs`; durable comparison work to `comparison/work`, hosted by `workers`;
model calls and images to `executors`. Contexts reach one another only through their `public.py`; the composition root adapts the ports
(`AGENTS.md` section 4). Lanes of a wave develop on the wave base and rebase their `adapters.py` hunk at their merge turn
(`R3-30`). The owners of the production hotspots are checked by the integrator at each seal's dispatch: `PROD-20` owns
`src/auditmanager/jobs/`, `PROD-05b` owns `infra/deploy/compose.server.yml`, and the `PROD-07` wrapper owns the `infra/**` erase files and
`scripts/recovery/product_purge.py`; a seal edits them only with that owner's grant (`R3-22`).

### 2. Identities (plan `A-2`)

`DocumentUid` is the series; the «шифр» is stamp metadata that an expert confirms, never identity. Every new identity has the catalogue
format `<prefix>_<ULID>`, is generated once, and is never parsed. A row marked «content-keyed» has a ULID id **and** a unique
content-key digest column; the digest is never a foreign key. The seal that adds a table adds the catalogue entry. Prefixes —
decided by CMP-ADR-01, revisable by CMP-MEASURE-01:

| Prefix | Identity | Content-keyed |
| --- | --- | --- |
| `cvo_` | version-order revision | no |
| `cpr_` | page profile (per version, per page) | yes |
| `cmx_` | matrix revision | no |
| `cme_` | manual matrix edit | no |
| `cak_` | accepted AI link | no |
| `cser_` | series of adjacent transitions | no |
| `csp_` | sheet-pair result | yes (the cache key of decision 15) |
| `cbt_` | upload batch | no |
| `cq_` | a row of `comparison_work` (a queue item; the launch queue of `CMP-VC-QUEUE-01` is itself comparison work, so its items are such rows) | no |
| `stp_` | stage pair | no |
| `sas_` | assembly | no |
| `slk_` | stage link revision | no |
| `crp_` | link repair | no |
| `crn_` | chain run | no |
| `cai_` | AI job | no |
| `ccd_` | card | yes (class and sorted evidence ids, decision 22) |
| `cdv_` | card verdict | no |
| `crt_` | report | no |

None of the eighteen collides with the catalogue at `5867d704`, and each fits the prefix pattern:
`python3 -I -c "import json;d=json.load(open('contracts/domain/v1/identifiers.json'));print(sorted(set('cvo cpr cmx cme cak cser csp cbt cq stp sas slk crp crn cai ccd cdv crt'.split()) & set(d['identifiers'].values())))"`
prints `[]`. The plan names no prefix for the rows of `comparison_work_attempt` and `comparison_model_call`; they are not decided here
(see «Left to the named slice»). A path, file name, display number, «шифр» or sheet number is never an identity and never a foreign
key; resume and grouping identities of an upload are opaque ids plus a declared sha256 and size.

### 3. Evidence layers and the effective matrix (plan `A-3`)

Raw deterministic layers — profiles, the algorithmic matrix, sheet-pair results, specification positions, permit reconciliation, text
fragments, exclusions, differences — are immutable rows or content-addressed blobs. AI layers — pair-check answers, accepted AI links,
sheet descriptions, reviewer decisions, classes, syntheses, report text — are separate rows that reference raw ids and never rewrite
them (`AGENTS.md` section 4; `ADR-0013`). The **effective matrix** is a read model: the algorithm, then accepted AI links (labelled
«ИИ», never an expert act), then manual edits (manual wins). A UI «final» layer is a read model over raw and AI rows. Every AI answer
passes a strict validator (schema, existing ids only, exact coverage, no invented numbers or designations); a failure keeps the
deterministic layer visible and marks the AI layer `failed` or `partial`. Downstream outputs that an AI decision shaped are marked: a
transition whose pairs depend on an AI link is marked in the series verdict, the MD summary and the report, and masked raw differences stay
listed in «Показать исходные текстовые различия» with their AI class.

### 4. Comparison work is durable and comparison-local (plan `A-4`, `R3-13`)

A Job is a Run in the schema, in the effect journals, in `model_call`, in the frozen contract and in the claim path (Context), so
comparison work does **not** enter `job` (rejected alternative 1). The comparison context owns a durable queue,
`src/auditmanager/comparison/work/**`, with tables `comparison_work` and `comparison_work_attempt` that copy the Lease pattern of `jobs`:
lease expiry, heartbeat, attempt count, pause, cancel, reclaim; heartbeat and expiry follow `jobs/lease.py`. No progress lives only in
memory. The worker hosts the comparison loop as a second loop the way `probe_runner` is hosted, counted against
`AUDITMANAGER_WORKER_SLOTS`. `executor_task` gains the origin `comparison_call` with a nullable `comparison_attempt_id`, the shape check
of `0031` and the live-attempt check of `runner_repository` get a branch for it, and the one-active-run-per-connection check also counts
active comparison AI work under the same advisory lock. The «Очередь» screen and its contract stay run-only.

**Handler registry — decided by CMP-ADR-01, revisable by CMP-MEASURE-01.** `comparison/public.py` exports one tuple of handler
factories. A handler has a unique `kind` string and a `run(item)` that returns a typed outcome (completed, failed with a reason, or
yielded). `build_worker_runtime` builds one dependency bundle once and applies every factory to it; the loop builds `{kind: handler}`
from the tuple and refuses to start on a duplicate kind or on a `comparison_work.kind` value that has no handler. A slice adds a handler by
appending to the tuple (plan section 4.0 rule 2). A test proves every `comparison_work.kind` value has exactly one handler.

### 5. Spend journal and the pre-call breadcrumb (plan `A-4`, `R3-01`, `R3-26`)

Comparison AI is recorded in its own journal `comparison_model_call`, with the columns and CHECKs of the `comparison_summary` precedent
(`provider_mode`, `cost_basis`, `cost_micros`). A row has the life `prepared → sent → completed | failed | unknown`. The `prepared`
row — request digest, attempt id, connection revision, pinned model, estimate share — is committed in its own transaction **before** the
adapter is called, as `provider_call_effect` does. On reclaim an item whose row is `prepared` or `sent` without a completion is never
re-sent automatically: it becomes `spend_unknown`, and only an explicit «Повторить» clears it. On the pull channel the `executor_task`
row is the breadcrumb; on HTTP direct the journal row is. The deployment spend that `R-29` reads is the union of the two journals in
`dashboard/repository.py` `_SPEND` only; the per-run `runs/repository.py` `_COST_SUMMARY` is untouched, because comparison work has no
Run (`R3-26`). Mutation proof: kill the process between send and commit, reclaim, and observe no second send and exactly one `unknown`
row.

### 6. Priority and operator control (plan `R3-07`)

Section and АР v3 runs have strict priority. The comparison loop claims only when no Run is claimable, and yields between items; an
item is one page or one pair, never a series. Comparison AI takes the executor connection per call, not per job. Comparison work honours
the global pause (`execution_control.paused`) and a module that is off (decision 23). The pause is read through the public entry of the
context that exports a reader — in the tree that is `execution/public.py:189`, because `jobs/public.py` exports only the setter — and
the comparison context never queries `execution_control` itself. «Очередь» gets an admin-visible, read-only section «Сравнение», owned on
the web side by `CMP-WORK-01` (one block of `web/src/widgets/execution-queue/**`). Throughput (pages per hour, pairs per hour, calls per
hour) is not measured yet; `CMP-MEASURE-01` writes it into an addendum (decision 27).

### 7. Project erase (plan `R3-25`)

`CMP-SEAL-C0` adds the non-terminal states of `comparison_work` and `comparison_work_attempt` to `NON_TERMINAL_STATES`
(`scripts/recovery/project_erase.py:112`) together with the test that derives that map from the migration's CHECKs. The comparison loop
re-checks, under a share lock, that the project exists before it publishes a blob. `blob_reference_audit.py` reports unreferenced
comparison blobs. A test proves that an erase during a leased comparison item is refused. Every new table is reachable from `project` by
foreign keys (profiles and results are per-version rows; there are no cross-project rows), so the erase closure holds.

### 8. Compute runs in a child process under a kernel ceiling (plan `R3-03`)

Every profile, engine and tile computation runs in a child process that sets `RLIMIT_AS`, a CPU ceiling and a wall ceiling before it
loads anything, as `ingest/pdf_reader.py` and `ingest/envelope.py` do. Defaults — decided by CMP-ADR-01, revisable by CMP-MEASURE-01:
**768 MiB** address space per item, **300 s** CPU, **600 s** wall (below the 900 s attempt watchdog of `jobs/lease.py:21`). The
production host has 4 GiB and one slot, so one child runs beside the API, the database and the object store; the upload reader's 512 MiB
(`envelope.py:206`) is the precedent. An overrun is a typed `needs_review` with reason `RENDER_FAILED` on that item only,
never «Совпадает». The engine tiles its full-resolution work to fit. The comparison worst case is added to `PROD-05a`'s measurement so
that the `AD-04` limits include it.

### 9. Bytes, pixels, masks and tiles: refusal caps and no eviction (plan `A-5`, `R3-05`, `R3-06`, `R3-23`)

There is **no eviction** of stored blobs in the beta: the storage boundary offers no delete of a published blob, and a delete from a lane
would be a dual write (rejected alternative 3). Previews and thumbnails are stored once per page. Masks are stored once per non-`same`
pair, as **one bit-packed blob** written by the engine in the worker; nothing is stored for a `same` pair. The API never calls PDFium: it
reads mask bytes and reduces them with `numpy`. Tiles of the A and B pages come from a **bounded pyramid rendered in the worker's child
process**; whether a level is kept as a blob or rendered again on request is left to `CMP-PROFILE-01` and `CMP-VIEWER-01`, and either
way the bytes it keeps count in the page budget. The full-page renderer is added to `analysis/geometry/render.py` under the existing
`PDFIUM_LOCK` and exported from `analysis/public.py`.

Abuse and capacity are bounded by refusal, never by deletion. Defaults — decided by CMP-ADR-01, revisable by CMP-MEASURE-01:

| Quantity | Value | Basis |
| --- | --- | --- |
| Version admission | the existing envelope: 250 MiB, 1–500 pages, unencrypted | `envelope.py:153`, `:156`; not a new number |
| Working raster per page | at most **40 Mpx**; the downsample-for-registration rule is fixed by `CMP-PROFILE-01` and `CMP-ENGINE-01`; a page that cannot be kept under the cap is refused with a typed state | A1 at 200 dpi is 6622 × 4677 = 30.97 Mpx; 2A0 (1682 × 1189 mm) at the same dpi is 123.99 Mpx |
| Stored bytes per project (sources and derived data) | at most **8 GiB**, refused when the declared bytes plus the stored bytes pass it, and per item when derived data would | `REVIEW-R3` `R3-05` arithmetic for 12 versions × 100 A1 sheets: sources 1–2 GB, previews and thumbnails 0.4–1.2 GB, masks 0.5–3 GB, 1.9–6.2 GB in all (a judge's estimate, unmeasured) |
| Upload chunk | 16 MiB on the default proxy location | under the 32 MiB body cap, `nginx.conf:219` |
| Batch | at most 10 000 files and 100 projects (the original's limits), **8 GiB** declared bytes and **10 000** declared pages, refused before the first part | the one real set in hand is 40 860 889 bytes and 85 pages for four versions (the table in `.local/comparison-measure/13AV-RD-EM2-PA/README.md`, outside git; plan section 9, `O-9`), so 100 such projects are ≈ 4 GB and ≈ 8 500 pages |
| Active batches | one per account, **two** per installation | one worker slot (`R-146j`) |
| Readiness | a finding `comparison-disk` when the free bytes of the object store's filesystem are under **11 GiB** (the project cap plus the 3 GiB reserve of the heavy-step stop rule, `infra/deploy/capacity-probe.sh:12-13`) | MinIO refuses writes near full, which is an outage of the whole product (`D-205`, `R3-05`) |

Declared pages are verified by the envelope when the item is read; a mismatch refuses that item. A refusal is a typed reason under an
existing error code (decision 25). `CMP-PROFILE-01` reports bytes per A1 page with peak RSS and `CMP-ENGINE-01` bytes per pair with peak
RSS; the per-project estimate above is replaced by those figures in the addendum.

### 10. Upload transport and multipart staging (plan `A-8`, `R3-04`)

Every comparison upload is chunked, 16 MiB per chunk, on the default proxy location, so no proxy file changes. The storage port gets
S3 multipart staging from `CMP-STORAGE-PARTS-01` (which owns `src/auditmanager/storage/**`): an opaque upload
token persisted **before** the first part, `UploadPart`, `Complete`, `Abort`, and verification of the whole object. A chunk has a database
owner (a declared blob) before its bytes are staged. A database-owned sweep of expired multipart uploads is comparison work that aborts
them; a sweep that only touches local temporaries is not enough, because the API container is recreated on every deploy. «Удалить пакет»
is renamed «Отменить пакет»: it aborts parts that were never completed, and the bytes of completed versions are removed only by the
operator's project erase (`R-146c`). Resume and grouping identities are opaque ids (`cbt_` and the item id) plus the declared sha256 and
size; file names and folders only feed the proposal that the user confirms. The 10 000-file and 100-project limits are typed refusals.
The portal-bundle upload is unchanged.

### 11. Plain-PDF admission, the version mark and the current-version rule (plan `A-8`, `R3-16`, `Q-CMP-5`)

`ingest` admits a plain PDF for comparison under a distinct manifest role (not `source.document`), so the existing start-run check
refuses it. `CMP-INGEST-01` adds the reason value `comparison_only_version` and its Russian sentence under the existing code
`analysis_input_invalid` — the catalogue stays at 27 codes. `DocumentVersion` gains an upload-kind field so that every existing screen
can mark the version «загружено без пакета портала» and disable its run start (`CMP-VERSION-MARK-01`). Passports and fragments of every
comparison input come from the page profile (stamp, words with boxes, vector lines); portal artefacts, when present, are optional extra
evidence. Stage (П/Р) and section of a plain PDF are a stamp proposal that an expert confirms through the existing classification
operations. A scan gives no TEXT evidence and is compared as an image only. A comparison-only version never becomes
`current_version_uid` of a document that has a portal version; a test per consumer of `current_version_uid` proves it.

### 12. ZIP sets of whole stages (plan `R3-17`, `Q-CMP-10`)

`CMP-INGEST-ZIP-01` parameterises the `bundle_archive` reader with a set policy: at most N entries, a total of at most 2 GiB, a PDF
envelope per member, no nested archives beyond one level, names never identity. The policy parameter is the only edit of
`bundle_archive.py`. The slice has its own security judge. N is the slice's, taken from the original's candidate table when
`CMP-ORIGINAL-READ-01` has read it.

### 13. One truth for sheet pairs of versions (plan `A-12`, `Q-CMP-8`)

The effective matrix (decision 3) is the only canonical store of «page X of version A ≙ page Y of version B». `CMP-SEAL-C1`'s migration
converts every active approval of `comparison_sheet_link` (`0035`) into a manual matrix edit with its actor, time and the `0035` ids in
its provenance; the `0035` rows stay as immutable history. When the versions module is on, `approveSheetPairing`,
`withdrawSheetPairing` and `generateComparisonSummary` answer `dependency_unavailable` with a reason that names the new module, and the
version-scoped screen drops those controls; its heading becomes «Сравнение с другой версией: находки». Finding match proposals and
decision carry-over keep their own proposals from runs (`comparison/carryover.py`, `comparison/finding_match_suggestions.py`),
unchanged. The web edits (`web/src/entities/version-comparison/**` included) belong to `CMP-VC-UI-01`.

### 14. Matrix revisions (plan `R3-10`)

An accepted AI link binds the algorithmic matrix revision and the cell state it answered; it applies only while that cell is still
unmatched or doubtful, otherwise it shows as superseded. «Применить сопоставления (N)» carries the base matrix revision; a mismatch
answers `conflict` with a reason, and the client rebases its draft. A manual edit binds the version-order revision; a reorder marks the
edits whose cells no longer exist as orphaned and never applies them silently. A mutation proof for each rule.

### 15. Cache key (plan `A-5`, `R3-09`)

A sheet-pair result is keyed by: the content Merkle of page A (its content stream and every referenced resource, XObjects and images
included), the same for page B, the annotation hashes, the sorted link reasons, the split part, the parameters and `ALGO_VERSION`. The
unique key also includes `project_uid`, so a result is reused within a project only. Mutation proofs: the same pages with a MEDIUM link give
`needs_review`; an annotation-only change gives `different` in `annotations`; a scan with a replaced image is not `same`; a change of
`ALGO_VERSION` changes the key. The key is the content-key digest of `csp_` (decision 2).

### 16. Expert acts (plan `A-7`, `R3-29`)

Stage-card verdicts («Принято» / «Не принято» with a reason) are append-only, keyed, audited and need the expert role (`R-60`). Manual
matrix edits, stage links and «Порядок версий» are expert acts with history; an administrator without the expert role is refused. The
version order never changes the documents' ordinal that runs and finding carry-over use (`D-5`). Version comparison has no verdict in
the original; its AI texts keep the label that they are model output not confirmed by an engineer, as `R-146ba` kept it above the
comparison summary.

### 17. Work kinds and routing (plan `A-6`)

Model work goes through «Исполнители» only. Five work kinds are added; their names are fixed here: `comparison_pair_check`,
`comparison_sheet_changes`, `comparison_spec`, `comparison_stage_review`, `comparison_report`. They are added to `WORK_KINDS` / `SERVES`
in `src/auditmanager/executors/model.py`, to the contract enum `ExecutorWorkKind`, to
`web/src/entities/executor-connection/model/vocabulary.ts` and to `web/src/widgets/executor-routes/`, and routed in «Назначения».
`ck_executor_route_work_kind` (`0030:360`) is widened by `CMP-SEAL-C2`'s migration. The model of the routed connection is pinned
(`R-133`: a reply from another model is a typed refusal), and every test uses recorded mode. An operator routes the new kinds on the stand
after the code (plan `O-6`).

### 18. Images and server-side gating (plan `A-6`, `R3-15`, `Q-CMP-4`)

`CMP-EXEC-IMAGES-01` extends the image channel from one portal-block PNG to several images per request, each addressed by an opaque
crop reference — crop id, blob id, sha256, size and media type — that is not bound to a portal block, on every served channel (HTTP
direct, VPN and SSH tunnel, pull command, local endpoint, MCP session, SSH command). Limits — decided by CMP-ADR-01, revisable by
CMP-MEASURE-01: at most **8** images per request, **16 MiB** per image (the existing `MAX_IMAGE_BYTES`, `image_input.py:19`) and **32
MiB** in all. The estimate counts images and image bytes. The contract part (`RunnerImage` without a required `portal_block_id`,
`ClaimedExecutorTask.images.maxItems` above 1, the `executor_task` origin) is sealed by `CMP-SEAL-C0`; the one-image field of
`ModelRequest` is granted to `CMP-EXEC-IMAGES-01` after `PW5`'s `SX` lane has merged; the runner tools are updated by the same slice.

**Gating is on the server.** The claim request carries the runner's declared `max_images`; an absent value means 1, which is the shape
every deployed runner sends today. The server never hands out a task with more images than declared. A runner already deployed on a
remote host that does not support several images therefore never receives such a task; if one is nevertheless failed it fails with
`image_input_unsupported` and never answers on a subset of the images. A test claims with an old-shape request and asserts that no
multi-image task is offered.

### 19. Money (plan `R3-08`, `Q-CMP-7`)

Estimates are in USD from the pinned rates. Ceilings are USD 10 per job and USD 50 per day per installation, enforced before each call
with the meter's before/after checks. Each consent binds {estimate digest, USD ceiling, connection revision, pinned model}; a change of
route or revision, or an actual spend above 1.2 × the estimate, pauses the job with a typed state and asks for a new consent. The launch
queue asks for AI consent per set only when its estimate exists. Every new write carries an `Idempotency-Key`. `not_metered`
connections are not limited by money. Live spend follows `R-29`.

### 20. No hidden change (plan `R3-02`)

A model's SAME or MOVED on a fragment whose deterministic status is CHANGED, REMOVED or ADDED becomes UNCERTAIN: a REVIEW card, no mask.
MOVED is accepted only with a found target outside the accepted link. An invented number or designation turns only the affected decision
into UNCERTAIN. An expert may move any SERVICE_STRUCTURE item or masked fragment into a REVIEW card, as an expert act with history.
The journal, the Excel and every PDF/HTML print «Скрыто ИИ как одинаковое: N; отнесено ИИ к служебным: M; экспертом не проверялось».
The client PDF report prints a recall line («изменённых листов N, описано K, отброшено проверкой D») and the unconfirmed label on every
page. An AI SAME never removes a raw difference row. Mutation proofs for each.

### 21. Stage pairs, chain runs and staleness (plan `A-9`, `R3-32`, `Q-CMP-2`)

A stage pair binds `DocumentUid`s: one on the П side, one or an assembly of several on the Р side. Each chain run pins the exact version
ids of every member. A newer version marks the run stale («Есть новые документы — сравнение не обновлено»). Staleness markers compare
stored input digests, never timestamps. Cards and verdicts belong to the run they were made on.

### 22. Cards, verdicts and carry-over (plan `A-10`, `R3-11`)

A card is a Stage-5 aggregate of the chain document: class (PROJECT_CHANGE, SERVICE_STRUCTURE or REVIEW), category, title and its atomic
evidence ids; its identity is a digest over the class and the sorted evidence ids. Verdicts are taken on PROJECT_CHANGE and REVIEW cards;
SERVICE_STRUCTURE is one collapsed block without verdicts. «Подтверждено изменений» counts accepted PROJECT_CHANGE and REVIEW cards. The
Stage-5.3 high-level changes are a read view over cards. «Шифр» and «Раздел» come from the documents deterministically; «Система» is a
classifier field taken from a **closed list that the validator enforces**; the members of that list are fixed by `CMP-SEAL-C4` before
`CMP-STAGE-AI-01` starts, because the tree holds no list of systems.

Evidence ids are content-keyed (side, document, version, sheet, normalised text, rounded box anchor). A verdict binds to the evidence
set, not to the model's class or grouping, and carries over **per evidence** to a newer run. A card whose evidence set is a superset or a
subset of a decided one shows «частично перенесено» and never loses a verdict silently; a verdict whose evidence digest changed is
shown as stale. Mutation proof: a rerun with no input change carries 100 % of the verdicts.

The Excel journal is written by `CMP-STAGE-REVIEW-01` inside `src/auditmanager/comparison/stage_review/**` with the stored-ZIP technique of
`exports/xlsx` (`src/auditmanager/exports/xlsx/writer.py:374`); there is no generic sheet writer (`R3-34`, `AGENTS.md` section 4). The PDF
export of tab 4 uses the PDF writer of decision 24.

### 23. The module flag and the screens (plan `A-11`, `R3-12`, `R3-31`)

The module set `AUDITMANAGER_COMPARISON_MODULES` (values `none`, `versions`, `versions,stages`) is exposed to the web **through the
contract**: an additive field of the existing product-version read or of the session subject that `screenDecision` already receives,
added by `CMP-SEAL-C0`; `navigation.ts` and `screenDecision` filter by it. The web never imports `server-env.ts` for it. The worker loop
and every comparison command refuse when the module is off, and a test proves that turning a module off pauses its queued comparison work.
A module that is off has no menu entry and its operations answer `dependency_unavailable`; its route still exists in the tree and in the
journey manifest. New FSD slices do not collide with the existing `_pages/stage-comparison` and `widgets/stage-comparison`:
`web/src/_pages/version-compare/`, `web/src/_pages/stage-compare/`, `web/src/entities/version-series/`, `web/src/entities/stage-pair/`.
The project is chosen on the screen. Styles are the product's own (`--am-*`, no UI library). On our screens the original's «проект» (a
document set) is written «комплект (шифр)»; «проект» keeps our meaning. Rollback is the flag: a wave that cannot finish leaves its
module off and the version-scoped screen as it was.

### 24. Dependencies (plan `A-5`, `R3-20`, `Q-CMP-9`)

`numpy` (BSD-3), `opencv-python-headless` (Apache-2.0, for phase correlation, morphology and connected components) and `reportlab`
(BSD) with a free Cyrillic font whose licence allows embedding. `CMP-SEAL-C0`, which owns the root lock slot, takes the three packages
once: `pyproject.toml`, `uv.lock` (which needs network), `docs/program/P02_LOCK.json` and the `DIRECT` tuple of
`tests/contract/test_w55b_direct_pins.py`, with the licences of everything the wheels bundle recorded and the image size noted, before the
profile and engine lanes start. The font file and its licence live together under `src/auditmanager/comparison/report/fonts/**`, granted
to `CMP-VC-REPORT-01`, which chooses the family. PyMuPDF stays excluded (`OD-01`). `CMP-ENGINE-01` has a time gate per A1 pair inside the
ceiling of decision 8. A dependency that `Q-CMP-9` did not approve is a STOP.

### 25. Contract surface of the seals (plan section 4.0 rules 3–5, `R3-21`)

Seals are serial (C0 → C1 → C2 → C2 FIX → C3 → C4), and each holds the contract and the migration head from its start to its merge.
Each seal is one additive minor bump of the API contract — `1.9.0`, `1.10.0`, `1.11.0`, `1.12.0`, `1.13.0`, or the next free minor at
dispatch — and takes the migration head plus one. A seal that adds tables owns the per-table family from its probe (schema coverage,
grants, purge, erase, blob audit, the tests that pin table counts). No new error code is added unless no existing code fits; a new reason
under an existing code is the default. Each seal publishes per-sheet and per-change results as versioned object schemas with explicitly
optional members; a lane that needs a new field STOPs to the wave's FIX slot and never edits the contract. A sealed operation is a stub
answering `503 dependency_unavailable` until its lane implements it. Every new operation is reviewed for exposure (`CMP-EXPOSURE-01`). Before wave C0 the integrator records the poll answers as rulings,
widens accepted risk `A-2` of `ADR-0022` to drawing images, extends `R-135` to the CMP waves (`R3-33`) and tells the executor workstream
and the `PROD` owners of decision 1 (plan `O-8`).

### 26. Deviations from the original (plan section 1.3, `Q-CMP-10`, `R3-18`)

- **Accepted — `D-2`.** GRAPHIC evidence in stage cards is an addition beyond the original: allowed only for 1↔1 links whose
  registration is reliable; otherwise the card says «графика не проверялась». TABLE evidence means text fragments of table rows, not a
  table extractor.
- **Withdrawn — `D-1`.** The automatic link repair behaves as in the original: with HIGH proof it may change an expert's link, as a
  recorded, revertible automatic act shown «Исправлено автоматически», with the expert's previous link in its before-snapshot and
  «Откатить». A deterministic repair is not an LLM decision.
- **Withdrawn — `D-3`.** The AI runtime follows the original: a main call, one technical retry, one model context request and one
  unparsed-record pass per item; a 429 waits 20, 60, 120, 300 and 600 s; quota and authorisation failures pause the job with a typed
  state. Every call goes through the breadcrumb of decision 5.
- **Built as in the original.** The «ZIP-комплект» upload of whole stage sets, with the safe reader of decision 12.
- **Deliberate, unchanged.** `D-4` grouping in tab 4 really groups and exports work; `D-5` the version order never changes the documents'
  ordinal.
- **Unread sources (`R3-18`).** `CMP-ORIGINAL-READ-01` reads the original's repair, matching, review, text-comparison, specification,
  report-prompt and Luna sources before wave C0. A slice whose source stays unread is tagged `[own design]` and accepted on answer keys.
  The original's stage chain had no live users (its buttons were dead in the live UI).

### 27. Measurement gates, fixtures and the right to revise (plan `R3-14`, `R3-19`, `Q-CMP-10`)

`CMP-FIXTURES-01` merges first after `CMP-SEAL-C0` and adds a realistic A1 generator (strokes-only text, `/Rotate`, a CropBox offset,
one OCG layer, hatches and dashes, about 75 000 elements, a second producer's rendering of the same sheet). `CMP-MEASURE-01` runs between
C0 and the merge of the C1 engine: one version set downloaded read-only from the original's instance into `.local/` (outside git), time,
RSS and bytes measured under the ceiling of decision 8 with their commands recorded, the engine's statuses compared with the original's
for that set, the set never sent to a model and deleted afterwards. `CMP-ENGINE-01` merges only with the A1 time/RSS/bytes gate met on that
set or on the realistic generator. One live run per AI work kind on three synthetic items under USD 0.50 each records the validator pass
rate; below 80 % the slice STOPs. **Every value marked «decided by CMP-ADR-01, revisable by CMP-MEASURE-01» is revised only by a dated
addendum to this ADR** that gives the measured figure, the command and the tree; a lane never changes such a value on its own.

## Left to the named slice

The plan does not settle these, and this ADR does not add a decision for them:

- the identity prefixes of the rows of `comparison_work_attempt` and `comparison_model_call` — `CMP-SEAL-C0` names them in the same
  catalogue entry as the tables; they must be new prefixes (the catalogue says a new entity needs a new prefix), not `att_` or `mc_`;
- the members of the closed «Система» list — `CMP-SEAL-C4`;
- the carrier of the module flag (the product-version read or the session subject) — `CMP-SEAL-C0`;
- the font family — `CMP-VC-REPORT-01`; the exact dependency pins — `CMP-SEAL-C0`;
- the entry limit N of a ZIP set — `CMP-INGEST-ZIP-01`;
- the pyramid levels and whether a level is stored — `CMP-PROFILE-01` and `CMP-VIEWER-01`;
- which seal first carries the name `comparison_stage_review`: the plan lists it with the work kinds of `CMP-SEAL-C2` (`A-6`) and again in
  `CMP-SEAL-C4`; the contract enum is additive, so either order is valid, but one seal must own the migration of the CHECK.

## Consequences

### Positive

- Comparison work cannot starve or break the primary product: it has its own durable tables, its own spend journal, strict priority
  below section runs, and the global pause.
- A paid call is never repeated by a reclaim, and an interrupted one is visible as `spend_unknown`.
- Raw evidence is immutable and an AI layer cannot hide a deterministic difference; every figure in the report can be traced to a raw row.
- A bad page costs one item, not the worker: the child process and the kernel ceiling bound memory and time.
- Disk use is bounded by refusal at known numbers, and an operator can read them from one place.

### Negative / cost

- A second queue, a second journal and a second hosted loop duplicate the Lease pattern of `jobs` and must be kept equal to it by tests.
- The spend union is written in one query (`_SPEND`); every future spend reader must remember the second journal.
- With no eviction and no delete of published blobs, a project's bytes stay until an operator erases it; a full disk is the failure
  mode, and the caps and the readiness finding are its only defence.
- Several images per request widen accepted risk `A-2` of `ADR-0022` to drawing images, and a remote runner that is not updated receives
  no image task at all.
- Three native dependencies enter the root lock and the image; `uv lock` needs network and the gate before the beta is moved to debt
  (`Q-CMP-11`, plan `O-7`).
- Every marked number is unmeasured until `CMP-MEASURE-01`; a wrong default costs a refusal or a slow page, not a wrong verdict.

## Alternatives considered

1. **A shared `job` subject for comparison work.** Rejected. A Job is a Run in the schema, the effect journals, `model_call`, the
   frozen contract and the claim path (91 source files name `run_id`), and the `job` machine has no paused state; a typed subject
   cannot be built inside one lane and would break a frozen contract (`REVIEW-R2` `R2-02`).
2. **The live V3 pipeline of the original for «Сравнение стадий».** Rejected by `Q-CMP-1`: the owner chose the deterministic chain with an
   AI layer that classifies and summarises over evidence an expert can check.
3. **Eviction of stored blobs when disk runs low.** Rejected. The storage boundary offers no delete of a published blob; a delete from
   a lane is a dual write of database and object store without outbox or reconciliation (`AGENTS.md` section 4). Refusal caps and a
   readiness finding replace it.
4. **Automatic re-send of an item whose call may have been sent.** Rejected. It pays twice and cannot be told from a lost reply; the item
   becomes `spend_unknown` and a person clears it (decision 5).
5. **Publishing every upload chunk as a canonical blob.** Rejected. It doubles storage forever with no delete; multipart staging with
   an abort sweep replaces it (decision 10).
6. **A sweep through `jobs/temporaries.py`.** Rejected. That sweep removes three exact local file names in the container's `/tmp` and
   never touches the object store (`REVIEW-R3` `R3-04`).
7. **Masks recomputed or tiles rendered in the API process.** Rejected. PDFium is guarded by one process-wide lock; one expert zooming an
   A1 overlay would queue dozens of tile requests behind it on a 4 GiB host. The worker renders, the API reads bytes.
8. **Trusting a model's SAME on a fragment the deterministic layer calls CHANGED.** Rejected (decision 20): an AI layer must not modify
   raw evidence, and a silent loss of a real difference is the product's worst failure.
9. **PyMuPDF for raster and text.** Rejected. It is AGPL and `OD-01` blocks a copyleft library until the owner rules otherwise; the owner
   chose `numpy` and OpenCV beside the pinned `pypdfium2`, `Pillow`, `pdfplumber` and `pypdf` (`Q-CMP-9`).
10. **Reading the module flag from the environment in the browser layer.** Rejected (`R3-12`): the contract carries it, so the menu, the
    route guard and the API agree.
11. **Keeping the `0035` approval buttons beside the matrix.** Rejected by `Q-CMP-8`: two stores of one fact drift.
12. **A `limit_req` rule at the proxy against upload abuse.** Rejected. The zone key is empty for every request but registration, token
    exchange and the runner, and `limit_req` does not account an empty key, so uploads are never throttled and a check against it always
    passes (`infra/deploy/proxy/nginx.conf:91-99`); caps are enforced in the application and refused before the first part (decision 9).
13. **Keeping deviations `D-1` and `D-3`.** Rejected by `Q-CMP-10`; the original's behaviour is built, with the breadcrumb on every call.

## Verification

Each commitment is checked by a test in the slice named in the last column. The Mutation column is the failure that the check must show
under a quoted mutation (`R-70`); a guard without a demonstrated failure does not count.

| # | Commitment | Mutation the check must catch | Delivered by |
| --- | --- | --- | --- |
| 1 | New prefixes are unique and fit the pattern (decision 2); the command in decision 2 prints `[]` | add `blk` or `att` to the list | each seal |
| 2 | `comparison_work`, `comparison_work_attempt` and `comparison_model_call` have no foreign key to `job`, `attempt` or `audit_run` (decisions 4, 5) | a foreign key added to `job` | `CMP-SEAL-C0` |
| 3 | Reclaim of a `prepared`/`sent` call never re-sends (decision 5) | kill between send and commit: no second send, one `unknown` row | `CMP-SPEND-01` |
| 4 | Comparison claims only when no Run is claimable and honours the pause (decision 6) | a claimable Run left unclaimed while a comparison item runs | `CMP-WORK-01` |
| 5 | An erase during a leased comparison item is refused (decision 7) | remove the states from `NON_TERMINAL_STATES` | `CMP-SEAL-C0` |
| 6 | A child process that passes its address-space ceiling ends one item as `RENDER_FAILED` (decision 8) | remove the `RLIMIT_AS` call: the child is no longer ended | `CMP-PROFILE-01` |
| 7 | A page above the pixel cap is refused, not rendered (decision 9) | raise the cap: the page renders | `CMP-PROFILE-01` |
| 8 | A comparison-only version is never `current_version_uid` of a document with a portal version (decision 11) | a consumer reads it | `CMP-INGEST-01` |
| 9 | Manual beats AI in the effective matrix; a stale base revision answers `conflict` (decisions 3, 14) | swap the layer order; ignore the base revision | `CMP-MATRIX-01` |
| 10 | The cache key changes with `ALGO_VERSION`, an annotation and a replaced scan image (decision 15) | drop one input from the key | `CMP-ENGINE-01` |
| 11 | An old-shape claim is offered no multi-image task (decision 18) | ignore `max_images` | `CMP-EXEC-IMAGES-01` |
| 12 | A consent precedes a call; spend above 1.2 × the estimate pauses the job (decision 19) | start a call without consent | `CMP-VC-AISHEET-01` |
| 13 | A model SAME on a CHANGED fragment becomes UNCERTAIN; an AI SAME removes no raw row (decision 20) | accept the model's SAME | `CMP-STAGE-AI-01` |
| 14 | A rerun with no input change carries 100 % of the verdicts; a changed digest shows stale (decision 22) | bind a verdict to the class instead of the evidence | `CMP-STAGE-REVIEW-01` |
| 15 | Turning a module off pauses its queued work and removes its menu entry (decision 23) | ignore the flag in the loop | `CMP-SEAL-C0`, `CMP-WORK-01` |
| 16 | Every `comparison_work.kind` has exactly one handler (decision 4) | register a kind twice, or none | `CMP-WORK-01` |

## Revisit trigger

Replace or amend this ADR when `CMP-MEASURE-01` records its figures (a dated addendum), when the production disk size is known, when a
second worker slot or a service-level objective is wanted (`ADR-0024` section 5), when the storage boundary gains a delete of published
blobs, when the owner widens the comparison to sections beyond those the plan names, or when a real client set shows that the
human-confirmed cards disagree with the deterministic layer often enough to change decision 20.

## Addendum 2026-10-27 — values from CMP-MEASURE-01A

Source: `docs/program/compare/MEASURE-RENDER-01.md` (450 child jobs, none over the ceiling; the real set of four
versions with pages up to 1682×1189 mm, the synthetic corpus, the realistic A1 from both producers). Changes to the
values this ADR marked «revisable by CMP-MEASURE-01»:

1. **Decision 8 (child ceilings).** Render, registration and tile children keep 768 MiB, CPU 300 s, wall 600 s. The
   child that runs `pdfplumber` words and lines gets **1024 MiB** (the heaviest real extraction needs 704 MiB with
   VmPeak 658–674 MiB). Any end without a result — `MemoryError`, a signal (PDFium aborts with SIGABRT/SIGTRAP below
   its need) or a CPU stall — maps to a typed `RENDER_FAILED` on that item; one item is one page per child.
2. **Decision 9 (caps and storage).** The working raster cap stays **40 Mpx**; registration dpi =
   `min(200, floor(sqrt(40e6 / (w_in × h_in))))`. The whole tile pyramid is **not** stored (54–137 % of the 8 GiB
   project cap for 1 200 pages): the worker stores preview and thumbnail per page (0.4–1.3 GB per 1 200 vector pages)
   and may store tile levels 2 and up; levels 0 and 1 are rendered on request in a child process under the 768 MiB
   ceiling, never inside the API process. The 8 GiB per-project cap stays.
3. **Admission (decision 11, for CMP-INGEST-01).** The existing envelope (`src/auditmanager/ingest/envelope.py`,
   `PAGE_ELEMENTS_MAX` = 400 000) would refuse the measured real set (one page has 536 426 elements). Comparison-only
   admission uses a comparison envelope policy whose per-page element limit is set from this measurement (the
   comparison path renders and extracts only in ceilinged children); the portal-bundle envelope is unchanged.

## Addendum 2026-10-28 — identity prefixes added by CMP-SEAL-C1

`ctn_` (a transition of a series) and `ctp_` (a sheet pair of a transition) join the prefixes of decision 2; the
catalogue now holds 63 prefixes. ADR-0025 decision 7's wording «FOR SHARE on project» is replaced by what CMP-WORK-01
proved necessary: the application role cannot lock a `project` row (no UPDATE), so the queue relies on item and attempt
row locks plus `ON DELETE RESTRICT` on `fk_comparison_work_project`.
