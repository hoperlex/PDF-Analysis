/** @jsxRuntime automatic */

/**
 * One quotation, rendered as the server sent it, with the honest state of its frame.
 *
 * The quotation is the load-bearing half of the review screen. `PROTOTYPE_PROFILE.md` §8 asks
 * that a reviewer open the page from a finding and view its exact quotation, and the quotation is
 * rendered as the server sent it -- `{item.quote}` in JSX escapes markup and changes nothing
 * else. No trim, no collapse, no ellipsis, no smart quotes; `entities/finding-observation/model/
 * quotation` explains why at length. The frame on the page is a convenience for finding that
 * text; it never replaces it, and it never edits it.
 *
 * `placement` is what the viewer reported about this quotation, and the card says it in one line:
 *
 *   pending         the page is still being read; nothing is claimed yet
 *   lines           framed from the server's own line geometry
 *   text            framed where the quotation was found in the page text, and how many times
 *   not-found       the page was read and the text is not in it -- SAID, beside the quotation,
 *                   because a page shown without a frame and without a word about it reads as
 *                   «this quotation is not on the page»
 *   no-text-layer   the page has no text characters at all (a scan), so no search was possible
 *                   and the sentence says that instead
 *
 * The badge is a button: choosing a card moves the viewer to its frame, and a click anywhere on
 * the card does the same unless the reader was selecting text in it.
 */

import type { Evidence } from '@/shared/api';
import type { TargetResolution } from '@/features/open-evidence';
import { resolutionSentence } from '@/features/open-evidence';
import { anchorLabel, anchorMatchesQuotation, anchorRangeLabel } from '@/entities/finding-observation';

import styles from './evidence-viewer.module.css';

export type QuotationPlacement = TargetResolution | null;

export interface QuotationCardProps {
  readonly item: Evidence;
  /** The number on the badge, and on the frame on the page. */
  readonly badge: string;
  /** Null until the viewer has read the page. */
  readonly placement: QuotationPlacement;
  readonly active: boolean;
  readonly onSelect?: (() => void) | undefined;
  /** For the owner to scroll the card into view when its frame is chosen. */
  readonly itemRef?: ((element: HTMLLIElement | null) => void) | undefined;
}

function locatedAttribute(placement: QuotationPlacement): 'true' | 'false' | 'pending' {
  if (placement === null) return 'pending';
  return placement.status === 'found' ? 'true' : 'false';
}

export function QuotationCard({ item, badge, placement, active, onSelect, itemRef }: QuotationCardProps) {
  const consistent = anchorMatchesQuotation(item);
  const sentence = placement === null ? null : resolutionSentence(placement);
  const unplaced = placement !== null && placement.status !== 'found';
  return (
    <li
      ref={itemRef}
      className={`am-quotation ${styles.card}`}
      data-evidence-ordinal={item.evidence_ordinal}
      data-quote-located={locatedAttribute(placement)}
      data-active={active ? 'true' : 'false'}
      onClick={
        onSelect === undefined
          ? undefined
          : () => {
              // A click that ends a text selection is the reader copying the quotation.
              if (typeof window !== 'undefined' && window.getSelection()?.isCollapsed === false) return;
              onSelect();
            }
      }
    >
      <div className={styles.cardBody}>
        <button
          type="button"
          className={styles.cardBadge}
          aria-pressed={active}
          aria-label={`Показать фрагмент ${badge} на странице`}
          title="Показать на странице"
          onClick={(event) => {
            event.stopPropagation();
            onSelect?.();
          }}
        >
          {badge}
        </button>
        <div className={styles.cardContent}>
          {/*
            `data-evidence-quote` carries the same string as the visible text so a test can
            assert byte-identity against the API value without parsing rendered markup.
          */}
          <blockquote className="am-quotation__text" data-evidence-quote={item.quote}>
            {item.quote}
          </blockquote>
          {/*
            `block_id` is deliberately not rendered. The contract calls it "a secondary anchor
            into this version's block index. Not a contract identifier" — it is an internal
            index handle that tells the reviewer nothing the page number does not, and printing
            an internal handle is how an object key reaches a screen when something upstream
            puts one in the wrong field. The leakage check in
            tests/unit/review/key-leakage.test.ts caught exactly that and this is the repair.

            The character range is not rendered here either, by owner ruling `R-43` (`D-50`):
            it is a document-global offset in the coordinate system of one extractor, and no
            second extractor resolves it. It is used only to pick the lines to frame, and it
            appears as text only inside the alert below, where it is the evidence of a
            discrepancy.
          */}
          <p className="am-quotation__anchor">{anchorLabel(item)}</p>
          {sentence === null ? null : (
            <p
              className={unplaced ? styles.unplaced : styles.placed}
              role={unplaced ? 'status' : undefined}
              data-quote-method={placement?.method ?? undefined}
              data-quote-occurrences={placement?.status === 'found' ? placement.occurrences : undefined}
            >
              {sentence}
            </p>
          )}
          {consistent ? null : (
            <p className="am-quotation__inconsistent" role="alert">
              Заявленная длина фрагмента не совпадает с цитатой. Якорь показан так, как его
              прислал сервер, и здесь он не пересчитывается: {anchorRangeLabel(item)}.
            </p>
          )}
        </div>
      </div>
    </li>
  );
}
