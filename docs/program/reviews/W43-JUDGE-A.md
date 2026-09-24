# W43-JUDGE-A — the stage-A judge, on both branches, before the merge

**task_id:** `W43-JUDGE-A` · **wave:** 43, stage A · **lane:** `gate-w43j`
**worktree:** `/root/w43judge` · **branch:** `agent/w43-judge` · **base:** `b7d9bc4`

**Subjects, both unmerged:** `agent/w43-compare` at `1579738` and at `4a2c493`, and
`agent/w43-prep` at `37a6bc2`.

**This branch repairs nothing.** Its diff against `b7d9bc4` is this file and nothing else;
`git diff --name-only b7d9bc4 agent/w43-judge` is quoted in §10. Every probe below was applied,
measured and reverted with `git checkout -- web/src`, and the tree was confirmed clean between
probes.

**Where measurements were taken.** Subjects were examined by `git checkout --detach <commit>`
inside this worktree. Neither `/root/w43comp` nor `/root/w43prep` was entered and nothing was run
in either. Containers: `gate-w43j*` only; six containers of other lanes were up throughout and
none was touched (§4.6 contention is noted per figure).

## 1. Findings, most severe first

| # | finding | question | reproduction |
|---|---|---|---|
| **F1** | **No frontend instrument reaches any of the five new screens.** The whole 1047-test suite is green with four fully-English reviewer sentences on four reachable addresses. | J1 | §2.1 |
| **F2** | **`R-33`'s 3:1 border floor evaluated none of the five.** A border at 1.08:1 on a rendered element of the comparison screen leaves all three `R-33` cases green. | J1 | §2.3 |
| **F3** | **Where the census does speak about a new screen, its message is false** — *"NO screen renders an element they match"* about a rule a screen renders. And it speaks at all only if the screen brought a stylesheet: `W43-COMPARE`'s claim is true and understates the case. | J1 | §2.3, §2.4 |
| **F4** | **`W43-PREP` note 3: "Two modules call `logging.getLogger`". Three do.** The only false statement in the four notes. | J2 | §3.1 |
| **F5** | **Three of the four prepared screens explain the contract to a reviewer** — *«ни одна операция договора»*, *«в договоре нет»*. `R-18`/`D-58`, and it is the line `W43-COMPARE`'s brief draws and that stream honours. Recorded as a question for the owner, not as a verdict. | J4 | §5 |
| **F6** | **`StageComparisonPage`'s own `looksLikeProjectUid` check is asserted by nothing.** The full suite stays green when it is removed, once the unused-import artefact is avoided. | J5 | §6 |
| **F7** | *(observation)* the comparison table prints `dependency_unavailable` to a reviewer with no Russian gloss, where the run screen prints the same code with one. | J4 | §5 |

**F1–F3 are one mechanism seen three ways and they are the wave's result.** `D-69` is marked
**closed** in `DEBT_REGISTER.md` at `b7d9bc4`. On the evidence below it is closed on the axis
wave 41 repaired — *which contract members are seeded* — and open on the axis this wave tested:
**which screens are rendered at all**. Both instruments derive the thing they cross screens
against (the contract; the stylesheet) and both take the screen list from a hand-written literal:
`rendered-language.guard.test.ts:795`'s `const SCREENS` and `web/tests/unit/styles/screens.ts`'s
import list. The one instrument that reached all five untold is not a frontend instrument and did
not have to be told anything, because it derives its subject from the filesystem —
`rglob("page.tsx")` over `web/src/app` in
`tests/e2e/test_pc01_journey_conformance.py`. **That is the difference, and it is a property of
the query rather than of the language.**

Both streams reported this themselves, in their own words, before any judge ran. **Two streams
and an integrator agreeing is exactly the kind of finding that has been wrong before on this
programme, so it was re-measured from scratch here and it holds.**

## 2. J1 — do the instruments reach the new screens, without being told to?

**Answered per screen, and the answer is the same for all five: no frontend instrument
evaluates any of them, and pointing one at a screen is the only thing that changes that.**

### 2.1 The language guard, measured on each screen

| screen | branch / commit | state of the instruments | English probe | verdict |
|---|---|---|---|---|
| `/blocks` | `w43-prep` `37a6bc2` | un-pointed | whole English promise | **GREEN — unreached** |
| `/optimisation` | `w43-prep` `37a6bc2` | un-pointed | whole English promise | **GREEN — unreached** |
| `/logs` | `w43-prep` `37a6bc2` | un-pointed | whole English promise | **GREEN — unreached** |
| `/workers` | `w43-prep` `37a6bc2` | un-pointed | whole English promise | **GREEN — unreached** |
| `…/comparison` | `w43-compare` `4a2c493` | un-pointed | whole English sentence | **GREEN — unreached** |
| `…/comparison` | `w43-compare` `1579738` | pointed at `ed1b3e6` | same sentence | **RED — reached** |

