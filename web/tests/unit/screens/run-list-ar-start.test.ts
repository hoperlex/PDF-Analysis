/**
 * `PROD-11-AR-V1-V2-REMOVAL-01`: a version classified АР has no ordinary start. The server refuses
 * `startRun` for it (`section_profile_unavailable`), so the version's run list draws the six-check
 * start in its place — when the pack allows it — and a sentence that says why there is no other.
 *
 * Rendered, not read from source (`D-53`), in both start positions (the empty state's action and
 * the foot of a list with runs) over the pack states that matter. The ordinary list
 * (`run-list-ar-v3-start.test.ts`, which passes no section) is untouched by any of it.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ProjectSection } from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import { AR_START_NOTE } from '@/entities/analysis-profile';
import { RUN_PAGE_LIMIT } from '@/entities/audit-run';

import { RunList } from '@/widgets/run-list';

import { NOT_INSTALLED_PACK, installedPackFixture } from '../analysis-settings/ar-v3-beta-pack-fixtures';
import { PROJECT_UID, VERSION_UID, runStatus } from '../review/fixtures';
import { newClient, renderScreen, seedError } from './harness';

type Client = ReturnType<typeof newClient>;

const page = { next_cursor: null } as { next_cursor: null };
const PACK = queryKeys.runs.arV3PackStatus();
const ORDINARY = '>Запустить прогон</button>';
const SIX_CHECKS = 'Запустить шесть проверок АР v3';

function listClient(withRuns: boolean): Client {
  const client = newClient();
  client.setQueryData(
    queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT),
    { items: withRuns ? [runStatus()] : [], page },
  );
  return client;
}

function markupOf(client: Client, sectionCode: ProjectSection | null | undefined): string {
  return renderScreen(
    client,
    createElement(RunList, { projectUid: PROJECT_UID, versionUid: VERSION_UID, sectionCode }),
  );
}

describe('an АР version is offered the six checks and never the ordinary start', () => {
  for (const withRuns of [false, true]) {
    const where = withRuns ? 'a list with runs' : 'an empty list';

    it(`${where}, pack installed: the six checks only`, () => {
      const client = listClient(withRuns);
      client.setQueryData(PACK, installedPackFixture());
      const markup = markupOf(client, 'AR');
      expect(markup).toContain(SIX_CHECKS);
      expect(markup).toContain('data-ar-v3-group-start');
      expect(markup).not.toContain(ORDINARY);
      expect(markup).not.toContain('data-start-run-control');
      expect(markup).not.toContain('data-ar-start-note');
    });

    for (const [name, seed] of [
      ['not installed', (client: Client) => client.setQueryData(PACK, NOT_INSTALLED_PACK)],
      ['loading', () => {}],
      [
        'a failed read',
        (client: Client) => seedError(client, PACK, new ApiError(503, {
          contract_version: '1.9.0', error_code: 'dependency_unavailable', message: 'm',
          correlation_id: 'c', retryable: true,
        }, 'c')),
      ],
    ] as const) {
      it(`${where}, pack ${name}: no start at all, and the reason in words`, () => {
        const client = listClient(withRuns);
        seed(client);
        const markup = markupOf(client, 'AR');
        expect(markup).not.toContain(ORDINARY);
        expect(markup).not.toContain('data-start-run-control');
        expect(markup).not.toContain(SIX_CHECKS);
        expect(markup).toContain('data-ar-start-note');
        expect(markup).toContain(AR_START_NOTE.slice(0, 60));
      });
    }
  }

  it('says «Запустить анализ АР» above the control of a list with runs', () => {
    const client = listClient(true);
    client.setQueryData(PACK, installedPackFixture());
    expect(markupOf(client, 'AR')).toContain('Запустить анализ АР');
    expect(markupOf(client, 'KJ')).toContain('Запустить ещё один прогон');
  });
});

describe('every other version keeps the ordinary start', () => {
  for (const section of ['KJ', 'PB', 'AI', null, undefined] as const) {
    it(`section ${String(section)}: the ordinary start, no АР sentence`, () => {
      const client = listClient(false);
      client.setQueryData(PACK, NOT_INSTALLED_PACK);
      const markup = markupOf(client, section);
      expect(markup).toContain(ORDINARY);
      expect(markup).toContain('data-start-run-control');
      expect(markup).not.toContain('data-ar-start-note');
    });
  }
});
