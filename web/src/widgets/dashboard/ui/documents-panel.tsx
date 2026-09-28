/**
 * Panel 1 — documents per project.
 *
 * `W46-WIRE`, `F-3b`. Presentational only: `Dashboard` reads `getDashboardSummary` once
 * and hands this panel its `documents_by_project` rows. Every count here is server-side
 * and deployment-wide — `ProjectDocumentCount.document_count` is not optional the way
 * `Project.document_count` is, so there is no "server did not say" branch left to draw:
 * every row this operation sends carries a real number.
 */

import Link from 'next/link';

import { EmptyState } from '@/shared/ui';
import type { ProjectDocumentCount } from '@/shared/api';

export interface DocumentsPanelProps {
  readonly rows: readonly ProjectDocumentCount[];
}

export function DocumentsPanel({ rows }: DocumentsPanelProps) {
  if (rows.length === 0) {
    return (
      <EmptyState
        title="Проектов пока нет."
        detail="Как только появится первый проект, здесь будут его документы."
      />
    );
  }

  const total = rows.reduce((sum, row) => sum + row.document_count, 0);

  return (
    <div data-panel="documents-per-project">
      <p>
        Документов: <strong>{total}</strong> на {rows.length}{' '}
        {rows.length === 1 ? 'проекте' : 'проектах'}.
      </p>
      <ul className="am-rows">
        {rows.map((row) => (
          <li key={row.project_uid} className="am-state" data-project={row.project_uid}>
            <p className="am-state__title">
              <Link href={`/projects/${row.project_uid}`}>{row.name}</Link>
            </p>
            <div className="am-state__detail">
              <p>документов {row.document_count}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
