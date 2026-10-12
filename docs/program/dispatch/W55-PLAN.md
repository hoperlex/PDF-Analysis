# Wave 55 — split: W55a the corpus on the stand and text search; W55b portal bundles and «Блоки»

**Status:** revision 5, 2026-10-12, branch `plan/corpus-chain`. It applies the chain judging round
(`reviews/W54-W57-CHAIN-JUDGING.md`) under the integrator's decisions CD-15…CD-21
(`reviews/W54-W57-CHAIN-REVIEW.md` §4). The plan's history lives in those two records (CD-20).
**Base:** `origin/dev` `4fe7615`; `origin/main` `2653dbf`, tagged `v0.4.0` (W53, R-86); migration head
`0017_execution_queue`; API `1.0.0-draft.1` (36 paths, 43 operations, 91 schemas); `VERSION=0.4.0`.
‡ marks a pin in a file W53-CLOSE changed (`3aeb75a`); every pin was re-measured on `4fe7615`, and
`W55A-FREEZE-01` re-runs `pin_sweep.py` on its own base.
**Controlling answers:** `ROADMAP-TO-BETA.md` §10.12 (F-2, F-4…F-10), §10.13 (G-1…G-12), §10.16
(K-1…K-12); rulings R-77 (backup in a beta wave), R-80 (role-less accounts read no product data), R-82
(re-audit on the current configuration), R-83 (MinIO image), R-86 (0.4.0 released, 0.3.0 kept as a history
row). `R-Y1`…`R-Y8` are placeholders for the labels after W54's `R-103`…`R-107`, assigned by each half's
`*-RULE-01`.
**Two waves (G-9)**, each with its own rule, freeze, seal, judges, close and release. Releases follow
§8.4 as R-86 applies it: a release needs its predecessor deployed and tagged and its own exact-SHA gate.
W55a's target `v0.6.0` follows W54's `v0.5.0`; W55b's `v0.6.1` follows W55a. Migrations: `0020_norms_search`
(W55a), `0021_portal_bundles` (W55b), re-assigned at each freeze if a predecessor changes (CD-2). The order
is A then B; a reverse order needs a reviewed amendment re-assigning migrations, versions, grants and W56's
head. **Not here:** region evidence (W56, G-8). **A-7:** whether «Настройки анализа» lands in W55 or W56b is
settled at `W55A-RULE-01`; W55 has no preset path today.

**The road to the stand (CD-3, CD-15, CD-16).** Each act needs a direct owner instruction naming its SHA
or bundle.

| Step | Act | State |
| --- | --- | --- |
| P1 | R-83's MinIO swap | done with W53's publication (K-12: no copy); its client-object read-back moves to P2 (`verify-objects`) |
| P2 | W54 code, `0018`/`0019`, the stand tools | `W54-INT-MAIN-01` |
| **P3** | **`W55A-INT-MAIN-01`**: W55a code and `0020`, no corpus bytes | §A4 |
| **P4** | **`W55A-STAND-IMPORT-01`**: the corpus written to the stand | §A7 |
| P5 | W57a's retrieval-set build | W57 |

---

## Part A — W55a: the corpus on the stand and text search (target `v0.6.0`)

### A1. Objective

On one deployed SHA: the repaired snapshot with its complete BGE build (G-1) imported through W54's tools
after K-1's copy, crops included; an administrator account the owner names (the owner may be that administrator) designates the **current snapshot** and every new run
and re-audit pins it (G-6, R-82); **text search** with Russian morphology and designation/clause lookup
(G-5); «Нормы» opening the norm PDF at its page; documents and norms **streamed** with byte ranges; the
`D-124` real-vector measurement. A copied bundle or rows without a complete build is not the outcome.

### A2. Where it starts (`origin/dev` `4fe7615`)

| Fact | Source |
| --- | --- |
| no free-text query parameter; listings paginate over a sort-key cursor | `contracts/api/v1/openapi.json:2643-2652, 3064`; `api/schemas/common.py:57-148` |
| `norm_document` has `slug`, `title`, `doc_type`, no designation; `СП_542_1325800_2024` sits beside `СП_54_…` | `0012:84-122`; `MANIFEST.json` |
| `norm_paragraph.page_label` is the true 1-based PDF page number; W54 adds `text_reliability` | `0012:138-172`; `norms/segmentation.py:55-66` |
| `streamDocumentVersionContent` loads the whole object for a `Range`; `WireResponse` takes `bytes` only; the BFF drops `Range`, `Content-Range`, `Content-Length` | `api/routers/documents.py:209-235`; `api/routers/wire.py:49-71`; `api/routers/ports.py:189`; `web/src/shared/api/credentialed-forward.ts:47-66` ‡ |
| a full read hashes the whole object against the manifest | `ingest/service.py:207-258` (hash 249-257) |
| `audit_run.norms_snapshot_id` is always NULL; the frozen-input digest omits it | `0002:670`; `runs/commands.py:94-142` ‡ |
| `reaudit_run` stamps the current profile, bundle, mode and digest (R-82) but carries the **source's** snapshot over; its fingerprint is the source run plus the source's digest | `runs/commands.py:352-432`, `:381-384`, `:426` ‡ |
| product reads use `_ANY_ROLE`; `role:admin\|expert` refusal; screens use `'any-role'`; `/norms` is a stub row | `api/security.py:292-297, 312-361` ‡; `tests/integration/api/test_role_register.py:43-84, 97-138` ‡; `screen-registry.ts:73, 175` ‡ |
| guards a new operation meets: `PORT_FOR_ARGUMENT`; `EXPECTED_ADDRESSED = 12`, `EXPECTED_UNADDRESSED = 10` and `_absent_identity` (path parameters must be `identifiers.json` keys: `norm_document_id`, not `ndoc_id`); `test_router_answers.py`; the subject-reader list; the R-66 stubs | `composition/test_every_port_implementation_is_whole.py:41`; `composition/test_an_absent_parent_is_not_an_empty_page.py:74-75, 111`; `identifiers.json:50`; `api/test_authorization.py:689-702`; `web/tests/unit/qa_w50/r66-navigation.test.ts:83-86, 225-245` |
| PostgreSQL derivative with pgvector 0.8.6; the HNSW index exists, so the import inserts into a live index | `compose.server.yml:61-67`; `0013:172-174` |
| a revert deploy after a migration fails the migrations-at-head guard | `infra/deploy/deploy.sh:720-744` |
| the stand: `2653dbf`, head `0017`, MinIO `2025-10-15` recreated without read-back; capacity never measured | `W53-INT-MAIN-01.md`; `readiness.sh` |
| corpus 674 PDFs (712 MB) + 28 246 crop PDFs (4.04 GiB); this host 14.1 GB free (2026-10-12, `df -B1 /`); available RAM fluctuated between 2.6 and 7.3 GiB that day | `MANIFEST.json`; measured |

### A3. Design

**A3.1 Build and import.** The input is W54's verified bundle with `build: present`; EMBED's resumable
`build` runs here in night windows (CD-11). The build is on the critical path: without it no snapshot
qualifies (§A3.2), none can be current, and search refuses. A missing build is finished by §C0's
`W55-PROMOTION-PRE-01` with W54's command, then re-exported and re-verified. The import is only §A7 (P4).
W55a writes no build, transport, copy or import code.

**A3.2 Current snapshot (G-6).** `0020` adds `norm_current_snapshot` (one row) and
`norm_current_snapshot_event` (append-only: actor, from, to, time; triggers refuse update and delete).
`setCurrentNormSnapshot {norms_snapshot_id, expected_current}` refuses a stale `expected_current`
(`conflict`, `conflict_reason: stale_current_snapshot`) and answers an already-current target as a replay.
A target **qualifies** only with (a) a complete `bge-m3-dense-v1` build (D-127) over W54's
reliability-aware chunks and (b) a confirmed `norm_source` binding for every document's PDF (W54 custody);
otherwise `required_norm_unavailable`. That the rows and the build equal the manifest is **procedural**: it
is proved by `report <key>` exiting 0 before any designation (§A7), not by the setter. There is no unset; a
wrong current snapshot is replaced by another qualifying one. Command, reader `current_snapshot()` and
predicate live in `src/auditmanager/norms/current_snapshot.py`, exported through `norms/public.py`; W57a
extends the predicate there. Role `admin`.

**A3.3 Run pinning (G-6, R-82, CD-6).** `startRun` and `reauditRun` read the current snapshot through
`norms.public.current_snapshot()` inside the run-creating transaction and write
`audit_run.norms_snapshot_id`; PIN replaces the carry-over of §A2. Profile, bundle and mode stay
caller-supplied configuration; the snapshot is database state, read in the transaction.
- `input_basis_digest` is today's computation and never holds the snapshot; the stored
  `frozen_input_digest` is the basis plus the snapshot when not NULL. `start_run_fingerprint` takes the
  basis only; both idempotency fingerprints are unchanged, so a retry after a designation change replays.
  Tests: a pinned run's two values differ; a NULL run's are equal.
