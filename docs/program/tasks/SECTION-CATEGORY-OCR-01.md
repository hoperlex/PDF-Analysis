# Task SECTION-CATEGORY-OCR-01 — AI TX EOM SS ITP report same-document omissions under the existing category `documentation`, and recognised text of text-less pages reaches the 14 section calls as marked context

task_id: SECTION-CATEGORY-OCR-01
status: completed in development candidate

## Outcome

(a) Five sections (`AI TX EOM SS ITP`, `profile_version` `1.3.0`) may report an item named on a scheme, plan or explication and absent from the specification or schedule as a `documentation` finding (`R-146ao`). The absence is anchored honestly: the model quotes the place that names the item and the heading of the range where it should appear and names the term and the page range; the stage then verifies, without the model, that the term does not occur in the saved text of that range, and publishes the pair only if it holds; otherwise the proposal is dropped and counted under a closed reason. Per-profile categories and response schema replace the two module constants (`text-profile/2`, a `categories` key); the other nine packages are byte-identical. (b) The recognised (OCR) text of a version's text-less pages reaches all 14 section calls as separately delimited, marked context in the user message, counted in the window decision; a quote found only in it confirms nothing (`R-146aq`). No contract change, no migration.

## Depends on

- `SECTION-WIDEN-G1-01`, `SECTION-WIDEN-G3-01` — completed; their decisions `AI-1`, `TX-1`, `EOM-4`, `ITP-5` (and `SS-5` for the scheme-to-specification pair) are the ones `R-146ao` supersedes.
- `SECTION-PROMPT-SENTENCE-GUARD-01`, `SECTION-PROMPT-TOKEN-GUARD-01`, `SECTION-RECORDINGS-01` — completed; the fragment table and its builder, the token guard and the recordings builder this lane extends and keeps green.
- `SECTION-CHUNKED-ANALYSIS-01` — completed; the window primitives whose arithmetic now counts the recognised blocks.
- `W55B-RECOGNISED-01` — completed; `prepared.recognised_text` and the version's `textless_pages`.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.8.0`, unchanged (`contracts/**` is not touched; the value `documentation` is already in `FindingCategory`)
- analysis/comparison/event contract: unchanged (`analysis.text_observations` keeps its shape; the `omission` object is a model-side claim consumed by the stage and not stored)
- migration head: `0036_cite_partition_v3`, unchanged (no migration; both finding CHECKs already allow the value)
- base commit: `05f4584d` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No route, screen, error code, migration or section is added or removed. The package format `text-profile/2` is a second accepted value of an existing key; the closed reason vocabulary of the omission check is a constant of `omission.py` and a pinned test, not a maintained set of the product.

## Captured premise evidence
- premise: the brief's premises hold (P-01 to P-09), with three differences that change a deliverable. (1) The brief says all 14 prompts and recordings change for part (b); the instruction to the model is put in the user message, next to the data, so the nine other packages, their recordings and the bundle hash stay byte-identical (P-07, P-08). (2) `documentation` is a whole token of each of the five sections' legacy `finding_categories.md`, so the token guard needs no allowlist line (P-09). (3) The legacy repository is not usable on this host (an empty skeleton, later absent), so the token guard's sourced part skips here; it was re-run over a hash-identical copy (P-09).

### P-01 — the base, the branch and the lane brief
- captured_at: 2026-10-27
- command: `git rev-parse --abbrev-ref HEAD; git rev-parse 05f4584d | cut -c1-12; git merge-base HEAD integration/ar-close-1026 | cut -c1-12; grep -n "SECTION-CATEGORY-OCR-01" docs/program/dispatch/PRODUCTION-WAVE-PW5.md | cut -c1-150`
- captured_output:
  ```text
  agent/section-category-ocr-01
  05f4584deeee
  05f4584deeee
  13:| SX | `SECTION-CATEGORY-OCR-01` | profile package code (`analysis/text/prompt.py`, `response.py`, `stage.py`, `profile_registry.py`), the 14 packa
  40:## 5. Lane SX — `SECTION-CATEGORY-OCR-01` (`R-146ao`, `R-146aq`)
  ```
- interpretation: the branch starts at the base the brief names; the lane is section 5 of the wave dispatch (the table row and the heading).

