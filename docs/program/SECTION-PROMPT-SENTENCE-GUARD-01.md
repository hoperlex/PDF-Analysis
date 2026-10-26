# SECTION-PROMPT-SENTENCE-GUARD-01 — the sentences of the section prompts are read, and the widen specimens are filed and replayed

Task: `docs/program/tasks/SECTION-PROMPT-SENTENCE-GUARD-01.md`. Written 2026-10-27 on branch `agent/section-prompt-sentence-guard-01`, base `630658b1` (`integration/ar-close-1026` with the three widen lanes merged). New files only: two tests, one builder, one generated table, 30 fixtures and these two documents. No prompt, recording, expectations line, allowlist line, ledger or report was edited.

**`reviewed` still carries no human review (`R-146ag`, `A-7`).** This lane adds a test that a sentence is *present*; it says nothing about whether the sentence is right.

## Result

1. `tests/unit/analysis/text_profiles/test_section_prompt_fragments.py` (336 cases) reads the real `system_prompt.md` of all 14 sections and asserts, from `section_prompt_fragments.json` (112 entries, 193 (entry, section) pairs): 29 ledger `adds` fragments present, 8 ledger `removes` fragments absent, 74 widen fragments present (G1 20 / 56 pairs, G2 31 / 40, G3 23 / 59), and the one ledger sentence a later lane replaced (`ITP` question ITP-1) recorded as `superseded`, absent, naming the two fragments of `SECTION-WIDEN-G3-01` that took its place, which are asserted present.
2. The residual of `D-224` is closed for these sentences. Deleting a sentence from a prompt and rebuilding the recording consistently left the existing set green (343 of 343 cases in the temp copy; the widen reports measured 322 of 322) and turns the new test red (M2, M3, M4, M6 and M8 below).
3. `tests/integration/sections/test_section_widen_specimens.py` (89 cases) replays the 30 specimens of the three widen reports, filed under `fixtures/recorded/sections_widen/<code>/<case>.json`, through the real `run_text_analysis` stage with each section's registered profile: a positive gives its findings grounded with every quote resolved, a negative gives no observation, one altered character in any one quote gives one unresolved evidence item.
4. The existing `test_section_recordings.py` and `fixtures/recorded/sections/build_fixtures.py` are untouched and do not see the new directory (proof under «The location»).

## Files

| File | What it is | Size |
| --- | --- | --- |
| `tests/unit/analysis/text_profiles/build_section_prompt_fragments.py` | the builder: reads the four documents, writes (`--write`) or checks (default) the table | 246 lines |
| `tests/unit/analysis/text_profiles/section_prompt_fragments.json` | the table, generated | 112 entries |
| `tests/unit/analysis/text_profiles/test_section_prompt_fragments.py` | the fragment test | 336 cases |
| `fixtures/recorded/sections_widen/<code_lower>/<case>.json` | the specimens, generated once from the reports | 30 files, 55,033 bytes (15 positive, 15 negative, 18 findings, 66 quotes) |
| `tests/integration/sections/test_section_widen_specimens.py` | the specimen test | 89 cases |
| `docs/program/tasks/SECTION-PROMPT-SENTENCE-GUARD-01.md`, this file | deliverables | |

## How the table was generated

Nothing was typed in. `python3 -I tests/unit/analysis/text_profiles/build_section_prompt_fragments.py --write` builds the file; the default run (and `test_the_table_is_what_the_documents_say`, which also compares the file byte for byte) re-reads the documents and fails on any difference.

