'use client';

/**
 * The published versions of one document, read from the server on mount.
 *
 * It was written for a list while the transport could produce only one row (`W18-SEAL` §2:
 * `uploadDocument` declared no `document_uid`), so the count is rendered rather than assumed.
 * Since `W59-VERSION-UPLOAD-01` the document screen uploads further versions
 * (`uploadDocumentVersion`) and this list grows with no change to its shape.
 *
 * The note under the rows said, until then, that one version per upload was expected; it now
 * states what holds for every row instead — each version is immutable and stays addressable,
 * and the newest is the document's current one — and, by `R-18`, still names no operation or
 * field of the transport. `D-58`.
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
          Каждая версия неизменяема и остаётся адресуемой: новая версия становится текущей,
          а прежние не меняются и ничего из загруженного не теряется.
        </em>
      </p>
      <div className="am-pager">
        {cursor === undefined ? null : (
          <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => setCursor(undefined)}>
            В начало
          </button>
        )}
        {nextCursor === null ? null : (
          <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => setCursor(nextCursor)}>
            Дальше
          </button>
        )}
      </div>
    </div>
  );
}
