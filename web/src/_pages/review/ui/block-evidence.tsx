'use client';

/** @jsxRuntime automatic */

/**
 * The card of a block finding on «Разбор»: the page of the document with a frame at each block, and a card for each block beside it
 * (`F8-WEB`, `D-683`, contract 1.52.0).
 *
 * A finding that comes from a drawing or a cross-check stands on blocks of the portal, not on text spans, so it has no quotation for
 * the quotation viewer (`widgets/evidence-viewer`), which refuses an observation with no evidence. This is the same page viewer
 * (`PageViewer`, pdf.js) with the same pages bar and the same cards column, drawn from `Finding.block_evidence`: each block is a target
 * with a normalised region, and the viewer frames it as it frames any region the source carries (`model/block-targets.ts`).
 *
 * What the card says is exactly what is known. The frame shows WHERE the block is: «привязка к блоку доказывает место, а не содержание»
 * (plan v5 section 4.3). A block's recognised text, when the server proved one, is shown as what it is, marked «распознано»; a block with
 * no such text says nothing more than its place. Navigation is restricted to the pages the finding's blocks are on.
 *
 * {@link BlockEvidenceView} is the markup without the viewer's own hooks (the page viewer comes in as a node), so the unit suite and the
 * preview draw what the screen draws; {@link BlockEvidence} is the connected one.
 */

import { useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import type { FindingBlockEvidence, ProviderMode } from '@/shared/api';
import type { ErrorStateProps } from '@/shared/ui';
import { ErrorState, LoadingState } from '@/shared/ui';
import { PageViewer, pdfPageUrl } from '@/features/open-evidence';
import { RECOGNISED_MARKER } from '@/entities/block';

import { BLOCK_FRAME_SENTENCES, blockCardsOnPage, blockPages } from '../model/block-targets';
import type { BlockCard } from '../model/block-targets';
import styles from './block-evidence.module.css';

export interface BlockEvidenceViewProps {
  readonly cards: readonly BlockCard[];
  readonly pages: readonly number[];
  readonly page: number;
  readonly onPageChange: (page: number) => void;
  readonly activeId: string | null;
  readonly onChoose: (id: string) => void;
  /** The page, drawn: the page viewer, or what stands for it. */
  readonly viewer: ReactNode;
  readonly providerMode?: ProviderMode | undefined;
  /**
   * The run's `unlinked_pages` (`UI-PARITY-C6`): pages where the portal's raster does not describe the PDF page. A block's box is normalised
   * to the portal's page, so on such a page the frame may lie elsewhere than the block, and the card says so instead of claiming the place.
   */
  readonly unlinkedPages?: ReadonlySet<number> | undefined;
  /** `blob:` URL of the document, for «Открыть PDF»; absent, the link is not offered. */
  readonly documentUrl?: string | null | undefined;
  readonly presentation?: 'inline' | 'full' | undefined;
  /** Inline only: opens the full-screen view. */
  readonly onExpand?: (() => void) | undefined;
  /** Full only: the finding and its ✓/✕, above the cards. */
  readonly aside?: ReactNode;
}

export function BlockEvidenceView({
  cards,
  pages,
  page,
  onPageChange,
  activeId,
  onChoose,
  viewer,
  providerMode,
  unlinkedPages,
  documentUrl,
  presentation = 'inline',
  onExpand,
  aside,
}: BlockEvidenceViewProps) {
  const full = presentation === 'full';
  const unlinked = unlinkedPages?.has(page) === true;
  return (
    <div
      className={full ? `am-evidence ${styles.full}` : 'am-evidence'}
      data-block-evidence=""
      data-active-page={page}
      data-presentation={presentation}
    >
      <nav className="am-evidence__pages" aria-label="Страницы с блоками замечания">
        {pages.map((candidate) => (
          <button
            key={candidate}
            type="button"
            className="am-button"
            data-page={candidate}
            data-active={candidate === page ? 'true' : 'false'}
            aria-current={candidate === page ? 'page' : undefined}
            onClick={() => {
              onPageChange(candidate);
            }}
          >
            стр. {candidate}
          </button>
        ))}
        {providerMode === undefined ? null : (
          <span className="am-evidence__provider" data-provider-mode={providerMode}>
            {providerMode === 'live' ? 'живой вызов' : 'из записи'}
          </span>
        )}
        {/* The whole document in the browser's own reader, opened on this page, as the quotation viewer's bar offers. */}
        {documentUrl === null || documentUrl === undefined ? null : (
          <a
            className="am-button am-button--quiet am-button--small"
            href={pdfPageUrl(documentUrl, page)}
            target="_blank"
            rel="noopener noreferrer"
            data-open-document={page}
          >
            Открыть PDF ↗
          </a>
        )}
        {!full && onExpand !== undefined ? (
          <button type="button" className="am-button am-button--quiet am-button--small" onClick={onExpand} data-expand-evidence="">
            Во весь экран
          </button>
        ) : null}
      </nav>

      <div className={full ? `am-evidence__panes ${styles.fullPanes}` : 'am-evidence__panes'}>
        <div className={full ? `am-evidence__page ${styles.fullPage}` : 'am-evidence__page'}>{viewer}</div>
        <div className={full ? `am-evidence__quotations ${styles.fullSide}` : 'am-evidence__quotations'}>
          {full ? aside : null}
          <h3>Блоки на странице {page}</h3>
          <ul className="am-quotation-list">
            {cards.map((card) => (
              <li
                key={card.id}
                className={`am-quotation ${styles.card}`}
                data-block-card={card.badge}
                data-block-frame={card.frame}
                data-active={activeId === card.id ? 'true' : 'false'}
                onClick={() => {
                  // A click that ends a text selection is the reader copying the text.
                  if (typeof window !== 'undefined' && window.getSelection()?.isCollapsed === false) return;
                  onChoose(card.id);
                }}
              >
                <div className={styles.cardBody}>
                  <button
                    type="button"
                    className="am-button am-button--small"
                    aria-pressed={activeId === card.id}
                    aria-label={`Показать блок ${card.badge} на странице`}
                    title="Показать на странице"
                    onClick={(event) => {
                      event.stopPropagation();
                      onChoose(card.id);
                    }}
                  >
                    {card.badge}
                  </button>
                  <div className={styles.cardContent}>
                    {card.recognisedQuote === undefined ? null : (
                      <blockquote className="am-quotation__text" data-block-recognised-quote={card.recognisedQuote}>
                        {RECOGNISED_MARKER}: {card.recognisedQuote}
                      </blockquote>
                    )}
                    <p className="am-quotation__anchor" data-block-frame-note={card.frame}>
                      Блок {card.badge} · стр. {card.page}. {BLOCK_FRAME_SENTENCES[card.frame]}
                    </p>
                  </div>
                </div>
              </li>
            ))}
          </ul>
          {unlinked ? (
            <p className="am-quotation__inconsistent" role="status" data-block-page-unlinked={page}>
              Для страницы {page} привязка блоков портала к странице PDF не определена: рамка может лежать не там, где блок.
            </p>
          ) : null}
          <p className="am-evidence__limits">
            Рамка помогает найти место: она показывает блок портала, а не его содержание. Сверяйте по самому чертежу.
          </p>
        </div>
      </div>
    </div>
  );
}

export interface BlockEvidenceProps {
  readonly blocks: readonly FindingBlockEvidence[];
  readonly activePage: number;
  readonly onPageChange: (page: number) => void;
  /** `blob:` URL of the fetched version content, or null while it is unavailable. */
  readonly documentUrl: string | null;
  readonly isLoading?: boolean | undefined;
  readonly error?: ErrorStateProps | null | undefined;
  readonly providerMode?: ProviderMode | undefined;
  /** The run's `unlinked_pages`; absent, no page is called unlinked. */
  readonly unlinkedPages?: ReadonlySet<number> | undefined;
  readonly presentation?: 'inline' | 'full' | undefined;
  readonly onExpand?: (() => void) | undefined;
  readonly aside?: ReactNode;
  /** The finding the blocks belong to: a different finding forgets the card the reader chose. */
  readonly scope: string;
}

interface Scoped<T> {
  readonly scope: string;
  readonly value: T;
}

export function BlockEvidence({
  blocks,
  activePage,
  onPageChange,
  documentUrl,
  isLoading,
  error,
  providerMode,
  unlinkedPages,
  presentation = 'inline',
  onExpand,
  aside,
  scope,
}: BlockEvidenceProps) {
  const pages = useMemo(() => blockPages(blocks), [blocks]);
  const page = pages.includes(activePage) ? activePage : (pages[0] ?? activePage);
  const cards = useMemo(() => blockCardsOnPage(blocks, page), [blocks, page]);

  // The card the reader chose belongs to one finding on one page; a different finding or page starts with the first frame.
  const pageScope = `${scope}:${page}`;
  const [chosen, setChosen] = useState<Scoped<string> | null>(null);
  const activeId = chosen !== null && chosen.scope === pageScope ? chosen.value : (cards.find((card) => card.frame === 'framed')?.id ?? null);

  const targets = useMemo(() => cards.map((card) => card.target), [cards]);
  const full = presentation === 'full';

  const viewer =
    isLoading === true ? (
      <LoadingState what="страницу документа" />
    ) : error !== undefined && error !== null ? (
      <ErrorState {...error} />
    ) : documentUrl === null ? (
      <ErrorState
        title="Страницу не удалось показать"
        detail={<p>Байты документа недоступны. Эта панель никогда не рисует пустую страницу так, будто в PDF ничего нет.</p>}
      />
    ) : (
      <PageViewer
        documentUrl={documentUrl}
        pageNumber={page}
        targets={targets}
        activeTargetId={activeId}
        onTargetSelect={(id) => {
          setChosen({ scope: pageScope, value: id });
        }}
        label={`Страница ${page} проверяемого документа`}
        fill={full}
      />
    );

  return (
    <BlockEvidenceView
      cards={cards}
      pages={pages}
      page={page}
      onPageChange={onPageChange}
      activeId={activeId}
      onChoose={(id) => {
        setChosen({ scope: pageScope, value: id });
      }}
      viewer={viewer}
      providerMode={providerMode}
      unlinkedPages={unlinkedPages}
      documentUrl={documentUrl}
      presentation={presentation}
      onExpand={onExpand}
      aside={aside}
    />
  );
}
