# W54-BGE-IMAGE — norms-worker image definition handback

Base: `7ebf162` (`W54-FREEZE-01`, = `origin/dev` at dispatch). Branch: `agent/w54-bge-image`,
worktree `.local/worktrees/w54-bge`. The integrator reads the exact HEAD after this report is
committed.

**Scope delivered now:** the image definition and its static, container-free contract. **Not
run (heavy steps, `W54-FREEZE-01`):** no image build, no `docker` command of any kind, no model
or wheel download, no corpus read. The pins below that the repository has never recorded are
not invented. They are spelled `TODO-PIN-WINDOW` and declared in
`images.norms_worker.pending_pins`. The Dockerfile cannot build until they are measured.

## 1. Changed files

- `infra/norms-worker/Dockerfile` (new). One `FROM` by tag plus index digest and no `ARG`.
  The wheels come from the hashed lock (`--require-hashes --no-deps --only-binary=:all:`), and
  a lock that still carries `TODO-PIN` is refused before `pip install`. Eleven model files
  come from revision `5617a9f…` through `ADD --chmod=0444 --checksum=sha256:…` into a hub-cache
  snapshot of that commit. The image sets `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`.
  Threads are pinned to 8 (`OMP_NUM_THREADS`, `MKL_NUM_THREADS`). The self-check runs under
  `RUN --network=none` and is also the image's `CMD`. The image runs as non-root uid 10001.
- `infra/norms-worker/self_check.py` (new): an offline self-check. It holds the profile
  constants and the exact model file set. It verifies the snapshot file set, the five runtime
  versions, a fast tokenizer with 2 special tokens, CLS pooling, and one probe vector
  `(1, 1024)` float32 with L2 norm 1. It imports only stdlib at module level.
- `infra/norms-worker/requirements.in` (new): the five versions the bake-off recorded.
- `infra/norms-worker/requirements.lock` (new): a `TODO-PIN-WINDOW` placeholder that gives
  the exact generation command.
- `infra/norms-worker/reproduce-mrr.sh` (new): the window runner. It makes one `docker run
  --rm --pull never --network none`. The checkout is mounted read-only at `/work` and the
  corpus drop read-only at `/corpus`. It refuses before any `docker` call when the corpus has no
  `MANIFEST.json`, when the output is inside the drop, or when the output is not empty.
- `infra/norms-worker/compare_bakeoff.py` (new, stdlib). It compares every deterministic field
  exactly against `fixtures/evaluation/norms/results/bge-m3.json`. Only timings, RSS, the
  Python patch level and the platform may differ.
- `docs/program/FOUNDATION_LOCK.json`: the new `images.norms_worker` entry. The
  `images.immutability.rule` sentence now names `infra/norms-worker` and the pending-pin refusal.
- `tests/integration/composition/test_norms_worker_image_contract.py` (new, 45 cases).
- `docs/program/W54-BGE-IMAGE.md` (this report).

## 2. Checks and results

| Command | Result |
| --- | --- |
| `.venv/bin/python -m pytest -q tests/integration/composition/test_norms_worker_image_contract.py` | 45 passed |
| `.venv/bin/python -m pytest -q tests/integration/composition/test_minio_image_contract.py tests/integration/composition/test_pgvector_image_contract.py tests/integration/norms/test_embedding_bakeoff_results.py tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py tests/contract/program/test_wave_governance.py tests/contract/tools/test_pin_sweep.py` | 108 passed |
| `shellcheck infra/norms-worker/reproduce-mrr.sh` | clean |
| `git diff --check 7ebf162..HEAD` | clean |

Notes on scope:

- The prose guards were included because they read the files this lane changed:
  `test_doc_prose_facts` sweeps `tests/**/*.py`, and `test_surface_counts_in_prose` sweeps
  `docs/**/*.md`.
- The other `FOUNDATION_LOCK` readers do not read `images`. They are
  `tests/integration/db/*`, `storage/test_check_storage.py` and
  `composition/test_dashboard_summary_over_a_fresh_deployment.py`, all of which need a stack,
  so they were not run.
- The excluded environmental files were not run: `test_cp00_candidate.py`,
  `test_cp00_final_state.py` and `test_validate_bootstrap.py`.

How the new test proves itself. Every structural check is a function of the text, and each
one is shown red on a mutant: an undigested or extra `FROM`, an `ARG`, `:latest`, a missing or
non-digest checksum, a non-frozen revision URL, a wrong destination, a missing file, a dropped
`--require-hashes`/`--no-deps`/`--only-binary`, a `curl` fetch, the removed TODO-lock refusal,
removed offline variables, a self-check without `--network=none`, a runner without
`--network none` or `--pull never`, and writable mounts. The pending-pin check fails both ways:
an unpinned value that is not declared, and a declared value that is pinned. The comparator
refuses each kind of deterministic drift (MRR, one rank, window count, runner SHA, torch
version, tokenizer window count, dimension, a missing field) and ignores only the host
fields. The runner is driven end to end against a `docker` stub on `PATH`: its exact argv,
the success line, and a drifted result that exits 1. Each of its three refusals is shown
before any `docker` call, and on a mutant without that guard.

