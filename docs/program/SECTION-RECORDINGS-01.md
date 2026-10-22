# SECTION-RECORDINGS-01 — every section profile is proven in recorded mode and refuses a foreign section

Task: `docs/program/tasks/SECTION-RECORDINGS-01.md`. Branch `agent/lane-b-01`; slice 3 of lane B, after
`PB-PROFILE-01` (tip `ba9f1a63`), which the ПБ case needs. Container-free (`R-126`): no stand, no database
suite, no model call.

## Result

Every section with a registered profile but AR now has one synthetic recording: the ten missing ones
(КЖ, КМ, ОВ, ВК, ПТ, ЭОМ, СС, ИТП, ГП and ПБ) were built by `fixtures/recorded/sections/build_fixtures.py`,
never by hand, and the four that existed (АИ, ПЗ, ПОС, ТХ) came out of the same run **byte for byte as
before** (`git status` shows them unmodified). Each recording replays through the real stage under its own
profile and publishes exactly its authored observations, grounded in the corpus text; each section's
request is refused by every other section's directory, by the canonical AR directory and by an empty one;
a section's reply filed under another key is not replayed. All recordings are labelled synthetic.

**Synthetic, not evidence** (`D-183`). No model produced these replies; usage and latency are authored
and differ per section on purpose. The ПБ recording is for a draft profile with no expert review: it
reports the three defects seeded in the AR corpus in fire-safety vocabulary and says nothing about how the
profile behaves on a real fire-safety volume.

## What changed

| File | Change |
| --- | --- |
| `fixtures/recorded/sections/build_fixtures.py` | ten new `SECTIONS` entries; `origin.task_id` and the statement now come from `task_of(code)`: the first four keep `W59-ANALYSIS-SETTINGS-01` (their files are unchanged), the ten new ones say `SECTION-RECORDINGS-01` |
| `fixtures/recorded/sections/{kj,km,ov,vk,pt,eom,ss,itp,gp,pb}/<request_sha256>.json` | ten new recordings |
| `fixtures/recorded/sections/README.md` | fourteen sections, the authoring task per file, a note that ПБ's is for a draft authored profile |
| `tests/integration/sections/test_section_recordings.py` | covers all fourteen; foreign-section refusal for every section; stage-level replay and refusal; builder plan test; source-block test fixed for an authored package |

No `src/**` change: `RecordedAdapter()` finds a new directory by itself (`default_recording_dirs` lists
every directory below `fixtures/recorded/sections/`).

## The recordings

Each answers the request of its section's profile over `fixtures/recorded/text_analysis/inputs/ar_baseline_text_layer.json`.
The text carries three seeded defects (fire-resistance degree II on page 2 and III on page 6; two exits on
page 3 and three on page 7; an unfilled window type on page 8), and the replies report combinations of them,
so every quote is an exact quotation of the page it names.

| Section | Key (`request_sha256`) | Observations | Tokens in / out | Latency ms |
| --- | --- | --- | --- | --- |
| КЖ `KJ` | `7208e6f7…4938` | fire resistance | 2370 / 430 | 9300 |
| КМ `KM` | `bf6a3d2c…7cfd` | exits | 2380 / 440 | 9500 |
| ОВ `OV` | `12c35374…d9ef` | placeholder, exits | 2390 / 720 | 10800 |
| ВК `VK` | `de50151c…378a` | placeholder | 2400 / 410 | 8900 |
| ПТ `PT` | `2fa06c39…0f28` | fire resistance, placeholder | 2410 / 740 | 11000 |
| ЭОМ `EOM` | `71e5232e…4be1` | exits | 2420 / 450 | 9200 |
| СС `SS` | `9ed13e71…0bd5` | placeholder | 2430 / 400 | 8800 |
| ИТП `ITP` | `cc1fab23…f57d` | fire resistance | 2440 / 460 | 9900 |
| ГП `GP` | `d6e10617…466e` | exits, fire resistance | 2450 / 790 | 11500 |
| ПБ `PB` | `153d0c01…6ad0` | fire resistance, exits, placeholder | 2460 / 980 | 12600 |

A recording is keyed by the digest of the exact request body, which includes the section's prompt: **editing
a profile's `system_prompt.md` orphans its recording.** `ПБ`'s is keyed to the prompt of `PB-PROFILE-01`'s
tip; if that prompt changes before the merge, run the builder again.

## Decisions taken

1. **Task identity per file.** The four existing files must not change (rebuilding them is part of
   `--check`), so they keep `W59-ANALYSIS-SETTINGS-01` in `origin.task_id` and the statement; the new ten
   say `SECTION-RECORDINGS-01`. The builder derives both from one function, so a section cannot get the
   wrong one without `--check` going red, and the test pins the mapping.
2. **The "section with no recording" seam.** The old test used КЖ for it. Every section has a recording now,
   so that case is an empty directory (`recording_missing`), per section, plus the stronger cases: another
   section's directory, the canonical directory, and a forged file name. A new test fails when a profile is
   registered without a recording or a recording directory exists without a profile.
3. **The builder's own plan is tested.** `--check` examines only what the builder plans: dropping a section
   from the builder left its recording behind unnoticed (the first mutation of that kind survived). A test
   now holds `plan()` to exactly the fourteen sections.
4. **Reply content.** Only the three defects the AR corpus really contains are used, in different
   combinations and wording, with per-section figures; no invented quotation. A fire-safety reply for a
   fire-safety section is a plausible reading of an AR text, not a claim.
