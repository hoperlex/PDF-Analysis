'use client';

/**
 * «Раздел» — one section of one project (`R-151l`): the original's section page, in our nouns.
 *
 * The list is the server's: `listDocuments` with `section_code` (contract 1.20.0) keeps the documents whose
 * **current** version an expert confirmed for this section, so the page walks this section's documents, not one
 * page of the whole project filtered on the client. They are drawn as the original's card grid (`R-151s`). A
 * document whose section is not confirmed is not here; the project page's «Не классифицировано» group holds it.
 *
 * The route answers a malformed address with not-found; the screen refuses one as well (a project uid without
 * the contract's shape, a section code outside the fifteen), without a request, so it never throws on one.
 */

import { useState } from 'react';
import Link from 'next/link';

import type { ProjectSection as ProjectSectionCode, ProjectUid } from '@/shared/api';
import { EmptyState, ErrorState, LoadingState, PageShell, UnsupportedState } from '@/shared/ui';
import { classifyListingFailure, routes } from '@/shared/lib';
import { DocumentCardGrid, useDocumentList } from '@/entities/document-version';
import type { ProjectSection } from '@/entities/project';
import { findProjectSection, looksLikeProjectUid, projectSectionTitle } from '@/entities/project';
import { DocumentContext } from '@/widgets/document-context';

export interface SectionDetailPageProps {
  readonly projectUid: string;
  readonly sectionCode: string;
}

export function sectionPageTitle(section: ProjectSection): string {
  return projectSectionTitle(section);
}

export function SectionDetailPage({ projectUid, sectionCode }: SectionDetailPageProps) {
  const section = findProjectSection(sectionCode);
  if (!looksLikeProjectUid(projectUid) || section === null) {
    return (
      <PageShell title="Раздел" actions={<Link href={routes.projects()}>Все проекты</Link>}>
        <UnsupportedState
          title="Это не адрес раздела."
          detail="Раздел адресуется идентификатором проекта и кодом одного из пятнадцати разделов. Запроса не было."
        />
      </PageShell>
    );
  }
  return <SectionDetail projectUid={projectUid} section={section} />;
}

function SectionDetail({ projectUid, section }: { readonly projectUid: ProjectUid; readonly section: ProjectSection }) {
  const sectionCode = section.code as ProjectSectionCode;
  const [cursors, setCursors] = useState<readonly string[]>([]);
  const cursor = cursors.at(-1);
  const query = useDocumentList(projectUid, cursor, sectionCode);

  let body;
  if (query.isPending) {
    body = <LoadingState what="документы раздела" />;
  } else if (query.isError) {
    const failure = classifyListingFailure(query.error, { collection: 'документы раздела', parent: 'project' });
    body = (
      <ErrorState
        title={failure.title}
        detail={<span data-list-failure={failure.kind}>{failure.detail}</span>}
        correlationId={failure.correlationId}
        {...(failure.retryable ? { onRetry: () => void query.refetch(), retryLabel: 'Повторить' } : {})}
      />
    );
  } else if (query.data.items.length === 0 && cursor === undefined) {
    body = (
      <EmptyState
        title="В этом разделе пока нет документов."
        detail="Документ попадает в раздел, когда эксперт подтвердит раздел для его текущей версии на экране версии."
        action={<Link href={routes.project(projectUid)}>К разделам проекта</Link>}
      />
    );
  } else {
    const nextCursor = query.data.page.next_cursor;
    body = (
      <>
        <DocumentCardGrid
          documents={query.data.items}
          addresses={(version) => ({
            href: routes.version(projectUid, version.version_uid),
            documentHref: routes.document(projectUid, version.document_uid),
          })}
        />
        <div className="am-pager">
          {cursors.length === 0 ? null : (
            <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => setCursors(cursors.slice(0, -1))}>
              Назад
            </button>
          )}
          {nextCursor === null ? null : (
            <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => setCursors([...cursors, nextCursor])}>
              Далее
            </button>
          )}
        </div>
      </>
    );
  }

  return (
    <PageShell
      title={sectionPageTitle(section)}
      subtitle="Документы проекта, чья текущая версия подтверждена для этого раздела."
      actions={(
        <button type="button" className="am-button am-button--quiet" disabled={query.isFetching} onClick={() => void query.refetch()}>
          {query.isFetching ? 'Обновляется…' : 'Обновить'}
        </button>
      )}
    >
      <DocumentContext projectUid={projectUid} current="section" sectionLabel={`${section.abbr} ${section.name}`} />
      <section className="am-section" data-section-page={section.code}>
        {body}
      </section>
    </PageShell>
  );
}