- With none current, both pin NULL (CD-6, decided): no stage reads norms before W57, and "none current"
  exists only before the first designation. W57a turns a norms-reading start or re-audit without a usable
  snapshot into `required_norm_unavailable` (CD-19).
- `RunStatus` gains an optional `norms_snapshot_id`.

**A3.4 Text search (G-5).**
- **Stored vector:** `0020` adds `norm_paragraph.text_tsv tsvector GENERATED ALWAYS AS
  (to_tsvector('russian', text)) STORED` and a partial GIN index `WHERE text_reliability = 'reliable'`
  (F-4). W54's canonical row digest covers declared columns only; the importer never writes a generated
  column.
- **Designation key:** `0020` adds `norm_document.designation_tokens text[]`, generated by the `IMMUTABLE`
  SQL function `norm_designation_tokens(text)`: the slug before `__`, split on `[ ._-]`, case and
  Latin/Cyrillic homoglyphs folded by explicit `translate` tables (never `lower()`; a test asserts the
  ctype). The query's designation part goes through the same function and matches when its tokens equal
  the key's leading tokens: «ГОСТ 10140» finds `ГОСТ_10140-2003`; «СП 54» finds `СП_54_13330_2022`, never
  `СП_542_…`.
- **Query:** `q` of 1–200 characters → optional designation, optional clause (`п. 7.1.4`; a dotted-segment
  prefix on `clause_number`) and words (`websearch_to_tsquery('russian', …)`), ranked by `ts_rank_cd`;
  designation- or clause-only queries order by designation, then `ordinal`.
- **Scope:** the current snapshot; none current → `required_norm_unavailable`. An explicit
  `norms_snapshot_id` is accepted only for a snapshot that has been current at least once (a `to` in the
  history), else the same refusal.
- **Result:** snapshot id, `ndoc_`, `npar_`, designation, title, `doc_type`, clause, `page_label`,
  `block_ref` and `ts_headline` of the canonical paragraph text (NORM-Q01), plain text with offsets.
  Unreliable paragraphs never appear.
- **Cursor:** opaque; the hash of (`q`, snapshot) plus the ordering position (rank as exact `float4` bits
  and `npar_`; or designation tokens, `ordinal`, `npar_`); refused with another query or snapshot. Window
  capped at 1 000.
- **Timeout:** `statement_timeout` from the operator setting `AUDITMANAGER_NORMS_SEARCH_TIMEOUT_MS`
  (`bootstrap/settings.py`; default fixed at the freeze from the promotion database; the stand value is
  set by the owner in the host-owned `provider.env` on the integrator's rehearsal figure). A cancelled
  query answers `validation_failed`, `constraint: norms_search_too_broad`, never an empty or partial page.

**A3.5 Streaming with ranges.** SEAL adds `StreamingWireResponse` to `api/routers/wire.py` (the exact
header list of `WireResponse`, an iterator body). `streamDocumentVersionContent` and
`streamNormDocumentContent` stream from S3 in chunks and honour one `Range` (`206`, `Content-Range`); an
unsatisfiable range keeps `422`. The BFF passes `Range` up and `Content-Range`, `Content-Length`,
`Accept-Ranges` down; the viewer keeps `<object>#page=N`.
- **Integrity (`R-Y4`).** A full `200` hashes while streaming and **holds back its last chunk** until the
  digest matches; on a mismatch it aborts, so the client receives fewer bytes than `Content-Length`, and
  logs `storage_integrity_error`. A `206` relies on recorded verification (publication and
  `verify_version`). Tests: a tampered object on both paths, asserting the short body.
- S3 is opened before the response starts, so a storage failure stays a typed `500`; records 14, 15, 31
  keep `Content-Length` and the header order.

**A3.6 Operations (the seal confirms names).**

| Operation | Method / path | Roles |
| --- | --- | --- |
| `searchNorms` | `GET /norms/search?q=&norms_snapshot_id=&cursor=&limit=` | `_ANY_ROLE` |
| `getNormDocument` | `GET /norm-documents/{norm_document_id}` | `_ANY_ROLE` |
| `listNormParagraphs` | `GET /norm-documents/{norm_document_id}/paragraphs` | `_ANY_ROLE` |
| `streamNormDocumentContent` | `GET /norm-documents/{norm_document_id}/content` (Range; confirmed binding only) | `_ANY_ROLE` |
| `listNormSnapshots` | `GET /norms/snapshots` (id, key, counts, build state, `qualified`, `current`) | `_ANY_ROLE` |
| `listNormSnapshotEvents` | `GET /norms/snapshots/events` | `_ADMIN` |
| `setCurrentNormSnapshot` | `PUT /norms/snapshots/current` | `_ADMIN` |

No new error code (CD-19): `required_norm_unavailable` with `reference_kind` values the seal adds,
`conflict` with `conflict_reason: stale_current_snapshot`, `validation_failed` with
`constraint: norms_search_too_broad`; the seal confirms the values under the error register's rule and
writes the new operations' roles into their contract text (`D-151` stays with W58). Every response carries
NORM-Q04's attribution; the corpus stays internal (D-4.1).

**A3.7 «Нормы».** The R-66 stub graduates: search; results with designation, clause, fragment and
«открыть» (the PDF at `page_label`); a document view (second registry row) with unreliable paragraphs
marked; for administrators the snapshot list, «сделать текущим» and the history. Before P4 it renders the
"no current snapshot" refusal, never an empty list.

**A3.8 Deferred.** The `norms.snapshot` registry contradiction is fixed in W57 by a digest-pinned
retrieval-set artefact; W55a registers it only.

### A4. Tasks

**`W55A-RULE-01`:** `R-Y1` text search on «Нормы», semantic retrieval inside analysis (G-5); `R-Y2` the
current snapshot, its history and qualification; runs and re-audits pin it, NULL until W57 (R-82, CD-6);
`R-Y3` the split (G-9); `R-Y4` streamed and ranged integrity. It proves that every `expert` and `admin`
account is within the approved internal audience (D-4.1) before P4, and settles A-7.

**`W55A-FREEZE-01`:** standard form, plus: base `4fe7615` or later; W54 merged and `W55-WORKER-01`
finished — **the freeze refuses otherwise**; `W55-PROMOTION-PRE-01` scheduled before D124 and REHEARSAL;
`0020_norms_search`; `pin_sweep.py` for `reseal-surface migration table route error-code`; the timeout
default; the two screen rows; ports; §C6's disk formula with fresh `df -B1` and `free -b`.

**Stage A** (from the freeze SHA):

- **`W55A-SEAL-01`** (full gate) — the seven operations with refusing stubs (§A3.6),
  `RunStatus.norms_snapshot_id`, `0020` (§A3.2, §A3.4), the error-register values, `NormsSearchPort`,
  `NormContentPort`, the chunked `DocumentPort.stream_content`, `StreamingWireResponse`, the role entries,
  the guards' literals, the four-document reseal and the facts file. **Allowed** (written out; no inherited
  W53 qualifier):
  - `contracts/**` (the W55a seal; other declarations review-only); `db/migrations/versions/<date>_0020_norms_search.py` (new);
  - `src/auditmanager/api/**`: `routers/norms.py` (new, stubs), `routers/wire.py`, `routers/ports.py`,
    schemas, `security.py` (seven entries) ‡, surface prose; `app.py` surface pins only;
  - `src/auditmanager/bootstrap/{adapters,composition}.py` ‡ (stub wiring); `src/auditmanager/shared/errors/{codes,catalog}.py`; the head constants of `shared/db/**`, `shared/statemachine/topology.py`, `documents/refusals.py`, `storage/check.py`;
  - `web/openapi/openapi.json`, `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json`, `web/src/shared/api/catalog-message.ts`, `web/src/entities/audit-run/model/terminal-reason.ts`;
  - `tests/contract/**`, `web/tests/contract/**`, `web/tests/guards/**` (W55a assertions only);
    `tests/integration/{api,auth,db}/**` (incl. `test_role_register.py` ‡ and `test_authorization.py`'s
    subject-reader list, which gains `norms.py`); `tests/integration/composition/{test_composition_root,test_every_port_implementation_is_whole,test_an_absent_parent_is_not_an_empty_page,test_router_answers}.py`;
    `tests/integration/api/test_streaming_wire_response.py` (new);
  - exact pins: `tests/support/expected_facts.{json,py}`, `tests/e2e/pc01/test_acceptance.py`,
    `tests/e2e/pc01/journey/manifest.json`, `tests/integration/p02_journey/journey.py`,
    `tests/integration/foundation/test_cross_provider_publication.py`;
  - prose: `docs/program/{CONTRACT_PIN_REGISTRY,P02_SEAMS,CURRENT_STATE,ALPHA_ROADMAP}.md`,
    `docs/manual-tests/{PC-01_prototype,README}.md`, `infra/deploy/{README.md,serve.py}`,
    `infra/deploy/proxy/nginx.conf`, `src/auditmanager/api/README.md`; `docs/program/W55A-SEAL-01.md`;
  - every path `pin_sweep.py` prints (its `table` event finds the count pins `0020`'s two new tables
    move); review-only: `web/src/shared/config/screen-registry.ts` and `web/src/shared/lib/routes.ts`
    (WEB-NORMS writes them).

  Required: fresh upgrade; upgrade from `0019` with norms rows (generated columns filled, declared-column
  digest unchanged); refused downgrade with retained data; `make gate`.
