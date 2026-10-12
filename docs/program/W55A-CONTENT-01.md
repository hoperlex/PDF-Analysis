# W55A-CONTENT-01 — hand-back report

- Task: `docs/program/tasks/W55A-CONTENT-01.md`; grant: `dispatch/W55-PLAN.md` §A4 Stage B item 1
  (minus `web/tests/unit/api/configuration-and-cache-keys.test.ts`, which WEB-NORMS owns), plus
  this file.
- Branch `agent/w55a-content-01`, worktree `.local/worktrees/w55a-content`, base `959eb86`
  (`integration/w54` with the W55a seal: head `0020`, `stream_content`, `ByteRange`,
  `StreamingWireResponse`). Commits `088c458` (implementation and tests), `17d703d` (a trailing
  blank line `git diff --check` found); this report is the next commit.
- Checks follow `R-102`/`R-111`: light and container-free. **No container was started.** The
  database- and MinIO-backed cases are written and listed in §5 for the window.

## 1. Changed files

`git diff --name-only 959eb86..HEAD` (17 paths, plus this report):

- **Storage:** `src/auditmanager/storage/{port,s3,durable_publication,public,__init__}.py` —
  `BlobStore.open_stream`, `STREAM_CHUNK_BYTES`, `BlobChunks`.
- **Ingest (read path):** `src/auditmanager/ingest/service.py` — `IngestService.open_source_stream`,
  `SourceStream`.
- **API:** `src/auditmanager/api/routers/documents.py` — the content route's body.
- **Composition:** `src/auditmanager/bootstrap/adapters.py` — `DocumentAdapter.stream_content` only.
- **Web:** `web/src/shared/api/credentialed-forward.ts`, `web/tests/unit/api/credentialed-forward.test.ts`.
- **Tests (new):** `tests/integration/storage/test_streamed_read_offline.py` (container-free),
  `tests/integration/storage/test_streamed_read.py` (MinIO, window),
  `tests/integration/api/test_document_content_streaming.py` (container-free),
  `tests/integration/api/test_document_content_window.py` (PostgreSQL + MinIO, window).
- **Tests (changed):** `tests/integration/api/test_range_rules.py`; and two paths **outside the
  grant**, see §6: `tests/contract/api_v1/test_w55a_norms_seal.py`, `tests/integration/api/conftest.py`.

What was built (plan §A3.5, `R-115`):

- `S3BlobStore.open_stream(blob_id, *, expected_sha256, expected_size, window=None, chunk_size)`
  issues one `GetObject` (with `Range: bytes=a-b` for a window) and checks its headers **before it
  returns**: absent object, refused or unreachable store, missing recorded digest, recorded digest
  ≠ the caller's declared one, stored size ≠ declared size (`ContentLength`, or the total after the
  slash of `ContentRange`), `InvalidRange`, and a store that ignored `Range` are all raised by the
  call, not by the iterator. The returned generator reads the body `chunk_size` at a time. A whole
  read hashes as it goes and **holds back its last chunk** until the digest equals the declared one;
  on a mismatch it logs `storage_integrity_error` (blob id, bytes sent of declared, no bucket or
  key) and raises `ChecksumMismatchError` instead of yielding it. A body that ends early or runs
  long raises `SizeMismatchError` on both kinds of read.
- `IngestService.open_source_stream` keeps the order the status line needs: manifest entry
  (`404`), the window resolved against the **manifest's** size (`422 unsatisfiable`, store not
  touched), then the object opened with `entry.sha256`/`entry.size_bytes` as the declaration. It
  maps failures as `read_source_bytes` does (absent object → `storage_integrity_error`, otherwise
  `domain_error_from_storage`).
- `streamDocumentVersionContent` now calls `DocumentPort.stream_content` and answers through
  `streamed_content_response`. A malformed `Range` on an unknown version still answers `404`: the
  router asks for the version before re-raising the parse refusal (`_parsed_range`).
- The BFF forwards `range` up and `content-length`, `content-range`, `accept-ranges` down.
  `content-length` is dropped when the upstream had a `content-encoding` (the fetch runtime decodes
  it, so the upstream length would be wrong) and on bodyless statuses.

