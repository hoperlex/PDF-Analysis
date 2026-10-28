'use client';

/**
 * «Спецификация и цены» — a document set's specification priced from the project's price
 * list (`W60-OPT-MATCH-01`; any section since `OPT-PROJECT-ALL-SECTIONS-01`), for the
 * project's «Оптимизация» tab.
 *
 * **Which set.** The project's documents come from `listDocuments` (the same cache entry the
 * project's structure reads); the sets offered are those whose **current** version an expert
 * confirmed in a section, whichever it is. The first is chosen; the expert may pick another.
 * A project with no such set says so and where a section is confirmed — the server is not
 * asked about a version nobody classified, which it would only answer `version_unclassified`
 * for. **A set whose current version was admitted for comparison only** (`upload_kind`
 * `comparison_pdf`, `Q-CMP-5`; `CMP-DEBT-261`) is listed and marked, as everywhere
 * (`CMP-VERSION-MARK-01`), but is a disabled option with the reason beside it: it has no published
 * run to read a specification from, it is never the set chosen by default, and nothing is
 * asked of the server for it.
 *
 * **What is shown** is `getSpecificationPrices` for the chosen set, one page of rows at a
 * time (`SpecificationPricesAnswer`): its state, or the rows with their match, the totals per
 * currency and what the totals leave out. Read-only: nothing here writes.
 */

import { useId, useState } from 'react';

import type { DocumentUid, DocumentVersion, ProjectUid } from '@/shared/api';
import { failureMessage } from '@/shared/api/failure-message';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import {
  COMPARISON_ONLY_MARK,
  COMPARISON_ONLY_START_NOTE,
  ComparisonOnlyMark,
  isComparisonOnly,
  useDocumentList,
} from '@/entities/document-version';
import { projectSectionOf } from '@/entities/project';
import { useSpecificationPrices } from '@/entities/specification-price';

import { SpecificationPricesAnswer } from './specification-prices-answer';
import styles from './specification-prices.module.css';

export interface SpecificationPricesSectionProps {
  readonly projectUid: ProjectUid;
}

/** The sets whose current version an expert confirmed in some section, in the order listed. */
export function classifiedDocumentSets(items: readonly DocumentVersion[]): readonly DocumentVersion[] {
  return items.filter((version) => (version.classification ?? null) !== null);
}

function setLabel(version: DocumentVersion): string {
  const title = version.display_title ?? version.source_filename ?? 'Комплект без названия';
  const code = version.classification?.section_code;
  const section = code === undefined ? '' : `, раздел ${projectSectionOf(code).abbr}`;
  return `${title} — версия ${version.version_ordinal}${section}`;
}

/**
 * What an `<option>` says of a set. An option holds text only, so a comparison-only set says the
 * mark in words here and the list under the select draws the badge; any other set is labelled as
 * before.
 */
function optionLabel(version: DocumentVersion): string {
  return isComparisonOnly(version) ? `${setLabel(version)} (${COMPARISON_ONLY_MARK})` : setLabel(version);
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
  const noteId = useId();
  if (sets.length === 0) {
    return (
      <EmptyState
        title="В проекте нет комплектов с подтверждённым разделом"
        detail="Спецификация и цены строятся для комплекта, текущую версию которого эксперт отнёс к одному из разделов. Подтвердите раздел на экране версии."
      />
    );
  }
  const comparisonOnly = sets.filter((version) => isComparisonOnly(version));
  return (
    <div className={styles.chooser}>
      <label>
        Комплект{' '}
        <select
          value={selected ?? ''}
          onChange={(event) => onSelect(event.target.value as DocumentUid)}
          data-spec-chooser={sets.length}
          aria-describedby={comparisonOnly.length > 0 ? noteId : undefined}
        >
          {sets.map((version) => (
            <option key={version.document_uid} value={version.document_uid} disabled={isComparisonOnly(version)}>
              {optionLabel(version)}
            </option>
          ))}
        </select>
      </label>
      {comparisonOnly.length > 0 ? (
        <div data-comparison-only-sets={comparisonOnly.length}>
          <ul>
            {comparisonOnly.map((version) => (
              <li key={version.document_uid}>
                {setLabel(version)} <ComparisonOnlyMark version={version} />
              </li>
            ))}
          </ul>
          <p className="am-note" id={noteId}>
            {COMPARISON_ONLY_START_NOTE}
          </p>
        </div>
      ) : null}
      {partial ? (
        <p className="am-note">Предложены комплекты первой страницы списка документов проекта.</p>
      ) : null}
    </div>
  );
}

export function SpecificationPricesSection({ projectUid }: SpecificationPricesSectionProps) {
  const documents = useDocumentList(projectUid);
  const sets = classifiedDocumentSets(documents.data?.items ?? []);
  // A comparison-only set is offered disabled, so it is never the default and never asked for.
  const readable = sets.filter((version) => !isComparisonOnly(version));
  const [chosen, setChosen] = useState<DocumentUid | null>(null);
  const [offset, setOffset] = useState(0);
  const selected = chosen ?? readable[0]?.document_uid ?? null;
  const prices = useSpecificationPrices(projectUid, selected, offset);
  const documentsFailure = documents.error === null ? null : failureMessage(documents.error);
  const pricesFailure = prices.error === null ? null : failureMessage(prices.error);

  return (
    <section className={styles.section} aria-labelledby="specification-prices-heading" data-specification-prices="">
      <div className={styles.bar}>
        <h2 id="specification-prices-heading" className={styles.heading}>Спецификация и цены</h2>
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
        Строки спецификации текущей версии комплекта (раздел подтверждён экспертом), прочитанные из
        сохранённого текста последнего опубликованного прогона, сопоставлены с действующим
        прайс-листом проекта. Цена и
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
