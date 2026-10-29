'use client';

/**
 * «Предложения» — the deterministic optimisation proposals of a document set's current version
 * (`W60-OPT-PROPOSALS-01`; any section since `OPT-PROJECT-ALL-SECTIONS-01`), for the project's
 * «Оптимизация» tab.
 *
 * **Which set.** The project's documents come from `listDocuments` (the cache entry the
 * project's structure reads); the sets offered are those whose **current** version an expert
 * confirmed in a section, whichever it is. A project with none says so and where a section is
 * confirmed. **A set whose current version was admitted for comparison only** (`upload_kind`
 * `comparison_pdf`, `Q-CMP-5`; `CMP-DEBT-261`) is listed and marked, as everywhere
 * (`CMP-VERSION-MARK-01`), but is a disabled option with the reason beside it: a pass reads the
 * set's last published run and such a version has none, so it is never the set chosen by default,
 * «Запустить проход» is never offered for it, and nothing is asked of the server for it.
 *
 * **What is shown.** The set's passes, newest first, each pinned to the version, run, price
 * list and vendor list it read; the open pass's counts by decision (the proposals' own, never
 * the findings'), a decision filter and the proposals page by page with their provenance,
 * both prices and the saving where a price-list position and a numeric quantity state it.
 * An expert starts a pass and decides each proposal (accept, reject, or revise with a
 * comment); an administrator reads. The CSV is the server's file for the open pass.
 *
 * Nothing here is a finding, reads one or changes one, and a model proposes nothing.
 */

import { useId, useState } from 'react';
import type { ReactNode } from 'react';
import Link from 'next/link';

import type {
  DocumentUid,
  DocumentVersion,
  OptimisationPass,
  OptimisationPassId,
  ProjectUid,
  Role,
} from '@/shared/api';
import type { FailureMessage } from '@/shared/api/failure-message';
import { failureMessage } from '@/shared/api/failure-message';
import { formatInstant, routes, useAddressState } from '@/shared/lib';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import {
  COMPARISON_ONLY_MARK,
  COMPARISON_ONLY_OPTIMISATION_NOTE,
  ComparisonOnlyMark,
  isComparisonOnly,
  useDocumentList,
} from '@/entities/document-version';
import { projectSectionOf } from '@/entities/project';
import {
  PROPOSAL_PAGE_LIMIT,
  describeCounts,
  useOptimisationPasses,
  useOptimisationProposals,
} from '@/entities/optimisation-proposal';
import { useEvidenceDocument } from '@/features/open-evidence';
import { CarryOverProposalDecisions } from '@/features/carry-over-proposal-decisions';
import { ImportProposalDecisions } from '@/features/import-proposal-decisions';
import { StartOptimisationPass } from '@/features/start-optimisation-pass';

import { readProposalDecision, writeProposalDecision } from '../model/decision-filter';
import { pageLimitOf, readProposalLayout, writeProposalLayout } from '../model/layout';
import { useExportProposalsCsv } from '../model/use-export-proposals-csv';
import { useExportProposalsXlsx } from '../model/use-export-proposals-xlsx';
import styles from './optimisation-proposals.module.css';
import { PassSummary } from './pass-summary';
import { ProposalList } from './proposal-list';
import type { SheetDocument } from './proposal-list';

export interface OptimisationProposalsProps {
  readonly projectUid: ProjectUid;
  /** The session's roles, as the route's guard read them. */
  readonly roles: readonly Role[];
  /**
   * `R-151r`: the document whose tab this is. Given, the widget works on that document only and offers no
   * «Комплект» choice; absent, the reader chooses among the project's classified sets as before.
   */
  readonly documentUid?: DocumentUid | undefined;
  /**
   * `UI-B-02`: the pass the address names (`?pass=`), read by the page layer. With `onPassChange` the chosen pass
   * is this value, so a link or a reload opens it; a pass the set does not have is said, not silently replaced.
   */
  readonly passId?: string | null | undefined;
  /** The reader chose another pass (or none): the page layer writes it onto the address. */
  readonly onPassChange?: ((passId: OptimisationPassId | null) => void) | undefined;
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

export interface ProposalSetChooserProps {
  readonly sets: readonly DocumentVersion[];
  readonly selected: DocumentUid | null;
  readonly onSelect: (documentUid: DocumentUid) => void;
  /** Whether the server has a further page of the project's documents. */
  readonly partial: boolean;
}

/** The set chooser. Rendered by the static harness. */
export function ProposalSetChooser({ sets, selected, onSelect, partial }: ProposalSetChooserProps) {
  const noteId = useId();
  if (sets.length === 0) {
    return (
      <EmptyState
        title="В проекте нет комплектов с подтверждённым разделом"
        detail="Предложения строятся для комплекта, текущую версию которого эксперт отнёс к одному из разделов. Подтвердите раздел на экране версии."
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
          data-proposal-set-chooser={sets.length}
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
            {COMPARISON_ONLY_OPTIMISATION_NOTE}
          </p>
        </div>
      ) : null}
      {partial ? (
        <p className="am-note">Предложены комплекты первой страницы списка документов проекта.</p>
      ) : null}
    </div>
  );
}

