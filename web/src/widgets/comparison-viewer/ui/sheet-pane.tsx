/**
 * One pane of the viewer: a window on the sheet with the tiles, the change boxes and, in the swipe, the divider
 * (`CMP-VIEWER-01`). A pane only draws; the island that owns it moves the sheet.
 */

import type { HTMLAttributes, ReactElement, Ref } from 'react';

import type { ComparisonDifference } from '@/shared/api';

import { boxToSheet } from '../model/pyramid';
import type { Placed, SheetTiles } from '../model/requests';
import type { TileRequest } from '../model/tile-loader';
import type { View } from '../model/pyramid';

import styles from './comparison-viewer.module.css';

export interface PaneLayer {
  readonly sheet: SheetTiles;
  /** Hide the part of the layer left of this per cent of the pane's width (the swipe); whole when absent. */
  readonly clipLeft?: number;
}

export interface BoxView {
  readonly index: number;
  readonly difference: ComparisonDifference;
  readonly selected: boolean;
}

export interface SheetPaneProps {
  readonly label: string;
  readonly layers: readonly PaneLayer[];
  readonly view: View;
  readonly dpi: number;
  readonly urlOf: (request: TileRequest) => string | null;
  readonly boxes: readonly BoxView[];
  /** A divider at this per cent of the pane's width. */
  readonly divider?: number;
  readonly dragging?: boolean;
  readonly innerRef?: Ref<HTMLDivElement>;
  readonly handlers?: HTMLAttributes<HTMLDivElement>;
}

function tileImage(placed: Placed, view: View, urlOf: (request: TileRequest) => string | null): ReactElement | null {
  const url = urlOf(placed.request);
  if (url === null) return null;
  const { tile } = placed;
  return (
    <img
      key={`${tile.level}/${tile.column}/${tile.row}`}
      className={styles.tile}
      src={url}
      alt=""
      draggable={false}
      style={{
        left: view.offsetX + tile.left * view.zoom,
        top: view.offsetY + tile.top * view.zoom,
        width: tile.width * view.zoom,
        height: tile.height * view.zoom,
      }}
    />
  );
}

export function SheetPane({ label, layers, view, dpi, urlOf, boxes, divider, dragging, innerRef, handlers }: SheetPaneProps) {
  return (
    <div
      ref={innerRef}
      className={dragging === true ? `${styles.pane} ${styles.paneDragging}` : styles.pane}
      role="group"
      aria-label={label}
      data-pane={label}
      {...handlers}
    >
      <span className={styles.paneLabel}>{label}</span>
      {layers.map(({ sheet, clipLeft }) => (
        <div
          key={sheet.kind}
          className={styles.layer}
          data-sheet={sheet.kind}
          style={clipLeft === undefined ? undefined : { clipPath: `inset(0 0 0 ${clipLeft}%)` }}
        >
          {tileImage(sheet.underlay, view, urlOf)}
          {sheet.tiles.map((placed) => tileImage(placed, view, urlOf))}
        </div>
      ))}
      {boxes.map(({ index, difference, selected }) => {
        const box = boxToSheet(difference.box, dpi);
        return (
          <div
            key={index}
            className={selected ? `${styles.box} ${styles.boxSelected}` : styles.box}
            data-difference={index}
            aria-hidden="true"
            style={{
              left: view.offsetX + box.left * view.zoom,
              top: view.offsetY + box.top * view.zoom,
              width: Math.max(2, box.width * view.zoom),
              height: Math.max(2, box.height * view.zoom),
            }}
          />
        );
      })}
      {divider === undefined ? null : <div className={styles.divider} style={{ left: `${divider}%` }} aria-hidden="true" />}
    </div>
  );
}
