# Current state

**Updated 2026-10-30 by `DESIGN-M06-KNOWLEDGE` (development candidate only).**
Knowledge base filters/results, block version selection/tabs, norms search and
catalogue, and the norm document now use consistent responsive panels in both
themes. Existing search, snapshot designation, PDF and paragraph reads remain
unchanged. Typecheck, lint and 85 focused tests pass. No API, contract,
migration or `origin/main` change is included. Publication is to `origin/dev`
only; M07–M10 remain.

**Updated 2026-10-30 by `DESIGN-M05-COMPARISON` (development candidate only).**
The global version and stage comparison routes and version-specific comparison
now have consistent project selectors, tabs, panels and scrollable evidence
surfaces in both themes. Selected tabs remain semantically marked; existing
pair selection, AI review, evidence, export and lazy reads are untouched. The
frontend typecheck, lint and 122 focused tests pass. No API, contract,
migration or `origin/main` change is included. Publication is to `origin/dev`
only; M06–M10 remain.

**Updated 2026-10-30 by `DESIGN-M04-RUN` (development candidate only).**
Dispatcher assignments, Run facts and Review list/detail/export now use
responsive panels in the shared two-theme palette. Run stage rail and outcome
retain their existing semantic statuses and progress polling; Review retains
finding admission, evidence, decision and export behavior. Typecheck, lint and
128 focused tests pass. No API, contract, migration or `origin/main` change is
included. Publication is to `origin/dev` only; M05–M10 remain.

**Updated 2026-10-30 by `DESIGN-M03-PROJECT` (development candidate only).**
The project, document and version routes now group their existing tabs,
sections, upload panels, version list, classification and run list in responsive
cards. Project's section cards use the shared large radius. No read order,
conditional mount, identity rule, API, contract, migration or `origin/main`
changed. Publication is to `origin/dev` only; M04–M10 remain.

**Updated 2026-10-30 by `DESIGN-M02-ENTRY` (development candidate only).**
The home route now presents its greeting, section overview and existing
role-filtered tiles as a responsive hierarchy. The projects route groups the
existing create form and list, and section optimisation groups its filters,
project summaries and wide table in contained panels. Both themes use the
semantic tokens established by M01. Data, controls, permissions, API, contracts,
migrations and `origin/main` are unchanged. Publication is to `origin/dev` only;
M03–M10 remain.

**Updated 2026-10-30 by `DESIGN-M01-FOUNDATION` (development candidate only).**
The common main area now consumes the same two-theme surfaces as the shell and
dashboard. Page titles, cards, fields and primary controls have consistent
geometry. The comparison CSS now reads defined semantic colour tokens instead
of raw literals or undefined fallbacks; its mask/search/focus evidence overlays
remain visually distinct. `styling-layer` and `tokens-defined` guards pass on
this candidate. This is the first of the sequential 31-screen mini-tasks; local
content screens still need M02–M09 and browser acceptance M10. No API,
contract, migration, analysis or `origin/main` change is included. Publication
is to `origin/dev` only.

**Updated 2026-10-30 by `HOTFIX-SHELL-NAVIGATION-INT-20261030`
(development candidate only).** The shared frame now has a persistent left
sidebar above 1160 px and the existing compact disclosure menu below it. Each
role-allowed desktop group starts expanded, remains collapsible, and marks the
current page; the brand still provides the sole home link. The theme and account
controls use the preceding showcase palette in both appearances. The frame
keeps its registry-backed links and access decisions, and makes no new API call.
The 31-screen design plan records the shell slice as complete; content screens
other than the dashboard still await their own design stages. No contract,
migration, analysis behavior or `origin/main` changes are included. Publication
is to `origin/dev` only.

**Updated 2026-10-30 by `HOTFIX-DASHBOARD-SHOWCASE-INT-20261030`
(development candidate only).** `/dashboard` now uses an isolated presentation
palette in both light and dark appearances; the existing system choice follows
the dark block exactly. Its hero, panel cards and responsive section-card grid
still show only the existing dashboard summary and retain its loading/error
states. `docs/program/DESIGN-31-SCREEN-PLAN.md` inventories all 31 routes and
stages the remaining work; those routes are not yet redesigned. This task
changes no API, analysis behavior, contract or migration. The baseline still
contains styling-layer and undefined-token failures in the comparison CSS,
outside this dashboard pilot. Publication is to `origin/dev` only.

**Updated 2026-10-30 by `HOTFIX-SECTION-PRESENTATION-INT-20261030`
(development candidate only).** The home and dashboard now lead with an
original-inspired overview of all fifteen sections: compact code badges, names
and the server's confirmed document counts. A project shows its section groups
as expandable cards. A Run shows a horizontal rail of the stages it actually
schedules or reports, followed by the detailed stage table and existing result.
This is a visual adaptation of `PDF-proverka`'s overview, project cards and
pipeline. The current API has no per-section project, finding or expert-decision
totals, so the UI does not invent them. This task changes no analysis behavior,
contract, migration or `origin/main`; the integrated development candidate has
contract `1.13.0` and migration head `0043_stage_ai_generations`.
The owner requested focused checks and publication to `origin/dev` only.

**Updated 2026-10-30 by `CMP-INT-CODE-1030` (integrated development candidate; publication record in its report).** CMP C2–C4 runtime includes version comparison and stage intake/pairs/assemblies, sheet maps and stored text, registered graphic evidence, bounded consented AI review/classification/synthesis, one-cycle recorded repair/undo, durable single/batch seven-step chains, expert cards/verdicts/escalation and grouped XLSX/PDF/HTML journals. Four stage tabs and immutable evidence navigation are integrated. R-148 beta choices are implemented: fresh cost preflight/finite-cap approval for ordinary, AR v3 and repeated Runs; background complete PDF interpretation with durable progress/error; and `п.м`↔`м` at factor1. Accepted metered consent enforces its cap even with raised limits; old accepted commands retain historical policy. Contract `1.13.0` has 230 paths / 256 operations / 619 schemas, migration head `0043_stage_ai_generations`. Owner dev hotfixes `99b337fb`/`06b94745`, their default-off controls and navigation are preserved. Root fixed command/worker locking, atomic child creation, cancellation and fresh receipts; AI generations retain paid replies and refuse uncertain resends. The presentation script is `CMP-PRESENTATION-1030.md`; its browser run is unverified. Full gates, heavy batteries, browser execution, exposure acceptance and live spend remain deferred to 2026-10-31 (D-290). No main publication is authorised. The paragraphs below retain historical measurements and earlier candidates.

