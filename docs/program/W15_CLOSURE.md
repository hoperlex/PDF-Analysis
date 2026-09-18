# Wave 15 closure: the browser sent no credential, and then it drove the whole journey

Written 2026-09-18 by the integrator. **`make gate` → `GATE OK`, exit 0** on the merged tip,
read from a log rather than through `| tail`.

Two streams. Wave 14 packaged the application and named exactly why the first live journey
could not start: **the frontend sent no credential at all**, on any of the twelve operations,
with no channel through which one could be supplied. `W15-AUTH` built that channel.
`W15-RUN` then drove a real browser through the deployed stack, and found six things four
certifications had missed.

## 1. The result

| Stream | Outcome |
|---|---|
| `W15-AUTH` | a server-side route in Next holds the token; the browser never sees it |
| integrator | the clean-lane breaker in my own baseline code, and wave 14's two `infra/` lines |
| `W15-RUN` | `D-5` answered, all seven journey steps driven twice, six defects |

**The app is reachable by a browser with a credential it never holds, over one origin.**
85 browser requests in the live journey, **none carrying `Authorization`**.

## 2. The shape, and why it is the one that survives OIDC

`web/src/app/bff/v1/[...path]/route.ts` — a catch-all Route Handler. The browser calls
`/bff/v1/<path>` on the origin it was served from; the handler reads the token out of the Node
process's environment and forwards. Three properties made it the answer rather than merely a
workable one, and the second two were checked rather than assumed:

1. **It is where OIDC lands without touching the twelve operations again.** Replacing a static
   token with an issued one is a change inside one route handler: today it reads an
   environment variable, tomorrow it exchanges a code and holds a session. `transport.ts`, the
   generated client, the twelve operations and the frozen contract do not move either way.
2. **It preserves wave 14's measured bundle property** — one origin, a relative base path, no
   baked origin in the built bundle.
3. **It needed no nginx change.** `location /api/v1` is special-cased and everything else falls
   to `location /` → `web:3000`, so a handler at `/api/v1` would never have been called.

**Measured, not asserted:** a build with the token as a sentinel puts **0 occurrences** of it
anywhere in `.next/`, while the same build puts a `NEXT_PUBLIC_*` sentinel in
`.next/static/chunks/904-*.js`. The instrument is proven on the same build that proves the
property — which is the only way that measurement means anything.

**And the sharper half of the problem was not in the brief.** `web/src` had no branch for
`authentication_required` **anywhere**: all five failure classifiers ended in
`default: kind: 'server_error'`, so even once a credential was sent, a refused one would have
rendered as a server fault. `PC01_ERROR_CODES` — the list of codes a PC-01 screen must render
— contained neither authorization code. That list was correct before `R-3` and false after it,
and nobody widened it. 19 mutations, 19 killed. Suite 440 → 498.

## 3. The defect I put there, and why no lane could see it

`W15-AUTH` found it while proving its own work on a fresh database. **It was mine.**

The response baseline's "cursor setup" POST bypassed `record()` — the only thing attaching
`T-6`'s credential. So from the moment `T-6` landed, that call was answered **401**, created
nothing, and its response was discarded. Case 16's second row never existed.

**On a lane that had been run before, an older project supplied it and the corpus passed.** On
a fresh one: 47 errors. Waves 13 and 14 were green because their lanes had history.

Proved on a purpose-built clean database: **55 passed, 2 projects** where the same lane had
given **8 passed / 47 errors / 1 project**.

The general lesson is not "add the header". It is that **a suite which passes only on a lane
with history is not a suite that passes**, and nothing in the gate distinguishes the two.

## 4. `D-5`, answered with the envelope

On 2026-09-16 a harness outside the repository drove the UI and got `POST /api/v1/runs` →
**500, twice**, and the session ended there. It logged status lines only, so the envelope was
gone. That was the only live-transport evidence this programme had ever produced.

A real headless Chromium clicked *Start run* against the deployed origin:

