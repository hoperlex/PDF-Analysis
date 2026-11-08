# UI-PARITY-01 — UI/UX parity with the original application

Owner rulings: `R-150a`…`R-150z` (`OWNER_RULINGS_2026-09-17.md` §3.50) and `R-151a`…`R-151z` (§3.51, the direct poll of 2026-11-05). Integrator: the UI-parity session, on `integration/ui-parity`. Base `origin/dev` 76e13471.

The working analysis is the session's local register (`.local/reports/ui-parity/UI-PARITY-REGISTER.md` plus `register-A.md` and `register-B.md`, 198 rows with anchors into both codebases; host-only, git-ignored). This record keeps what other sessions need: rulings, order, contract delivery and the completion criterion.

## Goal and principles

- Bring `web/` to the function and flow of the original (`SU10KAZ/PDF-proverka` at `d213bfdc`; all 17 screens). Keep FSD, existing solutions, reusable components and our visual style (`--am-*` tokens, no UI library).
- Likeness is layout only (`R-151s`): block arrangement and density follow the original; colours, fonts and components stay ours. A section's documents show as a card grid on our tokens.
- Transfer function and information structure; replace the original's technique (hidden `sessionStorage` context, native `alert`/`confirm`, client-side aggregates, demo data on failure) with ours.
- Our nouns stay. Original «Объект» ≈ our «Проект»; original «Проект» ≈ our «Документ»; «Раздел» ≈ «Раздел» (ours is an expert-confirmed property of a version). The original's «Диспетчер» (worker monitoring) ≈ our «Исполнители»/«Очередь»; ours (assignments) ≈ the original's work schedule.

## Project context (R-150c)

The address is the only source of the project (`?project=`); client code reads it, never keeps a copy.

| Class | Screens | Without `?project=` | Header choice |
| --- | --- | --- | --- |
| required (project in the path) | Проект, Раздел (`R-151l`), Документ, Версия, Блоки as a version tab (`R-151m`), Сравнение прогонов, Прогон, Разбор | impossible; unknown project → explicit not-found | goes to the chosen project's page |
| optional (follows the header) | Дашборд, База знаний, Оптимизация разделов, Оптимизация, Сравнение версий, Сравнение стадий, Диспетчер (`R-151m`) | explicit «Все проекты»; comparisons show «Выберите проект» | rewrites `?project=` on the current screen |
| global | Главная, Проекты, Очередь, Журнал выполнения, Исполнители, Настройки анализа, Нормы, admin, account | the parameter is ignored but carried | goes to the chosen project's page |

«График работ» (`R-151y`) gets its class when its task is written.

Rules: frame links carry `?project=` except onto required screens; on `/projects/X/…?project=Y` the path wins; a project change resets `section`, `version`, `pair`, `set`, `run`, `cursor`, `tab`; Back/Forward restore from the address only; `project_uid` is in every optional screen's cache key.

## Order

1. **Before wave 0:** re-check register rows against the current dev tip and give each a status; record the rulings (done: §3.50).
2. **Completeness fix, ahead of wave 2 (R-150i):** «Разбор находок» loads every finding (it showed the first 50 of a run silently); the knowledge base pages with «Назад/Далее».
3. **Wave 0:** the metrics dictionary first (wave 1 waits for its counters, R-150j); the role matrix; answers to the freeze list; the contract package P0; the project class in the screen registry and address helpers; the polling policy; only the `shared/ui` components wave 1 needs. The dispatcher domain description runs in parallel and blocks only its four items.
4. **Wave 1, shell:** the «Проекты ▾» selector in the top strip with the two counters, breadcrumbs, menu badges.
5. **Wave 2, auditor path:** one wave after P0 (sections, documents, versions, findings, blocks).
6. **Wave 3, secondary:** queue/journal/knowledge base, optimisation, comparisons.
7. **Wave 4, dispatcher:** queue group A consumers, worker metrics in «Исполнители», admin journal, and a «График работ» menu item (`R-151y`) with schedule facts, the monthly plan set by the administrator and the minimal reserve calendar (`R-150y`, `R-151x`: done work = a document reaching «Проверено экспертом»). Subscription accounts are not built; provider limits are not built now (`R-150y`).
8. **Wave 5, optional (T3):** does not hold programme completion.
9. **Read-only role, cross-cutting (R-150e):** one server change in P0 (Role enum, migration of `ck_app_user_role_role`, a new read set in `OPERATION_ROLES`, combinations refused); UI hiding per screen through waves 1–3; the admin form offers the role last.

