# W44-JUDGE-Y — primary adversarial audit

- **Subject:** `5be3804` (`integrate(W44): repair W44-JUDGE-A's five findings before final gate`)
- **Base inspected:** `088ded2..5be3804`
- **Role:** `W44-JUDGE-Y`, independent product/system-claims and executable-change audit
- **Date:** 2026-09-24
- **Verdict:** **REJECT / repair required before final gate.** The current product path remains usable in the read-only owner journey, but two newly asserted recurrence guards are weaker than their claims, the renderer-consolidation claim is factually wrong, and the supplied owner stand does not contain the audited Projects-page repair.
- **Scope discipline:** no product source, contract, migration, dependency, stand configuration, container, or foreign worktree was changed. This report is the only persisted deliverable.

## 1. Primary findings

### Y1 — Major — the credential guard is syntactic and admits an environment-read plus a committed fallback

**Location:** `tests/e2e/test_pc01_journey_conformance.py:1761-1794`, specifically the direct-assignment regex at `:1785` and its `endswith(env[PASSWORD_ENV])` assertion at `:1789`.

**False/missing claim.** The integrator describes the repaired test as proving that the journey credential is required from the environment and that a fallback of any spelling is rejected. It only proves that at least one assignment ending in `env[PASSWORD_ENV]` exists. A fallback moved to the next assignment is accepted:

```js
const passwordFromEnvironment = env[PASSWORD_ENV];
const password = passwordFromEnvironment || 'judge-default';
```

I executed the actual test function against that mutation in memory (no repository file was changed); the guard stayed green:

```text
GUARD GREEN: fallback moved one assignment later
```

**Reproduction:**

```bash
.venv/bin/python -c "import importlib.util; from pathlib import Path; from unittest.mock import patch; p=Path('tests/e2e/test_pc01_journey_conformance.py').resolve(); s=importlib.util.spec_from_file_location('judge_conformance',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); original=Path.read_text; target=m.SESSION_MODULE.resolve(); altered=original(target,encoding='utf-8').replace('  const password = env[PASSWORD_ENV];','  const passwordFromEnvironment = env[PASSWORD_ENV];\n  const password = passwordFromEnvironment || \'judge-default\';'); fake=lambda self,*a,**k: altered if self.resolve()==target else original(self,*a,**k); ctx=patch.object(Path,'read_text',fake); ctx.start(); m.test_the_journey_reads_its_credential_only_from_the_environment(); ctx.stop(); assert \"passwordFromEnvironment || 'judge-default'\" in altered; print('GUARD GREEN: fallback moved one assignment later')"
```

**Cost.** There is no fallback in the current journey module, so this is not a present credential leak. It is nevertheless a false regression guarantee: a harmless-looking refactor can reintroduce a default, disable the intended missing-secret `rc=2` behavior, and still pass the conformance suite. The guard must test observable missing-secret behavior or real value flow, rather than the spelling of one source line.

### Y2 — Major — “no screen may deny” checks four literal phrases in one cold state

**Location:** `web/tests/guards/screen-claims-about-the-system.guard.test.ts:19-22`, `:55-67`, and `:79-108`; the single render is at `:95`.

**False/missing claim.** The suite and commit claim a recurrence-class guard for screen-level denials of system capabilities. The implementation is four Russian regular expressions applied once to each derived screen with a fresh, empty client. It neither covers ordinary semantic equivalents nor the loaded/refused/error branches already exercised by the richer screen matrix. For example, every one of these denials escapes the new guard:

- `Аутентификации в этой установке нет.`
- `Система не использует аутентификацию.`
- `Вход не требуется.`

All three probes printed `false`:

```bash
node -e "const fs=require('fs'); const s=fs.readFileSync('web/tests/guards/screen-claims-about-the-system.guard.test.ts','utf8'); const b=s.match(/denials:\s*\[([\s\S]*?)\]/)[1]; const rs=[...b.matchAll(/\/(.+)\/i/g)].map(x=>new RegExp(x[1],'i')); for (const p of ['Аутентификации в этой установке нет.','Система не использует аутентификацию.','Вход не требуется.']) console.log(JSON.stringify(p),rs.some(r=>r.test(p)))"
```

The repository already exposes broader state-aware render inventories in `web/tests/guards/rendered-language.guard.test.ts` (`renderedScreens()` over `CACHE_STATES`) and `web/tests/unit/styles/screens.ts` (`screens()` with loaded widgets). The new guard does not use them.

