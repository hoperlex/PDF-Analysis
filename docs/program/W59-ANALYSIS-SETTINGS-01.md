# W59-ANALYSIS-SETTINGS-01 — section profiles proven by recorded runs and listed in «Настройки анализа»

**Base:** `121ef2ce` (task freeze on `origin/dev` `c4cbc026`), branch
`agent/w59-analysis-settings-01`, isolated worktree `w59-analysis-settings`, lane PostgreSQL
57520 / MinIO 61120–61121 (`auditmanager-w59-analysis-settings`). **Status:** development
candidate under `R-135`; no full gate, no live journey, no provider call, no push, merge into
another branch or tag.

## Phase A — section-profile runs in recorded mode

### Result

A version classified to АИ (`AI`), ПЗ (`PS`), ПОС (`POS`) or ТХ (`TX`) now runs end to end in
`recorded` mode with its own profile: the run pins the section's `analysis_profile_id` and
`prompt_bundle_id`, `text_analysis` sends that profile's prompt bundle, the recorded reply is
parsed by the v1 stage, the gate grounds it and the findings are published. Before this,
`W59-SECTION-SEAL-01` recorded the risk that only AR had a recording, so every
section-routed recorded run failed at `text_analysis`.

### How the recorded adapter finds a section recording

Recordings were, and still are, keyed by `request_sha256`: the checksum of the exact request
body, which includes the profile's system prompt. A section profile therefore already has
its own key, different from AR's and from every other section's. What the adapter lacked
was a place to look: `RecordedAdapter()` read `fixtures/recorded/text_analysis/` only, and
the phase-A paths do not include the composition root. The minimal change is in
`src/auditmanager/analysis/text/recorded.py`:

- `RecordedAdapter()` **without** a directory — what the composition root serves in recorded
  mode and what `python -m auditmanager.analysis.text` uses — searches the canonical
  directory and then each sub-directory of `fixtures/recorded/sections/` in name order
  (plain files and `_`/`.` names skipped). `RecordedAdapter(directory)` reads that directory
  alone, exactly as before, so every variant and every existing suite is unchanged.
- A key present in two searched directories is refused as `recording_ambiguous`
  (`analysis_input_invalid`, not retryable) instead of being answered by directory order.
  The other five reasons are untouched; a missing key is still `recording_missing`.
- `recording_dir` still names the canonical directory; the new `recording_dirs` names
  everything searched.
- `recording_document` takes an optional `origin` mapping, written only when given and
  refused if it names `provider_mode` or `mode`. Without it the document has the same eight
  keys as before, so the AR builder's `--check` still reports `fixtures match`.

AR is byte-identical: its key exists only in the canonical directory, so the same file
answers with the same response (`test_the_served_adapter_answers_ar_exactly_as_the_canonical_directory`
compares the two `ModelResponse`s), and the AR routed run still reproduces the corpus run.

### The synthetic recordings

`fixtures/recorded/sections/<code_lower>/<request_sha256>.json`, one per section, built by
`fixtures/recorded/sections/build_fixtures.py` (`--check` reports drift and stale files):

| Section | Key | Observations |
|---|---|---|
| АИ `AI` | `a03cfde3…04bf8f` | 1 — window-filling placeholder |
| ПЗ `PS` | `5dad5c5f…2411f3` | 1 — fire-resistance contradiction |
| ПОС `POS` | `9fd79951…f8ea15` | 1 — evacuation-exit contradiction |
| ТХ `TX` | `e1dcf36b…99c6df` | 2 — fire resistance + placeholder |

Each request is the section profile's bundle over the committed AR corpus text layer
(`fixtures/recorded/text_analysis/inputs/ar_baseline_text_layer.json`), which is what the
pinned extractor produces from the PDF the run suites seed. The replies are **authored by
hand**: each file has `origin.kind: synthetic`, a statement that no model produced the reply
and that it is not field evidence for the profile's review, the task, section, both
identities, the bundle's `content_sha256` and the profile status; every `finding_text` opens
with «Синтетический ответ (<раздел>), не результат вызова модели»; usage and latency are
authored. No file carries a provider mode; the adapter's class constant stamps `recorded`.
`fixtures/recorded/sections/README.md` says all of this beside the files.

### Registry

`RegisteredTextProfile` gains `source: TextProfileSource | None` (default `None`): the
package's validated `source` block — repository, commit and `(path, sha256)` files — kept
instead of discarded after validation. Builtin AR has none (its prompt was written in this
repository). Phase B lists it.