## 2. Checks run

On the committed tree `088c458`/`17d703d` unless stated.

| Command | Result |
| --- | --- |
| `git diff --check 959eb86..HEAD` | clean |
| `.venv/bin/python -m compileall -q src/auditmanager/{storage,ingest,api,bootstrap} tests/integration/{api,storage} tests/contract/api_v1` | exit 0 |
| `.venv/bin/python -m pytest -q tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py` | **620 passed**, 50 subtests (clean tree; on a dirty tree `test_alpha_acceptance_command.py` fails by design) |
| `pytest -q tests/integration/api/test_document_content_streaming.py tests/integration/storage/test_streamed_read_offline.py tests/integration/storage/test_publish_reuse_checks_offline.py tests/integration/api/test_range_rules.py tests/integration/api/test_streaming_wire_response.py` (no `DATABASE_URL`) | **63 passed** |
| `pytest -q tests/integration/composition/test_every_port_implementation_is_whole.py` (uncommitted tree with the same source) | 18 passed (3 min) |
| `pytest --co` over `tests/integration/api`, `tests/integration/storage`, the two storage fakes and `tests/characterization/w13_baseline` | 693 collected, 0 errors |
| `npm --prefix web run lint` / `npm --prefix web run typecheck` | exit 0 / exit 0 |
| `cd web && npx vitest run tests/unit/api tests/unit/session/bff-session.test.ts tests/unit/screens/routes.test.ts tests/guards tests/unit/review/evidence-viewer.test.ts tests/unit/review/key-leakage.test.ts` (uncommitted tree, same web source) | 31 files, **489 passed** (`configuration-and-cache-keys.test.ts` was run, not edited) |

**Each new behaviour fails without its change** (mutations applied to a scratch copy and reverted):

- hold-back removed (every chunk yielded as read): 5 cases red — both tamper cases in the API suite,
  three in the storage offline suite;
- the pre-change router body (`read_content` and slicing) restored: 16 of 21 API cases red,
  including "a ranged read never loads the object" (the store received a whole-object `GetObject`)
  and the short-body cases;
- the `404` precedence removed: `test_an_unknown_version_is_404_whatever_the_range_says[bytes=abc]` red;
- the BFF cases name `range`, `content-range`, `content-length`, `accept-ranges` as literals, and the
  `content-encoding` case fails if the condition is removed.

The two `.venv` and `web/node_modules` symlinks were used, not changed.

## 3. Contracts

No change to `contracts/**`, the migration head (`0020_norms_search`), the OpenAPI document, the
error catalog or the surface counts (45 / 52 / 116). New **internal** interfaces:

- port `BlobStore.open_stream(...) -> BlobChunks` (`Generator[bytes, None, None]`) and
  `STREAM_CHUNK_BYTES = 256 KiB`, exported from `auditmanager.storage` and `auditmanager.storage.public`;
  `DurablePublicationStore` delegates it;
- `IngestService.open_source_stream(version_uid, *, resolve_window, chunk_size) -> SourceStream`
  (`total_size`, `window`, `chunks`).

