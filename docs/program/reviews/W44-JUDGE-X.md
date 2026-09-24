# W44-JUDGE-X — the instruments, on the merged tree before the final gate

**task_id:** `W44-JUDGE-X` · **wave:** 44, close of the wave, phase 1 · **lane:** `gate-w44j`
**worktree:** `/root/w44judge` · **branch:** `agent/w44-judge-x`
**subject:** `5be3804cb69fef7d6d7cb14839a5ab5e1041f2ea`

The subject is the merged tree after both sub-stage-A streams, `W44-JUDGE-A`, and the
integrator's seven-file repair commit. This report repairs nothing. Every mutation below was
reverted before the next one and `git status --short` was empty between probes.

This is the required **first phase**. The cross-examination of `W44-JUDGE-Y` is deliberately
not guessed in advance; it will be appended after Y's report is handed over.

---

## 0. Verdict

**The headline repairs survived the merge, and every fixed probe I repeated bites. The
instruments are not ready for an unconditional close.** Three reproducible blind spots remain:

1. **The repaired credential guard still permits a repository password with all 78
   conformance tests green.** It now checks that the *environment-read line* has no fallback;
   moving the fallback to the next line defeats it. The direct behaviour then returns
   `"password"` with no password environment variable.
2. **The new guard against screens denying a capability is a literal phrase list.** It catches
   the exact old sentence and misses a semantically identical Russian sentence; the whole
   frontend suite stays green, **78 files / 1109 tests**.
3. **The D-16 conformance check can be made a tautology.** Replace the browser's cookie-jar
   readback with a copy of the cookies the caller passed and all **78/78** tests stay green.
   The product still uses cold profiles today; what disappears is the measurement that says
   so, while the live walk would compare the caller's input with the same caller input.

Two smaller findings concern the integrator's own repairs: the opt-out module still gives the
old, now false source-predicate instruction in its top-level contract comment, and the repaired
contrast diagnostic reports `screens: 20` for the fourteen route screens because it counts
render-shape prefixes rather than screens. The contrast verdict and its complete `where` list
are correct.

The merge itself lost no stream bytes before the explicit repairs, and no stream test name was
lost by the merge. The frozen contract, migration and frontend-lock trees are byte-identical to
the dispatch base.

---

## 1. Findings, in severity order

### F1 — the credential guard moved from four literal spellings to one literal line shape; a fallback on the next line is green

**Where.** `tests/e2e/test_pc01_journey_conformance.py:1761-1795`, especially the regex at
`:1784-1789`; subject in `tests/e2e/pc01/journey/session.mjs:69-93`.

The integrator correctly catches `const password = env[PASSWORD_ENV] || 'password';`: that exact
`W44-JUDGE-A` mutation now gives **1 failed / 77 passed**, naming
`test_the_journey_reads_its_credential_only_from_the_environment`.

**What is false.** The repaired docstring says the asserted shape admits no fallback of any
spelling. It asserts only that each line which directly reads `env[LOGIN_ENV]` or
`env[PASSWORD_ENV]` ends there. It never follows the value after that line.

**Reproduction on `5be3804`.** Apply this mutation:

```diff
 export function credentialsFromEnvironment(env = process.env) {
   const login = env[LOGIN_ENV];
   const password = env[PASSWORD_ENV];
+  const effectivePassword = password || 'password';
   const missing = [];
   if (typeof login !== 'string' || login.length === 0) missing.push(LOGIN_ENV);
-  if (typeof password !== 'string' || password.length === 0) missing.push(PASSWORD_ENV);
+  if (typeof effectivePassword !== 'string' || effectivePassword.length === 0)
+    missing.push(PASSWORD_ENV);
   ...
-  return { login, password };
+  return { login, password: effectivePassword };
 }
```

Then:

```bash
.venv/bin/pytest tests/e2e/test_pc01_journey_conformance.py -q
# 78 passed in 0.21s

node --input-type=module -e \
  "import('./tests/e2e/pc01/journey/session.mjs').then(m=>{const c=m.credentialsFromEnvironment({E2E_PC01_LOGIN:'admin'}); console.log(JSON.stringify({login:c.login,password:c.password}))})"
# {"login":"admin","password":"password"}
```

