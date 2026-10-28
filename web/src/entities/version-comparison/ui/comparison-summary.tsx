'use client';

/**
 * The summary of the approved pairs, beside their raw differences (`COMPARE-PERSISTED-SUMMARY-01`, B2).
 *
 * What a reviewer reads, in order: the server's label («Сводка подготовлена моделью, проверка
 * человеком не проводилась»), whether the text is a replayed recording, whether it still describes
 * the approved set as it stands, and each statement with the sheets and changes it cites. A
 * rejected reply is shown as what it is: an answer the check refused, with the reason, and no text.
 * The button asks the model once, on purpose, after a confirmation that says what is sent.
 *
 * `ComparisonSummaryView` is the whole markup, driven by props; `ComparisonSummarySection` adds the
 * state and the command.
 */

import { useState } from 'react';

import type { ApprovedSheetPairs, ComparisonSummary } from '@/shared/api';
import { formatInstant } from '@/shared/lib';

import type { GenerateComparisonSummaryCommand } from '../api/use-comparison-summary';
import { useGenerateComparisonSummary } from '../api/use-comparison-summary';
import type { SummaryFailure } from '../model/summary';
import {
  RECORDED_MODE_TEXT,
  SUMMARY_NOT_CURRENT_TEXT,
  SUMMARY_NOT_SEALED_TEXT,
  SUMMARY_REJECTION_TEXT,
  canOfferSummary,
  citationText,
  summaryFailure,
} from '../model/summary';

export interface ComparisonSummaryViewProps {
  readonly approved: ApprovedSheetPairs;
  readonly mayDecide: boolean;
  readonly confirming: boolean;
  readonly pending: boolean;
  readonly failure: SummaryFailure | null;
  readonly onOpen: () => void;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
}

function Stored({ summary, approved }: { readonly summary: ComparisonSummary; readonly approved: ApprovedSheetPairs }) {
  return (
    <div data-summary-state={summary.state} data-summary-current={summary.is_current ? 'yes' : 'no'}>
      <p className="am-note" role="note" data-summary-label="">{summary.label}</p>
      {summary.provider_mode === 'recorded' ? <p className="am-note">{RECORDED_MODE_TEXT}</p> : null}
      {summary.is_current ? null : <p className="am-note" role="status">{SUMMARY_NOT_CURRENT_TEXT}</p>}
      {summary.state === 'rejected' ? (
        <p role="status" data-summary-rejection={summary.rejection_reason ?? ''}>
          {summary.rejection_reason === null ? 'Ответ модели отклонён проверкой.' : SUMMARY_REJECTION_TEXT[summary.rejection_reason]}{' '}
          Различия подтверждённых пар не изменены.
        </p>
      ) : (
        <ol>
          {summary.statements.map((statement, index) => (
            <li key={index} data-summary-statement={index}>
              <p>{statement.text}</p>
              <p className="am-note">Относится к: {citationText(approved, statement)}.</p>
            </li>
          ))}
        </ol>
      )}
      <p className="am-note">
        Подготовил запрос: {summary.created_by_label}, {formatInstant(summary.created_at)}.
      </p>
    </div>
  );
}

export function ComparisonSummaryView({
  approved,
  mayDecide,
  confirming,
  pending,
  failure,
  onOpen,
  onConfirm,
  onCancel,
}: ComparisonSummaryViewProps) {
  const summary = approved.summary ?? null;
  const offer = canOfferSummary(mayDecide, approved);
  return (
    <section data-comparison-summary={summary === null ? 'none' : summary.state}>
      <h3>Сводка по подтверждённым парам</h3>
      {summary === null ? (
        <p className="am-note">Сводка ещё не подготовлена.</p>
      ) : (
        <Stored summary={summary} approved={approved} />
      )}
      {!offer ? (
        approved.evidence_state === 'sealed' || approved.items.length === 0 ? null : (
          <p className="am-note" data-summary-offer="blocked">{SUMMARY_NOT_SEALED_TEXT}</p>
        )
      ) : confirming ? (
        <div role="group" aria-label="Подтверждение запроса сводки" data-summary-offer="confirming">
          <p className="am-note">
            Будет сделан один запрос к модели по изменившимся строкам подтверждённых пар. Сводка не
            заменяет и не меняет различия; проверка человеком не проводится. Повторный запрос по
            тем же строкам вернёт уже сохранённую сводку.
          </p>
          <button type="button" className="am-button am-button--small" disabled={pending} onClick={onConfirm}>
            {pending ? 'Готовим…' : 'Подготовить'}
          </button>{' '}
          <button
            type="button"
            className="am-button am-button--small am-button--quiet"
            disabled={pending}
            onClick={onCancel}
          >
            Отмена
          </button>
        </div>
      ) : (
        <div data-summary-offer="offered">
          <button type="button" className="am-button am-button--small" onClick={onOpen}>
            {summary === null ? 'Подготовить сводку' : 'Подготовить сводку заново'}
          </button>
        </div>
      )}
      {failure === null ? null : (
        <p className="am-decision__refusal" role="alert" data-summary-failure={failure.kind}>
          {failure.detail}
          {failure.correlationId === null ? null : <> Код обращения: <code>{failure.correlationId}</code>.</>}
        </p>
      )}
    </section>
  );
}

export type SummaryView = Omit<GenerateComparisonSummaryCommand, 'linkRevision' | 'sealSha256'>;

export function ComparisonSummarySection({
  approved,
  mayDecide,
  view,
}: {
  readonly approved: ApprovedSheetPairs;
  readonly mayDecide: boolean;
  readonly view: SummaryView;
}) {
  const [confirming, setConfirming] = useState(false);
  const generate = useGenerateComparisonSummary();
  const failure = generate.isError ? summaryFailure(generate.error) : null;
  return (
    <ComparisonSummaryView
      approved={approved}
      mayDecide={mayDecide}
      confirming={confirming}
      pending={generate.isPending}
      failure={failure}
      onOpen={() => {
        generate.reset();
        setConfirming(true);
      }}
      onCancel={() => setConfirming(false)}
      onConfirm={() => {
        if (approved.link_revision === null || approved.raw_evidence_seal_sha256 === null) return;
        generate.mutate(
          { ...view, linkRevision: approved.link_revision, sealSha256: approved.raw_evidence_seal_sha256 },
          { onSuccess: () => setConfirming(false) },
        );
      }}
    />
  );
}
