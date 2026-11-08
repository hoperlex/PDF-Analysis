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

import type { DocumentAudit, DocumentUid, ProjectSection, ProjectUid } from '@/shared/api';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { classifyListingFailure, routes } from '@/shared/lib';
import { VersionRow, useSectionDocumentWalk, useVersionList } from '@/entities/document-version';
import { findProjectSection } from '@/entities/project';

export interface VersionListProps {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
  /**
   * `UI-A-45`: the section the document's current version is confirmed for, when it is. The audit state of a version is
   * read for the documents of a listing (`listDocuments`), never for a document's version list, so the current version's chip
   * comes from its section's listing -- the walk the section strip of this screen already reads, under the same keys, so
   * it costs no further request. Absent, or while the walk is read, no row carries a chip.
   */
  readonly sectionCode?: string | undefined;
}

const NO_AUDITS: ReadonlyMap<string, DocumentAudit> = new Map();

/** The versions of a document whose current version is confirmed for a section: the chip of that version, once its section is read. */
export function VersionList({ projectUid, documentUid, sectionCode }: VersionListProps) {
  const section = sectionCode === undefined ? null : findProjectSection(sectionCode);
  if (section === null) return <VersionRows projectUid={projectUid} documentUid={documentUid} audits={NO_AUDITS} />;
  // Keyed, so another section (or project) is another walk and never inherits this one's cursors.
  return <AuditedVersionRows key={`${projectUid}:${section.code}`} projectUid={projectUid} documentUid={documentUid} sectionCode={section.code} />;
}

function AuditedVersionRows({ projectUid, documentUid, sectionCode }: {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
  readonly sectionCode: ProjectSection;
}) {
  const walk = useSectionDocumentWalk(projectUid, sectionCode);
  const audits = new Map<string, DocumentAudit>();
  if (walk.status === 'complete') {
    for (const item of walk.items) {
      if (item.document_uid === documentUid && item.audit !== undefined) audits.set(item.version_uid, item.audit);
    }
  }
  return <VersionRows projectUid={projectUid} documentUid={documentUid} audits={audits} />;
}

/** The rows. `audits` is the audit state of the versions the screen has one for, by `version_uid`. */
function VersionRows({ projectUid, documentUid, audits }: {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
  readonly audits: ReadonlyMap<string, DocumentAudit>;
}) {
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
        {page.items.map((version) => {
          const audit = audits.get(version.version_uid);
          return (
            <VersionRow
              key={version.version_uid}
              version={audit === undefined ? version : { ...version, audit }}
              href={routes.version(projectUid, version.version_uid)}
              reviewAddress={(runId) => routes.review(projectUid, runId)}
            />
          );
        })}
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