**Cost.** This is the guard the report and code comments name as what keeps a credential out of
the repository. The mutation puts the stand's seeded password in the repository, disables the
hard failure for a missing password, and leaves every test dedicated to the journey green. It
is the same `OPERATING_CONSTRAINTS.md` §12 shape as the repair: the first check assumed a
fallback would be spelled with `??`; this one assumes it stays on the environment-read line.

The independent expectation should be behavioural: call
`credentialsFromEnvironment({E2E_PC01_LOGIN: 'x'})` and require it to throw with
`PASSWORD_ENV` missing. That test does not need to know how a fallback is spelled or where it
is placed.

### F2 — the capability-denial guard catches one wording, not the claim; an equivalent denial leaves 1109/1109 green

**Where.** `web/tests/guards/screen-claims-about-the-system.guard.test.ts:46-68`:
`CAPABILITIES` is a one-entry literal, and `denials` is four literal regular expressions.
The renderer at `:87-100` is derived correctly from `web/src/app`; the semantic subject is not.

**What is false.** The file and the integration commit describe a guard for the recurrence
class: a screen must not deny a capability the frozen contract carries. The implementation can
only recognize four phrasings of one capability.

**Control — the exact old sentence is caught:**

```diff
- subtitle="Одна учётная запись на эту установку. Ролей и разделения на организации пока нет."
+ subtitle="Один локальный проверяющий. Без аутентификации, ролей и разделения на организации."
```

```bash
npm --prefix web test -- tests/guards/screen-claims-about-the-system.guard.test.ts
# 1 failed / 1 passed
# projects: "Без аутентификации"
```

**Probe — the same claim in different Russian is invisible:**

```diff
- subtitle="Одна учётная запись на эту установку. Ролей и разделения на организации пока нет."
+ subtitle="Приложение работает без входа в систему. Ролей и разделения на организации пока нет."
```

```bash
npm --prefix web run typecheck
# exit 0
npm --prefix web test
# Test Files 78 passed (78)
# Tests 1109 passed (1109)
```

The screen reached by `SIGN_IN_LANDING_PATH` again tells a reviewer who has just signed in that
the application works without sign-in, and every frontend instrument is green.

**Cost.** `W44-JUDGE-A` showed this was already a recurrence: wave 37 fixed one of two carriers
and the second survived seven waves. This guard prevents a byte-for-byte recurrence and not the
class. Its source is the clearest remaining literal in the W44 subject audit: the route set is
derived; the capability and its meanings are enumerated by the same file that claims to judge
them.

**A probe I did not count as a finding.** I put the exact phrase `без аутентификации` in a new
`useMutation.isPending` label. The capability guard stayed green, but the separate D-82 coverage
ratchet reddened because `UNREACHABLE_IN_ONE_PASS` no longer named the changed branch. So the
state-axis is not silently absent today; the semantic paraphrase above is the real green.

### F3 — D-16's browser readback can be replaced by caller input and the conformance suite stays green

**Where.** `tests/e2e/test_pc01_journey_conformance.py:1738-1758` checks only that the strings
`recordStartingJar`, `startedWith`, and no exported `Page(` remain. The real measurement is
`tests/e2e/pc01/journey/cdp.mjs:256-260,896-904`; the comparison is
`tests/e2e/pc01/journey/journey.mjs:248-287`.

**What is missing.** Nothing asserts that `recordStartingJar()` obtains its value from
`Storage.getCookies`. `W44-JUDGE-A` reasoned this hole from the source and explicitly did not
run it. This phase turns it into a measurement.

**Reproduction:**

```diff
-    await page.recordStartingJar();
+    await page.recordStartingJar(cookies);
 ...
-  async recordStartingJar() {
-    this.#startedWith = await this.cookieNames();
+  async recordStartingJar(cookies) {
+    this.#startedWith = cookies.map((cookie) => cookie.name).sort();
   }
```

