# W32-SEE — an instrument that can see a rendered screen

**Task:** `W32-SEE`. **Base:** `cd475cc`. **Branch:** `agent/w32-see`, worktree `/root/w32see`.
**Contracts touched:** none. **`web/src` touched:** none — two mutations were applied and
reverted, and `git diff --stat cd475cc..HEAD` carries no file under `web/src`.

`R-18` makes presentation an acceptance condition and the gate cannot see a stylesheet.
Three sessions reported the interface translated and three were wrong (`D-53`), because
the strings they missed do not exist until React composes them. This wave gives the
repository two things it did not have: a browser that can photograph a screen, and a gate
that reads one.

---

## 1. How the screenshot landed, and the argument about `#send`

`tests/e2e/pc01/journey/cdp.mjs` gains `Page.screenshot(path, { fullPage, width, height })`.

**The brief said `#send` being private is the actual obstacle. It is not one, and that is
the design argument.** `#send` is private *to `Page`*. What it prevents is code **outside**
the class reaching the protocol — which is exactly the wall `W31-STYLE` hit, because it had
no licence to edit this file and could only call the public surface. A method **on** `Page`
is inside the class and calls `this.#send` like `goto`, `click` and `evaluate` already do.

So nothing was opened. The alternative — exposing `send` publicly, or adding an escape
hatch — would have widened the whole protocol to every caller in order to reach one method,
and the narrow public surface is the property that has kept this file from growing into a
browser library. The file's own header says what it deliberately does not do and that
anything needing more "is a reason to reopen the dependency question, not to grow this
file"; a screenshot is not more, it is one more call in a domain `enable()` already enables.
`Page.enable()` was already being sent, so `Page.captureScreenshot` needed no new domain and
no new dependency.

**Two properties worth stating rather than discovering later.**

- `fullPage` reads `Page.getLayoutMetrics().cssContentSize` and clips to it. That is the
  content box, which **excludes the scrollbar** a taller-than-the-window document brings, so
  a full-page capture comes back narrower than the viewport by the scrollbar's width — 385
  for a 400 viewport on this host. DevTools' own full-size capture behaves identically. The
  proof asserts it, so a change in it is visible rather than silent.
- `width`/`height` set `Emulation.setDeviceMetricsOverride`. Without them a capture is
  whatever window the browser happened to open, and an evidence photograph whose width
  depends on the machine is not comparable evidence. They are an override; omitting them
  changes nothing.

**`look.mjs` gains `--shot`**, off by default. That tool's stated contract is that it
asserts nothing — "a reading tool that also judged would invite the judgement to be written
after the reading" — and a reading that silently wrote files would change it.

### The anti-vacuity proof, and why it is in the tree

`tests/e2e/pc01/journey/prove_the_screenshot_sees.mjs`. Eight lines that write a file are
exactly the shape of change that gets believed without being watched: a `screenshot()` that
wrote a fixed blank PNG would satisfy every check anyone would think to run — the file
exists, it is a PNG, it is not empty — while seeing nothing. So the proof decodes the PNG
(IHDR for the size, and a real inflate-plus-unfilter for the pixels; reading a raw IDAT byte
would be reading compressed data and calling it a colour) and asserts in both directions.

It needs a Chromium binary and **no origin, no port, no stack, no built web image**, and
runs in about two seconds:

```
$ node tests/e2e/pc01/journey/prove_the_screenshot_sees.mjs
ok    the capture is the viewport it was asked for  -- 400x300, wanted 400x300
ok    a red page photographs red  -- rgb(255,0,0)
ok    a blue page photographs blue  -- rgb(0,0,255)
ok    repainting the page changes the bytes  -- 1038 vs 1039 bytes
ok    fullPage captures the document height the CSS declared  -- 385x600, viewport was 400x300
ok    a row below the viewport is in the photograph, and painted  -- rgb(0,255,0) at y=500, viewport height 300
ok    a full-page capture is narrower than the viewport by the scrollbar, and no more  -- 385 vs viewport 400: 15px of scrollbar
the screenshot sees the page.
EXIT=0
```

The third line is the one that matters: **a photograph that does not change when its subject
changes is not a photograph of its subject.**

