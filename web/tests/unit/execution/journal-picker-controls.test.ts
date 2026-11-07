/**
 * `UI-B-40` and `UI-B-43` on «Журнал выполнения»: the run picker «проект → документ → версия → прогон», «Скопировать»
 * and «Автообновление».
 *
 * The harness renders one pass and cannot click, so what a click does is held where it lives: the options and the
 * copied text are pure functions, the clipboard is passed in, and the switch is a React Query observer driven by fake
 * timers. What the page draws in each state is rendered through the same providers the screens use.
 */

import { QueryClient, QueryObserver } from '@tanstack/react-query';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type {
  DocumentVersion, DocumentVersionPage, ExecutionJournalEntry, Project, ProjectPage, RunStatus, RunStatusPage,
} from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import { VERSION_PAGE_LIMIT, documentListQueryOptions } from '@/entities/document-version';
import { PROJECT_PAGE_LIMIT } from '@/entities/project';
import { runListQueryOptions } from '@/entities/audit-run';
import { journalCopyLine, journalCopyText, journalQueryOptions } from '@/entities/execution';
import { operationalListRefetchInterval } from '@/entities/execution/api/operational-poll';
import {
  EMPTY_PICKER_SELECTION, JournalControls, RunPicker, UNRECOGNISED_RUN_STATE, copyToClipboard, documentOptions,
  projectOptions, runOptions, versionOptions,
} from '@/widgets/execution-journal';
import { LogsPage } from '@/_pages/logs';

import { DOCUMENT_UID, PROJECT_UID, RUN_ID, VERSION_UID, runStatus } from '../review/fixtures';
import { newClient, renderScreen, seedError } from '../screens/harness';

const NO_NEXT = { next_cursor: null } as const;
const MORE = { next_cursor: 'Y3Vyc29y' } as const;
const SECOND_RUN_ID = `${RUN_ID.slice(0, -1)}Z`;
const noop = () => {};

const PROJECT: Project = { project_uid: PROJECT_UID, name: 'Корпус на Лесной', created_at: '2026-09-20T08:00:00.000Z' };

function version(overrides: Partial<DocumentVersion> = {}): DocumentVersion {
  return {
    version_uid: VERSION_UID,
    document_uid: DOCUMENT_UID,
    project_uid: PROJECT_UID,
    version_ordinal: 2,
    media_type: 'application/pdf',
    byte_size: 58978,
    sha256: '6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f',
    page_count: 8,
    published_at: '2026-09-18T06:55:52.642022Z',
    input_manifest: [],
    display_title: 'Пояснительная записка',
    ...overrides,
  };
}

function entry(overrides: Partial<ExecutionJournalEntry> = {}): ExecutionJournalEntry {
  return {
    event_id: 'evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
    run_id: RUN_ID,
    aggregate_id: RUN_ID,
    aggregate_type: 'AuditRun',
    event_type: 'audit_run.transition',
    occurred_at: '2026-10-09T10:00:00Z',
    payload: { to_state: 'queued', error_code: 'analysis_failed', secret: 'NEVER_COPY_THIS' },
    ...overrides,
  };
}

function projectPage(items: readonly Project[], page: ProjectPage['page'] = NO_NEXT): ProjectPage {
  return { items: [...items], page };
}

function versionPage(items: readonly DocumentVersion[], page: DocumentVersionPage['page'] = NO_NEXT): DocumentVersionPage {
  return { items: [...items], page };
}

function runPage(items: readonly RunStatus[], page: RunStatusPage['page'] = NO_NEXT): RunStatusPage {
  return { items: [...items], page };
}

const PROJECTS_KEY = queryKeys.projects.list(undefined, PROJECT_PAGE_LIMIT);
const DOCUMENTS_KEY = documentListQueryOptions(PROJECT_UID).queryKey;
const VERSIONS_KEY = queryKeys.versions.list(DOCUMENT_UID, undefined, VERSION_PAGE_LIMIT);
const RUNS_KEY = runListQueryOptions(VERSION_UID).queryKey;

const FULL_SELECTION = { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID, versionUid: VERSION_UID };

/** A client with every list of the picker answered. */
function seededPicker() {
  const client = newClient();
  client.setQueryData(PROJECTS_KEY, projectPage([PROJECT]));
  client.setQueryData(DOCUMENTS_KEY, versionPage([version()]));
  client.setQueryData(VERSIONS_KEY, versionPage([version({ version_ordinal: 2 }), version({ version_ordinal: 1, version_uid: `ver_${'0'.repeat(26)}` })]));
  client.setQueryData(RUNS_KEY, runPage([
    runStatus({ run_id: RUN_ID, state: 'published', started_by_label: 'Петрова А. С.' }),
    runStatus({ run_id: SECOND_RUN_ID, state: 'failed', created_at: '2026-09-11T08:00:00.000Z' }),
  ]));
  return client;
}

