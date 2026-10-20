'use client';

/**
 * «Спецификация и цены» — a document set's AR specification priced from the project's price
 * list (`W60-OPT-MATCH-01`), for the project's «Оптимизация» tab.
 *
 * **Which set.** The project's documents come from `listDocuments` (the same cache entry the
 * project's structure reads); the sets offered are those whose **current** version an expert
 * confirmed as section АР. The first is chosen; the expert may pick another. A project with
 * no such set says so and where a section is confirmed — the server is not asked about a set
 * it would only answer `section_not_ar` for.
 *
 * **What is shown** is `getSpecificationPrices` for the chosen set, one page of rows at a
 * time (`SpecificationPricesAnswer`): its state, or the rows with their match, the totals per
 * currency and what the totals leave out. Read-only: nothing here writes.
 */

import { useState } from 'react';

import type { DocumentUid, DocumentVersion, ProjectUid } from '@/shared/api';
import { failureMessage } from '@/shared/api/failure-message';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { useDocumentList } from '@/entities/document-version';
import { useSpecificationPrices } from '@/entities/specification-price';

import { SpecificationPricesAnswer } from './specification-prices-answer';
import styles from './specification-prices.module.css';

export interface SpecificationPricesSectionProps {
  readonly projectUid: ProjectUid;
}

/** The sets whose current version is confirmed as section АР, in the order listed. */
export function arDocumentSets(items: readonly DocumentVersion[]): readonly DocumentVersion[] {
  return items.filter((version) => version.classification?.section_code === 'AR');
}

function setLabel(version: DocumentVersion): string {
  const title = version.display_title ?? version.source_filename ?? 'Комплект без названия';
  return `${title} — версия ${version.version_ordinal}`;
}

export interface SpecificationPricesChooserProps {
  readonly sets: readonly DocumentVersion[];
  readonly selected: DocumentUid | null;
  readonly onSelect: (documentUid: DocumentUid) => void;
  /** Whether the server has a further page of the project's documents. */
  readonly partial: boolean;
}

/** The set chooser. Rendered by the static harness. */
export function SpecificationPricesChooser({ sets, selected, onSelect, partial }: SpecificationPricesChooserProps) {
  if (sets.length === 0) {
    return (
      <EmptyState
        title="В проекте нет комплектов раздела АР"
        detail="Спецификация и цены строятся для комплекта, текущую версию которого эксперт подтвердил как раздел АР. Подтвердите раздел на экране версии."
      />
    );
  }
  return (
    <div className={styles.chooser}>
      <label>
        Комплект АР{' '}
        <select
          value={selected ?? ''}
          onChange={(event) => onSelect(event.target.value as DocumentUid)}
          data-spec-chooser={sets.length}
        >
          {sets.map((version) => (
            <option key={version.document_uid} value={version.document_uid}>
              {setLabel(version)}
            </option>
          ))}
        </select>
      </label>
      {partial ? (
        <p className="am-note">Предложены комплекты первой страницы списка документов проекта.</p>
      ) : null}
    </div>
  );
}

export function SpecificationPricesSection({ projectUid }: SpecificationPricesSectionProps) {
  const documents = useDocumentList(projectUid);
  const sets = arDocumentSets(documents.data?.items ?? []);
  const [chosen, setChosen] = useState<DocumentUid | null>(null);
  const [offset, setOffset] = useState(0);
  const selected = chosen ?? sets[0]?.document_uid ?? null;
  const prices = useSpecificationPrices(projectUid, selected, offset);
  const documentsFailure = documents.error === null ? null : failureMessage(documents.error);
  const pricesFailure = prices.error === null ? null : failureMessage(prices.error);

  return (
    <section className={styles.section} aria-labelledby="specification-prices-heading" data-specification-prices="">
      <div className={styles.bar}>
        <h3 id="specification-prices-heading" className={styles.heading}>Спецификация и цены</h3>
        <button
          type="button"
          className="am-button am-button--quiet"
          disabled={selected === null}
          onClick={() => void prices.refetch()}
        >
          Обновить
        </button>
      </div>
      <p className={styles.rule}>
        Строки спецификации текущей версии комплекта АР, прочитанные из сохранённого текста
        последнего опубликованного прогона, сопоставлены с действующим прайс-листом проекта. Цена и
        сумма показаны только для строки, однозначно сопоставленной с позицией в той же единице
        измерения и с числовым количеством; итоги считаются по валютам только по таким строкам.
      </p>
      {documents.isPending ? <LoadingState what="документов проекта" /> : null}
      {documentsFailure !== null ? (
        <ErrorState
          title="Документы проекта не прочитаны"
          detail={documentsFailure.detail}
          correlationId={documentsFailure.correlationId}
          onRetry={() => void documents.refetch()}
        />
      ) : null}
      {documents.data !== undefined ? (
        <SpecificationPricesChooser
          sets={sets}
          selected={selected}
          onSelect={(documentUid) => {
            setChosen(documentUid);
            setOffset(0);
          }}
          partial={documents.data.page.next_cursor !== null}
        />
      ) : null}
      {selected !== null && prices.isPending ? <LoadingState what="спецификации и цен" /> : null}
      {pricesFailure !== null ? (
        <ErrorState
          title="Спецификация и цены не прочитаны"
          detail={pricesFailure.detail}
          correlationId={pricesFailure.correlationId}
          onRetry={() => void prices.refetch()}
        />
      ) : null}
      {prices.data !== undefined && pricesFailure === null ? (
        <SpecificationPricesAnswer
          answer={prices.data}
          onPage={prices.isPlaceholderData ? null : setOffset}
        />
      ) : null}
    </section>
  );
}
