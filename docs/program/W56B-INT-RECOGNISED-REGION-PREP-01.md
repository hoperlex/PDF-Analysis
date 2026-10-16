# W56B-INT-RECOGNISED-REGION-PREP-01 — exact OCR region candidate

Base: published `origin/dev` at
`3d131d2966e0efeea7b53d9662785f253165a9a4`.

The additive pure selector joins a marked `prepared.recognised_text` TEXT
entry with the same version's `geometry.portal_blocks` TEXT region. It requires
the caller's stored textless-page set, an `ok` page and block geometry verdict,
one exact occurrence of the quote in that OCR block, and consistent block/page
identities. The immutable result carries the region, OCR-body character span,
quality flags and source-file digests with `quote_source=recognised`. It cannot
be mistaken for a PDF text-layer offset or a published citation.

## Checks

- New focused container-free tests: **21 passed**, including a committed
  W55b portal bundle read through its actual pure producers.
- Existing OCR-context, recognised-artifact and portal-layout tests:
  **65 passed**.
- Python compilation of the new module and test: passed.
- Direct task governance, frozen-input readback, staged whitespace check and
  exact changed-path proof: see final handoff check.
- No Docker, DB/S3, provider, network or complete gate was used. R-135
  defers the full beta gate; W55b's separate full gate owns the host lane.

## Contracts and limits

No contract, migration, stage registry, existing module, API route, UI,
composition root, provider or production behavior changed. This candidate
does not grant permission to cite OCR in a finding. It does not assess OCR
accuracy, verify the page's actual PDF content, or read Blob references. The
future W56b owner must read checksum-verified artifacts from the same saved
run, obtain `textless_pages` from the version row, and seal the citation shape,
status, storage and publication policy. The `results_sha256` and
`blocks_sha256` fields identify source files within the supplied artifacts;
they do not alone prove common-run custody. Repeated text in one block refuses
because the claim has no explicit OCR offset.

Rollback before wiring is deletion of the additive module and test. No
feature flag or data rollback is needed.

Changed paths are exactly this report, its formal task,
`src/auditmanager/analysis/recognised/region_candidate.py` and
`tests/integration/analysis/recognised/test_region_candidate.py`. The W56b
integrator should bring in those four paths only, then add a separate grant
for saved-artifact custody and approved citation behavior after the pending
W57b and model/region decisions.