### Tests

- `tests/integration/runs/test_w59_section_profile_recorded.py` (lane containers, 7 cases):
  for each of AI, PS, POS, TX — classify (stage `P`) → `start_audit_run` with the registry's
  table → the run pins the section's pair → `execute_run` with `RecordedAdapter()` and the
  registry's resolver → `published`, all four PC-01 stages `succeeded`, the persisted
  `text_analysis` metrics carry the section's `prompt_bundle_sha256`,
  `analysis_profile_sha256` and the recording's key, and the published findings are exactly
  the recording's observations under the section's pair in `recorded` mode; `PB` → refused
  (`required_norm_unavailable`, `analysis_profile`), unclassified → refused
  (`version_classification`), no run either way; a PS run over the AI directory alone ends
  `failed` with `recording_missing`, and over the AI file renamed to the PS key with
  `recording_key_mismatch`, with no finding published.
- `tests/integration/sections/test_section_recordings.py` (container-free, 16 cases): one
  synthetic recording per section keyed to its own request; the five requests (AR + four)
  pairwise distinct; builder `--check` clean; the served adapter answers AR as the
  canonical directory does and answers each section, the canonical directory alone does
  not; KJ (no recording) fails `recording_missing`; the AI recording never answers the PS
  request; one key in two searched directories → `recording_ambiguous`; `origin` cannot carry
  a mode; the registry keeps every package's `source`.

### Checks run (phase A)

Interpreter `PY=/root/projects/PDF-Analysis/.local/worktrees/w55b-main-candidate/.venv/bin/python`,
`$PY -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider`, lane containers up
via `make up` / `make migrate` (head `0024_version_classification`).

| Command (paths) | Result |
|---|---|
| `tests/integration/runs/test_w59_routed_execution.py` (before any change) | 3 passed, exit 0 |
| `tests/integration/runs/test_w59_section_profile_recorded.py` | 7 passed, exit 0 |
| `tests/integration/sections` | 79 passed, exit 0 |
| `tests/integration/sections tests/integration/runs/test_w59_section_profile_recorded.py tests/integration/runs/test_w59_routed_execution.py tests/integration/runs/test_full_chain.py tests/integration/runs/test_terminal_detail_says_which_dependency.py tests/integration/analysis_text tests/unit/analysis` | 423 passed, exit 0 |
| `tests/contract/architecture tests/contract/domain_p02 tests/contract/provider tests/contract/analysis_packages` | 202 passed, exit 0 |
| `build_fixtures.py --check` for `text_analysis` and `sections` | `fixtures match` ×2 |
| `git diff --check` | clean |

Mutation probes on commit `439580da` (each applied in-tree, run against the two new modules,
then restored with `git checkout`):

| Mutation | Result |
|---|---|
| served adapter reads the canonical directory only | 10 failed |
| ambiguity refusal removed (first match wins) | 1 failed |
| an explicit directory also searches the section directories | 8 failed |
| registry drops the `source` block | 1 failed |

## Phase B — «Настройки анализа»

Pending the integrator's hand-over of the contract slot.

## Risks and limits

- The section recordings answer **one document**: the AR corpus PDF the suites seed. Any
  other document classified to these sections still fails `recording_missing` in recorded
  mode — explicitly, as before. Nine sections with packages (EOM, GP, ITP, KJ, KM, OV, PT,
  SS, VK) still have no recording.
- The replies are synthetic. Passing proves routing, parsing, grounding and publication,
  not the quality of any profile. They never count as evidence for a profile becoming
  `reviewed`.
- `infra/deploy/Dockerfile.api` copies all of `fixtures/recorded/`, so the image carries the
  section recordings; its comment still names only `text_analysis/**` (outside this task's
  paths).
- Editing a section's `system_prompt.md` orphans its recording; the builder's `--check` and
  `test_the_builder_reports_no_drift` catch it.

## Hotspot proof (phase A)

Changed: `src/auditmanager/analysis/text/recorded.py`,
`src/auditmanager/analysis/text/profile_registry.py`, `fixtures/recorded/sections/**`,
`tests/integration/runs/test_w59_section_profile_recorded.py`,
`tests/integration/sections/test_section_recordings.py` and this report — all within
phase A's paths. Not touched: `contracts/**`, migrations, dependency files, the composition
root, `web/**`, `src/auditmanager/analysis/text/profiles/**`, `CURRENT_STATE.md`, refs, tags.