5. **`tests/integration/runs/test_w59_section_profile_recorded.py` was not extended** to run all fourteen
   sections through the database (its `RECORDED_SECTIONS` still lists four): it is outside this task's
   allowed paths, and the container-free stage replay here covers the same routing and parsing. Extending it
   is a one-line change for whoever owns that file next.

## Commands and exit statuses

From `/root/projects/PDF-Analysis/.local/worktrees/lane-b`, shared venv interpreter, `nice -n 10`. Pytest
as before (`-c pyproject.toml --rootdir=. -q -p no:cacheprovider`, status from `$?`, import origin printed).

| Command | Result |
| --- | --- |
| `PYTHONPATH=src .venv/bin/python fixtures/recorded/sections/build_fixtures.py --check`, before the new entries (tip `ba9f1a63`) | rc 0, `fixtures match` |
| the builder, writing | rc 0; ten files `wrote` as new, the four existing ones rewritten identically (no diff) |
| `build_fixtures.py --check` after | rc 0, `fixtures match` |
| `tests/integration/sections/test_section_recordings.py` | before (`ba9f1a63`): rc 1, 16 passed, 1 failed (the source-block test, red since `PB-PROFILE-01`); after: rc 0, 109 passed |
| slice 1–3 container-free files together (`test_section_recordings`, `test_routing`, `test_staged_routing`, `tests/unit/analysis`, `test_model_identity`, `test_proxy_adapter`, `test_w53c_proxy_answer_shapes`, `test_provider_modes`, `test_proxy_truncation_reaches_partial`) | rc 0, 370 passed |
| `git diff --check` | rc 0 |

### `--check` under a changed profile text and a changed request

Each probe edits a file, runs the builder's `--check`, restores the file and proves the restore by a byte
comparison:

| Mutation | `--check` |
| --- | --- |
| `profiles/pb/system_prompt.md`: «Ты — инструмент проверки» → «Ты - инструмент проверки» | rc 1: the new PB key differs, the old file is `(stale)` |
| `profiles/kj/system_prompt.md`, same edit | rc 1: new KJ key, old `(stale)` |
| `adapter.py`: `"max_tokens": bundle.max_output_tokens + 1` (a changed request) | rc 1: every recording's key differs (AI, PS, … listed) |

## Mutation probes (the test file)

In place for data, builder and profiles (the tests read them through the repository root, so a `src` copy
would not reach them; each restore proved by byte comparison, `restored=True` every time). Copy
(`.local/mut-b1/src`, `-o pythonpath=<copy>/src`) for `recorded.py` and `adapter.py`; the plugin line
proved the copy was imported. The unmutated copy has one failure, `test_the_served_adapter_answers_ar_exactly_as_the_canonical_directory`,
an artefact of the copy (it resolves `fixtures/` through its own location); the copy results below
include it.

| Guard | Mutation | Result |
| --- | --- | --- |
| a section needs its recording | the ПБ recording deleted | 7 failed |
| same | the КЖ recording deleted | 7 failed |
| a profile edit orphans its recording | ПБ prompt changed | 7 failed |
| same | КЖ prompt changed | 7 failed |
| the builder covers every section | the builder skips ПБ | **survived** (0 failed) before `test_the_builder_plans_exactly_the_recorded_sections`; 1 failed after |
| same | an entry renamed (`KJ_`) | 2 failed |
| task identity | the first four given the new task | 2 failed |
| request is the sealed one | builder `MODEL_ID` changed | 1 failed |
| labelled synthetic | ПБ statement says a model produced it | 2 failed |
| no provider mode | `provider_mode` added to ПБ's `origin` | 2 failed |
| task id per file | КЖ says the old task | 2 failed |
| section code per file | ПБ says `GP` | 2 failed |
| distinguishable replies | КЖ's usage and latency equal АИ's | 2 failed |
| foreign key refused | `recorded.py`: the `request_sha256` check removed | 16 failed (the forged-key case for every section plus the copy artefact) |
| lookup is by key | `recorded.py`: first file in a directory instead of the key's file | 58 failed |
| request is the sealed one | `adapter.py`: `max_tokens + 1` | 74 failed |

## Not exercised

- No database suite: `tests/integration/runs/test_w59_section_profile_recorded.py` was not touched and not
  run; the integrator's gate runs it.
- No `tests/contract` battery (once, at the end of slice 4).
- No model call, no live mode, no `infra/**` (the `Dockerfile.api` comment of `D-183` is left to an infra slice).
- `recording_model_mismatch` (the model id in a recording) is not guarded by this file; it is held by
  `tests/integration/analysis_text/test_provider_modes.py`.

## Risks

- A recording is orphaned by any edit to its profile's prompt, the prompt module or the request builder.
  `--check` and the test file say so loudly; the fix is one builder run.
- ПБ is the only recording for an authored, unreviewed profile; its presence makes a recorded ПБ run end
  `published` with three synthetic findings, which proves routing and parsing, never quality.

## Instruction for the integrator

Merge after `PB-PROFILE-01` (the ПБ recording is keyed to its prompt). Register: the `D-183` row stays open
(synthetic, not evidence). Optional follow-up: extend `RECORDED_SECTIONS` in
`tests/integration/runs/test_w59_section_profile_recorded.py` from four to fourteen sections on a stand.
