'use client';

/**
 * Two versions of one document set compared (`W59-VERSION-COMPARE-01`).
 *
 * The reviewer chooses the other version of the same set; the widget orders the pair older
 * → newer (the server compares in that direction only) and asks `compareDocumentVersions`.
 * Everything it shows is the server's: a refusal and its reason, the proposed sheet pairs
 * with their evidence, one page of raw line differences, and the proposed matches between
 * the two runs' findings. **Proposals are labelled as proposals** — a sheet pair is only a
 * suggestion until an expert confirms it, nothing here matches a finding or records a
 * decision, and the raw differences are shown exactly as computed.
 *
 * **The stored layer** (`COMPARE-PERSISTED-SUMMARY-01`): on a proposed sheet pair an expert
 * may press «Подтвердить пару» and confirm it, and «Отозвать» on an approved one; the section
 * «Подтверждённые пары листов» lists the approved pairs and, only for them, the deterministic
 * differences the server recomputed from the stored text and sealed. When a page's text is no
 * longer the approved one the section says so and shows no difference. An account without
 * the expert role sees the state and no buttons.
 *
 * **The one write it leads to** (`W59-DECISION-CARRYOVER-01`): on a «Без изменений» row whose
 * older finding carries an expert decision and whose newer finding has none (the server's
 * `findings.carryover_candidates`), an expert may press «Перенести решение» and confirm it;
 * the newer finding then receives a new decision authored by that expert. Nothing is carried
 * without the confirmation, and an account without the expert role sees no button.
 *
 * «Стадии П → Р» (`mode=stage`, the W62 slice) is offered only when the older version is
 * confirmed at stage П and the newer at stage Р with one section; otherwise the ordinary
 * comparison is asked and, for a П/Р pair, refused with a reason that names the switch.
 *
 * The machine vocabulary stays in `data-` attributes (`data-comparison-outcome`,
 * `data-comparison-refusal`, `data-sheet-status`, `data-proposal-kind`); a reviewer reads
 * Russian.
 */

import { useState } from 'react';

import type {
  ApprovedSheetPair,
  ApprovedSheetPairs,
  CarryOverDecisionResponse,
  DiffHunk,
  DocumentUid,
  DocumentVersion,
  FindingMatchProposal,
  FindingRef,
  ProjectUid,
  SheetDiff,
  SheetPairing,
  VersionComparison as Comparison,
  VersionUid,
} from '@/shared/api';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { classifyListingFailure } from '@/shared/lib';
import { useMe } from '@/entities/account';
import { CATEGORY_LABELS } from '@/entities/expert-decision';
import {
  ClassificationBadges,
  COMPARISON_DIFF_LIMIT,
  PROPOSAL_BASIS_TEXT,
  PROPOSAL_KIND_LABELS,
  SHEET_STATUS_LABELS,
  TOO_LARGE_TEXT,
  canCarryOverDecision,
  carryoverCandidateOf,
  orderedPair,
  pairingBasisText,
  refusalText,
  stageModeOffered,
  useDocumentVersion,
  useVersionComparison,
  useVersionList,
  versionLabel,
} from '@/entities/document-version';
import {
  EVIDENCE_STATE_TEXT,
  LINK_STATE_TEXT,
  SheetPairingControls,
  approvalOf,
  isApprovablePair,
} from '@/entities/version-comparison';
import { CarriedDecisionNote, CarryOverDecision } from '@/features/carry-over-decision';

import styles from './version-comparison.module.css';

export interface VersionComparisonProps {
  readonly projectUid: ProjectUid;
  readonly versionUid: VersionUid;
}

export function VersionComparison({ projectUid, versionUid }: VersionComparisonProps) {
  const version = useDocumentVersion(versionUid);
  if (version.isPending) return <LoadingState what="версию" />;
  if (version.isError) {
    const failure = classifyListingFailure(version.error, {
      collection: 'версии комплекта',
      parent: 'version',
    });
    return (
      <ErrorState
        title={failure.title}
        detail={<span data-list-failure={failure.kind}>{failure.detail}</span>}
        correlationId={failure.correlationId}
      />
    );
  }
  return <SetComparison projectUid={projectUid} current={version.data} />;
}

/** The nearest older version, or else the nearest newer one: a default, never an identity. */
function defaultOther(current: DocumentVersion, others: readonly DocumentVersion[]): DocumentVersion {
  const older = others.filter((item) => item.version_ordinal < current.version_ordinal);
  if (older.length > 0) {
    return older.reduce((best, item) => (item.version_ordinal > best.version_ordinal ? item : best));
  }
  return others.reduce((best, item) => (item.version_ordinal < best.version_ordinal ? item : best));
}

