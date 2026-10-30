'use client';

import { useEffect, useMemo, useRef, useState } from 'react';

import { streamVersionPageTile } from '@/shared/api';
import type { TileStatus, ViewerGeometry, ViewerState } from '@/widgets/comparison-viewer';
import { stageTileKey, stageTileRequests } from './viewer';

export function useStageTiles(profileId: string | undefined, geometry: ViewerGeometry | null, state: ViewerState): TileStatus {
  const cache = useRef(new Map<string, string>());
  const failures = useRef(new Set<string>());
  const [version, setVersion] = useState(0);
  const [pending, setPending] = useState(0);
  const [retry, setRetry] = useState(0);
  const requests = useMemo(() => stageTileRequests(geometry, state), [geometry, state]);
  const signature = requests.map(stageTileKey).join(';');
  useEffect(() => {
    const images = cache.current;
    const failed = failures.current;
    return () => { images.forEach((url) => URL.revokeObjectURL(url)); images.clear(); failed.clear(); };
  }, [profileId]);
  useEffect(() => {
    if (profileId === undefined) return;
    const controller = new AbortController();
    const wanted = requests.filter((request) => !cache.current.has(stageTileKey(request)) && !failures.current.has(stageTileKey(request)));
    setPending(wanted.length);
    let next = 0;
    const worker = async () => {
      while (next < wanted.length && !controller.signal.aborted) {
        const request = wanted[next++]!;
        const key = stageTileKey(request);
        try {
          const answer = await streamVersionPageTile({
            path: { comparison_page_profile_id: profileId },
            query: { level: request.level, column: request.column, row: request.row },
          }, { signal: controller.signal });
          if (!controller.signal.aborted) {
            cache.current.set(key, URL.createObjectURL(answer.data));
            while (cache.current.size > 160) {
              const oldest = cache.current.keys().next().value as string | undefined;
              if (oldest === undefined) break;
              URL.revokeObjectURL(cache.current.get(oldest)!);
              cache.current.delete(oldest);
            }
          }
        } catch { if (!controller.signal.aborted) failures.current.add(key); }
        if (!controller.signal.aborted) {
          setPending((count) => Math.max(0, count - 1));
          setVersion((value) => value + 1);
        }
      }
    };
    void Promise.all(Array.from({ length: Math.min(6, wanted.length) }, worker));
    return () => controller.abort();
    // The signature is the complete identity of the requested tile set.
  }, [profileId, signature, retry]);
  void version;
  return { urlOf: (request) => cache.current.get(stageTileKey(request)) ?? null,
    failed: requests.filter((request) => failures.current.has(stageTileKey(request))).length,
    pending,
    retry: () => { failures.current.clear(); setRetry((value) => value + 1); },
  };
}