**It is not in `make gate`,** for the same reason the journey is not — the gate is
stack-free and a browser is an environment prerequisite. What *is* in the gate is three
checks in `tests/e2e/test_pc01_journey_conformance.py`, which run inside the canonical
battery and need nothing: that `cdp.mjs` still declares `async screenshot(` and still speaks
`Page.captureScreenshot`, that `look.mjs` still offers `--shot` and still calls
`page.screenshot(`, and a negative control over sources that lost the method. They prove the
primitive is **declared and paired across two files**, not that it photographs anything —
the same residue that module already states for controls and markers, narrowed but not shut.

---

## 2. The guard

`web/tests/guards/rendered-language.guard.test.ts`. **Ten tests, one deliberately skipped.**

### Which side it belongs on, argued

`web/tests`, not `tests/e2e`. Three reasons and the third decides it:

1. `web/tests/unit/screens/harness.ts` already renders real page components with
   `renderToStaticMarkup` over a seeded `QueryClient`, and `W31-STYLE` used exactly that to
   photograph the screens. Building anything new would have been building a second one.
2. `make gate`'s `run_frontend` runs `npm --prefix web test`, so a vitest file is in the gate
   the moment it exists. The `tests/e2e` journey is explicitly *outside* the gate because it
   needs a built image, a bound port and a live stack.
3. **The guard must run on every commit, and a gate that needs a stack is a gate that gets
   skipped** — that is this repository's own stated reason for the split, and `D-53` exists
   precisely because nothing in the gate asked the question.

### What it renders

The six screens — `ProjectsPage`, `ProjectDetailPage`, `DocumentDetailPage`,
`VersionDetailPage`, `RunPage`, `ReviewPage` — in **seven cache states each, plus one**:
`cold`, `loaded`, `failed-run`, `partial-run`, `running`, `refused`, `empty`, and
`review (detail-pending)`. 43 renders.

