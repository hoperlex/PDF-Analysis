/**
 * `/projects/{project_uid}` — one project: upload an AR PDF, start a run.
 *
 * Delegation-only. When `B7` lands `@/_pages/project-detail`, the body becomes
 * `return <ProjectDetailPage projectUid={project_uid} />;`.
 *
 * The route parameter is named `project_uid`, matching the contract's path parameter
 * exactly. It is an opaque `prj_<ULID>`; nothing in the UI parses it.
 */

import { RoutePlaceholder } from '@/shared/ui';

export default async function ProjectDetailRoute({
  params,
}: {
  params: Promise<{ project_uid: string }>;
}) {
  const { project_uid } = await params;
  return (
    <RoutePlaceholder
      screen="Project"
      route={`/projects/${project_uid}`}
      awaitingModule="@/_pages/project-detail"
      owner="Gate B session B7"
    />
  );
}