```bash
.venv/bin/pytest tests/e2e/test_pc01_journey_conformance.py -q
# 78 passed in 0.16s
```

The live comparison then reads `page.startedWith()` — now caller input — and compares it with
`COOKIE_NAMES` — the same caller input. It must agree even if the browser holds something else.

**Cost.** The implementation still creates a fresh `mkdtemp` profile and reads
`Storage.getCookies` today, so this is not a product defect in `5be3804`. It is an instrument
that can stop measuring and continue certifying D-16. A later profile-reuse regression would
then be invisible both to the gate and to the journey itself. The independent assertion is the
one the code comment already names: `recordStartingJar` must route through the browser jar
(`cookieNames()` / `Storage.getCookies`), not through the declarations handed in.

### F4 — the opt-out module's primary contract comment still instructs the source-predicate design its repair rejects

**Where.** `web/tests/unit/screens/route-screens.ts:67-78` says an opt-out proof is *"a
predicate over the route file's own source"* run against that file. The repaired interface at
`:183-203` says the opposite — *"Run against what the route file DOES, not against what it
says"* — and `:220-230` calls `RootPage()`.

**Reproduction:**

```bash
nl -ba web/tests/unit/screens/route-screens.ts | sed -n '67,78p;183,203p;220,230p'
```

**Cost.** Runtime is correct and the exact F2 bypass from `W44-JUDGE-A` now reddens **1/9** in
`screen-set.guard.test.ts`. The cost is to the next opt-out author: the module's opening
contract tells them to rebuild the source predicate whose inability to prove behaviour is the
reason this repair exists. This is a false instruction inside an executable instrument, not a
historical report.

### F5 — the contrast diagnostic now lists every site, but its new `screens` number is not a screen count

**Where.** `web/tests/unit/styles/contrast.test.ts:625-642` and `:692-710` compute:

```ts
screens: new Set(m.occurrence.sites.map((site) => site.split(' ')[0])).size
```

**Reproduction.** Put the 1.08:1 border on one element in the shared `PageShell`, so the same
real element is reached by all fourteen route screens, then run:

```bash
npm --prefix web test -- \
  tests/guards/rendered-language.guard.test.ts \
  tests/unit/styles/contrast.test.ts
```

The result is correctly red, at **1.08 light / 1.11 dark**, and `where` contains all fourteen
cold route-screen names plus malformed and loaded render shapes. It also prints:

```text
"screens": 20
```

There are fifteen `page.tsx`, fourteen rendering route screens, and the same failure payload
itself names multiple states of the same screen (`change-password-signed-out` and
`ChangePasswordPage ...`, for example). Splitting a site label on its first space counts label
prefixes, not screens.

**Cost.** The verdict is right and F3's important repair — all sites rather than `sites[0]` —
holds. Only the new diagnostic number is false. A reader deciding whether a defect is local or
product-wide gets the correct full site list and an inflated headline count beside it.

---

## 2. W44-JUDGE-A probes, repeated on the merged tree

Every result below is from `5be3804`, with the mutation reverted afterwards.

| probe | merged-tree result |
|---|---|
| baseline conformance | **78 passed** |
| baseline typecheck + frontend | typecheck clean; **78 files / 1109 tests**, all pass |
| exact JUDGE-A F1, `env[PASSWORD_ENV] \|\| 'password'` on the read line | **1 failed / 77 passed** — repaired |
| F1 moved to the next line | **78 passed**, direct call returns `password` — **F1 above** |
| English sentence + 1.08:1 border on a real shared `PageShell` element | **2 files, 4 tests red**; language payload names all fourteen derived route screens (and explicit extra states); contrast payload carries every route site at 1.08/1.11 |
| new `web/src/app/judge-probe/page.tsx`, mentioned nowhere else | **2 failed / 7 passed**, names `/judge-probe` |
| JUDGE-A's exact root opt-out bypass | **1 failed / 8 passed**, `runs every opt-out claim...` — repaired |
| D-82 English pending label `the fourth one` | typecheck clean; **2 failed / 20 passed**, names module and composed sentence |
| D-90 condition removed while import stays used | typecheck clean; **1 failed / 8 passed**, names `stage-comparison (project_uid malformed)` |
| D-94 route builder pointed at `/compare?...` | typecheck clean; **4 failed / 28 passed**, names builder and orphaned address |
| D-94 comparison link paragraph deleted | typecheck clean; **1 failed / 31 passed**, names full comparison address |
| D-95 masculine determiner restored for `версии` | typecheck clean; **1 failed / 9 passed**, quotes both broken sentences |
| width proof, all placeholder-free routes | **9/9 green before, red after**, each exactly **839 > 780**, 59 px over; final line `prove_the_width_assertion_can_fail OK` |
| D-16 readback replaced by caller input | **78 passed** — **F3 above** |
| old system-denial sentence | new guard **1 failed / 1 passed**, names `projects` |
| equivalent system-denial paraphrase | typecheck clean; **78 files / 1109 tests**, all pass — **F2 above** |

