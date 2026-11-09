/**
 * «Нормы» — the search and its results (`W55A-WEB-NORMS`, plan §A3.7, R-112).
 *
 * Text search over the CURRENT snapshot: a designation (`СП 54`), a clause (`п. 7.1.4`) and
 * words, in any combination. Each result names its document, its clause and its page, shows
 * the matched fragment with the matched spans marked, says where the text came from
 * (`NORM-Q04`) and offers «Открыть» — the document view with its PDF at the result's page.
 *
 * The form is a plain `GET` to `/norms`, so a search is an address: it survives a reload and
 * can be sent to a colleague. Before an administrator designates a snapshot, search refuses
 * (`required_norm_unavailable`), and the screen says so with {@link NoCurrentSnapshot} —
 * never with an empty list.
 */

import Link from 'next/link';

import type { NormSearchHit } from '@/shared/api';
import { routes } from '@/shared/lib';
import { EmptyState, UnsupportedState } from '@/shared/ui';
import {
  NO_CURRENT_SNAPSHOT_DETAIL, attributionLabel, clauseLabel, fragmentParts,
} from '@/entities/norms';

import styles from './norm-search.module.css';

/** The refusal state before any snapshot is current, on the landing and after a search. */
export function NoCurrentSnapshot() {
  return (
    <div data-norms-refusal="no_current_snapshot">
      <UnsupportedState title="Текущий снимок норм не назначен" detail={NO_CURRENT_SNAPSHOT_DETAIL} />
    </div>
  );
}

export interface NormSearchFormProps {
  /** The search the address carries, shown back in the field. */
  readonly query: string | null;
  /** True while search is known to refuse (no current snapshot). */
  readonly disabled: boolean;
}

export function NormSearchForm({ query, disabled }: NormSearchFormProps) {
  return (
    <form className={`am-form ${styles.search}`} method="get" action={routes.norms()} role="search" aria-label="Поиск по нормам">
      <div className={styles.field}>
        <label htmlFor="norms-query">Что найти</label>
        <input
          id="norms-query"
          name="q"
          type="search"
          required
          minLength={1}
          maxLength={200}
          defaultValue={query ?? ''}
          disabled={disabled}
          placeholder="СП 54 п. 5.1 высота помещений"
        />
      </div>
      <button type="submit" className="am-button" disabled={disabled}>Найти</button>
      <details className={styles.help}>
        <summary>Что ищется</summary>
        <p className="am-form__hint">
          Обозначение документа, номер пункта и слова — по отдельности или вместе. Ищется
          текущий снимок нормативной базы; абзацы с ненадёжно распознанным текстом в поиск не
          попадают.
        </p>
      </details>
    </form>
  );
}

function HitRow({ hit }: { readonly hit: NormSearchHit }) {
  const clause = clauseLabel(hit.clause_number);
  return (
    <li className={styles.hit} data-norm-hit={hit.norm_paragraph_id} data-norm-attribution={hit.source_attribution}>
      {/* The document, where in it and the way into its PDF on one line; the fragment; the attribution last. */}
      <p className={styles.head}>
        <span className={styles.document}>
          <Link href={routes.normDocument(hit.norm_document_id)}><strong>{hit.designation}</strong></Link>
          {' — '}
          {hit.title}
        </span>
        <span className={styles.where}>
          <span>
            {clause === null ? null : <span data-norm-clause={hit.clause_number}>{clause} · </span>}
            <span data-norm-page={hit.page_label}>стр. {hit.page_label}</span>
          </span>
          <Link
            className="am-button am-button--quiet am-button--small"
            href={routes.normDocument(hit.norm_document_id, hit.page_label)}
            aria-label={`Открыть PDF документа ${hit.designation} на странице ${hit.page_label}`}
          >
            Открыть
          </Link>
        </span>
      </p>
      <blockquote className={styles.fragment} data-norm-fragment={hit.fragment.text}>
        {fragmentParts(hit.fragment).map((part, index) =>
          part.hit ? <mark key={index} className={styles.match}>{part.text}</mark> : <span key={index}>{part.text}</span>)}
      </blockquote>
      <p className={`am-form__hint ${styles.source}`}>{attributionLabel(hit.source_attribution)}</p>
    </li>
  );
}

export interface NormSearchResultsProps {
  readonly items: readonly NormSearchHit[];
  /** Back to the first page, or `null` on it. */
  readonly onFirst: (() => void) | null;
  /** The next page, or `null` on the last. */
  readonly onNext: (() => void) | null;
}

export function NormSearchResults({ items, onFirst, onNext }: NormSearchResultsProps) {
  if (items.length === 0 && onFirst === null) {
    return (
      <EmptyState
        title="Ничего не найдено"
        detail="В текущем снимке нет надёжно распознанного абзаца, подходящего под этот запрос. Попробуйте другое обозначение, пункт или слова."
        action={
          <Link className="am-button am-button--quiet am-button--small" href={routes.norms()} data-norm-search-reset="">
            Сбросить поиск
          </Link>
        }
      />
    );
  }
  return (
    <section aria-label="Результаты поиска по нормам" className={styles.results} data-norm-hits={items.length}>
      {items.length === 0 ? (
        <EmptyState
          title="На этой странице результатов нет"
          detail="Вернитесь к началу списка."
          action={onFirst === null ? undefined : (
            <button type="button" className="am-button am-button--quiet am-button--small" onClick={onFirst}>
              В начало
            </button>
          )}
        />
      ) : (
        <>
          <p role="status" className={styles.count} data-norm-hits-count={items.length}>
            Найдено на этой странице: {items.length}{onNext === null ? '' : '; следующие — по кнопке «Дальше»'}.
          </p>
          <ol>{items.map((hit) => <HitRow key={hit.norm_paragraph_id} hit={hit} />)}</ol>
        </>
      )}
      <div className="am-pager">
        {onFirst === null || items.length === 0 ? null : (
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
