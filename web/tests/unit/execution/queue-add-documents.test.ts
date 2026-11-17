/**
 * `UIP-S13-03`: «+ Добавить документы» and «Убрать завершённые (N)».
 *
 * Held here, each with a case that shows it can fail:
 *
 *   - the panel offers the documents of the chosen object that can be run and have no run in flight, each with a box and its section,
 *     and nothing else (not a document admitted for comparison only, not one with no confirmed section, not one already running);
 *   - the object is the one the header chose, and with «Все объекты» it is chosen in the panel; no documents are read until it is;
 *   - the start is the section page's batch panel, with «Выбрано: N» and «Запустить аудит (N)», and offers no choice of an action;
 *   - «Убрать завершённые (N)» hides the finished rows of the page in the browser only, says how to bring them back, and removes nothing.
 */

import { createElement } from 'react';
import type { ComponentType } from 'react';
import { describe, expect, it, vi } from 'vitest';

const navigation = vi.hoisted(() => ({ search: '' }));

vi.mock('next/navigation', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  usePathname: () => '/queue',
  useSearchParams: () => new URLSearchParams(navigation.search),
}));

import type { ExecutionQueueItem, ProjectPage } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { documentListQueryOptions } from '@/entities/document-version';
import { PROJECT_PAGE_LIMIT } from '@/entities/project';
import { QueuePage } from '@/_pages/queue';
import type { QueuePageProps } from '@/_pages/queue';
import { addableDocuments, addableSection, chosenEntries } from '@/_pages/queue/model/add-documents';
import { finishedCount, visibleRows } from '@/_pages/queue/model/hide-finished';
import { AddDocumentsPanel } from '@/_pages/queue/ui/add-documents-panel';

import { newClient, renderScreen } from '../screens/harness';
import { classification, otherVersion, page } from '../sections/fixtures';
import { QUEUE_WORK } from './queue-work';

const PROJECT = QUEUE_WORK.project_uid;
const OTHER_PROJECT = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z';

const projects = (): ProjectPage => ({
  items: [
    { project_uid: PROJECT, name: 'Школа № 7', created_at: '2026-10-01T00:00:00Z' },
    { project_uid: OTHER_PROJECT, name: 'Детский сад', created_at: '2026-10-02T00:00:00Z' },
  ],
  page: { next_cursor: null },
});

/** A document that can be run: a confirmed section, no run in flight. */
const ready = (suffix: string, title: string, section: 'AR' | 'KJ' = 'AR') => otherVersion(suffix, {
  display_title: title,
  classification: classification({ section_code: section }),
});

