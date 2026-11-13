# Product release ledger

Each row records one deployed and verified product release. The release
integration task fills it from the exact published SHA, image measurements,
full-gate log and host verification. No development candidate is entered as a
release. A row marked `not deployed` or `host verification owed` is a prepared record: it travels with the
release commit, every `pending` cell in it is replaced by the release
integration task from the exact published SHA, and the marker is removed only
after host verification.

| Tag | SHA | API `build_id` | Web `web_build_id` | `contract_version` | Migration head | Prompt bundle hash | Profile bundle hash | `GATE OK` evidence | Norms snapshot (from W55) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `v0.4.0` | `2653dbf49e9f37fa891dd6e47b396650a215542d` | `be7bf8dae6d63d63c` | not measured (stand environment) | `1.0.0-draft.1` | `0017_execution_queue` | `934705c04a71…` | `30053740f569…` | none — waived by `R-87`; deploy run `38219064192` verified (`W53-INT-MAIN-01.md`) | — |
| `v0.5.0` | `23fd729dbb06c642be0588017f6b195305e2e53e` | `bf9407822414591b3` | not measured (stand environment) | `1.0.0-draft.1` | `0020_norms_search` | `934705c04a71…` | `30053740f569…` | `W55A-INT-GATE-01.md` (GATE OK on this SHA); deploy run `38356461757` | — |
| `v0.6.0` | `37393a979a430e490843d7f410e9eca9491a4ea1` | `bf03d913bde596a77` (computed from tagged tree) | not measured (stand environment) | `1.0.0-draft.1` | `0021_portal_bundles` | `934705c04a71…` | `30053740f569…` | `W55B-INT-MAIN-PREP-03.md` (R-125 same-SHA gate completion); deploy run `38897018419`, owner-run host verification in `W55B-INT-MAIN-VERIFY-ADDENDUM-01.md`; five live checks waived in `W55B-INT-TAG-01.md` | — (not promoted) |
| `v0.7.0` — on `origin/main`, **host verification owed**, not tagged | `48c8e34ccd08a58ae61cbd09ecdba49066a5ad46` (the owner's pull request #3) | `bbbab3c0dfb856a39` computed from `git archive` of that SHA (`compute_build_id()`) | not measured (stand environment) | `1.0.0-draft.1` | `0028_classification_corrections` | `934705c04a71…` (builtin AR profile, unchanged since `v0.6.0`) | `30053740f569…` (builtin AR profile, unchanged since `v0.6.0`) | **none on this tree.** The owner merged pull requests #2 and #3 into `main` without a gate (`R-141e`); `NIGHT-1020-GATE-0-7-0-01.md` is an `R-125` completion of an earlier lineage and covers neither the classification correction, the normative references nor the hardening slices; light checks only (`RELEASE-0-7-0-RECORD-01.md`). Deploy workflow run `39571427597`, success, reported by the integrator and not re-read here; `infra/deploy/verify-deployed.sh` on the host: **pending** | none — the normative corpus is not imported on the stand |

## `v0.27.0` — verified repaired analysis flow

`W-ANALYSIS-INT-RELEASE-01` released and tagged exact SHA
`275bde8643e1e89f5f9741be2e57b7367cde44ae`. [Workflow 43433384065](https://github.com/hoperlex/PDF-Analysis/actions/runs/43433384065)
completed successfully; the job log confirms both the actual same-tree host verification
and `DEPLOY OK` for that SHA. Product 0.27.0, contract 1.55.0, migration
`0068_reviewable_findings`.

Fresh-consent analysis preserves valid work, semantic text/drawing origins, normative
uncertainty and additive corrections. Reviewable unverified findings use the existing
human ledger and memory; active/history CSV/XLSX follow real verdicts. Existing compatible
vectors can supply bounded human examples when the established switches permit it.
The publication correction reconciles CSV/nullable API metadata without changing analysis,
migration or value bounds. Fresh local checks: 10 Python and 8 frontend-lock tests passed,
generated-client verification OK. The owner expressly waived the full gate for this SHA;
no paid analysis or encoder was run. Production switches and extra manual host probes
were not inspected or changed. [Release evidence and limits](tasks/W-ANALYSIS-INT-RELEASE-01.md).
Closure records are dev-only; main remains the exact verified release SHA.

## `v0.12.5` — verified deployment and full machine run

`HOTFIX-RUN-COMPLETE-1106` deployed exact SHA `46b52dd068232236038d7ec4cbb0b13c63b9aa25`:
workflow 42241699088 succeeded, the host verifier confirmed the same tree, and public
TLS/auth smoke returned 200/401. The release exposes preparatory parameter progress,
retains ready answers to the server deadline and uses critic-specific semantic repair
with honest uncertainty. Run `run_01M6RQ9SZPB01G22AV6VQRHJHD` is published: all 7 procedures,
3 windows, 47 blocks, 30 pages and 1848 pairs completed; all 74 provider effects completed,
0 unresolved, recorded unmetered cost 0. The passport accepts 307 strictly validated
candidates; 80 unsupported candidates remain rejected outside accepted facts. Strict
source guards are unchanged; no expert decision is written. Build-only checks passed as
explicitly ordered; no behavioral suites, full gate or tag.
[Full verified task record](HOTFIX-RUN-COMPLETE-1106.md). Closure records are dev-only;
main runtime remains the exact verified release SHA.

## `v0.12.3` candidate — local stdin delivery and validation outcomes

`HOTFIX-RUN-COMPLETE-1106` follow-up repairs both interrupted subprocess stdin pipes,
versions the changed runner package separately, preserves normative quote variants per
input and adds a fresh passport policy for explicit rejection of unsupported candidates.
Only strictly validated facts are accepted; structural, transport and source-coverage
failures remain incomplete. The observed failed repeat is run_01M6RCQC0B0VJ8MFM0S58A61A5;
its timeout had zero CLI events and zero answer bytes. No behavioral suites/full gate;
build verification and a new unmetered live repeat are recorded in the task receipt.

## `v0.12.2` candidate — full source plans and execution statuses

Revision 1 repairs missing word spaces in newly extracted PDF text. Revision 2 carries
`HOTFIX-RUN-COMPLETE-1106`: complete source-sized passport and cross-window plans, a separate
consent-bound semantic repair, exact refusal diagnostics, literal normative lookup queries
and accurate phase closure. Contract 1.33.0 and migration 0055 are unchanged. Publication
uses the owner's deployment-build-only exception; the exact deployment and complete live
run remain independently verified in the task receipt. No release tag is created.

## `v0.12.1` development candidate — «График работ», the runs table, dense screens

`release-notes/0.12.1.json` (revision 1, 2026-11-06, three items): «График работ» (contract `1.31.0`, migration
`0055_work_schedule`, `/schedule`), «Выполнено» and «Календарь запаса»; the version's runs as a dense table (lane A,
`67a62928`); the second density pass over norms, settings, administration, account, logs and optimisation (lane B,
`22c63209`). A patch version on the day of `0.12.0`, because
`0.12.0` is full at seven items; the owner removed the strictly-later-date rule on 2026-11-06 (versions of one day may
share its date). `VERSION` is `0.12.1`. Revision 2 carries `HOTFIX-RUN-PARTIAL-1106`: partial parameter replies retain valid facts, completed visual work survives later failures, successful/stopped windows are distinguished, and Codex answer delivery ceilings and its hidden deadline are removed. Contract 1.33.0 relaxes the runner answer-text constraint. The owner authorized dev-to-main publication with deployment build checks only; the deployment workflow and exact-tree verification are recorded in that task's release receipt.

## `v0.12.0` — pull request #45, live from the grants hotfix

Written by `RELEASE-0-12-0` at the owner's request of 2026-11-06 (again no version for what `main` runs).
After `0.11.0` the owner merged #43 (`5958528b`) and #44 (`e8b12094`, which carried the `0.10.0`/`0.11.0`
notes), both without a user-visible change, and #45 (`68dd4d66`, 2026-11-06, 51 commits, contracts
`1.20.0`…`1.30.0`, migrations `0051`…`0054`). The deploy of #45 was refused at `apply-grants.sh`
(`grants_unclassified`, workflow run `42175149560`); the hotfix `d6e8b4af` classified `document_tag` and
`finding_execution_status`, and its deploy succeeded (run `42177263914`), so #45 reached users on 2026-11-06.
`release-notes/0.12.0.json` (revision 1 of 2026-11-06, seven items; now at revision 4, see below) describes it; `VERSION` is `0.12.0`.

