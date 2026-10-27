# CMP-INGEST-01 — plain-PDF comparison upload: declare, send in parts, complete, read, propose, confirm, order

Written 2026-10-28 by the Sonnet lane `CMP-INGEST-01` (branch `agent/cmp-ingest-01`, base `bddf340e` on `integration/compare-modules`; nothing pushed, nothing merged). Task file: [`tasks/CMP-INGEST-01.md`](tasks/CMP-INGEST-01.md). Decisions cited are those of [`ADR-0025`](../architecture/adr/ADR-0025-comparison-modules.md) (9, 10, 11, 16 and the addendum of 2026-10-27, item 3); the tables and operations are those of [`CMP-SEAL-C0`](CMP-SEAL-C0.md); the multipart API is [`CMP-STORAGE-PARTS-01`](CMP-STORAGE-PARTS-01.md) section 3.

Eight sealed operations of contract `1.9.0` answer instead of `503`: `createComparisonUpload`, `getComparisonUpload`, `getComparisonUploadProposal`, `uploadComparisonUploadPart`, `completeComparisonUploadFile`, `confirmComparisonUploadSet`, `listComparisonVersionOrders`, `appendComparisonVersionOrder`. The other eleven (six batch operations of `CMP-INGEST-02`, five page reads of `CMP-PROFILE-01`) are untouched stubs. No contract, migration or dependency file changed.

## 1. Base facts, printed before any edit

`git show HEAD:contracts/api/v1/openapi.json` read with `json`: contract `1.9.0`, **115 paths / 130 operations / 351 schemas**, 27 error codes; head `0038_comparison_foundation`; `HEAD` `bddf340e` (the merge of `CMP-STORAGE-PARTS-01`). They equal the premise (task file P-01), so the lane went on. After the lane: `git diff --name-only bddf340e..HEAD -- contracts db pyproject.toml uv.lock web` prints nothing.

## 2. What was built, in the order a file travels

| step | what happens | committed when it ends |
| --- | --- | --- |
| declare | the batch and its files (name, size, SHA-256, optional page count); the limits of decision 9 are refused **before any row exists** | committed with the command record |
| first part of a file | the declared Blob row, the multipart token (write-once) and the part row (`declared`) | **committed before any byte moves** |
| each part | `begin_multipart` (idempotent), `upload_part`; the part row becomes `staged` with size, SHA-256 and ETag | the receipt and the key's outcome, in one transaction |
| completion | the store assembles the parts under a temporary key, reads the object back and compares SHA-256 and size (`before_publish` commits `verifying`); on a match it publishes; the Blob is `available` and the file names it | **committed** |
| reading | the comparison envelope (child 1) and the stamp reader (child 2) over the verified object | nothing; a refusal marks the file `failed` with its reason |
| placement | the file is `verified` and joins the set of its designation (or, with none, its name); when every file of the batch is settled the batch is `proposed` and its sets `needs_confirmation` | **committed** with the command |
| confirmation | one transaction: the document (or the existing one), one `comparison_pdf` version per file in the confirmed order, the classification, the order revision, the set `done`, the batch `completed` when no set is left | **committed** with the command |

### 2.1 The comparison envelope (addendum item 3)

`ingest/comparison_pdf/envelope.py` is a **policy** (`ComparisonEnvelopePolicy`) applied by the **same program** the portal path starts (`ingest/pdf_reader.py`, unchanged), launched by `comparison_pdf/child.py` with the comparison's own figures. `envelope.py`, `pdf_reader.py` and `bundle_archive.py` are not edited (the brief's allowed paths do not include them): the module imports the portal's private `_refusal_for`, `_reader_limits_refusal`, `_refuse`, `_READER` and `PdfFacts` (same bounded context; `test_reading.py` fails loudly if one is renamed), and restates the 40-line launcher because the portal's has its wall clock fixed in the module.

