/**
 * One answer of `getSpecificationPrices`, rendered (`W60-OPT-MATCH-01`). Pure: the container
 * (`specification-prices-section.tsx`) owns the queries, this owns the reading.
 *
 * **A state is said, never shown as an empty table.** An unclassified version, a
 * project without a price list, a version without a published run or saved text, a
 * specification over the bound — each is one sentence saying what is missing and where it is
 * done, with the facts the server read before it stopped.
 *
 * **The money rule is the screen's too.** A price and an amount appear only on a row that
 * counts in a total — matched to one price-list position, in the same unit, with a numeric
 * quantity (`amount` present). Every other row shows a dash and says why. Totals are per
 * currency, never summed across currencies, and the rows they leave out are counted by
 * reason. Amounts are the server's exact decimals, grouped for reading and never rounded.
 */

import type { SpecificationPriceRow, SpecificationPrices } from '@/shared/api';
import { EmptyState } from '@/shared/ui';
import { projectSectionOf } from '@/entities/project';
import {
  formatDecimal,
  formatMoney,
  quantityIssueLabel,
  specificationBasisLabel,
  specificationExclusionLabel,
  specificationReasonLabel,
  specificationSkipLabel,
  specificationStateMessage,
  specificationStatusLabel,
  specificationUnitLabel,
} from '@/entities/specification-price';

import styles from './specification-prices.module.css';

export interface SpecificationPricesAnswerProps {
  readonly answer: SpecificationPrices;
  /** Move to another page of rows; `null` while a page is loading. */
  readonly onPage: ((offset: number) => void) | null;
}

const STATUS_TONES: Readonly<Record<string, string>> = {
  matched: 'am-badge--ok',
  ambiguous: 'am-badge--degraded',
  unmatched: 'am-badge--inert',
};

function Facts({ answer }: { readonly answer: SpecificationPrices }) {
  const { price_list: priceList } = answer;
  return (
    <dl className={styles.facts} data-spec-facts="">
      <dt>Версия комплекта</dt>
      <dd>
        версия {answer.version_ordinal}, страниц: {answer.page_count}
        {answer.section_code === null ? null : (
          <>, раздел {projectSectionOf(answer.section_code).abbr}{answer.project_stage === null ? null : `, стадия ${answer.project_stage === 'P' ? 'П' : 'Р'}`}</>
        )}
      </dd>
      {priceList === null ? null : (
        <>
          <dt>Прайс-лист</dt>
          <dd data-spec-price-list={priceList.price_list_id}>
            «{priceList.source_filename}», редакция {priceList.revision_number}, позиций: {priceList.position_count}
          </dd>
        </>
      )}
      {answer.run_id === null ? null : (
        <>
          <dt>Прогон</dt>
          <dd><code>{answer.run_id}</code></dd>
        </>
      )}
    </dl>
  );
}

function Quantity({ row }: { readonly row: SpecificationPriceRow }) {
  if (row.quantity !== null) return <>{formatDecimal(row.quantity)}</>;
  return (
    <>
      {row.quantity_text ?? '—'}
      {row.quantity_issue === null ? null : (
        <span className={styles.hint}> ({quantityIssueLabel(row.quantity_issue)})</span>
      )}
    </>
  );
}

function Match({ row }: { readonly row: SpecificationPriceRow }) {
  const tone = STATUS_TONES[row.status] ?? 'am-badge--inert';
  return (
    <>
      <span className={`am-badge ${tone}`}>{specificationStatusLabel(row.status)}</span>
      <span className={styles.hint}>
        {row.basis !== null ? ` ${specificationBasisLabel(row.basis)}` : null}
        {row.reason !== null ? ` — ${specificationReasonLabel(row.reason)}` : null}
        {row.status === 'ambiguous' ? `; кандидатов: ${row.candidate_count}` : null}
      </span>
    </>
  );
}

