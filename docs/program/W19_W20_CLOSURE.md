# Waves 19–20 closure: the app became drivable, and two rulings changed shape on contact

Written 2026-09-19 by the integrator. **`make gate` → `GATE OK`, exit 0**; battery 1806,
foundation 35, frontend 681.

Wave 19 built the screens. Wave 20 took execution off the request thread and carried out one
owner ruling that turned out to cost more than it had been priced at. Five streams, four
merged, one reverted on the owner's instruction with its evidence kept.

## 1. The result

| Stream | Row | Outcome |
|---|---|---|
| `W19-SHELL` | `D-16` screens, `D-22` | six addressable screens; a page reload survives |
| `W19-API` | `R-10` | `listProjects.document_count` populated |
| `W19-RUN` | — | the run screen says what the run did |
| `W20-EXEC` | `D-20` | the run leaves the request thread; `running` is observable |
| `W20-CODE` | `D-23`, `D-1.6` | the prose guard; `R-8` built, proved and **reverted** |

**Closed:** `D-16`, `D-20`, `D-22`, `D-23`. **Reopened with a price:** `D-18`.
Frontend **595 → 681**. Battery **1785 → 1806**.

**The application is drivable by hand.** Measured against the morning's figure:

| | `W15-RUN`, 2026-09-18 | after the rebuild |
|---|---|---|
| project page, fresh tab | **0 API calls** | **1** — `listDocuments` |
| what it said | *"No version published in this session"* | the document, with a route in |
| `startRun` | `202` already `published` | `202` `queued` in 22 ms |
| a poller's readings | `['published']` | `queued → running ×10 → published` |
| requests carrying `Authorization` | 0 | **0** |

## 2. Both waves found the defect somewhere other than where the brief pointed

This is now the rule rather than the exception, and it is worth stating as one.

**`D-16`'s screens were not in `web/src/app/**`.** That directory is nine files of six-line
delegations; the screen making zero calls was in `_pages/project-detail` and
`widgets/upload-panel`, and the version it could not reach sat in a `useState`. The session
read the *intent* of my ownership line, tabulated every file it touched with a reason, and
said that if the intent was narrower the **boundary** should move, not the report. That is the
right way round and it is now a memory rule.

**`D-19`'s count was produced seven layers deeper than it was consumed.** The serialiser was
already correct; the value died in a `SELECT` of three columns.

**`D-20` was not what its row said at all.** The row claimed `queued` and `running` were
unreachable. `executor.py:589-590` has written both since `B5`. They were unreachable **to a
client**, because creation and execution shared one transaction, so every intermediate state
was written and overwritten before anything committed. **A transaction-boundary repair, not a
write-the-missing-states repair** — and that distinction is what decided the crash story too.

**Four of my ownership lines were narrower than the code this week**, and two more in wave 20
(`bootstrap/composition.py` and `api/app.py`). Every session that measured instead of stopping
was right to.

## 3. The two things the browser found that no test could

**Rendering a field is not rendering a fact.** `W19-RUN` was sent to add timings and counts to
the run screen. Three of my premises were false: `published_finding_count` and the stage
timings were **already rendered**, and *"Published findings: not reported"* was a faithful
report of an empty reading from a run older than `W17-VIEW`. The real defect only appeared on
a cold load — **all four stages showed the same Started and Finished string**, because the run
takes 374 ms and the formatter prints to the second. Two correct, present columns carried zero
information. The repair is a `Took` column, and no unit test would ever have found it.

**The frontend had been built for a sequence the server could not produce.**
`web/tests/unit/run/polling.test.ts:108` already scripted
`['queued','running','validating','published']` against a fake transport. `PA-01` criterion
4's UI clause had a passing test and an unreachable subject. `W20-EXEC` needed **no `web/`
change at all** to make it real.

## 4. `R-8`, built and reverted, and the finding that outlives it

`W20-CODE` carried out `R-8` in full: `staged_upload_lost`, 503, `retryable: true`, proved
over a real socket — the two blob faults went from differing on `['correlation_id']` alone to
differing on five fields, 409 to 503.

**It did not land, for a cost the ruling had not priced.** Adding a domain-catalog code forces
one enum member into `contracts/api/v1/openapi.json` — *no path, operation or schema moved*,
the surface stayed 12 / 15 / 46 — but the contract's sha256 is recorded in
`web/FRONTEND_LOCK.json`, a hand-maintained file with no generator. **A catalog addition is
therefore also a frontend reseal.**

The session was blocked from that file twice — by its brief and by the harness's permission
classifier — and stopped rather than work around either. It offered me the four mechanical
steps; **I declined to perform an action a delegated session had been refused**, and put the
choice to the owner, who ruled `R-11`: revert.

**Nothing measured was lost.** The evidence is in `W20-CODE.md`; reinstating it is a
cherry-pick plus four steps whose six digest values are written down. And the general finding
is now `D-18`'s: `R-3` and `R-5` both paid this cost inside waves that were *already* resealing
the API contract, so **it had never once shown**. Any future catalog change is a two-document
change from the start.

## 5. Three failures of method, all self-reported

None of these was caught by review; each session found and disclosed its own.

- **A correct query, read before it finished.** `W20-CODE`'s sweep piped `grep` through
  `head -20`, and the first twenty hits were `status == 201`. It read the truncation as the
  answer, and it cost a red gate. That is a **fourth shape** for `OPERATING_CONSTRAINTS.md`
  §12 — not a wrong query, a correct one cut before it was read.
- **A mutation harness that reverted real work.** `git checkout` cannot tell your uncommitted
  work from the mutation. It happened to `W19-RUN` and it happened to me the day before.
  **Commit before you mutate.**
- **Killing a process by name on a shared host.** `W19-RUN`'s `ps | grep` sweep did not
  distinguish its own `next start` from the identically-named ones *inside other lanes'
  containers*, and restarted three alpha stacks. All recovered; none was its own.

And two of mine: **I merged and gated before pushing**, so `origin/dev` sat 18 commits behind
while a dependent session provisioned — it stopped at the stop line and was right to. And **I
cancelled a third stream after measuring that its work was already done**, rather than
inventing scope to keep three streams symmetrical.

## 6. What these waves hand forward

- **`D-18`** — open, with a measured price: a catalog code costs a frontend reseal.
- **`D-15`**, **`D-9`** (corpus, ruled `R-9` to wait for manual testing), **`D-1.6`**
  (PC-01's accepted artifacts have no erratum mechanism; creating one is the integrator's),
  **`D-8`**, **`D-11`**.
- **Two sentences left false and named**: `nginx.conf:37`'s comment about `startRun` being cut
  off mid-call, and `run-list.tsx:10-13` on waiting forever for `running`. The widget's
  behaviour is still right; only its reason moved.
- **`scripts/validate_bootstrap.py` fails on a clean tree**, and `make gate` does not run it.
- **No certification of the current state.** `main` is a gated tip tagged `alpha-w18`; the last
  certification is `W12-CERT`'s at `e6eae1e`, which now holds without a caveat since `D-1.5`
  closed. Wave 21 is establishing what `PA-01` actually says today.
