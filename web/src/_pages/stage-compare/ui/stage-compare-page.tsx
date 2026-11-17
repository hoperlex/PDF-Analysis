'use client';

/**
 * `/stage-comparison` — «Сравнение стадий» (`UIP-S16-01`).
 *
 * The screen has no heading line of its own: the top row of the workspace holds the four steps at the left and «Загрузить документы»
 * at the right, as the original's does, and the heading «Сравнение стадий» stays in the markup for a reader of the screen only. The
 * link to «Сравнение версий» is the menu's.
 *
 * **The object** (`R-150c`, `UIP-G-06`; the registry class is `optional`) is the one of the top strip, and there is no list of
 * objects on this screen. The address says it first (`?project=<uid>`), and an address that says nothing opens on the object the
 * account chose last. Where there is none, or the strip says «Все объекты», the screen asks for an object in the strip in one line:
 * pairs and suggestions belong to one object, so no object means no workspace, and no object is picked for the reader.
 */

import type { ProjectUid } from '@/shared/api';
import { failureMessage } from '@/shared/api';
import { routes } from '@/shared/lib';
import { EmptyState, ErrorState, LoadingState, UnsupportedState } from '@/shared/ui';
import { useMe } from '@/entities/account';
import { useCurrentProject, useProjectList } from '@/entities/project';
import { useProductVersion } from '@/entities/release';
import { StageWorkspace } from './stage-workspace';
import styles from './stage-compare-page.module.css';

export function StageComparePage() {
  const projects = useProjectList();
  const me = useMe();
  const product = useProductVersion(true);
  const current = useCurrentProject(routes.stageComparison());
  const projectUid = current.projectUid as ProjectUid | null;
  const moduleOn = product.data?.comparison_modules === 'versions,stages';
  const moduleOff = product.data !== undefined && !moduleOn;
  const mayAct = me.data?.roles.includes('expert') === true && moduleOn;
  const projectFailure = projects.error === null ? null : failureMessage(projects.error);
  const productFailure = product.error === null ? null : failureMessage(product.error);
  const noProjects = projects.isSuccess && projects.data.items.length === 0;

  return (
    <section className="am-page" data-screen="stage-compare">
      <h1 className={styles.visuallyHidden}>Сравнение стадий</h1>
      <div className="am-page__body">
        {projectFailure === null ? null : <ErrorState title="Объекты не открылись" detail={projectFailure.detail} correlationId={projectFailure.correlationId} onRetry={projectFailure.retryable ? () => void projects.refetch() : undefined} />}
        {productFailure === null ? null : <ErrorState title="Состояние модуля не прочитано" detail={productFailure.detail} correlationId={productFailure.correlationId} onRetry={productFailure.retryable ? () => void product.refetch() : undefined} />}
        {projects.isPending || product.isPending || current.pending ? <LoadingState what="сравнение стадий" /> : null}
        {moduleOff ? <UnsupportedState title="Модуль «Сравнение стадий» выключен" detail="Операции сравнения стадий на этом стенде недоступны." /> : null}
        {noProjects && moduleOn ? <EmptyState title="Объектов пока нет" detail="Создайте объект, затем добавьте документы П и Р." /> : null}
        {projects.isSuccess && !noProjects && projectUid === null && !current.pending && moduleOn ? <EmptyState title="Выберите объект в верхней строке" /> : null}
        {projectUid !== null && moduleOn ? (
          <div className={styles.workspace}>
            <StageWorkspace key={projectUid} projectUid={projectUid} mayAct={mayAct} />
          </div>
        ) : null}
      </div>
    </section>
  );
}
