# W54-RELNOTES-01 — hand-back report

- Task: `docs/program/tasks/W54-RELNOTES-01.md`; grant: `dispatch/W54-PLAN.md` §4 Stage C
  `W54-RELNOTES-01`; history rule `R-86` (`OWNER_RULINGS_2026-09-17.md` §3.29).
- Branch `agent/w54-relnotes-01`, worktree `.local/worktrees/w54-relnotes`, base `f1c24b8`
  (`integration/w54`). Implementation commit `e9de3a6`; this report is the last commit.
- Light acceptance, container-free. No container, server or browser was started.

## 0. The 0.5.0 notes

`release-notes/0.5.0.json`, revision 1, date `2026-10-13`. Title: «Исполнители и отдельная служба
выполнения прогонов». Seven items, all user-visible, nothing about the normative corpus:

| Kind | Screen | Says |
|---|---|---|
| new | `/workers` | the «Исполнители» section: state, slots, version, start, last heartbeat, current runs; offline ones collapsed |
| new | `/workers` | administrators switch a worker's intake off and on after a confirmation; started runs finish |
| new | `/queue` | the queue and the run page name the worker holding the run, linked to «Исполнители» |
| improved | `/` | runs are executed by a separate worker service; a queued job is taken within seconds |
| improved | `/queue` | on a planned restart the worker stops taking jobs and gives started runs up to 4.5 min (270 s drain) |
| improved | `/queue` | runs of a silent worker return to the queue and are taken by a worker on line; paid calls are not repeated |
| fixed | `/` | a long final check no longer loses the model's answer (D-141) |

Sources: `W54-WORKERS-WEB.md` §0, `W54-WORKER-01.md` §0 and limitation 4, `DEBT_REGISTER.md`
D-141. D-150 is left out: per the register it affects only recorded replay and tests.

## 1. Changed files (`git diff --name-only f1c24b8..HEAD`)

```
VERSION
docs/program/W54-RELNOTES-01.md
release-notes/0.5.0.json
tests/contract/release_notes/test_release_notes_form.py
tests/integration/releases/test_release_loader.py
```

- `VERSION`: `0.4.0` → `0.5.0`.
- `test_release_notes_form.py`: the revision map gains `"0.5.0": 1`; the order list is
  `["0.5.0", "0.4.0", "0.3.0", "0.2.0"]`.
- `test_release_loader.py`: `set(_notes())` gains `0.5.0`. The two-release filter in
  `test_loader_is_idempotent_and_serves_the_highest_revision` stays as it was; only its comment
  now names 0.5.0. **A latent defect, fixed:** five DB-backed tests
  (`test_conflicts_and_missing_history_roll_back_the_whole_load`,
  `test_future_database_release_survives_rollback_and_is_hidden`,
  `test_account_mark_only_rises_and_new_accounts_see_no_old_whats_new`,
  `test_a_newer_images_revision_falls_back_to_the_newest_servable_one` (three parameters) and
  `test_a_release_with_no_servable_revision_is_omitted_not_fatal`) passed the full authored tree to `load_notes(..., product_version="0.3.0")`. The loader
  refuses that before it opens a session: "VERSION must equal the highest non-archive release
  note". So these tests have been red since `ed66983` (0.4.0), and nothing caught it because the
  DB-backed tests did not run under `R-87`. They now load the history through a new helper,
  `_history()`, which applies the same `{0.2.0, 0.3.0}` filter.
- Not changed: `release-notes/dictionary.json` (no new term needed).
- Also not changed: `web/tests/guards/rendered-language.guard.test.ts:715` and
  `web/tests/unit/styles/screens.ts:499`. `git grep` prints them, but they are not release pins.
  They are the `version` of the *offline* worker fixture, an older build next to two `0.5.0`
  workers, and nothing ties them to `VERSION`.

## 2. Checks (on the committed tree, `git status --porcelain -uall` empty)

| Command | Result |
|---|---|
| `git diff --check` | clean |
| `.venv/bin/python -m pytest -q tests/contract/release_notes tests/contract/test_alpha_acceptance_command.py` | 48 passed |
| `.venv/bin/python -m pytest -q tests/integration/releases/test_release_loader.py::test_shape_schema_matches_the_served_item_and_kind ...::test_unknown_or_invalid_entry_refuses_before_database` (no database needed) | 4 passed |
| `read_notes(Path('release-notes'))` with the real loader | `['0.2.0', '0.3.0', '0.4.0', '0.5.0']` |
| `load_notes(None, notes=<full tree>, product_version='0.3.0')` | `ValueError: VERSION must equal the highest non-archive release note`, which is the defect above. With the `_history()` filter it passes that check and reaches the session (`AttributeError` on `None.begin`). |
| `cd web && npx vitest run tests/unit/release tests/guards/rendered-language.guard.test.ts tests/unit/styles` | 10 files, 99 tests passed (includes `release-notes/current-screen.test.ts`) |

Can-fail: `test_bad_fixture_fails_named_rule[product_version]` drops the newest entry and
expects `product_version`. The revision-map and order assertions fail on any tree without
`0.5.0.json`.

## 3. Contracts

None new or changed. The notes follow `release-notes/schema.json` unchanged.

## 4. Risks and known limitations

- **The date is `2026-10-13`, not `2026-10-12`.** `descending_dates` is strict, and 0.4.0 already
  holds `2026-10-12`. If the release lands later, the integrator may move the date while the
  revision is still 1 and unloaded.
- The five repaired DB-backed loader tests have not run here. They belong in the integrator's
  window: `tests/integration/releases/test_release_loader.py` in full.
- The drain figure ("до четырёх с половиной минут") is the 270 s drain from `W54-WORKER-01`. If
  the drain changes, this item needs a revision.
- `W54-NOTES-JUDGE` judges the wording.

## 5. Integrator instructions

1. Read the diff and this report, then merge `agent/w54-relnotes-01` into `integration/w54`.
2. In the window, run `tests/integration/releases/test_release_loader.py` with a database.
3. The `v0.5.0` tag follows deployment under `R-86` / plan §8.4. This lane did not tag.

## 6. Containment

`git diff --name-only f1c24b8..HEAD` lists the five paths in §1. Each is inside the grant:
`release-notes/0.5.0.json`, `VERSION`, two paths `git grep -n '0\.4\.0' tests web/tests` prints,
and this report. Not touched: `contracts/**`, migrations, `DEBT_REGISTER.md`,
`OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand, `.local/norms/corpus/**`. No
push, merge, tag or stash, and no other worktree was touched. `git status --porcelain -uall` is
empty after this commit.
