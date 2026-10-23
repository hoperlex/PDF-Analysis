/**
 * The states of «Блоки портала» (`W55B-WEB-BLOCKS`): absent, empty and present are three
 * different answers and read as three different things; absent has two causes.
 *
 * Rendered through the real widget over a seeded query cache, so the branch taken is the one
 * the widget takes for that answer — not a view handed the branch by the test.
 */

import { createElement } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { ErrorEnvelope, PortalBlockPage } from '@/shared/api';
import { ApiError } from '@/shared/api';
import { PORTAL_BLOCK_PAGE_LIMIT, portalBlocksQueryOptions } from '@/entities/block';
import { PortalBlocks } from '@/widgets/portal-blocks';

import { newClient, renderScreen, seedError } from '../screens/harness';
import {
  BLOCKS_VERSION_UID,
  TEST_CROP_SRC,
  blocksVersion,
  everyKindOfBlock,
  notProducedPage,
  portalPage,
} from './fixtures';

const KEY = portalBlocksQueryOptions(BLOCKS_VERSION_UID).queryKey;

function seeded(pages: readonly PortalBlockPage[]) {
  const client = newClient();
  client.setQueryData(KEY, { pages: [...pages], pageParams: pages.map((_, i) => (i === 0 ? undefined : `c${i}`)) });
  return client;
}

function widget(client: ReturnType<typeof newClient>, bundle = true): string {
  return renderScreen(client, createElement(PortalBlocks, { version: blocksVersion(bundle) }));
}

function apiError(status: number, code: ErrorEnvelope['error_code'], retryable: boolean): ApiError {
  return new ApiError(
    status,
    { contract_version: '1.4.0', error_code: code, message: 'm', correlation_id: 'cid-blocks', retryable },
    'cid-blocks',
  );
}

const NOT_YET =
  'Блоки портала появятся после первого запуска анализа этой версии, который дойдёт до разметки страниц.';
/** `W55B-FIX` (integrator addendum 2): a version whose run is refused gets no blocks, and the screen says so. */
const REFUSED_RUN = 'Если запуск отклонён — например, текст версии больше допустимого объёма, — блоков не будет.';
const NO_BUNDLE = 'У этой версии нет комплекта портала.';
const EMPTY = 'В комплекте портала нет ни одного блока.';

afterEach(() => {
  vi.unstubAllEnvs();
});

describe('absent is not empty', () => {
  it('says the blocks come after the first run, for a bundle no run has reached', () => {
    const markup = widget(seeded([notProducedPage()]), true);
    expect(markup).toContain(NOT_YET);
    expect(markup).toContain(REFUSED_RUN);
    expect(markup).not.toContain(NO_BUNDLE);
    expect(markup).not.toContain(EMPTY);
    expect(markup).not.toContain('data-portal-block-type');
  });

  it('says a version without a bundle has none, rather than promising them after a run', () => {
    // `W55B-GEOMETRY-01` §5 item 4: such a version answers `not_produced` after its runs too.
    const markup = widget(seeded([notProducedPage()]), false);
    expect(markup).toContain(NO_BUNDLE);
    expect(markup).not.toContain(NOT_YET);
    expect(markup).not.toContain(REFUSED_RUN);
  });

  it('says a produced block list is empty, in different words from both absences', () => {
    const markup = widget(seeded([portalPage([])]), true);
    expect(markup).toContain(EMPTY);
    expect(markup).not.toContain(NOT_YET);
    expect(markup).not.toContain(NO_BUNDLE);
  });

  it('shows the blocks of a produced list, and none of the three sentences', () => {
    // The crop's address is built from the configured base, the one value the widget reads
    // from configuration; it is the same address the instruments' TEST_CROP_SRC spells.
    vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', '/bff/v1');
    const blocks = everyKindOfBlock();
    const markup = widget(seeded([portalPage(blocks)]));
    expect(markup.split('data-portal-block-type=').length - 1).toBe(blocks.length);
    for (const sentence of [NOT_YET, NO_BUNDLE, EMPTY]) expect(markup).not.toContain(sentence);
    const image = blocks.find((block) => block.crop !== undefined);
    expect(image).toBeDefined();
    expect(markup).toContain(`src="${TEST_CROP_SRC(image as never)}"`);
  });

  it('reads `status`, never the length of `items`', () => {
    // A `not_produced` page that somehow carried items is still absent.
    const odd = { ...notProducedPage(), items: everyKindOfBlock() };
    const markup = widget(seeded([odd]));
    expect(markup).toContain(NOT_YET);
    expect(markup).not.toContain('data-portal-block-type');
  });
});

describe('a read that has not answered, or failed', () => {
  it('is a loading state while the first page is in flight', () => {
    expect(widget(newClient())).toContain('Загрузка: блоки портала…');
  });

  it('offers a retry only when the envelope says one can help', () => {
    const retryable = newClient();
    seedError(retryable, KEY, apiError(503, 'dependency_unavailable', true));
    const once = widget(retryable);
    expect(once).toContain('am-state--error');
    expect(once).toContain('cid-blocks');
    expect(once).toContain('<button');

    const final = newClient();
    seedError(final, KEY, apiError(404, 'not_found', false));
    const refused = widget(final);
    expect(refused).toContain('am-state--error');
    expect(refused).toContain('Такой версии не существует.');
    expect(refused).not.toContain('<button');
  });
});

describe('the page size is part of the key, and the key sits beside the text-line index', () => {
  it('asks for the declared page size', () => {
    expect(KEY).toEqual(['versions', 'portal-blocks', BLOCKS_VERSION_UID, { limit: PORTAL_BLOCK_PAGE_LIMIT }]);
    expect(PORTAL_BLOCK_PAGE_LIMIT).toBeGreaterThanOrEqual(1);
    expect(PORTAL_BLOCK_PAGE_LIMIT).toBeLessThanOrEqual(200);
  });
});
