'use client';

/**
 * `/projects` — the project list and create screen.
 *
 * Composition only: the frame from `shared/ui`, the create form from a feature, the list
 * from a widget. No query, no mutation and no domain rule lives at this layer.
 *
 * **No subtitle, `W50-LAZY-01`.** It read «Одна учётная запись на эту установку. Ролей и
 * разделения на организации пока нет.» — false since W49, which gave this installation
 * accounts and a role set. It is removed rather than reworded: what accounts and roles a
 * session has is the frame's account menu's to say (`W50-SHELL-FRAME`), not a sentence on
 * one screen that the next identity change would make false again.
 */

import { PageShell } from '@/shared/ui';
import { CreateProjectForm } from '@/features/create-project';
import { ProjectList } from '@/widgets/project-list';

export function ProjectsPage() {
  return (
    <PageShell title="Проекты">
      <CreateProjectForm />
      <h2>Все проекты</h2>
      <ProjectList />
    </PageShell>
  );
}
