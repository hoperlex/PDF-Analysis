'use client';

/**
 * «Блоки портала» — what a version's portal bundle brought, page by page
 * (`W55B-WEB-BLOCKS`, plan §B3.9).
 *
 * **Absent is not empty, and absent has two causes.** `listVersionPortalBlocks` answers
 * `not_produced` until a run's geometry stage has read the bundle, and an empty `produced`
 * page when it has and the block list is empty; the screen reads `status`, never the length
 * of `items` (the contract's own instruction). A `not_produced` version is then one of two
 * things, and they read differently: a bundle no run has reached yet (its blocks appear after
 * the first run) and a version published as a bare PDF before W55b, which has no portal
 * blocks however many runs it gets (`W55B-GEOMETRY-01` §5 item 4). The version's own
 * manifest says which (`versionHasPortalBundle`). Both are `NotApplicableState`; the
 * produced-but-empty answer is `EmptyState`.
 *
 * **Paged by the reader.** The first page loads with the tab; «Показать ещё» asks for the
 * next one with the last page's cursor (`entities/block`'s `usePortalBlocks`). The count the
 * API reports for the whole version (`block_count`) is printed beside the count loaded so
 * far, so a reader always knows whether the list is complete.
 *
 * {@link PortalBlockListView} is the loaded list without the query, exported so the
 * instruments that render one static pass (the language guard, the contrast census) render
 * the markup this widget renders rather than a copy of it.
 */

import Link from 'next/link';

import type { DocumentVersion, PortalBlock, ProjectUid, RunId, VersionUid } from '@/shared/api';
import { classifyListingFailure, routes } from '@/shared/lib';
import type { ListingFailure } from '@/shared/lib';
import { EmptyState, ErrorState, LoadingState, NotApplicableState } from '@/shared/ui';
import {
  DESCRIPTION_MARKER,
  RECOGNISED_MARKER,
  loadedPortalBlocks,
  sectionsByPage,
  usePortalBlocks,
  versionHasPortalBundle,
} from '@/entities/block';

import { PortalBlockCard } from './portal-block-card';
import styles from './portal-blocks.module.css';

export interface PortalBlockListViewProps {
  readonly projectUid: ProjectUid;
  /** The whole version's count, as the API reports it. */
  readonly blockCount: number;
  readonly producedByRunId: RunId | null;
  /** Every block loaded so far, in the order the pages were loaded. */
  readonly blocks: readonly PortalBlock[];
  /** The version the blocks belong to: each crop's address is the seam's to build from it. */
  readonly versionUid: VersionUid;
  /** Whether the API reported another page after the last one loaded. */
  readonly hasMore: boolean;
  readonly loadingMore: boolean;
  /** The failure of the last «Показать ещё», or `null`. */
  readonly moreFailure: ListingFailure | null;
  readonly onMore: () => void;
}

