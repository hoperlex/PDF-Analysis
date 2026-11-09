'use client';

/**
 * «Отозвать» and «Вернуть» on one memory case (`D-495`): the administrator's two buttons and the closed reason the operation
 * requires. A case that is in force offers «Отозвать», a withdrawn one «Вернуть», a forgotten one nothing (it accepts no further
 * event, and a control that could only be refused is not drawn).
 *
 * The reason is a closed list, not free text: the status event is append-only and kept for ever, and a free field would put
 * personal data into it. «Отозвать» is reversible by «Вернуть», so neither asks for a confirmation; the button is pressable once a
 * reason is chosen.
 */

import { useState } from 'react';

import type { DecisionMemoryCaseId } from '@/shared/api';
import { failureMessage } from '@/shared/api';
import { useIntentKey } from '@/shared/lib';
import { ErrorState } from '@/shared/ui';
import { MEMORY_REASON_CODES, MEMORY_REASON_LABELS } from '@/entities/decision-memory';
import type { MemoryReason, MemoryStatus } from '@/entities/decision-memory';

import { standingIntentSignature } from '../model/intent';
import type { StandingKind } from '../model/use-change-standing';
import { useChangeStanding } from '../model/use-change-standing';
import styles from './case-standing-control.module.css';

const BUTTON_LABELS: Readonly<Record<StandingKind, string>> = { withdraw: 'Отозвать', restore: 'Вернуть' };

const SUCCESS_NOTES: Readonly<Record<StandingKind, string>> = {
  withdraw: 'Дело отозвано: оно больше не попадёт в подсказки, запросы и выгрузки.',
  restore: 'Дело возвращено в силу.',
};

/** The sentences of the two refusals this screen can say more precisely about. */
const STANDING_WORDING = {
  state_transition_not_allowed: 'Состояние дела уже изменено: обновите страницу. Ничего не изменено.',
  conflict: 'Дело забыто: его состояние больше не меняется. Ничего не изменено.',
} as const;

export interface CaseStandingControlProps {
  readonly caseId: DecisionMemoryCaseId;
  readonly status: MemoryStatus;
}

export function CaseStandingControl({ caseId, status }: CaseStandingControlProps) {
  const [reason, setReason] = useState<MemoryReason | ''>('');
  const change = useChangeStanding();
  const kind: StandingKind = status === 'withdrawn' ? 'restore' : 'withdraw';
  const idempotencyKey = useIntentKey(standingIntentSignature(kind, caseId, reason));

  if (status === 'forgotten') return null;

  const failure = change.isError ? failureMessage(change.error, STANDING_WORDING) : null;
  const fieldId = `memory-standing-reason-${caseId}`;

  function submit() {
    if (reason === '' || change.isPending) return;
    change.mutate({ kind, caseId, reason, idempotencyKey }, { onSuccess: () => setReason('') });
  }

  return (
    <div className={styles.control} data-memory-standing-control={kind}>
      <div className={styles.row}>
        <label htmlFor={fieldId}>Причина</label>
        <select
          id={fieldId}
          value={reason}
          onChange={(event) => { setReason(event.target.value as MemoryReason | ''); change.reset(); }}
        >
          <option value="">Выберите причину</option>
          {MEMORY_REASON_CODES.map((code) => (
            <option key={code} value={code}>{MEMORY_REASON_LABELS[code]}</option>
          ))}
        </select>
        <button type="button" className="am-button am-button--small" disabled={reason === '' || change.isPending} onClick={submit}>
          {BUTTON_LABELS[kind]}
        </button>
      </div>
      {failure === null ? null : (
        <div data-memory-standing-failure={failure.kind}>
          <ErrorState title="Состояние дела не изменено" detail={failure.detail} correlationId={failure.correlationId} />
        </div>
      )}
      {change.isSuccess && failure === null ? (
        <p className="am-note" role="status">{SUCCESS_NOTES[change.data.kind]}</p>
      ) : null}
    </div>
  );
}
