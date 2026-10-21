# W56B-INT-CHUNK-PREFLIGHT-PREP-01 — saved TEXT window preflight

Base: `origin/dev` candidate 33 at
`77d39efedd4d5c74582a02dbf5ea86acb4b054f7`.

The additive `partition_text_layer` function accepts the existing validated
`TextLayer` and a caller-supplied positive maximum number of **document text
characters per window**. It rechecks a directly constructed layer, partitions
contiguous whole pages greedily, and returns immutable windows carrying
VersionUid, normalization ID, ordinal, page bounds, original global Unicode
offsets and exact text. Empty pages beside text remain covered. An all-blank
layer or any page longer than the ceiling refuses the entire plan; no partial
tuple escapes. No source text is normalized, shortened or decorated.

## Checks

- Focused container-free suite plus the existing text-layer validation:
  **40 passed**. Cases cover Unicode code point offsets, a quote crossing a
  window's local-to-global coordinate mapping, empty and whitespace-only
  pages, exact ceiling,
  oversized later page, malformed ceilings and forged layer metadata.
- Python compilation, direct task governance, frozen SHA-256 readback,
  whitespace and exact path proof: recorded at handoff.
- No Docker, PostgreSQL, S3, proxy, paid call or complete gate was run. The
  W55b release gate owns the host; R-135 defers the full beta gate.

## Contracts and limits

No contract, migration, stage registry, existing producer/consumer, API/UI,
composition, dependency or runtime behavior changes. The ceiling is an
explicit input, **not** a model-safe value inferred by this module. A future
caller must first reserve room and price for every request's fixed prompt,
response schema, normative context and output, bind this text layer to the
current saved Run/Attempt, and journal each call. W55b's one-call pypdfium2
input budget cannot simply be reused as the pdfplumber text-layer ceiling.

The partition makes no decision about overlap, splitting an oversized page,
cross-window contradictions, OCR, normative citations, provider choice or
multi-call resume. It does not publish findings. These require the W56b freeze,
owner rulings and integration tests before activation.

Rollback is removal of the additive module and test before wiring; no data
rollback or feature flag is needed.

Only these four paths change:

- `src/auditmanager/analysis/text/chunk_preflight.py`;
- `tests/integration/analysis_text/test_chunk_preflight.py`;
- `docs/program/tasks/W56B-INT-CHUNK-PREFLIGHT-PREP-01.md`;
- this report.

The integrator can cherry-pick the exact source commit as an unserved W56b
preparation. A later W56b stage may consume the windows only after freezing
budget, effect and cross-window semantics, with real saved-input acceptance.
