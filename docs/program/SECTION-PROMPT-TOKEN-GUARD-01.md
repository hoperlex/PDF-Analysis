# SECTION-PROMPT-TOKEN-GUARD-01 — a repository test reads every designation of the 14 section prompts against its pinned source

Task: `docs/program/tasks/SECTION-PROMPT-TOKEN-GUARD-01.md`. Register row: `D-224`. Written 2026-10-26 on the branch `agent/section-prompt-token-guard-01`, base `2aec42072c7ba81be59570206e99e29bfd9e041c`. A test and a data file: no prompt, `profile.json`, recording or `src/` file changes.

## What was built

`tests/unit/analysis/text_profiles/test_prompt_token_guard.py` (109 tests) and `tests/unit/analysis/text_profiles/prompt_token_allowlist.json` (8 entries). For each of the 14 packages the test extracts from `system_prompt.md` every **whole token** that is a designation and requires it to be a whole token of (a) the union of the section's five pinned legacy files (read with `git show <commit>:<path>` from `/root/projects/PDF-proverka`, each blob checked against the sha256 in `profile.json`), (b) the v1 prompt, or (c) the allowlist.

**Whole token.** A token is a maximal run of letters and digits; a decimal comma or point between two digits and a hyphen (hyphen-minus, U+2010, U+2011) between two words stay inside the token (`Е0,5`, `0,000`, `123-ФЗ`, `PE-проводника`); an en or em dash, a slash, a parenthesis and an underscore separate tokens (`Г1–Г4` is `Г1` and `Г4`, `(FRLS/FR)` is `FRLS` and `FR`). Text is NFC-normalised first. Matching is exact: case, script and every character count, so `LS` is not sourced by `FRLS`, `КМ` is not sourced by `КМ0`, `EX` is not `Ex`, and a Latin `E1` is not a Cyrillic `Е1`.

**Designation.** A token with a digit (`digit`); with any letter outside Cyrillic (`latin`); with two or more capital letters in any case mix (`abbreviation`: `ИТР`, `ГПЗУ`, and also `СНиП`, `СанПиН`); or hyphen-joined with a part that is not an ordinary word, such as a bare capital letter (`hyphen-code`: `Т-образный`). Ordinary words and ordinary hyphen compounds (`тамбур-шлюзов`) are not designations.

**Two parts.** The part that needs the legacy repository (63 tests) skips with an explicit reason string (`legacy repository … is not on this host (set AUDITMANAGER_LEGACY_PROMPTS_REPO); the sourced-token check is skipped, allowlist hygiene and PB still run`) when the repository or the pinned commit is absent; a blob whose sha256 differs from `profile.json` fails, it does not skip. The part that always runs (46 tests) holds the tokenizer and the class rules, the matching rules on synthetic text, the allowlist hygiene, the invisible-character test, and **PB's whole audit** (PB has no legacy source: its tokens are checked against v1 and the allowlist), including in-memory mutations of PB's prompt and allowlist.

## Files

| File | New / modified |
| --- | --- |
| `tests/unit/analysis/text_profiles/test_prompt_token_guard.py` | new |
| `tests/unit/analysis/text_profiles/prompt_token_allowlist.json` | new |
| `docs/program/tasks/SECTION-PROMPT-TOKEN-GUARD-01.md` | new |
| `docs/program/SECTION-PROMPT-TOKEN-GUARD-01.md` | new |

## The audit as run on the tree (what the guard found)

Run on the base tree, empty allowlist (premise P-04 of the task file): eight tokens in six sections were in none of the sources.

| Section | Designation tokens | In the pinned source | In v1 only | In the allowlist only |
| --- | --- | --- | --- | --- |
| AI | 36 | 6 | 29 | 1 |
| PS | 40 | 11 | 28 | 1 |
| POS | 34 | 5 | 28 | 1 |
| TX | 35 | 7 | 28 | 0 |
| KJ | 35 | 8 | 27 | 0 |
| KM | 36 | 8 | 28 | 0 |
| OV | 38 | 9 | 29 | 0 |
| VK | 39 | 13 | 26 | 0 |
| PT | 33 | 9 | 24 | 0 |
| EOM | 43 | 14 | 28 | 1 |
| SS | 44 | 19 | 25 | 0 |
| ITP | 36 | 9 | 27 | 0 |
| GP | 41 | 16 | 24 | 1 |
| PB | 35 | 0 | 32 | 3 |
| **Total** | **525** | **134** | **383** | **8** |

