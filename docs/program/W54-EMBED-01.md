# W54-EMBED-01 — hand-back report

- Task: `docs/program/tasks/W54-EMBED-01.md`. Grant: `dispatch/W54-PLAN.md` §4 Stage B item 4,
  plus this file.
- Branch `agent/w54-embed-01`, worktree `.local/worktrees/w54-embed`. Base `81bc86d`
  (`integration/w54`: SEAL, BGE-IMAGE (definition only), CUSTODY, REPAIR, SNAPSHOT and WORKER
  merged). Implementation commit `2e00bcf`; this report is the next commit.
- Checks follow `R-102` (light acceptance). **No container was started, no model or wheel was
  downloaded, the corpus was not read, and no database ran.** Every heavy step is listed in §5
  for the owner's window.

## 1. Changed files

`git diff --name-only 81bc86d..HEAD` lists 35 paths (§6).

- **The embedder, `src/auditmanager/norms/embedding/` (new).** It imports only the standard
  library and `auditmanager.norms` at module level. A subprocess test proves that importing it
  loads no `torch`, `transformers`, `tokenizers`, `numpy`, `sqlalchemy` or `psycopg`.
  - `profile.py`: the frozen `bge-m3-dense-v1` constants.
  - `model.py`: the values passed between phases. They are keyed by the computed key
    `(source_document_ref, ordinal)`, never by `norm_chunk_pk`.
  - `vectors.py`: one representation for every vector: 1024 big-endian float32 values of unit
    norm, base64-encoded in files, with SHA-256 over the bytes.
  - `windowing.py`:
    - `window_spans`, the runner's `_windows` ported byte for byte, returning character spans
      and inference token counts;
    - `paragraph_span`;
    - `verify_window_set`, the `D-127` full-window-set rule.
  - `digest.py`: `norm-embedding-set/2`, an incremental digest that refuses windows out of
    canonical order.
  - `checkpoint.py`: the build directory:
    - the plan, the per-batch input files and the per-batch checkpoints;
    - writes are fsynced and renamed, and each checkpoint's SHA-256 sidecar is written last;
    - full verification on read, with the batch status.
  - `builder.py`: the encode phase. It skips verified batches, holds one batch at a time and
    takes `--max-batches`.
  - `encoder.py`: the real BGE-M3 encoder.
    - The model runtime is imported only inside `load`.
    - The encoder refuses unless `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`.
    - It refuses when the runtime is absent.
  - `operations.py`: the two database phases, `prepare` and `load`. It imports SQLAlchemy and
    is reached only by those commands.
  - `texts.py`: `embed-texts`.
  - `selftest.py`: the image build-time self-test.
  - `__main__.py`: `prepare | build | load | status | embed-texts | self-test`.
- **`src/auditmanager/norms/embedding_repository.py` (rewritten).**
  - `ensure_build` takes a stream of `ChunkEmbedding` and checks it under `D-127`.
  - `build_subject`, `iter_chunk_inputs` and `stored_build_digest` are new.
  - `nearest` gains the `D-124` scan settings, the completion-row requirement and the
    short-scan refusal.
- **Export lines:** `src/auditmanager/norms/public.py` (lines marked `# W54-EMBED-01`).
  `norms/__init__.py` is unchanged, so the in-image import graph of `auditmanager.norms` stays
  exactly what it was.
- **Documents:** `src/auditmanager/norms/README.md`. Two module rows, the corrected
  embedding sentence, and a section on the embedding build with its commands.
- **Image, `infra/norms-worker/`:**
  - `Dockerfile` bakes in `src/auditmanager/{__init__.py,norms/}` after the model layers.
    `PYTHONPATH` names the baked package. A second `RUN --network=none` runs the embedder
    self-test. The build context is now the repository root.
  - `Dockerfile.dockerignore` (new) is the root context's allowlist. Only the lock, the
    self-check and the norms package can reach the daemon. No `.local/` byte can.
  - `run-build.sh` (new) is the encode window: one `docker run --rm --pull never --network none
    --memory 5g`, whose only mount is the checkpoint directory.
  - `check-windows.sh` and `check_windows.py` (new) are the real-tokenizer window check, with
    the checkout and the corpus mounted read-only.
  - `tokenizer_recording.py` (new) records and replays tokenizer answers, and generates the
    synthetic text set.
