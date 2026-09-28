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
  *опубликован 1*, because `run-activity-panel.tsx:69` filters `(byState.get(state) ?? 0) > 0`.
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

## 3. Y3 — the journey, live

*pending*

## 4. Y4 — widths and palettes

*pending*

## 5. Y5 — `F-5b` mutated

*pending*

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