Seven states and not one, because `D-53`'s survivors are spread across them: `Загрузка: the
run…` exists only while a question is unanswered, the panel labels only once it is answered,
`Correlation id` only when it is refused, and the four list widgets' third branch only when a
list comes back genuinely empty. That last state was added because a mutation found it
missing — §3.

### What it extracts

Every text node (`>…<`, with entities decoded so `&amp;` is not read as `amp`), plus four
attributes a browser shows a human: `placeholder`, `title`, `alt`, `aria-label`. `value` is
deliberately excluded: on these inputs it carries what the *test* typed, so including it
would make the guard judge its own fixtures.

### Why the seeded data is Cyrillic

A rendered screen carries two kinds of string: what the application wrote, and what the
server sent. Only the first is this programme's to translate — a finding's text is the
analysis's own words and may legitimately be in any language.
`web/tests/unit/review/fixtures.ts` seeds **English** finding text on purpose
(`"Delivery term stated as 30 days in §4 and 45 days in §9."`), so it is deliberately **not**
reused. Every value this guard seeds is Cyrillic, an identifier, or a contract enum.
**Anything Latin left in the output is therefore chrome the application authored**, and the
guard needs no rule for telling content from chrome — which is the rule that would have been
impossible to write.

### The allowlist

`W30-LISTS` closed eighteen instances of *a hand-maintained subset standing in for something
a contract defines*. An allowlist here is that class, so almost all of it is **read at run
time from the authority**:

| Source | What it supplies | Why it is the authority |
|---|---|---|
| `contracts/api/v1/openapi.json`, **every `enum` in every schema** | run states, stage ids, stage statuses, finding categories, verdicts, decision event types, provider modes, cost bases, **all 22 error codes** | One rule, no names written down. A twenty-third error code is allowed the moment the contract carries it; a removed one becomes an offence. This is also how the guard **takes no position on `DEBT_REGISTER.md` §2's open owner question** of whether contract vocabulary should be translated — it permits whatever the contract says, and stops permitting it the day the contract changes. |
| `docs/program/P02_SEAMS.md` §6 | the **seventeen CSV column names** | `OD-11` freezes them there; `web/tests/contract/csv-columns.contract.test.ts` already ties that table to `csv-columns.ts` and `exports/serializer.py`. The export panel prints the list to the reviewer, so those names are on a screen. |
| `contracts/analysis/v1/stage-registry.json` | the input/output **manifest roles** | The version panel prints an entry's role. `documents/models.py` derives `MANIFEST_ROLE_SOURCE_DOCUMENT` from this same file and raises at import if it cannot — its docstring records a session that restated the spelling as a constant and diverged silently. |

**Masking order is the whole design and is asserted, not described.** Machine *shapes* go
first, then whole contract *values* longest-first, and only what survives both is split into
words. So `needs_manual_review` is consumed as one value and **the guard never learns to
allow the bare word `review`** — which is the difference between deriving an allowlist and
writing a bag of words that stops catching things. There is a test for exactly that
(`does not learn a bare word from a compound contract value`).

**The machine shapes**, each with an authority outside this file so that "what shape is an
identifier" is not a question the guard answers by taste: prefixed ULIDs
(`contracts/domain/v1/identifiers.json` fixes the form — matched by shape, not by a list of
prefixes, because the catalog gains prefixes); bare ULIDs and UUID correlation ids; hex
digests; media types (RFC 6838); URLs and object URLs; filenames with a known extension;
absolute paths; ISO 8601 timestamps with an optional `UTC` designator; `PC-\d{2}`; and units
bound to a preceding number (`\d+\s*(KiB|MiB|ms|s|m|h|d|px|rem|%)`, so a bare `MB` in a
sentence is still an offence).

### The residue: eight entries, each with the reason no contract can supply it

| Entry | Why it cannot be derived |
|---|---|
| `proxy` | A provider mode the application supports and **the contract does not publish** — `openapi.json` `ProviderMode` is `live`/`recorded` only, and `W30-LISTS` §1.1 records `_DECLARED_MODES` as "the only extra is `proxy`". The owner's stand runs in it. **Derivable the day the contract publishes it**, and a test asserts it is *not* in the contract today, so this entry cannot go stale unnoticed. |
| `PDF` | The document format. A proper noun in Russian too (`PDF-документ`). `application/pdf` is matched separately as a media type. |
| `CSV` | The export format. RFC 4180 names it; no contract here does. |
| `API` | The name of the seam the screens talk to. Universal in Russian technical writing. |
| `RFC` | The IETF document series, cited by number beside the CSV escaping rule. A citation, not a label. |
| `SHA` | The digest algorithm family, shown as `SHA-256`. FIPS 180-4 fixes the spelling. |
| `UTF` | The character encoding family, shown as `utf-8`. The IANA charset registry fixes the spelling. |
| `UTC` | The time-scale designator. The ISO pattern consumes it after a timestamp; this covers it standing alone. |
| `MiB` | A unit symbol. IEC 80000-13 fixes the spelling and it is not localised. Bare form only; attached to a number the unit pattern takes it. |

Seven of the eight are **names of formats, standards and algorithms**, and they are the same
class `W30-LISTS` §1.4 ruled *out* of the hand-maintained-subset problem: "no contract or
catalog in this repository defines them, and no authority here can grow. Adding a guard would
mean pinning them to a copy of themselves." A list is the right answer for those, not a code
smell — and every one of them is untranslated in Russian technical writing, which is why they
are permitted rather than reported.

These eight are matched **case-insensitively**, which is a deliberate widening because
`utf-8` is written lowercase and `UTF` is the registry's spelling. It applies **only** to this
closed list and never to the contract vocabulary — so `Recorded:` as an English heading stays
an offence while `recorded` as a run's provider mode does not. That distinction is load-bearing
and is one of the strings §4 reports.

### How it is landed green without being weakened

The guard is **red on `cd475cc`** and `web/src` belongs to another live session this wave, so
`W32-SEE` may not repair what it finds. Committing a red gate is not an option and neither is
weakening the guard. So the nineteen outstanding strings are written down as `OUTSTANDING`,
with their modules, and asserted **in both directions**:

- **nothing outside it** — a *new* English string on a rendered screen reddens the gate
  today, which is the whole of what `D-53` asked for;
- **nothing missing from it** — translating one of these **also** reddens the gate, with a
  message saying to delete its line.

The second direction is the important one. `MEMORY.md`: *characterization can freeze a defect
— assert, don't just re-capture.* A list that only capped the damage would quietly outlive the
repair and the guard would go back to proving nothing. This one cannot: **it is a ratchet, it
may only shrink**, and when it is empty the one skipped test — `finds none at all` — is the
one to unskip. That test is skipped, not deleted and not weakened; it is the assertion the
guard exists to make.

The ratchet was observed working before it was believed: a first run listed
`— this run's provider mode is` with a typographic apostrophe in `OUTSTANDING` and a
typewriter apostrophe on the screen, and **both directions went red at once**, one for an
unrecorded string and one for a stale entry.

