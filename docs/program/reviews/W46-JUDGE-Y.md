# W46-JUDGE-Y — the product, the journey and the stream reports, on `d5c9be5`

**Judge:** `W46-JUDGE-Y` · **lane:** `gate-w46k` (PostgreSQL `127.0.0.1:56400`, S3
`60000`/`60001`, API `56401`, Next `56403`) · **worktree:** `/root/w46k` · **branch:**
`agent/w46-judge-y` · **tree judged:** `d5c9be5` (wave 46's merged tip: `9a295aa` W46-SPEND,
`1c38c52` W46-WIRE, `d5c9be5` the integrator's join repair).

Brief: `docs/program/dispatch/W46-JUDGES-XY.md`, section `W46-JUDGE-Y`. This judge repairs
nothing and owns this file only. Opened before the first measurement and committed after each
section. Every section is now final.

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
- ***контракт* and *операция* are gone from every state of the dashboard that has data — not from
  its failure state.** The rendered `main` text in s0–s3 contains neither (case-folded substring
  test on `контракт` and `операци`), and `grep -rni 'контракт\|операци' web/src/widgets/dashboard
  web/src/_pages/dashboard web/src/app/dashboard` → nothing. But the failure state takes its detail
  from the shared catalog. With my API stopped after sign-in, a cold `/dashboard` rendered
  (`data-list-failure="dependency_unavailable"`, three `GET /bff/v1/dashboard 503` — the query's
  retries): *«Зависимость, нужная сводке, недоступна. Требуемый адаптер — хранилище метаданных,
  хранилище объектов, провайдер модели или транспорт исполнителя — временно недоступен. …
  **Операция** ничего не создала, и её можно повторить.»* (`web/src/shared/api/catalog-message.ts:113`).
  The 403 detail it would show is `authorization.ts:49` (*«…эта операция над этим ресурсом им не
  разрешена»*), and the transport-failure detail is `transport.ts:185/192` (*«…по контракту»*).
  *Адаптер* and *транспорт исполнителя* are `R-39`'s author vocabulary too. Low, and the shared
  catalog is outside `W46-WIRE`'s dashboard files; but the brief asked about the dashboard, and the
  dashboard renders these words. `D-109` is the owner's line.
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

Every figure below was taken again, not read. Backend figures ran in the disposable clone
(`/root/w46k-probe`, `.venv` symlinked to this worktree's, the lane's `.env` exported, so the
fresh-deployment fixture created and dropped its own database in `gate-w46k-postgres-1`).

### `docs/program/W46-SPEND.md`

| claim | where | re-measured | verdict |
|---|---|---|---|
| over no `model_call` rows `spend` is absent; one call makes it present with all three fields | §2 | live, section 1: s0–s2 have no `spend` key; s3 `{1, 34400, "estimated"}` | **true** |
| `069f656` is the reseal in one commit: contract, mirror, four generated files, lock | §2 | `git show --stat 069f656` → exactly those seven files | **true** |
| only `types.gen.ts` changed in substance; the other three carry the new digest comment only | §2 | `git show 069f656 -- <file>`: `client.gen.ts`, `index.ts`, `operations.gen.ts` each change one line, the `sha256` comment; `types.gen.ts` changes that line, `CONTRACT_DIGEST`, and `spend: RunActivitySpend` → `spend?: RunActivitySpend` | **true** |
| the mirror is byte-identical to the contract | §2 | `cmp contracts/api/v1/openapi.json web/openapi/openapi.json` → identical | **true** |
| the lock's digests are recomputed | §2 | all **8** 64-hex values in `web/FRONTEND_LOCK.json` recomputed with `hashlib.sha256` → 8 match; 17 / 20 / 61; `api:verify` → *OK - 20 operations, contract sha256 f688b409…*. *"all six digests"* means the six that moved; the other two (lockfile, generator) are legitimately carried | **true** |
| the pin table's values | §2 | each cited line read at `848f260`: all values as stated | **true**, one line stale: the 22-code pin is `test_openapi_document.py:497` at `dbbf952`, when the table was written, and **`:577`** from the stream's own S2 (`a6e3015`) onward. Very low |
| `test_openapi_document.py` → 46 passed; `test_doc_prose_facts.py` → 21 passed | §3, §5 | at `bb985ce`: **46 passed**, **21 passed** | **true** |
| the fresh-deployment file → 3 passed | §4 | at `bb985ce`, lane `.env` loaded: **3 passed** | **true** |
| the canonical-ignore contract scope → 367 passed | §3, §5 | at `bb985ce`: **367 passed, 49 subtests passed** | **true** |
| `+5` passing nodes are *"three new tests in S3, the one net-new test in S2"* | §6 | the figures are consistent (2500 nodes − 1 replaced + 2 + 3 = 2504), but the sentence's own sum is 3 + 1 = **4**: the five new *passing* nodes are S3's three plus **both** of S2's replacements | **the arithmetic in the prose is off by one; the numbers are right.** Very low |

**Where `W46-SPEND` did the right thing, checked:** it reported against itself twice — the OOM-killed
baseline discarded rather than read (§1), and the brief's `TAGGED_TIP_CLAIM` measured to match
nothing in today's live section, with the union of three extractors used instead and the sentence
the integrator needs named (§5). Both are the behaviour the programme's constraints ask for.

### `docs/program/W46-WIRE.md`

| claim | where | re-measured | verdict |
|---|---|---|---|
| `dashboard: api=1` and `blocks: api=1`, zero undeclared calls, `e2e:pc01 OK` | W4 | section 3: two live runs of my own, both `OK`, raw exchanges one each | **true** |
| the `_rsc` requests are Next's link prefetches, not a second data fetch | W4 | section 1: they reach the API zero times (uvicorn log) | **true** — and stronger than the stream could say, since it read only the browser side |
| `/dashboard` makes zero requests to `/bff/v1/projects`; `/projects` makes exactly one | W5 | section 1 (dashboard, four states) and run 1's raw exchanges (`projects` → one) | **true** |
| the double `GET /projects` judge A saw *"was the old three-walk architecture's own redundancy"* — `documents-panel`'s `useProjectList` and the walk's own `useProjectList` | W5 | **not re-measured** (*What I could not answer*). At `2ffca8c` both call `useProjectList()` with no cursor, i.e. the same key `queryKeys.projects.list(undefined, 50)` (`git show 2ffca8c:web/src/widgets/dashboard/api/use-run-activity-walk.ts` line 59, `…/entities/project/api/use-project-list.ts` line 20), and one `QueryClient` deduplicates a key's concurrent fetch. So the stated cause does not by itself produce two requests | **unproven**: the effect (zero now) is measured; the cause is asserted |
| the `it(` table: five files touched, only `dashboard.test.ts` moved (10 → 7) | Frontend baseline | `grep -c '^\s*it('` at `fbea618` and `c26340f`: the five counts are exactly as stated; but `git diff --name-only fbea618 c26340f -- web/tests` lists **four** files — `tests/contract/narrow-sets.contract.test.ts` was not touched | counts **true**; *"touched five test files"* **false by one**. Very low |
| `fbea618`'s frontend is **1121 passed, 79 files** (reconstructed, not measured) | Frontend baseline | `npx vitest run` at `fbea618`: **79 files, 1121 passed** | **true** — the reconstruction is now a measurement |
| after W1–W3: **1118 passed, 79 files** | Frontend baseline | at `d5c9be5`: **79 files, 1118 passed** | **true** |
| `test_pc01_journey_conformance.py` → 78 passed | commit `4cb8c88` | at `4cb8c88` and at `d5c9be5`: **78 passed** | **true** |
| the rewritten project-sections pin can still go red | commit `293c368` | the old sentence restored in the clone → `project-sections.test.ts` **1 failed / 12 passed**, the rewritten case | **true** |
| the render guard is red under three mutations | commit `27e2c55`, test header | section 5, M1–M3 | **true** |
| *"invalidate the dashboard summary at every mutation that changes it"* | commit `d4f7b0e`; in the tree as `web/src/shared/api/query-keys.ts:165` (*"Every mutation that changes a number this key answers for invalidates it"*) | **false** — see Y6-a | **false** |

**Y6-a — creating a project does not invalidate the dashboard (medium-low).**
`features/create-project/model/use-create-project.ts:31-34` invalidates `queryKeys.projects.all()`
only. A new project changes `documents_by_project` (a row, *на N проектах*) and, for the first
project, flips `hasProjects`, which decides both empty states. With the app's `staleTime: 30_000`
(`_app/query-client.ts:35`), one browser page, all navigation client-side, on a fresh copy of s0:

```text
1 cold /dashboard     documents: Проектов пока нет. | runs: Проектов пока нет.
2 click the brand link -> /projects (client-side)
3 fill #new-project-name, click «Создать»  -> data-created-project = prj_01M3M1Y4V4Q99K2QGMPZ01G3K0
4 click a[href="/dashboard"] (client-side, ~2 s after step 1)
                      documents: Проектов пока нет. | runs: Проектов пока нет.
  /bff calls in the whole page session: GET /dashboard 200, GET /projects 200,
                                        POST /projects 201, GET /projects 200
5 reload /dashboard   documents: Документов: 0 на 1 проекте. | Judge Y staleness probe | документов 0
```

The screen says *no projects* seconds after the product created one, and makes no request to find
out; a reload shows the truth. This is **a regression of the wiring**: before it, the documents
panel read `useProjectList`, whose key sits under the `projects.all()` prefix that same mutation
invalidates. (Stated from the code at `2ffca8c`, not driven there — *What I could not answer*.) It is also exactly
the first-day path: an empty deployment, a first project, back to the dashboard. The sentence at
`query-keys.ts:165` names four mutations and asserts that the list is complete; the rest of the
comment ends *"Forgetting one is how this screen shows last month's numbers after this month's
upload."* **Cost:** one line in `use-create-project.ts`, and a test that lists every mutation hook
against the numbers each changes. **Reproduce:** the five steps above (scratch `stale.mjs`, which
uses only `cdp.mjs`'s `goto`/`click`/`fill`/`waitFor` and the manifest's own selectors).

**Y6-b — the stream report records no gate of its own (low).** The brief's *Verification* asks for
`make gate > /root/w46b-gate.log` and the verdict from its `GATE OK` line; the report's plan (item 6)
promises it. The report ends at W5 and says nothing about a gate on its own tree. The only record is
the integrator's merge commit `1c38c52`: *"Stream gate on c26340f: 2 failed / 2498 passed"*, one of
the two reds on the stream's own comment. And `/root/w46b-gate.log` now holds a different run —
foundation 35 passed, then the battery to 41% and `make: *** [Makefile:1026: gate] Terminated`,
mtime 16:56:46 (+0500), **after** the merge commit (16:54:16). So the one red gate this stream
produced is on record only in a commit message, and the file the brief names cannot confirm it.
(Read-only, `tail` and `stat` of a log outside my worktree.) **Where the stream did the right
thing:** it wrote two findings against itself — the machine-wide `pkill` and the OOM-killed
baseline discarded — and corrected an unmeasured baseline claim before it left the log; the
correction was then confirmed above by measurement.

## 7. Off the trail

The trail I was handed: four states of `/dashboard`, the captions, the live journey, four widths,
`F-5b`'s three mutations plus one, and the two stream reports. Where I went that none of it points,
and what came back — including the places that returned nothing:

| where | why the trail does not lead there | returned |
|---|---|---|
| **`POST /runs` on a document the server stores as `KM`** | the brief's premise is that the intake rule is unchanged; the trail asks whether the sentences are true, not whether the server does what they describe | **Y2-a**: accepted, analysed with the same profile, published with three findings, while two screens say that section is not analysed |
| **`createProject`, the one mutation the stream did not list** | every trail state is a *cold* load, which cannot see a cache; the stream enumerated four invalidations and the trail checks those | **Y6-a**: the dashboard says *«Проектов пока нет.»* seconds after the product created one, and asks nobody |
| **the seam between server and screen**: judge A's `F-5a` server mutation served to the unchanged client | `F-5a` is guarded on the server, `F-5b` by fixtures that always send every row; nothing looks at the join between them | **Y5-a**: nineteen zeros on screen that the server did not send; panel text identical to the honest server's |
| **the dashboard with its API stopped** | every trail state has a working API | the failure state is honest about *what* (`dependency_unavailable`, a retry button, a correlation id, the BFF answering `503` rather than crashing — correct), makes three requests (the query's retries), and says *операция* (Y2 addendum) |
| **a project name at the contract's limit** (200 characters, one word) | the journey names its projects with short strings; the brief's widths use ordinary data | a 3691 px sideways scroll on `/dashboard` at 360 and 1024 px, in both palettes; **pre-existing and product-wide** — `/projects` does the same, and the pre-wave panel rendered the same row. Not this wave's |
| **63 projects** | the brief's states hold at most two | `documents_by_project` has no bound: 63 rows, a 6906 px page at 1024 px. The panel it replaced showed the first page of 50 and said so (*«Показана первая страница проектов…»*, `git show 2ffca8c:web/src/widgets/dashboard/ui/documents-panel.tsx`). A consequence of `R-44`'s unpaginated read, not a false number; eight RSC prefetches (viewport-limited), zero extra API calls. Low, recorded for scale |
| **contrast, computed** | judge A could not take it, and no brief item asks | nothing wrong: 62 text elements per reading, none under 4.5:1, lowest 5.45 (light) and 5.05 (dark), both the verdict caption. **Said so, because a place that returned nothing is still a place** |
| **five malformed sections on upload**, beyond judge A's three | the trail reads sections; it does not write them | nothing wrong: `km` and `" KM"` are refused like `""`, `ar`, `ZZ`, and nothing is written |

## Findings, most severe first

| # | finding | reproduce | cost |
|---|---|---|---|
| **Y5-a** (medium) | **The screen cannot tell "the server said zero" from "the server said nothing."** `section-breakdown.ts:37-40`, `verdict-breakdown.ts:15-24` and `run-activity-panel.tsx:76,79` fill any row the response omits with `0` and call it *"its true zero"*. With judge A's `F-5a` mutation on the server, the API sends `section_breakdown: []`, `findings_by_verdict: []`, `by_state: []`, and the screen renders nineteen zeros, *Без раздела: 0* included — panel text identical to the honest server's. The server is guarded (`W46-SPEND`'s `F-5a` test); the browser can no longer see the property that guard protects | section 5: mutated `dashboard/repository.py` in a clone, API served from it, `/dashboard` from my Next, compare to the unmutated s0/s2 readings | an error state for an omitted member (the shape `dashboard-failure.ts` already has) and one render case with an omitted row |
| **Y2-a** (medium) | **"The only analysed section" is false for a document stored as `KM`.** The server accepts `section=KM` and analyses it with the same profile (published, three findings); the dashboard says *«АР — единственный анализируемый раздел: 0»* beside *КМ: 1*, and the project screen's КМ tab says *«Анализ этого раздела ещё не делается»*. The source (`section.ts:28-31`) says the restriction lives in the prompt; the screens call it *правило приёма*. Wave 46 created it; reachable through the API only | section 2: upload `section=KM`, `POST /runs`, render `/dashboard` and the КМ tab | two sentences, or an intake decision for the owner beside `D-107` |
| **Y6-a** (medium-low) | **Creating a project leaves the dashboard stale.** `use-create-project.ts:31-34` does not invalidate `queryKeys.dashboard.summary()`; with `staleTime: 30_000`, a client-side return to `/dashboard` after creating the first project still says *«Проектов пока нет.»* and makes no request. The sentence at `query-keys.ts:165` (*"Every mutation that changes a number this key answers for invalidates it"*) is false. A regression of the wiring: the old panel's key sat under the invalidated `projects.all()` prefix | section 6, Y6-a: five steps in one page | one line, plus a test mapping mutations to the numbers they move |
| **Y5 M5/M6** (medium-low) | **The render guard proves no number is invented, not that any number is in its place.** It is set membership over the fixture; per-row values of the verdict, run-state and section panels are asserted by nothing, and the one per-section check (`dashboard.test.ts:207-208`) is `toContain('4')` anywhere on the page. Every section showing its neighbour's count, and *принято*/*отклонено* swapped, both pass the **whole** frontend suite (79 / 1118) and `tsc` | section 5, M5 and M6 in a clone | one keyed assertion per row; the markup already carries the keys |
| **Y6-b** (low) | `W46-WIRE.md` records no gate of its own, though its plan and its brief ask for one. The only record of its red gate (*2 failed / 2498 passed*) is the merge commit; `/root/w46b-gate.log` now holds a later, terminated run | section 6 | a paragraph |
| **Y2-b** (low) | The verdict caption explains «ожидает решения», a label that appears nowhere; the row it qualifies reads «не решено» | `grep -rn 'ожидает решения' web/src` → one hit | one word |
| **Y2 addendum** (low) | The dashboard's failure state still says *операция*, *адаптер*, *транспорт исполнителя* (shared catalog, `catalog-message.ts:113`); the subtitle's *одного общего чтения* is transport vocabulary. `D-109`, the owner's line | section 2 | owner's call |
| low | The run panel hides the seven computed zeros the API sends (carried from `2ffca8c`) · `documents_by_project` is unbounded: 63 rows, 6906 px, where the old panel showed 50 and said so · a 200-character project name overflows `/dashboard` and `/projects` (**pre-existing, product-wide**) · `W46-SPEND` §6's prose sums 3 + 1 to explain +5 (numbers right) · its 22-code pin line is `:577` now, not `:497` · `W46-WIRE` says five test files touched, git says four · `W46-WIRE`'s cause for judge A's double `/projects` is asserted, not measured | sections 1, 6, 7 | — |

**Confirmed, and said plainly.** `F-1` is repaired on the wire and on the screen. Every number
on `/dashboard` equals `GET /dashboard` in four states plus a decisions state. The dashboard makes
one request, seen from both ends. The live journey is `OK` twice with zero undeclared calls and can
still go red. No overflow, clipping or sub-4.5:1 text at 780/781/360/1024 in either palette. The
rewritten section sentences are true as written. Every numeric claim in `W46-SPEND.md` I re-ran
held, and `W46-WIRE`'s reconstructed `1121` is now a measurement.

## What I could not answer, and why

- **Why judge A saw `GET /projects` twice at `2ffca8c`**, and so whether `W46-WIRE`'s explanation is
  right. It needs a second `next build` at `2ffca8c`. My attempt in the clone hit `timeout 600`
  (exit 124) with the host at load average ~300 and swap at 14.6 / 16 GB, while `dmesg` recorded
  three OOM kills of processes that were not mine (none of my browsers was running during the
  build). I stopped rather than try again, and **I cannot exclude that my build added to that
  pressure**. For the same reason, Y6-a's *"regression"* is argued from the code at `2ffca8c`, not
  driven there.
- **Whether `W46-WIRE` ran `make gate` on `c26340f` with the result the merge commit gives.** The
  log that would show it has been overwritten by a later run that was terminated.
- **Three branches no state I could build reaches:** a `needs_manual_review` finding (no PC-01
  producer), a run in a non-terminal state (recorded runs published in 1.5 s), and the spend
  sentence *«Ни один прогон ещё не обращался к провайдеру…»* with runs present (the recorded
  provider always makes a call). The render test covers the last one; nothing live does.
- **Live provider mode** was not used: it spends money against the ceiling.
- **The owner's stand at `127.0.0.1:31500`** was not touched, read-only or otherwise. Nothing here
  speaks about what is deployed.

## Evidence discipline

Branch `agent/w46-judge-y`, based on `d5c9be5`; `git diff --name-only d5c9be5..HEAD` lists this
file only (checked before the final commit). Every mutation ran in the disposable clone
`/root/w46k-probe`, was measured after an unmutated baseline, and was reverted; the clone was
removed at the end. Nothing was repaired. `make up` created the `gate-w46k-*` containers, which did
not exist before; no other container was touched and nothing host-wide was pruned. The API and Next
were stopped by PID after each was checked to be mine (`readlink /proc/<pid>/cwd` = `/root/w46k` or
`/root/w46k/web`); nothing was killed by name or pattern. The judge databases (`audit_w46k_judge`,
`_s0`–`_s4`, `_j1`, `_j2`, `_st`) are left in `gate-w46k-postgres-1` so the cross-examination can
serve any state again unchanged; the gate's own `audit_w46k` was migrated to head by `make migrate` during provisioning and
named as the fresh-deployment fixture's `DATABASE_URL`, whose test creates, uses and drops its own
database. The scratch drivers live in my
session scratch directory, which does not survive a restart; everything load-bearing is quoted here.

## Cross-examination of `W46-JUDGE-X` (`agent/w46-judge-x` at `2a7b00b`)

Read from git (`git show agent/w46-judge-x:docs/program/reviews/W46-JUDGE-X.md`), never from
`/root/w46j`. Every finding is judged as X stated it against `d5c9be5`. The integrator's `ce25e14`
(on `audit-auth`, after both reports) repairs X-5, X-8 and X-10; where I say whether it does, that
is a separate reading of `git show ce25e14`. The host restarted between my report and this
section: my scratch directory is gone and the lane's containers had exited, so every instrument
below was rebuilt and every figure below was taken after the restart.

*Findings are filled in as measured; a heading without a verdict has not been judged yet.*

### X-8 — three false sentences in `8ad692f` — **upheld, all three; `ce25e14` repairs all three**

X counted three commits and read `8ad692f^`. I took each sentence's whole history instead.

- **`route.ts:22-23`** (*"twenty operations across seventeen paths … after the `W45-BLOCKS`
  reseal"*). Paths / operations / schemas at **every** commit that touched the contract, back to
  `5bb5691`: `830fd76` (`W45-BLOCKS`) **16 / 19 / 53**, and the first commit with 17 / 20 is
  `d7ac848` (`W46-SEAL`), which is also the only commit where `git log -S'getDashboardSummary'
  -- contracts/api/v1/openapi.json` finds the operation arriving. **Upheld.** The history clause
  (*"fifteen and twelve once and sixteen and thirteen after that"*) matches `6398bcc` (12 / 15) and
  `5178379` (13 / 16) and skips 14 / 17, 15 / 18 and 16 / 19; `ce25e14` names the reseal
  correctly and adds *"nineteen and sixteen after `W45-BLOCKS`"*, which is `830fd76`'s count.
  **Repaired.**
- **`P02_SEAMS.md:601`** (*"… `W46-SEAL` added `getDashboardSummary` … on 2026-09-28"*). `git log
  -S'getDashboardSummary' --format='%ad %cd'` on the contract: author **and** committer date
  `2026-09-25 18:43`, one commit, `d7ac848`, so no rebase or cherry-pick moved it to the 28th.
  **Upheld.** `ce25e14` writes 2026-09-25. **Repaired.**
- **`ALPHA_ROADMAP.md:34-37`** (*"Corrected a fourth time … wrong three times in three days"*).
  The block through every commit that changed it: `aaf91ad` 09-22 (first correction, 13 / 16 / 48),
  `9cfb81b` 09-23 *"Corrected again … wrong twice in two days"*, `c42ab6e` 09-25 *"Corrected a
  third time … three times in three days"*, `8ad692f` 09-28 *"Corrected a fourth time … three
  times in three days"*. **Upheld**, and one step further than X: the tally was already
  generous at `c42ab6e` (09-22 → 09-25 is four calendar days). `ce25e14` says *"four times in
  seven days"*: 09-22 → 09-28 inclusive is seven. **Repaired, and now true.**

X's two extras hold as well: `ce25e14` renames the block to *"the twenty seam operations"* and
rewrites the README's no-token sentence as *"every operation but `issueToken` -- nineteen of
the twenty"*, which is what X's in-process probe measured.

### X-5 — `D-107`'s check cannot print anything but `0` — **narrowed**

X's two constructions are real misses. I ran the old command in a `git archive` copy of the two
directories against X's two and three of mine, restoring each file and `cmp`-ing it against
`git show d5c9be5:<path>` afterwards:

| construction | old command (`d5c9be5`) | `ce25e14`'s command |
|---|---|---|
| unmutated | 0 | 0 |
| X (1): `section: 'KM'` in the upload hook's body (`.ts`) | **0** | 1 |
| X (2): `<select className="am-input" name="section">` on one line | **0** | 1 |
| the same `<select>` written the way `upload-document-form.tsx` writes every control — one attribute per line | **1** | 1 |
| a `section` state variable in the form component | **1** | 1 |
| a picker component whose name and props avoid the word | 0 | 0 |

So the old check was blind to the hook and to a one-line control, but **not** to the same control
in the form file's own style (`<input` then `id=`, `name=` on lines of their own — lines 86-91), and
not to a `section` identifier in the `.tsx`. *"Cannot print anything but `0` for the two direct
ways"* is true of the two constructions X chose; the house style the form is actually written in
would have been caught. The finding stands as *a weak check*, not as *a check that cannot fail*.
`ce25e14`'s command catches every construction above except the last, and that one would still
have to put `section` into the hook's body, which the new command reads. **Repaired.**

### X-11 — the contract says nothing about an absent `spend` — **upheld**

X read the contract with `jq`. I read what a client author reads, the generated type:
`types.gen.ts:520-524` gives `RunStatus.cost_micros` a doc comment ending *"Absent when the run
made no provider call at all, which is a different fact from a cost of zero."*;
`types.gen.ts:482-484` gives `RunActivity.spend?: RunActivitySpend` **no comment at all**. The
behaviour mirrors `RunStatus`; the client does not say so. And the lock's note, split on
`Resealed`: nine segments; of the eight below `W46-SPEND`'s, three give the *"a commit cannot name
itself"* reason (`W46-SEAL`, `W45-BLOCKS`, `W42-SEAL`) and five do not (`W18-SEAL`, `W25-SEAL`,
`W34-CONTRACT`, `W38-KB`, `W39-REVOKE`). **Upheld as X states it.**

### X-1 — nothing in the gate compares the served document with the frozen one — **upheld, and strengthened: a drift that refuses valid input passes too**

X's drift (`RunActivity.spend` made required in the model only) changes nothing on the wire,
because the dashboard's serializer omits the key whatever the model says. So X showed that a
**document-only** drift passes the battery. I asked whether a drift that **changes behaviour**
does, and measured the document the production entry actually serves rather than the
documentation app.

- **The served document, over HTTP.** `infra/deploy/serve.py` serves `/openapi.json` behind the
  bearer (`R-31`; unauthenticated → `401`). Fetched from my API and compared with the programme's
  own engine (`surface`/`differences` from `tests/contract/api_v1/openapi_conformance.py`):
  **0 differences** at `d5c9be5`. So X's in-process proxy, `create_documentation_app().openapi()`,
  agrees with what the process serves today.
- **A behavioural drift.** In the clone at `d5c9be5`, `AppendDecisionRequest.comment`
  `max_length=4000` → `400` in `api/schemas/models.py` only. The same HTTP comparison:
  **1 difference**, *"schemas.AppendDecisionRequest.properties.comment.anyOf[0].maxLength: the
  contract has 4000, the generated document has 400"*. Then a real decision on a finding, through
  the served API, with comments of 400 / 401 / 1000 characters: mutated **201 / 422 / 422**
  (*"The comment property of the request body is not of the declared form."*); unmutated, on a
  copy of the same database, **201 / 201 / 201**. The contract and the generated client call a
  1000-character comment valid; the served application refuses it.
- **What notices.** `tests/integration/api tests/integration/composition tests/contract tests/e2e`
  with `run_battery`'s three ignores, lane `.env` loaded, mutation applied: **1119 passed, 6
  skipped, 0 failed, 0 errors** (6 min 43 s). Every suite that touches the API surface is green
  over an application that refuses reviewer comments the contract allows. No baseline is needed
  for that reading: an unmutated run can only fail more, not less.
- **Where X is already right about the exception.** `test_schema_bounds.py:121-128` pins the
  project name's 200 / 201 boundary through the operation, so the same drift on `CreateProjectRequest.name`
  would redden. That file exists because a judge once raised the bound to 100000 with *"all 816
  tests green"* (its own header). One field was repaired by hand; the check that covers every
  field was never written.

I started the whole canonical battery with the comment drift as well and **stopped it myself**
at 58% (PID 1177284, `cwd /root/w46k-probe`, confirmed mine): the host reached load 82 with swap at
13 / 15 GB, and the partial log already showed `F` and `E` marks I could not attribute without a
baseline in the same clone. **That run is not a result** and nothing here reads it as one.

### X-4 — `F-5c`'s control is blinded by a boundary after the first claim — **upheld, and broadened: no code fence is needed**

X blinded the scan with a shell comment inside a fenced block. I tried an ordinary Markdown heading.
Clone at `d5c9be5`, `docs/program/CURRENT_STATE.md`, inserted after the live section's
*"… stays at 22."* line, `test_doc_prose_facts.py` baseline **21 passed**:

| inserted | result |
|---|---|
| *"The migration head is \`0010_run_terminal_detail\`."* (control) | **1 failed** — `test_the_scanned_docs_state_the_migration_head_this_tree_has` |
| `### What the historical record below keeps`, then the same stale sentence | **21 passed** |
| the stale sentence, then that heading | **1 failed** (a claim above the boundary is still read) |
| the heading alone | **21 passed** |

So the code fence in X's reproduction is incidental: **any line starting with `#` that mentions
the historical record, placed after the first claim, blinds everything below it.** Today the
regex's first match is the right one (`CURRENT_STATE.md:48`, *"Previous release state — wave 45
(historical record)"*; three matches in all, none earlier), and `ALPHA_ROADMAP.md` has none and
is not truncated. The risk is the next live section, as X says.

### X-7 — `F-2`'s derivation ignores `in: cookie` — **upheld; the rule reads spellings, not HTTP**

X added one inline cookie. I ran `_takes_caller_input` itself, in-process, against every
parameter location on a copy of the frozen document, with `getDashboardSummary` given one
required parameter each time:

```text
path 'x' -> True   query 'x' -> True   header 'X-Scope' -> True   cookie 'am_scope' -> False
header 'x-correlation-id' -> True      header 'X-Correlation-Id' -> False
a $ref to a component cookie parameter -> False
locations the frozen contract uses: header 25, query 18, path 11 (no cookie)
```

`cookie` is missed inline and through a `$ref` (the rule resolves references correctly, so this is
the location list, not the resolution). And one thing X did not see: the correlation exemption
compares the header's **spelling** (`resolved["name"] != "X-Correlation-Id"`), while HTTP header
names are case-insensitive, so the same header spelled `x-correlation-id` counts as caller input.
That errs toward demanding a client fault, so it is harmless today; it is §12's *"both spellings"*
in miniature. Low, as X rates it.

### X-9 — four comments say the client types `spend` as required "today" — **upheld by the compiler; not repaired by `ce25e14`**

X grepped the comments. I asked the compiler what is true: a probe file declaring
`const noSpend: RunActivity = { by_state: [] }` against each commit's own `types.gen.ts`,
`tsc --strict --exactOptionalPropertyTypes`:

```text
2ffca8c: exit 2 -- probe.ts(2,14): error TS2741: Property 'spend' …  (the missing-property error)
d5c9be5: exit 0
```

The comments were true on the stream's base and are false on the merged tree. `git grep` at
`ce25e14` still finds all four (`run-activity-panel.tsx:8`, `:64`,
`rendered-language.guard.test.ts:644`, `dashboard.test.ts:61`).

*Remaining findings pending: X-2, X-3, X-6, X-10, then §12.*
