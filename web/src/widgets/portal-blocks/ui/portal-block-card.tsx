'use client';

/**
 * One portal block, as the «Блоки портала» tab shows it (`W55B-WEB-BLOCKS`, plan §B3.9).
 *
 * **Only what the response carries.** Every value printed here is a member of the
 * `PortalBlock` the API answered: its type, the portal's status, its ordinal, its page's
 * geometry verdict, the number of polygon vertices, the crop's pixel size, the recognised text
 * with its flags, the portal's description. Nothing is computed beyond counting a list the
 * response holds, and no polygon is drawn (`R-23`'s vector graph has no source in this
 * pipeline, and a shape drawn from the portal's vertices would be a picture nobody checked).
 *
 * **Text is text.** The recognised text and the portal's description are the portal model's
 * output and may carry anything — markup, a script tag, a markdown link. Both are rendered as
 * React children of an element styled `white-space: pre-wrap`, so React escapes every
 * character and nothing in them becomes an element, an attribute or a link. There is no
 * `dangerouslySetInnerHTML` and no markdown renderer here, and `tests/unit/blocks` asserts the
 * escaping on the rendered markup.
 *
 * **Marked, always.** A recognised text carries «распознано» (`R-116`: the portal's OCR is
 * never presented as the PDF's text layer); a description carries «описание портала — в
 * анализе не используется» (`R-117`, the plan's own words). The marker is part of the block
 * that holds the text, so no path renders one without the other.
 */

import { useState } from 'react';

import type { PortalBlock, PortalRecognisedText } from '@/shared/api';
import {
  DESCRIPTION_MARKER,
  RECOGNISED_MARKER,
  flagPresentation,
  geometryLabel,
  portalBlockTypeLabel,
  portalStatusPresentation,
} from '@/entities/block';

import styles from './portal-blocks.module.css';

/** The crop's `<img>`, or the sentence that stands where it failed to load. Pure. */
export interface CropFigureViewProps {
  readonly src: string;
  readonly widthPx: number;
  readonly heightPx: number;
  readonly alt: string;
  readonly failed: boolean;
  readonly onError: () => void;
}

export function CropFigureView({ src, widthPx, heightPx, alt, failed, onError }: CropFigureViewProps) {
  return (
    <figure className={styles.figure} data-portal-crop={failed ? 'failed' : 'shown'}>
      {failed ? (
        <p className={styles.absent} role="status">
          Изображение не удалось загрузить.
        </p>
      ) : (
        <img
          className={styles.crop}
          src={src}
          width={widthPx}
          height={heightPx}
          loading="lazy"
          decoding="async"
          alt={alt}
          onError={onError}
        />
      )}
      <figcaption className={styles.caption}>
        Фрагмент вырезан приложением из PDF. Размер, пикс.: {widthPx} × {heightPx}.{' '}
        {failed ? null : (
          <a href={src} target="_blank" rel="noopener noreferrer">
            Открыть фрагмент целиком
          </a>
        )}
      </figcaption>
    </figure>
  );
}

function CropFigure(props: Omit<CropFigureViewProps, 'failed' | 'onError'>) {
  // Per block and per mount: a failed crop says so instead of a broken-image icon. Nothing
  // retries it behind the reader's back; reopening the tab asks again.
  const [failed, setFailed] = useState(false);
  return <CropFigureView {...props} failed={failed} onError={() => setFailed(true)} />;
}

function RecognisedText({ recognised }: { readonly recognised: PortalRecognisedText }) {
  return (
    <div className={styles.recognised} data-quote-source={recognised.quote_source}>
      <p className={styles.marker}>{RECOGNISED_MARKER}</p>
      <pre className={styles.text}>{recognised.text}</pre>
      {recognised.flags.length === 0 ? null : (
        <ul className={styles.flags} aria-label="Признаки возможных ошибок распознавания">
          {recognised.flags.map((flag, index) => {
            const presentation = flagPresentation(flag);
            return (
              <li key={`${index}:${flag}`} className={styles.flag} data-recognised-flag={flag}>
                <span className="am-badge am-badge--degraded">{presentation.label}</span>
                <span>{presentation.explanation}</span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function PortalDescription({ text }: { readonly text: string }) {
  return (
    <div className={styles.description} data-portal-description>
      <p className={styles.descriptionMarker}>{DESCRIPTION_MARKER}</p>
      <p className={styles.text}>{text}</p>
    </div>
  );
}

export interface PortalBlockCardProps {
  readonly block: PortalBlock;
  /** The crop's address, asked only for a block that has a crop. */
  readonly cropSrc: (block: PortalBlock) => string;
}

export function PortalBlockCard({ block, cropSrc }: PortalBlockCardProps) {
  const status = portalStatusPresentation(block.status);
  const mismatch = geometryLabel(block.geometry);
  const vertices = block.polygon_points?.length ?? 0;
  const typeLabel = portalBlockTypeLabel(block.block_type);

  return (
    <article
      className={styles.block}
      data-portal-block-type={block.block_type}
      data-portal-geometry={block.geometry}
      data-portal-status={block.status}
    >
      <header className={styles.head}>
        <h4 className={styles.type}>{typeLabel}</h4>
        {block.ordinal === null ? null : (
          <span className={styles.meta}>порядок на странице: {block.ordinal}</span>
        )}
        <span className={`am-badge am-badge--${status.tone}`}>{status.label}</span>
        {vertices === 0 ? null : <span className={styles.meta}>вершин в контуре: {vertices}</span>}
      </header>
      {mismatch === null ? null : (
        <p className={styles.mismatch} data-geometry-mismatch>
          {mismatch}
        </p>
      )}

      {block.recognised_text === undefined ? (
        block.block_type === 'text' ? (
          <p className={styles.absent} data-recognised-absent>
            Текст не распознан.
          </p>
        ) : null
      ) : (
        <RecognisedText recognised={block.recognised_text} />
      )}

      {block.crop === undefined ? (
        block.block_type === 'image' ? (
          <p className={styles.absent} data-portal-crop="absent">
            {mismatch === null
              ? 'Фрагмент для этого блока не вырезан.'
              : 'Фрагмент не вырезан: страница портала не совпала со страницей PDF.'}
          </p>
        ) : null
      ) : (
        <CropFigure
          src={cropSrc(block)}
          widthPx={block.crop.width_px}
          heightPx={block.crop.height_px}
          alt={`${typeLabel}: фрагмент страницы ${block.page_number} PDF`}
        />
      )}

      {block.portal_description === undefined ? null : <PortalDescription text={block.portal_description} />}
    </article>
  );
}
