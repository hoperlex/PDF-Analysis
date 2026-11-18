/**
 * `UI-PARITY-DENSE` for the dashboard and the front door: the overview opens on its table, as the original's does.
 *
 * Before, the dashboard opened on a 220px poster (an eyebrow, a lead, an orbit drawing) and a section row was 44px high with
 * a single ink for its five numbers. These cases hold the three things the screen is read for: the poster is gone and the
 * scope line stayed, a row is no taller than its text asks for, and the five columns carry the original's five inks as
 * tokens (so both palettes). Each is a fact about the module CSS or the markup, not a pixel measurement; the pixel numbers
 * are in the lane's report, taken with the static preview.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { DashboardSummary, ProjectUid } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { PROJECT_SECTIONS, sectionColourStyle, sectionColourVar } from '@/entities/project';
import { Dashboard, HomeSectionsOverview } from '@/widgets/dashboard';

import { WEB_ROOT } from '../../guards/lib/repo';
import { AA_NON_TEXT, AA_TEXT, THEMES, contrastRatio, palette, parseRules, scopedPalettes } from '../styles/contrast';
import type { TokenName } from '../styles/contrast';
import { newClient, renderWith } from '../screens/harness';
import { sectionAudit } from './audit-counts';

const module = (path: string): string => readFileSync(join(WEB_ROOT, 'src', path), 'utf8');

/** The declarations of the first rule whose selector is exactly `selector`. */
function declarations(css: string, selector: string): ReadonlyMap<string, string> {
  const rule = parseRules(css, 'module').find((entry) => entry.selector === selector);
  if (rule === undefined) throw new Error(`no rule ${selector}`);
  return rule.declarations;
}

/**
 * The minimums a row's control and a row may declare: 24 px, the WCAG 2.5.8 target size (`--am-target-min`), and, since `UIP-S01-02`,
 * one step of the table (`--am-row-step`, 40 px, `UIP-G-14`) for the row itself. Both are tokens, so a retuned size costs no change
 * here. Any other `min-height` is a row height fixed in CSS, which is what the dense overview gave up.
 */
const TARGET_FLOOR = 'var(--am-target-min)';
const ROW_STEP = 'var(--am-row-step)';

/** The rules of a stylesheet that declare a `min-height` other than the target floor and the row step. */
function fixedHeights(css: string) {
  return parseRules(css, 'module').filter((rule) => {
    const height = rule.declarations.get('min-height');
    return height !== undefined && height !== TARGET_FLOOR && height !== ROW_STEP;
  });
}

