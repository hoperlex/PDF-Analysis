'use client';

/**
 * One portal block as a tile of the grid (`UI-PARITY`, «Блоки»): the crop at a fixed height with the
 * block's type and place beneath it, and a badge with the number of findings when the run's findings were read.
 * A press opens the block view.
 *
 * **What the tile shows is what the response carries.** An IMAGE block shows its crop (the address is
 * the seam's, built from the version and block identities); a TEXT block shows the beginning of the
 * recognised text, marked «распознано» like every recognised text (`R-116`) — the whole text, with its
 * flags, is in the block view; a STAMP shows that it has neither. A block the portal marked as failed or
 * unknown says so on the tile, because the tile is the only place a reader running down the grid sees it.
 *
 * **The badge says which number it is.** See `model/page-findings.ts`: with the server's block links (`UI-PARITY-C6`)
 * it is the findings whose evidence sits in this block and the `title` says «замечаний в блоке»; without them it is the
 * page's number and the `title` says «замечаний на странице». Either way the `title` says which run the count is from
 * («по прогону от <time>»). The outline is amber when there are any; none means no badge and no outline, and a tile
 * with no reading carries neither.
 */

import { useState } from 'react';

import type { PortalBlock, VersionUid } from '@/shared/api';
import { portalBlockCropUrl } from '@/shared/api';
import {
  RECOGNISED_MARKER,
  portalBlockTypeLabel,
  portalStatusPresentation,
  textExcerpt,
} from '@/entities/block';

import type { PageFindings } from '../model/page-findings';
import { runSourcePhrase } from '../model/page-findings';
import { severityTone } from '../model/severity-tone';
import styles from './portal-blocks.module.css';

export interface PortalBlockTileProps {
  readonly block: PortalBlock;
  readonly versionUid: VersionUid;
  /** The block's findings (`scope: 'block'`) or its page's in the run's findings, or `null` when no number may be shown. */
  readonly pageFindings: PageFindings | null;
  /** When the run the number is from started (`created_at`); the badge's title says «по прогону от <time>». */
  readonly runAt?: string | undefined;
  readonly onOpen: () => void;
}

function Media({ block, versionUid }: { readonly block: PortalBlock; readonly versionUid: VersionUid }) {
  // Per tile and per mount: a failed crop says so instead of a broken-image icon.
  const [failed, setFailed] = useState(false);

  if (block.crop !== undefined) {
    return failed ? (
      <span className={styles.tileNote} role="status" data-portal-crop="failed">
        Изображение не удалось загрузить.
      </span>
    ) : (
      <img
        className={styles.tileImage}
        src={portalBlockCropUrl(versionUid, block.portal_block_id)}
        width={block.crop.width_px}
        height={block.crop.height_px}
        loading="lazy"
        decoding="async"
        alt={`${portalBlockTypeLabel(block.block_type)}: фрагмент страницы ${block.page_number} PDF`}
        data-portal-crop="shown"
        onError={() => {
          setFailed(true);
        }}
      />
    );
  }
  if (block.block_type === 'image') {
    return (
      <span className={styles.tileNote} data-portal-crop="absent">
        {block.geometry === 'geometry_mismatch'
          ? 'Фрагмент не вырезан: страница портала не совпала со страницей PDF.'
          : 'Фрагмент для этого блока не вырезан.'}
      </span>
    );
  }
  if (block.block_type === 'text') {
    return block.recognised_text === undefined ? (
      <span className={styles.tileNote} data-recognised-absent>
        Текст не распознан.
      </span>
    ) : (
      <span className={styles.tileText} data-quote-source={block.recognised_text.quote_source}>
        <span className={styles.tileMarker}>{RECOGNISED_MARKER}</span>
        <span className={styles.tileExcerpt}>{textExcerpt(block.recognised_text.text)}</span>
      </span>
    );
  }
  return <span className={styles.tileNote}>У штампа нет ни изображения, ни текста.</span>;
}

export function PortalBlockTile({ block, versionUid, pageFindings, runAt, onOpen }: PortalBlockTileProps) {
  const status = portalStatusPresentation(block.status);
  const typeLabel = portalBlockTypeLabel(block.block_type);
  const flagged = pageFindings !== null && pageFindings.count > 0;
  const source = runSourcePhrase(runAt);
  const meta =
    block.ordinal === null ? `стр. ${block.page_number}` : `стр. ${block.page_number} · порядок ${block.ordinal}`;

  return (
    <button
      type="button"
      className={styles.tile}
      aria-haspopup="dialog"
      data-portal-block-type={block.block_type}
      data-portal-geometry={block.geometry}
      data-portal-status={block.status}
      data-has-findings={flagged ? 'true' : 'false'}
      onClick={onOpen}
    >
      <span className={styles.tileMedia}>
        <Media block={block} versionUid={versionUid} />
      </span>
      <span className={styles.tileCaption}>
        <span className={styles.tileType}>{typeLabel}</span>
        <span className={styles.tileMeta}>{meta}</span>
        {status.tone === 'ok' ? null : (
          <span className={`am-badge am-badge--${status.tone}`}>{status.label}</span>
        )}
      </span>
      {pageFindings === null || !flagged ? null : (
        <span
          className={`am-badge am-badge--${severityTone(pageFindings.worst)} ${styles.tileBadge}`}
          data-tile-badge={pageFindings.count}
          title={`${
            pageFindings.scope === 'block' ? 'Замечаний в блоке' : `Замечаний на странице ${block.page_number}`
          }: ${pageFindings.count}${source === null ? '' : ` (${source})`}`}
        >
          {pageFindings.count}
        </span>
      )}
    </button>
  );
}
