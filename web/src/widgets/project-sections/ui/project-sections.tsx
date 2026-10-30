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
 * Every row links to its version and to its document, exactly as the flat list did, so the
 * journey's walk from the project to a document is unchanged.
 */

import { useState } from 'react';

import type { DocumentVersion, ProjectUid } from '@/shared/api';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { classifyListingFailure, routes } from '@/shared/lib';
import { VersionRow, useDocumentList } from '@/entities/document-version';

import { projectStructure } from '../model/structure';
import styles from './project-sections.module.css';

export interface ProjectSectionsProps {
  readonly projectUid: ProjectUid;
}

function DocumentRows({
  projectUid,
  documents,
  toClassification = false,
}: {
  readonly projectUid: ProjectUid;
  readonly documents: readonly DocumentVersion[];
  /**
   * Open each version at its stage-and-section panel rather than at the top: the reader of
   * «Не классифицировано» came to confirm a section, and that is where it is done.
   */
  readonly toClassification?: boolean;
}) {
  return (
    <ul className="am-rows">
      {documents.map((version) => (
        <VersionRow
          key={version.document_uid}
          version={version}
          href={
            toClassification
              ? routes.versionClassification(projectUid, version.version_uid)
              : routes.version(projectUid, version.version_uid)
          }
          secondary={{
            href: routes.document(projectUid, version.document_uid),
            label: 'Все версии документа',
          }}
        />
      ))}
    </ul>
  );
}

export interface ProjectStructureViewProps {
  readonly projectUid: ProjectUid;
  readonly items: readonly DocumentVersion[];
  /** Whether the server has a further page of this project's documents. */
  readonly hasNextPage: boolean;
}

/** The grouped structure of one page of documents. Rendered by the static harness. */
export function ProjectStructureView({ projectUid, items, hasNextPage }: ProjectStructureViewProps) {
  const structure = projectStructure(items);
  return (
    <div data-project-structure="" data-document-count={items.length}>
      <p className={styles.rule} data-section-rule="confirmed">
        Документ стоит в разделе, который эксперт подтвердил для его текущей версии на экране
        версии. Пока раздел не подтверждён, документ находится в группе «Не классифицировано», и
        прогон по нему не запускается.
      </p>
      {hasNextPage ? (
        <p className="am-note" data-structure-page="partial">
          Показаны документы этой страницы списка; остальные документы проекта — на следующих
          страницах.
        </p>
      ) : null}
      <ol className={styles.sections}>
        {structure.sections.map(({ section, documents }) => (
          <li
            key={section.code}
            className={styles.section}
            data-section-group={section.code}
            data-section-documents={documents.length}
          >
            <details className={styles.card} open={documents.length > 0}>
              <summary className={styles.cardHeader}>
                <span className={styles.code}>{section.code}</span>
                <h3 className={styles.heading}>
                  <span className={styles.abbr}>{section.abbr}</span> {section.name}
                  {documents.length === 0 ? (
                    <span className={styles.count}> — документов нет</span>
                  ) : (
                    <span className={styles.count}> — документов: {documents.length}</span>
                  )}
                </h3>
                <span className={styles.chevron} aria-hidden="true">›</span>
              </summary>
              {documents.length === 0 ? null : (
                <div className={styles.cardBody}>
                  <DocumentRows projectUid={projectUid} documents={documents} />
                </div>
              )}
            </details>
          </li>
        ))}
        <li
          className={styles.section}
          data-section-group="unclassified"
          data-section-documents={structure.unclassified.length}
        >
          <details className={styles.card} open={structure.unclassified.length > 0}>
            <summary className={styles.cardHeader}>
              <span className={styles.code}>—</span>
              <h3 className={styles.heading}>
                Не классифицировано
                {structure.unclassified.length === 0 ? (
                  <span className={styles.count}> — документов нет</span>
                ) : (
                  <span className={styles.count}> — документов: {structure.unclassified.length}</span>
                )}
              </h3>
              <span className={styles.chevron} aria-hidden="true">›</span>
            </summary>
            {structure.unclassified.length === 0 ? null : (
              <div className={styles.cardBody}>
                <DocumentRows projectUid={projectUid} documents={structure.unclassified} toClassification />
              </div>
            )}
          </details>
        </li>
      </ol>
    </div>
  );
}

export function ProjectSections({ projectUid }: ProjectSectionsProps) {
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const query = useDocumentList(projectUid, cursor);

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
        detail="Загрузите комплект документации ниже. Ничего не потеряно: в проекте действительно нет опубликованных документов."
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
      <h2>Разделы проекта</h2>
      {body}
    </section>
  );
}
