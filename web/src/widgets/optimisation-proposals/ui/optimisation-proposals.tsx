'use client';

/**
 * «Предложения» — the deterministic optimisation proposals of a document set's АР version
 * (`W60-OPT-PROPOSALS-01`), for the project's «Оптимизация» tab.
 *
 * **Which set.** The project's documents come from `listDocuments` (the cache entry the
 * project's structure reads); the sets offered are those whose **current** version an expert
 * confirmed as section АР. A project with none says so and where a section is confirmed.
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

import { useState } from 'react';

import type {
  DocumentUid,
  DocumentVersion,
  OptimisationPass,
  OptimisationPassId,
  ProjectUid,
  ProposalDecisionState,
  Role,
} from '@/shared/api';
import type { FailureMessage } from '@/shared/api/failure-message';
import { failureMessage } from '@/shared/api/failure-message';
import { formatInstant } from '@/shared/lib';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { useDocumentList } from '@/entities/document-version';
import {
  describeCounts,
  useOptimisationPasses,
  useOptimisationProposals,
} from '@/entities/optimisation-proposal';
import { StartOptimisationPass } from '@/features/start-optimisation-pass';

import { useExportProposalsCsv } from '../model/use-export-proposals-csv';
import styles from './optimisation-proposals.module.css';
import { PassSummary } from './pass-summary';
import { ProposalList } from './proposal-list';

export interface OptimisationProposalsProps {
  readonly projectUid: ProjectUid;
  /** The session's roles, as the route's guard read them. */
  readonly roles: readonly Role[];
}

/** The sets whose current version is confirmed as section АР, in the order listed. */
export function arDocumentSets(items: readonly DocumentVersion[]): readonly DocumentVersion[] {
  return items.filter((version) => version.classification?.section_code === 'AR');
}

function setLabel(version: DocumentVersion): string {
  const title = version.display_title ?? version.source_filename ?? 'Комплект без названия';
  return `${title} — версия ${version.version_ordinal}`;
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
  if (sets.length === 0) {
    return (
      <EmptyState
        title="В проекте нет комплектов раздела АР"
        detail="Предложения строятся для комплекта, текущую версию которого эксперт подтвердил как раздел АР. Подтвердите раздел на экране версии."
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
          data-proposal-set-chooser={sets.length}
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
}

/** «Выгрузить CSV» and its refusal, from state already in hand. Rendered by the harness. */
export function ExportProposalsView({ pending, failure, onDownload }: ExportProposalsViewProps) {
  return (
    <div data-proposals-export="">
      <p>
        <button type="button" className="am-button am-button--quiet" disabled={pending} onClick={onDownload}>
          Выгрузить CSV предложений
        </button>
      </p>
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
}

function ActivePass({ passId, canDecide }: ActivePassProps) {
  const [decision, setDecision] = useState<ProposalDecisionState | null>(null);
  const [offset, setOffset] = useState(0);
  const proposals = useOptimisationProposals(passId, decision, offset);
  const exporter = useExportProposalsCsv({ passId });
  const failure = proposals.error === null ? null : failureMessage(proposals.error);
  const exportFailure = exporter.error === null ? null : failureMessage(exporter.error);
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
          <PassSummary pass={proposals.data.optimisation_pass} />
          <ExportProposalsView
            pending={exporter.isPending}
            failure={exportFailure}
            onDownload={exporter.download}
          />
          <ProposalList
            page={proposals.data}
            canDecide={canDecide}
            onDecision={(state) => {
              setDecision(state);
              setOffset(0);
            }}
            onPage={proposals.isPlaceholderData ? null : setOffset}
          />
        </>
      ) : null}
    </div>
  );
}

export function OptimisationProposals({ projectUid, roles }: OptimisationProposalsProps) {
  const documents = useDocumentList(projectUid);
  const sets = arDocumentSets(documents.data?.items ?? []);
  const [chosenSet, setChosenSet] = useState<DocumentUid | null>(null);
  const [chosenPass, setChosenPass] = useState<OptimisationPassId | null>(null);
  const selectedSet = chosenSet ?? sets[0]?.document_uid ?? null;
  const passes = useOptimisationPasses(projectUid, selectedSet);
  const list = passes.data?.items ?? [];
  const activePass =
    chosenPass !== null && list.some((pass) => pass.optimisation_pass_id === chosenPass)
      ? chosenPass
      : (list[0]?.optimisation_pass_id ?? null);
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
      <p className={styles.rule}>
        Предложение — отдельная сущность рядом с замечаниями, со своими решениями экспертов,
        счётчиками и выгрузкой. Оно появляется, когда строка спецификации однозначно сопоставлена с
        позицией прайс-листа, а в том же прайс-листе есть более дешёвая позиция той же единицы
        измерения и валюты от поставщика из вендор-листа раздела АР. Цены берутся только из
        прайс-листа, экономия считается только при числовом количестве.
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
      {sets.length > 0 ? (
        <StartOptimisationPass
          projectUid={projectUid}
          documentUid={selectedSet}
          canStart={roles.includes('expert')}
          onStarted={(passId) => setChosenPass(passId as OptimisationPassId)}
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
          <PassList passes={list} active={activePass} onOpen={setChosenPass} />
          {activePass !== null ? (
            <ActivePass key={activePass} passId={activePass} canDecide={roles.includes('expert')} />
          ) : null}
        </>
      ) : null}
    </section>
  );
}
