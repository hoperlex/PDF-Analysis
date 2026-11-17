/**
 * The queue's way in, as the original's «+ Добавить проекты» in its head (`UIP-S13-03`): work enters the queue from the queue's own page, so the
 * head carries a button that opens the panel «Добавить документы» there, and not a link to «Проекты»; «Обновить» stays beside it.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { queryKeys } from '@/shared/api';
import { QueuePage } from '@/_pages/queue/ui/queue-page';

import { newClient, renderScreen } from '../screens/harness';

describe('the head of the queue', () => {
  it('opens the panel of documents on the page, and keeps «Обновить»', () => {
    const client = newClient();
    client.setQueryData(queryKeys.execution.queue(), { items: [], page: { next_cursor: null }, paused: false });
    const markup = renderScreen(client, createElement(QueuePage));
    expect(markup).toMatch(/<button[^>]*data-queue-add[^>]*>\+ Добавить документы<\/button>/);
    // It no longer sends the reader away to the list of objects.
    expect(markup).not.toContain('href="/projects"');
    expect(markup).not.toContain('+ Добавить объекты');
    expect(markup).toContain('>Обновить</button>');
  });
});
