/**
 * `UI-A-10`: the home page's «Последние проекты» states each project's audit, as the project list does -- the original's
 * object rows carry the state of their documents beside the name.
 *
 * The figures are the `audit_counts` the same `listProjects` answer carries on each item: the tile reads nothing more.
 * A project whose item carries none shows no figures (unknown is not zero), and a state at zero is left out of the line.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { queryKeys } from '@/shared/api';
import type { Project } from '@/shared/api';
import { RECENT_PROJECT_LIMIT, RecentProjectsTile } from '@/widgets/home-tiles';

import { auditCounts } from '../dashboard/audit-counts';
import { newClient, renderWith } from '../screens/harness';
import { PROJECTS, projectPage } from '../screens/home-fixtures';

const KEY = queryKeys.projects.list(undefined, RECENT_PROJECT_LIMIT);

function withCounts(project: Project, counts: Project['audit_counts']): Project {
  return counts === undefined ? project : { ...project, audit_counts: counts };
}

function tile(items: readonly Project[]): string {
  const client = newClient();
  client.setQueryData(KEY, projectPage(items));
  return renderWith(client, createElement(RecentProjectsTile));
}

/** The rows of the tile, one string of markup each. */
function rowsOf(markup: string): string[] {
  return markup.split('<li ').slice(1).map((row) => row.slice(0, row.indexOf('</li>')));
}

describe('the recent projects of the home page state their documents\' audit', () => {
  const [first, second, third] = PROJECTS as readonly [Project, Project, Project];
  const WAITING = auditCounts(12, { not_run: 4, awaiting_decision: 3, checked: 4, clean: 1, no_expert_decision: 7 });

  it('draws the line of the project\'s own counters under its name and date, and reads nothing more', () => {
    const markup = tile([withCounts(first, WAITING)]);
    const [row] = rowsOf(markup);
    expect(row).toContain('data-recent-project-figures=""');
    expect(row).toContain('data-audit-tally="12"');
    expect(row).toMatch(/data-tally="notRun"[^>]*>не запускались(?:<!-- -->)? <span[^>]*>4</);
    expect(row).toMatch(/data-tally="awaitingDecision"[^>]*>ждут решения(?:<!-- -->)? <span[^>]*>3</);
    expect(row).toMatch(/data-tally="checked"[^>]*>проверено(?:<!-- -->)? <span[^>]*>4</);
    expect(row).toContain('aria-label="Состояние проверки: ' + first.name + '"');
    // The name, the date and the link are what they were.
    expect(row).toContain(first.name);
    expect(row).toContain('создан');
  });

  it('leaves a state at zero out of the line, and a project with no documents says only its total', () => {
    const [row] = rowsOf(tile([withCounts(first, auditCounts(0))]));
    expect(row).toContain('data-audit-tally="0"');
    expect(row).not.toContain('data-tally="notRun"');
    expect(row).not.toContain('data-tally="awaitingDecision"');
  });

  it('draws no figures for a project whose item carries no counters: unknown is not zero', () => {
    const rows = rowsOf(tile([withCounts(first, WAITING), second, third]));
    expect(rows).toHaveLength(3);
    expect(rows[0]).toContain('data-audit-tally');
    for (const row of rows.slice(1)) {
      expect(row).not.toContain('data-audit-tally');
      expect(row).not.toContain('data-recent-project-figures');
    }
  });

  it('keeps one row per project, each with its own figures, in the answer\'s order', () => {
    const rows = rowsOf(tile([
      withCounts(first, auditCounts(5, { not_run: 1, checked: 4, no_expert_decision: 1 })),
      withCounts(second, auditCounts(2, { not_run: 0, awaiting_decision: 2, no_expert_decision: 2 })),
    ]));
    expect(rows[0]).toContain(first.name);
    expect(rows[0]).toContain('data-audit-tally="5"');
    expect(rows[0]).not.toContain('data-tally="awaitingDecision"');
    expect(rows[1]).toContain(second.name);
    expect(rows[1]).toContain('data-audit-tally="2"');
    expect(rows[1]).toContain('data-tally="awaitingDecision"');
  });
});