**Updated 2026-10-30 by `HOTFIX-AR-ORIGINAL-PROFILE-INT-20261030` (development
candidate only).** The complete pre-change АР v3 solution is preserved on remote
branch `ready/ar-v3-20261030` at `99b337fb6e632ebd585f53134eb4425131cfe0b7`.
The default start for a confirmed АР version now uses an ordinary text Run with a new
draft АР profile. Its nine source resources are copied byte for byte from
`SU10KAZ/PDF-proverka` at `3c99481719218b9cfa7560886529916646c61939`;
the executable prompt embeds all eight Markdown resources verbatim and adds the current
Run's text evidence and JSON output rules. The original app's block, norm, review and
Excel pipeline is outside this profile-only change; numeric norms in the copied text
are historical context, not verified requirements. The ordinary start and raised-limit
switch now cover all 15 sections. Old six-check group Runs remain readable, while its
start is removed from the default version screen. Shared contract `1.13.0` has the
same 131 paths / 148 operations / 432 schemas and migration head `0039_comparison_core`.
The owner requested focused checks and one publication to `origin/dev`, without a
complete gate or live provider call. `origin/main` is unchanged by this task.

**Updated 2026-10-30 by `HOTFIX-SECTION-LIMITS-INT-20261030` (development
candidate only; no deployment claim).** The default-off «Повышенные лимиты
ИИ-анализа» switch now covers ordinary `startRun` for all 14 text-profile
sections as well as the separately served six-check AR v3 start. In the raised
mode an ordinary Run pins a distinct immutable 64,000-token profile/bundle pair,
persists the choice with its accepted command, records spend without the
application's USD cost halt, and keeps a stable 12-window operational input
bound. A provider may still refuse its output or context size. The shared
contract is `1.12.0` (131 paths / 148 operations / 432 schemas), adding only
the optional strict `StartRunRequest.relaxed_limits` field; migration head is
still `0039_comparison_core`. The owner requested focused checks and publication
to `origin/dev` only, without a complete gate or a live provider call.
`origin/main` and the deployed host are not addressed by this hotfix.

**Updated 2026-10-30 by `HOTFIX-UI-INT-20261030` (development candidate only; no
deployment claim).** The temporary «Повышенные лимиты ИИ-анализа» switch on the six-check
AR v3 start defaults off. When selected, the accepted group command persists that choice
for every child Run, disables the application's cost-derived input refusal and per-Run
cost halt, and requests up to 64,000 output tokens instead of 16,000; provider limits
can still refuse the request. Ordinary section-analysis starts are unchanged. The
navigation no longer duplicates the brand's home link, and the app has a favicon.
The shared contract is `1.11.0` (131 paths / 148 operations / 432 schemas), with one
optional request property; migration head remains `0039_comparison_core`. The owner
requested focused checks without a complete gate and publication to `origin/dev` only.
`origin/main` and the deployed host are not addressed by this hotfix.

**C3 candidate, 2026-10-29 (separate branch; not published):** `CMP-SEAL-C3` freezes contract `1.12.0` at 204 paths / 230 operations / 570 schemas and migration `0041_comparison_stage_core` with fifteen new tables. `CMP-STAGE-PAIR-01` serves seven pair/assembly and ten upload operations behind `versions,stages`; its first ZIP caller bounds raw bytes and disk, applies the reviewed policy and PDF envelope. The subsequent `CMP-STAGE-LINK-01` branch now serves six sheet-link operations, with stored passports, nonbinding hints, keyed map revisions and a second browser tab. `CMP-STAGE-TEXT-CORE-01` adds pure bounded text-fragment extraction and conservative exact proof; `CMP-STAGE-TEXT-DIFF-01` adds bounded raw differences and nonbinding left→right cross-sheet hints; `CMP-STAGE-TEXT-STORE-01` adds atomic append-only evidence storage under a current map revision; `CMP-STAGE-TEXT-READ-01` serves four read-only evidence GETs. `CMP-STAGE-TEXT-RECOMPUTE-01` now serves the keyed durable two-step recomputation and registers its lease-fenced worker; full chain runs remain stubs. D-262 stays open until integration. On 2026-10-30 the owner deferred full gates/heavy windows to tomorrow and authorised functional code delivery to dev; no prior gate success or publication is inferred. The paragraphs below record earlier merged and measured states. The integrated C2 candidate also contains the newer AR development fixes from `e8567a19`; its earlier acceptance record is in `CMP-WAVE-C2-REPORT.md`. Today's dev publication follows the owner override recorded in `CMP-INT-CODE-1030.md`.