## Contract delivery

One supplier per item; no consumer before its supplier.

| Item | Delivery | Consumers | Condition |
| --- | --- | --- | --- |
| optional `project_uid` on `getDashboardSummary` and `listDecisions`; project/document fields and `total` on decision records | **P0a, night window 2026-11-04** | waves 1–3 | none pending |
| `getProject`; selector and section counters | **1.19.0** (counters) and **1.29.0** (`getProject`, 987f8579) | waves 1, 2 | metrics dictionary approved |
| read-only role | P0, one change | cross-cutting line | matrix approved |
| last-run state, finding counts, severity summary on documents/versions | P0 | wave 2 | dictionary |
| severity strip and filter on «Разбор» | **delivered without a contract change** (e5846fb4): the page loads the whole run (`R-150i`), so counts and filter share that scope, as the verdict tally does | wave 2 | decided severity plus a labelled «предложено моделью» row (`R-151j`) |
| finding → portal block (`portal_block_id`), sheet label | sheet label **1.30.0** (`listVersionSheetLabels`, 1d6b93a9); per-finding blocks **1.41.0** (`listRunFindingBlocks`, lane C6, 2026-11-09): derived on read by geometry — the evidence's share of its text-layer line covered at least half by a portal block on a page whose geometry checks; known misses `D-353`, «в составе»/«проверен» `D-352` | wave 2 | — |
| queue group A: item names and times, state filter and period, overview, next-job flag, attempts | **1.18.0**, **1.26.0** (ETA) and **1.28.0** (overview, place in the queue, attempts; 83b59f9f) | waves 3, 4 | ETA by the median of similar past runs (`R-151u`); the "next job" is the place in the dispatcher's order, not a forecast |
| knowledge base: section, filters, decision `kind` and «Тип» filter | P0 | wave 3 | `R-151h` |
| document archive flag and display title | P0 | wave 2 | `R-151a` |
| multi-file upload with an explicit target per file | P0 | wave 2 | `R-151b` |
| batch run: estimates of several documents, one consent | P0 | wave 2 | `R-151c`; a consent per run stays on the server |
| decision import from our own export by `finding_uid` | P0 | wave 2 | `R-151d` |
| document tags and a tag filter | P0 | wave 2 | `R-151e` |
| queue pause state for the header | **1.20.0** (`getExecutionDispatch`) and web 110b9dac | wave 1 | `R-151f`; «interrupt now» is a later contract |
| finding execution status (designer side) | P0 | wave 2 | `R-151g`; who sets it is decided in the task |
| who started a run | P0 | waves 3, 4 | `R-151v` |
| start from a stage (UI-A-60) | **1.42.0** (`UI-PARITY-S2`, `startRunFromStage`; migration `0060`; web: «Запустить с этапа» on the run page) | wave 2 | `R-151i`; design `RUN-FROM-STAGE-01.md`; the idempotency key and the reuse rule decided by the lane (`D-410`) |
| dispatcher: schedule facts and plan, minimal reserve calendar, worker metrics, admin journal | «График работ» **1.31.0** (`UI-PARITY-P0P`, e8a2c6da; migration `0055`; web `/schedule`): month facts against plans, the work calendar and absences, «Календарь запаса» over «Диспетчер»'s assignments with drag, multi-select and «Раньше/Позже»; unverified on a database (`D-318`); gaps outside `R-152` in `D-319`. Worker metrics and the admin journal: P4 | wave 4 | `R-150y`, `R-151x`, `R-151y`, `R-152a`…`R-152h` |
| dispatcher: subscription accounts, provider limits | not built (`R-150y`) | — | — |

