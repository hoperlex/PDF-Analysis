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
                    <p>
                      x0 {block.bbox.x0} · y0 {block.bbox.y0} · x1 {block.bbox.x1} · y1{' '}
                      {block.bbox.y1} {block.bbox_unit} · начало координат {block.bbox_origin}
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