function picker(client: QueryClient, props: { selection?: typeof FULL_SELECTION | typeof EMPTY_PICKER_SELECTION; runId?: string | null } = {}): string {
  return renderScreen(client, createElement(RunPicker, {
    selection: props.selection ?? EMPTY_PICKER_SELECTION,
    runId: props.runId ?? null,
    onSelection: noop,
    onChooseRun: noop,
  }));
}

/** The markup of one step of the picker. */
function step(markup: string, name: 'project' | 'document' | 'version' | 'run'): string {
  const start = markup.indexOf(`data-journal-step="${name}"`);
  expect(start, `step ${name} is drawn`).toBeGreaterThan(-1);
  const next = markup.indexOf('data-journal-step="', start + 1);
  const scope = markup.indexOf('data-journal-scope', start + 1);
  const end = [next, scope].filter((index) => index > -1).sort((a, b) => a - b)[0] ?? markup.length;
  return markup.slice(start, end);
}

describe('the options each step of the picker offers', () => {
  it('names a record by its words and sends its identity', () => {
    expect(projectOptions([PROJECT])).toEqual([{ value: PROJECT_UID, label: 'Корпус на Лесной' }]);
    expect(documentOptions([version()])).toEqual([{ value: DOCUMENT_UID, label: 'Пояснительная записка' }]);
    const untitled = version({ source_filename: 'ПЗ.pdf' });
    delete untitled.display_title;
    expect(documentOptions([untitled])[0]?.label).toBe('ПЗ.pdf');
    expect(versionOptions([version()])).toEqual([{
      value: VERSION_UID, label: 'Версия 2 · 2026-09-18 06:55:52 UTC · страниц 8',
    }]);
  });

  it('names a run by when it began, its state in Russian and who started it, and says so for a state it has no word for', () => {
    const runs = runOptions([
      runStatus({ started_by_label: ' Петрова А. С. ' }),
      runStatus({ run_id: SECOND_RUN_ID, state: 'failed' }),
      runStatus({ run_id: `${RUN_ID.slice(0, -1)}Y`, state: 'archived' as RunStatus['state'] }),
    ]);
    expect(runs[0]).toEqual({ value: RUN_ID, label: '2026-09-10 08:00:00 UTC · опубликован · Петрова А. С.' });
    expect(runs[1]?.label).toBe('2026-09-10 08:00:00 UTC · отказ');
    expect(runs[2]?.label).toBe(`2026-09-10 08:00:00 UTC · ${UNRECOGNISED_RUN_STATE}`);
  });
});

describe('the picker, drawn', () => {
  it('opens on the projects and holds the three steps below shut, each saying what it waits for', () => {
    const markup = picker(seededPicker());
    expect(markup).toContain('data-journal-picker');
    expect(step(markup, 'project')).toContain('data-journal-step-status="ready"');
    expect(step(markup, 'project')).toContain('Корпус на Лесной');
    for (const [name, waiting] of [
      ['document', 'Сначала выберите проект'], ['version', 'Сначала выберите документ'], ['run', 'Сначала выберите версию'],
    ] as const) {
      const text = step(markup, name);
      expect(text, name).toContain('data-journal-step-status="idle"');
      expect(text, name).toContain('disabled');
      expect(text, name).toContain(waiting);
    }
    expect(markup).toContain('data-journal-scope="all"');
    expect(markup).toContain('Показаны события всех прогонов.');
  });

  it('walks to the runs of the chosen version and marks the run in view', () => {
    const markup = picker(seededPicker(), { selection: FULL_SELECTION, runId: SECOND_RUN_ID });
    expect(step(markup, 'document')).toContain('Пояснительная записка');
    expect(step(markup, 'version')).toContain('Версия 1 · 2026-09-18 06:55:52 UTC');
    const runs = step(markup, 'run');
    expect(runs).toContain('Все прогоны');
    expect(runs).toContain('2026-09-10 08:00:00 UTC · опубликован · Петрова А. С.');
    expect(runs).toContain(`<option value="${SECOND_RUN_ID}" selected="">2026-09-11 08:00:00 UTC · отказ</option>`);
    expect(runs).not.toContain(`<option value="${RUN_ID}" selected`);
    expect(markup).toContain('data-journal-scope="run"');
    expect(markup).toContain(`<code>${SECOND_RUN_ID}</code>`);
    expect(markup).toContain('Показать все прогоны');
  });

  it('says a step is still reading, and which read failed, instead of drawing an empty list', () => {
    const loading = picker(newClient());
    expect(step(loading, 'project')).toContain('data-journal-step-status="loading"');
    expect(step(loading, 'project')).toContain('Загрузка…');

    const client = newClient();
    client.setQueryData(PROJECTS_KEY, projectPage([PROJECT]));
    seedError(client, DOCUMENTS_KEY, new ApiError(503, {
      contract_version: '1.39.0', error_code: 'dependency_unavailable', message: 'Безопасная фраза.',
      correlation_id: 'cid-picker-1', retryable: true,
    }, 'cid-picker-1'));
    const failed = picker(client, { selection: { projectUid: PROJECT_UID, documentUid: null, versionUid: null } });
    expect(step(failed, 'document')).toContain('data-journal-step-failure="document"');
    expect(step(failed, 'document')).toContain('Не удалось прочитать список документов.');
    expect(step(failed, 'document')).toContain('Повторить');
  });

  it('says a step has nothing to offer, and that a list is only its first page', () => {
    const client = seededPicker();
    client.setQueryData(DOCUMENTS_KEY, versionPage([]));
    client.setQueryData(PROJECTS_KEY, projectPage([PROJECT], MORE));
    const markup = picker(client, { selection: { projectUid: PROJECT_UID, documentUid: null, versionUid: null } });
    expect(step(markup, 'document')).toContain('В проекте нет документов');
    expect(step(markup, 'document')).toContain('disabled');
    expect(step(markup, 'project')).toContain('data-journal-step-truncated="project"');
    expect(step(markup, 'project')).toContain('Показана первая страница списка.');
    expect(step(picker(seededPicker()), 'project')).not.toContain('data-journal-step-truncated');
  });
});

