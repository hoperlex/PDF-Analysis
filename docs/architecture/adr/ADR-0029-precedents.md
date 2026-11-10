# ADR-0029: Precedents — a model-free core that serves the AI critic through the client and the expert in «Разбор»

- Status: accepted by the repository owner by direct polls of 2026-11-10 (`R-153q`…`R-153ar`, `docs/program/OWNER_RULINGS_2026-09-17.md` section 3.55). The product decisions are the owner's; the engineering choices inside them are the planner's. Two decisions are **temporary** and carry an end condition (section «Temporary decisions»). Revisable by a dated addendum.
- Date: 2026-11-10
- Owners: repository owner / the «Прецеденты» programme integrator
- Amends: `ADR-0027` decisions 2, 3 and 6 (addendum there, 2026-11-10) and `DECISION-MEMORY-01` (Q4, Q8, Q9, Q10, section 5.3, phase M4; short dated notes there). It rewrites no text of either.
- Related ADRs: `ADR-0027` (decision memory), `ADR-0028` (hosts and the stage layout), `ADR-0020` (pgvector, the embedding producer), `ADR-0021` (one host, no managed database), `ADR-0024` (AI execution), `ADR-0026` (the pull channel)
- Plan and lanes: the plan is a working document of the integrator (git-ignored); this ADR carries its decisions and each lane has a task file under `docs/program/tasks/`. A task cites «ADR-0029 decision n» instead of re-deciding it.

## Context

The owner asked for expert decisions already kept in the decision memory (`ADR-0027`) to work for the product (`R-153x`, `R-153r`): the AI critic gets the norm reference and, later, similar cases; the expert sees in «Разбор» a neutral mark, a collapsed «Рекомендовано снять» queue, other experts' comments and «Возможные нормы». What the tree has:

- the memory holds cases, comments inside a decision, forget, withdraw and restore (`ADR-0027`, phases M1 and M2); it has no vectors and no read that compares cases;
- a run started under the stage layout carries a frozen `stage_plan` (`ADR-0028` decision 5); a legacy run has none (`src/auditmanager/runs/executor.py:816`);
- the AI critic exists only in the extended-review plan v3; on the base of this ADR the plan v2 has no critic (`rows_in_use` in `src/auditmanager/runs/stage_layout.py`), and the AR v3 removal wave gives it the original's deterministic critic and corrector, without a model (`R-154f`);
- the gate publishes only text findings to «Разбор» (`src/auditmanager/findings/publication.py:131`); the candidates of the extended review stay machine observations outside the expert's list;
- the executor client receives only what its task holds, and the CLI tools of the agent are closed (`tools/executor-runner/claude_answer.py:501`, `tools/executor-runner/codex_answer.py:402`);
- the production host has 4 GB (`R-146ad`); the encoder of the norm corpus peaks at 3 177,9 MiB (`docs/program/NORM_EMBEDDING_BAKEOFF.md:62`); `infra/deploy/compose.server.yml` sets a memory limit only when `ALPHA_MEM_LIMIT_<SERVICE>` is given, and none is.

The owner took no measurements before building: «Замеры: никакие, сразу строим» (`R-153an`). What is taken without a measurement is listed in section «Accepted risks».

## Decision

1. **One model-free core, in a new bounded context `precedents`.**
   - It imports only the `public` module of any other context. It never calls a model.
   - It is the single place that decides who votes, which mark a finding gets and which hint it shows. Both consumers read it; neither re-implements it.
2. **Two consumers, one writer of verdicts.**
   - The AI critic reads reference material through the executor client (decision 3).
   - The expert reads marks, the queue, comments and «Возможные нормы» in «Разбор» (`R-153x`: «И то, и другое»).
   - The decision ledger is written only by the expert (`src/auditmanager/decisions/ledger.py:9-14`). A mark is advice; the expert's ✓/✕ decides. «Отмена» is a mark and a collapsed queue, never an automatic withdrawal (`R-153r`: «Метка + свёрнутая очередь»).
