# Task W52-RELNOTES-01 — authored release history and prose rules

task_id: W52-RELNOTES-01

## Outcome

The `0.3.0` release and `0.2.0` archive display accurate Russian
product-facing notes, checked against W48–W52 evidence and strict prose
rules. The English technical release process and ledger scaffold exist.

## Depends on

- `W52-INT-C-TRANSLATE-01`, published on `origin/dev`.
- `W52-INT-C2-GRANT-01`, published on `origin/dev`.

## Frozen inputs

- Start from the exact `origin/dev` SHA read back by
  `W52-INT-C2-GRANT-01`; record it in the lane report.
- `VERSION=0.3.0`; API 30 paths / 37 operations / 83 schemas;
  23 error codes; domain revision 9 / 29 identities; migration head
  `0016_release_notes`; `contract_version=1.0.0-draft.1`.
- `dispatch/W52-PLAN.md` §§3.1, 3.4, Stage C2 and §5; sealed
  `release-notes/schema.json` and generated release client.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: `rg --files release-notes | sort` shows the same two
  authored SemVer entries; the new dictionary is a known non-entry

## Captured premise evidence

- premise: the current authored entries are minimal revision-1
  placeholders; there is no dictionary, prose suite or technical ledger.

### P-01 — authored-file baseline

- captured_at: 2026-10-08
- command: `rg --files release-notes tests/contract web/tests/unit docs/program | rg '(^release-notes/|release.notes|RELEASE_PROCESS|/RELEASES\\.md$|W52-RELNOTES)' | sort`
- captured_output:
  ```text
  release-notes/0.2.0.json
  release-notes/0.3.0.json
  release-notes/schema.json
  ```
- interpretation: edit the two entries by increasing their authored
  revision; `schema.json` stays sealed. New checks and technical docs
  are within this lane's grant.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `release-notes/**` except `release-notes/schema.json`:
  `0.3.0.json`, `0.2.0.json`, `dictionary.json` and test fixtures
  below that directory only.
- `tests/contract/release_notes/**` — prose/form rules and deliberately
  bad fixtures that fail each rule by name.
- `web/tests/unit/release-notes/**` — live screen-registry membership
  and display-path checks for the entry equal to `VERSION` only.
- `docs/program/RELEASE_PROCESS.md`,
  `docs/program/RELEASES.md`,
  `docs/program/W52-RELNOTES-01.md`.
- Local `agent/w52-relnotes-01` branch/worktree and ignored
  environment.

## Forbidden hotspots

All other paths: `contracts/**`, migrations, root dependency/lock,
release backend/loader, generated client, screen registry implementation,
web UI, composition root, global styles, `origin/dev`,
`origin/main`, tags and deployment. A needed extra test path requires
an integrator grant correction before editing it.

## Non-goals

No API or loader change, new screen or contract operation, acceptance-pack
implementation, independent NOTES-JUDGE verdict, full gate, QA,
live acceptance, release row, tag or publication.

## Deliverables

- Authored revision-2 `0.3.0` and archive `0.2.0` entries with a
  claim-to-commit/test evidence ledger in the six-part hand-back.
- Dictionary and executable prose rules: unique canonical descending
  versions/dates; title 3–9 words without final period; 1–7 items ordered
  new → improved → fixed; text ≤ 400 characters; no straight quotes,
  code traces or bare dictionary words; current-only registry check.
- English `RELEASE_PROCESS.md` and `RELEASES.md` header with an empty
  table ready for a later measured release row.

## Required checks

- `.venv/bin/python -m pytest -q tests/contract/release_notes` and
  targeted loader/schema tests as the local environment permits.
- From `web/`: `npm exec -- vitest run tests/unit/release-notes`.
- Validate the two authored files against the sealed shape; prove every
  bad fixture fails its named rule, and that historical `screen` paths
  are not revalidated against today's registry.
- `git diff --check`, exact allowed-path audit, and report unrun checks.
  Full `make gate` remains D-140.

## Integration contract

The loader appends a revision above what it has stored; rewriting
revision 1 would refuse a prior local/deployed load. Keep both versions
and raise each changed entry's revision. The server continues to select
the highest revision and filter by `VERSION`. The NOTES-JUDGE later
checks every claim independently. Hand back a clean branch; merge
RELNOTES before ACCEPT.

## Failure / idempotency / security

Unknown top-level files or invalid shapes fail; prose rules run at gate,
not at deployment. A released file is never deleted or silently
reinterpreted. A correction is a higher authored revision. No secret
or raw model output is a release claim.

## Rollback / feature flag

Revert a dev-only candidate with a new reviewed commit. After a file
reaches `main`, preserve it and issue a higher revision for corrections;
the loader's rollback visibility rule handles older images. No runtime
feature flag is added.

## Handoff

Return changed files, checks/results, contracts, claim evidence, risks,
integrator steps and forbidden-hotspot proof. No checkpoint or tag.