| Item | Commits |
| --- | --- |
| 1 section cards and page, «Несколько файлов», «Запустить аудит (N)» | `b6eccfe3`, `90f89103`, `22abc9e0`, `b468070f` |
| 2 rename and archive, «Показать архивные», tags and the tag filter, the document's «Оптимизация» | `46de9524`, `d8e2fb89`, `5a064771` |
| 3 ✓/✕ per row, the severity strip and the model row, the drawing sheet, the critic chips | `4e922722`, `e5846fb4`, `1d6b93a9`, `cce599cc` |
| 4 the execution status, «Загрузить решения из Excel» and «ID замечания» | `275cd57d`, `480458ea` |
| 5 «Замечания» / «Предложения» in the knowledge base | `284c10ad` |
| 6 the queue overview, place, attempts, «Запустил», «Ожидаемое завершение», the pause in the top strip | `83b59f9f`, `4343ce52`, `84325e26`, `110b9dac` |
| 7 the dense layout, «Блоки» as a version tab, «Диспетчер» by project, the «Процессы» tiles | `b757fc55`, `212e20a5`, `26e2bbbd`, `6f03944b`, `57d01cf9`, `ff3e9cb6`, `07a1c81b`, `31388f79` |

Revision 2 (2026-11-06) adds the hotfix `65ffb867` (main deploy run `42189173407`, success): a v3 window started its normative context receipts as the parent's list, so every full section plan with a norm paragraph context policy raised `AttributeError` at its first window save (production run `run_01M6QXCZA8EKYGSMX8JA7QH6XV`). To stay within seven items the knowledge-base item is folded into item 4, and item 7 is the fix. Revision 3 (2026-11-06) adds to item 7 the run page fix: `CrossWindowReview` shared the React key `run_id` with the observation list, so each poll duplicated the cross-window block; it now has its own key, and the plan detail and the observations are folded under `<details>`. Revision 4 (2026-11-06, AGENTS §6.1) carries the same day's dev publications, the version being full at seven items: item 3 gains «Во весь экран» and «Открыть PDF» on «Разбор» (`a941a6ae`, `c1f96051`), item 4 the knowledge base's «Все» (contract `1.32.0`, `55f3108b`), item 6 the run screen's head (`d50376c0`, `0dbf38b8`). «График работ» (`1.31.0`, `/schedule`) opens `0.12.1`, since this version is full.

