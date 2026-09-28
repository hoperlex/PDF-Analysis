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

## 2. Y2 — the sentences

*pending*

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
