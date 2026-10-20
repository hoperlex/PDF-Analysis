/**
 * «Нормы» — the catalogue of the current snapshot (`W57B-NORMS-CATALOGUE-XLSX-01`).
 *
 * Every document of the CURRENT snapshot (`listNormDocuments`), filtered by text and kind,
 * in designation order, paged. The designation and title are the server's display
 * derivation from the stored file name; nothing here re-derives or alters them. Each row
 * opens the existing document page.
 *
 * The filter form is a plain `GET` to `/norms` carrying `view=catalogue`, so a filtered
 * catalogue is an address, as a search is. The kind list is the snapshot's own
 * (`kinds` of the answer), never a list written down here.
 */

import Link from 'next/link';

import type { NormCatalogueEntry, NormKindCount } from '@/shared/api';
import { routes } from '@/shared/lib';
import { EmptyState } from '@/shared/ui';
import { attributionLabel } from '@/entities/norms';

import styles from './norm-catalogue.module.css';

/** The address parameter that opens the catalogue on `/norms`, and its two filters. */
export const CATALOGUE_VIEW = 'catalogue';
export const CATALOGUE_QUERY_PARAM = 'cq';
export const CATALOGUE_KIND_PARAM = 'kind';

/** `/norms` with the catalogue open. */
export function catalogueAddress(): string {
  return `${routes.norms()}?view=${CATALOGUE_VIEW}`;
}

export interface NormViewsProps {
  /** Which view of «Нормы» is open. */
  readonly active: 'search' | 'catalogue';
}

/** The two views of «Нормы» as addresses: «Поиск» and «Каталог». */
export function NormViews({ active }: NormViewsProps) {
  return (
    <nav aria-label="Разделы норм" className={styles.views} data-norm-view={active}>
      <Link
        href={routes.norms()}
        className="am-button am-button--quiet am-button--small"
        aria-current={active === 'search' ? 'page' : undefined}
      >
        Поиск
      </Link>
      <Link
        href={catalogueAddress()}
        className="am-button am-button--quiet am-button--small"
        aria-current={active === 'catalogue' ? 'page' : undefined}
      >
        Каталог
      </Link>
    </nav>
  );
}

export interface NormCatalogueFormProps {
  readonly query: string | null;
  readonly kind: string | null;
  /** The snapshot's kinds, from the last answer; empty before one arrives. */
  readonly kinds: readonly NormKindCount[];
  readonly disabled: boolean;
}

export function NormCatalogueForm({ query, kind, kinds, disabled }: NormCatalogueFormProps) {
  return (
    <form
      className={`am-form ${styles.filters}`}
      method="get"
      action={routes.norms()}
      role="search"
      aria-label="Отбор документов каталога"
    >
      <input type="hidden" name="view" value={CATALOGUE_VIEW} />
      <div className="am-form__field">
        <label htmlFor="norms-catalogue-query"><strong>Обозначение или название</strong></label>
        <input
          id="norms-catalogue-query"
          name={CATALOGUE_QUERY_PARAM}
          type="search"
          minLength={1}
          maxLength={200}
          defaultValue={query ?? ''}
          disabled={disabled}
          placeholder="СП 54.13330 или 24.04.2013"
        />
      </div>
      <div className="am-form__field">
        <label htmlFor="norms-catalogue-kind"><strong>Вид документа</strong></label>
        <select id="norms-catalogue-kind" name={CATALOGUE_KIND_PARAM} defaultValue={kind ?? ''} disabled={disabled}>
          <option value="">Все виды</option>
          {kinds.map((item) => (
            <option key={item.kind} value={item.kind}>
              {item.kind} ({item.document_count})
            </option>
          ))}
          {kind !== null && !kinds.some((item) => item.kind === kind) ? <option value={kind}>{kind}</option> : null}
        </select>
      </div>
      <button type="submit" className="am-button" disabled={disabled}>Показать</button>
    </form>
  );
}

function CatalogueRow({ item }: { readonly item: NormCatalogueEntry }) {
  return (
    <tr data-norm-document={item.norm_document_id} data-norm-attribution={item.source_attribution}>
      <td>
        <Link href={routes.normDocument(item.norm_document_id)}><strong>{item.designation}</strong></Link>
      </td>
      <td>{item.title ?? '—'}</td>
      <td data-norm-kind={item.kind}>{item.kind}</td>
      <td className={styles.count}>{item.page_count}</td>
      <td className={styles.count}>{item.paragraph_count}</td>
      <td data-norm-content={item.content_available ? 'available' : 'absent'}>
        {item.content_available ? 'есть' : 'нет'}
      </td>
    </tr>
  );
}

export interface NormCatalogueTableProps {
  readonly items: readonly NormCatalogueEntry[];
  /** Documents the filters keep, over every page. */
  readonly total: number;
  /** True when any filter is applied. */
  readonly filtered: boolean;
  readonly onFirst: (() => void) | null;
  readonly onNext: (() => void) | null;
}

export function NormCatalogueTable({ items, total, filtered, onFirst, onNext }: NormCatalogueTableProps) {
  if (items.length === 0 && onFirst === null) {
    return (
      <EmptyState
        title={filtered ? 'Под этот отбор документов нет' : 'В текущем снимке нет документов'}
        detail={filtered ? 'Измените обозначение, название или вид документа.' : 'Каталог пуст.'}
      />
    );
  }
  const attribution = items[0]?.source_attribution;
  return (
    <section aria-label="Каталог нормативных документов" data-norm-catalogue={items.length}>
      <p role="status" className="am-note" data-norm-catalogue-total={total}>
        Документов {filtered ? 'под отбор' : 'в текущем снимке'}: {total}.
      </p>
      {items.length === 0 ? (
        <EmptyState title="На этой странице документов нет" detail="Вернитесь к началу списка." />
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th scope="col">Обозначение</th>
                <th scope="col">Название</th>
                <th scope="col">Вид</th>
                <th scope="col" className={styles.count}>Страниц</th>
                <th scope="col" className={styles.count}>Абзацев</th>
                <th scope="col">PDF</th>
              </tr>
            </thead>
            <tbody>{items.map((item) => <CatalogueRow key={item.norm_document_id} item={item} />)}</tbody>
          </table>
        </div>
      )}
      {attribution === undefined ? null : <p className="am-form__hint">{attributionLabel(attribution)}</p>}
      <div className="am-pager">
        {onFirst === null ? null : (
          <button type="button" className="am-button am-button--quiet am-button--small" onClick={onFirst}>
            В начало
          </button>
        )}
        {onNext === null ? null : (
          <button type="button" className="am-button am-button--quiet am-button--small" onClick={onNext}>
            Дальше
          </button>
        )}
      </div>
    </section>
  );
}
