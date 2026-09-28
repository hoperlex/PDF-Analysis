# W46-JUDGE-Y — the product, the journey and the stream reports, on `d5c9be5`

**Judge:** `W46-JUDGE-Y` · **lane:** `gate-w46k` (PostgreSQL `127.0.0.1:56400`, S3
`60000`/`60001`, API `56401`, Next `56403`) · **worktree:** `/root/w46k` · **branch:**
`agent/w46-judge-y` · **tree judged:** `d5c9be5` (wave 46's merged tip: `9a295aa` W46-SPEND,
`1c38c52` W46-WIRE, `d5c9be5` the integrator's join repair).

Brief: `docs/program/dispatch/W46-JUDGES-XY.md`, section `W46-JUDGE-Y`. This judge repairs
nothing and owns this file only. Opened before the first measurement and committed after each
section; a section marked *pending* has not been measured yet.

## 0. Provisioning

```
make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12   -> bootstrap OK
.venv/bin/python -c "import boto3"                     -> boto3 ok 1.43.90
npm --prefix web ci                                    -> added 184 packages
make up && make check-services && make migrate         -> gate-w46k-{postgres,s3,s3-init}-1 healthy,
                                                          FOUNDATION-CHECK OK, head 0011_document_section
```

**The instrument.** Four judge databases in my lane's own container, never the gate's
`audit_w46k`: `audit_w46k_judge` was migrated to head (`0011_document_section (head)`) and
driven forward one state at a time through the API; after each state the API was stopped and
the database copied with `CREATE DATABASE audit_w46k_sN TEMPLATE audit_w46k_judge`, so every
state can be served again later, unchanged (sections 4 and 5 use them). Row counts, read from
each copy with `psql`:

| copy | `project` | `document` | `audit_run` | `model_call` |
|---|---|---|---|---|
| `audit_w46k_s0` | 0 | 0 | 0 | 0 |
| `audit_w46k_s1` | 1 | 0 | 0 | 0 |
| `audit_w46k_s2` | 2 | 2 (`KM` 1, `NULL` 1) | 0 | 0 |
| `audit_w46k_s3` | 2 | 2 | 1 (`published`, recorded, 3 findings) | 1 |

The API is `infra/deploy/serve.py` on `127.0.0.1:56401` (health `56402`),
`AUDITMANAGER_PROVIDER_MODE=recorded`, a freshly generated `AUDITMANAGER_API_TOKEN`, the lane's
`.env` with `DATABASE_URL` pointed at the copy being served. Next is `npm --prefix web run
build` (exit 0) with `NEXT_PUBLIC_API_BASE_URL=/bff/v1`, then `next start -p 56403 -H
127.0.0.1` with `AUDITMANAGER_API_UPSTREAM=http://127.0.0.1:56401` and the same token. Sign-in is
the seeded `admin` account migration `0006_app_user` names, through the real `/login` screen,
by the repository's own `session.mjs`; each reading is a cold browser from `cdp.mjs`
(`withColdBrowser`), and the width is `width.mjs`'s `MEASUREMENT`. The API was driven with a
scratch `httpx` script that prints the raw status and body; the screen with a scratch `.mjs`
probe that imports those three modules by path. Neither is committed; every load-bearing
reading is quoted here.

`W46-JUDGE-X` was running `make gate` in `/root/w46j` (PID `2413375`) throughout. Nothing here
ran a test suite while it did, except where section 5 says so.

## 1. Y1 — every number on `/dashboard` against the API's own answer — **all equal, one read**

`GET /dashboard` (raw, bearer from `POST /auth/token`) beside the screen rendered from the same
copy at 780 px, light palette. Each cell reads *API → screen*.

| state | documents by project | findings by verdict | run activity | spend | sections |
|---|---|---|---|---|---|
| **s0** no projects | `[]` → *«Проектов пока нет.»* | 4 × `0` → *Находок: 0*, four rows at 0 | 8 × `0` → *«Проектов пока нет. Прогонов показывать нечего…»* | **key absent** → (not reached: no projects) | 14 × `0` + unclassified `0` → fifteen rows, all 0 |
| **s1** one project, no documents | `[(…, 0)]` → *Документов: 0 на 1 проекте*, row *документов 0* | 4 × `0` → same | 8 × `0` → *«Прогонов пока нет. Среди проектов системы ни один прогон ещё не запускался.»* | **key absent** → (not reached: no runs) | all `0` → all 0 |
| **s2** + a project with one `KM` and one unclassified document | `[(…, 2), (…, 0)]` → *Документов: 2 на 2 проектах*, rows 2 and 0 | 4 × `0` → same | 8 × `0` → same as s1 | **key absent** → (not reached) | `KM 1`, unclassified `1`, 13 × `0` → *КМ: 1*, *Без раздела: 1*, thirteen 0 |
| **s3** + one published run (recorded) on the unclassified document | unchanged → unchanged | `pending 3`, three `0` → *Находок: 3*, *не решено 3*, three rows at 0 | `published 1`, seven `0` → *Прогонов: 1*, *опубликован 1* | `{1, 34400, "estimated"}` → *«Расход по всем прогонам: 0.034400 · вызовов модели: 1 · оценено.»* | unchanged → unchanged |

**Every number the screen renders equals the API's answer, in all four states.** `F-1` is
repaired on the wire: over zero `model_call` rows, `run_activity` carries `by_state` and **no
`spend` key at all** (s0, s1, s2), and one call later it carries all three fields (s3).

**Two things the screen does with the answer that are not "render it":**

- **The run panel drops seven computed zeros.** The API sends all eight `RunState` rows
  (`RunStateCount`: *"Every member of `RunState` is present"*); in s3 the screen shows one row,
  *опубликован 1*, because `run-activity-panel.tsx:76` filters `(byState.get(state) ?? 0) > 0`.
  The verdict panel's own header calls showing a computed zero *"the non-negotiable both the
  brief and `R-23`'s addendum state"*; the run panel, one column over, does the opposite. Not a
  false number — a hidden true one. The pre-wave panel filtered the same way
  (`git show 2ffca8c:web/src/widgets/dashboard/ui/run-activity-panel.tsx` line 95,
  `STATE_ROWS.filter((state) => summary.byState[state] > 0)`), so this is carried, not
  introduced. Low.
- **The spend line is reachable only when a run exists.** With projects and no runs the panel
  returns before the spend sentence, so *«Ни один прогон ещё не обращался к провайдеру…»* is
  rendered only for *runs exist, none called a provider* — which the recorded provider never
  produces. It is covered by the render test's fixture, not by any state I could drive.

### One read and nothing else — measured from both ends

- **Browser**, every `/bff/*` request in the cold load of `/dashboard`, all four states:
  `GET /bff/v1/dashboard 200`. Nothing else.
- **API**, the uvicorn access log of each copy, which also sees anything the Next *server*
  asks for (a server component, a prefetch that renders server-side) and the browser cannot:

  ```
  POST /auth/token 200      <- my driver
  GET /dashboard 200        <- my driver
  POST /auth/token 200      <- the /login screen's exchange (session.mjs)
  GET /projects?limit=50    <- /login lands on /projects (manifest `session.lands_on`)
  GET /dashboard 200        <- the dashboard's cold load: the only call it causes
  ```

  identical for s0–s3. The other requests in the browser's list are Next's own link
  prefetches (`GET /projects?_rsc=…`, `/knowledge-base?_rsc=…`, one per navigation link, and
  one `/projects/{uid}?_rsc=…` per project row) — 9, 10, 11, 11 requests in s0–s3. **None of
  them reaches the API**: the log above has no request between the landing and the dashboard's
  read. The cold-load double `GET /projects?limit=50` judge A measured on `130200d` is gone.

## 2. Y2 — the sentences — **true where the wave rewrote them; false one step past the form**

**What was checked, and held.**

- **Stored when supplied.** `POST /projects/{uid}/documents` with `section=KM` → `201`,
  `getDocumentVersion` → `"section": "KM"`, `psql` → `KM|1`, `NULL|1`.
- **Checked when supplied.** `section` = `""`, `ar`, `ZZ`, `km`, `" KM"` → five times `422
  validation_failed`, *"The section property of the request body is not of the declared
  form."*; `psql` afterwards still `KM|1`, `NULL|1` — nothing written, no silent
  unclassified fallback.
- **The product's form cannot supply one.** `features/upload-document/model/use-upload-document.ts:43`
  sends `body: { file, ...(title === '' ? {} : { display_title: title }) }`; the rendered form on
  `/projects/{uid}` offers *PDF* and *Отображаемое название* and nothing else.
- **The unclassified row is always shown**: *Без раздела* is present in s0 (`0`), s1 (`0`), s2
  (`1`), s3 (`1`) and the decisions state below (`1`).
- **The verdict caption matches what the aggregate counts.** On a copy with six findings from
  two runs, I recorded `accept` on one, `comment` on a second and `reject` on a third (`201`
  each). `GET /dashboard` → `pending 4, accepted 1, rejected 1, needs_manual_review 0`: the
  three never-opened findings of the second run plus the commented one. The screen: *Находок: 6*,
  *не решено 4 · принято 1 · отклонено 1 · нужен ручной разбор 0*. The caption says every
  finding is counted by its current verdict *"включая ту, которую ещё никто не открывал"* —
  **true**. (`revoke` → `422`, *"PC-01 emits no revocation"*, so the enum's *after a revocation*
  branch is unreachable and was not driven.)
- ***контракт* and *операция* are gone from the dashboard.** The rendered `main` text in s0–s3
  contains neither (case-folded substring test on `контракт` and `операци`), and
  `grep -rni 'контракт\|операци' web/src/widgets/dashboard web/src/_pages/dashboard web/src/app/dashboard`
  → nothing, the failure texts in `dashboard-failure.ts` included.
- **The project screen's rewritten sentences are true as written**: *«Раздел документа хранится
  и проверяется на сервере, когда его называют при загрузке; форма загрузки этого продукта
  раздел не предлагает…»*, rendered on `/projects/{uid}` over the project that holds the `KM`
  document.

### Y2-a — "the only analysed section" is false for a document the server stores as `KM` (medium)

The screens say three things about analysis and sections:

- `/dashboard`, sections panel: *«Архитектурные решения (АР) — единственный анализируемый
  раздел: 0»* (`sections-panel.tsx:51`);
- `/projects/{uid}`, the АР tab: *«Сейчас принимаются документы раздела АР … Это правило
  приёма, а не свойство файла»* (`project-sections.tsx:105-108`);
- `/projects/{uid}`, the КМ tab: *«Анализ этого раздела ещё не делается: сейчас принимаются
  документы раздела АР.»* (`project-sections.tsx:120`).

Measured: **the server accepts a document stored as `KM` and analyses it.**

```text
POST /projects/prj_01M3KY9CW2V709Z8RP4NKB5NXR/documents  section=KM   -> 201 ver_01M3KY9DVFFMTTF78QRGCHP5NF
POST /runs {"version_uid": "ver_01M3KY9DVFFMTTF78QRGCHP5NF"}            -> 202
GET /runs/run_01M3KYXQZAQABYCGW8D54EM0G0  -> state published, published_finding_count 3,
                                             analysis_profile_id ap_01M25P3TH08VVTTGJRXYBZZ7RP (the same
                                             profile the unclassified document's run used)
GET /versions/ver_01M3KY9DVFFMTTF78QRGCHP5NF -> "section": "KM"
```

After that, on one screen: *АР — единственный анализируемый раздел: 0*, *КМ: 1*, *Находок: 6*,
of which three came from the `KM` document and none from an `АР` one. On `/projects/{uid}`, the
КМ tab says the section is not analysed yet while the document the server stores as `KM` sits in
the АР tab's list with a published run. No intake refuses `section=KM`; nothing starts a run
conditionally on the section.

**Nothing in the tree hides this — the source says it and the screen does not.** The module
header `W46-WIRE` rewrote, `web/src/entities/project/model/section.ts:28-31`, is exact: *"the
`AR` restriction lives in the analysis prompt (`src/auditmanager/analysis/text/prompt.py`) and in
fixture names, not in what a document is uploaded carrying."* So the restriction is a property
of the prompt, not a rule of intake, and the screen still calls it *правило приёма*. The integrator's
brief premise *"The intake rule, only АР is analysed, is unchanged"* is true of the form path
only. **Wave 46 created the contradiction**: before `W46-SEAL` no document could carry `KM`.

Reachable only through the API, because the form offers no section — which is the path
`W46-WIRE` itself used in W5 to reach *КМ: 1*. **Reproduce:** the four lines above against a
fresh copy, then render `/dashboard` and click `button[data-section="KM"]` on `/projects/{uid}`.
**Cost:** a sentence on each of two screens (*what the analysis is built for*, not *what is
accepted*), or an intake decision that belongs to the owner beside `D-107`.

### Y2-b — the verdict caption explains a label the screen does not show (low)

The caption: *«…— «ожидает решения» здесь не то же самое, что «по ней есть отложенное
решение».»* (`verdicts-panel.tsx:50-53`). The row it is about is labelled **«не решено»**
(`VERDICT_LABELS.pending`, `web/src/entities/expert-decision/ui/verdict-badge.tsx:54`).

```text
grep -rn 'ожидает решения' web/src --include=*.ts --include=*.tsx   -> verdicts-panel.tsx:52 only
```

The quoted term appears nowhere else in the product, so a reviewer cannot connect the caption's
distinction to the row it qualifies. The *meaning* the caption states is right (above); the
*name* it uses for the row is not the row's name. **Cost:** one word.

### A judgement call, stated as one

The rewritten subtitle is *«Четыре панели одного общего чтения по всей системе: …»*. *контракт*
and *операция* are gone, but *одного общего чтения* — "one common read" — still tells the reviewer
how the screen fetches, which is `R-39`'s *transport*, in the author's vocabulary. Low; `D-109` is
the owner's line.

## 3. Y3 — the journey, live — **`e2e:pc01 OK` twice, zero undeclared calls, and it can still go red**

Run twice against my own Next and API, each time on its own copy so the write half starts from
a known state. The literal command, from `/root/w46k`:

```
E2E_PC01_LOGIN=admin E2E_PC01_PASSWORD=password \
  npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:56403 --phase all --out <dir>
```

**Run 1 — a fresh copy of s0 (`audit_w46k_j1`, nothing in it).** Summary, quoted in full:

```
sign-in: ok at /login -- carrying 'am_session' (HttpOnly=true, SameSite=Strict) into every cold browser

write half: 3 step(s), fixture fixtures/synthetic/ar/ar_baseline.pdf

ok  create-project   api=3 {"project_uid":"prj_01M3KZ790V9V8RRT4VN65SPXFV"}
ok  upload-document  api=4 {"project_uid":"prj_01M3KZ790V9V8RRT4VN65SPXFV","version_uid":"ver_01M3KZ84YHXKWX2C98NTAPET3T"}
ok  start-run        api=5 {"project_uid":"prj_01M3KZ790V9V8RRT4VN65SPXFV","run_id":"run_01M3KZ8ZQMMQBTE74WDTAPX57S"} terminal=published in 1514ms/150000ms

ok  root           200  api=1 auth=0 console=0 jar=[am_session] w=780/780
ok  projects       200  api=1 auth=0 console=0 jar=[am_session] w=780/780 {"project_uid":"prj_01M3KZ790V9V8RRT4VN65SPXFV"}
ok  project        200  api=1 auth=0 console=0 jar=[am_session] w=765/780 {"document_uid":"doc_01M3KZ84YFPX19NAJ9K155W2TY"}
ok  document       200  api=1 auth=0 console=0 jar=[am_session] w=780/780 {"version_uid":"ver_01M3KZ84YHXKWX2C98NTAPET3T"}
ok  version        200  api=2 auth=0 console=0 jar=[am_session] w=765/780 {"run_id":"run_01M3KZ8ZQMMQBTE74WDTAPX57S"}
ok  comparison     200  api=1 auth=0 console=0 jar=[am_session] w=780/780
ok  run            200  api=1 auth=0 console=0 jar=[am_session] w=765/780
ok  review         200  api=5 auth=0 console=0 jar=[am_session] w=765/780
ok  sign-in        200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  knowledge-base 200  api=1 auth=0 console=0 jar=[am_session] w=780/780
ok  change-password 200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  blocks         200  api=1 auth=0 console=0 jar=[am_session] w=780/780
ok  optimisation   200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  logs           200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  workers        200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  dashboard      200  api=1 auth=0 console=0 jar=[am_session] w=765/780

write steps checked: 3/3
routes checked: 16/16
e2e:pc01 OK
```

**Run 2 — a copy of the decisions state (`audit_w46k_j2`: two projects, two runs, three
decisions, one `KM` document), exit 0.** Every line `ok`, `write steps checked: 3/3`,
`routes checked: 16/16`, `e2e:pc01 OK`; the same `api=` count on every route as run 1.

**Zero undeclared calls on every route, `blocks` included — read from the raw exchanges, not
the summary.** `journey.mjs:364` builds `observedApi` as `[...new Set(observed)]`, so the
summary's `api=1` cannot tell one request from two. Counting every `/bff/` exchange in
`journey.json` for run 1: `dashboard` → exactly one, `GET /bff/v1/dashboard 200`; `blocks` →
exactly one, `GET /bff/v1/projects 200`; every route's `undeclaredApi` is `[]` and `failures`
is `[]`.

**`optional_api`: `W46-WIRE` did not use it.** `grep -c optional_api tests/e2e/pc01/journey/manifest.json`
→ `1` (the `review` row, older than this wave), and `git diff 2ffca8c d5c9be5 --
tests/e2e/pc01/journey/manifest.json | grep optional_api` → nothing. Both rewritten rows use
`expects_api`, and both calls are unconditional on this tree: the dashboard read in every state
of section 1, and `blocks`' `listProjects` with no project at all — a cold `/blocks` on s0 makes exactly
`GET /bff/v1/projects?limit=50 200` and renders *«Проектов пока нет.»*, so `expects_api` is the
right key for it.

**The instrument can still fail on these two rows.** A scratch copy of the manifest with
`dashboard.expects_api = []` and `blocks.expects_api = []` (the pre-wave `blocks` row), passed
with `--manifest`, `--phase read`, against run 2's copy:

```
RED blocks         200  api=1 auth=0 console=0 jar=[am_session] w=780/780
RED dashboard      200  api=1 auth=0 console=0 jar=[am_session] w=765/780
e2e:pc01 FAILED -- 2 finding(s):
  - blocks: made 1 API call(s) no route in the manifest declares: GET /bff/v1/projects
  - dashboard: made 1 API call(s) no route in the manifest declares: GET /bff/v1/dashboard
```

exit 1. The committed manifest was not touched (`git status --porcelain` empty after).

## 4. Y4 — widths and palettes — **no overflow, no clipping, no text under 4.5:1, on the brief's data**

The decisions state (`audit_w46k_s4`: two projects, two published runs, six findings, three
decisions, one `KM` and one unclassified document), every width in both palettes, each in its own
cold browser with the palette written to `am-theme` the way the toggle stores it. Beyond
`width.mjs`'s `MEASUREMENT`, the probe counted every element inside the dashboard whose content
is wider than its box under `overflow-x: hidden|clip|auto|scroll` (*clipped*), and computed the
WCAG contrast ratio of every element that owns a text node against its nearest opaque background
(62 text elements) — the pixel-level check judge A could not take.

| palette | viewport | `data-theme`, body background | `scrollWidth`/`clientWidth`/`innerWidth` | past the edge | clipped | grid | text < 4.5:1 | lowest ratio | errors | `/dashboard` calls |
|---|---|---|---|---|---|---|---|---|---|---|
| light | **780** | `light`, `rgb(245, 246, 248)` | 765 / 765 / 780 | 0 | 0 | 1 × 667 px | 0 | 5.45 | 0 / 0 | 1 |
| light | **781** | same | 766 / 766 / 781 | 0 | 0 | 2 × 322 px | 0 | 5.45 | 0 / 0 | 1 |
| light | **360** | same | 345 / 345 / 360 | 0 | 0 | 1 × 247 px | 0 | 5.45 | 0 / 0 | 1 |
| light | **1024** | same | 1009 / 1009 / 1024 | 0 | 0 | 2 × 443.5 px | 0 | 5.45 | 0 / 0 | 1 |
| dark | **780** | `dark`, `rgb(13, 18, 25)` | 765 / 765 / 780 | 0 | 0 | 1 × 667 px | 0 | 5.05 | 0 / 0 | 1 |
| dark | **781** | same | 766 / 766 / 781 | 0 | 0 | 2 × 322 px | 0 | 5.05 | 0 / 0 | 1 |
| dark | **360** | same | 345 / 345 / 360 | 0 | 0 | 1 × 247 px | 0 | 5.05 | 0 / 0 | 1 |
| dark | **1024** | same | 1009 / 1009 / 1024 | 0 | 0 | 2 × 443.5 px | 0 | 5.05 | 0 / 0 | 1 |

The lowest ratio in both palettes is the verdict panel's caption (`am-state__correlation`). The
breakpoint sits exactly where it should: one column at 780, two at 781. Screenshots at 781 light
and 360 dark were read by eye: every panel whole, the sections list wrapping inside its panel, the
navigation wrapping onto extra lines at 360 without pushing anything past the edge. The earlier
780 readings in s0–s3 (section 1) agree: 765 / 765 / 780, 0 offenders, in every state.

**One thing the brief's data does not contain, measured because the contract allows it.**
`ProjectDocumentCount.name` is `maxLength: 200` with no word-break requirement. One project named
`Проект` + 194 × `Ж` (201 from `POST /projects`), then the same probe:

```
/dashboard  360 light   scrollWidth 3691  innerWidth 360   1 element past the edge: <a> right=3691
/dashboard 1024 dark    scrollWidth 3691  innerWidth 1024  same <a>
/projects   360 light   scrollWidth 3691  innerWidth 360   same shape: the project row's <a>
```

**Pre-existing and product-wide, not this wave's**: `/projects` overflows identically, and the
pre-wave documents panel rendered the same `ProjectRow` (`git show
2ffca8c:web/src/widgets/dashboard/ui/documents-panel.tsx`, line 79). The journey never sees it
because its write half names projects with short names. Recorded in section 7.

## 5. Y5 — `F-5b` mutated — **the stream's three hold; two of mine survive everything; and the screen invents the zeros the server stopped sending**

**The instrument.** A disposable clone at `d5c9be5` (`git clone /root/w46k /root/w46k-probe`,
`git checkout d5c9be5`, `web/node_modules` symlinked to this worktree's), baselined unmutated:
`npx vitest run tests/unit/widgets/dashboard.test.ts` → **7 passed**; the whole frontend suite →
**79 files, 1118 passed**. `W46-JUDGE-X`'s gate had finished (`/root/w46x-gate.status` →
`exit=0`) and no `make gate` under `/root/w46*` was running. Each mutation was applied by an
exact-string replacement, measured, and reverted with `git checkout -- web/src`; `git status
--porcelain` showed only the untracked symlink after each.

| # | mutation | render test (7) | caught by |
|---|---|---|---|
| M1 | `W46-WIRE` #1: `' (42)'` appended to the verdict total | **2 failed** | *nothing invented* (`rendered numbers not in the fixture: 42`) and *never renders absent spend…* (its own invented-number half) |
| M2 | `W46-WIRE` #2: the unclassified `<li>` deleted | **1 failed** | *always shows the unclassified section row* |
| M3 | `W46-WIRE` #3: the absent-spend branch replaced by `spend?.cost_micros ?? 0` / `spend?.cost_basis ?? 'measured'` | **1 failed** | *never renders absent spend…*: the screen read *«Расход по всем прогонам: 0.000000 · вызовов модели: 0 · измерено»* |
| M4 | **mine — the right field of the wrong panel**: `dashboard.tsx` `<SectionsPanel rows={data.documents_by_project} />`. It **typechecks** (`npx tsc --noEmit` exit 0: `ProjectDocumentCount` is structurally a `SectionDocumentCount` with no `section`) | **1 failed** | only `'Без раздела: 11'` (`dashboard.test.ts:201`). The screen showed *КМ: 0* where the fixture says 4, and *Без раздела: 8* (the documents-per-project total) |
| M5 | **mine — the right field of the wrong row**: `sections-panel.tsx` renders `summary.byCode[PROJECT_SECTIONS[(i + 1) % PROJECT_SECTIONS.length]!.code]`, so every section shows its neighbour's count (the fixture's `KM 4` lands on АИ, `PB 2` on ПТ) | **7 passed** | **nothing**: whole suite **79 / 1118 passed**, `tsc` exit 0 |
| M6 | **mine — two rows swapped inside a panel**: `verdicts-panel.tsx` renders `accepted`'s cell from `rejected` and back (*принято 1 · отклонено 2* over a fixture of 2 and 1) | **7 passed** | **nothing**: whole suite **79 / 1118 passed**, `tsc` exit 0 |

