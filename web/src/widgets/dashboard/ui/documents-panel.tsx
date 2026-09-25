'use client';

/**
 * Panel 1 — documents per project.
 *
 * `D1`: `Project.document_count` exists today, so this panel is a straight read of
 * `listProjects` — the same query `widgets/project-list` already makes, under the same
 * cache key, so it inherits that screen's loading/error/empty/paged coverage rather than
 * inventing a second one. Real numbers only: `document_count` is optional in the
 * contract, and an absent count is rendered as absent (`projectDocumentCountLabel`'s
 * `—`), never folded into the sum as zero.
 *
 * **Scope, said plainly rather than implied.** This reads one page of `listProjects`
 * (`PROJECT_PAGE_LIMIT` projects). It is a page total, not a deployment total, and the
 * caption says so the moment the page carries a `next_cursor` — the full list is one
 * click away on `/projects`, and this panel does not re-implement its pager.
 */

import Link from 'next/link';

import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { ProjectRow, classifyProjectListFailure, useProjectList } from '@/entities/project';

import { summarizeDocumentTotals } from '../model/document-totals';

export function DocumentsPanel() {
  const projects = useProjectList();

  if (projects.isPending) return <LoadingState what="документы по проектам" />;

  if (projects.isError) {
    const failure = classifyProjectListFailure(projects.error);
    return (
      <ErrorState
        title={failure.title}
        detail={<span data-list-failure={failure.kind}>{failure.detail}</span>}
        correlationId={failure.correlationId}
        {...(failure.retryable
          ? { onRetry: () => void projects.refetch(), retryLabel: 'Повторить' }
          : {})}
      />
    );
  }

  const page = projects.data;

  if (page.items.length === 0) {
    return (
      <EmptyState
        title="Проектов пока нет."
        detail="Как только появится первый проект, здесь будут его документы."
      />
    );
  }

  const summary = summarizeDocumentTotals(page.items);
  const truncated = page.page.next_cursor !== null;

  return (
    <div data-panel="documents-per-project">
      <p>
        Документов: <strong data-known-total={summary.knownTotal}>{summary.knownTotal}</strong> на{' '}
        {summary.knownProjectCount === page.items.length
          ? `${page.items.length} проектах`
          : `${summary.knownProjectCount} из ${page.items.length} проектов`}
        {summary.unknownProjectCount > 0
          ? `; по ${summary.unknownProjectCount} проектам сервер число документов не сообщил`
          : ''}
        .
      </p>
      {truncated ? (
        <p className="am-state__correlation">
          Показана первая страница проектов. Полный список — на{' '}
          <Link href="/projects">странице проектов</Link>.
        </p>
      ) : null}
      <ul className="am-rows">
        {page.items.map((project) => (
          <ProjectRow key={project.project_uid} project={project} />
        ))}
      </ul>
    </div>
  );
}
