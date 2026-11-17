'use client';

/**
 * «Модели по этапам» of the screen «Диспетчер» (`HOSTS-WEB-01`, ADR-0028, plan 2026-11-09 §7.4): the table of the six rows and, for an
 * administrator, the form «Изменить». The table itself lives in `entities/stage-layout` (`UIP-S15-02`: the window of a start draws the
 * same one) and is re-exported here, so the screens and the tests that import it from this widget are unchanged. The viewer neither sees
 * the tab nor reads the layout (`R-150w`). The revisions and the journal live on the advanced page.
 */

import { useState } from 'react';

import type { Role } from '@/shared/api';
import { canExecute, executionFailure } from '@/entities/execution';
import { availableModelIds, mayReadHosts, useExecutorHosts } from '@/entities/executor-host';
import { StageModelsTable, useModelCatalogue, useStageModelLayout } from '@/entities/stage-layout';
import { LayoutEditor } from '@/features/manage-stage-layout';
import { ErrorState, LoadingState, UnsupportedState } from '@/shared/ui';

import styles from './executor-stage-models.module.css';

export interface ExecutorStageModelsProps {
  readonly roles: readonly Role[];
  /** Test seam: the administrator's form starts open. */
  readonly initiallyEditing?: boolean | undefined;
}

export function ExecutorStageModels({ roles, initiallyEditing = false }: ExecutorStageModelsProps) {
  const readable = mayReadHosts(roles);
  const admin = canExecute(roles, 'connections');
  const layout = useStageModelLayout(readable);
  // The models the form may offer are those some server can serve now, so the administrator also reads the servers.
  const hosts = useExecutorHosts(readable && admin);
  const catalogue = useModelCatalogue(readable && admin);
  const [editing, setEditing] = useState(initiallyEditing);

  if (!readable) {
    return <UnsupportedState title="Модели по этапам недоступны" detail="Набор моделей показывается экспертам и администраторам." />;
  }
  if (layout.isPending) return <LoadingState what="модели по этапам" />;
  if (layout.data === undefined) {
    const failure = executionFailure(layout.error, false);
    return (
      <div data-layout-read-failure={failure.kind}>
        <ErrorState title="Модели по этапам не прочитаны" detail={failure.detail} correlationId={failure.correlationId} onRetry={() => void layout.refetch()} />
      </div>
    );
  }

  const formReady = admin && editing && hosts.data !== undefined && catalogue.data !== undefined;
  return (
    <div className={styles.panel} data-executor-stage-models>
      {formReady ? (
        <LayoutEditor
          layout={layout.data}
          catalogue={catalogue.data}
          availableModelIds={availableModelIds(hosts.data)}
          onClose={() => setEditing(false)}
        />
      ) : (
        <StageModelsTable layout={layout.data} admin={admin} onEdit={() => setEditing(true)} />
      )}
      {admin && editing && !formReady ? <LoadingState what="серверы и каталог моделей" /> : null}
    </div>
  );
}