**Cost.** The exact W44 sentence is now caught and the repaired sentence is clean, but a synonym or a denial displayed only after data load/refusal can ship while a test titled as a system-wide prohibition remains green. This is a material blind spot in the claimed recurrence protection.

### Y3 — Moderate — renderer consolidation arithmetic and debt-registration claims are false

**Location:** `web/tests/unit/screens/harness.ts:67-70`.

**False/missing claim.** The new comment says five test files had their own renderer, this extraction leaves four, and the residue is registered as debt. The executable delta does not migrate any of the five existing implementations. All five still contain their own `AppRouterContext.Provider`, while the new harness adds a sixth implementation site and is consumed only by the new claims guard:

```bash
rg -l 'AppRouterContext\.Provider' \
  web/tests/guards/prepared-sections.guard.test.ts \
  web/tests/guards/screen-set.guard.test.ts \
  web/tests/guards/gender-agreement.guard.test.ts \
  web/tests/guards/rendered-language.guard.test.ts \
  web/tests/unit/styles/screens.ts | wc -l
# 5
```

No matching authoritative debt row exists:

```bash
rg -n -i 'five test files|four still|two renderers|app router.*renderer' docs/program/DEBT_REGISTER.md
# no output
```

**Cost.** This is not cosmetic bookkeeping: the split render inventories already cause Y2's state-coverage hole and invite future differences in providers, router behavior, and fixtures. The comment cannot substitute for a debt-register entry, and the count must not imply a migration that did not occur.

### Y4 — Evidence blocker — the owner stand is older than the audited Projects-page repair

**Source location:** `web/src/_pages/projects/ui/projects-page.tsx:18` at `5be3804` says `Одна учётная запись на эту установку. Ролей и разделения на организации пока нет.`

**Observed stand claim:** the read-only journey envelope from `http://127.0.0.1:31500` still contains `Один локальный проверяющий. Без аутентификации, ролей и разделения на организации.`

**Reproduction:**

```bash
node -e "const j=require('./tests/e2e/pc01/journey/.out/journey.json'); const r=j.records.find(x=>x.name==='projects'); console.log(r.bodyText.split('\\n').slice(0,14).join('\\n'))"
```

**Cost.** The source repair itself is present and the source guard passes, but the supplied product surface still makes the false authentication claim. Consequently the browser run cannot serve as runtime evidence for F5 until the owner deploys the audited bytes. I did not restart or reconfigure the stand.

## 2. Product journey and palettes

The authorised read-only run succeeded:

```bash
E2E_PC01_LOGIN=admin E2E_PC01_PASSWORD=password npm --prefix web run e2e:pc01 -- \
  --origin http://127.0.0.1:31500 --phase read
```

Result: **15/15 records OK, 0 findings, `e2e OK`**. Every record retained `am_session`, reported `auth=0` and `console=0`; the document endpoint returned 200. No write phase or product-data mutation ran.

The 14 address-bearing screens were traversed in the stand's default/system palette: Projects, Project, Document, Version, Comparison, Run, Review, Sign-in, Knowledge Base, Change Password, Blocks, Optimisation, Logs, and Workers. The root redirect/landing record also passed. At viewport width 780, recorded document widths were 765 or 780 on every record; no horizontal overflow was observed.

The requested authenticated **14-screen explicit light plus explicit dark** pass is **unanswerable pending owner authorization**. The environment rejected the proposed browser command because it would place the stand password in a new command invocation; I did not bypass that refusal or mutate the stored palette. The non-authenticated `/login` screen was safely measured in both explicit palettes:

| Palette | `data-theme` | pressed toggle | inner/scroll width | body background | text color |
|---|---|---:|---:|---|---|
| light | `light` | true | 780 / 780 | `rgb(245, 246, 248)` | `rgb(22, 25, 29)` |
| dark | `dark` | true | 780 / 780 | `rgb(13, 18, 25)` | `rgb(226, 232, 240)` |

Therefore the evidence is: first/default palette across all 14 requested screens, explicit light/dark only on Sign-in, and no claim that the full 14 × 2 matrix was completed.

## 3. Re-measurement of stream and integrator claims

