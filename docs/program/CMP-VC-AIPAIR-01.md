# CMP-VC-AIPAIR-01 — the AI check of the doubtful sheet pairs: questions with images, content-keyed answers, accepted AI links by rule, hints

Written 2026-10-29 by the Sonnet lane `CMP-VC-AIPAIR-01` (branch `agent/cmp-vc-aipair-01`, base `0f6a008d` on `integration/compare-modules`; nothing pushed, nothing merged). Task file: [`tasks/CMP-VC-AIPAIR-01.md`](tasks/CMP-VC-AIPAIR-01.md). Decisions cited are those of [`ADR-0025`](../architecture/adr/ADR-0025-comparison-modules.md) (3, 4, 10, 11, 14, 16, 18, 19, 20, 23); the plan is [`dispatch/COMPARE-MODULES-PLAN.md`](dispatch/COMPARE-MODULES-PLAN.md) (`A-3`, `A-6`, `A-12`, `R3-02`, `R3-10`); the seal is [`CMP-SEAL-C2.md`](CMP-SEAL-C2.md) (sections 3, 4, 8, 9); the core it builds on is [`CMP-AI-JOBS-01.md`](CMP-AI-JOBS-01.md) (section 2); the wave brief is [`dispatch/CMP-WAVE-C2.md`](dispatch/CMP-WAVE-C2.md). The original is `SU10KAZ/PDF-proverka` at commit `23f379fd`: `backend/app/services/version_comparison_ai/sheet_match.py` (cited as `sm:LINE`), `.../settings.py` (`st:LINE`) and `tests/test_version_comparison_sheet_match.py` (`smt:LINE`), read as data from `raw.githubusercontent.com` into a scratch directory outside git; nothing of it is committed.

## 1. Result

The seven operations `estimateComparisonAiPairCheck`, `getComparisonAiPairCheck`, `startComparisonAiPairCheck`, `pauseComparisonAiPairCheck`, `resumeComparisonAiPairCheck`, `cancelComparisonAiPairCheck` and `listComparisonAiPairHints` are served by `ComparisonAiPairAdapter` over `ComparisonAiPairService` and the shared AI-job core. The work kind `comparison_pair_check` has a handler in `HANDLER_FACTORIES`. `comparison_ai_pair_question`, `comparison_ai_pair_answer` and `comparison_ai_link` are written, by this lane only, and leave `SEALED_NOT_YET_WRITTEN`.

* The **doubtful cells** of a document set's effective matrix become **questions**: a sheet whose cell in the next version is `unmatched` with candidates (`no_pair`, up to four candidates) and a pair of `medium` confidence (`medium_pair`, the algorithm's page and its neighbours). A sheet an expert placed, a specification sheet, a sheet inside a table group «▤», a cell the model already settled and a page with no stored preview are not asked.
* A question is **sent with pictures**: the sheet and its candidates, the stored page previews through the C0 image channel (`attach_images`), sheet first, with opaque crop references; at most five pictures, far below the executors' eight.
* The answer is **stored once under a content key** (project, prompt version, pinned model, provider mode, the digest of the exact prompt and of every picture) and **never sent again**.
* It is **accepted** — written as a `comparison_ai_link` row, `confidence` `high`, bound to the build and to the cell state it answered (`unmatched`) — only with a high answer whose candidate number and page agree, a sheet outside a multi-sheet specification, a B that no row pairs with an A sheet, no other sheet of the version choosing the same B, and a **reverse question** (asked from B back to A's version) that returns A with high confidence. Every other answer is a hint (`hint_*`, `none`, `answer_mismatch`, `medium_*`), shown as «🌙 ИИ: вероятно стр. N» or «ИИ ?»; a manual edit always wins in the effective matrix.
* The counts are «вопросов · пар · подсказок · против» (`ComparisonAiPairCounts`).
* The model's answer never rewrites the deterministic result: the lane writes only its three tables, and a test reads the stored build back unchanged. (A model's SAME on a CHANGED fragment, ADR-0025 decision 20, belongs to the sheet-description lane; a sheet *pairing* has no such status.)

## 2. Base facts, printed before any edit