Left out: `getProject` naming the project page (`987f8579`), the role checkboxes (`aa8f139e`). The same commit
is on `origin/dev` and, cherry-picked, on `origin/main`. Checks: none (owner: not a code task); the text was
measured by a throwaway script against the form rules and the screens were read in the screen registry.

## `v0.10.0` and `v0.11.0` — notes for what `main` already ran without a version

Written by `RELEASE-0-10-0-0-11-0` on `origin/dev` at the owner's request of 2026-11-05 (versions existed on
the stand without a description). After `0.9.0` (pull request #38, `158a815e`) the owner merged `dev` into
`main` four times while `VERSION` stayed `0.9.0`: #39 (`5b831b45`, 2026-11-03), #40 (`6f388afc`), #41
(`06d4a07b`) and #42 (`86d4965e`, all 2026-11-05). Each is a release in the sense of `RELEASE_PROCESS.md`,
but the form rule `descending_dates` wants every higher version strictly later, so the deployments of one
day share a version, as pull requests #19 to #38 of 2026-10-30 share `0.9.0`: `0.10.0` (revision 1,
2026-11-03, seven items) is #39, and `0.11.0` (revision 1, 2026-11-05, seven items) is #40 to #42.
`VERSION` is `0.11.0`. Minor versions, because each day adds features. Nothing is stored before the next
deploy of `main`; after it the rows are permanent and only a higher revision changes a text.

