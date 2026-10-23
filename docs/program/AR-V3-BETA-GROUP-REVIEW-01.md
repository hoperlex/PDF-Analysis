# AR-V3-BETA-GROUP-REVIEW-01 — six scoped review outcomes

The read-only group service now preserves all six F1/F2/A1/A2/S1/S2 members in order. A queued or running member stays pending; a failed or cancelled member retains its Run terminal reason; a published or partial member receives a verified review or an explicit typed verification refusal. The group is reread after collection, so a membership/state change cannot produce a mixed-time answer.

The visible projection contains each C-topic's review state, source IDs and provisional citation count, plus grounded page/quote and normative paragraph references. Internal Blob pointers, provider hashes, reply text, prompt and model payload do not enter that projection. Every topic still says `requires_expert_review`; no numerical or legal conclusion is made.

## Verification and handoff

- Task: [AR-V3-BETA-GROUP-REVIEW-01](tasks/AR-V3-BETA-GROUP-REVIEW-01.md), frozen from `e4001a2c21aabd0b5e1af4b97ea8169da26ecf48`.
- Group outcome/projection tests: 5 passed; wider v3 reader, worker, CITE and journal checks: 101 passed.
- Python compile and `git diff --check`: passed. Full `make gate` remains deferred under R-135; local PostgreSQL is unavailable.
- No contract, migration, root dependency/lockfile, composition root, router, React or global style changed.

## Next integration boundary

A contract/API/UI task can expose this projection through a distinct group review read. The existing `getRunNormVerification` response describes canonical findings and should keep that meaning. Both production trusted-pack registries remain empty until an approved six-set pack and target-stand acceptance exist.