**`W46-WIRE`'s three are real**: each is red under its own mutation, and M1 is red twice. The
stream quoted all three in its commit (`27e2c55`) and in the test file's header, which is what
`AGENTS.md` §5 asks for.

**Why M4–M6 get through.** The *nothing invented* case is a **set-membership** test: every digit
on screen must be *some* number in the fixture. A number moved from one row or panel to another is
still in the set. The per-row values of three panels are asserted by nothing: the verdict rows
(4, 2, 1, 0), the run-state rows (6, 1) and the fourteen section rows. The one per-section
assertion, `dashboard.test.ts:207-208`, is `toContain('data-section="KM"')` plus
`toContain('4')` **anywhere in the page** — satisfied by the verdict panel's *не решено 4* even
when the КМ row reads 0 (M4, measured above). **The guard proves that no number is invented; it
does not prove that any number is in its place.** Cost: one assertion per row, keyed by
`data-verdict`/`data-run-state`/`data-section`, which the markup already carries.

### Y5-a — the screen cannot tell "the server said zero" from "the server said nothing" (medium)

Both client-side merges fill a row the response omits with `0`:
`section-breakdown.ts:37-40` seeds all fourteen codes at `0` and `unclassifiedCount = 0`;
`verdict-breakdown.ts:15-24` seeds all four verdicts at `0`; `run-activity-panel.tsx:76,79` read
`byState.get(state) ?? 0` and `:51` sums whatever rows arrived. Their headers call the result *"its true zero"*
(`section-breakdown.ts:10`, `verdict-breakdown.ts:8`) and say the merge is *"the same way the
backend's own repository does"*. **It is not the same fact.** The repository fills zeros over a
`GROUP BY` — a group with no rows *is* a computed zero. The client fills zeros over a response
whose schema says every member **is present** (`VerdictCount`, `RunStateCount`,
`SectionDocumentCount`); an omitted member there is the server not saying, and rendering it as `0`
is the silent fallback `AGENTS.md` §4 forbids and the invented zero `R-23`'s addendum names.

