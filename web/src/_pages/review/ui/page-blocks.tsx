'use client';

/** @jsxRuntime automatic */

/**
 * «Блоки страницы N» under the page on «Разбор», inline and in the full-screen view's side column
 * (`UI-A-74`): a strip of small thumbnails of the portal blocks of the page the viewer is on, each opening
 * the «Блоки» block view over the page's blocks.
 *
 * **A finding names pages, not blocks**, so the strip is headed by the page and says that it holds all of
 * the page's blocks. It reads the version's blocks through the hook the «Блоки» tab uses (one cursor read
 * for the whole version, cached); a finding adds no request. Where the cited page lies beyond the blocks
 * loaded so far, the strip says so and offers the tab's own «next portion» as a press, never on its own.
 *
 * A page with no blocks, and a version with no portal bundle, draw nothing. Blocks that cannot be read draw
 * one quiet sentence. {@link PageBlocksStrip} is the view without the query, so the instruments that render
 * one static pass draw the markup the screen draws.
 */

import Link from 'next/link';
import { useState } from 'react';

import type { PortalBlock, ProjectUid, VersionUid } from '@/shared/api';
import { portalBlockCropUrl } from '@/shared/api';
import { routes } from '@/shared/lib';
import { RECOGNISED_MARKER, portalBlockTypeLabel, textExcerpt, usePortalBlocks } from '@/entities/block';
import { PortalBlockViewer } from '@/widgets/portal-blocks';

import { readPageBlocks } from '../model/page-blocks';
import type { PageBlocksReading } from '../model/page-blocks';
import styles from './page-blocks.module.css';

/** What the strip draws: a reading that is not `none`. */
export type PageBlocksShown = Exclude<PageBlocksReading, { readonly kind: 'none' }>;

export interface PageBlocksStripProps {
  readonly reading: PageBlocksShown;
  readonly versionUid: VersionUid;
  /** A press on a thumbnail: its place among the page's blocks. */
  readonly onOpen: (index: number) => void;
  /** The next portion of the version's blocks, asked for only by a press. */
  readonly onMore: () => void;
  readonly loadingMore: boolean;
  readonly moreFailed: boolean;
  /**
   * The version's whole «Блоки» tab, where the original's thumbnails lead (`/project/<id>/blocks`). Absent, the strip
   * offers no way out, as the census and the unit suite draw it.
   */
  readonly blocksHref?: string | undefined;
}

/** A recognised text's beginning on a thumbnail that has no picture: a thumbnail is 112 px wide. */
const THUMB_EXCERPT_LIMIT = 60;

/**
 * One block as a thumbnail. `excerpt` (the finding's own blocks, `UI-PARITY-C6`) shows a TEXT block's recognised text
 * where it has no picture, marked as recognised; the page strip leaves it off and says «Без изображения».
 */
export function BlockThumb({
  block,
  versionUid,
  onOpen,
  excerpt = false,
}: {
  readonly block: PortalBlock;
  readonly versionUid: VersionUid;
  readonly onOpen: () => void;
  readonly excerpt?: boolean | undefined;
}) {
  // Per thumbnail and per mount: a crop that fails to load says so instead of a broken-image icon.
  const [failed, setFailed] = useState(false);
  const typeLabel = portalBlockTypeLabel(block.block_type);
  const picture = block.crop !== undefined && !failed;

  return (
    <button
      type="button"
      className={styles.thumb}
      aria-haspopup="dialog"
      title={`${typeLabel}: открыть блок`}
      data-page-block-type={block.block_type}
      data-page-block-picture={picture ? 'shown' : 'absent'}
      onClick={onOpen}
    >
      <span className={styles.thumbMedia}>
        {picture ? (
          <img
            className={styles.thumbImage}
            src={portalBlockCropUrl(versionUid, block.portal_block_id)}
            loading="lazy"
            decoding="async"
            alt={`${typeLabel}: фрагмент страницы ${block.page_number} PDF`}
            onError={() => {
              setFailed(true);
            }}
          />
        ) : (
          <span className={styles.thumbNote}>
            {failed
              ? 'Не загрузилось'
              : excerpt && block.recognised_text !== undefined
                ? `${RECOGNISED_MARKER}: ${textExcerpt(block.recognised_text.text, THUMB_EXCERPT_LIMIT)}`
                : 'Без изображения'}
          </span>
        )}
      </span>
      <span className={styles.thumbType}>{typeLabel}</span>
    </button>
  );
}

