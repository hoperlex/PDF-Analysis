# W57A-INT-RULE-FREEZE-01 — citation/custody seal preparation

**Base:** published `origin/dev=b9f1c149f004851de89a2fcc615618068e794bde`
on 2026-10-16. **Status:** documentation freeze for the next integrator
decision; no migration or contract is sealed by this report. The parent
`W57-INT-SEAL-FREEZE-PROPOSAL-01` was based on older dev `08055ca0` and is
reconciled here against the current tree.

## Rule ledger and code-first order

The functional rule remains W57 §A1–A3: a v3 normative observation cites
only labelled paragraphs in the pinned, verified set; the raw quote, required
value and stated document value pass the deterministic gate before merge. A
failed or ambiguous citation withholds the *whole* observation. The reviewed
map and complete vector build precede a verified set. The set and catalogue
need independently expected digests and two confirmed R-76 custody bindings.
A rejected or merely matching candidate is never pinnable. Runtime selects
the current qualified snapshot and a verified set for the configured profile;
no stand embedding, model substitution or normative legal-status inference is
introduced here.

`R-135` changes W57 §A4's timing: W57a code may receive bounded checks and
publish to `origin/dev` before stand import and the complete beta gate. A
contract/migration lane still owns one exact shared hotspot, proves its
forward upgrade and local contract consistency, and does not call its slice a
release. A later `origin/main` act still needs the separate exact-SHA
instruction and complete release gate. A future `W57A-RULE-01` must record
the rule under then-current owner-ruling numbers; this task assigns none.

The last completed W56a slice at this base is the *unactivated* recorded
publication gate (`CFB-INT-DEV-PUBLISH-17`). `W56A-INT-CLOSE` and the active
executor are absent. W54 has 674 source documents, checked files and a
restored base DB, but the 121-page repair lacks a proxy credential and there
is no qualified repaired snapshot, embedding build or published DB/S3 bundle.
The reviewed map and verified set are also absent. They remain explicit
preconditions for MAP/RETRIEVAL/PROFILE/CITE acceptance; they do not become
phantom `depends_on` entries in the docs task.

## Fresh pin inventory and direct consumers

`python3 tools/plan/pin_sweep.py reseal-surface migration table error-code route`
returned **124 paths**, SHA-256 of its complete stdout
`5412fa5a43a348c22cdaa9b99395d9ad2555d3c22210ffe680f37d1647f3ae47`.
This is a review inventory, not blanket write permission. Before the actual
seal, re-run it against the dispatched base, classify every path as changed or
review-only, and run `--check` against each task's explicit allowlist.

| Consumer class | Current exact paths and disposition |
| --- | --- |
| Four-artifact API reseal | `contracts/api/v1/openapi.json`, `web/openapi/openapi.json`, `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json` — one W57a seal owner. |
| Identifier, stage, error | `contracts/domain/v1/identifiers.json`, `contracts/analysis/v1/stage-registry.json`; `contracts/domain/v1/error-codes.json` is review-only because W57 adds no error code. `ProviderMode` and `P02_LOCK.json` remain byte-identical. |
| Migration/table pins | New `db/migrations/versions/20261016_0023_norm_citations.py`, `tests/integration/db/{test_migration_lifecycle,test_schema_shape,test_open_items_migration}.py`, `tests/support/expected_facts.json`, `tests/integration/composition/test_reset_rehearsal_counts_base_tables.py` — exact 0023 owner reviews these and updates only stale assertions. Old migrations stay byte-identical. |
| Served operation/roles | `src/auditmanager/api/{app,security}.py`, `src/auditmanager/api/routers/{runs,ports}.py`, `src/auditmanager/api/schemas/{models,findings,runs}.py`, `tests/integration/api/{test_operation_surface,test_role_register,test_served_document_and_health_plane}.py` — only a typed refusing `getRunNormVerification` until CITE supplies a verified reader. |
| Custody and category direct pins | `src/auditmanager/norms/custody/roles.py`, `src/auditmanager/shared/identity/ids.py`, `src/auditmanager/api/routers/handlers.py`, `web/src/entities/expert-decision/model/category-labels.ts`, `web/src/widgets/finding-list/ui/finding-list.tsx`, `web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx`, `src/auditmanager/findings/grounding.py`, and their focused tests — individually assigned, no inferred `norms/**` or web-wide grant. |
| Prose/operational pins | `docs/program/{CONTRACT_PIN_REGISTRY,P02_SEAMS,ALPHA_ROADMAP,NORM_CORPUS_CUSTODY}.md`, `infra/deploy/reset.sh`, `src/auditmanager/norms/bundle/{copy_record,stand}.py` — review live head/role/table claims. `CURRENT_STATE.md` belongs to the integration slot. |

