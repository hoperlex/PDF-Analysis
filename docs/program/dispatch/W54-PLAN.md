# Wave 54 — corpus custody, repair and the promotion bundle ∥ worker service, «Исполнители» and the AR-1 probes

**Status:** revision 4 with the fix round, 2026-10-12, on `plan/corpus-chain`. Directives CD-1…CD-21
(`docs/program/reviews/W54-W57-CHAIN-REVIEW.md`), judging and history
(`docs/program/reviews/W54-W57-CHAIN-JUDGING.md`), owner answers K-1, K-5…K-12 (`ROADMAP-TO-BETA.md` §10.16).
Base: `origin/dev` `4fe7615` (head `0017`); `origin/main` `2653dbf` is `v0.4.0`, and the stand is at `0017`
with MinIO recreated under `R-83` and no client-object read-back. Dispatchable after an entry commit adopts
this plan on `origin/dev` and `W54-FREEZE-01`. Rulings used: `R-76` custody, `R-77` backup deferred,
`R-79` retry limits, `R-80` role-less accounts, `R-85` (W53's stops; `D-153` replaces `W53-EXEC-STOP-01`),
`R-86` (0.4.0 with the 0.3.0 history row). `R-103`…`R-107` (renumbered at `W54-RULE-01`; K-1…K-15 took `R-103`…`R-102`).
**Exit:** the candidate on `origin/dev` with literal `GATE OK`; P2 published on the owner's instruction
(§3.10); then, on this machine, the promotion database with the repaired snapshot and a complete build and a
verified bundle; every stand-side tool W55a needs rehearsed on a disposable local stand. No corpus byte
reaches the stand in this wave (F-1). `v0.5.0` is a target under §8.4 and `R-86`.

## 1. Objective

- **Track 1 — the corpus foundation here (F-1, F-3).** Two-phase custody (`R-76`); the 121 repairs through a
  durable call journal under the $10 exception (W-4); `D-124`, `D-126`, `D-127` closed, `D-125` evidenced; a
  resumable embedder and a pinned BGE image; a promotion database; a bundle; the importer, both
  forced-command keys and the one-off copy tools that P2–P4 use (CD-3, CD-16, K-1, K-6).
- **Track 2 — execution and AR-1 groundwork.** A worker service with a registry; «Исполнители»;
  report-only probes of the portal's OCR bundle and of image input through the proxy (G-3's price per crop).

## 2. Where it starts

The measured facts and their `path:line` pins (re-measured on `4fe7615`) go into `W54-FREEZE-01`'s task
file. The ones that shape this plan: the drop's `MANIFEST.json` records sizes and no digests, and
`content_key` hashes `results.md` only (`norms/snapshot.py:89-95`); `NORM_CORPUS_CUSTODY.md:39, 52-54`
validates the target rows inside the intent transaction; `norm_embedding` rows need a completed build row
(`0013:121-150`); `record_declared` is a SELECT then an INSERT without `ON CONFLICT`
(`storage/blob_repository.py:65, 162-176`), called from `runs/executor.py:344`; `ProxyDispatchError`
(`analysis/text/proxy.py:83-98`) is not exported by `analysis/public.py`; the stand's compose has no
`worker` service; this host has one filesystem `/` with 14 GiB free (`df -B1G`, 2026-10-12), and its
available RAM fluctuated between 2.6 and 7.3 GiB that day (the session's heartbeats).

## 3. Design decisions bound by this plan

### 3.1 Custody

As frozen by `R-76`: content-derived Blobs, roles on bindings, reuse after size, SHA-256 and media-type
checks, reject the admission or Attempt and never the Blob row, erasure only without a live binding,
opaque anchors, `nad`/`nbd`, the outbox, five tries (30 s … 2 h; E-7, left to W54 by `R-79`) and
`admit|dispatch --until-idle|reconcile|report|requeue`. The only source of custody objects is a verified
bundle on the stand; the drop is never admitted. Implementation choices:

- **Two phases.** *Admission* appends intent and outbox with role, anchor, declared size, SHA-256, media
  type and the declared target, checked against the verified manifest. The dispatcher stages, verifies and
  publishes the Blob and marks the admission `confirmed`; no binding is visible. *Binding publication*
  `publish_bindings(role, target)` (CD-19) runs in the transaction that holds the target rows, locks each
  confirmed admission, checks invariant 4 there (moved from intent time to publication time) and inserts the
  binding with its audit event. A confirmed admission whose target never arrives stays unbound and reported.
  SEAL rewrites `NORM_CORPUS_CUSTODY.md`'s sequence and its stale batch section (`:86-102`, the
  re-recognition order); invariants 1–3 and 5 are unchanged.
- **Generic roles and targets.** `norm_custody_admission` and `norm_custody_binding` carry `role`,
  `target_kind` and `target_id` (text) plus the anchor; one named CHECK, `ck_norm_custody_role_shape`, maps
  each role to its target kind (`norm_source` → `norm_document`, PDF or crop anchor). W57a adds
  `norm_retrieval_set` and `norm_catalogue`, whose targets are not norm documents, by replacing that CHECK in
  its migration; W57a holds `norms/custody/roles.py` and the custody document's roles section from then on.
- **D-146:** `record_declared` becomes idempotent (`ON CONFLICT` on `blob_id`, then re-read and compare)
  under a per-blob advisory lock inside `BlobMetadataRepository`; two declarers of equal bytes serialise
  before a second worker exists. `ingest/service.py` is untouched.
- **D-142:** `analysis_artifact_publication` gains `abandoned` (`prepared → abandoned` when its Attempt is
  terminal and unbound), settled by `settle_terminal_provider_effects` (`jobs/repository.py:860`) with a
  journal event, so the reconciliation report is clean after a crash and rerun.
- **D-148:** `0018` recreates both effect-table state guards as `BEFORE INSERT OR UPDATE`; an insert must be
  `prepared`.
