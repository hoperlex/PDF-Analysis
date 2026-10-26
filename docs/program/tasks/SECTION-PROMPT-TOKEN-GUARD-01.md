# Task SECTION-PROMPT-TOKEN-GUARD-01 — a repository test reads every designation of the 14 section prompts against its pinned source

task_id: SECTION-PROMPT-TOKEN-GUARD-01
status: completed in development candidate

## Outcome

`D-224`: the sentences that the section lanes added to `system_prompt.md` are held by no test that reads them; only the sha256 of the prompt bytes inside the rebuilt recording pins them, and an edit with a consistent rebuild passes. One repository test now extracts, for each of the 14 section packages, every **whole token** of `system_prompt.md` that has a digit, a letter outside Cyrillic, two or more capital letters, or is a hyphenated code, and requires that token to be a whole token of (a) the union of the section's five hash-pinned legacy files, (b) the v1 prompt `src/auditmanager/analysis/text/prompt.py`, or (c) the explicit allowlist `tests/unit/analysis/text_profiles/prompt_token_allowlist.json` (a reason and the disclosing report per entry; `class: "a"` and a justification for anything that could be a class designation, a cable marking or a norm number). No prompt, `profile.json` or recording changes. The tokens the audit finds that no source holds are listed, not edited away.

## Depends on

- `PROD-14-0-EXPECTATIONS-01`, `W59-SECTION-PROFILES-01`, `SECTION-RECORDINGS-01` — completed; they created the packages and the package tests.
- `SECTION-<CODE>-FULL-01` for all 14 sections and `SECTION-REVIEW-LEDGER-01` — completed; their audits of numerals and designations are the source of the seeded allowlist entries.
- `PRODUCTION-WAVE-PW3` (lane G; the common rules are section 2 of `PRODUCTION-WAVE-PW2B`).

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.6.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable
- migration head: `0033_ar_v3_cite_stage_id`, unchanged
- base commit: `2aec42072c7ba81be59570206e99e29bfd9e041c` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No package, route, error code or migration is added. The test discovers the packages by listing `profiles/` and asserts that it found exactly the 14 section codes, so a package added later must be added to the guard's expected set on purpose.

## Captured premise evidence

- premise: the 14 packages, the 13 five-file source pins and PB's absent source are as the brief says; the legacy repository is on this host at the pinned commit; no guard that reads the prompts against the sources exists; the audit run on the base with an empty allowlist leaves exactly the tokens the brief lists plus one more

### P-01 — 14 packages, 13 with five pinned files, PB with none, the commit is in the legacy repository

- captured_at: 2026-10-26
- command: `ls -d src/auditmanager/analysis/text/profiles/*/ | wc -l; grep -c '"sha256"' src/auditmanager/analysis/text/profiles/*/profile.json; git -C /root/projects/PDF-proverka cat-file -t 16ba8e5d23e4782550e79355002fde1365f682b7`
- captured_output:
  ```text
  14
  gp/profile.json:5
  ps/profile.json:5
  ai/profile.json:5
  eom/profile.json:5
  itp/profile.json:5
  kj/profile.json:5
  km/profile.json:5
  ov/profile.json:5
  pt/profile.json:5
  pos/profile.json:5
  pb/profile.json:0
  tx/profile.json:5
  vk/profile.json:5
  ss/profile.json:5
  commit
  ```
- interpretation: 14 packages; 13 pin five legacy files by sha256; PB pins none (`"source": null`), so its guard has no source part and always runs. The pinned commit `16ba8e5d…` is the legacy repository's `HEAD` and its working tree is clean (`git status --short` printed nothing); the lane only runs `git show` on it.

### P-02 — no guard that reads the prompts against the sources exists

- captured_at: 2026-10-26
- command: `rg -n 'prompt.*pinned source|numerals' tests/unit/analysis/text_profiles | head`
- captured_output:
  ```text
  tests/unit/analysis/text_profiles/test_text_profile_packages.py:336:    """No clause, limit or class threshold: the only numerals are the two norm identifiers."""
  ```
- interpretation: the only hit is the PB test that pins `123` and `13130` as PB's only numerals; no test compares a prompt with a pinned source. `DEBT_REGISTER.md` `D-224` says the same.

### P-03 — the baseline of the existing package tests

- captured_at: 2026-10-26
- command: `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/text_profiles`
- captured_output:
  ```text
  .................                                                        [100%]
  17 passed in 0.79s
  ```
- interpretation: green on the base before any edit. These 17 tests are not edited by this task.

### P-04 — the first run of the whole-token audit with an empty allowlist

- captured_at: 2026-10-26
- command: `python3 -I -c "import sys;sys.path[:0]=['src','tests/unit/analysis/text_profiles'];import test_prompt_token_guard as g;[print(c,g.unexplained(d['prompt'],v1=g.V1,source=(g.source_universe(c) if d['manifest']['source'] else frozenset()),allowed=frozenset())) for c,d in g.SECTIONS.items()]"`
- captured_output:
  ```text
  AI ['КМ']
  EOM ['PE-проводника']
  GP ['0,000']
  ITP []
  KJ []
  KM []
  OV []
  PB ['123-ФЗ', '13130', 'ПБ']
  POS ['ИТР']
  PS ['ГПЗУ']
  PT []
  SS []
  TX []
  VK []
  ```
