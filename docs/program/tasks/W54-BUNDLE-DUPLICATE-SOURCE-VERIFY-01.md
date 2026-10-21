# Task W54-BUNDLE-DUPLICATE-SOURCE-VERIFY-01 — verify every source path before deduplicating bundle objects

task_id: W54-BUNDLE-DUPLICATE-SOURCE-VERIFY-01

## Outcome

Actual bundle export refuses a PDF or crop changed after the supplied source `SHA256SUMS`, even when another source path with the expected digest has already placed the content-addressed object. The additional custody slot is published only after its own source path has been checked.

## Depends on

- `W54-BUNDLE-01` — completed content-addressed object placer and bundle format;
- `W54-BUNDLE-DROP-CROP-COVERAGE-01` — completed index-to-listing coverage guard.

## Frozen inputs

- base/published development commit: `394a728f8a6f64ecb849f98fccdad687b79f282a`;
- W54 plan SHA-256: `b1b4acbf7ce02c4ef8b14533dedc8d7c9e64404b2f4cc0cc5c6342c9d7fdaf71`;
- W55 plan SHA-256: `9f4e0f204284347bc3ead59423a5cff830bbc9298ceaa2d47e1412f640b92b64`;
- source listing SHA-256: `eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`;
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- development API 48 paths / 55 operations / 131 schemas, errors 25, migration head `0023_norm_citations`;
- bundle format `auditmanager-norm-bundle/1` and per-source checks against the supplied sums; no format change.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: object deduplication binds a later source path to an earlier object without reading that later path.

### P-01 — duplicate digest bypasses the source byte check

- captured_at: 2026-10-16
- command: `rg -n -A 35 'def place\(self, source: Path, slot: ObjectSlot\)' src/auditmanager/norms/bundle/export.py`
- captured_output:
  ```text
  505:    def place(self, source: Path, slot: ObjectSlot) -> str:
  506-        """Place ``source`` for ``slot``; return the SHA-256 of the object now in the bundle."""
  507-        relative = source.relative_to(self._corpus).as_posix()
  508-        expected = self._sums.get(relative)
  509-        if expected is None:
  510-            raise BundleRefused("drop_file_unsummed", f"the drop's SHA256SUMS does not name {relative}")
  511-        if expected in self.objects:
  512-            self.objects[expected][1].append(slot)
  513-            return expected
  514-        target = self._staging / object_path(expected)
  515-        target.parent.mkdir(parents=True, exist_ok=True)
  516-        if self._copy:
  517-            shutil.copyfile(source, target)
  518-        else:
  519-            try:
  520-                os.link(source, target)
  521-            except OSError as exc:
  522-                raise BundleRefused(
  523-                    "object_link",
  524-                    f"{relative} cannot be hardlinked into the bundle ({exc.strerror}); the bundle "
  525-                    "must be on the drop's filesystem, or pass --copy-objects",
  526-                ) from None
  527-        sha, size = sha256_file(target)
  528-        if sha != expected:
  529-            raise BundleRefused(
  530-                "drop_file_differs", f"{relative} hashes to {sha}; the drop's SHA256SUMS says {expected}"
  531-            )
  532-        mode = target.stat().st_mode
  533-        if mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
  534-            os.chmod(target, mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
  535-        self.objects[expected] = (size, [slot])
  536-        return expected
  537-
  538-
  539-@dataclass(frozen=True, slots=True)
  540-class ExportResult:
  ```
- interpretation: the early return omits any read/hash of the second source path. A container-free synthetic reproduction changed the later of two equal-digest source paths, a PDF or crop according to their generated row IDs; `write_bundle` accepted it and produced five custody slots. This does not claim that any real corpus path is damaged.

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
- `docs/program/tasks/W54-BUNDLE-DUPLICATE-SOURCE-VERIFY-01.md`
- `docs/program/W54-BUNDLE-DUPLICATE-SOURCE-VERIFY-01.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root, global styles, `CURRENT_STATE.md`, other tasks/reports, source corpus/sums, promotion database/dump, repair journal, build/bundle payloads, credentials, S3/stand, refs and tags.

## Non-goals

No full source checksum run, database read, paid repair, embedding build, real bundle export/import, DB/S3 publication, full gate or beta qualification. The caller/operator pins the W54 sums digest; this task does not hardcode it into the generic exporter.

## Deliverables

A per-source-path byte check on the deduplicated object branch, a focused changed-source test, and a measured report. The bundle keeps one object file for equal bytes and multiple custody slots.

## Required tests

- `PYTHONPATH=src:. <lock-matched-venv>/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/bundle/test_export_offline.py`;
- bounded `tests/integration/norms/bundle -k 'not postgres'`;
- `python3 -m compileall -q src/auditmanager/norms/bundle/export.py tests/integration/norms/bundle/test_export_offline.py`;
- one reversing mutation, direct task governance, `git diff --check`, exact allowed-path proof.

## Integration contract

For a repeated expected digest, `write_bundle` hashes the newly named source path against the supplied `SHA256SUMS` before adding its custody slot. A missing or changed source path refuses; an equal-byte duplicate still shares one content-addressed bundle object. No bundle format, public contract or import behavior changes.

## Failure/idempotency/security cases

Tampered or missing second PDF/crop paths refuse without publishing an incomplete bundle. The valid duplicate remains idempotent. No corpus bytes, credentials or client data enter Git or test output.

## Rollback / feature flag

Revert this offline exporter/test/docs commit. No runtime flag or data rollback applies.

## Handoff

- changed files, checks, contracts, limits and integration note: result report;
- no publication authority or forbidden hotspot ownership.