function SetComparison({
  projectUid,
  current,
}: {
  readonly projectUid: ProjectUid;
  readonly current: DocumentVersion;
}) {
  const list = useVersionList(current.document_uid);
  const me = useMe();
  const mayCarry = me.data !== undefined && canCarryOverDecision(me.data.roles);
  const [chosenUid, setChosenUid] = useState<string | null>(null);
  const [stageMode, setStageMode] = useState(false);
  const [diffOffset, setDiffOffset] = useState(0);
  // Answers of carries completed on this screen, by the newer finding that received the
  // decision. The comparison is read again after a carry and then no longer lists the row as a
  // candidate, so the row's own state -- «Решение перенесено» -- would vanish with it.
  const [carried, setCarried] = useState<CarriedAnswers>({});

  const others = (list.data?.items ?? []).filter((item) => item.version_uid !== current.version_uid);
  const chosen = others.length === 0
    ? null
    : (others.find((item) => item.version_uid === chosenUid) ?? defaultOther(current, others));
  const pair = chosen === null ? null : orderedPair(current, chosen);
  const offered = pair !== null && stageModeOffered(pair.source, pair.target);
  const mode = offered && stageMode ? 'stage' : 'version';
  const comparison = useVersionComparison(
    pair === null
      ? null
      : {
          projectUid,
          documentUid: current.document_uid,
          sourceVersionUid: pair.source.version_uid,
          targetVersionUid: pair.target.version_uid,
          mode,
          diffOffset,
        },
  );

  if (list.isPending) return <LoadingState what="версии комплекта" />;
  if (list.isError) {
    const failure = classifyListingFailure(list.error, {
      collection: 'версии комплекта',
      parent: 'document',
    });
    return (
      <ErrorState
        title={failure.title}
        detail={<span data-list-failure={failure.kind}>{failure.detail}</span>}
        correlationId={failure.correlationId}
      />
    );
  }
  if (chosen === null || pair === null) {
    return (
      <EmptyState
        title="В комплекте пока одна версия."
        detail="Сравнивать её не с чем: другая версия этого комплекта ещё не опубликована."
      />
    );
  }

  return (
    <section className={styles.comparison} data-version-comparison="">
      <div className={styles.controls}>
        <label className={styles.choice}>
          <span>Сравнить с версией</span>
          <select
            value={chosen.version_uid}
            onChange={(event) => {
              setChosenUid(event.target.value);
              setDiffOffset(0);
            }}
          >
            {others.map((item) => (
              <option key={item.version_uid} value={item.version_uid}>
                {versionLabel(item)}
              </option>
            ))}
          </select>
        </label>
        {offered ? (
          <label className={styles.toggle}>
            <input
              type="checkbox"
              checked={stageMode}
              onChange={(event) => {
                setStageMode(event.target.checked);
                setDiffOffset(0);
              }}
            />{' '}
            Стадии П → Р
          </label>
        ) : null}
      </div>
      <p className={styles.pair}>
        <span>{versionLabel(pair.source)}</span>{' '}
        <ClassificationBadges classification={pair.source.classification} /> →{' '}
        <span>{versionLabel(pair.target)}</span>{' '}
        <ClassificationBadges classification={pair.target.classification} />
      </p>
      {comparison.isPending ? (
        <LoadingState what="сравнение версий" />
      ) : comparison.isError ? (
        <ComparisonFailure error={comparison.error} />
      ) : (
        <ComparisonResult
          comparison={comparison.data}
          onPage={setDiffOffset}
          carry={mayCarry ? { projectUid, documentUid: current.document_uid } : null}
          carried={carried}
          onCarried={(answer) => setCarried((held) => ({ ...held, [answer.event.finding_uid]: answer }))}
        />
      )}
    </section>
  );
}

function ComparisonFailure({ error }: { readonly error: unknown }) {
  const failure = classifyListingFailure(error, { collection: 'сравнение версий', parent: 'version' });
  return (
    <ErrorState
      title={failure.title}
      detail={<span data-list-failure={failure.kind}>{failure.detail}</span>}
      correlationId={failure.correlationId}
    />
  );
}

/** Where a carryover is sent; `null` when the account may not carry (not an expert). */
interface CarryContext {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
}

/** Completed carries by the finding that received the decision. */
export type CarriedAnswers = Readonly<Record<string, CarryOverDecisionResponse>>;