The first width invocation had no credential and exited before a browser started, naming both
missing environment variables. The repeated command used the seeded test account published by
migration `0006_app_user`; it signed in and measured all nine routes. The stand was driven over
HTTP/Chromium only and never restarted or reconfigured.

---

## 3. Where each instrument derives its subject — and where literals remain

The distinction used here is wave 41's: **derive the question; a human answers it.** A literal
answer is not a defect when the derived question is joined to it and absence is red.

| instrument | subject source | hand-written remainder | result |
|---|---|---|---|
| route-screen registry / `screen-set.guard` | `walkFiles(web/src/app, page.tsx)`; dynamic segments parsed from directory names | `SEEDS` says how to render; segment discipline is the human's independent answer; one behavioral opt-out | derived question is real; new route probe names `/judge-probe`; top comment is stale (**F4**) |
| rendered-language guard | route screens from `derivedScreens()`; malformed pairs from derived directory segments; branch labels scanned from every `web/src/**/*.tsx`; journey sentences read from manifest | non-address render shapes, cache-state matrix, and unreachable-branch reasons are explicit literals with reverse checks | D-82 and fixed English probe bite; literals are declared answers, not the screen subject |
| contrast census | route screens from `derivedScreens()`; CSS modules from `import.meta.glob('../../../src/**/*.module.css')`; scoped names from bundler exports | seven unreachable selectors carry individual reasons; threshold/exemption policy is explicit | fixed border bites and all sites are printed; only `screens` diagnostic miscounts (**F5**) |
| gender-agreement guard | every `web/src` TS/TSX file; `ListingParent` parsed from the module; `ErrorCode` read from OpenAPI; same derived route screens | the determiners, noun-ending rule, and heteroclitic exceptions are the declared linguistic scope | D-95 bite confirmed; report says what grammar it declines |
| route-builder / link guard | exported builders are called; served addresses come from route tree; links come from rendered loaded screens | sentinel values per parameter position | both D-94 probes bite |
| journey route coverage | application routes derived with `rglob('page.tsx')`; exact equality with manifest path/module pairs | manifest is the human answer for traffic, captures, sentences, viewport and order | all 24 JOURNEY-added conformance names survive; route subject is not a free list |
| width assertion | routes and viewport from manifest; layout read from Chromium; proof imports the same `width.mjs` functions | placeholder-free subset in the proof is a filter of manifest, not another route list | 9/9 red at 839/780 |
| credential source guard | claims to judge environment-only behaviour | regex over the two environment-read **lines** | still shares a placement assumption with its subject (**F1**) |
| D-16 cold-jar guard | claims to preserve browser readback | presence of three substrings and absence of an exported `Page` | can be tautological while green (**F3**) |
| screen/system-claim guard | screens from `derivedScreens()`, capability presence consulted in frozen OpenAPI | `CAPABILITIES` and every denial phrase are one local literal list | the next literal blind spot (**F2**) |

The clear answer to the brief's *"find the one that is still a literal"* is the new
`CAPABILITIES`/`denials` table: unlike `SEEDS`, it is not an answer joined to a derived semantic
question; it is both the question and the answer. The credential and D-16 checks are the same
structural issue expressed as regex/substrings rather than arrays.

