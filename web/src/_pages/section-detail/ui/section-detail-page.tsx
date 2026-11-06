'use client';

/**
 * «Раздел» — one section of one project (`R-151l`): the original's section page, in our nouns.
 *
 * The list is the server's: `listDocuments` with `section_code` (contract 1.20.0) keeps the documents whose
 * **current** version an expert confirmed for this section, so the page walks this section's documents, not one
 * page of the whole project filtered on the client. They are drawn as the original's card grid (`R-151s`). A
 * document whose section is not confirmed is not here; the project page's «Не классифицировано» group holds it.
 *
 * **Order and filter are the server's** (`UI-PARITY-DOC-AUDIT`, contract 1.34.0). The page asks for `order=audit`: the documents
 * the expert has checked, then the ones processed and still without every verdict, then the ones never audited, by
 * name within each group (`UI-A-49`), across pages and not within one. `?filter=not_run` (read here, from the
 * address the dashboard's «Не запускались» links to) asks for `audit_state=not_run` and says so above the list, with
 * «Показать все» to lift it (`UI-A-38`). Each card carries the chip of its audit state (`UI-A-46`).
 *
 * The route answers a malformed address with not-found; the screen refuses one as well (a project uid without
 * the contract's shape, a section code outside the fifteen), without a request, so it never throws on one.
 */

import { useState } from 'react';
import Link from 'next/link';

import type { ProjectSection as ProjectSectionCode, ProjectUid } from '@/shared/api';
import { EmptyState, ErrorState, LoadingState, PageShell, UnsupportedState } from '@/shared/ui';
import { classifyListingFailure, routes } from '@/shared/lib';
import {
  DocumentCardGrid, NOT_RUN_EMPTY_TITLE, SHOW_ALL_LABEL, notRunFilterSentence, parseSectionAuditFilter, useDocumentList,
} from '@/entities/document-version';
import type { SectionAuditFilter } from '@/entities/document-version';
import type { ProjectSection } from '@/entities/project';
import { findProjectSection, looksLikeProjectUid, projectSectionTitle } from '@/entities/project';
import { DocumentContext } from '@/widgets/document-context';

export interface SectionDetailPageProps {
  readonly projectUid: string;
  readonly sectionCode: string;
  /** The address's `filter` parameter as the route read it; only `not_run` is a filter, anything else shows the section whole. */
  readonly filter?: string | readonly string[] | undefined;
}

export function sectionPageTitle(section: ProjectSection): string {
  return projectSectionTitle(section);
}

export function SectionDetailPage({ projectUid, sectionCode, filter }: SectionDetailPageProps) {
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
  const auditFilter = parseSectionAuditFilter(filter);
  // Keyed by the filter, so lifting it or applying it starts from the first page.
  return <SectionDetail key={auditFilter ?? 'all'} projectUid={projectUid} section={section} auditFilter={auditFilter} />;
}

function SectionDetail({
  projectUid,
  section,
  auditFilter,
}: {
  readonly projectUid: ProjectUid;
  readonly section: ProjectSection;
  readonly auditFilter: SectionAuditFilter | null;
}) {
  const sectionCode = section.code as ProjectSectionCode;
  const [cursors, setCursors] = useState<readonly string[]>([]);
  const cursor = cursors.at(-1);
  const query = useDocumentList(projectUid, cursor, sectionCode, false, undefined, {
    ...(auditFilter === null ? {} : { state: auditFilter }),
    order: 'audit',
  });
  const wholeSection = routes.projectSection(projectUid, sectionCode);

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
  } else if (query.data.items.length === 0 && cursor === undefined && auditFilter !== null) {
    body = (
      <EmptyState
        title={NOT_RUN_EMPTY_TITLE}
        detail="Каждый документ раздела уже анализировался."
        action={<Link href={wholeSection} data-show-all="">{SHOW_ALL_LABEL}</Link>}
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
        {auditFilter === null ? null : (
          <p className="am-note" data-section-filter={auditFilter}>
            {notRunFilterSentence(query.data.items.length, cursors.length === 0 && nextCursor === null)}{' '}
            <Link href={wholeSection} data-show-all="">{SHOW_ALL_LABEL}</Link>
          </p>
        )}
        <DocumentCardGrid
          documents={query.data.items}
          addresses={(version) => ({
            href: routes.version(projectUid, version.version_uid),
            documentHref: routes.document(projectUid, version.document_uid),
          })}
          reviewAddress={(runId) => routes.review(projectUid, runId)}
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
