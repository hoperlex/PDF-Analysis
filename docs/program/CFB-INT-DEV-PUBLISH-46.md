# CFB-INT-DEV-PUBLISH-46 — guarded text read and v3 local replay

The published development base is
`acb24b5fadeb819978b4636aef0ef3f708cdaac3`. Reviewed source commits
`79e988f5` and `75240c33` were cherry-picked without conflicts as
`e8b62a90` and `7788ab49`. Their nine changed paths are disjoint. The
`analysis/public.py` export addition has one assigned W56b owner.

The unserved W56b read service uses the caller's transaction to fence the
current Attempt, load the exact Run, Version and saved source stage, bound
the Blob by explicit byte ceiling, read the exact saved reference, verify
the text and all windows, then fence and compare the source rows again.
Its tests use fake ports. It does not derive the W56b budget, reserve an
effect, call a provider or establish real DB/S3 acceptance. The caller must
finish the read transaction promptly and reacquire authority before any
later provider effect.

The unserved W57a evaluator rebuilds the draft request from the supplied
set/PDF/OCR inputs, checks the response's claimed request digest, strictly
parses the response and runs PDF-first/norm-second grounding. It returns
local diagnostics and raw-response SHA-256 only. A matching claimed digest
does not authenticate provider provenance or create a canonical finding.

## Checks

- Combined W56b, W57a, architecture and programme governance selection:
  **95 passed**.
- Additional boundary and public-import checks: **4 passed**.
- Frozen API SHA-256 remains
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
  exact 11-path diff and `git diff --check` pass.
- Clean-tree technical handoff and remote ref readback are recorded after
  this report is committed. R-135 defers the complete beta `make gate`.

No product contract, migration, root dependency, composition root, global
style, served provider/API/UI, W54 corpus payload, production DB/S3,
deployment workflow, `origin/main` or tag changes are included. No beta
acceptance, corpus publication or deployed v0.6.0 change is claimed.