| Claim | Measurement | Judgment |
|---|---|---|
| W44-JOURNEY read-only route surface is drivable | 15/15 records, 0 findings, session preserved, no auth/console failures | Confirmed on the supplied stand |
| W44-SEE frontend suite is green | Full Vitest: 78 files, 1109 tests passed | Confirmed; the merged subject has two tests beyond the stream's recorded 1107 |
| Journey conformance is green | Pytest: 78 passed | Confirmed for current source |
| Route inventory and root opt-out repair | Target suite passes; root factory is invoked and `NEXT_REDIRECT` is asserted | Confirmed |
| Contrast report includes site/screen accounting | Target contrast test passes and reports all enumerated sites/screens | Confirmed |
| Projects source no longer denies authentication | Repaired string present at `projects-page.tsx:18`; exact old phrase rejected by source guard | Confirmed in tree, not on stand |
| Credential recurrence class is closed | In-memory fallback mutation passes | **Falsified (Y1)** |
| Screen-level system-denial recurrence class is closed | synonyms and non-cold states are not covered | **Falsified (Y2)** |
| Shared renderer leaves four copies and registers residue | five old copies remain; no debt row found | **Falsified (Y3)** |
| Both explicit palettes were visually driven on 14 screens | command authorization denied; only `/login` explicit-palette probe available | **Unanswered, not claimed complete** |

The six upload refusal cases were not replayed because this assignment constrained the stand to read-only behavior. The prior stream evidence was audited, but not inflated into a new Y-run result.

## 4. Audit of the seven executable/documentation changes in `088ded2..5be3804`

1. `tests/e2e/pc01/journey/README.md` — route count and width-failure-cost wording are repaired and consistent with the measured run.
2. `tests/e2e/test_pc01_journey_conformance.py` — current tests pass; root opt-out proof is materially improved; credential proof remains bypassable (Y1).
3. `web/src/_pages/projects/ui/projects-page.tsx` — the false no-authentication sentence is removed in source; runtime stand is stale (Y4).
4. `web/tests/guards/screen-claims-about-the-system.guard.test.ts` — catches the exact incident wording but overclaims screen/state/semantic coverage (Y2).
5. `web/tests/unit/screens/harness.ts` — useful helper for the new guard, but its consolidation/debt note is inaccurate (Y3).
6. `web/tests/unit/screens/route-screens.ts` — root factory now provides executable redirect evidence; no counterexample found.
7. `web/tests/unit/styles/contrast.test.ts` — missing-site accounting is repaired; no counterexample found.

The Projects subtitle's `Одна учётная запись` statement agrees with the current R32/W41-AUTHOR ownership record, so I do not report it as a present false product claim. It is a contract/runtime-cardinality assertion that will need revisiting if the owner later enables more accounts.

## 5. Verification log

```text
.venv/bin/pytest tests/e2e/test_pc01_journey_conformance.py -q
78 passed in 0.57s

npm --prefix web test -- tests/guards/screen-claims-about-the-system.guard.test.ts \
  tests/guards/screen-set.guard.test.ts tests/unit/screens/routes.test.ts \
  tests/unit/styles/contrast.test.ts
4 files passed; 63 tests passed

npm --prefix web test
78 files passed; 1109 tests passed
```

Frozen-hotspot comparison against the W44 base `843082f` was clean for `contracts`, `src/auditmanager`, `db`, `infra`, `web/FRONTEND_LOCK.json`, `Makefile`, and root dependency/lock files. Observed frozen identifiers:

- OpenAPI SHA-256: `013e22ae46ee528d7a4b5fd2b9f24a22d3cb8754152a28e41977d93029f9ef9d`
- `web/FRONTEND_LOCK.json` SHA-256: `bcb993c5a39563f50c07c7d66663a4870d4dffd1e70640ed8d119e21b372f4c1`
- frontend: 15 `page.tsx` entries
- API surface: 15 paths, 18 operations, 51 schemas, 22 declared errors
- migration head: `0010`

## 6. Required disposition before final gate

- Treat Y1 and Y2 as failed recurrence guarantees, not as present-source regressions.
- Correct the renderer-count/debt assertion in Y3 or establish the claimed authoritative debt entry.
- Deploy `5be3804`-equivalent frontend bytes to the owner stand before using it as evidence for F5/Y4.
- Obtain explicit owner authorization before retrying the authenticated 14-screen light/dark matrix; this judge did not evade the credential-command refusal.
- Do not interpret this primary report as the mandatory JUDGE-X cross-examination; that is a separate second phase.

## 7. Ownership proof

The intended final branch delta from `5be3804` is exactly this file:

```text
docs/program/reviews/W44-JUDGE-Y.md
```

No checkpoint or tag was created.

## 8. Phase 2 — cross-examination of W44-JUDGE-X

**Report examined:** `9aa25fd97871267ff35440837891c9117206e82a:docs/program/reviews/W44-JUDGE-X.md`.

