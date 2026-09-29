/**
 * `/projects` — project list and create.
 *
 * Delegation-only: the route decides nothing. `B7` could not write this file - the app
 * directory was read-only to it and a forbidden hotspot in its task - so the placeholder
 * stood after its screens landed, nothing imported the page slices, and `next build`
 * tree-shook them away. The build's exit 0 covered the shell rather than the screens.
 *
 * `R-50`: the route awaits `requireAChangedPassword()` before it renders. A session still
 * on the password this deployment was seeded with is sent to `/account/password` instead,
 * and the API refuses this screen's data calls independently -- so what the reviewer would
 * otherwise meet here is a screen that cannot load. Declared `force-dynamic` because the
 * check reads a cookie, and a screen served from a cache is a screen showing somebody
 * else's session.
 */

import { ProjectsPage } from '@/_pages/projects';

import { requireAChangedPassword } from '../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function ProjectsRoute() {
  await requireAChangedPassword();
  return <ProjectsPage />;
}
