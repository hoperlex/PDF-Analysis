/**
 * `AR-V3-BETA-PACK-STATUS-WEB-01`, as `3821261a` ("restore original-source text profile") left it: the
 * version's run list offers the six-check start on NO answer of the pack status.
 *
 * `AR-V3-OPT-IN` (2026-11-07) made v3 an opt-in choice on the start form of an АР version, offered on ONE answer
 * (installed AND `start_allowed`): that successor, with its own grid, is `run-list-analysis-choice.test.ts`. What this
 * file still pins is the half that stays true: a version that is not АР, or has no confirmed section, is offered the
 * ordinary start and nothing else on every answer, and does not read the status at all.
 *
 * It used to draw the control beside the ordinary start on an installed, valid pack (and only then). The
 * owner restored the ordinary АР start with its original-source text profile and took the six-check
 * control off the run list; its API, the old group review and the control's own component remain
 * (`run-list-ar-v3-started.test.ts`, `ar-v3-group-start-*.test.ts`, `start-cost-flow.test.ts`). The grid
 * below is the one the old rule was pinned over -- both start positions, every answer the pack status can
 * be in -- with the verdict turned over: the control is absent from the markup in ALL of them, with
 * nothing in its place, and a reintroduction on any one answer reddens that row.
 *
 * Rendered, not read from source (`D-53`). The list is rendered in both of its start positions -- the
 * empty state's action and the foot of a list with runs.
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

describe('the six-check start is drawn on no answer of the pack status, for a version that is not АР', () => {
  // The third member is what the old rule drew; it is kept in the grid, because "installed and valid" is
  // exactly the row a reintroduction would turn back on.
  const statuses: ReadonlyArray<readonly [string, (client: Client) => void]> = [
    ['loading', () => {}],
    [
      'a failed read',
      (client) => seedError(client, PACK, new ApiError(503, {
        contract_version: '1.44.0', error_code: 'dependency_unavailable', message: 'm',
        correlation_id: 'c', retryable: true,
      }, 'c')),
    ],
    ['not installed', (client) => client.setQueryData(PACK, NOT_INSTALLED_PACK)],
    ['installed', (client) => client.setQueryData(PACK, installedPackFixture())],
    ['installed without a review', (client) => client.setQueryData(PACK, withoutMember(installedPackFixture(), 'review'))],
    [
      'installed with the wrong scopes',
      (client) => client.setQueryData(PACK, { ...installedPackFixture(), scope_ids: ['F1', 'F2'] }),
    ],
    ['an undeclared state', (client) => client.setQueryData(PACK, { state: 'withdrawn' })],
    ['not installed with a member', (client) => client.setQueryData(PACK, { ...NOT_INSTALLED_PACK, pack_sha256: 'x' })],
  ];

  for (const withRuns of [false, true]) {
    for (const [name, seed] of statuses) {
      it(`${withRuns ? 'a list with runs' : 'an empty list'}, ${name}: absent`, () => {
        const client = listClient(withRuns);
        seed(client);
        const markup = listMarkup(client);
        expect(markup.includes(SIX_CHECKS), name).toBe(false);
        expect(markup.includes('data-ar-v3-group-start'), name).toBe(false);
        // Nothing in its place: no disabled copy, no placeholder, no sentence about the pack.
        expect(markup).not.toContain('шесть проверок');
        expect(markup).not.toContain('Шесть отдельных прогонов');
        expect(markup).not.toContain('Пакет проверенных норм');
        expect(markup).not.toContain('data-ar-start-note');
        // The ordinary start is the only start, drawn once, and untouched by any of it.
        expect(markup).toContain('data-start-run-control="true"');
        expect(markup).toContain('>Запустить прогон</button>');
        expect(markup.match(/>Запустить прогон<\/button>/g)).toHaveLength(1);
      });
    }
  }

  it('does not even read the pack status, so a status that stops being readable changes nothing here', () => {
    const client = listClient(false);
    listMarkup(client);
    expect(client.getQueryCache().find({ queryKey: PACK }), 'the run list observes the pack status').toBeUndefined();
  });

  it('draws the same list whatever the pack says', () => {
    const drawn = statuses.map(([, seed]) => {
      const client = listClient(true);
      seed(client);
      // The ids React mints for labels differ per render; the structure does not.
      return listMarkup(client).replace(/_[rR]_[A-Za-z0-9]+_/g, '_ID_');
    });
    for (const markup of drawn) expect(markup).toBe(drawn[0]);
  });
});
