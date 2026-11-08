/**
 * `UI-A-04`: «Разделы» in the side menu — the current project's sections, each with its mark and a count badge,
 * leading to the section page (`R-151l`).
 *
 * The model is pure and read as data (`sectionNavigationOf`); the markup is read off a static pass of the frame's
 * navigation, in all three of its states; and the wiring (a project in the address, the dashboard's summary of that
 * project, no read without one) is read off a mounted frame over a seeded cache, the way
 * `project-switcher.test.ts` reads the selector.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

import { FrameNavigation, FrameNavigationView } from '@/_app/frame-navigation';
import { buildNavigation, offersSectionNavigation } from '@/_app/navigation';
import {
  SECTIONS_EMPTY_NOTE,
  SECTIONS_FAILED_NOTE,
  SECTIONS_GROUP_LABEL,
  SECTIONS_LOADING_NOTE,
  sectionEntryLabel,
  sectionNavigationOf,
  sectionsSummary,
  sectionsSummaryLabel,
} from '@/_app/section-navigation';
import type { SectionNavigation } from '@/_app/section-navigation';
import { RUN_STATE_VALUES, queryKeys } from '@/shared/api';
import type { DashboardSummary, ProjectSection, ProjectUid, SectionDocumentCount } from '@/shared/api';
import { routes } from '@/shared/lib';
import { PROJECT_SECTIONS } from '@/entities/project';

import { sectionAudit } from '../dashboard/audit-counts';
import { newClient, renderWith, seedError } from '../screens/harness';
import { ADMIN_ONLY, DEFAULT_CREDENTIAL, EXPERT, INCOMPLETE_PROFILE, NO_ROLES } from './subjects';

const navigationState = vi.hoisted(() => ({ pathname: null as string | null, search: '' }));

vi.mock('next/navigation', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  usePathname: () => navigationState.pathname,
  useSearchParams: () => new URLSearchParams(navigationState.search),
}));

const PROJECT = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const OTHER = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8C';

/** The fifteen rows of `section_breakdown`, with the given counts and zero elsewhere, and the «Без раздела» bucket. */
function rows(counts: Partial<Record<ProjectSection, number>>, unclassified = 7): SectionDocumentCount[] {
  return [
    ...PROJECT_SECTIONS.map((section) => ({
      section: section.code,
      document_count: counts[section.code] ?? 0,
      ...sectionAudit(counts[section.code] ?? 0),
    })),
    { document_count: unclassified, ...sectionAudit(unclassified) },
  ];
}

function summaryOf(sectionRows: SectionDocumentCount[]): DashboardSummary {
  return {
    documents_by_project: [{ project_uid: PROJECT, name: 'Мост через Неву', document_count: 9 }],
    findings_by_verdict: [
      { verdict: 'pending', count: 0 },
      { verdict: 'accepted', count: 0 },
      { verdict: 'rejected', count: 0 },
      { verdict: 'needs_manual_review', count: 0 },
    ],
    run_activity: { by_state: RUN_STATE_VALUES.map((state) => ({ state, count: 0 })) },
    section_breakdown: sectionRows,
    awaiting_decision_findings: 0,
  };
}

// `AR` and `KJ` with documents, and `PS` with one: the structure order (`S-5`) is AR, PS, KJ.
const COUNTS: Partial<Record<ProjectSection, number>> = { KJ: 2, AR: 4, PS: 1 };
const sectionPage = (code: string, project = PROJECT): string => routes.projectSection(project, code);

