/** @jsxRuntime automatic */

/**
 * The viewer as markup: everything `PageViewer` draws, with no hook in it.
 *
 * The container holds the document, the page, the pan and zoom and the pointer, and hands this
 * the finished picture; so every state a reader can meet (loading, ready, the next page still
 * drawing, a failure, a target active or not, the pill) is a function of plain props. That is
 * what lets the styling census render the states that only exist after pdf.js has drawn a page
 * in a browser, and the unit suite assert them without one.
 *
 * Layout, outside in: a root holding the framed viewport and the one muted line under it; the
 * viewport, which clips, takes the pointer and the keyboard and is the thing that is focusable;
 * in it the sheet (the canvas, moved and scaled by a CSS transform), the marks above it, and the
 * overlay that stands for the page when there is none; and beside the viewport, not inside it,
 * the pill, so that a press on a button is never the start of a drag.
 */

import type { HTMLAttributes, ReactNode, Ref } from 'react';

import type { Placement } from '../model/targets';
import type { Stage, View } from '../model/view-state';
import { zoomPercent } from '../model/view-state';
import styles from './page-viewer.module.css';
import { ViewerControls } from './viewer-controls';
import { ViewerMarks } from './viewer-marks';

/**
 * `loading`     nothing drawn yet
 * `ready`       the page is drawn and answers the pointer
 * `rendering`   another page or target set is being read; the old page stays, dimmed
 * `failed`      the overlay explains what went wrong, and the page is not shown
 */
export type ViewerState = 'loading' | 'ready' | 'rendering' | 'failed';

export interface PageViewerViewProps {
  readonly label: string;
  /** The viewport fills its container's height and a plain wheel zooms (`PageViewer` `fill`). */
  readonly fill?: boolean | undefined;
  readonly state: ViewerState;
  readonly documentUrl: string;
  /** The page the reader asked for. */
  readonly pageNumber: number;
  /** The document's page count, once it is open. */
  readonly pageCount: number | null;
  readonly stage: Stage | null;
  readonly view: View | null;
  readonly placements: readonly Placement[];
  readonly activeTargetId: string | null;
  readonly pulse: number;
  readonly animate: boolean;
  readonly dragging: boolean;
  /** What stands for the page while there is none: the loading state or an error. */
  readonly overlay: ReactNode;
  readonly onTargetSelect?: ((id: string) => void) | undefined;
  readonly onZoomOut: () => void;
  readonly onZoomIn: () => void;
  readonly onFit: () => void;
  readonly onFocus: () => void;
  readonly viewportRef?: Ref<HTMLDivElement> | undefined;
  readonly canvasRef?: Ref<HTMLCanvasElement> | undefined;
  /** Pointer, keyboard and double-click handlers for the viewport. */
  readonly viewportHandlers?: HTMLAttributes<HTMLDivElement> | undefined;
}

const HINT = 'Перетаскивайте страницу, Ctrl + колесо — масштаб, двойной щелчок — приблизить.';
const FILL_HINT = 'Перетаскивайте страницу, колесо — масштаб, двойной щелчок — приблизить.';

export function PageViewerView({
  label,
  fill = false,
  state,
  documentUrl,
  pageNumber,
  pageCount,
  stage,
  view,
  placements,
  activeTargetId,
  pulse,
  animate,
  dragging,
  overlay,
  onTargetSelect,
  onZoomOut,
  onZoomIn,
  onFit,
  onFocus,
  viewportRef,
  canvasRef,
  viewportHandlers,
}: PageViewerViewProps) {
  const drawn = state === 'ready' || state === 'rendering';
  const located = placements.some((placed) => placed.groups.length > 0);
  return (
    <div
      className={styles.root}
      data-viewer-state={state}
      data-viewer-src={documentUrl}
      data-viewer-page={pageNumber}
      data-fill={fill ? 'true' : 'false'}
    >
      <div className={styles.stage}>
        <div
          {...viewportHandlers}
          ref={viewportRef}
          className={styles.viewport}
          tabIndex={0}
          role="group"
          aria-label={`${label}. Клавиши «+» и «−» меняют масштаб, «0» показывает страницу целиком, стрелки двигают страницу.`}
          aria-busy={state === 'loading' || state === 'rendering'}
          data-animate={animate ? 'true' : 'false'}
          data-dragging={dragging ? 'true' : 'false'}
        >
          <div
            className={styles.sheet}
            hidden={!drawn || stage === null || view === null}
            data-zoom={view === null ? undefined : view.zoom}
            style={
              stage === null || view === null
                ? undefined
                : {
                    width: stage.page.width * stage.fit,
                    height: stage.page.height * stage.fit,
                    transform: `translate(${view.x}px, ${view.y}px) scale(${view.zoom})`,
                  }
            }
          >
            <canvas ref={canvasRef} className={styles.canvas} role="img" aria-label={label} />
          </div>
          {drawn && stage !== null && view !== null ? (
            <ViewerMarks
              placements={placements}
              view={view}
              stage={stage}
              activeTargetId={activeTargetId}
              pulse={pulse}
              onSelect={onTargetSelect}
            />
          ) : null}
          {overlay === null ? null : <div className={styles.overlay}>{overlay}</div>}
        </div>
        {drawn && view !== null ? (
          <ViewerControls
            percent={zoomPercent(view)}
            canFocus={located}
            onZoomOut={onZoomOut}
            onZoomIn={onZoomIn}
            onFit={onFit}
            onFocus={onFocus}
          />
        ) : null}
      </div>
      {drawn ? (
        <p className={styles.hint}>
          <span>{fill ? FILL_HINT : HINT}</span>
          <span>{pageCount === null ? `Страница ${pageNumber}` : `Страница ${pageNumber} из ${pageCount}`}</span>
        </p>
      ) : null}
    </div>
  );
}
