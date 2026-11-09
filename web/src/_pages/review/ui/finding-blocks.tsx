'use client';

/** @jsxRuntime automatic */

/**
 * «Блоки замечания» under the page on «Разбор», inline and in the full-screen view's side column (`UI-PARITY-C6`, the
 * original's thumbnails under an opened finding): the portal blocks that hold the finding's evidence, each opening the
 * «Блоки» block view over just those blocks.
 *
 * Where «Блоки страницы N» (`page-blocks.tsx`) says «this is the page the finding cites», this strip is the finding's own:
 * the server derives which blocks the evidence sits in (`listRunFindingBlocks`, `entities/block`) and a block is here
 * only when it covers at least half of the place of a quotation on its page. A picture block shows its crop, a text block
 * the beginning of the portal's recognised text marked as recognised. A finding with no linked block, a run whose links are
 * not produced and a read that failed draw nothing: the page strip is the way to the page's blocks. Blocks that are linked
 * but not yet loaded (the version's blocks arrive by cursor) are counted, with the press for the next portion.
 *
 * {@link FindingBlocksStrip} is the view without the queries, so the instruments that render one static pass draw the
 * markup the screen draws.
 */

import { useState } from 'react';

import type { PortalBlock, ProjectUid, RunId, VersionUid } from '@/shared/api';
import { blocksOfFinding, findingBlockIndex, useRunFindingBlocks, usePortalBlocks } from '@/entities/block';
import { PortalBlockViewer } from '@/widgets/portal-blocks';

import { readFindingBlocks } from '../model/finding-blocks';
import type { FindingBlocksReading } from '../model/finding-blocks';
import { BlockThumb } from './page-blocks';
import styles from './page-blocks.module.css';

/** What the strip draws: a reading that is not `none`. */
export type FindingBlocksShown = Exclude<FindingBlocksReading, { readonly kind: 'none' }>;

export interface FindingBlocksStripProps {
  readonly reading: FindingBlocksShown;
  readonly versionUid: VersionUid;
  /** A press on a thumbnail: its place among the finding's blocks. */
  readonly onOpen: (index: number) => void;
  /** The next portion of the version's blocks, asked for only by a press. */
  readonly onMore: () => void;
  readonly loadingMore: boolean;
  readonly moreFailed: boolean;
}

export function FindingBlocksStrip({ reading, versionUid, onOpen, onMore, loadingMore, moreFailed }: FindingBlocksStripProps) {
  const { blocks, missing, complete } = reading;
  return (
    <section className={styles.strip} aria-label="Блоки замечания" data-finding-blocks={blocks.length}>
      <h3 className={styles.title}>{`Блоки замечания (${blocks.length + missing})`}</h3>
      {blocks.length === 0 ? null : (
        <>
          <ol className={styles.thumbs}>
            {blocks.map((block, at) => (
              <li key={`${at}:${block.portal_block_id}`} className={styles.item}>
                <BlockThumb
                  block={block}
                  versionUid={versionUid}
                  excerpt
                  onOpen={() => {
                    onOpen(at);
                  }}
                />
              </li>
            ))}
          </ol>
          <p className={styles.note}>Блоки, в которых лежит цитата замечания: каждый покрывает не менее половины её места на странице.</p>
        </>
      )}
      {missing === 0 ? null : (
        <div className={styles.more} data-finding-blocks-more={complete ? 'absent' : moreFailed ? 'failed' : loadingMore ? 'loading' : 'idle'}>
          <p className={styles.note}>
            {complete
              ? `Ещё ${missing} из блоков замечания в списке блоков версии не найдено.`
              : `Ещё ${missing} из блоков замечания лежат на страницах, которые не загружены: блоки версии приходят порциями.`}
            {moreFailed ? ' Следующую порцию не удалось загрузить.' : null}
          </p>
          {complete ? null : (
            <button type="button" className="am-button am-button--quiet am-button--small" disabled={loadingMore} onClick={onMore}>
              {loadingMore ? 'Загружаю…' : 'Загрузить следующие блоки'}
            </button>
          )}
        </div>
      )}
    </section>
  );
}

export interface ReviewFindingBlocksProps {
  readonly projectUid: ProjectUid;
  readonly versionUid: VersionUid;
  readonly runId: RunId;
  readonly findingUid: string;
  /** The block view's starting place among the finding's blocks; absent, the view is closed. */
  readonly initialOpen?: number | undefined;
  /** The census and the unit suite: the block view is drawn open without `showModal`. */
  readonly staticOpen?: boolean | undefined;
}

/**
 * The strip of the open finding, connected. Mounted with a key of the finding, so a block view left open does not
 * outlive it.
 */
export function ReviewFindingBlocks({ projectUid, versionUid, runId, findingUid, initialOpen, staticOpen = false }: ReviewFindingBlocksProps) {
  const links = useRunFindingBlocks(runId);
  const query = usePortalBlocks(versionUid);
  const [openAt, setOpenAt] = useState<number | null>(initialOpen ?? null);

  // Nothing is drawn while either read is in flight or after either failed: a strip that may turn out to be absent is
  // not announced, and the page strip says what could not be read.
  if (links.data === undefined || query.isPending) return null;
  const linked = blocksOfFinding(findingBlockIndex(links.data), findingUid);
  const reading = readFindingBlocks({ pages: query.data?.pages, hasMore: query.hasNextPage }, linked);
  if (reading.kind === 'none') return null;

  const walk: readonly PortalBlock[] = reading.blocks;
  return (
    <>
      <FindingBlocksStrip
        reading={reading}
        versionUid={versionUid}
        onOpen={setOpenAt}
        onMore={() => void query.fetchNextPage()}
        loadingMore={query.isFetchingNextPage}
        moreFailed={query.isFetchNextPageError}
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
          // The findings of this screen are what the reader is already looking at.
          pageFindings={null}
          runId={null}
          staticOpen={staticOpen}
        />
      )}
    </>
  );
}
