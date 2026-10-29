'use client';

/**
 * The side panel «Изменения в листе» of the viewer (plan §1.1; `frontend/static/js/version-comparison-sheet-changes.js`).
 *
 * It reads the **stored** description of the sheet pair on open and when the reader steps to another sheet; opening it calls no
 * model. A sheet that was never described is «Не обработано» — which is not the same as no changes —, and «Описать этот лист…»
 * shows the estimate (sheets, images and their bytes, the size of the prompt, the model, the price) and the line «Подтверждаю
 * передачу этого листа исполнителю» before «Передать и описать» sends anything; the start carries the digest of that estimate.
 * «Отменить задание» stops a sheet that is queued or being described.
 *
 * **Every text the model wrote is drawn through `AiText`** and carries «не подтверждено инженером»; a recorded (test) answer says
 * that it is one and is not passed off as a description. A value whose tier is «не подтверждено» is marked so; one read from the
 * drawing says «с изображения». The description never rewrites the raw comparison of the pair beside it (`AGENTS.md` section 4).
 */

import { useState } from 'react';
import type { ReactNode } from 'react';

import type { ComparisonAiChange, ComparisonSheetDescription, ComparisonSheetDescriptionHistory, ComparisonSheetPair } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import type { ComparisonFailure, Evidence } from '@/entities/version-series';
import {
  AI_EXCLUDE_REASON_LABELS,
  AI_SHEET_STATE_LABELS,
  AI_SHEET_STATE_TONES,
  AI_TEXT_NOTE,
  AI_TIER_LABELS,
  AI_TIER_TITLES,
  AiText,
  CONFIRM_LABELS,
  EstimatePanel,
  RECORDED_LABEL,
  RECORDED_NOTE,
  comparisonFailure,
  copyText,
  descriptionHasContent,
  evidenceOf,
  useAiJobAct,
  useConsentFlow,
  useDescriptionHistory,
  useDownload,
  useSheetDescription,
  nowText,
  wasText,
} from '@/entities/version-series';
import { ErrorState, LoadingState, UnsupportedState } from '@/shared/ui';

import styles from './comparison-viewer.module.css';

export const PANEL_TITLE = 'Изменения в листе';
export const WHOLE_SPEC_NOTE = 'По полной спецификации · только изменения этого листа';
export const NOT_PROCESSED_TEXT = 'Не обработано. Для этой пары листов описания ещё нет — это не означает, что изменений нет.';
export const ENGINE_SAME_TEXT = 'По данным сравнения содержание листа не изменилось (только служебные зоны) — описание не требуется.';
export const NO_CHANGES_TEXT = 'Строительных изменений не выявлено. Что проверялось — в «Диагностике».';
export const STALE_TEXT = 'Описание устарело: сравнение листа изменилось после того, как он был описан. Переходы к чертежу могут не совпадать.';
export const PANEL_MODULE_TITLE = 'Модуль ещё недоступен';

function TierMark({ tier }: { readonly tier: ComparisonAiChange['was_tier'] }) {
  if (tier === undefined) return null;
  return (
    <span className={tier === 'unverified' ? `${styles.tier} ${styles.tierWarn}` : styles.tier} title={AI_TIER_TITLES[tier]} data-ai-tier={tier}>
      {AI_TIER_LABELS[tier]}
    </span>
  );
}

export interface ChangesPanelViewProps {
  /** The title of the sheet (from the stamp), for the passport. */
  readonly sheetTitle: string;
  readonly description: ComparisonSheetDescription | undefined;
  readonly loading: boolean;
  readonly failure: ComparisonFailure | null;
  readonly mayAct: boolean;
  readonly busy: boolean;
  readonly copied: boolean;
  readonly history: ComparisonSheetDescriptionHistory | undefined;
  /** The estimate dialog, when «Описать этот лист…» was pressed. */
  readonly estimate: ReactNode;
  readonly onDescribe: () => void;
  readonly onCancelJob: () => void;
  readonly onShow: (evidence: readonly Evidence[], id: string) => void;
  readonly onCopy: () => void;
  readonly onMd: () => void;
}