describe('sectionNavigationOf — the sections of the current project', () => {
  it('lists only the sections that hold documents, in the order of the project structure', () => {
    const result = sectionNavigationOf(rows(COUNTS), PROJECT, null);
    expect(result.status).toBe('ready');
    if (result.status !== 'ready') return;
    expect(result.entries.map((entry) => [entry.code, entry.abbr, entry.count])).toEqual([
      ['AR', 'АР', 4],
      ['PS', 'ПЗ', 1],
      ['KJ', 'КЖ', 2],
    ]);
  });

  it('leads each entry to the section page of that project, through the route helper', () => {
    const result = sectionNavigationOf(rows(COUNTS), PROJECT, null);
    if (result.status !== 'ready') throw new Error('not ready');
    expect(result.entries.map((entry) => entry.href)).toEqual([sectionPage('AR'), sectionPage('PS'), sectionPage('KJ')]);
  });

  it('marks the entry whose page is shown current, and no other: not another project\'s page, not the project page', () => {
    const current = (pathname: string | null): string[] => {
      const result = sectionNavigationOf(rows(COUNTS), PROJECT, pathname);
      if (result.status !== 'ready') throw new Error('not ready');
      return result.entries.filter((entry) => entry.current).map((entry) => entry.code);
    };
    expect(current(sectionPage('KJ'))).toEqual(['KJ']);
    expect(current(sectionPage('KJ', OTHER))).toEqual([]);
    expect(current(routes.project(PROJECT))).toEqual([]);
    expect(current(null)).toEqual([]);
  });

  it('is an empty list, not a failure, for a project none of whose documents is confirmed for a section', () => {
    expect(sectionNavigationOf(rows({}), PROJECT, null)).toEqual({ status: 'ready', entries: [] });
  });

  it('never lists the «Без раздела» bucket as a section, whatever it counts', () => {
    const result = sectionNavigationOf(rows({ AR: 1 }, 40), PROJECT, null);
    if (result.status !== 'ready') throw new Error('not ready');
    expect(result.entries.map((entry) => entry.code)).toEqual(['AR']);
  });

  it('is a failure, not a shorter list, when the breakdown is not whole: a section missing, repeated or unknown', () => {
    const whole = rows(COUNTS);
    expect(sectionNavigationOf(whole, PROJECT, null).status).toBe('ready');
    expect(sectionNavigationOf(whole.filter((row) => row.section !== 'OV'), PROJECT, null)).toEqual({ status: 'failed' });
    expect(sectionNavigationOf([...whole, whole[0] as SectionDocumentCount], PROJECT, null)).toEqual({ status: 'failed' });
    const unknown = whole.map((row, index) => (index === 0 ? { ...row, section: 'ZZ' as ProjectSection } : row));
    expect(sectionNavigationOf(unknown, PROJECT, null)).toEqual({ status: 'failed' });
  });

  it('names an entry by its mark, its name and its count, which the badge shortens to a number', () => {
    const result = sectionNavigationOf(rows(COUNTS), PROJECT, null);
    if (result.status !== 'ready') throw new Error('not ready');
    expect(sectionEntryLabel(result.entries[0] as (typeof result.entries)[number])).toBe('АР Архитектурные решения, документов: 4');
  });
});

/** The same rows with `awaiting_decision` set per section; a section named in `without` has no counts at all. */
function rowsAwaiting(
  counts: Partial<Record<ProjectSection, number>>,
  awaiting: Partial<Record<ProjectSection, number>>,
  without: readonly ProjectSection[] = [],
): SectionDocumentCount[] {
  return rows(counts).map((row) => {
    if (row.section === undefined) return row;
    if (without.includes(row.section)) {
      const bare: Partial<SectionDocumentCount> = { ...row };
      delete bare.audit_counts;
      return bare as SectionDocumentCount;
    }
    const waiting = awaiting[row.section] ?? 0;
    return { ...row, ...sectionAudit(row.document_count, { awaiting_decision: waiting, no_expert_decision: waiting }) };
  });
}

describe('UI-A-05: the documents of a section that no expert has checked', () => {
  const entriesOf = (sectionRows: SectionDocumentCount[]) => {
    const result = sectionNavigationOf(sectionRows, PROJECT, null);
    if (result.status !== 'ready') throw new Error('not ready');
    return result.entries;
  };

  it('is the row\'s audit_counts.awaiting_decision, and null where the row carries no counts: unknown is not zero', () => {
    const entries = entriesOf(rowsAwaiting(COUNTS, { AR: 3, PS: 0, KJ: 9 }, ['KJ']));
    expect(entries.map((entry) => [entry.code, entry.awaitingDecision])).toEqual([['AR', 3], ['PS', 0], ['KJ', null]]);
  });

  it('is the awaiting_decision figure and not the wider no_expert_decision, which counts the documents never run', () => {
    // 4 documents in AR: 1 waits for a decision, 3 were never run (`no_expert_decision` = 4).
    const row = { section: 'AR' as ProjectSection, document_count: 4, ...sectionAudit(4, { not_run: 3, awaiting_decision: 1, no_expert_decision: 4 }) };
    const [entry] = entriesOf([...rows({}).filter((other) => other.section !== 'AR'), row]);
    expect(entry?.awaitingDecision).toBe(1);
  });

  it('adds what the red number counts to the entry\'s name, only when there is one', () => {
    const labels = entriesOf(rowsAwaiting(COUNTS, { AR: 3 }, ['KJ'])).map(sectionEntryLabel);
    expect(labels).toEqual([
      'АР Архитектурные решения, документов: 4, не проверено экспертом: 3',
      'ПЗ Пояснительная записка, документов: 1',
      'КЖ Конструкции железобетонные, документов: 2',
    ]);
  });
});

