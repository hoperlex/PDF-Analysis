'use client';

/**
 * `/projects` — the project list and create screen.
 *
 * Composition only: the frame from `shared/ui`, the create form from a feature, the list
 * from a widget. No query, no mutation and no domain rule lives at this layer.
 */

import { PageShell } from '@/shared/ui';
import { CreateProjectForm } from '@/features/create-project';
import { ProjectList } from '@/widgets/project-list';

export function ProjectsPage() {
  return (
    <PageShell
      title="Projects"
      subtitle="One local reviewer. No authentication, no roles, no tenancy."
    >
      <CreateProjectForm />
      <h2>All projects</h2>
      <ProjectList />
    </PageShell>
  );
}
