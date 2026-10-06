/**
 * `/projects` while its screen loads — a typed state from `shared/ui`, never a blank frame.
 *
 * `W50-PLAN.md` §3.3. A placeholder body: `W50-LAZY-01` decides what this segment shows while
 * its heavy widgets load, and fills it.
 */

import { LoadingState } from '@/shared/ui';

export default function ProjectsLoading() {
  return <LoadingState />;
}
