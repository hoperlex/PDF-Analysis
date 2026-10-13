# W55B-STREAM-01 — hand-back report

- Task: `docs/program/tasks/W55B-STREAM-01.md`; grant: `dispatch/W55-PLAN.md` §B4 Stage A′
  `W55B-STREAM-01` under §B5's ownership order, plus this file. **Transport only**: the envelope limits stay
  at 30 pages and 25 MiB, the precheck numbers are unchanged, and the bundle is not parsed.
- Branch `agent/w55b`, worktree `.local/worktrees/w55b-exec`, base `461411b` (the `W55B-FIXTURES-01` report; SEAL
  is `85fd99f`). Eleven implementation commits `dd912f1` … `edbae40`; this report is the last commit.
- How the lane was written: the first ten commits were written by a delegate writer; the session ended before the
  delegate reported, so **the executor read every changed source file in full and re-ran every check and every
  measurement below on the final tree**. Nothing in this report is taken from the delegate.
- Checks follow `R-102` (light acceptance); no full `make gate` was run (§5).

## 1. Changed files

`git diff --name-only 461411b..HEAD` before this report: 23 paths.

- **API transport:** `api/routers/multipart.py` (`UploadGate`, the per-route cap, the busy refusal),
  `api/routers/{documents,__init__}.py`, `api/app.py` (the two caps and the gate capacity are written out where the
  application is assembled).
- **Ingest:** `ingest/envelope.py` (the envelope reads a seekable handle with `pypdfium2`), `ingest/service.py`
  (accepts a handle, rewinds it where it stages it), `bootstrap/adapters.py` (`DocumentAdapter` passes the handle on).
- **Proxy:** `infra/deploy/proxy/{nginx,tls-server}.conf`.
- **Web:** `web/src/shared/api/credentialed-forward.ts`, `web/tests/unit/api/credentialed-forward.test.ts`.
- **Tests (new):** `tests/integration/ingest/{test_envelope_differential,test_envelope_handle_adapter,test_envelope_through_the_service}.py`.
- **Tests (extended):** `tests/integration/api/test_multipart_rules.py`, `tests/integration/ingest/test_size_guard_boundary.py`,
  `tests/contract/test_proxy_rate_limits.py`, `tests/e2e/{test_upload_limit_headroom,prove_the_headroom_guard_can_fail}.py`,
  `tests/characterization/w13_baseline/journey.py` and records `18`, `22`.
- **Outside the grant (one file, see §5.4):** `tests/integration/api/test_portal_block_routes.py`, a `W55B-SEAL-01` test that
  pinned the whole-body read this lane removes.

## 2. Checks run, with commands and results

Host at the heavy steps: `MemAvailable` 3.3–4.0 GiB, 7.2–8.1 GB free on `/`, load average 17–21; lane stack PostgreSQL
`57420`, S3 `61020/61021` (images already on the host), `make up`/`make migrate` rc 0 earlier in the lane;
`make down` rc 0, only the lane's two volumes removed, `.env` deleted.