export function ComparisonResult({
  comparison,
  onPage,
  carry,
  carried = {},
  onCarried,
}: {
  readonly comparison: Comparison;
  readonly onPage: (offset: number) => void;
  readonly carry: CarryContext | null;
  readonly carried?: CarriedAnswers;
  readonly onCarried?: (answer: CarryOverDecisionResponse) => void;
}) {
  if (comparison.outcome === 'refused' || comparison.refusal !== null) {
    return (
      <div
        className={styles.refusal}
        role="status"
        data-comparison-outcome="refused"
        data-comparison-mode={comparison.mode}
        data-comparison-refusal={comparison.refusal?.reason ?? 'unknown'}
      >
        <p>
          <strong>Эти версии не сравниваются.</strong>{' '}
          {comparison.refusal === null ? 'Причина не указана.' : refusalText(comparison.refusal)}
        </p>
      </div>
    );
  }
  return (
    <div
      data-comparison-outcome="compared"
      data-comparison-mode={comparison.mode}
      data-comparison-sha256={comparison.comparison_sha256 ?? ''}
    >
      <p className={styles.note}>
        Пары листов и соответствия замечаний — предложения системы, а не решения эксперта: пока
        эксперт не подтвердил пару, они ничего не утверждают и не меняют. Построчные различия
        показаны так, как их дал детерминированный текст, без участия ИИ.
      </p>
      <SheetTable sheets={comparison.sheets} comparison={comparison} mayDecide={carry !== null} />
      {comparison.approved_pairs === null || comparison.approved_pairs === undefined ? null : (
        <ApprovedPairs approved={comparison.approved_pairs} />
      )}
      {comparison.sheet_diffs === null ? null : (
        <SheetDiffs page={comparison.sheet_diffs} onPage={onPage} />
      )}
      {comparison.findings === null ? null : (
        <FindingProposals
          findings={comparison.findings}
          comparison={comparison}
          carry={carry}
          carried={carried}
          onCarried={onCarried}
        />
      )}
    </div>
  );
}

function pageText(number: number | null): string {
  return number === null ? '—' : `лист ${number}`;
}