The direct search also found a maintained category filter
`CATEGORY_CHOICES` in `web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx`
and the role register `tests/integration/api/test_role_register.py`; neither
is safely inferred from the generated client. `norm_verification` is already
declared in `stage-registry.json` at 1.0.0, while W57 §A3.6 proposes making
`text_analysis`'s `norms.snapshot` input optional at version 1.1.0. The actual
seal must compare and reseal these exact registry entries, not add a second
stage of the same name.

## Proposed sole owner and precise grants

At the next dev head, assign **one** integration/contract owner
`W57A-SEAL-01` to `0023_norm_citations`, the `nrs_` identifier, the
stage/API reseal, role and vocabulary enumerators, and any composition-root
refusing-port wiring. Do not run a second writer on any of these paths until
that seal is integrated. The subsequent MAP, RETRIEVAL, PROFILE, CITE and WEB
lanes consume the seal serially and receive their own exact tasks and bases.

The later SEAL task must enumerate these named write grants, with exact files
instead of a broad directory: new 0023 migration and new migration tests;
the four API artifacts; `contracts/domain/v1/identifiers.json` and
`contracts/analysis/v1/stage-registry.json`; the three API schema modules;
`src/auditmanager/api/routers/{runs,ports}.py`, `security.py` and the direct
served-operation/role tests; `src/auditmanager/norms/custody/roles.py`,
`src/auditmanager/shared/identity/ids.py`; the category/reason consumers named
above; `src/auditmanager/bootstrap/{adapters,composition}.py` solely for a
typed refusing port; direct contract, schema, migration and reset tests; and
only the live pin-prose files actually made stale. `web` category labels and
the knowledge-base filter should be serial within that owner, or the filter
must be explicitly reserved to the later WEB lane with no conflicting writer.
No route may serve unverified caller-supplied citation data. The W57b
`0024_norm_references`, `exportRunXlsx` route and expert role remain a separate
later sole-owner slot; `api/routers/export.py` must be explicitly granted in
that W57b task.

Migration 0023 must contain the verified retrieval-set row; its expected and
observed digests, append-only state and unique verified identity; both new
custody roles and the binding trigger's `norm_retrieval_set` target arm; the
frozen `audit_run.norm_retrieval_set_id` pin; normative required/stated values;
the append-only observation citation relation; and category/reason CHECKs.
It must bind each citation to the exact observation/run/snapshot/set and
canonical paragraph, never just to a display designation or filename. The
new custody row is not `verified` until both confirmed bindings to the set
and catalogue exist, and a rejected row cannot pin. A `norm_paragraph_id`
alone is insufficient to show that its snapshot matches the run.

## Accepted zero-citation semantics

