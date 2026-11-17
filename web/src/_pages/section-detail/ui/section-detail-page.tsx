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
 * **The original's section page, in full** (`UI-A-35`, `UI-A-38`, `UI-A-51`, `UI-A-52`, `UI-A-53`, `UIP-S02-01`). Over the cards stands one
 * line (`SectionHeader`): «←» to the object's «Главная», the section's code and name, «(N)» with the box that chooses every
 * document, the plaques of the audit states counted over the documents the page holds (or the server's count of the section), «Выделить
 * необработанные» and «Снять выделение», and at the right end «+ Добавить» and «Обновить». There is no second line of crumbs in the page.
 * The cards open with the Σ card «Оптимизация раздела». The box, «Выделить необработанные» and «ждут решения N» choose across every page
 * of the listing in view, read to its end by the server's cursor (`useListingWalk`), and the chosen documents start together with one
 * consent for the batch (`R-151c`), from the bar that sticks to the bottom of the area while a card is chosen (`SectionSelectionBar`); the tag filter and «Показать архивные» stand in their own row over the cards (`R-151e`, `R-151a`);
 * «+ Добавить» leads to the project's upload.
 *
 * The route answers a malformed address with not-found; the screen refuses one as well (a project uid without
 * the contract's shape, a section code outside the fifteen), without a request, so it never throws on one.
 */

import { useState } from 'react';
import Link from 'next/link';

import type { DocumentVersion, ProjectSection as ProjectSectionCode, ProjectUid } from '@/shared/api';
import { EmptyState, ErrorState, LoadingState, PageShell, UnsupportedState } from '@/shared/ui';
import { classifyListingFailure, routes } from '@/shared/lib';
import { useMayActAsExpert } from '@/entities/account';
import {
  DocumentCardGrid, NOT_RUN_EMPTY_TITLE, SHOW_ALL_LABEL, auditTally, notRunFilterSentence,
  parseSectionAuditFilter, useSectionDocumentList, withNotRunFilter,
} from '@/entities/document-version';
import type { SectionAuditFilter } from '@/entities/document-version';
import type { ProjectSection } from '@/entities/project';
import { findProjectSection, looksLikeProjectUid, projectSectionTitle, useProject } from '@/entities/project';
import { ArchivedToggle, TagFilter, selectionSlot, useBatchSelection, useSectionFigures } from '@/widgets/project-sections';
import { groupDocuments } from '../model/group-documents';
import { wholeListing } from '../model/section-choices';
import { useListingWalk } from '../model/use-listing-walk';
import { SectionBatchBar } from './section-batch-bar';
import { GroupsWalkNote, SectionGroups } from './section-groups';
import { SectionHeader } from './section-header';
import { SectionSelectionBar } from './section-selection-bar';
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
      <PageShell title="Раздел" actions={<Link href={routes.projects()}>Все объекты</Link>}>
        <UnsupportedState
          title="Это не адрес раздела."
          detail="Раздел адресуется идентификатором объекта и кодом одного из пятнадцати разделов. Запроса не было."
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
  const optimisation = routes.sectionOptimisation(section.code, projectUid);
  // `UIP-S02-01`: the object's name for the arrow to its «Главная», read by identity (`getProject`).
  const objectName = useProject(projectUid).data?.name;
  // `R-151c`: the cards a reader chose to start together.
  const mayAct = useMayActAsExpert();
  const batch = useBatchSelection(mayAct);
  // `UI-A-35`, `UIP-S02-06`: a listing of more than one page is read to its end — for «Выбрать все», and for the groups, which
  // are made of the whole listing and are shown to every reader.
  const partialList = query.data !== undefined && (cursors.length > 0 || query.data.page.next_cursor !== null);
  const walk = useListingWalk(partialList, { projectUid, sectionCode, auditFilter, includeArchived: showArchived, tag });
  // `UIP-S02-06`: the cards by group when the whole listing is known and a document of it has one; `null`, the plain grid.
  const whole = query.data === undefined ? null : wholeListing(query.data.items, walk);
  const groups = whole === null ? null : groupDocuments(whole);
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
        action={<Link className={styles.backLink} href={routes.project(projectUid)}>К разделам объекта</Link>}
      />
    );
  } else {
    const nextCursor = query.data.page.next_cursor;
    // `UI-A-53`, `UIP-S02-02`: the original's Σ card, the section's own control and not a document: the same size as a
    // document's, the title opens the section's optimisation and the two links open its two views, with no figures.
    const sigma = (
      <>
        <p className={styles.sigmaTitle}>
          <Link href={optimisation} data-section-optimisation-link={section.code}>
            <span className={styles.sigma} aria-hidden="true">Σ</span> Оптимизация раздела
          </Link>
        </p>
        <span className={styles.sigmaLinks}>
          <Link className={styles.sigmaLink} href={optimisation} data-section-optimisation-view="specification">Спецификация</Link>
          {/* «Кандидаты»: the candidates the experts accepted, the view the address names `accepted`. */}
          <Link className={styles.sigmaLink} href={`${optimisation}&tab=accepted`} data-section-optimisation-view="accepted">Кандидаты</Link>
        </span>
      </>
    );
    // What every grid of cards takes but its documents and its first cell, whether it is the plain grid or a group's.
    const grid = {
      classification: 'stage' as const,
      select: selectionSlot(batch.selection),
      addresses: (version: DocumentVersion) => ({
        href: routes.version(projectUid, version.version_uid),
        documentHref: routes.document(projectUid, version.document_uid),
      }),
      reviewAddress: (runId: string) => routes.review(projectUid, runId),
      optimisationAddress: (version: DocumentVersion) => routes.documentOptimisation(projectUid, version.document_uid),
    };
    body = (
      <>
        {auditFilter === null ? null : (
          <p className="am-note" data-section-filter={auditFilter}>
            {groups === null || whole === null
              ? notRunFilterSentence(query.data.items.length, cursors.length === 0 && nextCursor === null)
              : notRunFilterSentence(whole.length, true)}{' '}
            <Link href={wholeSection} data-show-all="">{SHOW_ALL_LABEL}</Link>
          </p>
        )}
        {groups === null ? (
          <>
            {/* `UIP-S02-06`: until the whole listing is read the page cannot say whether the section has groups. */}
            <GroupsWalkNote walk={walk} />
            <DocumentCardGrid documents={query.data.items} leading={sigma} {...grid} />
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
        ) : (
          // `UIP-S02-06`: the whole listing, by group; there is no page to turn.
          <SectionGroups groups={groups} leading={sigma} grid={grid} />
        )}
      </>
    );
  }

  // `UI-A-35`: the original's row of numbers, counted over the documents this page holds; `UIP-S02-01`: in the header's one line.
  return (
    <section className="am-page" data-screen="section">
      <SectionHeader
        projectUid={projectUid}
        section={section}
        objectName={objectName}
        documents={query.data?.items}
        walk={walk}
        tally={query.data === undefined ? null : (figures ?? auditTally(query.data.items))}
        partial={partialList && figures === undefined}
        // `UI-A-38`: «не запускались N» narrows the page to those documents; narrowed already, it is plain.
        notRunHref={auditFilter === null ? withNotRunFilter(wholeSection) : undefined}
        selection={batch}
        addHref={`${routes.project(projectUid)}#upload`}
        refreshing={query.isFetching}
        onRefresh={() => void query.refetch()}
      />
      <div className="am-page__body am-page__body--canvas">
        <section className={batch.chosenCount > 0 ? `am-section ${styles.reserve}` : 'am-section'} data-section-page={section.code}>
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
          {/* `UIP-S02-03`: the last thing of the page, so scrolled to its end it covers no card; `reserve` is room below the cards. */}
          <SectionSelectionBar selection={batch} />
        </section>
      </div>
    </section>
  );
}
