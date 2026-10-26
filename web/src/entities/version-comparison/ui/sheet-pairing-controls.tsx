'use client';

/**
 * «Подтвердить пару» and «Отозвать» on one sheet row of a comparison
 * (`COMPARE-PERSISTED-SUMMARY-01`).
 *
 * The row is a pair of sheets the system proposed. Pressing the button opens a confirmation that
 * says exactly what is being approved; only «Подтвердить» sends the command, «Отмена» closes the
 * confirmation and nothing is written. The server recomputes the comparison when the
 * confirmation arrives and stores the approval, with who confirmed and the text of both sheets
 * as they were; an approved pair is ended by «Отозвать», which adds a record and deletes
 * nothing. A person without the expert role sees the state and no buttons.
 *
 * `SheetPairingControlsView` is the whole markup, driven by props, so every state can be
 * rendered by the static harness; `SheetPairingControls` adds the state and the commands.
 */

import { useState } from 'react';

import type { ApprovedSheetPair, SheetPairing } from '@/shared/api';
import { formatInstant } from '@/shared/lib';

import type { ApproveSheetPairingCommand } from '../api/use-sheet-pairing';
import { useApproveSheetPairing, useWithdrawSheetPairing } from '../api/use-sheet-pairing';
import type { PairingFailure } from '../model/pairing';
import { LINK_STATE_TEXT, isApprovablePair, pairingFailure } from '../model/pairing';

export interface SheetPairingControlsViewProps {
  readonly sheet: SheetPairing;
  readonly approval: ApprovedSheetPair | null;
  readonly mayDecide: boolean;
  readonly confirming: boolean;
  readonly pending: boolean;
  readonly failure: PairingFailure | null;
  readonly onOpen: () => void;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
  readonly onWithdraw: () => void;
}

function Refusal({ failure }: { readonly failure: PairingFailure | null }) {
  if (failure === null) return null;
  return (
    <p className="am-decision__refusal" role="alert" data-pairing-failure={failure.kind}>
      {failure.detail}
      {failure.correlationId === null ? null : <> Код обращения: <code>{failure.correlationId}</code>.</>}
    </p>
  );
}

export function SheetPairingControlsView({
  sheet,
  approval,
  mayDecide,
  confirming,
  pending,
  failure,
  onOpen,
  onConfirm,
  onCancel,
  onWithdraw,
}: SheetPairingControlsViewProps) {
  if (approval !== null) {
    return (
      <div data-pairing-state="approved" data-sheet-link={approval.sheet_link_id}>
        <p className="am-note" role="status">
          Пара подтверждена: {approval.approved_by_label}, {formatInstant(approval.approved_at)}.{' '}
          {LINK_STATE_TEXT[approval.state]}
        </p>
        {mayDecide ? (
          <button
            type="button"
            className="am-button am-button--small am-button--quiet"
            disabled={pending}
            onClick={onWithdraw}
          >
            {pending ? 'Отзываем…' : 'Отозвать'}
          </button>
        ) : null}
        <Refusal failure={failure} />
      </div>
    );
  }
  if (!isApprovablePair(sheet)) return <span>—</span>;
  if (!mayDecide) {
    return (
      <span className="am-note" data-pairing-state="read-only">
        Подтвердить пару может эксперт.
      </span>
    );
  }
  if (!confirming) {
    return (
      <div data-pairing-state="offered">
        <button type="button" className="am-button am-button--small" onClick={onOpen}>
          Подтвердить пару
        </button>
        <Refusal failure={failure} />
      </div>
    );
  }
  return (
    <div role="group" aria-label="Подтверждение пары листов" data-pairing-state="confirming">
      <p>
        Лист {sheet.source_page_number} более ранней версии и лист {sheet.target_page_number} более
        поздней версии.
      </p>
      <p className="am-note">
        Будет сохранено от вашего имени: какие листы вы сопоставили и какой текст они содержали.
        Различия подтверждённых пар система вычисляет заново из этого текста, без участия ИИ.
        Пару можно отозвать; запись о подтверждении при этом остаётся.
      </p>
      <button type="button" className="am-button am-button--small" disabled={pending} onClick={onConfirm}>
        {pending ? 'Сохраняем…' : 'Подтвердить'}
      </button>{' '}
      <button
        type="button"
        className="am-button am-button--small am-button--quiet"
        disabled={pending}
        onClick={onCancel}
      >
        Отмена
      </button>
      <Refusal failure={failure} />
    </div>
  );
}

/** The comparison view the commands name: the same versions, mode and runs the screen shows. */
export type PairingView = Omit<ApproveSheetPairingCommand, 'sourcePageNumber' | 'targetPageNumber' | 'suggestionSha256'>;

export interface SheetPairingControlsProps {
  readonly sheet: SheetPairing;
  readonly approval: ApprovedSheetPair | null;
  readonly mayDecide: boolean;
  readonly view: PairingView;
}

export function SheetPairingControls({ sheet, approval, mayDecide, view }: SheetPairingControlsProps) {
  const [confirming, setConfirming] = useState(false);
  const approve = useApproveSheetPairing();
  const withdraw = useWithdrawSheetPairing();
  const error = approve.isError ? approve.error : withdraw.isError ? withdraw.error : null;
  const failure = error === null ? null : pairingFailure(error);
  return (
    <SheetPairingControlsView
      sheet={sheet}
      approval={approval}
      mayDecide={mayDecide}
      confirming={confirming}
      pending={approve.isPending || withdraw.isPending}
      failure={failure}
      onOpen={() => {
        approve.reset();
        setConfirming(true);
      }}
      onCancel={() => setConfirming(false)}
      onConfirm={() => {
        if (sheet.source_page_number === null || sheet.target_page_number === null || sheet.suggestion_sha256 === null) return;
        approve.mutate(
          {
            ...view,
            sourcePageNumber: sheet.source_page_number,
            targetPageNumber: sheet.target_page_number,
            suggestionSha256: sheet.suggestion_sha256,
          },
          { onSuccess: () => setConfirming(false) },
        );
      }}
      onWithdraw={() => {
        if (approval === null) return;
        withdraw.reset();
        withdraw.mutate({ ...view, sheetLinkId: approval.sheet_link_id });
      }}
    />
  );
}