| Note | Item | Commits |
| --- | --- | --- |
| 0.10.0 | 1 «Группы», «Правила», cut-over, the three-way start choice | `49a47617`, `f552393c`, `43ae38b2`, `938b3aae`, `6c4ded41` |
| 0.10.0 | 2 «Добавить подключение», SSH install after the fingerprint, 15-minute command, OpenRouter, moving an agent, 1–16 concurrent runs | `548cf96b`, `e4cf01a8`, `ea3fbed1`, `669f2024`, `375800b1`, `d0a806e8` |
| 0.10.0 | 3 the review's page viewer with highlight and frame (`tasks/REVIEW-VIEWER-01.md`, no flag) | `1a7575c5`…`f2a68106`, `38d4e950` |
| 0.10.0 | 4 waiting reasons, planned and actual model | `d0a806e8`, `43ae38b2` |
| 0.10.0 | 5 intake limits back to 250 MiB and 500 pages unless `AUDITMANAGER_INTAKE_RELAXED=1` | `733ac3f7`, `d0573f05` |
| 0.10.0 | 6 undo of a link repair on a finished stage comparison makes the run stale | `efcf75e4` |
| 0.10.0 | 7 a failed specification batch leaves no final aggregate and is asked again | `d0573f05` |
| 0.11.0 | 1 «Проекты ▾» with the two document counts, project-scoped «Дашборд» and «База знаний», the context strip with the version choice | `13a74f80`, `1383264f`, `d369d9be`, `3fb5705a`, `ecba6592`, `4a2bb756` |
| 0.11.0 | 2 the role «Наблюдатель», offered by the admin forms | `5c6f9d0c`, `1b2780d7`, `32b3f121` |
| 0.11.0 | 3 «Список / Таблица», the verdict tally and filter, finding and filter in the address | `8da0b60a`, `1e3bfe71`, `4f7c19cb` |
| 0.11.0 | 4 the readable queue, state filter and badge, 10-second refresh with the update time | `928dded3`, `3e6362ab`, `7d117a57`, `6adeae81` |
| 0.11.0 | 5 «Отменить прогон» and «События прогона» | `71009019`, `5664f286` |
| 0.11.0 | 6 the five numbers of a dashboard section row; «за всё время» on the verdict panel | `deaeaa7f`, `c29ef738` |
| 0.11.0 | 7 every finding of a run on «Разбор находок»; «Назад»/«Далее» in «База знаний»; the home tile counts current versions | `3ca0ffed`, `c29ef738` |

Left out: the 2026-10-30 analysis blocks `BLOCK10`…`BLOCK16`, enrollment and pull-claim internals, the
`EXEC2-FOLLOWUP-01` captions, «Обновить» on a project's sections. Moved with `VERSION`: the revision map and
version order of `test_release_notes_form.py`, the version set of `test_release_loader.py`, and
`test_note_profile_versions.py`, which now judges the newest note that quotes profile versions (`0.9.0`),
because neither new note talks about the profiles. Checks: none run (owner: not a code task); the texts
were measured by a throwaway script against the form rules and the current note's screens were read in
the screen registry. No independent note judge, no table row and no tag.

## `v0.9.0` development candidate — section analysis, large documents and sheet pairing