### P-02 — the two module constants that the brief replaces by per-profile categories, as they stood at the base
- captured_at: 2026-10-27
- command: `git grep -n "CATEGORIES\|RESPONSE_SCHEMA" 05f4584d -- src/auditmanager/analysis/text/prompt.py src/auditmanager/analysis/text/profile_registry.py src/auditmanager/analysis/text/response.py | cut -c10-170`
- captured_output:
  ```text
  src/auditmanager/analysis/text/profile_registry.py:53:    CATEGORIES,
  src/auditmanager/analysis/text/profile_registry.py:56:    RESPONSE_SCHEMA,
  src/auditmanager/analysis/text/profile_registry.py:316:        response_schema=RESPONSE_SCHEMA,
  src/auditmanager/analysis/text/profile_registry.py:326:        categories=CATEGORIES,
  src/auditmanager/analysis/text/prompt.py:41:CATEGORIES: Final[tuple[str, ...]] = ("internal_contradiction", "explicit_placeholder")
  src/auditmanager/analysis/text/prompt.py:113:RESPONSE_SCHEMA: Final[Mapping[str, Any]] = {
  src/auditmanager/analysis/text/prompt.py:121:                    "category": {"type": "string", "enum": list(CATEGORIES)},
  src/auditmanager/analysis/text/prompt.py:212:    response_schema=RESPONSE_SCHEMA,
  src/auditmanager/analysis/text/response.py:22:from auditmanager.analysis.text.prompt import CATEGORIES
  src/auditmanager/analysis/text/response.py:87:    if category not in CATEGORIES:
  ```
- interpretation: the closed pair is the constant `CATEGORIES` (prompt.py:41), read by the parser (response.py:87) and handed to every profile by the registry (profile_registry.py:326), with the one `RESPONSE_SCHEMA` (profile_registry.py:316). `adapter.py`, `stage.py` and `artifact.py` do not name either constant.

### P-03 — the stage validation already checks the observation's category against the profile's declared categories
- captured_at: 2026-10-27
- command: `git show 05f4584d:src/auditmanager/analysis/text/artifact.py | sed -n 84,88p`
- captured_output:
  ```text
          if observation.category not in profile.categories:
              raise _malformed(
                  "category_not_declared",
                  "an observation carries a category the analysis profile does not declare",
              )
  ```
- interpretation: `build_text_observations` refuses an observation whose category the profile does not declare; with the profile's own list this check becomes the per-profile one, unchanged.

