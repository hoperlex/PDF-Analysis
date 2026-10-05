# Task W48-PUBLIC-01 — route every backend cross-context import through a public module

## Outcome

The complete ALR-05 walk reads `0 deep / 0 package-root` violations, and an executable guard
rejects reintroduction of either form without changing runtime behaviour.

## Depends on

- `W48-DURABLE-FIX-2` merged at `68cb5a2`
- `W48-GUARDS-2` merged at `5d99b62`
- `W48-TAILS` merged at `3d5f322`

## Frozen inputs

- domain contract: `1.0.0-draft.1`, candidate revision 8, unchanged
- API contract: 17 paths / 20 operations / 61 schemas at the W48 frozen digest
- analysis/comparison/event contract: unchanged
- migration head: `0014_durable_analysis_effects`
- base commit: `3d5f322408aec9c54f5638dddcd459f2463b64ce`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the complete AST walk finds 18 deep and 24 package-root ALR-05 violations on the exact base

### P-01 — complete cross-context import inventory

- captured_at: 2026-10-05
- command: `.venv/bin/python -c 'import ast,pathlib; root=pathlib.Path("src/auditmanager"); rows=[]; exec("for path in sorted(root.rglob(\"*.py\")):\n rel=path.relative_to(root); importer=rel.parts[0]\n if importer in {\"bootstrap\",\"shared\"}: continue\n tree=ast.parse(path.read_text())\n for node in ast.walk(tree):\n  names=[node.module] if isinstance(node,ast.ImportFrom) and node.level==0 and node.module else ([a.name for a in node.names] if isinstance(node,ast.Import) else [])\n  for name in names:\n   parts=name.split(\".\")\n   if len(parts)<2 or parts[0]!=\"auditmanager\": continue\n   target=parts[1]\n   if target in {\"shared\",importer}: continue\n   if len(parts)==3 and parts[2]==\"public\": continue\n   rows.append((\"package-root\" if len(parts)==2 else \"deep\",path.as_posix(),node.lineno,name))"); [print(kind,path+":"+str(line),name) for kind,path,line,name in rows]; print("COUNTS",sum(r[0]=="deep" for r in rows),sum(r[0]=="package-root" for r in rows))'`
- captured_output:
  ```text
  package-root src/auditmanager/analysis/engine/runner.py:54 auditmanager.storage
  deep src/auditmanager/analysis/engine/runner.py:55 auditmanager.storage.models
  package-root src/auditmanager/analysis/ports/artifacts.py:28 auditmanager.storage
  deep src/auditmanager/analysis/ports/artifacts.py:29 auditmanager.storage.models
  package-root src/auditmanager/analysis/ports/stage.py:25 auditmanager.storage
  deep src/auditmanager/analysis/ports/stage.py:26 auditmanager.storage.models
  deep src/auditmanager/analysis/stages/page_geometry_extraction.py:125 auditmanager.storage.models
  package-root src/auditmanager/api/app.py:295 auditmanager.runs
  deep src/auditmanager/api/composition.py:11 auditmanager.bootstrap.composition
  deep src/auditmanager/api/composition.py:12 auditmanager.bootstrap.settings
  package-root src/auditmanager/api/routers/errors.py:41 auditmanager.documents
  deep src/auditmanager/dashboard/repository.py:23 auditmanager.documents.repository
  deep src/auditmanager/decisions/ledger.py:61 auditmanager.findings.queries
  package-root src/auditmanager/decisions/ledger.py:327 auditmanager.ingest
  package-root src/auditmanager/documents/models.py:30 auditmanager.storage
  package-root src/auditmanager/documents/repository.py:34 auditmanager.storage
  package-root src/auditmanager/ingest/commands.py:42 auditmanager.documents
  package-root src/auditmanager/ingest/failures.py:28 auditmanager.storage
  package-root src/auditmanager/ingest/reconciliation.py:93 auditmanager.documents
  package-root src/auditmanager/ingest/reconciliation.py:97 auditmanager.storage
  deep src/auditmanager/ingest/reconciliation.py:107 auditmanager.storage.blob_repository
  package-root src/auditmanager/ingest/service.py:48 auditmanager.documents
  package-root src/auditmanager/ingest/service.py:66 auditmanager.storage
  deep src/auditmanager/ingest/service.py:75 auditmanager.storage.blob_repository
  deep src/auditmanager/jobs/repository.py:23 auditmanager.storage.models
  deep src/auditmanager/norms/__main__.py:109 auditmanager.analysis.text
  deep src/auditmanager/norms/__main__.py:117 auditmanager.analysis.text
  package-root src/auditmanager/runs/carrier.py:89 auditmanager.jobs
  package-root src/auditmanager/runs/commands.py:48 auditmanager.documents
  package-root src/auditmanager/runs/commands.py:49 auditmanager.ingest
  package-root src/auditmanager/runs/commands.py:74 auditmanager.documents
  deep src/auditmanager/runs/executor.py:83 auditmanager.analysis.ports.artifacts
  deep src/auditmanager/runs/executor.py:84 auditmanager.analysis.text
  deep src/auditmanager/runs/executor.py:99 auditmanager.analysis.text.stage
  package-root src/auditmanager/runs/executor.py:100 auditmanager.documents
  package-root src/auditmanager/runs/executor.py:101 auditmanager.findings
  package-root src/auditmanager/runs/executor.py:111 auditmanager.jobs
  package-root src/auditmanager/runs/executor.py:126 auditmanager.storage
  deep src/auditmanager/runs/executor.py:127 auditmanager.storage.blob_repository
  deep src/auditmanager/runs/executor.py:128 auditmanager.storage.models
  package-root src/auditmanager/runs/reconciliation.py:46 auditmanager.ingest
  package-root src/auditmanager/runs/reconciliation.py:47 auditmanager.jobs
  COUNTS 18 24
  ```
