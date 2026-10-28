'use client';

/**
 * The thumbnail of one page of a matrix as a `blob:` address a cell can put in an `<img>`
 * (`streamVersionPageThumbnail`, `CMP-PROFILE-01`). One store serves the whole page (`ThumbnailStore`), created
 * in the browser on first use; a server render has no store and every cell draws its placeholder.
 */

import { useEffect, useSyncExternalStore } from 'react';

import { ApiError, TransportError, streamVersionPageThumbnail } from '@/shared/api';

import type { ThumbnailFailureKind, ThumbnailSnapshot } from '../model/thumbnail-store';
import { ThumbnailStore } from '../model/thumbnail-store';

/** `404` is a fact about the page; a retryable answer or a network failure is tried again; the rest failed. */
export function classifyThumbnailFailure(error: unknown): ThumbnailFailureKind {
  if (error instanceof ApiError) {
    if (error.status === 404) return 'absent';
    return error.retryable ? 'retry' : 'failed';
  }
  if (error instanceof TransportError) return error.retryable ? 'retry' : 'failed';
  return 'failed';
}

let shared: ThumbnailStore | null = null;

function store(): ThumbnailStore | null {
  if (typeof window === 'undefined') return null;
  shared ??= new ThumbnailStore({
    fetchThumbnail: async (profileId, signal) =>
      (await streamVersionPageThumbnail({ path: { comparison_page_profile_id: profileId } }, { signal })).data,
    classify: classifyThumbnailFailure,
    createUrl: (blob) => URL.createObjectURL(blob),
    revokeUrl: (url) => URL.revokeObjectURL(url),
  });
  return shared;
}

const NONE: ThumbnailSnapshot = { state: 'loading', url: null };
const noSubscription = (): (() => void) => () => {};

/** The thumbnail of a page profile while `wanted` (a cell in view); the placeholder otherwise. */
export function useThumbnail(profileId: string | undefined, wanted: boolean): ThumbnailSnapshot {
  const held = store();
  useEffect(() => {
    if (held === null || profileId === undefined || !wanted) return undefined;
    held.acquire(profileId);
    return () => held.release(profileId);
  }, [held, profileId, wanted]);
  return useSyncExternalStore(
    held === null ? noSubscription : held.subscribe,
    () => (held === null || profileId === undefined || !wanted ? NONE : held.snapshot(profileId)),
    () => NONE,
  );
}