function Passport({ description, sheetTitle }: { readonly description: ComparisonSheetDescription; readonly sheetTitle: string }) {
  const changes = description.changes?.length ?? 0;
  const open = description.unresolved?.length ?? 0;
  return (
    <div className={styles.passport}>
      <strong>{sheetTitle}</strong>
      {description.source === 'whole_specification' ? <span className={styles.note}>{WHOLE_SPEC_NOTE}</span> : null}
      <span className={`am-badge am-badge--${AI_SHEET_STATE_TONES[description.state]}`} data-ai-sheet-state={description.state}>
        ● {AI_SHEET_STATE_LABELS[description.state]}
        {descriptionHasContent(description.state) && description.changes !== undefined ? ` · изменений: ${changes}` : ''}
        {open > 0 ? ` · требует уточнения: ${open}` : ''}
      </span>
      {description.recorded === true ? (
        <p className={styles.sideWarning} data-recorded-label="" title={RECORDED_NOTE}>
          {RECORDED_LABEL}
        </p>
      ) : description.model === undefined ? null : (
        <span className={styles.note}>
          Описал: {description.model}
          {description.prompt_version === undefined ? '' : `, ${description.prompt_version}`}
          {description.created_at === undefined ? '' : ` · ${formatInstant(description.created_at)}`}
        </span>
      )}
      {description.state === 'stale' ? <p className={styles.sideWarning}>{STALE_TEXT}</p> : null}
    </div>
  );
}

