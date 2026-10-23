# AR-SIX-RUN-SCOPE-BRIDGE-01 — six scopes in the unserved v3 corpus bridge

**Task:** [AR-SIX-RUN-SCOPE-BRIDGE-01](tasks/AR-SIX-RUN-SCOPE-BRIDGE-01.md). **Base:** `0205e2f63c4b41bab5b99aa4868170858c290772`. On 2026-10-23 the owner chose **six separate Runs** for F1/F2/A1/A2/S1/S2, preserving shared project context and each Run's own provenance. This code slice binds that choice into the existing *unserved* draft; it does not start or aggregate those Runs.

The exact fixed membership is F1 C01–C03, F2 C04–C10, A1 C11–C14, A2 C15–C20, S1 C21 and S2 C22. The canonical composition SHA-256 is `79396188486c430729213279fb7c1c8fca7c13ede3f3f13388d06d9f93bbb781`. The partition module, selected-item parser and scoped request code adapt the completed pure source at `c4ba51e7`/`c7860132` to this development tree. They prove C01–C22 totality, exact ordered membership and the existing 22,000-character W57 part limit; they do not judge source editions or project applicability.

`prepare_v3_corpus_request` now requires a scope and composition digest. After the Attempt-fenced saved-set reader verifies Blob custody and Run/profile/map/set identity, the scoped request compares the set's selected C item sequence with the fixed membership before constructing prompt material. The request SHA includes the scope, composition and item IDs. The local response replay rebuilds the *same scoped* request; a rebound scope is refused before any publication candidate. Wrong norm labels still yield no candidate.

The caller must obtain scope/composition/map identity from an approved six-map pack; free arguments are not evidence of approval. The bridge remains unserved and writes no CITE StageResult or finding. No provider, router, DB, Blob, migration or contract was changed. Existing unscoped pure draft calls retain their original format and digest for prior tests/recordings, but this Run bridge has no unscoped entry path.

## Checks and integration

- Focused partition, scoped request, bridge, existing v3 request/prompt/evaluation and programme tests: **70 passed, 6 skipped**. Six optional repaired-bundle checks skipped because that large bundle is not mounted in this worktree.
- Changed Python modules compile; staged whitespace and exact-path proof are recorded at handoff. No full gate under `R-135`.
- Future map owner: approve and seal six distinct map identities and verified sets after source editions, C15 and C21/C22, full corpus custody and actual-window budget are resolved. The decision sheet is `AR-NORM-MAP-APPROVAL-PREP-01.md`.
- Future runtime owner: persist each Run's selected scope/map/set and shared project-review relation; register a new v3 profile/bundle; prove HTTP/pull/SSH request equality, provider provenance and CAP-01 before dispatch. Future CITE owner rechecks current Attempt and saved model effect, then writes grounded citations and CITE StageResult transactionally. An absent/ambiguous Run scope or set refuses; no v1 fallback.

Rollback is a forward revert of the additive scope module and the scoped fields/calls. No data migration or feature flag exists here. Forbidden contracts, migrations, dependencies, composition root, global styles, router/UI, provider transport, corpus, `origin/main`, tags and deployment host remain untouched.
