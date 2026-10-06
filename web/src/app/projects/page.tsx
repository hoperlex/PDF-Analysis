/**
 * `/projects` — project list and create.
 *
 * Delegation-only: the route decides nothing. `B7` could not write this file - the app
 * directory was read-only to it and a forbidden hotspot in its task - so the placeholder
 * stood after its screens landed, nothing imported the page slices, and `next build`
 * tree-shook them away. The build's exit 0 covered the shell rather than the screens.
 *
 * `W50-PLAN.md` §3.2: the route awaits `requireScreen` with its own address, `params` and
 * `searchParams` before it renders, and the screen registry's row for that address decides
 * who may open it: a guest is sent to sign in and comes back here, a default credential
 * goes to `/account/password`, an incomplete profile to `/account`. Declared
 * `force-dynamic` because the guard reads a cookie, and a screen served from a cache is a
 * screen showing somebody else's session.
 */

import { ProjectsPage } from '@/_pages/projects';

import type { ScreenRouteProps } from '../bff/session/screen-lock';
import { requireScreen } from '../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function ProjectsRoute({ params, searchParams }: ScreenRouteProps) {
  await requireScreen('/projects', { params, searchParams });
  return <ProjectsPage />;
}
