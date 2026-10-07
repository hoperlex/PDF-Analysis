/**
 * `W50-LAZY-01`: five heavy widgets load lazily, and the instruments still see them.
 *
 * `W50-PLAN.md` §3.4 asks for two things at once and each needs its own check, because
 * each can be satisfied by breaking the other:
 *
 *   THE BUNDLE SPLITS      `widgets/evidence-viewer`, `stage-comparison`, `run-progress`,
 *                          `knowledge-base` and `dashboard` reach `_pages/**` only through a
 *                          `next/dynamic` wrapper. A single static import anywhere under
 *                          `_pages` keeps the widget in the page's first-load chunk and makes
 *                          the wrapper decoration, so the import graph is READ (parsed, every
 *                          spelling of a static edge, `import type` included) rather than
 *                          grepped for one spelling. The route table that proves the split
 *                          is in `docs/program/W50-LAZY-01.md`; `next build` is not a test.
 *
 *   THE INSTRUMENTS SEE    the contrast census, the language guards and the screen tests
 *                          render a page in one synchronous server pass, where a dynamic
 *                          import never resolves. Each wrapper therefore reads an EAGER SEAM
 *                          — a context its slice exports — that only
 *                          `tests/unit/screens/harness.ts` provides. This file holds that the
 *                          seam is provided there and nowhere under `web/src`, that the
 *                          census did not shrink below the count measured before the wrappers
 *                          existed, and that each widget is really in the census markup —
 *                          because a census that silently renders five loading states is
 *                          `D-88` in a new costume, and would stay green.
 *
 * And a third thing the integrator's ruling at the `W50-REGISTRY-01` merge added: a segment
 * `loading.tsx` above a guarded `page.tsx` turns `requireScreen`'s redirect into a `200`
 * with the redirect inside the stream. The four such files are deleted; the rule below keeps
 * any from returning above a screen that is not `public`. The `307` itself is measured on a
 * served build (`curl -sI`, in the report), because no node-side render can see an HTTP
 * status.
 *
 * `next/dynamic` is MOCKED in this file, and only here. The mock records what each wrapper
 * hands to `dynamic()` and renders the wrapper's own `loading` — which is what both of Next's
 * implementations render on a first server pass whose module has not resolved — so the
 * loading states are judged as the wrappers declare them, not as a copy of them. Everywhere
 * the seam is provided the mock is never reached.
 */

