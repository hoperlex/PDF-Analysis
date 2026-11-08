'use client';

/**
 * The project's sections, holding the project's documents (`W59-SECTION-UI-01`).
 *
 * **What replaced what.** Until this lane the widget was `R-18`'s honest stub: fourteen
 * section tabs, one of which opened the project's whole document list, thirteen of which
 * said there was nothing there yet — because nothing in the product could say which section
 * a document belonged to. Since `W59-SECTION-SEAL-01` an expert confirms a version's project
 * stage and section, and the version carries that confirmation. So this is now the project's
 * real storage structure: the fifteen sections in the order of the owner's poll answer
 * `S-5`, each listing the documents whose **current** version is confirmed for it, with the
 * stage on every row, and «Не классифицировано» for the documents still waiting for an expert.
 *
 * **One read.** It is `listDocuments`, the same request the project screen always made, and
 * the grouping is `../model/structure.ts` over its items: each item is the document's current
 * version, and its `classification` is the contract's own field. No request per document.
 *
 * **Paging.** The grouping covers the page the server answered (fifty documents); the pager
 * underneath moves to the next page and the structure regroups it, and the screen says when
 * there is more than one page rather than letting a reader take one page for the project.
 *
 * **Order and state** (`UI-PARITY-DOC-AUDIT`, contract 1.34.0). The request asks for `order=audit`, so inside every group the
 * documents the expert has checked come first, then the ones processed and still without every verdict, then the ones
 * never audited, by name within each (`UI-A-49`) -- the server's order, kept by the grouping and not re-sorted here. Each
 * card carries the chip of its audit state (`UI-A-46`).
 *
 * Every row links to its version and to its document, exactly as the flat list did, so the
 * journey's walk from the project to a document is unchanged.
 */

import { useState } from 'react';
import Link from 'next/link';

import type { DocumentVersion, ProjectUid } from '@/shared/api';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { classifyListingFailure, routes } from '@/shared/lib';
import { useMayActAsExpert } from '@/entities/account';
import {
  AuditTallyLine, DocumentCardGrid, auditTally, useDocumentList,
} from '@/entities/document-version';

import { useSectionFigures } from '../api/use-section-figures';
import type { SectionFigures } from '../model/section-figures';
import { UNCLASSIFIED_FIGURES, totalFigures } from '../model/section-figures';
import { projectStructure } from '../model/structure';
import type { CardSelection } from '../model/use-batch-selection';
import { startable, useBatchSelection } from '../model/use-batch-selection';
import { BatchBar, selectionSlot } from './batch-bar';
import { ArchivedToggle, TagFilter } from './document-filters';
import styles from './project-sections.module.css';

export interface ProjectSectionsProps {
  readonly projectUid: ProjectUid;
}

export type { CardSelection };
export { startable };

function DocumentRows({
  projectUid,
  documents,
  toClassification = false,
  selection,
}: {
  readonly projectUid: ProjectUid;
  readonly documents: readonly DocumentVersion[];
  readonly selection?: CardSelection | undefined;
  /**
   * Open each version at its stage-and-section panel rather than at the top: the reader of
   * «Не классифицировано» came to confirm a section, and that is where it is done.
   */
  readonly toClassification?: boolean;
}) {
  // `R-151s` (UI-A-45): the original's card grid, on our tokens; each card is one document's current version.
  return (
    <DocumentCardGrid
      documents={documents}
      // The group says the section (or that there is none), so the cards say only the stage.
      classification={toClassification ? 'none' : 'stage'}
      addresses={(version) => ({
        href: toClassification
          ? routes.versionClassification(projectUid, version.version_uid)
          : routes.version(projectUid, version.version_uid),
        documentHref: routes.document(projectUid, version.document_uid),
      })}
      reviewAddress={(runId) => routes.review(projectUid, runId)}
      select={selectionSlot(selection)}
    />
  );
}

export interface ProjectStructureViewProps {
  readonly projectUid: ProjectUid;
  readonly items: readonly DocumentVersion[];
  /** Whether the server has a further page of this project's documents. */
  readonly hasNextPage: boolean;
  /** `R-151c`: selection boxes on the startable cards, for a reader who may start runs. */
  readonly selection?: CardSelection | undefined;
  /**
   * `UI-A-35`: the server's count of each section over the whole project. Given, a section's row of figures is exact;
   * absent (still loading, failed, or a narrowed listing), it counts the page and says so.
   */
  readonly figures?: SectionFigures | undefined;
}

