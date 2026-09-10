/**
 * `/projects` — project list and create.
 *
 * Delegation-only. When `B7` lands `@/_pages/projects`, the body of this file becomes
 * `return <ProjectsPage />;` and nothing else changes here.
 */

import { RoutePlaceholder } from '@/shared/ui';

export default function ProjectsRoute() {
  return (
    <RoutePlaceholder
      screen="Projects"
      route="/projects"
      awaitingModule="@/_pages/projects"
      owner="Gate B session B7"
    />
  );
}