**Updated 2026-10-29 by `CMP-WAVE-C1` (development only; product `VERSION` is `0.9.0`).** The comparison modules' second wave `CMP-C1` (integrator `pdf-analysis-70`, report `docs/program/CMP-WAVE-C1-REPORT.md`) was integrated at contract `1.10.0` and migration `0039_comparison_core` — its data step turns every active `0035` sheet-pair approval into a manual matrix edit, so a deploy that runs it needs a dump of the production database first (`R-146n` item 3) — and, behind the module flag, the sheet matrix with manual edits, the per-sheet engine, the series of adjacent transitions, the overlay viewer and the screens of «Сравнение версий» (steps 1, 2, 3, 5; the AI steps are wave C2). The comparison modules' first wave `CMP-C0` (planner and integrator session `pdf-analysis-12`, branch `integration/compare-modules`, report `docs/program/CMP-WAVE-C0-REPORT.md`) is merged here: contract `1.9.0` (nineteen operations of the two modules sealed as stubs, `ADR-0025`), migration `0038_comparison_foundation`, dependencies `numpy`, `opencv-python-headless` and `reportlab` (`D-256`: the shared `.venv` must be re-bootstrapped), the module flag `ProductVersion.comparison_modules` with default `none` (enabling needs `AUDITMANAGER_COMPARISON_MODULES` on `api` and `worker`, which is also where the owner confirms the widened risk `A-12`), the durable comparison queue with its spend journal, the comparison-only mark of an uploaded version, the ZIP-set and PDF-batch intake, and the one granted change in `jobs/` (`CMP-SPEND-01`: a connection with an active comparison call counts as busy for the Run queue). The operations that are still stubs answer `503` (sealed by `CMP-SEAL-C0`); which of the nineteen do real work after this wave is stated in the wave report and `docs/program/CMP-SEAL-C0.md`, and the engine, overlay and AI layers are later waves. The owner's eleven poll answers `Q-CMP-1`…`Q-CMP-11` are recorded as `R-147a`…`R-147k` with their provenance (the planner session's report, not the integrator's own hearing); the waived complete gate is `D-255`; the debt ids `D-260` and above are reserved for the CMP integrator (its first five rows are listed under «Open items» of the wave report and are not yet in `DEBT_REGISTER.md`). Measured on the merged tree: `tests/unit` + `tests/contract` (minus the three `D-220` files) + journey conformance 5760 passed / 76 skipped; web `tsc`/`eslint` clean, `api:verify` 130 operations, `vitest` 3287; whole `tests/integration` in two halves 7354 passed / 28 skipped and 3691 passed (13 setup errors from the object store while 1.87 GiB was free, rerun green at 3.3 GiB, `D-205` class). Two unit tests and the eleven `profile_queue` integration tests that were red on the CMP branch were repaired by its own tests-only lane before this merge. No complete `make gate` (`D-255`), no browser journey, no model call. `origin/main` was `94d3dc46` when this was written; later the same day the owner merged `dev` `038a1cea` into `main` himself as pull request #13 (merge commit `2651cc7a`, tree identical to `038a1cea`), so the comparison foundation is on `main` and in whatever the deploy workflow then built: its result and `infra/deploy/verify-deployed.sh` on the host were not seen by the integrator. **Earlier the same day:** **Updated 2026-10-28 by `AR-CLOSE-1026` (development only; product `VERSION` is `0.9.0`).** Wave `PW5` (`docs/program/dispatch/PRODUCTION-WAVE-PW5.md`) is closed and an independent judging round over `PW4`/`PW5` was run and fixed (`D-253`): four read-only judges found 34 surviving findings, none HIGH, and three lanes fixed the MED ones (AR v3 citations are classified provisional by the paragraph they were grounded to, `exportRunXlsx` works for AR v3 Runs, section omission claims prove absence over every shown page and respect text-less and recognised pages, the budget's fixed prompt term comes from the run's own bundle, a replayed comparison summary is judged current from its sealed evidence, the registration day cap counts only pending and approved requests, the run CSV skips leading blanks and invisibles, preset keys are actor-scoped, release note `0.9.0` is revision 3). The owner's seventh poll is answered and built (`R-146ao`…`R-146bd`, accepted risks `A-9`…`A-11`); standing disk maintenance under `R-146bd`. The activation of AR v3 is PREPARED on the development host and runs on no live host (`D-247`, `AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01.md`). **Measured on this tree with a recreated lane database at head `0037`:** the whole `tests/integration` directory in two halves, 6021 + 4331 passed and 27 skipped, none failed (54 and 15 minutes); `tests/unit` + `tests/contract` (minus the three files of `D-220`) + the journey conformance test 4732 passed and 76 skipped with `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent` (the owner is re-cloning `/root/projects/PDF-proverka`, `D-252`), one thread-timing test red under load and green alone three times (`D-254`); web 3237 passed, `tsc` and `eslint` clean, `api:verify` 111 operations. No complete `make gate`. Open owner items: the live-host steps of AR v3, `PROXY_LLM_*` for the live identity probe, supplier CSV for the sections other than АР, the `D-230` host steps, the choices listed at the end of `D-253`. **Also 2026-10-29, the dev integrator:** the owner activated AR v3 on the live host with `scripts/ar-v3/activate-live.sh` (`R-146be`), and all six Runs failed on their first model call (provider 400, `Schema type 'oneOf' is not supported`; the Runs took the environment route `PROXY_LLM_*`, not a connection; owner's probe `scripts/ar-v3/live-schema-probe.py`: T3 400, T4 200). `AR-V3-WIRE-SCHEMA-01` (lane `af5460ba`, merged `25cc1cdf`, `docs/program/AR-V3-WIRE-SCHEMA-01.md`) sends every provider the wire form of the response schema, equal to the schema probe T4 got 200 for; the sealed schema, prompt, pack and digests are untouched. Measured on the merged tree: unit+contract 6554 passed / 76 skipped, `tests/integration/{executors,analysis_text,analysis,runs}` 2413 passed / 22 skipped; **not yet sent by a live Run** (`D-280`..`D-283`). `origin/main` is `5e0fe232` (the owner's PR #14, comparison `CMP-C1`); the owner deployed it and `verify-deployed.sh` on the host answered that the stack IS this tree (images identical, head `0039_comparison_core`, no published credential), after a first deploy was refused because the host clone held two untracked files (the activation script's `alpha.env` backup and the hand-copied `scripts/ar-v3/`). The owner then merged the fix as PR #15 (`origin/main` `35ac93ca`, deployed): the second live group passed the provider call (no 400) and failed again, at the citation stage — all six model calls ended `truncated` at exactly 4,096 output tokens on 65–70 thousand input tokens (cost about USD 0.17–0.18 each, USD 1.05 for the six), and the stage refuses a truncated reply (`saved_reply_incomplete`). The output cap in `runs/v3_worker.py` (`V3_BETA_SETTINGS`) is raised to 16,000, the largest the settings class admits (`93884e0f`, `D-284`; `tests/unit/runs` + `tests/integration/runs` + `tests/integration/jobs` 1122 passed); it is on `origin/dev`, not yet deployed, and not yet proven by a live Run. **Later 2026-10-29 (live AR v3 through connections):** the owner switched the live stand to `AUDITMANAGER_PROVIDER_SOURCE=database` and routed «Анализ текста» to `kzSonnet` (an `ssh_command` connection to Claude Code on the development server); every call was cut at exactly 780 s (the 900 s attempt watchdog less a 60 s margin) with `dependency_unavailable` although the command was alive. By the owner's rule (do not limit the model's thinking; check that the session is alive; ceiling 2 h, silence window 10 min) `AR-V3-LIVENESS-01` (lanes `009ab1de` and `71a2efe5`, merged `8336e687`, `docs/program/AR-V3-LIVENESS-01.md`) makes an attempt live while its SSH command sends heartbeats: hard cap 7200 s, stall 600 s, sealed `effort` passed to the command, no thinking cap. Measured on the merged tree: unit+contract 6680 passed / 76 skipped, `tests/integration/{jobs,workers,executors,runs}` 1342 passed / 16 skipped. The new command is installed on the development server (smoke-tested); the stand side is on `origin/dev`, **awaiting deployment and proof by a long live call** (`D-285`..`D-288`). **After the liveness deploy (`main` `34492653`):** the first live calls still ended after exactly 10 min 01 s — the command watched a regular file and the CLI writes nothing to a file until it exits (`D-289`); `AR-V3-LIVENESS-PIPE-01` (`9211b1af`) reads the CLI through a pipe (tests of the command 283 passed; an end-to-end run with the real CLI streamed events and heartbeats) and is installed on the development server; the repository copy reaches the stand's `tools/` with the next deploy, the running stand needs no change.

**Updated 2026-10-27 by `AR-CLOSE-1026` (development only; product `VERSION` is `0.9.0`).** The owner ordered the sections, their prompts and workflow, and the big roadmap's code remainder finished; the wave `PW4` (`docs/program/dispatch/PRODUCTION-WAVE-PW4.md`, measured gap report `docs/program/ROADMAP-GAP-2026-10-27.md`, integrator ruling `R-146an`) is merged on the integration branch: **(1)** the 12 section profiles `PS POS TX KJ KM OV VK PT EOM SS ITP GP` are version `1.2.0` (`AI` and `PB` stay `1.1.0`), status `reviewed` without a human review (`A-7`), and ask additionally for same-document checks inside the two existing categories — a table total against its rows, a unit equivalence by two definitional factors, a ППКП capacity against the connected devices, land-balance rows against the written total; every omission-type check was decided against (an absence has no quote) and the widened prompts were never run on a model or on real text (`D-238`); **(2)** a section run on a volume above one model call is analysed in whole-page windows (`MAX_ANALYSIS_WINDOWS` = 12, one cost meter, one effect-journal entry per window, resumable; `D-242`); **(3)** «Спецификация и цены» and «Предложения» accept a version confirmed in any of the 15 sections (migration `0034_pass_scope_all_sections` replaced the database trigger that pinned АР; the contract stayed `1.7.0` at that point, prose only; `D-243`); **(4)** the dashboard sections panel and the section registry (`analysedBy`) say what is true after W59; **(5)** a fragment test reads every narrowing and widening sentence of the 14 prompts and 30 hand-authored positive and negative specimens are filed (`fixtures/recorded/sections_widen/`); **(6)** libpq error verbosity is terse so that row data cannot reach a log (`D-237`, unrun in the images). **Measured on the integration tip with a recreated lane database at head `0034`:** the whole `tests/integration` directory 9827 passed and 27 skipped in 58 minutes; the whole `tests/unit` 2758 passed and 3 skipped (one run showed one timing failure of `test_runner_long_poll_cap.py` while a lane was running, passing alone and in the rerun); `tests/contract` without the three files of `D-220` 1175 passed; the web suite 200 files / 3050 passed, `tsc` and `eslint` clean; no complete `make gate`. Open owner choices of the wave: `D-236`. **(7)** wave B `COMPARE-PERSISTED-SUMMARY-01` is merged: an expert's approval of a sheet pairing (`approveSheetPairing`, `withdrawSheetPairing`) is stored append-only, `compareDocumentVersions` returns the sealed raw differences of approved pairs only, and `generateComparisonSummary` is a command (a read never calls a model) answered from a recorded model keyed by the request digest — no live path, no real recording yet (`D-244`); the contract grew by three operations that were sealed under `1.7.0` (`D-244`), and the shared version then moved to `1.8.0` (`CONTRACT-1-8-0-01`, owner ruling `R-146ar`). **(8)** the owner's seventh poll (`R-146ao`…`R-146bc`, accepted risks `A-9`…`A-11`) was answered and its first items built: the run CSV neutralises formula prefixes and registration refuses the 41st request in 24 hours (`D-246`); the AR v3 terminal now publishes the grounded findings of citations that passed both gates, an expert decides them through the existing `appendDecision`, and `getRunNormVerification` answers the canonical report (`AR-V3-DECISIONS-01`, migration `0036`, `D-248`); the activation of AR v3 was PREPARED on the development host (decision file, 22 query vectors reproduced from the frozen embedding profile, six scope maps, an independent second AI check, six rehearsed promotions, a sealed pack on the local custody lane — `D-247`, `AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01.md`) and **nothing of it runs on a live host**; no subject-matter expert took part in anything of it (`A-10`, `A-11`). The rest of that poll is built too: the two review labels are switched off by one constant (`SHOW_REVIEW_INDICATION`, `A-10`), the `documentation` category with a mechanical absence check and the OCR context block reach the sections (`SECTION-CATEGORY-OCR-01`), and «Настройки анализа» has presets — named executor selections with append-only revisions, chosen at run start (`ANALYSIS-PRESETS-01`, migration `0037`).

**Updated 2026-10-26 by `AR-CLOSE-1026` (development only; product `VERSION` is `0.8.2`).** The AR v3 beta six-Run path is code-complete behind an empty reviewed-pack registry; what activates it is data and review that no code can supply (`D-204`, `AR-V3-BETA-ACTIVATION-RUNBOOK-01.md`). New this window: a sealed reviewed-pack manifest loaded by both composition roots from `AR_V3_BETA_PACK_MANIFEST` and passed to `api` and `worker` by `infra/deploy/compose.server.yml` (`AR-V3-BETA-PACK-INSTALL-01`, `-PACK-DEPLOY-01`); a `plan`/`promote` command for one retrieval set that refuses a request whose targets differ from the reviewed map (`-SET-TOOL-01`, `-REVIEW-FIXES-02`); an offline builder and validator of the six scope maps (`-MAP-TOOL-01`); a read-only exporter of paragraph rows and a measurement of the 22 candidate spans on the qualified snapshot, all inside the 22,000-character cap as a lower bound (`-SPANS-MEASURE-01`); the authenticated read `getArV3BetaPackStatus` at contract `1.5.0` and, in «Настройки анализа» and the version's run list, the pack status and the control that starts six checks only when a pack is installed (`-PACK-STATUS-API-01`, `-PACK-STATUS-WEB-01`, `-WEB-FIX-01`); release note `0.8.1` judged by an independent reader (`RELEASE-0-8-1-DEV-01`). Measured on the exact tree `dbf0fb76` with no complete gate: `tests/contract` 1155 passed, web lint and typecheck clean, `next build` exit 0, the full Vitest suite 2952 passed in 194 files, and the whole `tests/integration` directory on a real PostgreSQL and MinIO lane with the corpus symlink attached, in two runs because the host disk reached 100 % during the first: the first run gave 7878 passed and 26 skipped before the object store began refusing writes from about 52 % on (297 failures and 394 errors in 100 files, almost all `dependency_unavailable` for `blob_storage`), and the same 100 files rerun whole on the same tree with 2.2 GiB free gave 854 passed, 0 failed, so every test in the directory passed on the exact tree but not in one uninterrupted run (`D-205`). That directory was red on the clean `origin/dev` tip `354a9092` (100 failures, 80 of them one cause: the product purge tool refused a database at head `0032` because two tables and one command type were unclassified, and it also deleted `executor.*` audit events that three documents say to keep); the tests and that tool were repaired and every shared or deployed-path change was read by an independent judge, see `D-213`, `D-214`, `D-215` and `D-218`. **No complete `make gate` was run and none can run on this host** (`D-205`); there is no `GATE OK`, no beta acceptance, and `origin/main` is untouched. The debt register was re-measured by three audits (`DEBT-AUDIT-1…3`): about 80 rows checked, 24 found closed in the tree, 21 narrowed; open work is `D-204`…`D-218` and the rows the audits kept open; the static B1–B12 coverage matrix (`BETA-STATIC-MATRIX-02.md`) gives no `PASS` and names what each criterion still needs.

**Updated 2026-10-26 by `AR-CLOSE-1026` (development only, second part of the day; product `VERSION` is `0.8.2` after the merge of `main`).** The AR v3 beta six-Run path is code-complete behind an empty reviewed-pack registry **after two defects found by the `PROD-11a` probe on 2026-10-26 and closed the same day (`D-225`): the database refused its CITE stage row (migration `0033` widens the check), and the recorded provider binding had no verifiable cost (`PROD-11C` marks it unmetered for the sealed v3 pair only); a Run still cannot start without the activation data (`D-204`)**; what activates it is data and review that no code can supply (`D-204`, `AR-V3-BETA-ACTIVATION-RUNBOOK-01.md`). New this window: a sealed reviewed-pack manifest loaded by both composition roots from `AR_V3_BETA_PACK_MANIFEST` and passed to `api` and `worker` by `infra/deploy/compose.server.yml` (`AR-V3-BETA-PACK-INSTALL-01`, `-PACK-DEPLOY-01`); a `plan`/`promote` command for one retrieval set that refuses a request whose targets differ from the reviewed map (`-SET-TOOL-01`, `-REVIEW-FIXES-02`); an offline builder and validator of the six scope maps (`-MAP-TOOL-01`); a read-only exporter of paragraph rows and a measurement of the 22 candidate spans on the qualified snapshot, all inside the 22,000-character cap as a lower bound (`-SPANS-MEASURE-01`); the authenticated read `getArV3BetaPackStatus` at contract `1.5.0` and, in «Настройки анализа» and the version's run list, the pack status and the control that starts six checks only when a pack is installed (`-PACK-STATUS-API-01`, `-PACK-STATUS-WEB-01`, `-WEB-FIX-01`); release note `0.8.1` judged by an independent reader (`RELEASE-0-8-1-DEV-01`). Measured on the exact tree `dbf0fb76` with no complete gate: `tests/contract` 1155 passed apart from three files that are red on every tree measured here (`D-220`), web lint and typecheck clean, `next build` exit 0, the full Vitest suite 2952 passed in 194 files, and the whole `tests/integration` directory on a real PostgreSQL and MinIO lane with the corpus symlink attached, in two runs because the host disk reached 100 % during the first: the first run gave 7878 passed and 26 skipped before the object store began refusing writes from about 52 % on (297 failures and 394 errors in 100 files, almost all `dependency_unavailable` for `blob_storage`), and the same 100 files rerun whole on the same tree with 2.2 GiB free gave 854 passed, 0 failed, so every test in the directory passed on the exact tree but not in one uninterrupted run (`D-205`). That directory was red on the clean `origin/dev` tip `354a9092` (100 failures, 80 of them one cause: the product purge tool refused a database at head `0032` because two tables and one command type were unclassified, and it also deleted `executor.*` audit events that three documents say to keep); the tests and that tool were repaired and every shared or deployed-path change was read by an independent judge, see `D-213`, `D-214`, `D-215` and `D-218`. **No complete `make gate` was run and none can run on this host** (`D-205`); there is no `GATE OK`, no beta acceptance, and `origin/main` is untouched. The debt register was re-measured by three audits (`DEBT-AUDIT-1…3`): about 80 rows checked, 24 found closed in the tree, 21 narrowed; open work is `D-204`…`D-235` and the rows the audits kept open; the static B1–B12 coverage matrix (`BETA-STATIC-MATRIX-02.md`) gives no `PASS` and names what each criterion still needs. The production version was decided by the owner on 2026-10-26 (`R-146a`…`R-146z`) and written as `ADR-0021`…`ADR-0024` and `PRODUCTION-READINESS-PLAN-01.md` (23 items `PROD-00`…`PROD-22`, accepted risks `A-1`…`A-5`); **Since then, on the same day: АР v1 and v2 are removed from the product (`PROD-11`)** — `startRun`/`reauditRun` on a version classified АР now answer the existing `section_profile_unavailable`, the АР analysis path is the six-Run v3 group only, and the 33 АР-bound steps of the acceptance journey are marked `pending_v3_activation` (`D-233`); the group start now queues and carries its six Runs (`D-231`); the deploy gates (`PROD-02`, `PROD-03`), the TLS/ACME layer (`PROD-01`, never run on a host), the project-erase core (`PROD-07a`), the database-role work (`PROD-04`, never run on a host: `D-235`) and the exposure review (`PROD-15`, `D-234`) are built; `SEC-RUNNER-CAP-01` bounds the runner long poll and refuses plain-http public model destinations. Of the first batch, only three items were built at the time of the earlier statement: `PROD-14.0` (one expectations file that every section lane edits instead of four shared tests, `PROD-14-0-EXPECTATIONS-01`), `PROD-09` (the manual scan helper `scripts/release/manual_scan.sh` and the eight-line release checklist) and `PROD-10` (what АР v3 needs moved out of `ar_v2` into `ar_shared`, behaviour byte-identical; the move of the live journey off АР is not done, and the saved text layer that АР optimisation reads is an open question, `D-222`); the rest is not (`D-219`). The wave `PW2b` (`docs/program/dispatch/PRODUCTION-WAVE-PW2B.md`: TLS and ACME in `infra/`, the АР text-layer probe, the model-identity probe tool, and the 14 section profiles to `reviewed` without a human review, accepted risk `A-7`) was launched on 2026-10-26 from the integration branch and is merged. **Measured on the integration tip `71c535ca` (code; the commits after it are documents) with no complete `make gate`:** `tests/contract` 1161 passed apart from the three files of `D-220`; web lint, typecheck clean and Vitest 194 files / 2956 passed; the whole `tests/integration` directory in two runs on a real PostgreSQL and MinIO lane at the then-current head `0033_ar_v3_cite_stage_id`: the first run 4688 passed and 8 skipped, then 3 `composition` files that failed only because MinIO refused writes at 1.1 GiB free (its own minimum-free-drive threshold, about 1 % of the 119 GB disk) reran whole: 30 passed; the second run (the other 25 directories) 4171 passed and 18 skipped, then 2 `foundation` files that failed only because the lane database was still at `0032` reran after `make migrate`: 9 passed. The `tests/e2e/pc01/test_acceptance.py` pins are red and stale (`D-226`). Nothing of `PROD-01` has run against a host or an authority (`D-227`). The manual scan's first run found a critical advisory in the pinned `next` and three high ones among the production dependencies of `web/package-lock.json` (`D-221`).

**Updated 2026-10-23 for the AR v3 beta group review API and browser read.** The earlier night-window state and its `R-137` W54 repair remain recorded below.
W55b is published on `origin/main` and tagged `v0.6.0`. Its exact-tree gate counts as `GATE OK` under R-125; the deploy workflow selected that tree, and the owner ran `infra/deploy/verify-deployed.sh` on the host with a passing image/tree comparison.
The workflow's own verify step was skipped because a child consumed its stdin; the tested repair is on `origin/dev`. Moving it to main needs a fresh complete gate and a direct exact-SHA owner instruction.
The owner waived five credentialed live W55b product checks; those journeys remain unverified. See `W55B-INT-TAG-01.md`, `W55B-INT-MAIN-VERIFY-ADDENDUM-01.md` and `CFB-INT-DEV-PUBLISH-43.md`.

The development API surface is **176 paths / 198 operations / 517 schemas**, the error catalogue has **27** codes, the migration head is **`0040_comparison_ai_reports`** (migration `0040` adds the twelve tables of the version comparison AI, specifications, reports and launch queue -- the consented AI jobs, the content-keyed pair-check answers and sheet descriptions, the questions and sheet items, the specification extractions and comparisons, the reports with their parts and files, and the launch queue and its entries -- the AI-job column of `comparison_work` and the four `comparison_*` executor work kinds, `CMP-SEAL-C2`; migration `0039` adds the seven tables of the version comparison core -- the builds of the matrix, its manual edit history, the accepted AI links, the series, its transitions and sheet pairs, and the content-keyed sheet-pair results -- the series column of `comparison_work` and the `compare_after_preparation` column of `comparison_upload`, and turns every active `0035` sheet-link approval into a manual matrix edit, `CMP-SEAL-C1`; migration `0038` adds the nine tables of the comparison modules -- upload batches, sets, files and parts, the version-order revisions, the page profiles, the comparison queue with its attempts and its spend journal -- the `upload_kind` of a document version and the `comparison_call` origin of an executor task, `CMP-SEAL-C0`; migration `0037` adds the append-only table `analysis_preset_revision` with its chain trigger and freezes the preset revision on `audit_run`, `ANALYSIS-PRESETS-01`; migration `0036` replaces the function of the deferred trigger `am_verify_norm_citation_partition` so that the stage of the AR v3 review may certify citations, `AR-V3-DECISIONS-01`; migration `0035` adds the two append-only tables `comparison_sheet_link` and `comparison_summary` with their chain triggers, `COMPARE-PERSISTED-SUMMARY-01`; migration `0034` replaces the function behind the optimisation-pass scope trigger so that a pass may pin a version of any section and the vendor list of that same section, `OPT-PROJECT-ALL-SECTIONS-01`; migration `0033` only widened the stage-id CHECK of `stage_result` so that the AR v3 CITE row is accepted, `D-225`), `VERSION` is `0.9.0`, and the shared contract is `1.10.0` after `CMP-SEAL-C1` (`ADR-0025`: eighteen operations of the version comparison core sealed as stubs answering `503 dependency_unavailable`, the optional `CreateComparisonUploadRequest.compare_after_preparation`, and the three `0035` operations withdrawn while the versions module is on; it was `1.9.0` after `CMP-SEAL-C0`: nineteen operations of the comparison modules sealed as stubs answering `503 dependency_unavailable`, the optional `DocumentVersion.upload_kind`, `ProductVersion.comparison_modules` and `RunnerImage.crop_id`; the module set `AUDITMANAGER_COMPARISON_MODULES` defaults to `none`; it was `1.8.0` after `COMPARE-PERSISTED-SUMMARY-01` under `R-146ar` (three operations: `approveSheetPairing`, `withdrawSheetPairing`, `generateComparisonSummary`; it was `1.7.0` after `PROD-11-AR-V1-V2-REMOVAL-01`, `1.6.0` after `EXEC-PAR-START-01`, and `1.5.0` after `AR-V3-BETA-PACK-STATUS-API-01`; `2.0.0` stays reserved, `D-233`; `AnalysisProfileStatus.builtin` is gone and `reviewed` is described as a lane's written answers with no human review)). The authenticated group review read exposes six verified, user-safe scope outcomes (`AR-V3-BETA-GROUP-API-SEAL-01`); the new authenticated read `getArV3BetaPackStatus` says whether a reviewed pack is installed and carries its reviewer attestation, nothing else; without `AR_V3_BETA_PACK_MANIFEST` the registry is empty and group starts refuse.
The browser's group review now compiles against the v3 stage union; its pending, invalid-ID, refused-read and inconsistent-answer branches are covered by the rendered-language guard. The profile-specific stage has a Russian label without changing the nine legacy stage IDs. The generic Run page selects the pinned v3 profile before any stage is reported, shows no legacy PC-01 placeholders, and never offers its canonical finding-review link for this review-only beta profile.
The runner can fetch one verified PNG for an active claim; no run stage sends one until W56b activates its image policy. `EXEC-IMAGE-CHANNELS-01` carries a selected PNG through direct/VPN HTTP, pull command, local endpoint and MCP session; the latter two require image opt-in.
SSH command/tunnel connections are served in `EXEC-SSH-CROPS-01` and `EXEC-SSH-TUNNEL-CROPS-01`: the command carries a verified PNG; the tunnel uses the HTTP adapter after checking current secrets and a pinned SSH host key. The image stage still does not create a task.
The `R-143` connections and pull channel were added under `R-144` (`EXEC-CANDIDATE-1.md`, `EXEC-CANDIDATE-2.md`). `origin/main` carries `0.8.2` (tip `bf5528a6` on 2026-10-27) since the owner's own pull-request merges (the first `48c8e34c` = `0.7.0`, no gate; the last `cecf8668` = pull request #11; see `RELEASES.md`); host verification of `v0.7.0` and its tag are owed. The last tag is `v0.6.0`.
Run `infra/deploy/verify-deployed.sh` for the current deployment; this document is no substitute for that probe.

`EXEC-ENV-OPENROUTER-01` adds the baseline option in «Назначения»: with source `database`, a worker holding the complete `PROXY_LLM_*` triplet registers one OpenRouter-compatible HTTP connection and queues its probe.
After an `ok` probe it is selectable; registration does not replace the Codex route. The `/api/v1` OpenAI Chat variant carries the same verified PNG as other HTTP variants.
A graphical-analysis stage still needs W56b prompt and evidence policy before issuing crop tasks; SSH command/tunnel transports can carry a verified PNG when a future stage issues one.

`EXEC-PAR-START-01` lets `startRun` name an executor connection (`executor_connection_id`; no fallback, `reauditRun` keeps it, `RunStatus.executor` shows it), `EXEC-PAR-QUEUE-01` adds `AUDITMANAGER_WORKER_SLOTS` (default `1`) with one active run per connection in the claim, and `EXEC-PAR-WEB-01` adds the «Исполнитель» selector to the start control and the executor to the run list and page. Whether a stand runs them is read from `infra/deploy/verify-deployed.sh`, not from this file. A stand shows parallel runs only with `AUDITMANAGER_PROVIDER_SOURCE=database`, `AUDITMANAGER_WORKER_SLOTS` above `1` and two probed connections; the journey is an operator check. See `dispatch/EXEC-PARALLEL-RUNS-PLAN.md` and, for the operator's check, `EXEC-PAR-OPERATOR-CHECK-01.md`.

## Normative corpus (W54)

The 674-document, 31,619-file source drop has complete file checksums and a restore-verified base dump with 348,777 paragraphs and 55,702 chunks
(`W54-CORPUS-OPERATE-01`, `W54-CORPUS-PROMOTION-01`).

Under `R-137`, 121 blocks containing the recognition model's own reasoning were re-read by Sonnet subagents of a Claude Code session. Their answers passed the unchanged two-read rule; the ignored ledger has 121 applied repairs, 0 unreliable blocks and no charge, and the real drop's ledger validation accepted it.
The repaired key is `2026-07-23..2026-08-20+17d+121r.0a1bafe103ff`. A 16-page spot check found two single-word deviations from print (a map label and a silently corrected printed typo) and two table-layout notes; under `R-138` the owner accepted the ledger. See `W54-SESSION-REPAIR-01.md`.

The repaired snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74` (674 documents,
350,194 paragraphs, 55,855 chunks) is loaded in the local promotion database
with a complete BGE-M3 embedding build (61,573 windows, set digest
`e7fac64c…`), dumped and restore-verified, and exported as a verified bundle
with `build: present` (`W54-SNAPSHOT-LOAD-01`, `W54-EMBED-BUILD-01`,
`W54-BUNDLE-EXPORT-01`). `W54-LOCAL-IMPORT-01` imported that bundle into an
isolated local stack and served search, document, paragraphs and ranged PDF
from it; «Нормы» now also has a catalogue (`listNormDocuments`) with
derived display designations, and a run's findings download as Excel
(`exportRunXlsx`). The stand import, its copy record and the admin's
designation of a current snapshot have not run; they need an owner window.

## Code-first series (R-135)

The plan is [`CODE-FIRST-TO-BETA.md`](dispatch/CODE-FIRST-TO-BETA.md);
`R-135` defers the complete beta gate to the final code candidate, and each
development candidate carries only its focused evidence. No beta acceptance
is claimed. Detailed evidence: `CFB-INT-DEV-PUBLISH-17.md` … `-67.md` and,
for the `R-139` night window of 2026-10-20, `NIGHT-1020-INT-01.md`.

- **Unserved preparations.** W56a (recorded-only AR v2 profile, source-bound
  request, observations, merge, finding plan; real model/price verification
  `W56A-MODEL-PIN-01` stopped), W57a (retrieval, map, qualification and
  citation preparations, v3 request/parser/grounding; qualified set, CITE
  stage and CAP-01 open), W57b (certified XLSX chain, catalogue custody and
  saved-text readers, slug chain; reviewed slug source and 0024 seal open),
  W56b (Attempt-fenced readers for text windows, crops, regions; vision
  policy open) and W58 (source mirror, isolated DB-plus-Blob restore drill,
  synthetic restore passed, real drill not run).
- **АР v3 beta group.** The API has explicit start/read operations for an atomic six-Run group with separate identity, immutable pins and idempotent replay. `getArV3BetaGroupReview` reads six verified, review-only scope outcomes, including pending and failed members; it exposes no internal custody data or numerical conclusions. «Настройки анализа» accepts a group ID in the address and shows the six outcomes and provisional quotes without a new start control. No reviewed six-map/six-set pack is installed, so new group starts refuse before any write or provider action. «Настройки анализа» shows the 22 F1.3 topic/source dispositions and still says v3 execution and numerical conclusions are unavailable. A full repaired snapshot passed isolated local custody qualification (`AR-BETA-LOCAL-CUSTODY-01`); the stand still lacks that import.
- **W59 sections (served).** An expert confirms a version's stage (П/Р) and
  one of 15 sections (`classifyDocumentVersion`, `getVersionSectionReview`,
  migration 0024); run start and re-audit route by the confirmed section
  through a text-profile registry — AR, 13 legacy-ported profiles and an
  authored one for ПБ, all `reviewed` since 2026-10-26 **without any human
  review** (`R-146ag`, accepted risk `A-7`, `SECTION-REVIEW-LEDGER-01.md`) — and refuse an unclassified version or a section
  without a profile; the project screen groups documents by section.
  «Настройки анализа» lists the profiles (`listAnalysisProfiles`); all 14
  non-AR profiles have synthetic recorded replay cases, not expert acceptance.
- **Run references.** A stopped run's page ends with «Нормативные ссылки»
  (`getRunNormReferences`): the standards cited in the run's saved text, each
  resolved against the snapshot the run pinned into five outcomes; no finding,
  no model call, no migration.
- **Versions.** An expert corrects a confirmed classification by an append-only
  revision with a reason (`correctVersionClassification`, migration 0028); the
  original confirmation is never changed. `uploadDocumentVersion` adds the next version to a set;
  `compareDocumentVersions` serves the deterministic comparison (same stage
  and section) and the W62 П→Р comparison; `carryOverDecision` carries an
  expert decision onto an `unchanged` matched finding as a new event.
- **Work and money.** «Диспетчер» (W61 code, migration 0025): an administrator
  assigns a project or document set to an expert who works it through «Мои
  задачи»; every change is an append-only event. The «Оптимизация» tab (W60,
  migration 0026) stores price lists (CSV/XLSX, immutable revisions with a
  parse report) and vendor lists per section; no money figure exists without
  a price-list position. «Спецификация и цены» (`getSpecificationPrices`)
  reads the AR specification rows from a version's saved text and matches
  them to the current price list; amounts and per-currency totals only for
  matched same-unit rows with a numeric quantity. «Предложения» (migration
  0027): an expert starts a pass for an AR set and gets deterministic
  `cheaper_analog` proposals from the price list and the effective vendor
  list, decides each (accept / reject / revise) in an append-only history, and
  downloads a formula-escaped CSV; a saving exists only when both prices and a
  quantity do. «Оптимизация разделов» (`getSectionSpecification`) shows a
  section's Form-7 specification across projects whose current version is
  confirmed in it — rows never merged across projects, each priced from its
  own project's list, per-project totals only. No menu item is a stub any
  more. A human review of the 14 profiles has not happened and is not scheduled (`R-146ag`, `A-7`).

## Pointers and history

Read the assigned task, completed `depends_on`, frozen contracts and allowed
paths before editing. `docs/program/DEBT_REGISTER.md` tracks open work. The
complete state at candidate 66 is preserved verbatim in
[the 2026-10-19 state archive](history/CURRENT_STATE_2026-10-19_ec41bb58.md),
and the 320-line state before candidate 17 in
[the 2026-10-16 state archive](history/CURRENT_STATE_2026-10-16_71373417.md).

## Previous release state — wave 48 (historical record)

The full previous release state, including the older CP-00 history, is stored
verbatim in [the dated archive](history/CURRENT_STATE_2026-10-15_ccfb9735.md).
That archive is a point-in-time record of the base tree, not live status.
