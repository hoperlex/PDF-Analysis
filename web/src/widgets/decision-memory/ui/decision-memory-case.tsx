'use client';

/**
 * One memory case (`D-495`, `getDecisionMemoryCase`): what the expert saw and said when the decision was taken -- the model's
 * finding and recommendation as they stood, the evidence quotes with their place, the certified norms the finding rested on, the
 * crop images it references, every captured decision with the expert's own words, and the history of the case's standing.
 *
 * **Crops are text here.** The response describes a crop (its page, box, size and digest) and gives no way to fetch its bytes --
 * that is phase M3 -- so this view does not request or draw an image, and says so once.
 *
 * **A forgotten case shows its tombstone only**: `content` is `null`, the lists are empty and no decision carries a comment; the
 * `forget` event holds the digest of what was forgotten. Nothing is drawn in place of the missing words.
 *
 * It draws what the server sent, in the order it sent it, and derives nothing. «Отозвать» and «Вернуть» are the administrator's
 * (`manage`); for an expert the case is read-only.
 */

import type { ReactNode } from 'react';

import type { DecisionMemoryCase, DecisionMemoryCrop, DecisionMemoryEvidence, DecisionMemoryNormRef } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import type { ErrorStateProps } from '@/shared/ui';
import { ErrorState, LoadingState, PROVIDER_MODE_LABELS, STAGE_LABELS } from '@/shared/ui';
import {
  MEMORY_CROP_STATE_LABELS,
  MEMORY_DATA_CLASS_LABELS,
  MEMORY_ORIGIN_KIND_LABELS,
  MEMORY_REASON_LABELS,
  MEMORY_STATUS_EVENT_LABELS,
  MEMORY_VERDICT_LABELS,
} from '@/entities/decision-memory';
import { SeverityBadge, normCitationStateLabel } from '@/entities/finding';
import { CaseStandingControl } from '@/features/manage-decision-memory';

import { formatBox, shortDigest, sizeLabel } from '../model/format';
import { MemoryStatusBadge } from './status-badge';
import { MemorySectionCell, memoryCategoryLabel } from './decision-memory-list';
import styles from './decision-memory.module.css';

export interface DecisionMemoryCaseViewProps {
  readonly data: DecisionMemoryCase | undefined;
  readonly isLoading: boolean;
  readonly error: ErrorStateProps | null;
  /** The account may withdraw and restore (`admin`). */
  readonly manage: boolean;
  readonly onBack: () => void;
}

function Section({ title, count, children }: { readonly title: string; readonly count?: number | undefined; readonly children: ReactNode }) {
  return (
    <section className={styles.section}>
      <h3 className={styles.sectionTitle}>
        {title}
        {count === undefined ? null : <span className={styles.sectionCount}> · {count}</span>}
      </h3>
      {children}
    </section>
  );
}

function stageLabel(stageId: string): string {
  return (STAGE_LABELS as Readonly<Record<string, string | undefined>>)[stageId] ?? stageId;
}

function EvidenceItem({ item }: { readonly item: DecisionMemoryEvidence }) {
  const box = item.bbox === null ? null : formatBox(item.bbox);
  const frame = [item.bbox_unit, item.bbox_origin].filter((part): part is string => part !== null).join(', ');
  return (
    <li data-memory-evidence={item.ordinal}>
      <p className={styles.itemMeta}>
        №{item.ordinal + 1} · стр. {item.page_number} · символы {item.char_start}–{item.char_end}
        {item.block_ref === null ? null : <> · блок <code>{item.block_ref}</code></>}
        {box === null ? null : <> · рамка {box}{frame === '' ? '' : ` (${frame})`}</>}
      </p>
      <blockquote className={styles.quote}>{item.quote}</blockquote>
    </li>
  );
}

