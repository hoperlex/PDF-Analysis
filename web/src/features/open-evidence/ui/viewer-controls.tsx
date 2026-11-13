/** @jsxRuntime automatic */

/**
 * The one control the viewer has: a small pill in the corner of the page.
 *
 * `−`, the zoom as a percentage of the whole-page fit (a click returns to the whole page), `+`,
 * and, only when something on the page is framed, «К фрагменту». Nothing else: the page is moved
 * by dragging it and zoomed by the wheel, a double click or the keys, and the hint under the
 * viewport says so. The pill sits at rest half-faded so it does not cover the page, and is fully
 * opaque under the pointer or while the keyboard focus is inside it (always, on a touch screen).
 * Focus is followed in state and not with `:focus-within`, which the contrast census cannot read.
 *
 * The glyphs are text, not icons from the shared set: it has no zoom or target glyph, and the
 * target mark is two borders in CSS, which needs no font that has a crosshair.
 */

'use client';

import { useState } from 'react';

import styles from './page-viewer.module.css';

export interface ViewerControlsProps {
  /** `Math.round(zoom * 100)`: a multiple of the whole-page fit. */
  readonly percent: number;
  /** True when a target is framed on this page. */
  readonly canFocus: boolean;
  readonly onZoomOut: () => void;
  readonly onZoomIn: () => void;
  readonly onFit: () => void;
  readonly onFocus: () => void;
}

export function ViewerControls({
  percent,
  canFocus,
  onZoomOut,
  onZoomIn,
  onFit,
  onFocus,
}: ViewerControlsProps) {
  const [engaged, setEngaged] = useState(false);
  return (
    <div
      className={styles.controls}
      role="group"
      aria-label="Масштаб страницы"
      data-engaged={engaged ? 'true' : 'false'}
      onFocus={() => {
        setEngaged(true);
      }}
      onBlur={(event) => {
        // Focus moving from one button of the pill to another is still inside it.
        if (!event.currentTarget.contains(event.relatedTarget)) setEngaged(false);
      }}
    >
      <button
        type="button"
        className={styles.control}
        aria-label="Уменьшить"
        title="Уменьшить (клавиша «−»)"
        onClick={onZoomOut}
      >
        −
      </button>
      <button
        type="button"
        className={`${styles.control} ${styles.percent}`}
        aria-label={`Масштаб ${percent} %. Показать страницу целиком`}
        title="Показать страницу целиком (клавиша «0»)"
        onClick={onFit}
      >
        {percent} %
      </button>
      <button
        type="button"
        className={styles.control}
        aria-label="Приблизить"
        title="Приблизить (клавиша «+»)"
        onClick={onZoomIn}
      >
        +
      </button>
      {canFocus ? (
        <button
          type="button"
          className={styles.control}
          aria-label="К фрагменту"
          title="К фрагменту"
          onClick={onFocus}
        >
          <span className={styles.crosshair} aria-hidden="true" />
        </button>
      ) : null}
    </div>
  );
}
