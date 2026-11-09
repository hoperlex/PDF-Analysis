'use client';

/**
 * The one dialog of a start that can charge money (`RUN-START-ONE-01a`, plan v3 §8): the estimate, the
 * ceiling, «Запустить» and «Отмена». «Запустить» is the agreement; there is no second tick-box.
 *
 * It says what `CostApproval` says, in the same words but for two: the money is written «$1.2», as the batch
 * panel writes it, and the recorded mode is «Тестовый режим» (a Latin word does not reach a reader, `R-18`). It
 * takes its figures through the same helpers (`microsAsUsd`, `ceilingMicros`). The 1.44.0 estimate holds one model and one total, so it shows the
 * model and the total; a per-model list belongs to the estimate that carries lines (plan v3 wave 2).
 *
 * `StartRunCostDialogView` is the markup; `StartRunCostDialog` opens it as a native modal `<dialog>`
 * (the browser keeps the focus inside, Esc is «Отмена», the page behind is inert), as the other windows
 * of this application do. Where `showModal` is missing, or the harness asks for `staticOpen`, it is drawn
 * open as it is.
 */

import { useEffect, useId, useRef } from 'react';
import type { ReactNode, Ref } from 'react';

import type { RunCostEstimate } from '@/shared/api';
import { ceilingMicros, microsAsUsd } from '@/shared/ui';

import { ceilingFloor, chargesMoney } from '../model/one-click-start';
import styles from './start-run-control.module.css';

/** What «Без денежного потолка (сбор статистики)» means, in the words the temporary mode always had. */
export const UNCAPPED_MEANING = 'Прикладной денежный потолок отключён; фактические вызовы и расход записываются.';

export interface StartRunCostDialogViewProps {
  readonly estimate: RunCostEstimate;
  /** The start is «Без денежного потолка (сбор статистики)»: there is no ceiling to type. */
  readonly relaxed: boolean;
  readonly ceiling: string;
  /** The server said the estimate or its binding changed; this is the new one. */
  readonly changed: boolean;
  /** A send is in flight. */
  readonly busy: boolean;
  readonly onCeilingChange: (value: string) => void;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
  /**
   * What the start is about, when the dialog is not opened from the start control (`RUN-START-ONE-01b`: the queue names the
   * run it repeats). One line under the title; absent, nothing is drawn and the start control looks as it did.
   */
  readonly subject?: ReactNode | undefined;
  /** The census and the unit suite: drawn open without `showModal`. */
  readonly staticOpen?: boolean | undefined;
  /** Wires the native `<dialog>`; a static render passes none. */
  readonly dialogRef?: Ref<HTMLDialogElement> | undefined;
}

export function StartRunCostDialogView({
  estimate, relaxed, ceiling, changed, busy, onCeilingChange, onConfirm, onCancel, subject, staticOpen = false, dialogRef,
}: StartRunCostDialogViewProps) {
  const titleId = useId();
  const sufficient = relaxed || ceilingMicros(ceiling, ceilingFloor(estimate)) !== null;
  return (
    <dialog
      ref={dialogRef}
      className={styles.dialog}
      aria-labelledby={titleId}
      open={staticOpen ? true : undefined}
      data-start-run-dialog=""
    >
      <h3 id={titleId} className={styles.dialogTitle}>Стоимость перед запуском</h3>
      {subject === undefined || subject === null ? null : <p data-start-run-subject="">{subject}</p>}
      {changed ? (
        <p role="status" data-start-run-changed="">Оценка изменилась с прошлого раза. Проверьте новую оценку и запустите снова.</p>
      ) : null}
      <p>
        {chargesMoney(estimate)
          ? `Предварительная оценка: $${microsAsUsd(estimate.estimated_cost_micros)}.`
          : 'Подключение без тарификации в приложении. Денежная оценка не отражает внешний счёт провайдера.'}
      </p>
      {estimate.provider_mode === 'recorded' ? (
        <p className="am-note">Тестовый режим: сохранённые ответы. Оценка не является фактическим расходом.</p>
      ) : null}
      <p>
        Модель: {estimate.model_id}. Страниц: {estimate.page_count}; символов: {estimate.text_characters}; окон: {estimate.windows};{' '}
        {relaxed ? 'начальная оценка вызовов' : 'вызовов'}: {estimate.calls}.
      </p>
      <p>Оценка входных токенов: {estimate.input_tokens}.</p>
      {relaxed ? (
        <p className="am-note">
          {UNCAPPED_MEANING} Подтверждение разрешает фактические расходы без предела приложения.
        </p>
      ) : (
        <>
          <label className={styles.dialogField}>Лимит стоимости, $
            <input
              type="text"
              inputMode="decimal"
              maxLength={24}
              value={ceiling}
              disabled={busy}
              aria-invalid={!sufficient}
              onChange={(event) => onCeilingChange(event.currentTarget.value)}
            />
          </label>
          <p className="am-note">
            Рекомендуемый лимит: ${microsAsUsd(estimate.recommended_ceiling_micros)}. Лимит должен покрывать оценку;
            окончательный расход зависит от ответа провайдера.
          </p>
        </>
      )}
      {sufficient ? null : (
        <p role="alert">
          Введите конечный лимит не ниже оценки, до шести знаков после запятой. Для тарифицируемого подключения лимит должен быть положительным.
        </p>
      )}
      <div className={styles.dialogActions}>
        <button type="button" className="am-button" data-start-run-confirm="" disabled={busy || !sufficient} onClick={onConfirm}>
          Запустить
        </button>
        <button type="button" className="am-button am-button--quiet" data-start-run-cancel="" disabled={busy} onClick={onCancel}>
          Отмена
        </button>
      </div>
    </dialog>
  );
}

export type StartRunCostDialogProps = Omit<StartRunCostDialogViewProps, 'staticOpen' | 'dialogRef'>;

/** The connected dialog: opens as a modal when it mounts, and Esc is «Отмена» unless a send is in flight. */
export function StartRunCostDialog(props: StartRunCostDialogProps) {
  const element = useRef<HTMLDialogElement | null>(null);
  const cancelRef = useRef(props.onCancel);
  cancelRef.current = props.onCancel;
  const busyRef = useRef(props.busy);
  busyRef.current = props.busy;

  useEffect(() => {
    const dialog = element.current;
    if (dialog === null || typeof dialog.showModal !== 'function') return;
    if (!dialog.open) dialog.showModal();
    const cancelled = (event: Event) => {
      // Esc: «Отмена», and never while the start is on its way.
      event.preventDefault();
      if (!busyRef.current) cancelRef.current();
    };
    dialog.addEventListener('cancel', cancelled);
    return () => {
      dialog.removeEventListener('cancel', cancelled);
      if (dialog.open) dialog.close();
    };
  }, []);

  return <StartRunCostDialogView {...props} dialogRef={element} />;
}
