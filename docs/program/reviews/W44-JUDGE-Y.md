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