Contract `1.11.0`, **176 paths / 198 operations / 517 schemas**, `VERSION` `0.9.0`, head `0040_comparison_ai_reports`, base `0f6a008d91f4fbdf1fd7a3b2561dae57392fa8da` (`P-01` of the task file). Equal to the brief's premise, so the lane went on. Nothing in `contracts/**` or `db/migrations/**` was changed; no column was missing.

## 3. What was built

`src/auditmanager/comparison/ai_pairs/` (new, 2 242 lines in 10 modules):

| module | what it holds |
| --- | --- |
| `model.py` | the vocabulary: kinds, decisions (pinned to the migration and to the contract by tests), limits, `Question`, `QuestionPage`, `PageFacts`, `Answer` |
| `questions.py` | `derive_questions`: the doubtful cells of an effective matrix (pure), `paired_pages`, the specification test (`is_spec_page`, `is_multi_sheet_spec`), `askable` |
| `decide.py` | the acceptance rule (pure): `pick_of`, `reverse_candidates`, `needs_reverse`, `decide`, `mark_shared` |
| `prompt.py` | the port of the prompt, the answer schema, `build_request` (the one author of a request), `validate_answer` (the strict validator) |
| `plans.py` | `forward_plan`, `reverse_plan`, `content_key`: what one call asks and the key its answer is stored under |
| `repository.py` | the only writer of `comparison_ai_pair_question`, `comparison_ai_pair_answer`, `comparison_ai_link`; the reads of page facts, answers, hints, figures, work-item states |
| `method.py` | `PairCheckMethod` (`AiMethod`: `counts`, `work_items`), `load_snapshot` (the effective matrix of a build) |
| `handler.py` | `PairCheckHandler` (kind `comparison_pair_check`): the `ask` item, the `close` item, `ModelBinder` |
| `service.py` | `ComparisonAiPairService`: the seven operations over `ComparisonAiJobService` |

Wiring (the hunks of wave brief rule 4, minimal): `bootstrap/adapters.py` (the body of `ComparisonAiPairAdapter`, module flag first in every method), `bootstrap/composition.py` (**one constructor**: `ComparisonAiPairAdapter(sessions, blob_store=store, comparison_modules=..., provider_mode=_provenance_mode(...))`), `comparison/public.py` (one import block, the line `pair_check_handler` of `HANDLER_FACTORIES`, seven names), `scripts/recovery/grant_classification.py` (`comparison_ai_link`, `comparison_ai_pair_answer`, `comparison_ai_pair_question` leave `SEALED_NOT_YET_WRITTEN`), `tests/integration/composition/{test_comparison_ai_stub_operations,test_router_answers,test_an_absent_parent_is_not_an_empty_page}.py` (seven operations into `WIRED`; three rows out of `SEALED_STUB_GETS` and of `SEALED_STUB_ADDRESSED`), `tests/unit/comparison/engine/test_handler_unit.py` (the kind in the shipped list). `api/routers/ports.py` and the router needed no change; `tests/unit/comparison/work/test_composition_unit.py` pins its kinds by membership of a stand-in tuple and needed none.

Tests: `tests/unit/comparison/ai_pairs/**` (4 files, 73 tests), `tests/integration/comparison/ai_pairs/**` (`conftest.py`, `pairs_support.py` and 6 files, 54 tests).

### 3.1 How the job runs (and why there is a closing item)

`startComparisonAiPairCheck` calls the core's `start`; the core asks the method for the first work items inside its transaction. `PairCheckMethod.work_items` writes one `comparison_ai_pair_question` per doubtful cell (`queued`) and answers one **`ask`** item for each (unit key `q:<question id>`, the question in its payload); it also enqueues one **`close`** item.