Prepared by `RELEASE-0-9-0-DEV-01` on `origin/dev` only: `VERSION=0.9.0` and `release-notes/0.9.0.json` (revision 3, 2026-10-28, seven items; dated the day after `0.8.2` because the form rule wants strictly descending dates and `0.8.2` carries 2026-10-27). The note describes what an expert can see on this tree and no more: the approval and withdrawal of a sheet pairing in the version comparison with the recomputed differences of the approved pairs, and a model summary of those pairs that in this build exists only for recorded cases; the 14 section profiles from `1.1.0` to `1.3.x`, status `reviewed` shown as «проверен» (no human review took place; the beta switch `SHOW_REVIEW_INDICATION` keeps the old label «рабочая версия, проверка человеком не проводилась» off the screens, `R-146ba`), the same-document total-against-rows checks asked of 12 of them, and, for five of them (АИ, ЭОМ, ИТП, СС, ТХ: `AI`, `EOM`, `ITP`, `SS`, `TX`), the report of an absent entry under «Документация»; whole-page windows for a text above one model call, each window analysed on its own under one cost ceiling; «Спецификация и цены» and «Предложения» for a version confirmed in any of the 15 sections; the removal of the ordinary АР start (only the six-check group remains); the corrected sentence about «Без раздела» on the dashboard; and an executor connection of the kind «Команда по SSH» that can now be routed and chosen, with the plain `http://` address rule of the connection settings. The note claims no measured quality for any prompt and no speed-up. Revision 2 (`REVIEW-INDICATION-SWITCH-01`) removed the quotation of that label from the note and the claim «проверенный экспертом набор» from the АР item; revision 3 (`ACCESS-COMPARE-JUDGE-FIXES-01`) corrected the profile versions the note quotes (it had said «1.1.0 или 1.2.0» while five profiles were at `1.3.0`) and added the sentence about «Документация»; the note had not reached `main`. `release-notes/0.8.2.json` is not edited. Every claim is traced to a commit and a test in `RELEASE-0-9-0-DEV-01.md`. There is no table row, no tag, no `origin/main` push, no complete gate (`D-205`), two independent note-judge passes (the first on `e1199c25`, the second on `79a7e415`, whose findings are fixed in `d04e8f83`) and no stand deployment.

## `v0.8.2` candidate — choosing the executor of a run

Prepared by the parallel-runs slices (`EXEC-PAR-START-01`, `EXEC-PAR-QUEUE-01`, `EXEC-PAR-WEB-01`): `VERSION=0.8.2` and `release-notes/0.8.2.json` (revision 1, 2026-10-27, five items; dated the day after `0.8.1` because the form rule wants strictly descending dates). The note describes what an expert sees and no more: the «Исполнитель» choice in the start control, the executor and its model on the run, the waiting label, the repeat that keeps the executor, and one run at a time per executor. It claims no parallel speed-up: the worker keeps one slot until an administrator sets `AUDITMANAGER_WORKER_SLOTS`, and a named executor needs the database provider source. There is no table row and no tag here; a row is entered only from the deployed and host-verified tree. The operator's check is `EXEC-PAR-OPERATOR-CHECK-01.md`.

## `v0.8.1` development candidate — pack status and the pack-gated six-check start

Prepared by `RELEASE-0-8-1-DEV-01` on `origin/dev` only: `VERSION=0.8.1` and `release-notes/0.8.1.json` (revision 1, 2026-10-26, seven items). The note describes what an expert can see on this tree and no more: «Настройки анализа» says whether the reviewed AR v3 pack is installed and prints the reviewer's attached record with the sentence that the system does not check it; the version's run list draws «Запустить шесть проверок АР v3» only when the pack is installed and opens the started group's review; that review panel and the run page of an AR v3 Run keep the result a provisional citation for expert verification, with no canonical finding and no numerical conclusion; the quotation caption names the page only (`R-43`, `D-50`); eight widget stylesheets stop drawing borders in the text colour; the classification history list has a gap. `release-notes/0.8.0.json` is not edited. Every claim is traced to a commit and a test in `RELEASE-0-8-1-DEV-01.md`.

