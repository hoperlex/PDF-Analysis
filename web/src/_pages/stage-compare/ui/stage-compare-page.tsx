'use client';

import { useState } from 'react';

import type { ProjectUid } from '@/shared/api';
import { failureMessage } from '@/shared/api';
import { EmptyState, ErrorState, LoadingState, PageShell, UnsupportedState } from '@/shared/ui';
import { useMe } from '@/entities/account';
import { useProjectList } from '@/entities/project';
import { useProductVersion } from '@/entities/release';
import { StagePairCatalog } from '@/widgets/stage-pair-catalog';

export function StageComparePage() {
  const projects = useProjectList();
  const me = useMe();
  const product = useProductVersion(true);
  const [chosen, setChosen] = useState<ProjectUid | null>(null);
  const projectItems = projects.data?.items ?? [];
  const projectUid = chosen ?? (projectItems.length === 1 ? projectItems[0]!.project_uid : null);
  const moduleOn = product.data?.comparison_modules === 'versions,stages';
  const moduleOff = product.data !== undefined && !moduleOn;
  const mayAct = me.data?.roles.includes('expert') === true && moduleOn;
  const projectFailure = projects.error === null ? null : failureMessage(projects.error);
  const productFailure = product.error === null ? null : failureMessage(product.error);

  return (
    <PageShell title="Сравнение стадий" subtitle="Документы П и Р, подтверждённые пары и полнота комплекта.">
      {projectFailure === null ? null : <ErrorState title="Проекты не открылись" detail={projectFailure.detail} correlationId={projectFailure.correlationId} onRetry={projectFailure.retryable ? () => void projects.refetch() : undefined} />}
      {productFailure === null ? null : <ErrorState title="Состояние модуля не прочитано" detail={productFailure.detail} correlationId={productFailure.correlationId} onRetry={productFailure.retryable ? () => void product.refetch() : undefined} />}
      {projects.isPending || product.isPending ? <LoadingState what="сравнение стадий" /> : null}
      {moduleOff ? <UnsupportedState title="Модуль «Сравнение стадий» выключен" detail="Операции сравнения стадий на этом стенде недоступны." /> : null}
      {projects.isSuccess && moduleOn ? (
        <label>
          Проект{' '}
          <select value={projectUid ?? ''} onChange={(event) => setChosen(event.target.value === '' ? null : event.target.value)}>
            <option value="">— выберите —</option>
            {projectItems.map((project) => <option key={project.project_uid} value={project.project_uid}>{project.name}</option>)}
          </select>
        </label>
      ) : null}
      {projects.isSuccess && projectItems.length === 0 && moduleOn ? <EmptyState title="Проектов пока нет" detail="Создайте проект, затем добавьте документы П и Р." /> : null}
      {projects.isSuccess && projectItems.length > 1 && projectUid === null && moduleOn ? <EmptyState title="Выберите проект" detail="Пары и предложения относятся к одному проекту." /> : null}
      {projectUid !== null && moduleOn ? <StagePairCatalog key={projectUid} projectUid={projectUid} mayAct={mayAct} /> : null}
    </PageShell>
  );
}