describe('offersSectionNavigation — who is offered the group', () => {
  it('a complete session holding a role, and not a guest, a default credential, an incomplete profile or no role', () => {
    expect(offersSectionNavigation(EXPERT)).toBe(true);
    expect(offersSectionNavigation(ADMIN_ONLY)).toBe(true);
    for (const subject of [null, DEFAULT_CREDENTIAL, INCOMPLETE_PROFILE, NO_ROLES]) {
      expect(offersSectionNavigation(subject), String(subject?.login)).toBe(false);
    }
  });

  it('can fail: a registry without the section page offers nothing', () => {
    expect(offersSectionNavigation(EXPERT, [])).toBe(false);
  });
});

// ------------------------------------------------------------------------------------------- markup

const READY: SectionNavigation = sectionNavigationOf(rows(COUNTS), PROJECT, null);
const READY_ON_KJ: SectionNavigation = sectionNavigationOf(rows(COUNTS), PROJECT, sectionPage('KJ'));

function draw(sections: SectionNavigation | undefined, pathname: string | null = routes.project(PROJECT)): string {
  return renderToStaticMarkup(
    createElement(FrameNavigationView, { navigation: buildNavigation(EXPERT), pathname, projectUid: PROJECT, sections }),
  );
}

/** The name text of every button, in document order: what stands before any counter the button carries (`D-360`). */
const buttons = (markup: string): string[] => [...markup.matchAll(/<button\b[^>]*>([^<]*)/g)].map((m) => m[1] as string);

/** The attributes of the «Разделы» group buttons. */
const sectionButtons = (markup: string): string[] =>
  [...markup.matchAll(/<button\b([^>]*)>Разделы(?=<|<\/button>)/g)].map((m) => m[1] as string);

/** The inside of every «Разделы» group button, after its name (the counters of `D-360`), in document order. */
const sectionButtonInsides = (markup: string): string[] =>
  [...markup.matchAll(/<button\b[^>]*>Разделы(.*?)<\/button>/g)].map((m) => m[1] as string);

/** The `href` of every section link carrying `aria-current="page"`, whatever the attribute order. */
const currentSectionLinks = (markup: string): string[] =>
  [...markup.matchAll(/<a\b([^>]*)>/g)]
    .map((m) => m[1] as string)
    .filter((attributes) => /\baria-current="page"/.test(attributes))
    .map((attributes) => /\bhref="([^"]*)"/.exec(attributes)?.[1] ?? '')
    .filter((href) => href.includes('/sections/'));

/** The visible text of the markup: tags and their attributes removed. */
const textOf = (markup: string): string => markup.replace(/<[^>]*>/g, ' ');

