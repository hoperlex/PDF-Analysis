# Architecture lint rules

**Task:** `W0-ARC-02` - **wave:** W0.3 - **checkpoint:** CP-00 - **base commit:**
`43a84d93fd544573226b82860ab24f924ed66d83`

**Status: specification only, candidate, not ratified.** This document states what must
be detectable. It implements no linter, selects no tool, runs no enforcement and makes
**no claim that the repository satisfies any rule**. Enforcement is `W1-ARC-01`.

The machine form of this document is
[ARCHITECTURE_LINT_RULES.json](ARCHITECTURE_LINT_RULES.json); the two are generated from
one source and are checked against each other by GATE-A below. Where they disagree, the
JSON is the contract.

Every command in this document runs under the locked validation interpreter
`.venv/bootstrap/bin/python`. A bare `python` or `python3` is never used.

## 1. Frozen inputs

- base commit `43a84d93fd544573226b82860ab24f924ed66d83`;
- architectural prohibitions: [AGENTS.md](../../AGENTS.md) section 4;
- accepted CP-00 architecture review:
  [CP00_ARCHITECTURE_REVIEW.md](CP00_ARCHITECTURE_REVIEW.md) and
  [CP00_ARCHITECTURE_REVIEW.json](CP00_ARCHITECTURE_REVIEW.json);
- recorded owner decisions: [CP00_OWNER_DECISIONS.md](CP00_OWNER_DECISIONS.md);
- [ARCHITECTURE_BIBLE.md](ARCHITECTURE_BIBLE.md),
  [ADR-0004](adr/ADR-0004-repository-layout-and-module-boundaries.md),
  [ADR-0016](adr/ADR-0016-testing-evidence-model.md);
- [REPOSITORY_LAYOUT.md](REPOSITORY_LAYOUT.md).

No rule is invented beyond these. Each rule names the input it derives from in its
`source_anchor`, lists the repository path of every input it cites in `anchor_files`,
and GATE-E resolves each of those paths at the base commit.

## 2. Vocabulary

| Field | Meaning |
|---|---|
| `static` | Decidable by inspecting repository files without executing the application: import graph, module and symbol names, declaration shapes, path layout, JSON keys. |
| `test` | Decidable mechanically, but only by running something - regenerating an artifact, applying migrations to a database. |
| `review` | Not mechanically decidable. The violation is a property of meaning, role, ordering or design intent. The rule records **why** a checker cannot decide it. |
| `error` | Blocks the change once enforcement exists. |
| `warning` | Reported and tracked, does not block. Used only where the frozen input states discipline rather than an invariant, and the rule carries a `severity_rationale`. |

A rule that cannot be decided mechanically is marked `review`. It is never dropped and
never relabelled `warning` to look enforceable: `warning` is a statement about blocking,
not about decidability, and eight of the ten prohibitions keep a `review` component for
exactly this reason.

## 3. Coverage of AGENTS.md section 4

All ten prohibitions are declared and covered. `yes` means the whole prohibition is
mechanically decidable; `partial` means a static rule covers a decidable shape while the
operative clause stays `review`.

| ID | Prohibition | Statically decidable | Rules | Why the remainder is review-only |
|---|---|---|---|---|
| AG4-01 | direct SQL/S3/filesystem from a router or React component | yes | ALR-01, ALR-02, ALR-03, ALR-04 | Decidable at the import, annotation and call-shape level. A router that delegates to a project helper which itself performs the I/O is caught only when that helper is itself in scope; no whole-program call graph is assumed. |
| AG4-02 | business logic in an ORM/Pydantic/transport schema/UI | partial | ALR-08, ALR-09 | The dependency direction into schema, model and component modules is static (ALR-08). Whether a conditional is a transport check or a domain invariant is a semantic judgment and stays review-only (ALR-09). |
| AG4-03 | deep imports into the internals of another bounded context | yes | ALR-05, ALR-06, ALR-07 | Fully decidable from the import graph plus the declared layout: backend cross-context imports (ALR-05), frontend FSD layer and slice direction (ALR-06) and the shared layer (ALR-07). |
| AG4-04 | generic repository/base service/global utils without proven semantics | partial | ALR-10, ALR-11, ALR-32 | The three names the Bible spells out are static (ALR-10). The operative clause 'without proven semantics' is P-14's two-independent-applications-or-mandatory-boundary judgment and stays review-only (ALR-11, ALR-32). |
| AG4-05 | job state held only in memory | partial | ALR-12, ALR-13 | A module-level or class-level container that holds job, run, attempt or progress execution state is a static shape (ALR-12); a constant table of the same Python type is not. 'Only in memory' is a claim about which copy answers a status query and about ordering against the side effect, and so is the residue of which unflagged container actually holds state; both stay review-only (ALR-13). |
| AG4-06 | path/filename/display number used as identity | partial | ALR-14, ALR-15 | Identifier values derived from a path, filename or ordinal are a static shape (ALR-14). Whether a value is used in the role of identity is semantic and stays review-only (ALR-15). |
| AG4-07 | dual-write to the database plus an external side effect without outbox/reconciliation | partial | ALR-16, ALR-17 | An external side effect inside a transaction block is static (ALR-16). Whether an effect outside the transaction has a matching outbox record and a reconciliation owner is operational design and stays review-only (ALR-17). |
| AG4-08 | silent fallback | partial | ALR-18, ALR-19 | Swallowed exceptions and empty catch blocks are static (ALR-18). Silent fallback in general is a statement about the meaning of a result: the same returned default is a declared partial in one contract and a swallowed failure in another, which is why the CP-00 review maps FS-01 to FS-08 case by case (ALR-19). |
| AG4-09 | LLM output treated as the canonical expert decision | partial | ALR-20, ALR-21 | An AI or analysis module importing a decision-write surface is static (ALR-20). Whether a stored recommendation is consumed as the canonical verdict is a property of the read model's meaning and stays review-only (ALR-21). |
| AG4-10 | modification of raw deterministic comparison evidence by the AI layer | partial | ALR-22, ALR-23 | A write or delete on a raw-evidence artifact from an AI module is static (ALR-22). Re-derivation republished under the same artifact identity preserves every syntactic constraint and stays review-only (ALR-23). |

## 4. Rule set

Every rule appears once in this table and once, in more detail, in section 5.