No reviewed pack is installed on any stand, so on a deployed tree the note's start button is not drawn and the group review has no group to show; this candidate proves the screens, not a verified citation. There is no table row, no tag, no `origin/main` push, no complete gate (`D-205`), no stand deployment and no live or credentialed journey for the new screens. The `v0.7.0` host verification and tag stay owed as recorded below. To roll back, revert `VERSION`, the note file and the version pins in the two release tests and `CURRENT_STATE.md` together.

## `v0.8.0` development candidate — source-status preview only

The owner requested `VERSION=0.8.0` on `origin/dev` and will handle any later `main` publication. The authenticated «Настройки анализа» screen now shows the frozen Ф1.3 C01–C22 beta dispositions in six groups. Its source JSON is byte-identical to the server's policy and says explicitly that v3 Runs and numerical conclusions are unavailable. This candidate does **not** meet the previously planned W57a `v0.8.0` milestone of reviewed maps and verified citations. The independent [local corpus qualification](AR-BETA-LOCAL-CUSTODY-01.md) is only on a disposable lane; neither the production stand nor the served Run path has its six verified sets. The user-facing note `release-notes/0.8.0.json` describes this narrower capability and no more. There is no tag, `main` push, complete gate, stand deployment or verified v3 citation associated with this development candidate.

## `v0.7.0` technical record (on `origin/main`, host verification owed)

