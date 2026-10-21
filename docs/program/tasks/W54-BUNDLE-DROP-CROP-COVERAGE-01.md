# Task W54-BUNDLE-DROP-CROP-COVERAGE-01 — bind export's crop inventory to source sums

task_id: W54-BUNDLE-DROP-CROP-COVERAGE-01

## Outcome

The actual bundle export refuses a source drop whose `crops_index.json` changed after `SHA256SUMS` or whose indexed crop paths do not exactly match the crop PDF paths in that listing. An omitted source crop cannot silently disappear from the exported custody slots.

## Depends on

- `W54-BUNDLE-01` — completed export, bundle and custody format;
- `W54-CORPUS-SUMS-BINDING-01` — completed W54 source-listing pin in operator preflight.

## Frozen inputs

- base/published development commit: `95de4f6b4e10a8b60f57ae84ab66156917c7b96c`;
- W54 plan SHA-256: `b1b4acbf7ce02c4ef8b14533dedc8d7c9e64404b2f4cc0cc5c6342c9d7fdaf71`;
- W55 plan SHA-256: `9f4e0f204284347bc3ead59423a5cff830bbc9298ceaa2d47e1412f640b92b64`;
- source listing SHA-256: `eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`;
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- development API 48 paths / 55 operations / 131 schemas, errors 25, migration head `0023_norm_citations`;
- bundle format `auditmanager-norm-bundle/1`, no format or identity change.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: export trusts the crop index without comparing its bytes or complete crop path set with the supplied source sums.

### P-01 — export loads sums and index independently

- captured_at: 2026-10-16
- command: `rg -n 'read_crops_index\(corpus\)|def read_crops_index|read_drop_sums\(drop_sums\)|out.mkdir' src/auditmanager/norms/bundle/export.py`
- captured_output:
  ```text
  327:def read_crops_index(corpus: Path) -> dict[str, tuple[str, ...]]:
  532:    sums_sha256, sums = read_drop_sums(drop_sums)
  535:    crops = read_crops_index(corpus)
  536:    out.mkdir(parents=True, exist_ok=True)
  ```
- interpretation: the index is not compared with the listing before staging. A separate synthetic reproduction removed one indexed crop and its file while retaining the original sums; `write_bundle` succeeded with four instead of five slots. This does not claim that the real source drop is damaged.

### P-02 — the actual frozen source is consistent with the proposed rule

- captured_at: 2026-10-16
- command:
  ```sh
  PYTHONPATH=src /root/projects/PDF-Analysis/.local/worktrees/w55b-main-candidate/.venv/bin/python - <<'PY'
  import hashlib, json
  from pathlib import Path
  from auditmanager.norms.corpus_source import read_drop_sums
  root = Path('/root/projects/PDF-Analysis/.local/norms')
  sums = read_drop_sums(root / 'corpus-sums/2026-10-15/SHA256SUMS')
  data = (root / 'corpus/crops_index.json').read_bytes()
  entries = json.loads(data)
  indexed = {f"{entry['slug']}/crops/{entry['block_id']}.pdf" for entry in entries}
  listed = {path for path in sums.entries if '/crops/' in path and path.endswith('.pdf')}
  print('index bytes', len(data), 'sha_matches', hashlib.sha256(data).hexdigest() == sums.entries.get('crops_index.json'))
  print('index entries', len(entries), 'unique_paths', len(indexed), 'crop paths in sums', len(listed),
        'missing', len(indexed - listed), 'extra', len(listed - indexed))
  print('unexpected crop-like summed paths', sum('/crops/' in path and path not in listed for path in sums.entries))
  PY
  ```
- captured_output:
  ```text
  index bytes 7037392 sha_matches True
  index entries 28246 unique_paths 28246 crop paths in sums 28246 missing 0 extra 0
  unexpected crop-like summed paths 0
  ```
- interpretation: this guard accepts the present real source index and listing. It does not re-hash all source PDFs or prove their bytes still match the listing.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/bundle/export.py`
- `tests/integration/norms/bundle/test_export_offline.py`
- `docs/program/tasks/W54-BUNDLE-DROP-CROP-COVERAGE-01.md`
- `docs/program/W54-BUNDLE-DROP-CROP-COVERAGE-01.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root, global styles, `CURRENT_STATE.md`, other tasks/reports, source corpus/sums, promotion database/dump, repair journal, build/bundle payloads, credentials, S3/stand, refs and tags.

## Non-goals

No full drop rehash, database read, paid repair, embedding build, real bundle export/import, DB/S3 publication, full gate or beta qualification. The exporter remains generic; its caller/operator pins the W54 sums digest.

## Deliverables

An actual export guard before staging, tests that show the prior accepted omission and changed index, and a measured report. Reuse the existing canonical source-sums parser.

## Required tests

- `PYTHONPATH=src:. <lock-matched-venv>/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/bundle/test_export_offline.py`;
- read-only comparison of real index digest and crop path sets with the frozen listing;
- `python3 -m compileall -q src/auditmanager/norms/bundle/export.py tests/integration/norms/bundle/test_export_offline.py`;
- one reversing mutation, direct task governance, `git diff --check`, exact allowed-path proof.

## Integration contract

Before creating a staging directory, export checks that the index's bytes equal the hash recorded in the supplied `SHA256SUMS`, and that its exact crop PDF path set equals that listing's crop PDF path set. It refuses a mismatch; a matching listing is still subject to the exporter’s existing per-object byte checks and the operator’s complete source checksum verification. No bundle format changes.

## Failure/idempotency/security cases

An absent or changed index digest and a listed crop omitted from the index refuse without a staging directory. Repeated valid exports retain existing idempotency. No corpus bytes, credentials or client data enter Git or test output.

## Rollback / feature flag

Revert this offline exporter/test/docs commit. No runtime feature flag or data rollback applies.

## Handoff

- changed files, checks, contracts, limitations and integration note: result report;
- no publication authority or forbidden hotspot ownership.
