/**
 * The queue's way in, as the original's «+ Добавить проекты» in its head: work enters the queue from a project's
 * documents, so the head carries the link to «Проекты» beside «Обновить».
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { queryKeys } from '@/shared/api';
import { QueuePage } from '@/_pages/queue/ui/queue-page';

import { newClient, renderScreen } from '../screens/harness';

describe('the head of the queue', () => {
  it('leads to the projects, where work is started, and keeps «Обновить»', () => {
    const client = newClient();
    client.setQueryData(queryKeys.execution.queue(), { items: [], page: { next_cursor: null }, paused: false });
    const markup = renderScreen(client, createElement(QueuePage));
    expect(markup).toContain('data-queue-add');
    expect(markup).toContain('href="/projects"');
    expect(markup).toContain('+ Добавить проекты');
    expect(markup).toContain('>Обновить</button>');
  });
});
