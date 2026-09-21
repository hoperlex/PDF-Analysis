/**
 * `D-16`: what a screen renders when it is opened **cold**.
 *
 * The defect this file guards is not "a screen looks wrong". It is that a screen looked
 * right on the path that created the thing and empty on every other path. `W15-RUN`
 * measured it in a real browser: a project page on a fresh load made **zero** API calls
 * and said "No version published in this session" over a project whose documents,
 * versions, runs and decisions had all survived in PostgreSQL and the store.
 *
 * So every test below renders a screen with a **cold cache** — a `QueryClient` that has
 * been handed nothing — and asserts what that screen does with no prior client state. The
 * harness cannot run an effect or fire a handler, so what it proves is the half that is
 * decided during render: *does the screen ask a question of the server, or does it report
 * emptiness without asking?* A screen that reads state a previous screen left behind
 * renders its empty state on a cold cache; a screen that asks renders a loading state and
 * files a pending query under the key the fetch will answer. That difference is exactly
 * `D-16`, and it is asserted here on both sides — the pending key is read back out of the
 * cache, so a hook wired to the wrong key is red rather than merely differently green.
 *
 * The other half — that the pending query actually reaches the network and the rendered
 * page arrives over a socket — is not a thing a node-environment render can show, and it
 * is not claimed here. It is measured in a real browser in
 * `docs/program/reviews/W19-SHELL.md` §4, against a served build, by URL, in a fresh tab.
 *
 * `D-20` is deliberately not exercised: `execute_run` is inline, so no client can observe
 * a `running` run, and nothing here waits for one.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { AppRouterContext } from 'next/dist/shared/lib/app-router-context.shared-runtime';
import type { AppRouterInstance } from 'next/dist/shared/lib/app-router-context.shared-runtime';

import type {
  DocumentVersion,
  DocumentVersionPage,
  ErrorCode,
  ErrorEnvelope,
  RunStatus,
  RunStatusPage,
} from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import { routes } from '@/shared/lib';
import { DOCUMENT_PAGE_LIMIT, VERSION_PAGE_LIMIT } from '@/entities/document-version';
import { RUN_PAGE_LIMIT } from '@/entities/audit-run';
import { DocumentDetailPage } from '@/_pages/document-detail';
import { ProjectDetailPage } from '@/_pages/project-detail';
import { VersionDetailPage } from '@/_pages/version-detail';

import { DOCUMENT_UID, PROJECT_UID, RUN_ID, VERSION_UID, runStatus } from '../review/fixtures';
import { newClient, renderWith, seedError } from './harness';

// --------------------------------------------------------------------- fixtures

/** A router that records instead of navigating. Nothing in one render pass calls it. */
function stubRouter(pushed: string[]): AppRouterInstance {
  return {
    push: (href: string) => pushed.push(href),
    replace: (href: string) => pushed.push(href),
    back: () => {},
    forward: () => {},
    refresh: () => {},
    prefetch: () => {},
  } as unknown as AppRouterInstance;
}

function version(overrides: Partial<DocumentVersion> = {}): DocumentVersion {
  return {
    version_uid: VERSION_UID,
    document_uid: DOCUMENT_UID,
    project_uid: PROJECT_UID,
    version_ordinal: 1,
    media_type: 'application/pdf',
    byte_size: 58978,
    sha256: '6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f',
    page_count: 8,
    published_at: '2026-09-18T06:55:52.642022Z',
    input_manifest: [],
    display_title: 'AR baseline',
    ...overrides,
  };
}

function versionPage(items: DocumentVersion[]): DocumentVersionPage {
  return { items, page: { next_cursor: null } as DocumentVersionPage['page'] };
}

function runPage(items: RunStatus[]): RunStatusPage {
  return { items, page: { next_cursor: null } as RunStatusPage['page'] };
}

function apiError(status: number, code: ErrorCode, retryable = false): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.0.0-draft.1',
    error_code: code,
    message: 'A caller-safe sentence.',
    correlation_id: 'cid-cold-1',
    retryable,
  };
  return new ApiError(status, envelope, 'cid-cold-1');
}

const DOCUMENTS_KEY = queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT);
const VERSIONS_KEY = queryKeys.versions.list(DOCUMENT_UID, undefined, VERSION_PAGE_LIMIT);
const RUNS_KEY = queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT);

type Client = ReturnType<typeof newClient>;

function withRouter(client: Client, element: ReturnType<typeof createElement>): string {
  return renderWith(
    client,
    createElement(AppRouterContext.Provider, { value: stubRouter([]) }, element),
  );
}