- **D-143:** no Blob state-machine edge. `custody report` lists `rejected` rows; an admission of such bytes is
  refused, naming D-143. P2's copy record measures the stand's `rejected` count: zero closes D-143; rows
  outside any manifest stay registered and never stop P4; only a `rejected` manifest Blob is refused.

### 3.2 The promotion database (identity origin)

A persistent local PostgreSQL, `promotion`, holds the base snapshot, the repaired snapshot, its build and
the repair journal. Every opaque id (`ns_`, `ndoc_`, `npar_`) is minted there once; the bundle exports
them; the importer inserts them as given (private keys remapped).

- `infra/promotion/compose.yml` (own project, named volume, `mem_limit`, small `shared_buffers`, port from
  `PORT_REGISTRY.md`) and `scripts/promotion/{dump,verify-dump}.sh`, owned by REPAIR. Disposable copies use
  `infra/local` with their own `.env` under `.local/`.
- Stopped between operator steps; a `pg_dump -Fc` after each step, restore-verified into a disposable
  instance that is removed afterwards; one latest dump under `.local/norms/promotion-dumps/`.

### 3.3 Repairs through a durable call journal (F-3, F-4, W-4)

- **Journal** `norm_repair_call` (`0018`): block, crop SHA-256, request SHA-256, model, attempt number,
  `idempotency_scope` = the call's own `nrc` id; the response checkpointed before parsing; terminal
  `completed | not_processed | outcome_unknown`. **Write order:** append and fsync the intent to
  `.local/norms/repairs/journal.jsonl` (outside the Docker volume), then commit the database row, then
  dispatch; an effect commits to the database first, then is appended. On start, an intent in the file but
  not in the database becomes `outcome_unknown` at maximum cost; an intent in the database but not in the
  file refuses the start. A lost volume is restored from the latest dump and reconciled forward from the
  file. No off-host mirror (K-11).
- **Retries (`R-79`):** at most three provider tries per call, delays 2 s and 8 s, `Retry-After` ≤ 60 s, only
  when W53's `ProxyDispatchError.retry_safe` is true (no connection, 429). Every 503 is `outcome_unknown`
  (`D-153`). 400/401/413 end the attempt; `outcome_unknown` is never re-paid. REPAIR exports
  `ProxyDispatchError` from `analysis/public.py`.
- **Price:** `usage.cost`; an unpriced response is refused. The $10 ceiling is cumulative across restarts;
  `outcome_unknown` counts at rate card × 8000 output tokens plus a pixel-derived input bound (≈ $0.20 on
  opus-5, ≈ $0.08 on sonnet-5). The model is named explicitly (`PROXY_LLM_MODEL`) and must be on the rate
  card; an answer naming another model is refused and its cost counted (H-6).
- **Sample first:** the three largest crops by area, live; the full run proceeds only if
  `mean sample cost × 121 × 1.25 ≤ $10`. Above that, the run **stops for the owner's decision** (K-8). The
  ceiling stays the hard stop of an approved run; pages it leaves are `NOT_ATTEMPTED`, hence unreliable.
- **Crop source:** the drop here, checked against the operator's `SHA256SUMS` (§4, operator step 0);
  `ADR-0020` L41-42 is amended (`R-104`).
- **Outcomes (F-4):** every block not ending `REPAIRED` is unreliable. The key becomes
  `<window>+<d>d+<n>r+<m>u.<12 hex>` (`+<m>u` whenever `m > 0`); REPAIR changes `repaired_snapshot()` and
  inverts `test_a_ledger_that_applied_nothing_returns_the_base_unchanged`; `0018` replaces
  `ck_norms_snapshot_raw_key` (`repair_count = 0 AND unreliable_count = 0 ⇔ base = content key`) and adds
  `unreliable_count`.

### 3.4 Snapshot, chunks and the embedder

- **`D-125`:** merged in W52; operator step 1 and this wave's full gate are its remaining evidence.
- **`D-126`:** any segmentation profile other than the literal `markdown-v1` adds `+seg-<profile>` after the
  digest; the current key and the bake-off pins stay byte-identical, and raising the constant yields a new key.
- **`D-127`:** complete only with every chunk's full window set; the digest uses the computed key
  `content_key ‖ source_document_ref ‖ chunking_profile ‖ ordinal`.
- **Unreliable paragraphs:** `norm_paragraph.text_reliability` (`NOT NULL DEFAULT 'reliable'`); a new chunking
  profile skips them ("every reliable paragraph covered, exactly the unreliable set skipped"); a
  `characters-v1` build over a snapshot with `unreliable_count > 0` is refused.
- **`D-124`:** `SET LOCAL hnsw.iterative_scan = strict_order`, `hnsw.ef_search`, `hnsw.max_scan_tuples`,
  proven on two snapshots with synthetic vectors (revert red); real-vector recall and p95 in W55.
- **Embedder** `norms/embedding/**`: the 512/64 windowing ported byte for byte from
  `tools/norms/embedding_bakeoff.py`; two entry points inside the BGE image —
  `python -m auditmanager.norms.embedding build --snapshot <ns_id> --chunking-profile <p> --checkpoint <dir>`
  (per-batch checkpoint files with SHA-256 under `.local/norms/builds/<content_key>/`; a restart skips verified
  batches, so the ≈ 14 h build spans night windows; when all exist, a streaming `ensure_build` loads them in
  one transaction with the completion row) and `embed-texts --in <json> --out <json>` (W57's batch entry
  point: float32 base64 vectors with profile id, model revision and SHA-256). `tokenizers`/`transformers`
  stay out of the root lock and are never imported at module level.
- **BGE image** `infra/norms-worker/`: model pinned by revision and file SHA-256; its own hashed lock (`torch`
  CPU); pinned threads; `HF_HUB_OFFLINE=1`; no network at run time. BGE-IMAGE proves pins and MRR; EMBED
  removes that image, rebuilds it with the embedder inside, repeats the MRR, checks the windowing against the
  real tokenizer and records the digest. **G-1:** the complete build runs here and ships in the bundle; if a
  floor fails, it is a W55a carryover; an incomplete build is never a production corpus.