- **Widen fragments**: the block between `<!-- fragments:begin -->` and `<!-- fragments:end -->` of each report, parsed with the same pattern as the report's own check command, taken as it stands (`id`, `sections`, `role`, `text`; text whitespace-normalised, which the reports already state). Ids are qualified with the report, `G1:W-HEAD`, because `W-HEAD` is one sentence in G1 and G3 and another in G2.
- **Ledger fragments**: the column «Prompt changes» of the 14 rows of `SECTION-REVIEW-LEDGER-01.md`. Each numbered change is read left to right: a `«…»` after `adds` becomes a `present` entry, after `removes` an `absent` entry; the entry id is `LEDGER:<section>:<change>:<adds|removes>:<k>`. A change with no fragment, a quote before any keyword, a row of the wrong width or a missing section is an error that stops the builder; nothing is skipped. Result: 14 rows, 25 changes, 38 fragments (29 `present`, 8 `absent`, 1 `superseded`), equal to an independent count of the same column (task file P-02).
- **The superseded sentence**: `SECTION-WIDEN-G3-01.md`, section «The ledger fragment this lane supersedes». The builder reads the verbatim sentence of the table row `ITP-1 (N)` there, finds the one ledger fragment with exactly that text (error if none or several), marks it `superseded` and records `superseded_in` and `superseded_by` (the two ids named in that section, each checked to exist in G3's block). Both directions are asserted: the old sentence stands nowhere (the new unit rule says to compare under a rule, the old one said not to compare: a prompt carrying both contradicts itself), and `G3:W-UNITS-REF-ITP-G3` and `G3:W-UNITS-ITP-G3` stand in the ITP prompt.
- **Matching**: a fragment matches when it occurs in the prompt after every run of whitespace, line breaks included, becomes one space on both sides, and for nothing else. A re-wrapped prompt stays green; one changed character, a comma or a quote mark turns the case red.

## What the fragment test holds

| Group | Cases | What it asserts |
| --- | --- | --- |
| shape | 5 | format and sources; every entry well formed (unique id, kind, known sections, normalised text of at least 7 characters, superseded entries complete); the 14 sections are read and the three lanes cover their four sections each; the counts of the reports (20/56, 31/40, 23/59) and of the ledger (25 changes by section, 29/8/1); the table equals what the documents say |
| prompts | 1 | `violations(table, prompts) == []` over the whole table |
| per entry | 103 + 8 + 1 | each `present` entry stands in every section it names; each `absent` entry does not; the superseded sentence is gone and its replacement stands |
| the guard can fail | 103 + 9 + 103 + 3 | on a copy of the prompts: deleting a fragment, putting a removed one back (also the superseded one), changing one character of a fragment, each turns the check red and names the entry and the section; re-wrapping the whole prompt keeps it green; a missing section is an error; a broken supersession is reported |

Container-free; 4.8 s.

## The specimens

Generated once, from the second `json` block of each report, by this script (kept here because the session scratchpad does not survive):

```python
"""One-off: file the specimens of SECTION-WIDEN-G1/G2/G3-01 (their second ```json block) as fixtures."""
import json
import re
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / "fixtures/recorded/sections_widen"
FENCE = "`" * 3
GROUPS = {"G1": "SECTION-WIDEN-G1-01", "G2": "SECTION-WIDEN-G2-01", "G3": "SECTION-WIDEN-G3-01"}
STATEMENT = (
    "Text and reply authored by hand for {task} to show what a widened prompt rule is meant to report or "
    "to leave alone, and filed by SECTION-PROMPT-SENTENCE-GUARD-01. No model produced this reply. Not "
    "field evidence for any profile's expert review; it says nothing about how a model answers."
)
for group, task in GROUPS.items():
    text = (ROOT / f"docs/program/{task}.md").read_text(encoding="utf-8")
    blocks = re.findall(FENCE + "json\n(.*?)\n" + FENCE, text, re.S)
    assert len(blocks) == 2, (task, len(blocks))
    for code, cases in json.loads(blocks[1]).items():
        for case, body in cases.items():
            assert set(body) == {"pages", "observations"} and case.endswith(("positive", "negative"))
            directory = OUT / code.lower()
            directory.mkdir(parents=True, exist_ok=True)
            document = {
                "format": "section-widen-specimen/1",
                "section_code": code,
                "case": case,
                "expect": "finding" if case.endswith("positive") else "none",
                "origin": {
                    "kind": "synthetic",
                    "statement": STATEMENT.format(task=task),
                    "task_id": task,
                    "source_report": f"docs/program/{task}.md",
                    "filed_by": "SECTION-PROMPT-SENTENCE-GUARD-01",
                },
                "pages": body["pages"],
                "observations": body["observations"],
            }
            (directory / f"{case}.json").write_text(
                json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
            )
```

From then on the fixtures are the home of the specimens; the test does not compare them with the reports.

**30 specimens, not 14.** The brief's «14 (7 + 7)» is G3's count. G1 holds 8, G2 8, G3 14: 15 positive, 15 negative, in the 12 widened sections (`PB` has nothing reinstatable, `AI` was not widened). The «positive with one altered quote» rows of the reports are the mutation of the check and are produced in the test, not filed. The OV positive holds 2 findings and the PT positive 3 (the report seeded several relations in one text), so the positives hold 18 findings in all, and the test asserts «exactly the findings of the reply, all grounded», not «exactly one». Case names are the keys of the reports (`positive`, `negative`, and for SS, ITP, GP the topic prefix: `journal_`, `capacity_`, `units_`, `total_`, `areas_`, `shares_`, `boundary_`, `nototal_`). Directories are lower-case, as under `fixtures/recorded/sections/`.

**What the replay does.** For each specimen the test builds the text layer from `pages` the way the extractor does (pages joined with no separator; the metadata of `fixtures/recorded/text_analysis/inputs/ar_baseline_text_layer.json`), builds the request the section's current prompt sends, writes the recording under that request's key into a pytest temporary directory, and calls `run_text_analysis` with `RecordedAdapter(<that directory>)`. Nothing is stored keyed to a prompt, so a prompt edit orphans nothing in this lane.

| Test | Cases | Asserts |
| --- | --- | --- |
| the filed set | 1 | exactly the 12 directories and 30 files named above; 15 and 15 |
| labelled and shaped | 30 | `synthetic`, task id by section, «No model produced this reply», no mode and no key field, not named like a recording key; every observation `internal_contradiction`, `finding_text` opens with «Синтетический ответ (», page numbers inside the text; a positive has findings, a negative has `[]` |
| positive replay | 15 | stage `succeeded`; proposed = emitted = number of findings; none dropped, none malformed, `evidence_unresolved` 0, `evidence_emitted` = quotes of the reply; the published texts equal the reply's; each quote equals the slice of the document-global text at the reported offsets and lies on the page the reply names; at least one finding quotes two places |
| negative replay | 15 | `succeeded`, 0 proposed, 0 emitted, 0 evidence, `observations == []` |
| one-character misquote | 15 | for every one of the 66 quotes of the positives in turn (one character replaced, checked not to occur in the text): `evidence_unresolved` 1, `evidence_emitted` one fewer; the finding stays when it has other quotes, and is dropped (`observations_dropped_unresolved` 1) when the altered quote was its only one |
| location | 1 + 12 | the adapter's default search never reads the directory; over a specimen text the default adapter finds no recording (`DomainError`), one case per section |

0.8 s.

### The location

The brief names `fixtures/recorded/sections_widen/` and says to put the specimens elsewhere if an existing test or glob picks the directory up. None does (task file P-05): `default_recording_dirs()` iterates `fixtures/recorded/sections` only, and `test_section_recordings.py` enumerates that directory only; `sections_widen` is a sibling. Measured: `test_section_recordings.py` and `tests/e2e/test_pc01_journey_section.py` with the new directory present, 122 passed. The converse is shown too (M16): the same specimens filed under `fixtures/recorded/sections/` turn `test_section_recordings.py` red.

**One cost, not a failure (task file P-06).** Everything under `fixtures/recorded/` is copied into the API image (`Dockerfile.api` line 87) and hashed into the content-derived build identity (`src/auditmanager/releases/build_id.py`). The 30 specimens add 55 KB to both. They are inert at run time. If the integrator prefers them out of the image and the build id, the move is `git mv fixtures/recorded/sections_widen fixtures/synthetic/sections_widen`, one constant (`SPECIMENS`) in the specimen test and the assertion `SPECIMENS.parent == default_section_recordings_root().parent` removed from `test_the_recorded_adapters_default_search_never_reads_the_specimens`; the 15 other cases do not change.

## Mutation table

All mutations were made in a **temp copy** (`src`, `fixtures/recorded`, `contracts`, the test directories and `docs/program/SECTION-*.md`, 14 MB, in the session scratchpad); the worktree was never edited and `git status` stayed clean. After each restore the SHA-256 over the profiles, fixtures, text-profile tests, program documents and section tests equalled the one taken before (`ef8cdeb252275798`). Unmutated: existing set 343, fragment test 336, specimen test 89 (all passed). «Existing set» = `tests/unit/analysis` (without `test_ar_v1_v2_removal.py`, which scans the whole repository), `tests/integration/sections` (without the new specimen test), `tests/contract/analysis_packages`, without the new fragment test. «Rebuilt» = `fixtures/recorded/sections/build_fixtures.py` run, `--check` printing `fixtures match`.

| # | Mutation | Existing set (343) | Fragment test (336) | Specimen test (89) | Red cases of the new test |
| --- | --- | --- | --- | --- | --- |
| M1 | PS prompt: the tolerance bullet `G1:W-B5` deleted; recordings not rebuilt | 8 failed (recordings, builder drift) | 4 failed | 89 passed | `test_the_prompts_agree_with_the_whole_table`, `…stands_in_every_section_it_names[G1:W-B5]`, and two self-check cases that need a green prompt |
| **M2** | the same deletion, **recordings rebuilt consistently** (the `D-224` residual) | **343 passed** | **4 failed** | 89 passed | the same |
| M3 | TX: the ledger sentence `LEDGER:TX:1:adds:1` deleted, rebuilt | 343 passed | 4 failed | 89 passed | `…stands_in_every_section_it_names[LEDGER:TX:1:adds:1]` |
| M4 | TX: one character of that sentence changed, rebuilt | 343 passed | 4 failed | 89 passed | the same |
| M5 | ITP: the unit rule `G3:W-UNITS-ITP-G3` deleted, rebuilt | 4 failed (token guard: three allowlist entries no longer occur) | 5 failed | 89 passed | `[G3:W-UNITS-ITP-G3]`, `test_a_superseded_ledger_sentence_is_gone_and_its_replacement_stands` |
| M6 | AI: the removed words «с одним и тем же номером» put back, rebuilt | 343 passed | 3 failed | 89 passed | `test_each_removed_fragment_stays_gone[LEDGER:AI:1:removes:1]` |
| M7 | AI: the removed designation «(Г1–Г4)» put back, rebuilt | 5 failed (token guard, as it should) | 3 failed | 89 passed | `[LEDGER:AI:2:removes:1]` |
| M8 | ITP: the superseded ledger sentence put back, rebuilt | 343 passed | 3 failed | 89 passed | `test_a_superseded_ledger_sentence_is_gone_and_its_replacement_stands` |
| M9 | the table loses the entry `G2:W-NONUM` | — | 2 failed | — | `test_the_counts_are_the_ones_the_documents_state`, `test_the_table_is_what_the_documents_say` |
| M10 | the G2 report's block loses `W-NONUM`; table kept | — | 1 failed | — | `test_the_table_is_what_the_documents_say` |
| M11 | the table and the G2 block both lose it (the source erased consistently) | — | 1 failed | — | `test_the_counts_are_the_ones_the_documents_state` (the pin of 31 / 40) |
| M12 | `ps/positive.json`: the last character of the first quote changed (`120` to `121`) | — | — | 2 failed | positive replay and misquote case of `ps/positive` |
| M13 | `ps/negative.json` given the positive's reply | — | — | 2 failed | `labelled_and_shaped[ps/negative]`, negative replay |
| M14 | `tx/positive.json`: the page number of the total moved from 2 to 1 | — | — | 2 failed | positive replay and misquote case of `tx/positive` |
| M15 | `gp/nototal_negative.json` deleted | — | — | 1 failed | the filed set |
| M16 | the PS specimens filed under `fixtures/recorded/sections/ps_widen` | `test_section_recordings.py`: 2 failed | — | — | (why the directory is a sibling) |
| M0 | all restored | 343 passed | 336 passed | 89 passed | — |

Read: for a plain-word sentence (M2, M3, M4, M6, M8) the new test is the **only** red; for a numeral or a class designation (M5, M7) the token guard also notices, as before.

## Commands and results

| Command | Result |
| --- | --- |
| `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections tests/contract/analysis_packages` | 824 passed (7.8 s) |
| the same with only `tests/unit/analysis/text_profiles/test_section_prompt_fragments.py` | 336 passed |
| the same with only `tests/integration/sections/test_section_widen_specimens.py` | 89 passed |
| the base set with the new fragment test ignored (`tests/unit/analysis/text_profiles`, `test_section_recordings.py`, `tests/contract/analysis_packages`) | 295 passed (P-07), so no existing case changed |
| `python3 -I tests/unit/analysis/text_profiles/build_section_prompt_fragments.py` | `fragments match`, rc 0 |
| `tests/integration/releases/test_build_id.py` | 8 passed |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` (committed tree) | 105 passed |
| the governance one-liner on the task file | `[]` |
| `git diff --check` | clean |

`tests/integration/sections` needs no stack: all of it ran container-free (267 passed with the new file). No database, no network, no docker.

## Corrections to the ledger and reports that this lane recommends (not made: forbidden paths)

1. **`SECTION-REVIEW-LEDGER-01`, row ITP, prompt change 1** («adds … не сравнивай»): the sentence no longer stands; mark it «superseded by `SECTION-WIDEN-G3-01` (`W-UNITS-REF-ITP-G3`, `W-UNITS-ITP-G3`)». The ITP assumption «ITP-1 (N). A load written in kW in one place and in another unit elsewhere is no longer compared» is stale for the same reason: the prompt now converts by the definition and compares. The table records the row as superseded, so the fragment test does not need the ledger to change, but it will read the new wording the same way as long as the superseded row still quotes the same sentence; if the integrator deletes the sentence, `apply_supersessions` stops with a named error and the table has to be regenerated.
2. **The ledger says «All 14 rows read `reviewed` at `1.1.0`»** (the method list, and «What is pinned by what» item 1, «pin the words `reviewed` and `1.1.0`»): twelve profiles are now `1.2.0` (all but `AI` and `PB`).
3. **«What is pinned by what», items 3 and 5**, and the PS assumption 7 («pinned by the recording key only, not by a content test»): the *sentences* of the narrowing and widening are now held by `test_section_prompt_fragments.py`. The decisions and assumptions themselves are still held by prose only.
4. **The widen reports** say the specimens «are not committed as fixtures» (G1 and G3 premise P-07, G2 deviation D1) and that the guard lane «must treat the row as superseded»: both are done by this lane. G2's note about restoring commit `b91e2022` is not needed.
5. **`DEBT_REGISTER.md`**, the `D-224` residual: closed for the sentences listed in the ledger and the three reports (a sentence that no table lists is still read by no test); this lane did not touch the register.

## Integration notes

- The diff adds files only (below); no existing file is edited, so the merge cannot conflict. The lane needs no migration, contract or composition-root change.
- **A prompt edit now has a cost, on purpose.** Deleting or rewording a listed sentence turns the fragment test red. The way through is not to edit the table: change the document that is the source (a new widen report carries a new block; a supersession is written in the report that makes it, in the form of `SECTION-WIDEN-G3-01` section «The ledger fragment this lane supersedes»), run `build_section_prompt_fragments.py --write`, and update the pins in `test_the_counts_are_the_ones_the_documents_state` (they are the third copy of the counts on purpose: a consistent erasure of a fragment from a report and from the table is caught only by them, M11).
- A new widen report (a G4) is added by extending `WIDEN`, `SECTION_ORDER` if a section appears, and the pins; the builder fails on a ledger or report it cannot read, so it cannot go quiet.
- The fragment test reads four documents at test time. Editing the ledger column «Prompt changes», a report's fragment block or G3's supersession section reddens it until `--write`; editing any other part of those documents does not.
- Cost: 336 + 89 cases, about 6 s together.

## Limits

- **Presence, not meaning.** A sentence that stands can be contradicted by another sentence of the prompt; the test sees that only for the one superseded pair. Nobody reads whether a fragment is right (`A-7`).
- **Whitespace is the only tolerance.** A fragment that ends in `;` (the reports quote some that way) turns red if a later edit ends it with `.`. That is a deliberate friction, and it is the cost of pinning by text.
- **`absent` is a weak guard.** It stops a removed sentence coming back verbatim; a reworded return passes. Eight entries; seven carry a designation (a class, a mark, a symbol) that the token guard also reads, one («с одним и тем же номером») is plain words and is held by this test alone.
- **Thin entries.** `PB` has one entry (`LEDGER:PB:1:adds:1`, «частям здания», 13 characters); `AI` has two removals and one addition. Neither was widened.
- **The ledger is parsed from English prose** («adds», «removes», `«…»`). A rewrite of the column in other words stops the builder with a named error; it is not read around.
- **Specimens are hand-authored.** The positive test shows the stage grounds the quotes, not that the claim is arithmetically true and not that a model would say it. The negative test proves only that an empty reply is accepted. A positive reply replayed over its own negative text still grounds in one pair (`SS` capacity: both quotes occur in both texts), so the negatives do not show that a wrong claim is caught.
- **The specimen tests do not read the prompts.** They build the request key from the current prompt and nothing else, so a prompt edit cannot redden them; that is the other half, the fragment test.
- **The temp-copy runs did not include `tests/unit/analysis/test_ar_v1_v2_removal.py`** (it scans `tools/`, `scripts/` and the web tree, absent from the copy); on the worktree it ran separately: 25 passed.
- **Footprint.** 55 KB of specimens enter the API image and the build identity (see «The location»).

## Proof that forbidden paths are untouched

`git diff --name-only 630658b1..HEAD` prints exactly these 35 paths, all new files, all in the allowed list (`git diff --diff-filter=M --name-only 630658b1..HEAD` prints nothing):

```text
docs/program/SECTION-PROMPT-SENTENCE-GUARD-01.md
docs/program/tasks/SECTION-PROMPT-SENTENCE-GUARD-01.md
fixtures/recorded/sections_widen/{eom,kj,km,ov,pos,ps,pt,tx,vk}/{negative,positive}.json   (18 files)
fixtures/recorded/sections_widen/gp/{areas_positive,boundary_negative,nototal_negative,shares_positive}.json
fixtures/recorded/sections_widen/itp/{total_negative,total_positive,units_negative,units_positive}.json
fixtures/recorded/sections_widen/ss/{capacity_negative,capacity_positive,journal_negative,journal_positive}.json
tests/integration/sections/test_section_widen_specimens.py
tests/unit/analysis/text_profiles/build_section_prompt_fragments.py
tests/unit/analysis/text_profiles/section_prompt_fragments.json
tests/unit/analysis/text_profiles/test_section_prompt_fragments.py
```

No profile, `profile.json`, `system_prompt.md`, recording, `build_fixtures.py`, `test_section_recordings.py`, expectations file, allowlist, ledger, widen report, `W59-SECTION-PROFILES-01.md`, registry, `prompt.py`, `response.py`, `stage.py`, `P02_LOCK.json`, contract, migration, `web/**`, `infra/**` or lock file appears.
