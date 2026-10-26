# Task SECTION-PROMPT-SENTENCE-GUARD-01 — the sentences of the 14 section prompts are read by a test, and the widen specimens are filed and replayed through the real stage

task_id: SECTION-PROMPT-SENTENCE-GUARD-01
status: completed in development candidate

## Outcome

(1) One test reads the real `system_prompt.md` of every section and asserts that each `adds` fragment of the 25 narrowing decisions of `SECTION-REVIEW-LEDGER-01` is present, each `removes` fragment is absent, every fragment of the machine-readable tables of `SECTION-WIDEN-G1-01`, `-G2-` and `-G3-` is present, and that the one ledger sentence a later lane replaced (`ITP` question ITP-1, replaced by `SECTION-WIDEN-G3-01`) is recorded as superseded, is absent, and names the fragments that stand in its place. A prompt edit that deletes a sentence and rebuilds the recording consistently, which passed every other test (`D-224` residual), turns this test red. (2) The 30 positive and negative specimens of the three widen reports are filed as fixtures and replayed through `run_text_analysis`: a positive gives grounded findings with every quote resolved, a negative gives no observation, one altered character in a quote gives one unresolved evidence item.

## Depends on

- `SECTION-REVIEW-LEDGER-01` — completed; its table is the source of the 25 narrowing decisions.
- `SECTION-WIDEN-G1-01`, `SECTION-WIDEN-G2-01`, `SECTION-WIDEN-G3-01` — completed and merged into the base; their fragment blocks and specimen blocks are the source.
- `SECTION-PROMPT-TOKEN-GUARD-01`, `SECTION-RECORDINGS-01` — completed; the model of a prompt-reading guard and the recordings test this lane must leave green and unedited.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.7.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable
- migration head: `0033_ar_v3_cite_stage_id`, unchanged (no migration)
- base commit: `630658b1` (`integration/ar-close-1026` with all three widen lanes merged)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No section, package, route, error code or migration is added or removed. The fragment table and the specimen directory are new test inputs, not maintained sets of the product.

## Captured premise evidence
- premise: the ledger, the three reports and the existing tests are as the lane brief (`PRODUCTION-WAVE-PW4.md` section 7) says, except P-04 (the reports hold 30 specimens, not 14: the brief's 14 is lane G3's count; OV and PT positives carry 2 and 3 findings, not one) and P-06 (a fixture directory under `fixtures/recorded/` is copied into the API image and hashed into the build identity).

