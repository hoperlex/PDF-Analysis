/**
 * Public API of the `projects` page slice.
 *
 * The route file at `web/src/app/projects/page.tsx` delegates here. That file belongs to
 * the toolchain owner, so this module exists and waits to be pointed at rather than
 * reaching up into `app/` to mount itself.
 */

export { ProjectsPage } from './ui/projects-page';
