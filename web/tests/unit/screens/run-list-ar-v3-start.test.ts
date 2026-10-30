/**
 * `AR-V3-BETA-PACK-STATUS-WEB-01`: the version's run list offers the six-check start only on an
 * installed reviewed pack. What a started group does is in `run-list-ar-v3-started.test.ts`.
 *
 * Rendered, not read from source (`D-53`). The list is rendered in both of its start positions
 * — the empty state's action and the foot of a list with runs — over every answer the pack status
 * can be in; the control must be absent from the markup in all but one, with nothing in its place:
 * no disabled button, no placeholder, no explanation (the settings panel carries that).
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { ApiError, queryKeys } from '@/shared/api';
import { RUN_PAGE_LIMIT } from '@/entities/audit-run';

import { RunList } from '@/widgets/run-list';

import {
  NOT_INSTALLED_PACK, installedPackFixture, withoutMember,
} from '../analysis-settings/ar-v3-beta-pack-fixtures';
import { PROJECT_UID, VERSION_UID, runStatus } from '../review/fixtures';
import { newClient, renderScreen, seedError } from './harness';

type Client = ReturnType<typeof newClient>;

const page = { next_cursor: null } as { next_cursor: null };
const PACK = queryKeys.runs.arV3PackStatus();

function listClient(withRuns: boolean): Client {
  const client = newClient();
  client.setQueryData(
    queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT),
    { items: withRuns ? [runStatus()] : [], page },
  );
  return client;
}

function listMarkup(client: Client): string {
  return renderScreen(client, createElement(RunList, { projectUid: PROJECT_UID, versionUid: VERSION_UID }));
}

const SIX_CHECKS = 'Запустить шесть проверок АР v3';

describe('the six-check start is drawn only on an installed, valid pack', () => {
  const statuses: ReadonlyArray<readonly [string, (client: Client) => void, boolean]> = [
    ['loading', () => {}, false],
    [
      'a failed read',
      (client) => seedError(client, PACK, new ApiError(503, {
        contract_version: '1.13.0', error_code: 'dependency_unavailable', message: 'm',
        correlation_id: 'c', retryable: true,
      }, 'c')),
      false,
    ],
    ['not installed', (client) => client.setQueryData(PACK, NOT_INSTALLED_PACK), false],
    ['installed', (client) => client.setQueryData(PACK, installedPackFixture()), true],
    [
      'installed without a review',
      (client) => client.setQueryData(PACK, withoutMember(installedPackFixture(), 'review')),
      false,
    ],
    [
      'installed with the wrong scopes',
      (client) => client.setQueryData(PACK, { ...installedPackFixture(), scope_ids: ['F1', 'F2'] }),
      false,
    ],
    ['an undeclared state', (client) => client.setQueryData(PACK, { state: 'withdrawn' }), false],
    ['not installed with a member', (client) => client.setQueryData(PACK, { ...NOT_INSTALLED_PACK, pack_sha256: 'x' }), false],
  ];

  for (const withRuns of [false, true]) {
    for (const [name, seed, drawn] of statuses) {
      it(`${withRuns ? 'a list with runs' : 'an empty list'}, ${name}: ${drawn ? 'drawn' : 'absent'}`, () => {
        const client = listClient(withRuns);
        seed(client);
        const markup = listMarkup(client);
        expect(markup.includes(SIX_CHECKS), name).toBe(drawn);
        expect(markup.includes('data-ar-v3-group-start'), name).toBe(drawn);
        if (!drawn) {
          // Nothing in its place: no disabled copy, no placeholder, no sentence about the pack.
          expect(markup).not.toContain('шесть проверок');
          expect(markup).not.toContain('Шесть отдельных прогонов');
          expect(markup).not.toContain('disabled');
          expect(markup).not.toContain('Пакет проверенных норм');
        }
        // The legacy start is untouched by any of it.
        expect(markup).toContain('>Запустить прогон</button>');
        expect(markup.match(/>Запустить прогон<\/button>/g)).toHaveLength(1);
      });
    }
  }

  it('draws the new control after the legacy one, so the usual start stays first', () => {
    const client = listClient(false);
    client.setQueryData(PACK, installedPackFixture());
    const markup = listMarkup(client);
    expect(markup.indexOf('>Запустить прогон</button>')).toBeGreaterThan(-1);
    expect(markup.indexOf(SIX_CHECKS)).toBeGreaterThan(markup.indexOf('>Запустить прогон</button>'));
  });
});