---

## 3. Both mutation directions, verbatim

### The first mutation reddened nothing, and the guard was not the reason

`web/src/widgets/project-list/ui/project-list.tsx`, `EmptyState title="Проектов пока нет."` →
`"No projects have been created yet."`

```
 ✓ tests/guards/rendered-language.guard.test.ts (10 tests | 1 skipped) 8ms
 Test Files  1 passed (1)
      Tests  9 passed | 1 skipped (10)
```

**`W31-STYLE` reported a fifth mutation that reddened nothing and said so, which is the
discipline; the brief asks which it is, and here it is the mutation.** A second mutation on a
string the guard certainly rendered — `projects-page.tsx` `title="Проекты"` →
`"All the projects in this deployment"` — reddened immediately:

```
+   "\"All the projects in this deployment\"  All deployment in projects the this  [projects]",
```

So the discriminator worked and the **coverage** did not: every seeded client held items and
every cold one was pending, so no list widget's *empty* branch was ever rendered — and four
widgets have one. **The coverage moved** (commit `8103cfa`, an `empty` state added to the
matrix), and no new offence appeared with it: the four empty states are already in Russian.
The same mutation then reddens:

```
 ❯ tests/guards/rendered-language.guard.test.ts (10 tests | 1 failed | 1 skipped) 13ms
   ✓ the guard reads a contract rather than a list of words > derives the whole published vocabulary from openapi.json
   ✓ the guard reads a contract rather than a list of words > keeps the hand-written residue small, and every entry reasoned
   ✓ the guard can tell an English label from a legitimate Latin string > calls an English label English
   ✓ the guard can tell an English label from a legitimate Latin string > does not redden a run state, a verdict, an identifier or a digest
   ✓ the guard can tell an English label from a legitimate Latin string > does not learn a bare word from a compound contract value
   ✓ the guard renders the screens it claims to render > reaches all six screens in every state, and none of them throws
   ✓ the guard renders the screens it claims to render > reaches past the loading state into a real reading
   × R-18: no Latin word reaches a reviewer that a contract did not put there > finds no English on a rendered screen that D-53 has not already recorded
     → ...: expected [ Array(1) ] to deeply equal []
   ✓ R-18: no Latin word reaches a reviewer that a contract did not put there > still finds every string the outstanding list claims, and no stale ones
   ↓ R-18: no Latin word reaches a reviewer that a contract did not put there > finds none at all (unskip when OUTSTANDING is empty)

+ [
+   "\"No projects have been created yet.\"  No been have projects yet  [projects]",
+ ]
```

### The other direction: legitimate Latin must not redden it

The same `EmptyState title` replaced with **one string carrying every class the brief names
as legitimately Latin** — the contract vocabulary, four identifier prefixes, a correlation
id, a digest, a media type, a URL, the product designation, units, four standard names, a CSV
column, a manifest role and an ISO timestamp:

```
title="Проектов пока нет: published partial failed cancelled queued running validating accept
accepted rejected pending needs_manual_review internal_contradiction explicit_placeholder
recorded live proxy text_analysis finding_merge succeeded skipped measured estimated
analysis_failed storage_integrity_error dependency_credential_refused
prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B doc_… ver_… run_… 0f0e9d8c-7b6a-4948-b726-150413021100
6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f application/pdf
https://example.test/a/b PC-01 25 MiB 4 m 0 s SHA-256 utf-8 RFC 4180 CSV API UTC PDF
source.document finding_uid current_verdict 2026-09-18T06:55:52.642022Z"
```

```
 ✓ tests/guards/rendered-language.guard.test.ts (10 tests | 1 skipped) 6ms
 Test Files  1 passed (1)
      Tests  9 passed | 1 skipped (10)
```

**A guard that fails on everything is not a guard, it is an outage.** Not one of those
reddened it, and nobody is forced to translate the contract vocabulary to keep the gate green.

Both mutations were applied to a committed-clean tree, run alone, and reverted;
`git status --porcelain` is empty at `HEAD`.

---

## 4. Every user-visible English string the guard finds, and whose it is