describe('the «Разделы» group in the menu', () => {
  it('follows «Работа» in the bar and in the stacked menu, and is drawn nowhere without a project\'s sections', () => {
    expect(buttons(draw(READY))).toEqual([
      'Работа', 'Разделы', 'Знания', 'Система',
      'Меню', 'Работа', 'Разделы', 'Знания', 'Система',
    ]);
    expect(buttons(draw(undefined))).toEqual(['Работа', 'Знания', 'Система', 'Меню', 'Работа', 'Знания', 'Система']);
    expect(draw(undefined)).not.toContain('data-section-nav');
  });

  it('draws one link per section: the mark, a badge with the count, the name as tooltip and the full name as its name', () => {
    const markup = draw(READY);
    const items = [...markup.matchAll(/<li class="am-disclosure__item" data-section-nav-item="([A-Z]+)">(.*?)<\/li>/g)];
    // Once in the bar and once in the stacked menu.
    expect(items.map((m) => m[1])).toEqual(['AR', 'PS', 'KJ', 'AR', 'PS', 'KJ']);
    const first = items[0]?.[2] ?? '';
    expect(first).toContain(`href="${sectionPage('AR')}"`);
    expect(first).toContain('aria-label="АР Архитектурные решения, документов: 4"');
    expect(first).toContain('title="Архитектурные решения"');
    expect(first).toMatch(/>АР<\/span><span class="[^"]*"><span class="[^"]*">4<\/span><\/span>/);
  });

  it('shows the Cyrillic marks and numbers and never the Latin code as text', () => {
    const text = textOf(draw(READY));
    expect(text).toContain('АР');
    expect(text).not.toMatch(/\b(?:AR|PS|KJ)\b/);
    expect(draw(READY)).toContain('data-section-nav-item="AR"');
  });

  it('marks the section page shown aria-current="page", and its group; it opens the group, which is closed otherwise', () => {
    const on = draw(READY_ON_KJ, sectionPage('KJ'));
    // The bar, the compact rail and the stacked menu each draw the page shown as current.
    expect(currentSectionLinks(on)).toEqual([sectionPage('KJ'), sectionPage('KJ'), sectionPage('KJ')]);
    const [bar, stacked] = sectionButtons(on);
    expect(bar).toContain('aria-expanded="true"');
    expect(bar).toContain('aria-current="true"');
    expect(stacked).toContain('aria-current="true"');

    const off = draw(READY);
    for (const attributes of sectionButtons(off)) {
      expect(attributes).toContain('aria-expanded="false"');
      expect(attributes).not.toContain('aria-current');
    }
    expect(currentSectionLinks(off)).toEqual([]);
  });

  it('is a disclosure button naming its panel, as the other groups are', () => {
    for (const attributes of sectionButtons(draw(READY))) {
      expect(attributes).toMatch(/aria-controls="[^"]+panel"/);
      expect(attributes).toContain('type="button"');
    }
  });

  it('says why there is no list, in words: still reading, could not be read whole, or no section holds a document', () => {
    const note = (sections: SectionNavigation): string | null =>
      /<p class="[^"]*" data-section-nav-status="([a-z]+)">([^<]*)<\/p>/.exec(draw(sections))?.slice(1).join('|') ?? null;
    expect(note({ status: 'loading' })).toBe(`loading|${SECTIONS_LOADING_NOTE}`);
    expect(note({ status: 'failed' })).toBe(`failed|${SECTIONS_FAILED_NOTE}`);
    expect(note({ status: 'ready', entries: [] })).toBe(`empty|${SECTIONS_EMPTY_NOTE}`);
    expect(draw({ status: 'failed' })).not.toContain('data-section-nav-item');
  });

  it('the compact rail holds a labelled group of mark links, only when there is a list', () => {
    const rail = (markup: string): string => /<div class="[^"]*" data-nav-state="rail">(.*?)<div class="[^"]*" data-nav-state="stacked">/s.exec(markup)?.[1] ?? '';
    const group = /<div class="[^"]*" role="group" aria-label="Разделы"[^>]*>(.*?)<\/div>/s.exec(rail(draw(READY_ON_KJ, sectionPage('KJ'))));
    expect(group, 'no rail group').not.toBeNull();
    const links = [...(group?.[1] ?? '').matchAll(/<a\b([^>]*)>(.*?)<\/a>/g)];
    expect(links.map((m) => /aria-label="([^"]*)"/.exec(m[1] as string)?.[1])).toEqual([
      'АР Архитектурные решения, документов: 4',
      'ПЗ Пояснительная записка, документов: 1',
      'КЖ Конструкции железобетонные, документов: 2',
    ]);
    expect(links.map((m) => /aria-current="page"/.test(m[1] as string))).toEqual([false, false, true]);
    expect(links.map((m) => textOf(m[2] as string).trim())).toEqual(['АР', 'ПЗ', 'КЖ']);
    for (const sections of [undefined, { status: 'loading' } as const, { status: 'failed' } as const, { status: 'ready', entries: [] } as const]) {
      expect(rail(draw(sections)), JSON.stringify(sections)).not.toContain(`aria-label="${SECTIONS_GROUP_LABEL}"`);
    }
  });

  describe('the red badge of UI-A-05', () => {
    const WAITING: SectionNavigation = sectionNavigationOf(rowsAwaiting(COUNTS, { AR: 3, KJ: 120 }), PROJECT, null);
    const itemsOf = (markup: string): Map<string, string[]> => {
      const found = new Map<string, string[]>();
      for (const match of markup.matchAll(/<li class="am-disclosure__item" data-section-nav-item="([A-Z]+)">(.*?)<\/li>/g)) {
        found.set(match[1] as string, [...(found.get(match[1] as string) ?? []), match[2] as string]);
      }
      return found;
    };
    const alerts = (item: string): string[] =>
      [...item.matchAll(/<span class="[^"]*" title="([^"]*)" data-menu-badge="alert">([^<]*)<\/span>/g)].map((m) => `${m[2]}|${m[1]}`);

    it('stands before the count in the bar and in the stacked menu, on the sections that wait, and nowhere else', () => {
      const found = itemsOf(draw(WAITING));
      // Once in the bar and once in the stacked menu.
      expect(found.get('AR')).toHaveLength(2);
      for (const item of found.get('AR') ?? []) {
        expect(alerts(item)).toEqual([
          '3|Не проверено экспертом: 3. Документы с замечаниями, по которым эксперт ещё не принял решения. Документы, которые не анализировались, не считаются.',
        ]);
        expect(item.indexOf('data-menu-badge="alert"')).toBeLessThan(item.lastIndexOf('>4<'));
        expect(item).toContain('aria-label="АР Архитектурные решения, документов: 4, не проверено экспертом: 3"');
      }
      for (const item of found.get('PS') ?? []) expect(alerts(item)).toEqual([]);
      expect(draw(READY)).not.toContain('data-menu-badge');
    });

    it('shows 99+ past two digits and keeps the exact figure in the tooltip and the name', () => {
      const kj = itemsOf(draw(WAITING)).get('KJ')?.[0] ?? '';
      expect(alerts(kj)).toHaveLength(1);
      expect(kj).toContain('>99+<');
      expect(kj).toContain('title="Не проверено экспертом: 120.');
      expect(kj).toContain('не проверено экспертом: 120"');
    });

    it('rides the corner of the glyph in the compact rail, and the link\'s name says what it counts', () => {
      const rail = /<div class="[^"]*" data-nav-state="rail">(.*?)<div class="[^"]*" data-nav-state="stacked">/s.exec(draw(WAITING))?.[1] ?? '';
      const links = [...rail.matchAll(/<a\b([^>]*)>(.*?)<\/a>/g)].filter((m) => (m[1] as string).includes('/sections/'));
      expect(links.map((m) => /aria-label="([^"]*)"/.exec(m[1] as string)?.[1])).toEqual([
        'АР Архитектурные решения, документов: 4, не проверено экспертом: 3',
        'ПЗ Пояснительная записка, документов: 1',
        'КЖ Конструкции железобетонные, документов: 2, не проверено экспертом: 120',
      ]);
      expect(links.map((m) => (m[2] as string).includes('data-menu-badge="alert"'))).toEqual([true, false, true]);
      expect(links.map((m) => /aria-hidden="true"><span[^>]*data-menu-badge="alert">([^<]*)</.exec(m[2] as string)?.[1] ?? null)).toEqual(['3', null, '99+']);
    });
  });

  describe('D-360: the group\'s own counters, seen while it is folded', () => {
    const WAITING: SectionNavigation = sectionNavigationOf(rowsAwaiting(COUNTS, { AR: 3, KJ: 2 }), PROJECT, null);
    const pills = (inside: string): string[] => [...inside.matchAll(/data-menu-badge="(\w+)">([^<]*)</g)].map((m) => `${m[1]}:${m[2]}`);
    const total = (inside: string): string | null => /data-section-nav-total="(\d+)"[^>]*>(\d+)</.exec(inside)?.slice(1).join('>') ?? null;

    it('sums the sections\' red figures and their documents, and says so in words', () => {
      const result = sectionNavigationOf(rowsAwaiting(COUNTS, { AR: 3, KJ: 2 }), PROJECT, null);
      if (result.status !== 'ready') throw new Error('not ready');
      expect(sectionsSummary(result.entries)).toEqual({ documents: 7, awaitingDecision: 5 });
      expect(sectionsSummaryLabel(sectionsSummary(result.entries))).toBe('Не проверено экспертом: 5. Документов в разделах: 7');
      // No red clause when nothing waits, and an unknown red figure is unknown, not zero.
      expect(sectionsSummary([{ count: 4, awaitingDecision: null }, { count: 1, awaitingDecision: null }])).toEqual({ documents: 5, awaitingDecision: null });
      expect(sectionsSummaryLabel({ documents: 5, awaitingDecision: null })).toBe('Документов в разделах: 5');
      expect(sectionsSummaryLabel({ documents: 5, awaitingDecision: 0 })).toBe('Документов в разделах: 5');
      expect(sectionsSummary([{ count: 4, awaitingDecision: null }, { count: 1, awaitingDecision: 2 }])).toEqual({ documents: 5, awaitingDecision: 2 });
    });

    it('stands on the button of the closed group, in the bar and in the stacked menu, red before grey, named in the button\'s name', () => {
      const markup = draw(WAITING);
      const insides = sectionButtonInsides(markup);
      expect(insides).toHaveLength(2);
      for (const inside of insides) {
        expect(pills(inside)).toEqual(['alert:5']);
        expect(total(inside)).toBe('7>7');
        expect(inside.indexOf('data-menu-badge="alert"')).toBeLessThan(inside.indexOf('data-section-nav-total'));
      }
      for (const attributes of sectionButtons(markup)) {
        expect(attributes).toContain('aria-expanded="false"');
        expect(attributes).toContain('aria-label="Разделы. Не проверено экспертом: 5. Документов в разделах: 7"');
      }
      // The button is still found by its name's first words, and the group's links are as they were.
      expect(buttons(markup)).toEqual(['Работа', 'Разделы', 'Знания', 'Система', 'Меню', 'Работа', 'Разделы', 'Знания', 'Система']);
    });

    it('draws only the grey figure when no section waits, and the red one stays out of the name', () => {
      const markup = draw(READY);
      for (const inside of sectionButtonInsides(markup)) {
        expect(pills(inside)).toEqual([]);
        expect(total(inside)).toBe('7>7');
      }
      for (const attributes of sectionButtons(markup)) expect(attributes).toContain('aria-label="Разделы. Документов в разделах: 7"');
    });

    it('draws nothing while the list is loading, failed or empty: a figure not read is no badge', () => {
      for (const sections of [{ status: 'loading' } as const, { status: 'failed' } as const, { status: 'ready', entries: [] } as const, undefined]) {
        const markup = draw(sections);
        expect(sectionButtonInsides(markup).every((inside) => inside === ''), JSON.stringify(sections)).toBe(true);
        for (const attributes of sectionButtons(markup)) expect(attributes, JSON.stringify(sections)).not.toContain('aria-label');
        expect(markup, JSON.stringify(sections)).not.toContain('data-section-nav-total');
      }
    });

    it('stays when the group is open, and leaves the other groups\' buttons as they were', () => {
      const on = draw(sectionNavigationOf(rowsAwaiting(COUNTS, { KJ: 2 }), PROJECT, sectionPage('KJ')), sectionPage('KJ'));
      const [bar] = sectionButtons(on);
      expect(bar).toContain('aria-expanded="true"');
      expect(sectionButtonInsides(on).map(pills)).toEqual([['alert:2'], ['alert:2']]);
      const others = [...on.matchAll(/<button\b([^>]*)>(Работа|Знания|Система|Меню)/g)];
      expect(others).toHaveLength(8);
      for (const other of others) expect(other[1], String(other[2])).not.toContain('aria-label');
    });

    it('the rail has no group button: its links carry their own figures, as before', () => {
      const rail = /<div class="[^"]*" data-nav-state="rail">(.*?)<div class="[^"]*" data-nav-state="stacked">/s.exec(draw(WAITING))?.[1] ?? '';
      expect(rail).not.toContain('data-section-nav-total');
    });
  });

  it('does not touch the other groups: the same links, in the same order, with or without it', () => {
    const hrefs = (markup: string): string[] =>
      [...markup.matchAll(/<a\b[^>]*\bhref="([^"]*)"/g)].map((m) => m[1] as string).filter((href) => !href.includes('/sections/'));
    expect(hrefs(draw(READY))).toEqual(hrefs(draw(undefined)));
  });
});

