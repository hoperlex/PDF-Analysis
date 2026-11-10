/**
 * `D-564`: the text links that stood under the 24 px target floor (`--am-target-min`, WCAG 2.5.8), found by the DOM facts of the
 * browser walk of lane WALK-V4 at 1280 and 390 px (the walk's `tap` list: an `a` that is not an inline link inside running text, under
 * 24 px high):
 *
 *  - the project name in the project list («Проекты», «Оптимизация») and on «Главная» (21 px);
 *  - the version title (21 px) and the second link of a version row in the document's list;
 *  - «все версии» of a document card (17 px) and «К разделам проекта» of the empty section (17 px);
 *  - «Подать заявку на доступ» of the sign-in card (19 px).
 *
 * The cure is the one `D-431` used for a held run's link: the surplus that makes the link 24 px is PADDING, and the same amount is taken
 * back as negative MARGIN, so the box a row sees is still one line of text and no row gets taller (the owner's order: a dense layout).
 * Each link states three declarations that belong together:
 *
 *   min-height: var(--am-target-min);                         the floor, as the dense overview holds it for buttons
 *   padding-block: calc((var(--am-target-min) - 1lh) / 2);    what it takes to reach it from one line of its own font
 *   margin-block: calc((1lh - var(--am-target-min)) / 2);     the same amount, returned
 *
 * The suite renders markup in `node` and cannot measure a box, so the check is on the declarations, and it can fail: it is run first on
 * fixtures that lack the pair (a floor with no margin would raise every row by the surplus), then on the real modules. The pixel
 * figures, before and after, are in the lane's report and the debt register, not here.
 *
 * `widgets/extended-review` (the report nav of «Прогон», 21 px) is a HOSTS path and is not read here.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { WEB_ROOT } from '../../guards/lib/repo';
import { parseRules } from './contrast';

const source = (...parts: readonly string[]): string => readFileSync(join(WEB_ROOT, 'src', ...parts), 'utf8');

const FLOOR = 'var(--am-target-min)';
const GROW = `calc((${FLOOR} - 1lh) / 2)`;
const BACK = `calc((1lh - ${FLOOR}) / 2)`;

/** The declarations of every rule whose selector list names `selector`, the later rule winning, as the cascade has it. */
function declared(css: string, selector: string): ReadonlyMap<string, string> {
  const merged = new Map<string, string>();
  for (const rule of parseRules(css, 'module')) {
    if (!rule.selector.split(',').some((part) => part.trim() === selector)) continue;
    for (const [property, value] of rule.declarations) merged.set(property, value);
  }
  return merged;
}

/**
 * Why `selector` does not hold the floor without raising its row, or `null` when it does: the three declarations are there, the padding
 * grows the box by exactly what the margin returns, and the floor is the token and not a length.
 */
function whyNot(css: string, selector: string): string | null {
  const rule = declared(css, selector);
  if (rule.size === 0) return `${selector}: no rule`;
  if (rule.get('min-height') !== FLOOR) return `${selector}: min-height is ${rule.get('min-height') ?? 'absent'}, not ${FLOOR}`;
  if (rule.get('padding-block') !== GROW) return `${selector}: padding-block is ${rule.get('padding-block') ?? 'absent'}, not ${GROW}`;
  if (rule.get('margin-block') !== BACK) return `${selector}: margin-block is ${rule.get('margin-block') ?? 'absent'}, not ${BACK}`;
  return null;
}