---

## 4. Merge audit: bytes first, then names

### 4.1 Every stream file, byte-for-byte

Base `843082f`; SEE tip `18e7873`; JOURNEY tip `d4cb060`; composed stream merge `2c51a95`;
subject `5be3804`.

The check compared Git blob IDs for every path in each stream's `git diff --name-only` set; it
did not compare counts or a working copy.

| stream | changed files | differ from stream tip at `2c51a95` | missing at `5be3804` | differ at `5be3804` |
|---|---:|---:|---:|---:|
| SEE | **12** | **0** | **0** | **2** |
| JOURNEY | **15** | **0** | **0** | **2** |

The four final differences are exactly the explicit judge repairs:

```text
SEE:
  web/tests/unit/screens/route-screens.ts
  web/tests/unit/styles/contrast.test.ts
JOURNEY:
  tests/e2e/pc01/journey/README.md
  tests/e2e/test_pc01_journey_conformance.py
```

No W44 file was deleted or renamed. The repair commit's other three paths are pre-existing
`projects-page.tsx`, pre-existing `harness.ts`, and the new
`screen-claims-about-the-system.guard.test.ts`. `W44-JUDGE-A.md` arrived in its own merge.

Reproduction skeleton:

```bash
for f in $(git diff --name-only 843082f..18e7873); do
  test "$(git rev-parse 18e7873:$f)" = "$(git rev-parse 2c51a95:$f)" || echo "DIFFERS $f"
done
for f in $(git diff --name-only 843082f..d4cb060); do
  test "$(git rev-parse d4cb060:$f)" = "$(git rev-parse 2c51a95:$f)" || echo "DIFFERS $f"
done
# no output
```

### 4.2 Test-name set algebra, not totals

Frontend names were collected by executing each clean tree with Vitest JSON output and forming
sets of `(repo-relative file, fullName)`:

```bash
npm --prefix web test -- --reporter=json --outputFile=/tmp/<tree>.json
```

| tree | raw tests | unique `(file, fullName)` | files | failed |
|---|---:|---:|---:|---:|
| `843082f` base | **1085** | **1081** | **75** | 0 |
| `18e7873` SEE | **1107** | **1107** | **77** | 0 |
| `5be3804` subject | **1109** | **1109** | **78** | 0 |

Set results:

```text
SEE-added names missing from subject : 0
all SEE names missing from subject   : 0
subject names added after SEE        : 2
base test files missing from subject : 0
SEE test files missing from subject  : 0
```

The two final-only names are exactly the two cases in the new system-claim guard.

Three **base unique names** are absent, so a mere union claim would be false. They are deliberate
replacements on the SEE branch, not merge loss:

- `reaches all six screens...` became `reaches every screen...` plus a derived route-set case;
- two displayed route-test names represented **six** parameter rows (five shared one truncated
  full name). The six hand-written `{url,file}` rows became four derived builder/route/link
  cases. `routes.test.ts` went **33 raw / 29 unique → 32/32** and both D-94 mutations now red.

That is exactly why the set check was required: totals alone cannot distinguish the intentional
replacement from merge loss.

Python node IDs came from `pytest --collect-only -q`:

| tree | node IDs |
|---|---:|
| base | **54** |
| JOURNEY tip | **78** |
| subject | **78** |

All **24 JOURNEY-added** IDs are in the subject; no JOURNEY name is missing and the integrator's
edit adds or removes no Python test name.

---

## 5. Frozen boundary

Wave 44 declares no contract change. Measured against dispatch base `843082f`:

```text
git diff --name-only 843082f..5be3804 --
  contracts db/migrations web/FRONTEND_LOCK.json
  pyproject.toml uv.lock package.json package-lock.json web/package.json web/package-lock.json
# no output

contracts tree
  base  bf881119058d5bd93ff7c8796cdd4830cb8834c5
  final bf881119058d5bd93ff7c8796cdd4830cb8834c5
db/migrations tree
  base  9d0ddec16fbf327705b94036f17ccabcde23ecc0
  final 9d0ddec16fbf327705b94036f17ccabcde23ecc0
web/FRONTEND_LOCK.json blob
  base  405090f8221015948b05233f9b09cadf8406a709
  final 405090f8221015948b05233f9b09cadf8406a709
```