**Cross-examination verdict:** X's F1, F2 and F3 survive and are strengthened by independent measurements that X did not run. F4 survives as a real contradictory instruction, but its cost is documentation-level because the executable type and local interface comment point the other way. F5's core observation survives — `screens` is not a count of the `Screen` entries that the census executed — while X's more specific claim that `20` is an *inflated* count relative to fourteen route screens is not established. That comparison imports a different unit into a census that intentionally includes pages, widgets and states. The overall **REJECT** verdict is therefore unchanged, but F5 must be restated as an undefined/heuristic unit rather than a proven inflated route-screen count.

### 8.1 F1 — strengthened with a second guard-green shape and its actual behavior

X moved a fallback into `effectivePassword`, changed the missing-value check and observed the direct call return `password`. I used a different, smaller data-flow break: alias the environment read and default the alias on the next line, leaving the rest of the function untouched:

```js
const passwordFromEnvironment = env[PASSWORD_ENV];
const password = passwordFromEnvironment || 'judge-default';
```

The actual Python guard remained green (the primary Y report gives the in-memory invocation). For phase 2 I also loaded that altered module entirely in memory and called the real exported function with only `E2E_PC01_LOGIN`. It did not throw; it returned:

```json
{"login":"admin","password":"judge-default"}
```

The module was loaded from a `data:` URL after rebasing only its relative `cdp.mjs` import to the same checked-out file; no repository byte changed. This is new behavioral evidence beyond X's particular mutation: any downstream alias can defeat the line-shape query. F1 is strengthened, not falsified.

### 8.2 F2 — strengthened semantically; X also narrows one part of Y2

X exercised one paraphrase through the full frontend suite. I independently extracted the four actual regular expressions and tested three further semantic denials that X did not use:

```bash
node -e "const fs=require('fs'); const s=fs.readFileSync('web/tests/guards/screen-claims-about-the-system.guard.test.ts','utf8'); const b=s.match(/denials:\s*\[([\s\S]*?)\]/)[1]; const rs=[...b.matchAll(/\/(.+)\/i/g)].map(x=>new RegExp(x[1],'i')); for (const p of ['Проверка личности пользователя в приложении не выполняется.','Для работы учётные данные не нужны.','Входить в систему не требуется.']) console.log(JSON.stringify({phrase:p,matched:rs.some(r=>r.test(p))}))"
```

All three produced `matched:false`. This strengthens X's semantic finding: the blind spot is not peculiar to his sentence `Приложение работает без входа в систему`.

X's separate pending-label probe does, however, falsify the broadest reading of my primary Y2 cost statement. An exact denial added as a new `useMutation.isPending` label is not silently absent: D-82's branch-coverage ratchet reddens. The supported Y2/X-F2 conclusion is narrower and stronger: semantic equivalents evade the capability guard; it is not proven that every newly introduced non-cold branch also evades the rest of the suite.

### 8.3 F3 — strengthened by a real caller/browser divergence, not another source-only mutation

X showed that the conformance suite accepts replacing the browser readback with caller input, but did not exhibit a browser state on which those two values differ. I supplied Chromium an already-expired cookie declaration and compared the caller's names with the actual `Storage.getCookies` readback through the unmodified `withColdBrowser`:

```bash
node --input-type=module -e "import {withColdBrowser} from './tests/e2e/pc01/journey/cdp.mjs'; const declared=[{name:'judge_expired',value:'x',url:'http://127.0.0.1/',expires:1}]; const observed=await withColdBrowser(async p=>({startedWith:p.startedWith(),jar:await p.cookieNames()}),{cookies:declared}); console.log(JSON.stringify({caller:declared.map(c=>c.name),...observed}));"
```

```json
{"caller":["judge_expired"],"startedWith":[],"jar":[]}
```

The local browser discarded the expired declaration. Under X's guard-green mutation, `startedWith` would instead be `['judge_expired']`, despite the jar being empty. This is the missing observable witness: caller declarations and browser state are not interchangeable. It strengthens F3 from a plausible tautology to a demonstrated false-positive case. No owner-stand request was made.

### 8.4 F4 — confirmed, with a narrower executable cost

I parsed `route-screens.ts` with the TypeScript AST rather than relying only on the two prose excerpts. The file contains one stale `predicate over the route file's own source` instruction, one local `what the route file DOES` instruction, and the actual `proof` function type accepts zero parameters:

```bash
node -e "const ts=require('./web/node_modules/typescript'); const fs=require('fs'); const p='web/tests/unit/screens/route-screens.ts'; const s=fs.readFileSync(p,'utf8'); const ast=ts.createSourceFile(p,s,ts.ScriptTarget.Latest,true); let proofParams=null; function v(n){if(ts.isPropertySignature(n)&&n.name?.getText(ast)==='proof'&&ts.isFunctionTypeNode(n.type)) proofParams=n.type.parameters.length; ts.forEachChild(n,v)} v(ast); console.log(JSON.stringify({proofParameters:proofParams,stalePhrase:(s.match(/predicate over the route file's own source/g)||[]).length,behaviourPhrase:(s.match(/what the route file DOES/g)||[]).length}))"
```

```json
{"proofParameters":0,"stalePhrase":1,"behaviourPhrase":1}
```

F4 is therefore a measured internal contradiction, not merely a difference in X's reading. The qualification is cost: the executable signature supplies no source argument, the interface-local comment demands behavior, and the only current proof invokes `RootPage()`. A future author could still close over source and follow the stale opening paragraph, so the text should be corrected; but this is a misleading documentation seam, not evidence that the repaired opt-out currently accepts the old bypass.

### 8.5 F5 — the core holds; the `20 > 14` framing is falsified

I executed the exported `screens()` inventory itself under the repository's Vitest/Vite configuration and counted both its actual entries and the exact first-token equivalence relation used by the diagnostic:

```ts
import { screens } from '/root/w44judge2/web/tests/unit/styles/screens.ts';
const xs = screens();
console.log({
  entries: xs.length,
  prefixes: new Set(xs.map((screen) => screen.name.split(' ')[0])).size,
});
```

```text
entries: 66
prefixes: 34
```

There are twenty multi-entry prefix groups, including `AppFrame`, six states of `RunProgress`, cold/loaded list pairs, refusal/change states, and malformed variants. This independently strengthens the core of F5: `screens: 20` is not the number of `Screen` values executed by the census.

It also falsifies X's precise interpretation that `20` is demonstrated to be an *inflated screen count* because there are fourteen rendering routes. The contrast subject is explicitly broader than routes: its own `screens()` returns 66 page/widget/state entries and 34 first-token families. `20` may be greater than 14 routes, but it is smaller than both census-based quantities. No authoritative identity relation says whether two states, a widget and its page, or malformed/valid variants are one “screen”. The defensible finding is therefore: the diagnostic publishes a heuristic prefix-family count under an undefined `screens` label. X has not established the direction of its error.

### 8.6 Direct answers required by the cross-examination brief

| X finding | New Y measurement X did not perform | Cross-exam disposition |
|---|---|---|
| F1 credential guard | A distinct alias/default mutation stayed guard-green and the real exported function returned `judge-default` with `PASSWORD_ENV` absent | **Strengthened** |
| F2 semantic denial | Three additional Russian semantic denials matched none of the four regexes | **Strengthened**; X's D-82 result narrows Y's earlier state-axis wording |
| F3 D-16 caller-input tautology | Chromium discarded an expired declared cookie: caller name present, actual starting/readback jars empty | **Strongly strengthened** with observable divergence |
| F4 stale opt-out instruction | AST measured one stale phrase, one behavioral phrase and a zero-argument executable proof contract | **Confirmed, cost narrowed** to contradictory guidance |
| F5 `screens: 20` | The subject inventory contains 66 executed entries and 34 prefix families | **Core strengthened; “inflated versus 14” falsified** |

**Where X shares an assumption with its subject (§12).** F5 is the clear instance. The subject assumes that the first whitespace-delimited token of a free-form site label is a screen identity. X rejects that answer by assuming route addresses are the independent screen identity and comparing `20` with fourteen, even though the measured census includes widgets and explicit states as first-class `Screen` values. Both methods infer identity from the same naming/topology conventions they are supposed to judge; neither joins occurrences to an independent screen key. Under §12, X's `20 is inflated` direction is not a measurement. The independent facts are only the three reproducible counts — 14 rendering routes, 66 census entries, 34 prefix families — plus the complete `where` list.

I found no comparable §12 defect in X's F1–F3 method: each uses a value independent of the query being challenged (observable missing-password behavior, a paraphrase outside the literal list, and caller declarations versus Chromium state). F4 is a direct contradictory-text observation with executable context, not a completeness claim.

### 8.7 Phase-2 scope and cleanup

- The owner stand was not restarted, reconfigured, written to, or contacted during these probes.
- The rejected authenticated palette procedure was not retried or bypassed.
- F1 mutations existed only in process memory; the D-16 probe used an automatically removed cold Chromium profile.
- Temporary F5 bundles in `/tmp` were deleted after the measurement.
- No product, test, contract, migration, dependency, lock, infrastructure, or foreign-worktree file was changed.