- interpretation: 8 tokens in 6 sections are in none of the five pinned files, v1's prompt or (PB) any source. The audit found the tokens the brief names (`КМ` in AI, `PE-проводника`, `0,000`, `123-ФЗ`, `13130`, `ИТР`, `ГПЗУ`) and one more, `ПБ`. Seven of the eight are named in a lane report as absent from the source or as vocabulary the source lacks; `КМ` is reported there as sourced (a substring match) and `ПБ` is covered by the PB report only through its audit statement (every capital-letter token is in v1 or the record). The other 517 of the 525 designation tokens (summed per section) are covered by a pinned source or by v1.

### P-05 — `КМ` is a substring of the AI source, never a whole token

- captured_at: 2026-10-26
- command: `for f in role checklist drawing_types project_params finding_categories; do git -C /root/projects/PDF-proverka show 16ba8e5d23e4782550e79355002fde1365f682b7:prompts/disciplines/AI/$f.md; done | grep -o -E "КМ[0-9]*" | sort | uniq -c`
- captured_output:
  ```text
        2 КМ0
        1 КМ1
        2 КМ2
        2 КМ5
  ```
- interpretation: the five AI files contain `КМ` only as the prefix of `КМ0`, `КМ1`, `КМ2` and `КМ5`; an audit that matched substrings reports it as sourced (the AI report says so), a whole-token audit does not. This is the failure the brief names.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

The section reports and the ledger are read, not rewritten. The AI report's statement that `КМ` is in the source is wrong by the whole-token rule; the allowlist entry says so and this task does not edit that report.

## Publication authority

- development_target: none
- origin_main_authority: none

The lane commits on `agent/section-prompt-token-guard-01` only; the integrator merges and publishes.

## Allowed paths

- `tests/unit/analysis/text_profiles/test_prompt_token_guard.py`
- `tests/unit/analysis/text_profiles/prompt_token_allowlist.json`
- `docs/program/tasks/SECTION-PROMPT-TOKEN-GUARD-01.md`
- `docs/program/SECTION-PROMPT-TOKEN-GUARD-01.md`

## Forbidden hotspots

- every `system_prompt.md`, every `profile.json`, `open_questions.md`, the recordings under `fixtures/recorded/sections/**`
- `src/**`, `contracts/**`, the migration head, root dependency/lock files, the composition root
- `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs, the section reports and the ledger
- `/root/projects/PDF-proverka` (read only)

## Non-goals

- editing a prompt to remove a token the audit finds (a token that is neither sourced nor disclosed is a finding for the integrator)
- checking words that are not designations (the vocabulary the reports list as «not from the source» stays an expert's call)
- checking that a sourced designation means the same thing in the prompt as in the source
- a copy of the legacy text in the repository: on a host without the legacy repository the sourced part skips with a reason

## Deliverables

- `tests/unit/analysis/text_profiles/test_prompt_token_guard.py` (109 tests: 46 that always run, 63 that need the legacy repository)
- `tests/unit/analysis/text_profiles/prompt_token_allowlist.json` (8 entries, seeded from what the audit found)
- `docs/program/SECTION-PROMPT-TOKEN-GUARD-01.md` (the mutation table, the decisions, the findings, the limits)

## Required tests

- command: `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/text_profiles`
- expected: 126 passed (the 17 existing and the 109 new); with `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent`, 46 of the new ones pass and 63 skip, each with the reason string `legacy repository … is not on this host …`
- command: `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/contract/analysis_packages tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`
- expected: green (the integrator re-runs it)

## Integration contract

The integrator can rely on: (1) a prompt edit that adds a digit-bearing token, a Latin-letter token, an abbreviation or a hyphenated code that no pinned source, v1 or the allowlist holds turns `test_every_designation_is_in_the_pinned_source_in_v1_or_the_allowlist[<CODE>]` red on a host with the legacy repository, and for PB on every host; (2) the allowlist is the only place a new exception can go, and the hygiene tests (which always run) refuse an entry with no reason, no existing disclosing report that contains the token, a token no longer in its prompt, a token v1 or the source already holds, a duplicate, or a digit/Latin/hyphen-code token without `class: "a"` and a justification; (3) the guard reads `tests/unit/analysis/text_profiles/**` and `docs/program/SECTION-*-FULL-01.md` only (the report check), writes nothing and runs no subprocess other than `git show` and `git cat-file` against the legacy repository.

## Failure/idempotency/security cases

- legacy repository absent or the pinned commit missing: the sourced part skips with a reason string; the always-running part still guards PB and the allowlist
- legacy blob present but its sha256 differs from `profile.json`: the test fails (the source must be the pinned one), it does not skip
- a zero-width or other format character in a prompt (it would split a token unseen): a hygiene test fails
- a homoglyph (Latin `E1` for Cyrillic `Е1`) or a changed case: not sourced, red
- the legacy repository is only read; no write, no network

## Rollback / feature flag

Not applicable: a test and a data file; reverting the commits removes the guard.

## Handoff

- changed files: the four paths above
- commands/results: see the report (`docs/program/SECTION-PROMPT-TOKEN-GUARD-01.md`)
- known limits: the report's «Limits»
- integration notes: the report's «Integration notes»