Written by `RELEASE-0-7-0-RECORD-01`. The owner merged `dev` into `main` twice on 2026-10-21: pull
request #2 (`829117d3`, `R-141e`, `VERSION` still `0.6.0`, workflow run `39561204544`) and pull request #3
(`48c8e34ccd08a58ae61cbd09ecdba49066a5ad46`, 11:43 +03, workflow run `39571427597`, success). Both run
ids come from the integrator's report and were not re-read here (`gh` is not installed on this host).
The second merge carried the record lane (`dfae803b`: `VERSION` `0.7.0`, `release-notes/0.7.0.json`,
this ledger) **and** four slices merged after it, so the tree on `main` is not the tree the record
was written on. The first deployed form of the tree reported `v0.6.0` and `build_id`
`b60e02fff4f168d21`; the release tree has `bbbab3c0dfb856a39` (`VERSION`, `release-notes/` and `src`
are inputs, so the images were rebuilt). The user layer is `release-notes/0.7.0.json` (revision 2,
after the independent judge's edits); every claim in it is traced in `RELEASE-0-7-0-RECORD-01.md`.
Between `dfae803b` and `48c8e34c` the contract, the migrations, the release notes and `VERSION`
are byte-identical.

- **Version.** `VERSION` moves `0.6.0` to `0.7.0`. The loader appends revision 2 of `0.7.0` at
  deploy; the highest non-archive entry equals `VERSION`. `VERSION` and `release-notes/` are
  `build_id` inputs, so publishing this record rebuilds the images and shows the update banner.
- **API surface.** 47 paths / 54 operations / 123 schemas in the `v0.6.0` tree become
  73 / 83 / 242 (29 added operations, none removed or moved; `contract_version` stays
  `1.0.0-draft.1`). `getRunNormVerification` answers a typed 503 until a verified reader exists
  and is claimed in no note. The error catalogue grows from 24 to 25 codes
  (`model_identity_mismatch`).
- **Migrations.** Head `0021_portal_bundles` becomes `0028_classification_corrections`; `0022`
  to `0028` were applied forward by the deploy of `829117d3`. `0022` has one data step: it sets
  `finding.canonical_observation_id` from each finding's only observation and aborts if a finding
  has not exactly one. `0023` adds nullable columns and empty tables and activates no v2/v3
  profile. `0024` creates the classification table empty: **every version that existed at deploy
  stays unclassified, and run start and re-audit refuse an unclassified version** until an
  expert confirms its stage and section. `0025`–`0027` create empty assignment, price-list,
  vendor-list and optimisation-proposal tables. `0028` adds the append-only correction table and
  the current-classification views and replaces one trigger function; it backfills nothing.
- **Read models and exports.** The dashboard's per-section counts follow the stage and section
  an expert confirmed (corrected or not) for each document's current version; documents without
  a confirmation fall in «Без раздела». The run CSV grows from 17 to 19 columns (`severity`,
  `severity_proposed`); the Excel export writes the screens' Russian labels.
- **Proxy.** The two upload locations are widened to admit `.../documents/{document_uid}/versions`
  in `infra/deploy/proxy/nginx.conf` and `tls-server.conf`. The tree on `main` also changes the edge
  (`HARDEN-AUTH-EDGE-01`): `POST /api/v1/auth/token` is throttled per client address (6 requests a
  minute, burst 10), and both upload locations first ask the application who the caller is
  (`auth_request`), so a stranger is refused with a typed `401` before the upload body is read.
- **Also in the tree, not in the notes** (nothing in it is a user-facing claim; each has its own report):
  `ACCESS-STORAGE-HARDEN-01` (a queue lock for every login writer, a bulkhead for norms search, the
  order of the upload door's headers, a memory of revoked credentials at the seam), `SPEC-TABLE-RECORDING-01`
  and the specification reader (wrapped-above cells, continued pages and the manufacturer are read from
  the saved text; a vendor's legal form is optional when matching), `RECOVERY-REBASE-01` (the W58
  restore drill rebased onto head `0028`), `BETA-LIVE-JOURNEY-01` (the stand acceptance script and
  the end-to-end journey), and two web repairs (a double press sends one request; a carried decision
  stays shown after the re-read).
- **Dependencies.** No dependency or lock change since `v0.6.0`; `infra/deploy/compose.server.yml`, `deploy.sh` and `env/alpha.env.example` differ only in comments.
- **Not part of this release.** The recorded-only AR v2 profile, retrieval and citation
  preparations, the certified-source preparations and the restore drill are unserved
  (`CURRENT_STATE.md`). The 13 non-AR text profiles are drafts; recorded-mode proof exists for
  four of them with synthetic recordings only. **The normative corpus is not imported on the
  stand**: «Нормы» search, the catalogue and «Нормативные ссылки» answer a typed refusal until the
  import and the administrator's designation of a snapshot have run
  (`STAND-NORMS-IMPORT-RUNBOOK-01.md`); runs started before the designation pin no snapshot.
- **Verification still owed.** (1) A literal `GATE OK` does not exist for this tree or for `829117d3`.
  (2) The owner's instruction for `origin/main` was given by his own merge, not as a named-SHA
  instruction to an integrator. (3) `infra/deploy/verify-deployed.sh` on the host for the same tree:
  **pending**; the `v0.7.0` tag follows it and the owner's say-so. (4) Live and manual acceptance of the new screens: not run;
  no credentialed journey has exercised them. (5) `tests/e2e/pc01/test_acceptance.py` needs real
  services and was not run by this task.
- **Rollback.** Revert through a reviewed forward commit with a fresh gate and host
  verification (`RELEASE_PROCESS.md`); never move `main` backward. The schema cannot be walked
  back by an image swap alone: the `0022` and `0023` downgrades refuse once findings exist, and
  the `0024`–`0028` downgrades drop the classification, correction, assignment, price-list and
  proposal tables with a logged row count. Restoring data means the host's pre-deploy database
  dump (`infra/deploy/reset.sh`; no off-host backup exists). The loader leaves a `0.7.0` row
  above a running `VERSION` untouched, so a `0.6.0` image hides it.


## 2026-10-30 CMP development code addendum

`CMP-INT-CODE-1030` prepares the two comparison modules for development publication. Release note0.9.0 revision4 describes the module screens, pre-start cost approval, background PDF checks and running-metre equivalence. Product VERSION remains0.9.0. Final additive contract is1.13.0,230 paths /256 operations /619 schemas, head0043_stage_ai_generations. Full gates, browser acceptance, exposure acceptance and heavy measurements are deferred by the owner to2026-10-31. This is no deployed-release row, tag or main authorisation. See the integration record for publication evidence and limitations.
