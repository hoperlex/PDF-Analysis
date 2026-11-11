/**
 * A confirmed АР version starts an ordinary Run with the original-source text profile: its start form is the form of every
 * other section, with no choice of analysis, and its run table names no analysis.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ProjectSection } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { RUN_PAGE_LIMIT } from '@/entities/audit-run';
import { RunList } from '@/widgets/run-list';

import { PROJECT_UID, VERSION_UID, runStatus } from '../review/fixtures';
import { newClient, renderScreen } from './harness';

type Client = ReturnType<typeof newClient>;

function listClient(withRuns: boolean): Client {
  const client = newClient();
  client.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), {
    items: withRuns ? [runStatus()] : [], page: { next_cursor: null },
  });
  return client;
}

function markupOf(client: Client, sectionCode: ProjectSection | null | undefined): string {
  return renderScreen(
    client,
    createElement(RunList, { projectUid: PROJECT_UID, versionUid: VERSION_UID, sectionCode }),
  );
}

describe('the default АР start', () => {
  for (const withRuns of [false, true]) {
    it(`offers an ordinary Run when ${withRuns ? 'runs exist' : 'no run exists'}`, () => {
      const markup = markupOf(listClient(withRuns), 'AR');
      expect(markup).toContain('data-start-run-control="true"');
      // `RUN-START-ONE-01a`: one «Запустить», enabled (it reads the estimate itself), and no estimate step before it.
      expect(markup).toMatch(/<button type="button" class="am-button" data-start-run-button="">Запустить<\/button>/);
      expect(markup).not.toContain('Оценить стоимость');
      expect(markup).not.toContain('data-cost-approval'); // no estimate, so no agreement yet
      // `af581631`: the temporary statistics mode of the ordinary start is a «▾» item, not a tick-box.
      expect(markup).toContain('>Без денежного потолка (сбор статистики)</button>');
      expect(markup).not.toContain('Временный режим сбора статистики');
      expect(markup).not.toContain('Повышенные лимиты ИИ-анализа');
      expect(markup).not.toContain('data-ar-start-note');
      // No choice of analysis: no radio group and no wrapper of one around the form.
      expect(markup).not.toContain('data-analysis-start');
      expect(markup).not.toContain('type="radio"');
    });
  }

  it('names no analysis in the run table of an АР version, and links no group review', () => {
    const markup = markupOf(listClient(true), 'AR');
    expect(markup).not.toContain('data-run-analysis');
    expect(markup).not.toContain('data-run-group-review');
  });

  it('labels АР and another section accurately', () => {
    expect(markupOf(listClient(true), 'AR')).toContain('Запустить анализ АР');
    expect(markupOf(listClient(true), 'KJ')).toContain('Запустить ещё один прогон');
  });
});

it('other sections also retain the ordinary start', () => {
  for (const section of ['KJ', 'PB', 'AI', null, undefined] as const) {
    const markup = markupOf(listClient(false), section);
    expect(markup).toContain('data-start-run-control="true"');
    expect(markup).toMatch(/<button type="button" class="am-button" data-start-run-button="">Запустить<\/button>/);
    expect(markup).not.toContain('Оценить стоимость');
  }
});