describe('«Скопировать»', () => {
  const known = entry();
  const unknown = entry({
    event_id: 'evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8G', event_type: 'raw.secret.provider.event',
    payload: { path: '/secret/provider/key', prompt: 'NEVER_COPY_THIS' },
  });

  it('writes one line per record from the closed projection the page draws, and nothing else of the record', () => {
    expect(journalCopyLine(known)).toBe(
      '2026-10-09 10:00:00 UTC · Состояние прогона · прогон ' + RUN_ID + ' · состояние: в очереди · код: analysis_failed',
    );
    const text = journalCopyText([known, unknown], { runId: null });
    expect(text.split('\n')).toEqual([
      'Журнал выполнения · все прогоны · записей на странице: 2',
      '',
      journalCopyLine(known),
      `2026-10-09 10:00:00 UTC · Другое событие выполнения · прогон ${RUN_ID}`,
    ]);
    for (const hidden of ['NEVER_COPY_THIS', '/secret/provider/key', 'raw.secret.provider.event', 'AuditRun', 'evt_01J9']) {
      expect(text).not.toContain(hidden);
    }
  });

  it('names the run when the journal is narrowed to one, and an empty page is just the heading', () => {
    expect(journalCopyText([known], { runId: RUN_ID }).split('\n')[0]).toBe(
      `Журнал выполнения · прогон ${RUN_ID} · записей на странице: 1`,
    );
    expect(journalCopyText([], { runId: null })).toBe('Журнал выполнения · все прогоны · записей на странице: 0\n');
  });

  it('reports a clipboard that is missing or refuses as not copied, and one that accepts as copied', async () => {
    const written: string[] = [];
    expect(await copyToClipboard('текст', { writeText: async (text) => { written.push(text); } })).toBe(true);
    expect(written).toEqual(['текст']);
    expect(await copyToClipboard('текст', undefined)).toBe(false);
    expect(await copyToClipboard('текст', { writeText: async () => { throw new DOMException('denied', 'NotAllowedError'); } })).toBe(false);
  });

  it('is offered for the rows in view, counts them, and is off while there are none', () => {
    const withRows = renderScreen(newClient(), createElement(JournalControls, {
      entries: [known, unknown], runId: null, autoRefresh: true, onAutoRefresh: noop,
    }));
    expect(withRows).toContain('data-journal-copy');
    expect(withRows).not.toMatch(/<button[^>]*disabled=""[^>]*data-journal-copy/);
    expect(withRows).toContain('data-journal-count="2"');
    expect(withRows).toContain('Записей на странице: 2');
    for (const entries of [[], undefined]) {
      const markup = renderScreen(newClient(), createElement(JournalControls, {
        entries, runId: null, autoRefresh: true, onAutoRefresh: noop,
      }));
      expect(markup, String(entries)).toMatch(/<button[^>]*disabled=""[^>]*data-journal-copy/);
    }
    expect(renderScreen(newClient(), createElement(JournalControls, {
      entries: undefined, runId: null, autoRefresh: true, onAutoRefresh: noop,
    }))).toContain('Записей на странице: —');
  });
});