3. **Prompts stay static; the client brings the data.**
   - The stand answers a task's `context_request` (kind `similar_cases` or `patterns`); the client appends one block after the JSON of `user_text`, headed `=== СПРАВОЧНО (не основание) ===`, and echoes its digest in the answer. Nothing is inserted before the task text.
   - A context failure never fails the task: on a refusal, a timeout or a 5xx the client calls the model without the block and says so in one line. The `Retry-After` rule of the runner API does not apply to context.
   - The CLI tools stay closed; an MCP server is a later experiment (`R-153y`: the client supplies, MCP «позже», and not for the legacy).
   - The consent freezes an `executor_context_policy` built like `norm_paragraph_context_policy`, only when the «контекст критику» switch is on (`R-153v`: «Политику, как для норм»). The policy names the kinds, the scope, the budget (two requests and 12 000 characters per task, a retry costs nothing) and the method.
   - The prompt paragraph that explains the reference block is added only to runs that carry a `stage_plan`. Because `analysis/extended/review.py` is part of the rules digest, a deploy of that paragraph changes `rules_sha256` of every v3 run: it ships with an empty v3 queue or with a note about the new consent.
4. **Who votes, and the similarity that counts.**
   - **Corpus:** cases of the memory of the **same section**; active at the moment of reading (a withdraw or a forget acts at once, not overnight); the same `data_class`; verdict ✓ or ✕; within 24 months. A case without a section does not vote.
   - **One vote per case**, its latest verdict. A comment lives in its own table and never changes a vote. A `carried` decision does not vote on its own; an imported one votes as «without a shown mark».
   - **Not the same run.** From one version of a document at most two votes: the most similar, and on a tie the smaller `case_id`.
   - **Independence.** A vote is independent only if, at the moment of the decision, no refusal mark was in force on that finding and no «история документа» fact was shown. «In force» is what the server issued for that finding at that moment, counting the council revision and the switches; capture writes it into `decision_memory_decision`. What the expert actually saw cannot be proved, and this ADR does not claim it.
   - **Similarity:** only the profile `bge-m3-dense-v1`; cosine ≥ 0,85 is «аналогичное» and is a vote; ≥ 0,75 is «похожее» and is for comments; ≥ 0,92 within the same document is the history fact. The figures are starting values; the replay (decision 6) adjusts them. Search is an exact scan inside the section; no vector means «Недоступно» with no fallback (`R-153ac`: «"Недоступно" до векторов»). The encoder input is the view `finding_v1`: category, finding text and the head of the recommendation, at most 1 000 characters, so that it stays under the 512-token limit at which the encoder refuses; a cut is marked.
5. **Marks, «снять» and their protections.**
   - Marks: `often_rejected` (at least 5 votes, at least 80 % refusals), `likely_accepted` (the same for acceptance), `mixed` (at least 5 votes, both verdicts present, neither share reaches 80 %), `few`/`none` (no mark in the row). Unanimous refusals never give `mixed`.
   - **`cancel_suggested` is a part of `often_rejected`** and needs all of: at least 5 independent votes (`R-153ad`: «≥5, ≥90 %, 2 проекта»), at least 90 % refusals, the latest vote a refusal, votes from at least 2 projects, **the finding was reviewed by a critic (the AI critic in plan v3, the deterministic critic in plan v2) and that critic did not veto** (`R-153ar`: «Не разбирал — не предлагать»), and none of the owner's stop-words in the finding text or its recommendation (`R-153ae`: «Вето ИИ + стоп-слова»).
   - **The core takes «critic in plan» and «reviewed» as inputs.** Mapping a plan's critic output (the AI critic's records in v3, the deterministic critic's results in v2) to them is the work of the pass (`PREC-PASS`), not of the core.
   - **Reviewed** means at least one linked candidate carries a critic record; **veto** means any linked candidate got `accept` or `needs_human`. A text finding is linked to the candidates whose sources include its `primary_text_<key>`; a candidate finding is linked through `extended_observation_ref`. Each candidate stores `context_kinds`, the reference kinds the critic saw, so a veto is not an echo of the same neighbours.
   - **A finding outside the AI critic's window** (at most 40 records and 16 000 characters; the rest is marked `outside_critic_window`), or that no critic reviewed, gets only the neutral line «Прецедентов: N (критик не разбирал)» and never enters the queue.
   - Stop-words are an administrator's list matched by word stems; a match hides «снять».
   - **Hints** (at most 2 per finding, no model text in them): P1, the reason for refusals (a refusing vote's comment, later an approved pattern), only under `often_rejected` or `cancel_suggested`; P4, the critic disagrees (exactly one linked candidate whose advice contradicts the mark); P5, document history (a vote from an earlier version of the same document at cosine ≥ 0,92; a neutral fact, and a shown refusal ends that vote's independence).
