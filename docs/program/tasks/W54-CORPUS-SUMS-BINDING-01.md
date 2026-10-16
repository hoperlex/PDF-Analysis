# Task W54-CORPUS-SUMS-BINDING-01 — bind every post-checksum preflight to the frozen source listing

task_id: W54-CORPUS-SUMS-BINDING-01

## Outcome

The read-only W54 corpus preflight refuses a changed `SHA256SUMS` listing for every step after `source-sums`, even when its file paths still match the source tree. This prevents a metadata-ready result against an unreviewed listing before base load, restore verification or bundle export.

## Depends on

- `W54-CORPUS-OPERATE-01` — completed source checksum listing;
- `W54-CORPUS-REPAIR-SAMPLE-PREFLIGHT-01` — completed frozen listing check for `repair-sample`;
- `W54-CORPUS-CPU-WINDOW-PREFLIGHT-01` — completed current preflight capacity guard.

## Frozen inputs

- base/published development commit: `f0b12ea705a9ccb476b5b69a5797de7d3731f543`;
- W54 plan SHA-256: `b1b4acbf7ce02c4ef8b14533dedc8d7c9e64404b2f4cc0cc5c6342c9d7fdaf71`;
- W55 plan SHA-256: `9f4e0f204284347bc3ead59423a5cff830bbc9298ceaa2d47e1412f640b92b64`;
- source listing SHA-256: `eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`;
- source manifest SHA-256: `160fdc7ea261b44298757b3a066982fd167b389fde614fb119c4c1d0d72fbb3b`;
- API contract SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- analysis stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- development API: 48 paths / 55 operations / 131 schemas; errors: 25; migration head: `0023_norm_citations`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the existing preflight checks the parsed listing's path set for all steps, but compares its frozen digest only for `repair-sample`.

### P-01 — the digest check is limited to one step

- captured_at: 2026-10-16
- command: `rg -n 'source_sums|sums_sha|SOURCE_SUMS_SHA256|next_step == "repair-sample"' scripts/norms/corpus_preflight.py`
- captured_output:
  ```text
  41:SOURCE_SUMS_SHA256 = "eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5"
  82:    source_sums: str
  265:def _bundle(root: Path, drop_sums_sha: str | None) -> str:
  291:            or metadata["drop"].get("sums_sha256") != drop_sums_sha
  362:    source_sums, sums_sha = _sums(source_root, source_paths)
  365:    bundle = _bundle(promotion_root, sums_sha)
  367:            if next_step == "repair-sample" else "not_checked")
  368:    if next_step != "source-sums" and source_sums != "listed_unverified":
  369:        refusals.append("source_sums_unavailable")
  378:    if next_step == "repair-sample":
  379:        if sums_sha != SOURCE_SUMS_SHA256:
  380:            refusals.append("source_sums_digest_mismatch")
  406:    return Result(next_step, manifest_sha, docs, files, source_sums, dump, build, bundle,
  ```
- interpretation: a listing with the same paths and changed digest can pass the non-repair steps' listing condition. This does not say any source PDF byte has changed; only the listing is tested here.

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
- `docs/program/tasks/W54-CORPUS-SUMS-BINDING-01.md`
- `docs/program/W54-CORPUS-SUMS-BINDING-01.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root, global styles, `CURRENT_STATE.md`, other tasks/reports, source corpus/sums, promotion dump/database, repair journal, embedding/build/bundle payloads, credentials, S3/stand, remote refs and tags.

## Non-goals

No source file rehash, dump rehash/restore, paid repair, embedding build, bundle verify/export, DB/S3 import, full gate, deployment or beta qualification. This metadata check cannot establish that listed digests match the source files.

## Deliverables

One shared post-`source-sums` digest refusal, focused positive and changed-listing tests, a read-only real-artifact result and this report.

## Required tests

- `PYTHONPATH=src <lock-matched-venv>/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/test_corpus_preflight.py`;
- read-only `base-load` preflight against explicit actual source and promotion roots, recording only statuses/refusals;
- `python3 -m compileall -q scripts/norms/corpus_preflight.py tests/integration/norms/test_corpus_preflight.py`;
- direct task governance, `git diff --check`, exact allowed-path proof.

## Integration contract

`source-sums` remains preparatory and can run before a listing exists. `base-load`, `restore-verify`, `repair-sample` and `bundle-export` require the pinned listing digest whenever a listing is present, and continue to refuse an absent/malformed/path-mismatched listing. A passing metadata preflight still requires the owning `sha256sum -c` and later verifiers. The integrator may cherry-pick this exact source commit; this lane has no publication authority.

## Failure/idempotency/security cases

Changed checksum values with the same paths refuse `source_sums_digest_mismatch`; missing or invalid listings keep their existing `source_sums_unavailable` refusal. The command is read-only and prints no source document text or secrets.

## Rollback / feature flag

Revert this script/test/docs commit. No runtime feature flag or data rollback applies to the offline preflight.

## Handoff

- changed files, checks, contracts, limits and exact commit: result report;
- forbidden hotspots untouched; no push.