- **`W55A-D124-MEASURE`** (after PROMOTION-PRE; night; promotion database): recall@10 of the iterative
  scan against an exact scan and p95 on the real build; the two-snapshot case only if W54's build reuses
  identical windows' vectors. Allowed: `docs/program/reviews/W55A-D124-MEASURE.md`, `scripts/probes/w55a/**`.

**Stage B** — sequential, each from the previous merge; check levels in §C6.

1. **`W55A-CONTENT-01`** (§A3.5; full gate) — `src/auditmanager/storage/{s3,public,port,__init__,durable_publication}.py`;
   the storage-protocol fakes `tests/integration/ingest/test_reconciliation_reads_the_bytes.py` and
   `tests/integration/runs/test_a_halted_chain_reaches_a_terminal.py`; `tests/integration/api/test_range_rules.py`;
   `tests/integration/storage/**`; `src/auditmanager/ingest/service.py` (the read path's integrity rule);
   `src/auditmanager/api/routers/documents.py` (content body); `src/auditmanager/bootstrap/adapters.py` ‡
   (`DocumentAdapter.stream_content`); `web/src/shared/api/credentialed-forward.ts` ‡; `web/tests/unit/api/**` ‡;
   `tests/integration/api/test_document_content*.py` (new); `docs/program/W55A-CONTENT-01.md`. Required: a
   ranged read never loads the object; `206`/`422`; the held-back last chunk and the short body on a tampered
   object; records 14, 15, 31 byte-identical; the BFF in both directions.
2. **`W55A-SEARCH-01`** (§A3.2, §A3.4, §A3.6; full gate) — `src/auditmanager/norms/search/**` (new);
   `src/auditmanager/norms/current_snapshot.py` (new); `src/auditmanager/norms/{public,__init__,repository}.py`
   (export lines and reads; `public.py` is W54's); `src/auditmanager/api/routers/norms.py` (bodies);
   `src/auditmanager/bootstrap/{adapters,composition,settings}.py` (adapters ‡; the timeout setting);
   `tests/integration/composition/{test_router_answers,test_an_absent_parent_is_not_an_empty_page,test_settings_defaults}.py`;
   `tests/integration/norms/search/**`, `tests/integration/norms/test_current_snapshot*.py` (new);
   `docs/program/W55A-SEARCH-01.md`. Required: morphology; designation and clause lookup (`СП 54` ≠ `СП 542`);
   homoglyphs; unreliable paragraphs absent; cursor refused across queries; the window cap; the timeout
   refusal; the scope rule; both qualification conditions and `listNormSnapshots.qualified` agreeing with the setter; the `expected_current` conflict; one history row
   per change; events admin-only; role-less refused on all seven; the PDF only through a confirmed binding.
3. **`W55A-PIN-01`** (§A3.3; full gate) — `src/auditmanager/runs/{commands,repository,scope,__init__}.py` ‡;
   `src/auditmanager/bootstrap/{adapters,composition}.py` ‡ (run status; the reader for start and
   re-audit); `tests/integration/runs/**` ‡; `docs/program/W55A-PIN-01.md`. Required: a new run pins the
   current snapshot; NULL when none, digest byte-identical; a retry after a change replays; a pre-W55 key
   replays; a re-audit pins the current snapshot and its retry replays.
4. **`W55A-WEB-NORMS`** (§A3.7; light + `npm --prefix web run e2e:pc01 -- --phase all` in the lane) —
   `web/src/app/norms/**` and its document view; `web/src/_pages/norms/**`;
   `web/src/widgets/{norm-search,norm-document,norm-snapshots}/**`, `web/src/features/set-current-snapshot/**`,
   `web/src/entities/norms/**` (new); `web/src/shared/config/screen-registry.ts` ‡ (two `'any-role'` rows)
   with `web/tests/guards/screen-registry.guard.test.ts` ‡; `web/src/shared/lib/routes.ts` ‡ with
   `web/tests/unit/screens/routes.test.ts` ‡ and `route-screens.ts`; `web/tests/unit/qa_w50/r66-navigation.test.ts`
   (`/norms` leaves `STUBS`); `web/src/shared/api/query-keys.ts` (namespace `norms`) with
   `web/tests/guards/query-key-shape.guard.test.ts` and `web/tests/unit/api/configuration-and-cache-keys.test.ts`;
   `web/docs/PC01_UI_SEAM.md` §6; `web/tests/contract/narrow-sets.contract.test.ts`;
   `web/tests/guards/{prepared-sections,dashboard-invalidation,rendered-language}.guard.test.ts` (entries;
   rendered-language ‡); `web/tests/unit/styles/screens.ts`; `tests/e2e/pc01/journey/manifest.json`
   (entries); `web/tests/unit/norms/**` (new); `docs/program/W55A-WEB-NORMS.md`. Required: the refusal state
   rendered; role-less sessions kept out; admin controls hidden from experts.

**Stage C — `W55A-REHEARSAL-01`** (after PROMOTION-PRE; night window): the whole of §A7 on a disposable
stand here built from the candidate, with W54's tools and local keys, seeded with synthetic client data:
`capacity`; `receive`/`status`; the copy sequence and attestation (the importer refused without it);
`import` interrupted once in custody and once in the row transaction, each re-run converging;
`report` reconciled by `scripts/rehearsal/w55a/reconcile_report.py` (an altered report detected); `resume`;
designation and the live checks; both failure branches (`resume`; `restore-db` then `resume`) and the
hung-importer drill (the owner clears the lock). It measures the disk peak per filesystem, the import's
memory peak, the copy-pull throughput and the window length. Allowed: `scripts/rehearsal/w55a/**`,
`tests/contract/rehearsal/test_w55a_reconcile_report.py` (new), `docs/program/W55A-REHEARSAL-01.md`.

**Stage D:** `W55A-QA-01`; `W55A-JUDGE-X` (search input and cursor forgery; overlapping and huge ranges;
content without a session; all seven operations for role-less, expert and admin; scope of a never-current
snapshot; history immutability); `W55A-JUDGE-Y` (lineage manifest → report → snapshot → pinned run; R-82;
ALR-05 for `norms.search`; fingerprints; §A7 against the rehearsal record); `W55A-FIX`. **If FIX touches
`0020`, `norms/search/**`, `current_snapshot.py`, content or pinning, import, search and the timeout are
re-run after NOTES-JUDGE on the exact INT-CLOSE candidate.**

**`W55A-RELNOTES-01`** (after P2 is deployed and tagged, on the candidate): `release-notes/0.6.0.json`,
`release-notes/dictionary.json`, `VERSION`, the predecessor hits — W54's 0.5.0 lines in
`tests/contract/release_notes/test_release_notes_form.py` and `tests/integration/releases/test_release_loader.py`
(0.4.0 on `4fe7615`) — and `docs/program/W55A-RELNOTES-01.md`. The note is true at P3: search starts once an
administrator designates a snapshot. Then `W55A-NOTES-JUDGE`, then the re-run if Stage D requires it.

**`W55A-INT-CLOSE`:** the full gate on the exact candidate; the memory summary (§C5); P4's thresholds and
the timeout figure from the rehearsal.

**`W55A-INT-MAIN-01` (P3)** — CD-16's migrating sequence, on a direct owner instruction naming the SHA.
Preconditions: P2 deployed, `verify-objects` passed and `v0.5.0` tagged; the audience proof; no other
publication in flight.
1. Literal `GATE OK` on the exact clean candidate.
2. In a window agreed in advance (K-5, sized from the rehearsal): `dump-db` → `inventory-s3` → `fetch` →
   `restore-test.sh` here → `attest <STAMP> <dump-sha256> <restore-report-sha256> publish <sha>` with the
   candidate SHA (W54 §3.5; K-6); `deploy.sh` then accepts exactly that SHA.
3. Push (`MAIN_AUTODEPLOY_POLICY.md`: fetch, fast-forward proof, re-read `origin/main`).
4. Workflow and `verify-deployed.sh`.
5. `resume <STAMP>`.

Checks after `resume`: head `0020`; «Нормы» renders the refusal state; a ranged read of a client document
answers `206`; a new run shows no snapshot; a role-less account is refused. **Failure:** a forward fix (re-attest
`publish <sha>` with its SHA); or the owner-ordered `restore-db <STAMP> <sha256>`, then a reviewed revert,
then `resume <STAMP>`. The task stays
open through P4 and closes with the tag `v0.6.0` and the `docs/program/RELEASES.md` row (integrator;
AGENTS §5: tags only in `W*-INT-*`). Allowed: `docs/program/W55A-INT-MAIN-01.md`, `docs/program/RELEASES.md`,
`docs/program/CURRENT_STATE.md`, refs and the tag, `.local/stand-copies/**`.

### A5. Ownership (W55a)

| Hotspot / path family | Owner |
| --- | --- |
| `contracts/**`, `0020`, `api/**` except router bodies, `security.py` entries, the guards' literals, generated client, facts file | SEAL |
| `storage/**` named files, the storage fakes, `ingest/service.py` read path, `documents.py` content body, `credentialed-forward.ts` | CONTENT |
| `norms/search/**`, `norms/current_snapshot.py`, norms export lines, `routers/norms.py` bodies, `bootstrap/settings.py` | SEARCH |
| `runs/{commands,repository,scope,__init__}.py` | PIN |
| web «Нормы» files, screen rows, `routes.ts`, the R-66 test | WEB-NORMS |
| `bootstrap/{adapters,composition}.py` | SEAL → CONTENT → SEARCH → PIN, one at a time |
| `scripts/rehearsal/w55a/**` | REHEARSAL |
| `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `RELEASES.md`, refs, tags, `.local/**`, P3, P4 | integrator |
| stand keys, `provider.env`, naming the designating administrator account (or designating), any `restore-db` order | owner |

### A6. Estimate (W55a)

Freeze 2.0; SEAL 4.5; merges 1.0; CONTENT 4.0, SEARCH 6.0, PIN 4.0 (each with its full gate); WEB-NORMS 4.0
(with the journey); merges 2.0; rehearsal with the failure drills 5.0; judging 1.5; FIX 2.5; re-run on the
candidate 2.0; release notes 0.5; close with the gate 2.0 — **≈ 41 h**, P50 ≈ 7.75 working days, P80 ≈ 10.5.
Outside: P3 ≈ 4 h plus its window; P4 ≈ 6 h active plus the measured transfer and import (≈ 2–4 h
estimated); the night-window build and D124; the owner's provisioning and keys.

### A7. `W55A-STAND-IMPORT-01` — the corpus written to the stand (P4)

**Authority:** a direct owner instruction naming the bundle's `content_key` and digest, after P3. **Executor:**
this host's integrator, only through W54 §3.5's verbs on the two owner-installed keys (inbound:
`receive`, `status`, `import`, `report`, `requeue`; copy: `capacity`, `dump-db`, `inventory-s3`, `fetch`,
`attest`, `verify-objects <N>`, `restore-db`, `resume <STAMP>`, `status`), `push-bundle.sh`, `pull-copy.sh` and `restore-test.sh` here.
No stand shell. The owner orders any `restore-db`, clears a hung importer lock and provisions disk.
Allowed: `docs/program/W55A-STAND-IMPORT-01.md`, `.local/stand-copies/**`; no repository code.

**Preconditions:** P3 verified and `origin/main` unchanged since; the bundle is W54's verified bundle with
`build: present`, the digest named and rehearsed; §C6's stand thresholds met by `capacity`; a window agreed
in advance (K-5) whose length is P3's measured copy-pull time plus the rehearsal's import and checks plus
a margin — **stop if it would exceed W54's 12 h copy-record limit minus 2 h**, checked with the copy key's
`status` (the open record's age) before `import`; no publication in flight.

**Sequence (CD-16):**
1. `capacity` — stop below §C6.
2. `receive <key> <size>`, `status` — before the quiesce, to keep the window short.
3. `dump-db` → `inventory-s3 <STAMP>` → `fetch` → `restore-test.sh` here →
   `attest <STAMP> <dump-sha256> <restore-report-sha256> import` (K-1). The record is attested `import`
   explicitly, because step 2's `receive` came before `dump-db` and so did not convert it; copy-key
   `status` gives the record's age.
4. `import <key>` — re-run until it exits 0; poisoned admissions take `requeue <key>`, then `import` again.
5. `report <key>` — exit 0 required; its client figures must equal the copy record's.
6. `resume <STAMP>`.
7. An administrator account the owner names (the owner may be that administrator) designates the snapshot (`expected_current` empty); the history row is
   checked.
8. `verify-objects <N>`, then the live checks on P3's SHA with accounts the owner names: «СП 54 п. 7.1.4» and
   «ГОСТ 10140» with attribution and recorded latency; «открыть» at `page_label` by a `206`; role-less
   refused; an expert's new run and a re-audit pin the snapshot.

Then `W55A-INT-MAIN-01` closes with the tag.

**Failure.** Before step 7 nothing is current: runs pin NULL, search refuses, and a never-designated
snapshot is never searchable (§A3.4). Branches: `resume <STAMP>`; or, when client figures differ, the
owner-ordered `restore-db <STAMP> <sha256>` then `resume <STAMP>`. A hung importer holding its lock (so `resume` refuses) is an owner
act, rehearsed. Confirmed corpus objects that never reach a designated snapshot stay unbound and are
reported, not deleted. Migrations are forward-only. **No `main` push can deploy during P4:**
from step 3 until `resume`, `W54-STAND-COPY-01`'s `deploy.sh` refuses before any `docker` call with
`stand_import_open` (an import record is open) or `stand_import_locked` (the importer lock is held).

---

## Part B — W55b: portal bundles, recognised text and «Блоки» (target `v0.6.1`)

### B1. Objective

Uploads are **portal bundles only** (G-4), up to **500 pages / 250 MiB** (G-2), read through a file handle
end to end, never whole in memory; recognised text kept as its own marked artefact with quality flags
(F-6); portal blocks and locally cut crops as geometry; «Блоки» showing blocks, crops, recognised text and
the portal's descriptions marked (G-7); runs over a document larger than the analysis input budget refused
up front with a clear reason (G-11). No model looks at a crop in this wave.

### B2. Where it starts (`4fe7615`)

| Fact | Source |
| --- | --- |
| the upload reads the part into memory; the port and adapter take `bytes`; `stage_temporary(BinaryIO)` already exists | `documents.py:103`; `ports.py:141`; `adapters.py:369-433` ‡; `storage/s3.py:123` |
| the envelope runs pypdf then pdfplumber on every page before the idempotency claim — 18.2 s for 30 pages (≈ 300 s at 500, equal to nginx `proxy_read_timeout` and the BFF's default `headersTimeout`); pypdfium2 does the same checks in 0.53 s | `ingest/envelope.py:127-243`; `ingest/service.py:272-320` (probe 299, claim 312-320); `nginx.conf:119` ‡; measured on the real АР PDF |
| one body cap for every route; one server-wide `client_max_body_size 32m`; unauthenticated `POST /registrations` exists | `multipart.py:76-157`; `app.py:453`; `nginx.conf:97` ‡ |
| `document_version.page_count BETWEEN 1 AND 30` | `0002:478-479` |
| text analysis sends the whole text layer in one prompt; 30 pages ≈ 93 690 characters; the $1 ceiling is checked around calls, not before the first | `analysis/text/prompt.py:156-168` (`render_document`); `text/config.py:43`; `text/cost.py:8-14` |
| the real `_blocks.json`: `pages` is a list of `{page_index (0-based), width_px, height_px, rotation}`; blocks carry `page_index`, integer `page_label`, `coords_norm [x0,y0,x1,y1]`, optional `polygon_points` (12), non-unique `ordinal`, `status` (failed blocks exist in the corpus), `crop_url`; `document_id` is `doc_<32hex>` | legacy `13АВ-РД-АР-ТП1-ТП2_V1`; corpus bundles |
| `_results.md` holds 103 block headers (56 TEXT, 47 IMAGE); stamps never appear there; every block carries a `> **Crop:**` link to the portal | same |
| every portal ZIP of the corpus also holds `<stem>_stamp_audit.json`; the АР set has no ZIP at all | `.local/norms/corpus/MANIFEST.json` |
| no rotated page exists in the АР set or in the 674 corpus bundles | measured |
| the existing blocks feature is keyed by version, with `produced` / `not_produced` | `api/routers/blocks.py`; `W45-BLOCKS.md` |
| `pypdfium2` and Pillow are only transitive | `uv.lock:643, 509`; `P02_LOCK.json:39` |

### B3. Design

**B3.1 The bundle (G-4, G-10).**
- One `file` part holding a ZIP, recognised by its magic bytes (browsers send `application/zip`,
  `application/x-zip-compressed` or nothing). A bare PDF is refused (`validation_failed`, constraint
  `portal_bundle_required`) with a Russian sentence on how to obtain the bundle.
- **Members by suffix**, all sharing one stem compared on the raw name bytes: exactly one `.pdf`, one
  `_blocks.json`, one `_results.md`; optional one `_results.html` (**digest only** — never kept, served or
  rendered) and one `_stamp_audit.json` (**stored**, G-10; not used in analysis). Anything else is refused.
  Names are never identity; the display name is the PDF member's name decoded — UTF-8 when flag 11 is set,
  else the Info-ZIP Unicode path extra field (`0x7075`), else strict UTF-8, else cp866 — display only.
  `_stamp_audit.json` is parsed as JSON under a size cap before it is stored.
- **Archive rules, one refusal test each:** directory entries and `__MACOSX/`; `/`-absolute, drive-letter,
  backslash and `..` names; symlinks (external attributes); encrypted members (flag bit 0); compression
  method other than stored or deflate; duplicate names, also after case folding and NFC; a stem mismatch;
  a missing or extra member; per-member and total uncompressed size (declared **and** actual, counted while
  extracting; total ≤ 300 MiB); compression ratio above the freeze's bound; more than 8 entries. ZIP64 and
  data descriptors are accepted within the size rules.
- **Never fetched or rendered:** `crop_url` values and the `> **Crop:**` links are portal capability URLs —
  never fetched, stored for display, or rendered. Recognised text is markdown and is shown as text, never
  as HTML.

**B3.2 Transport and limits (G-2).**
- **A file handle end to end:** router → `DocumentPort.upload(BinaryIO)` → adapter → ingest; members
  extracted to temporary files with a running SHA-256 and the actual-byte cap, then
  `stage_temporary(BinaryIO)`. The envelope opens the PDF from the file with **pypdfium2** (structure,
  encryption, page count, per-page text presence, per-page character count); pdfplumber stays in
  `source_preparation`.
- **Per-route caps:** the upload route ≈ 251 MiB; every other route keeps today's cap (`BodyCapMiddleware`
  per path, `app.py`). nginx: `client_max_body_size 260m` **only** in the two upload locations
  (`/api/v1/projects/*/documents`, `/bff/v1/projects/*/documents`) — regex locations with
  `rewrite ^/api/v1/(.*)$ /$1 break;` and a URI-less `proxy_pass`, repeating `proxy_redirect`, the throttle
  and the headers — with explicit `client_body_timeout` and `proxy_read_timeout`; the server default stays;
  both configs proven by `nginx -t` and a body test.
- **The BFF** streams the request body (`duplex: 'half'`) under `AbortSignal.timeout`; that can only
  shorten undici's 300 s default, so the plan's bound is that the API answers an accepted 250 MiB upload
  within ≈ 240 s, measured — no `undici` Agent is added.
- **Bounded concurrency:** at most two uploads in flight per API process, refused in `BodyCapMiddleware`
  **before the body is read** (FastAPI parses the form before route code); the third gets a typed `503`
  with `Retry-After`. The freeze states the API's worker count, so the per-stand bound is explicit.
- **D-44 headroom:** precheck 250 MiB < API cap < nginx 260m; the headroom test reads the upload location;
  the oversize stand-in is a sparse file generated at test time, never committed.
- **Database:** `0021` widens `ck_document_version_page_count` to 1–500 and adds three nullable
  columns, NULL for existing versions (which are ≤ 30 pages):
  - `document_version.text_character_count integer`: pypdfium2's count over the document;
  - `document_version.textless_pages integer[]`, requested by `W56-PLAN.md` §A9: the ascending,
    1-based numbers of the pages whose pypdfium2 character count is below a threshold this freeze pins;
    empty when no page qualifies;
  - `document_version.recognised_character_count integer`: the recognised characters on those pages,
    from `_results.md`.

**B3.3 The analysis input budget (G-11).** `startRun` **and `reauditRun`** refuse up front (typed,
`analysis_input_budget_exceeded`, with the version's character count and the budget) when
`text_character_count` exceeds the budget. A re-audit runs on the current configuration (R-82), so it
faces today's budget, not the source run's. The budget is the one the freeze derives from the configured model's context and the
$1 ceiling (≈ 50 pages of text). pypdfium2's count includes generated line breaks and differs from
pdfplumber's text layer: the ratio is calibrated on the АР set and the synthetic documents and the budget
set with margin. The model and the ceiling are operator settings, so the budget is derived at start-up
from them, and a configuration under which no 30-page АР document fits is refused at start-up. The budget is
`analysis.public.input_budget_characters(model_id, ceiling_usd, reserved_characters=0)` (new,
`analysis/text/budget.py`), in characters of pypdfium2's count, computed once at start-up in
`bootstrap/settings.py`; W57's CAP-01 fixes `reserved_characters` for the norms context. Upload, «Блоки» and the viewer work on any accepted
document. Chunked analysis is registered for W56 with AR-2.
- **A low-text document** (raster pages, thin text layer) passes a character budget, so the run side must
  hold on its own: `source_preparation` and `page_geometry_extraction` open the PDF from a temporary file,
  never from bytes in memory (`page_geometry_extraction.py:82` today), and the rehearsal runs a 500-page
  low-text bundle end to end with time and memory measured.

**B3.4 Stored inputs.** `source.document` (PDF), `source.structured_companion` (`_blocks.json`),
`source.markdown` (`_results.md`), `source.stamp_audit` (new role); the command fingerprint covers every
member's digest, `_results.html`'s included. Members are staged as temporaries and bound in the one
publication transaction; a failed publication leaves temporaries that the existing reconciliation sweeps —
no version exists with a partial member set.

**B3.5 Envelope.** PDF rules (not encrypted, parseable, 1–500 pages); `_blocks.json` against a pinned
schema (`pages[]` with `page_index` 0…n−1 equal to the PDF's page count; unique `blk_<32hex>` ids;
`coords_norm` in [0,1] with x0<x1, y0<y1; `rotation` ∈ {0, 90, 180, 270}; `status` ∈ the portal's set,
`failed` tolerated and shown); `document_id` ignored (it collides with the product's `doc_` prefix);
`_results.md` and `_blocks.json` agree **both ways** for TEXT and IMAGE blocks with equal types (stamps
only in `_blocks.json`). Text-layer rule: every page has a text layer **or** at least one portal block —
**"OCR is never substituted" becomes "OCR is always marked"** (with W54's `R-103`).

**B3.6 Recognised text.** `source_preparation` emits `prepared.recognised_text` — per portal block, the
OCR text with `quote_source = recognised` and quality flags: mixed-script words, Latin/Cyrillic
homoglyphs, CJK, doubled list markers and the norms degeneracy signals (through `norms.public`).
Engineering designations (`1.A`, `B25`, `A500C`, `REI 150`) are exempt by a pinned pattern; the flags'
precision is measured on the real `_results.md` against the same pages' text layer and recorded. Never
merged into `prepared.text_layer`. IMAGE bodies are stored as `portal_description`, shown as «описание
портала — в анализе не используется», never sent to analysis (G-7). Stamp blocks keep their fields.

**B3.7 Portal blocks and crops (OD-04 flips).**
- `page_geometry_extraction` normalises `_blocks.json` into `geometry.portal_blocks`: `page_number =
  page_index + 1`, `page_label` kept, `coords_norm`, `polygon_points`, type, status, ordinal (not unique;
  order by page, ordinal, id). `portal_block_id` is the bundle's `blk_<32hex>`, an **external** identifier
  (`identifiers.json` gains an external-identifier entry).
- **Page box check:** the portal's `width_px/height_px` aspect is compared with the PDF CropBox after
  `/Rotate` within a tolerance pinned at the freeze (the real pages differ by ≈ 0.06 %); a mismatch marks
  the page `geometry_mismatch` and cuts no crop (no silent fallback) — visible in the artefact and in
  «Блоки» while the stage reports success. Rotations
  are tested on generated pages; no real rotated page exists.
- **Crops** for IMAGE blocks: pypdfium2 renders **only the clip region** (matrix plus clip) at a scale
  giving a long side ≥ 800 px, capped at a pixel budget fixed at the freeze; PNG. **Roles:** the manifest
  stays `geometry.page_crops` — the existing required JSON output and `block_analysis`'s declared input
  (`stage-registry.json:292-295, 439-442`), now non-empty under a new `crop_policy` value — listing block,
  page, bbox, render profile, `blob_id`, SHA-256 and pixels; the PNGs are content-addressed blobs of a new
  role `geometry.crop_image` (`image/png`), referenced only from the manifest. Byte stability holds within
  one image only; tests assert properties and same-environment repeatability, never recorded crop bytes.
- The new outputs are `prepared.recognised_text` and `geometry.portal_blocks`, both `required: false`;
  W56 flips them when `block_analysis` consumes them.
- **Serving** follows `getVersionBlocks` (geometry is a property of the version): `listVersionPortalBlocks`
  `GET /versions/{version_uid}/portal-blocks` (cursor over page, ordinal, id; `not_produced` before the
  first run) and `streamVersionPortalBlockCrop` `GET /versions/{version_uid}/portal-blocks/{portal_block_id}/crop`,
  both from the latest run whose geometry stage succeeded. W56 adds serving by run or evidence for region
  evidence.

**B3.8 Fixtures.** `tools/fixtures/` (existing `ar_corpus/` generator; `MAX_PAGES = 30` moves) gains a
portal-bundle generator: one TEXT block per page from the text layer, a matching `_results.md`, optional
IMAGE blocks and a stamp audit; every synthetic PDF gets a bundle; `SHA256SUMS` covers them. Negative
fixtures keep their meaning: `oversize` (sparse, > 250 MiB) and `too_many_pages` (501 pages) are generated
at test time; `image_only` is a page with neither a text layer nor a portal block. The real АР set stays
under `.local/` (F-7). **The owner provides a fresh portal ZIP export (confirmed 2026-10-06)**, kept under
`.local/portal-exports/` and never committed (F-7). It is the rehearsal's real bundle, and `W55B-FREEZE-01`
checks it against §B3.1 and §B3.5 — member set and names, the `_blocks.json` schema, the stamp audit, the
`_results.md` headers — adjusting the rules where the real export differs. Only if it has not arrived by
that freeze is a bundle assembled from the АР set's files, and the rehearsal report says so.

**B3.9 Screens.** «Блоки»: per page, portal blocks by type; crops for IMAGE blocks; recognised text marked
«распознано» with its flags; portal descriptions marked; stamps; the text-line view as a second tab; «блоки
появятся после первого запуска» before one. Upload form: accepts the ZIP, explains the bundle and the
limits. Run start: the budget refusal shown with its figures.

### B4. Tasks

**`W55B-RULE-01`** (integrator): `R-Y5` portal bundles only, the member set with the stamp audit stored and
the HTML kept as a digest, 500 pages / 250 MiB, "OCR is always marked" (G-2, G-4, G-10, with `R-103`);
`R-Y6` portal descriptions never in analysis (G-7); `R-Y7` the analysis input budget until chunking, also on
re-audit (G-11);
`R-Y8` OD-04 flipped. Real client portal bundles may be uploaded before the beta backup wave without
conditions; the owner accepts the risk (K-7).

**`W55B-FREEZE-01`** (integrator): standard form, plus — the W54 probe reports read and §B3.5–§B3.7
adjusted if they contradict them; the owner's portal export checked against §B3.1 and §B3.5 (§B3.8); migration `0021_portal_bundles`; the ratio bound, crop pixel budget,
upload timeouts, the `textless_pages` threshold and the input budget number; `pin_sweep.py` for `reseal-surface migration route
error-code` and a `contract-version` decision for `uploadDocument`'s encoding change (the event added if it
moves); the **SUITE file list**: `git grep -l -E 'upload_single_pdf\(|files=|"file": \(|upload_document\(|uploadDocument' -- tests web/tests scripts`
plus `tests/e2e/pc01/journey/{journey,cdp}.mjs`, `tests/e2e/pc01/test_live_text_analysis.py`,
`tests/e2e/p02/test_journey.py`, `scripts/manual-alpha-check.sh` with
`tests/contract/test_alpha_acceptance_command.py`, each with a reason (63 files on `4fe7615`); minus only
files granted to a lane that runs **after** INGEST — files in SEAL's, FIXTURES' or STREAM's grants stay
in the list, because those lanes have merged; the page-box tolerance; the worker count;
the characterization records per lane; the predecessor hits (W55a's 0.6.0 lines in the two release
tests); ports.

**Stage A** (from the freeze SHA):
- **`W55B-SEAL-01`** (full gate; CD-10) — the upload encoding and description (bundle, limits, refusals, D-110 sentence),
  `listVersionPortalBlocks`, `streamVersionPortalBlockCrop` (both `_ANY_ROLE` in `security.py` ‡ and
  `test_role_register.py` ‡), the error codes (`analysis_input_budget_exceeded`,
  the busy refusal, constraint names), every port signature this half needs (`DocumentPort.upload(BinaryIO)`,
  `BlockPort` portal blocks and crops) with the `documents.py` upload call and its `_MULTIPART_ENCODING`
  constant adapted, the stage registry (role `source.stamp_audit`; `source.structured_companion` as an
  optional input of `page_geometry_extraction`, which today declares only `prepared.*` inputs; new outputs
  `prepared.recognised_text` and `geometry.portal_blocks`, `required: false`; `geometry.page_crops` stays
  the required manifest under a new `crop_policy`; role `geometry.crop_image`; the crop manifest and
  `_blocks.json` schemas), `identifiers.json`, one entry per new error code in
  `src/auditmanager/shared/errors/{codes,catalog}.py`, `web/src/shared/api/catalog-message.ts` and
  `web/src/entities/audit-run/model/terminal-reason.ts`, migration `0021`
  (§B3.2), the direct pins of `pypdfium2` and Pillow (`pyproject.toml`, `uv.lock`, `docs/program/P02_LOCK.json`),
  `P02_SEAMS.md` §4.1/§4.2/§4.4/§4.5/§4.7/§7/§8/§9, `PROTOTYPE_PROFILE.md` (OCR and archive sentences),
  `PROTOTYPE_EXECUTION_PLAN.md` (OD-04 row), the contract-text assertions in
  `web/tests/unit/projects/{upload-envelope,envelope-encoding-and-delivery}.test.ts`. Allowed: `W55A-SEAL-01`'s
  list with `<date>_0021_portal_bundles.py`, **minus** `tests/contract/fixtures_ar/**`,
  `tests/integration/api/test_multipart_rules.py`, the `nginx.conf` body directives and
  `tests/characterization/w13_baseline/**`; plus the files named here, the three composition guards'
  literals (`PORT_FOR_ARGUMENT`; `EXPECTED_ADDRESSED`/`EXPECTED_UNADDRESSED` with `portal_block_id` in
  `identifiers.json`; `test_router_answers.py`), `docs/program/W55B-SEAL-01.md` and
  every path `pin_sweep.py` prints. Required: fresh upgrade, upgrade from `0020` with rows, refused
  downgrade; adapters satisfy the new port signatures with today's behaviour; `make gate`.
- **`W55B-FIXTURES-01`** (§B3.8; runs after SEAL on this host) — `tools/fixtures/**`, `fixtures/synthetic/**`
  with `fixtures/synthetic/ar/SHA256SUMS`, `tests/contract/fixtures_ar/**`, the fixture manifest,
  `docs/program/W55B-FIXTURES-01.md`. Required: regeneration byte-stable; every synthetic PDF has a bundle;
  the negative generators added **beside** the committed negatives, which stay until INGEST switches their
  consumers.

**Stage A′** — **`W55B-STREAM-01`** (§B3.2; full gate, infra; from SEAL's merge) — **transport only**: it keeps the envelope
limits (30 pages, 25 MiB) and the precheck numbers, and its pypdfium2 envelope keeps every refusal's field,
constraint and message byte-identical (characterization records 17, 19, 20, 21 unchanged). Allowed:
`src/auditmanager/api/routers/{multipart,documents,__init__}.py`, `src/auditmanager/api/app.py` (per-path cap and the
concurrency gate), `src/auditmanager/bootstrap/adapters.py` ‡ (`DocumentAdapter`),
`src/auditmanager/ingest/{service,envelope}.py` (file handle, pypdfium2 checks),
`web/src/shared/api/credentialed-forward.ts` ‡ (request streaming, timeout) with
`web/tests/unit/api/credentialed-forward.test.ts` ‡, `infra/deploy/proxy/{nginx,tls-server}.conf` ‡,
`tests/integration/api/test_multipart_rules.py`, `tests/integration/ingest/test_envelope*.py`,
`tests/integration/ingest/test_size_guard_boundary.py` (`MAX_BODY`), `tests/e2e/test_upload_limit_headroom.py` and
`tests/e2e/prove_the_headroom_guard_can_fail.py` (two upload locations), `tests/contract/test_proxy_rate_limits.py`,
`tests/characterization/w13_baseline/journey.py` with records 18
and 22 (`permitted_change`), `docs/program/W55B-STREAM-01.md`. Required: a 250 MiB body read through the
transport to the envelope's size refusal with peak API memory bounded (measured, method recorded); every
other route still capped at today's limit; the third concurrent upload refused before its body is read;
`nginx -t` for both configs; the headroom test still green.

**Stage B** — sequential; check levels in §C6:
1. **`W55B-INGEST-01`** (§B3.1, §B3.4, §B3.5, and the suite; full gate and the journey) — `src/auditmanager/ingest/**`,
   `src/auditmanager/documents/**`, `src/auditmanager/bootstrap/adapters.py` ‡ (`DocumentAdapter`),
   `tests/integration/ingest/**` ‡; **the SUITE file list of the freeze**; `tests/integration/api/conftest.py`,
   `tests/integration/p02_journey/{journey,test_manifest_role_seam,test_explicit_failures}.py`,
   `tests/e2e/pc01/journey/{manifest.json,refusals.mjs}`; characterization records 02, 13, 17–21, 26, 32, 33
   with `journey.py`; the limits and the negatives — `tests/e2e/test_upload_limit_headroom.py` (reads the
   upload location; the sparse stand-in), `tests/e2e/prove_the_headroom_guard_can_fail.py`,
   `fixtures/synthetic/ar/{negative/**,SHA256SUMS,expected_issues.json}`, `tests/contract/fixtures_ar/**`,
   `tools/fixtures/ar_corpus/**` (`MAX_PAGES`), `src/auditmanager/documents/public.py` (exposes
   `text_character_count`, `textless_pages` and `recognised_character_count`); the browser upload — `web/src/entities/document-version/model/upload-envelope.ts`,
   `web/src/features/upload-document/**`, `web/src/widgets/upload-panel/**`, `web/tests/unit/projects/**`,
   `web/tests/unit/screens/{widgets,forms-and-pages}.test.ts`, `web/tests/guards/upload-precheck-wiring.guard.test.ts`;
   `docs/program/W55B-INGEST-01.md`. INGEST raises the limits and the precheck to 500 pages / 250 MiB,
   switches every consumer of `oversize.pdf` and `too_many_pages.pdf` to the generators and deletes those two
   files. Bundles are accepted first; the bare-PDF refusal switches on in the lane's last commit, after the
   suite moved. Required: one refusal test per archive rule; the stamp audit
   stored, the HTML not kept; the fingerprint over all members; both character counts and the text-less pages stored (§B3.2); a bare PDF refused with the sentence; an
   accepted 250 MiB bundle with bounded memory (measured); PC-02's corpus check registered as a debt, not
   changed.
2. **`W55B-BUDGET-01`** (§B3.3; full gate) — `src/auditmanager/analysis/text/budget.py` (new),
   `src/auditmanager/analysis/public.py` (one export line, before RECOGNISED), `src/auditmanager/runs/commands.py` ‡
   (keyword `input_budget_characters: int | None = None` on `start_audit_run` and `reaudit_run`, so the
   ≈ 30 existing callers stay untouched; None means "no configuration" and is reachable only from tests),
   `src/auditmanager/bootstrap/{settings,composition,adapters}.py` ‡ (derived once at start-up, always passed,
   the version's character count), `tests/integration/composition/test_settings_defaults.py`,
   `tests/integration/runs/test_input_budget*.py` (new), `docs/program/W55B-BUDGET-01.md`. Required: refused
   above, accepted at the budget, for a start and for a re-audit; NULL count accepted; a composition test
   proving the served application always passes a budget; the start-up refusal.
3. **`W55B-RECOGNISED-01`** (§B3.6) — `src/auditmanager/analysis/stages/source_preparation.py`,
   `src/auditmanager/analysis/recognised/**` (new), `src/auditmanager/analysis/{ports/artifacts,public}.py`
   (role constants and export lines), `src/auditmanager/norms/public.py` (one export line, degeneracy),
   `tests/integration/analysis/recognised/**` (new), the existing source-preparation cases in
   `tests/integration/{analysis,analysis_engine}/` the text-layer-or-block rule moves (named by the freeze,
   e.g. `test_fail_closed.py`), `docs/program/W55B-RECOGNISED-01.md`. Required: never in
   `prepared.text_layer`; each flag by a test on recorded portal text; the designation exemption; measured
   precision recorded; the PDF opened from a temporary file.
4. **`W55B-GEOMETRY-01`** (§B3.7; full gate) — `src/auditmanager/analysis/stages/page_geometry_extraction.py`,
   `src/auditmanager/analysis/geometry/**` (new), `src/auditmanager/analysis/{ports/artifacts,public}.py`
   (export lines, after RECOGNISED), `src/auditmanager/api/routers/blocks.py` (bodies),
   `src/auditmanager/bootstrap/adapters.py` ‡ (`BlockAdapter`), `src/auditmanager/analysis/README.md` (OD-04
   prose), `tests/integration/analysis/geometry/**` (new), `tests/integration/runs/test_w45_blocks_version_block_index.py`,
   `tests/integration/composition/{test_version_blocks_wire_shape,test_router_answers,test_an_absent_parent_is_not_an_empty_page}.py`,
   `docs/program/W55B-GEOMETRY-01.md`.
   Required: rotations 0/90/180/270 on generated pages; the page-box mismatch and its tolerance; clip
   rendering under the pixel budget; manifest digests; equal crops reused; `not_produced` before a run; the
   PDF opened from a temporary file.
5. **`W55B-WEB-BLOCKS`** (§B3.9; light + the journey) — `web/src/_pages/blocks/**`, `web/src/widgets/portal-blocks/**` (new),
   `web/src/entities/block/**` (new), `web/src/features/start-run/**` (the budget refusal),
   `web/src/shared/api/query-keys.ts` (beside `versions.blocks`) with `web/tests/guards/query-key-shape.guard.test.ts`
   and `web/tests/unit/api/configuration-and-cache-keys.test.ts`, `web/docs/PC01_UI_SEAM.md` §6,
   `web/tests/guards/{prepared-sections,rendered-language}.guard.test.ts` (entries), `web/tests/unit/styles/screens.ts`,
   `web/tests/unit/run/**` (start-run cases), the `/blocks` entry of `tests/e2e/pc01/journey/manifest.json`,
   `web/tests/unit/blocks/**` (new),
   `docs/program/W55B-WEB-BLOCKS.md`.

**Stage C:** **`W55B-REHEARSAL-01`** (night window): the owner's portal export (§B3.8) uploaded to a disposable stand,
a run, «Блоки» with every block and every IMAGE crop of the export (the АР set had 129 blocks and 47 crops); a synthetic 500-page text-rich bundle — upload time and
memory, the budget refusal; a synthetic 500-page **low-text** bundle (raster pages, IMAGE blocks) that passes
the budget — a full run with `source_preparation` and `page_geometry_extraction` time and memory measured. Allowed: `scripts/rehearsal/w55b/**` (no
surface-count phrases), `docs/program/W55B-REHEARSAL-01.md`. **`W55B-RELNOTES-01`** (after `v0.6.0` is tagged): `release-notes/0.6.1.json`,
`release-notes/dictionary.json`, `VERSION`, W55a's 0.6.0 lines in the two release tests, `docs/program/W55B-RELNOTES-01.md`.

**Stage D:** `W55B-QA-01`; `W55B-JUDGE-X` (every archive rule; malformed `_blocks.json`; a slow 250 MiB
body; concurrent uploads; large bodies to other routes; crop and block reads without a session; markdown
and HTML injection in recognised text); `W55B-JUDGE-Y` (lineage bundle → version inputs → run artefacts;
ALR-05 for `analysis.recognised` and `analysis.geometry`; the budget's arithmetic, on start and on re-audit); `W55B-NOTES-JUDGE`;
`W55B-FIX`.

**`W55B-INT-CLOSE`** — the full gate on the exact candidate; the memory-peak summary of both halves for the A13 decision (G-12, §C5); register: chunked analysis (W56); region evidence (W56); anonymised real fixtures
(F-7); the portal API (F-9); PC-02's archive refusal; hybrid search. **`W55B-INT-MAIN-01`** on the owner's
instruction naming the SHA, never during P4: CD-16's migrating sequence exactly as in `W55A-INT-MAIN-01`
(gate; in a K-5 window `dump-db` → `inventory-s3 <STAMP>` → `fetch` → `restore-test.sh` →
`attest <STAMP> <dump-sha256> <restore-report-sha256> publish <sha>`; push; workflow and `verify-deployed.sh`;
`resume <STAMP>`; the same failure branches); live acceptance — a bundle uploaded, a run,
«Блоки» with blocks and crops, the bare-PDF refusal, the budget refusal; tag `v0.6.1` and the
`RELEASES.md` row.

### B5. Ownership (W55b)

| Hotspot / path family | Owner | Parallel writer |
| --- | --- | --- |
| `contracts/**`, migration `0021`, `pyproject.toml`, `uv.lock`, `P02_LOCK.json`, `api/**` but router bodies and `app.py` (SEAL adapts the `documents.py` upload call to the new port), generated client, facts file, error-code entries, P02_SEAMS sections, the contract-text assertions | SEAL (A) | none |
| `tools/fixtures/**`, `fixtures/synthetic/**`, `tests/contract/fixtures_ar/**` | FIXTURES (A, after SEAL), then INGEST (the negatives) | none at once |
| `multipart.py`, `documents.py` upload body, `app.py`, nginx configs, `credentialed-forward.ts`, `ingest/{service,envelope}.py` (transport) | STREAM (A′) | none |
| `ingest/**`, `documents/**`, the SUITE list, the browser upload files | INGEST (B1) | none |
| `characterization/w13_baseline/journey.py` | STREAM (records 18, 22), then INGEST | none at once |
| `tests/e2e/pc01/journey/manifest.json` | INGEST, then WEB-BLOCKS (`/blocks` entry) | none at once |
| `runs/commands.py` | BUDGET (B2) | none |
| `source_preparation.py`, `analysis/recognised/**` | RECOGNISED (B3) | none |
| `analysis/{ports/artifacts,public}.py` export lines | BUDGET (`public.py`), RECOGNISED, then GEOMETRY | none at once |
| `bootstrap/{settings,composition}.py`, `test_settings_defaults.py` | BUDGET | none |
| `tests/e2e/{test_upload_limit_headroom,prove_the_headroom_guard_can_fail}.py` | STREAM, then INGEST | none at once |
| `page_geometry_extraction.py`, `analysis/geometry/**`, `blocks.py` bodies | GEOMETRY (B4) | none |
| web «Блоки» files | WEB-BLOCKS (B5) | none |
| `bootstrap/adapters.py` | SEAL → STREAM → INGEST → BUDGET → GEOMETRY | none at once |
| integrator-only files, refs, tags, the stand, `.local/**` | integrator | none |

### B6. Estimate (W55b)

Freeze 2.0; SEAL 4.5; FIXTURES 3.0; STREAM 6.5; INGEST with the suite, the negatives, its gate and the
journey 12.0; BUDGET 4.5; RECOGNISED 4.0; GEOMETRY 6.0; WEB-BLOCKS with the journey 4.0; merges 4.0;
rehearsal with the low-text run 4.0; release notes 0.5; judging 2.5; FIX 4.0; gate 0.5; close 1.5 —
**≈ 63.5 h**, P50 ≈ 12 working days, **plan on P80 ≈ 16** (INGEST carries most of the risk). Every lane
runs alone on this host.

---

## Common sections

### C0. W54 carryover

`W54-INT-CARRYOVER-01` names each unfinished W54 item; W55 runs it as a named task with W54's grant
re-measured by `pin_sweep.py`: `W55-PROMOTION-PRE-01` (repair, load, build, export, local rehearsal)
before D124, REHEARSAL and P4; `W55-VISION-PROBE-01` before W55b's geometry and budget freeze;
`W55-WORKERS-WEB-01` and `W55-WORKER-01` finished before `W55A-FREEZE-01` (they overlap SEAL, SEARCH and PIN)
and before P2. The freezes refuse a missing task or its evidence.

### C1. Integration order

**W55a:** RULE, FREEZE (W54 merged, WORKER-01 done) → SEAL ∥ PROMOTION-PRE → D124 → CONTENT → SEARCH →
PIN → WEB-NORMS → REHEARSAL → QA ∥ X ∥ Y → FIX → P2 deployed and tagged → RELNOTES → NOTES-JUDGE → the
re-run on the INT-CLOSE candidate (if FIX required it) → INT-CLOSE → P3 → P4 → tag.
**W55b:** RULE, FREEZE → SEAL → FIXTURES → STREAM → INGEST → BUDGET → RECOGNISED → GEOMETRY → WEB-BLOCKS →
REHEARSAL → judging → FIX → P4 done and `v0.6.0` tagged → RELNOTES → INT-CLOSE → INT-MAIN (never during P4).

### C2. Stop conditions

`W48-PLAN.md` §14, plus: W54 spill or WORKER-01 unfinished at the freeze; no complete build; P2 not
deployed, verified and tagged before P3; a W54 key missing; `capacity` below §C6; a copy failing its restore
test; `report` not exiting 0; a window longer than W54's copy limit allows; the disk here below §C6; a W54
probe report contradicting §B3.5–§B3.7; a 250 MiB upload beyond the stand's memory or timeouts; crops not
repeatable within one image; no input budget admitting the 30-page АР set; a budget-admitted run beyond the
worker's memory.

### C3. Non-goals

`block_analysis`, region evidence, chunked analysis, `finding_merge`, the critic (W56); `norm_verification`
and the registry fix (W57); semantic or hybrid screen search; a client PDF renderer (OD-09); anonymised
real fixtures; the portal API; the backup system (R-77); any stand-side tool (W54).

### C4. Estimate together

≈ 41 h + ≈ 63.5 h = **≈ 104.5 h**, P50 ≈ 19.75 working days, P80 ≈ 26.5; P3, P4 and W55b's main
publication are outside.

### C5. Memory measurement for A13 (G-12)

Each lane records the peak of its acceptance run — `memory.peak` of its cgroup, else `/usr/bin/time -v`
around the command — with the tree and the command. The full-gate lanes (§C6) give the figure A13 is sized
from; `W55B-INT-CLOSE` summarises both halves.

### C6. Check levels and disk (AGENTS §8, CD-10, CD-21)

**Levels.** Full gate: both SEALs, CONTENT, SEARCH, PIN, STREAM, INGEST, BUDGET, GEOMETRY (contracts,
migrations, infra, `bootstrap/**` or a `conftest.py`) and each INT-CLOSE. Light acceptance with the named
integration suites: FIXTURES, RECOGNISED. Screen lanes WEB-NORMS, WEB-BLOCKS and INGEST also run
`npm --prefix web run e2e:pc01 -- --phase all` on their own stand.

**Disk here** — one filesystem today (`/`, holding the worktree and the Docker data root):
increment = S + O + G + I + 3·D, where S is `receive`'s staged bundle copy (≈ 5 GB), O the disposable
stand's objects (≈ 4.75), G `db_growth_bytes` (≈ 2.5), I the disposable stand's images and containers
(measured, ≈ 3), D a stand dump (the pulled copy and its restore test). **Stop rule:** a rehearsal or copy
pull starts only if `df -B1` shows the increment + 3 GiB free (≈ 19 GB); W54's resident set (W54 §3.9,
≈ 8.6 GB, 5.1 GB with the image pruned) is already on disk and is not counted again. The total footprint is
≈ 28 GB against today's 14.1 GB free: it does not fit, and provisioning is the owner's (CD-21). The bundle
is never deleted to make room: it is the corpus's recovery copy (K-1). Memory: available RAM fluctuated
between 2.6 and 7.3 GiB on 2026-10-12, so the 6 GiB floor (swap excluded) is measured at each heavy step.

**Disk on the stand**, per filesystem from `capacity`, run right after P2 and again at P4 step 1: the Docker
data root needs O + G + 2 GiB; staging needs S + D + 2 GiB (the summed need if they share a filesystem),
each plus 25 %. Memory: available ≥ the rehearsal's import peak + 1 GiB, swap excluded.

### C7. Interfaces W56 and W57 rely on

| Interface | Promise |
| --- | --- |
| Pinning | `startRun` and `reauditRun` write `audit_run.norms_snapshot_id` from `norms.public.current_snapshot()`; the stored digest adds it when not NULL; the basis and both fingerprints never do; NULL until W57a refuses a norms-reading run with `required_norm_unavailable` (CD-19) |
| Setter | `src/auditmanager/norms/current_snapshot.py` (command, reader, predicate; tests `tests/integration/norms/test_current_snapshot*.py`); `setCurrentNormSnapshot`, `_ADMIN`, `expected_current`, no unset; history in `norm_current_snapshot_event`; `listNormSnapshots` reports `qualified` and `current` |
| `page_label` | the true 1-based PDF page: `#page=<page_label>` |
| Designation | `norm_designation_tokens(text)`, `IMMUTABLE`, `translate` tables |
| `textless_pages` | `document_version.textless_pages integer[]`, ascending 1-based pages below the frozen threshold; empty when none; NULL before W55b |
| G-11 | `analysis.public.input_budget_characters(model_id, ceiling_usd, reserved_characters=0)`, in characters of pypdfium2's count; checked at `startRun` and `reauditRun`; W57's CAP-01 fixes `reserved_characters` for the norms context |
