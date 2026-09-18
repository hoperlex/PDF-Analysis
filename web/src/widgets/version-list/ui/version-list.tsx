'use client';

/**
 * The published versions of one document, read from the server on mount.
 *
 * It returns one row today. That is a fact about the transport and not about this widget:
 * `uploadDocument` declares no `document_uid`, so every upload starts a new document at
 * ordinal 1, while `IngestService.upload_single_pdf` underneath does take one and does
 * publish a second version. `W18-SEAL` §2 measured both halves. So this is written for a
 * list, the count is rendered rather than assumed, and the day the transport carries a
 * `document_uid` this screen needs no change.
 *
 * It says so on screen, too, rather than leaving a reviewer to wonder whether a version
 * is missing.
 */

import { useState } from 'react';

import type { DocumentUid, ProjectUid } from '@/shared/api';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { classifyListingFailure, routes } from '@/shared/lib';
import { VersionRow, useVersionList } from '@/entities/document-version';

export interface VersionListProps {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
}

export function VersionList({ projectUid, documentUid }: VersionListProps) {
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const query = useVersionList(documentUid, cursor);

  if (query.isPending) return <LoadingState what="this document's versions" />;

  if (query.isError) {
    const failure = classifyListingFailure(query.error, {
      collection: "this document's versions",
      parent: 'document',
    });
    return (
      <ErrorState
        title={failure.title}
        detail={<span data-list-failure={failure.kind}>{failure.detail}</span>}
        correlationId={failure.correlationId}
        {...(failure.retryable
          ? { onRetry: () => void query.refetch(), retryLabel: 'Try again' }
          : {})}
      />
    );
  }

  const page = query.data;

  if (page.items.length === 0) {
    return (
      <EmptyState
        title="This document has no published version."
        detail="A document whose upload never completed has nothing to open, stream or run against."
      />
    );
  }

  const nextCursor = page.page.next_cursor;

  return (
    <div data-version-count={page.items.length}>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {page.items.map((version) => (
          <VersionRow
            key={version.version_uid}
            version={version}
            href={routes.version(projectUid, version.version_uid)}
          />
        ))}
      </ul>
      <p>
        <em>
          One version per upload: this surface gives `uploadDocument` no `document_uid`, so
          every upload starts a new document at ordinal 1. The service underneath already
          publishes a second version onto an existing document; only the transport withholds
          it.
        </em>
      </p>
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
