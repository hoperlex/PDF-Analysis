'use client';

/** @jsxRuntime automatic */

/**
 * «Прецеденты и векторы» on the advanced page (`PREC-WEB`, plan-v5 sections 2.6 and 6; **administrator only**): the refusal labels by section.
 *
 * Each section the journal names shows whether its labels «Обычно отклоняют» and «Рекомендуется снять» are on, the digest of the replay report the
 * switch was made from, and the threshold it chose. A section on can be switched off here (the way back needs no report). Switching ON needs the
 * report's digest, and the report has no endpoint in this contract, so this screen does not offer it and says so: it is not a switch that does nothing.
 * Every change is a journalled event with its author. Neutral labels, comments and «Возможные нормы» do not depend on this switch.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import type { PrecedentSetting, PrecedentSettingList } from '@/shared/api';
import { appendPrecedentSetting } from '@/shared/api';
import { executionFailure } from '@/entities/execution';
import type { ExecutionFailure } from '@/entities/execution';
import { precedentKeys, usePrecedentSettings } from '@/entities/decision-memory';
import { useCommandKey } from '@/features/manage-executor-connection';
import { ErrorState, LoadingState } from '@/shared/ui';

import { sectionLabelStates, shortDigest, valueWithSectionOff } from '../model/precedent-sections';
import type { SectionLabelState } from '../model/precedent-sections';
import styles from './workers-page.module.css';

export interface PrecedentSectionsViewProps {
  readonly sections: readonly SectionLabelState[];
  readonly pending: boolean;
  readonly failure: ExecutionFailure | null;
  readonly onOff: (section: string) => void;
}

export function PrecedentSectionsView({ sections, pending, failure, onOff }: PrecedentSectionsViewProps) {
  return (
    <section role="group" aria-label="Метки к отказу по разделам" data-precedent-sections={sections.filter((one) => one.enabled).length}>
      <p className="am-form__hint">
        Метки «Обычно отклоняют» и «Рекомендуется снять» включаются по разделам, по отчёту повтора истории. Нейтральные метки, комментарии и
        «Возможные нормы» от этого не зависят.
      </p>
      {sections.length === 0 ? (
        <p className="am-note" data-precedent-sections-none="">Метки к отказу выключены во всех разделах: ни один раздел не включался.</p>
      ) : (
        <ul className={styles.precedentSections}>
          {sections.map((one) => (
            <li key={one.section} className={styles.precedentSection} data-precedent-section={one.section} data-precedent-section-enabled={String(one.enabled)}>
              <strong>{one.section}</strong>
              <span>{one.enabled ? 'метки к отказу включены' : 'метки к отказу выключены'}</span>
              {one.reportSha256 === null ? null : (
                <span className={styles.precedentDigest} title={one.reportSha256}>отчёт {shortDigest(one.reportSha256)}</span>
              )}
              {one.analogous === null ? null : <span className={styles.precedentDigest}>порог сходства {one.analogous.toLocaleString('ru-RU')}</span>}
              {one.enabled ? (
                <button type="button" className="am-button am-button--quiet am-button--small" disabled={pending} data-precedent-section-off={one.section} onClick={() => onOff(one.section)}>
                  Выключить
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      )}
      <p className="am-note" data-precedent-enable-note="">
        Включить раздел можно только с отчётом повтора истории: у отчёта пока нет экрана, поэтому здесь доступно лишь выключение.
      </p>
      {failure === null ? null : <ErrorState title="Настройка не изменена" detail={failure.detail} correlationId={failure.correlationId} />}
    </section>
  );
}

export function PrecedentSections() {
  const settings = usePrecedentSettings(true);
  const client = useQueryClient();
  const keys = useCommandKey();
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);
  const write = useMutation<PrecedentSetting, unknown, { value: Record<string, unknown>; idempotencyKey: string }>({
    // The contract types `value` as an object with no members (the generator lost the shape); the value is the server's own `section_labels`.
    mutationFn: async ({ value, idempotencyKey }) =>
      (await appendPrecedentSetting({ body: { setting_name: 'section_labels', value: value as Record<string, never> }, idempotencyKey })).data,
    retry: false,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: precedentKeys.settings() });
    },
  });

  if (settings.isPending) return <LoadingState what="метки по разделам" />;
  if (settings.data === undefined) {
    const failed = executionFailure(settings.error, false);
    return <ErrorState title="Настройки прецедентов не прочитаны" detail={failed.detail} correlationId={failed.correlationId} onRetry={() => void settings.refetch()} />;
  }
  const list: PrecedentSettingList = settings.data;

  async function off(section: string) {
    setFailure(null);
    try {
      await write.mutateAsync({ value: valueWithSectionOff(list, section), idempotencyKey: keys.keyFor(`off:${section}`) });
      keys.release();
    } catch (error) {
      const failed = executionFailure(error, true);
      if (failed.kind !== 'unknown_outcome') keys.release();
      setFailure(failed);
    }
  }

  return <PrecedentSectionsView sections={sectionLabelStates(list)} pending={write.isPending} failure={failure} onOff={(section) => void off(section)} />;
}
