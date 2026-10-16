# W57A-INT-SET-PROMPT-INPUT-PREP-01 — pure v3 set-to-grounding input

**Base:** published code-first dev39 `45d5772480f62006b430151d464a7f7200be511b`. **Status:** isolated, unserved source candidate; no remote publication, model call, DB/S3 use or runtime activation.

The new `ar_v3/set_input.py` parses supplied canonical retrieval-set bytes after comparing their SHA-256 with the expected set digest and checking the expected snapshot and reviewed-map digest. It validates the existing builder and quote/value versions, exact prompt-part size and canonical JSON, full reliable paragraph hashes, prompt/full-row identity, sequential `N1…` labels and unique canonical paragraph IDs. Different map items may bind the same paragraph under separate labels. Its result supplies the exact `prompt_part`, unique `NormParagraph` values and `NormLabelBinding` values to the existing v3 grounding function.

The parser cannot prove where its bytes came from. A later owner must call it only after `load_verified_retrieval_set` has checked current Attempt, Run pin, confirmed custody and full Blob bytes, and after the registered v3 map identity is available. The parser adds no profile registration or prompt bundle. Those remain blocked by the reviewed W54-derived map/qualified snapshot and the `CAP-01` measurements that set v3's output cap; no model choice or cap was invented here.

## Checks

- Focused offline suite, including actual set-builder bytes roundtripped into grounding input: **19 passed**.
- `py_compile`, `git diff --check`: passed.
- Frozen API, stage, domain, error and migration SHA-256: unchanged against the task inputs.

## Integration

Cherry-pick the bounded commit after dev39. A later W57a PROFILE/CITE task owns the caller, registered profile/map, prompt rendering, Run/Attempt fencing, real DB/S3 acceptance and served route. The parser's result alone is a candidate, never a verified citation or canonical finding.

Changed paths are exactly this report, its formal task, the pure parser and its offline tests. `contracts/**`, migrations, locks, `norms/public.py`, existing builders/readers, composition root, API/UI, `CURRENT_STATE.md` and remote refs were untouched.
