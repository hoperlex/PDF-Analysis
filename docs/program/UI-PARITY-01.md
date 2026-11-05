# UI-PARITY-01 — UI/UX parity with the original application

Owner rulings: `R-150a`…`R-150m` (`OWNER_RULINGS_2026-09-17.md` §3.50). Integrator: the UI-parity session, on `integration/ui-parity`. Base `origin/dev` 76e13471.

The working analysis is the session's local register (`.local/reports/ui-parity/UI-PARITY-REGISTER.md` plus `register-A.md` and `register-B.md`, 198 rows with anchors into both codebases; host-only, git-ignored). This record keeps what other sessions need: rulings, order, contract delivery and the completion criterion.

## Goal and principles

- Bring `web/` to the function and flow of the original (`SU10KAZ/PDF-proverka` at `d213bfdc`; all 17 screens). Keep FSD, existing solutions, reusable components and our visual style (`--am-*` tokens, no UI library).
- Transfer function and information structure; replace the original's technique (hidden `sessionStorage` context, native `alert`/`confirm`, client-side aggregates, demo data on failure) with ours.
- Our nouns stay. Original «Объект» ≈ our «Проект»; original «Проект» ≈ our «Документ»; «Раздел» ≈ «Раздел» (ours is an expert-confirmed property of a version). The original's «Диспетчер» (worker monitoring) ≈ our «Исполнители»/«Очередь»; ours (assignments) ≈ the original's work schedule.

## Project context (R-150c)

The address is the only source of the project (`?project=`); client code reads it, never keeps a copy.

| Class | Screens | Without `?project=` | Header choice |
| --- | --- | --- | --- |
| required (project in the path) | Проект, Документ, Версия, Сравнение прогонов, Прогон, Разбор | impossible; unknown project → explicit not-found | goes to the chosen project's page |
| optional (follows the header) | Дашборд, База знаний, Оптимизация разделов, Оптимизация, Сравнение версий, Сравнение стадий | explicit «Все проекты»; comparisons show «Выберите проект» | rewrites `?project=` on the current screen |
| global | Главная, Проекты, Очередь, Журнал выполнения, Исполнители, Настройки анализа, Нормы, admin, account | the parameter is ignored but carried | goes to the chosen project's page |
| undecided | Диспетчер, Блоки | proposal: optional | decide at wave 1 |

Rules: frame links carry `?project=` except onto required screens; on `/projects/X/…?project=Y` the path wins; a project change resets `section`, `version`, `pair`, `set`, `run`, `cursor`, `tab`; Back/Forward restore from the address only; `project_uid` is in every optional screen's cache key.

## Order

1. **Before wave 0:** re-check register rows against the current dev tip and give each a status; record the rulings (done: §3.50).
2. **Completeness fix, ahead of wave 2 (R-150i):** «Разбор находок» loads every finding (it showed the first 50 of a run silently); the knowledge base pages with «Назад/Далее».
3. **Wave 0:** the metrics dictionary first (wave 1 waits for its counters, R-150j); the role matrix; answers to the freeze list; the contract package P0; the project class in the screen registry and address helpers; the polling policy; only the `shared/ui` components wave 1 needs. The dispatcher domain description runs in parallel and blocks only its four items.
4. **Wave 1, shell:** the «Проекты ▾» selector in the top strip with the two counters, breadcrumbs, menu badges.
5. **Wave 2, auditor path:** one wave after P0 (sections, documents, versions, findings, blocks).
6. **Wave 3, secondary:** queue/journal/knowledge base, optimisation, comparisons.
7. **Wave 4, dispatcher:** queue group A consumers, work-schedule facts, worker metrics, admin journal. The schedule plan, reserve calendar, subscription accounts and provider limits only after an approved domain description (R-150d).
8. **Wave 5, optional (T3):** does not hold programme completion.
9. **Read-only role, cross-cutting (R-150e):** one server change in P0 (Role enum, migration of `ck_app_user_role_role`, a new read set in `OPERATION_ROLES`, combinations refused); UI hiding per screen through waves 1–3; the admin form offers the role last.

## Contract delivery

One supplier per item; no consumer before its supplier.

| Item | Delivery | Consumers | Condition |
| --- | --- | --- | --- |
| optional `project_uid` on `getDashboardSummary` and `listDecisions`; project/document fields and `total` on decision records | **P0a, night window 2026-11-04** | waves 1–3 | none pending |
| `getProject`; selector and section counters | P0 | waves 1, 2 | metrics dictionary approved |
| read-only role | P0, one change | cross-cutting line | matrix approved |
| last-run state, finding counts, severity summary on documents/versions | P0 | wave 2 | dictionary |
| `severity` filter and summary on `listRunFindings` | P0 | wave 2 | summary scope equals filter scope |
| finding → portal block (`portal_block_id`), sheet label | P0 | wave 2 | — |
| queue group A: item names and times, state filter and period, overview, next-job flag, attempts | P0 | waves 3, 4 | ETA rule waits for the owner |
| knowledge base: section, filters | P0 | wave 3 | record type waits for Q-UI-B7 |
| start from a stage (UI-A-60) | not estimable until defined | wave 2 | owner question |
| dispatcher: schedule facts, worker metrics, admin journal | P4 | wave 4 | — |
| dispatcher: schedule plan, reserve calendar, subscription accounts, provider limits | outside delivery | — | approved domain description |

**P0b (2026-11-05, contract `1.19.0`):** the counters wave 1 waits for — a document's audit state, `audit_counts` on each `listProjects` item and on the section panel, `awaiting_decision_findings` for the home tile — are delivered under `R-150n`…`R-150u`; their dictionary is `UI-PARITY-METRICS.md`. The selector and the new columns remain waves 1 and 2.

**Freeze list of P0:** register questions Q-UI-6, 7, 8, 9, 10, 11, 14 and Q-UI-B7 have options that change the contract. Without an answer at freeze time the feature is excluded from P0; no option is chosen silently. The night window of 2026-11-04 shipped P0a only (no pending decision) and recorded the rest as debt.

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