* An `ask` item makes up to two calls: the forward question and, when the answer can be accepted (`needs_reverse`), the reverse one. Each call is `ComparisonModelCaller.call`: the journal row is `prepared` before the request, the ceilings and the consent are checked before it, an unknown outcome is never retried. A stored answer (by content key) is used with no call. The item stores the answers on the question (it stays `queued`) and decides **nothing**, because one decision depends on the others.
* The **`close` item** is not linked to the job (`comparison_work.comparison_ai_job_id` NULL), on purpose: the core's progress counts the job's items as its units, and `complete_if_drained` counts *every* live item of the job, so no item of the job can complete the job from inside — it is itself live (FIX item 2). The closing item yields while the job is not running or any question item is live, and then, **in one transaction** under `WorkItem.require_current`, decides every question, writes the accepted links, ends the questions (`answered`, `failed` or `cancelled`) and completes the job. A cancelled or failed job's pending questions end `cancelled`; nothing is decided.
* The decision reads the effective matrix **as it is when the job closes** (`decide_job`): `multi` and `taken_b` are read again (`taken_b` is every page of B that stands in a row with a sheet of A now), so a B an expert paired meanwhile is only a hint, and a cell settled meanwhile is never turned into a link.

### 3.2 The original's rules and prompt, ported with their lines

`sm` = `sheet_match.py`, `st` = `settings.py`, `smt` = `tests/test_version_comparison_sheet_match.py`, all of commit `23f379fd`.

