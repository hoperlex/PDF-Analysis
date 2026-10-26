# Task ROADMAP-GAP-2026-10-27 — a measured list of what is left of the big roadmap, and of what the 14 non-АР sections, their prompts and their workflow still lack

task_id: ROADMAP-GAP-2026-10-27
status: completed (read-only audit; documents only)

## Outcome

One document, `docs/program/ROADMAP-GAP-2026-10-27.md`, that the integrator can dispatch from: the wave table of `docs/program/dispatch/ROADMAP-TO-BETA.md` section 4 from W56a to W64 and «after 1.0» in 59 items with a status and its evidence (DONE 24, PARTIAL 18, MISSING 13, SUPERSEDED 4); one row for each of the 14 non-АР sections saying what its analysis does, what the legacy profile checked and the prompt excludes, and which exclusions could be reinstated inside the existing contract, which need a contract change, which need norms or experts and which are not possible in one document; the section workflow from upload to export in 24 steps with the scope of each (all sections, the 14, АР only, not implemented); what the prompts ask for and return and a sized option list for letting a section emit more categories; one list of what cannot be finished without a human or a host (27 items); and five code lanes with hotspots, sizes, dependencies, check commands and a parallel plan. The owner asked on 2026-10-27 («как там с разделами, их промптами и workflow? Надо доделать! … завершай всё, что было в плане большого роудмапа»).

## Depends on

- none: a read-only audit of the tip of `integration/ar-close-1026` named in the base commit below; nothing it reads was produced by an unfinished task.

## Frozen inputs

- domain contract: not_applicable (not read)
- API contract: `1.7.0`, 92 paths, 104 operations, 301 schemas (P-02), not touched
- analysis/comparison/event contract: not_applicable
- migration head: `0033_ar_v3_cite_stage_id`, unchanged (no migration)
- base commit: `87db74a91e9777df9e46a98f9b29df9b480f909d` (P-01). The integration branch has since merged `f134a6c9` and `a1d3f348` (P-14); the report says which statements that touches.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No route, screen, error code or migration is added or removed.

## Captured premise evidence

- premise: the tree at the base commit holds 14 `reviewed` section profiles that return two categories, a closed 12-value category list, a review-only АР path with no finding row, АР-only guards in the optimisation reads, window and crop loaders with no caller, a verification operation that always refuses, and a comparison that stores nothing; captured before the report was written

### P-01 — the base of the work

- captured_at: 2026-10-27
- command: `git merge-base HEAD integration/ar-close-1026`
- captured_output:
  ```text
  87db74a91e9777df9e46a98f9b29df9b480f909d
  ```
- interpretation: the audit branch forks from the tip named in the brief; the commit is the base commit of the report.

### P-02 — the surface, the contract version and the closed category list

- captured_at: 2026-10-27
- command: `python3 -I -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));s=d['components']['schemas'];print(len(d['paths']),sum(1 for p in d['paths'].values() for o in p.values() if isinstance(o,dict) and 'operationId' in o),len(s),d['info']['version']);print(s['FindingCategory']['enum'])"`
- captured_output:
  ```text
  92 104 301 1.7.0
  ['internal_contradiction', 'explicit_placeholder', 'dimensions', 'layout', 'facade', 'roof', 'documentation', 'evacuation', 'fire_safety', 'accessibility', 'insulation', 'sound']
  ```
- interpretation: 92 paths, 104 operations, 301 schemas, contract `1.7.0`, and the 12 values the report calls the closed list: 7 non-normative (the first seven) and 5 normative (the last five).

### P-03 — status and version of the 14 section profiles

- captured_at: 2026-10-27
- command: `python3 -I -c "import json,glob;print(sorted(json.load(open(f))['section_code']+':'+json.load(open(f))['status']+':'+json.load(open(f))['profile_version'] for f in glob.glob('src/auditmanager/analysis/text/profiles/*/profile.json')))"`
- captured_output:
  ```text
  ['AI:reviewed:1.1.0', 'EOM:reviewed:1.1.0', 'GP:reviewed:1.1.0', 'ITP:reviewed:1.1.0', 'KJ:reviewed:1.1.0', 'KM:reviewed:1.1.0', 'OV:reviewed:1.1.0', 'PB:reviewed:1.1.0', 'POS:reviewed:1.1.0', 'PS:reviewed:1.1.0', 'PT:reviewed:1.1.0', 'SS:reviewed:1.1.0', 'TX:reviewed:1.1.0', 'VK:reviewed:1.1.0']
  ```
- interpretation: all 14 are `reviewed` at `1.1.0`; the status carries no human review (`R-146ag`, `A-7`), which this output does not show and the rulings state.

### P-04 — every section profile gets the same two categories

