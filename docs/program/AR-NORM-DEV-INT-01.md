# AR-NORM-DEV-INT-01 — development candidate and draft-profile check

**Base:** `origin/dev=3bc7dae1a62ccd871ed42fc364ffa139cc2313f3`.
**Candidate:** local branch `task/ar-normative-slice-audit-01` in
`.local/worktrees/codex-ar-normative`. This is code integration evidence, not a
release or a beta acceptance result.

## Implemented here

The completed `AR-SET-PROMOTION-01` commits were replayed on the development
base without conflict. `prepare_promotion` binds an exact snapshot/build,
reviewed-map input and independently expected set/catalogue digests; its
admission and finalization use the existing two-role custody outbox. Exact
replay preserves the set identity. `RunRepository.create` can freeze a verified
set ID on INSERT, and `frozen_input_digest` can include its SHA-256. Both inputs
remain absent on the served v1/v2 path. No contract or migration changes were
needed; 0023 already provides the relation and nullable Run column.

The source task's isolated PostgreSQL/Blob acceptance is recorded in
`AR-SET-PROMOTION-01.md`. This replay was checked with container-free tests;
it needs a fresh service-backed readback on the final merged candidate.

## Technical check of draft section profiles

All **14** package manifests on this development base carry `status: draft`:
13 legacy ports (AI, PS, POS, TX, KJ, KM, OV, VK, PT, EOM, SS, ITP, GP) and the
authored PB profile. AR remains the built-in v1 profile. The package tests
verified the 15-code catalogue, unique profile/bundle identities, exact legacy
source hashes at the pinned commit, package layout, v1 question/categories and
output contract, and the PB-specific exclusions. **45 passed.** A separate
focused AR v2/v3 and retrieval check passed **58** tests. These checks establish
technical integrity, not expert quality. The existing synthetic recorded runs
cover AI, PS, POS and TX only; the other draft profiles have no independent
field positive/negative cases or recorded model responses. None was changed to
`reviewed`. `D-178` and the per-section questions in
`W59-SECTION-PROFILES-01.md` remain open; PB also has
`src/auditmanager/analysis/text/profiles/pb/open_questions.md`.

## Remaining functional boundaries

| Slice | Present | Required before claiming the slice works |
| --- | --- | --- |
| W56a | Recorded-only v2 profile, durable text/merge/publication executor bridge, seven categories and severity fields | A concrete served recorded fixture/selection and end-to-end service acceptance; live model and price pin is still STOP in `W56A-MODEL-PIN-01` after the gateway returned a different model. |
| W57a | Retrieval, citation grounding, certified read preparations and this candidate's set promotion | Independently reviewed normative map and expected digests, qualified snapshot/set, v3 profile and CITE stage. `getRunNormVerification` still answers a typed refusal. |
| W57b | Run norm-reference read and XLSX export already served | Review the 57 unparsed corpus slugs against the promoted catalogue and finish the source/edition rules before claiming complete normative coverage. |
| W56b | Saved text-window, crop and region readers with Attempt fencing | Owner-frozen vision/model budget and chunk/critic semantics, durable multi-call execution and a served recorded path. |

## Checks on this candidate

- Promotion, Run pin, retrieval candidate and qualification: **37 passed**.
- Programme contract: **28 passed**.
- Draft package and registry: **45 passed**.
- Focused recorded v2, v3 citation and profile content: **58 passed**.
- Python compilation and `git diff --check`: passed.
- No paid model call, stand action, full gate or remote publication was made.

## Integrator handoff and ownership proof

Review commits replayed from `99fe8934`, `80d3874a`, `3f3abb1f` and
`968ea008` against the exact dev base, then run the source task's isolated
PostgreSQL/Blob check on the final candidate. Keep the set unselected by normal
runs until map approval and v3 stage ownership are present. Retain all 14
section statuses as `draft` pending expert cases and review.

The changed-path proof is `git diff --name-only 3bc7dae1..HEAD`: only the
four original-citation/set-promotion documentation paths, three norms source
paths, two Run source paths, three focused test paths and this task/report are
in the candidate. `contracts/**`, migrations, root locks, composition, API,
web, global styles, `CURRENT_STATE.md`, refs, tags and stand are untouched.
