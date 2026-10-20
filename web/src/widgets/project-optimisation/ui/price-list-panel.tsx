'use client';

/**
 * «Прайс-листы проекта» (`W60-PRICE-LIST-01`): the upload, every stored revision, and one
 * revision's positions with the report of how its file was read.
 *
 * The newest revision is current and is shown first; every earlier one stays readable. A
 * position's price is shown exactly as stored, with the currency the price list stated: no
 * total, no conversion and no price that is not in the file. Each skipped row is listed with
 * its reason, so the expert can correct the file and upload it again.
 */

import { useState } from 'react';

import type { PriceListPositionPage, PriceListRevision, ProjectUid } from '@/shared/api';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { formatInstant } from '@/shared/lib';
import { failureMessage } from '@/shared/api/failure-message';
import { findProjectSection } from '@/entities/project';
import {
  CURRENCY_SOURCE_LABELS,
  FIELD_LABELS,
  FORMAT_LABELS,
  ROW_REASON_LABELS,
  formatPrice,
  sourceDescription,
  usePriceListPositions,
  usePriceListRevisions,
} from '@/entities/price-list';
import { UploadPriceListForm } from '@/features/upload-price-list';

import styles from './project-optimisation.module.css';

export interface PriceListRevisionsViewProps {
  readonly revisions: readonly PriceListRevision[];
  readonly selectedId: string | null;
  readonly onSelect: (priceListId: string) => void;
}