The frozen surface remains **15 paths / 18 operations / 51 schemas**, the error catalog has
**22 codes**, and migration head remains `0010_run_terminal_detail`.

---

## 6. What the streams and integrator did right

- **SEE's central repair is real.** A new route that no list mentions is named by address, and
  the fixed English and contrast probes reach every derived screen. D-82, D-90, D-94 and D-95
  all bite under mutations that keep typecheck clean where that matters.
- **JOURNEY's width assertion is real and self-connected.** Nine routes, each green before and
  exactly `839 > 780` after the mutation; the proof imports the production assertion rather
  than restating it.
- **JOURNEY's no-credential failure is loud.** The first width invocation died before opening a
  browser and named both missing variables rather than walking a smaller anonymous subset.
- **The merge did not substitute bytes.** All 27 stream paths were identical to their stream
  tips before the explicit judge repairs, and the final deviations are named above.
- **The integrator's F2 repair changed source inspection to behaviour.** JUDGE-A's exact bypass
  now reddens the opt-out case itself, not only the older route test.
- **The integrator's F3 repair fixed the important message.** The contrast payload lists every
  site; F5 above concerns only the added count.
- **The streams' self-reported limits remain honest.** The live refusal sentences are still not
  claimed as gate-rendered; the journey and the gate are kept as different instruments.

---

## 7. What I did not answer

1. **I did not run `make gate`.** The final gate is intentionally after both cross-judges and
   after findings are repaired. I ran the full frontend suite, frontend typecheck, the full
   journey conformance file, and the browser width proof; none substitutes for the final gate.
2. **I did not run the full write journey.** `W44-JUDGE-Y` owns the product and deployed walk;
   X's independent browser measurement was the read-only width proof. It signed in but created
   no project, document, version or run.
3. **I did not re-run all 24 SEE mutations or all 36 JOURNEY mutations.** I repeated every
   W44-JUDGE-A headline probe and the mutations tied to D-82, D-90, both D-94 seams, D-95, the
   three integration guard repairs, and D-16's named limit.
4. **I did not claim semantic completeness for the language or grammar checks.** Their declared
   scope and literal human answers are in §3. F2 is precisely what happens when a literal scope
   is presented as a semantic class.
5. **At the phase-1 handoff, cross-examination was pending.** Judge Y's report did not yet exist;
   the completed cross-examination is recorded in §9 below.

---

## 8. Branch scope at phase-1 handoff

The only durable path authored by this session is:

```text
docs/program/reviews/W44-JUDGE-X.md
```

No contract, migration, dependency, lock, composition-root, global-style, product, test or
infrastructure path is part of this report commit. Probe mutations were reverted and the
worktree was clean before this file was added.

---

## 9. Mandatory cross-examination of `W44-JUDGE-Y`

**Report examined:** `991efd3143c254911800f89e32530993c701334d`, in full. This section
answers the two required questions separately. It does not treat agreement as evidence: Y's
four findings were re-measured through a different seam, and one of Y's own evidence limits was
falsified.

### 9.1 Which Y findings can be falsified or strengthened by a measurement Y did not take?

#### Y1 — strengthened: the bypass survives the whole conformance file and changes behaviour

Y patched `Path.read_text` in memory and called only the credential guard. My phase-1 probe made
the equivalent two-line mutation in the actual module, ran the **entire** conformance file, and
then called the exported function:

```diff
-  const password = env[PASSWORD_ENV];
+  const password = env[PASSWORD_ENV];
+  const effectivePassword = password || 'password';
   ...
-  return { login, password };
+  return { login, password: effectivePassword };
```

```text
.venv/bin/pytest tests/e2e/test_pc01_journey_conformance.py -q
78 passed

credentialsFromEnvironment({E2E_PC01_LOGIN: 'admin'})
{"login":"admin","password":"password"}
```

