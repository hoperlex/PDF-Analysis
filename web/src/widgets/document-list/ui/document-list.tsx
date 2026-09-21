'use client';

/**
 * The documents of one project, read from the server on mount.
 *
 * This is the widget `D-16` was missing. The project screen used to render the version
 * held in the *previous* screen's React state, so a fresh tab showed "No version
 * published in this session" over a project whose rows, objects, runs and decisions were
 * all still in PostgreSQL and the store. This asks `listDocuments`.
 *
 * Every outcome of the read is one of the mandatory states and none of them is silence.
 * The one that matters here is the separation `W18-SEAL` §2 built into the API: an
 * unknown project is `404` and an empty project is `200` with no items, and this renders
 * them as two different sentences, because "there is no such project" and "this project
 * is empty" are things a reader acts on differently.
 */

import { useState } from 'react';

import type { ProjectUid } from '@/shared/api';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { classifyListingFailure, routes } from '@/shared/lib';
import { VersionRow, useDocumentList } from '@/entities/document-version';

export interface DocumentListProps {
  readonly projectUid: ProjectUid;
}

export function DocumentList({ projectUid }: DocumentListProps) {
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const query = useDocumentList(projectUid, cursor);

  if (query.isPending) return <LoadingState what="документы этого проекта" />;

  if (query.isError) {
    const failure = classifyListingFailure(query.error, {
      collection: 'документы этого проекта',
      parent: 'project',
    });
    return (
      <ErrorState
        title={failure.title}
        detail={<span data-list-failure={failure.kind}>{failure.detail}</span>}
        correlationId={failure.correlationId}
        {...(failure.retryable
          ? { onRetry: () => void query.refetch(), retryLabel: 'Повторить' }
          : {})}
      />
    );
  }

  const page = query.data;

  if (page.items.length === 0) {
    return (
      <EmptyState
        title="В этом проекте пока нет документов."
        detail="Загрузите PDF годового отчёта выше. Ничего не потеряно: в проекте действительно нет опубликованных документов."
      />
    );
  }

  const nextCursor = page.page.next_cursor;

  return (
    <div data-document-count={page.items.length}>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {page.items.map((version) => (
          <VersionRow
            key={version.document_uid}
            version={version}
            href={routes.version(projectUid, version.version_uid)}
            secondary={{
              href: routes.document(projectUid, version.document_uid),
              label: 'Все версии документа',
            }}
          />
        ))}
      </ul>
      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
        {cursor === undefined ? null : (
          <button type="button" className="am-button" onClick={() => setCursor(undefined)}>
            First page
          </button>
        )}
        {nextCursor === null ? null : (
          <button type="button" className="am-button" onClick={() => setCursor(nextCursor)}>
            Next page
          </button>
        )}
      </div>
    </div>
  );
}