## 3. Contracts

No `contracts/**`, migration, API or root lock change. The new `FOUNDATION_LOCK.json`
`images.norms_worker` entry records:

- the Dockerfile and its build context, the local image name
  `auditmanager-norms-worker:bge-m3-dense-v1-5617a9f`, and the base digest;
- the wheel inputs, the lock and the install policy;
- the runtime versions and the profile: `bge-m3-dense-v1`, `BAAI/bge-m3@5617a9f61b028005a4858fdac845db406aefb181`,
  CLS pooling, 1024 dimensions, float32, normalized, inner product, 512/64, 8 threads;
- the per-file model SHA-256 map, the network-at-run statement and the reproduction targets
  (MRR `0.848611`, 24 queries, 563 windows);
- `pending_pins` and the owner, which is this task with `W54-EMBED-01` as successor writer.

The test keeps the profile equal to the bake-off record, `NORM_EMBEDDING_BAKEOFF.md`, the
`0013_norm_embeddings` profile row and the lock.

### Pins: found and missing

| Pin | Source | State |
| --- | --- | --- |
| Base `python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254` | `infra/deploy/Dockerfile.api` (resolved 2026-09-18) | pinned |
| Model revision `5617a9f61b028005a4858fdac845db406aefb181` | bake-off doc, results JSON, migration 0013 | pinned |
| `torch==2.7.1+cpu`, `transformers==4.53.3`, `sentence-transformers==5.0.0`, `tokenizers==0.21.4`, `numpy==2.5.3` | bake-off doc | pinned as versions in `requirements.in` |
| Wheel hashes and the transitive closure (e.g. `huggingface-hub`, `safetensors`, `scipy`, `scikit-learn`) | recorded nowhere | **TODO** `wheel_lock` |
| SHA-256 of the 11 model files (`1_Pooling/config.json`, `README.md`, `config.json`, `config_sentence_transformers.json`, `modules.json`, `pytorch_model.bin`, `sentence_bert_config.json`, `sentencepiece.bpe.model`, `special_tokens_map.json`, `tokenizer.json`, `tokenizer_config.json`) | recorded nowhere; the bake-off cache `/tmp/norm-embed-hf-cache` no longer exists | **TODO**, 11 entries |
| Built image ID | produced by the build | **TODO** `image_id` |

## 4. Risks and known limitations

- **The image is unbuildable until the window.** This is by design: a `TODO-PIN-WINDOW`
  checksum is not a digest, and the wheel-lock refusal fires first.
- **Weight file choice.** The repository does not record which weight file the online
  bake-off loaded. `transformers` prefers `model.safetensors` when the revision has one. The
  definition fetches `pytorch_model.bin`. If the revision's tree lists `model.safetensors`,
  replace that entry in `self_check.MODEL_FILES`, in the Dockerfile `ADD` and in the lock
  before building.
- **Runtime differs from the bake-off host.** The image runs Python 3.12.x from the pinned
  base, not 3.12.3, and glibc 2.36, not 2.39. The transitive wheel versions are resolved at
  window time. The same torch CPU wheel should give the same ranks. Any deterministic
  difference is a plan §7 stop ("the MRR differs in either image"), and the comparator names
  every differing field.
- **Build memory.** The build-time self-check loads the model, so the build itself peaks near
  the 3.2 GiB RSS, not only the reproduction.
- **Frontend tag.** `# syntax=docker/dockerfile:1.7` is a frontend tag without a digest, the
  same as `infra/postgres` and `infra/minio`.
- **Run time.** The reproduction runtime is about 450 s of passage encoding, plus the corpus
  read and about 110 s of full-corpus tokenizer statistics, which the runner also computes and
  the comparator checks.

## 5. Instructions for the integrator (window commands)

Run from the merged checkout, one heavy step at a time, inside the owner's window.

0. **Floors.** Run `free -b` and `df -B1 /` immediately before each step. Proceed only if
   at least 6 GiB is available, and at least 6.5 GB + 3 GiB is free for the build.

