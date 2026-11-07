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
 * **The original's section page, in full** (`UI-A-35`, `UI-A-38`, `UI-A-51`, `UI-A-52`, `UI-A-53`). The row under the title is
 * the original's row of numbers (documents, not started, awaiting a decision, checked, findings), counted over the
 * documents the page holds, with no further request. The cards open with the Σ card «Оптимизация раздела». «Выбрать
 * все» and «Запустить аудит (N)» start the section's documents together, one consent for the batch (`R-151c`); «Выбрать все»
 * and «Выбрать не запускавшиеся» choose across every page of the listing in view, read to its end by the server's cursor
 * (`useListingWalk`), with the count in the button and no cap; the
 * tag filter and «Показать архивные» are the project page's (`R-151e`, `R-151a`); «Добавить документ» leads to the
 * project's upload.
 *
 * The route answers a malformed address with not-found; the screen refuses one as well (a project uid without
 * the contract's shape, a section code outside the fifteen), without a request, so it never throws on one.
 */

import { useState } from 'react';
import Link from 'next/link';

import type { ProjectSection as ProjectSectionCode, ProjectUid } from '@/shared/api';
import { EmptyState, ErrorState, LoadingState, PageShell, UnsupportedState } from '@/shared/ui';
import { classifyListingFailure, routes } from '@/shared/lib';
import { useMayActAsExpert } from '@/entities/account';
import {
  AuditTallyLine, DocumentCardGrid, NOT_RUN_EMPTY_TITLE, SHOW_ALL_LABEL, auditTally, notRunFilterSentence,
  parseSectionAuditFilter, useSectionDocumentList, withNotRunFilter,
} from '@/entities/document-version';
import type { SectionAuditFilter } from '@/entities/document-version';
import type { ProjectSection } from '@/entities/project';
import { findProjectSection, looksLikeProjectUid, projectSectionTitle } from '@/entities/project';
import { DocumentContext } from '@/widgets/document-context';
import { ArchivedToggle, TagFilter, selectionSlot, useBatchSelection, useSectionFigures } from '@/widgets/project-sections';
import { useListingWalk } from '../model/use-listing-walk';
import { SectionBatchBar } from './section-batch-bar';
import styles from './section-detail-page.module.css';

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
  // `R-151a`, `R-151e`: archived documents on request, and one tag; either starts the listing from its first page.
  const [showArchived, setShowArchived] = useState(false);
  const [tag, setTag] = useState<string | null>(null);
  // The listing and its order are the entity's, so the document page's «n из m» walks the same one.
  const query = useSectionDocumentList(projectUid, sectionCode, cursor, auditFilter, {
    includeArchived: showArchived,
    ...(tag === null ? {} : { tag }),
  });
  const wholeSection = routes.projectSection(projectUid, sectionCode);
  // `R-151c`: the cards a reader chose to start together.
  const mayAct = useMayActAsExpert();
  const batch = useBatchSelection(mayAct);
  // `UI-A-35`: a listing of more than one page is read to its end for «Выбрать все», but only for a session that can start an audit.
  const partialList = query.data !== undefined && (cursors.length > 0 || query.data.page.next_cursor !== null);
  const walk = useListingWalk(mayAct && partialList, { projectUid, sectionCode, auditFilter, includeArchived: showArchived, tag });
  // `UI-A-35`: the server's count of this section over the whole project, used while nothing narrows the listing.
  const exact = useSectionFigures(projectUid);
  const figures = auditFilter === null && !showArchived && tag === null ? exact.data?.get(section.code) : undefined;

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
          classification="stage"
          leading={
            // `UI-A-53`: the original's Σ card, the section's own control and not a document.
            <>
              <span className={`am-badge am-badge--active ${styles.sigmaBadge}`}>Σ сводная</span>
              <Link href={routes.sectionOptimisation(section.code, projectUid)} data-section-optimisation-link={section.code}>
                Оптимизация раздела
              </Link>
              <span className={styles.sigmaNote}>спецификация, кандидаты на замену, принятое</span>
            </>
          }
          select={selectionSlot(batch.selection)}
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

  // `UI-A-35`: the original's row of numbers, counted over the documents this page holds.
  return (
    <PageShell
      title={sectionPageTitle(section)}
      subtitle={query.data === undefined ? undefined : (
        <AuditTallyLine
          tally={figures ?? auditTally(query.data.items)}
          partial={partialList && figures === undefined}
          label={`${section.abbr} ${section.name}`}
          // `UI-A-38`: «не запускались N» narrows the page to those documents; narrowed already, it is plain.
          notRunHref={auditFilter === null ? withNotRunFilter(wholeSection) : undefined}
        />
      )}
      actions={(
        <>
          {/* `UI-A-56`: the original's «+ Добавить»; the upload form is the project page's. */}
          <Link className="am-button am-button--quiet" href={`${routes.project(projectUid)}#upload`} data-section-add="">
            Добавить документ
          </Link>{' '}
          <button type="button" className="am-button am-button--quiet" disabled={query.isFetching} onClick={() => void query.refetch()}>
            {query.isFetching ? 'Обновляется…' : 'Обновить'}
          </button>
        </>
      )}
    >
      <DocumentContext projectUid={projectUid} current="section" sectionLabel={`${section.abbr} ${section.name}`} />
      <section className="am-section" data-section-page={section.code}>
        <div className={styles.filters}>
          <ArchivedToggle
            checked={showArchived}
            onChange={(checked) => {
              setShowArchived(checked);
              setCursors([]);
            }}
          />
          <TagFilter projectUid={projectUid} tag={tag} onTag={(next) => { setTag(next); setCursors([]); }} />
        </div>
        {query.data === undefined ? null : (
          <SectionBatchBar projectUid={projectUid} selection={batch} pageDocuments={query.data.items} walk={walk} />
        )}
        {body}
      </section>
    </PageShell>
  );
}
