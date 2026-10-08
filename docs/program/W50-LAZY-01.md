# W50-LAZY-01 — completion report

## Result

**DONE.** Branch `agent/w50-lazy-01` from base `96a1653` (= `origin/dev` = `integration/w50` at
dispatch, the commit carrying the integrator's rulings at the `W50-REGISTRY-01` merge). One code
commit, `d0d71ad`; this report is a docs-only commit on top of it, and the gate measured
`d0d71ad` (§2.8, §2.9).

- The five heavy widgets — `widgets/dashboard`, `widgets/knowledge-base`,
  `widgets/run-progress`, `widgets/evidence-viewer`, `widgets/stage-comparison` — reach their
  pages only through a `next/dynamic` wrapper beside the page
  (`_pages/<slice>/ui/lazy-*.tsx`), whose `loading` is the typed `<LoadingState />` from
  `shared/ui` («Загрузка…»). No `_pages/**` module keeps a static edge to any of them, `import
  type` included.
- **The bundle splits.** First-load JS, exact gzip bytes, base and head built in one directory
  (§2.5): `/dashboard` −25,146, `…/versions/[version_uid]/comparison` −9,866,
  `…/runs/[run_id]` −7,775, `/knowledge-base` −2,352; every other route +633 … +1,370, inside
  the owner's amended bound (≤ 1.5 kB gzip per route, `W50-PLAN.md` §3.4 as amended on
  2026-10-07, option A).
- **The instruments still see the widgets.** One eager seam: each wrapper reads a context its
  slice exports, and only `web/tests/unit/screens/harness.ts` provides it, with the widgets it
  imports itself. The census reads **80 screens / 150 / 150 pairs** at the head, exactly the base
  (§2.4); the new guard holds that floor and finds each widget in the census markup.