/** The grouped structure of one page of documents. Rendered by the static harness. */
export function ProjectStructureView({ projectUid, items, hasNextPage, selection, figures }: ProjectStructureViewProps) {
  const structure = projectStructure(items);
  // `UI-A-36`: the sections' column sums, from the server's figures only; none while those are absent or incomplete.
  const sum = figures === undefined ? undefined : totalFigures(figures);
  return (
    <div data-project-structure="" data-document-count={items.length}>
      <p className={styles.rule} data-section-rule="confirmed">
        Документ стоит в разделе, который эксперт подтвердил для его текущей версии; до этого он в группе
        «Не классифицировано», и прогон по нему не запускается.
      </p>
      {hasNextPage ? (
        <p className="am-note" data-structure-page="partial">
          Показаны документы этой страницы списка; остальные документы проекта — на следующих
          страницах.
        </p>
      ) : null}
      <ol className={styles.sections}>
        {structure.sections.map(({ section, documents }) => {
          // The server's count may know of documents on other pages: the group is not empty then, though this page has none.
          const exact = figures?.get(section.code);
          const total = Math.max(exact?.documents ?? 0, documents.length);
          return (
            <li
              key={section.code}
              className={styles.section}
              data-section-group={section.code}
              data-section-documents={documents.length}
            >
              <details className={total === 0 ? `${styles.card} ${styles.cardEmpty}` : styles.card} open={total > 0}>
                <summary className={styles.cardHeader}>
                  {total === 0 ? (
                    <span className={styles.code}>{section.code}</span>
                  ) : (
                    // The original's section badge is a link to the section's page; here it is one click from the project.
                    <Link
                      className={styles.codeLink}
                      href={routes.projectSection(projectUid, section.code)}
                      title={`К разделу ${section.abbr}`}
                      data-section-code-link={section.code}
                    >
                      <span className={styles.code}>{section.code}</span>
                    </Link>
                  )}
                  <span className={styles.headText}>
                    <h3 className={styles.heading}>
                      <span className={styles.abbr}>{section.abbr}</span> {section.name}
                      {total === 0 ? <span className={styles.count}> — документов нет</span> : null}
                    </h3>
                    {total === 0 ? null : (
                      // `UI-A-35`: the original's row of numbers: the server's, else the page's own documents.
                      <AuditTallyLine
                        tally={exact ?? auditTally(documents)}
                        partial={hasNextPage && exact === undefined}
                        label={`${section.abbr} ${section.name}`}
                      />
                    )}
                  </span>
                  <span className={styles.chevron} aria-hidden="true">›</span>
                </summary>
                {total === 0 ? null : (
                  <div className={styles.cardBody}>
                    {/* `R-151l`: the section's own page lists every document of the section, not one page of the project. */}
                    <p data-section-page-link={section.code}>
                      <Link href={routes.projectSection(projectUid, section.code)}>Открыть раздел</Link>
                      {/* `UI-A-53`: the section's optimisation, with the project and the section in the address. */}
                      {' · '}
                      <Link href={routes.sectionOptimisation(section.code, projectUid)} data-section-optimisation-link={section.code}>
                        Оптимизация раздела
                      </Link>
                    </p>
                    {documents.length === 0 ? null : (
                      <DocumentRows projectUid={projectUid} documents={documents} selection={selection} />
                    )}
                  </div>
                )}
              </details>
            </li>
          );
        })}
        {sum === undefined ? null : (
          // `UI-A-36`: the original's «Σ Итого», after the sections it adds up; «Не классифицировано» below is not in it.
          <li className={`${styles.section} ${styles.totalCard}`} data-section-total="" data-section-documents={sum.documents}>
            <div className={`${styles.card} ${styles.totalBody}`}>
              <span className={styles.code}>Σ</span>
              <span className={styles.headText}>
                <h3 className={styles.heading}>Итого по разделам</h3>
                <AuditTallyLine tally={sum} label="Итого по разделам" />
              </span>
            </div>
          </li>
        )}
        {(() => {
          const exact = figures?.get(UNCLASSIFIED_FIGURES);
          const total = Math.max(exact?.documents ?? 0, structure.unclassified.length);
          return (
            <li
              className={styles.section}
              data-section-group="unclassified"
              data-section-documents={structure.unclassified.length}
            >
              <details className={total === 0 ? `${styles.card} ${styles.cardEmpty}` : styles.card} open={total > 0}>
                <summary className={styles.cardHeader}>
                  <span className={styles.code}>—</span>
                  <span className={styles.headText}>
                    <h3 className={styles.heading}>
                      Не классифицировано
                      {total === 0 ? <span className={styles.count}> — документов нет</span> : null}
                    </h3>
                    {total === 0 ? null : (
                      <AuditTallyLine
                        tally={exact ?? auditTally(structure.unclassified)}
                        partial={hasNextPage && exact === undefined}
                        label="Не классифицировано"
                      />
                    )}
                  </span>
                  <span className={styles.chevron} aria-hidden="true">›</span>
                </summary>
                {structure.unclassified.length === 0 ? null : (
                  <div className={styles.cardBody}>
                    <DocumentRows projectUid={projectUid} documents={structure.unclassified} toClassification />
                  </div>
                )}
              </details>
            </li>
          );
        })()}
      </ol>
    </div>
  );
}