`0022` has no citation relation; therefore an empty SQL result is ambiguous.
For every **published v3** observation, 0023 must persist a complete citation
partition in the same transaction as the observation and its citation rows.
A concrete additive shape is nullable `finding_observation.norm_citation_count`:
`NULL` means no certified partition (including historical v1/v2), `0` means a
certified empty partition, and `1..5` means that many verified rows. For v3
normative categories, zero is forbidden; a failed citation is an ungrounded
diagnostic without a published finding. For a published v3 nonnormative
observation, zero is valid only when the CITE gate completed and explicitly
wrote `0`. A deferrable check or equivalent transaction-local proof must
assert that the stored count equals the immutable citation rows at commit;
readers refuse null, a count mismatch, an incomplete stage or a wrong
run/snapshot/set. Canonical and member observations each need their own
partition proof. V1/v2 wire fields stay **absent, never null**; their legacy
export policy must be explicit in W57b rather than inferred from absent rows.

The exact column/constraint shape is for `W57A-SEAL-01` to validate against
the populated 0022 upgrade before it is dispatched. If it cannot enforce a
certified zero partition without changing this shape, the integrator must
amend the task and contract *before* W57b's reader is written. W57b's existing
`citations_by_finding` argument and `citation_source_ref` are untrusted inputs,
not evidence of zero. This closes the gap identified in the predecessor
proposal without declaring the relation implemented.

## Focused acceptance for the later seal

1. Fresh migration head has one 0022→0023 successor. A clean database and a
   populated 0022 database with v1/v2 findings upgrade without invented
   citations. Legacy wire shape and existing finding/decision rows survive.
2. Set rows reject bad `nrs_`, digest, state and duplicates. The custody
   shape and guard agree with the Python role registry; missing admission,
   unavailable/blob-digest mismatch, rejected set, wrong target and a single
   binding all refuse. A committed verified set has both roles confirmed.
3. Run pin is frozen and points to a verified set for the same snapshot;
   citation FKs/triggers reject wrong observation, run, snapshot, set,
   document and paragraph. Raw offset/length equals the stored raw quote and
   a substring of the canonical paragraph. Citation rows are append-only.
4. V3 normative findings have 1–5 grounded citations and both values;
   v3 nonnormative published findings have an explicit certified zero;
   missing or mismatched partitions refuse. A failed citation withholds the
   whole observation and emits no published finding. V1/v2 omit new API
   properties rather than serializing nulls.
5. The OpenAPI mirror/generated client/frontend lock, served OpenAPI, role
   register and expected facts agree. `getRunNormVerification` has `_ANY_ROLE`
   access and a typed refusal until its verified reader exists. Exhaustive
   category/reason/identifier cases, including `nrs_` and the
   `norm_retrieval_set` safe reference kind, pass. No new error code is added.
6. A populated downgrade refuses before data loss, including retained set or
   citation data. The previous 0022 file remains byte-identical. Run focused
   Python contract/integration tests, frontend generation verification,
   typecheck/lint for changed files and isolated forward migrations. Record
   actual test counts and resource lane; R-135 defers the complete beta gate.

## Integration instruction and limits

Create the numbered W57a RULE and executable FREEZE/SEAL tasks only after a
fresh `origin/dev` read. Their `depends_on` lists must contain completed task
IDs only. They must explicitly settle W56a code close, corpus/map/embedding
readiness, exact resource lanes, new enum totals, source and stand snapshot
pins, and the set builder/profile IDs. If the migration head moved, abandon
0023 and allocate the next slot. `pin_sweep --check` is rerun on each grant;
the 124-path inventory above may have changed. No live DB/S3, proxy call,
stand, full gate, tag or remote ref was changed by this task.

## Checks and ownership proof

- Direct `governance_findings` on the new task returned `[]`.
- Program governance and API prose/count suites: **93 passed in 10.28 s**.
- All seven frozen file SHA-256 values above matched; migration inventory
  contained only `20261015_0022_findings_v2.py` in slots 0022–0024.
- The five-event `pin_sweep` completed: **124 paths** and the digest above.
- Staged whitespace and exact two-path checks are recorded by the task commit.
  No product code, frozen contract, old migration, root lock, composition root
  or global style is in this task's diff.