The probe on the four prepared screens is stronger than the one the stream ran on itself. It
does not rename a title; it replaces the one sentence a reviewer actually reads on each of the
four with English prose, all four distinct so that `prepared-sections.guard.test.ts`'s own
distinctness case cannot fire and mask the result. **The whole frontend suite is green over it:
73 files, 1047 tests, 0 failed.**

```bash
cd /root/w43judge && git checkout --detach 37a6bc2
python3 - <<'PY'
import re, pathlib
for name in ['blocks','logs','optimisation','workers']:
    p = pathlib.Path(f'web/src/_pages/{name}/ui/{name}-page.tsx')
    s = p.read_text()
    p.write_text(re.sub(r'promise="[^"]*"',
        f'promise="PROBE {name}: this whole sentence is deliberately English prose on a '
        'reachable screen and must not survive."', s))
PY
npm --prefix web run test          # -> Test Files 73 passed (73) | Tests 1047 passed (1047)
git checkout -- web/src
```

### 2.2 What *is* reached, and it is worth being precise about

The frame's **navigation labels** are inside the guard, because `AppFrame` is itself an entry in
`SCREENS`. The screens behind those labels are not. So the guard covers the word a reviewer reads
in the bar and not one word of the page it opens:

```bash
cd /root/w43judge && git checkout --detach 37a6bc2
sed -i 's|^          Блоки$|          Blocks|' web/src/_app/app-frame.tsx
npm --prefix web run test -- tests/guards/rendered-language.guard.test.ts -t "finds none at all"
# -> RED: expected [ 'Blocks' ] to deeply equal []
git checkout -- web/src
```

That is the honest shape of wave 41's repair and it matches what both streams reported: the
guard's **branch** census walks `web/src` and does reach a directory that did not exist when it
was written; its **screen** census is `rendered-language.guard.test.ts:795`, a hand-written
`const SCREENS` literal, and a screen absent from it is a screen none of that file's assertions
about prose can see.

### 2.3 The contrast census, and its red says something false

Wave 42's `R-33` floor — *every border that meets on a screen clears 3:1* — **evaluated none of
the five screens**, on either branch, before the census was pointed at one.

On `…/comparison` at `4a2c493`, giving a rendered element of that screen a border at **1.08:1**:

```bash
cd /root/w43judge && git checkout --detach 4a2c493
# .summary is rendered by the screen; give it a failing border
python3 - <<'PY'
import pathlib
m = pathlib.Path('web/src/widgets/stage-comparison/ui/stage-comparison.module.css')
c = m.read_text()
m.write_text(c.replace(
  ".summary {\n  margin: 0 0 var(--am-gap-lg);\n  color: var(--am-ink);\n}",
  ".summary {\n  margin: 0 0 var(--am-gap-lg);\n  color: var(--am-ink);\n"
  "  background: var(--am-paper);\n  border: 1px solid var(--am-surface);\n}"))
PY
npm --prefix web run test -- tests/unit/styles/contrast.test.ts
git checkout -- web/src
```

All three `R-33` cases **pass**. The one red is
`names every colour-bearing rule that NO rendered screen reaches`, naming six scoped module
selectors — and its message, *"NO screen in `screens.ts` renders an element they match"*, **is
false**: a screen renders them; `screens.ts` does not render the screen. The same probe at the
tip `1579738` reddens `R-33` properly, naming
`edge|--am-surface|--am-paper|-|border` at **1.08** in both palettes.

### 2.4 The claim `W43-COMPARE` asked me to check, and it is true and understated

`W43-COMPARE` §4.2 claims the census noticed its screen **only** because the screen ships a
collocated `.module.css` that `import.meta.glob('../../../src/**/*.module.css')` picks up, and
that a screen reusing the global `am-*` classes would have been **wholly invisible**. Both halves
hold, and the four prepared screens are the proof in the other direction:

- **With a rule of its own**, the census speaks — but under the coverage assertion, with the
  false message above, and never under the floor. Reproduced on `/blocks` by declaring
  `.am-blocks__probe { background: var(--am-paper); border: 1px solid var(--am-surface); }` in
  `globals.css` and rendering it on the blocks screen: `R-33` green,
  `expected [ '.am-blocks__probe' ] to deeply equal []` red.
- **With no rule of its own** — which is exactly what `W43-PREP`'s four screens are, since they
  reuse `am-state`, `am-state--neutral`, `am-state__title` and `am-state__detail` and declare
  nothing — **the census is silent in both directions.** `grep -n "blocks\|logs\|optimis\|workers"
  web/tests/unit/styles/screens.ts` at `37a6bc2` returns nothing, and the census is green.