### P-01 — the base, the branch and the lane brief
- captured_at: 2026-10-27
- command: `git rev-parse --abbrev-ref HEAD; git rev-parse 630658b1 | cut -c1-12; git merge-base HEAD integration/ar-close-1026 | cut -c1-12; rg -n "SECTION-PROMPT-SENTENCE-GUARD-01" docs/program/dispatch/PRODUCTION-WAVE-PW4.md | cut -c1-160`
- captured_output:
  ```text
  agent/section-prompt-sentence-guard-01
  630658b1397b
  630658b1397b
  15:| The narrowing sentences are not read by any test (`D-224` residual) | `SECTION-PROMPT-SENTENCE-GUARD-01` |
  30:| SG | `SECTION-PROMPT-SENTENCE-GUARD-01` | `tests/unit/analysis/text_profiles/**` (new files only) | no | S |
  85:**Steps.** Per section: edit `system_prompt.md` (keep the v1 skeleton that `tests/unit/analysis/text_profiles/test_text_profile_packages.py` reads); bump `profile_version` to the next minor and keep `status` `reviewed`; add to the section's fixtures one **positive** recording (a text in which a total differs from its rows → the recorded reply has a finding with the two quotes) and one **negative** (consistent totals → no finding), through `fixtures/recorded/sections/build_fixtures.py` (read `fixtures/recorded/sections/README.md` first; editing a prompt orphans its recording; run `build_fixtures.py --check` last); regenerate the section's line of `tests/unit/analysis/text_profiles/section_profile_expectations.json` from `profile.json`; add the narrowing/widening sentences as **fragments** in the report table (section, added fragment verbatim) so that `SECTION-PROMPT-SENTENCE-GUARD-01` can read them.
  93:## 7. Lane SG — `SECTION-PROMPT-SENTENCE-GUARD-01` (after G1–G3 merge)
  ```
- interpretation: the branch starts at the base the brief names and the lane is section 7 of the wave dispatch. Line 85 is the sentence in the brief of lanes G1–G3 that obliges their reports to carry the fragment tables this lane reads.

### P-02 — the ledger: 14 rows, 25 prompt changes, 38 quoted fragments (checked independently of the builder)
- captured_at: 2026-10-27
- command: `python3 -I -c "import re;rows=[l for l in open('docs/program/SECTION-REVIEW-LEDGER-01.md',encoding='utf-8') if re.match(r'^\| [A-Z]+ \| ',l) and not l.startswith('| Code')];cells=[l.rstrip('\n')[1:-1].split(' | ')[5] for l in rows];print('rows',len(rows),'prompt-change items',sum(len([i for i in c.split('<br>') if re.match(r'\d+\. ',i)]) for c in cells),'quoted fragments',sum(c.count('«') for c in cells),'adds',sum(len(re.findall(r'\badds\b',c)) for c in cells),'removes',sum(len(re.findall(r'\bremoves\b',c)) for c in cells))"`
- captured_output:
  ```text
  rows 14 prompt-change items 25 quoted fragments 38 adds 23 removes 6
  ```
- interpretation: the ledger's column «Prompt changes» holds 25 numbered changes (one per narrowing group; the ledger's own total is «N 25») with 38 quoted fragments; «adds» and «removes» are fewer than the fragments because one keyword can govern several quotes («adds three near-miss pairs, «A», «B» and «C»»). The builder reads the same column and produces 29 `present`, 8 `absent` and 1 `superseded` entry, 38 in all (test `test_the_counts_are_the_ones_the_documents_state`).

### P-03 — the reports' own check commands: every widen fragment stands in the prompts of the base
- captured_at: 2026-10-27
- command: the check command of each report (the block «Check (prints the fragments missing from the prompts of this tree…)» of `SECTION-WIDEN-G1-01.md`, `-G2-` and `-G3-`, with the report name changed), run in turn
- captured_output:
  ```text
  G1 20 fragments; missing []
  G2 31 fragments; missing []
  G3 23 fragments; missing []
  ```
- interpretation: 74 fragments, 155 (fragment, section) pairs (56 + 40 + 59), none missing at the base. Seven ids occur in more than one report (`W-HEAD` in all three, six more in G1 and G3); `W-HEAD` is a different sentence in G2 than in G1 and G3, so the table qualifies every id with its report (`G1:W-HEAD`).

### P-04 — the specimens: 30, not 14
- captured_at: 2026-10-27
- command: `python3 -I -c "import json,re;F='\`'*3;[print('G%d'%g,{c:sorted(v) for c,v in json.loads(re.findall(F+'json\n(.*?)\n'+F,open('docs/program/SECTION-WIDEN-G%d-01.md'%g,encoding='utf-8').read(),re.S)[1]).items()}) for g in (1,2,3)]"`
- captured_output:
  ```text
  G1 {'PS': ['negative', 'positive'], 'POS': ['negative', 'positive'], 'TX': ['negative', 'positive'], 'KJ': ['negative', 'positive']}
  G2 {'KM': ['negative', 'positive'], 'OV': ['negative', 'positive'], 'VK': ['negative', 'positive'], 'PT': ['negative', 'positive']}
  G3 {'EOM': ['negative', 'positive'], 'SS': ['capacity_negative', 'capacity_positive', 'journal_negative', 'journal_positive'], 'ITP': ['total_negative', 'total_positive', 'units_negative', 'units_positive'], 'GP': ['areas_positive', 'boundary_negative', 'nototal_negative', 'shares_positive']}
  ```
- interpretation: G1 has 8 specimens, G2 8, G3 14: 30 in all, 15 positive and 15 negative. The brief's «14 (7 + 7)» is G3's count alone. The OV positive holds 2 findings and the PT positive 3 (the report seeded two and three relations in one text), so «exactly one grounded finding» is asserted as «exactly the findings of the reply, all grounded»; 18 findings in the 15 positives. Each report's table also lists a «positive with one altered quote» row; those are not separate texts, they are the mutation, produced in the test.

### P-05 — the existing recordings test pins the sections directory and the adapter searches only that root
- captured_at: 2026-10-27
- command: `rg -n "def default_recording_dirs|root.iterdir|SECTION_RECORDINGS_RELPATH: Final" src/auditmanager/analysis/text/recorded.py; rg -n "iterdir\(\)" tests/integration/sections/test_section_recordings.py; sed -n 195,200p tests/integration/sections/test_section_recordings.py`
- captured_output:
  ```text
  70:SECTION_RECORDINGS_RELPATH: Final[str] = "fixtures/recorded/sections"
  84:def default_recording_dirs() -> tuple[Path, ...]:
  97:                    for entry in root.iterdir()
  97:    assert sorted(item.name for item in directory.iterdir()) == [f"{request.request_sha256}.json"]
  197:        item.name for item in SECTIONS.iterdir()
      assert len(RECORDED_SECTIONS) == 14 == len(set(RECORDED_SECTIONS))
      directories = {
          item.name for item in SECTIONS.iterdir()
          if item.is_dir() and not item.name.startswith(("_", "."))
      }
      assert directories == {code.lower() for code in RECORDED_SECTIONS} | {"ar_specification"}
  ```
- interpretation: the adapter and the test both enumerate `fixtures/recorded/sections` only; `fixtures/recorded/sections_widen` is a sibling of it, not a child, so neither reads it. A directory filed under `sections/` instead is refused by the test (mutation M-J5 of the report). No other code or test enumerates `fixtures/recorded` as a whole (`rg` over `src tests tools scripts infra` for `fixtures/recorded` outside the two named subdirectories finds only the strings in P-06).

### P-06 — `fixtures/recorded/` is copied into the API image and hashed into the build identity
- captured_at: 2026-10-27
- command: `rg -n 'fixtures" / "recorded"|fixtures/recorded' --glob '*.py' --glob '*.sh' --glob 'Dockerfile*' --glob 'Makefile' src tests tools scripts infra Makefile | rg -v 'recorded/(sections|text_analysis)|recorded" / "(sections|text_analysis)' | rg -v "sections_widen|test_section_widen" | cut -c1-170`
- captured_output:
  ```text
  scripts/manual-alpha-check.sh:168:    "src/", "db/", "contracts/", "fixtures/recorded/", "release-notes/",
  infra/deploy/Dockerfile.api:84:# `fixtures/recorded` is 72K; the other 55M of `fixtures/` is corpus and test material and
  infra/deploy/Dockerfile.api:87:COPY fixtures/recorded/ /app/fixtures/recorded/
  src/auditmanager/releases/build_id.py:15:    "fixtures/recorded",
  tests/integration/analysis/test_stage_status_and_cost_rules.py:17:whatever object it was handed. Nothing is added to `fixtures/recorded/**`.
  tests/integration/releases/test_build_id.py:18:        "src/auditmanager", "db", "contracts", "fixtures/recorded",
  tests/integration/releases/test_build_id.py:26:        "fixtures/recorded/sample.json": b"[]\n",
  tests/integration/releases/test_build_id.py:40:        "docs/program/P02_LOCK.json", "fixtures/recorded/sample.json",
  tests/integration/releases/test_build_id.py:109:            "fixtures/recorded/sample.json": b"[]\n",
  tests/integration/composition/test_deployed_stack_probe.py:627:            "fixtures/recorded/",
  ```
- interpretation: every file under `fixtures/recorded/` is copied into the API image and is part of the content-derived build identity (`build_id.py`). The 30 specimens (55 KB) go there because the brief names that path; they are inert at runtime (the adapter never reads them), but the image and the build id grow with them. `tests/integration/releases/test_build_id.py` (8 passed) and the image-contents pin (`COPY` list) are unaffected. The report states the relocation recipe if the integrator prefers `fixtures/synthetic/`.

### P-07 — the baseline of the test set before this lane's files
- captured_at: 2026-10-27
- command: `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/text_profiles tests/integration/sections/test_section_recordings.py tests/contract/analysis_packages --ignore=tests/unit/analysis/text_profiles/test_section_prompt_fragments.py`
- captured_output:
  ```text
  295 passed in 2.74s
  ```
- interpretation: with the new fragment test ignored the set is the base's 295; no existing test is edited, so any later count is 295 plus the new cases.

### P-08 — what the real stage does with a positive, a negative and a one-character misquote (the replay snippet of the G1 report, run as it stands)
- captured_at: 2026-10-27
- command: `PYTHONPATH=src:$BS .venv/bin/python -c "import json,re;F=chr(96)*3;t=open('docs/program/SECTION-WIDEN-G1-01.md',encoding='utf-8').read();s=json.loads(re.findall(F+'json\n(.*?)\n'+F,t,re.S)[1])['PS'];exec(re.findall(F+'python\n(.*?)\n'+F,t,re.S)[0]);a=json.loads(json.dumps(s['positive']['observations']));a[0]['evidence'][1]['quote']=a[0]['evidence'][1]['quote'][:-1]+'X';k=('observations_proposed','observations_emitted','observations_dropped_unresolved','evidence_emitted','evidence_unresolved');[print(n,*(lambda r:(r[0],{x:r[1][x] for x in k}))(replay('PS',c['pages'],o))) for n,c,o in (('positive',s['positive'],s['positive']['observations']),('one character altered',s['positive'],a),('negative',s['negative'],s['negative']['observations']))]"`
- captured_output:
  ```text
  positive succeeded {'observations_proposed': 1, 'observations_emitted': 1, 'observations_dropped_unresolved': 0, 'evidence_emitted': 5, 'evidence_unresolved': 0}
  one character altered succeeded {'observations_proposed': 1, 'observations_emitted': 1, 'observations_dropped_unresolved': 0, 'evidence_emitted': 4, 'evidence_unresolved': 1}
  negative succeeded {'observations_proposed': 0, 'observations_emitted': 0, 'observations_dropped_unresolved': 0, 'evidence_emitted': 0, 'evidence_unresolved': 0}
  ```
- interpretation: a finding keeps standing with one unresolved quote among others; a finding whose only quote is altered is dropped (`observations_dropped_unresolved` 1; PT's second finding has one quote). The test asserts both. Replaying a positive reply over its negative text leaves no unresolved quote in one pair (`SS` capacity: the quotes occur in both texts), so the negatives do not prove that a wrong claim is caught, only that an empty reply is accepted (stated in the report as a limit).

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `tests/unit/analysis/text_profiles/build_section_prompt_fragments.py`
- `tests/unit/analysis/text_profiles/section_prompt_fragments.json`
- `tests/unit/analysis/text_profiles/test_section_prompt_fragments.py`
- `tests/integration/sections/test_section_widen_specimens.py`
- `fixtures/recorded/sections_widen/**`
- `docs/program/tasks/SECTION-PROMPT-SENTENCE-GUARD-01.md`
- `docs/program/SECTION-PROMPT-SENTENCE-GUARD-01.md`

## Forbidden hotspots

Every package under `src/auditmanager/analysis/text/profiles/**`, `prompt.py`, `response.py`, `stage.py`, the registry, `tests/integration/sections/test_section_recordings.py`, `fixtures/recorded/sections/**` (including `build_fixtures.py`), every other existing test, `section_profile_expectations.json`, `prompt_token_allowlist.json`, `docs/program/SECTION-REVIEW-LEDGER-01.md` and the three widen reports (the ledger corrections are only recommended), `DEBT_REGISTER.md`, `CURRENT_STATE.md`, `contracts/**`, migrations, `web/**`, `infra/**`, root dependency and lock files, the composition root.

## Non-goals

- No edit of any prompt, recording, expectations line, allowlist line, ledger or report; no correction of the ledger row ITP-1 (recorded as superseded in the table, recommended in the report).
- No claim that a model gives the specimens' replies or leaves their traps alone; no claim that any sentence was reviewed by anyone (`A-7`).
- No new category, field, severity or norm; no model call, no container, no migration, no push, no tag.

## Deliverables

- `tests/unit/analysis/text_profiles/build_section_prompt_fragments.py`: reads the ledger column «Prompt changes», the three fragment blocks and the G3 supersession section; `--write` rewrites the table, the default run checks it.
- `tests/unit/analysis/text_profiles/section_prompt_fragments.json`: 112 entries (38 from the ledger: 29 present, 8 absent, 1 superseded; 74 from the reports), generated.
- `tests/unit/analysis/text_profiles/test_section_prompt_fragments.py`: 336 cases.
- `fixtures/recorded/sections_widen/<code>/<case>.json`: 30 specimens, generated from the reports' specimen blocks by a one-off script (given in the report).
- `tests/integration/sections/test_section_widen_specimens.py`: 89 cases.
- Report `docs/program/SECTION-PROMPT-SENTENCE-GUARD-01.md`.

## Required tests

- command: `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles tests/integration/sections tests/contract/analysis_packages`
- expected: 824 passed (the new 336 + 89 included).
- command: `python3 -I tests/unit/analysis/text_profiles/build_section_prompt_fragments.py` — expected `fragments match`, rc 0.
- mutations (in a temp copy of the tree, never in the worktree): delete one fragment from one prompt, with and without a consistent recording rebuild; put a removed sentence back; put the superseded ITP sentence back; change one character; drop an entry from the table; drop a fragment from a report block; flip one character of a specimen quote; give a negative a reply; move a page number; delete a specimen file; file the specimens under `fixtures/recorded/sections/`.
- The governance one-liner on this file — expected `[]`; `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` and `git diff --check` after the last commit.

## Integration contract

The integrator can rely on: the diff is confined to the allowed paths and adds files only; no existing file is edited; the fragment test is container-free and reads only `src/auditmanager/analysis/text/profiles/*/{profile.json,system_prompt.md}`, the four documents named in the table and its own JSON; the specimen test is container-free and uses the registry, the committed AR text-layer metadata `fixtures/recorded/text_analysis/inputs/ar_baseline_text_layer.json` and a temporary recording directory; a later lane that edits a prompt must keep every `present` fragment (or move the entry to `superseded` through the document that records the supersession and regenerate the table with `--write`); a lane that adds a section or a widen report extends the builder's `SECTION_ORDER` / `WIDEN` constants and the test's pins.

## Failure/idempotency/security cases

A prompt that loses a `present` sentence, regains an `absent` one or regains the superseded ITP sentence fails the test with the fragment id and the section. A table that differs from the documents, or a count that differs from the reports', fails. A specimen whose reply is no longer grounded in its text, a negative with a reply, a missing specimen or a specimen filed under the recordings root fails. Nothing writes outside a pytest temporary directory.

## Rollback / feature flag

Delete the files listed under Deliverables; nothing else refers to them. No feature flag.

## Handoff

- changed files: see the report
- commands/results: see the report
- known limits: the specimens' replies are hand-authored; whitespace is the only tolerated difference; a fragment test cannot say that a sentence still means what it meant (see the report)
- integration notes: see the report
