# W56A-INT-GROUNDING-PREP-01 — OCR-only quotation diagnostic

The new pure AR v2 resolver delegates PDF anchoring to the existing exact
text-layer resolver. A quotation absent from the PDF but present in marked
OCR on the claimed page yields `quote_in_recognised_text` with no offsets.
A quotation on another PDF page retains the wrong-page reason; OCR on
another page or a near match cannot repair a citation. Unknown OCR pages
are refused.

This is preparation for `W56A-PROFILES-01`, not an active grounding stage.
Runtime still needs to persist the sealed diagnostic and reject a proposal
whose required evidence is unresolved. MODEL-PIN and PROVIDER remain
blocked, and this helper makes no provider request.

Checks: 33 focused parser/OCR/grounding tests passed; module compilation,
direct task governance (`[]`) and `git diff --check` passed. Exact changed
paths are this task/report, `CURRENT_STATE.md`, the new helper and its new
focused test. The optional Ruff executable is absent from the project venv;
the required bounded checks above are complete. No full local gate was run.

No shared
contract, migration, provider lock, existing application module, dependency,
composition root, style, recording, deployment file, `VERSION` or
`origin/main` ref is changed. Rollback is a revert before wiring.
