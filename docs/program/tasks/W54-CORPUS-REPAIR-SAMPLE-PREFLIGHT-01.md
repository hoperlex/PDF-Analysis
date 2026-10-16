# Task W54-CORPUS-REPAIR-SAMPLE-PREFLIGHT-01 — bind the offline plan before paid sample

task_id: W54-CORPUS-REPAIR-SAMPLE-PREFLIGHT-01

## Outcome

The metadata-only W54 preflight has a `repair-sample` step that refuses an absent,
unbound or changed zero-call plan before the later credentialed operator run. It
compares the plan with the verified source/dump markers and the owner-selected
model without opening corpus PDFs, dump payload, PostgreSQL, S3 or proxy.

## Depends on

- `W54-CORPUS-PROMOTION-01` — completed restore-verified base dump;
- `W54-CORPUS-REPAIR-PLAN-01` — completed 121-page zero-call plan;
- `W54-CORPUS-SPLIT-ROOT-PREFLIGHT-01` — completed separated source and promotion roots.

## Frozen inputs

- base commit: `de3d81085f30301ddc2965f7f4bf927ea738c8b3`
- base/published `origin/dev`: `de3d81085f30301ddc2965f7f4bf927ea738c8b3`;
- W54 plan SHA-256: `b1b4acbf7ce02c4ef8b14533dedc8d7c9e64404b2f4cc0cc5c6342c9d7fdaf71`;
- source manifest SHA-256: `160fdc7ea261b44298757b3a066982fd167b389fde614fb119c4c1d0d72fbb3b`;
- source sums SHA-256: `eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`;
- base dump SHA-256: `e1280373ffd7fa3deaa0716429def1844d7e858e79bae7fbad5ade6d516ff74d`;
- zero-call plan SHA-256: `045f8b636ccae1aa2503015c305575e0a9beb3349055c0aaa365b4474e573365`;
- base snapshot content key: `2026-07-23..2026-08-20+17d.4b74348debf7`;
- selected model: `claude-opus-5`; page count 121; three sample blocks;
- development API 47 paths / 54 operations / 124 schemas, error catalogue 25;
- migration head: `0022_findings_v2`; no database access in this task.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `scripts/norms/corpus_preflight.py` (`INCREMENTS`, CLI `--next-step` choices)
- enumerator_owner: `W54-CORPUS-REPAIR-SAMPLE-PREFLIGHT-01`
- totality_query: `python3 scripts/norms/corpus_preflight.py --help`

## Captured premise evidence

- premise: the plan exists as a separate ignored JSON artifact, but the existing
  preflight has no `repair-sample` step and cannot catch a changed/wrong-model plan.

### P-01 — preflight choices and existing plan

- captured_at: 2026-10-16
- command: `rg -n 'INCREMENTS =|def _dump|def inspect|--next-step' scripts/norms/corpus_preflight.py`
- captured_output:
  ```text
  40:INCREMENTS = {"source-sums": 0, "base-load": 3 * GIB, "restore-verify": 3 * GIB,
  142:def _dump(root: Path) -> str:
  248:def inspect(
  325:    parser.add_argument("--next-step", required=True, choices=sorted(INCREMENTS))
  ```
- interpretation: repair sample has no metadata check. The 364-byte JSON plan and
  its exact SHA are recorded by `W54-CORPUS-REPAIR-PLAN-01`; this task adds only a
  low-cost binding check and cannot qualify source/dump payload bytes.

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
- `docs/program/tasks/W54-CORPUS-REPAIR-SAMPLE-PREFLIGHT-01.md`
- `docs/program/W54-CORPUS-REPAIR-SAMPLE-PREFLIGHT-01.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root, global
styles, `CURRENT_STATE.md`, other task/reports, source corpus/sums bytes,
promotion dump/database/volume, repair journal, embedding/bundle artifacts,
credentials, S3/stand, refs and tags.

## Non-goals

No `sha256sum -c`, dump rehash/restore, actual paid sample/full repair, provider
credential discovery, repaired snapshot, embeddings, bundle, DB/S3 import,
deployment, full gate or beta verdict. No `METADATA_READY` is a publication
qualification or permission to spend.

## Deliverables

An explicit repair-plan metadata result, strict pinned plan digest/shape/model/
base/cost checks, source-sums and dump prerequisites, focused refusal tests and
read-only real-artifact command in a result report.

## Required tests

- `PYTHONPATH=src <venv-python> -m pytest -q -p no:cacheprovider tests/integration/norms/test_corpus_preflight.py`;
- run standalone CLI on the existing absolute source and promotion roots, with
  `--next-step repair-sample` and the ignored plan; report result without secrets;
- `python3 -m compileall -q scripts/norms/corpus_preflight.py tests/integration/norms/test_corpus_preflight.py`;
- `git diff --check`, direct task governance and exact allowed-path proof.

## Integration contract

The operator supplies the exact ignored plan under the promotion root. The
preflight refuses a stale or altered plan; `METADATA_READY` means only cheap
metadata and current host disk/RAM. A separate source checksum recheck,
restore-verified base, credentialed durable repair journal, sample projection,
ceiling and owner ruling still govern paid calls. The integrator may
cherry-pick this exact task commit; this lane does not push or tag.

## Failure/idempotency/security cases

Missing, symlinked or escaping plan, wrong digest, malformed JSON, model/base/
page/sample/cost mismatch, absent sums or restore marker, or low capacity
refuse. Preflight is read-only and never prints plan payload or credential.

## Rollback / feature flag

Revert this script/test/docs commit. No runtime feature flag or data rollback;
existing next-step choices keep their behavior.

## Handoff

- changed files/checks/contracts/limits and exact commit: result report;
- no publication authority.