/** Every revision, newest first; the current one is marked. */
export function PriceListRevisionsView({ revisions, selectedId, onSelect }: PriceListRevisionsViewProps) {
  return (
    <div className={styles.frame}>
      <table className={styles.table} data-price-list-revisions="">
        <thead>
          <tr>
            <th className={styles.cell}>Редакция</th>
            <th className={styles.cell}>Загружена</th>
            <th className={styles.cell}>Файл</th>
            <th className={styles.cell}>Позиции</th>
            <th className={styles.cell}>Пропущено строк</th>
            <th className={styles.cell} />
          </tr>
        </thead>
        <tbody>
          {revisions.map((revision) => (
            <tr key={revision.price_list_id} data-price-list={revision.price_list_id}>
              <td className={`${styles.cell} ${revision.is_current ? styles.current : ''}`}>
                {revision.revision_number}
                {revision.is_current ? ' (текущая)' : ''}
              </td>
              <td className={styles.cell}>{formatInstant(revision.uploaded_at)}</td>
              <td className={styles.cell}>
                {revision.source_filename} · {FORMAT_LABELS[revision.source_format]}
              </td>
              <td className={styles.cell}>{revision.accepted_row_count}</td>
              <td className={styles.cell}>{revision.skipped_row_count}</td>
              <td className={styles.cell}>
                {revision.price_list_id === selectedId ? (
                  'показана'
                ) : (
                  <button
                    type="button"
                    className="am-button am-button--quiet am-button--small"
                    onClick={() => onSelect(revision.price_list_id)}
                  >
                    Показать позиции
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function sectionLabel(code: string | null): string {
  if (code === null) return '—';
  const section = findProjectSection(code);
  return section === null ? code : section.abbr;
}

export interface PriceListPositionsViewProps {
  readonly page: PriceListPositionPage;
  readonly onOffset: (offset: number) => void;
}

/** One page of positions and the report of how the file was read. */
export function PriceListPositionsView({ page, onOffset }: PriceListPositionsViewProps) {
  const report = page.parse_report;
  const previous = page.offset === 0 ? null : Math.max(0, page.offset - page.limit);
  return (
    <div data-price-list-positions={page.revision.price_list_id}>
      <h4>Как прочитан файл</h4>
      <dl className={styles.report}>
        <dt>Источник</dt>
        <dd>{sourceDescription(report)}</dd>
        <dt>Столбцы</dt>
        <dd>
          {report.columns
            .map((column) => `${FIELD_LABELS[column.field]} — «${column.header}» (столбец ${column.column})`)
            .join('; ')}
        </dd>
        {report.ambiguous_columns.length > 0 ? (
          <>
            <dt>Не прочитаны, потому что неоднозначны</dt>
            <dd>
              {report.ambiguous_columns
                .map((item) => `${FIELD_LABELS[item.field]}: ${item.headers.map((h) => `«${h}»`).join(', ')}`)
                .join('; ')}
            </dd>
          </>
        ) : null}
        {report.ignored_columns.length > 0 ? (
          <>
            <dt>Не использованы</dt>
            <dd>{report.ignored_columns.map((header) => `«${header}»`).join(', ')}</dd>
          </>
        ) : null}
        <dt>Строки</dt>
        <dd>
          строк данных — {report.data_rows}, принято — {report.accepted_rows}, пропущено —{' '}
          {report.skipped_rows}
        </dd>
        <dt>Валюта</dt>
        <dd>
          {report.currency_sources
            .map((item) => `${CURRENCY_SOURCE_LABELS[item.source]} — ${item.count}`)
            .join('; ')}
        </dd>
        {report.skipped_by_reason.length > 0 ? (
          <>
            <dt>Пропущенные строки</dt>
            <dd>
              {report.skipped_by_reason
                .map((item) => `${ROW_REASON_LABELS[item.reason]} — ${item.count}`)
                .join('; ')}
              <ul className={styles.entries}>
                {report.skipped.map((note) => (
                  <li key={`skip-${note.row}`} data-skipped-row={note.row}>
                    строка {note.row}: {ROW_REASON_LABELS[note.reason]}
                  </li>
                ))}
              </ul>
              {report.skipped_listed_in_full ? null : (
                <p className="am-note">Перечислены первые 1000 пропущенных строк; счёт выше полный.</p>
              )}
            </dd>
          </>
        ) : null}
        {report.warnings.length > 0 ? (
          <>
            <dt>Предупреждения</dt>
            <dd>
              <ul className={styles.entries}>
                {report.warnings.map((note) => (
                  <li key={`warn-${note.row}`}>
                    строка {note.row}: {ROW_REASON_LABELS[note.reason]}
                  </li>
                ))}
              </ul>
            </dd>
          </>
        ) : null}
      </dl>

      <h4>Позиции</h4>
      {page.items.length === 0 ? (
        <EmptyState title="На этой странице позиций нет." />
      ) : (
        <div className={styles.frame}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.cell}>Строка</th>
                <th className={styles.cell}>Код</th>
                <th className={styles.cell}>Наименование</th>
                <th className={styles.cell}>Марка</th>
                <th className={styles.cell}>Ед. изм.</th>
                <th className={styles.cell}>Цена за единицу</th>
                <th className={styles.cell}>Поставщик</th>
                <th className={styles.cell}>Раздел</th>
              </tr>
            </thead>
            <tbody>
              {page.items.map((position) => (
                <tr key={position.price_list_position_id} data-position-row={position.row_number}>
                  <td className={styles.cell}>{position.row_number}</td>
                  <td className={styles.cell}>{position.code ?? '—'}</td>
                  <td className={styles.cell}>{position.name}</td>
                  <td className={styles.cell}>{position.mark ?? '—'}</td>
                  <td className={styles.cell}>{position.unit}</td>
                  <td className={`${styles.cell} ${styles.price}`}>
                    {formatPrice(position.unit_price, position.currency)}
                  </td>
                  <td className={styles.cell}>{position.vendor ?? '—'}</td>
                  <td className={styles.cell}>{sectionLabel(position.section_code)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="am-pager">
        Позиции {page.items.length === 0 ? 0 : page.offset + 1}–{page.offset + page.items.length} из{' '}
        {page.total}.{' '}
        {previous !== null ? (
          <button type="button" className="am-button am-button--quiet" onClick={() => onOffset(previous)}>
            Назад
          </button>
        ) : null}{' '}
        {page.next_offset !== null ? (
          <button
            type="button"
            className="am-button am-button--quiet"
            onClick={() => onOffset(page.next_offset ?? 0)}
          >
            Дальше
          </button>
        ) : null}
      </p>
    </div>
  );
}

export interface PriceListPanelProps {
  readonly projectUid: ProjectUid;
  /** Only an expert uploads; anyone with a role reads. */
  readonly canUpload: boolean;
}

export function PriceListPanel({ projectUid, canUpload }: PriceListPanelProps) {
  const revisions = usePriceListRevisions(projectUid);
  const [chosen, setChosen] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const current = revisions.data?.items.find((item) => item.is_current)?.price_list_id ?? null;
  const selected = chosen ?? current;
  const positions = usePriceListPositions(selected, offset);

  return (
    <div data-price-list-panel={projectUid}>
      {canUpload ? (
        <UploadPriceListForm projectUid={projectUid} />
      ) : (
        <p className="am-note">Прайс-лист загружает эксперт.</p>
      )}
      {revisions.isPending ? <LoadingState what="редакции прайс-листа" /> : null}
      {revisions.isError ? (
        <ErrorState
          title="Редакции прайс-листа не удалось прочитать."
          detail={failureMessage(revisions.error).detail}
          correlationId={failureMessage(revisions.error).correlationId}
          onRetry={() => void revisions.refetch()}
        />
      ) : null}
      {revisions.data !== undefined && revisions.data.items.length === 0 ? (
        <EmptyState
          title="Прайс-лист ещё не загружен."
          detail="Цены в оптимизации берутся только из загруженного прайс-листа проекта."
        />
      ) : null}
      {revisions.data !== undefined && revisions.data.items.length > 0 ? (
        <>
          <PriceListRevisionsView
            revisions={revisions.data.items}
            selectedId={selected}
            onSelect={(priceListId) => {
              setChosen(priceListId);
              setOffset(0);
            }}
          />
          {positions.isPending ? <LoadingState what="позиции прайс-листа" /> : null}
          {positions.isError ? (
            <ErrorState
              title="Позиции прайс-листа не удалось прочитать."
              detail={failureMessage(positions.error).detail}
              correlationId={failureMessage(positions.error).correlationId}
              onRetry={() => void positions.refetch()}
            />
          ) : null}
          {positions.data !== undefined ? (
            <PriceListPositionsView page={positions.data} onOffset={setOffset} />
          ) : null}
        </>
      ) : null}
    </div>
  );
}
