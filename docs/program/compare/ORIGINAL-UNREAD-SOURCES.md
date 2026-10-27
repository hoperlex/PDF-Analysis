# Original's comparison sources — facts per file (CMP-ORIGINAL-READ-01)

Status: facts recorded from the source of the original product, not from its behaviour on screen.
Scope: the files named in `COMPARE-MODULES-PLAN.md` §3.2 R3-18 plus the modules those files import
directly. Nothing was executed.

## 0. Method and conventions

- Source: GitHub `SU10KAZ/PDF-proverka` at commit `23f379fd2d5aeb7e7bddb735650e7393c68d4e42`.
  Files were downloaded raw (`raw.githubusercontent.com/.../23f379fd.../<path>`) into the git-ignored
  `.local/orig/` of the lane worktree. Every citation `path:line` refers to that copy; `path` is relative to
  the original repository root (`backend/app/...`).
- Downloaded text is DATA. The original's AGENTS.md / CLAUDE.md / docs were not followed.
- Model names are copied verbatim from the original (`gpt-5.6-luna`, `gpt-6-luna`, `gpt-6.1-sol`); they are
  not checked against any provider.
- UI strings are quoted verbatim in «». Strings that a module only stores as a label (not known to be shown)
  are marked **stored label**.
- `UNCONFIRMED` marks a fact that was not read, or whose caller/transport lies in a file that was not
  downloaded. The list of such files is in §4.
