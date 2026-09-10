# Gate A — session briefs

> **Status: A2, A3, A4 dispatchable now. A1-schema and A5 blocked on one owner ruling.**
> Base commit: the `planning/prototype-roadmap` tip carrying both merged candidates.
> Structure: `PROTOTYPE_WAVE_PLAN.md` §3. Specification content: the named task files.

## 0. Authority split — read before dispatching

`FF-01` §4 approves the foundation and explicitly does **not** approve
"Project, DocumentVersion, AuditRun or finding tables". `PROTOTYPE_WAVE_PLAN.md` §3 folded
the whole PC-01 schema into `A1` to give every Gate B session one frozen migration head.
That fold exceeds the standing authority, so `A1` is split here:

- **`A1a` — authorized by FF-01 now.** Migration runner, baseline head, typed
  session/transaction factory, identifier value types. No product table.
- **`A1b` — needs the owner's word.** The PC-01 tables, the stage-artifact shapes, the
  `contracts/api/v1` OpenAPI document and the CSV column contract.

`A1b` is what `OD-14` gates, and `OD-14` is now heavier than the planning line recorded.
Verified on `main`'s `artifacts/checkpoints/CP-00/manifest.json`, not on this branch's copy:
`ratified: false`; twelve rounds; **round ten `void` although both streams returned `PASS`**;
round eleven `void`; round twelve `frozen` with both streams unreported. CP-00 carries no
accepted ratification in the superseding series. The question is therefore not whether P02
may start while a tidy-up round is outstanding, but whether it may create a contract family
while the architecture checkpoint it descends from has none accepted.

`PROTOTYPE_PROFILE.md` §6.3 still quarantines CP-00 mechanics from prototype gates, and
`FF-01` still authorizes P01 without qualification. That is why `A1a`, `A2`, `A3` and `A4`
proceed regardless of the ruling.

## 1. Common to every session

- **Base:** the literal SHA in the dispatch prompt. Never `HEAD`, never a branch name.
- **Branch:** `agent/<session-id>` from that SHA. Do not stack on another session's branch.
- **Instance:** unique `FOUNDATION_INSTANCE`, `POSTGRES_PORT`, `S3_API_PORT`,
  `S3_CONSOLE_PORT`, `POSTGRES_DB`, `S3_BUCKET` (FF-01 §5). Never run `make up` against
  another session's instance.
- **Command surface:** the nine `make` targets are frozen. Fill your reserved path; never
  edit the `Makefile` or add a private alias. A missing implementation fails explicitly.
- **Out of bounds for all:** `contracts/domain|analysis|events/v1/**`, `fixtures/golden/**`,
  `artifacts/checkpoints/**`, `tests/contract/**`, `tests/checkpoint/**`, Git tags, root
  locks, `src/auditmanager/bootstrap/**`, and every other session's tree.
- **Historical suites are not your gate.** `tests/contract` and `tests/checkpoint` are CP-00
  evidence and are red on this tree before you touch anything. Run only your own commands.
- **Report:** changed paths, the exact commands run and their exit codes, what you could not
  do, and any seam you needed but did not have. Do not report a command you did not run.

## 2. `A1a` — migration and session foundation

- **Owns:** `db/migrations/**`, `src/auditmanager/shared/db/**`,
  `src/auditmanager/shared/identity/**`
- **Spec:** `docs/program/tasks/P1-DB-01.md`; identifier types from `P2-DOM-01.md`
- **Delivers:** migration configuration and one baseline head; typed engine, session and
  transaction construction behind the shared DB boundary; opaque identifier value types;
  `src/auditmanager/shared/db/check.py` proving connectivity and current head through
  `make check-db`; clean-install, current-head and rollback tests against PostgreSQL
- **No product table.** The baseline head is empty of domain entities.
- **Gate:** `make up && make migrate` exits `0` from an empty database; `make migrate &&
  make check-db` exits `0` and is safe at head; `.venv/bin/pytest tests/integration/db`
  exits `0` against PostgreSQL, not SQLite; `git diff --check` exits `0`.

## 3. `A2` — local services

- **Owns:** `infra/local/**`
- **Spec:** `docs/program/tasks/P1-INF-01.md`
- **Delivers:** Compose PostgreSQL and MinIO at pinned image digests, never a floating tag;
  health checks; network and volume names derived from `FOUNDATION_INSTANCE`; idempotent
  private-bucket initialization using the frozen `S3_BUCKET`; `infra/local/check_services.py`
  proving service health and bucket initialization and making **no** claim about the
  application migration head or the BlobStore; start/stop/troubleshooting documentation
