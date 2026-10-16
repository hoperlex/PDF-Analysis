# Task W54-CORPUS-BUILD-TARGET-PREFLIGHT-01 — bind bundle preflight to the selected build

task_id: W54-CORPUS-BUILD-TARGET-PREFLIGHT-01

## Outcome

The read-only `bundle-export` preflight requires the same snapshot ID and reliability-aware chunking profile that the actual bundle exporter receives. It refuses when only another snapshot's canonical checkpoint files exist, instead of reporting metadata readiness for the intended export.

## Depends on

- `W54-CORPUS-BUILD-PLAN-PREFLIGHT-01` — completed canonical embedding-plan recognition;
- `W54-BUNDLE-01` — completed bundle export CLI with required `--snapshot` and `--chunking-profile`.

## Frozen inputs

- base/published development commit: `4c16ccd7ae975d5a32829e9bcdf975f8b12f66e1`;
- W54 plan SHA-256: `b1b4acbf7ce02c4ef8b14533dedc8d7c9e64404b2f4cc0cc5c6342c9d7fdaf71`;
- W55 plan SHA-256: `9f4e0f204284347bc3ead59423a5cff830bbc9298ceaa2d47e1412f640b92b64`;
- source sums SHA-256: `eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`;
- W54 bundle exporter requires `--snapshot` and `--chunking-profile`; only `characters-v2:<target>` is designatable;
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- development API 48 paths / 55 operations / 131 schemas, errors 25, migration head `0023_norm_citations`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the preflight scans all build plans without an expected snapshot/profile, while the exporter requires both on its command line.

### P-01 — preflight and exporter selection differ

- captured_at: 2026-10-16
- command: `rg -n 'def _build|parsed.identity.content_key|return "batch_files_present_unverified"|def inspect|build = _build|build_checkpoint_unavailable|--next-step|--snapshot|--chunking-profile' scripts/norms/corpus_preflight.py src/auditmanager/norms/bundle/cli.py`
- captured_output:
  ```text
  src/auditmanager/norms/bundle/cli.py:6:    python -m auditmanager.norms.bundle export --snapshot <ns_id> \\
  src/auditmanager/norms/bundle/cli.py:7:        --chunking-profile characters-v2:1200 --corpus .local/norms/corpus \\
  src/auditmanager/norms/bundle/cli.py:134:    export.add_argument("--snapshot", required=True)
  src/auditmanager/norms/bundle/cli.py:136:        "--chunking-profile", required=True,
  scripts/norms/corpus_preflight.py:8:        --next-step bundle-export
  scripts/norms/corpus_preflight.py:10:For the first paid repair operation, use ``--next-step repair-sample`` and
  scripts/norms/corpus_preflight.py:240:def _build(root: Path) -> str:
  scripts/norms/corpus_preflight.py:257:        if parsed.identity.content_key != plan.parent.name:
  scripts/norms/corpus_preflight.py:269:            return "batch_files_present_unverified"
  scripts/norms/corpus_preflight.py:324:def inspect(
  scripts/norms/corpus_preflight.py:373:    build = _build(promotion_root)
  scripts/norms/corpus_preflight.py:389:        refusals.append("build_checkpoint_unavailable")
  scripts/norms/corpus_preflight.py:424:    parser.add_argument("--next-step", required=True, choices=sorted(INCREMENTS))
  ```
- interpretation: the preflight can see a canonical build for a different snapshot/profile and still return `batch_files_present_unverified`; the exporter would query the named snapshot/profile instead. This evidence does not say a complete build exists on the real host.

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
- `docs/program/tasks/W54-CORPUS-BUILD-TARGET-PREFLIGHT-01.md`
- `docs/program/W54-CORPUS-BUILD-TARGET-PREFLIGHT-01.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root, global styles, `CURRENT_STATE.md`, other tasks/reports, source corpus/sums, promotion database/dump, repair journal, embedding checkpoint payloads, bundle payloads, credentials, S3/stand, refs and tags.

## Non-goals

No source rehash, snapshot DB read, checkpoint byte/sidecar verification, paid repair, embedding load, bundle export/verify, DB/S3 import, full gate or beta qualification. A caller-supplied snapshot ID is not proof that the database holds the desired repaired snapshot.

## Deliverables

Targeted `bundle-export` metadata check, required CLI inputs and explicit JSON target/refusals, focused wrong/missing/invalid target tests, a read-only real-artifact result and this report.

## Required tests

- `PYTHONPATH=src <lock-matched-venv>/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/test_corpus_preflight.py`;
- actual read-only `bundle-export` preflight with the known base snapshot ID and `characters-v2:1200`, proving it refuses an absent build;
- `python3 -m compileall -q scripts/norms/corpus_preflight.py tests/integration/norms/test_corpus_preflight.py`;
- direct task governance, one reversing mutation, `git diff --check`, exact allowed-path proof.

## Integration contract

For `--next-step bundle-export`, supply `--snapshot <ns_id>` and `--chunking-profile characters-v2:<target>`, matching the subsequent export command exactly. The preflight refuses missing or invalid target inputs; a complete checkpoint of another snapshot or profile does not count. Other next steps keep their old input behavior. `batch_files_present_unverified` still means only a canonical plan with regular named files, not a verified or DB-loaded build. The integrator may fetch and cherry-pick the clean local task commit; this lane does not push.

## Failure/idempotency/security cases

Missing/invalid snapshot ID, non-designatable profile, unrelated canonical checkpoint, symlink or partial files refuse. No corpus payload or credential is read or printed; repeated preflight is read-only.

## Rollback / feature flag

Revert this offline script/test/docs commit. No runtime flag or data rollback applies.

## Handoff

- changed files, checks, contracts, limits and integration notes: result report;
- no publication authority or forbidden hotspot ownership.
