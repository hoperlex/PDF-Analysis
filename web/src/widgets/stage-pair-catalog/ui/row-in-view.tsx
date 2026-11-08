'use client';

import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';

import { watchViewport } from '../model/rows-in-view';

export interface RowInViewProps {
  readonly pairId: string;
  /** Called with the row's pair and whether the row is in view; the catalog keeps the set of rows in view. */
  readonly onVisibility: (pairId: string, visible: boolean) => void;
  readonly className?: string | undefined;
  readonly children: ReactNode;
}

/** The anchor of one row of the pairs catalog: it reports whether the row is in view, and that the row is gone when it unmounts. */
export function RowInView({ pairId, onVisibility, className, children }: RowInViewProps) {
  const anchor = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = anchor.current;
    if (element === null) return undefined;
    const stop = watchViewport(element, (visible) => onVisibility(pairId, visible));
    return () => {
      stop();
      onVisibility(pairId, false);
    };
  }, [pairId, onVisibility]);
  return <div ref={anchor} className={className} data-pair-row-anchor={pairId}>{children}</div>;
}