/**
 * The cold-cache assertion, factored because it is the same claim for all three screens:
 * a pending query exists under the key the screen's hook builds. A screen that read state
 * from elsewhere would file none.
 */
function pendingUnder(client: Client, key: readonly unknown[]): boolean {
  const entry = client.getQueryCache().find({ queryKey: [...key] });
  return entry !== undefined && entry.state.data === undefined;
}

// ------------------------------------------------------- /projects/{project_uid}

describe('the project screen asks the server on a cold load (D-16)', () => {
  it('renders a loading state, not "no version in this session"', () => {
    const client = newClient();
    const markup = withRouter(client, createElement(ProjectDetailPage, { projectUid: PROJECT_UID }));

    expect(markup).toContain('Загрузка: документы этого проекта…');
    // The exact sentence W15-RUN measured. Its presence is the defect.
    expect(markup).not.toContain('No version published in this session');
  });

  it('files the pending read under the listDocuments key for THIS project', () => {
    const client = newClient();
    withRouter(client, createElement(ProjectDetailPage, { projectUid: PROJECT_UID }));

    expect(pendingUnder(client, DOCUMENTS_KEY)).toBe(true);
    // Not some other project's: a hook that dropped the parameter would still be pending.
    const other = queryKeys.projects.documents(
      PROJECT_UID.replace(/.$/, 'C'),
      undefined,
      DOCUMENT_PAGE_LIMIT,
    );
    expect(pendingUnder(client, other)).toBe(false);
  });

  it('renders documents that came from the server, each addressable by its version', () => {
    const client = newClient();
    client.setQueryData(DOCUMENTS_KEY, versionPage([version()]));
    const markup = withRouter(client, createElement(ProjectDetailPage, { projectUid: PROJECT_UID }));

    expect(markup).toContain(VERSION_UID);
    expect(markup).toContain(`href="${routes.version(PROJECT_UID, VERSION_UID)}"`);
    expect(markup).toContain(`href="${routes.document(PROJECT_UID, DOCUMENT_UID)}"`);
    expect(markup).toContain('data-document-count="1"');
  });

  it('distinguishes an empty project from a project that does not exist', () => {
    const empty = newClient();
    empty.setQueryData(DOCUMENTS_KEY, versionPage([]));
    const emptyMarkup = withRouter(
      empty,
      createElement(ProjectDetailPage, { projectUid: PROJECT_UID }),
    );
    expect(emptyMarkup).toContain('В этом проекте пока нет документов.');
    expect(emptyMarkup).not.toContain('There is no such project.');

    const missing = newClient();
    seedError(missing, DOCUMENTS_KEY, apiError(404, 'not_found'));
    const missingMarkup = withRouter(
      missing,
      createElement(ProjectDetailPage, { projectUid: PROJECT_UID }),
    );
    // W18-SEAL made the server answer 404 rather than an empty page, precisely so these
    // two are different answers. A screen that collapsed them would undo that.
    expect(missingMarkup).toContain('Такого проекта не существует.');
    expect(missingMarkup).not.toContain('В этом проекте пока нет документов.');
  });

  it('offers a route back to the project list', () => {
    const client = newClient();
    const markup = withRouter(client, createElement(ProjectDetailPage, { projectUid: PROJECT_UID }));
    expect(markup).toContain(`href="${routes.projects()}"`);
  });

  it('does not offer to start a run from here; that lives on the version', () => {
    const client = newClient();
    client.setQueryData(DOCUMENTS_KEY, versionPage([version()]));
    const markup = withRouter(client, createElement(ProjectDetailPage, { projectUid: PROJECT_UID }));
    expect(markup).not.toContain('Запустить прогон');
  });
});

// ------------------------------------------- /projects/{project_uid}/versions/{v}