```
POST /bff/v1/runs -> 202  {"run_id": "run_01M2RTFR8TNHN7A6QK0WXEJ2ZV",
                           "state": "published", "provider_mode": "live"}
four stages succeeded; +11 793 ms to a terminal screen
```

The generated client over the same origin agrees: `202`, `published`, 10 475 ms.

**It closes as *not reproducible*, not as *explained*.** The only recorded 500 with that
signature predates the browser session by two days and is an **ancestor** of the commit that
recorded the row, so it explains it only if that harness drove an older checkout — and the
harness is gone. `W15-RUN` refused to round that off, which was right.

**The attribution is permanently unanswerable because somebody kept the status line and not
the envelope.** That is the whole lesson of the row, and it is why every stream since is told
to keep the envelope.

## 5. What a user found that four certifications did not

Seven journey steps, driven twice — once through the generated client over a socket, once
through a browser clicking real controls. Two live runs, `$0.076925` against the `OD-03` $1.00
ceiling. And six defects, none repaired, because **a session that repairs what it measures
cannot be cited for the measurement**.

**The largest is not a bug in any code.** The twelve operations have **no `listDocuments`, no
`listVersions`, no `listRuns`**. A project page on a **fresh load** makes **zero API calls**
and says *"No version published in this session"* — no Start-run control, no route back. Every
row, object, run, finding and decision survives; **no screen can reach them.** Four
certifications missed it because none ever reloaded a page.

That is the same class as wave 13's three criterion-10 defects, which survived four
certifications because none could construct a malformed multipart envelope in process. **The
pattern is now three for three: each new way of driving the system finds defects the previous
ways could not express.** In-process router → real HTTP envelope → a browser that reloads.

**And it corrected wave 14, which I had closed an hour earlier.** `reset.sh`'s restore
reattaches two of the four metadata keys the adapter writes; `blob-role` is lost, so every
later upload of the restored bytes answers `409` while the same bytes on a clean stack give
`201`. Wave 14 learned that `mc mirror` is not a backup of an object, fixed the digest, and
verified the fix **by reading**. A key only a write path consults survived the check.

**A restore is proved by writing to the restored instance, not by reading from it.** Under
`R-4` that restore is the commitment that real client documents leave the alpha host, so
`PA-01` criterion 10 was false in the direction that looks true.

## 6. What was false in my own briefs

- **`W15-AUTH` §7's "two `infra/` lines I stopped at" was stale by the time `W15-RUN` read
  it** — I had landed both. A report is a measurement at a commit, and this one was cited a
  wave later as if it were a standing fact.
- **"reuse or rebuild the wave-14 stack"** — reuse was impossible. Its images predate
  `W15-AUTH`, so the bundle carried `/api/v1`, there was no `/bff/v1` handler and the `web`
  container had no credential. A rebuild was mandatory, not optional.
- **"`.env.provider` carries `PROXY_LLM_*`"** — true of the repository's file, but the stack
  reads `infra/deploy/env/provider.env`, blank in a fresh worktree. Copying them across is an
  unmentioned step without which `settings.load` refuses in proxy mode.

## 7. The gate

```
GATE OK: battery, foundation, frontend and whitespace all pass
1726 passed, 5 skipped, 168 subtests passed
foundation 35 passed, frontend 498 passed (39 files)
```

Read from the log file, with `EXIT=0` appended by the same shell that ran `make`. This
programme once pushed a red gate by reading `make gate 2>&1 | tail -3` and taking `tail`'s
exit code; the habit that replaced it is written down here so it does not have to be
rediscovered.

## 8. What wave 15 hands forward

- The deployed stack is **driveable by a browser** and the credential path is proved absent
  from the bundle.
- **Six rows**, `D-16` through `D-21`, all from one live journey.
- `D-16` and `D-21` need a contract reseal. The owner ruled `R-5` on 2026-09-18: **one reseal,
  carrying both.**
- `D-17` needs the restore repaired and, more importantly, **re-verified by writing**.
