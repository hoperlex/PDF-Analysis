# CMP-STAGE-TEXT-CORE-01 — deterministic evidence core

Task: [`CMP-STAGE-TEXT-CORE-01`](tasks/CMP-STAGE-TEXT-CORE-01.md). The work starts from `9a35c888ff743a65363f63e59d06f34e5acee7aa` on an isolated C3 branch. It owns no API, migration, worker or remote ref.

## Implemented

- `extract_fragments` reads immutable ready `PageProfileData.words`, groups words into complete visual rows, and returns raw text, a conservative canonical form, top-left PDF-point boxes and stable SHA-256 content keys. It refuses malformed geometry, an invalid side, a failed profile, oversized words/rows and invalid UTF-8 before returning a partial result. A scan with no words yields no fragment and makes no absence claim.
- `prove_exact_exclusions` receives confirmed left/right profile pairs, their complete fragment-key manifests and page dimensions. It proves only unique canonical text on a linked pair with a bounded positional distance; text that repeats on either side of the relation set, text shorter than eight characters, a changed engineering value or a distant block remains unproven. `same` and `moved` are deterministic evidence categories. It refuses missing fragment keys, wrong-side fragments, duplicate link/key identity and an incomplete profile manifest.
- Normalisation changes only NFKC presentation, case, `ё`/`е` and whitespace. Numbers, units and punctuation remain material, so `10 кВт` cannot become an exact exclusion of `20 кВт`.

## Evidence and limits

- Scoped unit tests: **9 passed**; package compile and `git diff --check` passed. Tests cover stable box/key extraction, same and moved proof, repeated text within and across sheets, changed engineering value, incomplete evidence, invalid geometry/failed profile/invalid UTF-8, scan without words and positional refusal.
- This is a pure, currently unreachable core. `ComparisonStageTextAdapter` still returns the sealed 503. A later storage/worker slice must derive the manifest from *every* immutable profile of the pinned map revision, persist fragment and proof rows, and perform staleness checks. No mask, raw difference, second-pass hint, screen or full `CMP-STAGE-TEXT-01` parity is claimed.
- No contracts, migration, generated client, root dependency, composition root, global styles, C2 runtime, C3 pair/link internals or remote refs changed.

## Integration instruction

Consume this core only after the caller has verified current pair scope and a confirmed map revision. Read profiles through the comparison public reader. On any extraction refusal, keep the recomputation in an explicit failed state; do not publish a partial set of exclusions. Use the returned boxes as overlay anchors and persist the content keys into the sealed `stage_text_*` tables.