6. **Switching on is by section, from a replay report; every switch is off by default.**
   - The replay tool (`CRIT-REPLAY-01`) is a product tool, not a measurement. It cuts the history by time (70 % early to tune, 30 % late to check), leaves decisions made under a shown refusal mark out of the «снять» check, and reports the base refusal rate, the gain over it, the precision of «снять» and the harm (accepted findings it would have hidden).
   - A section may show refusal marks when precision is at least 0,90 on at least 30 cases, the gain at least 0,15, the harm at most 2 % and zero on protected findings (`R-153ah`: «По разделам»). The administrator turns it on from the report; the journal row carries the report's digest. Neutral marks are shown at once.
   - Three switches, journalled in `precedent_setting_event`, all off: «один список», «контекст критику», marks per section. A run's publication mode is frozen by a marker at its start, so a switch acts on new runs only.
7. **«Один список»: the extended-review candidates become findings in «Разбор» (`R-153al`).**
   - A new publisher turns a group of N observations into one finding; the canonical observation is the first member. Categories `drawing_discrepancy` and `cross_source` are added; a mixed group is `cross_source`. A group that is wholly `primary_text_*` is not published twice.
   - **Gate v2.** A block as evidence is accepted when its `blk_` is in this run's geometry, the crop's sha matches `page_crops`, and a quote, if present, is verbatim in that block's recognised text. **Block grounding proves a place, not a content.** For block evidence the refusal `quote_in_recognised_text` of the text gate (`db/migrations/versions/20261016_0023_norm_citations.py:52`) is cancelled by this decision; for text evidence the rule is unchanged.
   - Memory capture moves to `dm-capture/2` in the same release as the publisher, because capture skips empty evidence and a candidate case would be written without its block.
   - The legacy run is unchanged: it publishes text findings only (temporary decision 1).
   - The count of findings will grow; the owner took the volume without a measurement; the queue and the critic's advice are the help.
8. **Vectors: exact scan, an offline encoder in a night window, one pause (`R-153w`, `R-153ab`, `R-153ap`).**
   - No HNSW; the corpus of cases per section is small enough for an exact scan.
   - The encoder is a container of the norms-worker image run as `embed-texts`: **no database and no network**, a hard `mem_limit` that compose refuses to start without, a swap limit equal to it, a maximum `oom_score_adj`, two CPUs and two threads. It reads a file of intents (deduplicated by `input_sha256`) and writes vectors; the worker imports them with a unit-norm check. A text over 512 tokens is `poisoned` and visible to the administrator.
   - **The window** is by default 01:00–06:00 with the time zone as a setting. At its start the stand stops issuing new runs the way the analysis pause does and waits for running attempts; if they do not end before the window does, the window is **loudly skipped** with a reason. After the container exits the model is unloaded. A run started at night waits for the morning with a note.
   - **One «Пауза» button** in the top strip with two items, «Выдача анализа» and «Векторы» (`R-153w`: «ручная остановка админом доступной кнопкой (как пауза анализа в верхней панели)»). The badge «Векторы на паузе» exists only during a pause; on a pause no window starts.
9. **Norms for the critic (`R-153aa`).**
   - Paragraph text already reaches the critic in `norm_context`. The PNG crop of a norm page is declared among the task's `images` when the task is created, only from this run's norm-context paragraphs, only for a cell whose model accepts images, at most 2 per task. A Claude Code host takes no images. The render is made once from a one-page PDF and kept in `norm_crop_render`.
   - «Возможные нормы» in the finding card come from the same paragraphs and do not depend on the encoder.
10. **Comments have their own table (`R-153ag`).** `decision_memory_comment` keeps the experts' comments as content of the memory (KEEP); on a case's first ✓/✕ the earlier comments are carried into it. The forget protection refuses an insert into a forgotten case. This revises `DECISION-MEMORY-01` Q8, where `comment` was not captured.
11. **Later, in the second seal (patterns, quality, cross-document).**
    - **Failure patterns (`R-153ai`: «Предлагает алгоритм, утверждает эксперт»):** the algorithm proposes, an expert approves; an unapproved pattern never reaches P1; a pattern whose group dissolves is suspended.
    - **Cross-document parameters (`R-153aj`: «Расхождение как находка с ✓/✕»):** a discrepancy is a finding of the **newer** document's run, with the other document's evidence; there is no project-level finding (`finding_observation.run_id` and `finding.version_uid` are NOT NULL); different units are not compared.
    - **Quality of stages and models (`R-153ak`: «Таблица для администратора»):** the share of accepted findings by `stage_plan` cell and section; the model is read from the cell because `model_identity` is not copied into the memory.