**Driven end to end.** Judge A's `F-5a` mutation (`_filled` drops members with no rows; the
unclassified bucket appended only when non-zero) applied to `dashboard/repository.py` in the clone,
the API served **from the clone** on `56401` (cwd `/root/w46k-probe`, `PYTHONPATH` the clone's
`src`), my unchanged Next in front of it:

```text
copy s0, mutated API:  {"documents_by_project": [], "findings_by_verdict": [],
                        "run_activity": {"by_state": []}, "section_breakdown": []}
screen:                Находок: 0 · не решено 0 · принято 0 · отклонено 0 · нужен ручной разбор 0
                       … fourteen sections at 0 … Без раздела: 0
panel text identical to the unmutated API's s0 screen: True

copy s2, mutated API:  findings_by_verdict [], by_state [],
                       section_breakdown [{"section":"KM","document_count":1},{"document_count":1}]
panel text identical to the unmutated API's s2 screen: True
```

**Nineteen zeros on the s0 screen that the server did not send**, including *Без раздела: 0*, the
row `W46-WIRE`'s own brief made non-negotiable. And on s2 with `by_state: []`, the run panel would
say *«Прогонов пока нет.»* — a claim about runs from a response that said nothing about them.

**Why it matters today, and why it is not an emergency.** The server is honest *now* and
`W46-SPEND`'s `F-5a` guard keeps it so — I credit that: the one mutation above is exactly what
`test_dashboard_summary_over_a_fresh_deployment.py` turns red. But **the client makes that
property invisible from the browser**, so a server regression past that guard (a new member added
to the enum on one side, a code path that returns early) would ship as a correct-looking screen,
and no browser-level instrument — render test, language guard, live journey — could see it. The
render test's fixtures always send every row, so none of them exercises the branch. **Cost:** the
two merges should report an omitted member as the server's fault (an error state, as
`dashboard-failure.ts` already does for an unparseable answer) instead of a zero, plus one render
case with an omitted row.

**Reverted**: the clone's `git checkout -- src`, the lane API restarted from `/root/w46k`; `git
status --porcelain` in the clone → only the symlink.

## 6. Y6 — the stream reports, re-measured

*pending*

## 7. Off the trail

*pending*

## Findings, most severe first

*pending*

## What I could not answer, and why

*pending*

## Evidence discipline

*pending*
