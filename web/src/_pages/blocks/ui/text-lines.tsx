'use client';

/**
 * «Строки текста» — the text-line block index of one version (`getVersionBlocks`,
 * `W45-BLOCKS`), the second tab of «Блоки» since `W55B-WEB-BLOCKS`.
 *
 * Moved here from `blocks-page.tsx` unchanged: the same states, the same wording, the same
 * page grouping. `R-39`'s plain statement about the vector graph moved with it, because it
 * is a statement about THIS view's geometry (the application's own rectangular bounds); the
 * portal's polygons are the other tab's, and that tab draws none either.
 *
 * **No invented numbers.** Every count on this view -- a page number, a block's character
 * span, a coordinate -- is carried on the response exactly as `getVersionBlocks` answered
 * it; nothing here is computed, rounded further or guessed at while data is loading.
 */

import type { BlockGeometry, VersionUid } from '@/shared/api';
import { EmptyState, ErrorState, LoadingState, NotApplicableState } from '@/shared/ui';

import { useVersionBlocks } from '../api/use-version-blocks';

/*
 * `R-18`, applied when `W55B-WEB-BLOCKS` first rendered this view in the language guard:
 * the coordinates printed the contract's own words — `x0`/`y0`/`x1`/`y1`, `pt`, `top_left` —
 * as visible text since `W45-BLOCKS`, and no instrument had reached a loaded index to see
 * them. The values are unchanged and the machine words keep their home in `data-` attributes;
 * the two single-member vocabularies are `Record`s, so a reseal that adds a unit or an origin
 * stops this file type-checking until it is worded.
 */
const BBOX_UNIT_LABELS: Readonly<Record<BlockGeometry['bbox_unit'], string>> = {
  pt: 'в пунктах',
};

const BBOX_ORIGIN_LABELS: Readonly<Record<BlockGeometry['bbox_origin'], string>> = {
  top_left: 'от левого верхнего угла страницы',
};

export function TextLines({ versionUid }: { readonly versionUid: VersionUid }) {
  return (
    <>
      <p>
        Векторный граф блока здесь пока не строится: приложение вычисляет прямоугольные
        границы блока на странице, но не его контур. Ниже показано то, что есть.
      </p>
      <BlockMarkup versionUid={versionUid} />
    </>
  );
}

interface BlockMarkupProps {
  readonly versionUid: VersionUid;
}

function BlockMarkup({ versionUid }: BlockMarkupProps) {
  const blocks = useVersionBlocks(versionUid);

  if (blocks.isPending) return <LoadingState what="разметку блоков" />;
  if (blocks.isError) {
    return (
      <ErrorState
        title="Разметку блоков не удалось прочитать."
        onRetry={() => void blocks.refetch()}
      />
    );
  }

  const index = blocks.data;

  if (index.status === 'not_produced') {
    return (
      <NotApplicableState
        title="Разметка блоков для этой версии ещё не построена."
        detail="Ни один прогон этой версии ещё не дошёл до вычисления геометрии страниц. Это не то же самое, что «блоков нет» — как только прогон её вычислит, здесь появится разметка."
      />
    );
  }

  if (index.blocks.length === 0) {
    return (
      <EmptyState
        title="Блоков не обнаружено."
        detail="Геометрия для этой версии вычислена, и в документе не нашлось ни одного блока."
      />
    );
  }

  const byPage = new Map<number, BlockGeometry[]>();
  for (const block of index.blocks) {
    const page = byPage.get(block.page_number) ?? [];
    page.push(block);
    byPage.set(block.page_number, page);
  }
  const pageNumbers = [...byPage.keys()].sort((a, b) => a - b);

  return (
    <div>
      {pageNumbers.map((pageNumber) => {
        const pageBlocks = (byPage.get(pageNumber) ?? []).slice().sort(
          (a, b) => a.block_ordinal - b.block_ordinal,
        );
        return (
          <section key={pageNumber} style={{ marginBottom: '1rem' }}>
            <h3>
              Страница {pageNumber} · блоков {pageBlocks.length}
            </h3>
            <ul>
              {pageBlocks.map((block) => (
                <li key={block.block_id} className="am-state" style={{ marginBottom: '0.25rem' }}>
                  <div className="am-state__detail">
                    <p>
                      <code>{block.block_id}</code>
                    </p>
                    <p data-bbox-unit={block.bbox_unit} data-bbox-origin={block.bbox_origin}>
                      левый край {block.bbox.x0} · верхний край {block.bbox.y0} · правый край{' '}
                      {block.bbox.x1} · нижний край {block.bbox.y1}, {BBOX_UNIT_LABELS[block.bbox_unit]}{' '}
                      {BBOX_ORIGIN_LABELS[block.bbox_origin]}
                    </p>
                    <p>
                      символы {block.char_start}–{block.char_end}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