**So the reach of the contrast census is a property of whether a screen brought a stylesheet,
not of whether a screen exists.** A screen built the way the thirteen project-section stubs and
these four are built cannot move that instrument at all.

## 3. J2 — are `W43-PREP`'s four data-shape notes true?

**Re-measured at `b7d9bc4`, every claim, with my own commands. Thirty-one of the thirty-two
checkable statements hold. One is false.**

### 3.1 The one false statement

> `docs/program/W43-PREP.md`, note 3: *"Two modules call `logging.getLogger`; those lines go to
> the process's output…"*

**Three do.**

```bash
cd /root/w43judge && git checkout --detach b7d9bc4 && grep -rn "getLogger" src/
# src/auditmanager/access/repository.py:118
# src/auditmanager/runs/carrier.py:106
# src/auditmanager/api/app.py:50
```

Cost: small in itself — the note's conclusion (*the server's own log lines are nowhere on the
surface*) is unaffected, and the screen says nothing that depends on the number. It is reported
because `P3` exists so the next wave can budget against these notes, and the note is the one
artefact of this wave whose whole value is that every figure in it was measured. The note also
did not say which command produced the two, so the query cannot be inspected — the one place in
either report where `OPERATING_CONSTRAINTS.md` §12's *"show the query"* is not honoured.

### 3.2 The four things the brief told the stream to verify rather than copy — all four re-measured

**1. The corpus's `coords_norm` and `polygon_points`.** Measured over the corpus itself, not the
manifest summary, in the original clone (`.local/` is git-ignored and no worktree carries it):

```bash
cd /root/projects/PDF-Analysis && python3 - <<'PY'
import json, glob, collections
c=collections.Counter(); p=collections.Counter(); s=collections.Counter(); b=collections.Counter(); n=0
files=sorted(glob.glob('.local/norms/corpus/*/blocks.json'))
for f in files:
    for blk in json.load(open(f))['blocks']:
        n+=1; c[json.dumps(blk.get('coords_norm'))]+=1
        pp=blk.get('polygon_points'); p['null' if pp is None else ('empty-list' if pp==[] else 'nonempty')]+=1
        s[blk.get('shape_type')]+=1; b[blk.get('block_type')]+=1
print(len(files), n, dict(c), dict(p), dict(s), dict(b))
PY
# 674 28249 {'[0.0, 0.0, 1.0, 1.0]': 28249} {'null': 28249} {'rectangle': 28249} {'text': 28249}
```

The note is right on every count **including its correction of the brief**: `polygon_points` is
`null`, not an empty list, on all 28 249. Writing a screen against `[]` and being served `null`
is a real defect, and the note is the only document in this wave that records the difference.

Its second correction is right too and it matters more. *"There is no geometry to draw"* is true
of the legacy corpus and **false of this application**: `page_geometry_extraction` writes
`bbox {x0, y0, x1, y1}` with `BBOX_UNIT = "pt"` and `BBOX_ORIGIN = "top_left"`
(`src/auditmanager/analysis/stages/page_geometry_extraction.py:57,58,226-233`), one per text
line, keyed `b_%06d`. And no geometry word reaches the surface at all:

```bash
grep -oiE '"(bbox|coords_norm|polygon_points|x0|y0|x1|y1|width_px|height_px|page_width|page_height)"' \
  contracts/api/v1/openapi.json | sort -u          # -> no output
python3 -c "import json,re;print(sorted(set(re.findall(r'\"([a-z_]*block[a-z_]*)\"',open('contracts/api/v1/openapi.json').read()))))"
# -> ['block_analysis', 'block_id']
```

and `Evidence.block_id` carries verbatim the description the note quotes: *"Secondary anchor into
this version's block index. Not a contract identifier."*

**2. The one visible analysis stage.** `PC01_STAGES` is the four the note names
(`src/auditmanager/runs/repository.py:53-58`); `contracts/analysis/v1/stage-registry.json`
declares nine; `PROTOTYPE_PROFILE.md` §7.1 says verbatim *"One visible AI stage, canonical
`text_analysis`, is supported by three deterministic preparation stages"*. The note's refusal to
write "one against seventeen" without qualifying both halves is correct:
`docs/LEGACY_TECHNICAL_INVENTORY.md`'s list is exactly **17 directories observed**, and that
document does say sequencing is described *"in multiple places"*. `StartRunRequest` has exactly
`version_uid` and `provider_mode` under `additionalProperties: false`; no `section` field exists
anywhere on the surface; `contracts/` holds `analysis api comparison domain events` and **no
`optimization`**.

