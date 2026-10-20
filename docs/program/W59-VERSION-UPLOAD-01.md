# W59-VERSION-UPLOAD-01 — upload a further version into an existing document set

Status: **complete** on `agent/w59-version-upload-01`. Phase A was committed alone at
`78ee20bf` (base `641f2b9e` = `origin/dev` `1af17a48` + the frozen task file). Phase B was
built after the integrator handed over the contract slot from `1049367e`, then merged with
`integration/night-1020` at `0f0903f2` (W59-ANALYSIS-SETTINGS-01's `listAnalysisProfiles`, 52/59/153).
Final surface on the merged tree: **53 paths / 60 operations / 154 schemas**. This lane adds one path,
one operation and one schema. Head `0024_version_classification` is unchanged and no error code was
added.

## Phase A — the next version in ingest and documents

**Result.** `IngestService.upload_next_version(project_uid, document_uid, content,
source_filename, idempotency_key)` admits a portal bundle as the next immutable version
of an existing document. It is `upload_bundle` with the document named — not a copy of it
— so the envelope (portal bundle only, ≤ 500 pages / 250 MiB), the custody order (stage,
verify, `verifying` breadcrumbs in one transaction, publish, then blobs `available` +
version + manifest + command outcome in one transaction), reconciliation's breadcrumbs
and the command record are the same code as `uploadDocument`'s.

What the next version does:

- **Next ordinal, pointer moves.** No `document` row is created; the version takes the
  document's next `version_ordinal` and `document.current_version_uid` moves to it in the
  publishing transaction. The project still counts one document; `listDocuments` names the
  new head, `listVersions` lists every version newest first.
- **Inherits nothing.** No title and no section are taken: the document keeps its title,
  `document.section` stays the legacy document-level fact written at the first upload, and
  the new version has no `document_version_classification` row (stage and confirmed
  section absent until an expert confirms them, `W59-SECTION-IDENTITY-DECISION-01`). The
  older version's row, manifest and classification are byte-for-byte unchanged.
- **Idempotency as `uploadDocument`.** Same command type; the fingerprint already names
  the document, so an exact retry (same key, document and bundle) replays the first
  version (`replayed=True`), and the same key spent on another document — or on
  `uploadDocument` — is `idempotency_key_reuse`.
- **Refusals.** An unknown project is `not_found` naming `Project`; an unknown document or a
  document of another project is `not_found` naming `Document`. Both are decided before the
  key is claimed or a byte is staged (the key stays free). Envelope refusals are
  `uploadDocument`'s (a bare PDF: `validation_failed` / `portal_bundle_required`), with no
  version, no command record and the pointer unchanged.
- **Concurrency.** `DocumentRepository.publish_version` now locks the document row
  (`SELECT … FOR NO KEY UPDATE`) before reading `max(version_ordinal) + 1`. Two uploads into
  one document queue on that row and get consecutive ordinals. Before this, both read the
  same ordinal and the second died on `uq_document_version_ordinal` as `internal_error`
  (reachable already through `upload_bundle(document_uid=…)`). `FOR NO KEY UPDATE` is the
  lock the closing `UPDATE document` takes anyway, taken earlier; it does not block other
  transactions' foreign-key checks against the document. The lock also makes the
  repository refuse a missing document as `not_found` instead of a foreign-key fault.

No migration: the schema already expresses a further version (`document_version.
version_ordinal` with `uq_document_version_ordinal`, the mutable `document.
current_version_uid`, classification in its own table).

**Changed files (phase A).**

- `src/auditmanager/documents/repository.py` — `_LOCK_DOCUMENT` and its use in
  `publish_version`.
- `src/auditmanager/ingest/service.py` — `upload_next_version` and the module note.
- `tests/integration/ingest/test_next_version.py` — 11 tests (new).
- `docs/program/W59-VERSION-UPLOAD-01.md` — this report.

**Checks (phase A),** lane `auditmanager-w59-version-upload` (postgres 57550, s3
61150/61151), `PY=…/w55b-main-candidate/.venv/bin/python`,
`PYTHONPATH=src $PY -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider`:

- `tests/integration/ingest/test_next_version.py`: **11 passed**; the concurrency test
  5 × green in a row.
- Mutation probes (each restored with `git checkout`):
  - M1, `_LOCK_DOCUMENT` without `FOR NO KEY UPDATE`:
    `test_concurrent_next_versions_get_consecutive_ordinals` **fails** with
    `DomainError: An unclassified server fault` (the `uq_document_version_ordinal` collision).
  - M2, the `locked is None` refusal removed:
    `test_publishing_into_a_missing_document_is_refused_by_the_repository` **fails** with
    `ForeignKeyViolation … document_version_document_uid_fkey`.
  - The first draft of the concurrency test stayed green under M1: its two bundles shared the
    block-list and markdown blobs, and the shared blob row serialised the two publishing
    transactions by accident. The bundles now differ in every stored member (a stem per
    revision), which is also what real revisions look like.
- `tests/integration/ingest` + `tests/unit/ingest`: **650 passed** (83.8 s).
- Other callers of `publish_version`, read-only: `tests/integration/runs/test_w59_classification_command.py`
  + `tests/integration/composition/test_version_comparison_over_http.py`: **17 passed**.

## Phase B — `uploadDocumentVersion`, the BFF and the document screen

**Operation** (accepted as proposed). `POST /projects/{project_uid}/documents/{document_uid}/versions`,
`uploadDocumentVersion`, tag `documents`, role `expert` (as `uploadDocument`):
`Idempotency-Key` required, `multipart/form-data` with the `file` part encoded
`application/zip`, closed `UploadDocumentVersionRequest` (the bundle only: a `display_title` or
`section` part is `422 additionalProperties`), `201 DocumentVersion` for a new version and for an
exact replay, refusals `401/403/404/409/422/500/503`. A `404` for an unknown document or a document
of another project carries `details.aggregate_type: Document`.

**Edge.**
- The route is declared like `uploadDocument`: `UploadRoute` part bounds, the strict multipart
  pass, the part's handle passed to the port unread. `DocumentPort.upload_document_version` →
  `DocumentAdapter.upload_document_version` → `IngestService.upload_next_version`.
- `_UPLOAD_ROUTE` (`api/routers/multipart.py`) now matches `^/projects/[^/]+/documents(?:/[^/]+/versions)?$`.
  The version upload therefore gets the 251 MiB body cap and takes one of the same two upload
  slots. A path under a version (classification, section review, comparison) gets neither.
- **Proxy (integrator grant).** `infra/deploy/proxy/nginx.conf` and `tls-server.conf` widen their
  two upload locations to the same single optional suffix:
  `location ~ ^/(api|bff)/v1/projects/[^/]+/documents(?:/[^/]+/versions)?$`. Both files are written
  out, not with the alternation shown here. The integrator granted `tls-server.conf` and
  `tests/e2e/test_upload_limit_headroom.py` by message on 2026-10-20; both pin these exact location
  strings, as does `tests/contract/test_proxy_rate_limits.py`. No new location block was added:
  the size, timeout, rewrite and throttle lines are the existing ones.
- **BFF.** `credentialed-forward.ts` already streams every `multipart/form-data` body with
  `duplex: 'half'`, `redirect: 'error'`, `window: null` and the 290 s deadline, whatever the path.
  The new path needed no code. A unit test pins the version path to exactly that treatment.

**Screen.** `/projects/{p}/documents/{d}` now shows «Новая версия» under the version list. It holds
the same «Что принимается» envelope note as the project's upload panel (one `EnvelopeNote`), a
sentence on what carries over (the version becomes current, older versions keep their stage,
section, runs, findings and decisions, the new one inherits nothing), and
`UploadDocumentVersionForm`:
- the picker, «Загрузить новую версию», no title field;
- the same pre-check and the same refusal states through `UploadOutcome`, which is now shared with
  `UploadDocumentForm` (the markup moved, it did not change);
- the intent key is bound to the document and the file.

On success the screen opens `routes.versionClassification(...)`, the new version's
stage-and-section panel. The hook writes `versions.detail` and invalidates:
- `versions.lists(document_uid)`, a new prefix key covering every page of `listVersions`;
- `projects.all()`: the document list and structure, the project detail and the listing;
- `dashboard.summary()`.

The version list's note «Одна версия на загрузку…» was false from this change on; it now says
that every version stays addressable and the newest is current.

**Reseal**, re-derived after the merge with `0f0903f2`:
- contract and `web/openapi/openapi.json` are byte-identical;
- the generated client was regenerated (`api:generate`; `api:verify` OK, 60 operations, contract sha256
  `2dd62b45a6505c7bf9a88fa3b461866b0732656c78a05a77c67c77aec281446d`);
- `FRONTEND_LOCK.json` has new digests and 53/60/154;
- `tests/support/expected_facts.json` has 53 paths, one operation and one schema added.

Surface prose (at 53/60/154) was updated in:
- `P02_SEAMS.md`: count, history sentence, table row, keyed-write list;
- `ALPHA_ROADMAP.md`;
- `infra/deploy/{README.md,serve.py,proxy/nginx.conf}`;
- the API package docstrings, including «Forty-two of the sixty» declaring their own `422`
  and «eighteen of the sixty» that declare none;
- the BFF `route.ts`;
- `shared/api/authorization.ts`.

Test pins moved:
- the `NotFound` reference count, 36 → 37;
- the prose-guard mutations;
- the P02 operation sets;
- the API role and authorization samples;
- the served-422 set;
- the web keyed-write list, ten → eleven;
- the dashboard-invalidation registry;
- the pre-check wiring guard, which now also scans the version form with two mutations.

`docs/manual-tests/CP-06_comparison_core.md` gains `MT06-07`.
`docs/program/CURRENT_STATE.md` is not touched: it still says 52/59/153, which is the one
expected red of `test_doc_prose_facts::test_the_scanned_docs_state_the_contract_surface_this_tree_has`.

**Checks (phase B).** Python with `PYTHONPATH=src $PY -m pytest …`; web with `npx vitest run …`
in `web/`.

| What | Result |
| --- | --- |
| `tests/contract` (whole directory, container-free) | All green except: the known pre-existing reds `test_error_kernel::test_there_are_twenty_four` and `test_ar_v2_seeded::test_seeded_categories_equal_the_sealed_api_enum`; the `CURRENT_STATE.md` triple (integrator's); and environment-only failures of a git worktree: `test_cp00_candidate` (174, `NotADirectoryError` copying `.git`, which is a file in a worktree), `test_validate_bootstrap` (21, `jsonschema` absent from the bootstrap interpreter), `test_cp00_final_state` (3, CP-00 manifest paths and tags). |
| `tests/contract/api_v1` + `domain_p02` (before the merge) | 440 passed, 1 failed (the `CURRENT_STATE.md` triple) |
| proxy: `test_proxy_rate_limits`, `test_upload_limit_headroom`, `test_proxy_tls_path`, `test_proxy_security_headers` | 84 passed |
| `tests/integration/api/test_version_upload.py` (new, lane DB) | 8 passed |
| api + composition subset before the merge: role register, authorization, served document, operation surface, router and body rules, multipart rules, journey, schema conformance, version upload, composition root, token channel, every port, router answers, absent parent, TLS path | 294 passed, 1 skipped, 1 failed: `test_every_port_implementation_is_whole::test_pre_decide_adapter_refuses_a_severity_instead_of_dropping_it`, pre-existing on the base (recorded by `W59-VERSION-COMPARE-01`) |
| after the merge with `0f0903f2`: role register, authorization, served document, operation surface, router and body rules, version upload, multipart rules, composition root, token channel, every port, TLS path, proxy rate limits, upload headroom, journey conformance | 385 passed, 1 failed (the same pre-existing `test_pre_decide_adapter_…`) |
| `tests/e2e/test_pc01_journey_conformance.py` | 87 passed |
| `npm --prefix web run api:verify` / `lint -- --quiet` / `typecheck` | OK / clean / clean |
| vitest `tests/guards tests/unit/screens tests/unit/styles tests/unit/api tests/unit/upload tests/contract` (includes the rendered-language guard), on the merged tree | 54 files, 916 passed |

Mutation probe M3: `_UPLOAD_ROUTE` reverted to `^/projects/[^/]+/documents$` makes three tests fail.
Two are `TestEveryRouteHasItsOwnCap` version-path cases; the third is
`TestTheUploadGate::test_a_version_upload_shares_the_same_two_slots`. The file was restored from a copy.

Not run (R-135): the full gate, the live browser journey (`e2e:pc01`), the whole frontend suite,
the whole integration battery, any provider call.

## Risks and limitations

- **D-174 stays open for this path too.** The BFF's resident set under a real 250 MiB bundle through
  nginx and `next start` is unmeasured. The version upload takes the same code path, so it inherits
  the same open measurement rather than adding a new one.
- **The live journey does not exercise «Загрузить новую версию».** The PC-01 manifest was left
  unchanged, because a step that was never run live would be an unverified handle for the deferred
  full gate. It needs a journey step plus the live run.
- **A byte-identical bundle is admitted as a new version** under a new key, reusing the blobs. That
  is the same rule as `uploadDocument`, and nothing in the task asked to refuse it.
- **`document.section` is still shown on the new version.** It is the legacy document-level fact
  written at the first upload and is not a classification; the new version's `classification` is
  `null`. `D-180` (dashboard grouping by legacy section) is unchanged.
- **One stale comment is outside this task's paths.** `web/src/shared/lib/routes.ts` (`routes.document`)
  still says a document has exactly one version.
- **Pin merges with parallel reseal lanes.** The literal `NotFound` count (37), the
  «Forty-two of the fifty-nine» prose and every surface count were derived on this lane's tree. A
  merge with the parallel lanes (NORMS-CATALOGUE-XLSX, ANALYSIS-SETTINGS, DISPATCHER) must re-derive
  them.

## Integrator instructions

- Merge the branch head. It contains phase A, the reseal and the web slice, merged with
  `integration/night-1020` at the last check.
- Update `CURRENT_STATE.md` to **53/60/154**, the triple on this branch merged with `0f0903f2`.
  If NORMS-CATALOGUE-XLSX or DISPATCHER lands first, re-derive it after the merge.
- Record this as the first upload path for further versions. W59-VERSION-COMPARE-01's
  "further versions are unreachable" limitation is closed.
- No migration, dependency, `providers.tsx`, global style, ref or tag was touched.

## Proposed operation for phase B (as sent to the integrator)

`POST /projects/{project_uid}/documents/{document_uid}/versions`, `operationId:
uploadDocumentVersion`, tag `documents`, the same roles as `uploadDocument`:

- parameters: `Idempotency-Key` (required, as `uploadDocument`), `X-Correlation-Id`;
- request: `multipart/form-data` with the `file` part encoded `application/zip`, exactly as
  `uploadDocument`; the schema `UploadDocumentVersionRequest` is closed and holds **only**
  `file` — a further version takes no `display_title` and no `section`, and accepting and
  ignoring them would be a silent fallback (an undeclared part is the usual
  `additionalProperties` 422);
- `201 DocumentVersion` for a published version and for an exact replay;
- refusals: `uploadDocument`'s `401, 403, 404, 409, 422, 500, 503` (envelope `422`,
  `upload_capacity` `503` with `Retry-After`), with `404` also for an unknown document or a
  document of another project (`details.aggregate_type: Document`);
- the route goes through `UploadRoute` (strict multipart, part bounds, upload capacity) like
  `uploadDocument`.

Surface after phase B: **52 paths / 59 operations / 148 schemas** (one path, one
operation, one request schema).
