'use client';

/**
 * The project list.
 *
 * Every outcome of the read is one of the mandatory states and none of them is silence:
 * in flight is `LoadingState`, a failure is `ErrorState` with the correlation id, and a
 * genuinely empty list is `EmptyState` — which is a different claim from "the request
 * failed" and must not look like it.
 *
 * Paging follows the opaque cursor exactly as received. Nothing here parses one, builds
 * one, or assumes a page number behind it.
 */

import { useState } from 'react';

import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { ProjectRow, classifyProjectListFailure, useProjectList } from '@/entities/project';

export function ProjectList() {
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const query = useProjectList(cursor);

  if (query.isPending) return <LoadingState what="projects" />;

  if (query.isError) {
    const failure = classifyProjectListFailure(query.error);
    return (
      <ErrorState
        title={failure.title}
        detail={<span data-list-failure={failure.kind}>{failure.detail}</span>}
        correlationId={failure.correlationId}
        {...(failure.retryable
          ? { onRetry: () => void query.refetch(), retryLabel: 'Try again' }
          : {})}
      />
    );
  }

  const page = query.data;

  if (page.items.length === 0) {
    return (
      <EmptyState
        title="No projects yet."
        detail="Create one above, then upload the annual report PDF you want checked."
      />
    );
  }

  const nextCursor = page.page.next_cursor;

  return (
    <div>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {page.items.map((project) => (
          <ProjectRow key={project.project_uid} project={project} />
        ))}
      </ul>
      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
        {cursor === undefined ? null : (
          <button type="button" className="am-button" onClick={() => setCursor(undefined)}>
            First page
          </button>
        )}
        {nextCursor === null ? null : (
          <button type="button" className="am-button" onClick={() => setCursor(nextCursor)}>
            Next page
          </button>
        )}
      </div>
    </div>
  );
}