import { dirname, join, relative, resolve, sep } from 'node:path';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import ts from 'typescript';
import { createElement } from 'react';
import type { ComponentType, ReactElement, ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { SCREEN_REGISTRY } from '@/shared/config';
import { DashboardEagerSeam, DashboardPage } from '@/_pages/dashboard';
import { KnowledgeBaseEagerSeam, KnowledgeBasePage } from '@/_pages/knowledge-base';
// Imported for its wrapper's `dynamic()` call, which the cases below read; the review page
// itself is rendered by the census (`ReviewPage loaded`), not here.
import '@/_pages/review';
import { RunPage, RunProgressEagerSeam } from '@/_pages/run';
import { StageComparisonEagerSeam, StageComparisonPage } from '@/_pages/stage-comparison';
import { Dashboard } from '@/widgets/dashboard';
import { EvidenceViewer } from '@/widgets/evidence-viewer';
import { KnowledgeBase } from '@/widgets/knowledge-base';
import { RunProgress } from '@/widgets/run-progress';
import { StageComparison } from '@/widgets/stage-comparison';

import { WEB_ROOT, readText, repoRelative, walkFiles } from './lib/repo';
import { newClient, renderScreen } from '../unit/screens/harness';
import { routeAddresses } from '../unit/screens/route-screens';
import { census, palette, parseRules } from '../unit/styles/contrast';
import type { Rule } from '../unit/styles/contrast';
import { screens } from '../unit/styles/screens';
import { PROJECT_UID, RUN_ID, VERSION_UID } from '../unit/review/fixtures';

// ================================================================= next/dynamic, recorded

interface LoadingProps {
  readonly isLoading: boolean;
  readonly pastDelay: boolean;
  readonly error: Error | null;
}
interface DynamicCall {
  readonly loader: () => Promise<unknown>;
  readonly loading: ((props: LoadingProps) => ReactNode) | undefined;
}

const recorded = vi.hoisted(() => [] as DynamicCall[]);

vi.mock('next/dynamic', () => ({
  default: (loader: () => Promise<unknown>, options?: { loading?: (props: LoadingProps) => ReactNode }) => {
    const call: DynamicCall = { loader, loading: options?.loading };
    recorded.push(call);
    // A first server pass over a module that has not resolved: the declared fallback, or
    // nothing — which is what Next renders when a wrapper declares no `loading` at all.
    return function FirstPass(): ReactNode {
      return call.loading === undefined
        ? null
        : call.loading({ isLoading: true, pastDelay: false, error: null });
    };
  },
}));

// ======================================================================= the five widgets

const SRC = join(WEB_ROOT, 'src');
const PAGES = join(SRC, '_pages');

/**
 * The five, with what the census must show of each when the seam works.
 *
 * `screen` is a census entry that renders the widget THROUGH ITS PAGE (the census also
 * renders three of the widgets on their own, and those entries would stay green with the
 * seam gone). `marker` is something only the eager widget draws in that state: its own
 * query's loading sentence or its own root, never the wrapper's bare «Загрузка…».
 */
const WIDGETS = [
  {
    slice: 'dashboard',
    widget: Dashboard as ComponentType<never>,
    seam: 'DashboardEagerSeam',
    screen: 'dashboard cold',
    marker: '>Загрузка: сводку по системе…<',
  },
  {
    slice: 'knowledge-base',
    widget: KnowledgeBase as ComponentType<never>,
    seam: 'KnowledgeBaseEagerSeam',
    screen: 'knowledge-base cold',
    marker: '>Загрузка: базу знаний…<',
  },
  {
    slice: 'run-progress',
    widget: RunProgress as ComponentType<never>,
    seam: 'RunProgressEagerSeam',
    screen: 'run cold',
    marker: '>Загрузка: прогон…<',
  },
  {
    slice: 'evidence-viewer',
    widget: EvidenceViewer as ComponentType<never>,
    seam: 'EvidenceViewerEagerSeam',
    screen: 'ReviewPage loaded',
    marker: 'class="am-evidence"',
  },
  {
    slice: 'stage-comparison',
    widget: StageComparison as ComponentType<never>,
    seam: 'StageComparisonEagerSeam',
    screen: 'StageComparisonPage with two runs',
    marker: 'data-left-run=',
  },
] as const;

const LAZY_SLICES: ReadonlySet<string> = new Set(WIDGETS.map((entry) => entry.slice));

/** The wrapper's own fallback, as `<LoadingState />` renders it with no `what`. */
const BARE_FALLBACK = '>Загрузка…<';

// =================================================== (a) the import graph of `_pages/**`

/** The widget slice a module specifier resolves into, if it is one of the five. */
export function lazyWidgetOf(specifier: string, fromFile: string): string | null {
  let absolute: string;
  if (specifier.startsWith('@/')) absolute = join(SRC, specifier.slice(2));
  else if (specifier.startsWith('.')) absolute = resolve(dirname(fromFile), specifier);
  else return null;
  const inside = relative(join(SRC, 'widgets'), absolute);
  if (inside.startsWith('..') || inside === '') return null;
  const slice = inside.split(sep)[0] ?? '';
  return LAZY_SLICES.has(slice) ? slice : null;
}

export interface ImportEdge {
  readonly widget: string;
  readonly kind: 'static' | 'dynamic';
  readonly line: number;
  readonly text: string;
}

/**
 * Every edge from `source` into one of the five widgets, PARSED.
 *
 * Static: `import … from`, `import type … from`, a bare `import '…'`, `export … from`,
 * `import x = require('…')` and a `require('…')` call. Dynamic: an `import('…')`
 * expression, which is the one edge a wrapper is allowed. A type-only import is counted as
 * static on purpose: it carries no code into the chunk today, and the rule is simpler to
 * hold — and to read — as "no `_pages` module names these widgets except inside
 * `import()`" than as a list of exceptions.
 */
export function widgetEdges(source: string, fromFile: string): readonly ImportEdge[] {
  const file = ts.createSourceFile(fromFile, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const out: ImportEdge[] = [];
  const add = (node: ts.Node, specifier: ts.Node | undefined, kind: ImportEdge['kind']): void => {
    if (specifier === undefined || !ts.isStringLiteralLike(specifier)) return;
    const widget = lazyWidgetOf(specifier.text, fromFile);
    if (widget === null) return;
    const line = file.getLineAndCharacterOfPosition(node.getStart(file)).line + 1;
    out.push({ widget, kind, line, text: node.getText(file).split('\n')[0] ?? '' });
  };
  const visit = (node: ts.Node): void => {
    if (ts.isImportDeclaration(node)) add(node, node.moduleSpecifier, 'static');
    else if (ts.isExportDeclaration(node)) add(node, node.moduleSpecifier, 'static');
    else if (ts.isImportEqualsDeclaration(node) && ts.isExternalModuleReference(node.moduleReference)) {
      add(node, node.moduleReference.expression, 'static');
    } else if (ts.isCallExpression(node)) {
      if (node.expression.kind === ts.SyntaxKind.ImportKeyword) add(node, node.arguments[0], 'dynamic');
      else if (ts.isIdentifier(node.expression) && node.expression.text === 'require') {
        add(node, node.arguments[0], 'static');
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(file);
  return out;
}

const PAGE_SOURCES = walkFiles(PAGES, (path) => /\.(?:ts|tsx)$/.test(path));

function edgesUnderPages(): readonly (ImportEdge & { readonly file: string })[] {
  return PAGE_SOURCES.flatMap((path) =>
    widgetEdges(readText(path), path).map((edge) => ({ ...edge, file: repoRelative(path) })),
  );
}

describe('(a) no _pages module imports one of the five widgets statically', () => {
  it('reads the whole of _pages, not a sample of it', () => {
    // A path set, never a count alone: a walk that stopped at the first directory would
    // satisfy the case below by having read nothing.
    expect(PAGE_SOURCES.length, 'the walk found almost nothing under _pages').toBeGreaterThan(40);
    const relativePaths = PAGE_SOURCES.map(repoRelative);
    for (const slice of ['dashboard', 'knowledge-base', 'review', 'run', 'stage-comparison']) {
      expect(relativePaths.some((p) => p.startsWith(`web/src/_pages/${slice}/`)), slice).toBe(true);
    }
  });

  it('finds a static edge to none of them', () => {
    const statics = edgesUnderPages()
      .filter((edge) => edge.kind === 'static')
      .map((edge) => `${edge.file}:${edge.line}  ${edge.text}  (widgets/${edge.widget})`)
      .sort();
    expect(
      statics,
      'a _pages module imports a lazy widget statically, so the widget is back in that ' +
        "page's first-load chunk and its next/dynamic wrapper is decoration (W50-PLAN.md " +
        '§3.4). Reach it through the wrapper beside the page; a label map or a type the ' +
        'page needs belongs in an entity (as CATEGORY_LABELS moved to expert-decision).',
    ).toEqual([]);
  });

  it('reaches each of the five through exactly one import() — the walk covers all five', () => {
    const dynamics = edgesUnderPages().filter((edge) => edge.kind === 'dynamic');
    expect(dynamics.map((edge) => edge.widget).sort()).toEqual([...LAZY_SLICES].sort());
  });

  it('can fail: every spelling of a static edge is caught, and import() is not', () => {
    const page = join(PAGES, 'probe', 'ui', 'probe-page.tsx');
    const probe = [
      "import { Dashboard } from '@/widgets/dashboard';",
      "import type { EvidenceViewerProps } from '@/widgets/evidence-viewer';",
      "export { RunProgress } from '@/widgets/run-progress';",
      "import '@/widgets/knowledge-base';",
      "import deep from '../../../widgets/stage-comparison/ui/stage-comparison';",
      "import legacy = require('@/widgets/dashboard');",
      "const viaRequire = require('@/widgets/knowledge-base');",
      "const lazy = () => import('@/widgets/stage-comparison');",
      "import { ProjectList } from '@/widgets/project-list';",
    ].join('\n');
    const edges = widgetEdges(probe, page);
    expect(edges.filter((e) => e.kind === 'static').map((e) => e.line)).toEqual([1, 2, 3, 4, 5, 6, 7]);
    expect(edges.filter((e) => e.kind === 'dynamic').map((e) => e.widget)).toEqual(['stage-comparison']);
    // `project-list` is not one of the five, and `@/widgets/dashboardX` is not `dashboard`.
    expect(lazyWidgetOf('@/widgets/dashboardX', page)).toBeNull();
    expect(lazyWidgetOf('@/widgets', page)).toBeNull();
  });
});

// ============================================== the wrappers: next/dynamic and their loading

/** The text nodes a reader would see, decoded. Attributes are machinery and are not read. */
function visibleText(markup: string): string[] {
  return [...markup.matchAll(/>([^<>]+)</g)]
    .map((m) => (m[1] ?? '').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&').trim())
    .filter((text) => text.length > 0);
}

describe('each wrapper loads its widget through next/dynamic, behind a typed Russian loading state', () => {
  it('records exactly five dynamic() calls, and their loaders resolve to the five widgets', async () => {
    // The pages were imported above, so every wrapper has called `dynamic()` by now.
    expect(recorded.length, 'not every wrapper called next/dynamic, or something else did').toBe(5);
    const resolved = await Promise.all(recorded.map((call) => call.loader()));
    const names = resolved.map((component) => WIDGETS.find((entry) => entry.widget === component)?.slice ?? `?${String(component)}`);
    expect(names.sort()).toEqual([...LAZY_SLICES].sort());
  });

  // The name is read off the loader only to title the case; which widget a loader really
  // reaches is the case above, which resolves it.
  const named = recorded.map(
    (call) => [/widgets\/([a-z-]+)/.exec(String(call.loader))?.[1] ?? '?', call] as const,
  );

  /**
   * Moved here from `screen-guard.guard.test.ts` (`§3.3 … loading.tsx renders the typed
   * loading state`, granted to this task on 2026-10-06): the segment files it rendered are
   * deleted, and the loading states that replace them are these five.
   */
  it.each(named)('the %s wrapper renders a typed loading state, in Russian, through the harness', (_name, call) => {
    expect(call.loading, 'a wrapper declares no loading state: Next renders nothing').toBeDefined();
    const Loading = call.loading as ComponentType<LoadingProps>;
    const markup = renderScreen(
      newClient(),
      createElement(Loading, { isLoading: true, pastDelay: false, error: null }),
    );
    // Typed: the state block from `shared/ui`, not a string or a hand-made element.
    expect(markup).toMatch(/^<div class="am-state am-state--neutral" role="status"><p class="am-state__title">/);
    const text = visibleText(markup);
    expect(text.length, 'the loading state says nothing').toBeGreaterThan(0);
    expect(text.join(' '), 'the loading state carries a Latin letter').not.toMatch(/[A-Za-z]/);
    expect(text.join(' '), 'the loading state is not Russian').toMatch(/[А-Яа-яЁё]/);
  });

  /**
   * The review page is not in this list: it mounts the viewer only once a finding is
   * selected and its detail has arrived, so its product path needs four seeded caches —
   * the census' `ReviewPage loaded` is that state, and (c) below reads the viewer there.
   */
  it('the product path: with the seam empty, each page draws its frame and the fallback where the widget goes', () => {
    const pages: readonly (readonly [string, unknown, ReactElement])[] = [
      ['dashboard', DashboardEagerSeam, createElement(DashboardPage)],
      ['knowledge-base', KnowledgeBaseEagerSeam, createElement(KnowledgeBasePage)],
      ['run-progress', RunProgressEagerSeam, createElement(RunPage, { projectUid: PROJECT_UID, runId: RUN_ID })],
      [
        'stage-comparison',
        StageComparisonEagerSeam,
        createElement(StageComparisonPage, { projectUid: PROJECT_UID, versionUid: VERSION_UID }),
      ],
    ];
    for (const [slice, seam, page] of pages) {
      // `null` under the harness' own provider is exactly what the product has: no provider.
      const Provider = (seam as typeof DashboardEagerSeam).Provider as ComponentType<{
        value: null;
        children: ReactNode;
      }>;
      const markup = renderScreen(newClient(), createElement(Provider, { value: null, children: page }));
      expect(markup, `${slice}: the page frame did not render`).toContain('<h1');
      expect(markup, `${slice}: no fallback where the widget goes`).toContain(BARE_FALLBACK);
      const marker = WIDGETS.find((entry) => entry.slice === slice)?.marker ?? '';
      expect(markup, `${slice}: the eager widget rendered with no seam`).not.toContain(marker);
    }
  });
});

// ================================================ the seam: provided by the harness only

describe('the eager seam is provided by the harness and by nothing under web/src', () => {
  const SEAMS = WIDGETS.map((entry) => entry.seam);
  const mentioning = walkFiles(SRC, (path) => /\.(?:ts|tsx)$/.test(path))
    .filter((path) => SEAMS.some((seam) => readText(path).includes(seam)))
    .map(repoRelative)
    .sort();

  it('is named by exactly the five wrappers and their five slice indexes', () => {
    expect(mentioning).toEqual(
      [
        'web/src/_pages/dashboard/index.ts',
        'web/src/_pages/dashboard/ui/lazy-dashboard.tsx',
        'web/src/_pages/knowledge-base/index.ts',
        'web/src/_pages/knowledge-base/ui/lazy-knowledge-base.tsx',
        'web/src/_pages/review/index.ts',
        'web/src/_pages/review/ui/lazy-evidence-viewer.tsx',
        'web/src/_pages/run/index.ts',
        'web/src/_pages/run/ui/lazy-run-progress.tsx',
        'web/src/_pages/stage-comparison/index.ts',
        'web/src/_pages/stage-comparison/ui/lazy-stage-comparison.tsx',
      ].sort(),
    );
  });

  it('is never mounted under web/src — read in the files that name it', () => {
    const mounts = mentioning.flatMap((relativePath) => {
      const source = readText(join(WEB_ROOT, '..', relativePath));
      return SEAMS.filter(
        (seam) => source.includes(`${seam}.Provider`) || new RegExp(`<${seam}\\b`).test(source),
      ).map((seam) => `${relativePath} mounts ${seam}`);
    });
    expect(
      mounts,
      'a production module provides the eager seam, so the product renders the eager widget ' +
        'and the bundle split is gone from that render path',
    ).toEqual([]);
  });

  it('is provided by the harness, once per widget, with the widget itself', () => {
    const harness = readText(join(WEB_ROOT, 'tests/unit/screens/harness.ts'));
    for (const { seam, slice } of WIDGETS) {
      expect(harness, `${seam} is not provided by the harness`).toMatch(
        new RegExp(`${seam}\\.Provider,\\s*\\{\\s*value:\\s*\\w+\\s*\\}`),
      );
      expect(harness).toContain(`from '@/widgets/${slice}'`);
    }
  });

  it('can fail: a mount in either spelling is read as one', () => {
    const seam = 'DashboardEagerSeam';
    for (const source of [`<${seam}.Provider value={Dashboard}>`, `<${seam} value={Dashboard}>`]) {
      expect(source.includes(`${seam}.Provider`) || new RegExp(`<${seam}\\b`).test(source)).toBe(true);
    }
    expect(new RegExp(`<${seam}\\b`).test(`useContext(${seam})`)).toBe(false);
  });
});

// ========================================================== (b) and (c): the census held

const GLOBALS = readFileSync(join(SRC, 'app', 'globals.css'), 'utf8');

const MODULE_EXPORTS = import.meta.glob('../../src/**/*.module.css', { eager: true }) as Record<
  string,
  { readonly default: Record<string, string> }
>;

/** The census' rules: `globals.css` and every CSS module, scoped as the markup names them. */
function censusRules(): Rule[] {
  const modules = Object.keys(MODULE_EXPORTS)
    .sort()
    .map((relativePath) => {
      const scope = (MODULE_EXPORTS[relativePath] as { readonly default: Record<string, string> }).default;
      const css = readFileSync(fileURLToPath(new URL(relativePath, import.meta.url)), 'utf8');
      return parseRules(
        css.replace(/\.([a-zA-Z_][A-Za-z0-9_-]*)/g, (_m, name: string) => `.${scope[name]}`),
        relativePath,
      );
    })
    .flat();
  return [...parseRules(GLOBALS, 'globals.css'), ...modules];
}

/**
 * THE BASELINE, measured at the lane base `96a1653` (= `integration/w50` after
 * `W50-REGISTRY-01`), before any wrapper existed:
 *
 *   `npm --prefix web test -- --run tests/guards/census-counts.probe.test.ts`
 *   → `CENSUS screens=80 pairs.light=150 pairs.dark=150`
 *
 * over a disposable clone of `96a1653`, where the probe (quoted whole in
 * `docs/program/W50-LAZY-01.md` §2) computes exactly what `censusCounts()` below computes:
 * `screens()` from `tests/unit/styles/screens.ts`, and `census()` over them with
 * `globals.css` plus every scoped CSS module, per palette. A PAIR is the census' own key —
 * kind, foreground, background, state, pseudo — not a site.
 *
 * The figures may rise; a fall is a stop (`W50-PLAN.md` §7: "the census shrinks").
 */
const BASELINE = { screens: 80, pairsLight: 150, pairsDark: 150 } as const;

function censusCounts(rendered: ReturnType<typeof screens>): {
  screens: number;
  pairsLight: number;
  pairsDark: number;
} {
  const rules = censusRules();
  return {
    screens: rendered.length,
    pairsLight: census(rendered, rules, palette(GLOBALS, 'light')).size,
    pairsDark: census(rendered, rules, palette(GLOBALS, 'dark')).size,
  };
}

describe('the contrast census still sees the five widgets', () => {
  const rendered = screens();

  it('(b) holds its screen count and its measured pair count at or above the baseline', () => {
    const counts = censusCounts(rendered);
    expect(counts.screens, 'the census renders fewer screens than before the wrappers').toBeGreaterThanOrEqual(
      BASELINE.screens,
    );
    expect(counts.pairsLight, 'the census measures fewer pairs in the light palette').toBeGreaterThanOrEqual(
      BASELINE.pairsLight,
    );
    expect(counts.pairsDark, 'the census measures fewer pairs in the dark palette').toBeGreaterThanOrEqual(
      BASELINE.pairsDark,
    );
  });

  it.each(WIDGETS.map((entry) => [entry.slice, entry] as const))(
    '(c) %s is in the census markup eagerly, through its page',
    (_slice, entry) => {
      const screen = rendered.find((candidate) => candidate.name === entry.screen);
      expect(screen, `the census has no screen named ${entry.screen}`).toBeDefined();
      const markup = screen?.markup ?? '';
      expect(
        markup,
        `${entry.screen} does not draw ${entry.slice}: the census renders the page without the ` +
          'widget, so every colour the widget draws is unmeasured (the eager seam is not reaching it)',
      ).toContain(entry.marker);
      expect(markup, `${entry.screen} renders the lazy fallback instead of the widget`).not.toContain(BARE_FALLBACK);
    },
  );
});

// ================================== no segment loading.tsx above a screen that is not public

export interface LoadingOffence {
  readonly loading: string;
  readonly address: string;
  readonly access: string;
}

/**
 * Every (`loading.*`, guarded page) pair where the loading file's segment is the page's own
 * or an ancestor of it. Taken as data so the case below can show it fail on a tree that has
 * one, without writing a file into `web/src/app`.
 */
export function loadingAboveGuardedPages(
  loadingFiles: readonly string[],
  pages: readonly { readonly address: string; readonly file: string }[],
  accessOf: (address: string) => string | undefined,
): readonly LoadingOffence[] {
  const out: LoadingOffence[] = [];
  for (const loading of loadingFiles) {
    const segment = dirname(loading);
    for (const page of pages) {
      const pageSegment = dirname(page.file);
      if (pageSegment !== segment && !pageSegment.startsWith(`${segment}/`)) continue;
      const access = accessOf(page.address) ?? 'unregistered';
      if (access !== 'public') out.push({ loading, address: page.address, access });
    }
  }
  return out.sort((a, b) => `${a.loading} ${a.address}`.localeCompare(`${b.loading} ${b.address}`));
}

describe('no loading.tsx sits at or above a page whose registry access is not public', () => {
  const APP = join(SRC, 'app');
  const loadingFiles = walkFiles(APP, (path) => /\/loading\.(?:tsx|ts|jsx|js)$/.test(path)).map(repoRelative);
  const pages = routeAddresses();
  const accessOf = (address: string): string | undefined =>
    SCREEN_REGISTRY.find((row) => row.address === address)?.access;

  it('reads the route tree and the registry it judges against', () => {
    expect(pages.length, 'no page.tsx found under web/src/app').toBeGreaterThan(15);
    expect(pages.filter((page) => accessOf(page.address) === 'session').length).toBeGreaterThan(10);
    expect(pages.filter((page) => accessOf(page.address) === 'public').map((p) => p.address).sort()).toEqual([
      '/403',
      '/login',
    ]);
  });

  it('finds none', () => {
    expect(
      loadingAboveGuardedPages(loadingFiles, pages, accessOf).map(
        (o) => `${o.loading} is above ${o.address} (${o.access})`,
      ),
      "a segment loading boundary wraps a guarded page in Suspense, so requireScreen's " +
        'redirect travels inside a 200 stream and a guest gets no 307 and no Location ' +
        "(W50-REGISTRY-01 §4.10, the integrator's ruling at its merge). Put the loading state " +
        'inside the page, below the guard, around the widget that is slow.',
    ).toEqual([]);
  });

  it('can fail: the four deleted files, and a root one, are each named', () => {
    const restored = [
      'web/src/app/projects/loading.tsx',
      'web/src/app/projects/[project_uid]/loading.tsx',
      'web/src/app/dashboard/loading.tsx',
      'web/src/app/knowledge-base/loading.tsx',
    ];
    const offences = loadingAboveGuardedPages(restored, pages, accessOf);
    expect(new Set(offences.map((o) => o.loading))).toEqual(new Set(restored));
    expect(offences.some((o) => o.address === '/projects/[project_uid]/runs/[run_id]/review')).toBe(true);
    // A root boundary is above every screen, including the public ones it must not count.
    const root = loadingAboveGuardedPages(['web/src/app/loading.tsx'], pages, accessOf);
    expect(root.map((o) => o.address)).not.toContain('/login');
    expect(root.map((o) => o.address)).toContain('/');
    // A public screen's own boundary is allowed.
    expect(loadingAboveGuardedPages(['web/src/app/login/loading.tsx'], pages, accessOf)).toEqual([]);
  });
});