export function ChangesPanelView({
  sheetTitle, description, loading, failure, mayAct, busy, copied, history, estimate, onDescribe, onCancelJob, onShow, onCopy, onMd,
}: ChangesPanelViewProps) {
  if (failure !== null) {
    return (
      <aside className={styles.side} aria-label={PANEL_TITLE} data-changes-panel="failed">
        <h3 className={styles.sideTitle}>{PANEL_TITLE}</h3>
        {failure.moduleUnavailable ? (
          <div data-comparison-module="unavailable">
            <UnsupportedState title={PANEL_MODULE_TITLE} detail={failure.detail} />
          </div>
        ) : (
          <div data-comparison-failure={failure.kind}>
            <ErrorState title="Описание листа не открылось" detail={failure.detail} correlationId={failure.correlationId} />
          </div>
        )}
      </aside>
    );
  }
  if (description === undefined) {
    return (
      <aside className={styles.side} aria-label={PANEL_TITLE} data-changes-panel="loading">
        <h3 className={styles.sideTitle}>{PANEL_TITLE}</h3>
        {loading ? <LoadingState what="описание листа" /> : null}
      </aside>
    );
  }
  const evidence = evidenceOf(description);
  const changes = description.changes ?? [];
  const unresolved = description.unresolved ?? [];
  const moving = description.state === 'queued' || description.state === 'running';
  const recorded = description.recorded === true;
  return (
    <aside className={styles.side} aria-label={PANEL_TITLE} data-changes-panel={description.state} data-sheet-pair={description.sheet_pair_id}>
      <h3 className={styles.sideTitle}>{PANEL_TITLE}</h3>
      <Passport description={description} sheetTitle={sheetTitle} />
      {moving ? (
        <div className={styles.passport} role="status">
          <span className={styles.note}>{description.state === 'running' ? 'Идёт описание листа' : 'Лист в очереди'}</span>
          {mayAct && description.job_id !== undefined ? (
            <button type="button" className="am-button am-button--small am-button--quiet" disabled={busy} title="Остановить описание этого листа." onClick={onCancelJob}>
              Отменить задание
            </button>
          ) : null}
        </div>
      ) : null}
      {description.state === 'not_processed' || description.state === 'cancelled' || description.state === 'failed' ? (
        <div className={styles.passport}>
          <p className={styles.lead}>{description.state === 'not_processed' ? NOT_PROCESSED_TEXT : AI_SHEET_STATE_LABELS[description.state]}</p>
          {mayAct && estimate === null ? (
            <button type="button" className="am-button am-button--small" disabled={busy} data-describe-sheet="" title="Подготовить данные листа и показать, что будет передано ИИ. На этом шаге ничего не отправляется." onClick={onDescribe}>
              Описать этот лист…
            </button>
          ) : null}
          {mayAct ? null : <span className={styles.note}>Описание запускает эксперт.</span>}
        </div>
      ) : null}
      {estimate}
      {description.state === 'engine_same' ? <p className={styles.note}>{ENGINE_SAME_TEXT}</p> : null}
      {changes.length === 0 ? null : (
        <ol className={styles.changeList}>
          {changes.map((change) => (
            <li key={change.change_id} className={styles.change} data-ai-certainty={change.certainty}>
              <p className={styles.lead}>
                <AiText recorded={recorded}>
                  {wasText(change)}
                  {change.was === undefined ? null : <TierMark tier={change.was_tier} />}
                  {' → '}
                  {nowText(change)}
                  {change.now === undefined ? null : <TierMark tier={change.now_tier} />}
                </AiText>
              </p>
              <span>
                <strong>{change.object_name}</strong>
                {change.place === undefined || change.place === '' ? '' : ` — ${change.place}`}
              </span>
              {change.limitation === undefined || change.limitation === '' ? null : <span className={styles.note}>Неясно: {change.limitation}</span>}
              {change.box === undefined ? null : (
                <button type="button" className="am-button am-button--small am-button--quiet" data-show-on-drawing="" title="Приблизить место этого изменения на листах. Недоступно, если у пункта нет привязки к чертежу." onClick={() => onShow(evidence, change.change_id)}>
                  Показать на чертеже
                </button>
              )}
            </li>
          ))}
        </ol>
      )}
      {unresolved.length === 0 ? null : (
        <details className={styles.details} open>
          <summary>Требует уточнения ({unresolved.length})</summary>
          {unresolved.map((item, index) => (
            <div key={index} className={styles.change}>
              <AiText as="span" recorded={recorded}>{item.question}</AiText>
            </div>
          ))}
        </details>
      )}
      {description.state === 'no_construction_changes' ? <p className={styles.note}>{NO_CHANGES_TEXT}</p> : null}
      {description.changes === undefined ? null : (
        <div className={styles.sideActions}>
          <button type="button" className="am-button am-button--small am-button--quiet" title="Скопировать список изменений листа в буфер обмена." onClick={onCopy}>
            {copied ? 'Скопировано' : 'Скопировать'}
          </button>
          <button type="button" className="am-button am-button--small am-button--quiet" data-sheet-md="" title="Скачать описание изменений этого листа файлом MD." onClick={onMd}>
            MD листа
          </button>
        </div>
      )}
      {description.declared === undefined || description.declared.length === 0 ? null : (
        <details className={styles.details}>
          <summary>Заявлено проектировщиком в разрешении ({description.declared.length})</summary>
          {description.declared.map((item, index) => (
            <span key={index} className={styles.note}>
              {item.reference === undefined ? '' : `${item.reference}: `}
              {item.text}
            </span>
          ))}
        </details>
      )}
      {description.excluded === undefined || description.excluded.length === 0 ? null : (
        <details className={styles.details}>
          <summary>Не включено в сводку</summary>
          {description.excluded.map((item, index) => (
            <span key={index} className={styles.note} data-exclude-reason={item.reason}>
              {AI_EXCLUDE_REASON_LABELS[item.reason]}
              {item.text === undefined || item.text === '' ? '' : ` — ${item.text}`}
            </span>
          ))}
        </details>
      )}
      {description.diagnostics === undefined && description.coverage === undefined ? null : (
        <details className={styles.details}>
          <summary>Диагностика</summary>
          {description.coverage === undefined ? null : (
            <span className={styles.note}>
              Кандидатов {description.coverage.candidates}: в изменениях {description.coverage.in_changes}, не рассмотрено {description.coverage.not_reviewed}.
            </span>
          )}
          {description.diagnostics === undefined ? null : (
            <span className={styles.note}>
              Исключено программой: {description.diagnostics.excluded_by_program}; проверок не прошло: {description.diagnostics.issues.length}.
            </span>
          )}
        </details>
      )}
      {description.history_count > 1 ? (
        <details className={styles.details}>
          <summary>История ({description.history_count})</summary>
          {(history?.items ?? []).map((item) => (
            <span key={item.description_id} className={styles.note} data-ai-sheet-state={item.state}>
              {formatInstant(item.created_at)} · {AI_SHEET_STATE_LABELS[item.state]} · изменений {item.changes_count}
              {item.unresolved_count > 0 ? `, уточнений ${item.unresolved_count}` : ''}
              {item.recorded ? ` · ${RECORDED_LABEL}` : item.model === undefined ? '' : ` · ${item.model}`}
            </span>
          ))}
        </details>
      ) : null}
      <p className={styles.note}>{AI_TEXT_NOTE}</p>
    </aside>
  );
}