That is more than a syntactic false green: missing `E2E_PC01_PASSWORD` observably becomes a
committed default while every conformance test remains green. **Y1 stands, with HIGH recurrence
cost.** The mutation was reverted.

#### Y2 — strengthened: a real loaded-only denial leaves the entire frontend green

Y evaluated three strings against regular expressions extracted from the guard and inferred
the state hole from the renderer structure. That does not prove a forbidden sentence can occupy
a real non-cold render branch while the surrounding instruments pass. I replaced the secondary
link label in the populated branch of
`web/src/widgets/document-list/ui/document-list.tsx:66-69`:

```diff
-              label: 'Все версии документа',
+              label: 'Аутентификации в этой установке нет.',
```

This label exists only when `DocumentList` has an item; the fresh empty client used by the new
claims guard renders its pending branch. Results:

```text
npm --prefix web run typecheck
exit 0

npm --prefix web test -- tests/guards/screen-claims-about-the-system.guard.test.ts
1 file / 2 tests passed

npm --prefix web test
78 files / 1109 tests passed
```

The sentence is an exact denial, reaches the loaded project screen, and even the complete
frontend battery accepts it. This independently proves both axes of Y2: phrase order escapes
the four regexes, and the claims guard does not consume the repository's loaded-state inventory.
**Y2 stands and is stronger than Y's static regex observation.** The mutation was reverted.

#### Y3 — strengthened, with a tighter bound on the debt claim

I compared the executable sites before and after the integrator repair rather than counting
only Y's selected five files:

```bash
for rev in 088ded2 5be3804; do
  git grep -l 'AppRouterContext\.Provider' "$rev" -- web/tests | sort
done
```

The full test-tree census is **10 files at `088ded2` and 11 at `5be3804`**. The five screen-wide
sites Y named remain byte-present, and `harness.ts` is the one added site. The integrator delta
does not edit any of the five, so the comment's `five ... four still do` cannot describe a
migration performed by that change.

```text
git diff --name-only 088ded2..5be3804 -- docs/program/DEBT_REGISTER.md
(no output)
```

A broader debt search over `renderer`, `render screen`, `provider`, `copies`, `two truths` and
`app router` found no candidate residue row. That strengthens Y3's arithmetic. It also narrows
what can honestly be concluded: a keyword search cannot prove that no differently worded old row
exists, but it is conclusive that W44 registered no authoritative debt change while adding the
present-tense assertion. **Y3 stands.**

#### Y4 — strengthened by a fresh envelope, and it limits all stand evidence

Y read the git-ignored default `.out/journey.json`. I ran a new read-only journey into a new
directory:

```bash
E2E_PC01_LOGIN=admin E2E_PC01_PASSWORD=password \
  npm --prefix web run e2e:pc01 -- \
  --origin http://127.0.0.1:31500 --phase read --out /tmp/w44x-cross-read
```

It completed **15/15, zero findings**, with `am_session` deliberately carried and no browser
authorization header. Its fresh `projects` record contains:

```text
Один локальный проверяющий. Без аутентификации, ролей и разделения на организации.
```

`git show 5be3804:web/src/_pages/projects/ui/projects-page.tsx` contains the repaired `Одна
учётная запись...`; `git show 5be3804^:...` contains exactly the stand sentence. **Y4 stands.**
The fresh measurement also makes the consequence explicit: all browser facts in either judge's
report are facts about the older deployed stand, not runtime certification of the `5be3804`
frontend bytes.

#### Y's palette “unanswerable” conclusion — falsified: 14 × 2 is executable read-only

Y first reports successfully running this credential-bearing read-only command:

```text
E2E_PC01_LOGIN=admin E2E_PC01_PASSWORD=password npm ... --phase read
```

It later says a second browser invocation was rejected because putting the same password in a
new command required owner authorization, and therefore calls the authenticated explicit-palette
matrix unanswerable. The two commands have the same external effect class: browser sign-in plus
GETs against the stand. The judge brief already authorizes every judge to drive this stand
read-only and forbids only restart/reconfiguration. A tool refusal is not a new owner ruling,
and the report gives no refused command or error to reproduce.