function PricePosition({ row }: { readonly row: SpecificationPriceRow }) {
  const position = row.price_position;
  if (position === null) return <>—</>;
  const extras = [position.mark, position.code].filter((value): value is string => value !== null);
  return (
    <>
      {position.name}
      {extras.length === 0 ? null : <span className={styles.hint}> ({extras.join(', ')})</span>}
      <span className={styles.hint}>, строка прайс-листа {position.row_number}</span>
    </>
  );
}

function Row({ row }: { readonly row: SpecificationPriceRow }) {
  const counted = row.amount !== null && row.price_position !== null;
  const place = row.sheet_label === null ? `с. ${row.page_number}` : `л. ${row.sheet_label} / с. ${row.page_number}`;
  return (
    <tr data-spec-row={row.row_id} data-spec-status={row.status} data-spec-counted={counted ? 'yes' : 'no'}>
      <td className={styles.cell} title={`строки ${row.line_start}–${row.line_end}`}>{place}</td>
      <td className={styles.cell}>{row.position ?? '—'}</td>
      <td className={styles.cell}>
        {row.group === null ? null : <span className={styles.group}>{row.group}: </span>}
        {row.name}
        {row.note === null ? null : <span className={styles.hint}> Примечание: {row.note}</span>}
      </td>
      <td className={styles.cell}>{row.unit !== null ? specificationUnitLabel(row.unit) : (row.unit_text ?? '—')}</td>
      <td className={`${styles.cell} ${styles.number}`}><Quantity row={row} /></td>
      <td className={styles.cell}><Match row={row} /></td>
      <td className={styles.cell}><PricePosition row={row} /></td>
      <td className={`${styles.cell} ${styles.number}`} data-spec-price={counted ? row.price_position?.unit_price : 'none'}>
        {counted ? formatMoney(row.price_position?.unit_price ?? null, row.price_position?.currency ?? null) : '—'}
      </td>
      <td className={`${styles.cell} ${styles.number}`} data-spec-amount={row.amount ?? 'none'}>
        {counted ? formatMoney(row.amount, row.price_position?.currency ?? null) : '—'}
        {!counted && row.excluded_reason !== null ? (
          <span className={styles.hint}> ({specificationExclusionLabel(row.excluded_reason)})</span>
        ) : null}
      </td>
    </tr>
  );
}

function Totals({ answer }: { readonly answer: SpecificationPrices }) {
  const matching = answer.matching;
  if (matching === null) return null;
  const excluded = Object.entries(matching.excluded).filter(([, count]) => count > 0);
  const excludedTotal = excluded.reduce((sum, [, count]) => sum + count, 0);
  return (
    <section className={styles.totals} aria-label="Итоги" data-spec-totals="">
      <h3 className={styles.subheading}>Итого по однозначно сопоставленным строкам</h3>
      {matching.totals.length === 0 ? (
        <p data-spec-total="none">
          Итога нет: ни одна строка не сопоставлена с одной позицией прайс-листа в той же единице
          измерения и с числовым количеством.
        </p>
      ) : (
        <ul className={styles.list}>
          {matching.totals.map((total) => (
            <li key={total.currency} data-spec-total={total.currency}>
              <strong>{formatMoney(total.amount, total.currency)}</strong> — строк: {total.row_count}
            </li>
          ))}
        </ul>
      )}
      {matching.totals.length > 1 ? (
        <p className="am-note">Итоги в разных валютах не складываются и не пересчитываются.</p>
      ) : null}
      <p data-spec-excluded={excludedTotal}>
        {excludedTotal === 0
          ? 'В итог вошли все строки спецификации.'
          : `Не вошли в итог строк: ${excludedTotal} — ${excluded
              .map(([reason, count]) => `${specificationExclusionLabel(reason)}: ${count}`)
              .join('; ')}.`}
      </p>
    </section>
  );
}