**3. No log-reading operation among the 18.** Verified by listing all eighteen rather than
sampling. None reads a log. `journal` occurs **6** times in the contract and every one is the
**decision** journal. The `audit_event` table exists in `0002_pc01_schema` and
`grep -rn 'audit_event' src/ | wc -l` is **0** — the note's sharpest observation, and the one a
future logs screen would otherwise have been built on.

**4. `PROTOTYPE_PROFILE.md` §7's exclusion of workers.** §7.2's **Deferred** list names both
*"remote/distributed workers"* and *"automatic retry/skip/resume policy, Job/Attempt lease,
heartbeat, fencing and outbox"*. The note's insistence that the document says **deferred** and
not **excluded**, and that the distinction decides what the screen may promise, is right and is
the reason `/workers` reads correctly (J4). `execution_scopes` says of itself *"a target
statement, never a legacy parity claim"*; `runs/executor.py` runs `PC01_STAGES` in order, in
process; the schema has **16** tables and none is a job, attempt, lease or worker.

### 3.3 One thing §7.2 also says, which neither report mentions

**§7.2's Deferred list also names `comparison`.** By the standard `W43-PREP` applies to
`/workers` — a deferred section may not say *coming soon* — the comparison screen's *«появится
позже»* would be the same claim. **It is not, and the integrator should know why before the
merge:** `R-23` rules the stage comparison explicitly — *"very important; a stub skeleton now,
the real thing during the alpha"* — and an owner ruling of 2026-09-22 is later and more specific
than the profile's list. The two streams reached opposite conclusions about two §7.2-deferred
sections and **both are right**, for a reason neither wrote down.

## 4. J3 — is any number on these screens invented?

**No, on all five, and the two streams arrived there by different routes that are both sound.**

**`W43-PREP`'s four carry no digit at all.** Rendered and read rather than grepped:

```bash
# rendered markup of all four, visible text only — the dump is in §9
# /blocks /optimisation /logs: title, «Раздел пока недоступен», «Этот раздел ещё не готов.», one promise
# /workers:                    title, «Раздела нет в альфе»,   «Распределённых исполнителей в альфе нет.», one promise
```

Their own guard asserts it (`withDigits`), and it asserts the right thing: its `can fail` case
uses `'Исполнителей: 0'`, which is the plausible zero the question warns about.

**`W43-COMPARE`'s screen prints figures, and every one of them is a reading.** Driven through
`screens.ts`'s `StageComparisonPage with two runs` state, the screen shows `3`, `0`, `4`,
`0.001234`, two durations, four instants, `Сопоставлено признаков: 11. Различий среди них: 10.`
— and `—` in six cells. Each traced back: the counts are `published_finding_count`,
`diagnostic_observation_count`, `model_call_count` and `cost_micros` off the two seeded
`RunStatus` readings; the two summary numbers are `comparedCount()` and `differenceCount()` over
the rows actually built. **The distinction the question is about is made structurally**: a
reported `0` prints `0`, an absent field prints `—` and the row reads
*«не сообщается ни одним прогоном»* rather than *«совпадает»*. `D-15`'s unreadable cost — a
`cost_micros` with no `model_call_count` — is routed to `null` and reads `one_sided`, never
`same` against a real figure.

## 5. J4 — does any stub promise something nobody decided to build?

**`/workers` is correct, and it is the best single piece of work in this wave.** It is the only
`RoutePlaceholder` in the tree that refuses the component's own two sentences, and it refuses
them for a measured reason. `«Раздела нет в альфе»` / `«Распределённых исполнителей в альфе
нет.»` — no *yet*, no date, and a promise that says what is true instead. The stream grew the
component two optional props to do it, both defaulting to today's wording, so every existing
caller renders the bytes it rendered before.

**The finding is the other three.** All three explain the contract to a reviewer:

| screen | the clause |
|---|---|
| `/blocks` | *«…но наружу их не отдаёт **ни одна операция договора**, поэтому показывать пока нечего»* |
| `/logs` | *«…но **операции, которая отдала бы их приложению, в договоре нет**…»* |
| `/optimisation` | *«Пока **запуск прогона принимает только версию документа и режим работы с провайдером**…»* |

`R-18` is that a finished application does not explain its own transport, and `D-58` was closed
by deleting exactly that kind of sentence. `W43-COMPARE`'s own brief draws the line in the same
words this finding needs — *«полное сравнение этапов появится позже»* is for a reviewer;
*«операция listRuns не отдаёт X»* is for you — and that stream honoured it, with a test asserting
no reviewer-facing string on its screen contains `listRuns`, `getRunStatus`, `RunStatus`, `API`
or `endpoint`. **`W43-PREP`'s three sentences are the generic form of the forbidden one**: they
name no operation, but they tell a domain expert auditing a PDF that a thing called *«договор»*
has *«операции»* and that this is why the screen is empty.

