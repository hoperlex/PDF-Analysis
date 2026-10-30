/** A confirmed АР version starts an ordinary Run with the original-source text profile. */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ProjectSection } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { RUN_PAGE_LIMIT } from '@/entities/audit-run';
import { RunList } from '@/widgets/run-list';

import { NOT_INSTALLED_PACK, installedPackFixture } from '../analysis-settings/ar-v3-beta-pack-fixtures';
import { PROJECT_UID, VERSION_UID, runStatus } from '../review/fixtures';
import { newClient, renderScreen } from './harness';

type Client = ReturnType<typeof newClient>;
const PACK = queryKeys.runs.arV3PackStatus();

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
    for (const pack of ['installed', 'not installed', 'loading'] as const) {
      it(`offers an ordinary Run when ${withRuns ? 'runs exist' : 'no run exists'} and the old pack is ${pack}`, () => {
        const client = listClient(withRuns);
        if (pack === 'installed') client.setQueryData(PACK, installedPackFixture());
        if (pack === 'not installed') client.setQueryData(PACK, NOT_INSTALLED_PACK);
        const markup = markupOf(client, 'AR');
        expect(markup).toContain('data-start-run-control="true"');
        expect(markup).toContain('>Запустить прогон</button>');
        expect(markup).toContain('Повышенные лимиты ИИ-анализа');
        expect(markup).not.toContain('data-ar-v3-group-start');
        expect(markup).not.toContain('data-ar-start-note');
      });
    }
  }

  it('labels АР and another section accurately', () => {
    expect(markupOf(listClient(true), 'AR')).toContain('Запустить анализ АР');
    expect(markupOf(listClient(true), 'KJ')).toContain('Запустить ещё один прогон');
  });
});

it('other sections also retain the ordinary start', () => {
  for (const section of ['KJ', 'PB', 'AI', null, undefined] as const) {
    const markup = markupOf(listClient(false), section);
    expect(markup).toContain('data-start-run-control="true"');
    expect(markup).not.toContain('data-ar-v3-group-start');
  }
});
