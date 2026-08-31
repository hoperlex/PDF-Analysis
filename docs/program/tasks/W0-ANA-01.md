# Contract task W0-ANA-01 — target stage registry and analysis packages draft.1

## Outcome

Publish a reviewable analysis-contract candidate `1.0.0-draft.1` with one
machine-readable canonical stage registry, a complete 31/31 legacy-declaration map
and fail-closed Job/Stage/Result package schemas. Canonical registry IDs are unique;
multiple legacy declarations may intentionally map to the same canonical stage.

## Problem

Legacy exposes conflicting stage enums, orders, aliases, artifact maps and remote
eligibility declarations. Control plane and engine need one versioned target
registry plus fail-closed Job/Stage/Result package semantics before parallel
implementation.

## Owners / consumers

- provider/contract owner: planned agent `/root/w0_analysis_contract`
- frozen-boundary governor: primary agent `/root`
- consumers: control plane, local/remote engine, workers and independent QA
- product/domain approval authority: repository owner/user

## Depends on

- Completed `W0-BHV-01`, accepted at
  `667fb00fe3e45d1ce0bce7860725c1654b4cdeba`.

## Frozen inputs

- base commit: `667fb00fe3e45d1ce0bce7860725c1654b4cdeba`
- accepted inventory including 31/31 legacy declaration ledger
- current analysis package drafts at the base commit
- domain `1.0.0-draft.0` and Bible/ADR package invariants: read-only
- `W0-ARC-01` and `W0-DOM-01` are parallel candidates; semantic mismatch blocks
  integration rather than authorizing cross-family edits
- migration head: none

## Allowed paths

- `contracts/analysis/v1/**`

No other contract family or path is writable.

## Forbidden hotspots

- `contracts/domain/**`, API/events/comparison contracts
- architecture/program docs, fixtures/tests, source/runtime code
- root dependencies/locks, migrations, composition root, global styles and legacy

## Non-goals

- No production engine, worker, scheduler, control-plane or publication code.
- No changes to domain/API/event/comparison contracts or the bootstrap validator.
- No product/architecture decision made by the task author.
- No live provider call, customer payload, credential or mutable legacy execution.
- No canonical metadata write from the analysis engine.
- No fabricated graphic/vector analysis stage; future graphic comparison remains
  outside this contract.

## Proposed semantics

- One machine-readable registry is the sole target source for canonical stage name,
  version, dependencies, required input/output roles, execution scope and
  success/partial/failed/skipped semantics.
- Every one of the 31 inventory declaration sites maps to a canonical target stage,
  control-plane concern, sub-pipeline or explicit exclusion with evidence.
- No single legacy order is copied as the target registry.
- `JobPackage` and `ResultPackage` require `run_id`, `job_id`, `attempt_id` and a
  non-empty equality-only attempt authority/fencing token.
- Artifacts expose `blob_id`, SHA-256, size, media type and role, never object key,
  URL, credential or secret.
- `ResultPackage` references the standalone `StageResult` schema instead of embedding
  a duplicate definition.
- `failed`, `partial` and `skipped` require a typed reason/error; `succeeded` cannot
  carry hidden error state.
- Publication is outside the engine and occurs only after schema/checksum/manifest
  and current-attempt validation.

## Deliverables

- `stage-registry.schema.json` and `stage-registry.json` as the sole target registry.
- `legacy-stage-map.schema.json` and `legacy-stage-map.json`, covering exactly all
  31 inventory declaration sites. Many-to-one mappings are allowed and explicit;
  canonical IDs in the registry remain unique. The registry exposes `stages[]` with
  `stage_id`; the map exposes `declarations[]` with unique
  `source_declaration_id` (`LSD-01` through `LSD-31`),
  `source_declaration_site` equal to the normalized accepted inventory table cell,
  `source_inventory_commit`, `legacy_source_commit`, `target_kind` and, when
  `target_kind` is `stage`, `canonical_stage_id`.
- Updated README, `job-package.schema.json`, `stage-result.schema.json`,
  `result-package.schema.json` and their valid examples.
- Negative fixtures for failed-without-error, succeeded-with-error and missing
  attempt-authority cases, clearly named `*.invalid.json`.
- All analysis artifacts declare candidate version `1.0.0-draft.1`.

Expert decisions/KB/publication/export/comparison/graphic comparison are not owned by
analysis stages. Graphic comparison maps to future Comparison scope, not a fabricated
analysis stage. Distinct Run/fencing semantics are greenfield target extensions, not
legacy parity claims.

## Compatibility

- backward compatible: no; required authority/error/registry semantics tighten
- version bump: bootstrap draft → `1.0.0-draft.1`
- safe before frozen consumers; after freeze requires version/freeze-break procedure

## Required tests

- Command: `PYTHONPATH=/tmp/pdf-analysis-validator-deps python3 -c "import glob,json; from jsonschema import Draft202012Validator as V; [V.check_schema(json.load(open(p))) for p in glob.glob('contracts/analysis/v1/*.schema.json')]"`.
  Expected: exit `0`; every schema passes the Draft 2020-12 metaschema check.
- Command: `PYTHONPATH=/tmp/pdf-analysis-validator-deps python3 -m jsonschema -i contracts/analysis/v1/stage-registry.json contracts/analysis/v1/stage-registry.schema.json`.
  Expected: exit `0`.
