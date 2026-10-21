# Task W54-CORPUS-BUILD-PLAN-PREFLIGHT-01 — recognize only a canonical embedding plan

task_id: W54-CORPUS-BUILD-PLAN-PREFLIGHT-01

## Outcome

The read-only W54 corpus preflight reports batch files present only when their `plan.json` is the canonical W54 embedding plan, has the frozen profile, and names its containing content-key directory. A fabricated or misbound plan cannot make `bundle-export` metadata-ready.

## Depends on

- `W54-EMBED-01` — completed canonical checkpoint plan reader and frozen embedding profile;
- `W54-CORPUS-SUMS-BINDING-01` — completed source-listing pin in the current preflight.

## Frozen inputs

- base/published development commit: `6f1307412c94de45e67ffdeba71506dc5a0aa8fb`;
- W54 plan SHA-256: `b1b4acbf7ce02c4ef8b14533dedc8d7c9e64404b2f4cc0cc5c6342c9d7fdaf71`;
- W55 plan SHA-256: `9f4e0f204284347bc3ead59423a5cff830bbc9298ceaa2d47e1412f640b92b64`;
- W54 embedding plan format: `auditmanager-embedding-plan/1`, directory `.local/norms/builds/<content_key>/`, profile `bge-m3-dense-v1`, model revision `5617a9f61b028005a4858fdac845db406aefb181`;
- source-listing SHA-256: `eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`;
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- development API: 48 paths / 55 operations / 131 schemas; errors: 25; migration head: `0023_norm_citations`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the current preflight treats any JSON plan with sequential batch indices and corresponding file names as a present build checkpoint, without reading the format or build identity.

### P-01 — current build metadata check

- captured_at: 2026-10-16
- command: `sed -n '234,263p' scripts/norms/corpus_preflight.py`
- captured_output:
  ```text
  def _build(root: Path) -> str:
      builds = root / "builds"
      if builds.is_symlink():
          return "unsafe_directory"
      candidates = [path for path in builds.glob("*/plan.json") if not path.parent.is_symlink() and _is_regular(path)]
      if not candidates:
          return "absent"
      for plan in candidates:
          try:
              batches = json.loads(plan.read_bytes())["batches"]
          except (OSError, ValueError, KeyError, TypeError):
              continue
          if not isinstance(batches, list) or not batches:
              continue
          indices = [row.get("index") for row in batches if isinstance(row, dict)]
          if indices != list(range(len(batches))):
              continue
          vectors = plan.parent / "vectors"
          inputs = plan.parent / "inputs"
          if vectors.is_symlink() or inputs.is_symlink():
              continue
          if all(
              _is_regular(inputs / f"batch-{index:05d}.jsonl")
              and _is_regular(vectors / f"batch-{index:05d}.jsonl")
              and _is_regular(vectors / f"batch-{index:05d}.jsonl.sha256")
              for index in indices
          ):
              return "batch_files_present_unverified"
      return "plan_only_or_partial"

  ```
- interpretation: a malformed/fabricated plan with three named files can satisfy this metadata condition. The preflight does not claim verified vectors, but the `bundle-export` readiness condition uses it; the canonical parser is already available in the W54 embedding module.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `scripts/norms/corpus_preflight.py`
- `tests/integration/norms/test_corpus_preflight.py`
- `docs/program/tasks/W54-CORPUS-BUILD-PLAN-PREFLIGHT-01.md`
- `docs/program/W54-CORPUS-BUILD-PLAN-PREFLIGHT-01.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root, global styles, `CURRENT_STATE.md`, other tasks/reports, source corpus/sums, promotion database/dump, repair journal, embedding checkpoint payloads, bundle payloads, credentials, S3/stand, remote refs and tags.

## Non-goals

No vector-byte or sidecar verification, source rehash, database build/load, paid repair, bundle export/verification, DB/S3 publication, full gate, deployment or beta qualification. A canonical plan alone cannot prove a completed embedding build or name the current database snapshot.

## Deliverables

The metadata preflight calls W54's canonical plan parser and identity check, bounds plan size, retains the existing statuses and exit codes, and has focused valid/fabricated/misbound/oversize-plan tests plus a report.

## Required tests

- `PYTHONPATH=src <lock-matched-venv>/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/test_corpus_preflight.py`;
- read-only `bundle-export` preflight on the real separate source/promotion roots (no build or bundle operation);
- `python3 -m compileall -q scripts/norms/corpus_preflight.py tests/integration/norms/test_corpus_preflight.py`;
- direct task governance, `git diff --check` and exact allowed-path proof.

## Integration contract

`build_checkpoint=batch_files_present_unverified` means a canonical plan with the frozen profile is under `builds/<its content_key>/` and each declared input/vector/sidecar pathname is a regular file. The preflight still does not read vector bytes or sidecar contents and does not certify a complete build; the owning `embedding status/load` and bundle verifier remain mandatory. Invalid plans become `plan_only_or_partial`. No served behavior or public contract changes. The integrator may fetch and cherry-pick the clean local task commit; this lane does not push.

## Failure/idempotency/security cases

Wrong plan format/profile, noncanonical plan, directory/content-key mismatch, malformed or oversized plan, symlinked inputs/vectors, or missing batch files cannot yield `batch_files_present_unverified`. The command is read-only and prints no plan payload, document text or secret.

## Rollback / feature flag

Revert this offline script/test/docs commit. No feature flag or data rollback applies.

## Handoff

- changed files, checks, contracts, limits and integration instructions: result report;
- no publication authority or forbidden hotspot ownership.