describe('the reader can fail (lane TARGETS)', () => {
  it('names a link with no rule, with a floor and no margin, with a margin that does not match, and with a literal floor', () => {
    expect(whyNot('.other { color: red; }', '.link')).toBe('.link: no rule');
    const NO_MARGIN = `.link { min-height: ${FLOOR}; padding-block: ${GROW}; }`;
    expect(whyNot(NO_MARGIN, '.link')).toContain('margin-block is absent');
    const WRONG_MARGIN = `.link { min-height: ${FLOOR}; padding-block: ${GROW}; margin-block: calc((1lh - 20px) / 2); }`;
    expect(whyNot(WRONG_MARGIN, '.link')).toContain('margin-block is calc((1lh - 20px) / 2)');
    const LITERAL = `.link { min-height: 24px; padding-block: ${GROW}; margin-block: ${BACK}; }`;
    expect(whyNot(LITERAL, '.link')).toContain('min-height is 24px');
  });

  it('reads a link that holds the floor, in one rule, in a selector list, and over two rules', () => {
    const ONE = `.link { min-height: ${FLOOR}; padding-block: ${GROW}; margin-block: ${BACK}; }`;
    expect(whyNot(ONE, '.link')).toBeNull();
    expect(whyNot(`.a, .link { min-height: ${FLOOR}; padding-block: ${GROW}; margin-block: ${BACK}; }`, '.link')).toBeNull();
    expect(whyNot(`.register a { color: red; }\n.register a { min-height: ${FLOOR}; padding-block: ${GROW}; margin-block: ${BACK}; }`, '.register a')).toBeNull();
  });

  it('reads the base stylesheet of a module as wrong, which is what the walk saw', () => {
    // The project row's name before this lane: font, weight and no decoration, a flex or grid item of one line (21 px).
    const BASE = '.name { min-width: 0; overflow-wrap: anywhere; font-size: var(--am-text-base); font-weight: 650; text-decoration: none; }';
    expect(whyNot(BASE, '.name')).not.toBeNull();
  });
});

describe('the links the walk named hold the floor and give the surplus back (lane TARGETS)', () => {
  const CASES: ReadonlyArray<{ readonly what: string; readonly css: readonly string[]; readonly selector: string }> = [
    { what: 'the project name in the project list', css: ['entities', 'project', 'ui', 'project-row.module.css'], selector: '.name' },
    { what: 'the project name on «Главная»', css: ['widgets', 'home-tiles', 'ui', 'home-tiles.module.css'], selector: '.project > a' },
    { what: 'the version title of a version row', css: ['entities', 'document-version', 'ui', 'version-row.module.css'], selector: '.title' },
    { what: 'the second link of a version row', css: ['entities', 'document-version', 'ui', 'version-row.module.css'], selector: '.secondary' },
    { what: '«все версии» of a document card', css: ['entities', 'document-version', 'ui', 'document-cards.module.css'], selector: '.history' },
    { what: '«К разделам проекта» of the empty section', css: ['_pages', 'section-detail', 'ui', 'section-detail-page.module.css'], selector: '.backLink' },
    { what: '«Подать заявку на доступ» of the sign-in card', css: ['_pages', 'sign-in', 'ui', 'sign-in-page.module.css'], selector: '.register a' },
  ];

  for (const { what, css, selector } of CASES) {
    it(`${what}: ${selector} is 24 px and costs its row nothing`, () => {
      expect(whyNot(source(...css), selector)).toBeNull();
    });
  }

  it('makes the one inline link an inline block, because an inline box takes padding without taking it into its line only so', () => {
    const rule = declared(source('_pages', 'section-detail', 'ui', 'section-detail-page.module.css'), '.backLink');
    expect(rule.get('display')).toBe('inline-block');
  });
});

describe('the markup carries the classes the stylesheets read (lane TARGETS)', () => {
  it('puts each class on its link', () => {
    // The tile's link carries no class (the rendered markup is pinned by `screens/home.test.ts`): `.project > a` reads its list item.
    expect(source('widgets', 'home-tiles', 'ui', 'recent-projects-tile.tsx')).toContain('<Link href={routes.project(project.project_uid)}>{project.name}</Link>');
    expect(source('entities', 'document-version', 'ui', 'document-cards.tsx')).toContain('<Link className={styles.history} href={documentHref} title="История версий документа">');
    expect(source('_pages', 'section-detail', 'ui', 'section-detail-page.tsx')).toContain('<Link className={styles.backLink} href={routes.project(projectUid)}>К разделам проекта</Link>');
    expect(source('entities', 'project', 'ui', 'project-row.tsx')).toContain('<Link className={styles.name} href=');
    expect(source('entities', 'document-version', 'ui', 'version-row.tsx')).toContain('<Link className={styles.title} href={href}>');
    expect(source('entities', 'document-version', 'ui', 'version-row.tsx')).toContain('<Link className={styles.secondary} href={secondary.href}>');
    expect(source('_pages', 'sign-in', 'ui', 'sign-in-page.tsx')).toContain('<p className={styles.register} data-sign-in-register="">');
  });
});