- Command: `PYTHONPATH=/tmp/pdf-analysis-validator-deps python3 -m jsonschema -i contracts/analysis/v1/legacy-stage-map.json contracts/analysis/v1/legacy-stage-map.schema.json`.
  Expected: exit `0`.
- Command: `PYTHONPATH=/tmp/pdf-analysis-validator-deps python3 -m jsonschema -i contracts/analysis/v1/examples/job-package.example.json contracts/analysis/v1/job-package.schema.json`.
  Expected: exit `0`.
- Command: `PYTHONPATH=/tmp/pdf-analysis-validator-deps python3 -m jsonschema -i contracts/analysis/v1/examples/stage-result.example.json contracts/analysis/v1/stage-result.schema.json`.
  Expected: exit `0`.
- Command: `PYTHONPATH=/tmp/pdf-analysis-validator-deps python3 -m jsonschema -i contracts/analysis/v1/examples/result-package.example.json contracts/analysis/v1/result-package.schema.json`.
  Expected: exit `0`.
- Command: `PYTHONPATH=/tmp/pdf-analysis-validator-deps python3 -m jsonschema -i contracts/analysis/v1/examples/stage-result.failed-missing-error.invalid.json contracts/analysis/v1/stage-result.schema.json`.
  Expected: non-zero exit because `failed` requires a typed error.
- Command: `PYTHONPATH=/tmp/pdf-analysis-validator-deps python3 -m jsonschema -i contracts/analysis/v1/examples/stage-result.succeeded-with-error.invalid.json contracts/analysis/v1/stage-result.schema.json`.
  Expected: non-zero exit because `succeeded` forbids error state.
- Command: `PYTHONPATH=/tmp/pdf-analysis-validator-deps python3 -m jsonschema -i contracts/analysis/v1/examples/result-package.missing-attempt-authority.invalid.json contracts/analysis/v1/result-package.schema.json`.
  Expected: non-zero exit because the full authority tuple is required.
- Command: `PYTHONPATH=/tmp/pdf-analysis-validator-deps python3 -c "import json,re; from pathlib import Path; inventory=Path('docs/behavior/legacy_capability_inventory.md').read_text().split('### 2.2 Pipeline stage/order declarations',1)[1].split('Declaration coverage:',1)[0]; rows=[line for line in inventory.splitlines() if re.match(r'^\|\s*\d+\s*\|',line)]; expected={(f'LSD-{int(cols[1]):02d}',cols[2].strip().replace(chr(96),'')) for line in rows for cols in [[x.strip() for x in line.split('|')]]}; m=json.loads(Path('contracts/analysis/v1/legacy-stage-map.json').read_text()); r=json.loads(Path('contracts/analysis/v1/stage-registry.json').read_text()); d=m['declarations']; actual={(x['source_declaration_id'],x['source_declaration_site']) for x in d}; stages=[x['stage_id'] for x in r['stages']]; assert len(rows)==len(expected)==len(d)==len(actual)==31 and actual==expected; assert all(x['source_inventory_commit']=='667fb00fe3e45d1ce0bce7860725c1654b4cdeba' and x['legacy_source_commit']=='32b9d903792b30506048a1d42b0e6b2d07aee403' for x in d); assert len(stages)==len(set(stages)); assert all(x['target_kind']!='stage' or x['canonical_stage_id'] in stages for x in d)"`.
  Expected: exit `0`; exact IDs and normalized site names match the accepted 31-row
  ledger, both provenance SHAs are pinned, canonical registry IDs are unique and
  many-to-one legacy-to-canonical mappings remain allowed. Any omission plus
  substitution fails set equality.
- Command: `PYTHONPATH=/tmp/pdf-analysis-validator-deps python3 scripts/validate_bootstrap.py`.
  Expected: exit `0` and a standalone `PASS`.
- Command: `git diff --check -- contracts/analysis/v1`.
  Expected: exit `0` and no output.
- Independent consumer review verifies the authority tuple and conditional
  StageResult error semantics. `W0-QA-01` later owns cross-family consumer tests.

## Integration contract

After acceptance/freeze, control plane and engine rely on registry version,
canonical stage references and the authority tuple. Replaying a byte-identical valid
result is idempotent; different content under the same authority conflicts; stale
authority never publishes. The engine does not write canonical metadata.

## Failure / idempotency / security

- Unknown registry/package major or stage name fails closed.
- Missing required artifact/norm/provider state is explicit failure/partial, never
  silent success.
- Same authority plus same package checksum is idempotent; changed checksum conflicts.
- Manifest/packages contain no secret, permanent credential, internal key or raw
  protected payload.
- Architecture/domain mismatch or unapproved `PD-02`/`PD-03` blocks integration.

## Rollback / feature flag

Contract-only draft; no bypass feature flag. Before freeze, revert this task's path.
After freeze, stop consumers and follow freeze-break/version bump procedure.

## Handoff

- changed files and candidate version/commit recorded by the integrator after
  acceptance
- expanded schema/example commands and results, including expected-invalid fixtures
- new/changed contracts: analysis `1.0.0-draft.1` candidate only
- compatibility, 31/31 mapping evidence, known exclusions and unresolved decisions
- integration notes for control-plane/engine/worker consumers
- proof that no other contract family, migration/runtime/legacy or forbidden hotspot
  changed