function NormItem({ item }: { readonly item: DecisionMemoryNormRef }) {
  return (
    <li data-memory-norm={item.ordinal}>
      <p className={styles.itemMeta}>
        <strong>{item.designation}</strong>
        {item.clause_number === null ? null : ` · п. ${item.clause_number}`} · стр. {item.page_label} · {normCitationStateLabel(item.citation_state)}
      </p>
      <blockquote className={styles.quote}>{item.quote}</blockquote>
    </li>
  );
}

function CropItem({ item }: { readonly item: DecisionMemoryCrop }) {
  return (
    <li data-memory-crop={item.crop_id}>
      <p className={styles.itemMeta}>
        Кадр {item.crop_ordinal} · стр. {item.page_number} · рамка {formatBox(item.bbox)} · {item.width_px}×{item.height_px} пикс. ·{' '}
        {sizeLabel(item.size_bytes)}
        {item.evidence_ordinal === null ? null : ` · к подтверждению №${item.evidence_ordinal + 1}`}
        {' · отпечаток '}
        <code title={item.sha256}>{shortDigest(item.sha256)}</code>
      </p>
      {item.portal_description === null ? null : <p className={styles.text}>{item.portal_description}</p>}
    </li>
  );
}

export function DecisionMemoryCaseView({ data, isLoading, error, manage, onBack }: DecisionMemoryCaseViewProps) {
  const back = (
    <button type="button" className="am-button am-button--quiet am-button--small" data-memory-back="" onClick={onBack}>
      ← К списку дел
    </button>
  );
  if (error !== null) return <div className={styles.case}>{back}<ErrorState {...error} /></div>;
  if (isLoading || data === undefined) return <div className={styles.case}>{back}<LoadingState what="дело" /></div>;

  const { summary, content, decisions, evidence, norm_refs: norms, crops, status_events: events } = data;
  return (
    <article className={styles.case} data-memory-case-view={summary.case_id} data-memory-status={summary.status}>
      <header className={styles.caseHead}>
        {back}
        <h2 className={styles.caseTitle}>{memoryCategoryLabel(summary.category)}</h2>
        <MemoryStatusBadge status={summary.status} />
      </header>
      <dl className={styles.facts}>
        <div><dt>Раздел</dt><dd><MemorySectionCell code={summary.section_code} /></dd></div>
        <div><dt>Записано</dt><dd><time dateTime={summary.captured_at}>{formatInstant(summary.captured_at)}</time></dd></div>
        <div><dt>Данные</dt><dd>{MEMORY_DATA_CLASS_LABELS[summary.data_class]}</dd></div>
        <div><dt>Проект</dt><dd><code data-memory-origin-project={summary.origin_project_uid}>{summary.origin_project_uid}</code></dd></div>
        <div><dt>Кадры</dt><dd>{MEMORY_CROP_STATE_LABELS[summary.crop_state]}</dd></div>
        <div><dt>Дело</dt><dd><code>{summary.case_id}</code></dd></div>
      </dl>
      {summary.status === 'active' ? null : (
        <p className="am-note" data-memory-standing-note={summary.status}>
          {summary.status === 'forgotten'
            ? 'Содержимое дела забыто: остались решения без слов эксперта и запись о забвении.'
            : 'Дело отозвано: оно не попадает в подсказки, запросы и выгрузки, но остаётся в памяти.'}
          {summary.status_reason_code === null ? null : ` Причина: ${MEMORY_REASON_LABELS[summary.status_reason_code].toLowerCase()}.`}
          {summary.status_changed_at === null ? null : ` ${formatInstant(summary.status_changed_at)}.`}
        </p>
      )}
      {manage ? <CaseStandingControl caseId={summary.case_id} status={summary.status} /> : null}
      <div className={styles.columns}>
        <div className={styles.column}>
          {content === null ? null : (
            <Section title="Находка и рекомендация">
              <p className={styles.text} data-memory-finding-text="">{content.finding_text}</p>
              <p className={styles.text} data-memory-recommendation-text="">{content.recommendation_text}</p>
              <p className={styles.itemMeta}>
                {content.proposed_severity === null ? null : (
                  <span className={styles.inlineEnd}><SeverityBadge severity={content.proposed_severity} title="Важность, предложенная моделью" /></span>
                )}
                {content.required_value === null && content.stated_value === null ? null : (
                  <>
                    {content.required_value === null ? null : <>требуется: {content.required_value} · </>}
                    {content.stated_value === null ? null : <>указано: {content.stated_value} · </>}
                  </>
                )}
                этап: {stageLabel(content.stage_id)} · профиль <code>{content.analysis_profile_id}</code> · {PROVIDER_MODE_LABELS[content.provider_mode]}
              </p>
            </Section>
          )}
          <Section title="Решения" count={decisions.length}>
            <ol className={styles.items} data-memory-decisions="">
              {decisions.map((decision) => (
                <li key={decision.memory_decision_id} data-memory-decision={decision.memory_decision_id} data-memory-verdict={decision.verdict}>
                  <p className={styles.itemMeta}>
                    <span className="am-kb__verdict" data-verdict={decision.verdict}>{MEMORY_VERDICT_LABELS[decision.verdict]}</span>
                    {decision.severity === null ? null : (
                      <span className={styles.inline}><SeverityBadge severity={decision.severity} title="Важность, решённая экспертом" /></span>
                    )}{' '}
                    · {MEMORY_ORIGIN_KIND_LABELS[decision.origin_kind]} · <time dateTime={decision.decided_at}>{formatInstant(decision.decided_at)}</time>
                  </p>
                  {decision.comment === null ? null : <blockquote className={styles.quote}>{decision.comment}</blockquote>}
                </li>
              ))}
            </ol>
          </Section>
          <Section title="История состояния" count={events.length}>
            {events.length === 0 ? <p className={styles.muted}>Состояние не менялось.</p> : (
              <ol className={styles.items} data-memory-status-events="">
                {events.map((event) => (
                  <li key={event.status_event_id} data-memory-status-event={event.status_event_id} data-memory-event-kind={event.kind}>
                    <p className={styles.itemMeta}>
                      <strong>{MEMORY_STATUS_EVENT_LABELS[event.kind]}</strong> · {MEMORY_REASON_LABELS[event.reason_code].toLowerCase()} ·{' '}
                      <time dateTime={event.created_at}>{formatInstant(event.created_at)}</time>
                      {event.forgotten_content_sha256 === null ? null : (
                        <> · отпечаток забытого <code title={event.forgotten_content_sha256}>{shortDigest(event.forgotten_content_sha256, 16)}</code></>
                      )}
                    </p>
                  </li>
                ))}
              </ol>
            )}
          </Section>
        </div>
        <div className={styles.column}>
          <Section title="Подтверждения" count={evidence.length}>
            {evidence.length === 0 ? <p className={styles.muted}>Цитат нет.</p> : (
              <ol className={styles.items} data-memory-evidence-list="">
                {evidence.map((item) => <EvidenceItem key={item.ordinal} item={item} />)}
              </ol>
            )}
          </Section>
          <Section title="Нормы" count={norms.length}>
            {norms.length === 0 ? <p className={styles.muted}>Нормативных ссылок нет.</p> : (
              <ol className={styles.items} data-memory-norm-list="">
                {norms.map((item) => <NormItem key={item.ordinal} item={item} />)}
              </ol>
            )}
          </Section>
          <Section title="Кадры" count={crops.length}>
            {crops.length === 0 ? <p className={styles.muted}>Кадров нет.</p> : (
              <>
                <ol className={styles.items} data-memory-crop-list="">
                  {crops.map((item) => <CropItem key={item.crop_id} item={item} />)}
                </ol>
                <p className={styles.muted} data-memory-crops-text-only="">Изображения кадров пока не открываются: здесь только их описание.</p>
              </>
            )}
          </Section>
        </div>
      </div>
    </article>
  );
}