| rule | original | here |
| --- | --- | --- |
| a pair is accepted only if: high, number and page agree, not inside a multi-sheet specification, B not linked to another A, no other A chose the same B, the reverse question returns A with high; otherwise a hint; manual edits win | `sm:11-15` (docstring) | `decide.py` module docstring and `decide` |
| `review` question: A has a sheet, B's cell is `unmatched` with candidates; candidates sorted, at most 4, not specification sheets | `sm:151-158` (`:154` `[:4]`) | `questions.derive_questions` → `no_pair`; `MAX_CANDIDATES_NO_PAIR` |
| `medium` question: the algorithm's pair at medium confidence, not manual, not a bridge; candidates `{b} ∪ {b−1, b+1}` that exist and are not specification sheets | `sm:159-165` | `medium_pair` |
| a sheet placed by an expert is not asked | `sm:145` | `confidence == "manual"` skip |
| a specification sheet is not asked and not a candidate; `multi` = a specification sheet whose neighbour is one | `sm:118-121`, `:148-150`, `:154`, `:164` | `is_spec_page`, `is_multi_sheet_spec`, `askable` |
| a sheet inside the range of a table group «▤» of the pair of versions is not asked | `sm:132-134`, `:152-153` | `group_a` range |
| `taken_b`, the candidates of B's own cell (`back`) | `sm:135-139` | `paired_pages`, `Question.back` |
| the prompt (Russian, the original's wording) | `sm:171-202` | `prompt.build_prompt` |
| the answer schema `choice`, `page`, `confidence`, `reason` | `sm:46-49` | `prompt.ANSWER_SCHEMA` (pinned equal by a test) |
| the answer is stored by content and reused; stored only when usable | `sm:234-254`, `:287-289`; `st:259-263` (prompt version, model, effort, width) | `plans.content_key`, `store_answer` (adds project and provider mode) |
| `pick_of`: `0` none, `−1` number and page disagree, `None` no answer | `sm:306-315` | `decide.pick_of` |
| `reverse_cands`: B's own candidates (≤ 3) and A, or A's neighbours | `sm:318-324` | `decide.reverse_candidates` |
| `decide`: `failed`, `mismatch`, `medium_*`, `none`, `hint_table`, `hint_confidence`, `hint_taken`, `hint_reverse`, `accepted` | `sm:326-350`, labels `:51-65` | `decide.decide`; `accepted` = `link_accepted`, `mismatch` = `answer_mismatch`, `hint_double` = `hint_shared` |
| the reverse question only where it can decide: high, not a table, B free | `sm:558-568` | `decide.needs_reverse` |
| two sheets of one version that chose the same B are both only a hint | `sm:595-601` | `decide.mark_shared` |
| an accepted pair is an `ai_link` edit with the note «ИИ» | `sm:607-608`, `:612` | a `comparison_ai_link` row read by the effective matrix, cell `confidence` `ai` |
| a start needs the consent; pause lets begun questions finish; cancel | `sm:416-419`, `:464-471`, `:455-461` | the core: consent digest, pause, cancel |
| the original's own tests (`test_decide_rules`, the job tests) | `smt:51-67`, `:132-241` | `test_decide.py::test_the_originals_decide_rules_case_for_case`, the integration flow tests |

**Where this port differs from the original, each deliberately:**

1. **No caption band on the pictures** (`sm:215-232`, a yellow band with «ЛИСТ A» / «КАНДИДАТ n — стр. N» burned in; the original's docstring says the model confused the pictures without it). A labelled copy would be a blob that no table owns and nothing can delete (ADR-0025 decision 9: no eviction), and the pull channel fetches a picture by the blob id of its descriptor. The pictures here are the page profiles' own stored previews (long side 1400 px, `PREVIEW_LONG_SIDE_PX`, against the original's 1800 px thumbnails), and the prompt says that the pictures come in the order of the list (the paragraph at `sm:197-198` is replaced; `PROMPT_VERSION` is `cmp-pair-p1`, not the original's `vcsm-p3`). A test pins that the descriptor of each picture is the preview's own blob. **This is unmeasured:** the one live run per AI kind of plan `R3-19` should compare the two on a real set before the beta.
2. **No reverse question for a `medium_pair` question** (the original asks it for a high answer naming another page, `sm:562-565`, and its decision never reads it, `:332-337`): it would only spend money.
3. **Per-question items and one closing step** instead of three phases (`sm:546-621`), so that every call is its own spend and its own durable item; the decision is still made when every question has ended (section 3.1).
4. **Retries, account pauses and 30 parallel calls** (`sm:41-45`, `:265-282`, `:262`) are the spend wrapper's, the queue's and the core's: an unusable reply is `Failed(retry=True)` within the item's three attempts; a quota, an overrun and a route that changed pause the job with the contract's reasons; one call per connection at a time (`CMP-SPEND-01` decision 5), so the calls of a check run one after another on one worker slot.
5. **`taken_b` is read again when the job closes**, from the effective matrix of the question's build (the original reads it when it makes the question, `sm:135-136`).
6. **Specification sheets are recognised from the stamp** (designation ending in «.СО», or the title «Спецификация…» not naming a plan, scheme, section or detail), not from the words of the sheet; the original's kind also reads a column header of the top of the sheet (`stamp.py classify_kind`), which is in the page archive, not in the profile summary (FIX item 4).
7. The content key adds the **project** and the **provider mode**: a recorded answer is never mistaken for a live one, and an answer is never read across projects.
8. A **`doubtful` AI link is never written**: the effective matrix supports one (`answered_state` `doubtful`), the original never wrote one, and the contract's decision vocabulary gives a `medium_pair` question only `medium_*` outcomes; a model's «another page» for the algorithm's pair is a hint (`medium_other`).

## 4. Safety proofs (mutation)

Each row: the quoted mutation, applied to the file named; the lane's two directories (`tests/unit/comparison/ai_pairs`, `tests/integration/comparison/ai_pairs`) run **red**; the file restored with `git checkout`; the same directories **green**; `git status --porcelain` empty (driver `mutate.py` in the lane's scratch, outside git; one line per mutation). The set was 126 tests for the rows below and 127 after the test M6 needed. Counts are pytest's.

| # | commitment | mutation | red | restored |
| --- | --- | --- | --- | --- |
| M1 | **acceptance needs high confidence** | the `confidence != "high"` return deleted from `decide` | **6 failed** | 126 passed |
| M2 | **and an agreeing reverse answer** | the reverse test of `decide` replaced by `if False` | **8 failed** | 126 passed |
| M2b | the reverse answer must itself be high | `and reverse_confidence == "high"` deleted | **4 failed** | 126 passed |
| M3 | **never inside a multi-sheet specification** (the decision's guard) | the `question.multi` return deleted | **2 failed** | 126 passed |
| M3b | the same, the first layer: a specification sheet is not asked | the specification skip deleted from `derive_questions` | **2 failed** | 126 passed |
| M3c | a specification sheet is not a candidate | `not is_spec_page` deleted from `askable` | **2 failed** | 126 passed |
| M4 | **never over a linked B** (the decision's guard) | the `taken_b` return deleted from `decide` | **3 failed** | 126 passed |
| M4b | the guard reads the matrix **as it is now** | `replace(found, taken_b=found.taken_b \| paired)` becomes `found` | **1 failed** (the expert's link made while the job runs) | 126 passed |
| M5 | two sheets choosing one B are both hints | `> 1` becomes `> 99` in `mark_shared` | **2 failed** | 126 passed |
| M6 | **a manual edit wins over an accepted link** (the layer order) | the AI layer applied after the manual layer, `matrix/effective.py` | **survived at first** (126 passed): the AI link's own applicability conditions already refuse a cell a manual link took. The test `test_a_manual_unlink_of_the_page_an_ai_link_joined_wins_and_is_not_orphaned` (an unlink of the AI-joined page, which only the right layer order lets apply) was added: **1 failed** | 127 passed |
| M6b | an expert's cell is not asked | the `manual` skip deleted from `derive_questions` | **1 failed** | 126 passed |
| M7a | **a stored answer is never re-requested** (the handler) | the stored-answer return replaced by `if False` | **1 failed** | 126 passed |
| M7b | (the estimate) | the estimate finds no stored answer | **1 failed** | 126 passed |
| M7c | the key includes the project | `project_uid` out of `content_key` | **1 failed** | 126 passed |
| M7d | and the provider mode | `mode` out of `content_key` | **1 failed** | 126 passed |
| M8 | **at most 8 pictures** | the cap of four candidates (`[:MAX_CANDIDATES_NO_PAIR]`) becomes `[:9]` | **2 failed** | 126 passed |
| M9a | **the module gate** (the service) | `_require_versions_module` never raises | **1 failed** (all seven operations, nothing read or written) | 126 passed |
| M9b | **the module gate** (the adapter, `bootstrap/adapters.py`) | `_VersionsModuleGate._require_versions_module` never raises | **44 failed** of the lane's directories and `test_comparison_ai_stub_operations.py` | 303 passed |
| M10 | **the expert role** (the service's check) | the service's check deleted | **survives by design** (126 passed): the core refuses a non-expert too | 126 passed |
| M10b | the expert role (both layers) | with M10, the core's `_require_expert` returns | **1 failed** | 126 passed |
| M11 | **key replay** | the replay branch of the core's `start` deleted | **2 failed** | 126 passed |
| M12 | a hint never becomes a link | `hint_reverse` also writes a link | **6 failed** | 126 passed |
| M14 | the job is completed by the closing item | `complete_if_drained` deleted | **6 failed** | 126 passed |
| M15 | the closing item waits for every question | the wait deleted | **1 failed** | 126 passed |
| M16 | the overrun pause | `pause_for_spend` after a call that overruns replaced by `False` | **1 failed** | 126 passed |
| M17 | the number and the page must agree | the `answer_mismatch` return deleted from `pick_of` | **4 failed** | 126 passed |
| M18 | no reverse question where the decision never reads it | the `medium_pair` return deleted from `needs_reverse` | **4 failed** | 126 passed |
| M19 | the hint's stale flag | `IS DISTINCT FROM` becomes `IS NOT DISTINCT FROM` | **1 failed** | 126 passed |
| M20 | a reply that is not the schema is no answer | the choice/page/confidence range test deleted from `validate_answer` | **4 failed** | 126 passed |
| M21 | an answer is looked up within its project | the project filter deleted from the stored-answer statement | **23 failed, 22 errors** | 126 passed |

Self-checks that fail without an edit of the tree: `test_that_check_fails_when_the_module_flag_is_ignored` and the other self-checks of `test_comparison_ai_stub_operations.py`; `test_the_originals_decide_rules_case_for_case` (the original's own cases); the AST test that the module flag is the first statement of each of the seven operations of the adapter and of the service. The mutation runs were made on the tree of `ce343e51`; `540e77ba` added only the test that M6 needed (and M6 was re-run red with it), and `893d2e5f` reworded two docstrings and two test fixtures (section 5). The driver lived in the lane's scratch, which did not survive a restart of the session; the table is its output.

## 5. Checks (light acceptance)

`df -h /` before the stack and before each long run (7.9 to 9.2 GiB free, never near the 2.0 GiB line); the stack is the lane's own (`auditmanager-cmp-vc-aipair-01`, ports 57960 / 61960 / 61961, head `0040`, brought up again after a restart of the session). All runs: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q -p no:cacheprovider --basetemp=/tmp/pytest-cmp-vc-aipair-01/<run> <path>` with `set -a; . ./.env; set +a`, the basetemp removed afterwards; the runs were serial, one at a time, and nothing edited the tree while one measured.

**Two batteries.** The first (tree `540e77ba`, the lane's last test commit) found three reds that the lane's own directories could not: the two composition sweeps (`test_every_get_that_names_a_parent_refuses_an_identity_that_names_nothing`, `TestNoOperationAnswersWithAServerFault::test_every_declared_get_answers_without_an_internal_error`: they build the application with the module off, where a wired C2 read answers the module flag's `503` before it can answer `404`), the core's `test_only_the_cores_repository_writes_the_job_table_and_no_lane_does` (a docstring of this lane named an `UPDATE` of the job table) and the surface-count prose guard (`test_the_api_prose_states_the_surface_this_document_declares`: «seven operations» in two docstrings). `893d2e5f` is the fix (the two sweeps build the application with `AUDITMANAGER_COMPARISON_MODULES=versions`, two docstrings reworded); the second battery, on the clean tree `893d2e5f` (the last code commit), is green.

| what | command (path) | result |
| --- | --- | --- |
| diff hygiene | `git diff --check 0f6a008d..HEAD` | exit 0 |
| this lane, unit and integration | `tests/unit/comparison/ai_pairs tests/integration/comparison/ai_pairs` | **127 passed** (73 unit, 54 integration), 10 s |
| the whole comparison integration directory, **one process** | `tests/integration/comparison` | **707 passed**, 1 warning, 405 s (`CMP-AI-JOBS-01` measured 653; this lane adds 54) |
| the composition files this lane touches, on the final tree | `tests/integration/composition/test_router_answers.py test_an_absent_parent_is_not_an_empty_page.py test_comparison_ai_stub_operations.py` | **203 passed**, 1 skipped, 18 s |
| the **whole composition directory**, first battery (tree `540e77ba`) | `tests/integration/composition` | 2135 passed, 5 skipped, **2 failed** (the two sweeps above, 39 min); not repeated as a whole after `893d2e5f`, which changed only those two files' fixtures and docstrings, and the three files above were re-run in full on the final tree |
| the classification | `tests/integration/recovery/test_grant_classification.py`; `scripts/recovery/grant_classification.py --verify-script infra/deploy/apply-grants.sh` | **35 passed**; exit 0 |
| the whole unit battery, after the last code commit | `tests/unit` | **5117 passed**, 76 skipped (none of this lane's), 1 warning, 332 s (`CMP-AI-JOBS-01`: 5044; +73 are this lane's unit tests) |
| the contract battery, after the last code commit | `tests/contract --ignore` of `test_cp00_candidate.py`, `test_validate_bootstrap.py`, `test_cp00_final_state.py` (`D-220`) | **1310 passed**, 19283 subtests passed, 173 s |

## 6. Limits, risks, FIX items

**FIX items for the wave's FIX slot or the integrator** (none blocks the merge; 1 and 3 decide whether the pair check is usable live):

1. **The worker has no way to bind a routed connection to an adapter.** `WorkDependencies` carries neither the private ring nor the destination policy, so a handler cannot call `executors.runtime.bind_connection`. The handler takes a `ModelBinder` (`(session, job) -> CallRoute`) and, without one, a live item fails loudly with `model_binder_missing` (no fall back). The one thing the integrator wires: in `build_comparison_work` (or where `COMPARISON_HANDLER_FACTORIES` is applied) build `PairCheckHandler(deps, binder=...)` with a binder made the way `DatabaseProviders.resolve` makes its binding (`bind_connection(session, job.connection_revision_id, ring=, policy=, context=, runtime=)`, then `CallRoute.from_binding(adapter, CallBinding(...), pin)`); the three other AI lanes have the same gap. Every test, and a recorded process, uses a binder of its own over `RecordedAnswers`.
2. **`ComparisonAiJobService.complete_if_drained` cannot be called by the last item of a job** (its own item is live). This lane works around it with a closing item that is not linked to the job (section 3.1). A parameter `excluding_work_id` on the core's method would let a lane complete from the last item; nothing else depends on it.
3. **A job with no call to send cannot start** (`comparison_ai_nothing_to_do`), so the answers stored for one build are not applied to a **rebuilt** matrix while every question is `reused`: the accepted links of the old build read `superseded`, and a new check of the new build has nothing to ask. Applying stored answers costs nothing; either the core should accept `calls == 0` when `reused > 0`, or an apply step should run after a build. Not done here (the core and the matrix are other lanes' files).
4. **The page profile's summary has no `kind`**, and the matrix computes it (`PageFeatures._kind`) without storing it, so a specification sheet is recognised from its stamp only (section 3.2, difference 6). Storing `kind` per page (an additive member of the stored build's cells or of the profile summary) would restore the original's rule exactly.
5. The router's docstring and the OpenAPI descriptions of the seven operations still say «Sealed as a stub by `CMP-SEAL-C2` … until `CMP-VC-AIPAIR-01` wires it» (the same stale text `CMP-MATRIX-01` §9 item 7 reported); contract text changes only in a seal or a FIX.

**Limits.**

* The estimate is an **upper bound**: a forward call that is not stored is counted with the heaviest reverse call its question could need, because whether a reverse question is asked depends on the answer; the real spend is lower. The token conversion is the core's `[own design]` (2.5 characters per token, 1600 per image); `MAX_OUTPUT_TOKENS` (1 200) is `[own design]` and is what the estimate prices every call's output at.
* The calls of a check run **one after another** (one call per connection at a time), where the original ran 30 at once; a check of a few hundred questions is a long job, visible in the queue. Throughput is not measured (no live call was made).
* A job paused while an `ask` item is in flight leaves that item `queued`; it looks at the job again every 60 seconds (a yield spends no attempt) until the job is resumed.
* `listComparisonAiPairHints` lists the questions that have a decision, of **every** job of the document, newest first; a client joins them to cells by `(version_uid, page_number)` of `page` and `version_uid` (seal section 3 decision 4) and takes the newest, and `stale` says the question was asked of an older build.
* A cell that is no longer in the state it answered when the job closes (an expert linked it, an earlier check settled it) is `hint_taken`, never a link.
* `get` and the hints are read-only and need no ready matrix; the estimate and the start do (`409 comparison_matrix_stale`).
* The HTTP tests commit a document set, a matrix build, an executor route for the work kind and a cancelled job to the lane's database (the application reads through connections of its own); they are written to be repeatable in one database (a key per run, counts scoped to the project). The route event is append-only and stays: a suite that wants an unrouted kind injects a route reader, as the core's suite and this one do.
* **No live model call was made, ever.** The money tests use a scripted adapter that says `live` and calls nothing.
* `AGENTS.md` §8 case 3 names a `conftest.py` and the composition root: this lane adds `tests/integration/comparison/ai_pairs/conftest.py` and edits `bootstrap/**`, so the full gate on the merged candidate covers them; `R-135` defers the gate. Not run: `make gate`, the web battery (no web change), the live journey.
* **Environment trap found:** the lane's `.env` needs `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` equal to `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` (the comment of `.env.example` says so; `make up` does not check it): with other values the stack starts and every test that reads the object store fails with `dependency_credential_refused`, which reads like 180 real reds.
* **Commit trailer.** The commits carry `Claude Sonnet 5.5` (the attribution line the harness gave this session), not the `4.6` of the brief's template; the integrator may rewrite it on merge.

## 7. Notes for the next lanes

**`CMP-VC-QUEUE-01`** (the step `ai_pairs` of a launch entry): build `ComparisonAiPairService(session_factory, blob_store=, comparison_modules=, provider_mode=)` (exported from `comparison.public`). `estimate(project_uid=, document_uid=)` is the consent digest to store (`needs_consent` while the entry holds none); it raises `409 comparison_matrix_stale` for a matrix that is not ready (the step waits for step 3), and `start` raises `409 comparison_ai_nothing_to_do` when every question is answered or nothing is doubtful (the step is `done`, not failed). `start(..., consent=AiConsentInput(digest, True), user_uid=, actor_roles=, idempotency_key=)` is the one write; `get(...)` carries the latest job and its counts; the installation's AI queue is `service.jobs.waiting()` (a pair-check job is `method` `pair_check`). A check holds its document: a second start is `comparison_ai_job_active`.

**`CMP-VC-UI-02`** (step 4 and the matrix cells): «4 ИИ-проверка сомнительных пар» is `getComparisonAiPairCheck` (`job.state`, `job.counts` for progress, `counts` for «вопросов N · пар N · подсказок N · против N»: `questions`, `pairs`, `hints`, `against`; `failed` and `reused` are extra). «Проверить» is the estimate dialog, then `startComparisonAiPairCheck` with the digest and `confirmed`; «Пауза» / «Продолжить» are pause / resume (after `overrun` or `route_changed` the resume carries a new consent for what is left). The cell's «ИИ» label is the matrix's `confidence` `ai` (an applied accepted link, with `ai_link_id`); «🌙 ИИ: вероятно стр. N» is `hint_page` of a hint whose `decision` is one of `hint_table`, `hint_confidence`, `hint_taken`, `hint_shared`, `hint_reverse`, `medium_weak`, `medium_other`; «против» (`none`, `medium_none`), `answer_mismatch` and `failed` are not hints about a page. Join a hint to a cell by `(page.version_uid, page.page_number)` → the cell of `version_uid`; show a `stale` hint dimmed or not at all. Every `reason` is the model's own sentence and carries the «не подтверждено инженером» label; a job whose `estimate.route.provider_mode` is `recorded` produced recorded (test) answers and says so.

## 8. Instructions for the integrator

1. Merge in the wave's order (AI-JOBS, SPEC, **AIPAIR**, AISHEET, REPORT, QUEUE, UI-02). The hunks in shared files are line-local: `adapters.py` (the body of one class), `composition.py` (one constructor), `public.py` (an import block after the AI-job core's, one line of `HANDLER_FACTORIES`, seven names at the top of `__all__`), the three composition registers, `grant_classification.py` (three names). In `test_comparison_ai_stub_operations.py` three tests named `startComparisonAiPairCheck` and one the pair-hints path; they now take the first operation still sealed (`STUBS[0]`), the hints path gets its own three lines (`422`, `422`, `404`), and the unconfirmed-consent line expects the lane's own `422`: a later lane that wires its operations keeps `STUBS[0]` and needs no further edit there.
2. FIX items 1 to 5 of section 6; 1 and 3 before a live check.
3. The stack of this lane is `auditmanager-cmp-vc-aipair-01`; it was brought down with `make down` and its two volumes (`auditmanager-cmp-vc-aipair-01-postgres-data`, `-s3-data`) were removed by exact name; the lane's git-ignored `.env` was deleted.

## 9. Proof that the forbidden hotspots were not touched

`git diff --name-only 0f6a008d..HEAD` lists only (the three composition register tests include the two sweeps' fixtures, `893d2e5f`): `src/auditmanager/comparison/ai_pairs/**` (new), `src/auditmanager/comparison/public.py`, `src/auditmanager/bootstrap/adapters.py`, `src/auditmanager/bootstrap/composition.py`, `scripts/recovery/grant_classification.py`, the three composition register tests and `tests/unit/comparison/engine/test_handler_unit.py` (the wiring hunks of the wave brief's rule 4 and the sweeps' module setting), `tests/unit/comparison/ai_pairs/**`, `tests/integration/comparison/ai_pairs/**`, `docs/program/CMP-VC-AIPAIR-01.md` and `docs/program/tasks/CMP-VC-AIPAIR-01.md`. Nothing under `contracts/`, `db/migrations/`, `src/auditmanager/comparison/{ai_jobs,matrix,work,spend,profile}/`, `src/auditmanager/api/`, `src/auditmanager/jobs/`, `src/auditmanager/executors/`, `src/auditmanager/workers/`, `src/auditmanager/analysis/`, `infra/`, `web/`, `pyproject.toml`, `uv.lock` or `web/FRONTEND_LOCK.json`; no other `conftest.py` and nothing in `tests/support/`. (The mutations of M6, M9b, M10b and M11 edited `matrix/effective.py`, `bootstrap/adapters.py` and `ai_jobs/service.py` for the length of a run; each was restored with `git checkout` and the tree was clean afterwards.)