describe('what the panel offers', () => {
  const listing = [
    ready('1', 'АР, лист 1'),
    ready('2', 'АР, лист 2', 'KJ'),
    otherVersion('3', { display_title: 'Без раздела' }),
    otherVersion('4', { display_title: 'Только для сравнения', classification: classification(), upload_kind: 'comparison_pdf' }),
    ready('5', 'Уже идёт'),
  ].map((item) => (item.display_title === 'Уже идёт'
    ? { ...item, audit: { state: 'not_run' as const, finding_count: 0, undecided_finding_count: 0, partial: false, active_run: { run_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', state: 'running' as const } } }
    : item)) as ReturnType<typeof ready>[];

  it('keeps the documents that can be run and have no run in flight, in the listing\'s order', () => {
    expect(addableDocuments(listing).map((item) => item.display_title)).toEqual(['АР, лист 1', 'АР, лист 2']);
  });

  it('says the section of each, and the batch\'s entries follow the listing, not the order of the boxes', () => {
    const offered = addableDocuments(listing);
    expect(offered.map(addableSection)).toEqual(['АР', 'КЖ'].map((word) => expect.stringContaining(word)));
    const entries = chosenEntries(offered, new Set([offered[1]!.version_uid, offered[0]!.version_uid]));
    expect(entries.map((entry) => entry.title)).toEqual(['АР, лист 1', 'АР, лист 2']);
    expect(chosenEntries(offered, new Set())).toEqual([]);
  });
});

describe('the panel', () => {
  function render(search: string, seeded: { documents?: boolean; objects?: boolean } = { documents: true, objects: true }): string {
    navigation.search = search;
    const client = newClient();
    if (seeded.objects !== false) client.setQueryData(queryKeys.projects.list(undefined, PROJECT_PAGE_LIMIT, 'name'), projects());
    if (seeded.documents !== false) {
      client.setQueryData(documentListQueryOptions(PROJECT).queryKey, page([ready('1', 'АР, лист 1'), ready('2', 'АР, лист 2', 'KJ'), otherVersion('3', { display_title: 'Без раздела' })]));
    }
    return renderScreen(client, createElement(AddDocumentsPanel));
  }

  it('opens on the object the header chose, with its documents, each with a box and its section', () => {
    const markup = render(`project=${PROJECT}`);
    expect(markup).toContain('data-queue-add-panel');
    expect(markup).toContain(`<option value="${PROJECT}" selected="">Школа № 7</option>`);
    expect(markup).toContain('data-queue-add-documents="2"');
    expect(markup.match(/type="checkbox"/g)).toHaveLength(2);
    expect(markup).toContain('АР, лист 1');
    expect(markup).toContain('АР, лист 2');
    expect(markup).not.toContain('Без раздела');
    expect(markup.match(/data-queue-add-section/g)).toHaveLength(2);
  });

  it('says «Выбрано: 0» and «Запустить аудит (0)», inactive, and offers no choice of an action', () => {
    const markup = render(`project=${PROJECT}`);
    expect(markup).toContain('Выбрано: 0');
    expect(markup).toMatch(/<button[^>]*disabled=""[^>]*>Запустить аудит \(0\)<\/button>/);
    expect(markup).toContain('Выбрать все');
    expect(markup).not.toMatch(/Оптимизац/);
    expect(markup).not.toContain('Оба');
  });

  it('with «Все объекты» asks for the object first and reads no documents', () => {
    const markup = render('project=all', { objects: true, documents: false });
    expect(markup).toContain('data-queue-add-pick');
    expect(markup).toContain('<option value="" selected="">Выберите объект</option>');
    expect(markup).toContain('Школа № 7');
    expect(markup).toContain('Детский сад');
    expect(markup).not.toContain('data-queue-add-documents');
  });

  it('says when every document of the object is already running or has no section', () => {
    navigation.search = `project=${PROJECT}`;
    const client = newClient();
    client.setQueryData(queryKeys.projects.list(undefined, PROJECT_PAGE_LIMIT, 'name'), projects());
    client.setQueryData(documentListQueryOptions(PROJECT).queryKey, page([otherVersion('3', { display_title: 'Без раздела' })]));
    const markup = renderScreen(client, createElement(AddDocumentsPanel));
    expect(markup).toContain('data-queue-add-empty');
    expect(markup).not.toContain('type="checkbox"');
  });
});

describe('the page', () => {
  const finishedItem = (suffix: string, state: ExecutionQueueItem['state']): ExecutionQueueItem => ({
    job_id: `job_01J9ZQ8K7NHVXW3T2R5M6P4Q8${suffix}`, run_id: `run_01J9ZQ8K7NHVXW3T2R5M6P4Q8${suffix}`, state, priority: 0,
    created_at: '2026-10-09T10:00:00Z', available_at: '2026-10-09T10:00:00Z', ...QUEUE_WORK,
  });
  const ITEMS = [finishedItem('A', 'queued'), finishedItem('B', 'running'), finishedItem('C', 'succeeded'), finishedItem('D', 'failed'), finishedItem('E', 'cancelled')];

  function render(items: readonly ExecutionQueueItem[], props: QueuePageProps = {}, roles: readonly string[] = ['expert']): string {
    navigation.search = '';
    const client = newClient();
    client.setQueryData(queryKeys.execution.queue(), { items, page: { next_cursor: null }, paused: false });
    client.setQueryData(queryKeys.account.me(), { roles });
    return renderScreen(client, createElement(QueuePage as ComponentType<QueuePageProps>, props));
  }

  it('opens the panel from a button, not a link, and swaps its words for «Скрыть» while it is open', () => {
    const closed = render(ITEMS);
    expect(closed).toMatch(/<button[^>]*data-queue-add[^>]*>\+ Добавить документы<\/button>/);
    expect(closed).not.toContain('href="/projects"');
    expect(closed).not.toContain('data-queue-add-panel');
    const open = render(ITEMS, { initiallyAdding: true });
    expect(open).toMatch(/<button[^>]*aria-expanded="true"[^>]*data-queue-add[^>]*>Скрыть<\/button>/);
    expect(open).toContain('data-queue-add-panel');
  });

  it('is not offered to a role that may not start an audit', () => {
    expect(render(ITEMS, {}, ['viewer'])).not.toContain('data-queue-add=');
    expect(render(ITEMS, { initiallyAdding: true }, ['admin'])).not.toContain('data-queue-add-panel');
  });

  it('counts the finished rows of the page in «Убрать завершённые (N)», and leaves every row in place', () => {
    expect(finishedCount(ITEMS)).toBe(3);
    const markup = render(ITEMS);
    expect(markup).toContain('Убрать завершённые (3)');
    expect(markup.match(/data-queue-row="/g)).toHaveLength(5);
  });

  it('is not drawn for a page with nothing finished', () => {
    const markup = render([finishedItem('A', 'queued'), finishedItem('B', 'running')]);
    expect(markup).not.toContain('data-queue-hide-finished');
  });

  it('hides the finished and the failed rows only, and offers «Показать всё»', () => {
    const markup = render(ITEMS, { initiallyHidden: true });
    expect(visibleRows(ITEMS, true).map((item) => item.state)).toEqual(['queued', 'running']);
    expect(visibleRows(ITEMS, false)).toHaveLength(5);
    expect(markup.match(/data-queue-row="/g)).toHaveLength(2);
    expect(markup).not.toContain('data-queue-row="succeeded"');
    expect(markup).not.toContain('data-queue-row="failed"');
    expect(markup).not.toContain('data-queue-row="cancelled"');
    expect(markup).toContain('Показать всё');
    expect(markup).not.toContain('Убрать завершённые');
  });

  it('says that the records are hidden, not that the queue is empty, when every row of the page is finished', () => {
    const markup = render([finishedItem('C', 'succeeded'), finishedItem('D', 'failed')], { initiallyHidden: true });
    expect(markup).toContain('data-queue-all-hidden');
    expect(markup).toContain('Завершённые задачи скрыты');
    expect(markup).not.toContain('Очередь пуста');
    expect(markup).toContain('Показать всё');
  });
});