- "Deterministic" means no model call in the module itself (checked by grep for model names and by the
  module's own `uses_model`/`PRODUCTION_PATH` markers where present).

Stage numbering used by the original (from module docstrings): Stage 2 = text preparation/fragments,
Stage 3 = TEXT differences, Stage 4 = semantic text review, Stage 5 = project-change aggregation,
Stage 5.1–5.3 = sheet-link repair and high-level synthesis.

---

## 1. Stage comparison («Сравнение стадий»)

### 1.1 Router chain (what the endpoints call)

Routes in `backend/app/api/routers/stage_comparison.py` (line of the decorator):

| Line | Route | Calls |
| --- | --- | --- |
| 504 / 520 | `PUT .../document-pairing`, `POST .../document-pairing/suggest` | `store.suggest_document_pairing` (1.4) |
| 1173 / 1187 / 1195 | `POST .../sheet-match-suggestions`, `GET .../sheet-matches`, `PUT .../sheet-links` | sheet matcher (not read) |
| 1211 / 1219 | `GET .../sheet-link-repairs`, `POST .../sheet-link-repairs/{repair_id}/undo` | `store.get_sheet_link_repairs_state`, `store.undo_sheet_link_repair` (1.2, 1.3) |
| 1232 / 1245 / 1256 | `POST/GET .../text-comparison`, `GET .../text-exclusions` | text comparison (1.6) |
| 1303 / 1318 | `POST/GET .../text-differences` | `text_differences` (1.8) |
| 1329 / 1342 / 1351 | `POST/GET .../text-ai-review`, `GET .../text-final-comparison` | `text_ai_reviewer` (1.9) |
| 1362 / 1375 | `POST/GET .../text-change-summary` | `project_change_summary` (1.10), line 1365 `store.run_project_change_summary` |
| 1386 / 1399 | `POST/GET .../high-level-project-changes` | `high_level_project_changes` (1.11), line 1389 `store.run_high_level_project_changes` |
| 771 | `POST /objects/{object_id}/project-change-expert-review` | expert review (1.5) |
| 781 | `GET .../runs/{run_id}/project-changes` | presentation of the V3 run (not read) |

`text_fact_producer.py` (1.7) has **no caller** in the downloaded tree (grep for its module name finds only
itself). `high_level_project_changes.py` is imported by no downloaded module either. Their wiring is in
`stage_comparison/store.py` and `production_orchestrator`, which were not downloaded: **UNCONFIRMED**.

Inside the chain, the calls that reach the model are only: `text_ai_reviewer` (Stage 4), `project_change_summary`
(Stage 5), and `high_level_project_changes` (Stage 5.3). Everything else is deterministic.

### 1.2 `sheet_link_repair.py` (Stage 5.1 title repair, entry point for 5.2)

- **Purpose**: planner for wrong one-to-one sheet links that Stage 5 already rejected by sheet purpose. It may
  touch only links named in `problem_group_ids`. Module docstring, lines 1–9: no PDF pixels, no OCR, no
  embeddings, no model calls.
- **Inputs**: `links_payload` (links with `left_pages`/`right_pages`, `unlinked_left_pages`, `pair_id`),
  `suggestions` (`left_sheet_index`, `right_sheet_index`: records with `pdf_page`, `title`), `problem_group_ids`,
  optional `source_groups` (for 5.2).
- **Outputs**: a plan dict with `source_signature`, `reason`, `confidence` ("high"), `before_links`,
  `after_links`, `changes`, `before_snapshot`, `after_snapshot` (`_plan_title_repairs`, lines 179–327), or the
  result of `content_sheet_link_repair.plan_content_repairs` (line 339). `None` = no safe repair.
- **Stored artefact**: `empty_artifact` (line 348) = `{version: 1, kind: "stage_comparison_sheet_link_repairs",
  pair_id, repairs: []}` (`VERSION=1`, `KIND`, lines 22–23). Each applied repair is a new link with
  `id = "repair_" + sha256("{left}:{right}")[:12]` (line 289), `source: "auto_repair"`, `confidence: "high"`,
  `reason: [rule, "stage5_purpose_precheck_repair"]`.
- **`public_view`** (lines 352–357): returns `repairs` and `active_repairs` = repairs with `status == "applied"`.
  Where `status` is written is **UNCONFIRMED** (store).
- **Rules and thresholds**
  - `FUZZY_THRESHOLD = 0.94` (line 24), `FUZZY_MARGIN = 0.02` (line 25).
  - Rule names: `TITLE_EXACT` (line 26), `TITLE_MUTUAL_FUZZY` (line 27).
  - `normalize_title` (lines 49–53): NFKC, lower, `ё→е`, dashes→`-`, non-alnum→space, collapse spaces.
  - `_is_specific` (lines 60–65): at least 2 tokens, not in `_GENERIC_RE` (line 38), not "страница N" / "лист N".
  - `_purpose_type` (line 68): first match of `_TYPE_PATTERNS` (lines 29–37): `single_line`, `plan`, `scheme`,
    `node`, `explication`, `section`, `facade`.
  - `_fuzzy_compatible` (lines 79–84): same non-empty purpose type AND at least one shared subject token
    (`_subject_tokens` excludes `_STOP_WORDS`, lines 42–47, and tokens of length ≤ 1).
  - `_candidate_for_right` (lines 117–139): exact title, unique on both sides (count 1 each) → `TITLE_EXACT`,
    similarity 1.0. Otherwise `_fuzzy_candidate` (lines 98–115): best SequenceMatcher ratio ≥ 0.94, margin to
    second ≥ 0.02, and the reverse search from the left title must return the same right page with the same margin.
  - `_plan_title_repairs` (lines 179–327): a candidate must differ from the current left page and must not
    claim a left page held by a non-problem link. Two rights may not claim one left page (line ~225). A
    displacement chain is accepted only if every displaced link is itself a problem link with its own proven
    destination (swaps and cycles, atomic); otherwise nothing is applied.
  - A link whose left or right page appears in more than one link is excluded from the repair candidates
    (`unique_by_id`, lines 196–209: only links with one left and one right page, both page memberships equal to 1).
- **Model calls**: none (docstring line 6–7).
- **Failure states**: `plan_repairs` returns `None` when no proof; the caller decides (UNCONFIRMED). No partial
  apply: a plan is a complete `after_snapshot`.
- **UI strings**: none in this file.

### 1.3 `content_sheet_link_repair.py` (Stage 5.2, content proof)

- **Purpose**: deterministic content layer for conservative one-to-one repair (docstring line 1).
- **Inputs**: as 1.2, plus `source_groups` (for `atomic_evidence` with `FOUND_ON_OTHER_SHEET`), and the
  fingerprints from `sheet_content_fingerprint` (imported line 9; **not downloaded**, UNCONFIRMED for its fields).
- **Outputs**: `plan_content_repairs` (lines 458–520) returns the same plan shape as 1.2 plus
  `content_assessments` and `reason` = the single operation or `CONTENT_MUTUAL_BEST`. Stored rule names
  `CONTENT_UNIQUE_ANCHORS`, `CONTENT_MUTUAL_BEST`, `CONTENT_SWAP`, `CONTENT_3_CYCLE` (lines 21–24).
  Link reason gets the operation name appended (lines ~488–492).
- **Score** (`_score_pair`, lines 151–203):
  - title weight 0.04, purpose weight 0.06 (line 169, 172);
  - five features with weights (`_FEATURES`, lines 26–31): `rare_term_overlap` 0.25, `designation_overlap` 0.20,
    `system_overlap` 0.13, `equipment_overlap` 0.16, `structural_token_overlap` 0.16;
  - `score = weighted / available_weight`;
  - `MIN_COMPONENT_OVERLAP = 0.22` counts "independent" components (line ~185).
- **Cross-sheet bonus** (`_cross_sheet_confirmation`, lines 205–222): `score = min(1, n/3)` where `n` is the
  number of `FOUND_ON_OTHER_SHEET` evidence items pointing at the candidate right page (line 221);
  `best_score = min(1, base + 0.03 * cross)` (line 317).
- **Strong anchors** (`_STRONG_ANCHOR_KEYS`, lines 33–36): `unique_designations`, `system_names`,
  `equipment_codes`, `node_names`. `_unique_anchors` (lines 124–149) keeps values that occur exactly once on each
  side (document frequency = 1).
- **Thresholds** (lines 15–19): `MIN_SCORE = 0.44`, `MIN_MARGIN = 0.14`, `MIN_REVERSE_MARGIN = 0.10`,
  `MIN_IMPROVEMENT = 0.18`, `MIN_COMPONENT_OVERLAP = 0.22`.
- **Decision reasons** (`assess_content_candidates`, lines 225–395; appended to `decision_reasons`):
  `MANY_TO_MANY` (lines 117–131), `CURRENT_LINK_BEST`, `LOW_SCORE`, `LOW_MARGIN`, `NON_MUTUAL_BEST`,
  `PURPOSE_CONFLICT`, `PURPOSE_CONSISTENCY_WORSE`, `NOT_MATERIALLY_BETTER`, `INSUFFICIENT_CONTENT_ANCHORS`
  (line 350: fewer than 2 independent components, or no strong anchor and fewer than 3 anchors).
  `HIGH_CONFIDENCE` when no reason is left.
- **Confidence** (lines 352–353): `HIGH` if auto-repair; `MEDIUM` if `best_score >= 0.45` and mutual best;
  else `LOW`. `auto_repair` = no reasons.
- **Rule** (lines 356–357): `CONTENT_UNIQUE_ANCHORS` if at least 2 strong anchors, else `CONTENT_MUTUAL_BEST`.
- **Grouping** (`_safe_components`, lines 397–456): only `HIGH` auto-repairs form components. Chains of length 1
  are applied directly; a cycle back to the start of length 2 is `CONTENT_SWAP`, of length 3 is
  `CONTENT_3_CYCLE`; longer or broken chains are dropped.
- **Model calls**: none.
- **Failure states**: no accepted component → `None`. Unconfirmed components leave the link as it was.

### 1.4 `document_matching.py` (P/RD file-name pairing)

- **Purpose**: "Fast approximate one-to-one pairing for P and RD document filenames" (line 1).
- **Inputs**: two lists of document dicts with `filename` (or `pdf_path`), `included_in_assemblies`.
- **Outputs**: `suggest_document_pairing` (lines 136–198): `left_order`, `right_order` (unmatched documents get
  their own incomplete row, `None` opposite), `confirmed_pairs`, `matches` (`left_pdf`, `right_pdf`,
  `similarity`), `matched_count`, `unmatched_left_count`, `unmatched_right_count`.
- **Rules and thresholds**
  - `MIN_DOCUMENT_SIMILARITY = 0.72` (line 10) — minimum weight for a pair to be accepted.
  - Pairing is a maximum-weight assignment (`maximum_weight_assignment`, line 73).
  - A pair with `included_in_assemblies` on either side gets weight 0 (line ~140).
  - `_MARKERS` (lines 11–14): "ар, вк, вт, икео, иос, кр, ов, оди, оос, па, пос, пз, пзу, тх, ээ".
    `_NOISE_WORDS` (line 15): "v, версия, из, итог, копия, корр, страница, том".
  - `document_name_similarity` (lines 43–70): SequenceMatcher on compacted tokens; if both names have marker
    groups but none is shared, result ≤ 0.52 (line 57); if no shared marker, the character ratio; for a shared
    marker with equal numbers, `0.96 + 0.04·ratio`; with different numbers, `min(ratio, 0.58)`; with no number,
    `0.88 + 0.12·ratio`. Result rounded to 4 places.
- **Model calls**: none ("without semantic models", line 44).
- **Callers**: the router calls `store.suggest_document_pairing` (line 521–523). The store is not downloaded:
  **UNCONFIRMED** whether it calls this function.
- **UI strings**: none.

### 1.5 `project_change_v3/expert_review.py` («Экспертная оценка» verdicts)

The module that persists verdicts is `backend/app/services/project_change_v3/expert_review.py` (the router imports
it as `pc_expert_review`, router line 24). It is not in `stage_comparison/`.

- **Purpose**: "Human assessments of exact published V3 results, separate from frozen artifacts" (line 1).
- **Storage**: SQLite file `comparison_root_path() / 'project_change_expert_reviews.sqlite3'` (line 46). Table
  `reviews` (lines 56–61): `revision INTEGER PRIMARY KEY AUTOINCREMENT`, `object_id`, `session_id`, `pair_id`,
  `run_id`, `change_id`, `result_sha256`, `decision` CHECK in (`accepted`, `rejected`) or NULL, `reason`,
  `actor`, `timestamp` (UTC ISO). Index `review_scope` (line 62). Append-only: every saved decision is a new row.
- **Request model** (`ReviewUpdate`, lines 20–37, `extra='forbid'`): `session_id` (1–128), `pair_id` (1–128),
  `run_id` (1–128), `change_id` (1–300), `decision` (`accepted`|`rejected`|null), `reason` (≤ 4000, stripped),
  `expected_revision` (≥ 0). `ReviewRequest` (lines 40–42): `updates` list of 1–1000 items.
- **Rules**
  - `rejected` requires a non-empty reason: `ValueError` "Укажите причину отказа" (line 34).
  - `decision = None` clears the reason (line 36).
  - Every update must belong to a run whose object is `object_id` (`object_id_for_session`, line 141).
  - Runs with `run_id` starting `pcv3snap_` are checked against the sealed snapshot (`_snapshot_context`, lines
    77–92). Other runs are checked with `run_storage.validate` and `published_run` (lines 146–157).
  - `change_id` must be one of the run's `projectchange_id` values (line 159).
  - Two updates for the same change in one request → `ValueError` "Повторное решение для одного изменения"
    (line 163).
  - Concurrency: inside `BEGIN IMMEDIATE`, each update's `expected_revision` must equal the current latest
    `revision` for that identity (lines 170–175); otherwise the whole batch is refused (all or nothing).
- **Outputs**: `save` returns `{items: [ {…update fields without expected_revision, revision, actor, timestamp} ]}`
  (line 185). `read_run` (lines 67–74) returns the latest row per `change_id`. `attach_snapshot_reviews`
  (lines 95–127) adds `expert_review`, `expert_review_run_id`, `expert_review_available`, `projectchange_id`
  to each accepted snapshot card without writing the source.
- **Actor**: `_decision_author(request)` (router line 774) — the function is not read (UNCONFIRMED).
- **Failure states and HTTP mapping** (router lines 771–778):
  - `ReviewConflict` → HTTP 409, message "Оценка уже изменена другим пользователем. Обновите страницу и повторите решение."
    (text from line 175).
  - `LookupError`, `ValueError`, `OSError` → HTTP 404, message "Изменение или опубликованный запуск недоступны".
    Underlying LookupError texts (not shown to the user by the router): "Опубликованный результат не найден для этой пары"
    (line 86), "Результат не относится к выбранному объекту" (142), "Опубликованный результат не найден" (152),
    "Привязка результата не совпадает" (155), "Изменение не найдено в этом запуске" (160), "Объект результата не совпадает" (148).
- **Model calls**: none. Verdicts are human; no LLM output is used here.

### 1.6 `text_comparison.py` (exact text, linked sheets and cross-sheet lookup)

- **Purpose**: "Deterministic exact-text exclusion for accepted P ↔ RD sheet links" (lines 1–6). PyMuPDF is only
  used to locate units for overlays. No OCR, semantic or vector comparison.
- **Inputs**: Markdown pages (`parse_markdown_fragments`, line 102), PDF page text (`attach_pdf_locations`, line 483;
  `extract_document_fragments`, line 534), accepted links (`{id, left_pages, right_pages}`).
- **Fragment provenance**: `SOURCE_MARKDOWN = "MARKDOWN"` (line 32) and `SOURCE_NATIVE_PDF = "NATIVE_PDF_TEXT"`
  (line 37), the latter only as a last resort for pages with no Markdown unit; never fully proven (comment lines 33–36).
- **Canonical text** (`canonicalize_text`, lines 48–66): casefold, `ё→е`, NBSP→space, `|`→space, dashes unified
  (`_DASH_RE`, line 38), markup stripped. Long paragraphs split at 520 characters on sentence breaks
  (`_split_long_paragraph`, lines 83–100).
- **Pass 1 (linked sheets)** (`compare_fragments`, lines 635–788): links sorted by first left page, then first right
  page, then id. Within each link, fragments with equal canonical text are paired by `_safe_exact_pairs`
  (lines 572–591): one-to-one only if counts are equal and, for each pair, the `source_kind` is equal and the
  relative position distance is ≤ `0.24` when the canonical text has ≥ 30 characters, else `≤ 0.12` (line 587).
  Equal counts of length 1 pair directly.
  - Status `same_on_linked_sheet`, `confidence: "exact"`, `evidence: "structured_text"` (`_match_record`, lines 598–620).
  - Pass 1b: still-unmatched fragments with a PDF-layer canonical text of ≥ 8 characters are paired the same way,
    `evidence: "pdf_text_layer"` (lines 671–687; length gate at 673 and 677).
- **Pass 2 (found on another sheet)**: only for fragments on linked pages, and only if
  `_cross_sheet_eligible` (lines 622–624): canonical length ≥ 15 or matches `_SPECIFIC_ENGINEERING_RE` (lines 41–44).
  - Candidates on the other side, not on the expected pages, not already used (lines 710–728).
  - Frequency gate (`is_frequent`, lines 706–708): ≥ 8 occurrences on the side, or pages > `max(4, 18% of page_count)`
    → no match.
  - Exactly one candidate page; if several candidates on that page, ranked by relative position distance: the best
    must be ≤ `0.3` and ≥ `0.02` ahead of the second (lines 750–751).
  - Status `found_on_other_sheet` with `origin_side`.
- **Outputs** (`compare_fragments`, return at ~line 782): `matches`, `remaining` (fragment ids left for later
  stages), `used_left`, `used_right`, `left_by_id`, `right_by_id`.
- **Metrics and hints** (`build_metrics_and_hints`, lines 793–945):
  - Per side and total: `linked_percent`, `found_elsewhere_percent`, `remaining_percent` (rounded to 1 place).
  - Hint aggregates per (source side, source page, target page) (line ~866–884); skipped if fewer than 40 matched
    characters and fewer than 2 fragments (line 882).
  - Hint `kind`: `likely_incorrect` if the source side's linked share < `0.18` and the aggregate share of the source
    text ≥ `0.55` (line 887); otherwise `additional`.
- **Overlays** (`build_overlays`, lines 946–975). Overlay titles (stored, shown on the page):
  - `«Найдено на другом листе П: {label}»` or `«Найдено на другом листе РД: {label}»` for `found_on_other_sheet`
    (the stage label is РД when the other side is right, П when left) (lines 955–957);
  - `«Совпало на связанном листе»` otherwise (line 961).
  - Fallback label `"Страница {n}"` for a sheet without a label (line 956).
- **Exclusion contract** (`build_text_exclusion_contract`, lines 1399–1490): persists masks per page and the
  remaining lines that downstream stages subtract. `text_exclusion_contract_is_valid` (line 1492) checks
  `version == 1` and structure; `public_view` (line 1534).
- **Model calls**: none.
- **Failure states**: links without fragments produce no matches; the contract records what is still remaining.

### 1.7 `text_fact_producer.py` (structured facts from Stage 3 TEXT)

- **Purpose**: "Deterministic structured facts over production Stage 3 TEXT deltas" (lines 1–9): "precision-first".
  "No model, fuzzy entity match, or unstated engineering assumption is used here" (line 7).
- **Constants**: `KIND = "stage_comparison_text_fact_production"` (line 26), `SCHEMA_VERSION =
  "text-fact-production.v1"` (line 27), `PRODUCER_VERSION = "deterministic-text-fact-producer-v1"` (line 28).
- **Inputs**: `text_differences` artifact (must have the same `pair_id`, line 1279) and the Stage 2 preparation artifact
  (`kind == PREPARATION_KIND`, `schema_version == PREPARATION_SCHEMA_VERSION`, line 1273–1278; else
  `ValueError("production text preparation artifact required")`).
- **Outputs** (`produce_text_facts`, lines 1267–1487): `facts`, `not_applicable_source_evidence`,
  `unresolved_source_evidence`, `diagnostics` (counts: `automatic_facts`, `review_required_facts`,
  `sheet_relation_blocked_facts`, `opposite_coverage_blocked_facts`, `recognition_coverage_blocked_facts`,
  `facts_by_rule`, `owned_facts`, `one_property_per_fact: True`, `uses_model: False`), `provenance`
  (`producer`, `uses_model: False`, `precision_first: True`, `ambiguous_scopes_fail_closed: True`).
- **Fact outcome**: `REVIEW_REQUIRED` vs automatic (line 1400–1401).
- **Sheet-relation gate** (`_relation_assessment`, lines 198–262): reason codes `sheet_relation_unconfirmed`,
  `sheet_relation_confidence_unknown`, `opposite_side_structured_coverage_incomplete`, and
  `recognition_coverage_<status>`. A fact with only the first reason is flagged as the upstream blocker
  (line 257).
- **Recognised structures and rules** (the `rule` value of a fact):
  - `recognized_electrical_load_table` (line 499; header/units checks at 312–354; column sets 51–64);
  - `recognized_room_schedule_table` (line 553; `room_schedule` module, not downloaded: UNCONFIRMED for its header rules);
  - `recognized_assembly_layer_table` (line 741): thresholds `_ASSEMBLY_MIN_THICKNESS_ROWS = 4` (line 591),
    `_ASSEMBLY_MIN_THICKNESS_SHARE = 0.4` (592), `_ASSEMBLY_MIN_MATERIAL_CHARS = 4` (593);
  - `complete_labeled_value_expression` (line 793), `explicit_supply_from_expression` (line 820);
  - owned rules `owned_table_row_field` (905), `owned_label_value_row` (879), `owned_key_value_expression` (921),
    listed in `OWNED_RULES` (lines 832–836). Owned facts need a material difference (`material_difference`,
    lines 1138–1150): owned rules never produce REMOVED or ADDED (comment at ~1290).
- **Ownership module**: `text_fact_ownership` (imported line 24) is not downloaded: UNCONFIRMED.
- **Labels and value vocabulary**: `_LABEL_SPECS` (lines 86–98) map labels to facet names: `installed_power_kw`,
  `demand_active_power_kw`, `protection_degree`, `temperature_range`, `voltage`, `frequency`, `power`, `current`,
  `cross_section`, `quantity`, `reserve_space` (SPACE), `device_type` (TYPE).
- **UI strings**: none found in this file (grep for Cyrillic string literals: only table/column keys and regexes).
- **Model calls**: none (`uses_model: False`, line ~1480).

### 1.8 `text_differences.py` (Stage 3 deterministic TEXT deltas)

- **Purpose**: "Deterministic factual TEXT deltas for accepted sheet-link groups" (lines 1–6). "The production path
  intentionally contains no model call: the August 2026 real-data benchmark found no factual gain" (lines 4–5).
- **Constants**: `VERSION = 1`, `KIND = "stage_comparison_text_differences"` (lines 20–21),
  `ALGORITHM = "deterministic_text_differences_v1_5"` (22), `PRODUCTION_PATH = "deterministic_only"` (23),
  `SIMILARITY_THRESHOLD = 0.82` (24), `AMBIGUITY_THRESHOLD = 0.55` (25).
- **Inputs**: `build_text_differences` (lines 503–590): requires `exclusions.valid` (else `ValueError("text_exclusions_invalid")`),
  rejects remaining fragments that are also excluded (`ValueError("remaining_contains_excluded_fragment")`).
  Only the `remaining` fragment ids of Stage 2 are compared.
- **Candidate score** (`_candidate_score`, lines 156–175):
  - equal `stable_key` → 1.0 (line 161);
  - equal skeleton → 0.97;
  - shared identifier and ratio ≥ 0.68 and token overlap ≥ 0.45 → `min(0.96, ratio + 0.04)`;
  - ratio ≥ 0.82 and token overlap ≥ 0.5 and `max(len) ≥ 24` → ratio;
  - otherwise 0.0.
  Overlap = `|intersection| / min(|A|, |B|)` (`_token_overlap`, lines 149–154).
- **Algorithm** (`compare_group`, lines 342–491):
  - exact-equivalent fragments paired first (lines ~360–380, `_equivalence_key`);
  - room-identity rule (`_room_identity`, lines 289–331) refuses to pair rooms with different room numbers;
  - candidates sorted by score, one-to-one;
  - pairs with raw ratio ≥ `0.55` but no candidate score → `ambiguous` (line 443) and are shown as ambiguity, not a delta.
  - Output buckets: `same`, `changed`, `removed`, `added`, `ambiguous`, `ambiguity_count`, `exact_equivalents`.
- **Summaries** (stored, shown in the UI as "summary"):
  - changed with a key: `"{key}: {old} → {new}."` (line ~201–202, `prefix = key or "Значение"`);
  - changed without a key: `"{first sentence or subject} — текст {action}."`: `"Текст"` as the default subject
    (line 223) and `"— текст изменён."` (line 223);
  - removed: `"… — текст удалён."` (line 270 via `_single_summary(before, "удалён")`, line 233);
  - added: `"… — текст добавлен."` (line 281).
  - Subject is cut at 87 characters plus `…` (line 224–225); first sentence cut at 127 characters (line 232).
  - Fallback label `"Страница {n}"` (lines 550–551).
- **Graphic descriptions** (`is_graphic_description`, lines 140–147): text starting with "the image contains",
  "the image shows", "a blue circular official stamp", or a bracketed shape marker is treated as graphic.
- **Audit-language guard** (`_AUDIT_LANGUAGE_RE`, lines 27–30): words such as «критич», «нарушен»,
  «необходимо исправ», «влияет на стоимост», «ухудшен», «улучшен», «ошибк… проектиров».
- **`validate_model_response`** (lines 601–654): strict checks for a model response (keys `changed`, `removed`,
  `added`; verbatim `before`/`after`; no reused id; numbers must come from the source; no audit language).
  Not on the production path (benchmark code).
- **Model calls**: none in production.

### 1.9 `text_ai_reviewer.py` (Stage 4 semantic review)

- **Purpose**: "Strict contract and safety policy for Stage 4 semantic text review" (lines 1–7). "A model may only
  propose a complete classification over the supplied fragment ids" (lines 3–5).
- **Model**: `PRODUCTION_MODEL = "gpt-5.6-luna"` (line 25), `PRODUCTION_REASONING_EFFORT = "medium"` (line 26).
  "Production has no fallback model cascade; transport retries keep this same reviewer model" (lines 23–24).
  The module does not call the model; the transport is in `store.run_text_ai_review` (router line 1332):
  **UNCONFIRMED** (not downloaded).
- **Constants**: `VERSION = 1`, `KIND = "stage_comparison_text_ai_review"` (18–19), `FINAL_KIND =
  "stage_comparison_text_final_comparison"` (20), `PROMPT_VERSION = "stage4_semantic_reviewer_v2_page_membership"` (21),
  `VALIDATOR_VERSION = "stage4_validator_v1_2_page_membership"` (22), `PRODUCTION_MAX_PRELIMINARY_PER_CHUNK = 40` (27).
- **Final statuses**: `SAME`, `MOVED`, `CHANGED`, `REMOVED`, `ADDED`, `UNCERTAIN` (line 29); confidences `high`,
  `medium`, `low` (line 31); preliminary statuses (lines 32–35): also `AMBIGUOUS`, `REMOVED_ADDED`, `MIXED`.
- **Response schema** (`DECISION_SCHEMA` lines 50–72, `RESPONSE_SCHEMA` lines 74–92): `{groups: [{group_id,
  decisions: [{left_fragment_ids, right_fragment_ids, final_status, confidence, summary, reason, actual_right_pages}]}]}`,
  `additionalProperties: false` everywhere.
- **System prompt** (`SYSTEM_PROMPT`, lines 94–131, Russian). Points the model must follow:
  - each mandatory fragment id exactly once in one decision;
  - **page rule**: a current accepted sheet group is defined by its `left_pages`/`right_pages`; different PDF pages
    inside the group are normal; semantically equal LEFT and RIGHT fragments both inside the group → `SAME`,
    even when the pages differ; `MOVED` only when the matched fragment lies outside the accepted opposite pages;
    do not compare sheet numbers, absolute pages or their order;
  - safety: "ложные SAME/MOVED опаснее UNCERTAIN; при сомнении выбирай UNCERTAIN" (line 121);
    a negation, number, mark, material, mode, method or formula makes the result `CHANGED`;
  - `actual_right_pages` only for `MOVED` and only with RIGHT pages;
  - no judgement of quality, norms, criticality, cost, schedule;
  - `summary` and `reason` are short factual semantic deltas; JSON only.
- **Input to the model** (`prompt_for_groups`, lines 448–472): `SYSTEM_PROMPT` + one hint line (either "Предварительная
  deterministic-классификация присутствует: проверь, а не копируй её." or the benchmark variant) + JSON schema + INPUT
  JSON with, per group: `group_id`, `left_pages`, `right_pages`, `source_left`, `source_right`, and (when hints on)
  `preliminary`. Each source fragment (`_review_source_fragment`, lines 487–501) carries `fragment_id`, `page`,
  `sheet`, `text`, `bboxes`, `source_kind`, `table_key`, `local_context`. **Text only; no images are part of the payload.**
- **Chunking**: a group with more than 40 preliminary items is split into chunks (`chunk_review_group`, lines 663–733),
  ordered by mean fragment position; each chunk id is `"{group_id}::chunk_{n}"` (line ~711).
- **Validation** (`validate_group_response`, lines 216–412; all raise `ReviewValidationError`, which rejects the whole group):
  - schema and `group_id` must match (lines 224–227); `decisions` must be a list (line 230);
  - every required fragment must exist in the source (line 239);
  - decision keys exact (line 249); ids must be lists of strings (line 256); no duplicate ids inside a decision;
  - ids must belong to the source, no hallucinated id (line 269); no fragment classified twice (line 271);
  - enums (line 276);
  - shape rules: `SAME`, `MOVED`, `CHANGED` need both sides (line 279); `REMOVED` only left (281); `ADDED` only right
    (283); `UNCERTAIN` needs at least one side (285);
  - `actual_right_pages` must equal the pages of the right fragments for `MOVED`, and be empty otherwise (lines 293–296);
  - summary and reason must be non-empty (line 300);
  - coverage: when `enforce_coverage`, all required fragments must be used (line 410).
- **Policy overrides applied after validation** (the model's answer is kept in `model_*` fields):
  - `SAME` or `MOVED` with confidence not `high` → `UNCERTAIN`, reason `same_moved_requires_high_confidence` (lines 331–333);
  - `MOVED` with both sides inside the accepted pages → normalised to `SAME`, summary "Смысл совпадает внутри принятой группы листов.",
    reason "Разные абсолютные номера PDF-страниц внутри принятой группы не означают перенос." (lines 349–356),
    reason tag `moved_inside_accepted_group_to_same`;
  - `MOVED` with both sides outside the accepted pages → `UNCERTAIN`, reason
    `moved_requires_exactly_one_side_outside_linked_pages` (lines 358–360);
  - `SAME` where the deterministic status is `CHANGED` → `UNCERTAIN`, reason `same_conflicts_with_deterministic_change` (lines 365–367);
  - summary or reason that cites a value, designation or audit judgement not present in the source → `UNCERTAIN`,
    reason `unsupported_model_<summary|reason>` (lines 370–375). The check (`_supported_claim_text`, lines 180–192)
    requires every number and identifier of the claim to occur in the source and no audit phrase outside the source.
- **Response-level validation** (`validate_response`, lines 414–446): exact key `groups`; no duplicate or unknown
  group; every group must be present (`incomplete_group_coverage`). Atomic: no group is accepted partially.
- **Deterministic status** (`_derived_deterministic_status`, lines 194–214): from the preliminary items touching the
  group; `MIXED` if none or conflicting; `REMOVED_ADDED` if both.
- **Build** (`build_review_groups`, lines 525–661): from Stage 2+3 evidence and accepted links; `"group_id"` and
  `required_fragment_ids` per side; unlinked fragments are not reviewed here.
- **Final comparison** (`build_final_comparison`, lines 782–900): counts per final status (`counts`); transitions
  `"{deterministic}→{final}"`; `requires_review` = count of `UNCERTAIN` (line ~892); fallback groups use the
  deterministic differences with `review_status: "deterministic_fallback"` (`_fallback_group`, lines 766–780,
  `review_error` = the error string). Groups that were reviewed get `review_status: "ai_reviewed"` (line ~820).
  Summary note `failed_groups_use_deterministic_differences_without_masks: True` (line ~896).
- **Failure states**: `status != "completed"` for a group's review → fallback for that group (lines 805–808 region);
  a group with a `ReviewValidationError` cannot be partially accepted (the caller decides; UNCONFIRMED).
- **UI strings** (stored `summary` of the overlay, shown on the page):
  - `"Проверено ИИ: найдено на другом листе (тот же смысл)"` for MOVED (line 743);
  - `"Проверено ИИ: смысл совпадает"` for SAME (line 744).
  - Stored fallback labels `"Страница {n}"` (lines 164, 494, 644–645).
- **Fragment ids and pages** are reconstructed by the backend from source (`_anchors`, lines 169–178).

### 1.10 `project_change_summary.py` (Stage 5 aggregation)

- **Purpose**: "The model may only classify and group existing atomic evidence ids" (lines 3–4). "A failed or invalid
  model response falls back to conservative deterministic classification; it never changes Stage 2/3/4 artifacts
  or `sheet_links`" (lines 4–6).
- **Model**: `PRODUCTION_MODEL = "gpt-5.6-luna"` (line 21), `PRODUCTION_REASONING_EFFORT = "medium"` (line 22).
  **One source group per call**: "Every production call contains exactly one source group" (line 530).
  Transport: **UNCONFIRMED** (caller in store/orchestrator).
- **Constants**: `VERSION = 1`, `KIND = "stage_comparison_project_change_summary"` (17–18),
  `PROMPT_VERSION = "stage5_project_change_aggregator_v3"` (19), `VALIDATOR_VERSION = "stage5_project_change_validator_v6"` (20),
  `PAIR_OK` / `PAIR_REVIEW_REQUIRED` (24–25), `CLASSES = {PROJECT_CHANGE, SERVICE_STRUCTURE, REVIEW}` (26),
  `CATEGORIES` (27–33): `areas`, `floors`, `electrical_load`, `calculation_method`, `consumer_composition`,
  `room_composition`, `dimensions`, `materials`, `equipment_parameters`, `system_configuration`, `fire_safety`,
  `designation_rename`, `administrative`, `documentation_structure`, `formatting`, `other_project`, `other_service`, `uncertain`.
- **Source groups** (`build_source_groups`, lines 368–411): one per sheet group of Stage 4's final comparison. Evidence
  is built from `changed` (status `CHANGED`) and `removed` (status `REMOVED`) buckets (lines ~376–383). Each evidence
  item gets `evidence_id` (line 358), `source_status`, `summary`, a deterministic class hint and category hint
  (`deterministic_class_hint`, lines 305–357). `source_group_sha256` over the group (line ~405).
- **Sheet-purpose precheck** (`precheck_sheet_purpose`, lines 256–293):
  - no titles on one side → `PAIR_OK` with `reason: "purpose_title_unavailable_no_conflict_detected"`, confidence `low`;
  - shared purpose family → `PAIR_OK`, `shared_sheet_purpose_family`, confidence `high`;
  - title-token overlap ≥ `0.35` (`min` of the two token counts, line ~275) → `PAIR_OK`, `sheet_purpose_title_overlap`, confidence `medium`;
  - otherwise `PAIR_REVIEW_REQUIRED`, `sheet_purpose_conflict`, confidence `high`.
  The precheck never mutates links.
- **Prompt** (`prompt_for_groups`, lines 412–436): `SYSTEM_PROMPT` (lines 177–214, Russian) + JSON schema + INPUT JSON
  with per group `group_id`, `left_titles`, `right_titles`, and `atomic_evidence` (`evidence_id`, `source_status`,
  `summary`, `before`, `after`, `reason`, `deterministic_class_hint`, `deterministic_category_hint`). **Text only.**
  Key rules in the system prompt: classes as in lines 186–197 (SERVICE_STRUCTURE covers drawing annotations; PROJECT_CHANGE
  covers object/system parameters; REVIEW covers uncertain/OCR/unverified); group evidence only by one engineering
  attribute; no aggregate counts in `title` (backend adds them); a strong explicit parameter change stays PROJECT_CHANGE
  (lines 205–207).
- **Validation** (`validate_group_response`, lines 448–516; `validate_response`, lines 519–553):
  - exact keys; `group_id` must match (`wrong_group_id`); `items` list;
  - per item exact keys `class`, `category`, `title`, `evidence_ids`; enum checks (`_enum`);
  - `evidence_ids` non-empty list of strings; no duplicate and no id reused across items (`_duplicate_evidence`);
    no hallucinated id (`_hallucinated_evidence`) (lines 448–477);
  - class overrides (lines ~478–505): a `PROJECT_CHANGE` whose evidence hints are only SERVICE_STRUCTURE/UNCLASSIFIED
    becomes `SERVICE_STRUCTURE`; a `SERVICE_STRUCTURE` whose hints are only PROJECT_CHANGE/UNCLASSIFIED becomes
    `PROJECT_CHANGE`; any conflict becomes `REVIEW`;
  - any non-REVIEW item containing a deterministic `REVIEW` hint is refused (`uncertain_must_remain_review`, line ~505);
  - `title` must be non-empty, ≤ 260 characters (line ~506), and every number/designation in it must be literally in the
    evidence (`_supported_title`, line 438);
  - all evidence must be covered (`incomplete_evidence_coverage`, line ~514).
  - Response level: exact key `groups`; `recover_single_group_id` (line 521) accepts a single-group response with a wrong
    id; unknown, duplicate or missing groups are refused (`incomplete_group_coverage`).
  - Error class `SummaryValidationError` (line 216). A refused group becomes a fallback group.
- **Deterministic fallback** (`deterministic_fallback_items`, lines 554–562): one item, class `REVIEW`, category
  `uncertain`, title **"Классификация группы требует проверки"** (line 558).
- **Backend-computed titles** (`_backend_title`, lines 569–587): the model title is replaced by a backend text for
  some categories; stored `model_title` keeps the model's. Stored texts (shown in the UI):
  - 1 evidence: model title + "." ;
  - `areas`: "Скорректированы площади {n} помещений." (line 575);
  - `consumer_composition` with statuses ADDED only: "Расширен состав потребителей{ subject}: добавлено {n} нагрузок." (580);
    REMOVED only: "Сокращён состав потребителей{ subject}: исключено {n} нагрузок." (582);
    mixed: "Изменён состав потребителей{ subject}: {n} изменений." (583). The subject is the first match of
    `ВРУ|ГРЩ|ЩР|ЩО|ЩАО` in the evidence text (`_subject_from_evidence`, lines 563–568);
  - `documentation_structure`: "Изменена структура комплекта документации ({n} фактов)." (585);
  - `administrative`: "Изменены служебные сведения ({n} фактов)." (587);
  - otherwise: "{model title} ({n} связанных изменений)." (line 588).
- **Wrong-pair summary** (`build_wrong_pair_summary`, lines 628–640): title **"Возможно неверно сопоставлены листы"** (line 632),
  class `REVIEW`, aggregation status `pair_review_required`.
- **Artifact** (`build_artifact`, lines 641–690):
  - `status`: `completed` if no group fell back; `failed` if all did; otherwise `partial` (line 658);
  - `aggregation_status` per group: `ai_aggregated`, `deterministic_fallback`, or `pair_review_required`;
  - `summary` counts: `groups`, `pair_ok`, `pair_review_required`, `atomic_evidence`, `project_change_evidence`,
    `project_changes`, `service_structure_evidence`, `service_structure`, `review_evidence`, `review`, `model_calls`,
    `represented_model_calls`, `fresh_model_calls`, `fallback_groups`;
  - `constraints`: `stage4_immutable`, `atomic_evidence_preserved`, `counts_computed_by_backend`,
    `fallback_policy: "review_only_v1"` (line 686);
  - `model`, `reasoning_effort` stored (lines 663–664 area).
- **Model calls**: one per source group in production (line 530); text only.
- **Source signature**: `source_signature` (line 691).

### 1.11 `high_level_project_changes.py` (Stage 5.3 high-level synthesis)

- **Purpose**: "only asks the production model about coherent groups which can still affect a project-level conclusion"
  (lines 5–6). "Every published statement is rebuilt and checked against the selected evidence by the backend" (lines 6–7).
- **Model**: `PRODUCTION_MODEL` and `PRODUCTION_REASONING_EFFORT` are taken from `project_change_summary` (lines 26–27):
  `gpt-5.6-luna`, `medium`. Transport: UNCONFIRMED.
- **Constants**: `KIND = "stage_comparison_high_level_project_changes"` (23), `PROMPT_VERSION = "stage5_3_high_level_synthesis_v1"` (24),
  `VALIDATOR_VERSION = "stage5_3_high_level_validator_v1"` (25), `SCHEMA_VERSION = "1.0"` (22).
  Decisions `CONFIRMED`, `REVIEW_REQUIRED`, `MATERIAL_REVIEW`, `NON_MATERIAL_REVIEW`, `SOURCE_LINK_UNCERTAIN` (29–33).
  `AI_DECISIONS` = `REAL_CHANGE`, `DETAIL_ONLY`, `NO_HIGH_LEVEL_CHANGE`, `INSUFFICIENT_CONTEXT` (48–50).
  `HIGH_LEVEL_TYPES` (35–47): `DESIGN_PRINCIPLE_CHANGED`, `SYSTEM_OPERATION_CHANGED`, `SYSTEM_STRUCTURE_CHANGED`,
  `SPACE_PROGRAM_CHANGED`, `CALCULATION_APPROACH_CHANGED`, `PARAMETER_SET_CHANGED`, `EQUIPMENT_OR_MATERIAL_CHANGED`,
  `QUANTITY_OR_CAPACITY_CHANGED`, `DETAIL_LEVEL_INCREASED`, `NO_HIGH_LEVEL_CHANGE`, `UNRESOLVED_HIGH_LEVEL_CHANGE`.
- **Deterministic pre-grouping** (`build_semantic_groups`, lines 456–485): records from Stage 5 (`_stage5_index`, line 216),
  cross-sheet counterparts marked (line 263), routed by `_route` (lines 418–449):
  - `_is_service` → `SERVICE` / `SERVICE_STRUCTURE`;
  - service text without PROJECT_CHANGE class → `NON_MATERIAL` / `SERVICE_ONLY_REVIEW`;
  - cross-sheet counterpart → `NON_MATERIAL` / `CROSS_SHEET_COUNTERPART`;
  - designation-only without changed numbers → `NON_MATERIAL` / `DESIGNATION_ONLY`;
  - paraphrase or same → `NON_MATERIAL` / `NO_SEMANTIC_CHANGE` (`_is_paraphrase_or_same`, lines 351–378; token overlap ≥ `0.78` with equal numbers, line 374; the `0.82` overlap at line 213 belongs to `_side_counterpart`, lines 199–213);
  - `pair_status == PAIR_REVIEW_REQUIRED` → `MATERIAL_REVIEW` / `SOURCE_LINK_UNCERTAIN`;
  - detail-only → `DETAIL` / `DETAIL_ONLY`;
  - strong two-sided text proof → `CONFIRMED` / `TWO_SIDED_TEXT_PROOF`;
  - Stage-5 `UNCERTAIN` source with parameter/calculation/space/material words → `MATERIAL_REVIEW` / `INSUFFICIENT_CONTEXT`,
    else `NON_MATERIAL` / `LOW_VALUE_UNCERTAIN`;
  - PROJECT_CHANGE class or hint → `AI_REVIEW` / `DETAIL_VS_REAL_CHANGE` (the only route that calls the model);
  - parameter/calculation/operation/material words → `MATERIAL_REVIEW` / `INSUFFICIENT_CONTEXT`;
  - else `NON_MATERIAL` / `NO_PROJECT_DECISION_SIGNAL`.
  Group id `"hlg_" + sha256(...)[:16]` (lines 451–453).
- **Deterministic decisions** (`_decision_for_group`, lines 638–655; `deterministic_decisions`, lines 665–671):
  `CONFIRMED` → `REAL_CHANGE`; `DETAIL` → `DETAIL_ONLY`; `NON_MATERIAL` and `SERVICE` → `NO_HIGH_LEVEL_CHANGE`;
  `MATERIAL_REVIEW` → `INSUFFICIENT_CONTEXT`. Only `AI_REVIEW` groups go to the model.
- **Prompt** (`prompt_for_groups`, lines 578–605): `SYSTEM_PROMPT` (lines 153–170, Russian) + JSON schema + INPUT with per
  group `group_id`, `candidate_type`, `subject`, `source_link_uncertain`, and `atomic_evidence` (`evidence_id`,
  `source_status`, `stage5_class`, `stage5_category`, `summary`, `before`, `after`, `reason`, `sheet_group`,
  `left_pages`, `right_pages`). **Text only.**
- **Validation** (`validate_ai_response`, lines 521–576; `HighLevelValidationError` line 172): exact keys; `group_id` in
  expected set and not duplicated; `evidence_ids` must equal the group's set (`incomplete_or_hallucinated_evidence`);
  enums (`invalid_decision_enum`); `decision_type_mismatch`; `REAL_CHANGE` type must be in `_allowed_ai_types` (lines 507–519,
  adjacency map); `source_link_uncertain_cannot_publish` (REAL_CHANGE with uncertain link); `unsupported_claim` (title/reason
  must pass `_supported_text`, line 491; length ≤ 320 at line 492); `one_sided_presence_cannot_publish` (REAL_CHANGE with only
  ADDED or only REMOVED evidence); `detail_claims_new_object` (DETAIL_ONLY whose title claims a new object, `_NEW_OBJECT_CLAIM_RE`,
  line 120); `unexpected_or_duplicate_group`, `incomplete_group_coverage` (lines 521–576).
- **Fallback** (`fallback_decision`, lines 656–663): `decision: INSUFFICIENT_CONTEXT`, `type: UNRESOLVED_HIGH_LEVEL_CHANGE`,
  `reason: "AI_UNAVAILABLE:{error}"` (line 660), `decision_source: "FAIL_CLOSED"`.
- **Titles** (`_backend_title`, lines 607–636): backend-chosen texts when the model title is missing or unsupported:
  "Скорректированы площади {n} помещений." (617), "Скорректированы расчётные нагрузки группы потребителей." (619),
  "Скорректирован набор проектных параметров." (620), and per-type defaults (line 624 onward, e.g.
  "Изменена структура проектной системы или э…", full text not re-read: UNCONFIRMED for the remaining defaults).
- **Artifact** (`build_artifact`, lines 772–872): `status` = `partial` if any `FAIL_CLOSED` decision (line 829
  `"status": "partial" if fallback_groups else "completed"`, `fallback_groups` at line 821); `evidence_sources: ["TEXT"]`;
  `model` and `reasoning_effort` (line 828); summary includes `model_calls` and `fresh_model_calls` (line 853).
- **Model calls**: one per `AI_REVIEW` group as far as the module shows (grouping is not implemented here: UNCONFIRMED).

---

## 2. Version comparison («Сравнение версий»)

### 2.1 `version_comparison/spec.py` (deterministic positions of a specification page)

- **Purpose**: "Спецификации (СО) по позициям через страницы" (docstring line 1): a specification page is a table per
  GOST 21.110, columns by vertical rules of the header, rows by horizontal rules (lines 2–4).
- **Model calls**: none (module imports `fitz` and `textdiff`, no model).
- **Constants**: `SPEC_VERSION = "so3"` (38); `FIELDS` (39): `pos, name, mark, code, supplier, unit, qty, mass, note`;
  `COMPARE_FIELDS` (40): `qty, unit, mark, code, supplier, note, pos`; `FIELD_LABELS` (41–42): `Поз.`, `Наименование`,
  `Тип, марка`, `Код`, `Поставщик`, `Ед.`, `Кол.`, `Масса`, `Примечание`. `_HEADER_KEYS` (43–45) map header words to fields.
- **Row types** (docstring lines 6–13): section header (name only, centred or bold); position (has unit or quantity);
  parent (name and mark, no unit and no quantity; subrows below); subrow (size/execution + unit + quantity → parent);
  continuation (text only in name/supplier/note → appended to the previous item or parent). Row type is decided by
  filled columns, not by the `pos` number (line 4).
- **Stream**: header skipped on each page; top rows of a new page are classified by the same rules (docstring 15–18).
  Ambiguity is a flag `ambiguous`, never a silent guess (docstring 18).
- **Key for comparison** (`_key`, line 405): `(normalized parent name, normalized name, normalized mark)`; order inside a key kept.
  Page change alone is not a change (docstring 20–21).
- **Normalization**: `_norm` (line 50–52): remove whitespace, lower, homoglyph translation, `×→х`, `,→.`.
  `_qty` (55–57): number with comma or dot, else `None`. `_same_value` (417–422): quantities equal within `1e-9`
  (line 421), other fields by `_norm`.
- **Drawing stamp** (`drawing_stamp`, lines 380–398): a page is a drawing (not a specification) if its stamp title
  matches `план|схема|разрез|узел` (`_DRAWING`, line 380) or its text does and does not contain «спецификац».
- **Comparison** (`compare`, lines 435–536):
  - first pass by key, preferring the same section and note (lines 443–451);
  - second pass (lines 459–478): same unit and same parent-kind; for same mark: `SequenceMatcher` on names; for same name:
    `SequenceMatcher` on marks (or 1.0 if both empty); accepted when score ≥ `0.8` (line 479);
  - third pass (lines 481–490): same name, same unit, same section → pair (replacement of mark);
  - changes (lines 492–527): `name` change recorded; COMPARE_FIELDS differences recorded;
    kinds `changed` (line ~506+), `renumbered` when only `pos` differs (lines 504–506), `ambiguous` when a flagged side
    has no differences (line 513–516), and `moved_between_pages` counted (`_sheet_shift`, line 538).
  - `removed` and `added` items list `qty` and `unit` only (lines ~519–528).
  - order of changes: changed, removed, added, ambiguous, renumbered (line 529); ids `s1…sN`.
  - returns `changes`, `matched`, `moved_between_pages`, `totals` (`_totals`, line 544), `a_items`, `b_items`.
- **Page output**: `page_changes` (line 568) lines per page for the viewer (UNCONFIRMED beyond the signature).
- **Failure states**: `load` returns `None` if no profile file (line 375); `build` writes `spec` file with `SPEC_VERSION`.

### 2.2 `version_comparison/specification_structure.py` (structural markup of a full specification via a model)

- **Purpose**: "Разметь структуру полной спецификации в авторитетном Markdown" (prompt, `prompt_for` lines 45–73). The
  model marks structure only; the program copies cells from the Markdown (`Не переписывай и не исправляй ячейки`).
- **Model**: the prompt is run by `specification_run` with `structure=True` (see 2.3). Model name: see 2.3.
- **Input**: `label`, `document`, `source_sha256`, `blocks` (JSON). Text only (instructions: "Не открывай PDF, сеть или другие файлы").
- **Answer schema** (`schema`, lines 16–44): `sections` (line numbers of plain header lines), `parents` (parent row and first/last
  start lines of its children), `continuations` (adjacent data rows of one position), `notes` (plain note lines).
- **Validation** (`_validate_once`, lines 120–317; `validate`, line 543):
  - structural issues: payload must have `sections, parents, continuations, notes` (else
    "Structural payload must contain sections, parents, continuations, and notes", line ~131); each must be an array;
    "Duplicate section or note line"; "A plain line cannot be both section and note";
    "Plain-line classification mismatch; missing=…, extra=…";
  - continuations: unique table data rows in source order, adjacent, not across a section boundary, not reused, and
    must not merge two values of the same field (lines ~210–240);
  - parents: row-start lines, no gaps or overlaps in child ranges, parent row must have an exact name cell (lines ~240–260);
  - the Jaccard rule for identifying matching row blocks (inside `_validate_once`): `ok = (jac ≥ 0.6 and title ≥ 0.5 and size ≥ 2) or (jac ≥ 0.85 and size ≥ 3)`,
    score `0.4·title + 0.6·jac` (lines 257–263);
  - structural failure → `unlocalizable: True` and the whole version is refused.
- **Thresholds**: `MAX_UNRESOLVED_SHARE = 0.5` (line 319): more than half of the data rows unparsed is not a small error.
  `_PARTIAL_ROUNDS = 4` (line 320). `_SKIP_ISSUES` and `_NOISE_ISSUES` (lines 321–323) are ignored issue texts.
- **Partial** (`_partial`, lines 383–470): reruns on the complete blocks to produce a partial markup with `unresolved_groups`.
- **Normalize** (`normalize`, lines 474–541): applies programme-level corrections to the payload (`fixes` list).
- **Failure states**: `complete`, `partial` (with rows), or failed; `specification_run.usable` (2.3) accepts `complete`
  or `partial` with rows.

### 2.3 `version_comparison/specification_run.py` (whole-specification runner)

- **Purpose**: builds prompts for a full specification of one version, runs them through the executor, validates and
  stores results (module comments; `VERSION = "whole-specification/1"`, line 21).
- **Model**: `MODEL = "gpt-6-luna"` (line 22), `EFFORT = "high"` (line 23). `_run` refuses an executor whose model differs
  (`ValueError("Для этого механизма зафиксирована модель {MODEL}")`, lines ~218–220). The executor factory hard-codes the
  same pair: `executor.py:322` `CodexExecDescriber(model="gpt-6-luna", effort="high", …)`.
- **Constants**: `MAX_SOURCE_CHARS = 140_000` (line 24), `INHERIT_MAX_SHARE = 0.5` (line 25, "изменено больше половины строк —
  версия размечается…", inherit logic not read: UNCONFIRMED).
- **RULES** (lines 27–54, Russian). Key rules: process ALL assigned blocks (rule 1); a page break does not end a position
  (rule 2); `section` and `parent` verbatim (rule 3); copy all fields verbatim, do not sum, round or change commas,
  empty field = empty string, several lines joined by a space, duplicates are not merged (rule 4); evidence must be absolute
  MD line numbers with non-empty quotes; every non-empty line must be in evidence or `ignored`; `ignored` only for table
  headers, separators, section headings (rule 5); table format change and header repeat is not a position; unclear
  boundaries → `issues` (rule 6); do not compare versions (rule 7).
- **Input** (`prepare`, lines 113–175): manifest schema `whole-specification-input/v1` (line ~121); each pair needs
  `id`, two sides each with `label`, `path` to a `.md` file, and exactly one of `pages`, `block_ids`, `all_blocks: true`;
  `pdf_sha256` of 64 hex if given. Source prompt is `RULES + JSON(label, document, source_sha256, blocks)` (`prompt_for`, lines 108–110).
  A prompt longer than `max_source_chars` raises only in structure mode (line ~171).
- **Run** (`run`, lines 177–213; `_run`, line 215): `parallel` must be 1..50 (line ~188; default 50 at line 179);
  `timeout_s` must be positive (default 900 at line 179). A lock file `.run.lock` prevents two runs in one directory
  (`"В этом каталоге уже идёт прогон (.run.lock)"`).
- **Quota or authentication failures stop submission**; there is no replacement model (docstring of `run`).
- **Answer handling** (`best_markup`, lines 76–87): structure validation first; then `structure.normalize`; if the answer is
  not complete, `specification_portions.strict_autofix` may fix known issues and the better partial parse (more rows) is kept
  (`_best_markup`, lines 89–101). Autocorrections are stored in `autocorrections`.
- **Output**: `schema`, `manifest_sha256`, `pairs`, `extraction_mode` (`structure` or `full`).
- **Model calls**: one per block/part; text only (`image_paths` not used; `DescribeTask`
  is built in `specification_run` through the executor: UNCONFIRMED for the exact call fields).

### 2.4 `version_comparison/specification_compare.py` (compare two whole specifications, text output)

- **Purpose**: compares structured rows of two whole specifications and renders a Markdown report.
- **Constants**: `FIELDS` (19), `SUBSTANTIVE_FIELDS` = FIELDS minus `pos` (20), `NUMERIC_FIELDS = {qty, mass}` (21),
  `FIELD_LABELS` (22–26): «Позиция», «Наименование», «Марка», «Код», «Поставщик», «Ед. изм.», «Количество», «Масса», «Примечание».
- **Identity** (`_identities`, line 75; `_pair`, line 153; `_unique_identity_pairs`, line 192; `_align_sections`, line 233):
  rows matched by identity keys, unique-identity pairs first, sections aligned.
- **Not compared** (`_not_compared`, lines 292–314): a group (section) unresolved in at least one version is not compared in
  either version; its pages are described by per-sheet AI (the line 292 docstring says "листовой ИИ"; the delegated path
  is UNCONFIRMED).
- **Compare** (`compare`, lines 316–487): kinds of change: `moved` (`Перенесено без изменения: раздел «…» → …`, line 588),
  position change (`Поз. X → Y; …`, line 604), added (`Добавлено: не было → …`, line 630), removed (`Удалено: … → отсутствует`,
  line 640), group title changed (`Заголовок группы изменён: «…» → «…»`, line 652).
  Ambiguity reason (line 425): «Несколько строк имеют общие признаки; автоматическое соответствие неоднозначно.».
- **Issues** (lines 441 and 443): «Исходная спецификация неполна; остаточные строки предварительные.» and
  «Новая спецификация неполна; остаточные строки предварительные.».
- **Render** (`render_markdown`, lines 670–696): header «Старая версия: **{label}**.» and «Новая версия: **{label}**.»;
  then entries, or one of:
  - «Сравнение неполное; выводы о добавлении, удалении и отсутствии изменений не сформированы.» (line 680);
  - «Однозначные содержательные изменения не подтверждены.» (line 682);
  - «Содержательных изменений не выявлено.» (line 684);
  - «Не сравнены построчно (разметка не прошла проверку; листы описаны по отдельности): «…»; …» (lines 686–688),
    default title «начало спецификации»;
  - «Сравнение неполное; добавления и удаления не публикуются.» (line 692);
  - «Часть позиций требует уточнения; их изменения не подтверждены.» (line 694).
- **Entry rendering** (`render_entry`, line 698; location line 724): `Старая: {old_location}; новая: {new_location}. {text}`;
  location lists sheets `л.{sheet}` and `стр. PDF {page}` (lines 715–719); default text «Строка спецификации» (line 565).
- **Model calls**: none in this module.

### 2.5 `version_comparison_ai/md_report/*` («Отчёт по сводке изменений», AI report from a Markdown summary)

The report is built from a Markdown summary of changes (`parse.py`), analysed by Codex-executed models in three stages
(analyst → verifier → composer), validated by the program, then rendered to PDF. A second, client-facing report uses
`client.py` and `client_edit.py`.

#### 2.5.1 settings (`md_report/settings.py`)

| Setting | Default | Env | Lines |
| --- | --- | --- | --- |
| model | `gpt-6.1-sol` | `VC_MR_MODEL` | 16, 50–51 |
| effort | `high` | `VC_MR_EFFORT` | 17, 54–55 |
| executor CLI | `ai_settings.sc_codex_bin()` | `VC_MR_CODEX_BIN` | 58–60 |
| service tier | none; only `priority` or `ultrafast` accepted | — | 62–66 |
| parallel calls | 4 (1..32) | `VC_MR_PARALLEL` | 68–70 |
| block size | 70 000 characters (2 000..400 000) | `VC_MR_BLOCK_CHARS` | 73–75 |
| verify full text | 150 000 characters (0..400 000) | `VC_MR_VERIFY_FULL_CHARS` | 78–80 |
| verify unit | `transition` (or `group`) | `VC_MR_VERIFY_UNIT` | 83–86 |
| call timeout | 2 400 s (120..7 200) | `VC_MR_CALL_TIMEOUT_S` | 89–91 |
| retries | 1 (0..3) | `VC_MR_RETRIES` | 93–95 |
| retry delays | 20, 60, 120 s | — | 98–108 |
| client parallel | 10 (1..10) | `VC_MR_CLIENT_PARALLEL` | 148–150 |
| client retries | 3 (0..3) | `VC_MR_CLIENT_RETRIES` | 153–155 |
| client retry wait | 30 s (0..600) | `VC_MR_CLIENT_RETRY_WAIT_S` | 158–160 |

- `CHARS_PER_TOKEN = 2.0` (line 24); `MAX_UPLOAD_BYTES = 20 MiB` (line 22); `PROMPT_VERSION = "mdr-p1"` (19); `SCHEMA_VERSION = "mdr-s2"` (20); `REPORT_SCHEMA = "report_v2"` (21).
- `budget` (lines 135–146): context window from the models cache, default 272 000 tokens if unknown; `hard = window × 0.5 × 2.0`
  characters; `block_chars = min(requested, hard)`.

#### 2.5.2 `parse.py` (summary intake)

- UTF-8 only; decoding error → `ValueError("файл не в кодировке UTF-8 (байт …)")` (line 45).
- Transition heading: `^##\s+(\d+)\.\s+(?:(.+?):\s+)?(.+?)\s+→\s+(.+?)\s*$` (line 18); page tokens `A стр. PDF n`, `B стр. PDF n` (lines 20–22).
- Single sheet lines: «Лист добавлен» / «Лист удалён» (line 23). Files: `A: … файл «…». B: … файл «…».` (line 26).
- "No content change" phrase: «изменений содержания нет» (line 28).
- Incomplete markers (lines 30–31): «не досчитано», «ошибка ИИ», «не отправлен», «ещё не описан», «описывается»,
  «не описан (отменено)», «ИИ-описание не запускалось», «не запускалось» …
- «Требует уточнения: N» (line 33). Coverage registry heading «## Реестр покрытия» (line 35) and row regex (lines 36–37).
- Intake errors (runner `create`, lines 144–169): «неизвестный вид отчёта»; «ИИ-обработка в разделе «Сравнение версий» выключена»;
  «нужно подтвердить передачу текста сводки исполнителю»; «объект не найден»; «файл пустой»; «файл больше 20 МБ»;
  «в файле не найдено ни одного перехода «## N. … A → B» — это не сводка изменений»; «среда исполнителя не готова: …».

#### 2.5.3 `runner.py` (orchestration)

- `SCHEMA = "version_comparison_ai.md_report/v1"` (39). `RETRY_KINDS = ("INVALID_JSON", "TRANSIENT", "UNKNOWN", "TIMEOUT", "CHECK")` (52).
- `ACTIVE`, `RESUMABLE` states (41–42). `STATE_LABELS` (43–49): «в очереди», «идёт», «отменяется…», «готово»,
  «неполный результат», «ошибка», «отменено», «прервано — можно продолжить», «пауза: исчерпана квота подписки Codex»,
  «пауза: Codex не авторизован», «ставится на паузу…», «на паузе — можно продолжить».
- `STAGE_LABELS` (50–51): «файл принят, подготовка», «анализ переходов», «проверка выводов», «составление отчёта», «формирование PDF».
- Executor: `_describer()` (108–112) = `CodexExecDescriber(model=settings.model(), effort=settings.effort(), …)` (see 2.9).
- `runtime()` (115–124): the UI text before a run, **verbatim** beginning: «Полный текст загруженной MD-сводки будет передан
  исполнителю Codex на подписке сервера …» (line 121–122, rest of the sentence is in the file; "секреты в задания не входят").
- Flow `_run` (886–975):
  1. prepare: prompts and schemas are read from the report folder recorded at creation (so code changes do not affect a running report);
  2. `plan.build` splits blocks (`PlanError` → «структура не делится на задания без потерь: …», line ~912);
  3. analysis: analyst per group, in parallel up to `parallel` (`_analyse_and_verify`, 1054–1145);
  4. verify: a verifier unit runs as soon as all its groups are done;
  5. coverage: `incomplete` if any transition is missing or a unit failed: «не обработаны переходы: …» (line ~925–928);
  6. compose (1147–1166); programmatic checks (`_checked_report`, 1167–1188);
  7. `report_errors` or `consistency` → `failed`: «отчёт не прошёл проверку: …» (line ~947);
  8. PDF stage (`_pdf_stage`, 1189–1204).
- `_Ctx.call` (703–797): each call writes `calls/<stage>/<unit>/attempt-N/` (prompt, answer, call.json).
  `DescribeTask(prompt, schema, image_paths=[], timeout_s=…)` (line 749) — **text only**.
  - Up to `retries + 1` attempts (line ~735); a schema-invalid answer is `INVALID_JSON` (line ~758);
  - a semantic check failure is `CHECK` and the next attempt gets the feedback text «ПРЕДЫДУЩИЙ ОТВЕТ ОТКЛОНЁН ПРОВЕРКОЙ ПРОГРАММЫ» (lines ~771–777);
  - `TRANSIENT` waits from `retry_delays()` and does not use an attempt;
  - `QUOTA`, `AUTH`, `CANCELLED` stop the job (`_Stop`);
  - a best partial answer that failed only soft checks is accepted with warnings (lines ~791–793).
- Reuse: an existing result file with the same key is reused (`_find_result`, 857–885; `reused_from`).

#### 2.5.4 `stages.py` (prompts, checks, assembly)

- `PROMPT_NAMES = ("rules", "common", "analyst", "verifier", "composer")` (21). Templates `prompts/md_report_<name>.md`.
  Placeholders `{{NAME}}` filled by `render` (lines 38–56); text between `{{BEGIN}}`/`{{END}}` is declared data.
- `RELATED_PER_TOKEN = 5`, `RELATED_MAX_TOKENS = 40`, `RELATED_MAX_CHARS = 40 000`, `EXCERPT_PAD = 2`, `WORD_LIMIT = 1000` (23–27).
- **Analyst** (`analyst_prompt`, 100–124): input = assigned transitions, block manifest (`{bid}: {transition}, {kind}, строки …, {chars} символов`),
  source limitations (header lines), and the numbered MD lines of the blocks (`numbered`, line 69). Each data line carries its
  MD line number in brackets.
  `check_analyst` (130–172, `hard` = reject, `soft` = warn): run_id and group_id must match; transitions must equal the assigned
  set; all assigned blocks processed; evidence ranges must lie inside the assigned ranges (`_in`); every fact needs evidence;
  explicit «изменений содержания нет» must match `content_status` `no_content_changes`; references outside assigned text are counted.
- **Claims** (`claims_for_unit`, 174–201): claim ids `G{group}.{transition}.A` (transition assessment), `.{fact_id}` (facts; flagged
  «кандидат в серьёзные» when `serious_candidate`), `.K{n}` (issue condition), `.X{n}` (contradiction).
- **Verifier** (`verifier_prompt`, 237–311; `check_verifier`, 312–336; `clean_verifier`, 338–361): one verdict per claim from
  `VERDICTS = supported, qualified, contradictory, insufficient, rejected` (schemas.py:18). Hard: missing verdict for a claim
  (`нет вердикта по утверждениям`), transition totals not equal to the unit (line 326), references to lines not shown to the verifier (line 332).
  Unknown claim verdicts are dropped with a soft warning (line 323).
  Excerpts: `_excerpt_ranges` (217–236) around claims; `FULL` text when the unit is below `verify_full_chars`.
- **Final per-transition assessment** (`final_assessment`, 371–387): one verified part → its own `change_scope` and `significance`;
  several parts → the composer's value raised to the highest part value; note «масштаб поднят до оценки части (…)» /
  «значимость поднята до оценки части (…)».
- **Composer** (`composer_prompt`, 468–499; `composer_facts`, 437–450: `FACTS_PER_CLAIM = 4` (433), `FACTS_PER_CANDIDATE = 8` (434)).
  `check_composer` (584–670): run_id match; exactly the transitions of the report (line 594); **more than 5 serious changes is a
  hard error** (line 598: «серьёзных изменений {n} — допускается не больше 5»); every serious change must cite verified claims
  (lines 602–604); soft: unconditional wording of the consequence (644); assessment outside the verified range (665).
  `chain_problems` (567) checks that chain statements reference known objects; `numbers` (506) compares numbers with the source.
- **Scope and significance vocabularies** (`schemas.py`, lines 14–25): scope «Нет изменений содержания», «Только оформление»,
  «Локальные изменения», «Существенные изменения», «Широкая переработка», «Не установлено»; significance «Нет новых технических
  изменений», «Низкая», «Средняя», «Высокая», «Не установлена». Ranks: `SCOPE_RANK`, `SIGNIFICANCE_RANK` (23–25).
  Priorities `P1`, `P2`, `P3` (19).
- **Assembly** (`assemble`, 756–845): the report is built from the composer answer, with ids humanised (`humanize`, 705) and
  internal ids removed (`internal_ids`, 694). `distribution` (846) and `consistency` (857) are the final checks.

#### 2.5.5 `plan.py`, `parse.py`, `facts.py`, `schemas.py`, `disciplines.py`

- `plan.build` (61–157): blocks ≤ `block_chars` made of transitions or parts of transitions (`_units`, 32–60: a sheet larger than the
  limit is split by lines, its heading kept as context); groups are sets of blocks; `verify_units` by `verify_unit`.
  `PlanError` when a split is impossible without loss (186–…).
- `facts.py`: fact ids `Ф0000` / `F0000` (`FACT_ID`, line 16). Location grammar `SPEC_LOC` (line 20) for «Старая: …; новая: …».
  `CONFIRMATION` (23–35) maps confirmation kinds to Russian labels (not re-read: UNCONFIRMED for the exact texts).
  `TEXT_CHARS = 160`, `EXTRA_CHARS = 220` (182–183).
- `schemas.py`: `ANALYST_SCHEMA` (72–92), `VERIFIER_SCHEMA` (93–113), `COMPOSER_SCHEMA` (115–136), `validate_report` (156…).
  `CONTENT = technical, formatting_only, no_content_changes, unknown` (17).
- `disciplines.py`: client discipline profiles from `prompts/client_disciplines/*.md` (`DIR`, line 15; 35 files: AGPT, AK, AR, …);
  `resolve(code, title)` (49–62).

#### 2.5.6 `client.py` and `client_edit.py` (client-facing report)

- `client.py`: `NO_CHANGES = "Технических изменений не выявлено."` (21); `SCOPE_NONE = "Без технических изменений"` (22);
  `POINTS_MAX = 6` (23). `build` (122–198): fact points per transition, ranked (`_RANK`, 109–121). `object_title` (199), `section_title` (214).
- `client_edit.py` (writer of the client text, one call per transition):
  - `PROMPT_VERSION = "client-edit/3"` (23); `FIELD_CHARS = 110`, `TEXT_CHARS = 260`, `NAME_CHARS = 36`, `MEMBER_CHARS = 60`, `TITLE_CHARS = 34`, `POINTS_MAX = 8` (24–29).
  - `SCOPES` (31–32): «Локальные изменения», «Существенные изменения», «Широкая переработка», «Только оформление», «Нет изменений содержания».
  - `packet` (77–183) builds the input per transition; `schema` (184); `prompt_for` (210–221).
  - `check` (357–463): forbidden phrases list `_FORBIDDEN` (340–349); number and side checks; `UNCERTAIN` facts (`_UNCERTAIN`, line 584).
  - Runtime: `CHARS_PER_TOKEN = 1.9` (755), `PARALLEL = 10` (756, "переходов одновременно (решение 21.10.2026)"), `RETRIES = 3` (757),
    `RETRY_WAIT_S = 30` (758), `STOP_KINDS = QUOTA, AUTH, CANCELLED` (759). `run` (775–908) calls `DescribeTask(prompt, schema(),
    image_paths=[], timeout_s=1800)` (line 838) — **text only**.
  - Reserved: `save_edit` (714–753) stores an editor decision; `recheck` (909).

#### 2.5.7 `pdf.py`

- Renders the report PDF; previews at `dpi=90` (lines 380, 650). 681 lines: the rest is UNCONFIRMED (not read).

#### 2.5.8 Model calls of the md_report family

| Call | Model / effort | Images | Sent | Parallel | Retries |
| --- | --- | --- | --- | --- | --- |
| analyst, verifier, composer (`runner.py` `_Ctx.call`) | `gpt-6.1-sol` / `high` (settings 16–17) | 0 (`image_paths=[]`, line 749) | prompt text (numbered MD, claims, verdicts) | 4 (default) | 1 retry (2 attempts); TRANSIENT waits 20/60/120 s, not counted as attempts |
| client edit (`client_edit.py` run) | `gpt-6.1-sol` / `high` (via `_describer`, runner 635) | 0 (line 838) | packet text per transition | 10 | 3, wait 30 s |

### 2.6 `version_comparison_ai/sheet_match.py` («Проверить сомнительные пары через Луну»)

- **Purpose** (module docstring, lines 1–20): the model checks doubtful sheet pairs of every cipher of an object. Pilot on
  object 213 (18.10.2026): on drawings at confidence `high`, 0 wrong pairs out of 74; on multi-sheet tables answers are
  unstable, so only a hint is shown there.
- **Model**: `ex.get("sheet_match")` (line 526) → `CodexExecDescriber(model=settings.sm_model(), effort=settings.sm_effort(), binary=settings.sm_codex_bin())`
  (executor.py:323–325). Defaults `gpt-6-luna`, `high` (settings.py:260–261; model function at 283–284; effort at 287–288).
- **Constants**: `SCHEMA = "version_comparison_ai.sheet_match/v1"` (39); `ACTIVE = (running, cancelling, pausing)` (40);
  `RETRY_KINDS = (TRANSIENT, TIMEOUT, INVALID_JSON, UNKNOWN)` (41); `ACCOUNT_KINDS = (QUOTA, AUTH)` (44);
  `ACCOUNT_PAUSES_S = (30, 120)` (45); `ANSWER_SCHEMA` (46–49): `choice` (int), `page` (int), `confidence` (high|medium|low), `reason` (str).
  Settings: `SM_PROMPT_VERSION = "vcsm-p3"` (settings.py:259), `SM_DEFAULT_PARALLEL = 30` (262, "30 обращений одновременно"), `SM_IMAGE_WIDTH = 1800` (263).
- **Questions** (`questions`, lines 124–169), per adjacent version pair and cipher:
  - `review` (line 154–158): sheet A has no pair and B's cell has candidates; candidates are the B pages not spec pages, up to 4 (line 154 `[:4]`); sheets inside a table group («▤ группа») are not asked (lines 136–139);
  - `medium` (lines 160–165): an algorithm pair of medium confidence; candidates are `{b} ∪ {b−1, b+1}` that exist and are not spec pages.
- **Prompt** (`_prompt`, lines 171–203; Russian): two images, image 1 = sheet A, image 2..n+1 = candidates; asks: which candidate is the same
  sheet (same plan/facade/section/scheme/table of the same object; same floor, axes, unit, system, section); equal layout is not enough;
  cipher and object name in the stamp may change; "Если ни один кандидат не является тем же листом — ответ 0."; reply JSON
  `choice` (1…n or 0), `page` (the page of the chosen candidate or 0), `confidence`, `reason` (≤ 300 characters).
- **Images** (`_labeled`, lines 215–232; `ask`, lines 243–292): each image is the sheet's thumbnail at width `SM_IMAGE_WIDTH = 1800` px
  (`profile.thumbnail`, line 221) with a yellow band of 90 px on top and text drawn in red (line 223: `band = 90`). Captions:
  `ЛИСТ A` (for A) and `КАНДИДАТ {n} — стр. {b}`. Image count = 1 + number of candidates (≤ 5 in practice; `review` has ≤ 4 candidates
  plus A; `medium` has up to 3 candidates plus A = 4 images). Image files are copied with neutral names by the executor (see 2.9).
- **Reverse check** (`reverse_cands`, lines 318–324, and `one_rev`, lines 578–582): for each proposed pair the question is repeated from B
  to A with candidates = B's previous candidates (≤ 3) ∪ {A} (or A±1 when fewer than 2).
- **Decision** (`decide`, lines 326–350):
  - no pick → `failed`; pick −1 (number and page disagree) → `mismatch`;
  - `medium` questions: 0 → `medium_none`; pick = current pair → `medium_confirm` if confidence high else `medium_weak`; other → `medium_other`;
  - pick 0 → `none`; multi-sheet spec → `hint_table`; confidence not high → `hint_confidence`; B already paired with another A sheet
    in the algorithm matrix → `hint_taken`; reverse check did not return A with high confidence → `hint_reverse`;
  - otherwise `accepted`: the pair is set automatically with a note «ИИ» (`ai_link`), only when all conditions of the module docstring hold
    (answer high, candidate number and page agree, sheet not inside a multi-sheet specification, B not linked to another A,
    no other A sheet chose the same B, reverse question returns A with high).
  - Manual edits (`manual`) win over Луна (docstring lines 17–18).
- **Stored labels** (`DECISIONS`, lines 51–63; stored in `_note`, shown in cells as the hint text per the docstring):
  «пара принята Луной»; «подсказка: встречная проверка не подтвердила»; «подсказка: уверенность не высокая»;
  «подсказка: многолистовая таблица»; «подсказка: лист уже в паре алгоритма»; «подсказка: два листа выбрали один»;
  «Луна: ни один кандидат не тот же лист»; «ответ отброшен: номер кандидата и страница не сходятся»; «сбой обращения»;
  «пара подтверждена Луной»; «пара подтверждена неуверенно»; «Луна указывает другой лист»;
  «Луна: ни один из [пара, соседи] не тот же лист». Display of these labels: UNCONFIRMED (frontend not read).
- **Retries and pauses** (`ask`, lines 265–281): `RETRY_KINDS` retried up to 2 times with `time.sleep(2 + 3·n)`;
  `ACCOUNT_KINDS` (QUOTA, AUTH) pause for 30 s then 120 s, then continue or stop; cancel → «отменено».
- **Cache** (`_answer_path` line 239; key `_key` line 234; digest from prompt version, model, effort, line 235): answers are stored by content
  (`answers/<key>.json`) and reused; a rerun over the same sheets does not call the model.
- **Parallelism**: `_parallel` (lines 364–385) with `sm_parallel()` (default 30, `settings.py:262`, clamp 1..50 at lines 295–300).
- **Start** (`start`, lines 412–454): requires `consent` (else refusal, line 418). Pause/cancel/resume via `pause`, `cancel`.
- **Model calls**: one per question (≤ 2 per adjacent pair with the reverse check); images as above; text is the prompt (no OCR text by default:
  the prompt says to read from the picture when the PDF has no text, line ~196).

### 2.7 `version_comparison_ai/packet.py`, `prompt.py`, `validate.py` (per-sheet description packet, older path)

- These three files build and check the per-sheet **describe** packet from records of the sheet comparison (`packet.py` `SCHEMA =
  "version_comparison_ai.sheet_packet/v1"`, line 28). `prompt.py` renders `prompts/describe_sheet.md` (`TEMPLATE`, line 16).
  `validate.py` checks the answer per chunk (`check_chunk`, line 73; `ledger`, line 207).
- **Who calls them**: the `sheet_changes` runner does NOT use these (it uses `pack.build_pooled`, see 2.8). The caller of
  `packet.build` is not in the downloaded tree: **UNCONFIRMED** (probably the records describer in `jobs.py`, not downloaded).
- **Constants**: `MAX_MARKS = 60` (29); `AI_STATUSES = (different, needs_review)` (32); `SHEET_TEXT_LIMIT = 3000` (33).
- **Chunking** (`_pack_chunks`, lines 306–329): a chunk holds at most `chunk_records()` records (default 40, env
  `VC_AI_CHUNK_RECORDS`, settings.py:93–94, range 5..400) and at most `chunk_images() − 1` cluster images
  (default 12 images, env `VC_AI_CHUNK_IMAGES`, settings.py:97–98, range 2..40; one image is reserved for the whole sheet).
  Each cluster counts 2 images (line ~313). Records not on a box are appended up to the record limit.
- **Images**: sheet overlay image scaled so that the long side is ≤ 1400 px (`_sheet_image`, lines 284–305, scale at line 298–299).
- **Output files**: `sheet.md` (whole sheet) and `prompt.md` per chunk (lines 558–562).
- **Validation** (`validate.py`): `ISSUE_TEXT` (lines 30–48) lists the codes and their Russian text: "ответ не соответствует схеме" (SCHEMA),
  "ответ относится к другому пакету или части" (MIXED_INPUT), "ссылка на несуществующую запись" (UNKNOWN_ID),
  "ссылка на запись другой части листа" (FOREIGN_ID), "ссылка на несуществующий контекст" (UNKNOWN_CONTEXT),
  "ссылка на изображение, которого не было в части" (UNKNOWN_IMAGE), "пункт без действительных доказательств" (NO_EVIDENCE),
  "у записи несколько судеб — взята первая" (DUPLICATE_DISPOSITION), "судьба указывает на пункт, который эту запись не содержит"
  (DISPOSITION_ITEM_MISMATCH), "запись не получила судьбы от модели" (MISSING_DISPOSITION), "значение «было/стало» не найдено на своей
  стороне" (DIRECTION_UNVERIFIED), "число или марка из текста пункта не найдены в доказательствах" (UNSUPPORTED_TOKEN),
  "нечитаемое значение описано без неопределённости" (UNREADABLE_NOT_FLAGGED), "расхождение между листами без доказательств с двух
  страниц" (CROSS_CHECK_ONE_SIDE), "графика описана без просмотра изображения — не считается проверенной" (GRAPHIC_WITHOUT_IMAGE),
  "пустой ответ при непустом списке записей" (EMPTY_ANSWER).
- **Prompt** (`prompt.py`): channels, states, reasons, kinds, types and flags have Russian labels (lines 18–55); records table, contexts,
  xrefs, images list and program section are rendered per chunk (`render_chunk`, 245; `render_sheet`, 255).
  States shown: «проверено», «НЕ проверено», «не применяется» (line 23).
- **Model**: the describer is passed in; the model/effort are those of `ex.get(...)` for the caller (UNCONFIRMED: no `ex.get` call for this path
  was found in the downloaded tree).

### 2.8 `version_comparison_ai/sheet_changes/*` («Изменения в листе», the sheet-changes run)

- **Entry**: `run_sheet` (`sheet_changes/run.py:147–273`) builds the packet with `pack.build_pooled` (line 152), then calls the model.
- **Model**: `settings.sc_model()` = `gpt-6.1-sol` and `sc_effort()` = `high` (settings.py:180–181, 206–211); the executor is
  `ex.get("sheet_changes")` by method name (executor.py:327–329) — the call site that passes it into `run_sheet` is not in the
  downloaded tree (UNCONFIRMED). Runtime digest for cache keys: `cache_key` (run.py:48–53) includes executor, model, effort and
  `context_rounds`.
- **Timeout**: `call_timeout_s` = max(`VC_AI_CALL_TIMEOUT_S`, `VC_SC_CALL_TIMEOUT_S` default 1800) (run.py:44–46).
- **Limits** (run.py:33–36): `MAX_LAUNCHES = 3` (launches per sheet, free waits excluded), `MAX_REQUESTS = 6` (context requests),
  `MAX_EXTRA_IMAGES = 6`, `RETRY_KINDS = (INVALID_JSON, TRANSIENT, UNKNOWN, TIMEOUT)`.
- **Retry policy** (`attempt`, inside `run_sheet`): `QUOTA`, `AUTH`, `CANCELLED` → pause; other non-retry kinds end the attempt;
  `TRANSIENT` waits `sc_retry_delays()` (default 20, 60, 120, 300, 600 s; settings.py:231 area) and does not use a launch.
  A schema-or-check failure is `INVALID_JSON` with issue text «ответ не по схеме: …» (line ~196).
- **Phases** (`run_sheet`): primary call (`MAX_LAUNCHES`) → optional context round (`sc_context_rounds()` default 1, range 0..1;
  `resolve` returns the requested extra images, ≤ `MAX_EXTRA_IMAGES`) → optional coverage call when `not_reviewed` objects remain
  (prompt3) → result `sheet_changes.json`; cache hit when `answer.json` exists with matching meta (line ~215).
- **Packet** (`sheet_changes/pack.py`):
  - constants (34–41): `SCHEMA = "version_comparison_ai.sheet_changes_packet/v1"`, `TEMPLATE = prompts/sheet_changes.md`,
    `GROUP_MAX_PT = 520.0` (group box size in points, line 84), `IMAGE_MAX_PX = 1950` (long side of an image, lines 124–200),
    `TEXT_PX = 14.0`, `DPI_RANGE = (150.0, 300.0)` (dpi derived from the median text height, lines 69–73; default 200 when no words),
    `XREF_LIMIT = 2`, `POINTERS_SHOWN = 30`;
  - image kinds: region/block crops and whole-sheet overlay; a table image is needed when a candidate is a full table, a region or block
    pointer, or a unit number appears (`_needs_table_image`, lines 92–101);
  - `build_pooled` (411–431) and `_build` (356–405): manifest `method` = `sc_versions()` plus `template_digest` (line 369).
  - Prompt: `render_prompt` (334–344) renders `prompts/sheet_changes.md` with `{{BEGIN}}`/`{{END}}` data delimiters (the template states that everything between them
    is data, lines 1–4 of the template); `render_data` (256–333) renders the candidates.
- **Prompt rules** (`prompts/sheet_changes.md` lines 1–20, Russian): the unit of the answer is a construction object and its place
  ("люк у помещения, тип пола, кабельная линия, аппарат защиты, узел, позиция материала"), one item per object: «объект/место — было → стало»,
  1–2 sentences with marks, sizes, quantities and units; "Не пиши «изменена маркировка», если можно назвать марку и размер."; `was` only from A,
  `now` only from B; engine pointers are positional and not proof of replacement (rule 4).
- **Schema** (`schema.py`): `KINDS` (10–11, including `replacement`, `added`, `removed`, `quantity`, `parameter`, `requirement`, `route`,
  `relocation`, …); `MAPPINGS = one_to_one, one_to_many, many_to_one, none` (17); `SOURCES = text, image, text_and_image` (18);
  `CERTAINTY = confirmed, unclear` (19); `EXCLUDE_REASONS = service, formatting, label_move, revision_mark, duplicate, not_construction` (20);
  `REQUEST_KINDS = mark, zoom, rows` (26). Full schema `SHEET_CHANGES_SCHEMA` (51–102), `schema_digest` (103).
- **Validation** (`sheet_changes/validate.py`): `PACKET_ID_MIN_RATIO = 0.8` (line 40): `packet_id` typo tolerated if similarity ≥ 0.8 (line 143);
  `check` (130–242) issue codes include `SCHEMA`, `MIXED_INPUT`, `UNKNOWN_CANDIDATE`, `UNKNOWN_IMAGE`, `NO_CANDIDATE`,
  `VALUE_UNVERIFIED`, `TEXT_CORRECTION_UNCHECKED` (line 205: «исправлен текст» without the same value checked in another packet),
  `SERVICE_PART_REMOVED`, `REASON_REMOVED`, `NOT_REVIEWED` (line 236). `_confirm` (71) decides whether a field is confirmed by text or image.
  `check` returns `ok`, `changes`, `unresolved`, `excluded`, `issues`, `coverage` (`not_reviewed`), `context_requests`.
- **State of a sheet** (`state_of`, lines 244–255): not ok → `failed`; not-reviewed objects → `partial`; unresolved → `needs_clarification`;
  no changes → `partial` if the engine had notes, else `no_construction_changes`; else `done`.
- **UI strings** (`STATE_LABELS`, lines 257–263): «Не обработано», «В очереди», «В обработке», «Готово», «Требуется уточнение», «Частично»,
  «Строительных изменений не выявлено», «Описание устарело», «Ошибка», «Отменено», «По данным сравнения изменений нет».
- **Model calls**: per sheet, up to 3 primary launches + 1 context + 1 coverage (retries counted as launches); images are the packet images
  (count not capped in `run.py`: UNCONFIRMED). Text = `render_prompt` output.

### 2.9 `version_comparison_ai/executor.py` and `settings.py` (shared transport)

- **Adapter**: `CodexExecDescriber` runs `codex exec` on the service's own subscription (module docstring lines 1–12).
  Isolation: empty temporary folder, `--sandbox=read-only`, `--ephemeral`, no user config or rules, 22 features disabled, environment whitelist,
  cancel kills the process group.
- **Command** (`cmd`, lines 174–185): `codex exec --model=<model> --sandbox=read-only --skip-git-repo-check --ephemeral
  --ignore-user-config --ignore-rules --json`, `-c model_reasoning_effort=<effort>`, `--output-schema=<file>`, one `--image=<path>` per image,
  `--cd=<workdir>`, `--output-last-message=<file>`, `-` (prompt on stdin). Images are copied to neutral names `img001.png`… (lines 196–200).
- **Errors** (`ERROR_TEXT`, lines 44–54; `NO_RETRY`, line 56): «исчерпана квота подписки Codex — повторите после сброса лимита» (QUOTA),
  «Codex не авторизован у пользователя службы» (AUTH), «превышено время ожидания ответа» (TIMEOUT), «отменено» (CANCELLED),
  «временный отказ провайдера» (TRANSIENT), «ответ не является JSON» (INVALID_JSON), «пакет не поместился в контекст модели» (CONTEXT),
  «среда исполнителя не готова» (RUNTIME), «изображение части недоступно — часть не отправлена» (IMAGE_UNAVAILABLE), «неизвестная ошибка исполнителя» (UNKNOWN).
  Markers for quota and auth text: `QUOTA_MARKERS` (37), `AUTH_MARKERS` (39).
- **Factory** `get(method)` (315–330): `kind` must be `codex_exec` (`VC_AI_EXECUTOR`, settings.py:67–68). Methods:
  `whole_specification` → `gpt-6-luna`/`high` (hard-coded, line 322); `sheet_match` → `sm_model/sm_effort` (324); `sheet_changes` → `sc_model/sc_effort` (328);
  default `CodexExecDescriber()` with `settings.effort()`/`model()` of the caller.
- **`validate_cli`** (231–271): probes the CLI's `exec --help` for `--output-schema`, `--sandbox`, `--ignore-user-config`, `--disable`, `--config`,
  `--image`, `--json`.
- **Test double** `FakeDescriber` (273–306).
- **Settings relevant to all version comparisons** (`version_comparison_ai/settings.py`): `VC_AI_CALL_TIMEOUT_S` default 900, range 60..7200 (84–85);
  `VC_AI_CHUNK_RECORDS` 40, `VC_AI_CHUNK_IMAGES` 12 (93–98); sheet_changes: `SC_DEFAULT_MODEL = "gpt-6.1-sol"`, `SC_DEFAULT_EFFORT = "high"` (180–181),
  `sc_parallel` default 1 (range 1..50, lines 219–225), `sc_retry_delays` default (20, 60, 120, 300, 600) (line ~231), `sc_context_rounds` default 1 (243–246);
  sheet_match: `SM_DEFAULT_MODEL = "gpt-6-luna"`, `SM_DEFAULT_EFFORT = "high"`, `SM_DEFAULT_PARALLEL = 30`, `SM_IMAGE_WIDTH = 1800` (259–263).

---

## 3. Summary tables

### 3.1 Every model call found in the read files

| Caller | Model | Effort | Sent to the model | Images | Source |
| --- | --- | --- | --- | --- | --- |
| Stage 4 review (`text_ai_reviewer`) | `gpt-5.6-luna` | medium | system prompt + schema + JSON groups (fragment texts, bboxes, hints) | 0 in payload (transport UNCONFIRMED) | `text_ai_reviewer.py:25–26, 448–472` |
| Stage 5 aggregation (`project_change_summary`) | `gpt-5.6-luna` | medium | system prompt + schema + one group per call | 0 | `project_change_summary.py:21–22, 530` |
| Stage 5.3 synthesis (`high_level_project_changes`) | `gpt-5.6-luna` (from 5) | medium | system prompt + schema + AI_REVIEW groups | 0 | `high_level_project_changes.py:26–27, 578–605` |
| Whole specification (`specification_run`, structure mode) | `gpt-6-luna` | high | RULES + JSON blocks (MD text) | 0 | `specification_run.py:22–23`; `executor.py:322` |
| Summary report analyst / verifier / composer (`md_report/runner.py`) | `gpt-6.1-sol` | high | numbered MD lines, claims, verdicts | 0 | `md_report/settings.py:16–17`; `runner.py:749` |
| Client edit (`md_report/client_edit.py`) | `gpt-6.1-sol` | high | packet text per transition | 0 | `client_edit.py:838` |
| Sheet doubtful-pair check («Луна», `sheet_match.py`) | `gpt-6-luna` | high | prompt + 1 sheet image + up to 4 candidate images | 2–5 | `sheet_match.py:257–269`; `settings.py:260–261` |
| Sheet changes (`sheet_changes/run.py`) | `gpt-6.1-sol` | high | prompt + packet images (crops, overlay) + context images | packet images (count UNCONFIRMED) | `settings.py:180–181`; `run.py:147–273` |

### 3.2 Deterministic modules and stored artefacts

- No model call: `sheet_link_repair.py`, `content_sheet_link_repair.py`, `document_matching.py`, `project_change_v3/expert_review.py`
  (human verdicts), `text_comparison.py`, `text_fact_producer.py`, `text_differences.py` (production path), `spec.py`,
  `specification_compare.py`, `specification_structure.py` (validation only), `packet.py`/`prompt.py`/`validate.py` (describe path).
- Stored artefacts and their identity keys are listed in each section under «outputs»: stage kinds and versions
  (e.g. `stage_comparison_text_differences` v1, `text_differences.py:20–21`; `stage_comparison_project_change_summary` v1,
  `project_change_summary.py:17–18`); expert verdicts in SQLite `project_change_expert_reviews.sqlite3`, table `reviews`
  (`expert_review.py:46, 56–61`); version artefacts `so3` (`spec.py:38`), `whole-specification/1` (`specification_run.py:21`),
  `version_comparison_ai.md_report/v1` (`md_report/runner.py:39`), `client-edit/3` (`client_edit.py:23`),
  `version_comparison_ai.sheet_match/v1` (`sheet_match.py:39`), `version_comparison_ai.sheet_changes_packet/v1` (`sheet_changes/pack.py:34`).

## 4. UNCONFIRMED and not-read items

Not downloaded (named by the read files, or needed for the caller side):

- `backend/app/services/stage_comparison/store.py`, `production_orchestrator`, `production_batch`, `stage_upload` — the transport and wiring of
  `text_ai_reviewer`, `project_change_summary`, `high_level_project_changes`, `sheet_link_repair`, `document_matching`,
  `text_fact_producer` (no caller in the downloaded tree). **UNCONFIRMED**: who calls them, with what batch, and how the model
  is invoked (Codex or API).
- `backend/app/services/stage_comparison/sheet_content_fingerprint.py` (imported by `content_sheet_link_repair.py:9` and
  `sheet_matching.py`) — fingerprint fields and `purpose_terms`. **UNCONFIRMED**.
- `backend/app/services/stage_comparison/text_fact_ownership.py`, `room_schedule.py`, `recognition_coverage.py`,
  `production_text_flow.py`, `production_artifacts.py` (imported by `text_fact_producer.py`). **UNCONFIRMED**.
- `backend/app/services/stage_comparison/text_atom_builder.py`, `text_region_classifier.py`, `text_semantic_validation.py` — not read.
- `backend/app/services/version_comparison_ai/jobs.py`, `series_ai.py`, `series_summary.py`, `report.py`, `view.py`, `verify.py`,
  `whole_specifications.py`, `stage_queue.py`, `summary.py` — callers of the describe packet and the report; not read.
  **UNCONFIRMED**: who calls `packet.build` and `sheet_changes.run_sheet`, and their image limits.
- `backend/app/services/version_comparison/specification_portions.py` (`strict_autofix`), `specification_inherit.py`, `specification_reconcile.py`,
  `specification_pdf_values.py` — used by `specification_run.py`; not read.
- `backend/app/services/version_comparison_ai/md_report/pdf.py` (681 lines), `plan.py` details beyond the listed functions,
  `client_edit.check` rules beyond the names listed, and `facts.py` `CONFIRMATION` texts. **UNCONFIRMED** for exact wording.
- `prompts/md_report_composer.md`, `md_report_verifier.md`, `md_report_client_edit.md`, `prompts/describe_sheet.md` — listed by placeholder
  only; their rule text was not read in full (the analyst prompt's rules block `md_report_rules.md` was read).
- `high_level_project_changes.py` `_backend_title` defaults after line 624 — UNCONFIRMED for the rest of the defaults.
- `version_comparison_ai/settings.py:191–205` (switch file for `sheet_changes`) — read only at the signature level.
- The frontend and the version-comparison router (`api/routers/version_comparison*.py`) — not read; so the UI labels above are the strings
  the backend produces, not the text the page shows, except where the router quotes them.

Files read in full at the line level: `expert_review.py` (project_change_v3), `sheet_link_repair.py`, `document_matching.py`
(most of it), `text_ai_reviewer.py` (validation and prompt), `project_change_summary.py` (validation and artefact), `executor.py` (command and errors).

Files read at the signature and constant level, with the decisive rules quoted: `text_comparison.py`, `text_fact_producer.py`,
`text_differences.py`, `high_level_project_changes.py`, `spec.py`, `specification_run.py`, `specification_compare.py`,
`specification_structure.py` (validation), `md_report/runner.py`, `md_report/stages.py`, `md_report/settings.py`, `md_report/client_edit.py`,
`sheet_match.py`, `packet.py`, `prompt.py`, `validate.py`, `sheet_changes/run.py`, `sheet_changes/pack.py`, `sheet_changes/validate.py`,
`sheet_changes/schema.py`.