export function ProjectSections({ projectUid }: ProjectSectionsProps) {
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  // `R-151a`: archived documents are out of the lists unless the reader asks to see them.
  const [showArchived, setShowArchived] = useState(false);
  // `R-151e`: the tag filter, offered from the project's whole catalogue (never from one page of documents).
  const [tag, setTag] = useState<string | null>(null);
  const query = useDocumentList(projectUid, cursor, undefined, showArchived, tag ?? undefined, { order: 'audit' });
  const mayAct = useMayActAsExpert();
  // `UI-A-35`: the server's own count per section; used only while the listing is not narrowed by a tag or the archive.
  const exact = useSectionFigures(projectUid);
  const figures = tag === null && !showArchived ? exact.data : undefined;
  // `R-151c`: the chosen cards, and the batch the panel was opened with (fixed for its life).
  const batch = useBatchSelection(mayAct);

  let body;
  if (query.isPending) {
    body = <LoadingState what="документы этого проекта" />;
  } else if (query.isError) {
    const failure = classifyListingFailure(query.error, {
      collection: 'документы этого проекта',
      parent: 'project',
    });
    body = (
      <ErrorState
        title={failure.title}
        detail={<span data-list-failure={failure.kind}>{failure.detail}</span>}
        correlationId={failure.correlationId}
        {...(failure.retryable
          ? { onRetry: () => void query.refetch(), retryLabel: 'Повторить' }
          : {})}
      />
    );
  } else if (query.data.items.length === 0 && cursor === undefined) {
    body = (
      <EmptyState
        title="В этом проекте пока нет документов."
        detail="Загрузите комплект документации в панели «Загрузка». Ничего не потеряно: в проекте действительно нет опубликованных документов."
      />
    );
  } else {
    const nextCursor = query.data.page.next_cursor;
    body = (
      <>
        <ProjectStructureView
          projectUid={projectUid}
          items={query.data.items}
          hasNextPage={nextCursor !== null}
          selection={batch.selection}
          figures={figures}
        />
        <div className="am-pager">
          {cursor === undefined ? null : (
            <button
              type="button"
              className="am-button am-button--quiet am-button--small"
              onClick={() => setCursor(undefined)}
            >
              В начало
            </button>
          )}
          {nextCursor === null ? null : (
            <button
              type="button"
              className="am-button am-button--quiet am-button--small"
              onClick={() => setCursor(nextCursor)}
            >
              Дальше
            </button>
          )}
        </div>
      </>
    );
  }

  return (
    <section className="am-section" data-project-sections={projectUid}>
      <div className={styles.titleRow}>
        <h2>Разделы проекта</h2>
        <ArchivedToggle
          checked={showArchived}
          onChange={(checked) => {
            setShowArchived(checked);
            setCursor(undefined);
          }}
        />
        {/* `UI-A-51`: the original's «Обновить» beside the section list; it re-reads this page. */}
        <button
          type="button"
          className="am-button am-button--quiet am-button--small"
          data-project-sections-refresh
          disabled={query.isFetching}
          onClick={() => {
            void query.refetch();
          }}
        >
          {query.isFetching ? 'Обновляется…' : 'Обновить'}
        </button>
      </div>
      <TagFilter projectUid={projectUid} tag={tag} onTag={(next) => { setTag(next); setCursor(undefined); }} />
      {query.data === undefined ? null : <BatchBar projectUid={projectUid} selection={batch} documents={query.data.items} />}
      {body}
    </section>
  );
}