export interface PassListProps {
  readonly passes: readonly OptimisationPass[];
  readonly active: OptimisationPassId | null;
  readonly onOpen: (passId: OptimisationPassId) => void;
}

/** The set's passes, newest first, each with its counts by decision. */
export function PassList({ passes, active, onOpen }: PassListProps) {
  if (passes.length === 0) {
    return (
      <EmptyState
        title="Проходов по этому комплекту ещё не было"
        detail="Эксперт запускает проход кнопкой выше; результат сохраняется и остаётся доступным."
      />
    );
  }
  return (
    <ul className={styles.passes} aria-label="Проходы комплекта" data-pass-count={passes.length}>
      {passes.map((pass) => (
        <li key={pass.optimisation_pass_id} className={styles.pass}>
          <button
            type="button"
            className={pass.optimisation_pass_id === active ? 'am-button' : 'am-button am-button--quiet'}
            aria-pressed={pass.optimisation_pass_id === active}
            onClick={() => onOpen(pass.optimisation_pass_id)}
          >
            Проход от {formatInstant(pass.started_at)}
          </button>
          <span>
            предложений — {pass.proposal_count}; {describeCounts(pass)}
          </span>
        </li>
      ))}
    </ul>
  );
}

export interface ExportProposalsViewProps {
  readonly pending: boolean;
  readonly failure: FailureMessage | null;
  readonly onDownload: () => void;
  /** `UI-B-15`: the workbook an expert edits and loads back; absent, the table is not offered. */
  readonly onDownloadXlsx?: (() => void) | undefined;
  /** `UI-B-15`: «Загрузить решения», offered to an expert only. */
  readonly importControl?: ReactNode;
  /** `UI-B-14`: «Перенести решения из V#», offered to an expert only, and only when an earlier version has a pass. */
  readonly carryOverControl?: ReactNode;
}

/** «Выгрузить CSV», «Выгрузить таблицу решений» and «Загрузить решения» with the refusal, from state already in hand. Rendered by the harness. */
export function ExportProposalsView({
  pending,
  failure,
  onDownload,
  onDownloadXlsx,
  importControl,
  carryOverControl,
}: ExportProposalsViewProps) {
  return (
    <div data-proposals-export="">
      <p>
        <button type="button" className="am-button am-button--quiet" disabled={pending} onClick={onDownload}>
          Выгрузить CSV предложений
        </button>
        {onDownloadXlsx === undefined ? null : (
          <>
            {' '}
            <button type="button" className="am-button am-button--quiet" disabled={pending} onClick={onDownloadXlsx}>
              Выгрузить таблицу решений (.xlsx)
            </button>
          </>
        )}
      </p>
      {importControl ?? null}
      {carryOverControl ?? null}
      {failure !== null ? (
        <ErrorState
          title="Файл не выгружен"
          detail={failure.detail}
          correlationId={failure.correlationId}
          onRetry={onDownload}
        />
      ) : null}
    </div>
  );
}

interface ActivePassProps {
  readonly passId: OptimisationPassId;
  readonly canDecide: boolean;
  /** The set's passes, newest first: the earlier versions' decisions can be carried from them (`UI-B-14`). */
  readonly passes: readonly OptimisationPass[];
}