| limit | portal | comparison | basis |
| --- | --- | --- | --- |
| file bytes | 250 MiB | 250 MiB | one bound for every PDF the product stores (R-116) |
| pages | 1 to 500 | 1 to 500 | `ck_document_version_page_count` |
| **page elements** | 400 000 | **1 000 000** | 1.86 times the measured maximum, 536 426 (`MEASURE-RENDER-01` section 3, finding 9: `v1.pdf` p. 7); the portal's figure is 5.3 times *its* maximum (75 486) |
| page characters | 200 000 | 200 000 | unchanged: the real set's text pages are far below it |
| document elements, characters | 8 M, 20 M | 8 M, 20 M | unchanged: the real set's heaviest file is about 2.4 M elements |
| reader address space | 512 MiB | **768 MiB** | decision 8's default; the measurement's `scan` child ran at 768 MiB |
| reader CPU and wall clock | 60 s | **120 s** | the two children run one after the other inside one request, 240 s in all, under the BFF's 290 s |

The text rule is **not** applied (a page with no text layer is admitted and said so: `scan_without_text`), and the second program the portal path starts (`stage_reader`: `pypdf` and `pdfplumber` open the document the way a *run* will) is not started: no run reads a comparison-only version, and the profile children of `CMP-PROFILE-01` read page by page. Every refusal keeps the field, constraint and message of the portal's own, shown equal for encrypted, not-a-PDF, empty, truncated and 501-page inputs.

### 2.2 The stamp reader

