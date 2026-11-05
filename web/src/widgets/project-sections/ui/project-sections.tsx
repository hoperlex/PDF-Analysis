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
import Link from 'next/link';

import type { DocumentVersion, ProjectUid, VersionUid } from '@/shared/api';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { classifyListingFailure, routes } from '@/shared/lib';
import { useMayActAsExpert } from '@/entities/account';
import { DocumentCardGrid, documentCardTitle, isComparisonOnly, useDocumentList } from '@/entities/document-version';
import type { BatchEntry } from '@/features/start-run';
import { BatchStartPanel } from '@/features/start-run';

import { projectStructure } from '../model/structure';
import styles from './project-sections.module.css';

export interface ProjectSectionsProps {
  readonly projectUid: ProjectUid;
}

/**
 * `R-151c`: the cards a reader may start together. Only a version confirmed for a section can be run, and a version
 * admitted for comparison only cannot; the box is not drawn for either.
 */
export interface CardSelection {
  readonly selected: ReadonlySet<string>;
  readonly onToggle: (version: DocumentVersion) => void;
}

export function startable(version: DocumentVersion): boolean {
  return version.classification !== undefined && !isComparisonOnly(version);
}

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
      addresses={(version) => ({
        href: toClassification
          ? routes.versionClassification(projectUid, version.version_uid)
          : routes.version(projectUid, version.version_uid),
        documentHref: routes.document(projectUid, version.document_uid),
      })}
      select={selection === undefined ? undefined : (version) => startable(version) ? (
        <input
          type="checkbox"
          aria-label={`Выбрать «${documentCardTitle(version)}» для запуска аудита`}
          checked={selection.selected.has(version.version_uid)}
          onChange={() => selection.onToggle(version)}
        />
      ) : null}
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
}

/** The grouped structure of one page of documents. Rendered by the static harness. */
export function ProjectStructureView({ projectUid, items, hasNextPage, selection }: ProjectStructureViewProps) {
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
                  {/* `R-151l`: the section's own page lists every document of the section, not one page of the project. */}
                  <p data-section-page-link={section.code}>
                    <Link href={routes.projectSection(projectUid, section.code)}>Открыть раздел</Link>
                  </p>
                  <DocumentRows projectUid={projectUid} documents={documents} selection={selection} />
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
  // `R-151a`: archived documents are out of the lists unless the reader asks to see them.
  const [showArchived, setShowArchived] = useState(false);
  const query = useDocumentList(projectUid, cursor, undefined, showArchived);
  const mayAct = useMayActAsExpert();
  // `R-151c`: the chosen cards, by version, and the batch the panel was opened with (fixed for its life).
  const [chosen, setChosen] = useState<ReadonlyMap<string, BatchEntry>>(new Map());
  const [batch, setBatch] = useState<readonly BatchEntry[] | null>(null);
  const selection: CardSelection | undefined = mayAct && batch === null ? {
    selected: new Set(chosen.keys()),
    onToggle: (version) => setChosen((map) => {
      const next = new Map(map);
      if (next.has(version.version_uid)) next.delete(version.version_uid);
      else next.set(version.version_uid, { versionUid: version.version_uid as VersionUid, title: documentCardTitle(version) });
      return next;
    }),
  } : undefined;

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
          selection={selection}
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
        <label className={styles.archivedToggle}>
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(event) => {
              setShowArchived(event.target.checked);
              setCursor(undefined);
            }}
          />{' '}
          Показать архивные
        </label>
        {/* `UI-A-51`: the original's «Обновить» beside the section list; it re-reads this page. */}
        <button
          type="button"
          className="am-button am-button--quiet"
          data-project-sections-refresh
          disabled={query.isFetching}
          onClick={() => {
            void query.refetch();
          }}
        >
          {query.isFetching ? 'Обновляется…' : 'Обновить'}
        </button>
      </div>
      {mayAct && chosen.size > 0 && batch === null ? (
        <p className="am-note" data-batch-selection={chosen.size}>
          <button type="button" className="am-button" onClick={() => setBatch([...chosen.values()])}>
            Запустить аудит ({chosen.size})
          </button>{' '}
          <button type="button" className="am-button am-button--quiet" onClick={() => setChosen(new Map())}>
            Снять выбор
          </button>
        </p>
      ) : null}
      {batch === null ? null : (
        <BatchStartPanel
          projectUid={projectUid}
          entries={batch}
          onClose={() => {
            setBatch(null);
            setChosen(new Map());
          }}
        />
      )}
      {body}
    </section>
  );
}
