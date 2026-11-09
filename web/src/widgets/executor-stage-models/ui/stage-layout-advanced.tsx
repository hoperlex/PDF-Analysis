'use client';

/**
 * «Модели по этапам» on the advanced page (`HOSTS-WEB-01`, plan 2026-11-09 §4.5 and §7.5; **administrator only**): the switch
 * «Модели по этапам: включены» with its journal, and the revisions of the layout, newest first. The table and the form are on
 * the screen «Исполнители»; what lives here is what the plan keeps out of it: putting the layout in force, and its history.
 */

import type { Role, StageModelLayout } from '@/shared/api';
import { canExecute, executionFailure } from '@/entities/execution';
import { mayReadHosts } from '@/entities/executor-host';
import {
  HISTORY_EMPTY,
  HISTORY_TITLE,
  STAGE_KIT_LABELS,
  useStageModelLayout,
} from '@/entities/stage-layout';
import { LayoutSwitch } from '@/features/manage-stage-layout';
import { formatInstant } from '@/shared/lib';
import { ErrorState, LoadingState, UnsupportedState } from '@/shared/ui';

import styles from './executor-stage-models.module.css';

/** The revisions newest first, with their set and time. The pure part. */
export function LayoutHistoryView({ layout }: { readonly layout: StageModelLayout }) {
  const revisions = [...layout.history].sort((a, b) => b.revision_no - a.revision_no);
  return (
    <section role="group" aria-label={HISTORY_TITLE} data-layout-history>
      <h3>{HISTORY_TITLE}</h3>
      {revisions.length === 0 ? (
        <p className="am-note">{HISTORY_EMPTY}</p>
      ) : (
        <ul className={styles.cells}>
          {revisions.map((revision) => (
            <li key={revision.layout_revision_id} className={styles.cell} data-layout-revision={revision.revision_no}>
              Версия {revision.revision_no} · {STAGE_KIT_LABELS[revision.kit]} · {formatInstant(revision.created_at)}
              {layout.current?.layout_revision_id === revision.layout_revision_id ? ' · действует' : ''}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function StageLayoutAdvanced({ roles }: { readonly roles: readonly Role[] }) {
  const admin = canExecute(roles, 'connections') && mayReadHosts(roles);
  const layout = useStageModelLayout(admin);
  if (!admin) return <UnsupportedState title="Недоступно" detail="Переключатель набора моделей меняет администратор." />;
  if (layout.isPending) return <LoadingState what="модели по этапам" />;
  if (layout.data === undefined) {
    const failure = executionFailure(layout.error, false);
    return (
      <ErrorState title="Модели по этапам не прочитаны" detail={failure.detail} correlationId={failure.correlationId} onRetry={() => void layout.refetch()} />
    );
  }
  return (
    <div className={styles.panel} data-stage-layout-advanced>
      <LayoutSwitch layout={layout.data} />
      <LayoutHistoryView layout={layout.data} />
    </div>
  );
}