function Skipped({ answer }: { readonly answer: SpecificationPrices }) {
  const extraction = answer.extraction;
  if (extraction === null || extraction.skipped_count === 0) return null;
  return (
    <details className={styles.details} data-spec-skipped={extraction.skipped_count}>
      <summary>Строки таблиц, которые не прочитаны: {extraction.skipped_count}</summary>
      <ul className={styles.list}>
        {extraction.skipped.map((line) => (
          <li key={`${line.page_number}-${line.line}`}>
            с. {line.page_number}, строка {line.line}: {specificationSkipLabel(line.reason)}
            {line.excerpt === '' ? null : <span className={styles.hint}> — «{line.excerpt}»</span>}
          </li>
        ))}
      </ul>
      {extraction.skipped.length < extraction.skipped_count ? (
        <p className="am-note">Показаны первые {extraction.skipped.length}; счёт по причинам полный.</p>
      ) : null}
    </details>
  );
}

function Pager({ answer, onPage }: SpecificationPricesAnswerProps) {
  const rows = answer.rows;
  if (rows === null || rows.total <= rows.limit) return null;
  const last = rows.offset + rows.items.length;
  return (
    <div className="am-pager" data-spec-pager="">
      <span>Строки {rows.offset + 1}–{last} из {rows.total}</span>
      <button
        type="button"
        className="am-button am-button--quiet"
        disabled={onPage === null || rows.offset === 0}
        onClick={() => onPage?.(Math.max(0, rows.offset - rows.limit))}
      >
        Предыдущие
      </button>
      <button
        type="button"
        className="am-button am-button--quiet"
        disabled={onPage === null || rows.next_offset === null}
        onClick={() => rows.next_offset !== null && onPage?.(rows.next_offset)}
      >
        Следующие
      </button>
    </div>
  );
}

export function SpecificationPricesAnswer({ answer, onPage }: SpecificationPricesAnswerProps) {
  if (answer.state !== 'ready') {
    return (
      <div data-spec-state={answer.state}>
        <Facts answer={answer} />
        <EmptyState title="Спецификация не сопоставлена с ценами" detail={specificationStateMessage(answer.state)} />
      </div>
    );
  }
  const rows = answer.rows;
  const extraction = answer.extraction;
  const counts = answer.matching?.counts;
  return (
    <div data-spec-state="ready">
      <Facts answer={answer} />
      <p data-spec-summary="">
        Найдено таблиц спецификации: {extraction?.table_count ?? 0}, строк: {extraction?.row_count ?? 0}.
        {counts === undefined ? null : ` Сопоставлено: ${counts.matched}, неоднозначно: ${counts.ambiguous}, не сопоставлено: ${counts.unmatched}.`}
      </p>
      <Totals answer={answer} />
      <Skipped answer={answer} />
      {rows === null || rows.total === 0 ? (
        <EmptyState
          title="Таблицы спецификации в тексте версии не найдены"
          detail="Спецификация ищется по заголовку таблицы с графами «Наименование» и «Кол.»; в сохранённом тексте этой версии такой таблицы нет."
        />
      ) : (
        <>
          <div className={styles.frame}>
            <table className={styles.table} aria-label="Строки спецификации и цены">
              <thead>
                <tr>
                  <th className={styles.cell} scope="col">Лист / стр.</th>
                  <th className={styles.cell} scope="col">Поз.</th>
                  <th className={styles.cell} scope="col">Наименование и характеристика</th>
                  <th className={styles.cell} scope="col">Ед. изм.</th>
                  <th className={styles.cell} scope="col">Кол.</th>
                  <th className={styles.cell} scope="col">Сопоставление</th>
                  <th className={styles.cell} scope="col">Позиция прайс-листа</th>
                  <th className={styles.cell} scope="col">Цена</th>
                  <th className={styles.cell} scope="col">Сумма</th>
                </tr>
              </thead>
              <tbody>
                {rows.items.map((row) => <Row key={row.row_id} row={row} />)}
              </tbody>
            </table>
          </div>
          <p className="am-note">
            В сохранённом тексте графы «Тип, марка», «Код» и «Завод-изготовитель» не отделены от
            наименования и показаны вместе с ним.
          </p>
          <Pager answer={answer} onPage={onPage} />
        </>
      )}
    </div>
  );
}
