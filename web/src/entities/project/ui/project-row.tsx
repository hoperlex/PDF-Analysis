/**
 * One project as a row.
 *
 * Presentational: it takes a contract `Project` and renders it. It holds no query, no
 * mutation and no route policy beyond the URL frozen in the UI seam document.
 *
 * **Dense, as the original's object list** (`UI-A-10`): the name and its figures share one row instead of a
 * bordered block of three paragraphs. The figures come from the project's own `audit_counts` (`listProjects`, contract
 * 1.19.0) and arrive as the `figures` slot, drawn by the widget that knows how to say them; a project without them
 * (the answer of `createProject` carries none) keeps the plain count of documents. The opaque identity stays in the
 * link's address and in its tooltip, and the project's own page prints it.
 */

import type { ReactNode } from 'react';
import Link from 'next/link';

import type { Project } from '@/shared/api';
import { formatInstant } from '@/shared/lib';

import { projectDocumentCountLabel } from '../model/project';
import styles from './project-row.module.css';

export interface ProjectRowProps {
  readonly project: Project;
  /** The row of audit figures, when the project carries them; absent, the plain count of documents. */
  readonly figures?: ReactNode | undefined;
}

export function ProjectRow({ project, figures }: ProjectRowProps) {
  return (
    <li className={styles.row} data-project-uid={project.project_uid}>
      <Link className={styles.name} href={`/projects/${project.project_uid}`} title={project.project_uid}>
        {project.name}
      </Link>
      <span className={styles.created}>создан {formatInstant(project.created_at)}</span>
      <span className={styles.figures}>
        {figures ?? <>документов {projectDocumentCountLabel(project)}</>}
      </span>
    </li>
  );
}