### 3.5 The bundle, the importer and the stand-side tools (F-2, CD-3, CD-16, K-1, K-6)

- **Manifest** (frozen at the freeze): version; `content_key`; `min_migration_head`; snapshot, row and build
  digests; counts; object bytes; `db_growth_bytes` measured on the promotion database; the drop sums'
  digest; each document's `results.md` SHA-256; the ledger's applied and unreliable entries; a canonical
  row digest over ids, text and `text_reliability`; every file's SHA-256, size, kind and anchor.
- **Bundle** `python -m auditmanager.norms.bundle export` writes `<content_key>+<bundle digest>/`; PDFs and
  crops are **hardlinked** from the drop (same filesystem, made read-only) and every object is re-hashed at
  export and at push, so the bundle adds ≈ 0.6 GB of rows and vectors instead of ≈ 5 GB.
- **Importer** `python -m auditmanager.norms.bundle import <dir> --copy-record <path>`, one-shot, never in a
  serving process: (1) verify the manifest, the copy record and free space; refuse a `rejected` manifest
  Blob; (2) admit and dispatch until every admission is `confirmed`, exiting non-zero and keeping the
  bundle otherwise; (3) one transaction: assert all confirmed, insert the rows with their ids,
  `publish_bindings('norm_source', snapshot)`; exact replay is a no-op, the same key with other ids or the
  same id with another key is refused; (4) the build, by the computed chunk key; a bundle without a complete
  build is refused; (5) after `report` matches, delete the objects, keep manifest and report.
- **`report`** (read-only) prints and compares with the manifest: documents, paragraphs, chunks, windows; the
  unreliable-paragraph count; admissions confirmed, pending, poisoned; the binding count and binding digest
  (SHA-256 over sorted role, target, `blob_id`, anchor); content key, recomputed row digest and build digest.
  It also prints the client-table row counts and the Blob totals (count, bytes, `rejected` count; manifest
  Blobs and all others) and compares the client side with the open copy record. Exit 0 only on a full match.
