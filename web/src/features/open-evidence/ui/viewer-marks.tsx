/** @jsxRuntime automatic */

/**
 * The highlights, frames and badges drawn over the page.
 *
 * Presentational and effect-free: it takes the placements (rectangles in page points), the view
 * the page is under, and draws each one in viewport pixels. That is deliberately NOT a child of
 * the transformed sheet: a frame inside a scaled box would grow a fatter border as the reader
 * zooms in and a badge would swell with it. Here every size that is a line or a letter stays what
 * it is, and only the positions follow the view. During an animated move the positions and sizes
 * are transitioned with the sheet's own curve; both are linear in the view, so they stay in step.
 *
 * Each framed spot is ONE button (the badge sits on its corner), so the keyboard reaches it once
 * and a screen reader hears «Фрагмент 2» once. The highlights under it are decoration: the
 * quotation beside the page is the evidence and is announced in full.
 */

import type { CSSProperties } from 'react';

import type { Rect } from '../model/locate-quotation';
import type { Placement } from '../model/targets';
import type { Stage, View } from '../model/view-state';
import { grow, toScreen } from '../model/view-state';
import styles from './page-viewer.module.css';

/** Room the frame leaves around the lines it encloses, in CSS pixels. */
export const FRAME_PADDING = 5;

export interface ViewerMarksProps {
  readonly placements: readonly Placement[];
  readonly view: View;
  readonly stage: Stage;
  readonly activeTargetId: string | null;
  /** Bumped whenever the viewer moves to a target, so the active frame pulses once more. */
  readonly pulse: number;
  readonly onSelect?: ((id: string) => void) | undefined;
}

function place(rect: Rect): CSSProperties {
  const round = (value: number) => Math.round(value * 10) / 10;
  return {
    transform: `translate(${round(rect.left)}px, ${round(rect.top)}px)`,
    width: round(rect.width),
    height: round(rect.height),
  };
}

export function ViewerMarks({
  placements,
  view,
  stage,
  activeTargetId,
  pulse,
  onSelect,
}: ViewerMarksProps) {
  return (
    <div className={styles.marks}>
      {placements.flatMap((placed) =>
        placed.groups.flatMap((group, at) =>
          group.highlights.map((rect, line) => (
            <div
              key={`${placed.target.id}:${at}:${line}`}
              className={styles.highlight}
              data-active={placed.target.id === activeTargetId ? 'true' : 'false'}
              style={place(toScreen(rect, view, stage))}
              aria-hidden="true"
            />
          )),
        ),
      )}
      {placements.flatMap((placed) =>
        placed.groups.map((group, at) => {
          const active = placed.target.id === activeTargetId;
          const several = placed.groups.length > 1;
          const quote = placed.target.quote;
          return (
            <button
              // The pulse is part of the key of the ACTIVE frame only: a new key is a new element,
              // and a new element plays its entrance once.
              key={`${placed.target.id}:${at}:${active ? pulse : 'quiet'}`}
              type="button"
              className={styles.frame}
              data-active={active ? 'true' : 'false'}
              data-target-id={placed.target.id}
              data-method={placed.resolution.method ?? undefined}
              style={place(grow(toScreen(group.hull, view, stage), FRAME_PADDING))}
              aria-label={
                several
                  ? `Фрагмент ${placed.target.badge}, совпадение ${at + 1} из ${placed.groups.length}`
                  : `Фрагмент ${placed.target.badge}`
              }
              aria-pressed={active}
              title={quote === undefined || quote === '' ? undefined : quote}
              onClick={
                onSelect === undefined
                  ? undefined
                  : () => {
                      onSelect(placed.target.id);
                    }
              }
            >
              <span className={styles.badge}>{placed.target.badge}</span>
            </button>
          );
        }),
      )}
    </div>
  );
}
