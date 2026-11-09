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
 * **Tiles, a page selector and a block view** (`UI-PARITY`, the original's «Блоки»). The loaded blocks are
 * a grid of tiles, one grouped heading per page, narrowed by the chips above it to «Все блоки», one
 * page or «Без сущностей»; a press on a tile opens the block view (`portal-block-viewer.tsx`), which walks the
 * blocks of the selection. The tile's number is the run's findings whose evidence sits in the BLOCK when the server's
 * block links for the run were produced (`UI-PARITY-C6`), and otherwise the findings that cite its PAGE, and the
 * sentence under the summary says which (`model/page-findings.ts`). With no run in scope, or none that published
 * findings, there is no number. «Без сущностей» (`model/no-entities.ts`) is drawn only with the block links: the blocks
 * no finding sits in, in the original's two lists.
 *
 * {@link PortalBlockListView} is the loaded list without the query, exported so the
 * instruments that render one static pass (the language guard, the contrast census) render
 * the markup this widget renders rather than a copy of it.
 *
 * **The page chosen above the tiles can live in the address.** The widget keeps the choice in its own
 * state; a page that wants it kept (the version's tab: `?page=N` or `?page=all`) hands the starting choice
 * in (`initialPage`) and hears every change (`onPageChange`), and owns the address itself.
 */

import { useState } from 'react';
import Link from 'next/link';

import type { DocumentVersion, PortalBlock, ProjectUid, RunId, VersionUid } from '@/shared/api';
import { classifyListingFailure, routes } from '@/shared/lib';
import type { ListingFailure } from '@/shared/lib';
import { EmptyState, ErrorState, LoadingState, NotApplicableState } from '@/shared/ui';
import {
  DESCRIPTION_MARKER,
  RECOGNISED_MARKER,
  blocksOfSelection,
  effectiveSelection,
  loadedPortalBlocks,
  pageChips,
  sectionsByPage,
  sectionsOfSelection,
  usePortalBlocks,
  versionHasPortalBundle,
} from '@/entities/block';
import type { PageSelection } from '@/entities/block';

import { blocksWithoutFindings, noEntityWalk } from '../model/no-entities';
import { NO_PAGE_FINDINGS, blockReading, runSourcePhrase } from '../model/page-findings';
import type { PageFindingsReading } from '../model/page-findings';
import { usePageFindings } from '../model/use-page-findings';
import { PageSelector } from './page-selector';
import { PortalBlockTile } from './portal-block-tile';
import { PortalBlockViewer } from './portal-block-viewer';
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
  /** What the run's findings say about each page; absent, the tiles carry no number. */
  readonly pageFindings?: PageFindingsReading | undefined;
  /** The page selector's starting choice (a render that cannot press a chip says it here). */
  readonly initialPage?: PageSelection | undefined;
  /** Told each time the reader chooses «Все блоки» or a page, so a page can keep the choice in the address. */
  readonly onPageChange?: ((selection: PageSelection) => void) | undefined;
  /** The block view's starting place in the selection; absent, the view is closed. */
  readonly initialOpen?: number | undefined;
  /** The census and the unit suite: the block view is drawn open without `showModal`. */
  readonly staticOpen?: boolean | undefined;
}

/**
 * The list of blocks no finding was linked to (judge J3 F7). The relation is geometric and has known misses (`D-353`: a
 * quotation in the gap between blocks, in a line the portal did not box, a merged observation's evidence), so the list says
 * what is known -- nothing was linked -- and not that the block has no findings.
 */
const NOT_LINKED_TITLE =
  'Привязка замечаний к блокам считается по положению цитаты на странице; цитата в зазоре между блоками или в строке, которую портал не выделил, ни к какому блоку не привязана.';
const NOT_LINKED_HINT =
  'Ни одно замечание прогона не привязано к этим блокам по положению цитаты на странице. Это не значит, что замечаний по ним нет: привязка приблизительная и может пропустить цитату.';

/** The sentence under the summary that says what the numbers on the tiles are, or why there are none. */
function FindingsNote({ reading }: { readonly reading: PageFindingsReading }) {
  if (reading.kind === 'none') return null;
  if (reading.kind === 'read') {
    const source = runSourcePhrase(reading.runAt);
    const runAt = reading.runAt === undefined ? {} : { 'data-page-findings-run-at': reading.runAt };
    if (reading.blocks !== undefined) {
      return (
        <p className="am-note" data-page-findings="read" data-findings-scope="block" {...runAt}>
          Число на плитке — это число замечаний прогона <code>{reading.runId}</code>
          {source === null ? null : <> ({source})</>}, цитата которых лежит в этом блоке: блок покрывает не менее
          половины места цитаты на странице. Цитата, которую ни один блок не покрывает, в число плиток не входит, а
          на страницах, где разметка портала не совпала со страницей PDF, чисел нет: там неизвестно, есть ли
          замечания у блока.
        </p>
      );
    }
    return (
      <p className="am-note" data-page-findings="read" {...runAt}>
        Число на плитке — это число замечаний прогона <code>{reading.runId}</code>
        {source === null ? null : <> ({source})</>}, у которых есть цитата с
        этой страницы PDF. Замечание указывает страницу, а не блок, поэтому у всех плиток одной страницы число
        одно; у страниц без таких замечаний числа нет. Привязки замечаний к блокам для этого прогона нет.
      </p>
    );
  }
  return (
    <p className="am-note" data-page-findings={reading.kind}>
      {reading.kind === 'no-result' ? 'Прогон ' : 'Замечания прогона '}
      <code>{reading.runId}</code>
      {reading.kind === 'no-result'
        ? ' не опубликовал замечаний, поэтому чисел замечаний на плитках нет.'
        : ' не удалось прочитать, поэтому чисел замечаний на плитках нет.'}
    </p>
  );
}

/** One tile of a grid; the block view opens on its place in the selection's walk. */
function Tile({
  block,
  at,
  versionUid,
  pageFindings,
  runAt,
  onOpen,
}: {
  readonly block: PortalBlock;
  readonly at: number;
  readonly versionUid: VersionUid;
  readonly pageFindings: PageFindingsReading;
  readonly runAt: string | undefined;
  readonly onOpen: (at: number) => void;
}) {
  return (
    <li>
      <PortalBlockTile
        block={block}
        versionUid={versionUid}
        pageFindings={blockReading(pageFindings, block)}
        runAt={runAt}
        onOpen={() => {
          onOpen(at);
        }}
      />
    </li>
  );
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
  pageFindings = NO_PAGE_FINDINGS,
  initialPage = 'all',
  onPageChange,
  initialOpen,
  staticOpen = false,
}: PortalBlockListViewProps) {
  const [choice, setChoice] = useState<PageSelection>(initialPage);
  const [openAt, setOpenAt] = useState<number | null>(initialOpen ?? null);
  const sections = sectionsByPage(blocks);
  // «Без сущностей» exists only with the server's block links; chosen without them it is «Все блоки».
  const noEntities = blocksWithoutFindings(blocks, pageFindings);
  const noEntityTotal = noEntities === null ? 0 : noEntities.withoutFindings.length + noEntities.withoutContent.length;
  const selection: PageSelection =
    choice === 'empty' ? (noEntityTotal > 0 ? 'empty' : 'all') : effectiveSelection(sections, choice);
  const shown = sectionsOfSelection(sections, selection);
  const walk = selection === 'empty' && noEntities !== null ? noEntityWalk(noEntities) : blocksOfSelection(sections, selection);
  let position = -1;
  const runId = pageFindings.kind === 'none' ? null : pageFindings.runId;
  const runAt = pageFindings.kind === 'read' ? pageFindings.runAt : undefined;
  const open = (at: number) => {
    setOpenAt(at);
  };

  return (
    <div className={styles.portal} data-portal-blocks-loaded={blocks.length} data-portal-block-count={blockCount}>
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

      {/* How to read the tiles is one click away: the page selector and the tiles come first, as the original's. */}
      <details className={styles.howTo} data-portal-how-to="">
        <summary>Как читать плитки</summary>
        <p className="am-note">
          «{RECOGNISED_MARKER}» — текст, который портал распознал по изображению страницы; это не
          текстовый слой PDF. «{DESCRIPTION_MARKER}» — подпись портала к изображению; анализ её
          не читает. Изображения вырезаны этим приложением из PDF.
        </p>
        <FindingsNote reading={pageFindings} />
      </details>

      <PageSelector
        chips={pageChips(sections)}
        total={blocks.length}
        partial={hasMore}
        selection={selection}
        noEntities={noEntityTotal}
        onSelect={(next) => {
          setChoice(next);
          setOpenAt(null);
          onPageChange?.(next);
        }}
      />

      {shown.map((section) => (
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
                <Tile key={`${position}:${block.portal_block_id}`} block={block} at={position} versionUid={versionUid} pageFindings={pageFindings} runAt={runAt} onOpen={open} />
              );
            })}
          </ol>
        </section>
      ))}

      {selection === 'empty' && noEntities !== null ? (
        <>
          {(
            [
              ['withoutFindings', 'Замечания к блоку не привязаны', NOT_LINKED_HINT, noEntities.withoutFindings, NOT_LINKED_TITLE],
              ['withoutContent', 'Без значимого содержимого', 'В этих блоках нечего читать: штампы и области, в которых портал ничего не распознал.', noEntities.withoutContent, undefined],
            ] as const
          ).map(([group, title, hint, list, explanation]) =>
            list.length === 0 ? null : (
              <section key={group} className={styles.page} data-portal-empty={group}>
                <h3 className={styles.pageTitle} title={explanation}>{`${title} (${list.length})`}</h3>
                <p className="am-note">{hint}</p>
                <ol className={styles.blocks}>
                  {list.map((block) => {
                    position += 1;
                    return (
                      <Tile key={`${position}:${block.portal_block_id}`} block={block} at={position} versionUid={versionUid} pageFindings={pageFindings} runAt={runAt} onOpen={open} />
                    );
                  })}
                </ol>
              </section>
            ),
          )}
        </>
      ) : null}

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
          pageFindings={blockReading(pageFindings, walk[openAt] as PortalBlock)}
          runId={runId}
          runAt={runAt}
          staticOpen={staticOpen}
        />
      )}

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
  /** The page chosen when the list opens, from the address; absent, «Все блоки». */
  readonly page?: PageSelection | undefined;
  /** Told each time the reader chooses «Все блоки» or a page, so the page layer can write the address. */
  readonly onPage?: ((selection: PageSelection) => void) | undefined;
}

export function PortalBlocks({ version, page, onPage }: PortalBlocksProps) {
  const query = usePortalBlocks(version.version_uid);
  // The findings that number the tiles are the version's latest run that published a result; only when
  // there is none is it the run that read the bundle (`scopeRunId`), and the tiles say which run it is.
  const geometryRunId = query.data?.pages[0]?.produced_by_run_id ?? null;
  const pageFindings = usePageFindings(version.version_uid, geometryRunId);

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
        title="Блоки портала появятся после первого запуска анализа этой версии, который дойдёт до разметки страниц."
        detail="Ни один прогон этой версии ещё не дошёл до разметки страниц. Если запуск отклонён — например, текст версии больше допустимого объёма, — блоков не будет. Это не то же самое, что «блоков нет»: после такого прогона здесь появятся блоки, распознанный текст и вырезанные изображения комплекта."
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
      pageFindings={pageFindings}
      {...(page === undefined ? {} : { initialPage: page })}
      {...(onPage === undefined ? {} : { onPageChange: onPage })}
    />
  );
}