- **Copy record** (JSON, `record_version 1`, on the stand): `stamp`, instance, deployed tree, migration head,
  `quiesced_at`, the writers present and stopped, the dump's size and SHA-256, the fingerprint, the
  inventory's count, bytes and SHA-256, the `rejected` Blob count, and `attestation {dump_sha256,
  restore_report_sha256, attested_at}`. **Fingerprint:** row counts and their SHA-256 for every base table
  outside the `norm*` and custody families; in `audit_event` and `command_record` it counts only rows whose
  event or command type is outside `norm_custody.*`; in `blob` only rows no custody admission names. The
  importer refuses unless the record is attested and open, the writers stayed stopped, at most 12 h have
  passed, and on the first run the fingerprint is unchanged. **Purpose:** `attest … publish <sha>` makes a
  publication record bound to that target SHA (re-attesting rebinds it, e.g. for a forward fix); a record
  becomes an import record when attested `import`, or when a bundle is received or an import starts while
  it is open. Only the latest copy is kept; it holds client data and never enters Git, a report or a chat.
- **Inbound key** (owner-installed, `restrict,from="<this host>"`, forced command `receive-bundle.sh`):
  `receive <KEY> <size>`, `status`, `import <KEY>` (detached, locked, re-entrant), `report <KEY>`,
  `requeue <KEY>` (custody `requeue` of that bundle's poisoned admissions). `<KEY>` is the bundle name; the
  grammar, staging and refusal rules are frozen in TRANSPORT's task file.
- **Copy key** (a second owner-installed key; forced command `copy-serve.sh`): `capacity`; `dump-db`;
  `inventory-s3 <STAMP>`; `fetch <STAMP> (db|inventory|record)`; `attest <STAMP> <dump-sha256>
  <restore-report-sha256> (publish <sha>|import)`; `verify-objects <N>` (a seeded sample of `available` Blobs read back against
  their size and SHA-256); `restore-db <STAMP> <sha256>` (stops the writers itself, restores, leaves them
  stopped); `resume <STAMP>` (refused under an import lock; closes the record); `status` (open record and its
  age). `capacity` prints, per filesystem, free disk of the Docker data root, the MinIO volume and staging,
  plus available RAM, swap, load, `pg_database_size`, the MinIO volume size, `docker system df` and the
  bucket's count and bytes. `dump-db` stops only the writers present (`web`, `api`, `worker` if deployed) and
  records which.
- **One dispatcher, extensible.** `infra/deploy/lib/forced-command.sh` parses a verb table; each key's script
  registers its verbs. A later lane adds a verb by one table entry and one refusal case in the key's test
  (`test_bundle_transport_refusals.py` or `test_stand_copy_refusals.py`; a guard without a case is red). W57a
  adds `retrieval-set-build` (and its report verb) to the inbound key.
- **Here:** `push-bundle.sh`; `pull-copy.sh`; `scripts/stand-copy/restore-test.sh` (restore into a disposable
  local PostgreSQL, compare the fingerprint, parse the inventory, write the report `attest` binds).
- **Risk:** both keys' account runs `docker` (root-equivalent); the forced command is the boundary.
  **`ADR-0020` addendum (`R-104`):** a verified bundle and the one-off dump may sit transiently on the stand,
  read only by the importer or `restore-db`; re-recognition may read the drop here, digest-verified.

### 3.6 Worker service (F-8)

- `python -m auditmanager.workers serve` on the API image; compose service `worker` after `migrate`, no
  `ports:`, not on the session volume; the API's environment except `AUDITMANAGER_API_TOKEN`; `provider.env`.
- `EXECUTION_ROLE ∈ {all, api, worker}`, set literally per service in `compose.server.yml` (never in the
  `.env`'s 15 frozen names); `deploy.sh` refuses a compose file where either lacks it. `all` keeps W53's
  in-process behaviour for tests; on the stand only the worker claims, both reclaim; `LISTEN/NOTIFY` on a
  dedicated connection, a logged warning when lost, a 5 s poll as the stated fallback.
- Registry `worker` (`0019`): `wrk` id on tmpfs, version, started, heartbeat every 20 s, `slots`,
  `intake_enabled`; stale after 90 s, offline after 600 s. `lease.worker_id` joins `trg_lease_frozen_guard`.
- **D-141:** the text stage's lease-row lock shrinks to the final writes (`runs/executor.py:905`,
  `jobs/repository.py:540-564`); the heartbeat extends the lease while the evidence gate runs.
- **D-150** (the freeze decides; proposed): a `recorded` effect spends nothing, so reclaim settles a prepared
  one as `not_processed` and a completed one does not block resume; the pinning QA test is inverted.
- **D-152:** the order-sensitive composition test parks every foreign queued Job before unpausing.
- «Очередь» and the run page show «нет активных исполнителей» when no worker is online. `ADR-0002`
  addendum (`R-105`).

### 3.7 Operations and «Исполнители»

`listWorkers` `GET /execution/workers` (`role:admin|expert`, `R-80`): state, intake, slots, version, current
runs. `setWorkerIntake` `PUT /execution/workers/{worker_id}/intake` (`admin`), body `{enabled}`. `/workers`
keeps `any-role` and graduates from the stub: online and stale first, offline collapsed; «Не брать новые /
Разрешить» for administrators; refresh on focus, after an action and by «Обновить».

### 3.8 AR-1 probes (report only)

- **OCR probe** (`scripts/probes/w54/ocr/**`): parse `_blocks.json` and `_results.md`, cut crops with
  `pypdfium2` at 100 and 150 dpi, run the degeneracy detector, propose W55b's design. No network.
- **Vision probe** (`scripts/probes/w54/vision/**`): image parts on 5–10 image-block crops (no stamps); spend
  fsynced to `.local/probes/w54/spend.jsonl` before each call; **≤ $3**; a mismatched model refused.

### 3.9 Disk and memory (CD-12, CD-21)

A **heavy step** is an image build, a full gate, a lane's private stack run, a full-corpus load, a dump with
its restore-verify, the repair run, a build window, a bundle export, a rehearsal or a copy restore test.
Heavy steps run one at a time, in night windows.

**This host** (one filesystem, `/`): `peak = resident W54 artefacts + the running step's increment + 3 GiB`.

| Item | Resident (GB) | Increment (GB) |
| --- | --- | --- |
| a lane's private stack / a full gate | — | 2 / 2 |
| BGE image (pruned after the build; W57a rebuilds it from its pins) | 3.5 | 6.5 to build |
| rehearsal (subset promotion DB, disposable stand, staged bundle) | — | 3 |
| promotion database (two snapshots, both profiles, one build) | 3 | 3 to load |
| latest dump; restore-verify instance | 1 | 3 |
| build checkpoints | 0.5 | 0.5 |
| bundle (objects hardlinked) | 0.6 | 0.6 |

Largest planned peak: the build with the database loaded, 3.5 + 3 + 1 + 0.5 + 3 = 11 GB against today's 14
GiB. **Stop rule:** a heavy step starts only if `df -B1` shows its increment + 3 GiB free and `free` shows
≥ 6 GiB available (swap does not count), both measured at that step, since available RAM moves between
2.6 and 7.3 GiB; provisioning memory or disk is the owner's decision and a precondition of every heavy step. Two failed nights move the step under
`W54-INT-CARRYOVER-01`.

**The stand at P4:** on the staging filesystem `bundle + dump + 2 GiB`; on the Docker volumes' filesystem
`objects (≈ 4.75 GB) + db_growth_bytes + 2 GiB`. `capacity` measures both; `receive` and `import` refuse below
their part.

### 3.10 The road to the stand (CD-15, CD-16)

P1 is done: the MinIO swap rode W53's publication; its read-back is P2's `verify-objects`. **Every migrating
publication is preceded by a one-off copy** until the beta backup wave (K-6; W53 was exempt, K-12). **P2**
(W54 code and migrations), in CD-16's order:

1. The exact-SHA gate.
2. Inside an agreed window (K-5): `dump-db` → `inventory-s3` → `fetch` → test restore here → `attest`.
3. Push.
4. Workflow and `verify-deployed.sh`.
5. `resume`.

Then `verify-objects` (P1's read-back) and the D-144 probe (`Set-Cookie` over HTTPS and distinct client
addresses in the proxy log, read by the owner). On failure: a forward fix; or the owner-ordered
`restore-db <STAMP> <sha256>`, then a reviewed revert under `MAIN_AUTODEPLOY_POLICY.md` (complete gate,
fast-forward), then `resume` — a revert alone would fail migrations-at-head. **Bootstrap:** the copy key's script ships in P2, so the
owner installs the copy key and its forced command at `/srv/auditmanager/copy-serve/` with the candidate's
`copy-serve.sh` and `lib/` extracted from git objects, their SHA-256 checked against the gate record, and
`ALPHA_CHECKOUT` naming the deployed checkout; the integrator then runs every verb. `status` prints the
installed script's SHA-256; a later publication that changes it asks the owner to refresh it.

**Rollback per lane at P2:** migrations `0018`/`0019` refuse downgrade, so a code rollback is `restore-db`
then a reviewed revert, as above; WORKER can instead fall back by a forward fix to `EXECUTION_ROLE=all` on
`api` without the `worker` service; TRANSPORT and STAND-COPY by the owner removing the keys; REPAIR,
SNAPSHOT, EMBED and BUNDLE have no stand effect before P4.

P3 (W55a) follows the same order; **P4** is CD-16's: `capacity`; `receive` and `status`; `dump-db` →
`inventory-s3` → `fetch` → test restore → `attest`; `import`; `report`; `resume`; designation;
`verify-objects` and live checks. Failure: `resume`, or `restore-db` then `resume`; a hung importer holding
its lock is an owner act, rehearsed.

## 4. Tasks

Unprefixed source paths are under `src/auditmanager/`. Levels (`R-70`, CD-10): **full gate** for SEAL,
BGE-IMAGE, TRANSPORT, CUSTODY, REPAIR, SNAPSHOT (it holds `tests/integration/norms/conftest.py`), EMBED,
WORKER, WORKERS-WEB, STAND-COPY, RELNOTES and before `main`; **light acceptance** for BUNDLE and the probes.

### `W54-RULE-01` (integrator)

Records after the owner confirms: `R-103` the W54 shape (F-1) and AR-1 inputs (F-5, F-6, F-9; "OCR is always
marked" in W55); `R-104` transport and the road — F-2, CD-16's sequences, K-5, K-6 and its P2 bootstrap,
K-1's copy, both keys and their verbs, the importer's refusals, the `ADR-0020` addendum and the two-phase
custody sequence; `R-105` the worker service and the `ADR-0002` addendum; `R-106` repairs (F-3, F-4, W-4):
journal and write order, `R-79` tries, the sample stop (K-8), the cumulative $10, the local journal (K-11);
`R-107` real-document scope (F-7).

### `W54-FREEZE-01` (integrator)

Standard form, plus: base `4fe7615` or a fast-forward successor, adopted by an entry commit; §2's facts with
pins; the R-76 seam re-check of `storage/**` and `ingest/**`; the D-150 decision; migrations
`0018_norm_custody` (custody, D-142, D-148) and `0019_execution_workers`, then CD-2's `0020`…`0024`;
`pin_sweep.py reseal-surface migration table route` with hand grants and `--check` on every task file; the
manifest, copy-record and fingerprint schemas, both keys' grammars, the windowing rule and the repaired-key
format in the task files; ports for twelve lanes; the proxy credential file sourced into the runner's
environment (outside the repository); fresh `df`/`free` against §3.9. **Overrun is a replan:** if Stage B is
not merged by working day 8 after the freeze (the P50 of the freeze, Stage A and Stage B), or the host misses
a floor for two nights, `W54-INT-CARRYOVER-01` records status, SHA, unmerged work and every unperformed
operator step, and grants VISION-PROBE, WORKERS-WEB, WORKER in that order to the conditional tasks of
`W55-PLAN.md` §C0. No agent inherits a grant by implication.

### Stage A — from the freeze SHA (executor)

**`W54-SEAL-01`** — `0018_norm_custody` (`norm_custody_admission`, `norm_custody_binding` with
`ck_norm_custody_role_shape`, `norm_repair_call`, their triggers, `norm_paragraph.text_reliability`,
`norms_snapshot.unreliable_count`, the replaced `ck_norms_snapshot_raw_key`, `abandoned` for
`analysis_artifact_publication`, both state guards on `INSERT OR UPDATE`) and `0019_execution_workers`
(`worker`, `lease.worker_id`); new identifiers `nad`, `nbd`, `nrc`, `wrk`; the two operations (stubs); role
registers; the four-document reseal; facts; the addenda; `NORM_CORPUS_CUSTODY.md`. Allowed:
- `contracts/**`; `web/openapi/openapi.json`, `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json`;
- `db/migrations/versions/<date>_0018_norm_custody.py`, `<date>_0019_execution_workers.py` (new only);
- `api/**` except `app.py`'s lifespan; `bootstrap/{adapters,composition}.py` (stub wiring);
  `shared/identity/{ids,__init__}.py`; `runs/scope.py` (`worker`, `outbox`); head constants only in
  `documents/refusals.py`, `storage/check.py`, `shared/db/{__init__,check,errors,migrations,schema}.py`,
  `shared/statemachine/topology.py`;
- `tests/contract/**`, `web/tests/contract/**`, `web/tests/guards/**`, `web/tests/unit/**` (surface, role
  and pin assertions); `tests/integration/{api,auth,db}/**`;
  `tests/integration/composition/{test_api_token_channel,test_composition_root,test_an_absent_parent_is_not_an_empty_page,test_router_answers,test_every_port_implementation_is_whole,test_reset_rehearsal_counts_base_tables,test_session_register_volume,test_proxy_config_follows_checkout,test_reset_script_refusals}.py`
  (counts and the two stubs: `EXPECTED_UNADDRESSED` 10 → 11, the stub marked in the page-shape and 503
  sweeps); `tests/integration/runs/{test_idempotency_and_topology,test_w53c_exec_closure}.py`;
  `tests/integration/foundation/test_cross_provider_publication.py`, `tests/integration/p02_journey/journey.py`,
  `tests/support/expected_facts.{json,py}`, `tests/e2e/pc01/test_acceptance.py`,
  `tests/e2e/pc01/journey/manifest.json`;
- `web/src/app/bff/v1/[...path]/route.ts`, `web/src/shared/api/{credentialed-forward,authorization}.ts`,
  `web/src/shared/config/{screen-registry,index}.ts`, `web/src/shared/lib/routes.ts`, `web/src/_app/navigation.ts`,
  `web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx`,
  `web/src/widgets/home-tiles/model/registrations-screen.ts` (pins only);
- `infra/deploy/{README.md,serve.py,compose.server.yml,deploy.sh,reset.sh}`, `infra/deploy/proxy/nginx.conf`
  (counts only); `docs/program/{CONTRACT_PIN_REGISTRY,P02_SEAMS,CURRENT_STATE,ALPHA_ROADMAP,NORM_CORPUS_CUSTODY,NORM_CORPUS_DECISION_BACKLOG}.md`;
  `docs/architecture/adr/{ADR-0020-normative-corpus-alpha-runtime,ADR-0002-modular-monolith-control-plane}.md`
  (addenda); `docs/manual-tests/{PC-01_prototype,README}.md`; `api/README.md`; `docs/program/W54-SEAL-01.md`;
- every further path `pin_sweep.py` prints.
Required: fresh upgrade, upgrade from `0017` with rows, refused downgrade with retained data, for both; an
insert in a non-initial effect state refused; `prepared → abandoned`; an unknown role or target kind refused.

**`W54-BGE-IMAGE`** — `infra/norms-worker/**`, `docs/program/FOUNDATION_LOCK.json` (`norms_worker` entry,
`images.immutability` sentence), `tests/integration/composition/test_norms_worker_image_contract.py` (new),
`docs/program/W54-BGE-IMAGE.md`. In the lane (drop mounted, ≈ 450 s, ≈ 3.2 GiB): with `--network none`, the
24 bake-off queries over 563 windows reproduce the recorded MRR exactly.

**`W54-TRANSPORT-01`** — `infra/deploy/{receive-bundle,push-bundle}.sh`, `infra/deploy/lib/forced-command.sh`
(new), `tests/integration/composition/test_bundle_transport_refusals.py` (new), `infra/deploy/README.md`
(file table, edited only after SEAL's merge), `docs/program/DEPLOYMENT_RUNBOOK.md` (transport),
`docs/program/W54-TRANSPORT-01.md`. Required, `docker` stubbed on `PATH`: a refusal per guard and grammar
violation of every inbound verb, the real repaired key accepted, size refused before reading, a mismatching
tar removed inside staging only, `import`/`report`/`requeue` invoking only the fixed module command;
`shellcheck`.

**`W54-OCR-PROBE`**, **`W54-VISION-PROBE`** — their `scripts/probes/w54/{ocr,vision}/**` and
`docs/program/reviews/W54-{OCR,VISION}-PROBE.md`.

### Stage B — sequential on this host; each lane starts from the previous lane's merge

1. **`W54-CUSTODY-01`** (§3.1; `W54-JUDGE-A1` before its merge) — `norms/custody/**` (new), `norms/public.py`
   (new), `storage/{s3,models,public,blob_repository}.py`, `storage/README.md`, `storage/errors.py`
   (docstring), `ingest/reconciliation.py`, `jobs/repository.py` (D-142 settlement only),
   `infra/deploy/object_attrs.py`, `infra/deploy/reset.sh` (role rationale) with
   `tests/integration/composition/test_reset_script_refusals.py`, `tests/integration/norms/custody/**`,
   `tests/integration/storage/**`, `tests/integration/ingest/{test_reconciliation*,test_blob_metadata}.py`,
   `tests/integration/runs/test_durable_effect_boundaries.py`,
   `tests/integration/qa_w53/test_queue_and_effect_journal.py` (settlement assertions),
   `docs/program/W54-CUSTODY-01.md`. Required: the five interruption points and eight cases; admission before
   the target, binding with it; an orphaned admission stays unbound; double admission a no-op; equal bytes
   under two roles; a media-type conflict; two concurrent declarers (D-146); D-142 settlement and event;
   D-143 report and refusal.
2. **`W54-REPAIR-01`** (§3.2, §3.3) — `norms/{__main__,rerecognition,repair}.py`, export lines of
   `norms/{public,__init__}.py`, `norms/repair_journal/**`, the `ProxyDispatchError` line of
   `analysis/public.py`, `infra/promotion/**`, `scripts/promotion/**`,
   `tests/integration/norms/{test_rerecognition,test_repair_projection,test_degeneracy}.py`,
   `tests/integration/norms/repair/**` (new), `tests/integration/db/test_norms_corpus_migration.py` (ledger and
   key cases), `docs/program/W54-REPAIR-01.md`. Required: a kill after acceptance and before the ledger write
   does not re-pay; the write order and both reconcile directions; `R-79`'s tries; 503 ambiguous; the
   cumulative ceiling; a lost volume reconciled; a model mismatch refused; the sample stop; the `+<m>u` key and
   the inverted test; zero live calls in the gate.
3. **`W54-SNAPSHOT-01`** — `norms/{corpus_source,model,loader,repository,snapshot,segmentation,chunking}.py`,
   export lines, `norms/README.md`, `tests/integration/norms/**` (including `conftest.py`) except `custody/**`,
   `repair/**`, `bundle/**`, `embedding/**` and REPAIR's three files,
   `tests/integration/db/test_norms_corpus_migration.py` (loader cases), `docs/program/NORM_CORPUS_PERSISTENCE.md`,
   `docs/program/W54-SNAPSHOT-01.md`. Required: D-126; the reliability-aware profile and its invariant; the
   `characters-v1` refusal; `import_snapshot(rows with ids)` with replay and conflict tests and the row digest.
4. **`W54-EMBED-01`** — `norms/embedding/**`, `norms/embedding_repository.py`, export lines, `norms/README.md`
   (its rows), `tests/integration/norms/embedding/**` (new),
   `tests/integration/db/test_norm_embeddings_migration.py` (repository cases), `infra/norms-worker/**`,
   `docs/program/FOUNDATION_LOCK.json` (`norms_worker` digest),
   `tests/integration/composition/test_norms_worker_image_contract.py`, `docs/program/W54-EMBED-01.md`.
   Required: D-124's red revert; D-127; windows equal the runner's on recorded offsets and, in the rebuilt
   image, on the real tokenizer; a build killed between batches resumes to the same digest; rows invisible
   until the completion row; memory bounded by the batch; MRR in the rebuilt image; `embed-texts` stable.
5. **`W54-WORKER-01`** (§3.6) — `workers/**`, `{jobs,execution}/**`, `runs/{carrier,public,reconciliation}.py`,
   `runs/executor.py` (D-141 only), `runs/scope.py` (remote-execution line), `api/app.py` (lifespan),
   `bootstrap/{settings,composition,adapters,public}.py`, `api/routers/execution.py` (bodies),
   `infra/deploy/{compose.server.yml,deploy.sh,verify-deployed.sh,reset.sh,README.md}` (worker lines),
   `infra/deploy/env/provider.env.example`, `docs/program/DEPLOYMENT_RUNBOOK.md` (worker operations),
   `scripts/light_acceptance.py` (`CONTEXT_SUITES` for `workers`, `execution`),
   `tests/contract/test_light_acceptance_command.py`, `tests/contract/architecture/test_alr05_boundaries.py`,
   `tests/integration/{workers,jobs,execution,runs}/**`, `tests/integration/qa_w53/test_queue_and_effect_journal.py`
   (D-150), `tests/integration/api/{test_query_surface,test_authorization}.py`,
   `tests/integration/composition/{test_session_register_volume,test_deploy_script_refusals,test_deployed_stack_probe,test_deploy_image_identity,test_the_run_leaves_the_request_thread,test_composition_root,test_an_absent_parent_is_not_an_empty_page,test_router_answers,test_every_port_implementation_is_whole,test_reset_script_refusals}.py`
   (stubs unmarked), `docs/program/W54-WORKER-01.md`. Required: only the worker claims; both reclaim; an API
   restart leaves the worker's run alone; a killed worker's lease reclaimed; lost `LISTEN` logged; drain; the
   token exemption; a compose file without the role refused; a final transaction longer than the lease is not
   reclaimed (D-141); recorded reclaim (D-150); D-152's test isolation; W53's drivers pass under `all`.
6. **`W54-WORKERS-WEB`** — `web/src/_pages/{workers,run,queue}/**`,
   `web/src/widgets/{worker-list,execution-queue,run-progress}/**`, `web/src/features/set-worker-intake/**`,
   `web/src/entities/execution/**`, `web/src/shared/api/query-keys.ts` (inside `execution`),
   `web/src/shared/lib/routes.ts`, `web/src/shared/config/screen-registry.ts` (the `/workers` row),
   `web/src/shared/ui/route-placeholder.tsx` (stub text), `web/tests/unit/screens/{routes.test,route-screens,run-progress.test,run-cache-shape.test}.ts`,
   `web/tests/unit/execution/**`, `web/tests/unit/workers/**` (new), `web/tests/unit/styles/screens.ts`,
   `web/tests/guards/{prepared-sections,dashboard-invalidation,rendered-language,lazy-boundary,screen-registry}.guard.test.ts`,
   `tests/e2e/pc01/journey/manifest.json`, `docs/program/W54-WORKERS-WEB.md`.

### Stage C — from the Stage-B merges (`W54-JUDGE-A2` before their merges)

**`W54-BUNDLE-01`** — `norms/bundle/**` (export, import, report, `copy_record.py`), export lines,
`norms/README.md`, `tests/integration/norms/bundle/**` (new), `docs/program/DEPLOYMENT_RUNBOOK.md` (import and
report), `docs/program/W54-BUNDLE-01.md`. Required: §3.5's order on a disposable stand; replay a no-op;
conflicts refused; an unconfirmed admission keeps the bundle; `report` matches, and a tampered row fails it;
**an import alone leaves the fingerprint unchanged**; refusals without a record, with a stale, unattested or
expired one, with a drifted fingerprint, an absent build or a `rejected` manifest Blob.

**`W54-STAND-COPY-01`** — `infra/deploy/{copy-serve,pull-copy,capacity-probe}.sh` (new),
`infra/deploy/receive-bundle.sh` (record pre-check, `requeue`), `infra/deploy/lib/forced-command.sh`,
`infra/deploy/deploy.sh` (one guard), `scripts/stand-copy/**` (new),
`tests/integration/composition/{test_stand_copy_refusals,test_bundle_transport_refusals,test_deploy_script_refusals}.py`,
`infra/deploy/README.md` (file table), `docs/program/DEPLOYMENT_RUNBOOK.md` (one-off copy, P2 bootstrap,
read-back), `docs/program/W54-STAND-COPY-01.md`. Required: a refusal per guard and verb; `dump-db` stops
exactly the writers present; `resume` refused under an import lock; `restore-db` re-quiesces and checks the
digest; `attest` binds both digests; a dump restored here reproduces the fingerprint; `verify-objects`
detects a corrupted object; every `capacity` field; the extracted script acts on `ALPHA_CHECKOUT`;
`deploy.sh` refuses with a typed message before any `docker` call while the importer lock is held, while
an open record is an import record, while an open record is unattested, or when an open publication record
binds another SHA (`stand_import_locked`, `stand_import_open`, `stand_copy_unattested`,
`stand_copy_other_target`), and accepts exactly the bound SHA; each is a marked guard with its case in
`test_deploy_script_refusals.py` (the every-guard-has-a-case check, `:1079`), so no `main` push deploys
during P4; `shellcheck`.

**`W54-RELNOTES-01`** — base ≥ `ed66983` (0.4.0 notes, `R-86`'s history rows): `release-notes/0.5.0.json`,
`release-notes/dictionary.json` (additions), `VERSION`, the paths `git grep -n '0\.4\.0' tests web/tests`
prints, `docs/program/W54-RELNOTES-01.md`.

### Stage D — rehearsal, judging, FIX

- **`W54-REHEARSAL-01`** (`scripts/rehearsal/w54/**`, `docs/program/W54-REHEARSAL-01.md`): *P2 bootstrap* on
  a disposable stand built from the exact deployed tree (`2653dbf`), with the extracted script; *P4* on a
  disposable stand at the W54 candidate with a subset bundle, every verb in CD-16's order, plus no record, a
  write after quiesce, window expiry, an interrupted import resumed, `requeue`, `restore-db` followed by
  re-import, `report`'s client side equal to the record, a hung importer, `deploy.sh` accepted under an attested
  publication record for its SHA and refused under an import record; the window measured and extrapolated
  to 28.9k objects (K-5); *worker* — kill mid-run, a second worker, drain, no worker online.
- `W54-QA-01`; `W54-JUDGE-A1` (custody); `W54-JUDGE-A2` (bundle, copy record, stand tools); `W54-JUDGE-X`
  (both keys attacked, quiesce, credentials in logs, worker faults); `W54-JUDGE-Y` (lineage from the drop sums
  to `report`; identities; ALR-05; locks); `W54-NOTES-JUDGE`; `W54-FIX`.

### `W54-INT-CLOSE` (integrator)

Full gate on the final SHA; register: close D-124, D-126, D-127, D-141, D-142, D-146, D-148, D-150, D-152;
D-125 and D-143 close on the evidence of operator step 1 and P2's copy record; debts: least-privilege
roles, the portal API, OCR quality on real documents, D-124's real-vector measurement (W55).

### `W54-INT-MAIN-01` (integrator; P2, on the owner's instruction naming the SHA)

Before the operator steps, so their artefacts do not crowd the gate: §3.10's P2 sequence on the INT-CLOSE
SHA; D-137–D-140 dispositions; the worker runs, the API does not claim, «Исполнители» shows it online, a
run completes; `verify-objects`; the D-144 probe. A tag only under §8.4.

### `W54-CORPUS-OPERATE-01` (integrator, after INT-MAIN-01 or on the owner's choice before it)

In night windows, each step under §3.9's stop rule: (0) `SHA256SUMS` over the drop under
`.local/norms/corpus-sums/<date>/`; (1) load the base snapshot; dump and restore-verify; (2) the priced
sample, then — unless K-8 stops it — the 121 pages; export journal and ledger to
`.local/norms/repairs/<date>/`; dump; (3) load the repaired snapshot; the resumable `build`; dump; prune the
image; (4) export and verify the bundle into `.local/norms/bundles/`; stop the promotion database.

## 5. Integration order

1. `W54-RULE-01`, `W54-FREEZE-01`.
2. Stage A: SEAL ∥ BGE-IMAGE ∥ TRANSPORT ∥ OCR-PROBE ∥ VISION-PROBE; merge SEAL, BGE-IMAGE, then TRANSPORT
   rebased.
3. Stage B: CUSTODY → REPAIR → SNAPSHOT → EMBED → WORKER → WORKERS-WEB.
4. Stage C: BUNDLE → STAND-COPY; RELNOTES.
5. Stage D: REHEARSAL; QA ∥ X ∥ Y ∥ NOTES-JUDGE; FIX.
6. `W54-INT-CLOSE`; `W54-INT-MAIN-01` on instruction; `W54-CORPUS-OPERATE-01`.

## 6. Shared paths (one writer at a time, in this order)

| Path | Writers |
| --- | --- |
| `runs/scope.py` | SEAL → WORKER |
| `bootstrap/{adapters,composition}.py` | SEAL (stubs) → WORKER |
| `compose.server.yml` | SEAL (counts) → WORKER |
| `deploy.sh`, `test_deploy_script_refusals.py` | SEAL (counts) → WORKER → STAND-COPY (copy/import guard) |
| `reset.sh`, `test_reset_script_refusals.py` | SEAL (counts) → CUSTODY → WORKER |
| the three composition sweeps of B1 | SEAL → WORKER |
| `infra/deploy/README.md` | SEAL → TRANSPORT (after SEAL's merge) → WORKER → STAND-COPY |
| `docs/program/DEPLOYMENT_RUNBOOK.md` | TRANSPORT → WORKER → BUNDLE → STAND-COPY |
| `receive-bundle.sh`, `lib/forced-command.sh`, `test_bundle_transport_refusals.py` | TRANSPORT → STAND-COPY |
| `infra/norms-worker/**`, `FOUNDATION_LOCK.json`, the image test | BGE-IMAGE → EMBED |
| `jobs/repository.py`, `qa_w53/test_queue_and_effect_journal.py` | CUSTODY → WORKER |
| `norms/{public,__init__}.py` export lines | CUSTODY → REPAIR → SNAPSHOT → EMBED → BUNDLE |
| `norms/README.md` | SNAPSHOT → EMBED → BUNDLE |
| `tests/integration/db/test_norms_corpus_migration.py` | REPAIR → SNAPSHOT |
| `CURRENT_STATE.md` | SEAL (sweep edit) → integrator |
| `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand, `.local/norms/**`, the promotion database | integrator |

## 7. Stop conditions

`W48-PLAN.md` §14, plus: the sample projects above $10 (K-8); the proxy refuses image parts or is unreachable
from this host (stops the vision probe and the repair run); a drop file differs from its sums; the model
cannot be pinned by file digests; the MRR differs in either image; a bundle cannot be imported
all-or-nothing with its ids; `report` disagrees with the manifest or the record in rehearsal; a lane would
write to the stand or read the drop in a serving path; a heavy step below §3.9's floors.

## 8. Non-goals

The stand import (W55a, P4); recall and latency on real vectors, search, «Нормы» (W55a); the full backup
system (`R-77`); a Blob state-machine edge for D-143; AR-1 itself (W55b); least-privilege roles; the portal
API; remote workers.

## 9. Estimate

Critical path in active hours: freeze 2.0; Stage A (SEAL) 4.0 + merges 1.5; Stage B CUSTODY 5.5, REPAIR 4.0,
SNAPSHOT 3.5, EMBED 4.0, WORKER 5.0, WORKERS-WEB 2.5, merges 3.0; Stage C BUNDLE 4.5, STAND-COPY 4.5;
Stage D rehearsal 4.0, judging 2.0, FIX 3.0, gate 0.5; INT-CLOSE 1.0 — **≈ 54 h**; at the measured overhead
(1.5–2.0) **P50 ≈ 10 working days, P80 ≈ 13**. Not counted: the repair calls (≈ 1 h), the ≈ 14 h build over
night windows, P2's window and the owner's instructions.