**Nineteen strings, measured at `cd475cc` by rendering.** None is in
`web/src/entities` or `web/src/shared/api`, which is why
`presentation-language.guard.test.ts` is green over them and why this list is not a
duplicate of anything.

| # | String, as a reviewer reads it | Screen | Module |
|---|---|---|---|
| 1 | `Create` | projects | `features/create-project/ui/create-project-form.tsx:89` |
| 2 | `Upload` | project-detail | `features/upload-document/ui/upload-document-form.tsx:117` |
| 3 | `Display title` | project-detail | `features/upload-document/ui/upload-document-form.tsx:95` |
| 4 | `Start run` | version-detail | `features/start-run/ui/start-run-control.tsx:44` |
| 5 | `Correlation id` | **five screens** | `shared/ui/states.tsx:42`, `features/start-run/…:63`, `features/upload-document/…:145` |
| 6 | `All versions of this document` | version-detail | `_pages/version-detail/ui/version-detail-page.tsx:82` |
| 7 | `Published findings: 3` | run | `widgets/run-progress/ui/run-progress.tsx:98` |
| 8 | `Recorded:` | run | `widgets/run-progress/ui/run-progress.tsx:178` |
| 9 | `Terminal reason:` | run | `widgets/run-progress/ui/run-progress.tsx:140` |
| 10 | `The run terminated` | run | `widgets/run-progress/ui/run-progress.tsx:137,159` |
| 11 | `. Nothing was published.` | run | `widgets/run-progress/ui/run-progress.tsx:137,159` |
| 12 | `provider mode:` | run | `widgets/run-progress/ui/run-progress.tsx:264` |
| 13 | `— this run's provider mode is` | run | `widgets/run-progress/ui/run-progress.tsx:264` |
| 14 | `Загрузка: projects…` | projects | `widgets/project-list/ui/project-list.tsx:24` — `LoadingState what=` |
| 15 | `Загрузка: findings…` | review | `widgets/finding-list/ui/finding-list.tsx:63` — `what=` |
| 16 | `Загрузка: the run…` | run, review | `widgets/run-progress/…:253` and `_pages/review/…:271` — `what=` |
| 17 | `Загрузка: the document page…` | review | `widgets/evidence-viewer/ui/evidence-viewer.tsx:130` — `what=` |
| 18 | `Загрузка: the finding…` | review | `_pages/review/ui/review-page.tsx:198` — `what=` |
| 19 | ``Одна версия на загрузку: этот экран не передаёт `uploadDocument` параметр `document_uid`…`` | document-detail | `widgets/version-list/ui/version-list.tsx:7` |

**Whose they are.** Every one is in `features/`, `widgets/`, `_pages/` or `shared/ui` — the
trees held this wave by `pdf-analysis-84`, and none is in a tree `W32-SEE` may edit.

**Numbers 14–18 are the class that matters.** Not one of them is findable by reading a
string: the module writes `what="the run"`, and `Загрузка: {what}…` is composed elsewhere.
`presentation-language.guard.test.ts`'s prose rule cannot see them either — `the run` carries
one function word and needs two. **This is why the repair had to be a renderer and not a
fourth sweep.**

**Number 19 is a different defect in the same output.** It is a sentence addressed to a
*developer* — it names an operation id and a request parameter — standing on a reviewer's
screen. It is the same class as the footer `R-18` names by name and `D-54` closed. It is not
a translation job; the sentence should not be there at all.

**Number 8 is worth a line.** `Recorded:` is an English heading; `recorded` is a contract
provider mode. The guard's case-sensitivity is what tells them apart, and a case-insensitive
contract vocabulary would have let this one through.

### Two things the guard renders that are not language defects

- **`R-18`'s "seventeen CSV columns printed to the user as a list" is still there.** All
  seventeen column names render on the review screen at `cd475cc`. They are contract
  identifiers, so the guard permits them — the defect is that they are *shown*, which is a
  question about what the screen contains, not what language it is in. Reported here rather
  than smuggled into a language guard.
- **Ten `LoadingState what=` arguments are English in source**, of fourteen call sites. The
  guard renders five of them; the other five (`the new project`, `the upload`, `the run
  request`, `the decision history`, `the finding` in one path) sit behind `useMutation`
  pending states or selection states that one static render pass cannot reach. Stated as a
  limit, not left to be discovered.

---

## 5. A defect found by rendering that is not about language

