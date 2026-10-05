# Task W48-SAFE-01 — preserve every unpublished W48 line and open the closure branch

## Outcome

All fifteen `agent/w48-*` branches have immutable backup refs plus one verified bundle, the
closure line starts from `411c6d0`, and the accepted identity programme is merged before any
repair starts.

## Depends on

- none

## Frozen inputs

- domain contract: `1.0.0-draft.1`, candidate revision 8, 27 opaque identities
- API contract: 17 paths / 20 operations / 61 schemas at
  `f043eb6c3a5bbba3cb95fff59039fff42582c79ae0dc8ff2ba261e2cb4583585`
- analysis/comparison/event contract: unchanged W48 frozen set
- migration head: `0014_durable_analysis_effects` on the preserved furthest tip
- base commit: `411c6d0a4fcc44a2b522dbb11f7ed726ef87fe12`
- plan commit: `b0e112d2cd3b8cc2d4c79dccf4f257967ce256b4`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: fifteen W48 branches exist and the furthest durable tip is 46 commits after the audit

### P-01 — branch inventory

- captured_at: 2026-10-05
- command: `git for-each-ref --format='%(refname:short) %(objectname)' 'refs/heads/agent/w48-*' | sort`
- captured_output:
  ```text
  agent/w48-durable 00100e8129ab0d144d66f7bac4899c069879b3cb
  agent/w48-durable-judge b43185071af3b315df208245089e27f56fd91f64
  agent/w48-durable-repair 411c6d0a4fcc44a2b522dbb11f7ed726ef87fe12
  agent/w48-fix fad3c28748ef52bc9b5f711191ff0130483e0055
  agent/w48-fix-b c05b3edbf2c4bd56ea8b647fe2b766785b642127
  agent/w48-gov 1843db5cfb948472d9e1d1ee6ff0eb9aaac1b07a
  agent/w48-guards e329f8a29ebe78c3557d6bc63c130798cb9e2a0f
  agent/w48-judge-a d5655ec3773ddb75ae57eb820e33d730c413a989
  agent/w48-judge-x 349e824d18e3a3e82da9f3f4cdf0054ce0dfd8c6
  agent/w48-judge-y 9a3126454bf49cdcf3f6d069de10845bad0124f4
  agent/w48-live 300567afefcffff89fbba02ddc7a7000c2e04622
  agent/w48-ports 81b1f2a2e588fb89a291b9b60417975997fddf02
  agent/w48-prose 4cf424d0636eb4cccbae64d7ce030e589813fa19
  agent/w48-stage-a 03c04a1d87fda862d085a6a49d0a46f2692f7ffd
  agent/w48-web 996b5463b2510ea686457b2cb7fe768665ab8315
  ```
- interpretation: this is the complete ref inventory at backup time; it does not claim that
  every patch is accepted.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `refs/backup/w48-2026-10-05/**`
- `.local/backup/w48-2026-10-05.bundle`
- `docs/program/tasks/W48-*.md` named by `W48-CLOSE.md` section 4
- `docs/program/W48-SAFE-01.md`
- `docs/program/dispatch/PORT_REGISTRY.md`
- branch/worktree bookkeeping for `integration/w48-close`

## Forbidden hotspots

- contracts, migrations, runtime, frontend, root locks, composition and global styles
- `origin/dev`, `origin/main`, tags and deployment
- credentials and host-owned environment files

## Non-goals

- no repair, merge of implementation lanes, test gate or publication

## Deliverables

- fifteen matching backup refs, verified bundle, branch inventory, closure worktree, lane rows,
  task files and this report

## Required tests

- `git bundle verify .local/backup/w48-2026-10-05.bundle` prints that the bundle is okay
- every backup ref equals the corresponding branch tip
- `git diff --check`

## Integration contract

The closure branch contains `411c6d0` and the complete `plan/identity-waves` history. Any later
loss of an old worktree remains recoverable from both a ref and the bundle.

## Failure/idempotency/security cases

- a mismatched ref, incomplete bundle, running gate, moved remote or merge conflict stops work
- rerunning backup verification is read-only; no secret is stored in the bundle report

## Rollback / feature flag

Documentation and additive backup refs only. The bundle is retained through `alpha-w48` or an
owner instruction; no runtime feature flag applies.

## Handoff

- changed files: report, task files and port registry only
- commands/results: recorded in `docs/program/W48-SAFE-01.md`
- known limits: the detached freeze worktree retains ignored `.venv` and `web/node_modules`
- integration notes: run `W48-RULE-01` next; do not publish any ref