**Reproduction:** render each screen and read the longest visible string — the dump is §9, and
`prepared-sections.guard.test.ts`'s own `longest(visibleText(...))` produces it.

**Cost and judgement.** It is one sentence per screen and the rewrite is cheap
(*«…эти данные пока не доходят до интерфейса»*). I am not certain it crosses the line — the
sentences are in domain Russian and name nothing internal — so I record it as a question for the
owner or the integrator rather than as a defect, and I record that the two streams drew the line
in different places within one wave, which is itself worth one ruling.

**One smaller observation, not a rule violation.** The comparison screen prints
`dependency_unavailable` to a reviewer as a bare code. So does the run screen — but the run
screen puts `terminalReasonNote(...)`'s Russian gloss beside it
(`web/src/widgets/run-progress/ui/run-progress.tsx:154`) and the comparison table does not. A
reviewer reading the comparison meets an English error code with nothing next to it.

## 6. J5 — does each new guard bite?

**Thirteen mutations, twelve red, one survived.**

### `W43-PREP` — `web/tests/guards/prepared-sections.guard.test.ts`, 6 of 6 bite

Baseline 15 passed. Each mutation applied alone to the application (never to the test), run,
reverted with `git checkout -- web/src`, tree confirmed clean.

| # | mutation | assertion that reddened |
|---|---|---|
| P1 | `«разметка блоков страницы:»` → `«разметка блоков страницы (28 249 блоков):»` | *`blocks` shows no number at all* |
| P2 | `promise=` deleted from `logs-page.tsx`, so the component default renders | *none of the four falls back to the generic sentence* |
| P3 | `unavailability=` and `headline=` deleted from `workers-page.tsx` | *workers renders neither of the component's two "yet" sentences* |
| P4 | the `/logs` `<Link>` removed from `app-frame.tsx` | *the frame links to all four addresses* |
| P5 | `web/src/app/logs/page.tsx` made to render `BlocksPage` | *each address is served by a route file that renders its own screen and no other* |
| P6 | the optimisation promise set to the logs promise verbatim | *the four promises are pairwise distinct* |

The file also carries a `can fail` case per rule, exercising the pure function against a broken
input — so each rule is shown to fail **without** a tree mutation as well. That is the right
shape and it is the shape `styling-layer.test.ts` set.

### `W43-COMPARE` — 68 cases in three files, 6 of 7 bite

Baseline 68 passed.

| # | mutation | result |
|---|---|---|
| C1 | `compareReadings`: `return 'absent'` → `'same'` | **RED**, 7 cases |
| C2 | `compareReadings`: `return 'one_sided'` → `'same'` | **RED**, 7 cases |
| C3 | `defaultPair` returns `[newest, previous]` | **RED**, 3 cases |
| C4 | the stage cell renders `row.stageId` instead of `STAGE_LABELS[row.stageId]` | **RED** — *renders a stage id as a Russian label and keeps the contract value in `data-`* |
| C5 | `comparableCostMicros` reads `run.cost_micros` instead of going through `runCost` | **RED** — *treats a cost with no call count as absent rather than as a figure* |
| C6 | a transport word put in front of a reviewer: *«Ниже — то, что операция listRuns вернула по каждому прогону.»* | **RED** — *names no operation, field or schema to the reviewer* |
| C7 | `StageComparisonPage`'s own `looksLikeProjectUid(projectUid)` dropped from `wellFormed` | **SURVIVES** |

**C7 is the finding, and it is small but it is exactly what this question is for.**

```bash
cd /root/w43judge && git checkout --detach 1579738
sed -i 's/const wellFormed = looksLikeProjectUid(projectUid) \&\& looksLikeVersionUid(versionUid);/const wellFormed = looksLikeVersionUid(versionUid) \&\& (looksLikeProjectUid(projectUid) || true);/' \
  web/src/_pages/stage-comparison/ui/stage-comparison-page.tsx
npm --prefix web run test      # -> Test Files 74 passed (74) | Tests 1070 passed (1070)
git checkout -- web/src
```

The `|| true` is not decoration. Written the obvious way — deleting the call — the mutation dies
against `query-key-shape.guard.test.ts`'s `typechecks web/ clean`, because the import goes
unused. **That is a right answer from a wrong premise**, §12's near-miss shape: the mutation is
caught by `noUnusedLocals` and not by anything that knows what the screen is for. With the import
kept used, the whole suite is green.

`routes.test.ts`'s new case covers the **route file**'s `notFound()` on both segments, and
`W43-COMPARE`'s own M8 mutated that. The page component carries a **second, independent** check
of the same two identifiers, and nothing asserts the `project_uid` half of it. Cost: low —
in the application the route 404s first, so the branch is defence in depth — but it is a live
condition that no test can distinguish from `true`, on the one screen this wave added.