- **A guest gets a real `307`.** The four segment `loading.tsx` files are deleted (the
  integrator's ruling 1 at the `W50-REGISTRY-01` merge). On the lane stand all 18 `session`
  screens answer `307` with `Location: /login?next=…`; on the base the same command found nine
  of them answering `200` with no `Location` (§2.7).
- `CATEGORY_LABELS` moved to `@/entities/expert-decision`; the false `/projects` subtitle
  «Одна учётная запись на эту установку. Ролей и разделения на организации пока нет.» is gone,
  with no replacement claim.
- New guard `web/tests/guards/lazy-boundary.guard.test.ts` (24 tests); nine mutations, each red
  (§2.6).

**Who did what.** The lane was executed on 2026-10-06 by a subagent of the W50 executor session
of that day; that session and its subagent ended at the host's session restart on 2026-10-07.
Everything in §2.1–§2.7 was measured by that subagent on `d0d71ad` and `96a1653` and is quoted
here from its saved artefacts (`/root/w50lazy-logs/`, `/root/w50lazy-stand/`,
`/root/w50lazy-mut-logs/`) and its transcript; the code did not change after those
measurements. The gate (§2.8), this report and the cleanup (§2.10) are the successor executor
session's.

**The stop and its ruling.** The lane stopped on `W50-PLAN.md` §7 ("any measured route whose
first-load JS grows is a stop") with the exact-byte table of §2.5 and options A/B/C. The owner
chose **A by direct poll on 2026-10-07**; `W50-PLAN.md` §3.4 and §7 on `integration/w50` @
`23c25c0` now read: the five target routes fall, and no other route grows by more than the
measured fixed cost of the async-chunk runtime, at most 1.5 kB gzip per route, with the
exact-byte table in this report. `d0d71ad` passes it unchanged.

## 1. Changed files

`git diff --name-only 96a1653..d0d71ad` (27 paths; this report adds the 28th,
`docs/program/W50-LAZY-01.md`):

```
web/src/_pages/dashboard/index.ts
web/src/_pages/dashboard/ui/dashboard-page.tsx
web/src/_pages/dashboard/ui/lazy-dashboard.tsx
web/src/_pages/knowledge-base/index.ts
web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx
web/src/_pages/knowledge-base/ui/lazy-knowledge-base.tsx
web/src/_pages/projects/ui/projects-page.tsx
web/src/_pages/review/index.ts
web/src/_pages/review/ui/lazy-evidence-viewer.tsx
web/src/_pages/review/ui/review-page.tsx
web/src/_pages/run/index.ts
web/src/_pages/run/ui/lazy-run-progress.tsx
web/src/_pages/run/ui/run-page.tsx
web/src/_pages/stage-comparison/index.ts
web/src/_pages/stage-comparison/ui/lazy-stage-comparison.tsx
web/src/_pages/stage-comparison/ui/stage-comparison-page.tsx
web/src/app/dashboard/loading.tsx
web/src/app/knowledge-base/loading.tsx
web/src/app/projects/[project_uid]/loading.tsx
web/src/app/projects/loading.tsx
web/src/entities/expert-decision/index.ts
web/src/entities/expert-decision/model/category-labels.ts
web/src/widgets/knowledge-base/index.ts
web/src/widgets/knowledge-base/ui/knowledge-base.tsx
web/tests/guards/lazy-boundary.guard.test.ts
web/tests/guards/screen-guard.guard.test.ts
web/tests/unit/screens/harness.ts
```

The four `web/src/app/**/loading.tsx` are deletions (`git diff --name-status 96a1653 d0d71ad --
web/src/app` prints `D` for each and nothing else). Every path is inside the grant: the task
file's allowed paths at `96a1653`, widened by the integrator's ruling 1 at the `W50-REGISTRY-01`
merge (delete the four segment files) and by the integrator's grant of 2026-10-06 recorded on
`integration/w50` in `b0a1a4e` (`screen-guard.guard.test.ts`: only delete the `LOADING` map at
lines 57–61, its `it.each` case at lines 410–414, and drop "and loading" from the `describe` title
at line 391 — exactly the three hunks of this diff). Checked mechanically:

```
git diff --name-only 96a1653 d0d71ad | grep -v -E '^(web/src/_pages/(dashboard|knowledge-base|projects|review|run|stage-comparison)/|web/src/app/(projects|projects/\[project_uid\]|dashboard|knowledge-base)/loading\.tsx$|web/src/widgets/knowledge-base/|web/src/entities/expert-decision/|web/tests/unit/screens/(cold-load\.test|harness)\.ts$|web/tests/guards/(lazy-boundary|screen-guard)\.guard\.test\.ts$|docs/program/W50-LAZY-01\.md$)'
```

prints nothing. `web/tests/unit/screens/cold-load.test.ts` was granted and is unchanged: the seam
lives in `harness.ts`, through which it already renders. `git status --porcelain -uall` is empty
(§2.9).

## 2. Checks and their results

### 2.1 The premise, re-measured at the base

```
git grep -n -E "from '@/widgets/(evidence-viewer|stage-comparison|run-progress|knowledge-base|dashboard)'" 96a1653 -- web/src/_pages
96a1653:web/src/_pages/dashboard/ui/dashboard-page.tsx:18:import { Dashboard } from '@/widgets/dashboard';
96a1653:web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx:31:import { CATEGORY_LABELS, KnowledgeBase } from '@/widgets/knowledge-base';
96a1653:web/src/_pages/review/ui/review-page.tsx:49:import { EvidenceViewer } from '@/widgets/evidence-viewer';
96a1653:web/src/_pages/run/ui/run-page.tsx:15:import { RunProgress } from '@/widgets/run-progress';
96a1653:web/src/_pages/stage-comparison/ui/stage-comparison-page.tsx:37:import { StageComparison } from '@/widgets/stage-comparison';

git grep -n -E 'CATEGORY_LABELS|Ролей и разделения' 96a1653 -- web/src
96a1653:web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx:31:import { CATEGORY_LABELS, KnowledgeBase } from '@/widgets/knowledge-base';
96a1653:web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx:60:  ...CATEGORY_LABELS,
96a1653:web/src/_pages/projects/ui/projects-page.tsx:18:      subtitle="Одна учётная запись на эту установку. Ролей и разделения на организации пока нет."
96a1653:web/src/widgets/knowledge-base/index.ts:4:export { CATEGORY_LABELS, KnowledgeBase } from './ui/knowledge-base';
96a1653:web/src/widgets/knowledge-base/ui/knowledge-base.tsx:49:export const CATEGORY_LABELS: Readonly<Record<FindingCategory, string>> = {
96a1653:web/src/widgets/knowledge-base/ui/knowledge-base.tsx:121:              <span className="am-kb__category">{CATEGORY_LABELS[record.category]}</span>

git ls-tree -r --name-only 96a1653 -- web/src/app | grep -E '/loading\.tsx$'
web/src/app/dashboard/loading.tsx
web/src/app/knowledge-base/loading.tsx
web/src/app/projects/[project_uid]/loading.tsx
web/src/app/projects/loading.tsx

git grep -n -E "loading'\)|loading\.tsx" 96a1653 -- web/tests
96a1653:web/tests/guards/screen-guard.guard.test.ts:58:  projects: (await import('@/app/projects/loading')).default,
96a1653:web/tests/guards/screen-guard.guard.test.ts:59:  'projects/[project_uid]': (await import('@/app/projects/[project_uid]/loading')).default,
96a1653:web/tests/guards/screen-guard.guard.test.ts:60:  dashboard: (await import('@/app/dashboard/loading')).default,
96a1653:web/tests/guards/screen-guard.guard.test.ts:61:  'knowledge-base': (await import('@/app/knowledge-base/loading')).default,
96a1653:web/tests/guards/screen-guard.guard.test.ts:410:  it.each(Object.entries(LOADING))('%s/loading.tsx renders the typed loading state', (_segment, Loading) => {
96a1653:web/tests/unit/projects/upload-failure.test.ts:102:      expect(failure.title.toLowerCase()).not.toContain('uploading');
```

The five static imports and the two label lines are the task file's P-01 and P-02, unchanged by
`W50-REGISTRY-01`. The last command is why the lane stopped for a grant before deleting the four
files: `screen-guard.guard.test.ts` imported them at top level, so their deletion turned the whole
file red at import; the integrator granted the three-hunk edit (§1).

### 2.2 The seam, and why this one

The plan's example — each wrapper module also exports the eager component — would put a static
import of the widget in a `_pages/**` module, which contradicts guard (a) and may keep the widget
in the page's chunk (the task file's own note). The lane took the alternative the task file
names:

- each wrapper (`_pages/<slice>/ui/lazy-*.tsx`, `'use client'`) holds **no** static import of its
  widget: `dynamic(() => import('@/widgets/<w>').then((m) => m.<W>), { loading: () =>
  <LoadingState /> })`, its props type inferred from the loader;
- each wrapper exports a context, `<W>EagerSeam = createContext<ComponentType<Props> | null>(null)`,
  re-exported from the slice's `index.ts`; the wrapper renders the component found there, or the
  lazy chunk when it is `null`;
- `harness.ts` imports the five eager widgets itself and wraps every `renderWith` (hence every
  `renderScreen`) in the five providers. Nothing under `web/src` provides a seam, so in the
  product the context is always `null` and the lazy branch is the only one taken.

`<LoadingState />` carries no `what=` on purpose: the loaded widget then shows its own
`Загрузка: …` sentence while its query runs, and a branch label here would also need an
`UNREACHABLE_IN_ONE_PASS` entry in `rendered-language.guard.test.ts`, a forbidden file.

### 2.3 Frontend suite, lint, typecheck, whitespace

On the worktree at `d0d71ad`'s tree, before the commit (`/root/w50lazy-logs/vitest-1.log`):

```
npm --prefix web test -- --run          exit=0
 Test Files  92 passed (92)
      Tests  1419 passed (1419)
npm --prefix web run typecheck          exit=0
npm --prefix web run lint -- --quiet    exit=0
git diff --cached --check               exit=0
```

The base is 91 files / 1,399 tests (`W50-REGISTRY-01`'s head, which `96a1653` carries unchanged
in `web/`). 1,399 − 4 (the `LOADING` cases removed from `screen-guard.guard.test.ts`) + 24 (the
new guard) = 1,419. `git diff --check 96a1653 d0d71ad` is clean.

### 2.4 The census baseline, and the probe that measured it

The guard's literal `BASELINE = { screens: 80, pairsLight: 150, pairsDark: 150 }` was measured
in a disposable `git clone --shared` of the repository at `96a1653` (`/root/w50lazy-base`,
`web/node_modules` symlinked to the worktree's) by copying the probe below into
`web/tests/guards/`, running it, and deleting it:

```
npm --prefix web test -- --run tests/guards/census-counts.probe.test.ts
CENSUS screens=80 pairs.light=150 pairs.dark=150
 Test Files  1 passed (1)
      Tests  1 passed (1)
```

The same probe on the lane tree with the seam working printed the same line,
`CENSUS screens=80 pairs.light=150 pairs.dark=150`; with the seam switched off (M2, §2.6) the
light palette measures 147. The probe, whole (`/root/w50lazy-logs/census-counts.probe.test.ts`;
never committed):

```ts
/**
 * W50-LAZY-01 baseline probe: the census' screen count and measured pair count per palette,
 * computed exactly as `censusCounts()` in `tests/guards/lazy-boundary.guard.test.ts` does.
 * Copied into `web/tests/` of a tree, run, and deleted; never committed.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { it } from 'vitest';

import { census, palette, parseRules } from '../unit/styles/contrast';
import type { Rule } from '../unit/styles/contrast';
import { screens } from '../unit/styles/screens';

const MODULE_EXPORTS = import.meta.glob('../../src/**/*.module.css', { eager: true }) as Record<
  string,
  { readonly default: Record<string, string> }
>;

function censusRules(): Rule[] {
  const globals = readFileSync(fileURLToPath(new URL('../../src/app/globals.css', import.meta.url)), 'utf8');
  const modules = Object.keys(MODULE_EXPORTS)
    .sort()
    .map((relative) => {
      const scope = (MODULE_EXPORTS[relative] as { readonly default: Record<string, string> }).default;
      const css = readFileSync(fileURLToPath(new URL(relative, import.meta.url)), 'utf8');
      return parseRules(
        css.replace(/\.([a-zA-Z_][A-Za-z0-9_-]*)/g, (_m, name: string) => `.${scope[name]}`),
        relative,
      );
    })
    .flat();
  return [...parseRules(globals, 'globals.css'), ...modules];
}

it('prints the census counts', () => {
  const rendered = screens();
  const rules = censusRules();
  const globals = readFileSync(fileURLToPath(new URL('../../src/app/globals.css', import.meta.url)), 'utf8');
  const light = census(rendered, rules, palette(globals, 'light')).size;
  const dark = census(rendered, rules, palette(globals, 'dark')).size;
  console.log(`CENSUS screens=${rendered.length} pairs.light=${light} pairs.dark=${dark}`);
});
```

A PAIR is the census' own key (kind, foreground, background, state, pseudo), not a site: the
site count would fall from the `/projects` subtitle removal alone, which is not a loss of
coverage.

### 2.5 `next build`: the route tables, and the exact bytes

**The freeze table.** `docs/program/W50-FREEZE-01.md` records none, verbatim: "The `next build`
route table (first-load JS per route) is **not** measured here: a production build under the
present host load would measure the load. `W50-LAZY-01` compares against its own base, the
Stage-A merge, measured on that lane before any change". `W50-REGISTRY-01.md` §2.5 has the first
reading with the six new routes (on `17742cd`, label `w50reg`).

**Before, on the worktree at `96a1653`**, before any change
(`NEXT_PUBLIC_API_BASE_URL=/bff/v1 NEXT_PUBLIC_INSTANCE_LABEL=w50lazy npm --prefix web run build`,
exit 0, `/root/w50lazy-logs/build-before-96a1653.log`):

```
Route (app)                                                       Size  First Load JS
┌ ƒ /                                                            201 B         111 kB
├ ƒ /_not-found                                                  127 B         103 kB
├ ƒ /403                                                         578 B         123 kB
├ ƒ /account                                                     201 B         111 kB
├ ƒ /account/password                                            184 B         115 kB
├ ƒ /analysis-settings                                           201 B         111 kB
├ ƒ /bff/v1/[...path]                                            127 B         103 kB
├ ƒ /blocks                                                    2.11 kB         135 kB
├ ƒ /dashboard                                                 4.23 kB         143 kB
├ ƒ /knowledge-base                                            2.76 kB         129 kB
├ ƒ /login                                                       201 B         111 kB
├ ƒ /logs                                                        201 B         111 kB
├ ƒ /norms                                                       201 B         111 kB
├ ƒ /optimisation                                                201 B         111 kB
├ ƒ /projects                                                  3.51 kB         133 kB
├ ƒ /projects/[project_uid]                                    5.71 kB         139 kB
├ ƒ /projects/[project_uid]/documents/[document_uid]           1.39 kB         135 kB
├ ƒ /projects/[project_uid]/runs/[run_id]                      3.76 kB         139 kB
├ ƒ /projects/[project_uid]/runs/[run_id]/review               9.61 kB         145 kB
├ ƒ /projects/[project_uid]/versions/[version_uid]             4.14 kB         146 kB
├ ƒ /projects/[project_uid]/versions/[version_uid]/comparison  3.77 kB         146 kB
├ ƒ /queue                                                       201 B         111 kB
├ ƒ /section-optimisation                                        201 B         111 kB
└ ƒ /workers                                                     201 B         111 kB
+ First Load JS shared by all                                   103 kB
```

**After, at `d0d71ad`, built in the same directory as the base** (the clone `/root/w50lazy-base`,
checked out at `96a1653`, built, then at `d0d71ad`, `rm -rf web/.next`, built again — same
command, both exit 0, `build-base-clone.log` and `build-clone-d0d71ad.log`):

```
Route (app)                                                       Size  First Load JS
┌ ƒ /                                                            202 B         112 kB
├ ƒ /_not-found                                                  132 B         103 kB
├ ƒ /403                                                         581 B         124 kB
├ ƒ /account                                                     202 B         112 kB
├ ƒ /account/password                                            188 B         115 kB
├ ƒ /analysis-settings                                           202 B         112 kB
├ ƒ /bff/v1/[...path]                                            132 B         103 kB
├ ƒ /blocks                                                    2.11 kB         136 kB
├ ƒ /dashboard                                                 1.67 kB         118 kB
├ ƒ /knowledge-base                                            3.06 kB         127 kB
├ ƒ /login                                                       202 B         112 kB
├ ƒ /logs                                                        202 B         112 kB
├ ƒ /norms                                                       202 B         112 kB
├ ƒ /optimisation                                                202 B         112 kB
├ ƒ /projects                                                  3.45 kB         134 kB
├ ƒ /projects/[project_uid]                                    5.72 kB         140 kB
├ ƒ /projects/[project_uid]/documents/[document_uid]            1.4 kB         135 kB
├ ƒ /projects/[project_uid]/runs/[run_id]                      4.11 kB         132 kB
├ ƒ /projects/[project_uid]/runs/[run_id]/review                 12 kB         147 kB
├ ƒ /projects/[project_uid]/versions/[version_uid]             6.23 kB         147 kB
├ ƒ /projects/[project_uid]/versions/[version_uid]/comparison  2.04 kB         136 kB
├ ƒ /queue                                                       202 B         112 kB
├ ƒ /section-optimisation                                        202 B         112 kB
└ ƒ /workers                                                     202 B         112 kB
+ First Load JS shared by all                                   103 kB
```

**The rounded table is not precise enough to judge a ±1 kB bound**: the base built in the worktree
read `/knowledge-base 129 kB` and the same commit built in the clone `130 kB`. So the comparison
is made in exact bytes: `/root/w50lazy-logs/first-load.mjs <web dir>` sums, for each app route,
the gzip-9 size of every `.js` file its entry lists in `.next/app-build-manifest.json` — the
quantity `next build` prints as "First Load JS". Both builds in the one clone directory
(`fl-base-clone.tsv`, `fl-clone-d0d71ad.tsv`):

| route | base `96a1653` | head `d0d71ad` | Δ bytes |
|---|---:|---:|---:|
| `/dashboard` | 142,709 | 117,563 | **−25,146** |
| `/projects/[project_uid]/versions/[version_uid]/comparison` | 145,965 | 136,099 | **−9,866** |
| `/projects/[project_uid]/runs/[run_id]` | 139,414 | 131,639 | **−7,775** |
| `/knowledge-base` | 129,559 | 127,207 | **−2,352** |
| `/projects/[project_uid]/runs/[run_id]/review` | 145,266 | 146,636 | +1,370 |
| `/projects/[project_uid]/versions/[version_uid]` | 146,339 | 147,372 | +1,033 |
| `/403` | 123,383 | 124,113 | +730 |
| `/account/password` | 114,737 | 115,467 | +730 |
| `/_not-found` | 102,656 | 103,384 | +728 |
| `/bff/v1/[...path]` (route) | 102,656 | 103,384 | +728 |
| `/projects/[project_uid]/documents/[document_uid]` | 134,735 | 135,462 | +727 |
| `/`, `/account`, `/analysis-settings`, `/login`, `/logs`, `/norms`, `/optimisation`, `/queue`, `/section-optimisation`, `/workers` | 111,376 | 112,102 | +726 |
| `/blocks` | 135,450 | 136,176 | +726 |
| `/projects/[project_uid]` | 139,055 | 139,781 | +726 |
| `/projects` | 133,164 | 133,797 | +633 |

Against the amended bound: the four target routes that carry their widget on first load fall,
together by **45,139 bytes**; the review route, whose evidence viewer is mounted only once a
finding is open, is the largest growth at **+1,370 ≤ 1,536**; every route is inside 1.5 kB.

**Why every route grows by ~726 bytes.** The webpack runtime chunk every route loads grows from
1,718 to 2,443 gzip bytes (`node /root/w50lazy-logs/chunks.mjs <web dir> /page` lists `/`'s
chunks: `webpack-c94daa69fe02cd27.js 1718` → `webpack-de2abdf5363a799b.js 2443`; the other five
move by at most 34 bytes). Before this task the client bundle had no async chunk, so webpack
emitted no chunk-id → filename map; the head's runtime has it
(`r.u=e=>2619===e?"static/chunks/2619-3c9e02e22d10480a.js":3455===e?…`). Any `import()` adds it
— `next/dynamic` or `React.lazy` alike — so "no route grows" was unsatisfiable by any lazy
loading, which is what the owner's amendment records.

**Above that fixed cost:** the review route's +1,370 also carries the `next/dynamic` runtime
(`LoadableComponent`, `BailoutToCSR`, `PreloadChunks`), which webpack grouped into one chunk with
`useMutation` (`313-0b2e955bc5e3c205.js`, 2,974 gzip bytes); the version page did not change, and
its +1,033 is webpack redistributing shared modules among chunks (bundler configuration is a
non-goal). The widgets' own async chunks (gzip): evidence viewer 1,676, run progress 3,369,
dashboard 5,927, knowledge base 1,292, stage comparison 5,408.

**Variant B, measured and not taken.** With the evidence viewer left eager (built exit 0 in the
same clone, `fl-clone-v2.tsv`): review +896, version +1,015, others ≈ +708, the four wins kept
(−25,164 / −9,884 / −7,793 / −2,370). The owner chose A, so the five-widget set of §3.4 stands.

### 2.6 Mutations, each red

A disposable `git clone --shared` at `d0d71ad`, `/root/w50lazy-mut` (`web/node_modules`
symlinked to the worktree's), driven by `/root/w50lazy-mut-logs/run.sh <id> <vitest files>`: apply
ONE mutation with `mutate.py <id>` (every replacement must match exactly once), run the named
files, `git checkout -- . && git clean -fdq -e web/node_modules`, and require an empty status
(`restored clean` after every case). Unmutated baseline over the four files involved
(`lazy-boundary`, `contrast`, `rendered-language`, `screen-guard`): `Test Files 4 passed (4)`,
`Tests 96 passed (96)`. Logs: `/root/w50lazy-mut-logs/<id>.log`.

| id | mutation | files run | red (verbatim) |
|---|---|---|---|
| M1 *(required)* | a static `import { Dashboard } from '@/widgets/dashboard'` in `dashboard-page.tsx`, rendered in place of the wrapper | lazy-boundary | `Tests 2 failed \| 22 passed (24)`: `(a) … finds a static edge to none of them` — `a _pages module imports a lazy widget statically, so the widget is back in that page's first-load chunk and its next/dynamic wrapper is decoration (W50-PLAN.md §3.4)…: expected [ Array(1) ] to deeply equal []`, the received entry `"web/src/_pages/dashboard/ui/dashboard-page.tsx:19  import { Dashboard } from '@/widgets/dashboard';  (widgets/dashboard)"`; and `the product path…` — `dashboard: no fallback where the widget goes` |
| M1b | `import type { EvidenceViewerProps } from '@/widgets/evidence-viewer'` in `lazy-evidence-viewer.tsx` | lazy-boundary | `Tests 1 failed \| 23 passed (24)`: (a), received `"web/src/_pages/review/ui/lazy-evidence-viewer.tsx:22  import type { EvidenceViewerProps } from '@/widgets/evidence-viewer';  (widgets/evidence-viewer)"`. The walk's coverage of all five is its own case: `reaches each of the five through exactly one import()` |
| M2 *(required)* | the seam switched off in `harness.ts` (`renderWith` renders without `withEagerWidgets`) | lazy-boundary, contrast, rendered-language | `Tests 8 failed \| 58 passed (66)`: `(b) holds its screen count and its measured pair count at or above the baseline` — `the census measures fewer pairs in the light palette: expected 147 to be greater than or equal to 150`; all five `(c) <widget> is in the census markup eagerly`, e.g. `ReviewPage loaded does not draw evidence-viewer: … (the eager seam is not reaching it): expected '<html><body><section class="am-page">…' to contain 'class="am-evidence"'`; and two `rendered-language` cases (`renders every attribute it claims to read…`, `renders every member of every translated schema…`). **`contrast.test.ts` stayed green**: its own floor is 140 pairs, so 147 passes it — (b) is the tighter check |
| M2b | one widget's seam provided with `null` (`{ value: Dashboard }` → `{ value: null }`) | lazy-boundary, contrast | `Tests 1 failed \| 43 passed (44)`: `(c) dashboard …` — `dashboard cold does not draw dashboard: … expected '<html><body><section class="am-page">…' to contain '>Загрузка: сводку по системе…<'`. The pair count holds at 150 here (the dashboard draws no pair another screen does not), so only (c) catches it — which is why (c) exists |
| M3 *(required)* | an untyped fallback: `{ loading: () => <p>Loading…</p> }` in `lazy-run-progress.tsx` | lazy-boundary, rendered-language | `Tests 2 failed \| 44 passed (46)`: `the run-progress wrapper renders a typed loading state, in Russian, through the harness` — `expected '<p>Loading…</p>' to match /^<div class="am-state am-state--neutr…/`; `the product path…` — `run-progress: no fallback where the widget goes`. `rendered-language` stayed green: with the seam provided it never renders a wrapper's fallback, which is why the boundary guard judges the fallbacks itself (the check moved out of `screen-guard`, §1) |
| M3b | a typed state with English words: `<LoadingState what="the comparison" />` in `lazy-stage-comparison.tsx` | lazy-boundary, rendered-language | `Tests 4 failed \| 42 passed (46)`: `the stage-comparison wrapper renders a typed loading state, in Russian…` — `the loading state carries a Latin letter: expected 'Загрузка: the comparison…' not to match /[A-Za-z]/`; `the product path…`; and the existing `rendered-language` `renders every one of them, and NAMES the branch it does not reach` and `D-82: no branch label carries English, reachable or not` |
| M4 *(required)* | `web/src/app/dashboard/loading.tsx` restored (`<LoadingState />`) | lazy-boundary | `Tests 1 failed \| 23 passed (24)`: `no loading.tsx sits at or above a page whose registry access is not public > finds none` — `a segment loading boundary wraps a guarded page in Suspense, so requireScreen's redirect travels inside a 200 stream and a guest gets no 307 and no Location…: expected [ Array(1) ] to deeply equal []`. **And on a served build** (§2.7): `GET /dashboard 200 (no Location)` |
| M5 | production mounts the seam: `<DashboardEagerSeam.Provider value={null}>` around `<LazyDashboard />` in `dashboard-page.tsx` | lazy-boundary | `Tests 3 failed \| 21 passed (24)`: `is never mounted under web/src` — `a production module provides the eager seam, so the product renders the eager widget and the bundle split is gone from that render path: expected [ Array(1) ] to deeply equal []`; `is named by exactly the five wrappers and their five slice indexes` — `expected [ …(11) ] to deeply equal [ …(10) ]`; `(c) dashboard …` (the inner `null` provider hides the harness' widget) |

### 2.7 The lane stand: the guest `307`, two live journeys, and M4 served

**Stand.** Lane `gate-w50lazy`, worktree `.local/worktrees/w50-lazy`, `.env` copied from the
`w49-int` worktree with exactly the lane's values changed (`FOUNDATION_INSTANCE=gate-w50lazy`,
`POSTGRES_PORT=56670`, `S3_API_PORT=60270`, `S3_CONSOLE_PORT=60271`,
`POSTGRES_DB=auditmanager_w50lazy`, `S3_BUCKET=auditmanager-w50lazy`, both sides of
`DATABASE_URL` / `S3_ENDPOINT_URL`). Ports checked free with `ss -ltn` immediately before use:
`56670`, `60270`, `60271` (the lane's `PORT_REGISTRY.md` row), and the stand's own `56671` (API),
`56672` (health), `56673` (`next start`, head), `56675` (`next start`, base build; `56674` was
briefly held by another process and not used), `56676` (`next start`, M4 build). `make up` and
`make migrate` exit 0 (head `0015_accounts_roles_registration`). API:
`PYTHONPATH=src .venv/bin/python infra/deploy/serve.py` with the `.env` values,
`AUDITMANAGER_PROVIDER_MODE=recorded`, a disposable `AUDITMANAGER_API_TOKEN` in a `0600` file
outside the tree, bound to `127.0.0.1` (PID 3861244, cwd the worktree). Web: `next start -p 56673
-H 127.0.0.1` over the `d0d71ad` build of §2.5 (PID 3861922, cwd `…/w50-lazy/web`).

**The guest `307`.** `/root/w50lazy-stand/guest-curl.sh <origin>`: one cold `curl -sI` per
registered address — the 22 rows read from `SCREEN_REGISTRY` — with no cookie, dynamic segments
filled with well-formed opaque identifiers (`prj_`/`doc_`/`ver_`/`run_` + one ULID). Head,
`http://127.0.0.1:56673` (`guest-curl-d0d71ad.txt`), verbatim:

```
GET /                                                      session                     307 /login?next=%2F
GET /projects                                              session                     307 /login?next=%2Fprojects
GET /dashboard                                             session                     307 /login?next=%2Fdashboard
GET /section-optimisation                                  session                     307 /login?next=%2Fsection-optimisation
GET /projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B               session                     307 /login?next=%2Fprojects%2Fprj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B
GET /projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/documents/doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B session                     307 /login?next=%2Fprojects%2Fprj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B%2Fdocuments%2Fdoc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B
GET /projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/versions/ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B session                     307 /login?next=%2Fprojects%2Fprj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B%2Fversions%2Fver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B
GET /projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/versions/ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/comparison session                     307 /login?next=%2Fprojects%2Fprj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B%2Fversions%2Fver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B%2Fcomparison
GET /projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/runs/run_01J9ZQ8K7NHVXW3T2R5M6P4Q8B session                     307 /login?next=%2Fprojects%2Fprj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B%2Fruns%2Frun_01J9ZQ8K7NHVXW3T2R5M6P4Q8B
GET /projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/runs/run_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/review session                     307 /login?next=%2Fprojects%2Fprj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B%2Fruns%2Frun_01J9ZQ8K7NHVXW3T2R5M6P4Q8B%2Freview
GET /knowledge-base                                        session                     307 /login?next=%2Fknowledge-base
GET /blocks                                                session                     307 /login?next=%2Fblocks
GET /norms                                                 session                     307 /login?next=%2Fnorms
GET /logs                                                  session                     307 /login?next=%2Flogs
GET /workers                                               session                     307 /login?next=%2Fworkers
GET /analysis-settings                                     session                     307 /login?next=%2Fanalysis-settings
GET /queue                                                 session                     307 /login?next=%2Fqueue
GET /optimisation                                          session                     307 /login?next=%2Foptimisation
GET /login                                                 public                      200 (no Location)
GET /account                                               open-to-default-credential  307 /login?next=%2Faccount
GET /account/password                                      open-to-default-credential  307 /login?next=%2Faccount%2Fpassword
GET /403                                                   public                      200 (no Location)
```

All 18 `session` screens: `307`, `Location: /login?next=<the address>`; the two
`open-to-default-credential` screens: `307`; the two `public`: `200`. Also on the head: `GET
/projects?x=1` → `307 /login?next=%2Fprojects%3Fx%3D1`, and a full `GET /dashboard` (not only
`HEAD`) → `HTTP/1.1 307 Temporary Redirect`, `location: /login?next=%2Fdashboard`.

**The same command on the base build** (`96a1653`, served on `56675` against the same API,
`guest-curl-base-96a1653.txt`), the rows that differ:

```
GET /projects                                              session                     200 (no Location)
GET /dashboard                                             session                     200 (no Location)
GET /projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B               session                     200 (no Location)
GET /projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/documents/doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B session                     200 (no Location)
GET /projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/versions/ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B session                     200 (no Location)
GET /projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/versions/ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/comparison session                     200 (no Location)
GET /projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/runs/run_01J9ZQ8K7NHVXW3T2R5M6P4Q8B session                     200 (no Location)
GET /projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/runs/run_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/review session                     200 (no Location)
GET /knowledge-base                                        session                     200 (no Location)
```

Nine addresses — every one under the four deleted segment files — answered `200` with no
`Location` on the base (`grep -c ' session .* 200 ' guest-curl-base-96a1653.txt` → `9`; the
lane's interim hand-back said "eight", a miscount the file corrects). The other thirteen rows
are identical to the head's.

**M4 served.** The M4 clone (`d0d71ad` + a restored `app/dashboard/loading.tsx`) built exit 0
(`/root/w50lazy-mut-logs/M4-build.log`) and served on `56676` against the same API
(`guest-curl-M4-mutant.txt`):

```
GET /dashboard       200 (no Location)
GET /projects        307 /login?next=%2Fprojects
GET /knowledge-base  307 /login?next=%2Fknowledge-base
```

and the `/dashboard` body carried `__next-page-redirect" http-equiv="refresh"
content="1;url=/login?next=%2Fdashboard"` and `NEXT_REDIRECT;replace;/login?next=%2Fdashboard;307;`
— the redirect inside a `200` stream that the guard's last rule now refuses.

**Account for the journeys.** The migration's seeded `admin`, through the API: `POST /auth/token
200` (default credential), `POST /auth/password 200`, `PATCH /me 200` (e-mail login, names) →
`profile_complete: true`, roles `admin`, `expert`, label «Проверкина А. С.». The password lives in
a `0600` file outside the tree; no credential appears here.

**Journey on the head**, `E2E_PC01_CHROME=<chrome-for-testing 154.0.8037.92>
E2E_PC01_LOGIN=<account> E2E_PC01_PASSWORD=<file> npm --prefix web run e2e:pc01 -- --origin
http://127.0.0.1:56673 --phase all --out /root/w50lazy-stand/journey-d0d71ad`, exit 0, verbatim:

```
sign-in: ok at /login -- carrying 'am_session' (HttpOnly=true, SameSite=Strict) into every cold browser

write half: 3 step(s), fixture fixtures/synthetic/ar/ar_baseline.pdf

ok  create-project   api=3 {"project_uid":"prj_01M48Z9BSGZ2JNR36BE89XAQP1"}
ok  upload-document  api=4 {"project_uid":"prj_01M48Z9BSGZ2JNR36BE89XAQP1","version_uid":"ver_01M48ZA701WZ3G8T4Z112X3NHM"}
ok  start-run        api=5 {"project_uid":"prj_01M48Z9BSGZ2JNR36BE89XAQP1","run_id":"run_01M48ZB1H5HR0SMS3BT728ZBZC"} terminal=published in 1507ms/150000ms

ok  root           200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  projects       200  api=1 auth=0 console=0 jar=[am_session] w=780/780 {"project_uid":"prj_01M48Z9BSGZ2JNR36BE89XAQP1"}
ok  project        200  api=1 auth=0 console=0 jar=[am_session] w=765/780 {"document_uid":"doc_01M48ZA700QY06X57DRCWW6WBQ"}
ok  document       200  api=1 auth=0 console=0 jar=[am_session] w=780/780 {"version_uid":"ver_01M48ZA701WZ3G8T4Z112X3NHM"}
ok  version        200  api=2 auth=0 console=0 jar=[am_session] w=765/780 {"run_id":"run_01M48ZB1H5HR0SMS3BT728ZBZC"}
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
ok  forbidden      200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  account        200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  section-optimisation 200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  norms          200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  analysis-settings 200  api=0 auth=0 console=0 jar=[am_session] w=780/780
ok  queue          200  api=0 auth=0 console=0 jar=[am_session] w=780/780

envelope: /root/w50lazy-stand/journey-d0d71ad/journey.json
write steps checked: 3/3
routes checked: 22/22
e2e:pc01 OK
```

The envelope reads `routesDeclared: 22, routesChecked: 22, failures: []`.

**Journey on the base**, the same command against the base build on `56675`, `--out
/root/w50lazy-stand/journey-base-96a1653`: exit 0, `write steps checked: 3/3`,
`routes checked: 22/22`, `e2e:pc01 OK`, every row `auth=0 console=0`, the same widths
(`w=765/780` on the same routes).

**Observed API calls, base against head**, read from the two envelopes' `records[].exchanges`
per route, identifiers normalised to `<id>` because each run created its own project
(`/root/w50lazy-stand/journey-api-compare-normalised.txt`), verbatim:

```
same account                0 []
same analysis-settings      0 []
same blocks                 1 ['GET /bff/v1/projects']
same change-password        0 []
same comparison             1 ['GET /bff/v1/versions/ver_<id>/runs']
same dashboard              1 ['GET /bff/v1/dashboard']
same document               1 ['GET /bff/v1/documents/doc_<id>/versions']
same forbidden              0 []
same knowledge-base         1 ['GET /bff/v1/decisions']
same logs                   0 []
same norms                  0 []
same optimisation           0 []
same project                1 ['GET /bff/v1/projects/prj_<id>/documents']
same projects               1 ['GET /bff/v1/projects']
same queue                  0 []
same review                 5 ['GET /bff/v1/findings/fnd_<id>', 'GET /bff/v1/findings/fnd_<id>/decisions', 'GET /bff/v1/runs/run_<id>', 'GET /bff/v1/runs/run_<id>/findings', 'GET /bff/v1/versions/ver_<id>/content']
same root                   0 []
same run                    1 ['GET /bff/v1/runs/run_<id>']
same section-optimisation   0 []
same sign-in                0 []
same version                2 ['GET /bff/v1/versions/ver_<id>', 'GET /bff/v1/versions/ver_<id>/runs']
same workers                0 []
routes compared: 22; identical observed API calls (identifiers normalised): 22
```

No route's API calls moved, so the manifest's `expects_api` did not need to move for this task.
(Both journeys predate the `W50-HOME-01` merge: `root` makes no call on this base.)

**Teardown of the stand.** Before the gate: web PIDs 4125980 (M4, cwd `/root/w50lazy-mut/web`)
and 4009267 (base, cwd `/root/w50lazy-base/web`), then the API 3861244 and web 3861922 (cwd
re-confirmed with `readlink /proc/<pid>/cwd` before each `kill`); ports `56671`–`56676` closed;
`make down` exit 0; volumes `gate-w50lazy-postgres-data` and `gate-w50lazy-s3-data` removed by
exact name; network `gate-w50lazy-net` gone.

### 2.8 The full gate

Run once, from the worktree on a clean tree at `d0d71ad`, through the integrator's Stage-B
wrapper (the lock `/root/projects/PDF-Analysis/.local/w50-stage-b-gate.lock`, ≥ 3 GB available,
no other `make gate`), with one extra condition agreed with the integrator: it also waited until
the acceptance session's `make alpha-acceptance` (another worktree) had exited, so this gate's
load could not disturb release evidence. Output to `.local/worktrees/w50-lazy/.local/gate.log`:

```
gate start 2026-10-07T06:49:45Z head=d0d71ad635ca838cb5946052fe1009cce1c8d71d avail=5 load=15.69 14.95 9.30
```

Foundation `35 passed in 28.08s`; battery `3183 passed, 6 skipped, 4 warnings, 298 subtests
passed in 1180.49s (0:19:40)`; `eslint .` and `tsc --noEmit` with no output; frontend
`Test Files  92 passed (92)`, `Tests  1419 passed (1419)`; then, verbatim:

```
GATE OK: battery, foundation, frontend lint/typecheck/tests and whitespace all pass
gate end 2026-10-07T07:11:01Z
exit=0
```

The four warnings are one `starlette` `DeprecationWarning` (`anyio.abc.BlockingPortal`) and three
`SAWarning`s (`transaction already deassociated from connection`) in
`tests/integration/runs/harness.py`; this diff holds no Python file. The battery and foundation
counts equal `W50-SHELL-UI`'s and `W50-HOME-01`'s on the same base. `git status --porcelain -uall`
was empty before and after, and `HEAD` was `d0d71ad` throughout.

### 2.9 What the gate measured

The gate measured the code commit `d0d71ad`. The commit that adds this report changes
`docs/program/W50-LAZY-01.md` only (`git diff --name-only d0d71ad..HEAD` names that one file).
On the tree carrying this report, the battery's tests that read `docs/`, run the gate's way
(`.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q tests/contract/program
tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py
tests/contract/api_v1/test_openapi_conformance.py tests/contract/api_v1/test_finding_detail_composition.py
tests/contract/domain_p02/test_openapi_document.py tests/e2e/test_pc01_journey_conformance.py`):
`311 passed`. (`tests/checkpoint` and `tests/contract/test_cp00_candidate.py` also read `docs/`;
the gate quarantines them as CP-00 mechanics, and they are red with or without this file.)

### 2.10 Cleanup

After the gate: `make down` exit 0 (`FOUNDATION_INSTANCE=gate-w50lazy`; containers
`gate-w50lazy-{postgres,s3,s3-init}-1` and network `gate-w50lazy-net` removed); volumes
`gate-w50lazy-postgres-data` and `gate-w50lazy-s3-data` removed by exact name (`docker volume ls`
shows no `gate-w50lazy*`); the disposable clones `/root/w50lazy-base` and `/root/w50lazy-mut`
removed after confirming each was clean and its `web/node_modules` a symlink; the stand's token
and password files deleted, after confirming neither value appears in any kept artefact; ports
`56670`–`56679`, `60270`, `60271` free; no lane process left. Every process stopped in this lane
was stopped by PID after its cwd was confirmed (§2.7).

## 3. New and changed contracts

No file under `contracts/**`, `web/openapi/**` or `web/src/shared/api/generated/**` changed: the
surface is still 27 paths / 34 operations / 77 schemas, the error catalog 23, the migration head
`0015_accounts_roles_registration`. No dependency, no bundler configuration, no global CSS, no
registry row, no manifest entry, no query namespace. Internal seams:

- **`CATEGORY_LABELS`** is exported from `@/entities/expert-decision`
  (`model/category-labels.ts`); `@/widgets/knowledge-base` no longer exports it, and both the
  widget and `_pages/knowledge-base` import it from the entity. The values are unchanged.
- **Five eager seams**, exported from the page slices' public indexes:
  `DashboardEagerSeam` (`@/_pages/dashboard`), `KnowledgeBaseEagerSeam`
  (`@/_pages/knowledge-base`), `EvidenceViewerEagerSeam` (`@/_pages/review`),
  `RunProgressEagerSeam` (`@/_pages/run`), `StageComparisonEagerSeam`
  (`@/_pages/stage-comparison`) — React contexts of `ComponentType<widget props> | null`, default
  `null`. **Only `web/tests/unit/screens/harness.ts` may provide them**; the boundary guard reads
  every file under `web/src` that names one and fails on a mount.
- The five widgets' public APIs are unchanged; the pages reach them through
  `LazyDashboard`, `LazyKnowledgeBase`, `LazyEvidenceViewer`, `LazyRunProgress`,
  `LazyStageComparison`, module-private to their slices.
- `web/tests/guards/lazy-boundary.guard.test.ts` (new, 24 tests): (a) no `_pages/**` module has a
  static edge to the five widgets, read by parsing every `.ts`/`.tsx` under `_pages` with the
  TypeScript compiler (`import … from`, `import type`, a bare `import '…'`, `export … from`,
  `import x = require(…)`, a `require(…)` call, through `@/` or a relative path); each widget is
  reached by exactly one `import()`; (b) the census' screen count and pair counts per palette are
  at or above `BASELINE = { screens: 80, pairsLight: 150, pairsDark: 150 }`, with the command
  beside the literal; (c) each of the five widgets is in the census markup through its page;
  every wrapper's `loading` renders the typed `am-state--neutral` state with no Latin letter
  (`next/dynamic` is mocked in this file only); with the seam empty, each page draws its frame
  and the fallback where the widget goes; the seam is named only by the five wrappers and their
  indexes, never mounted under `web/src`, and provided by the harness once per widget; no
  `loading.tsx` sits at or above a `page.tsx` whose registry access is not `public`.
- `screen-guard.guard.test.ts` no longer checks segment loading boundaries (they no longer
  exist); the "typed loading state, in Russian" check lives in the boundary guard.

## 4. Risks and known limitations

1. **Every route pays the async-chunk runtime, about 726 gzip bytes.** It is the cost of any
   `import()` on this toolchain and is accepted by the owner's amendment (≤ 1.5 kB per route).
   The review route (+1,370) and the version page (+1,033) are the closest to the bound; a
   later lazy widget that pushes a route past it is a stop under §7 as amended.
2. **The tables were measured against the Stage-A base `96a1653`**, not against
   `integration/w50` with `W50-SHELL-UI` and `W50-HOME-01` merged. `W50-HOME-01` §2.5/§4.4
   records that `/` grows 111 → 133 kB and seven rows read +1 kB from its own change; read
   against a merged tree, those movements are HOME's, not lazy loading's. The script
   `/root/w50lazy-logs/first-load.mjs` re-measures any built tree in exact bytes.
3. **The census floor is the Stage-A count.** `W50-SHELL-UI` added census seeds (avatar,
   disclosure and menu states), so the merged tree counts more screens and pairs; guard (b)
   asserts "at or above" and stays green, but it would not notice the loss of SHELL-UI's own
   additions. Raising the literal to the merged count is a one-line change for whoever next owns
   that file (`W50-FIX` or `W50-SHELL-FRAME`).
4. **`contrast.test.ts`'s own floor (140 pairs) is looser than this guard's**: with the seam off
   it stays green at 147 (M2). The boundary guard is the instrument that catches a blind census.
5. **An instrument that renders pages without `renderWith`/`renderScreen` would see only the
   fallbacks.** Every instrument today goes through `harness.ts`; guard (c) catches it for the
   census only.
6. **The evidence viewer's chunk is fetched when a reviewer first opens a finding**; on a slow
   connection «Загрузка…» shows briefly where the viewer goes. The other four widgets are fetched
   with their pages.
7. **Two loading sentences in sequence.** The wrapper's fallback reads «Загрузка…»; the loaded
   widget then shows its own `Загрузка: …` while its query runs (§2.2).
8. **Not in the gate:** `next build` and the live journey (`D-108`) are measured on the lane
   stand only (§2.5, §2.7); the `307` is visible only to a served build.

## 5. Instructions to the integrator

- Merge `agent/w50-lazy-01` after `W50-SHELL-UI` and `W50-HOME-01` (plan §5). The paths are
  disjoint from both; the boundary guard walks `_pages/home` too, which imports none of the five
  widgets, and SHELL-UI's census seeds only raise the counts guard (b) reads.
- The integration gate on the merged tree is the measurement of record for the combination;
  this lane's gate (§2.8) measured `d0d71ad` alone.
- The grant for `screen-guard.guard.test.ts` lives on `integration/w50` in `b0a1a4e`, not on
  this branch; the owner's §3.4/§7 amendment is at `23c25c0`. Both are cited here and reach the
  merged tree from your side.
- Optional, for `W50-FIX` or `W50-SHELL-FRAME`: raise `BASELINE` in
  `lazy-boundary.guard.test.ts` to the merged census count (§4.3).
- Lane artefacts left on the host for the record: `/root/w50lazy-logs/` (build logs, TSVs,
  `first-load.mjs`, `chunks.mjs`, the census probe, the base build copy), `/root/w50lazy-stand/`
  (guest-curl outputs, both journey envelopes, the API comparison; the token and password files
  were deleted), `/root/w50lazy-mut-logs/`.

## 6. Forbidden hotspots untouched

`git diff --name-only 96a1653 d0d71ad | grep -E '^(contracts/|src/|web/src/shared/|web/src/_app/|web/package|web/FRONTEND_LOCK|web/vitest|web/next\.config|web/tests/unit/styles/|web/tests/guards/rendered-language|web/tests/unit/screens/route-screens|docs/program/(CURRENT_STATE|DEBT_REGISTER|OWNER_RULINGS|dispatch/PORT_REGISTRY))'`
prints nothing. Under `web/src/app/**` the only entries are the four granted deletions; no
`page.tsx`, `layout.tsx` or `globals.css`. No widget other than `knowledge-base` changed, and in
it only the `CATEGORY_LABELS` move (the declaration and its export removed, the import from the
entity added). No ref, tag, push, merge or worktree removal; no deployment or secret.