export function PortalBlockListView({
  projectUid,
  blockCount,
  producedByRunId,
  blocks,
  versionUid,
  hasMore,
  loadingMore,
  moreFailure,
  onMore,
}: PortalBlockListViewProps) {
  const sections = sectionsByPage(blocks);
  let position = 0;

  return (
    <div className={styles.portal} data-portal-blocks-loaded={blocks.length} data-portal-block-count={blockCount}>
      <p className="am-note">
        «{RECOGNISED_MARKER}» — текст, который портал распознал по изображению страницы; это не
        текстовый слой PDF. «{DESCRIPTION_MARKER}» — подпись портала к изображению; анализ её
        не читает. Изображения вырезаны этим приложением из PDF.
      </p>
      <p className={styles.summary}>
        Блоков в комплекте: {blockCount}. Показано: {blocks.length}.
        {producedByRunId === null ? null : (
          <>
            {' '}Разметку страниц получил прогон{' '}
            <Link href={routes.run(projectUid, producedByRunId)}>
              <code>{producedByRunId}</code>
            </Link>
            .
          </>
        )}
      </p>

      {sections.map((section) => (
        <section key={section.pageNumber} className={styles.page} data-portal-page={section.pageNumber}>
          <h3 className={styles.pageTitle}>
            Страница {section.pageNumber}
            {section.differingLabel === null ? null : <> (у портала — {section.differingLabel})</>}
          </h3>
          <ol className={styles.blocks}>
            {section.blocks.map((block) => {
              position += 1;
              // The portal's id is an external identifier: a key here and nothing else. The
              // position keeps two copies of one id (a server that repeated a block across a
              // cursor) from colliding, so the repetition is shown rather than swallowed.
              return (
                <li key={`${position}:${block.portal_block_id}`}>
                  <PortalBlockCard block={block} versionUid={versionUid} />
                </li>
              );
            })}
          </ol>
        </section>
      ))}

      {hasMore ? (
        <p className={styles.summary}>
          Загружены не все блоки: последняя показанная страница может продолжаться в следующей
          порции.
        </p>
      ) : null}
      {loadingMore ? <LoadingState what="следующие блоки портала" /> : null}
      {moreFailure === null ? null : (
        <ErrorState
          title={moreFailure.title}
          detail={moreFailure.detail}
          correlationId={moreFailure.correlationId}
          {...(moreFailure.retryable ? { onRetry: onMore } : {})}
        />
      )}
      <div className="am-pager">
        {hasMore && moreFailure === null ? (
          <button type="button" className="am-button am-button--quiet am-button--small" disabled={loadingMore} onClick={onMore}>
            Показать ещё
          </button>
        ) : null}
      </div>
    </div>
  );
}

export interface PortalBlocksProps {
  readonly version: Pick<DocumentVersion, 'version_uid' | 'project_uid' | 'input_manifest'>;
}

export function PortalBlocks({ version }: PortalBlocksProps) {
  const query = usePortalBlocks(version.version_uid);

  if (query.isPending) return <LoadingState what="блоки портала" />;
  if (query.data === undefined) {
    const failure = classifyListingFailure(query.error, { collection: 'блоки портала', parent: 'version' });
    return (
      <ErrorState
        title={failure.title}
        detail={failure.detail}
        correlationId={failure.correlationId}
        {...(failure.retryable ? { onRetry: () => void query.refetch() } : {})}
      />
    );
  }

  const first = query.data.pages[0];
  if (first === undefined || first.status === 'not_produced') {
    return versionHasPortalBundle(version) ? (
      <NotApplicableState
        title="Блоки портала появятся после первого запуска анализа этой версии."
        detail="Ни один прогон этой версии ещё не дошёл до разметки страниц. Это не то же самое, что «блоков нет»: после прогона здесь появятся блоки, распознанный текст и вырезанные изображения комплекта."
      />
    ) : (
      <NotApplicableState
        title="У этой версии нет комплекта портала."
        detail="Версия опубликована как отдельный PDF, без архива портала, поэтому блоков портала у неё нет и после прогона. Строки текстового слоя — на вкладке «Строки текста»."
      />
    );
  }

  const blocks = loadedPortalBlocks(query.data.pages);
  if (first.block_count === 0 && blocks.length === 0) {
    return (
      <EmptyState
        title="В комплекте портала нет ни одного блока."
        detail="Разметка страниц для этой версии получена, и блок-лист портала пуст."
      />
    );
  }

  return (
    <PortalBlockListView
      projectUid={version.project_uid}
      blockCount={first.block_count}
      producedByRunId={first.produced_by_run_id}
      blocks={blocks}
      versionUid={version.version_uid}
      hasMore={query.hasNextPage}
      loadingMore={query.isFetchingNextPage}
      moreFailure={
        query.isFetchNextPageError
          ? classifyListingFailure(query.error, { collection: 'следующие блоки портала', parent: 'version' })
          : null
      }
      onMore={() => void query.fetchNextPage()}
    />
  );
}