## 7. `D-89` — is the journey conformance the ONLY red on each branch?

The integrator asked me to check the claim rather than take it, because
`tests/e2e/pc01/journey/manifest.json` is in neither grant and both streams add screens. One
`make gate` per branch, verdict read from the log and never from a status a harness handed me.

### `agent/w43-compare` at `1579738`

```bash
cd /root/w43judge && git checkout --detach 1579738
make gate > /tmp/claude-0/-root-projects-PDF-Analysis/d3c5557d-39a2-4b53-84a1-12157aa41a8a/scratchpad/compare-gate.log 2>&1
grep -c 'GATE OK' /tmp/claude-0/-root-projects-PDF-Analysis/d3c5557d-39a2-4b53-84a1-12157aa41a8a/scratchpad/compare-gate.log     # 0
```

| | figure |
|---|---|
| foundation | **35 passed** in 25.78s |
| canonical battery | **1 failed, 2441 passed, 5 skipped, 4 warnings, 169 subtests** in **509.50s** |
| the one failure | `tests/e2e/test_pc01_journey_conformance.py::test_the_journey_walks_every_screen_the_application_offers` |
| its message | *1 screen(s) exist that the PC-01 journey does not walk: `['/projects/{project_uid}/versions/{version_uid}/comparison']`* |
| `GATE OK` | **absent**; the gate's own line reads *"GATE: the canonical battery failed with pytest exit status 1."* |

**The claim holds.** `2441 + 1 = 2442`, `alpha-w42`'s battery figure exactly: this branch adds no
Python test and loses none. The battery ran in **509.50s** against `W43-COMPARE`'s own 646.76s on
the same tree — a quieter machine, §4.6's contention read in the direction it is meant to be read.

### A third live instance of `OPERATING_CONSTRAINTS.md` §4.62, in this session

`W43-PREP` reported its harness handing it exit code 0 over a failed gate. **Mine did the same.**
The background task that ran this gate was reported **"completed (exit code 0)"** while the log
ends:

```
GATE: the canonical battery failed with pytest exit status 1.
make: *** [Makefile:1026: gate] Error 1
make exit=2
```

The `make exit=2` is the line the command itself appended after the redirect; the 0 belongs to
the wrapper. **Recorded because it is now three sessions in two days**, and because a judge that
had read the notification would have certified a green gate over a red one in the same report
where it faults others for trusting instruments.

### `agent/w43-prep` at `37a6bc2`

```bash
cd /root/w43judge && git checkout --detach 37a6bc2
make gate > /tmp/claude-0/-root-projects-PDF-Analysis/d3c5557d-39a2-4b53-84a1-12157aa41a8a/scratchpad/prep-gate.log 2>&1
grep -c 'GATE OK' /tmp/claude-0/-root-projects-PDF-Analysis/d3c5557d-39a2-4b53-84a1-12157aa41a8a/scratchpad/prep-gate.log        # 0
```

| | figure |
|---|---|
| foundation | **35 passed** in 24.81s |
| canonical battery | **1 failed, 2441 passed, 5 skipped, 4 warnings, 169 subtests** in **497.52s** |
| the one failure | the same conformance case |
| its message | *4 screen(s) exist that the PC-01 journey does not walk: `['/blocks', '/logs', '/optimisation', '/workers']`* |
| `GATE OK` | **absent**, same gate line |

**The claim holds on this branch too**, and the two failures are the same guard naming disjoint
sets of addresses. `2441 + 1 = 2442` again: neither branch adds or loses a Python test.

### The frontend figures, measured in this lane rather than inherited

| tree | frontend suite | typecheck |
|---|---|---|
| `b7d9bc4` (base) | **1032 passed in 72 files** | clean |
| `37a6bc2` (`w43-prep`) | **1047 passed in 73 files** — `+15` in `+1` | clean |
| `1579738` (`w43-compare`) | **1070 passed in 74 files** — `+38` in `+2` | clean |

Both streams' reported deltas reproduce exactly, and the base figure is measured here rather
than taken from `alpha-w42`'s tag. `+1` file is `prepared-sections.guard.test.ts`; `+2` are
`run-comparison.test.ts` and `stage-comparison.test.ts`. **No frontend test is lost on either
branch.** Whether the merge keeps all of them is `W43-JUDGE-B`'s question, and the arithmetic it
should hold the merged tree to is **1032 + 15 + 38 = 1085 in 75 files**, since the two branches
share no file.

### What this means for the merge