**P0b (2026-11-05, contract `1.19.0`):** the counters wave 1 waits for — a document's audit state, `audit_counts` on each `listProjects` item and on the section panel, `awaiting_decision_findings` for the home tile — are delivered under `R-150n`…`R-150u`; their dictionary is `UI-PARITY-METRICS.md`. The selector and the new columns remain waves 1 and 2.

**Delivered 2026-11-05 (unverified candidates on `origin/dev`):** contract 1.20.0 (`listDocuments` `section_code`, `getExecutionDispatch`); web: pause state in the header (`R-151f`), section page and card grid (`R-151l`, `R-151s`), «Блоки» as a version tab (`R-151m`), «Диспетчер» following the header (`R-151m`), ✓/✕ in rows (`R-151n`), batch start (`R-151c`), multi-file upload (`R-151b`), optimisation on the document (`R-151r`), critic queue chips (`R-151q`), severity strip (`R-151j`). Delivered 2026-11-06 (contracts 1.21.0 to 1.27.0, unverified candidates): `R-151v` run starter, `R-151a` archive and rename, `R-151e` tags, `R-151g` execution status, `R-151h` knowledge-base kind (two journals, `D-317`), `R-151u` ETA, `R-151d` decision import. Delivered 2026-11-09 (contract 1.42.0, unverified candidate): `R-151i` start from a stage (`D-301` closed; `D-410`..`D-414` open).

**Freeze list of P0:** register questions Q-UI-6, 7, 8, 9, 10, 11, 14 and Q-UI-B7 have options that change the contract. The night window of 2026-11-04 shipped P0a only (no pending decision) and recorded the rest as debt; the owner answered all eight on 2026-11-05 (`R-151a`…`R-151h`). The contract slot for this work is the UI-parity session's until the programme ends (`R-151w`).

**Other register questions answered 2026-11-05:** Q-UI-3 section page at `/projects/[project_uid]/sections/[section_code]` (`R-151l`); Q-UI-4 «Блоки» as a version tab, out of the menu (`R-151m`); Q-UI-12 ✓/✕ in the finding row, one event per click (`R-151n`); Q-UI-B3 optimisation-by-section tabs as a separate wave (`R-151p`); Q-UI-B5 critic queues inside the extended review (`R-151q`); Q-UI-B6 optimisation on the document only, a summary on the project (`R-151r`); UI-A-45 card grid (`R-151s`).

## Polling (R-150k)

Polling stays; the platform has no WebSocket or SSE. Operational lists (queue, journal, later workers and overview) refresh every 10 s while the tab is visible, stop in the background, back off ×2 to 60 s on errors and show «Обновлено ЧЧ:ММ:СС», marked stale past three intervals or after an error. SSE is considered only on a measured need (event-to-screen p95 above 15 s, or a visible poll load in the API access logs).

## Completion criterion

The programme is complete when these scenarios pass in our application:
1. find the right document from the header and the menu;
2. open the right version and its run;
3. see a filter's complete result: every finding, and the number on screen equals the summary and the export;
4. record a decision with the right rights, and fail to do so under the read-only role (no buttons, the server refuses);
5. return through a saved link to the same screen, project and filter;
6. see a readable, refreshing queue (names, start, end, error, «Обновлено …»).

Each wave adds functional browser-path checks for the scenarios it changes. Guard tests stay per wave. Visual acceptance (every registered address × 2 themes × 3 widths) runs once at the end (R-150h), after the contrast pending list is closed or explicitly accepted by the owner.

## Debt

Owner questions and follow-ups from this programme are `D-300`…`D-319` in `DEBT_REGISTER.md`.