- interpretation: this is the untruncated import inventory on the exact dispatch base. It
  identifies dependency boundaries, not whether the imported symbols are behaviourally correct.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/reviews/W48-AUDIT.md`
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/storage/public.py`
- `src/auditmanager/bootstrap/public.py`
- `src/auditmanager/documents/public.py`
- `src/auditmanager/findings/public.py`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/ingest/public.py`
- `src/auditmanager/jobs/public.py`
- `src/auditmanager/runs/public.py`
- import lines only in every importer named by captured premise P-01
- `src/auditmanager/api/composition.py` (its two import lines only)
- `tests/contract/architecture/test_alr05_boundaries.py`
- `docs/architecture/ARCHITECTURE_LINT_RULES.md` (guard-enforcement sentence only)
- `docs/program/W48-PUBLIC-01.md`

## Forbidden hotspots

- contracts, migrations, error catalog, root locks, generated clients and global styles
- executable changes other than import targets and exact symbol re-exports
- `docs/architecture/EXCEPTIONS.md`; no waiver exists
- task files, state/debt/ruling records, refs, tags and deployment

## Non-goals

- no renaming, moving or redesigning imported symbols; no generic repository or public facade
  beyond the exact subject imports

## Deliverables

- minimal public modules, import-line rewrites, ALR-05 AST guard, architecture-rule enforcement
  note, completion report and two red mutations

## Required tests

- AST walk reads `COUNTS 0 0`
- guard fails on one reintroduced deep import and one package-root import
- `.venv/bin/python -m pytest tests/contract -q` with inherited quarantine reported honestly
- canonical non-quarantined contract suite; `make gate`; `git diff --check`
- diff changes only import lines, new `public.py` files, the guard and two documents

## Integration contract

Every backend context imports another context only from `auditmanager.<context>.public`; shared
and bootstrap importers retain the ALR-05 exceptions. Public modules re-export only symbols
consumed on the dispatch subject and add no behaviour.

## Failure/idempotency/security cases

- any cycle, runtime import change, missing symbol, contract/migration need or importer absent
  from P-01 stops the task and returns to the integrator
- mutations use scratch copies and restore every byte

## Rollback / feature flag

Import-only structural repair; rollback is a revert. No stored data or feature flag applies.

## Handoff

- changed files: allowed paths only
- commands/results: report complete AST output, tests, gate and mutations
- known limits: no waiver and no stable-public-API promise beyond internal context boundaries
- integration notes: merge before `W48-JUDGE-Z`