**`queryKeys.runs.detail(runId)` holds two incompatible shapes.**

- Written and read as a **bare `RunStatus`** by `entities/audit-run/api/use-run-status.ts:43,59,79`
  and `features/start-run/model/use-start-run.ts:38`.
- Written and read as a **`{ data: RunStatus }` envelope** by `_pages/review/ui/review-page.tsx:74,124`,
  whose `queryFn` returns the generated client's response.

One `QueryClient` serves both screens, so both shapes land under the identical key. Two
reachable consequences: a reviewer who watches a run finish and clicks through to review
renders `runQuery.data?.data` → `undefined` → `run = null`, so the review header and export
panel show their empty branch over a run that is in the cache — `D-16` in reverse; and after
the review page's own fetch settles, returning to the run screen makes `useRunStatus`'s
`useState` initialiser read the envelope, find `seeded.state` undefined,
`isTerminalRunState(undefined)` false, and **poll a finished run**.

Found because the guard had to seed both and could not. It is `web/src`, so it is reported,
not fixed; the guard carries two client builders and a comment saying why, so the next reader
does not conclude the harness is confused. **This is the third time in this programme that
rendering answered a question a file scan could not** — `OPERATING_CONSTRAINTS.md` §12's
sixth shape is the other two.

---

## 6. The gate delta, case by case

`make gate` from a committed-clean tree, lane `gate-w32a` (`POSTGRES_PORT=56110`,
`S3_API_PORT=59710/59711`, `POSTGRES_DB=audit_w32a`, `S3_BUCKET=auditmanager-gate-w32a`),
log at `/root/w32-logs/see-gate.log`:

```
GATE OK: battery, foundation, frontend and whitespace all pass
EXIT=0
```

| Component | Baseline | Measured | Delta | Accounted for |
|---|---|---|---|---|
| battery | 2013 passed, 5 skipped, 169 subtests | **2016 passed, 5 skipped, 169 subtests** | **+3 passed** | exactly the three checks appended to `tests/e2e/test_pc01_journey_conformance.py`: the screenshot is declared, `look.mjs` and `cdp.mjs` still agree about it, and the negative control |
| foundation | 35 | **35** | **0** | nothing in this wave touches `src/`, `db/` or `infra/` |
| frontend | 792 passed in 56 files | **801 passed, 1 skipped, in 57 files** | **+1 file, +9 passed, +1 skipped** | the one new file, `web/tests/guards/rendered-language.guard.test.ts`, contributing exactly ten cases: 2 derivation, 3 discriminator, 2 render-coverage, 2 ratchet, and 1 skipped (`finds none at all`) |
| whitespace | pass | pass | 0 | — |

`npm run typecheck` and `npm run lint` both exit 0. `git status --porcelain` was empty before
and after the gate run, so `checkout_is_unchanged` had nothing to report.

**`make up` did not hit the address-pool blocker.** `OPERATING_CONSTRAINTS.md` §4.5 says a
peer ran `docker network prune -f` after wave 31, and the lane came up on the first attempt.
Recorded because §4.5's third consequence is "do not read *the blocker cleared itself*" — it
did not clear itself here either; it had already been cleared by someone.

---

## 7. Every premise of the brief I measured and found false

**1. "`#send` being private is the actual obstacle."** It is not. `#send` is private to
`Page`; a method on `Page` calls it like every other primitive in the file. The obstacle
`W31-STYLE` actually hit was that it had **no licence to edit `cdp.mjs`** and could only call
the public surface from outside. Nothing needed opening, and the right design was to open
nothing. §1.

**2. "the whole version panel's `label=` props" are among the survivors.** They are not, at
`cd475cc`. All nine are Russian: `Версия`, `Документ`, `Порядковый номер`, `Тип содержимого`,
`Страниц`, `Размер`, `SHA-256`, `Опубликовано`, `Загружено как`. `3bd2c82` (`W31-UI-TAIL`)
repaired them after `W31-STYLE` measured them, and the brief carried the pre-repair list
forward. Check: `grep -o 'label="[^"]*"' web/src/entities/document-version/ui/version-panel.tsx`.

**3. "four `LoadingState what=` arguments."** There are **ten** English ones, across fourteen
call sites. The brief's four are the four the earlier session happened to render. Check:
`grep -rn --include=*.tsx 'what="' web/src | grep -v generated | grep -cvP 'what="[^"]*[а-яА-Я]'` → `10`.