| ID | Rule | Enforcement | Severity | Positive example (compliant) | Negative example (violating) |
|---|---|---|---|---|---|
| ALR-01 | A router or HTTP transport module never executes SQL and never touches an ORM session, connection or engine. | `static` | `error` | `async def list_runs(uc: ListRuns = Depends(get_list_runs)): return await uc.execute(query)` | `async def list_runs(session: AsyncSession = Depends(get_session)): return await session.execute(text('select * from runs'))` |
| ALR-02 | Only the storage adapter imports an object-storage SDK or builds or parses an object key; routers, application code, domain code and UI know blob_id, role, size, sha256 and media type. | `static` | `error` | `url = await self.storage.presigned_read(blob_id=version.blob_id, ttl_seconds=300)` | `url = s3.generate_presigned_url('get_object', Params={'Bucket': 'audit', 'Key': f'projects/{project_id}/v1.pdf'})` |
| ALR-03 | A router or HTTP transport module performs no filesystem I/O; bytes reach it through the storage port. | `static` | `error` | `stream = await self.storage.open_read(blob_id)` | `data = open(f'/var/audit/{project_id}/report.pdf', 'rb').read()` |
| ALR-04 | A React component performs no data access: no database or object-storage SDK, no node filesystem module and no raw HTTP outside the generated transport in web/src/shared/api. | `static` | `error` | `const { data } = useRunsQuery({ projectId });` | `const data = await fetch('/api/v1/runs?project=' + projectId).then(r => r.json());` |
| ALR-05 | A backend bounded context imports another context only through that context's public module; any deeper target is a violation. | `static` | `error` | `from auditmanager.documents.public import DocumentSummary` | `from auditmanager.documents.adapters.persistence.models import DocumentRow` |
| ALR-06 | Frontend imports run strictly downward through the layer order app, _app, _pages, widgets, features, entities, shared, and reach another slice only through that slice's public entry. | `static` | `error` | `import { RunStatusBadge } from 'entities/run';` | `import { useRunFilters } from 'features/run-filter/model/useRunFilters';` |
| ALR-07 | A shared module imports no bounded context and no domain slice; the dependency arrow into shared is one-way. | `static` | `error` | `shared/checksum.py: class Checksum(Protocol) with def hexdigest(self) -> str, importing only the standard library` | `from auditmanager.findings.domain.finding import Finding` |
| ALR-08 | ORM models, transport schemas and UI components do not import application or domain modules and do not call repositories or ports. | `static` | `error` | `class RunOut(BaseModel) declaring run_id: str and status: Literal of the five declared run states` | `class RunOut(BaseModel) declaring def is_billable(self) that calls pricing_repository.rate_for(self.tenant)` |
| ALR-09 | No business rule is decided in an ORM model, a Pydantic or transport schema, or a UI component. | `review` | `error` | `Reviewer records: the schema declares types and ranges only; the eligibility decision lives in the application handler.` | `Reviewer records: the schema validator rejects a finding whose severity is below the tenant threshold, which is a domain rule executed in transport.` |
| ALR-10 | The names the Bible forbids do not appear: BaseService, GenericRepository and their variants as classes, and utils, helpers, common or misc as catch-all modules under shared. | `static` | `error` | `src/auditmanager/shared/checksum.py exporting Sha256 and verify_sha256` | `src/auditmanager/shared/utils.py exporting normalize, to_dict, retry and parse_any` |
| ALR-11 | An abstraction is introduced only after two independent applications or because it is a mandatory boundary, and it carries a declared semantics. | `review` | `error` | `Reviewer records: the retry decorator has two independent callers, the storage adapter and the provider adapter, and its semantics are declared as bounded, error-class aware retry.` | `Reviewer records: the new AggregateRoot base class has one subclass and implements no declared boundary.` |
| ALR-12 | Job, run, attempt and progress state is never held in a module-level or class-level mutable container. | `static` | `error` | `status = await self.jobs.get_attempt_status(attempt_id)` | `ACTIVE_TASKS: dict[str, asyncio.Task] = {}` |
| ALR-13 | A durable Job and Attempt record exists before any side effect, process memory and progress transport are never a status source, and the attempt's execution_token is verified inside the publishing transaction. | `review` | `error` | `Reviewer records: the attempt row is inserted and committed before the provider call, and publish compares the stored execution_token inside the same transaction that writes the result.` | `Reviewer records: the worker sends the provider request first and inserts the attempt row afterwards, so a crash in between leaves an effect with no durable record.` |
| ALR-14 | No identifier is constructed from, or resolved through, a path, a filename or a display ordinal, and identifiers are compared only by equality. | `static` | `error` | `project_id = ProjectId(request.path_params['project_id'])` | `project_id = Path(upload.filename).stem.removesuffix('.pdf')` |
| ALR-15 | Identity resolution is an explicit typed lookup; an unresolvable identifier yields a typed error and never a guessed alternative form, and human or display numbers stay presentation fields. | `review` | `error` | `Reviewer records: an unknown project identifier returns the typed error project_not_found with a correlation id and no second lookup is attempted.` | `Reviewer records: the lookup misses, the code appends the pdf extension and looks up again, so two different inputs resolve to one entity.` |
| ALR-16 | Inside a database transaction or unit of work there is no external side effect; the intent is appended to the outbox and executed after commit. | `static` | `error` | `async with self.uow: the handler calls self.runs.add(run) and then self.outbox.append(RunPublished(run_id=run.id))` | `async with self.uow: the handler calls self.runs.add(run) and then await self.storage.put(blob_id, payload)` |
| ALR-17 | Every external side effect paired with a database mutation has an outbox record and a named reconciliation or recovery procedure with an owner. | `review` | `error` | `Reviewer records: the export publication intent is an outbox row, the dispatcher is at-least-once and idempotent by export_id, and the reconciliation job is named with its owner.` | `Reviewer records: the provider webhook is sent by the request handler after commit with no record of the intent, so a crash loses it with no way to detect the loss.` |
| ALR-18 | No caught error is discarded: a handler re-raises, maps to a typed error, or returns a declared partial or degraded result that the caller can observe. | `static` | `error` | `except ProviderTimeout as exc: raise AnalysisUnavailable(correlation_id=ctx.correlation_id) from exc` | `except Exception: return an empty list` |
| ALR-19 | An unknown or failed contract, auth, norm, provider or stage state resolves to a typed failure, a declared partial, or a named, observable and temporary degraded mode; no path resolves a failure to success. | `review` | `error` | `Reviewer records: the export omits a declared member, so the response is partial with a stable error code and the manifest lists the missing member.` | `Reviewer records: the embedded workbook failed to render, the archive was produced without it and the response is success.` |
| ALR-20 | Analysis, model-provider and AI synthesis modules never write an expert decision or the verdict projection; their output is a recommendation artifact. | `static` | `error` | `await self.recommendations.add(Recommendation(finding_id=f.id, model_call_id=call.id))` | `await self.decisions.append(DecisionEvent(finding_id=f.id, verdict='confirmed', actor='llm'))` |
| ALR-21 | LLM output is a recommendation; the canonical expert verdict is a projection of append-only decision events, and a revocation projects the current verdict to pending without restoring a superseded one. | `review` | `error` | `Reviewer records: the verdict projection is built from decision events only; recommendations are joined for display and are labelled.` | `Reviewer records: when no human decision exists the projection falls back to the model recommendation and presents it in the verdict column.` |
| ALR-22 | Raw deterministic comparison evidence is write-once for the AI layer: an AI module never writes, deletes, overwrites or recomputes the checksum of a raw evidence artifact. | `static` | `error` | `await self.artifacts.add(AiReview(source_checksum=raw.sha256, revision=raw.revision))` | `await self.artifacts.update(raw.id, body=ai_summary, sha256=sha256(ai_summary))` |
| ALR-23 | AI output stays a separate versioned derived artifact that references the source checksum; it is never republished under the identity of the raw evidence. | `review` | `error` | `Reviewer records: the AI review artifact has its own id and revision and names the raw diff checksum it was derived from.` | `Reviewer records: the AI summary is written into the diff artifact record so consumers reading raw evidence receive synthesis.` |
| ALR-24 | A machine contract declares its version under contract_version; a bare version key and a schema_version envelope key are violations. | `static` | `error` | `"contract_version": "1.0.0-draft.1"` | `"schema_version": 1` |
| ALR-25 | The attempt fencing capability is named execution_token, is opaque and is compared only for equality; fencing_token, fence_token and a numeric or ordered token are violations. | `static` | `error` | `"execution_token": {"type": "string", "minLength": 16}` | `"fencing_token": {"type": "integer"}` |
| ALR-26 | Until W5-OPT-01 is accepted, the four project-optimization names are declared nowhere as a stage, status, endpoint, package or capability. | `static` | `error` | `"excluded_reason": "PD-05 moves optimization_review to the project-optimization sub-pipeline"` | `"stage_id": "optimization_review"` |
| ALR-27 | Backend test modules live under tests/; a test module or a test-framework import inside src/auditmanager/ is a violation. | `static` | `error` | `tests/contract/test_stage_registry.py` | `src/auditmanager/jobs/test_lease.py` |
| ALR-28 | No release, checkpoint or merge gate uses a coverage percentage as its sole proof; each gate names the ADR-0016 evidence classes it rests on. | `review` | `error` | `Reviewer records: the checkpoint names characterization, contract and manual runbook evidence, each with a produced artifact.` | `Reviewer records: the release gate is the coverage threshold and nothing else is required to be green.` |
| ALR-29 | A module sublayer exists only when a real use case populates it; a sublayer directory holding only an init file or a placeholder is a violation. | `static` | `warning` | `src/auditmanager/jobs/application/lease_attempt.py exists together with the application package` | `src/auditmanager/jobs/application/ contains only an init file` |
| ALR-30 | Concrete adapters are constructed only in the composition root; domain and application code receives ports as parameters and no module resolves a dependency from a global container or service locator. | `static` | `error` | `def build_run_service(storage: StoragePort, runs: RunRepository) -> RunService: ...` | `def handle(cmd): storage = S3StorageAdapter(settings.bucket); ...` |
| ALR-31 | The generated TypeScript API client is byte-identical to a fresh generation from the committed OpenAPI document; a hand edit is a violation. | `test` | `error` | `The regeneration job reports no diff against web/src/shared/api` | `A response type in the committed client gains an extra optional field that the OpenAPI document does not declare` |
| ALR-32 | A shared module holds only genuinely cross-cutting primitives; a domain-specific helper placed there for convenience is a violation. | `review` | `error` | `Reviewer records: shared/clock.py exposes a Clock protocol used as a port by several contexts and encodes no rule.` | `Reviewer records: shared/finding_merge.py encodes the merge policy of the findings context and was placed in shared to avoid an import.` |
| ALR-33 | Migrations are forward-only and re-runnable, a breaking data change follows expand, backfill, switch and contract, and a down path is never the recovery procedure. | `test` | `error` | `The chain applies to an empty and to a seeded database and the head re-applies with no change` | `The rollback runbook instructs the operator to run the down migration to recover` |

## 5. Rule details

### ALR-01 - router-no-sql

