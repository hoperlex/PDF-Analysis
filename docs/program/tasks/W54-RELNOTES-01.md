# Task W54-RELNOTES-01 — Release notes 0.5.0 describe W54's user-visible changes and VERSION moves to 0.5.0

## Outcome
Release notes 0.5.0 describe W54's user-visible changes and VERSION moves to 0.5.0.

## Depends on
- `W54-FREEZE-01` and the Stage B merges on `integration/w54`

## Frozen inputs
- domain contract: after `W54-SEAL-01`
- API contract: after `W54-SEAL-01`
- analysis/comparison/event contract: unchanged
- migration head: `0019_execution_workers`
- base commit: the EMBED merge on `integration/w54`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: none

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- Exactly the `W54-RELNOTES-01` grant in `docs/program/dispatch/W54-PLAN.md` §4 Stage C (`release-notes/0.5.0.json`, `release-notes/dictionary.json` additions, `VERSION`, the paths `git grep -n '0\\.4\\.0' tests web/tests` prints), plus `docs/program/W54-RELNOTES-01.md`.

## Forbidden hotspots
- any path outside the grant; contracts and migrations; `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand, `.local/norms/corpus/**`

## Non-goals
- Any code change.

## Deliverables
- `release-notes/0.5.0.json` in the form `tests/contract/release_notes/test_release_notes_form.py` enforces (3–9 word title, ≤ 7 items ordered new → improved → fixed, no straight quotes, no code traces or dictionary words, Russian, user-visible only): «Исполнители» screen and intake control, runs executed by a separate worker service, more reliable recovery; nothing about the corpus (not visible to users yet). `VERSION` → `0.5.0`; update every test pin `git grep` prints so they read `VERSION` or the new history; the release-notes form, loader and acceptance-command tests green.

## Required tests
- command: container-free: `tests/contract/release_notes`, `tests/contract/test_alpha_acceptance_command.py`, the release web tests and guards; DB-backed loader tests are the integrator's window step.
- expected: exit 0; each new behaviour has a test that fails without the change.

## Integration contract
The integrator merges after reading the diff and the report.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; never touch the stand, published refs or other worktrees; no container before the window.
