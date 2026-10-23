# AR-V3-BETA-SAVED-SOURCE-01 — saved text for v3 request

`prepare_v3_execution_request` now obtains the text layer from `load_saved_reference_text` under the same current Attempt as the group/set checks. That existing reader verifies the Run and Version, saved `source_preparation` stage, exact Blob bytes, canonical text shape and page count, then rechecks its rows after the read. The v3 assembler requires an explicit positive byte ceiling and checks the returned version against the group before constructing the provider body. It no longer accepts a caller supplied `TextLayer`.

The existing empty production pack registry and v3 executor guard remain in place. This task makes no provider call and records no StageResult, response or citation. The full executor still needs provider identity/mode checks, durable intent/response/cost journaling and Attempt/set rechecks around the effect; CITE and expert review remain separate.

## Verification

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_execution_request.py tests/integration/runs/test_reference_text_input_offline.py tests/integration/runs/test_v3_corpus_citation_bridge.py tests/integration/analysis/test_ar_v3_request_delivery.py -x --tb=short`: **72 passed**.
- New task governance findings: empty. `git diff --check`: passed.
- Changed paths are exactly the five `allowed_paths` of the task. Contracts, migration head, composition root, dependencies/lockfiles, global styles, provider transports, active executor, norm maps and sets are untouched.

## Integration note

After deterministic `source_preparation` and Job/Attempt commits, call the assembler with `max_text_bytes`, installed reviewed pack, provider-selected model and generation pins. Its `saved_text`, sealed request, candidate SHA and provider-body SHA are read-only preparation results, not durable dispatch authority. Recheck current Attempt/set immediately before and after the model effect.