**4. "`dev` has moved past `cd475cc` … your lane does not read those files."** My lane
**renders** them — the guard's subject is the whole of `web/src`, which is why the reading is
of `cd475cc` and not of `dev`. And it matters: `git diff --stat cd475cc..461b784 -- web/src`
is **7 files, 10 insertions**, and every one of them is a file §4 names. `pdf-analysis-84` is
repairing these strings right now, so **part of `OUTSTANDING` will already be stale when this
branch is merged** — see §8, this is the one thing the integrator must not merge blind.

**5. "`Published findings:`" and "`Display title`" and "`Create`" and "`Start run`" are the
remaining strings.** They are *among* them. The full rendered census is nineteen, and five of
the nineteen — the composed `Загрузка: …` strings — are invisible to every technique tried so
far including the brief's own list, which named only `the run`.

**6. "An allowlist is the whole difficulty."** It was about a third of it. The larger
difficulty was **telling the application's chrome from the server's content**, and the
allowlist could not have solved it: `"Delivery term stated as 30 days in §4"` is a finding's
own words and is legitimately English, while `Display title` is not, and no list of permitted
strings distinguishes them. Seeding Cyrillic data does, structurally, and the allowlist only
then has to cover the machine vocabulary. Stated because a session that starts on the
allowlist will build the wrong thing first.

**7. Not false, but stated so it is not re-measured:** the battery baseline `2013 / 5 / 169`
and the frontend baseline `792 in 56 files` are both **correct** at `cd475cc`, and foundation
is **35**.

---

## 8. Risks, limits, and instructions to the integrator

**Merge order matters, and this is the one thing not to do blind.** `pdf-analysis-84` is
translating the same strings `OUTSTANDING` records. The ratchet's second direction means a
merge with `dev` will go **red** on every string that session has already repaired, with a
message naming each one and saying to delete its line. That is the mechanism working, and the
repair is to delete those lines from `OUTSTANDING` in
`web/tests/guards/rendered-language.guard.test.ts` — **never to relax the assertion.** At
`461b784` seven of the nineteen's modules have already changed. Doing this after the merge
rather than before is deliberate: the list must be checked against a rendered screen, not
against a diff.

**Rollback.** Additive; three commits, droppable independently and in either order:

- `71651b7` — the screenshot, `look.mjs --shot`, the browser proof. Drop this and
  `ea99b05`'s three conformance checks go red; drop both together.
- `ea99b05` — the guard and the conformance checks.
- `8103cfa` — the `empty` state. Dropping it loses coverage of four widgets' empty branch and
  nothing else; the guard stays green either way.

**If the guard proves noisy, drop `ea99b05`.** It is the only commit that can redden a gate
on somebody else's work.

**Known limitations, stated rather than left to be found.**

1. **One static render pass.** No effect, no event handler, no second render. Five English
   `what=` arguments behind `useMutation` pending states are therefore invisible to it, and so
   is anything a click reveals. Named in §4.
2. **Six screens, not every component.** A widget no screen composes in one of the eight
   states is unread. The `empty` state exists because a mutation proved this is a live risk,
   and the same mutation technique is how to check it again.
3. **The `NOT_DERIVABLE` residue is case-insensitive.** Eight entries, so an English word that
   is a substring of one of them (e.g. `apid`, `pdfs`) would be partly masked. Measured on the
   current tree: no such word appears.
4. **`OUTSTANDING` is a ratchet, which means it makes repairs red.** Intentional, but it puts
   a one-line edit on whoever translates a string. The failure message says exactly which line.
5. **The screenshot is proved by a script outside the gate.** If Chromium disappears from this
   host the proof cannot run; the three in-gate checks would still hold the declaration.

**Two rows the register may want**, neither opened here because
`docs/program/DEBT_REGISTER.md` is a forbidden hotspot for this session:

- the `queryKeys.runs.detail` shape collision (§5) — reviewer-visible, two reachable paths;
- `version-list.tsx:7`'s developer-facing sentence on a reviewer's screen (§4, string 19) —
  the class `D-54` closed, recurring in a tree `D-54` did not cover.

**`D-55` can be closed.** **`D-53` cannot yet** — its repair is now *guarded* but not *done*,
and the nineteen strings in §4 are what is left of it.