The eight allowlist entries, each found by running the audit (none added from memory), with the report that disclosed it:

| Section | Token | Class | Disclosed by | What the report says |
| --- | --- | --- | --- | --- |
| AI | `КМ` | a | `SECTION-AI-FULL-01.md` | listed as «in the source»; wrong by the whole-token rule: the files hold `КМ0`, `КМ1`, `КМ2`, `КМ5`, never `КМ` (premise P-05) |
| EOM | `PE-проводника` | a | `SECTION-EOM-FULL-01.md` | «PE-проводника» (the source says «PE-шины») among the vocabulary not from the source |
| GP | `0,000` | a | `SECTION-GP-FULL-01.md` | the one token not in the source, kept and disclosed; the earlier audit split it at the comma and saw `000` |
| PB | `123-ФЗ` | a | `SECTION-PB-FULL-01.md` | the record's, no pinned source (assumption 7) |
| PB | `13130` | a | `SECTION-PB-FULL-01.md` | the same |
| PB | `ПБ` | none | `SECTION-PB-FULL-01.md` | covered only by the report's audit statement (every capital-letter token is in v1 or the PB record, where `ПБ` heads `open_questions.md`); the report does not name the token |
| POS | `ИТР` | none | `SECTION-POS-FULL-01.md` | assumption 5: a term of the earlier drafting not in the source |
| PS | `ГПЗУ` | none | `SECTION-PS-FULL-01.md` | assumption 5: vocabulary already in the draft prompt that the source lacks |

### Tokens neither sourced nor disclosed

The full list the audit found that is **neither sourced nor disclosed by name**: **none**. Two of the eight are weaker than the rest and the integrator may want to decide them:

- `ПБ` (PB): not in v1, no pinned source, and not named by the PB report; accepted into the allowlist because the report's audit statement covers every capital-letter token against v1 and the record, and `ПБ` is in the record. It is the section's own abbreviation (the opening sentence and the hint heading).
- `КМ` (AI): the AI report states it is sourced; the whole-token audit shows it is not. The allowlist reason says so. If the integrator prefers the prompt to carry no unsourced designation, the fix is a prompt edit (outside this lane): `КМ` stands in the class bullet «класс пожарной опасности (КМ)» and in condition 2.

No prompt was edited. `0,000` and PB's `123-ФЗ` and `13130` are numerals, and the section template forbids a normative number that is not in the section's source; the GP report argues that `0,000` is the conventional zero mark and states no value to compare, and the PB report argues that its two identifiers stand only in the sentence that tells the model what not to check. Those are the lane reports' decisions; this guard makes them visible and pins them, and `class: "a"` plus a justification is what each now carries.

## Decisions taken by the lane (the owner asked for no questions)

Each is **decided by the lane**.

1. **Abbreviations include mixed case.** The brief names «all-capital Cyrillic abbreviation of two or more letters», and the problem statement names «mixed-case symbols». The rule is two or more capital letters in any case mix, so `СНиП` and `СанПиН` are checked (both are in v1 or the source). A one-letter capital (`И`) is not a designation.
2. **`latin` is any letter outside Cyrillic.** Greek or other lookalike letters cannot hide as «not Latin».
3. **A hyphen-joined token is one token on both sides; there is no «part» rule.** A first draft let `LS` match a part of the source's `нг-LS`; no prompt token needed it, and the looser rule can only hide an invention, so it was removed. A hyphenated prompt token must be whole in the source (`PE-проводника` is not, although `PE` and `PE-шины` are).
4. **`class: "a"` means** «could be a class designation, a cable marking or a norm number, accepted knowingly». The hygiene tests require it, with a justification of at least 40 characters, for every allowlist entry whose token is of class `digit`, `latin` or `hyphen-code`, and accept it on any other. Voluntarily set on `КМ` (it names the fire-hazard class family). Plain abbreviations (`ИТР`, `ГПЗУ`, `ПБ`) need only a reason.
5. **`disclosed_by` is checked**: it must be a `SECTION-<CODE>-FULL-01.md` file under `docs/program` that exists and contains the token, so an entry cannot name a report that never mentions it.
6. **GP's entry is `0,000`**, the whole token, not `000`; the brief's `000` came from a script that split at the comma.
7. **Staleness is a failure.** An entry whose token is no longer in its prompt, is in v1, or is now a whole token of the pinned source (the last needs the legacy repository) fails: the allowlist cannot accumulate cover for nothing.
8. **Invisible characters.** A zero-width or other format character, or a non-ASCII space, in a prompt fails a hygiene test: such a character would split a token unseen.
9. **PB** is audited against v1 and the allowlist only and always runs, since it has no source to wait for.
10. **Edge case left as is:** v1's prompt is part of every section's cover, so v1's own numerals `1`–`5`, `TBD`, `XX`, `ГОСТ`, `СП`, `СНиП` and its upper-case emphasis words pass everywhere. 383 of the 525 designations are covered by v1 alone; they are the text that `test_every_system_prompt_keeps_the_v1_question_categories_and_output_contract` already pins byte for byte.

