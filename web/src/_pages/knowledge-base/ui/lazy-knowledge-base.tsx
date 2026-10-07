'use client';

/**
 * The knowledge-base widget, loaded lazily — `W50-PLAN.md` §3.4, `W50-LAZY-01`.
 *
 * The same construction as `_pages/dashboard/ui/lazy-dashboard.tsx`, whose header carries
 * the whole argument: a `next/dynamic` chunk with a typed `<LoadingState />` fallback below
 * the page's guard (the segment `loading.tsx` above the guard turned a guest's `307` into a
 * streamed redirect and is deleted), and `KnowledgeBaseEagerSeam`, which only the screen
 * harness provides, so the instruments that render in one synchronous pass see the widget
 * rather than its fallback. No static import of the widget: `CATEGORY_LABELS`, which the
 * page used to import from it, now comes from `entities/expert-decision`.
 */

import dynamic from 'next/dynamic';
import { createContext, useContext } from 'react';
import type { ComponentProps, ComponentType } from 'react';

import { LoadingState } from '@/shared/ui';

const KnowledgeBaseChunk = dynamic(
  () => import('@/widgets/knowledge-base').then((widget) => widget.KnowledgeBase),
  { loading: () => <LoadingState /> },
);

type KnowledgeBaseProps = ComponentProps<typeof KnowledgeBaseChunk>;

/** The eager seam. `null` everywhere but the screen harness. */
export const KnowledgeBaseEagerSeam = createContext<ComponentType<KnowledgeBaseProps> | null>(
  null,
);

export function LazyKnowledgeBase(props: KnowledgeBaseProps) {
  const Eager = useContext(KnowledgeBaseEagerSeam);
  return Eager === null ? <KnowledgeBaseChunk {...props} /> : <Eager {...props} />;
}
