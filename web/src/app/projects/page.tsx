/**
 * `/projects` — project list and create.
 *
 * Delegation-only: the route decides nothing. `B7` could not write this file - the app
 * directory was read-only to it and a forbidden hotspot in its task - so the placeholder
 * stood after its screens landed, nothing imported the page slices, and `next build`
 * tree-shook them away. The build's exit 0 covered the shell rather than the screens.
 */

import { ProjectsPage } from '@/_pages/projects';

export default function ProjectsRoute() {
  return <ProjectsPage />;
}
