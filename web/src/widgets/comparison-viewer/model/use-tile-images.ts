'use client';

/**
 * The tiles of one sheet pair as `blob:` addresses a window can put in an `<img>` (`CMP-VIEWER-01`).
 *
 * Every tile goes through the generated client (`streamComparisonPairTile`): the BFF turns the session into the API
 * credential, so an `<img>` pointed at the API would carry none. The bytes arrive as a `Blob`, become an object URL for
 * as long as the window can still want them, and are revoked when the loader lets them go or the viewer closes
 * (`TileLoader`). Nothing is written to `localStorage`, `sessionStorage` or IndexedDB (the seam's `P3-WEB-02`: page bytes
 * are fetched per view and not persisted on the client).
 */

import { useEffect, useRef, useState } from 'react';

import { ApiError, TransportError, streamComparisonPairTile } from '@/shared/api';
import type { ComparisonSheetPairId } from '@/shared/api';

import { type FailureKind, type TileRequest, TileLoader, tileKey } from './tile-loader';

export interface TileImages {
  /** The address of a tile, or `null` while it is on its way, absent, or failed. */
  readonly urlOf: (request: TileRequest) => string | null;
  readonly failed: number;
  readonly pending: number;
  readonly retry: () => void;
}

const NO_IMAGES: TileImages = { urlOf: () => null, failed: 0, pending: 0, retry: () => {} };

/** `404` is a fact about the sheet; `dependency_unavailable` and a network failure are tried again; the rest is a failure. */
export function classifyTileFailure(error: unknown): FailureKind {
  if (error instanceof ApiError) {
    if (error.status === 404) return 'absent';
    return error.retryable ? 'retry' : 'failed';
  }
  if (error instanceof TransportError) return error.retryable ? 'retry' : 'failed';
  return 'failed';
}

export function useTileImages(pairId: ComparisonSheetPairId, requests: readonly TileRequest[]): TileImages {
  const loader = useRef<TileLoader | null>(null);
  const [, setVersion] = useState(0);

  useEffect(() => {
    const created = new TileLoader({
      fetchTile: async (request, signal) => {
        const response = await streamComparisonPairTile(
          {
            path: { comparison_sheet_pair_id: pairId },
            query: {
              mode: request.mode,
              level: request.level,
              column: request.column,
              row: request.row,
              ...(request.layers === undefined ? {} : { layers: request.layers }),
              ...(request.align === true ? { align_blocks: true } : {}),
            },
          },
          { signal },
        );
        return response.data;
      },
      classify: classifyTileFailure,
      createUrl: (blob) => URL.createObjectURL(blob),
      revokeUrl: (url) => URL.revokeObjectURL(url),
      onChange: () => setVersion((version) => version + 1),
    });
    loader.current = created;
    setVersion((version) => version + 1);
    return () => {
      created.dispose();
      if (loader.current === created) loader.current = null;
    };
  }, [pairId]);

  const wanted = requests.map(tileKey).join('|');
  useEffect(() => {
    loader.current?.want(requests);
    // `wanted` stands for `requests`: the same tiles in the same order are the same wish.
  }, [wanted, pairId]);

  const current = loader.current;
  if (current === null) return NO_IMAGES;
  return {
    urlOf: (request) => current.urlOf(request),
    failed: current.failedCount(),
    pending: current.pendingCount(),
    retry: () => current.retryFailed(),
  };
}