- **Gate:** `make up` exits `0` and both services become healthy with no manual step;
  `make check-services` exits `0`; `make down && make up && make check-services` exits `0`
  with this instance's volumes intact; anonymous bucket list, read and write are **denied**;
  a second bucket-initialization attempt is a no-op; `git diff --check` exits `0`.

## 4. `A3` — BlobStore port and S3 adapter

- **Owns:** `src/auditmanager/storage/**`
- **Spec:** `docs/program/tasks/P1-STO-01.md`
- **Delivers:** typed BlobStore port with explicit storage errors; S3 adapter implementing
  temporary upload, metadata and hash verification, publication, inspection and read;
  opaque `blob_id` with the object-key layout confined to the adapter;
  `src/auditmanager/storage/check.py` for `make check-storage`; real-service tests for
  success, wrong checksum, unavailable service and repeated publication of identical
  verified content
- **`temporary -> verify -> publish` is the whole point.** A checksum or size mismatch
  leaves nothing canonical. There is no filesystem fallback. Bucket and key never appear in
  a public return model or in error text.
- **Ownership note:** Gate B's `B1` will extend this tree with the blob-metadata repository
  only. Leave the port and the adapter shaped so that is an addition, not a rewrite.
- **Gate:** `make up && make check-storage` exits `0`;
  `.venv/bin/pytest tests/integration/storage` exits `0` against MinIO including the
  negative paths; `git diff --check` exits `0`.

## 5. `A4` — synthetic AR corpus

- **Owns:** `fixtures/synthetic/ar/**`, `tools/fixtures/**`, `tests/contract/fixtures_ar/**`
- **Spec:** `docs/program/tasks/P2-BHV-01.md`
- **Delivers:** a generator and a committed synthetic Russian-language AR PDF with an
  embedded text layer containing **two cross-page contradictions** (for example two
  different fire-resistance classes, and two different evacuation-exit counts stated on
  different pages), **one explicit placeholder** (`TBD` / `уточнить`), and clean control
  statements that must not be flagged; an expected-issues manifest naming each seeded issue
  with its page and exact quotation; negative fixtures — encrypted, image-only, over 25 MiB,
  over 30 pages
- **The manifest is the acceptance oracle for the whole programme.** Every seeded quotation
  must be recoverable character-for-character from the extracted text layer, or the
  grounding gate in Gate B cannot be trusted. Assert this, do not assume it.
- **No customer or production bytes.** Synthetic only.
- **Gate:** the generator reproduces the committed PDF deterministically; a test asserts
  every manifest quotation is present in the extracted text at its declared page; the
  negative fixtures are each rejected by the envelope rule they violate;
  `git diff --check` exits `0`.

## 6. `A1b` and `A5` — held

`A1b` owns `db/migrations/**` (product tables, extending `A1a`'s head),
`contracts/api/v1/**` and `docs/program/P02_SEAMS.md`. `A5` owns the `web/` toolchain,
`web/src/app/**` and `web/src/shared/**`, and generates the typed client from `A1b`'s
OpenAPI document.

Both are ready to brief and neither is dispatched until the owner rules `OD-14`. If the
ruling is that the CP-00 supersession must complete first, Gate A still delivers a running
foundation and Gate B is what waits.

## 7. Gate A closes when

On one clean, dedicated integration instance that no authoring session is using:

1. `make bootstrap` twice — exit `0`, no lock or tracked file changes on the second run;
2. `make foundation` — exit `0`;
3. `make down && make up && make check-services && make check-db && make check-storage` —
   exit `0`, migrated state and a published test object intact;
4. anonymous bucket access denied; a corrupt upload publishes nothing;
5. every seeded quotation in the AR manifest recoverable from the extracted text layer;
6. `.venv/bootstrap/bin/python scripts/validate_bootstrap.py` — exit `0`, `PASS`;
7. `git diff --check` — exit `0`.

With `A1b` and `A5` released, add: the seam document frozen at a named commit, the OpenAPI
document validating, and `npm --prefix web ci && npm --prefix web run build` exiting `0`.

**Do not measure during the fan-out.** These suites copy the working tree and will report
another session's state. Acceptance runs serially, after the authoring sessions are done.