function SheetTable({
  sheets,
  comparison,
  mayDecide,
}: {
  readonly sheets: readonly SheetPairing[];
  readonly comparison: Comparison;
  readonly mayDecide: boolean;
}) {
  const approved = comparison.approved_pairs ?? null;
  const view = {
    projectUid: comparison.project_uid,
    documentUid: comparison.document_uid,
    sourceVersionUid: comparison.source_version_uid,
    targetVersionUid: comparison.target_version_uid,
    mode: comparison.mode,
    sourceRunId: comparison.source?.run_id ?? null,
    targetRunId: comparison.target?.run_id ?? null,
  };
  const counts = new Map<SheetPairing['status'], number>();
  for (const sheet of sheets) counts.set(sheet.status, (counts.get(sheet.status) ?? 0) + 1);
  return (
    <>
      <h3>Сопоставление листов (предложение)</h3>
      <p className={styles.summary}>
        Без изменений: {counts.get('unchanged') ?? 0} · изменено: {counts.get('changed') ?? 0} ·
        удалено: {counts.get('removed') ?? 0} · добавлено: {counts.get('added') ?? 0}.
      </p>
      <div className={styles.scroller}>
        <table>
          <thead>
            <tr>
              <th scope="col">Более ранняя версия</th>
              <th scope="col">Более поздняя версия</th>
              <th scope="col">Состояние</th>
              <th scope="col">Основание пары</th>
              <th scope="col">Подтверждение эксперта</th>
            </tr>
          </thead>
          <tbody>
            {sheets.map((sheet) => (
              <tr
                key={`${sheet.source_page_number ?? 0}-${sheet.target_page_number ?? 0}`}
                data-sheet-status={sheet.status}
                data-suggestion-sha256={sheet.suggestion_sha256 ?? ''}
              >
                <td>{pageText(sheet.source_page_number)}</td>
                <td>{pageText(sheet.target_page_number)}</td>
                <td>{SHEET_STATUS_LABELS[sheet.status]}</td>
                <td>{pairingBasisText(sheet)}</td>
                <td>
                  {isApprovablePair(sheet) ? (
                    <SheetPairingControls
                      sheet={sheet}
                      approval={approvalOf(approved, sheet)}
                      mayDecide={mayDecide}
                      view={view}
                    />
                  ) : (
                    <span>—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function ApprovedPairDiff({ item }: { readonly item: ApprovedSheetPair }) {
  if (item.diff === null) return null;
  return (
    <>
      <p className={styles.summary}>
        Добавлено строк: {item.diff.added_line_count} · удалено строк: {item.diff.removed_line_count}.
      </p>
      <div className={styles.hunks} data-evidence-sha256={item.diff.evidence_sha256}>
        {item.diff.hunks.map((hunk) => (
          <div
            key={`${hunk.source_start}-${hunk.target_start}-${hunk.tag}`}
            data-hunk-id={hunk.hunk_id ?? ''}
          >
            <Hunk hunk={hunk} />
          </div>
        ))}
      </div>
    </>
  );
}

/**
 * The pairs an expert approved and their deterministic differences. The server recomputes the
 * differences from the stored text and seals them; when it withholds them (`evidence_state`) this
 * says why in words instead of showing a list that looks complete.
 */
function ApprovedPairs({ approved }: { readonly approved: ApprovedSheetPairs }) {
  return (
    <section
      data-approved-pairs={approved.evidence_state}
      data-raw-evidence-seal={approved.raw_evidence_seal_sha256 ?? ''}
    >
      <h3>Подтверждённые пары листов</h3>
      <p className={styles.summary}>{EVIDENCE_STATE_TEXT[approved.evidence_state]}</p>
      {approved.items.map((item) => (
        <article
          key={item.sheet_link_id}
          className={styles.diff}
          data-approved-pair={item.sheet_link_id}
          data-approved-pair-state={item.state}
        >
          <h4>
            Лист {item.source_page_number} → лист {item.target_page_number}
          </h4>
          <p className={styles.summary}>
            Подтвердил: {item.approved_by_label}. {LINK_STATE_TEXT[item.state]}
          </p>
          <ApprovedPairDiff item={item} />
        </article>
      ))}
    </section>
  );
}

function diffHeading(diff: SheetDiff): string {
  if (diff.status === 'added') return `Лист ${diff.target_page_number ?? '—'} более поздней версии добавлен`;
  if (diff.status === 'removed') return `Лист ${diff.source_page_number ?? '—'} более ранней версии удалён`;
  return `Лист ${diff.source_page_number ?? '—'} → лист ${diff.target_page_number ?? '—'}`;
}

function Hunk({ hunk }: { readonly hunk: DiffHunk }) {
  if (hunk.tag === 'equal') {
    const count = hunk.source_end - hunk.source_start;
    return <p className={styles.equal} data-hunk="equal">… строк без изменений: {count} …</p>;
  }
  return (
    <div data-hunk={hunk.tag}>
      {hunk.source_lines.map((line, index) => (
        <del key={`d${index}`} className={styles.line}>
          <span className={styles.lineNumber}>{hunk.source_start + index + 1}</span>− {line}
        </del>
      ))}
      {hunk.target_lines.map((line, index) => (
        <ins key={`i${index}`} className={styles.line}>
          <span className={styles.lineNumber}>{hunk.target_start + index + 1}</span>+ {line}
        </ins>
      ))}
    </div>
  );
}

function SheetDiffs({
  page,
  onPage,
}: {
  readonly page: NonNullable<Comparison['sheet_diffs']>;
  readonly onPage: (offset: number) => void;
}) {
  return (
    <>
      <h3>Построчные различия</h3>
      {page.total === 0 ? (
        <p className={styles.summary}>Текст ни одного сопоставленного листа не изменился.</p>
      ) : (
        <p className={styles.summary}>
          Листы с различиями: {page.offset + 1}–{page.offset + page.items.length} из {page.total}.
        </p>
      )}
      {page.items.map((diff) => (
        <article
          key={`${diff.source_page_number ?? 0}-${diff.target_page_number ?? 0}`}
          className={styles.diff}
          data-sheet-diff={diff.status}
          data-evidence-sha256={diff.evidence_sha256 ?? ''}
        >
          <h4>{diffHeading(diff)}</h4>
          {diff.outcome === 'too_large' ? (
            <p>{diff.too_large_reason === null ? 'Лист слишком велик для сравнения.' : TOO_LARGE_TEXT[diff.too_large_reason]}</p>
          ) : (
            <>
              <p className={styles.summary}>
                Добавлено строк: {diff.added_line_count ?? 0} · удалено строк: {diff.removed_line_count ?? 0}.
              </p>
              <div className={styles.hunks}>
                {diff.hunks.map((hunk) => (
                  <Hunk key={`${hunk.source_start}-${hunk.target_start}-${hunk.tag}`} hunk={hunk} />
                ))}
              </div>
            </>
          )}
        </article>
      ))}
      {page.offset > 0 || page.next_offset !== null ? (
        <p className={styles.controls}>
          {page.offset > 0 ? (
            <button
              type="button"
              className="am-button"
              onClick={() => onPage(Math.max(0, page.offset - COMPARISON_DIFF_LIMIT))}
            >
              Предыдущие листы
            </button>
          ) : null}{' '}
          {page.next_offset !== null ? (
            <button type="button" className="am-button" onClick={() => onPage(page.next_offset ?? 0)}>
              Следующие листы
            </button>
          ) : null}
        </p>
      ) : null}
    </>
  );
}

function FindingCell({ finding }: { readonly finding: FindingRef | null }) {
  if (finding === null) return <span>—</span>;
  return (
    <span data-finding-uid={finding.finding_uid}>
      <span className={styles.category}>{CATEGORY_LABELS[finding.category]}</span>{' '}
      {finding.finding_text}{' '}
      <span className={styles.pages}>
        ({finding.page_numbers.map((page) => `лист ${page}`).join(', ')})
      </span>
    </span>
  );
}

function CarryCell({
  findings,
  proposal,
  comparison,
  carry,
  carried,
  onCarried,
}: {
  readonly findings: NonNullable<Comparison['findings']>;
  readonly proposal: FindingMatchProposal;
  readonly comparison: Comparison;
  readonly carry: CarryContext | null;
  readonly carried: CarriedAnswers;
  readonly onCarried: ((answer: CarryOverDecisionResponse) => void) | undefined;
}) {
  const done = proposal.target_finding === null ? undefined : carried[proposal.target_finding.finding_uid];
  if (done !== undefined) return <CarriedDecisionNote result={done} />;
  const candidate = carryoverCandidateOf(findings, proposal);
  if (candidate === null || proposal.target_finding === null) return <span>—</span>;
  if (carry === null) {
    return (
      <span className="am-note" data-carryover-state="read-only">
        Решение более ранней версии может перенести эксперт.
      </span>
    );
  }
  return (
    <CarryOverDecision
      target={proposal.target_finding}
      command={{
        projectUid: carry.projectUid,
        documentUid: carry.documentUid,
        sourceVersionUid: comparison.source_version_uid,
        targetVersionUid: comparison.target_version_uid,
        mode: comparison.mode,
        candidate,
        targetRunId: comparison.target?.run_id ?? null,
      }}
      onCarried={onCarried}
    />
  );
}

function FindingProposals({
  findings,
  comparison,
  carry,
  carried,
  onCarried,
}: {
  readonly findings: NonNullable<Comparison['findings']>;
  readonly comparison: Comparison;
  readonly carry: CarryContext | null;
  readonly carried: CarriedAnswers;
  readonly onCarried: ((answer: CarryOverDecisionResponse) => void) | undefined;
}) {
  return (
    <>
      <h3>Соответствие замечаний (предложение)</h3>
      {findings.status === 'unavailable' ? (
        <p className={styles.summary} data-findings-unavailable={findings.unavailable_reason ?? ''}>
          Замечаний больше двухсот в одном из прогонов — соответствие не строится, чтобы не
          показывать неполный список.
        </p>
      ) : findings.proposals.length === 0 ? (
        <p className={styles.summary}>Ни в одном из двух прогонов нет опубликованных замечаний.</p>
      ) : (
        <div className={styles.scroller}>
          <table>
            <thead>
              <tr>
                <th scope="col">Предложение</th>
                <th scope="col">Более ранняя версия</th>
                <th scope="col">Более поздняя версия</th>
                <th scope="col">Основание</th>
                <th scope="col">Решение эксперта</th>
              </tr>
            </thead>
            <tbody>
              {findings.proposals.map((proposal: FindingMatchProposal) => (
                <tr
                  key={`${proposal.source_finding?.finding_uid ?? ''}-${proposal.target_finding?.finding_uid ?? ''}`}
                  data-proposal-kind={proposal.kind}
                >
                  <td>{PROPOSAL_KIND_LABELS[proposal.kind]}</td>
                  <td><FindingCell finding={proposal.source_finding} /></td>
                  <td><FindingCell finding={proposal.target_finding} /></td>
                  <td>{PROPOSAL_BASIS_TEXT[proposal.basis]}</td>
                  <td>
                    <CarryCell
                      findings={findings}
                      proposal={proposal}
                      comparison={comparison}
                      carry={carry}
                      carried={carried}
                      onCarried={onCarried}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
