'use client';

/**
 * The home page's five most recent projects (`W50-PLAN.md` §3.6), in the contract's order
 * (`recentProjects`). Each project links through `routes` (`@/shared/lib`), the one place an
 * address is built.
 */

import Link from 'next/link';

import { formatInstant, routes } from '@/shared/lib';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { classifyProjectListFailure } from '@/entities/project';

import { useRecentProjects } from '../api/home-reads';
import { recentProjects } from '../model/recent-projects';
import { NO_PROJECTS_DETAIL, NO_PROJECTS_TITLE } from './copy';
import styles from './home-tiles.module.css';

function Body() {
  const query = useRecentProjects();

  if (query.isPending) return <LoadingState what="последние проекты" />;

  if (query.isError) {
    const failure = classifyProjectListFailure(query.error);
    return (
      <ErrorState
        title={failure.title}
        detail={<span data-list-failure={failure.kind}>{failure.detail}</span>}
        correlationId={failure.correlationId}
        {...(failure.retryable
          ? { onRetry: () => void query.refetch(), retryLabel: 'Повторить' }
          : {})}
      />
    );
  }

  const shown = recentProjects(query.data);
  if (shown.length === 0) {
    return <EmptyState title={NO_PROJECTS_TITLE} detail={NO_PROJECTS_DETAIL} />;
  }

  return (
    <ol className={styles.projects} data-recent-project-count={shown.length}>
      {shown.map((project) => (
        <li key={project.project_uid} className={styles.project}>
          <Link href={routes.project(project.project_uid)}>{project.name}</Link>
          <span className={styles.created}>создан {formatInstant(project.created_at)}</span>
        </li>
      ))}
    </ol>
  );
}

export function RecentProjectsTile() {
  return (
    <section className={styles.tile} aria-labelledby="home-recent-projects" data-home-tile="recent-projects">
      <h2 id="home-recent-projects">Последние проекты</h2>
      <Body />
      <p className={styles.more}>
        <Link href={routes.projects()}>Все проекты</Link>
      </p>
    </section>
  );
}
