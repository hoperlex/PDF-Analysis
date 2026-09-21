/**
 * `widgets/upload-panel` and `widgets/project-list` — two more screens no test reached.
 *
 * `W12-WEB`'s U-09 empties `UPLOAD_ENVELOPE_RULES` where the panel renders it, so the
 * accepted envelope disappears from the screen while every rule about it stays guarded as
 * data. The panel's whole claim is that the envelope is stated **before** the file picker
 * rather than only in the rejection that follows a bad choice, so the order is asserted
 * and not just the presence.
 *
 * `ProjectList` has no mutation of its own in `b8.json`, but it carries the three
 * mandatory read states — in flight, failed, genuinely empty — and the one that matters
 * is that an empty list is not rendered as a failure and a failure is not rendered as an
 * empty list. Both are reached here for the first time.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ErrorCode, ErrorEnvelope, Project, ProjectPage } from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import { PROJECT_PAGE_LIMIT } from '@/entities/project';
import { ProjectList } from '@/widgets/project-list';
import { UploadPanel } from '@/widgets/upload-panel';

import { join } from 'node:path';

import { WEB_ROOT, readText } from '../../guards/lib/repo';
import { PROJECT_UID } from '../review/fixtures';
import { newClient, renderWith, seedError } from './harness';

// ---------------------------------------------------------------- upload panel

// The panel composes the upload form, which holds a mutation, so it needs the provider
// even though the panel itself asks no question of the cache.
function panel(): string {
  return renderWith(newClient(), createElement(UploadPanel, { projectUid: PROJECT_UID }));
}

describe('the upload panel states the envelope before the file picker (U-09)', () => {
  it('renders every rule of the accepted envelope', () => {
    const markup = panel();
    expect(markup).toContain('Один PDF за загрузку.');
    expect(markup).toContain('Без пароля и без шифрования.');
    expect(markup).toContain('извлекаемый встроенный текст');
    expect(markup).toContain('оптическим распознаванием');
  });

  it('renders a non-empty list of them, so an emptied source is red', () => {
    // The mutation replaces the mapped array with `[]`. Counting the items is what makes
    // that red: every other assertion here would still pass on a panel that listed one.
    const items = panel().match(/<li>/g) ?? [];
    expect(items.length).toBeGreaterThanOrEqual(5);
  });

  it('states the envelope above the picker, not only after a refusal', () => {
    const markup = panel();
    const envelopeAt = markup.indexOf('Что принимается');
    const pickerAt = markup.indexOf('id="upload-file"');
    expect(envelopeAt).toBeGreaterThanOrEqual(0);
    expect(pickerAt).toBeGreaterThanOrEqual(0);
    expect(envelopeAt).toBeLessThan(pickerAt);
  });

  it('names both numeric limits, which is what a later validation_failed refers back to', () => {
    const markup = panel();
    expect(markup).toMatch(/25\s*MiB|25\s*MB/);
    expect(markup).toMatch(/\d+\s*страниц/);
  });

  it('offers no run control at all: the run is started from the version address (D-16)', () => {
    // This assertion used to read `expect(markup).toContain('No version published in this
    // session.')`. That sentence is the defect W15-RUN measured in a browser: the panel
    // held the published version in React state, so a reload reported an empty project
    // over published work and the run control existed only for whoever had just uploaded.
    // The version now has an address, and the Start-run control lives there.
    const markup = panel();
    expect(markup).not.toContain('No version published in this session');
    expect(markup).not.toContain('Запустить прогон');
  });

  it('says a published version is immutable rather than offering to replace one', () => {
    expect(panel()).toContain('неизменяем');
  });

  it('keeps no copy of what it just published', () => {
    // The panel holds no version state of its own any more. Anything it rendered from
    // such state would be the only copy in the product, and a reload would lose it.
    const source = readText(join(WEB_ROOT, 'src/widgets/upload-panel/ui/upload-panel.tsx'));
    expect(source).not.toContain('useState');
  });
});

// ---------------------------------------------------------------- project list

const LIST_KEY = queryKeys.projects.list(undefined, PROJECT_PAGE_LIMIT);

function project(overrides: Partial<Project> = {}): Project {
  return {
    project_uid: PROJECT_UID,
    name: 'Acme plc annual report',
    created_at: '2026-09-10T08:00:00.000Z',
    document_count: 2,
    ...overrides,
  };
}

function page(items: Project[], nextCursor: string | null = null): ProjectPage {
  return { items, page: { next_cursor: nextCursor } as ProjectPage['page'] };
}

function list(seed?: (client: ReturnType<typeof newClient>) => void): string {
  const client = newClient();
  seed?.(client);
  return renderWith(client, createElement(ProjectList, {}));
}

function apiError(status: number, code: ErrorCode, retryable: boolean): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.0.0-draft.1',
    error_code: code,
    message: 'A caller-safe sentence.',
    correlation_id: 'corr-list-1',
    retryable,
  };
  return new ApiError(status, envelope, 'corr-list-1');
}

describe('the project list renders each read outcome as a different state', () => {
  it('in flight is a loading state, not silence', () => {
    const markup = list();
    expect(markup.toLowerCase()).toContain('загрузка');
    expect(markup).not.toContain('Проектов пока нет.');
  });

  it('a genuinely empty list says so, and does not look like a failure', () => {
    const markup = list((c) => c.setQueryData(LIST_KEY, page([])));
    expect(markup).toContain('Проектов пока нет.');
    expect(markup).not.toContain('data-list-failure');
    expect(markup.toLowerCase()).not.toContain('загрузка');
  });

  it('a failure says so with its correlation id, and does not look like an empty list', () => {
    const markup = list((c) => seedError(c, LIST_KEY, apiError(503, 'dependency_unavailable', true)));
    expect(markup).toContain('data-list-failure');
    expect(markup).toContain('corr-list-1');
    expect(markup).not.toContain('Проектов пока нет.');
  });

  it('offers a retry only when the decoded envelope said retryable', () => {
    const retryable = list((c) =>
      seedError(c, LIST_KEY, apiError(503, 'dependency_unavailable', true)),
    );
    const notRetryable = list((c) =>
      seedError(c, LIST_KEY, apiError(422, 'validation_failed', false)),
    );
    expect(retryable).toContain('Повторить');
    expect(notRetryable).not.toContain('Повторить');
  });

  it('renders each project as a row carrying its own opaque identity', () => {
    const other = `prj_${'01J9ZQ8K7NHVXW3T2R5M6P4Q8C'}`;
    const markup = list((c) =>
      c.setQueryData(LIST_KEY, page([project(), project({ project_uid: other, name: 'Beta Ltd' })])),
    );
    expect(markup).toContain(PROJECT_UID);
    expect(markup).toContain(other);
    expect(markup).toContain('Acme plc annual report');
    expect(markup).toContain('Beta Ltd');
    expect(markup).toContain(`href="/projects/${PROJECT_UID}"`);
  });

  it('offers the next page only when the server handed back a cursor', () => {
    const withCursor = list((c) => c.setQueryData(LIST_KEY, page([project()], 'opaque-cursor-xyz')));
    const withoutCursor = list((c) => c.setQueryData(LIST_KEY, page([project()], null)));
    expect(withCursor).toContain('Next page');
    expect(withoutCursor).not.toContain('Next page');
  });

  it('shows no "first page" control while already on the first page', () => {
    const markup = list((c) => c.setQueryData(LIST_KEY, page([project()], 'opaque-cursor-xyz')));
    expect(markup).not.toContain('First page');
  });
});