1. **Measure the pins.** This needs network but is not a heavy step. Resume this lane, or
   assign it to the owner of `infra/norms-worker/**`.
   - Model files. This streams about 2.3 GB to `sha256sum` and writes nothing to disk:

     ```bash
     rev=5617a9f61b028005a4858fdac845db406aefb181
     curl -fsSL "https://huggingface.co/api/models/BAAI/bge-m3/tree/$rev?recursive=true" \
       | python3 -c 'import json,sys; [print(e.get("lfs",{}).get("oid","-"), e["path"]) for e in json.load(sys.stdin) if e["type"]=="file"]'
     for f in 1_Pooling/config.json README.md config.json config_sentence_transformers.json \
              modules.json pytorch_model.bin sentence_bert_config.json sentencepiece.bpe.model \
              special_tokens_map.json tokenizer.json tokenizer_config.json; do
       printf '%s  %s\n' "$(curl -fsSL "https://huggingface.co/BAAI/bge-m3/resolve/$rev/$f" | sha256sum | cut -d' ' -f1)" "$f"
     done
     ```

     The tree listing confirms the weight-file question in §4. Each LFS `oid` must equal the
     streamed SHA-256. Write each value into its `ADD --checksum` line and into
     `images.norms_worker.model_files_sha256`, then drop those entries from `pending_pins`.
   - Wheels: run the `uv pip compile` command written in `infra/norms-worker/requirements.lock`
     (the Makefile's uv `0.12.11`), then drop `wheel_lock` from `pending_pins`.
   - Re-run `.venv/bin/python -m pytest -q tests/integration/composition/test_norms_worker_image_contract.py`.
     It must be green, with the new values accepted as 64-hex digests.

2. **Build** (heavy: about 6.5 GB, 3.2 GiB, 450 s; BuildKit):

   ```bash
   docker build --file infra/norms-worker/Dockerfile \
     --tag auditmanager-norms-worker:bge-m3-dense-v1-5617a9f infra/norms-worker
   ```

   The build log must contain
   `norms-worker self-check OK: bge-m3-dense-v1 BAAI/bge-m3@5617a9f61b028005a4858fdac845db406aefb181 offline dim=1024 dtype=float32 norm=1.000000`.
   Then record the image ID in `images.norms_worker.image_id` and drop `image_id` from
   `pending_pins`:

   ```bash
   docker image inspect --format '{{.Id}}' auditmanager-norms-worker:bge-m3-dense-v1-5617a9f
   ```

3. **MRR reproduction** (heavy: about 3.2 GiB RSS; the drop is mounted read-only; `--network none`):

   ```bash
   infra/norms-worker/reproduce-mrr.sh auditmanager-norms-worker:bge-m3-dense-v1-5617a9f \
     /root/projects/PDF-Analysis/.local/norms/corpus <new-empty-scratch-dir>
   ```

   Expected last line: `norms-worker MRR reproduced: 0.848611 (24 queries, 563 windows)`,
   exit 0. Any `MISMATCH …` line is a stop under plan §7.

4. Afterwards, set `images.norms_worker.reproduction.status` and `status` to the measured
   result. Per plan §3.9/§3.4 the image is then pruned: remove it **by its own tag only**
   (`docker image rm auditmanager-norms-worker:bge-m3-dense-v1-5617a9f`). Do not run a
   host-wide builder or image prune, because the host is shared. `W54-EMBED-01` becomes the
   next writer of `infra/norms-worker/**`, `FOUNDATION_LOCK.json` and this test (plan §6).

Merge order (plan §5): after SEAL, before TRANSPORT. The diff touches nothing SEAL or
TRANSPORT owns.

## 6. Containment

Grant (plan §4 Stage A, `W54-BGE-IMAGE`): `infra/norms-worker/**`,
`docs/program/FOUNDATION_LOCK.json` (`norms_worker` entry and the `images.immutability`
sentence only), `tests/integration/composition/test_norms_worker_image_contract.py` (new),
and `docs/program/W54-BGE-IMAGE.md`.

`git diff --name-only 7ebf162..HEAD`:

```
docs/program/FOUNDATION_LOCK.json
docs/program/W54-BGE-IMAGE.md
infra/norms-worker/Dockerfile
infra/norms-worker/compare_bakeoff.py
infra/norms-worker/reproduce-mrr.sh
infra/norms-worker/requirements.in
infra/norms-worker/requirements.lock
infra/norms-worker/self_check.py
tests/integration/composition/test_norms_worker_image_contract.py
```

The `FOUNDATION_LOCK.json` diff adds only `images.norms_worker` and changes only
`images.immutability.rule`. No other key and no other byte changed: the file was rewritten by
the same `json.dumps(indent=2, ensure_ascii=False)` it round-trips byte-identically through.

`git status --porcelain -uall` is empty after the commit.

Untouched:

- `contracts/**`, migrations, root `pyproject.toml`/`uv.lock`/`Makefile`, the composition
  root and `infra/deploy/**`;
- `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, `CURRENT_STATE.md`;
- refs, tags, the stand, other worktrees, and `.local/norms/**`, which was only listed (one
  `ls` of the drop's top level and one `du -sh`), never read or written.