function ActivePass({ passId, canDecide, passes }: ActivePassProps) {
  // `D-372`: the decision filter is in the address (`?decision=`; «Все» is the absent parameter), as the layout is, so a link, a
  // reload and Back/Forward return to it. A filter is not a place to go Back to: choosing one replaces the entry.
  const [decision, setDecision] = useAddressState(readProposalDecision, writeProposalDecision);
  const [offset, setOffset] = useState(0);
  // `UI-B-06`: the layout is in the address (`?layout=table`); the table pages by the original's fifty, the cards by their own page.
  const [layout, setLayout] = useAddressState(readProposalLayout, writeProposalLayout);
  const proposals = useOptimisationProposals(passId, decision, offset, pageLimitOf(layout, PROPOSAL_PAGE_LIMIT));
  const exporter = useExportProposalsCsv({ passId });
  const workbook = useExportProposalsXlsx({ passId });
  const failure = proposals.error === null ? null : failureMessage(proposals.error);
  const exportError = exporter.error ?? workbook.error;
  const exportFailure = exportError === null || exportError === undefined ? null : failureMessage(exportError);
  // `UI-B-09`: the pass's version PDF is read once for every card's «Открыть лист», as the review screen reads its own;
  // the bytes are asked for only for a pass that has proposals, so an empty pass costs no download.
  const pass = proposals.data?.optimisation_pass;
  const pdf = useEvidenceDocument(pass !== undefined && pass.proposal_count > 0 ? pass.version_uid : null);
  const sheet: SheetDocument = {
    url: pdf.objectUrl,
    isLoading: pdf.isLoading,
    failure: pdf.error === null || pdf.error === undefined ? null : failureMessage(pdf.error),
    onRetry: pdf.refetch,
  };
  return (
    <div>
      {proposals.isPending ? <LoadingState what="предложений" /> : null}
      {failure !== null ? (
        <ErrorState
          title="Предложения не прочитаны"
          detail={failure.detail}
          correlationId={failure.correlationId}
          onRetry={() => void proposals.refetch()}
        />
      ) : null}
      {proposals.data !== undefined && failure === null ? (
        <>
          {/* `UI-B-05`: the original's strip -- the counts by decision and the buttons -- comes first; the pass's facts follow it. */}
          <ProposalList
            page={proposals.data}
            canDecide={canDecide}
            onDecision={(state) => {
              setDecision(state, 'replace');
              setOffset(0);
            }}
            onPage={proposals.isPlaceholderData ? null : setOffset}
            layout={layout}
            onLayout={(next) => {
              // A view, not a place: it replaces the entry. A page of one size is not a page of the other, so it starts again.
              setLayout(next, 'replace');
              setOffset(0);
            }}
            summary={
              <details className={styles.details} data-pass-summary="">
                <summary>Сведения о проходе</summary>
                <PassSummary pass={proposals.data.optimisation_pass} />
              </details>
            }
            actions={
              <ExportProposalsView
                pending={exporter.isPending || workbook.isPending}
                failure={exportFailure}
                onDownload={exporter.download}
                onDownloadXlsx={workbook.download}
                importControl={canDecide ? <ImportProposalDecisions passId={passId} /> : null}
                carryOverControl={
                  canDecide ? <CarryOverProposalDecisions pass={proposals.data.optimisation_pass} passes={passes} /> : null
                }
              />
            }
            sheet={sheet}
          />
        </>
      ) : null}
    </div>
  );
}

