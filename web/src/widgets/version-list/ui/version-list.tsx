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

  if (query.isPending) return <LoadingState what="версии этого документа" />;

  if (query.isError) {
    const failure = classifyListingFailure(query.error, {
      collection: 'версии этого документа',
      parent: 'document',
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
        title="У документа нет опубликованных версий."
        detail="У документа, загрузка которого не завершилась, нечего открыть, отдать или проверить."
      />
    );
  }

  const nextCursor = page.page.next_cursor;

  return (
    <div data-version-count={page.items.length}>
      <ul className="am-rows">
        {page.items.map((version) => (
          <VersionRow
            key={version.version_uid}
            version={version}
            href={routes.version(projectUid, version.version_uid)}
          />
        ))}
      </ul>
      <p className="am-note">
        <em>
          Одна версия на загрузку: сегодня каждая загрузка заводит новый документ, а не
          новую версию уже загруженного. Ограничение в передаче данных, а не в хранилище:
          вторую версию оно умеет публиковать, и ничего из загруженного не потеряно.
        </em>
      </p>
      <div className="am-pager">
        {cursor === undefined ? null : (
          <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => setCursor(undefined)}>
            First page
          </button>
        )}
        {nextCursor === null ? null : (
          <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => setCursor(nextCursor)}>
            Next page
          </button>
        )}
      </div>
    </div>
  );
}
