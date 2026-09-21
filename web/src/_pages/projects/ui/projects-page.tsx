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
      title="Проекты"
      subtitle="Один локальный проверяющий. Без аутентификации, ролей и разделения на организации."
    >
      <CreateProjectForm />
      <h2>Все проекты</h2>
      <ProjectList />
    </PageShell>
  );
}