The manifest is the only thing either branch needs and neither was allowed to touch, and the two
streams' proposed rows do not collide: four `RoutePlaceholder` routes with `expects_api: []` and
one route with a single `listRuns` claim. Both sets of rows are quoted in the streams' own
reports. `W43-PREP`'s argument about **position** — after `sign-in`, because the read walk's
follow-chain captures identifiers in order — applies to `W43-COMPARE`'s row as well, and that one
addresses a `{project_uid}`/`{version_uid}` pair the walk must already have captured, so it
belongs **after** the routes that capture them rather than beside the four.

## 8. Where each stream did the right thing

An audit that only names faults teaches sessions to hide them, and both of these reported
weaknesses in their own work that nothing would have forced out of them.

**`W43-COMPARE` reported the measurement that makes its own screen look worse.** §4.1 states in
a table that both frontend instruments were **green** over a fully English sentence and a failing
border on its reachable screen (it quotes 1.06:1; the probe I ran on the same commit measures
the pair `--am-surface` on `--am-paper` at **1.08:1** light and **1.11:1** dark, which is the
figure its own after-wiring table gives — the 1.06 in its §4.1 prose is the one number in either
report that disagrees with itself, and it changes nothing), and §4.3 says outright *"I pointed both instruments at the
screen, and I am saying so rather than reporting a clean green."* It preserved the before-state
as a named commit (`4a2c493`) so the measurement is re-takeable — **which is the only reason this
judge could measure the un-pointed state at all.** I re-took it and it reproduces exactly. A
stream that had pointed the instruments in the same commit as the screen would have left a clean
green and no way to tell the difference.

**`W43-COMPARE` also reported four things outside its grant rather than repairing them** — the
missing `routes.ts` builder, the absent link from the version screen, the journey manifest entry
and the recommendation that `D-69` not be closed — and it reported that **its own screen is
reachable only by being typed** until someone else lands two lines. That is a stream saying its
deliverable is not yet wired into the product.

**`W43-PREP` deliberately did not seed its own screens**, wrote the reason into the guard file
itself, and reported the two halves of the result separately — *"wave 41's coverage repair is
half-reaching"* and *"the instrument that did catch the new screens is not a frontend instrument
at all"*. Both are exactly right. It would have been a single line in `screens.ts` and a single
entry in `SCREENS` to turn this wave's central measurement green and meaningless.

**`W43-PREP` corrected its own brief twice, in the direction that costs it work.** `null` rather
than `[]` on `polygon_points`, and *"there is no geometry to draw"* being false of our own
pipeline. It also argued the frame layout as a decision, named the alternatives it rejected and
why, and **disclosed the cost it could not pay**: six links plus the right-hand cluster will
overflow the bar on a narrow viewport, and the repair is one `flex-wrap: wrap` in a file it does
not own.

**`W43-PREP` caught a live instance of `OPERATING_CONSTRAINTS.md` §4.62** — its harness reported
exit code 0 over a gate that had failed — and reported it rather than reporting a green gate.

**Both streams independently reported the shared-hotspot collision** (`tests/e2e/pc01/journey/
manifest.json`) instead of editing it, and both wrote out the exact JSON the integrator needs.
`W43-PREP` went further and argued **where** in the file the rows belong — after `sign-in`,
because the read walk's follow-chain captures identifiers in order.

**Both stayed inside their grants.** Measured rather than asserted:

```bash
git diff --name-only b7d9bc4 1579738 | grep -E '^(contracts/|src/auditmanager/|db/|infra/|Makefile|web/FRONTEND_LOCK.json|web/src/shared/api/generated/|docs/program/DEBT_REGISTER.md|docs/program/dispatch/|web/src/_app/)'   # no output
git diff --name-only b7d9bc4 37a6bc2 | grep -E '^(contracts/|src/auditmanager/|db/|infra/|Makefile|web/FRONTEND_LOCK.json|web/src/shared/api/generated/|docs/program/DEBT_REGISTER.md|docs/program/dispatch/|web/src/_pages/stage-comparison|web/src/widgets/stage-comparison|web/src/app/projects/)'   # no output
comm -12 <(git diff --name-only b7d9bc4 1579738 | sort) <(git diff --name-only b7d9bc4 37a6bc2 | sort)   # EMPTY
```

**The two branches share no file at all.** The merge has no textual conflict to resolve; the only
thing they collide on is the file neither was allowed to touch.

The surface is unmoved on both: **15 paths / 18 operations / 51 schemas**, migration head
`0010_run_terminal_detail`.

## 9. The rendered screens, as a reviewer meets them

Taken by rendering, not by reading source (`D-53`). Visible text nodes only; attributes excluded.

**`/blocks`, `/optimisation`, `/logs`, `/workers`** at `37a6bc2`:

