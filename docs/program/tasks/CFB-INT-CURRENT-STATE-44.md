# Task CFB-INT-CURRENT-STATE-44 — align current state with v0.6.0 release

task_id: CFB-INT-CURRENT-STATE-44

## Outcome

The mandatory `CURRENT_STATE.md` entry identifies the W55b v0.6.0 main
release and owner waiver, the later dev43 slices, and the still-unpublished
normative corpus without making a perishable deployed-SHA claim.

## Depends on

- `W55B-INT-TAG-01`, completed at `72fa7f69afc93890b9e0c50fb1b4ccd66ee810e8`.
- `CFB-INT-DEV-PUBLISH-43`, completed at `0461042487cc0e2199d2e273c9001b5c88781d45`.

## Frozen inputs

- base commit: `0461042487cc0e2199d2e273c9001b5c88781d45`
- `origin/main` and `v0.6.0`: `37393a979a430e490843d7f410e9eca9491a4ea1`;
- dev API 48 paths / 55 operations / 131 schemas, errors 25, migration head `0023_norm_citations`;
- W55b release API 47 paths / 54 operations / 123 schemas, migration head `0021_portal_bundles`;
- owner-host verification in `W55B-INT-MAIN-VERIFY-ADDENDUM-01.md`;
- owner waiver in `W55B-INT-TAG-01.md`;
- corpus 674 documents / 31,619 files / 348,777 paragraphs / 55,702 chunks, 121 repair pages.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the development state still says main was unchanged and W55b was not deployed after the tag and host proof.

### P-01 — stale live-state text in the exact base

- captured_at: 2026-10-16
- command: `git show 0461042487cc0e2199d2e273c9001b5c88781d45:docs/program/CURRENT_STATE.md | rg -n 'main is unchanged|None of these candidates has been|No current W54 corpus'`
- captured_output:
  ```text
  5:`37393a97` counts `GATE OK` under R-125; main is unchanged. See `CFB-INT-DEV-PUBLISH-39.md`.
  95:after a host memory/load window. None of these candidates has been
  105:intermediate dev tasks carry their focused evidence. No current W54 corpus,
  ```
- interpretation: dev39's release status was still presented as current; the earlier detail can remain as a dated snapshot after a corrected current entry.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/CURRENT_STATE.md`
- `docs/program/tasks/CFB-INT-CURRENT-STATE-44.md`
- `docs/program/CFB-INT-CURRENT-STATE-44.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, source/tests, historical release reports, deployment files,
production DB/S3, `origin/main` and tags.

## Non-goals

No runtime change, new deployment, corpus import, credentialed product
check, beta acceptance or workflow fix main publication.

## Deliverables

Corrected live state, retained datestamped dev39 detail, this task/report,
doc guard proof, clean-tree handoff and dev-only fast-forward.

## Required tests

- `tests/contract/api_v1/test_doc_prose_facts.py`,
  `tests/contract/api_v1/test_surface_counts_in_prose.py`, programme
  governance: pass.
- Exact allowed-path diff, whitespace and clean tree; task handoff with
  explicit check argv.
- Fresh remote dev/main/tag read, fast-forward proof, exact-SHA dev push and
  readback. No full gate under R-135 for documentation-only state repair.

## Integration contract

New tasks read a current summary that separates W55b release, dev-only
preparations and the unpromoted W54 corpus. The prior dev39 account is
explicitly contextualised as past state. For present host identity use
`infra/deploy/verify-deployed.sh`, not this prose.

## Failure/idempotency/security cases

Stop if remote dev moves or doc guards fail. Do not record credentials or
invent a current host SHA. Correct future drift with another dated update;
no force push.

## Rollback / feature flag

Documentation only; correct with a later state update. No runtime flag or
data rollback applies.

## Handoff

- changed files: exactly this allowlist;
- contracts: none;
- checks: 93 doc/governance tests plus handoff;
- limits: timestamped observations, no product acceptance or corpus load;
- forbidden hotspots untouched.
