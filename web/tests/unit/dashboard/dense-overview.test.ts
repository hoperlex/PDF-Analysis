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
import { PROJECT_SECTIONS } from '@/entities/project';
import { Dashboard } from '@/widgets/dashboard';

import { WEB_ROOT } from '../../guards/lib/repo';
import { parseRules } from '../styles/contrast';
import { newClient, renderWith } from '../screens/harness';
import { sectionAudit } from './audit-counts';

const module = (path: string): string => readFileSync(join(WEB_ROOT, 'src', path), 'utf8');

/** The declarations of the first rule whose selector is exactly `selector`. */
function declarations(css: string, selector: string): ReadonlyMap<string, string> {
  const rule = parseRules(css, 'module').find((entry) => entry.selector === selector);
  if (rule === undefined) throw new Error(`no rule ${selector}`);
  return rule.declarations;
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
    expect(markup).toContain('>Сводка по проектам</h2>');
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
    for (const rule of parseRules(sections, 'module')) {
      expect(rule.declarations.get('min-height'), `${rule.selector} keeps a fixed height`).toBeUndefined();
    }
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
    expect(total).toContain('Итого по разделам');
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

  it('greets in the page-title size on a band no larger than the tiles under it', () => {
    expect(declarations(home, '.greeting').get('font-size')).toBe('var(--am-text-2xl)');
    expect(declarations(home, '.hero').get('padding')).toBe('var(--am-gap)');
    expect(declarations(home, '.hero').get('border-radius')).toBe('var(--am-radius)');
  });
});

describe("a section's arrow opens the section in one click when a project is chosen", () => {
  const PROJECT = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B' as ProjectUid;
  const render = (projectUid: ProjectUid | null): string => {
    const client = newClient();
    client.setQueryData(queryKeys.dashboard.summary(projectUid), SUMMARY);
    return renderWith(client, createElement(Dashboard, { projectUid }));
  };

  it('is a link to the project’s section page for every section', () => {
    const markup = render(PROJECT);
    for (const section of PROJECT_SECTIONS) {
      expect(markup, section.code).toContain(`data-section-open="${section.code}"`);
      expect(markup, section.code).toContain(`href="/projects/${PROJECT}/sections/${section.code}"`);
    }
  });

  it('is only an arrow across all projects, where there is no one section page to open', () => {
    expect(render(null)).not.toContain('data-section-open');
  });
});