## Mutation table

Each row was applied to the committed tree, the guard (`test_prompt_token_guard.py`) was run, and the change was reverted with `git checkout` (final run: 109 passed). «Red» lists the tests that failed; counts are the tests of the file. Baseline: 109 passed. The harness is outside the repository.

| # | Mutation | Result | Red tests (shortened) |
| --- | --- | --- | --- |
| M1 | class designation «(класс Г9)» appended to the SS prompt | 3 failed | `every_designation_is_in_the_pinned_source_in_v1_or_the_allowlist[SS]`, `inserting_an_invented_designation_turns_the_audit_red` |
| M2 | cable marking «ПвБШнг(А)-FRHFX» appended to the EOM prompt | 4 failed | the same two, `removing_an_allowlist_entry_turns_the_audit_red` |
| M3 | norm number «СП 999.1325800.2099» appended to the PB prompt (no legacy source) | 6 failed | `pb_designations_are_all_in_v1_or_the_allowlist`, the PB insertion and removal tests (**no legacy repository needed**) |
| M3b | the same in the GP prompt | 4 failed | `every_designation_…[GP]` and the insertion/removal tests |
| M4 | «LS» (a substring of the sourced `FRLS`) appended to the SS prompt | 4 failed | `every_designation_…[SS]` |
| M5 | Latin `E1` for the Cyrillic `Е1` in the AI prompt | 5 failed | `every_designation_…[AI]` |
| M6 | zero-width space inside `FRLS` in the SS prompt | 5 failed | `every_prompt_character_is_visible_so_a_token_cannot_be_split_unseen` and `every_designation_…[SS]` |
| M7 | each of the 8 allowlist entries removed in turn (GP `0,000`, AI `КМ`, PS `ГПЗУ`, PB `ПБ`, PB `13130`, PB `123-ФЗ`, EOM `PE-проводника`, POS `ИТР`) | 8 of 8 red | the section's `every_designation_…` (PB: `pb_designations_are_all_in_v1_or_the_allowlist`) |
| M8 | `class` and `justification` dropped from GP `0,000` | 1 failed | `a_designation_like_entry_carries_class_a_and_a_justification` |
| M9 | reason of POS `ИТР` emptied | 1 failed | `the_allowlist_has_the_documented_shape` |
| M10 | duplicate PS `ГПЗУ` entry added | 3 failed | `the_allowlist_has_the_documented_shape`, `removing_an_allowlist_entry_turns_the_audit_red` |
| M11 | redundant AI `ГОСТ` entry (v1 holds it) added | 2 failed | `every_entry_still_appears_in_its_prompt_and_is_not_covered_by_v1` |
| M12 | entry for a token absent from its prompt (POS `ИТРХ`) | 3 failed | `every_entry_still_appears_in_its_prompt_…`, `every_entry_names_a_report_that_contains_its_token` |
| M13 | `disclosed_by` of GP `0,000` points to `SECTION-KJ-FULL-01.md` | 1 failed | `every_entry_names_a_report_that_contains_its_token` |
| M14 | entry for a token the source already holds (OV `В1`) | 3 failed | `no_allowlist_entry_is_already_sourced`, `a_designation_like_entry_carries_class_a_…` |
| M15 | first hex digit of one pinned sha256 flipped in `kj/profile.json` | 4 failed | `every_designation_…[KJ]` (the blob no longer matches the pin) |
| M16 | the matcher turned into a **substring match** | 4 failed | `a_substring_of_a_sourced_token_is_not_sourced`, `matching_is_exact_in_case_script_and_characters`, `removing_an_allowlist_entry_turns_the_audit_red[AI-КМ]` |
| M17 | the matcher made case-insensitive | 1 failed | `matching_is_exact_in_case_script_and_characters` |
| M18 | the tokenizer stops joining on the hyphen-minus | 27 failed | the tokenizer, class, hyphen and allowlist tests |
| M19 | a decimal comma no longer joins digits | 10 failed | `the_tokenizer_returns_whole_tokens`, `every_designation_…`, the allowlist tests (`0,000`) |
| M20 | the abbreviation rule removed | 27 failed | `the_token_classes`, `the_guard_reads_exactly_the_fourteen_section_prompts` and others |
| M21 | `source_universe` returns an empty set (the sourced part made vacuous) | 58 failed | `every_designation_…` for 13 sections, `the_ai_km_case_…` |