describe('the version screen asks the server on a cold load (D-16)', () => {
  const screen = (client: Client, versionUid = VERSION_UID, projectUid = PROJECT_UID) =>
    withRouter(client, createElement(VersionDetailPage, { projectUid, versionUid }));

  it('files two pending reads: the version itself and its runs', () => {
    const client = newClient();
    const markup = screen(client);

    expect(pendingUnder(client, queryKeys.versions.detail(VERSION_UID))).toBe(true);
    expect(pendingUnder(client, RUNS_KEY)).toBe(true);
    expect(markup).toContain('Загрузка: эту версию…');
    expect(markup).toContain('Загрузка: прогоны этой версии…');
  });

  it('renders the manifest the server returned, with the version identity', () => {
    const client = newClient();
    client.setQueryData(queryKeys.versions.detail(VERSION_UID), version());
    client.setQueryData(RUNS_KEY, runPage([]));
    const markup = screen(client);

    expect(markup).toContain(VERSION_UID);
    expect(markup).toContain('8');
    expect(markup).toContain('неизменяем');
  });

  it('offers Start run when the version has no run yet', () => {
    const client = newClient();
    client.setQueryData(queryKeys.versions.detail(VERSION_UID), version());
    client.setQueryData(RUNS_KEY, runPage([]));
    const markup = screen(client);

    expect(markup).toContain('По этой версии прогонов не запускалось.');
    expect(markup).toContain('Запустить прогон');
  });

  it('lists the runs that exist, each addressable, without waiting for `running`', () => {
    const client = newClient();
    client.setQueryData(queryKeys.versions.detail(VERSION_UID), version());
    client.setQueryData(RUNS_KEY, runPage([runStatus({ state: 'published' })]));
    const markup = screen(client);

    expect(markup).toContain(`href="${routes.run(PROJECT_UID, RUN_ID)}"`);
    expect(markup).toContain('data-run-count="1"');
    expect(markup).toContain('data-run-state="published"');
    // D-20: nothing here promises a state no response can carry.
    expect(markup).not.toContain('data-run-state="running"');
  });

  it('builds the back link from the fetched body, not from the pasted address', () => {
    const OTHER = PROJECT_UID.replace(/.$/, 'C');
    const client = newClient();
    client.setQueryData(queryKeys.versions.detail(VERSION_UID), version());
    client.setQueryData(RUNS_KEY, runPage([]));
    // The address carries a project this version does not belong to.
    const markup = screen(client, VERSION_UID, OTHER);

    expect(markup).toContain(`href="${routes.project(PROJECT_UID)}"`);
    expect(markup).not.toContain(`href="${routes.project(OTHER)}"`);
  });

  it('refuses a malformed version address without asking the server about it', () => {
    const client = newClient();
    const markup = screen(client, 'ver_lowercase');

    expect(markup).toContain('Это не адрес версии.');
    expect(markup).toContain('Запроса не было.');
    // "Nothing was requested" is a claim about the wire, so it is checked against the
    // cache and not against the sentence. React forbids an early return before a hook,
    // so the version query is constructed -- but `enabled: false` keeps it idle, and the
    // run listing is never mounted at all.
    const fetching = client.getQueryCache().getAll().filter((q) => q.state.fetchStatus !== 'idle');
    expect(fetching).toHaveLength(0);
    expect(client.getQueryCache().find({ queryKey: [...RUNS_KEY] })).toBeUndefined();
  });
});

// ------------------------------------------ /projects/{project_uid}/documents/{d}

describe('the document screen asks the server on a cold load (D-16)', () => {
  const screen = (client: Client, documentUid = DOCUMENT_UID) =>
    renderWith(
      client,
      createElement(DocumentDetailPage, { projectUid: PROJECT_UID, documentUid }),
    );

  it('files the pending read under the listVersions key for THIS document', () => {
    const client = newClient();
    const markup = screen(client);

    expect(pendingUnder(client, VERSIONS_KEY)).toBe(true);
    expect(markup).toContain('Загрузка: версии этого документа…');
  });

  it('renders the versions the server returned, each addressable', () => {
    const client = newClient();
    client.setQueryData(VERSIONS_KEY, versionPage([version()]));
    const markup = screen(client);

    expect(markup).toContain(`href="${routes.version(PROJECT_UID, VERSION_UID)}"`);
    expect(markup).toContain('data-version-count="1"');
  });

  it('says why one version is what this transport can produce, rather than looking empty', () => {
    const client = newClient();
    client.setQueryData(VERSIONS_KEY, versionPage([version()]));
    const markup = screen(client);
    // W18-SEAL section 2: uploadDocument declares no document_uid, so every upload starts
    // a new document. The screen states that rather than leaving a reviewer to wonder
    // whether a version went missing.
    expect(markup).toContain('document_uid');
  });

  it('distinguishes an unknown document from a document with no version', () => {
    const empty = newClient();
    empty.setQueryData(VERSIONS_KEY, versionPage([]));
    expect(screen(empty)).toContain('У документа нет опубликованных версий.');

    const missing = newClient();
    seedError(missing, VERSIONS_KEY, apiError(404, 'not_found'));
    const markup = screen(missing);
    expect(markup).toContain('Такого документа не существует.');
    expect(markup).not.toContain('У документа нет опубликованных версий.');
  });

  it('refuses a malformed document address without asking the server about it', () => {
    const client = newClient();
    expect(screen(client, 'doc_lowercase')).toContain('Это не адрес документа.');
    expect(client.getQueryCache().getAll()).toHaveLength(0);
  });
});