- **Statement:** A router or HTTP transport module never executes SQL and never touches an ORM session, connection or engine.
- **Source:** AGENTS.md section 4 bullet 1; ARCHITECTURE_BIBLE.md section 5 backend dependency rule; ADR-0004 module boundaries
- **Scope:** `src/auditmanager/api/**`, `src/auditmanager/*/adapters/http/**`
- **Enforcement / severity:** `static` / `error`
- **Covers:** AG4-01
- **Detection:** In a module in scope, flag: (a) an import of a database driver or ORM package (sqlalchemy, psycopg, asyncpg, sqlite3, databases); (b) a parameter, attribute or annotation typed Session, AsyncSession, Connection or Engine; (c) a string literal matching the SQL statement pattern select/insert/update/delete/create/alter/drop/with at the start, case-insensitive, that is passed as a call argument. A compliant router references only application command and query handlers plus typed transport DTOs.
- **Not a violation:** A use-case object with an execute method is not a session: no database symbol is imported or annotated, so nothing is flagged. A route path or an error message containing the word select is a string, not a statement passed to a call. Modules under tests/** are out of scope.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.

### ALR-02 - object-storage-key-only-in-adapter

- **Statement:** Only the storage adapter imports an object-storage SDK or builds or parses an object key; routers, application code, domain code and UI know blob_id, role, size, sha256 and media type.
- **Source:** AGENTS.md section 4 bullet 1; ARCHITECTURE_BIBLE.md section 7 storage rules; P-02
- **Scope:** `src/auditmanager/**`, `web/src/**`
- **Enforcement / severity:** `static` / `error`
- **Covers:** AG4-01
- **Detection:** Outside src/auditmanager/storage/adapters/**, flag: an import of boto3, aioboto3, botocore, minio or an equivalent object-storage client; a call to a presign, put_object, get_object or upload_fileobj method; and a string literal or f-string that starts with the s3 URI scheme or concatenates a bucket name with a key path. Inside the storage adapter these are the intended shapes.
- **Not a violation:** Passing a blob_id, role, size, sha256 or media type across a port is the intended shape and carries no key. A signed URL received from the storage port and returned to the client is a value, not a key construction. infra/** deployment descriptors are not application code.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.

### ALR-03 - router-no-filesystem

- **Statement:** A router or HTTP transport module performs no filesystem I/O; bytes reach it through the storage port.
- **Source:** AGENTS.md section 4 bullet 1; ARCHITECTURE_BIBLE.md P-06 side effects at edges
- **Scope:** `src/auditmanager/api/**`, `src/auditmanager/*/adapters/http/**`
- **Enforcement / severity:** `static` / `error`
- **Covers:** AG4-01
- **Detection:** In a module in scope, flag a call to open, os.remove, os.makedirs, shutil.copy, shutil.rmtree or tempfile.NamedTemporaryFile, a pathlib.Path constructed from a request value, and any read_text, write_text, read_bytes or write_bytes call. Streaming a response from a storage port iterator is not filesystem access.
- **Not a violation:** A pathlib import used only inside an if TYPE_CHECKING block for a port signature performs no I/O. Reading a static OpenAPI document at process start belongs to the composition root, not to a router. Modules under tests/** are out of scope.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.

### ALR-04 - react-no-data-access

- **Statement:** A React component performs no data access: no database or object-storage SDK, no node filesystem module and no raw HTTP outside the generated transport in web/src/shared/api.
- **Source:** AGENTS.md section 4 bullet 1; ARCHITECTURE_BIBLE.md section 10 frontend rules; ADR-0009
- **Scope:** `web/src/**`
- **Enforcement / severity:** `static` / `error`
- **Covers:** AG4-01
- **Detection:** Flag in any module under web/src/** except web/src/shared/api/**: an import of node:fs, fs, path, pg, mysql, or an aws-sdk client package; and a direct call to fetch, axios or XMLHttpRequest. A component obtains server state from a query hook that calls the generated transport.
- **Not a violation:** The generated transport under web/src/shared/api/** is the single place fetch appears. A bounded client island opening a WebSocket for live progress is a declared exception in the Bible section 10 and is not raw HTTP. Test doubles and mock servers under tests/** are out of scope.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.

### ALR-05 - backend-cross-context-public-only

- **Statement:** A backend bounded context imports another context only through that context's public module; any deeper target is a violation.
- **Source:** AGENTS.md section 4 bullet 3; ADR-0004 Decision; ADR-0002 Boundary; REPOSITORY_LAYOUT.md backend module shape
- **Scope:** `src/auditmanager/**`
- **Enforcement / severity:** `static` / `error`
- **Covers:** AG4-03
- **Detection:** Resolve every absolute and relative import in src/auditmanager/A/** that targets src/auditmanager/B/** with A different from B and B not equal to shared. The only admissible target module is auditmanager.B.public. Any import of auditmanager.B.domain, .application, .ports, .adapters or a submodule of them is a violation, including an import guarded by TYPE_CHECKING.
- **Not a violation:** auditmanager.shared is cross-cutting and importable by every context; its own direction is governed by ALR-07. src/auditmanager/bootstrap/** is the composition root and wires concrete adapters of every context by design. A contract event payload type published under contracts/** is a contract, not a context internal.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.

### ALR-06 - frontend-fsd-import-direction

- **Statement:** Frontend imports run strictly downward through the layer order app, _app, _pages, widgets, features, entities, shared, and reach another slice only through that slice's public entry.
- **Source:** AGENTS.md section 4 bullet 3; ADR-0004 Decision (FSD upward and cross-slice imports); ARCHITECTURE_BIBLE.md section 10; ADR-0009
- **Scope:** `web/src/**`
- **Enforcement / severity:** `static` / `error`
- **Covers:** AG4-03
- **Detection:** Assign every module its layer from its path. Flag an import whose target layer is the same as or above the importer's layer, except an import inside the importer's own slice. Flag an import that reaches past a slice's public entry into its internal folders. app/page.tsx may only re-export or render a _pages entry.
- **Not a violation:** External packages such as react and next/* carry no layer and are never flagged. A module importing its own sibling inside the same slice is intra-slice, not cross-slice. shared is the lowest layer and may be imported from everywhere.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.

### ALR-07 - shared-imports-no-context

- **Statement:** A shared module imports no bounded context and no domain slice; the dependency arrow into shared is one-way.
- **Source:** REPOSITORY_LAYOUT.md Shared; ARCHITECTURE_BIBLE.md section 5 and P-14; AGENTS.md section 4 bullet 3
- **Scope:** `src/auditmanager/shared/**`, `web/src/shared/**`
- **Enforcement / severity:** `static` / `error`
- **Covers:** AG4-03
- **Detection:** Flag any import in src/auditmanager/shared/** that targets auditmanager.<context> for any context other than shared, and any import in web/src/shared/** that targets _app, _pages, widgets, features or entities. A TYPE_CHECKING-guarded import is still a dependency and is flagged.
- **Not a violation:** Third-party packages and the standard library are not contexts. A generic protocol defined in shared and implemented by a context creates no import from shared. Whether the primitive belongs in shared at all is a separate, semantic question carried by ALR-32.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.

### ALR-08 - schema-layer-no-domain-import

- **Statement:** ORM models, transport schemas and UI components do not import application or domain modules and do not call repositories or ports.
- **Source:** AGENTS.md section 4 bullet 2; ARCHITECTURE_BIBLE.md section 5 backend dependency rule
- **Scope:** `src/auditmanager/*/adapters/persistence/**`, `src/auditmanager/api/schemas/**`, `src/auditmanager/*/adapters/http/schemas/**`, `web/src/**`
- **Enforcement / severity:** `static` / `error`
- **Covers:** AG4-02
- **Detection:** Flag a runtime import of auditmanager.<context>.domain or auditmanager.<context>.application from a module in scope, and any call to a repository, unit-of-work or port symbol inside an ORM model class body, a Pydantic model body, a validator, or a React component body. Mapping code that converts a row or a DTO into a plain value object is not a call.
- **Not a violation:** An import guarded by if TYPE_CHECKING that is used only in annotations creates no runtime coupling and is not flagged. Importing a typed identifier or checksum primitive from auditmanager.shared is allowed. Field type, format, length and range constraints are transport validation, not a domain call.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.

### ALR-09 - no-business-logic-in-schema-or-ui

- **Statement:** No business rule is decided in an ORM model, a Pydantic or transport schema, or a UI component.
- **Source:** AGENTS.md section 4 bullet 2; ARCHITECTURE_BIBLE.md section 5 and section 10
- **Scope:** `src/auditmanager/*/adapters/persistence/**`, `src/auditmanager/api/schemas/**`, `src/auditmanager/*/adapters/http/schemas/**`, `web/src/**`
- **Enforcement / severity:** `review` / `error`
- **Covers:** AG4-02
- **Detection:** The reviewer reads each changed schema, model or component and asks whether it decides something the domain owns: eligibility, a state transition, an authorization outcome, a merge or carryover policy, a cost or budget outcome, or an invariant that must hold regardless of transport. Any such decision is a violation even when it is expressed as a validator, a computed property or a rendering condition.
- **Not a violation:** Type, format, length, range and required checks are transport validation. Presentation formatting of a value the backend already decided is not a business rule. A disabled button that mirrors a permission the server already enforced is presentation, provided the server enforcement exists.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.
- **Why review-only:** No syntactic property separates a transport check from a domain invariant. The same conditional is validation in one context and an owned rule in another, and deciding which requires the domain model, not the file.

### ALR-10 - forbidden-generic-abstraction-names

- **Statement:** The names the Bible forbids do not appear: BaseService, GenericRepository and their variants as classes, and utils, helpers, common or misc as catch-all modules under shared.
- **Source:** AGENTS.md section 4 bullet 4; ARCHITECTURE_BIBLE.md P-14
- **Scope:** `src/auditmanager/**`, `web/src/**`
- **Enforcement / severity:** `static` / `error`
- **Covers:** AG4-04
- **Detection:** Flag a class named BaseService, BaseRepository, GenericRepository, AbstractService or BaseManager anywhere in scope, and a module or package named utils, helpers, common or misc directly under src/auditmanager/shared/** or web/src/shared/**.
- **Not a violation:** A module named for its concept, such as shared/errors.py, shared/ids.py or shared/clock.py, is not a dumping ground and is not flagged. A third-party package that happens to be named utils is not repository code. Helper modules under tests/** and fixtures/** are out of scope. Whether an abstraction with an acceptable name is premature is a separate, semantic question carried by ALR-11.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.

### ALR-11 - abstraction-requires-proven-semantics

- **Statement:** An abstraction is introduced only after two independent applications or because it is a mandatory boundary, and it carries a declared semantics.
- **Source:** AGENTS.md section 4 bullet 4; ARCHITECTURE_BIBLE.md P-14; REPOSITORY_LAYOUT.md backend module shape
- **Scope:** `src/auditmanager/**`, `web/src/**`
- **Enforcement / severity:** `review` / `error`
- **Covers:** AG4-04
- **Detection:** For each new base class, generic wrapper, shared helper or framework-like layer, the reviewer names the two independent applications that already exist, or the mandatory boundary it implements, and the semantics it guarantees. Absence of that record is the violation.
- **Not a violation:** A port or protocol at a declared architectural boundary is mandatory by definition and needs no second application. An abstraction introduced together with its second real caller in the same change satisfies the rule.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.
- **Why review-only:** Counting import sites does not establish that two applications are independent, and mandatory boundary is an architectural judgment. A checker cannot decide whether a base class carries proven semantics or is premature framework.

### ALR-12 - no-module-level-job-state

- **Statement:** Job, run, attempt and progress state is never held in a module-level or class-level mutable container.
- **Source:** AGENTS.md section 4 bullet 5; ARCHITECTURE_BIBLE.md section 8 jobs and execution; P-09
- **Scope:** `src/auditmanager/jobs/**`, `src/auditmanager/workers/**`, `src/auditmanager/analysis/**`, `src/auditmanager/api/**`
- **Enforcement / severity:** `static` / `error`
- **Covers:** AG4-05
- **Detection:** Flag a module-level or class-level mutable container in scope only where it holds execution state: (a) its elements are asyncio task handles, futures, threads, or per-identifier locks, events or semaphores; or (b) its elements are job, run, attempt, stage-execution or progress records, statuses, counters or timestamps, read off the value annotation (dict[str, Attempt], dict[JobId, RunStatus], list[ProgressEvent]) or off the name of the binding (ACTIVE_RUNS, _JOB_STATE, PROGRESS_BY_ATTEMPT, LAST_HEARTBEAT). In both cases the container must also be mutated after its definition somewhere in scope: an assignment to an index, a del, or a call to append, add, update, setdefault, pop or clear. That mutation is what separates a state container from a table built once and only read, and a container that is never mutated is not flagged. Flag any read of a flagged container in a code path that produces an API response, a status projection or a scheduling decision.
- **Not a violation:** An immutable lookup table annotated Final and built from literals or frozen tuples is a constant, not state. A constant lookup table is not flagged for being a dict, a list or a set: a stage-name map, an error-code table, or a registry whose values are types or callables, holds no execution state. This rule does not flag a container merely for being mutable in principle. A container created inside a function and not escaping it is local state. Whether a container this rule did not flag is nevertheless where job, run, attempt or progress state actually lives is a semantic question and belongs to ALR-13, which is review. Modules under tests/** are out of scope.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.

### ALR-13 - durable-job-state-and-fencing

- **Statement:** A durable Job and Attempt record exists before any side effect, process memory and progress transport are never a status source, and the attempt's execution_token is verified inside the publishing transaction.
- **Source:** AGENTS.md section 4 bullet 5; ARCHITECTURE_BIBLE.md section 8; ADR-0007 with its adapt qualification; owner decision PD-03; integration decision ID-02; CP00_ARCHITECTURE_REVIEW.md FS-06
- **Scope:** `src/auditmanager/jobs/**`, `src/auditmanager/workers/**`, `src/auditmanager/analysis/**`, `src/auditmanager/api/**`, `contracts/domain/v1/**`, `contracts/analysis/v1/**`
- **Enforcement / severity:** `review` / `error`
- **Covers:** AG4-05
- **Detection:** For each execution path the reviewer traces the order of the durable write and the side effect, names which record answers a status query, and confirms that the publishing transaction reads and compares the execution_token of the attempt it is publishing for. A recovery after failover must be a declared transition creating a new Attempt of the same Job, never a new AuditRun. The reviewer also decides the two residues the static rules in this area deliberately leave. First, whether a module-level or class-level container that ALR-12 did not flag is nevertheless where job, run, attempt or progress state lives. Second, whether any declared value of another name - an epoch, a sequence, a counter or a version - is used as the authority of the current attempt, a role only the opaque, equality-compared execution_token may hold. No static rule carries any part of that second question: ALR-25 flags only the two names ID-02 renames and the numeric or ordered shape of execution_token itself, so every value whose authority role has to be established rather than read off a name arrives here.
- **Not a violation:** A progress projection rebuilt from durable events is allowed; it is not the source of truth but it may be the read path. An in-process cache in front of the durable record is allowed when the durable record remains the answer of record.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.
- **Why review-only:** Ordering between a durable write and a side effect, and the question of which copy answers a status query, are properties of an execution path rather than of a syntactic shape. Verification inside the publishing transaction depends on the transaction scope actually taken at run time. The two residues handed here by ALR-12 and ALR-25 are undecidable for the same reason: what a container holds and what role a field plays are established by the execution path that reads them, not by the declaration. A name is not a role, and neither is a neighbour - a field declared beside the authority token is not thereby an authority token, which is why no narrower name test was substituted for this one. The static rules stop at the shapes AGENTS.md section 4 bullet 5 and integration decision ID-02 actually name, and the role question is answered here.

### ALR-14 - no-path-derived-identity

- **Statement:** No identifier is constructed from, or resolved through, a path, a filename or a display ordinal, and identifiers are compared only by equality.
- **Source:** AGENTS.md section 4 bullet 6; ARCHITECTURE_BIBLE.md P-01 and P-02; CP00_ARCHITECTURE_REVIEW.md FS-07 and DV-08
- **Scope:** `src/auditmanager/**`, `web/src/**`
- **Enforcement / severity:** `static` / `error`
- **Covers:** AG4-06
- **Detection:** Flag an assignment to a name or field whose name ends in _id or Id, or which is annotated with a declared identifier type, whose value derives from a path or filename expression such as Path(...).stem, .name, os.path.basename, a split on a separator, or a removesuffix call, or from a display ordinal such as index, row_number or counter. Flag a comparison of two identifier-typed values using startswith, endswith or membership instead of equality.
- **Not a violation:** Building a storage key from an identifier is the allowed direction and lives in the storage adapter under ALR-02. Parsing a filename to produce a display label or an ingest hint is allowed when the result is never stored or compared as identity. Reading an identifier out of a request path parameter is transport binding, not derivation from a filesystem path.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.

### ALR-15 - typed-identity-resolution

- **Statement:** Identity resolution is an explicit typed lookup; an unresolvable identifier yields a typed error and never a guessed alternative form, and human or display numbers stay presentation fields.
- **Source:** AGENTS.md section 4 bullet 6; ARCHITECTURE_BIBLE.md P-01 and P-02; CP00_ARCHITECTURE_REVIEW.md FS-07
- **Scope:** `src/auditmanager/**`, `web/src/**`
- **Enforcement / severity:** `review` / `error`
- **Covers:** AG4-06
- **Detection:** The reviewer determines, for each value crossing a boundary, whether it is used in the role of identity, and confirms that resolution is a single typed lookup with a typed failure. The FS-07 shape, retrying a lookup with a stripped or appended extension after the first lookup misses, is a violation even though both lookups are typed.
- **Not a violation:** A display ordinal rendered next to a record is presentation and is not identity. A migration mapping legacy identifiers to new ones is explicit evidence, not a guessed alternative form.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.
- **Why review-only:** Whether a value plays the role of identity is semantic: the same string is a label in one call and a lookup key in another. The FS-07 fallback is only visible once that role is known.

### ALR-16 - no-external-side-effect-in-transaction

- **Statement:** Inside a database transaction or unit of work there is no external side effect; the intent is appended to the outbox and executed after commit.
- **Source:** AGENTS.md section 4 bullet 7; ARCHITECTURE_BIBLE.md P-07 and section 6; ADR-0007
- **Scope:** `src/auditmanager/**`
- **Enforcement / severity:** `static` / `error`
- **Covers:** AG4-07
- **Detection:** Determine the transaction blocks: a with or async with on a unit-of-work or session.begin object, or a function decorated as transactional. Inside such a block flag a call to an object-storage port write method, an HTTP or provider client, an event or broker publish, or a mail or webhook send. The admissible statement is an append to the outbox repository.
- **Not a violation:** Reading from an external system inside the transaction is not a dual write, although it holds the transaction open. Appending an outbox row is the intended shape and is never flagged. A side effect performed after commit is outside this rule and is governed by ALR-17.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.

### ALR-17 - outbox-and-reconciliation

- **Statement:** Every external side effect paired with a database mutation has an outbox record and a named reconciliation or recovery procedure with an owner.
- **Source:** AGENTS.md section 4 bullet 7; ARCHITECTURE_BIBLE.md P-07 and section 6; CP00_ARCHITECTURE_REVIEW.md FS-03
- **Scope:** `src/auditmanager/**`, `infra/runbooks/**`
- **Enforcement / severity:** `review` / `error`
- **Covers:** AG4-07
- **Detection:** For each pair of a database mutation and an external effect, the reviewer names the outbox record that carries the intent, the dispatcher that performs it, the retry and poison policy, and the reconciliation procedure that detects an effect without a record or a record without an effect.
- **Not a violation:** A read-only external call needs no outbox record. An effect that is idempotent and re-driven from the outbox needs no separate compensation, only a bounded retry policy.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.
- **Why review-only:** A checker sees the call site, not the operational design. It cannot tell whether the outbox row that exists corresponds to the effect that was performed, nor whether a reconciliation procedure exists and has an owner.

### ALR-18 - no-swallowed-error

- **Statement:** No caught error is discarded: a handler re-raises, maps to a typed error, or returns a declared partial or degraded result that the caller can observe.
- **Source:** AGENTS.md section 4 bullet 8; ARCHITECTURE_BIBLE.md P-10; CP00_ARCHITECTURE_REVIEW.md section 7
- **Scope:** `src/auditmanager/**`, `web/src/**`
- **Enforcement / severity:** `static` / `error`
- **Covers:** AG4-08
- **Detection:** Flag a bare except clause; an except body that is only pass or only a debug or info log; an except body that returns None, an empty container, zero or False without raising; in TypeScript an empty catch block, a catch that neither rethrows nor records, and a catch handler on a promise that returns a literal default.
- **Not a violation:** A handler that raises a typed adapter or domain error is the intended mapping shape. A retry loop that suppresses intermediate attempts and re-raises after the last one is compliant. A UI error boundary that renders an error state makes the failure visible and is compliant. A finally block is cleanup, not a handler.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with the declared, observable degraded mode that the suppressed path resolves to; a waiver may never produce a silent success, which ALR-19 forbids without exception. No self-service bypass.

### ALR-19 - no-silent-fallback

- **Statement:** An unknown or failed contract, auth, norm, provider or stage state resolves to a typed failure, a declared partial, or a named, observable and temporary degraded mode; no path resolves a failure to success.
- **Source:** AGENTS.md section 4 bullet 8; ARCHITECTURE_BIBLE.md P-10; CP00_ARCHITECTURE_REVIEW.md section 7 target policies FS-01 to FS-08
- **Scope:** `src/auditmanager/**`, `web/src/**`, `contracts/**`
- **Enforcement / severity:** `review` / `error`
- **Covers:** AG4-08
- **Detection:** For each failure path the reviewer names the resolved outcome and checks it against the target policy of the matching FS row: a required export member that is missing yields partial or failed (FS-01); a carryover failure is a declared state with a recorded failure class (FS-02); a projection build failure is a named degraded mode (FS-03); a degraded stage resolves to a declared non-success terminal state (FS-04-A); a failed optional optimization branch resolves the consuming run to partial and never to success (FS-04-C); a deterministic summary substituted for AI review is marked and states its provenance (FS-05).
- **Not a violation:** A declared partial with a stable error code is the intended outcome, not a fallback. A compatibility mode that is named, observable, time-boxed and owned is admissible under P-10.
- **Waiver:** none. CP00_ARCHITECTURE_REVIEW.md section 7 records that the no-silent-success rule binds FS-04-A, FS-04-B and FS-04-C in full and admits no exception.
- **Why review-only:** Silent fallback in the general case is a statement about the meaning of a result, not its shape. The same returned default is a declared partial in one contract and a swallowed failure in another, which is exactly why the CP-00 review maps FS-01 to FS-08 one at a time instead of by pattern.

### ALR-20 - ai-modules-no-decision-write

- **Statement:** Analysis, model-provider and AI synthesis modules never write an expert decision or the verdict projection; their output is a recommendation artifact.
- **Source:** AGENTS.md section 4 bullet 9; ARCHITECTURE_BIBLE.md P-18; ADR-0012; owner decision PD-01
- **Scope:** `src/auditmanager/analysis/**`, `src/auditmanager/comparison/**`, `src/auditmanager/workers/**`
- **Enforcement / severity:** `static` / `error`
- **Covers:** AG4-09
- **Detection:** Flag an import or call of a decision-write surface from a module in scope or from any module that imports a model-provider port: the append or revoke command of the decisions context, the verdict projection writer, and any repository write on the decision aggregate. Writing a recommendation record that references a finding is the admissible shape.
- **Not a violation:** Reading the current verdict projection for context is allowed. Modules of the decisions context itself are out of scope. A replay test that seeds decisions through the public command surface lives under tests/** and is out of scope.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.

### ALR-21 - llm-output-not-canonical-verdict

- **Statement:** LLM output is a recommendation; the canonical expert verdict is a projection of append-only decision events, and a revocation projects the current verdict to pending without restoring a superseded one.
- **Source:** AGENTS.md section 4 bullet 9; ARCHITECTURE_BIBLE.md P-18 and section 2; ADR-0012; owner decision PD-01 as approved with modification
- **Scope:** `src/auditmanager/**`, `contracts/**`, `web/src/**`
- **Enforcement / severity:** `review` / `error`
- **Covers:** AG4-09
- **Detection:** The reviewer follows the read path of the current verdict and confirms that it is a projection over decision events only, that no recommendation table feeds it, and that the interface presents a recommendation as a recommendation. A recommendation consumed as a verdict by a projection or by the UI is a violation even when no forbidden import exists.
- **Not a violation:** An AI recommendation displayed beside the verdict, clearly attributed, is the intended shape. An AI-suggested review flag that creates work for a human is not a verdict.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.
- **Why review-only:** Whether a stored value is consumed as the canonical verdict is a semantic role of the read model. A recommendation table can be projected as if it were a decision without any forbidden import appearing anywhere.

### ALR-22 - raw-evidence-write-once

- **Statement:** Raw deterministic comparison evidence is write-once for the AI layer: an AI module never writes, deletes, overwrites or recomputes the checksum of a raw evidence artifact.
- **Source:** AGENTS.md section 4 bullet 10; ARCHITECTURE_BIBLE.md P-17 and section 11; ADR-0013
- **Scope:** `src/auditmanager/comparison/**`, `src/auditmanager/analysis/**`
- **Enforcement / severity:** `static` / `error`
- **Covers:** AG4-10
- **Detection:** Flag, in a module that imports a model-provider port or lives under an AI or synthesis package, a storage write or delete on a blob whose declared role is a raw evidence role, a repository update or delete on the raw evidence record, and a checksum recomputation that overwrites the stored checksum. Creating a new derived artifact that references the source checksum is the admissible shape.
- **Not a violation:** The deterministic comparison stage that produces the artifact is its writer and is not an AI module. Retention or erasure of a whole retired comparison revision is a lifecycle operation, and its authority is the deferred ADR-0014. Reading the raw artifact and its checksum is always allowed.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.

### ALR-23 - ai-artifacts-stay-derived

- **Statement:** AI output stays a separate versioned derived artifact that references the source checksum; it is never republished under the identity of the raw evidence.
- **Source:** AGENTS.md section 4 bullet 10; ARCHITECTURE_BIBLE.md P-17 and section 11; ADR-0013; CP00_ARCHITECTURE_REVIEW.md FS-05
- **Scope:** `src/auditmanager/comparison/**`, `src/auditmanager/analysis/**`, `contracts/**`
- **Enforcement / severity:** `review` / `error`
- **Covers:** AG4-10
- **Detection:** The reviewer follows the provenance chain of every artifact a consumer may read as raw evidence and confirms that each AI artifact has its own identity, its own revision and a reference to the source checksum. Re-deriving an artifact and publishing it under the same identity, or copying an AI summary into a field consumers read as raw evidence, is a violation.
- **Not a violation:** A new AI revision produced for an unchanged raw artifact is normal, as long as it carries its own identity. A deterministic re-run that reproduces the raw artifact byte for byte is a deterministic stage output, not an AI write.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.
- **Why review-only:** The prohibition is about substance. Republishing under the same identity, or presenting a synthesis in a raw-evidence field, preserves every syntactic constraint; only the artifact's meaning and provenance chain decide it.

### ALR-24 - canonical-contract-version-key

- **Statement:** A machine contract declares its version under contract_version; a bare version key and a schema_version envelope key are violations.
- **Source:** Integration decision ID-01 recorded in CP00_ARCHITECTURE_REVIEW.md section 6.3 and CP00_OWNER_DECISIONS.md
- **Scope:** `contracts/**/*.json`
- **Enforcement / severity:** `static` / `error`
- **Detection:** Walk every JSON document under contracts/** and flag an object key named version or schema_version at any depth. The dialect key is not a version key and neither is the identity key; both keep their JSON Schema meaning.
- **Not a violation:** contract_version is the required key and is never flagged. A distinct domain field with its own name, such as a norms snapshot version field, is a different key and is not flagged. A string value that contains the word version is not a key. docs/** prose is out of scope.
- **Waiver:** granted by the repository owner, recorded by the program integrator, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with the integration decision it departs from, exact scope, expiry checkpoint and removal task. No self-service bypass.

### ALR-25 - canonical-execution-token-name

- **Statement:** The attempt fencing capability is named execution_token, is opaque and is compared only for equality; fencing_token, fence_token and a numeric or ordered token are violations.
- **Source:** Integration decision ID-02 recorded in CP00_ARCHITECTURE_REVIEW.md section 6.3; ADR-0007 with the adapt qualification recorded in that review; owner decision PD-03
- **Scope:** `contracts/**`, `src/auditmanager/**`, `web/src/**`
- **Enforcement / severity:** `static` / `error`
- **Detection:** Flag a declared field named fencing_token or fence_token in a contract schema or in code; flag an execution_token declared with a numeric type in a schema or annotated as an integer in code; and flag an ordering comparison - <, >, <=, >=, min, max, sorted - applied to an execution_token value. Those three shapes are the whole of this rule. No field is flagged for being named epoch, sequence, counter or version, in any position and next to any neighbour: ID-02 fixes the name of the attempt-authority token, and which value holds that role is not a syntactic property. The role question is ALR-13, which is review.
- **Not a violation:** A database sequence used internally by an adapter is not the domain token and is not a declared field. The name epoch is not part of this rule's detection. A created_epoch timestamp declared on an Attempt, a connection, session or gateway epoch, a unix time epoch, a cache or configuration generation: none of them is examined here, including when declared beside attempt_id or execution_token. Being declared next to the authority token is adjacency, not the authority role, and no owner decision bans the word epoch. The connection-epoch mechanism is recorded as DW-05 legacy evidence in the ADR-0007 row of CP00_ARCHITECTURE_REVIEW.md section 5, which states that no domain-level fencing_token field was established. It is an observed legacy behavior, not a target field, and is not relabelled by this rule. Whether a value of another name - an epoch, a sequence, a counter or a version - is in fact used as the authority of the current attempt is not decided here; that whole question is ALR-13, which is review. docs/** and fixtures/** records of legacy behavior are out of scope.
- **Waiver:** granted by the repository owner, recorded by the program integrator, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with the integration decision it departs from, exact scope, expiry checkpoint and removal task. No self-service bypass.

### ALR-26 - optimization-vocabulary-disabled

- **Statement:** Until W5-OPT-01 is accepted, the four project-optimization names are declared nowhere as a stage, status, endpoint, package or capability.
- **Source:** Owner decision PD-05 and obligation U-06-OB-1 recorded in CP00_ARCHITECTURE_REVIEW.md section 11 and CP00_OWNER_DECISIONS.md
- **Scope:** `contracts/analysis/v1/**`, `contracts/domain/v1/**`, `contracts/events/v1/**`, `src/auditmanager/**`, `web/src/**`
- **Enforcement / severity:** `static` / `error`
- **Detection:** Flag the names optimization, optimization_critic, optimization_corrector and optimization_review appearing as the value of a stage, status, endpoint or capability declaration key, or as a module, route or component name, in scope.
- **Not a violation:** The legacy stage name map records these four names as explicit exclusions with evidence; an exclusion record is the required form, not a declaration. Prose in docs/** that describes the decision is out of scope. contracts/optimization/v1/** does not exist yet; when W5-OPT-01 creates it this rule is re-scoped by that task, not waived.
- **Waiver:** none. U-06-OB-1 is an owner obligation that expires by acceptance of W5-OPT-01, not by waiver.

### ALR-27 - backend-tests-outside-src

- **Statement:** Backend test modules live under tests/; a test module or a test-framework import inside src/auditmanager/ is a violation.
- **Source:** REPOSITORY_LAYOUT.md repository tree; ADR-0004 Decision; ADR-0016 evidence model
- **Scope:** `src/auditmanager/**`
- **Enforcement / severity:** `static` / `error`
- **Detection:** Flag a module in src/auditmanager/** whose filename matches the test module pattern, and a runtime import of pytest, unittest or a test double library from product code.
- **Not a violation:** A fixture builder shipped as product code is not a test module, provided it is not named as one. tests/** itself is out of scope. Frontend test placement is not decided by any frozen input and is deliberately out of scope; see escalation E-ARC02-01.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.

### ALR-28 - coverage-not-sole-release-evidence

- **Statement:** No release, checkpoint or merge gate uses a coverage percentage as its sole proof; each gate names the ADR-0016 evidence classes it rests on.
- **Source:** ADR-0016 Decision; ARCHITECTURE_BIBLE.md section 12; P-20 and P-21
- **Scope:** `docs/stages/**`, `docs/manual-tests/**`, `docs/program/**`, `infra/**`
- **Enforcement / severity:** `review` / `error`
- **Detection:** The reviewer reads the acceptance record of the gate and lists the evidence classes it actually rests on. A gate whose only stated proof is a coverage number, or whose other evidence classes are named but not produced, is a violation.
- **Not a violation:** A coverage threshold used as one signal beside named evidence classes is admissible. A coverage report attached as context to a checkpoint bundle is evidence about tests, not a substitute for them.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.
- **Why review-only:** The rule constrains what a human accepts as proof. A threshold in CI configuration is detectable, but whether it is the sole proof depends on the whole acceptance record, which lives in the manual runbook and the integration report.

### ALR-29 - no-empty-framework-layer

- **Statement:** A module sublayer exists only when a real use case populates it; a sublayer directory holding only an init file or a placeholder is a violation.
- **Source:** ADR-0004 Decision, empty folders are not architecture; REPOSITORY_LAYOUT.md backend module shape
- **Scope:** `src/auditmanager/*/domain/**`, `src/auditmanager/*/application/**`, `src/auditmanager/*/ports/**`, `src/auditmanager/*/adapters/**`
- **Enforcement / severity:** `static` / `warning`
- **Detection:** Flag a sublayer directory in scope that contains no module other than an init file, and a sublayer whose modules define no symbol.
- **Not a violation:** The context-level boundary README that the frozen skeleton ships is required by REPOSITORY_LAYOUT.md and is not a sublayer. Declared top-level layout directories such as db/migrations and tests/<class> are layout, not module sublayers. A namespace package intentionally left empty for packaging reasons must be declared as such.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.
- **Why warning:** ADR-0004 states this as layout discipline rather than a runtime invariant, and a sublayer can be legitimately empty for the length of one in-progress change. The rule is fully decidable from the tree, so it stays static; only its severity is warning.

### ALR-30 - composition-root-only-wiring

- **Statement:** Concrete adapters are constructed only in the composition root; domain and application code receives ports as parameters and no module resolves a dependency from a global container or service locator.
- **Source:** ARCHITECTURE_BIBLE.md section 5, dependency injection at the composition root and no service locator; REPOSITORY_LAYOUT.md bootstrap module
- **Scope:** `src/auditmanager/**`
- **Enforcement / severity:** `static` / `error`
- **Detection:** Outside src/auditmanager/bootstrap/**, flag: an import of a module under an adapters package by a module under a domain or application package; instantiation of an adapter class inside a domain or application function; and a call of the shape container.get, registry.resolve or a service-locator lookup, including a module-level singleton accessor that returns a wired service.
- **Not a violation:** FastAPI dependency declarations in src/auditmanager/api/** resolve against providers declared in the composition root and are not a service locator. A factory function that receives its dependencies as arguments is compliant wherever it lives. Importing a port protocol is not importing an adapter.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.

### ALR-31 - generated-client-parity

- **Statement:** The generated TypeScript API client is byte-identical to a fresh generation from the committed OpenAPI document; a hand edit is a violation.
- **Source:** ARCHITECTURE_BIBLE.md section 9 and section 10, the generated client is not edited by hand; ADR-0009
- **Scope:** `web/src/shared/api/**`, `contracts/api/v1/**`
- **Enforcement / severity:** `test` / `error`
- **Detection:** An evidence job regenerates the client from the committed OpenAPI document with the pinned generator version into a temporary directory and diffs it against the committed client. Any difference is a violation. A generated-file header check is a supporting signal, not the decision.
- **Not a violation:** A generator version bump changes the whole output; that is a recorded regeneration with a new pin, not a hand edit. Formatting applied by a repository-wide formatter is admissible only if the same formatter runs on the regenerated output before the diff.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.

### ALR-32 - shared-only-cross-cutting

- **Statement:** A shared module holds only genuinely cross-cutting primitives; a domain-specific helper placed there for convenience is a violation.
- **Source:** AGENTS.md section 4 bullet 4; REPOSITORY_LAYOUT.md Shared; ARCHITECTURE_BIBLE.md P-14
- **Scope:** `src/auditmanager/shared/**`, `web/src/shared/**`
- **Enforcement / severity:** `review` / `error`
- **Covers:** AG4-04
- **Detection:** For each module in shared the reviewer names the cross-cutting concern it implements and confirms the concern is not owned by a single context. A helper that encodes a rule of one context, even if three contexts call it, belongs to that context and is a violation.
- **Not a violation:** Typed identifiers, checksum, clock, error base types and telemetry abstractions are the declared cross-cutting set. A primitive used by one context today but defined by a mandatory boundary is admissible under P-14.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.
- **Why review-only:** Cross-cutting is a judgment about meaning, not about imports. A helper can be imported by three contexts and still be a rule owned by one of them; the import graph shows usage, never ownership.

### ALR-33 - forward-only-migrations

- **Statement:** Migrations are forward-only and re-runnable, a breaking data change follows expand, backfill, switch and contract, and a down path is never the recovery procedure.
- **Source:** ARCHITECTURE_BIBLE.md section 6 PostgreSQL rules; section 12 evidence class 5; ADR-0016
- **Scope:** `db/migrations/**`, `infra/runbooks/**`
- **Enforcement / severity:** `test` / `error`
- **Detection:** The migration evidence job applies the full chain to an empty database, then to a database seeded with the previous release fixture, then re-applies the head migration to prove idempotence. A violation is a chain that fails on either database, a head that is not re-runnable, or a runbook that names a down path as the recovery procedure.
- **Not a violation:** An individually reversible expand-phase migration is still forward-only as a chain. A down implementation kept for local development is admissible while no runbook names it as recovery. A re-runnable data backfill is compliant.
- **Waiver:** granted by the repository owner, recorded in [EXCEPTIONS.md](EXCEPTIONS.md) with principle/ADR violated, exact scope, reason, risk, compensating control, owner, expiry checkpoint, removal task. No self-service bypass.

## 6. The review-only subset

These 10 rules are **not** mechanically decidable and are recorded as `review` with the reason, in the JSON as `review_reason`. None of them was dropped, and none was weakened to `warning` to look enforceable - every one of them is `error`. A reviewer checking this task should read section 5 and confirm that each reason is a genuine undecidability rather than an unwillingness to implement.

- **ALR-09** (no-business-logic-in-schema-or-ui) - No syntactic property separates a transport check from a domain invariant. The same conditional is validation in one context and an owned rule in another, and deciding which requires the domain model, not the file.
- **ALR-11** (abstraction-requires-proven-semantics) - Counting import sites does not establish that two applications are independent, and mandatory boundary is an architectural judgment. A checker cannot decide whether a base class carries proven semantics or is premature framework.
- **ALR-13** (durable-job-state-and-fencing) - Ordering between a durable write and a side effect, and the question of which copy answers a status query, are properties of an execution path rather than of a syntactic shape. Verification inside the publishing transaction depends on the transaction scope actually taken at run time. The two residues handed here by ALR-12 and ALR-25 are undecidable for the same reason: what a container holds and what role a field plays are established by the execution path that reads them, not by the declaration. A name is not a role, and neither is a neighbour - a field declared beside the authority token is not thereby an authority token, which is why no narrower name test was substituted for this one. The static rules stop at the shapes AGENTS.md section 4 bullet 5 and integration decision ID-02 actually name, and the role question is answered here.
- **ALR-15** (typed-identity-resolution) - Whether a value plays the role of identity is semantic: the same string is a label in one call and a lookup key in another. The FS-07 fallback is only visible once that role is known.
- **ALR-17** (outbox-and-reconciliation) - A checker sees the call site, not the operational design. It cannot tell whether the outbox row that exists corresponds to the effect that was performed, nor whether a reconciliation procedure exists and has an owner.
- **ALR-19** (no-silent-fallback) - Silent fallback in the general case is a statement about the meaning of a result, not its shape. The same returned default is a declared partial in one contract and a swallowed failure in another, which is exactly why the CP-00 review maps FS-01 to FS-08 one at a time instead of by pattern.
- **ALR-21** (llm-output-not-canonical-verdict) - Whether a stored value is consumed as the canonical verdict is a semantic role of the read model. A recommendation table can be projected as if it were a decision without any forbidden import appearing anywhere.
- **ALR-23** (ai-artifacts-stay-derived) - The prohibition is about substance. Republishing under the same identity, or presenting a synthesis in a raw-evidence field, preserves every syntactic constraint; only the artifact's meaning and provenance chain decide it.
- **ALR-28** (coverage-not-sole-release-evidence) - The rule constrains what a human accepts as proof. A threshold in CI configuration is detectable, but whether it is the sole proof depends on the whole acceptance record, which lives in the manual runbook and the integration report.
- **ALR-32** (shared-only-cross-cutting) - Cross-cutting is a judgment about meaning, not about imports. A helper can be imported by three contexts and still be a rule owned by one of them; the import graph shows usage, never ownership.

## 7. Handoff to W1-ARC-01

**Implement first: the `error` + `static` subset, 20 rules.** In `rule_id` order:

`ALR-01`, `ALR-02`, `ALR-03`, `ALR-04`, `ALR-05`, `ALR-06`, `ALR-07`, `ALR-08`, `ALR-10`, `ALR-12`, `ALR-14`, `ALR-16`, `ALR-18`, `ALR-20`, `ALR-22`, `ALR-24`, `ALR-25`, `ALR-26`, `ALR-27`, `ALR-30`

Then the remaining mechanical rules: `ALR-29` as `static` + `warning`, and `ALR-31`, `ALR-33` as `test`, which need an execution environment (a pinned client generator, a database evidence job) that does not exist at CP-00.

Not automatable, and not to be turned into a checker: `ALR-09`, `ALR-11`, `ALR-13`, `ALR-15`, `ALR-17`, `ALR-19`, `ALR-21`, `ALR-23`, `ALR-28`, `ALR-32`. Implementing a weak proxy for a `review` rule and reporting it as that rule is a defect, not partial credit.

`W1-ARC-01` may rely on `rule_id`, `slug`, `enforcement`, `severity` and `detection` as the implementation target. It may **not** rely on any rule being currently satisfied: this task makes no compliance claim, and the first enforcement run is expected to produce findings. A scope glob that matches nothing today is not a pass; it is an empty scope.

## 8. Escalations

This task never authors, supersedes or indexes an ADR. `ADR_INDEX.md` and
`docs/architecture/adr/**` are forbidden hotspots here, so a rule that contradicts an
accepted ADR is recorded below for the integrator to route to an ADR-owning task.

| Escalation | Rule | Conflicting ADR | Contradiction | Evidence | Action taken here |
|---|---|---|---|---|---|
| E-ARC02-01 | ALR-27 | ADR-0004, ADR-0016 | The obvious form of this rule, pinning every test module to the five directories the repository layout declares, contradicts ADR-0016. REPOSITORY_LAYOUT.md declares tests/characterization, tests/contract, tests/integration, tests/e2e and tests/replay. ADR-0016 and ARCHITECTURE_BIBLE.md section 12 require ten evidence classes, and four of them have no declared home: domain unit tests, migration and re-run tests, live-quality policy tests for LLM, and restore/rollback drills. Frontend test placement is likewise undeclared, although ADR-0009 puts the frontend under web/src. | docs/architecture/REPOSITORY_LAYOUT.md repository tree, tests subtree lists five directories; docs/architecture/adr/ADR-0016-testing-evidence-model.md Decision names the evidence classes; docs/architecture/ARCHITECTURE_BIBLE.md section 12 lists ten required evidence types | ALR-27 was written to the intersection both inputs agree on: a backend test module must not live under src/auditmanager. The directory set is deliberately not pinned and the frontend is explicitly out of scope. |
| E-ARC02-02 | ALR-25 | ADR-0007 | ALR-25 makes the field names fencing_token and fence_token violations, while the accepted ADR-0007 text says each Attempt carries a lease/heartbeat and fencing token. The CP-00 review disposes ADR-0007 as adapt and records the qualification that the capability is named execution_token, is opaque and equality-only, and that fencing is behavior rather than a field name; integration decision ID-02 fixes the name. The rule therefore follows a recorded qualification that the ADR body itself does not carry, so an implementer reading only ADR-0007 would write the forbidden name. | docs/architecture/adr/ADR-0007-postgres-jobs-outbox-and-attempt-fencing.md Decision; docs/architecture/CP00_ARCHITECTURE_REVIEW.md section 5, ADR-0007 row, adapt qualification; docs/architecture/CP00_ARCHITECTURE_REVIEW.md section 6.3, integration decision ID-02 | ALR-25 is published as specified, with its source anchor naming ID-02 and the ADR-0007 adapt qualification, so the conflict is visible at the rule rather than hidden in it. |

Both escalations are routed to the program integrator. Neither was executed here:
no ADR file, status or index row was touched by this task.

Three further candidate conflicts were checked and are **not** escalated:

- **ALR-24** against ADR-0003 - ADR-0003 requires every boundary to be versioned by a machine schema but names no version key, so pinning the key to contract_version adds a naming decision without contradicting the ADR. The conflict that does exist is with repository state, not with an ADR: scripts/validate_bootstrap.py currently requires a bare version key in the domain error catalog. That is the ID-01 work of W0-QA-03 and W0-DOM-02 and is recorded as an open item.
- **ALR-26** against ADR-0008 - ADR-0008 makes the stage registry a package-contract boundary and says nothing about optimization membership. PD-05 decided membership and U-06 assigned the capability to a separate bounded context, so the rule implements an owner decision rather than contradicting the ADR.
- **ALR-29** against ADR-0004 - ADR-0004 states that empty folders are not architecture and the frozen skeleton ships context-level boundary READMEs, which REPOSITORY_LAYOUT.md requires. The rule is scoped to module sublayers, so the required skeleton shape is not a violation and no ADR is contradicted.

## 9. Known limits and open items

- No compliance claim is made by this task. The repository holds a skeleton only: src/auditmanager and web/src contain boundary READMEs and one package init, so most scopes currently match no code. A first enforcement run under W1-ARC-01 will produce findings, and that is expected.
- ALR-24 is contradicted by repository state at the base commit, not by an ADR: scripts/validate_bootstrap.py requires a bare version key in contracts/domain/v1/error-codes.json. W0-QA-03 teaches the validator to read contract_version and W0-DOM-02 removes the mirror. Until both are integrated, an enforcement run of ALR-24 and the bootstrap validator cannot both be green, and neither task is owned here.
- Scope globs are written against the layout ADR-0004 and REPOSITORY_LAYOUT.md declare, including directories that do not exist yet, such as the module sublayers and web/src/shared/api. W1-ARC-01 must treat an empty glob as no finding, never as a pass.
- ALR-31 and ALR-33 need infrastructure that does not exist at CP-00: a pinned client generator and a database evidence job. They are specified as test enforcement precisely so that no reader mistakes them for a static check available today.
- The rules constrain code that is prohibited before CP-00 anyway. They are a specification for W1-ARC-01, not a gate on this wave.
- U-04 stays open, so no rule mentions a tenant, an identity provider, a TTL, a retention period or a legal hold; ALR-22 defers artifact lifecycle authority to the deferred ADR-0014 rather than deciding it.

## 10. Verification

Every command below was executed exactly as written, from the repository root, under
`.venv/bootstrap/bin/python`. Copy them verbatim.

**GATE-A** - the JSON rule set is well-formed and the Markdown table covers exactly the
same rule IDs, once each (this is the first required test of the task file):

```bash
.venv/bootstrap/bin/python -c "import json,re; from pathlib import Path; spec=json.loads(Path('docs/architecture/ARCHITECTURE_LINT_RULES.json').read_text()); rules=spec['rules']; ids=[r['rule_id'] for r in rules]; assert ids and len(ids)==len(set(ids)); assert all(re.fullmatch(r'ALR-\d{2}',i) for i in ids); required={'rule_id','statement','source_anchor','scope','enforcement','severity','detection','false_positive_notes','waiver_policy'}; assert all(required<=set(r) for r in rules); assert all(r['enforcement'] in {'static','test','review'} and r['severity'] in {'error','warning'} and r['scope'] and r['statement'] and r['source_anchor'] and r['detection'] for r in rules); md=Path('docs/architecture/ARCHITECTURE_LINT_RULES.md').read_text(); md_ids=re.findall(r'^\|\s*(ALR-\d{2})\s*\|',md,re.MULTILINE); assert sorted(md_ids)==sorted(ids) and len(md_ids)==len(set(md_ids))"
```

**GATE-B** - every declared `AGENTS.md` section 4 prohibition is covered, with no orphan
on either side (the second required test):

```bash
.venv/bootstrap/bin/python -c "import json; from pathlib import Path; spec=json.loads(Path('docs/architecture/ARCHITECTURE_LINT_RULES.json').read_text()); covered={c for r in spec['rules'] for c in r.get('covers_prohibitions',[])}; declared=set(spec['agents_md_prohibitions']); assert declared and covered==declared, sorted(declared^covered)"
```

**GATE-C** - rule identity is pinned. `rule_id` is stable only if it cannot be renamed,
duplicated or dropped unnoticed, so the ID set, the slug, the enforcement and the severity
of every rule are pinned in `rule_identity_pin` and compared against the rule set:

```bash
.venv/bootstrap/bin/python -c "import json; from pathlib import Path; spec=json.loads(Path('docs/architecture/ARCHITECTURE_LINT_RULES.json').read_text()); check=lambda s: sorted(s['rule_identity_pin'])==sorted(r['rule_id'] for r in s['rules']) and len({r['slug'] for r in s['rules']})==len(s['rules']) and all(s['rule_identity_pin'].get(r['rule_id'])=={'slug': r['slug'], 'enforcement': r['enforcement'], 'severity': r['severity']} for r in s['rules']); assert check(spec); print('identity pin ok')"
```

What the pin does **not** do is worth stating: it cannot stop a coordinated edit of both a
rule and its pin entry. What it guarantees is that such an edit is a deliberate, visible
change to a declared identity block rather than a silent rename inside a rule row - which is
exactly the freeze-break the integration contract requires.

**GATE-D** - the mutation probe for GATE-C. A check proves only what it checks, so this
mutates an in-memory copy four ways - rename an ID, duplicate an ID, flip a severity,
delete a rule - and asserts that the GATE-C predicate rejects each one. Nothing on disk is
modified:

```bash
.venv/bootstrap/bin/python -c "import copy,json; from pathlib import Path; spec=json.loads(Path('docs/architecture/ARCHITECTURE_LINT_RULES.json').read_text()); check=lambda s: sorted(s['rule_identity_pin'])==sorted(r['rule_id'] for r in s['rules']) and len({r['slug'] for r in s['rules']})==len(s['rules']) and all(s['rule_identity_pin'].get(r['rule_id'])=={'slug': r['slug'], 'enforcement': r['enforcement'], 'severity': r['severity']} for r in s['rules']); assert check(spec); m=copy.deepcopy(spec); m['rules'][0]['rule_id']='ALR-99'; assert not check(m); m=copy.deepcopy(spec); m['rules'][1]['rule_id']=m['rules'][0]['rule_id']; assert not check(m); m=copy.deepcopy(spec); m['rules'][2]['severity']='warning'; assert not check(m); m=copy.deepcopy(spec); del m['rules'][3]; assert not check(m); print('rename, duplicate, severity flip and removal all rejected')"
```

**GATE-E** - every file cited in an `anchor_files` entry exists **at the frozen base
commit**, so no rule cites a source that is not in the repository the task was frozen
against. Existence is resolved with `git --no-replace-objects cat-file -e` against that
commit; a working-tree path test would answer a different question and is not used:

```bash
.venv/bootstrap/bin/python -c "import json,subprocess; from pathlib import Path; base='43a84d93fd544573226b82860ab24f924ed66d83'; spec=json.loads(Path('docs/architecture/ARCHITECTURE_LINT_RULES.json').read_text()); at_base=lambda q: subprocess.run(['git','--no-replace-objects','cat-file','-e',base+':'+q],capture_output=True).returncode==0; anchors=sorted({a for r in spec['rules'] for a in r['anchor_files']}); missing=[a for a in anchors if not at_base(a)]; assert not missing, missing; print('anchor files present at base commit:', len(anchors))"
```

`anchor_files` lists the path of every input a rule cites in any field, not only in
`source_anchor`: a citation inside `statement`, `detection`, `false_positive_notes`,
`review_reason` or `severity_rationale` belongs there too. That is a promise about
content, so it is checked rather than asserted. The command below resolves each frozen
input named in a rule - the five documents by filename, every ADR by its `ADR-NNNN` id -
and fails on any rule that cites one without anchoring it:

```bash
.venv/bootstrap/bin/python -c "import json,re; from pathlib import Path; spec=json.loads(Path('docs/architecture/ARCHITECTURE_LINT_RULES.json').read_text()); docs={'AGENTS.md':'AGENTS.md','ARCHITECTURE_BIBLE.md':'docs/architecture/ARCHITECTURE_BIBLE.md','REPOSITORY_LAYOUT.md':'docs/architecture/REPOSITORY_LAYOUT.md','CP00_ARCHITECTURE_REVIEW.md':'docs/architecture/CP00_ARCHITECTURE_REVIEW.md','CP00_OWNER_DECISIONS.md':'docs/architecture/CP00_OWNER_DECISIONS.md'}; adr={p.name[:8]:str(p) for p in Path('docs/architecture/adr').glob('ADR-*.md')}; body=lambda r: json.dumps({k:v for k,v in r.items() if k not in ('anchor_files','waiver_policy')}); cited=lambda r: {docs[n] for n in docs if n in body(r)} | {adr[i] for i in re.findall(r'ADR-\d{4}',body(r))}; gaps={r['rule_id']: sorted(cited(r)-set(r['anchor_files'])) for r in spec['rules'] if cited(r)-set(r['anchor_files'])}; assert not gaps, gaps; print('every cited frozen input is anchored; rules checked:', len(spec['rules']))"
```

`waiver_policy` is excluded from that scan on purpose: `EXCEPTIONS.md` is where a waiver
is *recorded*, not an input the rule derives from, and anchoring it would make the gate
report a provenance that does not exist. Extra entries in `anchor_files` are allowed and
are not an error - a rule may anchor `CP00_OWNER_DECISIONS.md` while citing only the
`PD-01` decision it records - because the gate constrains the direction that matters:
nothing cited may go unanchored.

The probe below is what makes the first command of this gate a claim about the base
commit rather than about this working tree. It runs that same predicate over the anchor
set plus one
added path that exists in the working tree and not at the base commit - this document's
own JSON, still untracked - and asserts that the gate reports exactly that path as
missing, while `Path.exists()` would have accepted it. Nothing on disk is modified:

```bash
.venv/bootstrap/bin/python -c "import json,subprocess; from pathlib import Path; base='43a84d93fd544573226b82860ab24f924ed66d83'; spec=json.loads(Path('docs/architecture/ARCHITECTURE_LINT_RULES.json').read_text()); at_base=lambda q: subprocess.run(['git','--no-replace-objects','cat-file','-e',base+':'+q],capture_output=True).returncode==0; probe='docs/architecture/ARCHITECTURE_LINT_RULES.json'; anchors=sorted({a for r in spec['rules'] for a in r['anchor_files']}|{probe}); missing=[a for a in anchors if not at_base(a)]; assert missing==[probe], missing; assert Path(probe).exists(); print('GATE-E rejects a path present only in the working tree:', probe)"
```

**GATE-F** - repository gates required by the task file. The third command is the decisive
one for the allowed-path claim:

```bash
.venv/bootstrap/bin/python scripts/validate_bootstrap.py
git diff --check -- docs/architecture
git status --porcelain -- docs/architecture
```

The validator must exit `0` and print a standalone `PASS`; `git diff --check` must print
nothing; and `git status --porcelain -- docs/architecture` must print exactly two lines,
`?? docs/architecture/ARCHITECTURE_LINT_RULES.json` and
`?? docs/architecture/ARCHITECTURE_LINT_RULES.md`, with nothing else under
`docs/architecture`. The strict form of that last expectation, which fails on a third line
as well as on a missing one:

```bash
.venv/bootstrap/bin/python -c "import subprocess; out=subprocess.run(['git','status','--porcelain','--','docs/architecture'],capture_output=True,text=True).stdout.splitlines(); assert sorted(out)==['?? docs/architecture/ARCHITECTURE_LINT_RULES.json','?? docs/architecture/ARCHITECTURE_LINT_RULES.md'], out; print('write boundary holds: exactly the two owned files')"
```

The command
`git diff --name-only 43a84d93fd544573226b82860ab24f924ed66d83 -- docs/architecture`
is **not** part of this gate and is recorded here only as history. `git diff` reads
tracked content; both deliverables of this task are untracked and `git add` is not
authorized here, so it prints nothing whether the two files were written or nothing at
all was. It cannot distinguish the two cases it would have to distinguish, and its
stated expectation of two paths is unreachable while the files are untracked. It becomes
meaningful again once the integrator stages them, and is worth re-running at that point.

## 11. Waivers

No rule has a self-service bypass. A waiver is an entry in
[EXCEPTIONS.md](EXCEPTIONS.md) carrying the principle or ADR it departs from, the exact
scope, the reason, the risk, the compensating control, the owner, an expiry checkpoint and
a removal task; an exception without an expiry is a new architectural decision and needs an
ADR. Rules anchored in `AGENTS.md` section 4, the Bible or an ADR are waivable by the
repository owner. Rules anchored in a recorded integration decision are waivable by the
repository owner and recorded by the program integrator. Two rules are not waivable at all:
`ALR-19`, because the CP-00 review records that the no-silent-success rule admits no
exception, and `ALR-26`, because it carries owner obligation `U-06-OB-1`, which expires by
acceptance of `W5-OPT-01` rather than by waiver.

## 12. Change control

Re-running this specification updates one entry per `rule_id`; it cannot duplicate an ID or
silently remove an accepted rule, and GATE-C plus GATE-D are what make that true rather
than aspirational. After acceptance, a `statement` may be clarified, but changing a
`rule_id`, `enforcement` or `severity` - or adding and removing a rule - requires the normal
freeze-break procedure. All examples are synthetic: they contain no credential, no
production payload, no customer data and no legacy checkout content.
