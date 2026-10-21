# W57A-INT-V3-LOCAL-EVALUATION-PREP-01 — pure v3 response replay

**Base:** local W57a request candidate `9978ded43b3ac42aa5327dcf552f11097e15ddd2`. **Status:** isolated unserved source; no provider, DB/Blob, runtime or remote publication.

The evaluator accepts a supplied response only when its claimed request digest matches the draft candidate and the entire candidate can be rebuilt from the same set bytes, PDF text layer and OCR selection. It reparses those bytes for local paragraph/label bindings, strictly parses the response and invokes PDF-first/norm-second grounding. A changed unselected normative paragraph refuses because its set SHA changes. The result contains accepted/rejected diagnostics, malformed/salvaged counts and the SHA-256 of raw response text; it creates no finding or expert verdict.

## Checks

- Focused v3 evaluator, request, parser and grounding tests: **37 passed**.
- Program governance: **16 passed**.
- `py_compile`, `git diff --check` and frozen hashes: passed; clean-tree technical handoff is generated after the local commit.
- Tests cover response/set/PDF/schema/OCR mismatch, PDF-before-norm withholding, OCR-only refusal, malformed untruncated refusal and complete-prefix salvage when explicitly truncated.

## Integration

Cherry-pick after `9978ded4`. The later PROFILE/CITE owners must prove Run/Attempt and Blob custody, provider response provenance, qualified set/reviewed map, G-11 and CAP-01; only then may a guarded runtime stage use local diagnostics. This replay's accepted entries are candidates, not canonical findings.

Changed files are exactly this report, formal task, additive evaluator and tests. Contracts, migrations, root dependencies, W54/W56b, v1/v2 production, norms context, API/UI, composition root, `CURRENT_STATE.md` and remote refs are untouched.