- **Lock:** `docs/program/FOUNDATION_LOCK.json`, changes to `images.norms_worker` only:
  - `build_context` is `.`;
  - new keys `dockerignore`, `context_rule` and `embedder`;
  - `status` and `owner` are reworded.
  - `image_id` and every pending pin are unchanged.
- **Tests:**
  - new, container-free, under `tests/integration/norms/embedding/` (82 cases):
    `test_windowing.py` (27), `test_build_resume.py` (11), `test_digest.py` (12),
    `test_embed_texts.py` (14), `test_repository_offline.py` (12), `test_memory_bound.py` (3)
    and `test_cli.py` (3);
  - support files in the same directory: `support.py` and
    `recordings/synthetic-fake-tokenizer.v1.json`;
  - `tests/integration/composition/test_norms_worker_image_contract.py`: 45 → 66 cases;
  - `tests/integration/db/test_norm_embeddings_migration.py`: 4 → 9 repository cases,
    database-backed.

### What was built, case by case

| Required | Behaviour | Proved by |
| --- | --- | --- |
| **`D-124`'s red revert** | `nearest` sets `hnsw.iterative_scan = strict_order`, `hnsw.ef_search = 200` and `hnsw.max_scan_tuples = 100000` with `SET LOCAL`, before its query. It refuses a build with no completion row, and refuses a scan that returns fewer rows than `min(limit, window_count)` (`NormEmbeddingScanShort`). | Offline: the exact statement order (`test_nearest_scopes_the_d124_scan_settings…`), the short-scan refusal, the missing-build refusal. DB: `test_d124_a_second_snapshot_no_longer_shrinks_nearest` — 150 near and 30 far synthetic windows in one HNSW index, the plan asserted to use `ix_norm_embedding_hnsw_ip`. The pre-fix query returns **0** rows for the far snapshot (the defect, reproduced on purpose); the repository returns 10 rows, all from it; with `SCAN_SETTINGS` reverted to `()` it raises. |
| **`D-127` completeness** | A build is accepted only with every chunk's full window set, checked against the **stored** chunk text and paragraph layout before any insert: <br>• ordinals run `0..n-1`; <br>• token counts are `1..512`; <br>• the first window starts at character 0 and the last ends at the chunk's end; <br>• consecutive windows overlap and advance; <br>• every input digest is SHA-256 of exactly its slice; <br>• every paragraph span is the one its slice touches; <br>• every chunk of the profile appears once, in order. | `test_anything_but_the_full_window_set_is_refused` (12 mutants, including one one-character window, a gap, and windows that touch without overlapping). Offline repository: one-character windows per chunk refused with nothing inserted; missing, repeated, unknown and out-of-order chunks refused. DB: zero vector, one-character window and missing chunk each leave both tables empty. |
| **`D-127` digest** | `norm-embedding-set/2`: SHA-256 over a version line and one compact JSON line per window: `[content_key, source_document_ref, chunking_profile, chunk ordinal, embedding_profile, window fields…, input_sha256, embedding_sha256]`. <br>• Windows come in code-point order (`COLLATE "C"`). <br>• No private key enters it. <br>• After inserting, the database recomputes the digest from the stored rows, and it must match. | `test_the_digest_is_the_documented_canonical_serialisation` (written out by hand); every field and every key part moves it; out-of-order windows are refused; no `*_pk` or `*_id` input exists. DB: `test_the_digest_is_the_same_in_a_database_whose_private_keys_differ` (the `norm_chunk_pk` sequence advanced to 7000 in the second clone). |
| **Windows equal the runner's on recorded offsets** | The port keeps the runner's control flow, every tokenizer call and every refusal. | Equality with `tools/norms/embedding_bakeoff.py`'s `_windows`, without a model runtime: <br>• on a synthetic fast tokenizer at 512/64 and at three small limits that force every branch, including the shrink loop (a `ё` quirk makes re-encoding exceed the offset count); <br>• on a **replayed recording**: the replay refuses any unrecorded question, and the port's question log must equal the runner's; <br>• the committed synthetic recording is shown reproducible; <br>• equal refusals, with equal messages. <br>The real-tokenizer recording is a window step (§5.3); until it is committed, its case is skipped with that instruction. |
| **…and on the real tokenizer in the rebuilt image** | `check-windows.sh` compares the port and the runner with the `BAAI/bge-m3` tokenizer, over the synthetic set and every paragraph and chunk of the drop. It records the synthetic set. | Window step §5.3. |
| **A build killed between batches resumes to the same digest** | Fixed batches; checkpoint fsynced, renamed, then its sidecar; verified on read; invalid or missing batches recomputed and reported. | `test_a_build_killed_inside_a_batch_resumes_to_the_same_digest`: a forked build is `SIGKILL`ed inside batch 3. On resume, 2 batches are verified and 3 recomputed, and the digest equals the uninterrupted run's. Also covered: a kill between rename and sidecar costs that batch only; a corrupted byte is reported and recomputed; a checkpoint copied from another batch is rejected; `--max-batches` spans three "windows" to the same digest; an edited input file stops the build; another prepare is refused, and an equal one is a no-op that touches no checkpoint. |
| **Rows invisible until the completion row** | Window rows and the completion row go in the caller's one transaction. The completion row is written last, and `fk_norm_embedding_build` is deferred. The repository never commits. | Offline: the completion row comes after every window insert; zero commits. DB: during the load another connection sees 0 windows and 0 builds, and `nearest` from it refuses; after commit it sees all of them; a load that dies mid-stream leaves nothing. |
| **Memory bounded by the batch** | Every phase holds one batch: `prepare` streams one cursor; `build` reads and encodes one batch; `load` reads one checkpoint at a time; the repository works in groups of 128 chunks. | The encoder receives exactly one batch per call, and inputs are read one batch ahead of nothing. The loader's iterator reads checkpoint *k* only when chunk *k·B* is wanted. The repository pulls at most one group ahead of what it has written. The traced peak of a 4× longer build is 0.95× the shorter one's, against 1.59× for a mutant that keeps every batch; the bound is 1.25×. |
| **MRR in the rebuilt image** | `reproduce-mrr.sh` unchanged. | Window step §5.4. |
| **`embed-texts` stable** | `auditmanager-embed-texts/1`, a fixed key set, base64 big-endian float32, the profile, the model revision, per-vector SHA-256. The output is rendered canonically and written atomically, and an existing response is never overwritten. | Exact format; byte-equal responses to equal requests, pinned by SHA-256 (backed by explicit field assertions, so the pin is not the only check); 9 refusals, including a text over 512 tokens, which is never truncated; the command refuses outside the image without importing a runtime. |
| **SNAPSHOT's notes** | Embeds any parseable profile, `characters-v2` in the procedure. Window paragraph spans come from `paragraph_ordinal_first/last` and the stored paragraph lengths, not a running count. `+seg-` keys are carried verbatim in the digest; the support content key carries one. `build_subject` refuses a missing chunk build and names `build_chunks_from_stored`. | `test_chunk_inputs_stream_in_code_point_order_with_their_paragraph_layout` (DB); the support fixtures. |