M4 and M16 are the two the brief asks for beyond the insertions: a substring of a sourced token does not pass, and a matcher that would let it pass is caught by a test that names the case.

## Modified tests

None. The 17 existing tests under `tests/unit/analysis/text_profiles` are untouched (before: 17 passed; after: the same 17 pass beside the 109 new ones).

## Commands and counts

All with `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages)` and `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider`:

- `tests/unit/analysis/text_profiles/test_prompt_token_guard.py`: **109 passed** (about 1 s).
- `tests/unit/analysis/text_profiles` with `tests/unit/analysis/test_text_profile_registry.py`: **159 passed**.
- the same guard file with `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent`: **46 passed, 63 skipped**, every skip carrying the reason string above.
- DOCS_CHECKS_PLACEHOLDER

## Integration notes

- The merge adds two files under `tests/unit/analysis/text_profiles/` and the two documents. Nothing else moves; no section lane edits these files, so there is no conflict with the expectations file.
- A section lane that edits a prompt later must keep the guard green: sourced designations only, or an allowlist entry with a reason and the disclosing report (the integrator decides). The message of the failing test says so.
- `DEBT_REGISTER.md` `D-224` can be closed or narrowed by the integrator: its check command `rg -n 'prompt.*pinned source|numerals' tests/unit/analysis/text_profiles | head` now also finds `test_prompt_token_guard.py`. The lane did not edit the register.
- The two weaker entries (`ПБ`, `КМ` in AI) are listed above for a decision.

## Limits

- The guard checks that a designation **occurs** as a whole token in the source, not that it **means** the same thing there or stands in a comparable context: `ГОСТ` in a hint bullet and `ГОСТ` in v1's exclusion paragraph are the same token.
- 383 of the 525 designation tokens are covered by v1 alone (its numerals `1`–`5`, `TBD`, `XX`, `ГОСТ`, `СП`, `СНиП`, upper-case emphasis words, the English field names). A new numeral `1`–`5` or a new mention of `ГОСТ` therefore passes; the byte-for-byte pins of the v1 question, categories and output contract hold that text, not this guard.
- Words that are not designations (the vocabulary the reports list as «not from the source»: «исполнение (левое или правое)», «класс эксплуатации», «уставки») are outside the guard by design.
- On a host without `/root/projects/PDF-proverka` at the pinned commit the sourced part skips: only PB, the tokenizer, the allowlist hygiene and the in-memory mutations run. The environment variable `AUDITMANAGER_LEGACY_PROMPTS_REPO` points elsewhere.
- Prompts are compared as they are in the tree; the guard does not read the recordings, so a recording rebuilt for a different prompt is `test_section_recordings.py`'s concern.
- The `disclosed_by` check reads the lane reports in `docs/program`; moving or renaming a report breaks it on purpose.

## Proof that forbidden paths are untouched

`git diff --name-only 2aec42072c7ba81be59570206e99e29bfd9e041c..HEAD` prints exactly the four paths of the table «Files» (checked on the final commit; see the lane's final message for the output). `/root/projects/PDF-proverka` was only read: its `HEAD` is the pinned `16ba8e5d…` and `git status --short` there prints nothing.
