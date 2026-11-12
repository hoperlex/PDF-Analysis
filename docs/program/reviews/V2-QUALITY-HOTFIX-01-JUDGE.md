# V2-QUALITY-HOTFIX-01-JUDGE — independent significant-defect review

## Verdict: ACCEPT

- Reviewed SHA: `c665efca6c3db014928a49d32be98c73ce2ea274`.
- Base: `0b9b44a1f0fa859c083bf5c72a5bfd6bf506b02f`.
- Reviewer: independent `block_limits_judge` agent; did not author the hotfix.
- Date: 2026-11-12.
- Scope: approved hotfix items 1–4 only. Review intentionally excludes nits,
  refactoring requests, new stages, benchmark work and full-run/gate certification.
- Significant findings requiring repair: **none**.

## Reviewed boundaries

The new behaviour is gated by the frozen quality policy. Legacy accepted v2 policies
retain their deterministic review; fresh estimates include and price the existing review
cell. A changed quality bundle fails validation before the new calls. The substantive
critic uses the normal Run call/journal/budget path; no separate unmetered call path was
introduced.

Substantive approval requires all three checks, bound evidence, adequate confidence and
complete supplied context. Missing replies remain unreviewed, unchecked alternatives
and insufficient context cannot become a pass, and structural source failures also prevent
approval. Fabricated text citations and references to unattached images are refused.
Advice does not write expert decisions or replace the original observation text.

The new summary projection preserves every origin. It uses reciprocal, same-batch
match/extension references, leaves disputed candidates separate, and retains raw view and
the individual evidence/advice inside groups. The input passport records hashes and
uncertainty; it does not claim that an unresolved sheet is absent or that source coverage
certifies engineering completeness. Legacy presentation remains available for older records.

No API/domain contract, migration, root dependency/lockfile, composition, deployment
configuration or global-style change appears in the reviewed diff.

## Independent checks

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /root/projects/PDF-Analysis/.local/worktrees/plan-exec2/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/analysis_extended/test_v2_quality.py tests/unit/analysis_extended/test_v2_quality_runtime.py tests/unit/analysis_extended/test_original_review_runtime.py
```

Result on the reviewed SHA: **29 passed in 3.09s**. The earlier draft's two new quality
files also passed during review; that draft result is not substituted for the SHA-bound run.

An independent read-only projection of the owner's attached report gave **171 raw
observations → 139 groups, 32 accepted relationships**. Assertions verified that each raw
index occurred exactly once, every accepted match/extension link was represented, the
in-memory input remained identical after canonical serialization and the attachment bytes
were unchanged.

`git diff --check 0b9b44a1f0fa859c083bf5c72a5bfd6bf506b02f..c665efca6c3db014928a49d32be98c73ce2ea274`
passed. Forbidden-hotspot diff was empty. Production code and tests were unchanged by the
reviewer; only this report was written.

## Integration handoff

The exact candidate is accepted for the owner-authorized development publication. Preserve
its release note and independent evidence, re-read remote dev and use a fast-forward only.
This review does not authorize main or certify a deployment/live model run. The reviewer
made no network/model call, full test run, commit, tag, ref update or publication.