export function OptimisationProposals({
  projectUid,
  roles,
  documentUid,
  passId = null,
  onPassChange,
}: OptimisationProposalsProps) {
  const documents = useDocumentList(projectUid);
  const sets = classifiedDocumentSets(documents.data?.items ?? []);
  // A comparison-only set is offered disabled, so it is never the default, never started for and
  // never asked for.
  const startable = sets.filter((version) => !isComparisonOnly(version));
  const [chosenSet, setChosenSet] = useState<DocumentUid | null>(null);
  const [localPass, setLocalPass] = useState<OptimisationPassId | null>(null);
  // With a page layer behind it (`onPassChange`) the address is the one place the chosen pass lives; without one
  // it is local state, opened on the pass the caller names.
  const chosenPass =
    onPassChange === undefined ? (localPass ?? (passId as OptimisationPassId | null)) : (passId as OptimisationPassId | null);
  const setChosenPass = (next: OptimisationPassId | null) => {
    setLocalPass(next);
    onPassChange?.(next);
  };
  const fixed = documentUid !== undefined;
  const selectedSet = documentUid ?? chosenSet ?? startable[0]?.document_uid ?? null;
  const passes = useOptimisationPasses(projectUid, selectedSet);
  const list = passes.data?.items ?? [];
  const activePass =
    chosenPass !== null && list.some((pass) => pass.optimisation_pass_id === chosenPass)
      ? chosenPass
      : (list[0]?.optimisation_pass_id ?? null);
  // `UI-B-02`: a pass named by the address that the set does not have (a stale link, another document's pass) opens
  // the newest one and says so.
  const missingPass =
    passes.data !== undefined &&
    !passes.isFetching &&
    chosenPass !== null &&
    !list.some((pass) => pass.optimisation_pass_id === chosenPass)
      ? chosenPass
      : null;
  const documentsFailure = documents.error === null ? null : failureMessage(documents.error);
  const passesFailure = passes.error === null ? null : failureMessage(passes.error);

  return (
    <section
      className={styles.section}
      aria-labelledby="optimisation-proposals-heading"
      data-optimisation-proposals=""
    >
      <div className={styles.bar}>
        <h2 id="optimisation-proposals-heading" className={styles.heading}>
          Предложения
        </h2>
        <button
          type="button"
          className="am-button am-button--quiet"
          disabled={selectedSet === null}
          onClick={() => void passes.refetch()}
        >
          Обновить
        </button>
      </div>
      {/* `UI-PARITY-DENSE`: what a proposal is, one click away; it was a five-line paragraph above every list. */}
      <details className={styles.details}>
        <summary>Как строятся предложения</summary>
        <p className={styles.rule}>
          Предложение — отдельная сущность рядом с замечаниями, со своими решениями экспертов,
          счётчиками и выгрузкой. Оно появляется, когда строка спецификации однозначно сопоставлена с
          позицией прайс-листа, а в том же прайс-листе есть более дешёвая позиция той же единицы
          измерения и валюты от поставщика из вендор-листа раздела этого комплекта. Цены берутся
          только из прайс-листа, экономия считается только при числовом количестве.
        </p>
      </details>
      {!fixed && documents.isPending ? <LoadingState what="документов проекта" /> : null}
      {!fixed && documentsFailure !== null ? (
        <ErrorState
          title="Документы проекта не прочитаны"
          detail={documentsFailure.detail}
          correlationId={documentsFailure.correlationId}
          onRetry={() => void documents.refetch()}
        />
      ) : null}
      {!fixed && documents.data !== undefined ? (
        <ProposalSetChooser
          sets={sets}
          selected={selectedSet}
          onSelect={(documentUid) => {
            setChosenSet(documentUid);
            setChosenPass(null);
          }}
          partial={documents.data.page.next_cursor !== null}
        />
      ) : null}
      {fixed || sets.length > 0 ? (
        <StartOptimisationPass
          projectUid={projectUid}
          documentUid={selectedSet}
          canStart={roles.includes('expert')}
          onStarted={(startedId) => setChosenPass(startedId as OptimisationPassId)}
        />
      ) : null}
      {selectedSet !== null && passes.isPending ? <LoadingState what="проходов" /> : null}
      {passesFailure !== null ? (
        <ErrorState
          title="Проходы не прочитаны"
          detail={passesFailure.detail}
          correlationId={passesFailure.correlationId}
          onRetry={() => void passes.refetch()}
        />
      ) : null}
      {passes.data !== undefined && passesFailure === null ? (
        <>
          {missingPass !== null ? (
            <p className="am-note" role="status" data-pass-not-found={missingPass}>
              Проход из адреса не найден среди проходов этого комплекта: открыт последний.
            </p>
          ) : null}
          <PassList passes={list} active={activePass} onOpen={setChosenPass} />
          {activePass !== null ? (
            <ActivePass key={activePass} passId={activePass} canDecide={roles.includes('expert')} passes={list} />
          ) : null}
        </>
      ) : null}
    </section>
  );
}

/**
 * `R-151r`: the project's summary of optimisation by document. The passes and proposals live on each document's own
 * «Оптимизация» tab; the project lists its classified documents and links each one there.
 */
export function OptimisationByDocument({ projectUid }: { readonly projectUid: ProjectUid }) {
  const documents = useDocumentList(projectUid);
  const sets = classifiedDocumentSets(documents.data?.items ?? []);
  const failure = documents.error === null ? null : failureMessage(documents.error);
  return (
    <section className={styles.section} aria-labelledby="optimisation-by-document-heading" data-optimisation-by-document="">
      <h2 id="optimisation-by-document-heading" className={styles.heading}>Предложения по документам</h2>
      <p className={styles.rule}>
        Проходы оптимизации и предложения ведутся у каждого документа на его вкладке «Оптимизация». Здесь —
        документы проекта с подтверждённым разделом.
      </p>
      {documents.isPending ? <LoadingState what="документов проекта" /> : null}
      {failure !== null ? (
        <ErrorState
          title="Документы проекта не прочитаны"
          detail={failure.detail}
          correlationId={failure.correlationId}
          onRetry={() => void documents.refetch()}
        />
      ) : null}
      {documents.data !== undefined && sets.length === 0 ? (
        <p className="am-note">В проекте нет документов с подтверждённым разделом.</p>
      ) : null}
      {sets.length === 0 ? null : (
        <ul data-optimisation-documents={sets.length}>
          {sets.map((version) => (
            <li key={version.document_uid}>
              <Link href={routes.documentOptimisation(projectUid, version.document_uid)}>
                {version.display_title ?? version.source_filename ?? 'Комплект без названия'}
              </Link>
              {isComparisonOnly(version) ? ' — только для сравнения, оптимизация не запускается' : null}
            </li>
          ))}
        </ul>
      )}
      {documents.data !== undefined && documents.data.page.next_cursor !== null ? (
        <p className="am-note">Показаны документы первой страницы проекта.</p>
      ) : null}
    </section>
  );
}
