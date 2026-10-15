# W56A-INT-RECOGNISED-CONTEXT-PREP-01 — marked OCR context selector

The new pure selector binds W55b's `prepared.recognised_text` artifact to
the same version's stored `textless_pages`. It includes only recognised
TEXT entries on those pages, preserves their quality flags and excludes
portal IMAGE descriptions and recognised text from PDF-textful pages. A
legacy version without W55b counts and without an artifact yields no OCR
context. Missing or mismatched artifacts for a bundle fail loudly.

`render_context()` places selected entries under an explicit «распознанный
текст — не цитировать» notice and serializes OCR as JSON string data.
Delimiter-looking OCR content cannot add a raw prompt boundary. The
result is context only: later `W56A-PROFILES-01` must continue grounding
quotes against the PDF text layer and report an OCR-only quote as
`quote_in_recognised_text`. That lane also owns input-budget accounting.

Checks: 34 focused AR v2 content/schema/parser/OCR-context tests passed,
including exclusion of IMAGE descriptions, textful pages, invalid flags,
wrong version, missing artifact and delimiter-looking text. Compilation,
direct task governance and `git diff --check` passed. Pytest emitted only
unrelated old `/tmp` cleanup warnings. No full local gate, paid call,
service-backed acceptance or `origin/main` publication was run.

Changed paths: new `analysis/profiles/ar_v2/recognised_context.py`, one
focused test, this task/report and top status in `CURRENT_STATE.md`. No
contract, migration, provider lock, W55b producer, existing runtime module,
dependency, composition root, style, recording, stand file, `VERSION` or
release ref changed. Rollback is a revert before profile wiring; later
changes require a forward correction.

The available stand configuration still selects a stub and no separate
recording route has been identified. MODEL-PIN and live v2 activation
remain blocked. This report makes no OCR quality or beta claim.