- captured_at: 2026-10-27
- command: `grep -n "^CATEGORIES" src/auditmanager/analysis/text/prompt.py; grep -n "categories=CATEGORIES" src/auditmanager/analysis/text/profile_registry.py`
- captured_output:
  ```text
  41:CATEGORIES: Final[tuple[str, ...]] = ("internal_contradiction", "explicit_placeholder")
  326:        categories=CATEGORIES,
  ```
- interpretation: the registry builds every package's profile with the one module constant; no section declares its own list.

### P-05 — kept, excluded and open items in the 13 legacy records

- captured_at: 2026-10-27
- command: `python3 -I -c "import re;t=open('docs/program/W59-SECTION-PROFILES-01.md',encoding='utf-8').read();p=re.split(r'(?m)^### (\w+) — ',t);f=lambda x:[len(re.findall(r'(?m)^- ',x.split(a)[1].split(b)[0])) for a,b in (('Kept (reframed','Excluded:'),('Excluded:','Open questions'),('Open questions','@@END'))];r={p[i]:f(re.split(r'\n## ',p[i+1])[0]+'@@END') for i in range(1,len(p),2) if p[i]!='PB'};print(r);print([sum(v[k] for v in r.values()) for k in range(3)])"`
- captured_output:
  ```text
  {'AI': [10, 10, 4], 'PS': [11, 13, 5], 'POS': [11, 9, 4], 'TX': [12, 12, 5], 'KJ': [14, 13, 5], 'KM': [11, 11, 5], 'OV': [10, 11, 5], 'VK': [10, 8, 5], 'PT': [11, 12, 5], 'EOM': [7, 10, 4], 'SS': [11, 19, 5], 'ITP': [12, 17, 5], 'GP': [11, 13, 5]}
  [141, 158, 62]
  ```
- interpretation: the per-section lists are `[kept, excluded, open]`; the totals 141, 158 and 62 are the figures of section 2 of the report. `PB` has no such record. The assignment of each of the 158 excluded items to a bucket is the lane's reading and is not computed by this command.

### P-06 — the one-call input budget in characters