const SUMMARY: DashboardSummary = {
  documents_by_project: [{ project_uid: 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', name: 'Проект Альфа', document_count: 3 }],
  findings_by_verdict: [
    { verdict: 'pending', count: 1 },
    { verdict: 'accepted', count: 2 },
    { verdict: 'rejected', count: 3 },
    { verdict: 'needs_manual_review', count: 4 },
  ],
  run_activity: { by_state: [] },
  section_breakdown: [
    ...PROJECT_SECTIONS.map((section, index) => ({ section: section.code, document_count: index + 1, ...sectionAudit(index + 1) })),
    { document_count: 1, ...sectionAudit(1) },
  ],
  awaiting_decision_findings: 0,
};

describe('the dashboard opens on its table', () => {
  const client = newClient();
  client.setQueryData(queryKeys.dashboard.summary(), SUMMARY);
  const markup = renderWith(client, createElement(Dashboard));

  it('keeps the title and the scope in one header line, with no poster', () => {
    expect(markup).toContain('>Сводка по объектам</h2>');
    expect(markup).toContain('data-dashboard-scope="all"');
    expect(markup).not.toContain('AuditManager / Аналитика');
    expect(markup).not.toMatch(/orbit/i);
    expect(markup).not.toContain('в едином обзоре');
  });

  it('keeps the module free of the poster and of fixed row heights', () => {
    const css = module('widgets/dashboard/ui/dashboard.module.css');
    // The selectors, not the text: the comment above `.hero` names what it replaced.
    const selectors = parseRules(css, 'module').map((rule) => rule.selector).join(' ');
    expect(selectors).not.toMatch(/orbit|heroArt|heroCopy|eyebrow|heroDescription/);
    expect(declarations(css, '.hero').get('min-height')).toBeUndefined();
    const sections = module('widgets/dashboard/ui/sections-panel.module.css');
    expect(fixedHeights(sections).map((rule) => rule.selector), 'a rule that fixes a height').toEqual([]);
  });

  it('can fail: a fixed row height is reported, the 24 px target floor and the table\'s row step are not', () => {
    const css =
      '.a { min-height: 44px; }\n.b { min-height: var(--am-target-min); }\n.c { padding: 0; }\n.d, .e { min-height: 3rem; }\n.f { min-height: var(--am-row-step); }\n.g { min-height: 40px; }';
    expect(fixedHeights(css).map((rule) => rule.selector)).toEqual(['.a', '.d, .e', '.g']);
  });

  it('UIP-S01-02: a section row is one step of the table high, read from the token and not spelled in the module', () => {
    const css = module('widgets/dashboard/ui/sections-panel.module.css');
    expect(declarations(css, '.row').get('min-height')).toBe(ROW_STEP);
    // No row rule fixes the height with a length of its own: `height` is not declared on a row, and `min-height` is the token.
    for (const selector of ['.row', '.sectionRow', '.unclassified', '.totalRow']) {
      const rule = parseRules(css, 'module').find((entry) => entry.selector === selector);
      expect(rule?.declarations.get('height'), selector).toBeUndefined();
      const minHeight = rule?.declarations.get('min-height');
      expect(minHeight === undefined || minHeight === ROW_STEP, selector).toBe(true);
    }
  });

  it('gives the row\'s button and toggle the 24 px target floor and nothing taller', () => {
    const css = module('widgets/dashboard/ui/sections-panel.module.css');
    expect(declarations(css, '.rowButton').get('min-height')).toBe(TARGET_FLOOR);
    expect(declarations(css, '.toggle').get('min-height')).toBe(TARGET_FLOOR);
  });
});

/** The rules of a header (`.header`, its media variants and what is inside it) that let a browser cut a word. */
function cuttingRules(css: string) {
  return parseRules(css, 'module').filter((rule) => {
    if (!/^\.(?:header|head|nameHead)\b/.test(rule.selector)) return false;
    const wrap = rule.declarations.get('overflow-wrap') ?? rule.declarations.get('word-wrap');
    const breaking = rule.declarations.get('word-break');
    const hyphens = rule.declarations.get('hyphens');
    return (wrap !== undefined && wrap !== 'normal') || (breaking !== undefined && breaking !== 'normal') || (hyphens !== undefined && hyphens !== 'manual');
  });
}

describe('UIP-S01-02: the headings wrap between words and never inside one', () => {
  const css = module('widgets/dashboard/ui/sections-panel.module.css');

  it('says so on the header: no cutting of words, no hyphenation, at every width', () => {
    const header = declarations(css, '.header');
    expect(header.get('overflow-wrap')).toBe('normal');
    expect(header.get('word-break')).toBe('normal');
    expect(header.get('hyphens')).toBe('manual');
    // The narrow layout (a phone) used to cut words anywhere; no rule of the header or inside it does now.
    expect(cuttingRules(css).map((rule) => rule.selector)).toEqual([]);
  });

  it('can fail: the old narrow rule, which cut a word anywhere, is reported', () => {
    const old = '.header { overflow-wrap: normal; }\n@media (max-width: 1100px) { .header .metrics { overflow-wrap: anywhere; } }\n.name { overflow-wrap: anywhere; }';
    expect(cuttingRules(old).map((rule) => rule.selector)).toEqual(['.header .metrics']);
    expect(cuttingRules('.header { word-break: break-all; }\n.head { hyphens: auto; }').map((rule) => rule.selector)).toEqual(['.header', '.head']);
  });

  it('reads the original\'s weight and spacing, so the longest word fits its 5.5rem column (about 87 px of 88 px, measured on the face)', () => {
    const header = declarations(css, '.header');
    expect(header.get('font-weight')).toBe('600');
    expect(header.get('letter-spacing')).toBe('0.02em');
  });
});

describe("the section table's five numbers carry the original's inks", () => {
  const css = module('widgets/dashboard/ui/sections-panel.module.css');
  // A class per column, not `:nth-child`: the contrast census evaluates class selectors and declines positional ones.
  const ink = (column: string): string | undefined => declarations(css, `.${column}`).get('color');

  it('reads the inks as tokens, in the original order: not run, awaiting, checked, all, remarks', () => {
    expect(['notRun', 'awaiting', 'checked', 'total', 'remarks'].map(ink)).toEqual([
      'var(--am-degraded)',
      'var(--am-accent-strong)',
      'var(--am-ok)',
      'var(--am-ink-muted)',
      'var(--am-failed)',
    ]);
  });

  it('adds the original’s total row: the sums of the fifteen rows above it, the unclassified row outside them', () => {
    const client = newClient();
    client.setQueryData(queryKeys.dashboard.summary(), SUMMARY);
    const markup = renderWith(client, createElement(Dashboard));
    const total = /<li[^>]*data-section="total"[^>]*>([\s\S]*?)<\/li>/.exec(markup)?.[1] ?? '';
    // `UIP-S01-02`: the original's word, «Итого», and not «Итого по разделам».
    expect(total).toContain('>Итого</span>');
    expect(total).not.toContain('Итого по разделам');
    const sections = SUMMARY.section_breakdown.filter((row) => row.section !== undefined);
    const sum = (read: (row: (typeof sections)[number]) => number): number => sections.reduce((acc, row) => acc + read(row), 0);
    // The five figures, in the table's column order: not run, awaiting a decision, checked, documents, remarks.
    const shown = (total.replace(/<[^>]*>/g, ' ').match(/\d+/g) ?? []).map(Number);
    expect(shown).toEqual([
      sum((row) => row.audit_counts?.not_run ?? 0),
      sum((row) => row.audit_counts?.no_expert_decision ?? 0),
      sum((row) => row.audit_counts?.checked ?? 0),
      sum((row) => row.document_count),
      sum((row) => row.finding_count),
    ]);
    // «Без раздела» is a row of its own with its own number, and the total row comes before it.
    expect(markup.indexOf('data-section="total"')).toBeLessThan(markup.indexOf('data-section="unclassified"'));
    expect(markup).not.toMatch(/data-section="total"[^>]*data-analysed-by/);
  });
});

describe('the front door is compact', () => {
  const tiles = module('widgets/home-tiles/ui/home-tiles.module.css');
  const home = module('_pages/home/ui/home-page.module.css');

  it('puts a figure and its label on one line, and a recent project (name, date) on one line', () => {
    expect(declarations(tiles, '.figures').get('grid-template-columns')).toBe('minmax(0, 1fr) auto');
    expect(declarations(tiles, '.project').get('display')).toBe('flex');
    expect(declarations(tiles, '.figures dd').get('font-size')).toBe('var(--am-text-lg)');
  });

  it('greets in the page-title size, in one line with no frame (UIP-S01-01: the band is not a card any more)', () => {
    expect(declarations(home, '.greeting').get('font-size')).toBe('var(--am-text-2xl)');
    // The greeting and the roles are one flex line that wraps; the old `.hero` card (padding, border, background, shadow) is gone.
    expect(declarations(home, '.heading').get('display')).toBe('flex');
    expect(declarations(home, '.heading').get('flex-wrap')).toBe('wrap');
    expect(parseRules(home, 'module').map((rule) => rule.selector)).not.toContain('.hero');
    for (const selector of ['.heading', '.greeting']) {
      const painted = ['border', 'background', 'box-shadow'].filter((property) => declarations(home, selector).has(property));
      expect(painted, selector).toEqual([]);
    }
  });
});

describe('a section row opens the section in one click when a project is chosen', () => {
  const PROJECT = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B' as ProjectUid;
  const render = (projectUid: ProjectUid | null): string => {
    const client = newClient();
    client.setQueryData(queryKeys.dashboard.summary(projectUid), SUMMARY);
    return renderWith(client, createElement(Dashboard, { projectUid }));
  };

  it('is a link to the project’s section page for every section, with the section’s code and name in it', () => {
    const markup = render(PROJECT);
    for (const section of PROJECT_SECTIONS) {
      const link = markup.match(new RegExp(`<a [^>]*data-section-open="${section.code}"[^>]*>(.*?)</a>`))?.[0];
      expect(link, section.code).toBeDefined();
      expect(link, section.code).toContain(`href="/projects/${PROJECT}/sections/${section.code}"`);
      expect(link, section.code).toContain(section.name);
    }
  });

  it('keeps the panel with the section’s optimisation reachable from a toggle at the row’s end', () => {
    const markup = render(PROJECT);
    for (const section of PROJECT_SECTIONS) {
      expect(markup, section.code).toMatch(new RegExp(`<button[^>]*data-section-toggle="${section.code}"`));
    }
  });

  it('is a button that opens the panel across all projects, where there is no one section page to open', () => {
    const markup = render(null);
    expect(markup).not.toContain('data-section-open');
    expect(markup).not.toContain('data-section-toggle');
  });

  it('stretches the link over the row and lifts the figure link and the toggle above it', () => {
    const css = module('widgets/dashboard/ui/sections-panel.module.css');
    expect(declarations(css, '.sectionRow').get('position')).toBe('relative');
    expect(declarations(css, '.rowLink::after').get('position')).toBe('absolute');
    expect(declarations(css, '.rowLink::after').get('inset')).toBe('0');
    expect(declarations(css, '.metricLink').get('z-index')).toBe('1');
    expect(declarations(css, '.toggle').get('z-index')).toBe('1');
  });
});

describe('UIP-S01-03: the code badge of a section row wears the section\'s colour', () => {
  const css = module('widgets/dashboard/ui/sections-panel.module.css');
  const globals = readFileSync(join(WEB_ROOT, 'src', 'app', 'globals.css'), 'utf8');
  const PROJECT = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B' as ProjectUid;

  /**
   * The outline each badge in `markup` is set to, by the text it carries (a section code, `Σ` or `—`); `null` for a badge with no
   * colour of its own, which wears the stylesheet's neutral outline.
   */
  function badgeColours(markup: string): Map<string, string | null> {
    const found = new Map<string, string | null>();
    for (const match of markup.matchAll(/<span class="_badge_[a-z0-9]+"(?: style="border-color:([^"]*)")?>([^<]*)<\/span>/gu)) {
      found.set(match[2] ?? '', match[1] ?? null);
    }
    return found;
  }

  const dashboard = (projectUid: ProjectUid | null): string => {
    const client = newClient();
    client.setQueryData(queryKeys.dashboard.summary(projectUid), SUMMARY);
    return renderWith(client, createElement(Dashboard, { projectUid }));
  };
  const frontDoor = (projectUid: ProjectUid | null): string => {
    const client = newClient();
    client.setQueryData(queryKeys.dashboard.summary(projectUid), SUMMARY);
    return renderWith(client, createElement(HomeSectionsOverview, { projectUid }));
  };

  it('sets each of the fifteen sections\' badges to that section\'s own colour, on the dashboard and on the front door, with or without an object', () => {
    for (const [name, markup] of [
      ['dashboard, all objects', dashboard(null)],
      ['dashboard, one object', dashboard(PROJECT)],
      ['front door, all objects', frontDoor(null)],
      ['front door, one object', frontDoor(PROJECT)],
    ] as const) {
      const colours = badgeColours(markup);
      for (const section of PROJECT_SECTIONS) {
        expect(colours.get(section.code), `${name}: ${section.code}`).toBe(sectionColourVar(section.code));
      }
      expect(PROJECT_SECTIONS).toHaveLength(15);
    }
  });

  it('gives the fifteen badges fifteen different colours, the ones of the menu\'s dots', () => {
    const colours = PROJECT_SECTIONS.map((section) => badgeColours(dashboard(PROJECT)).get(section.code));
    expect(new Set(colours).size).toBe(PROJECT_SECTIONS.length);
    for (const colour of colours) expect(colour).toMatch(/^var\(--am-section-(?:0[1-9]|1[0-5])\)$/);
    // The one list: what the markup sets is what `sectionColourVar` says, the same list the dot reads.
    for (const section of PROJECT_SECTIONS) {
      expect(sectionColourStyle(section.code)['--am-section-colour']).toBe(sectionColourVar(section.code));
    }
  });

  it('leaves the total row and «Без раздела» neutral: no colour of their own, so the stylesheet\'s neutral token', () => {
    for (const markup of [dashboard(null), frontDoor(null)]) {
      const colours = badgeColours(markup);
      expect(colours.get('Σ')).toBeNull();
      expect(colours.get('—')).toBeNull();
      expect([...colours.keys()].sort()).toEqual([...PROJECT_SECTIONS.map((section) => section.code), 'Σ', '—'].sort());
    }
    expect(declarations(css, '.badge').get('border')).toContain(sectionColourVar(null));
  });

  /** The colour values a module may not spell: a hex, a colour function, a mix. */
  const COLOUR_LITERAL = /#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color|color-mix)\(/;
  const spelledColours = (text: string): string[] => {
    const rules = parseRules(text, 'module');
    return rules.flatMap((rule) => [...rule.declarations].filter(([, value]) => COLOUR_LITERAL.test(value)).map(([property]) => `${rule.selector} { ${property} }`));
  };
  const declaredTokens = (text: string): string[] =>
    parseRules(text, 'module').flatMap((rule) => [...rule.declarations.keys()].filter((property) => property.startsWith('--')).map((property) => `${rule.selector} { ${property} }`));

  it('reads only tokens: the outline is the neutral token, the section\'s colour comes from the markup, and the stylesheet spells no colour and declares no token', () => {
    // `STYLE-ORIG-01`, `R-157e`: the code badge is the original's small plaque, a 1 px outline.
    expect(declarations(css, '.badge').get('border')).toBe('1px solid var(--am-inert)');
    expect(spelledColours(css)).toEqual([]);
    expect(declaredTokens(css)).toEqual([]);
  });

  it('can fail: a hex, a colour function or a declared token in the stylesheet is reported', () => {
    const bad = '.a { background: #ff0000; }\n.b { border: 1px solid rgb(1 2 3); }\n.c { --am-section-colour: red; }\n.d { color: var(--am-ink); }';
    expect(spelledColours(bad)).toEqual(['.a { background }', '.b { border }']);
    expect(declaredTokens(bad)).toEqual(['.c { --am-section-colour }']);
  });

  /**
   * The census (`contrast.test.ts`) cannot measure this pair: the badge's section colour is an inline `border-color` the markup sets,
   * which no rule of any stylesheet declares, so the census sees the neutral outline and the code's ink on the fill. The outline is measured here,
   * for every one of the fifteen sections in both themes, against what it touches: the fill inside it, the row outside it and the
   * row's tint under the pointer, as the frame draws them (`.am-app__main` remaps the surfaces) and as the root has them; the lower
   * ratio counts. The colours' own distance from the surfaces is `section-palette.test.ts`'s.
   */
  describe('the outline and the code are readable in both themes, for every section', () => {
    const fill = /^var\((--am-[\w-]+)\)$/.exec(declarations(css, '.badge').get('background') ?? '')?.[1] as TokenName;
    const ink = /^var\((--am-[\w-]+)\)$/.exec(declarations(css, '.badge').get('color') ?? '')?.[1] as TokenName;
    const row = /^var\((--am-[\w-]+)\)$/.exec(declarations(css, '.row').get('background') ?? '')?.[1] as TokenName;
    // The rule is a list (`.sectionRow:hover, .sectionRow[data-open='true']`): the one whose first selector is the hover.
    const hoverRule = parseRules(css, 'module').find((entry) => entry.selector.startsWith('.sectionRow:hover'));
    const hover = /^var\((--am-[\w-]+)\)$/.exec(hoverRule?.declarations.get('background') ?? '')?.[1] as TokenName;
    const scope = scopedPalettes(parseRules(globals, 'globals.css')).find((entry) => entry.selectors.includes('.am-app__main'));

    it('reads its fill, its ink, the row and the row\'s tint as tokens', () => {
      expect([fill, ink, row, hover]).toEqual(['--am-surface-sunken', '--am-ink', '--am-paper', '--am-accent-light']);
      expect(scope, 'the frame remaps the surfaces').toBeDefined();
    });

    for (const theme of THEMES) {
      it(`${theme}: every section's outline (and the neutral one) is 3:1 against the fill, the row and its tint, and the code is 4.5:1 on the fill`, () => {
        const tokens = palette(globals, theme);
        const hex = (token: TokenName, remapped: boolean): string => {
          const named = remapped ? (scope?.alias.get(token) ?? token) : token;
          const value = tokens.get(named);
          if (value === undefined) throw new Error(`${theme}: no value for ${named}`);
          return value;
        };
        const ratios: string[] = [];
        // The fifteen sections' tokens, and the neutral one the total row and «Без раздела» keep.
        const outlines = [
          ...PROJECT_SECTIONS.map((section) => [section.code, /var\((--am-[\w-]+)\)/.exec(sectionColourVar(section.code))?.[1] as TokenName] as const),
          ['neutral', /var\((--am-[\w-]+)\)/.exec(sectionColourVar(null))?.[1] as TokenName] as const,
        ];
        expect(outlines).toHaveLength(PROJECT_SECTIONS.length + 1);
        for (const [name, token] of outlines) {
          for (const remapped of [false, true]) {
            for (const [against, surface] of [['fill', fill], ['row', row], ['tint', hover]] as const) {
              const ratio = contrastRatio(hex(token, remapped), hex(surface, remapped));
              if (ratio < AA_NON_TEXT) ratios.push(`${name} ${token} against the ${against}${remapped ? ' (framed)' : ''}: ${ratio.toFixed(2)}`);
            }
          }
        }
        for (const remapped of [false, true]) {
          const ratio = contrastRatio(hex(ink, remapped), hex(fill, remapped));
          if (ratio < AA_TEXT) ratios.push(`the code on the fill${remapped ? ' (framed)' : ''}: ${ratio.toFixed(2)}`);
        }
        expect(ratios).toEqual([]);
      });
    }

    it('can fail: a colour below 3:1 against a surface is told from one above it', () => {
      expect(contrastRatio('#eef0f4', '#ffffff')).toBeLessThan(AA_NON_TEXT);
      expect(contrastRatio('#428228', '#ffffff')).toBeGreaterThanOrEqual(AA_NON_TEXT);
    });
  });
});