12. **Seals.** The first seal is one contract and one migration for everything above that needs them: **1.51.0 / `0064`**. The AR v3 removal wave takes 1.50.0 / `0063` first (`R-154h`). The second seal (patterns, cross-document evidence, parameter facts, `parameter_mismatch`) is **1.52.0 / `0065`**. The lane ids `CRIT-SEAL-50` and `CRIT-SEAL-51` are labels kept from the plan; they no longer name the versions. Every additive change is a minor version (`docs/program/VERSIONING_AND_FREEZE_POLICY.md:11-13`). Every new table, command type and event type is classified in the recovery tools in the lane that adds it. The new events use the prefixes `precedent.` and `vector.`.
13. **Amendments to `ADR-0027` and `DECISION-MEMORY-01`.**
    - `ADR-0027` decision 6 stays in force and is refined: the memory does not import the core; the core reads the memory through `decision_memory.public` (addendum there).
    - Decision 2: tables of derived state (probes, the precedent run and advice) are `PRODUCT`; the content, comments, block evidence, embeddings and their intents stay `KEEP`.
    - Decision 3: a mark reads the verdicts of **other** cases; the verdict of the finding itself is still decided by the ledger.
    - `DECISION-MEMORY-01`: Q4 is closed by `R-153z`; Q8 is revised by decision 10; Q9(b) and Q10 are answered in part; section 5.3 and phase M4 are replaced by this ADR (short notes there).
14. **Correction after the AR v3 removal and the plan v2 critic (`R-154a`…`R-154h`).**
    - AR v3 is removed (`R-154a`). The rules that applied only to it are not built: the hints P2 (importance) and P3 (norm), and the ban on «снять» for `critical` and normative AR v3 findings.
    - The extended-review plan v3 is opt-in by `AUDITMANAGER_EXTENDED_ANALYSIS_PLAN=v3`, **default v2** (`R-154b`). On the base of this ADR `src/auditmanager/runs/preflight.py:345` still defaults to v3; the removal wave changes it.
    - Plan v2 is the original's legacy flow with the executors split per stage (`R-154e`). It gains the original's **deterministic critic and corrector**, without a model, after the norms, advice only (`R-154f`); its «Критик» and «Уточнение» rows and the critic counters show real results (`R-154g`). On the base of this ADR none of that exists yet; the AR v3 removal wave builds it as the lane `V2-ORIGINAL-REVIEW-01`.
    - **So «В3» applies to v2 and v3 in the same way:** a finding that a critic (deterministic in v2, AI in v3) reviewed and did not veto can get «снять»; a finding no critic reviewed cannot (`R-153ar`). Until the v2 critic's output is mapped, a v2 finding counts as not reviewed and gets no «снять».
    - Neutral marks, comments and «Возможные нормы» work under any plan. The critic's reference block (decision 3) works only under v3, because only the AI critic reads it.
    - The veto of `R-153ae` («Вето ИИ») is applied to the deterministic critic of plan v2 in the same way. The owner did not rule on that case separately, so this is the planner's extension, revisable.

## Temporary decisions

Each has an end condition. Neither may be taken as the final shape without a new owner decision.

1. **The legacy run stays as the legacy (plan label «В1»).**
   - A run without a `stage_plan` gets no «один список» and no reference block for the critic; it works as in the legacy original (`R-153y`: «не для легаси, легаси работает как в легаси-оригинале. Однако сделай пометку об этом в ADR как о временном решении»).
   - Why it is acceptable: this is the rollback path. The layout switch (`ADR-0028` decision 14) takes a run back to the legacy route, and the marker `publication_mode = text_only` makes that run read as before.
   - **Ends when** the layout switch is removed («After production is switched the switch is removed», `ADR-0028` decision 14) or when the owner decides otherwise.
