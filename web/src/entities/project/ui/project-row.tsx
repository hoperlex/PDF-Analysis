/**
 * One project as a row.
 *
 * Presentational: it takes a contract `Project` and renders it. It holds no query, no
 * mutation and no route policy beyond the URL frozen in the UI seam document.
 */

import Link from 'next/link';

import type { Project } from '@/shared/api';
import { formatInstant } from '@/shared/lib';

import { projectDocumentCountLabel } from '../model/project';

export interface ProjectRowProps {
  readonly project: Project;
}

export function ProjectRow({ project }: ProjectRowProps) {
  return (
    <li className="am-state" style={{ marginBottom: '0.5rem' }}>
      <p className="am-state__title">
        <Link href={`/projects/${project.project_uid}`}>{project.name}</Link>
      </p>
      <div className="am-state__detail">
        <p>
          <code>{project.project_uid}</code>
        </p>
        <p>
          Created {formatInstant(project.created_at)} · documents{' '}
          {projectDocumentCountLabel(project)}
        </p>
      </div>
    </li>
  );
}
