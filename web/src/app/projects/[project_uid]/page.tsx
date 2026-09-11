/**
 * `/projects/{project_uid}` — one project, its documents and its runs.
 *
 * Delegation-only. See the note in `/projects/page.tsx` for why these three routes were
 * wired by the integrator rather than by the session that wrote the screens.
 */

import { ProjectDetailPage } from '@/_pages/project-detail';

export default async function ProjectRoute({
  params,
}: {
  params: Promise<{ project_uid: string }>;
}) {
  const { project_uid } = await params;
  return <ProjectDetailPage projectUid={project_uid} />;
}