// ------------------------------------------------------------------------------------------- wiring

describe('the frame reads the current project\'s sections only where it is offered one', () => {
  const frame = (client: ReturnType<typeof newClient>, offersSections: boolean): string =>
    renderWith(client, createElement(FrameNavigation, { navigation: buildNavigation(EXPERT), offersSections }));

  const summaryKey = (project: string) => queryKeys.dashboard.summary(project as ProjectUid);

  /**
   * The reads of the dashboard's summary that the frame filed. The frame files the menu's own counters too (the queue,
   * the knowledge base: `menu-badges.test.ts`), which are not what these cases are about.
   */
  const summaryReads = (client: ReturnType<typeof newClient>): number =>
    client.getQueryCache().getAll().filter((query) => query.queryKey[0] === 'dashboard').length;

  function seeded(): ReturnType<typeof newClient> {
    const client = newClient();
    client.setQueryData(summaryKey(PROJECT), summaryOf(rows(COUNTS)));
    return client;
  }

  it('on a required screen, the project of the path: lists its sections from the dashboard\'s summary entry', () => {
    navigationState.pathname = sectionPage('KJ');
    navigationState.search = '';
    const markup = frame(seeded(), true);
    expect([...markup.matchAll(/data-section-nav-item="([A-Z]+)"/g)].map((m) => m[1])).toEqual(['AR', 'PS', 'KJ', 'AR', 'PS', 'KJ']);
    expect(currentSectionLinks(markup)).toEqual([sectionPage('KJ'), sectionPage('KJ'), sectionPage('KJ')]);
  });

  it('on an optional screen, the project of ?project=, which the dashboard follows too', () => {
    navigationState.pathname = '/dashboard';
    navigationState.search = `project=${PROJECT}`;
    const markup = frame(seeded(), true);
    expect(markup).toContain('data-section-nav-item="AR"');
    expect(markup).toContain(`href="${sectionPage('AR')}"`);
  });

  it('holds only that project\'s entry: another project\'s summary is not shown for this one', () => {
    navigationState.pathname = routes.project(OTHER);
    navigationState.search = '';
    const client = seeded();
    const markup = frame(client, true);
    expect(markup).not.toContain('data-section-nav-item');
    expect(markup).toContain(`data-section-nav-status="loading"`);
    expect(client.getQueryCache().find({ queryKey: summaryKey(OTHER) })).toBeDefined();
  });

  it('asks the server on a cold load: the group says it is reading, under the summary key of that project', () => {
    navigationState.pathname = routes.project(PROJECT);
    navigationState.search = '';
    const client = newClient();
    const markup = frame(client, true);
    expect(markup).toContain('data-section-nav-status="loading"');
    expect(client.getQueryCache().find({ queryKey: summaryKey(PROJECT) })?.state.status).toBe('pending');
  });

  it('draws nothing, and files no read, with no project in the address', () => {
    navigationState.pathname = '/dashboard';
    navigationState.search = '';
    const client = seeded();
    const before = summaryReads(client);
    const markup = frame(client, true);
    expect(markup).not.toContain('data-section-nav');
    expect(buttons(markup)).not.toContain('Разделы');
    expect(summaryReads(client)).toBe(before);
  });

  it('draws nothing, and files no read, for a session that is not offered it', () => {
    navigationState.pathname = routes.project(PROJECT);
    navigationState.search = '';
    const client = newClient();
    const markup = frame(client, false);
    expect(markup).not.toContain('data-section-nav');
    expect(summaryReads(client)).toBe(0);
  });

  it('draws nothing, and files no read, for a project the address does not spell as one', () => {
    navigationState.pathname = routes.project('не-проект');
    navigationState.search = '';
    const client = newClient();
    const markup = frame(client, true);
    expect(markup).not.toContain('data-section-nav');
    expect(summaryReads(client)).toBe(0);
  });

  it('says it could not read the sections when the summary failed and none is held', () => {
    navigationState.pathname = routes.project(PROJECT);
    navigationState.search = '';
    const client = newClient();
    seedError(client, summaryKey(PROJECT), new Error('нет связи'));
    const markup = frame(client, true);
    expect(markup).toContain('data-section-nav-status="failed"');
  });
});
