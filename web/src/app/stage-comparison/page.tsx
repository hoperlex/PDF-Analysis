/** Registered screen for the stage-pair catalog. */

import { StageComparePage } from '@/_pages/stage-compare';

import type { ScreenRouteProps } from '../bff/session/screen-lock';
import { requireScreen } from '../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function StageComparisonRoute({ params, searchParams }: ScreenRouteProps) {
  await requireScreen('/stage-comparison', { params, searchParams });
  return <StageComparePage />;
}