Wire behaviour: `200` and `206` keep records 14's and 15's header lists and order
(`Content-Type`, `Content-Length`, `Content-Range` on `206`, `Accept-Ranges`, then
`X-Correlation-Id`); a refused storage credential keeps record 31 (`500
dependency_credential_refused`, `{dependency: blob_storage}`), asserted container-free. Changes
that are intended by the plan: an unsatisfiable range is now `422` even when storage is down (it was
checked after the read); a tampered object's whole read is `200` with a short body and an aborted
stream instead of a `422 storage_integrity_error` envelope; an absent object is still `422
storage_integrity_error` (the catalog's status for that code).

## 4. Risks and known limitations

- **Records 14, 15, 31 are proved container-free only** (header lists, order, bodies, the record-31
  envelope); the byte comparison `tests/characterization/w13_baseline` runs in the window (§5).
- **A window is not hashed** (`R-115`): a body replaced under intact metadata is served as stored on
  a `206` (asserted, so the limitation is visible). The open does compare the recorded digest and
  the stored size against the manifest on both paths.
- Hold-back granularity is one chunk (256 KiB): on a tampered whole read the client receives every
  earlier chunk. A document of one chunk or less (the AR baseline, 58 978 bytes) delivers nothing.
- If a client disconnects before the first chunk, the S3 body is released by garbage collection
  rather than by `close()` (an unstarted generator runs no `finally`).
- The abort after the status line is how Starlette and Uvicorn end a failed stream; the API-level
  proof drives the ASGI app with a recording `send` (no `more_body: False` is sent). Behaviour
  through nginx and the Next BFF with a real short stream is not observed here (window/journey).
- `DocumentPort.read_content` has no caller in the router any more; it stays on the port (SEAL's
  shape). `ports.py`'s docstrings ("the router still calls `read_content`", "served by slicing")
  are now stale — that file is SEAL's (api/** except router bodies), so it was not edited.

## 5. Integrator instructions

1. Read the diff and this report; merge `agent/w55a-content-01`. Stage B continues with SEARCH,
   which takes `bootstrap/adapters.py` next.
2. **Window (D-157)**, this lane's stack on PostgreSQL `57220` and S3 `60820/60821` with a lane
   `.env`, from the worktree:

   ```sh
   set -a; . ./.env; set +a
   .venv/bin/python -m pytest -q tests/integration/storage/test_streamed_read.py
   .venv/bin/python -m pytest -q tests/integration/api/test_document_content_window.py
   .venv/bin/python -m pytest -q tests/integration/storage tests/integration/api \
       tests/characterization/w13_baseline \
       tests/integration/ingest/test_reconciliation_reads_the_bytes.py \
       tests/integration/runs/test_a_halted_chain_reaches_a_terminal.py \
       tests/integration/composition/test_router_answers.py
   ```

   Expected: all green; records 14, 15 and 31 compare byte for byte.
3. Stop the lane stack by its own compose project; kill nothing by pattern.

**Notes for `W55A-SEARCH-01`:** `NormContentAdapter.stream_content` should resolve the confirmed
binding (its `blob_id`, `sha256`, `size_bytes`), resolve `byte_range` against the binding's size
(`ByteRange.resolve`, `422`), then call `blob_store.open_stream(blob_id,
expected_sha256=binding.sha256, expected_size=binding.size_bytes, window=..., chunk_size=CONTENT_CHUNK_BYTES)`
and map `BlobNotFoundError`/`StorageError` as `IngestService.open_source_stream` does. The hold-back,
the size checks and the `storage_integrity_error` log come with `open_stream`. The norms route parses
`Range` before the port (a malformed header on an unknown norm document is `422`, not `404`); align it
with `documents.py`'s `_parsed_range` if the same precedence is wanted.

## 6. Containment

- `git diff --name-only 959eb86..HEAD`: the 17 paths of §1 plus this report. Fifteen are inside the
  grant. **Two are outside it, each forced by the change and kept minimal; revert them only together
  with the corresponding behaviour:**
  - `tests/contract/api_v1/test_w55a_norms_seal.py` — it asserted that `DocumentAdapter(None).stream_content`
    refuses as a sealed stub (now it has a body), and imported `documents._resolve_range`, which the
    route no longer uses. The stub assertion is removed; the retired range rule is copied verbatim into
    the test as the oracle, so the 48-case `ByteRange` comparison can still fail.
  - `tests/integration/api/conftest.py` — `IngestDocumentAdapter.stream_content` was a refusing stub
    ("nothing in this suite calls it before the content lane gives both adapters a body"); it now
    delegates to the shipped `DocumentAdapter`, so `test_journey.py`'s content cases drive the shipped body.
- Not touched: `contracts/**`, migrations, `api/routers/{ports,wire,norms}.py`, `api/schemas/**`,
  `bootstrap/composition.py`, `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`,
  `configuration-and-cache-keys.test.ts`, root dependency and lock files, refs, tags, the stand, other
  worktrees.
- No container, no push, no merge, no tag. `git status --porcelain -uall` is empty after the report
  commit.