2. **The encoder runs only at night, on our own server (plan label «В2»).**
   - While the production server has 4 GB and no measurement, the encoder is the offline container of decision 8 inside the night window, with no new runs started during it (`R-153ap`: «Ночью без новых прогонов»).
   - Its consequences: the AI critic (plan v3) gets the norm reference only and the line `Прецеденты: недоступно до переезда (временный ночной режим).` (`R-153aq`: «Критик без прецедентов»); the stand answers a context request for similar cases with `unavailable`, reason `until_move`; the expert sees precedents the next morning, with one line above the list that says so (the owner's wording: «явный комментарий к „Недоступно“: что будет доступно после переезда и что сейчас работает в ночное окно, и как работает; комментарий максимально краткий и информативный», `R-153am`).
   - **Ends when any one of these holds:**
     - the database and object storage move to Yandex and the encoder runs on a separate machine (`R-153ab`: «запланировать полный перенос на Яндекс. Пока выбрать вариант ночное окно, пометить как временное решение на локальном хранилище»; the plan is `docs/program/YC-MOVE-PLAN.md`);
     - a compressed model with a **proven vector compatibility** is built in a future task and the owner permits it;
     - the server is enlarged.
   - When it ends, the three lines of text that mention the night mode are removed. The content of the consent policy does not change, so no new consent is needed.

## Accepted risks

- **К3: the models see decisions of any project, whole, with quotes.**
  - The owner chose «Любой проект, целиком» (`R-153z`): text of one client's document can go to the provider in a call about another client's document. It falls under `D-291` and closes `DECISION-MEMORY-01` Q4.
  - The delivery journal is `KEEP`, holds no text, and survives the erase of a project.
- **The encoder is shipped without a measurement.**
  - The peak of 3 177,9 MiB sits next to services that have no memory limit. The first night is the test; a lack of memory is loud (a skipped window, a status the administrator sees), never silent.
  - Observed at first operation: the number of findings per run after «один список», the encoder's peak and the window's length, the length of the intent tail, the share of findings outside the critic window, and how Codex handles norm images.
- **Block grounding proves a place, not a content.** A block as evidence shows where the machine looked; the quote check of the text gate does not apply to it (decision 7).
- **The replay's figures are a tool, not proof, until real decisions exist.** Synthetic data proves only that the tool works; the thresholds start as the owner's «≥5, ≥90 %, 2 проекта» and the section switch is the real gate.

## Consequences

- A user-visible list grows. The release note must say that the number of findings will grow, that for runs with «один список» «проверено» and «ждут решения» count differently, and that the v3 queue is re-consented.
- Rollback is a switch for new runs; a migration with rows in the new tables is not rolled back, as with `0059`…`0062`.
- The compose file gains its first memory-limited service and the host gains its first timer; `deploy.sh` checks the disk before the image build (the image is 5,51 GB and a rebuild needed 9,5 GB, `docs/program/W54-EMBED-BUILD-01.md`).
- «Разбор» gains a source chip and a mark in each row, a collapsed queue and, above the list, one line while vectors are missing. The concepts per screen are counted in each UI task (`R-153f`).
- The lanes of `docs/program/tasks/` carry the owner of each hotspot; `runs/extended_review.py` has one owner at a time.

## Alternatives considered

- **A resident encoder with database access** (`DECISION-MEMORY-01` section 3.6): 3,2 GiB next to a run on a 4 GB host risks an out-of-memory kill of the run and the database. Rejected for now; the end condition of temporary decision 2 reopens it.
- **A mark per row «Недоступно».** Rejected for one line above the list.
- **A new rail chip for «Прецеденты».** Rejected: `RunStageChip` is not extended; the state lives in «Разбор».
- **HNSW over the cases.** Rejected: an exact scan inside a section needs no training data and no index overhead.
- **Letting a model write the mark or the reason.** Rejected: a verdict is a human's (`ADR-0027` decision 3); P1 quotes a comment or an approved pattern, not a model.
- **«Снять» for findings the critic did not review.** Rejected by `R-153ar`.
- **A single fallback search when a vector is missing.** Rejected by `R-153ac`; the answer is «Недоступно».

## Verification

Checks are minimal and proportional (`R-153j`, `R-153an`): focused unit and contract tests per task, one narrow throwaway-database run for the migration, and a read-only judge after each wave. Every guard has a test that can fail. The judges of the programme:

- J1: grants and recovery classification, the forget protection, the encoder's limits and the loud window skip;
- J2: the gate admits only what was verified;
- J3: 404 for the legacy and foreign tokens, the budget, instruction injection from the reference block;
- J4: «снять», independence, veto and the critic condition;
- J5: patterns and cross evidence.

A browser journey covers «находка-блок», «очередь» and «пауза векторов». A change a user can see is previewed in two themes at two widths before it is published.

## Revisit trigger

Any of these reopens this ADR:

- the end of either temporary decision;
- the first use with real client documents (`D-291`, `ADR-0028` decision 17);
- the encoder or the vectors move off the host;
- a model is allowed to write a mark, a reason or a verdict;
- the legacy route is removed.