`stamp_reader.py` is a program (standard library and `pypdfium2` only, `python -I -B`, a descriptor, a bare environment, `RLIMIT_AS` and `RLIMIT_CPU`, a wall clock on this side): for every page it returns the text that lies in the lower-right 205 x 70 mm of the page **as displayed**, whatever `/Rotate` and `/CropBox` say (the mapping is shown with decoys at the other corners, four rotations and an inset crop box; the displayed-to-native map is taken from PDFium's own `FPDF_DeviceToPage`, not from the lane's formula). `stamp.py` turns the text into facts: designation under «Обозначение»/«Шифр» or by shape, the highest `Изм.N`, the release date (of a sheet carrying that revision), the stage (Cyrillic **П**/**Р** only: a Latin look-alike is a reason to ask, not to guess), the section from the mark that ends the designation (`-ЭМ` → `EOM`; every mark is held to `sections.public.SECTION_CODES`). Control, surrogate and unassigned characters are stripped (a NUL would not survive `text` or `jsonb`).

Read against the answer key of `fixtures/comparison/vs1`: designation `СИНТ-01-ЭМ`; `Изм.0..4` and the dates 15.01, 12.02, 10.03, 07.04, 05.05.2026; 6, 6, 6, 6 and 8 pages; page 4 of V4 and V5 is the scan and contributes no stamp (5 and 7 of the sheets carry the designation).

### 2.3 Proposals (never decisions)

Grouping by designation (a name never overrides one; without a designation the folder, else the base name, and the set says `no_stamp_found`); order by the highest `Изм.`, then the date, then the number in the name, then the name; labels `V{n} Изм.{N} {дд.мм.гггг}`; the five warnings of the contract; the offered `existing_document_uid` (a set an earlier batch confirmed under the same designation, else a document of the project whose title is it; **never applied**: a confirmation that names no document makes a new one). A batch of the five synthetic versions, declared in the wrong order under names whose numbers run backwards, is proposed as one set in the answer key's order with `order_disagrees_with_file_numbers` and `scan_without_text`.

### 2.4 Confirmation

An expert's act (decision 16, checked again in the transaction that acts). Membership must be exactly the set's files (`comparison_set_members`), the stage and the section come together or not at all, an existing document must be the project's. The versions are `comparison_pdf` versions published through `DocumentRepository.publish_version`; the confirmed stage and section classify each one (the first classification of a version stands); the order revision is `proposal` when the confirmed order is the proposed one and `expert` otherwise; the label of each file is kept in the set's confirmed proposal (`ComparisonUploadRepository.version_labels(document_uid)`: a version has no label column).

### 2.5 Decision 11, in `documents` and `runs`

* `document_version.upload_kind` is read by every SELECT of `DocumentRepository` and written by `publish_version(upload_kind=...)`; a comparison version holds none of the portal bundle's counts (typed refusal before the CHECK).
* Its manifest role is the distinct **`comparison.source_pdf`** (blob role `comparison_pdf`), not `source.document`, so the existing start-run manifest check refuses it. `DocumentVersionRecord.source` (the *bytes* accessor: content stream, page reads) answers the `comparison.source_pdf` entry when there is no `source.document`; `entry(MANIFEST_ROLE_SOURCE_DOCUMENT)` stays strict, which is what a run tests.
* **Current version**: `publish_version` moves `document.current_version_uid` to a `comparison_pdf` version **only while the document holds no portal version**, decided once under the document's row lock; a portal version always becomes current. A document made only of comparison versions has the newest of them as its current version (it would otherwise be invisible to `listDocuments`). A test per consumer of the column: the listing, the project document count, the two section memberships, the dashboard, the API's own read path, plus a test that lists every place in `src` that mentions the column, so a consumer added later is a red test until judged.
* **`comparison_only_version`** (`runs/commands.py`): `startRun` and `reauditRun` refuse by the version's kind with `analysis_input_invalid`, reason `comparison_only_version`, **before** the profile is routed and **before** any key is claimed; `_resolve_references` asks the kind too (defence in depth). Over HTTP: `POST /runs` on a comparison version is `422` with that reason.

## 3. The API `CMP-INGEST-02` builds on

Import from `auditmanager.ingest.comparison_pdf.public` (the boundary test refuses deeper paths from other contexts).

```python
ComparisonUploadService(store, *, session_factory=None, read=read_pdf)   # store: BlobStore + MultipartStaging (S3BlobStore)
    .create_upload(project_uid, files: Sequence[DeclaredFileRequest], user_uid, actor_label, idempotency_key) -> UploadView
    .get_upload(upload_id) -> UploadView                    .get_proposal(upload_id) -> ProposalView
    .put_part(upload_id, file_id, part_number, content: bytes, user_uid, idempotency_key) -> PartReceiptView
    .complete_file(upload_id, file_id, user_uid, idempotency_key) -> FileView
    .confirm_set(upload_id, set_id, files: Sequence[ConfirmedFile], designation, existing_document_uid,
                 project_stage, section_code, user_uid, actor_roles, idempotency_key) -> SetView
ComparisonVersionOrderService(*, session_factory=None)
    .list_orders(project_uid, document_uid, before_revision, limit) -> OrderPageView
    .append_order(project_uid, document_uid, version_uids, base_revision_no, user_uid, actor_label, actor_roles, idempotency_key) -> OrderView
ComparisonUploadRepository      # stateless statements on the five tables (every method takes the caller's session)
read_pdf(handle, *, policy=COMPARISON_POLICY) -> PdfReading(facts: PdfFacts, stamp: FileStamp)   # the two children
propose_set(entries) -> SetProposal; FileEntry; ACTIVE_BATCH_STATES; RETRYABLE_FILE_REASONS; parts_needed(size)
require_expert(roles)           # decision 16, for the acts INGEST-02 adds
```

States this lane writes, and the ones it leaves to INGEST-02:

| table | written here | INGEST-02's |
| --- | --- | --- |
| `comparison_upload` | `uploading`, `proposed`, `completed` (when no set is left to act on, or when nothing was admitted to any set) | `processing`, `paused`, `cancelled`, the pause flag; `listComparisonUploads` (the repository has no listing yet) |
| `comparison_upload_set` | `uploading`, `reading`, `needs_confirmation`, `ready`, `admitting`, `done`, `failed` (only `comparison_sets_limit`) | `excluded`; `failed` → `reading`/`ready` (retry) |
| `comparison_upload_file` | `declared`, `uploading`, `verified`, `failed` | the file side of a cancel: `ComparisonUploadRepository.list_files` gives the tokens for `abort_multipart_sweep` after the database is marked |
| `comparison_upload_part` | `declared`, `staged`, `completed`; rows are **deleted** when a failed completion consumed the store-side upload | `aborted` |

A file is `failed` for a *retryable* reason (`comparison_file_sha256`, `comparison_file_size`, `staged_upload_lost`: the client sends it again; the batch stays `uploading`) or a *permanent* one (`content_<constraint>`, e.g. `content_not_encrypted`, `content_declared_page_count`: the same bytes would be refused again; the file counts as settled and the rest of the batch goes on). The reading is **inside the completion request** (two ceilinged children, at most 240 s); the pieces a work handler needs to move it behind a work kind are public (`read_pdf`, the repository, `propose_set`).

## 4. Tests

Commands run from the worktree root with the lane's `.env` loaded, `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q -p no:cacheprovider`:

| Run | Result |
| --- | --- |
| `tests/unit/ingest/comparison_pdf` (no container: the two children run over real PDFs) | **114 passed** = names and limits 23, stamp and proposal rules 50, reading and the envelope policy 41 |
| `tests/integration/ingest/comparison_pdf` (lane's PostgreSQL 17 and MinIO) | **148 passed** = completion 22, confirmation rules and decision 11 25, declaration and limits 22, orders 22, upload flow 18, parts 16, over HTTP 13, run refusal 6, documents rules 4 |
| the two together, one run on the final tree | **262 passed**, 134 s |
| `tests/contract` minus the three `D-220` files, on the clean committed tree | **1307 passed**, 19283 subtests passed (133 s); the same figure the seal and `CMP-STORAGE-PARTS-01` recorded |
| `tests/integration/composition` (whole directory; the three register files this lane edited are in it) | **1909 passed, 3 skipped** (26 min; the skips are the directory's own) |
| `tests/integration/ingest` (the portal path, unchanged by this lane) and `tests/integration/documents` | 780 passed, **1 failed**: `documents/test_version_record_equality.py::test_every_other_field_still_counts_toward_equality`, which is **red on the base `bddf340e` too** (section 6, item 9) |
| `tests/integration/runs -k "idempotency or reaudit or classification_correction or manifest or input_budget"` | 214 passed (these run `start_audit_run` and `reaudit_run`, which this lane edited) |
| `tests/integration/p02_journey/test_manifest_role_seam.py`, `recovery/{test_grant_classification,test_blob_reference_audit,test_comparison_foundation_erase,test_schema_coverage}.py` | 116 passed |
| `git diff --check bddf340e..HEAD` | clean |

Not run, by `R-135`/`R-126`: the live journey, the full gate, any suite whose context this lane did not touch. The over-HTTP suite (`test_http.py`) drives the composed application (`create_app`) against the lane's own database and bucket: declare, parts, completion, proposal, confirmation, the document and its content stream, the order, an administrator without `expert` refused, `POST /runs` on a comparison version refused.

## 5. Mutation proofs

Each row: the one-occurrence replacement applied to the committed file, the named tests run (red), the file restored with `git checkout --`, `git status --short` empty, the same tests run again (green). The harness and the 52 specifications are the lane's scratch (`mut.py`, `specs.py`, `specs2.py`); every row below was run on the final code of its guard.

| id | mutation | red | restored |
| --- | --- | --- | --- |
| M1 | comparison page-element limit set back to the portal's 400 000 | 2 failed | 2 passed |
| M2 | the portal's text rule applied to a comparison PDF | 1 failed | 1 passed |
| M3 | a quarter-turn page read in its unrotated lower-right corner | 3 failed, 9 passed | 12 passed |
| M4 | the version's revision is the lowest sheet's, not the highest | 5 failed, 4 passed | 9 passed |
| M5 | a name overrides a designation in the grouping | 3 failed, 2 passed | 5 passed |
| M6 | proposal order ignores the revision | 2 failed, 8 passed | 10 passed |
| M7 | files limit raised by one | 2 failed, 4 passed | 6 passed |
| M8 | project bytes limit not applied | 3 failed, 2 passed | 5 passed |
| M9 | name-group sets limit not applied | 2 failed, 1 passed | 3 passed |
| M10 | active batches not counted | 3 failed, 2 passed | 5 passed |
| M11 | the creation lock removed (two requests may both take the slot) | 1 failed | 1 passed |
| M12 | the part row (its database owner) is not written before the bytes move | 3 failed | 3 passed |
| M13 | the token is not persisted before the first part | 6 failed | 6 passed |
| M14 | a part in the middle of a file may be any length | 1 failed, 1 passed | 2 passed |
| M15 | a part number beyond the declared size is accepted | 2 failed, 1 passed | 3 passed |
| M16 | the same part is sent to the store again | 1 failed, 2 passed | 3 passed |
| M17 | a key reused for other bytes is not refused | 2 failed | 2 passed |
| M18 | the failed file keeps its part rows | 3 failed, 3 passed | 6 passed |
| M19 | an integrity failure does not mark the file failed | 3 failed, 3 passed | 6 passed |
| M20 | a refused document keeps the batch from being proposed | 2 failed, 8 passed | 10 passed |
| M21 | a completion with parts missing goes to the store | 1 failed, 1 passed | 2 passed |
| M22 | the stamp grouping is not held to the sets limit | 1 failed | 1 passed |
| M23 | a confirmation need not list exactly the set's files | 4 failed, 5 passed | 9 passed |
| M24 | the expert's act is not checked by the command (confirm and order) | 2 failed, 2 passed | 4 passed |
| M25 | a stale base revision is accepted | 3 failed, 1 passed | 4 passed |
| M26 | an order may omit, repeat or invent a version | 5 failed | 5 passed |
| M27 | the order lock removed from the append (stale check and insert split) | 1 failed | 1 passed |
| M28 | decision 11: a comparison version becomes current whatever the document holds | 5 failed, 5 passed | 10 passed |
| M29 | documents read the kind as portal whatever the row says | 1 failed, 6 passed | 7 passed |
| M30 | the bytes accessor does not know the comparison role | 2 failed | 2 passed |
| M31 | a new reader of current_version_uid appears unjudged | 1 failed | 1 passed |
| M32 | the comparison_only_version refusal removed | 5 failed, 1 passed | 6 passed |
| M33 | the refusal asked after the profile is routed (order of the guard) | 1 failed | 1 passed |
| M34 | the page-character ceiling not passed to the reader | 1 failed | 1 passed |
| M35 | the oversize check removed from the comparison envelope | 1 failed | 1 passed |
| M36 | the stamp child runs without its ceiling | 1 failed | 1 passed |
| M37 | the served adapter answers a stub again | 2 failed, 7 passed | 9 passed |
| M38 | a written table left in SEALED_NOT_YET_WRITTEN | 2 failed, 33 passed | 35 passed |
| M39 | a Latin P read as the project stage | 1 failed | 1 passed |
| M40 | an impossible year read as a date | 1 failed, 2 passed | 3 passed |
| M41 | a sub-document joins a parent that is rare | 1 failed, 1 passed | 2 passed |
| M42 | control characters of a hostile stamp are kept | 1 failed | 1 passed |
| M43 | the child inherits the API's environment | 1 failed | 1 passed |
| M44 | the confirmed classification is not written | 1 failed | 1 passed |
| M45 | an accepted order is recorded as the experts | 1 failed | 1 passed |
| M46 | the order of a joined document forgets its earlier versions | 1 failed | 1 passed |
| M47 | the existing document is never offered | 2 failed | 2 passed |
| M48 | a batch whose sets are all done is left proposed (it would hold its slot) | 1 failed | 1 passed |
| M49 | a comparison version may carry the portal bundle's counts | 1 failed | 1 passed |
| M50 | a kind outside the two is accepted | 1 failed | 1 passed |
| M51 | the reference check does not ask the kind | 1 failed | 1 passed |
| M52 | a display name with control characters is stored as sent | 2 failed | 2 passed |

Not provable by mutation: "an order never changes `version_ordinal`" is structural (the column is immutable, and the append writes no `document_version` row); it is pinned as a regression by `test_the_documents_ordinal_never_changes`.

## 6. Risks and known limits

1. **The reading is inside the completion request.** Two ceilinged children, 120 s each, so a completion of a 500-page 250 MiB document can take up to 240 s (under the BFF's 290 s) and a heavier one is refused `pdf_reader_limits`. The real set (26 pages) is read in seconds. The 250 MiB object is spooled to a temporary file in the API container while it is read (the portal path spools the same size). `CMP-INGEST-02` may move the reading behind a work kind; `read_pdf`, the repository and `propose_set` are public for that.
2. **A content-refused file leaves its published blob.** The store offers no delete of a published blob (decision 9), so a PDF the envelope refuses (encrypted, over a ceiling) has been verified and published before it is read; the failed file row names the blob (so the unreferenced-blob audit stays quiet) and its bytes count toward the project's 8 GiB. The portal path refuses before it stores because it holds the bytes; a multipart object exists only in the store.
3. **A file that failed its integrity keeps the batch `uploading`.** A wrong *declaration* (a size that is not the object's) can never be sent right, because the declaration is frozen: the batch cannot be proposed and only `CMP-INGEST-02`'s cancel frees the account's one active slot. A batch in which every file was refused for good is `completed` at once (nothing to confirm).
4. **`proposed` batches count as active.** One per account and two per installation include a batch that is waiting for its set to be confirmed; an expert who walks away holds the slot until the sets are confirmed or `CMP-INGEST-02` cancels the batch.
5. **Limits at declaration are on names, at placement on stamps.** The contract's "a batch that groups into more than 100 document sets" is checked at declaration on the folder or base name of each file (the stamps are not read yet) and again when files are placed: the 101st stamp group becomes a set `failed` with `comparison_sets_limit`, never merged into another. A batch of 100 name groups can still hold 101 stamp groups.
6. **Labels live in the set.** A version has no label column; the label of each version is in the confirmed proposal of the set that made it (`ComparisonUploadRepository.version_labels(document_uid)`). A lane that shows labels reads it from there or asks for a column (a migration, not this lane's).
7. **Unregistered reason strings.** The lane could not edit the contract's notes, so these values are used but not listed there: `validation_failed` / `files` / `display_name` (a name made only of control characters), / `project_stage` or `section_code` / `required_together`, / `page_count` / `declared_page_count`, `validation_failed` / `parts` / "ascending part numbers from 1 with no gap and no repeat" (the storage wording, for a completion with a part missing), and the file `failure_reason` values `comparison_file_sha256`, `comparison_file_size`, `staged_upload_lost` and `content_<constraint>` (free text up to 128 characters in the schema). The registered ones (`comparison_*` limits, `comparison_part_number`, `comparison_part_size`, `comparison_set_members`, `comparison_upload_active`, `comparison_upload_state`, `comparison_set_state`, `comparison_version_order_stale`, `comparison_only_version`) are used exactly as registered; `comparison_set_members` is also what an order that does not list the document's versions exactly once answers (field `version_uids`).
8. **The group start refuses a comparison version by the manifest role, not by the kind.** `runs/v3_group.py` is outside this lane's paths. Its existing check (`source.document` absent) already refuses the version, but with `missing_required_input` (and an unclassified one first with `version_classification_required`), not `comparison_only_version` as the contract's note promises. One line there fixes it: `refuse_comparison_only_version(version)` (exported from `runs/commands.py`) right after `DocumentRepository().get_version(...)` in `start_ar_v3_group`.
9. **A pre-existing red outside the lane's paths.** `tests/integration/documents/test_version_record_equality.py::test_every_other_field_still_counts_toward_equality` pins the set of compared fields of `DocumentVersionRecord` and fails on the base `bddf340e` (the seal added `upload_kind` to the record and no suite of its list runs that directory). The fix is one line in that test's `changed` mapping: `"upload_kind": "comparison_pdf",`. It is left to the integrator (the file is not this lane's).
10. **Replacing a staged part.** Sending a part again with the same bytes replays its receipt; with other bytes it replaces the part (the whole file is verified at completion). A wrong last part is therefore found at completion, as `comparison_file_size` or `comparison_file_sha256`, as the contract says.
11. **A name is never an identity, and two files may share one.** Two files declared with the same name are two files; two batches may declare identical content (two versions with one blob).

## 7. Instructions for the integrator

1. **Merge position:** `WORK → STORAGE-PARTS → SPEND → EXEC-IMAGES → INGEST-ZIP → INGEST-01 → INGEST-02 → PROFILE → VERSION-MARK`. This lane's hunks in shared files, to be resolved in that order: `bootstrap/adapters.py` (the two adapter classes and the mapping helpers; the six `CMP-INGEST-02` stub methods are kept in `ComparisonUploadAdapter`), `bootstrap/composition.py` (one import and the two constructor lines: `ComparisonUploadAdapter(sessions, service=ComparisonUploadService(store, session_factory=sessions))` and `ComparisonVersionOrderAdapter(sessions, service=ComparisonVersionOrderService(session_factory=sessions))`), `scripts/recovery/grant_classification.py` (five tables leave `SEALED_NOT_YET_WRITTEN`), and three composition tests (`SEALED_STUB_GETS` loses three paths, `SEALED_STUB_ADDRESSED` loses three operations, and `test_comparison_stub_operations.py` gains `WIRED`/`STUBS`: the next lane to wire an operation adds it to `WIRED`). `EXPECTED_ADDRESSED` is unchanged (it counts all addressed reads, wired or not).
2. **`INGEST-02`** builds on section 3. It writes the states the table there leaves to it, calls `abort_multipart_sweep` for the files of a cancelled batch after marking the database, and must remove nothing from `SEALED_NOT_YET_WRITTEN` (the five tables are already out).
3. **Contract notes** (a seal/FIX slot, not this lane): register the reason strings of limit item 7.
4. **One-line fixes outside this lane's paths:** limit items 8 (`runs/v3_group.py`) and 9 (`test_version_record_equality.py`).
5. **Compose and settings:** nothing new. The module flag (`AUDITMANAGER_COMPARISON_MODULES`) does not gate these operations yet (the seal's report item 10; `CMP-WORK-01` and the screens use it); with the flag `none` an expert can still declare a batch through the API.
6. **Image size and disk:** no dependency changed. The completion spools one object (at most 250 MiB) under the API container's temporary directory while it is read; size that directory for it (`PROD-05a`).

## 8. Forbidden hotspots

`git diff --name-only bddf340e..HEAD` lists exactly: the task file and this report; `src/auditmanager/ingest/comparison_pdf/**` (new); `src/auditmanager/documents/{README.md,__init__,models,public,repository}.py`; `src/auditmanager/runs/commands.py`; the wiring hunks (`src/auditmanager/bootstrap/{adapters,composition}.py`, `scripts/recovery/grant_classification.py`, `tests/integration/composition/{test_router_answers,test_an_absent_parent_is_not_an_empty_page,test_comparison_stub_operations}.py`); and the lane's tests under `tests/unit/ingest/comparison_pdf/` and `tests/integration/ingest/comparison_pdf/`. No file of `contracts/**`, `db/migrations/**`, `pyproject.toml`, `uv.lock`, `web/**`, `src/auditmanager/ingest/{envelope,pdf_reader,bundle_archive}.py`, `src/auditmanager/storage/**`, `src/auditmanager/comparison/**`, `src/auditmanager/runs/v3_group.py`, `api/routers/**` or any `conftest.py` outside the lane's own directory. `api/routers/ports.py` and the two router files are **unchanged**: the port signatures already carry what the service needs (the adapter reads the actor's label and roles in the transaction that acts), and the router's part body (at most 16 MiB as bytes) is kept because the storage port holds one part in memory anyway.

## 9. Environment

Stack `auditmanager-cmp-ingest-01` (PostgreSQL `57760`, MinIO `61760`/`61761`, database `auditmanager_cmp_ingest_01`, bucket `auditmanager-cmp-ingest-01`), started with `make up` and stopped with `make down` (then its two named volumes removed by name); `.env` on the lane only (git-ignored); `df -h /` before the start (2.8 G) and before every long run, never below 2.4 G; the stop line is 1.5 G. The shared `cmp-seal-c0` environment was used read-only (`.venv`); no process of another lane was touched.