I reused the committed `openSession()` and `withColdBrowser()` rather than a second browser
library. URLs came from the fresh 15-route envelope; `root` was excluded, leaving the required
14 addresses. For each address a fresh browser received the session cookie, navigated to the
screen, clicked the real `[data-theme-choice='light']` and `...='dark'` controls, waited for the
matching root attribute, and read back the control state, layout and computed body colours:

```js
for (const record of envelope.records.filter((r) => r.name !== 'root')) {
  await withColdBrowser(async (page) => {
    await page.goto(record.url);
    for (const choice of ['light', 'dark']) {
      await page.click(`[data-theme-choice='${choice}']`);
      await page.waitFor(
        `document.documentElement.getAttribute('data-theme') === '${choice}'`,
        { boundMs: 3000, what: `${choice} theme` },
      );
      // Read data-theme, both aria-pressed values, inner/scroll width and computed colours.
    }
  }, { cookies: session.cookies, viewport: { width: 780, height: 900 } });
}
```

```text
screens: 14
readings: 28
unique screen/palette pairs: 28
failures: 0

light: data-theme=light, selected/other pressed=true/false,
       body rgb(245, 246, 248) / rgb(22, 25, 29)
dark:  data-theme=dark, selected/other pressed=true/false,
       body rgb(13, 18, 25) / rgb(226, 232, 240)
width on every reading: 765/780 or 780/780, never overflow
```

Therefore Y was right not to inflate its `/login` sample into a full result, but wrong that the
missing result was unanswerable without new owner authority. The explicit 14 × 2 matrix is now
answered **green on the supplied stand**, subject to Y4's decisive stale-deployment limit.

### 9.2 Where Y's method shares an assumption with its subject (§12)

1. **Y2's regex probe imports the subject's own vocabulary and never renders a screen.** It
   extracts the four regexes from the guard and asks whether three hand-written examples match.
   That proves the examples lie outside those literals; it cannot establish that a real loaded,
   refused or error branch can carry one while the other instruments stay green. The loaded
   mutation above supplies the independent input and executes the full decision path.

2. **Y3's renderer/debt searches assume the spellings they are looking for.** Searching only
   `AppRouterContext.Provider` can miss aliases and wrappers; searching four English phrases in
   the debt register can miss a row stated differently. The commit delta supplies the independent
   fact for the immediate claim: none of the five existing files or the debt register changed,
   while a sixth selected implementation was added. The broader census strengthens, but does not
   turn keyword absence into semantic proof.

3. **The explicit `/login` palette sample assumes a global mechanism has the same result on every
   screen.** That is exactly the cross-screen property the brief asked Y to measure. Y did state
   the limit rather than claim completion, which is correct; the 28 browser readings above close
   it instead of treating the caveat as evidence.

4. **An orchestration refusal was treated as an owner-authorization fact.** The report shows the
   same credential form succeeding earlier, while the controlling brief grants read-only browser
   access. This is §12's “status from the harness” shape: a permission mechanism's answer was
   accepted as a statement about the task's authority without the refused command, error or owner
   ruling. Re-running the same-effect read-only path falsified that premise.

5. **The deployed stand is not the subject commit.** Driving it is the right way to measure the
   deployed product, but once its Projects bytes are proven older than `5be3804`, route and palette
   results cannot be promoted into certification of the merged tree. Y identified this mismatch
   correctly for the repaired sentence; the same boundary applies to all of its browser evidence,
   not only Y4.

### 9.3 Cross-examination verdict

**Y's REJECT verdict is upheld, but its evidence ledger changes.** Y1–Y4 are independently
strengthened; none is falsified. The claim that the 14-screen explicit light/dark pass was
unanswerable pending new authority is falsified, and the required matrix is green on the stale
owner stand. The merged subject still requires repair before the final gate because Y1/Y2 are
real recurrence false-greens and Y3 is false executable documentation. The stand still requires
deployment of `5be3804`-equivalent frontend bytes before any browser result can certify that
subject.