export function PageBlocksStrip({ reading, versionUid, onOpen, onMore, loadingMore, moreFailed, blocksHref }: PageBlocksStripProps) {
  if (reading.kind === 'unreadable') {
    return (
      <p className={`${styles.note} ${styles.alone}`} data-page-blocks="unreadable">
        Блоки страницы {reading.page} не удалось прочитать, поэтому полоска блоков не показана.
      </p>
    );
  }

  const blocks = reading.kind === 'blocks' ? reading.blocks : [];
  const complete = reading.kind === 'blocks' && reading.complete;

  return (
    <section
      className={styles.strip}
      aria-label={`Блоки страницы ${reading.page}`}
      data-page-blocks={reading.kind}
      data-page-blocks-page={reading.page}
    >
      <h3 className={styles.title}>
        {reading.kind === 'blocks' ? `Блоки страницы ${reading.page} (${blocks.length})` : `Блоки страницы ${reading.page}`}
        {blocksHref === undefined ? null : (
          <>
            {' '}
            <Link className={styles.all} href={blocksHref} data-page-blocks-all="">
              Все блоки версии →
            </Link>
          </>
        )}
      </h3>
      {blocks.length === 0 ? null : (
        <>
          <ol className={styles.thumbs}>
            {blocks.map((block, at) => (
              // The portal's id is an external identifier: a key here and nothing else. The position keeps a
              // block a server repeated across a cursor from colliding.
              <li key={`${at}:${block.portal_block_id}`} className={styles.item}>
                <BlockThumb
                  block={block}
                  versionUid={versionUid}
                  onOpen={() => {
                    onOpen(at);
                  }}
                />
              </li>
            ))}
          </ol>
          <p className={styles.note}>
            Замечание указывает страницу PDF, а не блок портала, поэтому здесь все блоки этой страницы.
          </p>
        </>
      )}
      {complete ? null : (
        <div className={styles.more} data-page-blocks-more={moreFailed ? 'failed' : loadingMore ? 'loading' : 'idle'}>
          <p className={styles.note}>
            {reading.kind === 'blocks'
              ? 'Загружены не все блоки комплекта: страница может продолжаться в следующей порции.'
              : 'Эта страница лежит за блоками, которые уже загружены: следующая порция ещё не прочитана.'}
            {moreFailed ? ' Следующую порцию не удалось загрузить.' : null}
          </p>
          <button type="button" className="am-button am-button--quiet am-button--small" disabled={loadingMore} onClick={onMore}>
            {loadingMore ? 'Загружаю…' : 'Загрузить следующие блоки'}
          </button>
        </div>
      )}
    </section>
  );
}

export interface ReviewPageBlocksProps {
  readonly projectUid: ProjectUid;
  readonly versionUid: VersionUid;
  /** The cited page the viewer is on. */
  readonly page: number;
  /** The block view's starting place among the page's blocks; absent, the view is closed. */
  readonly initialOpen?: number | undefined;
  /** The census and the unit suite: the block view is drawn open without `showModal`. */
  readonly staticOpen?: boolean | undefined;
}

/**
 * The strip of the open finding's page, connected. Mounted with a key of the finding and the page, so a
 * block view left open does not outlive either.
 */
export function ReviewPageBlocks({ projectUid, versionUid, page, initialOpen, staticOpen = false }: ReviewPageBlocksProps) {
  const query = usePortalBlocks(versionUid);
  const [openAt, setOpenAt] = useState<number | null>(initialOpen ?? null);

  // Nothing is drawn while the one read is in flight: a strip that may turn out to be absent is not announced.
  if (query.isPending) return null;
  const reading = readPageBlocks({ pages: query.data?.pages, hasMore: query.hasNextPage }, page);
  if (reading.kind === 'none') return null;

  const walk = reading.kind === 'blocks' ? reading.blocks : [];
  return (
    <>
      <PageBlocksStrip
        reading={reading}
        versionUid={versionUid}
        onOpen={setOpenAt}
        onMore={() => void query.fetchNextPage()}
        loadingMore={query.isFetchingNextPage}
        moreFailed={query.isFetchNextPageError}
        blocksHref={routes.versionBlocks(projectUid, versionUid)}
      />
      {openAt === null || walk[openAt] === undefined ? null : (
        <PortalBlockViewer
          projectUid={projectUid}
          versionUid={versionUid}
          blocks={walk}
          index={openAt}
          onIndex={setOpenAt}
          onClose={() => {
            setOpenAt(null);
          }}
          // The run's findings are what this screen is already showing; the view's own list of them would be
          // a second, linking back to the screen it is opened from.
          pageFindings={null}
          runId={null}
          staticOpen={staticOpen}
        />
      )}
    </>
  );
}
