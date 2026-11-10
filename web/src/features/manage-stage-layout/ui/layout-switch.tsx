'use client';

/**
 * The switch «Модели по этапам: включены» and its journal (`HOSTS-WEB-01`, plan 2026-11-09 §4.5 and §7.5; **administrator
 * only**, on the advanced page). On, runs started from now on take the layout; off, they follow the route as before. Runs
 * already started keep the plan they froze, so switching off breaks none of them. Each change is a journalled event with its
 * author and time.
 *
 * **A blocked switch says why.** The server refuses to switch on without a saved revision (`no_layout_revision`) and without
 * the database provider source (`provider_source_not_database`); the first is known from the layout itself, so the switch is
 * disabled with its reason beside it, and the second is said in words when the server refuses.
 */

import { useState } from 'react';

import type { StageModelLayout } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import {
  JOURNAL_EMPTY,
  JOURNAL_TITLE,
  SWITCH_HINT,
  SWITCH_LABEL,
  SWITCH_NEEDS_REVISION,
  layoutFailure,
} from '@/entities/stage-layout';
import { useCommandKey } from '@/features/manage-executor-connection';
import { HostFailure } from '@/features/manage-executor-host';
import { formatInstant } from '@/shared/lib';

import { useSetStageModelLayoutEnabled } from '../model/use-manage-stage-layout';
import styles from './manage-stage-layout.module.css';

export interface LayoutSwitchViewProps {
  readonly layout: StageModelLayout;
  readonly pending: boolean;
  readonly failure: ExecutionFailure | null;
  readonly onChange: (next: boolean) => void;
}

export function LayoutSwitchView({ layout, pending, failure, onChange }: LayoutSwitchViewProps) {
  // Switching on needs a saved revision; switching off never does.
  const blocked = !layout.enabled && layout.current === undefined;
  return (
    <section role="group" aria-label={SWITCH_LABEL} data-layout-switch={layout.enabled ? 'on' : 'off'}>
      <label>
        <input
          type="checkbox"
          role="switch"
          checked={layout.enabled}
          disabled={pending || blocked}
          onChange={(event) => onChange(event.currentTarget.checked)}
        />{' '}
        {SWITCH_LABEL}
      </label>
      <p className="am-form__hint">{SWITCH_HINT}</p>
      {blocked ? <p className="am-note" role="status" data-layout-switch-reason>{SWITCH_NEEDS_REVISION}</p> : null}
      {failure === null ? null : <HostFailure failure={failure} title="Переключатель не изменён" />}
      <details className={styles.fold}>
        <summary>{JOURNAL_TITLE}</summary>
        {layout.switch_journal.length === 0 ? (
          <p className="am-note">{JOURNAL_EMPTY}</p>
        ) : (
          <ul className={styles.journal} data-layout-journal>
            {layout.switch_journal.map((event) => (
              <li key={`${event.set_at}:${String(event.enabled)}`} className={styles.entry}>
                {event.enabled ? 'Включён' : 'Выключен'} · {formatInstant(event.set_at)}
              </li>
            ))}
          </ul>
        )}
      </details>
    </section>
  );
}

export function LayoutSwitch({ layout }: { readonly layout: StageModelLayout }) {
  const set = useSetStageModelLayoutEnabled();
  const keys = useCommandKey();
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);

  async function change(next: boolean) {
    setFailure(null);
    try {
      await set.mutateAsync({ enabled: next, idempotencyKey: keys.keyFor(String(next)) });
      keys.release();
    } catch (error) {
      const failed = layoutFailure(error, true);
      if (failed.kind !== 'unknown_outcome') keys.release();
      setFailure(failed);
    }
  }

  return <LayoutSwitchView layout={layout} pending={set.isPending} failure={failure} onChange={(next) => void change(next)} />;
}
