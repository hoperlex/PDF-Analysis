# Comparison ZIP-set reader — agent code review, 2026-10-29

Task: [`CMP-ZIP-SEC-01`](../tasks/CMP-ZIP-SEC-01.md). Reviewed tree: `ac5ee5cc6d593bdb1089ad1f566494ec83794da3`; API `1.11.0`, migration `0040_comparison_ai_reports`. The owner chose an agent code review for D-262 and chose to keep rejecting `__MACOSX/` records. This is a static review of the reader and its existing tests; no archive was uploaded to a running service.

## Verdict

**Reader first use is blocked by one policy mismatch.** `LevelJudge.__call__` rejects a raw member name beginning `__MACOSX/` (`src/auditmanager/ingest/comparison_zip/policy.py:171`) but does not apply that check to the displayed name decoded from a valid Info-ZIP Unicode Path field (`policy.py:175–177`). The shared decoder gives that field precedence over the raw name when the UTF-8 flag is absent (`bundle_archive.py:396–413`). Thus a header named `ordinary.pdf` with a Unicode Path of `__MACOSX/._ordinary.pdf` reaches the PDF-kind branch and, if its bytes are a valid PDF, the reader accepts it. This is a static implication of those branches, not a claim of an executed probe. The owner chose to preserve rejection of the literal `__MACOSX/` prefix; a scoped test and fix must cover both raw and displayed names before `CMP-STAGE-PAIR-01` uses the reader. Case variants are outside this ruling.

The mismatch does **not** put an archive name into a filesystem path: extracted files are still named by the reader's own keys. Its immediate effect is violation of the selected member policy and a misleading acceptance/display hint. The repair should not alter the portal-bundle default policy.

## Reviewed controls

| Boundary | Code evidence | Assessment |
| --- | --- | --- |
| ZIP structure and bounded directory | `bundle_archive.py:439–508`, `:853–869`; `comparison_zip/policy.py:85–95` | EOCD and ZIP64 offsets are checked against the file, entry count is limited to 1,000, and the set policy rejects a central directory over 4 MiB before loading it. |
| Names and paths | `bundle_archive.py:622–635`, `comparison_zip/policy.py:161–202`, `comparison_zip/reader.py:173–179, 238–269` | Raw and displayed names reject traversal/absolute/drive/backslash forms; duplicate keys use NFC and case folding. Chosen keys are `pdf_<index>` or `zip_<index>`; names only become scrubbed hints. The `__MACOSX/` alias gap above remains. |
| Member types | `comparison_zip/policy.py:163–201` | Symlinks, encrypted members and methods other than stored/deflate are refused; only PDF, and ZIP at the outer level, are accepted. Empty directories are structural and counted. A deeper ZIP is refused. |
| Decompression budget | `bundle_archive.py:684–704, 711–789`, `comparison_zip/reader.py:238–264` | Declared size and ratio are checked before unpacking. Actual bytes, CRC and real stream consumption are counted during/after extraction. The nested archive's own bytes and the members inside it spend the same 2 GiB budget. An emitted piece is at most 64 KiB. |
| PDF envelope | `comparison_zip/reader.py:275–295`, `comparison_zip/reader.py:79–86` | By default every PDF passes the existing envelope and one failure refuses the set. A caller may pass its own comparison envelope or `None`; the latter leaves `facts=None` and requires separate validation before storage. |
| Cleanup and error surface | `bundle_archive.py:851–876`, `comparison_zip/reader.py:237–295`, `comparison_zip/refusals.py:31–100` | The shared reader removes its temporary directory on any exception; the set's `ExitStack` closes accepted outer/inner bundles on refusal. Archive errors map to fixed `comparison_zip_*` constraints without echoing names. |
| Portal isolation | `bundle_archive.py:815–848`, `tests/unit/ingest/comparison_zip/test_portal_policy_unchanged.py:59–164` | `PORTAL_POLICY` is the default and the set policy is passed explicitly. The existing differential and portal tests guard that boundary. |

Existing tests cover malformed headers, ZIP64, traversal in raw and Unicode Path names, symlinks, encryption, method restrictions, duplicates, nested depth, budget accounting, ratio padding, PDF envelope refusals, cleanup and deterministic ordinals (`tests/unit/ingest/comparison_zip/`). They do not test a `__MACOSX/` prefix supplied only by Unicode Path; the existing test at `test_adversarial_archives.py:444–449` uses raw names. The original lane recorded 57 successful mutations in `docs/program/CMP-INGEST-ZIP-01.md`; those are prior lane evidence.

This review reran `PYTHONPATH=src ../cmp-seal-c0/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider --basetemp=/tmp/cmp-zip-sec-01-focused tests/unit/ingest/comparison_zip/` after the C2 gate released the host: **183 passed in 5.19 s** (`/tmp/cmp-zip-sec-01-focused.log`). The 57 mutations remain prior lane evidence; the newly found Unicode Path service-prefix case is not among these 183 tests.

## Conditions for the first caller

1. Fix and test the `__MACOSX/` raw/Unicode Path mismatch under a separate source-owning task; keep the owner-selected rejection. Confirm the portal policy remains unchanged.
2. The first upload caller must enforce a bound on the **raw compressed upload** and admission/concurrency before a temporary ZIP is accepted. This reader bounds its central directory and extracted bytes but has no general outer-file byte limit; it is intentionally called with an already-open seekable handle. A large trailing/padded archive can otherwise cost incoming storage even when its extracted members are small. The caller must also check disk readiness for the maximum 2 GiB temporary extraction, as `CMP-INGEST-ZIP-01` report §6 states.
3. The first caller must use the production set policy or a stricter one. `SetPolicy` permits caller-supplied bounds; they are not request fields. It must pass the comparison PDF envelope, or defer each PDF envelope check to bounded work and never store a member while `facts=None`.
4. `CMP-STAGE-PAIR-01` needs a caller-level test for these conditions and for refusal/cleanup of a ZIP-set upload. This review does not certify a caller that has not been written.

No source, contract, migration or runtime behavior changed in this review. The D-262 review path is now decided and performed; the debt stays open until the policy gap is fixed and the first-use caller satisfies these conditions.