export interface ChangesPanelProps {
  readonly pair: ComparisonSheetPair;
  readonly mayAct: boolean;
  readonly onShow: (evidence: readonly Evidence[], id: string) => void;
}

export function sheetTitleOf(pair: ComparisonSheetPair): string {
  const page = pair.page_b ?? pair.page_a;
  if (page === undefined) return 'Лист';
  const number = page.sheet_number === undefined ? `стр. ${page.page.page_number}` : `л. ${page.sheet_number}`;
  return `${number}${page.title === undefined ? '' : ` · ${page.title}`}`;
}

export function ChangesPanel({ pair, mayAct, onShow }: ChangesPanelProps) {
  const description = useSheetDescription(pair.sheet_pair_id);
  const history = useDescriptionHistory(pair.sheet_pair_id, (description.data?.history_count ?? 0) > 1);
  const act = useAiJobAct();
  const download = useDownload();
  const [estimating, setEstimating] = useState(false);
  const [copied, setCopied] = useState(false);
  const error = description.error ?? act.error ?? download.error ?? null;
  const flow = useConsentFlow(estimating ? { kind: 'sheet', pairId: pair.sheet_pair_id } : null, {
    onStarted: () => setEstimating(false),
  });
  const data = description.data;
  return (
    <ChangesPanelView
      sheetTitle={sheetTitleOf(pair)}
      description={data}
      loading={description.isPending}
      failure={description.isError ? comparisonFailure(description.error) : error === null ? null : comparisonFailure(error)}
      mayAct={mayAct}
      busy={act.isPending || download.isPending}
      copied={copied}
      history={history.data}
      estimate={
        estimating ? (
          <EstimatePanel
            title="Описать этот лист"
            consentKind="sheet"
            confirmLabel={CONFIRM_LABELS.sheet}
            estimate={flow.estimate}
            loading={flow.loading}
            failure={flow.failure}
            agreedDigest={flow.agreedDigest}
            busy={flow.busy}
            onAgree={flow.agree}
            onConfirm={flow.confirm}
            onCancel={() => setEstimating(false)}
          />
        ) : null
      }
      onDescribe={() => setEstimating(true)}
      onCancelJob={() => {
        if (data?.job_id !== undefined) act.mutate({ method: 'sheet_changes', act: 'cancel', jobId: data.job_id });
      }}
      onShow={onShow}
      onCopy={() => {
        if (data === undefined) return;
        void navigator.clipboard?.writeText(copyText(sheetTitleOf(pair), data)).then(() => setCopied(true));
      }}
      onMd={() => download.mutate({ kind: 'sheet-md', pairId: pair.sheet_pair_id, fileName: 'izmeneniya-lista.md' })}
    />
  );
}