```
=== blocks ===
  | Блоки
  | Раздел пока недоступен
  | Этот раздел ещё не готов.
  | Здесь будет разметка блоков страницы: какие фрагменты документа анализ считает блоками и
  | где каждый из них находится. Границы блоков приложение уже вычисляет во время прогона, но
  | наружу их не отдаёт ни одна операция договора, поэтому показывать пока нечего.
=== optimisation ===
  | Оптимизация
  | Раздел пока недоступен
  | Этот раздел ещё не готов.
  | Здесь будет настройка анализа: какие модели и стадии применяются к документу и к разделу.
  | Пока запуск прогона принимает только версию документа и режим работы с провайдером, а
  | раздел документа нигде не хранится, поэтому выбирать здесь нечего.
=== logs ===
  | Журнал выполнения
  | Раздел пока недоступен
  | Этот раздел ещё не готов.
  | Здесь будет журнал выполнения прогона: что делал сервер, когда и чем это закончилось.
  | Сервер ведёт свои записи, но операции, которая отдала бы их приложению, в договоре нет,
  | поэтому сейчас этот журнал виден только тому, у кого есть доступ к самому серверу.
=== workers ===
  | Исполнители
  | Раздела нет в альфе
  | Распределённых исполнителей в альфе нет.
  | Прогон выполняет один последовательный исполнитель внутри самого приложения. Распределённые
  | исполнители и связанный с ними учёт задач и попыток вынесены за границы альфы, поэтому
  | здесь ничего не появится, пока это решение не изменится.
=== app-frame nav ===
  | AuditManager | База знаний | Смена пароля | Блоки | Оптимизация | Журнал выполнения
  | Исполнители | Вход
```

**`…/comparison`** at `1579738`, in the three states `screens.ts` seeds. The populated state
carries twelve fact rows and four stage rows; the cells are `3`, `0`, `4`, `0.001234`, two
durations, four instants, six `—`, and the four verdicts *«совпадает» / «отличается» / «есть
только у одного прогона» / «не сообщается ни одним прогоном»*. Its closing sentence is the one
`C2` asks for and stops where `C2` says to stop:

```
| Здесь сравниваются те признаки прогона, которые система уже записывает. Разбор того, что
| именно изменилось внутри этапа — какие находки появились, исчезли или поменяли формулировку —
| появится позже. Пустая клетка означает, что прогон этого не сообщил: это честнее, чем
| правдоподобное число.
```

## 10. Proof that this branch repaired nothing

```bash
cd /root/w43judge && git diff --name-only b7d9bc4 agent/w43-judge
# docs/program/reviews/W43-JUDGE-A.md
git status --porcelain      # (empty)
```

Every probe in this file was applied with `sed`/`python3` into `web/src`, measured, and reverted
with `git checkout -- web/src`; `git status --porcelain` was confirmed empty after each. No probe
was ever committed. Nothing outside `docs/program/reviews/` exists in this branch's diff.

**Lane discipline.** `gate-w43j` only — PostgreSQL `127.0.0.1:56280`, S3 `59880`/`59881`,
`FOUNDATION_INSTANCE=gate-w43j`. `docker ps` showed six containers belonging to `gate-w43a`,
`gate-w43b` and `auditmanager-w19a` up throughout; none was touched, started or stopped. Both
gate runs below therefore ran against a machine with three other compose projects resident, which
is the §4.6 contention context and is stated with the figures rather than after them.

## 11. Which of the five questions I could not answer, and why

**J1, J2, J3, J5 — answered in full.**

**J4 — answered, with one part deliberately left as a question rather than a verdict.** Whether
*«ни одна операция договора»* on a reviewer's screen is the sentence `R-18` and `D-58` forbid is
a line the two streams drew in different places inside one wave. I can measure what each screen
says and I can quote both rules; **I cannot rule on it**, and a judge that ruled on it would be
inventing a ruling. §5 states the measurement, the rule and the cost, and names it as a question
for the owner.

**What I did not measure, stated as a limit and not as a method note:**

1. **Neither branch was driven in a browser.** Every render in this file is a static server pass
   through `renderToStaticMarkup`. The comparison screen's run chooser is a `useState` branch no
   static pass reaches — `W43-COMPARE` §8 says so itself — so *"is any number invented"* is
   answered for every state a server pass produces and **not** for the state a reviewer reaches
   by selecting a different pair. `W43-JUDGE-B` runs on the deployed stand and that question is
   properly its.
2. **`D-88`'s reach was measured for the language guard and the contrast census only.** The other
   frontend instruments were exercised incidentally (the full suite ran green over the probes) but
   not probed one by one.
3. **The battery's contents were not compared item by item across the two branches.** Both came
   back `2441 passed` with one identical failing case, and `2441 + 1` is `alpha-w42`'s `2442`,
   so no test was added or lost on either — but a test *renamed* or *swapped* would satisfy that
   arithmetic. Only the merged tree can answer that, and it is `W43-JUDGE-B`'s first question.