## 2. Checks run, with commands and results

All of these ran on the committed tree `2e00bcf`, with `git status --porcelain -uall` empty.

| Command | Result |
| --- | --- |
| `git diff --check 81bc86d..HEAD` | clean |
| `.venv/bin/python -m compileall -q src/auditmanager/norms tests/integration/norms tests/integration/db/test_norm_embeddings_migration.py tests/integration/composition/test_norms_worker_image_contract.py infra/norms-worker` | exit 0 |
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms -k "not postgres" --ignore=tests/integration/norms/custody/test_two_phase_custody.py --deselect tests/integration/norms/test_embedding_bakeoff_fixture.py::test_every_relevance_anchor_resolves_to_the_exact_real_corpus` | **342 passed, 1 skipped**, 39 deselected. The skip is the real-tokenizer recording, §5.3. The 82 new cases are included. |
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/composition/test_norms_worker_image_contract.py tests/integration/composition/test_minio_image_contract.py tests/integration/composition/test_pgvector_image_contract.py tests/integration/norms/test_embedding_bakeoff_results.py tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py tests/contract/program/test_wave_governance.py tests/contract/tools/test_pin_sweep.py` | **174 passed** |
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py` | **558 passed**, 50 subtests. Includes ALR-05. |
| `pytest --collect-only tests/integration/db/test_norm_embeddings_migration.py` (no database) | 9 collected |
| `shellcheck infra/norms-worker/*.sh` | clean |
| `ruff 0.17.0 check` over every changed Python file (scratch virtualenv in the session scratchpad) | All checks passed |
| SQL, container-free: every `text()` statement and the three `SET LOCAL` statements of `embedding_repository.py`, parsed with `pglast` (libpg_query) in the scratch virtualenv | 13 parse. Syntax only, not column names. |
| Mutation check: 16 mutations applied in place to the source, `tests/integration/norms/embedding` run, each file restored | **16 of 16 red**. One survivor in the first pass (the overlap rule masked by a digest check) was closed by an internally consistent gap mutant. |

The mutations were:

- the overlap step;
- no last-window end check;
- no input-digest check;
- no overlap check;
- a digest without the content key;
- a digest without the order check;
- no sidecar requirement;
- no header check;
- verified batches recomputed;
- the completion row inserted first;
- no scan settings;
- no short-scan guard;
- no window-set check in the repository;
- no chunk-count check;
- `embed-texts` truncating silently;
- `prepare` overwriting a different plan.

**Not run (heavy, window only):**

- the 9 DB cases;
- the image build and its two self-checks;
- the real-tokenizer window check;
- the MRR reproduction;
- any embedding build.

The commands are in §5.

## 3. Contracts

- **No `contracts/**`, migration, error code or API change.** `0013` (one HNSW index,
  deferred build FK) and `0018` were sufficient: `D-124` is fixed in the query session, not in
  the schema.
- **Repository API (intra-context, exported through `norms.public`):**
  - `ensure_build(snapshot_id, chunking_profile, chunks: Iterable[ChunkEmbedding])` replaces
    `windows: Sequence[EmbeddingWindow]`, which was keyed by `chunk_pk`. `EmbeddingWindow` is
    gone; its only caller was the DB test.
  - New: `build_subject`, `iter_chunk_inputs`, `stored_build_digest`, `NormEmbeddingScanShort`.
  - The chunking profile must parse as `characters-v1:<n>` or `characters-v2:<n>`.
- **`embedding_set_sha256` format `norm-embedding-set/2`** (§1). A build stored under the old
  digest would conflict on replay, loudly. None exists: no corpus has reached any database
  with embeddings.
- **File formats:**
  - `auditmanager-embedding-plan/1`;
  - `auditmanager-embedding-batch/1`, with a `sha256sum`-format sidecar;
  - `auditmanager-tokenizer-recording/1`, which stores text digests, never texts;
  - `auditmanager-embed-texts-request/1` and `auditmanager-embed-texts/1`.
- **CLI:** `python -m auditmanager.norms.embedding prepare|build|load|status|embed-texts|self-test`.
  Exit 0 means done, 2 refused, 75 batches remain.
- **`norms.public` additions:**
  - `EMBEDDING_PROFILE`, `EMBEDDING_SET_DIGEST_VERSION`, `EMBED_TEXTS_REQUEST_FORMAT` and
    `EMBED_TEXTS_RESPONSE_FORMAT`;
  - `EmbeddingSetDigest`;
  - `NormEmbeddingRepository`, `NormEmbeddingConflict`, `NormEmbeddingScanShort`,
    `NearestEmbedding` and `StoredEmbeddingBuild`.

### Readings where the plan was silent (conservative choices)

1. **`build` in the image is the encode phase only.** It has no database and no network. The
   plan names one `build` entry point inside the BGE image, but the image has no database
   driver, and its contract is `--network none`. Database access would mean either adding
   SQLAlchemy and psycopg to the image lock or giving the container a network. So the work is
   split:
   - `prepare` on the host writes the inputs;
   - `build` in the image writes the checkpoints;
   - `load` on the host is the plan's "streaming `ensure_build` … in one transaction with the
     completion row".
   The plan's `build --snapshot --chunking-profile --checkpoint` argument shape is kept.
2. **The embedder is baked in from a repository-root context cut to an allowlist.** The
   alternatives were a mounted checkout, which is not "with the embedder inside", or a call-site
   `--build-context`, which is an input redirectable from the call site.
3. **The overlap is checked in characters.** The repository cannot re-tokenize. The 64-token
   overlap is guaranteed by the port and by the real-tokenizer equality check. The repository
   checks what it can check exactly: coverage, a strict character overlap, slice digests and
   spans. A run that produced merely touching windows is refused, never accepted.
4. **Window paragraph spans are per window.** `NORM_EMBEDDING_BAKEOFF.md` says "every window
   records its canonical paragraph IDs". A whole-chunk span would be true but coarse.
5. **`nearest` refuses a short answer** (`NormEmbeddingScanShort`) rather than returning fewer
   rows. `AGENTS.md` §4 forbids a silent fallback. `ef_search = 200` and
   `max_scan_tuples = 100 000` are first values; W55 measures recall and p95 on real vectors and
   owns any retuning.
6. **`embed-texts` refuses a text over 512 tokens** rather than windowing it. A batch caller
   that wants windows asks for them. The vectors are big-endian, so `vector_sha256` equals
   `norm_embedding.embedding_sha256` for the same bytes.
7. **No corpus text is committed.** The recordings use a deterministic synthetic text set.
   Equality on the corpus itself is measured in the window, never recorded.
8. **`run-build.sh` caps the container at 5 GiB with no swap.** The bake-off peaked at 3.2 GiB,
   and the host floor is 6 GiB available. An OOM kill costs one batch.

## 4. Risks and known limitations

- **No database ran.** The 9 DB cases are unexecuted, and the SQL was checked for syntax only.
  The first places to fail in the window would be:
  - a column name;
  - psycopg's adaptation of `CAST(:refs AS text[])`;
  - `EXPLAIN` with bound parameters;
  - whether the planner, with sequential scans, bitmap scans and sorts disabled, picks the HNSW
    index for 180 rows. The test asserts this and fails loudly if not.
- **No image was built.** Neither `encoder.py`, `selftest.py` nor `check_windows.py` has run
  against the real libraries. They use the calls `self_check.py` already uses
  (`SentenceTransformer`, `model[1].pooling_mode_cls_token`, `encode(...,
  normalize_embeddings=True)`). The BGE-IMAGE pins (11 model digests, the wheel lock, the image
  id) are still `TODO-PIN-WINDOW`, and they block the build. §5.2 step 1 measures them first.
- **Resume determinism depends on the CPU inference.** A recomputed batch is a fresh encode of
  the same windows in the same order on the same image and 8 threads. Equal bytes are expected
  but unmeasured. The window procedure includes the check (§5.5, step 5).
- **Disk, estimated by arithmetic and not measured:**
  - vectors: 62,325 windows × 5,464 base64 bytes ≈ 340 MB;
  - inputs: about 55,700 chunks × about 1,072 characters, Cyrillic UTF-8 plus JSON, ≈ 130 MB;
  - total ≈ 0.47 GB, against §3.9's 0.5 GB. The checkpoint directory can be removed after a
    verified `load` and a promotion dump.
- **Time, by the bake-off rate:** 1.25 windows/s, so the full build is ≈ 13.8 h. At the
  default 256 chunks per batch there are ≈ 218 batches of ≈ 4 minutes each. The load
  (≈ 62,000 HNSW inserts plus the read-back digest) is unmeasured.
- **`check-windows.sh` reads the base projection's paragraphs and chunks**, not the repaired
  snapshot's `characters-v2` chunks. That proves the algorithm on the real tokenizer. The
  build itself re-verifies every window set against the stored chunks.

## 5. Integrator instructions (window commands)

Merge after reading the diff and this report: SNAPSHOT → **EMBED** → WORKER (plan §5). Shared
paths handed on:

- the export lines of `norms/public.py` and `norms/README.md`, to BUNDLE;
- `infra/norms-worker/**`, `FOUNDATION_LOCK.json` (`norms_worker`) and the image test, which
  stay with this lane until the window steps below are recorded.

Every step below is a heavy step. Run one at a time, inside the owner's window. Before each:
`free -b` must show ≥ 6 GiB available and `df -B1 /` the step's increment + 3 GiB. Kill only
by confirmed own PID, never by pattern.

### 5.1 Database cases (lane stack: PostgreSQL `57160`, S3 `60760/60761`)

Bring up the lane stack with a lane `.env` naming those ports, then from the worktree:

```sh
set -a; . ./.env; set +a
.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/db/test_norm_embeddings_migration.py
.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms \
    --ignore=tests/integration/norms/custody/test_two_phase_custody.py \
    --deselect tests/integration/norms/test_embedding_bakeoff_fixture.py::test_every_relevance_anchor_resolves_to_the_exact_real_corpus
```

- Expected from the first command: **9 passed**.
- Expected from the second: **379 passed, 1 skipped**. That is the 342 container-free cases
  plus REPAIR's 37 `postgres` cases; the skip lasts until §5.3 commits its recording.
- Stop the stack by its own compose project.

### 5.2 Rebuild the image with the embedder inside (≈ 6.5 GB, 3.2 GiB, ≈ 8 min)

1. **Pins first,** if BGE-IMAGE's window has not measured them: `W54-BGE-IMAGE.md` §5
   steps 1–2. That covers 11 model SHA-256 values into the `ADD --checksum` lines and
   `model_files_sha256`, plus the `uv pip compile` wheel lock. Drop each from `pending_pins`.
2. If a BGE-only image exists, remove it **by its tag only**:
   `docker image rm auditmanager-norms-worker:bge-m3-dense-v1-5617a9f`.
3. Build from the **repository root** (the context is cut by `infra/norms-worker/Dockerfile.dockerignore`):

   ```sh
   docker build --file infra/norms-worker/Dockerfile \
     --tag auditmanager-norms-worker:bge-m3-dense-v1-5617a9f .
   ```

   - BuildKit's "transferring context" must be about 0.4 MB plus the measured wheel lock (the
     tracked bytes of the four allowlisted paths are 429,764 today, `du -cb $(git ls-files …)`).
   - The log must contain the BGE line
     `norms-worker self-check OK: bge-m3-dense-v1 BAAI/bge-m3@5617a9f61b028005a4858fdac845db406aefb181 offline dim=1024 dtype=float32 norm=1.000000`
     and then `norms-worker embedder self-test OK: windows=<n≥2> tokens=<t> embed-texts=stable`.
4. Record the digest:
   `docker image inspect --format '{{.Id}}' auditmanager-norms-worker:bge-m3-dense-v1-5617a9f`.
   It goes into `images.norms_worker.image_id`; drop `image_id` from `pending_pins`. Then run
   `.venv/bin/python -m pytest -q tests/integration/composition/test_norms_worker_image_contract.py`,
   which must give 66 passed.

### 5.3 Window equality on the real tokenizer (a few minutes, < 1 GiB)

```sh
infra/norms-worker/check-windows.sh auditmanager-norms-worker:bge-m3-dense-v1-5617a9f \
  /root/projects/PDF-Analysis/.local/norms/corpus <new-empty-scratch-dir>
```

- Expected last line: `norms-worker windows equal: <n> texts, <w> windows`, with exit 0. `<n>`
  is 24 synthetic texts plus every paragraph and chunk of the projection.
- Any `MISMATCH` line is a stop.
- Then copy `<dir>/bge-m3-5617a9f.v1.json` to `tests/integration/norms/embedding/recordings/`.
- Run `.venv/bin/python -m pytest -q tests/integration/norms/embedding/test_windowing.py`. It
  must give 27 passed, with no skip; the replay now runs on the real offsets.
- Commit the recording (lane resume). Set `images.norms_worker.embedder.window_check_status`.

### 5.4 MRR in the rebuilt image (≈ 450 s, 3.2 GiB)

```sh
infra/norms-worker/reproduce-mrr.sh auditmanager-norms-worker:bge-m3-dense-v1-5617a9f \
  /root/projects/PDF-Analysis/.local/norms/corpus <new-empty-scratch-dir>
```

- Expected: `norms-worker MRR reproduced: 0.848611 (24 queries, 563 windows)`.
- Any `MISMATCH` is a plan §7 stop.
- Set `images.norms_worker.reproduction.status` and `status`.

### 5.5 The full corpus build over night windows (`W54-CORPUS-OPERATE-01`)

**Preconditions:**

- the image of §5.2 is built;
- the promotion database holds the repaired snapshot with its `characters-v2:1200` chunk build
  (operator step 3, `W54-SNAPSHOT-01.md` §5.5);
- the loader printed `<ns_id>` and `<content_key>`.

1. **Prepare** (database up, ≈ 1 GiB). Run:

   ```sh
   scripts/promotion/stack.sh up
   scripts/promotion/stack.sh run -- env PYTHONPATH=src .venv/bin/python -m auditmanager.norms.embedding \
     prepare --snapshot <ns_id> --chunking-profile characters-v2:1200 \
     --checkpoint .local/norms/builds/<content_key>
   scripts/promotion/stack.sh stop
   ```

   - It prints `plan_sha256`, about 55.7 k chunks and about 218 batches.
   - A re-run is a no-op when equal; it is refused if anything differs.
   - The database is stopped during encoding.
2. **Encode, one night window at a time** (≈ 3.2 GiB, no database, `--network none`).
   Choose `MAX_BATCHES` to fit the window: about 15 batches per hour (≈ 286 windows per batch
   at the bake-off's 1.25 windows/s; estimated, not measured).

   ```sh
   infra/norms-worker/run-build.sh auditmanager-norms-worker:bge-m3-dense-v1-5617a9f \
     .local/norms/builds/<content_key> <ns_id> characters-v2:1200 <MAX_BATCHES>
   ```

   - Exit 75 means batches remain: run the same command in the next window.
   - Exit 0 prints `all <n> batches verified: … embedding-set digest <sha>`.
   - Killing the container at any moment costs at most the batch in flight. A restart reports
     an invalid or partial batch and computes it again.
   - Progress between windows:
     `PYTHONPATH=src .venv/bin/python -m auditmanager.norms.embedding status --checkpoint .local/norms/builds/<content_key>`.
3. **Two failed nights** move the step under `W54-INT-CARRYOVER-01` (§3.9).
4. **Load** (database up). Run:

   ```sh
   scripts/promotion/stack.sh up
   scripts/promotion/stack.sh run -- env PYTHONPATH=src .venv/bin/python -m auditmanager.norms.embedding \
     load --snapshot <ns_id> --chunking-profile characters-v2:1200 \
     --checkpoint .local/norms/builds/<content_key>
   ```

   - It verifies every checkpoint and loads them in one transaction ending with the
     completion row.
   - It prints `embedding_set_sha256`, which must equal the digest printed by step 2.
   - A replay prints `created: false`.
   - Then take the promotion dump and restore-verify it (`scripts/promotion/dump.sh`,
     `verify-dump.sh`).
5. **Determinism check (once, in the first window after step 2 has verified at least one
   batch):**
   - note `vectors/batch-00000.jsonl.sha256`;
   - move the pair `batch-00000.jsonl{,.sha256}` aside, out of the build directory;
   - run step 2 with `MAX_BATCHES=1`;
   - the new sidecar must equal the noted one.
   Equal means a resumed build is byte-identical. A difference is a stop: report it, do not
   load.

## 6. Containment

Grant (plan §4 Stage B item 4):

- `norms/embedding/**` and `norms/embedding_repository.py`;
- the export lines of `norms/{public,__init__}.py`;
- `norms/README.md`, its rows;
- `tests/integration/norms/embedding/**`;
- `tests/integration/db/test_norm_embeddings_migration.py`, its repository cases;
- `infra/norms-worker/**`;
- `docs/program/FOUNDATION_LOCK.json`, the `norms_worker` entry;
- `tests/integration/composition/test_norms_worker_image_contract.py`;
- `docs/program/W54-EMBED-01.md`.

`git diff --name-only 81bc86d..HEAD`:

```
docs/program/FOUNDATION_LOCK.json
docs/program/W54-EMBED-01.md
infra/norms-worker/Dockerfile
infra/norms-worker/Dockerfile.dockerignore
infra/norms-worker/check-windows.sh
infra/norms-worker/check_windows.py
infra/norms-worker/run-build.sh
infra/norms-worker/tokenizer_recording.py
src/auditmanager/norms/README.md
src/auditmanager/norms/embedding/__init__.py
src/auditmanager/norms/embedding/__main__.py
src/auditmanager/norms/embedding/builder.py
src/auditmanager/norms/embedding/checkpoint.py
src/auditmanager/norms/embedding/digest.py
src/auditmanager/norms/embedding/encoder.py
src/auditmanager/norms/embedding/model.py
src/auditmanager/norms/embedding/operations.py
src/auditmanager/norms/embedding/profile.py
src/auditmanager/norms/embedding/selftest.py
src/auditmanager/norms/embedding/texts.py
src/auditmanager/norms/embedding/vectors.py
src/auditmanager/norms/embedding/windowing.py
src/auditmanager/norms/embedding_repository.py
src/auditmanager/norms/public.py
tests/integration/composition/test_norms_worker_image_contract.py
tests/integration/db/test_norm_embeddings_migration.py
tests/integration/norms/embedding/recordings/synthetic-fake-tokenizer.v1.json
tests/integration/norms/embedding/support.py
tests/integration/norms/embedding/test_build_resume.py
tests/integration/norms/embedding/test_cli.py
tests/integration/norms/embedding/test_digest.py
tests/integration/norms/embedding/test_embed_texts.py
tests/integration/norms/embedding/test_memory_bound.py
tests/integration/norms/embedding/test_repository_offline.py
tests/integration/norms/embedding/test_windowing.py
```

All 35 paths are inside the grant.

- The `FOUNDATION_LOCK.json` diff touches only `images.norms_worker`. The file was rewritten by
  the same `json.dumps(indent=2, ensure_ascii=False)` it round-trips byte-identically through
  (checked before the edit).
- `infra/norms-worker/self_check.py`, `compare_bakeoff.py`, `reproduce-mrr.sh`,
  `requirements.in` and `requirements.lock` are unchanged.
- A lint auto-fix touched two of them during the work; both were restored with
  `git checkout --` before the commit.

**Not touched:**

- `contracts/**` and migrations;
- root `pyproject.toml`, `uv.lock` and `Makefile`;
- the composition root;
- `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md` and `CURRENT_STATE.md`;
- `norms/__init__.py`;
- refs and tags;
- the stand and other worktrees;
- `.local/norms/**`, which was neither read nor written.

No container was started. There was no push, merge, tag or stash. The scratch virtualenv
(`pglast`, `ruff`) lives in the session scratchpad. `git status --porcelain -uall` is empty
after this commit.