describe('«Автообновление»', () => {
  const RUN_FILTER = RUN_ID;

  it('is part of the read, not of the data: the cache entry is the same, the mode differs', () => {
    const on = journalQueryOptions(RUN_FILTER, 'c1', true, true);
    const off = journalQueryOptions(RUN_FILTER, 'c1', true, false);
    expect(off.queryKey).toEqual(on.queryKey);
    expect(on.meta).toEqual({ autoRefresh: true });
    expect(off.meta).toEqual({ autoRefresh: false });
    expect(on.refetchOnWindowFocus).toBe('always');
    expect(off.refetchOnWindowFocus).toBe(false);
    // On is the default: a caller that says nothing keeps the screen as it was.
    expect(journalQueryOptions().meta).toEqual({ autoRefresh: true });
    expect(journalQueryOptions().refetchOnWindowFocus).toBe('always');
    // Still the one policy function, still never in the background.
    expect(off.refetchInterval).toBe(on.refetchInterval);
    expect(off.refetchIntervalInBackground).toBe(false);
  });

  it('answers the policy interval when on and none when off', () => {
    const client = new QueryClient();
    const ask = (autoRefresh: boolean) => {
      const options = client.defaultQueryOptions(journalQueryOptions(RUN_FILTER, `c-${autoRefresh}`, true, autoRefresh));
      return operationalListRefetchInterval(client.getQueryCache().build(client, options));
    };
    expect(ask(true)).toBe(10_000);
    expect(ask(false)).toBe(false);
  });

  it('reaches the query the policy function reads: a toggle on a mounted observer changes the answer, with no new cache entry', () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } });
    const optionsFor = (autoRefresh: boolean) => ({
      ...journalQueryOptions(RUN_FILTER, undefined, true, autoRefresh),
      queryFn: async () => ({ items: [], page: NO_NEXT }),
    });
    const observer = new QueryObserver(client, optionsFor(true));
    const query = client.getQueryCache().find({ queryKey: journalQueryOptions(RUN_FILTER).queryKey });
    expect(query).toBeDefined();
    expect(operationalListRefetchInterval(query!)).toBe(10_000);
    observer.setOptions(optionsFor(false));
    expect(operationalListRefetchInterval(query!)).toBe(false);
    observer.setOptions(optionsFor(true));
    expect(operationalListRefetchInterval(query!)).toBe(10_000);
    expect(client.getQueryCache().getAll()).toHaveLength(1);
  });
});

describe('the page', () => {
  const LOGS_KEY_ALL = journalQueryOptions().queryKey;
  const page = (entries: readonly ExecutionJournalEntry[]) => ({ items: [...entries], page: NO_NEXT, paused: false });

  it('keeps the paste field, its sentences and its identity, and adds the picker, the switch and the count', () => {
    const markup = renderScreen(seededPicker(), createElement(LogsPage, {}));
    expect(markup).toContain('id="execution-run-filter"');
    expect(markup).toContain('placeholder="Идентификатор прогона"');
    expect(markup).toContain('Или вставьте идентификатор прогона');
    expect(markup).toContain('Пустое поле показывает все прогоны.');
    expect(markup).toContain('Журнал обновляется автоматически, пока вкладка открыта.');
    expect(markup).toContain('data-journal-picker');
    expect(markup).toContain('data-journal-auto-refresh="on"');
    expect(markup).toContain('<input type="checkbox" data-journal-auto-refresh="on" checked=""/>');
    expect(markup).toContain('Автообновление');
    expect(markup).toContain('Журнал читается заново раз в 10 с, пока вкладка видна; после сбоя реже.');
    expect(markup).toContain('Записей на странице: —');
  });

  it('counts the rows of the page and offers to copy them', () => {
    const client = seededPicker();
    client.setQueryData(LOGS_KEY_ALL, page([entry(), entry({ event_id: 'evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8G' })]));
    const markup = renderScreen(client, createElement(LogsPage, {}));
    expect(markup).toContain('Записей на странице: 2');
    expect(markup).not.toMatch(/<button[^>]*disabled=""[^>]*data-journal-copy/);
    expect(markup).toContain('aria-label="События выполнения"');
  });

  it('shows the run it was opened with in the picker and keeps the controls for it', () => {
    const client = seededPicker();
    client.setQueryData(journalQueryOptions(RUN_ID).queryKey, page([entry()]));
    const markup = renderScreen(client, createElement(LogsPage, { initialRunId: RUN_ID }));
    expect(markup).toContain('data-journal-scope="run"');
    expect(markup).toContain(`<code>${RUN_ID}</code>`);
    expect(markup).toContain('Записей на странице: 1');
  });

  it('keeps its refusal of a malformed identity, and shows no controls over a journal it does not read', () => {
    const markup = renderScreen(newClient(), createElement(LogsPage, { initialRunId: 'некорректный' }));
    expect(markup).toContain('Неверный идентификатор прогона');
    expect(markup).not.toContain('data-journal-controls');
    expect(markup).toContain('id="execution-run-filter"');
  });
});