### P-04 — the omission refusals this lane supersedes (decision X of lanes G1 and G3) and the reason in the first of them
- captured_at: 2026-10-27
- command: `grep -nE "^\| (AI-1|TX-1|EOM-4|SS-5|ITP-5) \|" docs/program/SECTION-WIDEN-G1-01.md docs/program/SECTION-WIDEN-G3-01.md | cut -c1-260`
- captured_output:
  ```text
  docs/program/SECTION-WIDEN-G1-01.md:24:| AI-1 | AI | An item on a plan or in the explication that the finishing schedule does not list, and the reverse (omission pair of cross-section question 4; excluded item 5, its required-presence form) | **X** | (a) The e
  docs/program/SECTION-WIDEN-G1-01.md:32:| TX-1 | TX | A position in the explication with no specification row, and the reverse (question 4) | **X** | The reasons (a), (b) and (c) of AI-1; and position numbers repeat across rooms and enterprises (`SECTION-TX-FUL
  docs/program/SECTION-WIDEN-G3-01.md:29:| EOM-4 | EOM | A panel or apparatus named on a scheme and absent from the specification (excluded item 7; record q3) | **X** | The reasons (a) to (d) above. EOM's own: panel and group designations repeat across buildings
  docs/program/SECTION-WIDEN-G3-01.md:34:| SS-5 | SS | A list (signals shown at the dispatch point, composition of an access point) that is shorter in one place than in another (record q3; gap cell) | **X** | The reasons (a) to (d) above. SS's own: a list in the
  docs/program/SECTION-WIDEN-G3-01.md:39:| ITP-5 | ITP | A scheme item with no specification row, and the reverse (excluded item 13) | **X** | The reasons (a) to (d) above. ITP's own: valves, filters and sensors are designated per circuit and repeat on the princ
  ```
- interpretation: five rows, all X. AI-1 names the reason that matters: an absence has no quote, so the grounding gate would publish a non-existence claim as grounded. SS-5 is about a list that is merely shorter in one place (a different shape from the scheme-to-specification pair).

### P-05 — the value `documentation` is already in the contract and both CHECKs (no contract change, no migration)
- captured_at: 2026-10-27
- command: `grep -n '"documentation"' contracts/api/v1/openapi.json db/migrations/versions/20261015_0022_findings_v2.py db/migrations/versions/20261016_0023_norm_citations.py`
- captured_output:
  ```text
  contracts/api/v1/openapi.json:7990:          "documentation",
  db/migrations/versions/20261015_0022_findings_v2.py:23:_NEW_CATEGORIES = (*_OLD_CATEGORIES, "dimensions", "layout", "facade", "roof", "documentation")
  db/migrations/versions/20261016_0023_norm_citations.py:45:    "facade", "roof", "documentation",
  ```
- interpretation: the contract's FindingCategory enum and the category lists of migrations 0022 and 0023 (which replace `ck_finding_category` and `ck_finding_observation_category`) carry the value; `documentation` is not one of the five normative values that demand citations.

### P-06 — a quote is resolved against the text layer only, and the gate re-verifies against the same layer
- captured_at: 2026-10-27
- command: `grep -nE "text_layer.slice|page.text.find|QUOTE_IN_RECOGNISED_TEXT" src/auditmanager/findings/grounding.py src/auditmanager/analysis/text/anchors.py`
- captured_output:
  ```text
  src/auditmanager/findings/grounding.py:57:    QUOTE_IN_RECOGNISED_TEXT = "quote_in_recognised_text"
  src/auditmanager/findings/grounding.py:195:    if text_layer.slice(item.char_start, item.char_end) != quote:
  src/auditmanager/analysis/text/anchors.py:130:        offset_in_page = page.text.find(candidate)
  src/auditmanager/analysis/text/anchors.py:138:        if text_layer.slice(char_start, char_end) != candidate:
  ```
- interpretation: `resolve_anchor` finds the quote in `page.text` of the text layer (anchors.py:130) and the gate compares the slice of the same layer (grounding.py:195). Recognised text is in neither, so a quote found only there is unresolved without any change to `grounding.py`. `QUOTE_IN_RECOGNISED_TEXT` is in the vocabulary and is not emitted by this gate.

### P-07 — what the section run path holds and does not read of the recognised text, at the base
- captured_at: 2026-10-27
- command: `git grep -n "outputs.absorb(result)\|text_character_count=version.text_character_count\|ROLE_RECOGNISED_TEXT\|select_context" 05f4584d -- src/auditmanager/runs/executor.py src/auditmanager/analysis/profiles/ar_shared/recognised_context.py | cut -c10-170`
- captured_output:
  ```text
  src/auditmanager/analysis/profiles/ar_shared/recognised_context.py:45:def select_context(
  src/auditmanager/runs/executor.py:1011:        outputs.absorb(result)
  src/auditmanager/runs/executor.py:1107:                text_character_count=version.text_character_count,
  ```
- interpretation: the executor absorbs every stage's artifacts into `outputs.refs` (so the run's `prepared.recognised_text` reference is in hand after `source_preparation`) and passes `version.text_character_count` to the text stage; it never names `ROLE_RECOGNISED_TEXT`. The selector `select_context` exists (AR v2's uncitable context) and selects by the version's `textless_pages`.

### P-08 — the budget arithmetic: the one-call figure, the framing allowance and the fixed term it subtracts
- captured_at: 2026-10-27
- command: `python3 -I -c "import sys;sys.path.insert(0,'src');from auditmanager.analysis.text.budget import input_budget_characters as b,PAGE_FRAMING_ALLOWANCE_CHARACTERS as f,_fixed_prompt_characters as x;print(b('claude-opus-5',1.0),f,x())"`
- captured_output:
  ```text
  152361 12000 3639
  ```
- interpretation: 152,361 characters per call at the primary model and USD 1.00; the banners of 500 pages are allowed 12,000; the fixed term is v1's prompt plus v1's schema (3,639), not the section's own prompt (5,361 to 7,219 characters longer than v1's for the five sections after this lane). The recognised blocks are in none of these, which is why they are counted where the decision is made.

### P-09 — the legacy source of the five sections, for the token guard: the 25 pinned files equal a copy found on this host, and `documentation` is a whole token of each section's `finding_categories.md`
- captured_at: 2026-10-27
- command: `python3 -I -c "import json,hashlib;b='/home/ciuser/lane-baseline/src/';n=ok=0;h=[(n:=n+1,ok:=ok+(hashlib.sha256(open(b+f['path'],'rb').read()).hexdigest()==f['sha256'])) for c in ('ai','tx','eom','ss','itp') for f in json.load(open('src/auditmanager/analysis/text/profiles/'+c+'/profile.json',encoding='utf-8'))['source']['files']];print('pinned files',n,'equal to the copy',ok)"; grep -rlw documentation /home/ciuser/lane-baseline/src/prompts/disciplines/AI /home/ciuser/lane-baseline/src/prompts/disciplines/TX /home/ciuser/lane-baseline/src/prompts/disciplines/EOM /home/ciuser/lane-baseline/src/prompts/disciplines/SS /home/ciuser/lane-baseline/src/prompts/disciplines/ITP | sed 's#.*/disciplines/##'`
- captured_output:
  ```text
  pinned files 25 equal to the copy 25
  AI/finding_categories.md
  TX/finding_categories.md
  EOM/finding_categories.md
  SS/finding_categories.md
  ITP/finding_categories.md
  ```
- interpretation: the legacy repository at `/root/projects/PDF-proverka` was an empty `git init` skeleton while this lane ran (later absent), so the token guard's sourced part skips on this host. A copy under another path has the 25 pinned files byte for byte, and in each of the five sections the new category name is a whole token of `finding_categories.md` (the legacy category for «drawings against the specification»): no allowlist line is needed, and the guard run with its own functions over that copy finds no unexplained token in any of the 14 prompts.

### P-10 — the baseline of the container-free battery before this lane's first edit
- captured_at: 2026-10-27
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis tests/integration/sections tests/contract/analysis_packages tests/integration/analysis_text`
- captured_output:
  ```text
  1244 passed, 73 skipped in 28.70s
  ```
- interpretation: the figure the final battery is compared with (the 73 skips are the token guard's sourced part and the legacy-commit hash check, both needing the legacy repository). The variable only makes the skip explicit; without it the legacy check failed on the empty skeleton at the time.


## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/text/**`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/runs/section_recognised_input.py`
- `src/auditmanager/runs/executor.py`
- `fixtures/recorded/sections/**`
- `fixtures/recorded/sections_widen/**`
- `tests/unit/analysis/**`
- `tests/integration/sections/**`
- `tests/integration/analysis_text/**`
- `tests/contract/analysis_packages/**`
- `docs/program/SECTION-CATEGORY-OCR-01.md`
- `docs/program/tasks/SECTION-CATEGORY-OCR-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, `web/**`, `infra/**`, `src/auditmanager/findings/grounding.py` (the design note proves it is not needed), the nine other section packages (`ps pos kj km ov vk pt gp pb`) and their recordings, optimisation, comparison, access, `bootstrap/**`, `api/**`, root dependency and lock files, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the ledger and the widen reports, `P02_LOCK.json`.

## Non-goals

- No change of the contract's `Evidence` (it stays quote-only), of `analysis.text_observations`, of the finding CHECKs or of any web or XLSX label.
- No new category; no severity; no norm; no calculation. The nine other sections do not change. The reverse omission (an item in the schedule that is absent from the plans) and a list that is merely shorter in one place (`SS-5`) are not added.
- No model call, no push, no tag, no container command; the lane stack is used through a copy of the integrator's `.env` and private databases only.
- No claim that any prompt sentence, specimen or decision was reviewed by anyone (`A-5`, `A-7`); no measurement of how a model answers.
- No change of the start-time refusal `analysis_input_budget_exceeded` (`runs/commands.py`, outside the allowed paths).

## Deliverables

- `src/auditmanager/analysis/text/omission.py` (the check), `recognised_input.py` (the block), and the edits of `prompt.py`, `response.py`, `profile_registry.py`, `adapter.py`, `stage.py`, `windowed.py`, `windows.py`, `chunk_preflight.py`.
- `src/auditmanager/runs/section_recognised_input.py` (the loader) and the call site in `src/auditmanager/runs/executor.py`; additive exports in `src/auditmanager/analysis/public.py`.
- The five packages (`profile.json` `text-profile/2` with `categories`, `profile_version` `1.3.0`, one prompt paragraph each), the five rebuilt recordings, the expectations lines, the fourth source of the fragment table (built by its builder), the omission specimens and their builder.
- Tests: `test_omission_check.py` (45), `test_recognised_input.py` (13), `test_recognised_context.py` (11), `test_section_recognised_input.py` (12), `test_section_omission_specimens.py` (45), `test_section_omission_over_db.py` (1, skipped without a stack), and the edits listed in the report under «Modified tests».
- Report `docs/program/SECTION-CATEGORY-OCR-01.md` (design, result, files, modified tests, mutation table, counts, integration notes, limits).

## Required tests

- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis tests/integration/sections tests/integration/analysis_text tests/contract/analysis_packages`
- expected: 1406 passed, 73 skipped (base 1244 passed, 73 skipped; +162 cases).
- command: the same with `DATABASE_URL` naming a private, migrated database, `tests/integration/runs` — expected 944 passed; `python3 fixtures/recorded/sections/build_fixtures.py --check` — `fixtures match`; `python3 -I tests/unit/analysis/text_profiles/build_section_prompt_fragments.py` — `fragments match`; `python3 -I fixtures/recorded/sections_widen/omission/build_specimens.py` — `specimens match`.
- mutations: one per guard (the report's table, 21 rows): the absence check, the wrong category, an OCR quote, a recognised block for a page with text, the notice, the window arithmetic, each reason of the check, the JSON quoting, the prompt fragments.
- The governance one-liner on this file — expected `[]`; `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` (on the committed tree) and `git diff --check`.

## Integration contract

The integrator can rely on: no contract, migration, web or infra file is touched; the nine other packages, recordings and the bundle hash are byte-identical; a version without a text-less page sends exactly the request it sent before (same body, same `request_sha256`, same recordings; its stage metrics gain nothing); `startRun` is unchanged. The one edit in `runs/executor.py` is the call site of the loader (`_run_text_analysis_stage` gains `textless_pages`; the window decision gains the blocks' characters). A new stage metric set appears only where it means something: `omissions_*` for the five profiles, `recognised_pages` and `recognised_characters` for a call that carried a block. The five sections are `text-profile/2`; the registry accepts `/1` and `/2` and refuses any other format. The wave brief puts this lane after `SMALL-HARDENING-02`; the two share no file. The start-time budget refusal compares the text-layer count alone; a version that its scans push over the windowed limit is refused by the plan (`window_plan_over_limit`) before any call, with both figures in the message; making `startRun` add `recognised_character_count` is a follow-up in `runs/commands.py`.

## Failure/idempotency/security cases

A proposal that fails the absence check is not written and is counted under its reason; nothing is retried or repaired. A `documentation` reply from a profile that does not declare it, without a well-formed claim, or with the claim on another category is malformed. Recognised text is rendered as a JSON string literal, so hostile OCR (a forged banner, a closing marker, an instruction) cannot open or close a block; the notice tells the model not to follow it; a quote found only in it is unresolved. A text-less page with no recognised artifact, or an artifact that disagrees with the version, fails the stage explicitly before any call. Re-invoking a windowed stage recovers finished windows by a key that now binds the blocks through the request checksum.

## Rollback / feature flag

Revert the commits: the nine packages never changed, the five revert to `text-profile/1`, `1.1.0`/`1.2.0` and their old recordings, and the stage reads no recognised page when the executor passes none. No feature flag; the recognised context is off for any version without text-less pages and the category is off for any profile whose package does not declare it.

## Handoff

- changed files: see the report («Files»)
- commands/results: see the report («Commands and counts»)
- known limits: nothing ran against a model; the check is a literal term in the saved text layer, not a proof that an item is absent from the project; the budget's fixed term still uses v1's prompt length (report «Limits»)
- integration notes: see the report («Integration notes»)