| Command | Result |
| --- | --- |
| `git diff --check 461411b..HEAD`; `.venv/bin/python -m compileall -q` over `src/auditmanager/{api,ingest,bootstrap}` and the changed test trees | rc 0; rc 0 |
| `… pytest -q tests/integration/ingest/test_envelope_differential.py tests/integration/ingest/test_envelope_handle_adapter.py tests/integration/ingest/test_size_guard_boundary.py tests/integration/api/test_multipart_rules.py tests/contract/test_proxy_rate_limits.py tests/contract/test_proxy_security_headers.py tests/e2e/test_upload_limit_headroom.py tests/e2e/prove_the_headroom_guard_can_fail.py` | **193 passed** |
| `… pytest -q tests/integration/ingest tests/characterization` on the lane stack | **243 passed** |
| `… pytest -q tests/integration/api tests/integration/composition/{test_an_absent_parent_is_not_an_empty_page,test_router_answers,test_composition_root,test_api_token_channel}.py tests/integration/p02_journey` on the lane stack | 678 passed, 1 skipped, **1 failed**: `test_portal_block_routes.py::test_the_document_adapter_reads_the_handle…` (the stale SEAL test, §5.4); after the fix `test_portal_block_routes.py` **8 passed** |
| `… pytest -q tests/contract` (minus `test_cp00_candidate.py`, `test_cp00_final_state.py`, `test_validate_bootstrap.py`) with `tests/e2e/test_pc01_journey_conformance.py`, clean committed tree | **822 passed**, 18 588 subtests |
| `npm --prefix web run typecheck` / `lint` | rc 0 / rc 0 |
| Vitest in two parts: `npx vitest run --exclude 'tests/guards/query-key-shape.guard.test.ts'`, then that file alone (a single run is killed by the host's load: the worker RPC times out while that file runs `tsc` inside the suite) | **130 files, 1942 tests passed** and **1 file, 14 tests passed** |
| `nginx -t` in `nginx:1.27-alpine` (`docker run --rm --add-host api:127.0.0.1 --add-host web:127.0.0.1 -v <dir>:/etc/nginx/conf.d:ro …`) with `nginx.conf` | rc 0, "syntax is ok / test is successful" |
| the same with `nginx.conf` + `tls-server.conf` and the certificates mounted | rc 0 |
| the same with `client_max_body_size 260m` missing its `;` (control) | **rc 1**, `invalid number of arguments in "client_max_body_size" directive` |

### The real-nginx body test

The committed `nginx.conf` and `tls-server.conf` were loaded into one disposable `nginx:1.27-alpine` container (plain on
`8080`, TLS on `8443`) with two stand-in upstreams that answer `200` and name the URI that reached them; `curl` bodies of zeros:

| Request | Result |
| --- | --- |
| 40 MiB to `/api/v1/projects/{p}/documents` and to `/bff/v1/projects/{p}/documents` (http and https) | `200`; the API stand-in saw `/projects/{p}/documents` (prefix removed), the web stand-in the full path; the query string is kept |
| 40 MiB to `/api/v1/projects`, `/bff/v1/projects`, `/api/v1/projects/{p}/runs`, `/api/v1/projects/{p}/documents/` | `413` (nginx's HTML page) — the larger cap is on the two locations alone |
| 30 MiB to `/api/v1/projects` | `200` — the server default `32m` is unchanged |
| **250 MiB** to each upload location | `200` in 0.28–0.34 s; to `/api/v1/projects` `413` in 0.001 s |
| declared `Content-Length` of 260 MiB + 1 byte to either upload location | `413`; exactly 260 MiB is waited for, not refused (the client times out on the empty body) |
| response headers of the upload answer and of a `413` | the four server-level security headers are present on both |

An HTTP/2 probe that declares 260 MiB and sends nothing answers `400` over TLS: that is the protocol framing of a lying
`Content-Length`, not the size rule.

### Peak API memory — measured, method recorded

`.venv/bin/python <scratch>/measure_upload.py 250` with the lane `.env` loaded, tree `edbae40`. The script starts the repository's own
entry point `infra/deploy/serve.py` as a child it owns (loopback `57421`/`57422`, `AUDITMANAGER_API_TOKEN` of its own), mints a
credential for a suite account with `tests/support/accounts.py`, creates a project, and streams one upload from a sparse file in
1 MiB writes with a `Content-Length`: a `multipart/form-data` body whose `file` part is `%PDF-` and zeros. It reads the child's
**`VmHWM`** (the kernel's peak resident set) from `/proc/<pid>/status` before and after each upload.

| Upload | Answer | Time | `VmHWM` growth over an idle process of 127 MiB |
| --- | --- | --- | --- |
| 50 MiB | `422` `validation_failed`, "larger than the accepted envelope allows" | 0.1 s | +2.4 MiB |
| 150 MiB | the same | 0.3 s | +0.2 MiB |
| 250 MiB | the same | 0.8–1.0 s (two runs) | +0.0 to +2.3 MiB |
| a **valid** 24.85 MiB PDF (the committed AR PDF with comment lines appended after `%%EOF`, 8 pages) | `201`, published | 1.1 s | +37.4 MiB |

Control for the instrument: the same reader on a process that allocates 250 MiB shows `VmHWM` +250 MiB. The 250 MiB body is read
through the transport into Starlette's temporary file and refused by the envelope's size rule with the answer `uploadDocument`
gave for an over-25-MiB file before this lane (record 18). **Bounded** here means: independent of the body's size and far below it
(a few MiB for a 250 MiB body). The valid-upload row is larger because it goes on to PDFium (this input's tail forces a
cross-reference rebuild) and to the object store's multipart upload; its 37 MiB is *not* proportional to anything measured here,
and the reading that it is the store client's part buffers is a hypothesis, not a measurement.

**The plan's "≈ 240 s for an accepted 250 MiB upload" cannot be measured in this lane**: the envelope still refuses a file over 25 MiB.
What was measured is the transport — a 250 MiB body is read and answered in about one second on loopback — and `W55B-INGEST-01`,
which accepts such a bundle, owns the end-to-end figure.

### How each new behaviour was shown to fail

Each mutation was applied to the committed file, the named tests run with `-x`, and the file restored byte-for-byte (SHA-256
checked). All nineteen were red.

| Mutation | First red test |
| --- | --- |
| the gate never refuses | `test_multipart_rules.py::TestTheUploadGate::test_the_third_upload_is_refused_before_its_body_is_read` |
| a finished upload keeps its slot; three uploads admitted | the same |
| every route takes the upload cap | `TestTheTransportBodyLimit::test_a_body_one_byte_over_the_limit_of_an_ordinary_route_is_refused_as_max_bytes` |
| the upload route matched as a prefix | `TestTheUploadGate::test_only_an_upload_takes_a_slot` |
| the busy refusal loses `Retry-After` | `test_the_refusal_carries_retry_after_between_the_length_and_the_correlation_id` |
| the encrypted refusal's message changes by one character | `test_envelope_differential.py::test_every_named_input_gets_the_old_answer_from_every_way_of_being_handed_it[…]` |
| PDFium used without its lock | `test_pdfium_is_only_ever_called_with_its_lock_held` |
| the digest reads the upload whole | `test_no_read_is_unbounded_or_larger_than_one_chunk` |
| the service does not rewind before staging | `test_envelope_through_the_service.py::test_a_handle_is_rewound_where_it_is_staged_whatever_the_probe_left_of_it` |
| the adapter reads the whole body again | `test_envelope_handle_adapter.py::test_the_adapter_hands_the_service_the_handle_it_was_given_and_reads_none_of_it` and `test_portal_block_routes.py` |
| nginx's server default raised to 260m; the bff location loses its cap; the api location loses its rewrite; the TLS api location is 250m; an upload location gains an `add_header` | `test_proxy_rate_limits.py::test_the_upload_locations_alone_take_the_larger_body[nginx.conf|tls-server.conf]` |
| the bff stops streaming (`duplex`); its deadline is 300 s; its body has no deadline | `credentialed-forward.test.ts > a request body is streamed to the API under a deadline` |

## 3. Contracts

**None changed.** `contracts/**`, the migration head, the lock files and `bootstrap/composition.py` are untouched. The busy refusal
uses the classifier `SEAL` registered: `dependency_unavailable` with `details.dependency = "upload_capacity"`, plus a
`Retry-After` header of 5 seconds. The characterization records `18` and `22` changed in what they *send* (record `22` now
declares a `Content-Length` one byte over the upload route's own cap instead of carrying a 26 MiB body); **their responses are
byte-identical** (`git diff` of the two records touches the request side and the `purpose` text only). Records 17, 19, 20, 21 are unchanged.

## 4. Risks and known limitations

- **`PDFIUM_LOCK`.** PDFium is not thread-safe and the upload route runs in a thread pool, so every call into PDFium in
  `envelope.py` holds one process-wide lock. **Any other code in the same process that calls `pypdfium2`** — `W55B-GEOMETRY-01`'s
  clip renderer and `W55B-RECOGNISED-01`'s page reads, if analysis runs in the API process — **must take
  `auditmanager.ingest.envelope.PDFIUM_LOCK`** or import it from a better home. This is the largest hazard this lane leaves.
- **pypdfium2 differences were pinned, not assumed.** The differential test (`test_envelope_differential.py`) runs the committed
  negatives, hand-built PDFs (encrypted with a user password, no pages, an empty page, sizes at the boundary) and
  twenty-five damaged variants (truncations, a header with zeros or prose, seeded byte flips) through the previous implementation, kept in the test as the oracle, and requires identical refusals, field
  for field and message for message. It also proves *leniency only toward accepting*: no damaged input is refused differently or
  refused after being accepted. A document PDFium loads where `pypdf` refused it is therefore accepted — by design, recorded there.
- **A failed load reads PDFium's own error code**, not the library wrapper's "last error": after an earlier upload was refused as
  encrypted, a stale code would say "password" for a document that merely has no pages (`test_a_failed_load_never_borrows_the_last_error_of_an_earlier_one`).
- **The gate is a counter in the process.** One uvicorn process serves a stand (the freeze), so the bound is two per stand; a
  second API process would double it. It never waits: it admits or refuses. A slot is released however the request ends
  (finish, failure, cancellation, disconnect — one test each).
- **The BFF streams any `multipart/form-data` body and any body declared over 1 MiB**; every other body is still read whole. A
  client that sends a streamed upload with no `Content-Length` (what the BFF does) is counted against the same cap as one that
  declares it, and the transport's answer wins over the framework's own 400 once the cap is passed.
- **The deadline of 290 s is shorter than undici's own wait, never longer**; on expiry the BFF answers a synthesized
  `dependency_unavailable` that says the write may have been applied and to resend it with the same idempotency key.
- **The valid-upload memory figure (+37 MiB for 24.85 MiB) was measured once, on one synthetic input.** INGEST must measure the
  accepted 250 MiB bundle.
- The HTTPS `400` on a body-less declared-length probe is an HTTP/2 framing artefact, recorded above rather than hidden.

### Readings where the plan was silent

1. **Retry-After is 5 seconds.** A hint; the refusal is answered before the body is read, so a retry costs nothing.
2. **The upload route is `POST /projects/{uid}/documents` matched whole** (never a prefix, and not `GET` of the collection), so
   no other route takes the larger cap or a slot.
3. **nginx's two upload locations are regex locations declaring no `add_header` and no `proxy_set_header`**, so they inherit the
   server's four security headers (a `location` that adds one drops them all) — proven by the body test above and by
   `test_proxy_security_headers.py`.
4. **`client_body_timeout 120s`** is the gap between two reads of the client's body, not a bound on the transfer.
5. **The measurement uses ports `57421`/`57422`**, next to the lane's `57420`; both were free and are closed.

## 5. Integrator instructions

1. Read the diff and this report; merge `agent/w55b` at the tip named in the hand-back message by fast-forward. INGEST inherits
   `UploadGate`, the per-route cap, the handle-taking `IngestService` and `PDFIUM_LOCK`.
2. **INGEST** raises `MAX_PAGES`/`MAX_BYTES` and the browser precheck, moves the upload cap's partner numbers in
   `tests/e2e/test_upload_limit_headroom.py` (`headroom_problems` reads the chain pre-check < API cap < nginx cap), switches the
   consumers of the committed `oversize.pdf`/`too_many_pages.pdf` to `tools/fixtures/portal_bundle/generated.py`, and measures the
   accepted 250 MiB bundle's time and memory.
3. **Heavy steps still owed: none for this lane.** The full `make gate` is the integrator's, on the final candidate. Nothing here
   needs a night window.
4. **One path outside the grant.** `tests/integration/api/test_portal_block_routes.py` (created by `W55B-SEAL-01`) pinned the
   whole-body read in `DocumentAdapter`; this lane removes that read, so its one test now asserts the service receives the very
   handle the port was given, unread (shown failing when `.read()` returns). The integrator may move that edit to a merge commit.
5. `tests/contract/test_alpha_acceptance_command.py` needs a clean checkout; it passed on the committed tree (part of the 822).

## 6. Containment

- `git diff --name-only 461411b..HEAD`: the 23 paths of §1 before this report, all inside the §B4 list **except**
  `tests/integration/api/test_portal_block_routes.py` (§5.4); this report is the 24th path.
- Not touched: `contracts/**`, migrations, lock files, `bootstrap/composition.py`, `ingest/{commands,reconciliation,…}.py`,
  `multipart.py`'s strict-body rules, the committed negatives, `tools/fixtures/**`, `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`,
  `PORT_REGISTRY.md`, `CURRENT_STATE.md`, refs, tags, the stand, other worktrees, `.local/norms/corpus`.
- No push, no merge, no tag. The lane `.env` is deleted, the lane's containers and its two volumes are gone, the scratch
  `.local/nginx-proof` directory is removed, and `git status --porcelain -uall` is empty after the report commit.