- captured_at: 2026-10-27
- command: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -c "from auditmanager.analysis.text.budget import input_budget_characters as f, REFERENCE_DOCUMENT_CHARACTERS as r;print(f('claude-opus-5',1.0),f('claude-sonnet-5',1.0),r)"`
- captured_output:
  ```text
  152361 572361 93690
  ```
- interpretation: at the pinned primary model and the 1.00 USD ceiling a section run accepts at most 152,361 characters; the one real 30-page set is 93,690 characters, so the limit is about 48 pages of that density (a derived figure) while the upload admits 500 pages.

### P-07 — the АР-only guards of the optimisation reads

- captured_at: 2026-10-27
- command: `grep -rn "SECTION_AR" src/auditmanager/optimisation --include=*.py | grep -v "__all__\|^src/auditmanager/optimisation/project_match.py:5" | cut -c1-140`
- captured_output:
  ```text
  src/auditmanager/optimisation/proposals/commands.py:48:    SECTION_AR,
  src/auditmanager/optimisation/proposals/commands.py:221:        if entry.section_code == SECTION_AR
  src/auditmanager/optimisation/project_match.py:69:SECTION_AR: Final[str] = "AR"
  src/auditmanager/optimisation/project_match.py:281:    if classification.section_code != SECTION_AR:
  ```
- interpretation: two guards, the specification read (`project_match.py:281`) and the vendor list the pass picks (`src/auditmanager/optimisation/proposals/commands.py:221`); the section Form-7 read has no such guard.

### P-08 — the АР path writes no finding and drops every proposal without a norm citation

- captured_at: 2026-10-27
- command: `grep -n "if not accepted.norm_citations" src/auditmanager/runs/v3_review_artifact.py; grep -n "no finding row is written" src/auditmanager/runs/v3_review_terminal.py`
- captured_output:
  ```text
  101:        if not accepted.norm_citations:
  67:    publishes only the already verified CITE review; no finding row is written.
  ```
- interpretation: the first line is the skip of every accepted non-normative proposal (all seven non-normative values); the second is the docstring of the terminal that closes a v3 Run.

### P-09 — the one function that would publish a grounded v3 finding has no production caller

- captured_at: 2026-10-27
- command: `grep -rn "publish_grounded_v3_finding" src tests --include=*.py | cut -c1-130`
- captured_output:
  ```text
  src/auditmanager/findings/citation_publication.py:230:def publish_grounded_v3_finding(
  tests/integration/findings/test_w57a_citation_publication_offline.py:15:    publish_grounded_v3_finding,
  tests/integration/findings/test_w57a_citation_publication_offline.py:114:    return publish_grounded_v3_finding(
  ```
- interpretation: a definition and one test; nothing in `src` calls it.

### P-10 — the W56b loaders have no caller

- captured_at: 2026-10-27
- command: `grep -rn "load_saved_text_windows\|load_saved_recognised_region\|load_saved_image_crop_item" src --include=*.py | cut -c1-130`
- captured_output:
  ```text
  src/auditmanager/runs/text_window_input.py:87:def load_saved_text_windows(
  src/auditmanager/runs/text_window_input.py:165:__all__ = ["SavedTextWindowInput", "load_saved_text_windows"]
  src/auditmanager/runs/public.py:33:    load_saved_image_crop_item,
  src/auditmanager/runs/public.py:135:    "load_saved_image_crop_item",
  src/auditmanager/runs/recognised_region_input.py:188:def load_saved_recognised_region(
  src/auditmanager/runs/recognised_region_input.py:281:__all__ = ["SavedRecognisedRegionInput", "load_saved_recognised_region"]
  src/auditmanager/runs/geometry_crop_item_input.py:83:def load_saved_image_crop_item(
  src/auditmanager/runs/geometry_crop_item_input.py:167:__all__ = ["SavedImageCropItemInput", "load_saved_image_crop_item"]
  ```
- interpretation: definitions, `__all__` lists and one re-export in `src/auditmanager/runs/public.py`; no stage, executor or router calls any of the three.

### P-11 — the norm-verification operation refuses every call

- captured_at: 2026-10-27
- command: `sed -n 1151,1160p src/auditmanager/bootstrap/adapters.py | cut -c1-110`
- captured_output:
  ```text
      def get_norm_verification(self, *, run_id: str) -> models.NormVerificationReport:
          """Refuse until a reader proves the 0023 partition and the pinned set.

          An empty citation SELECT is not a certificate of zero. CITE will replace this
          seam after it checks stage success and every canonical/member partition.
          """
          raise DomainError(
              ErrorCode.DEPENDENCY_UNAVAILABLE,
              dependency="norm_verification_reader",
          )
  ```
- interpretation: `getRunNormVerification` answers a typed `dependency_unavailable` for every run.

### P-12 — the register census

- captured_at: 2026-10-27
- command: `python3 -I -c "import re;r={};[r.setdefault(m.group(3),bool(m.group(2))) for l in open('docs/program/DEBT_REGISTER.md',encoding='utf-8') for m in [re.match(r'^\| (\*\*)?(~~)?(D-\d+)',l)] if m];print(len(r),sum(1 for v in r.values() if not v))"`
- captured_output:
  ```text
  168 94
  ```
- interpretation: 168 table rows carry a debt id and 94 are not struck through. A row that is not struck through is not proved open: `D-206` says rows go stale, and the rows `D-204` to `D-235` are never struck even where their text says closed.

### P-13 — stale statements in the web and the contract

- captured_at: 2026-10-27
- command: `grep -n "Раздел документа сохраняется" web/src/widgets/dashboard/ui/sections-panel.tsx | cut -d: -f1; grep -n "True for exactly one section today" web/src/entities/project/model/section.ts | cut -d: -f1; grep -c "is applied to any uploaded document" contracts/api/v1/openapi.json`
- captured_output:
  ```text
  61
  93
  1
  ```
- interpretation: the dashboard panel's sentence about the upload form is at line 61, the claim that exactly one section is analysed is at line 93 of the section catalogue, and the contract text that the analysis «is applied to any uploaded document» occurs once.

### P-14 — what the integration branch has merged since the base

- captured_at: 2026-10-27
- command: `git log --oneline 87db74a9..integration/ar-close-1026 | grep "^[0-9a-f]* Merge"`
- captured_output:
  ```text
  a1d3f348 Merge agent/harden-01 into integration/ar-close-1026 (F-03, F-12, F-13, F-16, F-17 of EXPOSURE-REVIEW-02)
  f134a6c9 Merge agent/erase-wrap-01 into integration/ar-close-1026 (PROD-07 wrapper, PROD-08 key-ring runbook, log rotation and memory-limit mechanism)
  ```
- interpretation: two infrastructure lanes were merged after the base; the erase wrapper script under infra/deploy does not exist at the base (`ls` prints «No such file or directory»).

### P-15 — the container-free section tests

- captured_at: 2026-10-27
- command: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/text_profiles/test_section_profile_expectations.py tests/unit/analysis/test_text_profile_registry.py tests/integration/sections/test_section_recordings.py`
- captured_output:
  ```text
  149 passed in 1.53s
  ```
- interpretation: the status and version pins, the registry and the section replay pass on the base; this proves routing and replay over the АР corpus text, not any section's quality on its own text.

### P-16 — the host constraint at the time of the audit

- captured_at: 2026-10-27
- command: `df -h . | tail -1`
- captured_output:
  ```text
  /dev/vda3       119G  110G  2.2G  99% /
  ```
- interpretation: 2.2 GiB free against the 6144 MiB the gate preflight requires (`D-205`); the lanes of section 6 of the report that need a lane stack are marked so.

### P-17 — no table stores an approved sheet pairing, a comparison revision or a summary

- captured_at: 2026-10-27
- command: `grep -il "sheet_link\|comparison_revision\|approved_pair" db/migrations/versions/*.py`
- captured_output:
  ```text
  (no output; exit status 1)
  ```
- interpretation: no migration names a sheet link, a comparison revision or an approved pair, so the comparison of two versions stores nothing; the domain identifier `SheetLinkId` and the pure modules under `src/auditmanager/comparison/` exist without a table.

### P-18 — the files that name what the three larger lanes change

- captured_at: 2026-10-27
- command: `for p in "section_not_ar\|SECTION_AR\|STATE_SECTION_NOT_AR" "analysis_input_budget_exceeded\|input_budget_characters\|run_text_analysis\|PC01_STAGES" "compareDocumentVersions\|VersionComparisonService\|comparison.public"; do grep -rl "$p" src web/src web/tests tests contracts web/openapi 2>/dev/null | wc -l; done`
- captured_output:
  ```text
  24
  84
  30
  ```
- interpretation: 24 files name the АР-only guard or its reason code, 84 name the one-call budget, its refusal or the stage list, 30 name the version comparison; these are the "files counted" behind the sizes of the lanes in section 6 of the report. The lane's own change set is a subset plus new files, which is an estimate.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

No historical record is corrected. The report quotes `docs/program/W59-SECTION-PROFILES-01.md` and `docs/program/SECTION-REVIEW-LEDGER-01.md` as they stand.

## Publication authority

- development_target: none
- origin_main_authority: none

This lane pushes nothing, tags nothing and touches no remote ref; the integrator merges the branch.

## Allowed paths

- `docs/program/ROADMAP-GAP-2026-10-27.md`
- `docs/program/tasks/ROADMAP-GAP-2026-10-27.md`

## Forbidden hotspots

- contracts, `contracts/**`
- migration head, `db/migrations/**`
- root dependency and lock files, `web/FRONTEND_LOCK.json`
- composition root `src/auditmanager/bootstrap/**` and global styles
- every other path: `src/**`, `web/**`, `tests/**`, `fixtures/**`, `infra/**`, `scripts/**`, `tools/**`, and `docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`, `docs/program/OWNER_RULINGS_2026-09-17.md`

## Non-goals

- no code, test, fixture, prompt, profile, recording or migration is written or changed
- no register row is entered and no ruling is recorded (the report lists the choices and the stale statements for the integrator)
- no live run, no paid call, no container, no network, no push, no tag
- no recommendation to widen a section profile: the options are sized, not advised

## Deliverables

- `docs/program/ROADMAP-GAP-2026-10-27.md` (seven sections as the brief lists them)
- this task file with the captured premises above

## Required tests

- command: the governance check of this file, `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/ROADMAP-GAP-2026-10-27.md',encoding='utf-8').read())))"`
- expected: `[]`
- command: the documentation guards after committing, `PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`
- expected: all pass
- command: `git diff --check`
- expected: no output
- command: the token checker kept outside git (extracts the backticked tokens of both documents and checks each against the tree, `contracts/api/v1/openapi.json`, `docs/program/DEBT_REGISTER.md` and `docs/program/OWNER_RULINGS_2026-09-17.md`)
- expected: the line quoted at the end of the report, with zero missing

## Integration contract

The integrator can rely on, and only on: the status of each of the 59 wave items with the file, line, operation, migration or test named in its row; the bucket table of section 2.3 as the lane's reading of the record's own stated reasons; the 24-step workflow table with the guard quoted where a step is АР-only; the 27 items that need a human or a host; and the five lanes, each with the hotspot it needs. The integrator should not rely on any statement as «live»: none was run live. The lanes are proposals; each needs its own freeze, task file and `allowed_paths` from a fresh tip (`CODE-FIRST-TO-BETA.md` section 2.1).

## Failure/idempotency/security cases

- a backticked name in the report that does not exist on the tree is a defect; the checker reports it
- a statement whose evidence is only a document is marked «documented, not verified» in the report
- the report contains no credential, no host address beyond the public name already recorded in the register, and no client data

## Rollback / feature flag

Not applicable: two documents, no behaviour. Revert the branch `agent/roadmap-gap-2026-10-27`.

## Handoff

- changed files: `docs/program/ROADMAP-GAP-2026-10-27.md`, `docs/program/tasks/ROADMAP-GAP-2026-10-27.md`
- commands/results: the premises above; the governance check printed `[]`; the documentation guards and the token checker are quoted in the report and in the hand-back
- known limits: section 7 of the report; the bucket assignment of the 158 excluded items is the lane's reading
- integration notes: both files are new; merging them touches no other path; the `D-233` item 2 text («`1.6.0` in two documents») is already stale on this tree and `D-206` applies
